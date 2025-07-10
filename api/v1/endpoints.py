import logging
from api.services.inference_service import InferenceService
from api.services.authentication_service import AuthenticationService
from api.services.cache_service import cache_service
from api.core.config import settings
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/inference")
async def inference(
    input_context: str,  # Expecting a single string input
    auth_key: str,
    max_length: int = Query(512),  # Allow custom max_length via the request
    temperature: float = Query(0.3)  # Allow custom temperature via the request
):
    """
    Endpoint for single inference (batch size 1), where user submits a single string as input.
    """
    try:
        # Initialize the inference service
        inference_service = InferenceService(auth_key)
        
        # Check authentication (with caching)
        cached_auth = None
        if settings.CACHE_ENABLED:
            cached_auth = await cache_service.get_auth_cache(auth_key)
        
        if cached_auth is None:
            # Validate the auth_key
            AuthenticationService(auth_key).raise_exception_if_invalid()
            # Cache the authentication result
            if settings.CACHE_ENABLED:
                await cache_service.set_auth_cache(auth_key, True)
        elif not cached_auth:
            raise HTTPException(status_code=401, detail="Invalid authentication key")
        
        # Check cache for inference result
        cached_result = None
        if settings.CACHE_ENABLED:
            cached_result = await cache_service.get_inference_cache(
                input_context=input_context,
                max_length=max_length,
                temperature=temperature
            )
        
        if cached_result is not None:
            logger.info("Returning cached inference result")
            return {"generated_text": cached_result}
        
        # Call the generate_text method for a single input context (batch size 1)
        generated_text = inference_service.generate_text(
            input_context, 
            max_length=max_length, 
            temperature=temperature
        )
        
        # Cache the result
        if settings.CACHE_ENABLED:
            await cache_service.set_inference_cache(
                input_context=input_context,
                result=generated_text,
                max_length=max_length,
                temperature=temperature
            )
        
        return {"generated_text": generated_text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during inference: {e}")
        raise HTTPException(status_code=500, detail=f"Text generation failed: {str(e)}")


@router.post("/batch_inference")
async def batch_inference(
    input_context: str,  # A single input string
    auth_key: str,
    num_batches: int = Query(1),  # Number of times to duplicate the input to simulate batch size
    max_length: int = Query(128),
    temperature: float = Query(0.7)
):
    """
    Endpoint for batch inference, where the user submits a single string that will be duplicated.
    """
    try:
        # Initialize the inference service
        inference_service = InferenceService(auth_key)
        
        # Check authentication (with caching)
        cached_auth = None
        if settings.CACHE_ENABLED:
            cached_auth = await cache_service.get_auth_cache(auth_key)
        
        if cached_auth is None:
            # Validate the auth_key
            AuthenticationService(auth_key).raise_exception_if_invalid()
            # Cache the authentication result
            if settings.CACHE_ENABLED:
                await cache_service.set_auth_cache(auth_key, True)
        elif not cached_auth:
            raise HTTPException(status_code=401, detail="Invalid authentication key")

        # Duplicate the single input context for batch processing
        input_contexts = [input_context] * num_batches
        
        # Check cache for batch inference result
        cached_result = None
        if settings.CACHE_ENABLED:
            cached_result = await cache_service.get_batch_inference_cache(
                input_contexts=input_contexts,
                batch_size=num_batches,
                max_length=max_length,
                temperature=temperature
            )
        
        if cached_result is not None:
            logger.info("Returning cached batch inference result")
            return {"generated_texts": cached_result}

        # Call the batch generate_text_with_batch_size method
        generated_texts = inference_service.generate_text_with_batch_size(
            input_contexts, 
            batch_size=num_batches, 
            max_length=max_length, 
            temperature=temperature
        )
        
        # Cache the result
        if settings.CACHE_ENABLED:
            await cache_service.set_batch_inference_cache(
                input_contexts=input_contexts,
                results=generated_texts,
                batch_size=num_batches,
                max_length=max_length,
                temperature=temperature
            )
        
        return {"generated_texts": generated_texts}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during batch inference: {e}")
        raise HTTPException(status_code=500, detail=f"Batch text generation failed: {str(e)}")


@router.get("/login")
async def login(
    auth_key: str = Body(...),
):
    """
    Endpoint for login validation.
    """
    try:
        # Check cache first
        cached_auth = None
        if settings.CACHE_ENABLED:
            cached_auth = await cache_service.get_auth_cache(auth_key)
        
        if cached_auth is not None:
            logger.debug("Returning cached authentication result")
            return {'authenticated': cached_auth}
        
        # Validate authentication
        authentication_service = AuthenticationService(auth_key)
        is_valid = authentication_service.is_valid()
        
        # Cache the result
        if settings.CACHE_ENABLED:
            await cache_service.set_auth_cache(auth_key, is_valid)
        
        return {'authenticated': is_valid}

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/cache/invalidate")
async def invalidate_cache(
    auth_key: str = Body(...),
    pattern: Optional[str] = Body(None)
):
    """
    Endpoint to invalidate cache entries.
    Admin endpoint - requires valid authentication.
    """
    try:
        # Validate authentication
        AuthenticationService(auth_key).raise_exception_if_invalid()
        
        if not settings.CACHE_ENABLED:
            return {"error": "Cache is disabled"}
        
        # Default pattern invalidates all caches
        if pattern is None:
            pattern = "*"
        
        deleted_count = await cache_service.invalidate_cache(pattern)
        
        return {
            "message": f"Invalidated {deleted_count} cache entries",
            "pattern": pattern
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.get("/cache/health")
async def cache_health():
    """
    Check cache service health.
    """
    if not settings.CACHE_ENABLED:
        return {"status": "disabled", "cache_enabled": False}
    
    try:
        stats = await cache_service.get_cache_stats()
        return {
            "status": "healthy",
            "cache_enabled": True,
            "connected": cache_service.redis_client is not None,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "cache_enabled": True,
            "connected": False,
            "error": str(e)
        }