#!/usr/bin/env python3
"""
Test script for TTS caching functionality
"""
import os
import sys
import time
import logging

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tts_handler import TTSHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tts_caching():
    """Test TTS caching functionality"""
    
    # Note: You'll need to set these environment variables for testing
    subscription_key = os.getenv("AZURE_TTS_SUBSCRIPTION_KEY")
    if not subscription_key:
        logger.error("AZURE_TTS_SUBSCRIPTION_KEY environment variable not set")
        return
    
    # Initialize TTS handler
    tts_handler = TTSHandler(subscription_key=subscription_key)
    
    # Test SSML content
    test_ssml = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="en-US-AriaNeural">
            <prosody rate="medium" pitch="medium">
                Hello! This is a test of the TTS caching system. 
                The first time you hear this, it will be generated fresh. 
                The second time should come from the cache.
            </prosody>
        </voice>
    </speak>'''
    
    logger.info("=== Testing TTS Caching ===")
    
    # First call - should generate and cache
    logger.info("First call (should generate fresh audio)...")
    start_time = time.time()
    audio1 = tts_handler.generate_speech(test_ssml)
    duration1 = time.time() - start_time
    
    if audio1:
        logger.info(f"✓ First call successful: {len(audio1)} bytes in {duration1:.2f} seconds")
    else:
        logger.error("✗ First call failed")
        return
    
    # Wait a moment for async cache save
    logger.info("Waiting for cache save to complete...")
    time.sleep(2)
    
    # Second call - should use cache
    logger.info("Second call (should use cached audio)...")
    start_time = time.time()
    audio2 = tts_handler.generate_speech(test_ssml)
    duration2 = time.time() - start_time
    
    if audio2:
        logger.info(f"✓ Second call successful: {len(audio2)} bytes in {duration2:.2f} seconds")
        
        # Compare results
        if audio1 == audio2:
            logger.info("✓ Audio data matches between calls")
        else:
            logger.warning("⚠ Audio data differs between calls")
            
        if duration2 < duration1 * 0.5:  # Cache should be significantly faster
            logger.info(f"✓ Cache significantly faster ({duration2:.2f}s vs {duration1:.2f}s)")
        else:
            logger.warning(f"⚠ Cache not much faster ({duration2:.2f}s vs {duration1:.2f}s)")
            
    else:
        logger.error("✗ Second call failed")
        return
    
    # Test cache info
    logger.info("Testing cache info...")
    cache_info = tts_handler.get_cache_info("Hello! This is a test of the TTS caching system. The first time you hear this, it will be generated fresh. The second time should come from the cache.")
    logger.info(f"Cache info: {cache_info}")
    
    logger.info("=== Test Complete ===")

if __name__ == "__main__":
    test_tts_caching()
