#!/usr/bin/env python3
"""
Simple test for gemini-2.5-flash-lite-preview-06-17 model
"""

import requests
import json
import time

# Test the lite model
def test_lite_model():
    url = "http://127.0.0.1:9090/predict"
    
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
        "params": {
            "model_version": "gemini|gemini-2.5-flash-lite-preview-06-17"
        }
    }
    
    print("🚀 Testing Gemini 2.5 Flash Lite model...")
    print("📦 Using model_version: gemini|gemini-2.5-flash-lite-preview-06-17")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=120)
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
                        print(f"   Extracted (first 200 chars): {text[:200]}...")
            
            if errors:
                print(f"❌ Errors:")
                for error in errors:
                    print(f"   - {error.get('error_type')}: {error.get('error_message')}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Quick Test: Gemini 2.5 Flash Lite Model")
    print("=" * 60)
    
    success = test_lite_model()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("❌ Test failed!")
        exit(1)