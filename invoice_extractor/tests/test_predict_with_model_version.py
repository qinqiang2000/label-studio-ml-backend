#!/usr/bin/env python3
"""
Test script for the /predict endpoint with different model versions
"""

import requests
import json
import sys
import time

# Default ML Backend URL
ML_BACKEND_URL = "http://127.0.0.1:9090"

def test_predict_with_model_version(model_version=None, prompt_name=None):
    """Test the /predict endpoint with specific model version"""
    url = f"{ML_BACKEND_URL}/predict"
    
    # Base request payload (from your original working request)
    payload = {
        "tasks": [{
            "id": 1362,
            "data": {
                "pdf": "<embed src=\"/data/local-files/?d=28/495d02f7.pdf\" width=\"100%\" height=\"811px\"/>",
                "filename": "1_3.pdf",
                "invoices_json": ""
            }
        }],
        "label_config": "<View style=\"display: flex;\"><!-- 左侧：文档渲染区 --><View style=\"flex: 75%;\"><!-- 用内嵌 HTML 渲染 PDF / 图片，也可换成 <Image> / <PDF> --><HyperText name=\"pdf\" value=\"$pdf\" inline=\"true\" height=\"900px\"/></View><!-- 右侧：字段校对区 --><View style=\"flex: 30%;padding-left: 1em; border-left: 1px solid #ddd;\"><Text name=\"filename_display\" value=\"$filename\" /><TextArea name=\"invoices_json\" value=\"$invoices_json\" toName=\"pdf\" editable=\"true\" rows=\"39\"/><Text name=\"comment_display\" value=\"备注\"/><TextArea name=\"comment\" toName=\"pdf\" rows=\"1\" displayMode=\"tag\" showSubmitButton=\"false\"/></View></View>",
        "params": {}
    }
    
    # Add model_version to params if specified
    if model_version:
        payload["params"]["model_version"] = model_version
        print(f"🔧 Using model version: {model_version}")
    else:
        print(f"🔧 Using default model version")
    
    # Add prompt_name to params if specified
    if prompt_name:
        payload["params"]["prompt_name"] = prompt_name
        print(f"📝 Using prompt name: {prompt_name}")
    
    print(f"🚀 Testing /predict endpoint: {url}")
    print(f"📦 Request payload keys: {list(payload.keys())}")
    print(f"📦 Params: {payload['params']}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=120)  # 2 minute timeout
        end_time = time.time()
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"⏱️ Response Time: {end_time - start_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Prediction completed")
            
            # Analyze the response structure
            results = data.get('results', {})
            if isinstance(results, dict):
                predictions = results.get('predictions', [])
                errors = results.get('errors', [])
                model_version_used = results.get('model_version', 'unknown')
                
                print(f"📊 Response Analysis:")
                print(f"   Predictions count: {len(predictions)}")
                print(f"   Errors count: {len(errors)}")
                print(f"   Model version used: {model_version_used}")
                
                # Show prediction details
                if predictions:
                    for i, pred in enumerate(predictions):
                        print(f"   Prediction {i+1}:")
                        print(f"     Task ID: {pred.get('task', 'unknown')}")
                        print(f"     Score: {pred.get('score', 'unknown')}")
                        print(f"     Model Version: {pred.get('model_version', 'unknown')}")
                        
                        # Show extracted result (first 200 chars)
                        result = pred.get('result', [])
                        if result and len(result) > 0:
                            text_content = result[0].get('value', {}).get('text', [''])[0]
                            if text_content:
                                print(f"     Extracted text (first 200 chars): {text_content[:200]}...")
                            else:
                                print(f"     Extracted text: [empty]")
                
                # Show errors if any
                if errors:
                    print(f"❌ Errors found:")
                    for i, error in enumerate(errors):
                        print(f"   Error {i+1}:")
                        print(f"     Task ID: {error.get('task_id', 'unknown')}")
                        print(f"     Error Type: {error.get('error_type', 'unknown')}")
                        print(f"     Error Message: {error.get('error_message', 'unknown')}")
                
                return True
            else:
                print(f"⚠️ Unexpected response format: {type(results)}")
                print(f"Raw response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return True
                
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not connect to {url}")
        print(f"   Make sure the ML Backend is running on {ML_BACKEND_URL}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: Request to {url} timed out (>120s)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 80)
    print("🧪 ML Backend /predict API Test with Model Version")
    print("=" * 80)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Default Model (no model_version specified)",
            "model_version": None,
            "prompt_name": None
        },
        {
            "name": "Gemini 2.5 Flash Lite (fastest and cheapest)",
            "model_version": "gemini|gemini-2.5-flash-lite-preview-06-17",
            "prompt_name": None
        },
        {
            "name": "Gemini 2.5 Flash Preview (tested)",
            "model_version": "gemini|gemini-2.5-flash-preview-04-17", 
            "prompt_name": None
        },
        {
            "name": "OpenAI GPT-4.1 (requires OPENAI_API_KEY)",
            "model_version": "openai|gpt-4.1",
            "prompt_name": None
        },
        {
            "name": "OpenAI GPT-4o (Vision + Text, requires OPENAI_API_KEY)",
            "model_version": "openai|gpt-4o",
            "prompt_name": None
        },
        {
            "name": "Mock Processor (for testing)",
            "model_version": "mock|mock-v1.0",
            "prompt_name": None
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        print("-" * 60)
        
        success = test_predict_with_model_version(
            model_version=scenario['model_version'],
            prompt_name=scenario['prompt_name']
        )
        
        results.append({
            'scenario': scenario['name'],
            'success': success
        })
        
        if i < len(test_scenarios):
            print(f"\n⏳ Waiting 3 seconds before next test...")
            time.sleep(3)
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 Test Results Summary:")
    print("=" * 80)
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['scenario']}")
    
    failed_count = sum(1 for r in results if not r['success'])
    if failed_count == 0:
        print(f"\n🎉 All {len(results)} tests passed!")
    else:
        print(f"\n⚠️ {failed_count}/{len(results)} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()