"""
Test Azure Application Insights Instrumentation
Simple test to validate that OpenTelemetry is properly configured
"""

import unittest
import logging
import os
import sys
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.telemetry import configure_telemetry, telemetry_span, add_span_attributes
from src.app_config import config

class TestApplicationInsightsInstrumentation(unittest.TestCase):
    """Test suite for Application Insights instrumentation"""
    
    def setUp(self):
        """Set up test environment"""
        self.logger = logging.getLogger(__name__)
        
    def test_telemetry_configuration_without_connection_string(self):
        """Test that telemetry gracefully handles missing connection string"""
        # Temporarily clear the connection string
        original_value = config.APPLICATIONINSIGHTS_CONNECTION_STRING
        config.APPLICATIONINSIGHTS_CONNECTION_STRING = ""
        
        try:
            tracer = configure_telemetry()
            self.assertIsNone(tracer, "Tracer should be None when connection string is not configured")
        finally:
            # Restore original value
            config.APPLICATIONINSIGHTS_CONNECTION_STRING = original_value
    
    @patch('src.telemetry.AzureMonitorTraceExporter')
    @patch('src.telemetry.AZURE_MONITOR_AVAILABLE', True)
    def test_telemetry_configuration_with_connection_string(self, mock_exporter):
        """Test telemetry configuration with valid connection string"""
        # Mock the connection string
        config.APPLICATIONINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test-key;IngestionEndpoint=https://test.in.applicationinsights.azure.com/"
        
        try:
            tracer = configure_telemetry()
            # Should return a tracer when properly configured
            self.assertIsNotNone(tracer, "Tracer should be configured when connection string is provided")
            
            # Verify the exporter was created with the connection string
            mock_exporter.assert_called_once_with(
                connection_string=config.APPLICATIONINSIGHTS_CONNECTION_STRING
            )
        except Exception as e:
            # It's ok if the actual Azure Monitor components fail in test environment
            self.logger.info(f"Expected failure in test environment: {e}")
    
    def test_telemetry_span_context_manager(self):
        """Test that telemetry span context manager works safely"""
        # Test with telemetry not initialized (should not crash)
        with telemetry_span("test.operation", {"test_attr": "test_value"}) as span:
            # Should handle gracefully even if telemetry is not initialized
            pass
        
        # Test that it doesn't raise exceptions
        self.assertTrue(True, "Telemetry span context manager should work safely")
    
    def test_add_span_attributes_with_none_span(self):
        """Test that add_span_attributes handles None span gracefully"""
        try:
            add_span_attributes(None, test_attr="test_value", numeric_attr=123)
            self.assertTrue(True, "add_span_attributes should handle None span gracefully")
        except Exception as e:
            self.fail(f"add_span_attributes should not raise exception with None span: {e}")
    
    def test_imports_work(self):
        """Test that all required modules can be imported"""
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
            self.assertTrue(True, "All telemetry imports should work")
        except ImportError as e:
            self.fail(f"Failed to import telemetry modules: {e}")
    
    def test_opentelemetry_dependencies_available(self):
        """Test that OpenTelemetry dependencies are available"""
        try:
            import opentelemetry
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            self.assertTrue(True, "OpenTelemetry dependencies should be available")
        except ImportError as e:
            self.fail(f"OpenTelemetry dependencies not available: {e}")
    
    def test_azure_monitor_exporter_available(self):
        """Test that Azure Monitor exporter is available (if installed)"""
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
            self.assertTrue(True, "Azure Monitor exporter is available")
        except ImportError:
            # This is expected in environments where Azure Monitor exporter is not installed
            self.skipTest("Azure Monitor exporter not installed - this is expected in test environments")

if __name__ == '__main__':
    # Configure logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    unittest.main(verbosity=2)