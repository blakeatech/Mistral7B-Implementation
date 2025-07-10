"""
Integration tests for the API endpoints.
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from fastapi import status

from main import app


class TestEndpoints:
    """Test suite for API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.test_auth_key = "test_auth_key"
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_inference_success(self, mock_auth_service, mock_inference_service):
        """Test successful inference endpoint."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text.return_value = "Generated response"
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request
        response = self.client.get(
            "/api/v1/inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key,
                "max_length": 256,
                "temperature": 0.5
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"generated_text": "Generated response"}
        mock_inference_service.assert_called_once_with(self.test_auth_key)
        mock_auth_service.assert_called_once_with(self.test_auth_key)
        mock_inference_instance.generate_text.assert_called_once_with(
            "test context", max_length=256, temperature=0.5
        )
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_inference_default_params(self, mock_auth_service, mock_inference_service):
        """Test inference endpoint with default parameters."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text.return_value = "Generated response"
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request without optional parameters
        response = self.client.get(
            "/api/v1/inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        mock_inference_instance.generate_text.assert_called_once_with(
            "test context", max_length=512, temperature=0.3
        )
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_inference_authentication_failure(self, mock_auth_service, mock_inference_service):
        """Test inference endpoint with authentication failure."""
        # Setup mocks - authentication fails
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.side_effect = Exception("Authentication failed")
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request
        response = self.client.get(
            "/api/v1/inference",
            params={
                "input_context": "test context",
                "auth_key": "invalid_key"
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Text generation failed" in response.json()["detail"]
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_inference_generation_failure(self, mock_auth_service, mock_inference_service):
        """Test inference endpoint when text generation fails."""
        # Setup mocks - authentication succeeds but generation fails
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text.side_effect = Exception("Generation failed")
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request
        response = self.client.get(
            "/api/v1/inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Text generation failed" in response.json()["detail"]
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_batch_inference_success(self, mock_auth_service, mock_inference_service):
        """Test successful batch inference endpoint."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text_with_batch_size.return_value = ["Response 1", "Response 2"]
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request
        response = self.client.post(
            "/api/v1/batch_inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key,
                "num_batches": 2,
                "max_length": 256,
                "temperature": 0.7
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"generated_texts": ["Response 1", "Response 2"]}
        mock_inference_instance.generate_text_with_batch_size.assert_called_once_with(
            ["test context", "test context"], batch_size=2, max_length=256, temperature=0.7
        )
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_batch_inference_default_params(self, mock_auth_service, mock_inference_service):
        """Test batch inference endpoint with default parameters."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text_with_batch_size.return_value = ["Response 1"]
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request with minimal parameters
        response = self.client.post(
            "/api/v1/batch_inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        mock_inference_instance.generate_text_with_batch_size.assert_called_once_with(
            ["test context"], batch_size=1, max_length=128, temperature=0.7
        )
        
    @patch('api.v1.endpoints.InferenceService')
    @patch('api.v1.endpoints.AuthenticationService')
    def test_batch_inference_failure(self, mock_auth_service, mock_inference_service):
        """Test batch inference endpoint when generation fails."""
        # Setup mocks - authentication succeeds but generation fails
        mock_auth_instance = Mock()
        mock_auth_instance.raise_exception_if_invalid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        mock_inference_instance = Mock()
        mock_inference_instance.generate_text_with_batch_size.side_effect = Exception("Batch generation failed")
        mock_inference_service.return_value = mock_inference_instance
        
        # Make request
        response = self.client.post(
            "/api/v1/batch_inference",
            params={
                "input_context": "test context",
                "auth_key": self.test_auth_key
            }
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Batch text generation failed" in response.json()["detail"]
        
    @patch('api.v1.endpoints.AuthenticationService')
    def test_login_success(self, mock_auth_service):
        """Test successful login endpoint."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.is_valid.return_value = True
        mock_auth_service.return_value = mock_auth_instance
        
        # Make request
        response = self.client.get(
            "/api/v1/login",
            json={"auth_key": self.test_auth_key}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"authenticated": True}
        mock_auth_service.assert_called_once_with(self.test_auth_key)
        
    @patch('api.v1.endpoints.AuthenticationService')
    def test_login_failure(self, mock_auth_service):
        """Test login endpoint with invalid credentials."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth_instance.is_valid.return_value = False
        mock_auth_service.return_value = mock_auth_instance
        
        # Make request
        response = self.client.get(
            "/api/v1/login",
            json={"auth_key": "invalid_key"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"authenticated": False}
        
    @patch('api.v1.endpoints.AuthenticationService')
    def test_login_exception(self, mock_auth_service):
        """Test login endpoint when service raises exception."""
        # Setup mocks
        mock_auth_service.side_effect = Exception("Service error")
        
        # Make request
        response = self.client.get(
            "/api/v1/login",
            json={"auth_key": self.test_auth_key}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Login failed" in response.json()["detail"]
        
    def test_inference_missing_parameters(self):
        """Test inference endpoint with missing required parameters."""
        # Make request without required parameters
        response = self.client.get("/api/v1/inference")
        
        # Should return 422 for missing required parameters
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
    def test_batch_inference_missing_parameters(self):
        """Test batch inference endpoint with missing required parameters."""
        # Make request without required parameters
        response = self.client.post("/api/v1/batch_inference")
        
        # Should return 422 for missing required parameters
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
    def test_login_missing_parameters(self):
        """Test login endpoint with missing required parameters."""
        # Make request without required parameters
        response = self.client.get("/api/v1/login")
        
        # Should return 422 for missing required parameters
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("endpoint,method,params", [
    ("/api/v1/inference", "GET", {"input_context": "test", "auth_key": "key"}),
    ("/api/v1/batch_inference", "POST", {"input_context": "test", "auth_key": "key"}),
])
@patch('api.v1.endpoints.InferenceService')
@patch('api.v1.endpoints.AuthenticationService')
def test_endpoints_with_parametrize(mock_auth_service, mock_inference_service, endpoint, method, params):
    """Parametrized test for endpoints."""
    client = TestClient(app)
    
    # Setup mocks
    mock_auth_instance = Mock()
    mock_auth_instance.raise_exception_if_invalid.return_value = True
    mock_auth_service.return_value = mock_auth_instance
    
    mock_inference_instance = Mock()
    mock_inference_instance.generate_text.return_value = "Generated response"
    mock_inference_instance.generate_text_with_batch_size.return_value = ["Generated response"]
    mock_inference_service.return_value = mock_inference_instance
    
    # Make request
    if method == "GET":
        response = client.get(endpoint, params=params)
    else:
        response = client.post(endpoint, params=params)
    
    # Should not return 404 or 405
    assert response.status_code not in [404, 405] 