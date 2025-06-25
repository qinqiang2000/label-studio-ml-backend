"""
Runtime Config API Tests for Invoice Extractor

This file contains comprehensive tests for the runtime_config functionality.
Run with: pytest test_runtime_config.py -v
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from model import NewModel


class TestRuntimeConfig:
    """Test suite for runtime_config functionality"""
    
    @pytest.fixture
    def model_instance(self):
        """Create a NewModel instance for testing"""
        model = NewModel()
        model.setup()
        return model
    
    @pytest.fixture
    def sample_task(self):
        """Sample task data for testing"""
        return {
            "id": 661,
            'data': {
                "pdf": "<embed src='/data/local-files/?d=3/fc0fd018.pdf' width='100%' height='811px'/>",
                "filename": "test_invoice.pdf",
                "invoices_json": ""
            }
        }
    
    @pytest.fixture
    def sample_runtime_config(self):
        """Sample runtime configuration"""
        return {
            "temperature": 0.2,
            "response_mime_type": "application/json",
            "max_output_tokens": 2000,
            "seed": 12345,
            "response_schema": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "date": {"type": "string"},
                    "vendor": {"type": "string"}
                },
                "required": ["invoice_number", "total_amount", "date"]
            }
        }

    def test_predict_without_runtime_config(self, model_instance, sample_task):
        """Test predict method without runtime_config (backward compatibility)"""
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict without runtime_config
            result = model_instance.predict([sample_task])
            
            # Verify predict_single was called with None runtime_config
            mock_predict_single.assert_called_once_with(sample_task, None)
            assert result is not None

    def test_predict_with_runtime_config(self, model_instance, sample_task, sample_runtime_config):
        """Test predict method with runtime_config"""
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict with runtime_config
            result = model_instance.predict([sample_task], runtime_config=sample_runtime_config)
            
            # Verify predict_single was called with the runtime_config
            mock_predict_single.assert_called_once_with(sample_task, sample_runtime_config)
            assert result is not None

    def test_predict_with_prompt_and_runtime_config(self, model_instance, sample_task, sample_runtime_config):
        """Test predict method with both prompt and runtime_config"""
        custom_prompt = "Extract detailed invoice information"
        
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict with both prompt and runtime_config
            result = model_instance.predict(
                [sample_task], 
                prompt=custom_prompt,
                runtime_config=sample_runtime_config
            )
            
            # Verify both parameters were set
            assert model_instance.prompt == custom_prompt
            mock_predict_single.assert_called_once_with(sample_task, sample_runtime_config)

    def test_runtime_config_validation_invalid_type(self, model_instance, sample_task):
        """Test runtime_config validation with invalid type"""
        invalid_config = "not_a_dict"  # Should be dict
        
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict with invalid runtime_config type
            result = model_instance.predict([sample_task], runtime_config=invalid_config)
            
            # Should pass None to predict_single due to validation failure
            mock_predict_single.assert_called_once_with(sample_task, None)

    def test_runtime_config_unknown_parameters(self, model_instance, sample_task):
        """Test runtime_config with unknown parameters"""
        config_with_unknown = {
            "temperature": 0.5,
            "unknown_param": "should_be_ignored",
            "another_unknown": 123
        }
        
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict with unknown parameters
            result = model_instance.predict([sample_task], runtime_config=config_with_unknown)
            
            # Should still pass the config (unknown params will be handled by processor)
            mock_predict_single.assert_called_once_with(sample_task, config_with_unknown)

    @patch('model.NewModel.get_local_path')
    @patch('model.NewModel.doc_understanding')
    def test_predict_single_passes_runtime_config(self, mock_doc_understanding, mock_get_local_path, model_instance, sample_task, sample_runtime_config):
        """Test that predict_single passes runtime_config to doc_understanding"""
        mock_get_local_path.return_value = "/fake/path/invoice.pdf"
        mock_doc_understanding.return_value = '{"invoice_number": "INV-001", "total_amount": 100.0}'
        
        # Mock label interface
        model_instance.label_interface = Mock()
        model_instance.label_interface.get_first_tag_occurence.return_value = ("invoices_json", "pdf", "pdf")
        
        # Call predict_single with runtime_config
        result = model_instance.predict_single(sample_task, sample_runtime_config)
        
        # Verify doc_understanding was called with runtime_config
        mock_doc_understanding.assert_called_once_with("/fake/path/invoice.pdf", sample_runtime_config)
        assert result is not None

    @patch('inspect.signature')
    def test_doc_understanding_processor_compatibility_check(self, mock_signature, model_instance):
        """Test that doc_understanding checks processor compatibility"""
        # Mock processor that supports runtime_config
        mock_processor = Mock()
        mock_processor.process_document = Mock(return_value='{"test": "data"}')
        model_instance.processor = mock_processor
        
        # Mock signature to indicate runtime_config is supported
        mock_sig = Mock()
        mock_sig.parameters = {'file_path': None, 'instruction': None, 'runtime_config': None}
        mock_signature.return_value = mock_sig
        
        runtime_config = {"temperature": 0.5}
        
        # Call doc_understanding
        with patch.object(model_instance, 'prompt', 'test_prompt'):
            result = model_instance.doc_understanding("/fake/path", runtime_config)
        
        # Verify processor was called with runtime_config
        mock_processor.process_document.assert_called_once_with("/fake/path", 'test_prompt', runtime_config)

    @patch('inspect.signature')
    def test_doc_understanding_processor_no_runtime_config_support(self, mock_signature, model_instance):
        """Test doc_understanding with processor that doesn't support runtime_config"""
        # Mock processor that doesn't support runtime_config
        mock_processor = Mock()
        mock_processor.process_document = Mock(return_value='{"test": "data"}')
        model_instance.processor = mock_processor
        
        # Mock signature to indicate runtime_config is NOT supported
        mock_sig = Mock()
        mock_sig.parameters = {'file_path': None, 'instruction': None}  # No runtime_config
        mock_signature.return_value = mock_sig
        
        runtime_config = {"temperature": 0.5}
        
        # Call doc_understanding
        with patch.object(model_instance, 'prompt', 'test_prompt'):
            result = model_instance.doc_understanding("/fake/path", runtime_config)
        
        # Verify processor was called WITHOUT runtime_config
        mock_processor.process_document.assert_called_once_with("/fake/path", 'test_prompt')

    def test_error_handling_with_runtime_config(self, model_instance, sample_task, sample_runtime_config):
        """Test error handling when runtime_config causes issues"""
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            # Make predict_single raise an exception
            mock_predict_single.side_effect = Exception("Runtime config error")
            
            # Call predict with runtime_config
            result = model_instance.predict([sample_task], runtime_config=sample_runtime_config)
            
            # Should handle error gracefully and return ModelResponse with errors
            assert result is not None
            assert hasattr(result, 'has_errors')
            if result.has_errors():
                assert len(result.errors) > 0

    def test_multiple_tasks_with_runtime_config(self, model_instance, sample_task, sample_runtime_config):
        """Test processing multiple tasks with runtime_config"""
        tasks = [sample_task.copy() for _ in range(3)]
        tasks[0]["id"] = 1
        tasks[1]["id"] = 2
        tasks[2]["id"] = 3
        
        with patch.object(model_instance, 'predict_single') as mock_predict_single:
            mock_predict_single.return_value = Mock()
            
            # Call predict with multiple tasks
            result = model_instance.predict(tasks, runtime_config=sample_runtime_config)
            
            # Verify predict_single was called for each task with the same runtime_config
            assert mock_predict_single.call_count == 3
            for call in mock_predict_single.call_args_list:
                assert call[0][1] == sample_runtime_config  # Second argument should be runtime_config


class TestRuntimeConfigIntegration:
    """Integration tests for runtime_config with real components"""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client"""
        from _wsgi import init_app
        app = init_app(model_class=NewModel)
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_api_request_without_runtime_config(self, client):
        """Test API request without runtime_config (backward compatibility)"""
        request_data = {
            'tasks': [{
                "id": 661,
                'data': {
                    "pdf": "<embed src='/data/local-files/?d=3/fc0fd018.pdf' width='100%' height='811px'/>",
                    "filename": "test_invoice.pdf",
                    "invoices_json": ""
                }
            }],
            'label_config': """
                <View>
                    <HyperText name="pdf" value="$pdf"/>
                    <TextArea name="invoices_json" value="$invoices_json" toName="pdf"/>
                </View>
            """
        }
        
        with patch('model.NewModel.doc_understanding') as mock_doc:
            mock_doc.return_value = '{"test": "response"}'
            
            response = client.post('/predict', 
                                 data=json.dumps(request_data), 
                                 content_type='application/json')
            
            assert response.status_code == 200

    def test_api_request_with_runtime_config(self, client):
        """Test API request with runtime_config"""
        runtime_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json",
            "max_output_tokens": 1500
        }
        
        request_data = {
            'tasks': [{
                "id": 661,
                'data': {
                    "pdf": "<embed src='/data/local-files/?d=3/fc0fd018.pdf' width='100%' height='811px'/>",
                    "filename": "test_invoice.pdf", 
                    "invoices_json": ""
                }
            }],
            'runtime_config': runtime_config,
            'label_config': """
                <View>
                    <HyperText name="pdf" value="$pdf"/>
                    <TextArea name="invoices_json" value="$invoices_json" toName="pdf"/>
                </View>
            """
        }
        
        with patch('model.NewModel.doc_understanding') as mock_doc:
            mock_doc.return_value = '{"test": "response"}'
            
            response = client.post('/predict',
                                 data=json.dumps(request_data),
                                 content_type='application/json')
            
            assert response.status_code == 200

    def test_api_request_with_complex_runtime_config(self, client):
        """Test API request with complex runtime_config including schema"""
        runtime_config = {
            "temperature": 0.1,
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "invoices": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "invoice_number": {"type": "string"},
                                "total_amount": {"type": "number"},
                                "date": {"type": "string"}
                            },
                            "required": ["invoice_number", "total_amount"]
                        }
                    }
                },
                "required": ["invoices"]
            }
        }
        
        request_data = {
            'tasks': [{
                "id": 661,
                'data': {
                    "pdf": "<embed src='/data/local-files/?d=3/fc0fd018.pdf' width='100%' height='811px'/>",
                    "filename": "complex_invoice.pdf",
                    "invoices_json": ""
                }
            }],
            'runtime_config': runtime_config,
            'prompt': 'Extract all invoice information with strict schema compliance'
        }
        
        with patch('model.NewModel.doc_understanding') as mock_doc:
            mock_doc.return_value = '{"invoices": [{"invoice_number": "INV-001", "total_amount": 100.0, "date": "2024-01-01"}]}'
            
            response = client.post('/predict',
                                 data=json.dumps(request_data),
                                 content_type='application/json')
            
            assert response.status_code == 200
            
            # Verify the response structure
            response_data = json.loads(response.data)
            assert 'results' in response_data 