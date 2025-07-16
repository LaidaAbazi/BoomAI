#!/usr/bin/env python3
"""
Test script for Swagger documentation setup
"""

import requests
import json
import sys

def test_swagger_endpoints():
    """Test basic Swagger endpoints"""
    base_url = "http://localhost:10000"
    
    print("🧪 Testing StoryBoom AI API Swagger Setup")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Server is running (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start with: python run.py")
        return False
    
    # Test 2: Check Swagger UI endpoint
    try:
        response = requests.get(f"{base_url}/apidocs/")
        if response.status_code == 200:
            print("✅ Swagger UI is accessible at /apidocs/")
        else:
            print(f"❌ Swagger UI returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing Swagger UI: {e}")
    
    # Test 3: Check API spec endpoint
    try:
        response = requests.get(f"{base_url}/apispec_1.json")
        if response.status_code == 200:
            spec = response.json()
            print(f"✅ API spec loaded successfully")
            print(f"   - Title: {spec.get('info', {}).get('title', 'N/A')}")
            print(f"   - Version: {spec.get('info', {}).get('version', 'N/A')}")
            print(f"   - Endpoints: {len(spec.get('paths', {}))}")
        else:
            print(f"❌ API spec returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing API spec: {e}")
    
    # Test 4: Test a simple endpoint (signup)
    try:
        test_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "testpassword123"
        }
        response = requests.post(
            f"{base_url}/api/signup",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code in [201, 409]:  # 201 = created, 409 = already exists
            print("✅ API endpoint /api/signup is working")
        else:
            print(f"⚠️  API endpoint /api/signup returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing API endpoint: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Swagger setup test completed!")
    print("\n📖 Next steps:")
    print("1. Open your browser and go to: http://localhost:10000/apidocs/")
    print("2. Explore the interactive API documentation")
    print("3. Test endpoints directly from the Swagger UI")
    print("4. Check the SWAGGER_SETUP.md file for detailed instructions")
    
    return True

def show_usage():
    """Show usage instructions"""
    print("""
Usage: python test_swagger.py

This script tests the Swagger documentation setup for the StoryBoom AI API.

Prerequisites:
1. Make sure the Flask app is running (python run.py)
2. The app should be accessible at http://localhost:10000

The script will test:
- Server connectivity
- Swagger UI accessibility
- API specification loading
- Basic endpoint functionality
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
    else:
        test_swagger_endpoints() 