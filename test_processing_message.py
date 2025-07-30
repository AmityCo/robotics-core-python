#!/usr/bin/env python3
"""
Test script for the get_random_processing_message function
"""

import sys
import os
import asyncio
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from answer_flow_sse import get_random_processing_message
from org_config import load_org_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_processing_message():
    """Test getting processing messages from org config"""
    
    # Test config ID (from the sample data)
    sample_org_id = "sample_org_123"
    sample_config_id = "45f9aacfe37ff6c7e072326c600a3b60"
    
    try:
        # Load organization configuration
        logger.info(f"Loading org config for orgId: {sample_org_id}, configId: {sample_config_id}")
        org_config = await load_org_config(sample_org_id, sample_config_id)
        
        if not org_config:
            logger.error(f"No configuration found for orgId: {sample_org_id}, configId: {sample_config_id}")
            return
        
        logger.info(f"Loaded org config: {org_config.displayName}")
        
        # Test different languages
        test_languages = ['th-TH', 'en-US', 'zh-CN', 'ja-JP', 'ko-KR', 'ar-AE', 'ru-RU']
        
        for language in test_languages:
            try:
                message = get_random_processing_message(org_config, language)
                logger.info(f"Processing message for {language}: '{message}'")
            except Exception as e:
                logger.error(f"Error getting message for {language}: {str(e)}")
        
        # Test multiple calls for one language to see randomization
        logger.info("\nTesting randomization for th-TH (5 calls):")
        for i in range(5):
            message = get_random_processing_message(org_config, 'th-TH')
            logger.info(f"  Call {i+1}: '{message}'")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_processing_message())
