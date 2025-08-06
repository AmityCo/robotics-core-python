#!/usr/bin/env python3
"""
Test script to verify Azure Application Insights logging integration
"""

import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.telemetry import configure_telemetry

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    """Test the logging integration"""
    
    print("Testing Azure Application Insights logging integration...")
    
    # Initialize telemetry (this should add the Azure Monitor logging handler)
    tracer = configure_telemetry()
    
    if tracer:
        print("✓ Telemetry configured successfully")
    else:
        print("⚠ Telemetry not configured (this is normal if no connection string is set)")
    
    # Test logging at different levels
    logger.debug("This is a DEBUG message - should not be sent to Application Insights")
    logger.info("This is an INFO message - should be sent to Application Insights")
    logger.warning("This is a WARNING message - should be sent to Application Insights")
    logger.error("This is an ERROR message - should be sent to Application Insights")
    
    # Test logging from different modules
    test_logger = logging.getLogger("test.module")
    test_logger.info("This is a test message from a different logger")
    
    print("\nLogging test completed. If Application Insights is configured,")
    print("the INFO, WARNING, and ERROR messages should appear in Azure Portal.")
    print("Check the 'Logs' section in your Application Insights resource.")

if __name__ == "__main__":
    main()
