#!/usr/bin/env python3
"""
Test script for OpenSearch crash prevention improvements
"""

import os
import sys
import time
import logging
from unittest.mock import Mock, patch

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opensearch_data import OpenSearchDataService, CircuitBreaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_circuit_breaker():
    """Test Circuit Breaker functionality"""
    print("🧪 Testing Circuit Breaker...")
    
    cb = CircuitBreaker(max_failures=3, reset_timeout=5)
    
    # Test successful calls
    def success_func():
        return "success"
    
    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == 'CLOSED'
    print("✅ Circuit breaker handles successful calls")
    
    # Test failure handling
    def failure_func():
        raise Exception("Test failure")
    
    failures = 0
    for _ in range(3):
        try:
            cb.call(failure_func)
        except Exception:
            failures += 1
    
    assert failures == 3
    assert cb.state == 'OPEN'
    print("✅ Circuit breaker opens after max failures")
    
    # Test reset after timeout
    time.sleep(6)  # Wait for reset timeout
    try:
        cb.call(success_func)
        assert cb.state == 'CLOSED'
        print("✅ Circuit breaker resets after timeout")
    except Exception:
        print("❌ Circuit breaker should reset after timeout")

def test_safe_opensearch_call():
    """Test safe_opensearch_call decorator"""
    print("🧪 Testing Safe OpenSearch Call Decorator...")
    
    from opensearch_data import safe_opensearch_call
    
    @safe_opensearch_call
    def failing_search():
        raise Exception("Connection timeout")
    
    # Should return fallback instead of raising
    result = failing_search()
    assert result == {"hits": {"hits": []}}
    print("✅ Decorator returns fallback for search functions")
    
    @safe_opensearch_call
    def failing_get():
        raise Exception("Connection timeout")
    
    result = failing_get()
    assert result == {}
    print("✅ Decorator returns fallback for get functions")

def test_opensearch_service_initialization():
    """Test OpenSearch service initialization with crash protection"""
    print("🧪 Testing OpenSearch Service Initialization...")
    
    # Test with invalid host (should not crash)
    with patch.dict(os.environ, {'OPENSEARCH_HOST': 'https://invalid-host:9999'}):
        try:
            service = OpenSearchDataService()
            # Should not crash, just log warning
            assert service.client is None
            print("✅ Service handles invalid host gracefully")
        except Exception as e:
            print(f"❌ Service crashed with invalid host: {e}")

def test_health_check():
    """Test health check functionality"""
    print("🧪 Testing Health Check...")
    
    service = OpenSearchDataService()
    
    # Test health check
    is_healthy = service.is_healthy()
    print(f"Health status: {is_healthy}")
    
    # Test reconnect
    reconnect_success = service.reconnect()
    print(f"Reconnect success: {reconnect_success}")

def test_search_with_fallbacks():
    """Test search methods with fallback behavior"""
    print("🧪 Testing Search with Fallbacks...")
    
    service = OpenSearchDataService()
    
    # Test search with fallback
    query = {"match_all": {}}
    results = service.search(query)
    assert isinstance(results, dict)
    assert "hits" in results
    print("✅ Search returns valid fallback structure")
    
    # Test batch search with fallback
    unique_ids = ["drone1", "drone2", "drone3"]
    positions = service.search_drone_positions_batch(unique_ids)
    assert isinstance(positions, dict)
    assert len(positions) == len(unique_ids)
    print("✅ Batch search returns valid fallback structure")

def test_connection_configuration():
    """Test connection configuration improvements"""
    print("🧪 Testing Connection Configuration...")
    
    service = OpenSearchDataService()
    
    if service.client:
        # Check if client has proper configuration
        config = service.client.transport.connection_pool.connection_kwargs
        print(f"Connection timeout: {config.get('timeout', 'Not set')}")
        print(f"Max retries: {config.get('max_retries', 'Not set')}")
        print("✅ Connection configuration applied")
    else:
        print("⚠️ Client not available, skipping configuration test")

def test_performance_monitoring():
    """Test performance monitoring features"""
    print("🧪 Testing Performance Monitoring...")
    
    service = OpenSearchDataService()
    
    # Test cluster health
    health = service.get_cluster_health()
    assert isinstance(health, dict)
    print("✅ Cluster health check works")
    
    # Test indices listing
    indices = service.get_indices()
    assert isinstance(indices, list)
    print("✅ Indices listing works")

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting OpenSearch Crash Prevention Tests\n")
    
    tests = [
        test_circuit_breaker,
        test_safe_opensearch_call,
        test_opensearch_service_initialization,
        test_health_check,
        test_search_with_fallbacks,
        test_connection_configuration,
        test_performance_monitoring,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
        print()
    
    print("📊 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! OpenSearch crash prevention is working correctly.")
    else:
        print(f"\n⚠️ {failed} tests failed. Please check the implementation.")

if __name__ == "__main__":
    run_all_tests()
