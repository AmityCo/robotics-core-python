"""
OpenTelemetry Configuration Module
Sets up Azure Application Insights instrumentation for FastAPI, requests, DynamoDB, and Azure Storage
"""

import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor

try:
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter, AzureMonitorLogExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    AZURE_MONITOR_AVAILABLE = True
except ImportError:
    try:
        # Fallback for older versions
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter, AzureMonitorLogExporter
        from opentelemetry._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk._logs import LoggingHandler
        AZURE_MONITOR_AVAILABLE = True
    except ImportError:
        AZURE_MONITOR_AVAILABLE = False
        logging.warning("Azure Monitor exporter not available. Install azure-monitor-opentelemetry-exporter")

from .app_config import config

logger = logging.getLogger(__name__)

_telemetry_initialized = False

def configure_telemetry() -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry with Azure Application Insights
    
    Returns:
        Tracer instance if successfully configured, None otherwise
    """
    global _telemetry_initialized
    
    if _telemetry_initialized:
        logger.debug("Telemetry already initialized")
        return trace.get_tracer(__name__)
    
    if not config.APPLICATIONINSIGHTS_CONNECTION_STRING:
        logger.info("Azure Application Insights connection string not configured, skipping telemetry setup")
        return None
    
    if not AZURE_MONITOR_AVAILABLE:
        logger.warning("Azure Monitor exporter not available, telemetry disabled")
        return None
    
    try:
        # Set up the tracer provider
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        
        # Configure Azure Monitor exporter for traces
        azure_trace_exporter = AzureMonitorTraceExporter(
            connection_string=config.APPLICATIONINSIGHTS_CONNECTION_STRING
        )
        
        # Add the trace exporter to the tracer provider with batch processing
        span_processor = BatchSpanProcessor(azure_trace_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Set up logging integration
        _setup_logging_integration()
        
        # Set up automatic instrumentation
        _setup_auto_instrumentation()
         
        _telemetry_initialized = True
        logger.info("Azure Application Insights telemetry configured successfully")
        
        return trace.get_tracer(__name__)
        
    except Exception as e:
        logger.error(f"Failed to configure telemetry: {str(e)}")
        return None

def _setup_auto_instrumentation():
    """Set up automatic instrumentation for common libraries"""
    try:
        # Instrument requests library
        RequestsInstrumentor().instrument()
        logger.debug("Requests instrumentation enabled")
        
        # Instrument boto3 for DynamoDB operations
        Boto3SQSInstrumentor().instrument()
        logger.debug("Boto3 instrumentation enabled")
        
    except Exception as e:
        logger.warning(f"Failed to set up some auto-instrumentation: {str(e)}")

def _setup_logging_integration():
    """Set up Azure Monitor logging integration to send logs to Application Insights"""
    try:
        # Configure Azure Monitor log exporter
        azure_log_exporter = AzureMonitorLogExporter(
            connection_string=config.APPLICATIONINSIGHTS_CONNECTION_STRING
        )
        
        # Set up logger provider with batch processing and reduced timeout
        logger_provider = LoggerProvider()
        log_processor = BatchLogRecordProcessor(
            azure_log_exporter,
            export_timeout_millis=5000,  # Reduce timeout to 5 seconds
            schedule_delay_millis=1000   # Reduce delay to 1 second
        )
        logger_provider.add_log_record_processor(log_processor)
        
        # Create and configure the logging handler
        logging_handler = LoggingHandler(
            level=logging.INFO,  # Send INFO level and above to Application Insights
            logger_provider=logger_provider
        )
        
        # Add the handler to the root logger to capture all logging
        root_logger = logging.getLogger()
        root_logger.addHandler(logging_handler)
        
        logger.info("Azure Monitor logging integration enabled - all logs will be sent to Application Insights")
        
    except Exception as e:
        logger.warning(f"Failed to set up logging integration: {str(e)}")

def instrument_fastapi(app):
    """
    Instrument FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    if not _telemetry_initialized:
        logger.debug("Telemetry not initialized, skipping FastAPI instrumentation")
        return
    
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {str(e)}")

def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer instance for creating custom spans
    
    Args:
        name: Name for the tracer
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)

def create_span(name: str, attributes: dict = None) -> trace.Span:
    """
    Create a custom span for manual instrumentation
    
    Args:
        name: Name of the span
        attributes: Optional attributes to add to the span
        
    Returns:
        Span instance
    """
    tracer = get_tracer()
    span = tracer.start_span(name)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    return span

# Context managers for easy span usage
class telemetry_span:
    """Context manager for creating telemetry spans"""
    
    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None
    
    def __enter__(self):
        if not _telemetry_initialized:
            return None
        
        try:
            tracer = get_tracer()
            self.span = tracer.start_span(self.name)
            
            # Add attributes
            for key, value in self.attributes.items():
                self.span.set_attribute(key, str(value))
            
            return self.span
        except Exception as e:
            logger.debug(f"Failed to create span {self.name}: {str(e)}")
            return None
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            try:
                if exc_type:
                    self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
                else:
                    self.span.set_status(trace.Status(trace.StatusCode.OK))
                
                self.span.end()
            except Exception as e:
                logger.debug(f"Failed to end span {self.name}: {str(e)}")

def add_span_attributes(span, **attributes):
    """
    Add attributes to a span safely
    
    Args:
        span: Span instance (can be None)
        **attributes: Attributes to add
    """
    if span and attributes:
        try:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        except Exception as e:
            logger.debug(f"Failed to add span attributes: {str(e)}")

def record_exception(span, exception: Exception):
    """
    Record an exception in a span safely
    
    Args:
        span: Span instance (can be None)
        exception: Exception to record
    """
    if span:
        try:
            span.record_exception(exception)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
        except Exception as e:
            logger.debug(f"Failed to record exception in span: {str(e)}")