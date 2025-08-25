#!/usr/bin/env python3
"""
Simple test script for Phase 3 Content Intelligence API endpoints.
Run this after starting the Flask backend to verify the APIs are working.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an API endpoint and return the result."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
            
        print(f"Testing {method} {endpoint}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print("✅ Success")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    result = response.json()
                    print(f"Response keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                except:
                    print("Response: Non-JSON or empty")
            print()
            return True
        else:
            print(f"❌ Expected {expected_status}, got {response.status_code}")
            print(f"Response: {response.text[:200]}")
            print()
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed - is the backend running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Test all Phase 3 API endpoints."""
    print("🧪 Testing Phase 3 Content Intelligence API Endpoints")
    print("=" * 60)
    
    # Health check first
    if not test_endpoint("GET", "/api/health"):
        print("❌ Backend health check failed. Make sure the backend is running.")
        sys.exit(1)
    
    # Test basic endpoints
    tests = [
        # Entity Recognition
        ("GET", "/api/entities"),
        ("GET", "/api/entities?type=PERSON&min_confidence=0.5"),
        
        # Topic Modeling
        ("GET", "/api/topics"),
        ("GET", "/api/topics?search=test"),
        
        # Embeddings
        ("GET", "/api/embeddings"),
        
        # Emotions
        ("GET", "/api/emotions"),
        
        # Semantic Search
        ("POST", "/api/search/semantic", {"query": "test search", "threshold": 0.7, "limit": 10}),
    ]
    
    passed = 0
    total = len(tests)
    
    for method, endpoint, *args in tests:
        data = args[0] if args else None
        if test_endpoint(method, endpoint, data):
            passed += 1
    
    # Test video-specific endpoints (these will likely return 404 for non-existent videos)
    video_tests = [
        ("GET", "/api/videos/test-video-id/entities", None, 404),
        ("GET", "/api/videos/test-video-id/topics", None, 404),
        ("GET", "/api/videos/test-video-id/emotions", None, 404),
        ("POST", "/api/videos/test-video-id/process-intelligence", {}, 404),
    ]
    
    print("Testing video-specific endpoints (expecting 404 for non-existent video):")
    for method, endpoint, data, expected in video_tests:
        if test_endpoint(method, endpoint, data, expected):
            passed += 1
        total += 1
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 3 API endpoints are working!")
    else:
        print(f"⚠️  {total - passed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
