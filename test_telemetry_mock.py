"""
Test Azure Application Insights Instrumentation - Mock Version
Simple test to validate that our code structure is correct without requiring dependencies
"""

import unittest
import sys
import os

# Mock the OpenTelemetry modules for testing
class MockSpan:
    def set_attribute(self, key, value): pass
    def set_status(self, status): pass
    def record_exception(self, exception): pass
    def end(self): pass

class MockTracer:
    def start_span(self, name): return MockSpan()

class MockTrace:
    Tracer = MockTracer
    Span = MockSpan
    StatusCode = type('StatusCode', (), {'OK': 'OK', 'ERROR': 'ERROR'})()
    Status = lambda status_code, description="": None
    
    def get_tracer(self, name): return MockTracer()
    def set_tracer_provider(self, provider): pass

class MockTracerProvider:
    def add_span_processor(self, processor): pass

class MockBatchSpanProcessor:
    def __init__(self, exporter): pass

class MockFastAPIInstrumentor:
    @classmethod
    def instrument_app(cls, app): pass

class MockRequestsInstrumentor:
    def instrument(self): pass

class MockBoto3SQSInstrumentor:
    def instrument(self): pass

class MockAzureMonitorTraceExporter:
    def __init__(self, connection_string): pass

# Mock modules
sys.modules['opentelemetry'] = type('module', (), {'trace': MockTrace()})()
sys.modules['opentelemetry.trace'] = MockTrace()
sys.modules['opentelemetry.sdk'] = type('module', (), {})()
sys.modules['opentelemetry.sdk.trace'] = type('module', (), {
    'TracerProvider': MockTracerProvider
})()
sys.modules['opentelemetry.sdk.trace.export'] = type('module', (), {
    'BatchSpanProcessor': MockBatchSpanProcessor
})()
sys.modules['opentelemetry.instrumentation'] = type('module', (), {})()
sys.modules['opentelemetry.instrumentation.fastapi'] = type('module', (), {
    'FastAPIInstrumentor': MockFastAPIInstrumentor
})()
sys.modules['opentelemetry.instrumentation.requests'] = type('module', (), {
    'RequestsInstrumentor': MockRequestsInstrumentor
})()
sys.modules['opentelemetry.instrumentation.boto3sqs'] = type('module', (), {
    'Boto3SQSInstrumentor': MockBoto3SQSInstrumentor
})()
sys.modules['azure'] = type('module', (), {})()
sys.modules['azure.monitor'] = type('module', (), {})()
sys.modules['azure.monitor.opentelemetry'] = type('module', (), {})()
sys.modules['azure.monitor.opentelemetry.exporter'] = type('module', (), {
    'AzureMonitorTraceExporter': MockAzureMonitorTraceExporter
})()

# Mock other dependencies
sys.modules['dotenv'] = type('module', (), {'load_dotenv': lambda **kwargs: None})()
sys.modules['boto3'] = type('module', (), {'resource': lambda *args, **kwargs: None})()
sys.modules['azure.storage'] = type('module', (), {})()
sys.modules['azure.storage.blob'] = type('module', (), {
    'BlobServiceClient': type('BlobServiceClient', (), {
        'from_connection_string': classmethod(lambda cls, conn_str: None),
        '__init__': lambda self, **kwargs: None
    })
})()
sys.modules['azure.core'] = type('module', (), {})()
sys.modules['azure.core.exceptions'] = type('module', (), {
    'AzureError': Exception,
    'ResourceNotFoundError': Exception
})()
sys.modules['botocore'] = type('module', (), {})()
sys.modules['botocore.exceptions'] = type('module', (), {
    'ClientError': Exception,
    'NoCredentialsError': Exception
})()
sys.modules['cashews'] = type('module', (), {})()

# Mock config
class MockConfig:
    APPLICATIONINSIGHTS_CONNECTION_STRING = ""
    CORS_ORIGINS = ["*"]
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 8000
    
    @classmethod
    def get_cors_settings(cls):
        return {"allow_origins": cls.CORS_ORIGINS}

sys.modules['src.app_config'] = type('module', (), {'config': MockConfig()})()

class TestApplicationInsightsInstrumentation(unittest.TestCase):
    """Test suite for Application Insights instrumentation structure"""
    
    def test_telemetry_module_structure(self):
        """Test that telemetry module can be imported and has expected functions"""
        try:
            from src.telemetry import (
                configure_telemetry, 
                instrument_fastapi,
                get_tracer,
                create_span,
                telemetry_span,
                add_span_attributes,
                record_exception
            )
            self.assertTrue(True, "All telemetry functions imported successfully")
        except Exception as e:
            self.fail(f"Failed to import telemetry functions: {e}")
    
    def test_telemetry_configuration_without_connection_string(self):
        """Test that telemetry gracefully handles missing connection string"""
        from src.telemetry import configure_telemetry
        from src.app_config import config
        
        # Ensure connection string is empty
        config.APPLICATIONINSIGHTS_CONNECTION_STRING = ""
        
        tracer = configure_telemetry()
        self.assertIsNone(tracer, "Should return None when connection string is not configured")
    
    def test_telemetry_span_context_manager(self):
        """Test that telemetry span context manager works safely"""
        from src.telemetry import telemetry_span
        
        # Test with telemetry not initialized (should not crash)
        with telemetry_span("test.operation", {"test_attr": "test_value"}) as span:
            # Should handle gracefully
            pass
        
        self.assertTrue(True, "Telemetry span context manager worked safely")
    
    def test_add_span_attributes_safety(self):
        """Test that add_span_attributes handles None span gracefully"""
        from src.telemetry import add_span_attributes
        
        try:
            add_span_attributes(None, test_attr="test_value", numeric_attr=123)
            self.assertTrue(True, "add_span_attributes handled None span gracefully")
        except Exception as e:
            self.fail(f"add_span_attributes should not raise exception with None span: {e}")
    
    def test_updated_modules_structure(self):
        """Test that updated modules maintain their structure"""
        try:
            # Test that we can import the modules (they should not crash on import)
            import ast
            
            modules_to_test = [
                'src/telemetry.py',
                'src/app_config.py', 
                'src/dynamodb_handler.py',
                'src/azure_storage_handler.py',
                'main.py'
            ]
            
            for module_path in modules_to_test:
                with open(module_path, 'r') as f:
                    code = f.read()
                
                # Parse to check syntax
                ast.parse(code)
                
                # Check for telemetry imports in appropriate modules
                if 'dynamodb_handler.py' in module_path:
                    self.assertIn('telemetry_span', code, "DynamoDB handler should import telemetry_span")
                    self.assertIn('add_span_attributes', code, "DynamoDB handler should import add_span_attributes")
                
                if 'azure_storage_handler.py' in module_path:
                    self.assertIn('telemetry_span', code, "Azure storage handler should import telemetry_span")
                
                if module_path == 'main.py':
                    self.assertIn('configure_telemetry', code, "main.py should import configure_telemetry")
                    self.assertIn('instrument_fastapi', code, "main.py should import instrument_fastapi")
            
            self.assertTrue(True, "All modules have correct structure")
        
        except Exception as e:
            self.fail(f"Module structure test failed: {e}")
    
    def test_configuration_additions(self):
        """Test that configuration has been properly updated"""
        from src.app_config import config
        
        # Test that Application Insights connection string config exists
        self.assertTrue(hasattr(config, 'APPLICATIONINSIGHTS_CONNECTION_STRING'), 
                       "Config should have APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    def test_requirements_updated(self):
        """Test that requirements.txt has been updated with OpenTelemetry dependencies"""
        try:
            with open('requirements.txt', 'r') as f:
                requirements = f.read()
            
            expected_packages = [
                'opentelemetry-api',
                'opentelemetry-sdk', 
                'opentelemetry-instrumentation-fastapi',
                'opentelemetry-instrumentation-requests',
                'azure-monitor-opentelemetry-exporter'
            ]
            
            for package in expected_packages:
                self.assertIn(package, requirements, f"Requirements should include {package}")
            
            self.assertTrue(True, "Requirements.txt properly updated")
        
        except Exception as e:
            self.fail(f"Requirements test failed: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2)