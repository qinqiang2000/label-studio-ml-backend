#!/usr/bin/env python3
"""
Test script for the /versions API endpoint
"""

import requests
import json
import sys
import os

# Default ML Backend URL
ML_BACKEND_URL = "http://localhost:9090"

def test_versions_endpoint():
    """Test the /versions endpoint"""
    url = f"{ML_BACKEND_URL}/versions"
    
    print(f"🚀 Testing /versions endpoint: {url}")
    
    try:
        # Test with GET request (as expected by Label Studio)
        response = requests.get(url, timeout=10)
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Received {len(data.get('versions', []))} model versions")
            
            # Pretty print the response
            print("📋 Response Data:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Analyze the response
            versions = data.get('versions', [])
            current_version = data.get('current_version', {})
            
            print(f"\n📊 Analysis:")
            print(f"   Total versions: {len(versions)}")
            print(f"   Current processor: {current_version.get('processor_type', 'unknown')}")
            print(f"   Current model: {current_version.get('model_name', 'unknown')}")
            
            print(f"\n📝 Available versions:")
            for i, version in enumerate(versions, 1):
                default_marker = " (DEFAULT)" if version.get('is_default') else ""
                print(f"   {i}. {version['version_string']} - {version['description']}{default_marker}")
            
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
        print(f"❌ Timeout: Request to {url} timed out")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_health_endpoint():
    """Test the /health endpoint to verify ML Backend is running"""
    url = f"{ML_BACKEND_URL}/health"
    
    print(f"🏥 Testing /health endpoint: {url}")
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ML Backend is healthy: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 ML Backend /versions API Test")
    print("=" * 60)
    
    # Check if custom URL provided
    if len(sys.argv) > 1:
        global ML_BACKEND_URL
        ML_BACKEND_URL = sys.argv[1].rstrip('/')
        print(f"Using custom ML Backend URL: {ML_BACKEND_URL}")
    
    # Test health first
    print("\n1. Testing ML Backend Health...")
    if not test_health_endpoint():
        print("\n❌ ML Backend is not running or not accessible!")
        print(f"   Please start the ML Backend first:")
        print(f"   cd /Users/qinqiang02/colab/codespace/ai/label-studio-ml-backend/invoice_extractor")
        print(f"   python _wsgi.py")
        sys.exit(1)
    
    # Test versions endpoint
    print("\n2. Testing /versions endpoint...")
    success = test_versions_endpoint()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! /versions endpoint is working correctly.")
    else:
        print("❌ Tests failed! Check the ML Backend logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()