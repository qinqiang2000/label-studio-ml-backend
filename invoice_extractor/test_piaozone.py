#!/usr/bin/env python3
"""
Test script for PiaoZone processor
"""

import os
import sys
import json
import tempfile
import logging

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Test only the PiaoZone processor directly to avoid dependency issues
try:
    from processors.piaozone import PiaoZoneProcessor
    PIAOZONE_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import PiaoZone processor: {e}")
    PIAOZONE_AVAILABLE = False

try:
    from processors.factory import DocumentProcessorFactory
    FACTORY_AVAILABLE = True
except ImportError as e:
    print(f"Factory not available (dependency issues): {e}")
    FACTORY_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_piaozone_processor():
    """Test PiaoZone processor basic functionality"""
    
    print("=== Testing PiaoZone Processor ===")
    
    if not PIAOZONE_AVAILABLE:
        print("✗ PiaoZone processor not available, skipping tests")
        return False
    
    # 1. Test factory creation (if available)
    if FACTORY_AVAILABLE:
        try:
            print("\n1. Testing factory creation...")
            processor = DocumentProcessorFactory.create_processor('piaozone')
            print(f"✓ Successfully created PiaoZone processor: {processor}")
            print(f"  Model version: {processor.get_model_version()}")
            
        except Exception as e:
            print(f"✗ Failed to create processor: {e}")
            return False
    else:
        print("\n1. Factory not available, skipping factory test...")
    
    # 2. Test direct instantiation
    try:
        print("\n2. Testing direct instantiation...")
        direct_processor = PiaoZoneProcessor()
        print(f"✓ Successfully created PiaoZone processor directly: {direct_processor}")
        print(f"  Model version: {direct_processor.get_model_version()}")
        
    except Exception as e:
        print(f"✗ Failed to create processor directly: {e}")
        return False
    
    # 3. Test with custom model name
    try:
        print("\n3. Testing with custom model name...")
        custom_processor = PiaoZoneProcessor(model_name="gemini-2.5-flash-preview-04-17")
        print(f"✓ Successfully created processor with custom model: {custom_processor}")
        print(f"  Model version: {custom_processor.get_model_version()}")
        
    except Exception as e:
        print(f"✗ Failed to create processor with custom model: {e}")
        return False
    
    # 4. Test configuration building
    try:
        print("\n4. Testing configuration building...")
        config = processor._build_param_config({'temperature': 0.5})
        print(f"✓ Successfully built config: {config}")
        
    except Exception as e:
        print(f"✗ Failed to build config: {e}")
        return False
    
    # 5. Test schema normalization
    try:
        print("\n5. Testing schema normalization...")
        test_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "amount": {"type": "number"}
            }
        }
        normalized = processor._normalize_schema(test_schema)
        print(f"✓ Successfully normalized schema: {normalized}")
        
    except Exception as e:
        print(f"✗ Failed to normalize schema: {e}")
        return False
    
    # 6. Test available processors (if factory available)
    if FACTORY_AVAILABLE:
        try:
            print("\n6. Testing available processors...")
            available = DocumentProcessorFactory.get_available_processors()
            print(f"✓ Available processors: {available}")
            
            if 'piaozone' in available:
                print("✓ PiaoZone processor is available")
            else:
                print("✗ PiaoZone processor is NOT available")
                return False
            
        except Exception as e:
            print(f"✗ Failed to get available processors: {e}")
            return False
    else:
        print("\n6. Factory not available, skipping available processors test...")
    
    # 7. Test MIME type detection
    try:
        print("\n7. Testing MIME type detection...")
        test_cases = [
            ("test.pdf", "application/pdf"),
            ("test.png", "image/png"),
            ("test.jpg", "image/jpeg"),
            ("test.jpeg", "image/jpeg"),
            ("test.txt", "application/octet-stream"),
        ]
        
        for filename, expected_mime in test_cases:
            actual_mime = processor._get_mime_type(filename)
            if actual_mime == expected_mime:
                print(f"✓ {filename} -> {actual_mime}")
            else:
                print(f"✗ {filename} -> Expected: {expected_mime}, Got: {actual_mime}")
                return False
        
    except Exception as e:
        print(f"✗ Failed to test MIME type detection: {e}")
        return False
    
    print("\n=== All tests passed! ===")
    return True

def test_environment_variables():
    """Test environment variable configuration"""
    
    print("\n=== Testing Environment Variables ===")
    
    # Test with environment variables
    os.environ['PIAOZONE_TEMPERATURE'] = '0.3'
    os.environ['PIAOZONE_MAX_OUTPUT_TOKENS'] = '1000'
    os.environ['PIAOZONE_RESPONSE_MIME_TYPE'] = 'text/plain'
    
    try:
        processor = PiaoZoneProcessor()
        config = processor._build_param_config({})
        
        print(f"Config with env vars: {config}")
        
        # Check if environment variables are applied
        if config.get('temperature') == 0.3:
            print("✓ Temperature from env var applied")
        else:
            print("✗ Temperature from env var NOT applied")
            return False
            
        if config.get('max_output_tokens') == 1000:
            print("✓ Max output tokens from env var applied")
        else:
            print("✗ Max output tokens from env var NOT applied")
            return False
            
        if config.get('response_mime_type') == 'text/plain':
            print("✓ Response MIME type from env var applied")
        else:
            print("✗ Response MIME type from env var NOT applied")
            return False
        
    except Exception as e:
        print(f"✗ Failed to test environment variables: {e}")
        return False
    finally:
        # Clean up environment variables
        for key in ['PIAOZONE_TEMPERATURE', 'PIAOZONE_MAX_OUTPUT_TOKENS', 'PIAOZONE_RESPONSE_MIME_TYPE']:
            if key in os.environ:
                del os.environ[key]
    
    print("✓ Environment variable tests passed")
    return True

def main():
    """Run all tests"""
    print("Starting PiaoZone processor tests...\n")
    
    success = True
    
    # Run basic functionality tests
    if not test_piaozone_processor():
        success = False
    
    # Run environment variable tests
    if not test_environment_variables():
        success = False
    
    if success:
        print("\n🎉 All tests passed successfully!")
        print("\nNext steps:")
        print("1. Set environment variables:")
        print("   export PIAOZONE_ACCESS_TOKEN='550a597856d536f440ced4638827602b'")
        print("   export PIAOZONE_API_URL='https://api-sit.piaozone.com/ai/knowledge/v1/chat/completions'")
        print("2. Test with a real document:")
        print("   processor = PiaoZoneProcessor()")
        print("   result = processor.process_document('path/to/document.pdf', 'Extract invoice data')")
        print("3. Use in main model with model_version='piaozone|gemini-2.5-flash-preview-04-17'")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())