#!/usr/bin/env python3
"""
Test script to verify client interview flow and final summary update
"""

import requests
import json
import time

def test_client_interview_flow():
    """Test the complete client interview flow"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Client Interview Flow...")
    
    # Step 1: Test client summary generation
    print("\n1️⃣ Testing client summary generation...")
    
    test_data = {
        "transcript": "INTERVIEWER: Hi, welcome to StoryBoom AI! How's your day going?\nCLIENT: Hi! My day is going well, thanks for asking.\nINTERVIEWER: Great! I recently spoke with John from TechCorp about the CRM implementation project you worked on together. Could you tell me about your experience?\nCLIENT: Oh yes, that was a fantastic project. We were struggling with our old system and TechCorp really helped us streamline everything. The new CRM has improved our customer response time by 40% and our team is much more efficient now.\nINTERVIEWER: That's impressive! What was the biggest challenge you faced?\nCLIENT: The biggest challenge was getting our team to adapt to the new system. But TechCorp provided excellent training and support, which made the transition much smoother than we expected.\nINTERVIEWER: Wonderful! Is there anything else you'd like to add?\nCLIENT: Just that we're very satisfied with the results and would definitely recommend TechCorp to other companies looking for similar solutions.",
        "token": "test-token-123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/generate_client_summary",
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Client summary generated successfully!")
            print(f"   Status: {result.get('status')}")
            print(f"   Case Study ID: {result.get('case_study_id')}")
            print(f"   Client Summary Length: {len(result.get('client_summary', ''))}")
            
            if result.get('client_summary'):
                print(f"   Summary Preview: {result.get('client_summary')[:100]}...")
            
            return True
        else:
            print(f"❌ Failed to generate client summary")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_full_case_study_generation():
    """Test full case study generation"""
    
    base_url = "http://localhost:5000"
    
    print("\n2️⃣ Testing full case study generation...")
    
    test_data = {
        "case_study_id": 1,  # Assuming case study ID 1 exists
        "solution_provider": "TechCorp",
        "client_name": "TestClient",
        "project_name": "CRM Implementation"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/generate_full_case_study",
            headers={"Content-Type": "application/json"},
            json=test_data,
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Full case study generated successfully!")
            print(f"   Status: {result.get('status')}")
            
            if result.get('full_case_study'):
                print(f"   Case Study Length: {len(result.get('full_case_study'))}")
                print(f"   Preview: {result.get('full_case_study')[:100]}...")
            
            return True
        else:
            print(f"❌ Failed to generate full case study")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Client Interview Flow Tests...")
    
    # Test client summary generation
    success1 = test_client_interview_flow()
    
    # Test full case study generation
    success2 = test_full_case_study_generation()
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS:")
    print(f"   Client Summary Generation: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"   Full Case Study Generation: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The client interview flow is working correctly.")
        print("   The final summary should now be updated after client interviews.")
    else:
        print("\n⚠️ Some tests failed. Please check the error messages above.")
    
    print("="*50) 