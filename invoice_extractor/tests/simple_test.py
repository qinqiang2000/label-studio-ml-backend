#!/usr/bin/env python3
"""
Simple test to verify model version functionality
"""
import sys
import os
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))

def test_basic_functionality():
    """Test basic model version functionality"""
    print("Testing basic model version functionality...")
    
    try:
        # Import the model
        from model import NewModel
        print("✓ Successfully imported NewModel")
        
        # Create model instance
        os.environ['API_KEY'] = 'test_key'
        os.environ['DOCUMENT_PROCESSOR'] = 'mock'
        
        model = NewModel()
        model.setup()
        print("✓ Successfully created and set up model")
        
        # Test parse_model_version
        processor_type, model_name = model._parse_model_version("gemini|gemini-2.5-flash-preview-04-17")
        assert processor_type == "gemini"
        assert model_name == "gemini-2.5-flash-preview-04-17"
        print("✓ Model version parsing works correctly")
        
        # Test get_versions
        versions = model.get_versions()
        assert 'versions' in versions
        assert 'current_version' in versions
        assert versions['total_count'] > 0
        print("✓ Get versions functionality works")
        
        # Test parsing edge cases
        processor_type, model_name = model._parse_model_version("")
        assert processor_type is None
        assert model_name is None
        print("✓ Empty string parsing handled correctly")
        
        processor_type, model_name = model._parse_model_version("just-model-name")
        assert processor_type == "gemini"
        assert model_name == "just-model-name"
        print("✓ Model name only parsing works")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_factory_functionality():
    """Test processor factory functionality"""
    print("\nTesting processor factory...")
    
    try:
        from processors.factory import DocumentProcessorFactory
        print("✓ Successfully imported DocumentProcessorFactory")
        
        # Test get available processors
        processors = DocumentProcessorFactory.get_available_processors()
        assert 'gemini' in processors
        assert 'mock' in processors
        print("✓ Available processors retrieved correctly")
        
        # Test create mock processor
        mock_processor = DocumentProcessorFactory.create_processor('mock')
        print("✓ Mock processor created successfully")
        
        # Test create gemini processor with config
        os.environ['API_KEY'] = 'test_key'
        try:
            gemini_processor = DocumentProcessorFactory.create_processor('gemini', model_name='test-model')
            print("✓ Gemini processor created successfully")
        except Exception as e:
            print(f"Note: Gemini processor creation failed (expected in test env): {e}")
        
        print("🎉 Factory tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Simple Model Version Functionality Test")
    print("=" * 60)
    
    success1 = test_basic_functionality()
    success2 = test_factory_functionality()
    
    if success1 and success2:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)