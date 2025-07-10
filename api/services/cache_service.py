"""
Redis-based caching service for improving API scalability.
"""

import json
import hashlib
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
import redis.asyncio as redis
from api.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based caching service for caching inference results and authentication tokens.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize the cache service.
        
        Args:
            redis_url: Redis connection URL. If None, uses settings.REDIS_URL
        """
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour default TTL
        self.auth_ttl = 300  # 5 minutes for auth cache
        
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
            
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a cache key based on prefix and parameters.
        
        Args:
            prefix: Key prefix (e.g., 'inference', 'auth')
            **kwargs: Parameters to include in the key
            
        Returns:
            str: Generated cache key
        """
        # Sort parameters for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_string = json.dumps(sorted_params, sort_keys=True)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
        
    async def get_inference_cache(self, input_context: str, max_length: int = 512, 
                                 temperature: float = 0.3, **kwargs) -> Optional[str]:
        """
        Get cached inference result.
        
        Args:
            input_context: Input context for inference
            max_length: Maximum generation length
            temperature: Temperature parameter
            **kwargs: Additional parameters
            
        Returns:
            Optional[str]: Cached result if exists, None otherwise
        """
        if not self.redis_client:
            return None
            
        cache_key = self._generate_cache_key(
            "inference",
            input_context=input_context,
            max_length=max_length,
            temperature=temperature,
            **kwargs
        )
        
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for inference key: {cache_key}")
                return cached_result
            else:
                logger.debug(f"Cache miss for inference key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None
            
    async def set_inference_cache(self, input_context: str, result: str, 
                                 max_length: int = 512, temperature: float = 0.3, 
                                 ttl: int = None, **kwargs) -> bool:
        """
        Cache inference result.
        
        Args:
            input_context: Input context for inference
            result: Generated text result
            max_length: Maximum generation length
            temperature: Temperature parameter
            ttl: Time to live in seconds
            **kwargs: Additional parameters
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False
            
        cache_key = self._generate_cache_key(
            "inference",
            input_context=input_context,
            max_length=max_length,
            temperature=temperature,
            **kwargs
        )
        
        try:
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(cache_key, ttl, result)
            logger.info(f"Cached inference result with key: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error caching inference result: {e}")
            return False
            
    async def get_batch_inference_cache(self, input_contexts: list, batch_size: int = 1,
                                       max_length: int = 128, temperature: float = 0.7,
                                       **kwargs) -> Optional[list]:
        """
        Get cached batch inference result.
        
        Args:
            input_contexts: List of input contexts
            batch_size: Batch size
            max_length: Maximum generation length
            temperature: Temperature parameter
            **kwargs: Additional parameters
            
        Returns:
            Optional[list]: Cached results if exists, None otherwise
        """
        if not self.redis_client:
            return None
            
        cache_key = self._generate_cache_key(
            "batch_inference",
            input_contexts=input_contexts,
            batch_size=batch_size,
            max_length=max_length,
            temperature=temperature,
            **kwargs
        )
        
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for batch inference key: {cache_key}")
                return json.loads(cached_result)
            else:
                logger.debug(f"Cache miss for batch inference key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving batch result from cache: {e}")
            return None
            
    async def set_batch_inference_cache(self, input_contexts: list, results: list,
                                       batch_size: int = 1, max_length: int = 128,
                                       temperature: float = 0.7, ttl: int = None,
                                       **kwargs) -> bool:
        """
        Cache batch inference results.
        
        Args:
            input_contexts: List of input contexts
            results: List of generated text results
            batch_size: Batch size
            max_length: Maximum generation length
            temperature: Temperature parameter
            ttl: Time to live in seconds
            **kwargs: Additional parameters
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False
            
        cache_key = self._generate_cache_key(
            "batch_inference",
            input_contexts=input_contexts,
            batch_size=batch_size,
            max_length=max_length,
            temperature=temperature,
            **kwargs
        )
        
        try:
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(cache_key, ttl, json.dumps(results))
            logger.info(f"Cached batch inference results with key: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error caching batch inference results: {e}")
            return False
            
    async def get_auth_cache(self, auth_key: str) -> Optional[bool]:
        """
        Get cached authentication result.
        
        Args:
            auth_key: Authentication key
            
        Returns:
            Optional[bool]: Cached auth result if exists, None otherwise
        """
        if not self.redis_client:
            return None
            
        cache_key = self._generate_cache_key("auth", auth_key=auth_key)
        
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for auth key: {cache_key}")
                return cached_result.lower() == 'true'
            else:
                logger.debug(f"Cache miss for auth key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving auth result from cache: {e}")
            return None
            
    async def set_auth_cache(self, auth_key: str, is_valid: bool, ttl: int = None) -> bool:
        """
        Cache authentication result.
        
        Args:
            auth_key: Authentication key
            is_valid: Whether the key is valid
            ttl: Time to live in seconds
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not self.redis_client:
            return False
            
        cache_key = self._generate_cache_key("auth", auth_key=auth_key)
        
        try:
            ttl = ttl or self.auth_ttl
            await self.redis_client.setex(cache_key, ttl, str(is_valid))
            logger.debug(f"Cached auth result with key: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error caching auth result: {e}")
            return False
            
    async def invalidate_cache(self, pattern: str = None) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Cache key pattern to match (e.g., 'inference:*')
            
        Returns:
            int: Number of keys deleted
        """
        if not self.redis_client:
            return 0
            
        try:
            if pattern:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted = await self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {deleted} cache entries with pattern: {pattern}")
                    return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0
            
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        if not self.redis_client:
            return {}
            
        try:
            info = await self.redis_client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


# Global cache service instance
cache_service = CacheService() 