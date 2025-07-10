from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.v1 import endpoints
from api.services.inference_service import InferenceService
from api.services.cache_service import cache_service
from api.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan (startup and shutdown).
    """
    # Startup
    logger.info("Starting LeaderOracle API...")
    
    # Initialize cache service if enabled
    if settings.CACHE_ENABLED:
        try:
            await cache_service.connect()
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            logger.info("Continuing without cache...")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LeaderOracle API...")
    
    # Close cache service connection
    if settings.CACHE_ENABLED:
        try:
            await cache_service.disconnect()
            logger.info("Cache service disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting cache service: {e}")

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# CORS configuration: Allow traffic from localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://leader-oracle-ai.fly.dev"],  # Allow requests from localhost:3000
    allow_credentials=True,                   # Allow cookies to be sent
    allow_methods=["*"],                      # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],                      # Allow all headers
)

# Include API endpoints
app.include_router(endpoints.router, prefix="/api/v1")

# Add health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    cache_status = "connected" if cache_service.redis_client else "disconnected"
    return {
        "status": "healthy",
        "cache_status": cache_status,
        "cache_enabled": settings.CACHE_ENABLED
    }

# Add cache statistics endpoint
@app.get("/api/v1/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    if not settings.CACHE_ENABLED:
        return {"error": "Cache is disabled"}
    
    stats = await cache_service.get_cache_stats()
    return {"cache_stats": stats}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )