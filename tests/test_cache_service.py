"""
Unit tests for the CacheService class.
"""

import pytest
import json
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from fakeredis import aioredis

from api.services.cache_service import CacheService


class TestCacheService:
    """Test suite for CacheService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.redis_url = "redis://localhost:6379/0"
        self.cache_service = CacheService(self.redis_url)
        
    def test_init(self):
        """Test CacheService initialization."""
        assert self.cache_service.redis_url == self.redis_url
        assert self.cache_service.redis_client is None
        assert self.cache_service.default_ttl == 3600
        assert self.cache_service.auth_ttl == 300
        
    def test_init_with_default_redis_url(self):
        """Test CacheService initialization with default Redis URL."""
        cache_service = CacheService()
        assert "redis://localhost:6379/0" in cache_service.redis_url
        
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful Redis connection."""
        fake_redis = aioredis.FakeRedis()
        
        with patch('redis.asyncio.from_url', return_value=fake_redis):
            await self.cache_service.connect()
            assert self.cache_service.redis_client is not None
            
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('redis.asyncio.from_url', return_value=mock_redis):
            with pytest.raises(Exception) as exc_info:
                await self.cache_service.connect()
            assert "Connection failed" in str(exc_info.value)
            
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test Redis disconnection."""
        mock_redis = AsyncMock()
        self.cache_service.redis_client = mock_redis
        
        await self.cache_service.disconnect()
        mock_redis.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_disconnect_no_client(self):
        """Test disconnection when no client exists."""
        # Should not raise an exception
        await self.cache_service.disconnect()
        
    def test_generate_cache_key(self):
        """Test cache key generation."""
        key = self.cache_service._generate_cache_key("test", param1="value1", param2="value2")
        assert key.startswith("test:")
        assert len(key) > 10  # Should have hash
        
        # Same parameters should generate same key
        key2 = self.cache_service._generate_cache_key("test", param1="value1", param2="value2")
        assert key == key2
        
        # Different parameters should generate different keys
        key3 = self.cache_service._generate_cache_key("test", param1="value1", param2="value3")
        assert key != key3
        
    def test_generate_cache_key_parameter_order(self):
        """Test that parameter order doesn't affect key generation."""
        key1 = self.cache_service._generate_cache_key("test", a="1", b="2", c="3")
        key2 = self.cache_service._generate_cache_key("test", c="3", a="1", b="2")
        assert key1 == key2
        
    @pytest.mark.asyncio
    async def test_get_inference_cache_no_client(self):
        """Test get_inference_cache when no Redis client."""
        result = await self.cache_service.get_inference_cache("test context")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_get_inference_cache_hit(self):
        """Test successful cache hit for inference."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache
        cache_key = self.cache_service._generate_cache_key(
            "inference", input_context="test context", max_length=512, temperature=0.3
        )
        await fake_redis.set(cache_key, "cached result")
        
        result = await self.cache_service.get_inference_cache("test context")
        assert result == "cached result"
        
    @pytest.mark.asyncio
    async def test_get_inference_cache_miss(self):
        """Test cache miss for inference."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.get_inference_cache("test context")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_get_inference_cache_error(self):
        """Test error handling in get_inference_cache."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        self.cache_service.redis_client = mock_redis
        
        result = await self.cache_service.get_inference_cache("test context")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_set_inference_cache_no_client(self):
        """Test set_inference_cache when no Redis client."""
        result = await self.cache_service.set_inference_cache("test context", "result")
        assert result is False
        
    @pytest.mark.asyncio
    async def test_set_inference_cache_success(self):
        """Test successful cache set for inference."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.set_inference_cache("test context", "result")
        assert result is True
        
        # Verify the value was set
        cache_key = self.cache_service._generate_cache_key(
            "inference", input_context="test context", max_length=512, temperature=0.3
        )
        cached_value = await fake_redis.get(cache_key)
        assert cached_value == "result"
        
    @pytest.mark.asyncio
    async def test_set_inference_cache_with_ttl(self):
        """Test cache set with custom TTL."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.set_inference_cache("test context", "result", ttl=1800)
        assert result is True
        
    @pytest.mark.asyncio
    async def test_set_inference_cache_error(self):
        """Test error handling in set_inference_cache."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")
        self.cache_service.redis_client = mock_redis
        
        result = await self.cache_service.set_inference_cache("test context", "result")
        assert result is False
        
    @pytest.mark.asyncio
    async def test_get_batch_inference_cache_success(self):
        """Test successful batch inference cache retrieval."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache
        cache_key = self.cache_service._generate_cache_key(
            "batch_inference", 
            input_contexts=["context1", "context2"], 
            batch_size=2, 
            max_length=128, 
            temperature=0.7
        )
        await fake_redis.set(cache_key, json.dumps(["result1", "result2"]))
        
        result = await self.cache_service.get_batch_inference_cache(
            ["context1", "context2"], batch_size=2
        )
        assert result == ["result1", "result2"]
        
    @pytest.mark.asyncio
    async def test_get_batch_inference_cache_invalid_json(self):
        """Test batch inference cache with invalid JSON."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache with invalid JSON
        cache_key = self.cache_service._generate_cache_key(
            "batch_inference", 
            input_contexts=["context1"], 
            batch_size=1, 
            max_length=128, 
            temperature=0.7
        )
        await fake_redis.set(cache_key, "invalid json")
        
        result = await self.cache_service.get_batch_inference_cache(["context1"])
        assert result is None
        
    @pytest.mark.asyncio
    async def test_set_batch_inference_cache_success(self):
        """Test successful batch inference cache storage."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.set_batch_inference_cache(
            ["context1", "context2"], ["result1", "result2"], batch_size=2
        )
        assert result is True
        
        # Verify the value was set
        cache_key = self.cache_service._generate_cache_key(
            "batch_inference", 
            input_contexts=["context1", "context2"], 
            batch_size=2, 
            max_length=128, 
            temperature=0.7
        )
        cached_value = await fake_redis.get(cache_key)
        assert json.loads(cached_value) == ["result1", "result2"]
        
    @pytest.mark.asyncio
    async def test_get_auth_cache_success(self):
        """Test successful auth cache retrieval."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache
        cache_key = self.cache_service._generate_cache_key("auth", auth_key="test_key")
        await fake_redis.set(cache_key, "true")
        
        result = await self.cache_service.get_auth_cache("test_key")
        assert result is True
        
    @pytest.mark.asyncio
    async def test_get_auth_cache_false(self):
        """Test auth cache retrieval returning False."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache
        cache_key = self.cache_service._generate_cache_key("auth", auth_key="test_key")
        await fake_redis.set(cache_key, "false")
        
        result = await self.cache_service.get_auth_cache("test_key")
        assert result is False
        
    @pytest.mark.asyncio
    async def test_set_auth_cache_success(self):
        """Test successful auth cache storage."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.set_auth_cache("test_key", True)
        assert result is True
        
        # Verify the value was set
        cache_key = self.cache_service._generate_cache_key("auth", auth_key="test_key")
        cached_value = await fake_redis.get(cache_key)
        assert cached_value == "True"
        
    @pytest.mark.asyncio
    async def test_invalidate_cache_no_client(self):
        """Test cache invalidation when no Redis client."""
        result = await self.cache_service.invalidate_cache("test:*")
        assert result == 0
        
    @pytest.mark.asyncio
    async def test_invalidate_cache_success(self):
        """Test successful cache invalidation."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        # Pre-populate cache
        await fake_redis.set("test:key1", "value1")
        await fake_redis.set("test:key2", "value2")
        await fake_redis.set("other:key", "value3")
        
        result = await self.cache_service.invalidate_cache("test:*")
        assert result == 2
        
        # Verify only test keys were deleted
        assert await fake_redis.get("test:key1") is None
        assert await fake_redis.get("test:key2") is None
        assert await fake_redis.get("other:key") == "value3"
        
    @pytest.mark.asyncio
    async def test_invalidate_cache_no_pattern(self):
        """Test cache invalidation with no pattern."""
        fake_redis = aioredis.FakeRedis()
        self.cache_service.redis_client = fake_redis
        
        result = await self.cache_service.invalidate_cache()
        assert result == 0
        
    @pytest.mark.asyncio
    async def test_get_cache_stats_no_client(self):
        """Test get_cache_stats when no Redis client."""
        result = await self.cache_service.get_cache_stats()
        assert result == {}
        
    @pytest.mark.asyncio
    async def test_get_cache_stats_success(self):
        """Test successful cache stats retrieval."""
        mock_redis = AsyncMock()
        mock_redis.info.return_value = {
            "connected_clients": 1,
            "used_memory": 1024,
            "used_memory_human": "1KB",
            "keyspace_hits": 100,
            "keyspace_misses": 10,
            "total_commands_processed": 1000
        }
        self.cache_service.redis_client = mock_redis
        
        result = await self.cache_service.get_cache_stats()
        assert result["connected_clients"] == 1
        assert result["used_memory"] == 1024
        assert result["keyspace_hits"] == 100
        
    @pytest.mark.asyncio
    async def test_get_cache_stats_error(self):
        """Test error handling in get_cache_stats."""
        mock_redis = AsyncMock()
        mock_redis.info.side_effect = Exception("Redis error")
        self.cache_service.redis_client = mock_redis
        
        result = await self.cache_service.get_cache_stats()
        assert result == {}


@pytest.mark.parametrize("input_context,max_length,temperature", [
    ("test context", 512, 0.3),
    ("another context", 256, 0.7),
    ("", 128, 0.5),
    ("long context with many words", 1024, 0.1),
])
@pytest.mark.asyncio
async def test_inference_cache_roundtrip(input_context, max_length, temperature):
    """Parametrized test for inference cache roundtrip."""
    cache_service = CacheService()
    fake_redis = aioredis.FakeRedis()
    cache_service.redis_client = fake_redis
    
    # Test cache miss
    result = await cache_service.get_inference_cache(
        input_context, max_length=max_length, temperature=temperature
    )
    assert result is None
    
    # Set cache
    test_result = f"Generated result for {input_context}"
    success = await cache_service.set_inference_cache(
        input_context, test_result, max_length=max_length, temperature=temperature
    )
    assert success is True
    
    # Test cache hit
    cached_result = await cache_service.get_inference_cache(
        input_context, max_length=max_length, temperature=temperature
    )
    assert cached_result == test_result


@pytest.mark.asyncio
async def test_cache_service_integration():
    """Integration test for cache service with multiple operations."""
    cache_service = CacheService()
    fake_redis = aioredis.FakeRedis()
    cache_service.redis_client = fake_redis
    
    # Test auth cache
    await cache_service.set_auth_cache("user123", True)
    auth_result = await cache_service.get_auth_cache("user123")
    assert auth_result is True
    
    # Test inference cache
    await cache_service.set_inference_cache("test input", "test output")
    inference_result = await cache_service.get_inference_cache("test input")
    assert inference_result == "test output"
    
    # Test batch inference cache
    await cache_service.set_batch_inference_cache(
        ["input1", "input2"], ["output1", "output2"], batch_size=2
    )
    batch_result = await cache_service.get_batch_inference_cache(
        ["input1", "input2"], batch_size=2
    )
    assert batch_result == ["output1", "output2"]
    
    # Test invalidation
    deleted_count = await cache_service.invalidate_cache("*")
    assert deleted_count >= 3  # At least the keys we set 