#!/usr/bin/env python3
"""
Test script for TTS integration with answer flow
"""

import sys
import os
import logging
import time
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tts_stream import TTSStreamer, TTSBuffer
from src.org_config import load_org_config, OrgConfigData, TTSConfig, AzureTTSConfig, TTSModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_org_config():
    """Create a test organization configuration with TTS settings"""
    
    # Sample TTS model (you'll need to adjust based on your actual Azure setup)
    tts_model = TTSModel(
        language="en-US",
        name="en-US-JennyNeural",  # Common Azure TTS voice
        pitch=None,
        phonemeUrl=None
    )
    
    azure_config = AzureTTSConfig(
        subscriptionKey="YOUR_AZURE_TTS_KEY_HERE",  # Replace with actual key
        lexiconURL="",
        phonemeUrl="",
        models=[tts_model]
    )
    
    tts_config = TTSConfig(azure=azure_config)
    
    # Create minimal org config for testing
    class TestOrgConfig:
        def __init__(self):
            self.tts = tts_config
            self.displayName = "Test Organization"
    
    return TestOrgConfig()

def test_tts_buffer():
    """Test the TTS buffer functionality"""
    logger.info("Testing TTS buffer...")
    
    def audio_callback(text: str, audio_data: bytes):
        logger.info(f"Audio generated for: '{text}' (size: {len(audio_data)} bytes)")
    
    try:
        # Create test config
        test_config = create_test_org_config()
        model = test_config.tts.azure.models[0]
        
        # Test buffer with dummy subscription key (will fail API call but test logic)
        buffer = TTSBuffer(
            subscription_key="test_key",
            region="southeastasia",
            min_words=3,
            max_wait_seconds=2.0,
            chunk_callback=audio_callback
        )
        
        # Test adding text chunks
        logger.info("Adding text chunks...")
        buffer.add_text("Hello", "en-US", model)
        buffer.add_text(" world", "en-US", model)
        buffer.add_text(" this", "en-US", model)  # Should trigger at 3 words
        
        time.sleep(0.5)
        
        buffer.add_text(" is another", "en-US", model)
        buffer.add_text(" test", "en-US", model)  # Should trigger timeout after 2 seconds
        
        # Wait for timeout
        time.sleep(3)
        
        # Test flush
        buffer.add_text(" final text", "en-US", model)
        buffer.flush("en-US", model)
        
        time.sleep(1)
        
        logger.info("TTS buffer test completed")
        
    except Exception as e:
        logger.error(f"TTS buffer test failed: {e}")

def test_tts_streamer():
    """Test the TTS streamer functionality"""
    logger.info("Testing TTS streamer...")
    
    def audio_callback(text: str, language: str, audio_data: bytes):
        logger.info(f"Audio ready - Text: '{text[:50]}...', Language: {language}, Size: {len(audio_data)} bytes")
    
    try:
        # Create test config
        test_config = create_test_org_config()
        
        streamer = TTSStreamer(test_config, chunk_callback=audio_callback)
        
        # Test getting available voices (will fail without real key)
        logger.info("Testing voice list retrieval...")
        voices = streamer.get_available_voices()
        if voices:
            logger.info(f"Found {len(voices)} available voices")
        else:
            logger.warning("Could not retrieve voices (expected with test key)")
        
        # Test adding text chunks
        logger.info("Adding text chunks to streamer...")
        streamer.add_text_chunk("Hello", "en-US")
        streamer.add_text_chunk(" world", "en-US")
        streamer.add_text_chunk(" this is", "en-US")
        streamer.add_text_chunk(" a comprehensive", "en-US")
        streamer.add_text_chunk(" test of the", "en-US")
        streamer.add_text_chunk(" TTS streaming", "en-US")
        streamer.add_text_chunk(" functionality.", "en-US")
        
        # Wait for processing
        time.sleep(3)
        
        # Flush all buffers
        streamer.flush_all()
        
        time.sleep(2)
        
        logger.info("TTS streamer test completed")
        
    except Exception as e:
        logger.error(f"TTS streamer test failed: {e}")

def test_integration_with_real_config():
    """Test integration with real organization configuration"""
    logger.info("Testing integration with real org config...")
    
    try:
        # Try to load a real config (you'll need to provide a valid config ID)
        config_id = os.getenv("TEST_ORG_CONFIG_ID")
        if not config_id:
            logger.warning("No TEST_ORG_CONFIG_ID environment variable set, skipping real config test")
            return
        
        org_config = load_org_config(config_id)
        if not org_config:
            logger.error(f"Could not load org config for ID: {config_id}")
            return
        
        logger.info(f"Loaded org config: {org_config.displayName}")
        
        def audio_callback(text: str, language: str, audio_data: bytes):
            logger.info(f"Real TTS Audio - Text: '{text[:50]}...', Language: {language}, Size: {len(audio_data)} bytes")
        
        streamer = TTSStreamer(org_config, chunk_callback=audio_callback)
        
        # Test with real configuration
        test_language = org_config.defaultPrimaryLanguage
        logger.info(f"Testing with default language: {test_language}")
        
        streamer.add_text_chunk("This is a test", test_language)
        streamer.add_text_chunk(" of the real", test_language)
        streamer.add_text_chunk(" TTS integration", test_language)
        streamer.add_text_chunk(" with actual", test_language)
        streamer.add_text_chunk(" Azure configuration.", test_language)
        
        # Wait for processing
        time.sleep(5)
        
        streamer.flush_all()
        time.sleep(3)
        
        logger.info("Real config integration test completed")
        
    except Exception as e:
        logger.error(f"Real config integration test failed: {e}")

def main():
    """Run all TTS tests"""
    logger.info("Starting TTS integration tests...")
    
    print("\n" + "="*60)
    print("TTS INTEGRATION TEST SUITE")
    print("="*60)
    
    # Test 1: TTS Buffer
    print("\n1. Testing TTS Buffer...")
    test_tts_buffer()
    
    # Test 2: TTS Streamer
    print("\n2. Testing TTS Streamer...")
    test_tts_streamer()
    
    # Test 3: Real Config Integration (optional)
    print("\n3. Testing Real Config Integration...")
    test_integration_with_real_config()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
    
    print("\nNOTE: To test with real Azure TTS:")
    print("1. Set up a valid organization configuration with Azure TTS settings")
    print("2. Set TEST_ORG_CONFIG_ID environment variable")
    print("3. Ensure Azure credentials are properly configured")

if __name__ == "__main__":
    main()
