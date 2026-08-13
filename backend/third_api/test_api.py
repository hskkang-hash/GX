"""
Test file for API Key Management endpoints
This file can be used to test the API endpoints manually
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api/third-party"

# Test endpoints
ENDPOINTS = {
    "create_api_key": f"{BASE_URL}/api-key-management/keys",
    "list_api_keys": f"{BASE_URL}/api-key-management/keys",
    "get_api_key": f"{BASE_URL}/api-key-management/keys/1",
    "update_api_key": f"{BASE_URL}/api-key-management/keys/1",
    "delete_api_key": f"{BASE_URL}/api-key-management/keys/1",
    "regenerate_api_key": f"{BASE_URL}/api-key-management/keys/1/regenerate",
    "get_usage_logs": f"{BASE_URL}/api-key-management/keys/1/usage-logs",
    "get_stats": f"{BASE_URL}/api-key-management/stats",
    "get_analytics": f"{BASE_URL}/api-key-management/analytics",
    "bulk_deactivate": f"{BASE_URL}/api-key-management/bulk-deactivate",
    "check_api_key": f"{BASE_URL}/api-key-management/check",
}

def test_create_api_key(token):
    """Test creating a new API key"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": "Test API Key",
        "expires_days": 30
    }
    
    response = requests.post(ENDPOINTS["create_api_key"], headers=headers, json=data)
    print(f"Create API Key - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_list_api_keys(token):
    """Test listing API keys"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(ENDPOINTS["list_api_keys"], headers=headers)
    print(f"List API Keys - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_get_stats(token):
    """Test getting API key statistics"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(ENDPOINTS["get_stats"], headers=headers)
    print(f"Get Stats - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

def test_get_analytics(token):
    """Test getting API key analytics"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(ENDPOINTS["get_analytics"], headers=headers, params={"days": 7})
    print(f"Get Analytics - Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response

if __name__ == "__main__":
    # You need to provide a valid JWT token here
    token = "your_jwt_token_here"
    
    print("Testing API Key Management Endpoints")
    print("=" * 50)
    
    # Test create API key
    print("\n1. Testing Create API Key:")
    test_create_api_key(token)
    
    # Test list API keys
    print("\n2. Testing List API Keys:")
    test_list_api_keys(token)
    
    # Test get stats
    print("\n3. Testing Get Stats:")
    test_get_stats(token)
    
    # Test get analytics
    print("\n4. Testing Get Analytics:")
    test_get_analytics(token)
    
    print("\nTest completed!") 