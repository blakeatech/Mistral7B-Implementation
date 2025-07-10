"""
Unit tests for the AuthenticationService class.
"""

import pytest
import hashlib
from unittest.mock import patch, Mock
from fastapi import HTTPException, status

from api.services.authentication_service import AuthenticationService


class TestAuthenticationService:
    """Test suite for AuthenticationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_auth_key = "test_auth_key"
        self.auth_service = AuthenticationService(self.test_auth_key)
        
    def test_init(self):
        """Test AuthenticationService initialization."""
        assert self.auth_service.auth_key == self.test_auth_key
        
    def test_hash_key(self):
        """Test key hashing functionality."""
        test_key = "test_key"
        expected_hash = hashlib.sha256(test_key.encode()).hexdigest()
        assert self.auth_service._hash_key(test_key) == expected_hash
        
    def test_hash_key_empty_string(self):
        """Test hashing empty string."""
        empty_key = ""
        expected_hash = hashlib.sha256(empty_key.encode()).hexdigest()
        assert self.auth_service._hash_key(empty_key) == expected_hash
        
    def test_hash_key_special_characters(self):
        """Test hashing key with special characters."""
        special_key = "!@#$%^&*()_+{}[]|:;<>?,./"
        expected_hash = hashlib.sha256(special_key.encode()).hexdigest()
        assert self.auth_service._hash_key(special_key) == expected_hash
        
    @patch('api.services.authentication_service.settings')
    def test_is_valid_correct_key(self, mock_settings):
        """Test is_valid returns True for correct key."""
        # Mock the settings.AUTH_KEY to match our hashed test key
        hashed_test_key = hashlib.sha256(self.test_auth_key.encode()).hexdigest()
        mock_settings.AUTH_KEY = hashed_test_key
        
        assert self.auth_service.is_valid() is True
        
    @patch('api.services.authentication_service.settings')
    def test_is_valid_incorrect_key(self, mock_settings):
        """Test is_valid returns False for incorrect key."""
        # Mock the settings.AUTH_KEY to be different from our hashed test key
        mock_settings.AUTH_KEY = "different_hash"
        
        assert self.auth_service.is_valid() is False
        
    @patch('api.services.authentication_service.settings')
    def test_raise_exception_if_invalid_valid_key(self, mock_settings):
        """Test raise_exception_if_invalid returns True for valid key."""
        # Mock the settings.AUTH_KEY to match our hashed test key
        hashed_test_key = hashlib.sha256(self.test_auth_key.encode()).hexdigest()
        mock_settings.AUTH_KEY = hashed_test_key
        
        assert self.auth_service.raise_exception_if_invalid() is True
        
    @patch('api.services.authentication_service.settings')
    def test_raise_exception_if_invalid_invalid_key(self, mock_settings):
        """Test raise_exception_if_invalid raises HTTPException for invalid key."""
        # Mock the settings.AUTH_KEY to be different from our hashed test key
        mock_settings.AUTH_KEY = "different_hash"
        
        with pytest.raises(HTTPException) as exc_info:
            self.auth_service.raise_exception_if_invalid()
            
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid authentication key"
        
    def test_different_keys_produce_different_hashes(self):
        """Test that different keys produce different hashes."""
        key1 = "key1"
        key2 = "key2"
        
        hash1 = self.auth_service._hash_key(key1)
        hash2 = self.auth_service._hash_key(key2)
        
        assert hash1 != hash2
        
    def test_same_key_produces_same_hash(self):
        """Test that the same key always produces the same hash."""
        key = "consistent_key"
        
        hash1 = self.auth_service._hash_key(key)
        hash2 = self.auth_service._hash_key(key)
        
        assert hash1 == hash2


@pytest.mark.parametrize("test_key,expected_valid", [
    ("correct_key", True),
    ("wrong_key", False),
    ("", False),
    ("123456", False),
    ("very_long_key_that_should_not_work", False),
])
@patch('api.services.authentication_service.settings')
def test_is_valid_parametrized(mock_settings, test_key, expected_valid):
    """Parametrized test for is_valid method."""
    # Set up the correct key hash
    correct_key = "correct_key"
    mock_settings.AUTH_KEY = hashlib.sha256(correct_key.encode()).hexdigest()
    
    auth_service = AuthenticationService(test_key)
    assert auth_service.is_valid() == expected_valid 