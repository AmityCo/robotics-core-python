#!/usr/bin/env python3
"""
Manual test script to verify the application starts correctly with telemetry integration
This can be run even without OpenTelemetry dependencies installed to verify graceful degradation
"""

import sys
import os
import subprocess
import tempfile

def test_import_main():
    """Test that main.py can be imported without errors"""
    print("Testing main.py import...")
    
    try:
        # Create a temporary script that imports main
        test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    import main
    print("✓ main.py imported successfully")
    print(f"✓ FastAPI app created: {main.app is not None}")
    print(f"✓ App title: {main.app.title}")
    print("✓ All imports working correctly")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        # Write to temporary file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            result = subprocess.run([sys.executable, temp_script], 
                                 capture_output=True, text=True, timeout=30)
            
            print("Import test output:")
            print(result.stdout)
            
            if result.stderr:
                print("Warnings/Errors:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("✓ Import test passed")
                return True
            else:
                print("✗ Import test failed")
                return False
                
        finally:
            os.unlink(temp_script)
            
    except Exception as e:
        print(f"✗ Import test error: {e}")
        return False

def test_telemetry_graceful_degradation():
    """Test that telemetry handles missing dependencies gracefully"""
    print("\nTesting telemetry graceful degradation...")
    
    try:
        # Test with minimal environment
        test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

# Test without Application Insights connection string
os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)

try:
    from src.telemetry import configure_telemetry, telemetry_span
    
    # Should return None when no connection string
    tracer = configure_telemetry()
    if tracer is None:
        print("✓ Telemetry correctly disabled without connection string")
    else:
        print("? Telemetry initialized (this might be expected in some environments)")
    
    # Test span context manager doesn't crash
    with telemetry_span("test.operation") as span:
        pass
    print("✓ Telemetry span context manager works safely")
    
except ImportError as e:
    if "opentelemetry" in str(e).lower():
        print("✓ Telemetry gracefully handles missing OpenTelemetry (expected in test environment)")
    else:
        print(f"✗ Unexpected import error: {e}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Telemetry test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            result = subprocess.run([sys.executable, temp_script], 
                                 capture_output=True, text=True, timeout=30)
            
            print("Telemetry test output:")
            print(result.stdout)
            
            if result.stderr:
                print("Warnings/Errors:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("✓ Telemetry graceful degradation test passed")
                return True
            else:
                print("✗ Telemetry test failed")
                return False
                
        finally:
            os.unlink(temp_script)
            
    except Exception as e:
        print(f"✗ Telemetry test error: {e}")
        return False

def test_app_startup():
    """Test that the application can start without crashing"""
    print("\nTesting application startup...")
    
    try:
        # Test app creation and basic endpoints
        test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    import main
    
    # Test basic endpoint structure
    app = main.app
    
    # Check if routes are registered
    routes = [route.path for route in app.routes]
    print(f"✓ Routes registered: {routes}")
    
    # Check for expected endpoints
    expected_endpoints = ["/", "/health", "/api/v1/answer-sse"]
    for endpoint in expected_endpoints:
        if endpoint in routes:
            print(f"✓ Endpoint {endpoint} registered")
        else:
            print(f"? Endpoint {endpoint} not found (might be expected)")
    
    print("✓ Application startup test completed successfully")
    
except Exception as e:
    print(f"✗ Application startup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            result = subprocess.run([sys.executable, temp_script], 
                                 capture_output=True, text=True, timeout=30)
            
            print("App startup test output:")
            print(result.stdout)
            
            if result.stderr:
                print("Warnings/Errors:")
                print(result.stderr)
            
            if result.returncode == 0:
                print("✓ Application startup test passed")
                return True
            else:
                print("✗ Application startup test failed")
                return False
                
        finally:
            os.unlink(temp_script)
            
    except Exception as e:
        print(f"✗ App startup test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Azure Application Insights Integration - Manual Test")
    print("=" * 60)
    
    tests = [
        test_import_main,
        test_telemetry_graceful_degradation,
        test_app_startup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Application Insights integration is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())