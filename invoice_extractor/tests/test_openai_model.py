#!/usr/bin/env python3
"""
Simple test for OpenAI GPT-4.1 model
"""

import requests
import json
import time
import os

# Configuration
OPENAI_MODEL_VERSION = "openai|gpt-4.1-mini"

# Test the OpenAI model
def test_openai_model():
    url = "http://127.0.0.1:9090/predict"
    
    # Check if OpenAI API key is set
    # if not os.environ.get('OPENAI_API_KEY'):
    #     print("❌ OPENAI_API_KEY environment variable is not set!")
    #     print("   Please set it before testing OpenAI models:")
    #     print("   export OPENAI_API_KEY='your-api-key-here'")
    #     return False
    
    payload = {
        "tasks": [{
            "id": 1357,
            "data": {
                "filename": "1078848715.pdf",
    "pdf": "<embed src='/data/local-files/?d=海外发票_2025-05-22.17_06_401/1078848715.pdf' width='100%' height='811px'/>",
                "invoices_json": ""
            }
        }],
        "label_config": "<View style=\"display: flex;\"><!-- 左侧：文档渲染区 --><View style=\"flex: 75%;\"><!-- 用内嵌 HTML 渲染 PDF / 图片，也可换成 <Image> / <PDF> --><HyperText name=\"pdf\" value=\"$pdf\" inline=\"true\" height=\"900px\"/></View><!-- 右侧：字段校对区 --><View style=\"flex: 30%;padding-left: 1em; border-left: 1px solid #ddd;\"><Text name=\"filename_display\" value=\"$filename\" /><TextArea name=\"invoices_json\" value=\"$invoices_json\" toName=\"pdf\" editable=\"true\" rows=\"39\"/><Text name=\"comment_display\" value=\"备注\"/><TextArea name=\"comment\" toName=\"pdf\" rows=\"1\" displayMode=\"tag\" showSubmitButton=\"false\"/></View></View>",
        "params": {
            "model_version": OPENAI_MODEL_VERSION
        }
    }
    
    print("🚀 Testing OpenAI model...")
    print(f"📦 Using model_version: {OPENAI_MODEL_VERSION}")
    print("🔑 Using API key: " + ("*" * (len(os.environ.get('OPENAI_API_KEY', '')) - 8)) + os.environ.get('OPENAI_API_KEY', '')[-8:])
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=180)  # 3 minute timeout for OpenAI
        end_time = time.time()
        
        print(f"📡 Status: {response.status_code}")
        print(f"⏱️ Time: {end_time - start_time:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', {})
            
            predictions = results.get('predictions', [])
            errors = results.get('errors', [])
            model_version = results.get('model_version', 'unknown')
            
            print(f"✅ Success!")
            print(f"   Model version: {model_version}")
            print(f"   Predictions: {len(predictions)}")
            print(f"   Errors: {len(errors)}")
            
            if predictions:
                pred = predictions[0]
                print(f"   Task ID: {pred.get('task')}")
                print(f"   Score: {pred.get('score')}")
                
                # Show extracted text sample
                result = pred.get('result', [])
                if result:
                    text = result[0].get('value', {}).get('text', [''])[0]
                    if text:
                        print(f"   Extracted (first 300 chars): {text[:300]}...")
            
            if errors:
                print(f"❌ Errors:")
                for error in errors:
                    print(f"   - {error.get('error_type')}: {error.get('error_message')}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: OpenAI request took longer than 3 minutes")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_versions_with_openai():
    """Test the /versions endpoint to see if OpenAI models are listed"""
    url = "http://127.0.0.1:9090/versions"
    
    print("🔍 Checking if OpenAI models are available in /versions...")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            versions = data.get('versions', [])
            
            openai_versions = [v for v in versions if v.get('processor_type') == 'openai']
            
            print(f"📋 Found {len(openai_versions)} OpenAI models:")
            for version in openai_versions:
                print(f"   - {version['version_string']}: {version['description']}")
            
            return len(openai_versions) > 0
        else:
            print(f"❌ Failed to get versions: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting versions: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print(f"🧪 OpenAI {OPENAI_MODEL_VERSION} Model Test")
    print("=" * 60)
    
    # First check if OpenAI models are available
    print(f"\n1. Checking OpenAI {OPENAI_MODEL_VERSION} model availability...")
    if not test_versions_with_openai():
        print("❌ OpenAI models are not available. This could be because:")
        print("   - OpenAI package is not installed: pip install openai")
        print("   - Import error in the OpenAI processor")
        exit(1)
    
    # Then test the actual prediction
    print("\n2. Testing OpenAI prediction...")
    success = test_openai_model()
    
    print("\n" + "=" * 60)
    if success:
        print(f"🎉 OpenAI {OPENAI_MODEL_VERSION} test completed successfully!")
        print("💡 Tip: Compare the results with Gemini models to see the differences")
    else:
        print("❌ OpenAI test failed!")
        print("💡 Common issues:")
        print("   - Missing OPENAI_API_KEY environment variable")
        print("   - Invalid API key")
        print("   - Network connectivity issues")
        print("   - OpenAI API rate limits or quota exceeded")
        exit(1)