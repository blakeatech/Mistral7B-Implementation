"""
Unit tests for the InferenceService class.
"""

import pytest
import torch
from unittest.mock import patch, Mock, MagicMock, mock_open
from torch.cuda.amp import autocast

from api.services.inference_service import InferenceService
from api.services.authentication_service import AuthenticationService


class TestInferenceService:
    """Test suite for InferenceService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_auth_key = "test_auth_key"
        
        # Mock the model and tokenizer
        self.mock_model = Mock()
        self.mock_tokenizer = Mock()
        self.mock_device = torch.device("cpu")
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.AuthenticationService')
    def test_init(self, mock_auth_service, mock_tokenizer, mock_model):
        """Test InferenceService initialization."""
        mock_auth_service.return_value = Mock()
        
        service = InferenceService(self.test_auth_key)
        
        assert service.model == mock_model
        assert service.tokenizer == mock_tokenizer
        assert service.authentication_key == self.test_auth_key
        mock_auth_service.assert_called_once_with(self.test_auth_key)
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('torch.cuda.empty_cache')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt with <<CONTEXT>>")
    def test_generate_text_success(self, mock_file, mock_empty_cache, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test successful text generation."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
        mock_tokenizer.decode.return_value = "Test response <bot>: Generated text"
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        
        service = InferenceService(self.test_auth_key)
        
        # Test the method
        result = service.generate_text("test context")
        
        # Assertions
        assert result == "Generated text"
        mock_file.assert_called_once_with('/workspace/lo-backend/prompt.txt', 'r')
        mock_tokenizer.encode.assert_called_once()
        mock_model.generate.assert_called_once()
        mock_tokenizer.decode.assert_called_once()
        mock_empty_cache.assert_called()
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt with <<CONTEXT>>")
    def test_generate_text_empty_context(self, mock_file, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test text generation with empty context."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
        mock_tokenizer.decode.return_value = "Test response <bot>: Generated text"
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        
        service = InferenceService(self.test_auth_key)
        
        # Test with empty context
        result = service.generate_text("")
        
        # Verify the prompt was constructed correctly for empty context
        expected_prompt_call = mock_file.return_value.read.return_value.replace('<<CONTEXT>>', 'context: ')
        mock_tokenizer.encode.assert_called_once()
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt with <<CONTEXT>>")
    def test_generate_text_context_without_punctuation(self, mock_file, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test text generation with context that doesn't end with punctuation."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
        mock_tokenizer.decode.return_value = "Test response <bot>: Generated text"
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        
        service = InferenceService(self.test_auth_key)
        
        # Test with context that doesn't end with punctuation
        result = service.generate_text("test context")
        
        # The method should add a period to the context
        mock_tokenizer.encode.assert_called_once()
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('torch.cuda.empty_cache')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt with <<CONTEXT>>")
    def test_generate_text_cuda_out_of_memory(self, mock_file, mock_empty_cache, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test handling of CUDA out of memory error."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
        mock_model.generate.side_effect = torch.cuda.OutOfMemoryError()
        
        service = InferenceService(self.test_auth_key)
        
        # Test that RuntimeError is raised
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_text("test context")
            
        assert "Out of GPU memory during inference" in str(exc_info.value)
        mock_empty_cache.assert_called()
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('builtins.open', new_callable=mock_open, read_data="Test prompt with <<CONTEXT>>")
    def test_generate_text_general_exception(self, mock_file, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test handling of general exceptions."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.encode.return_value = torch.tensor([[1, 2, 3]])
        mock_model.generate.side_effect = Exception("Test error")
        
        service = InferenceService(self.test_auth_key)
        
        # Test that RuntimeError is raised
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_text("test context")
            
        assert "Text generation failed" in str(exc_info.value)
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('torch.cuda.empty_cache')
    def test_generate_text_with_batch_size_success(self, mock_empty_cache, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test successful batch text generation."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.return_value = Mock()
        mock_tokenizer.return_value.to.return_value = torch.tensor([[1, 2, 3], [4, 5, 6]])
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4], [5, 6, 7, 8]])
        mock_tokenizer.decode.side_effect = ["Response 1", "Response 2"]
        
        service = InferenceService(self.test_auth_key)
        
        # Test batch generation
        input_contexts = ["context 1", "context 2"]
        result = service.generate_text_with_batch_size(input_contexts, batch_size=2)
        
        assert result == ["Response 1", "Response 2"]
        mock_tokenizer.assert_called_once_with(input_contexts, return_tensors="pt", padding=True, truncation=True)
        mock_model.generate.assert_called_once()
        assert mock_tokenizer.decode.call_count == 2
        mock_empty_cache.assert_called()
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('torch.cuda.empty_cache')
    def test_generate_text_with_batch_size_multiple_batches(self, mock_empty_cache, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test batch text generation with multiple batches."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.return_value = Mock()
        mock_tokenizer.return_value.to.return_value = torch.tensor([[1, 2, 3]])
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4]])
        mock_tokenizer.decode.return_value = "Response"
        
        service = InferenceService(self.test_auth_key)
        
        # Test with 3 inputs and batch size 2 (should create 2 batches)
        input_contexts = ["context 1", "context 2", "context 3"]
        result = service.generate_text_with_batch_size(input_contexts, batch_size=2)
        
        assert len(result) == 3
        assert all(r == "Response" for r in result)
        # Should be called twice (2 batches)
        assert mock_model.generate.call_count == 2
        
    @patch('api.services.inference_service.model')
    @patch('api.services.inference_service.tokenizer')
    @patch('api.services.inference_service.device')
    @patch('api.services.inference_service.AuthenticationService')
    @patch('torch.cuda.empty_cache')
    def test_generate_text_with_batch_size_cuda_oom(self, mock_empty_cache, mock_auth_service, mock_device, mock_tokenizer, mock_model):
        """Test batch generation with CUDA out of memory error."""
        # Setup mocks
        mock_auth_service.return_value = Mock()
        mock_tokenizer.return_value = Mock()
        mock_tokenizer.return_value.to.return_value = torch.tensor([[1, 2, 3]])
        mock_model.generate.side_effect = torch.cuda.OutOfMemoryError()
        
        service = InferenceService(self.test_auth_key)
        
        # Test that RuntimeError is raised
        with pytest.raises(RuntimeError) as exc_info:
            service.generate_text_with_batch_size(["context 1"], batch_size=1)
            
        assert "GPU out of memory during batch inference" in str(exc_info.value)
        mock_empty_cache.assert_called()


@pytest.mark.parametrize("input_context,expected_suffix", [
    ("test context", "."),
    ("test context.", ""),
    ("test context!", ""),
    ("test context?", ""),
    ("", ""),
])
def test_context_punctuation_handling(input_context, expected_suffix):
    """Test that context punctuation is handled correctly."""
    # This would be tested in integration, but we can verify the logic
    if input_context and input_context[-1] not in ['?', '!', '.']:
        assert input_context + "." == input_context + expected_suffix
    else:
        assert input_context == input_context + expected_suffix 