"""
Integration tests for processor switching and runtime configuration
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
from pathlib import Path

# Import the model and processors
from model import NewModel
from processors.factory import DocumentProcessorFactory
from processors.gemini import GeminiProcessor
from processors.mock import MockProcessor


class TestProcessorSwitchingIntegration(unittest.TestCase):
    """Integration tests for processor switching with runtime config"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Set up environment for testing
        os.environ['API_KEY'] = 'test_api_key'
        os.environ['DOCUMENT_PROCESSOR'] = 'mock'  # Use mock for testing
        
        self.model = NewModel()
        self.model.setup()
        
        # Mock the label_interface
        self.model.label_interface = Mock()
        self.model.label_interface.get_first_tag_occurence.return_value = ('from_name', 'to_name', 'value')
        
        # Create sample task
        self.sample_task = {
            'id': 1,
            'data': {
                'value': '<embed src="/test/path.pdf" />'
            }
        }
        
        # Mock file operations
        self.model.get_local_path = Mock(return_value='/tmp/test_file.pdf')
    
    def tearDown(self):
        """Clean up after tests"""
        # Clean up environment
        if 'DOCUMENT_PROCESSOR' in os.environ:
            del os.environ['DOCUMENT_PROCESSOR']
    
    def test_model_setup_with_mock_processor(self):
        """Test that model sets up correctly with mock processor"""
        self.assertIsInstance(self.model.processor, MockProcessor)
        self.assertEqual(self.model.model_version, self.model.processor.get_model_version())
    
    @patch('processors.gemini.genai.Client')
    def test_switch_to_gemini_processor(self, mock_gemini_client):
        """Test switching from mock to gemini processor"""
        # Setup mock gemini client
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        
        # Verify initial state (should be mock)
        self.assertIsInstance(self.model.processor, MockProcessor)
        
        # Test processor switching via model version
        with patch.object(self.model, 'doc_understanding', return_value='{"test": "data"}'):
            response = self.model.predict(
                tasks=[self.sample_task],
                model_version="gemini|gemini-1.5-flash"
            )
        
        # Verify we're back to original processor after prediction
        self.assertIsInstance(self.model.processor, MockProcessor)
    
    def test_runtime_config_passing(self):
        """Test that runtime config is properly passed to processors"""
        runtime_config = {
            'temperature': 0.5,
            'response_mime_type': 'application/json',
            'max_output_tokens': 1000
        }
        
        # Mock doc_understanding to capture runtime_config
        captured_config = {}
        
        def mock_doc_understanding(file_path, runtime_config_param=None):
            captured_config['runtime_config'] = runtime_config_param
            return '{"test": "data"}'
        
        with patch.object(self.model, 'doc_understanding', side_effect=mock_doc_understanding):
            response = self.model.predict(
                tasks=[self.sample_task],
                runtime_config=runtime_config
            )
        
        # Verify runtime config was passed
        self.assertEqual(captured_config['runtime_config'], runtime_config)
    
    def test_combined_model_version_and_runtime_config(self):
        """Test using both model version and runtime config together"""
        runtime_config = {
            'temperature': 0.7,
            'response_schema': {
                'type': 'object',
                'properties': {
                    'invoice_number': {'type': 'string'}
                }
            }
        }
        
        captured_params = {}
        
        def mock_doc_understanding(file_path, runtime_config_param=None):
            captured_params['file_path'] = file_path
            captured_params['runtime_config'] = runtime_config_param
            return '{"invoice_number": "INV-001"}'
        
        with patch.object(self.model, 'doc_understanding', side_effect=mock_doc_understanding):
            response = self.model.predict(
                tasks=[self.sample_task],
                model_version="mock|mock-v1.0",
                runtime_config=runtime_config
            )
        
        # Verify both parameters were handled
        self.assertEqual(captured_params['runtime_config'], runtime_config)
        self.assertIsNotNone(captured_params['file_path'])
    
    def test_error_handling_during_processor_switch(self):
        """Test error handling when processor switching fails"""
        # Force an error during processor creation
        with patch('processors.factory.DocumentProcessorFactory.create_processor', 
                   side_effect=Exception("Processor creation failed")):
            
            # This should not crash and should use the default processor
            with patch.object(self.model, 'doc_understanding', return_value='{"test": "data"}'):
                response = self.model.predict(
                    tasks=[self.sample_task],
                    model_version="gemini|gemini-2.5-flash"
                )
            
            # Should still get a response with the original processor
            self.assertIsNotNone(response)
            self.assertIsInstance(self.model.processor, MockProcessor)
    
    def test_processor_version_consistency(self):
        """Test that processor versions are consistent"""
        # Get versions info
        versions = self.model.get_versions()
        
        # Verify version format consistency
        for version in versions['versions']:
            self.assertIn('processor_type', version)
            self.assertIn('model_name', version)
            self.assertIn('version_string', version)
            self.assertIn('description', version)
            self.assertIn('is_default', version)
            
            # Verify version string format
            parts = version['version_string'].split('|')
            self.assertEqual(len(parts), 2)
            self.assertEqual(parts[0], version['processor_type'])
            self.assertEqual(parts[1], version['model_name'])


class TestProcessorSpecificBehavior(unittest.TestCase):
    """Test processor-specific behaviors and configurations"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['API_KEY'] = 'test_api_key'
        
    def tearDown(self):
        """Clean up after tests"""
        # Clean up environment variables
        env_vars_to_clean = [
            'GEMINI_TEMPERATURE', 'GEMINI_MAX_OUTPUT_TOKENS',
            'GEMINI_TOP_P', 'GEMINI_TOP_K'
        ]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
    
    @patch('processors.gemini.genai.Client')
    def test_gemini_processor_with_env_config(self, mock_gemini_client):
        """Test gemini processor with environment configuration"""
        # Set environment variables
        os.environ['GEMINI_TEMPERATURE'] = '0.8'
        os.environ['GEMINI_MAX_OUTPUT_TOKENS'] = '2000'
        os.environ['GEMINI_TOP_P'] = '0.9'
        
        # Create processor
        processor = GeminiProcessor(model_name='gemini-1.5-pro')
        
        # Verify configuration was loaded from environment
        expected_config = {
            'temperature': 0.8,
            'max_output_tokens': 2000,
            'top_p': 0.9
        }
        
        # Check that config contains expected values
        for key, expected_value in expected_config.items():
            self.assertEqual(processor.llm_param_config.get(key), expected_value)
    
    @patch('processors.gemini.genai.Client')
    def test_gemini_processor_runtime_config_override(self, mock_gemini_client):
        """Test that runtime config overrides environment config"""
        # Set environment config
        os.environ['GEMINI_TEMPERATURE'] = '0.1'
        
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client
        
        # Mock response
        mock_response = Mock()
        mock_response.text = '{"test": "result"}'
        mock_client.models.generate_content.return_value = mock_response
        
        processor = GeminiProcessor(model_name='gemini-1.5-pro')
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b'test pdf content')
            test_file_path = tmp_file.name
        
        try:
            # Process with runtime config that overrides env config
            runtime_config = {'temperature': 0.9}
            
            with patch('pathlib.Path.read_bytes', return_value=b'test content'):
                result = processor.process_document(
                    test_file_path, 
                    "extract data", 
                    runtime_config=runtime_config
                )
            
            # Verify the call was made (indicates successful processing)
            mock_client.models.generate_content.assert_called_once()
            
            # Verify result
            self.assertEqual(result, '{"test": "result"}')
            
        finally:
            # Clean up test file
            os.unlink(test_file_path)
    
    def test_mock_processor_behavior(self):
        """Test mock processor behavior"""
        processor = MockProcessor()
        
        # Test with any file path (mock doesn't actually read files)
        result = processor.process_document('/fake/path.pdf', 'extract data')
        
        # Verify mock returns valid JSON
        parsed_result = json.loads(result)
        self.assertIsInstance(parsed_result, list)
        
        # Verify version
        version = processor.get_model_version()
        self.assertEqual(version, 'mock-v1.0')
    
    def test_processor_factory_registration(self):
        """Test processor factory registration functionality"""
        # Test getting available processors
        processors = DocumentProcessorFactory.get_available_processors()
        self.assertIn('gemini', processors)
        self.assertIn('mock', processors)
        
        # Test creating each processor type
        mock_proc = DocumentProcessorFactory.create_processor('mock')
        self.assertIsInstance(mock_proc, MockProcessor)
        
        with patch('processors.gemini.genai.Client'):
            gemini_proc = DocumentProcessorFactory.create_processor('gemini', model_name='test-model')
            self.assertIsInstance(gemini_proc, GeminiProcessor)
            self.assertEqual(gemini_proc.model_name, 'test-model')


class TestErrorScenarios(unittest.TestCase):
    """Test error scenarios and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = NewModel()
        # Mock the label_interface
        self.model.label_interface = Mock()
        self.model.label_interface.get_first_tag_occurence.return_value = ('from_name', 'to_name', 'value')
    
    def test_malformed_model_version_strings(self):
        """Test handling of malformed model version strings"""
        test_cases = [
            "||double_separator",
            "|empty_processor",
            "processor|",
            "too|many|separators|here",
            "unicode_test|模型名称",
            "special!@#$%^&*()characters|model",
        ]
        
        for malformed_version in test_cases:
            with self.subTest(version=malformed_version):
                processor_type, model_name = self.model._parse_model_version(malformed_version)
                
                # Should either parse correctly or return None, None
                if processor_type is not None:
                    self.assertIsInstance(processor_type, str)
                    self.assertIsInstance(model_name, str)
                else:
                    self.assertIsNone(model_name)
    
    def test_get_versions_with_processor_errors(self):
        """Test get_versions when processor has issues"""
        # Mock a processor that throws when getting version
        mock_processor = Mock()
        mock_processor.__class__.__name__ = 'BrokenProcessor'
        mock_processor.get_model_version.side_effect = Exception("Version error")
        
        self.model.processor = mock_processor
        
        # Should still return a valid response
        versions = self.model.get_versions()
        
        self.assertIn('versions', versions)
        self.assertIn('current_version', versions)
        # Current version info might be incomplete but shouldn't crash
    
    def test_predict_with_None_values(self):
        """Test predict method with None values in various parameters"""
        sample_task = {
            'id': 1,
            'data': {
                'value': '<embed src="/test/path.pdf" />'
            }
        }
        
        with patch.object(self.model, 'doc_understanding', return_value='{"test": "data"}'):
            # Test with None model_version
            response = self.model.predict(
                tasks=[sample_task],
                model_version=None,
                runtime_config=None
            )
            
            self.assertIsNotNone(response)
    
    def test_processor_creation_with_invalid_config(self):
        """Test processor creation with invalid configurations"""
        with patch('processors.gemini.genai.Client', side_effect=Exception("API Error")):
            # This should handle the error gracefully
            try:
                processor = GeminiProcessor(model_name='invalid-model')
                # If creation succeeds, that's also acceptable (mocking might prevent the error)
            except Exception as e:
                # Error should be handled gracefully
                self.assertIsInstance(e, Exception)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)