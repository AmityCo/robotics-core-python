#!/usr/bin/env python3
"""
Test script for the new <break/> logic in TTS streaming
"""
import logging
from unittest.mock import Mock, MagicMock
from src.tts_stream import TTSStreamer, TTSChunk

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_break_logic():
    """Test the new <break/> detection logic"""
    
    # Create mock organization config
    mock_azure_config = Mock()
    mock_azure_config.subscriptionKey = "test_key"
    mock_azure_config.models = []
    mock_azure_config.phonemeUrl = None
    mock_azure_config.lexiconURL = None
    
    mock_tts_config = Mock()
    mock_tts_config.azure = mock_azure_config
    
    mock_org_config = Mock()
    mock_org_config.tts = mock_tts_config
    
    # Create audio callback to capture results
    processed_chunks = []
    
    def audio_callback(text, audio_data):
        processed_chunks.append(text)
        logger.info(f"Audio callback received: '{text}'")
    
    # Create TTS streamer instance
    try:
        streamer = TTSStreamer(
            org_config=mock_org_config,
            language="en-US",
            audio_callback=audio_callback,
            min_words=4
        )
        
        # Mock the _generate_speech method to avoid actual API calls
        streamer._generate_speech = Mock(return_value=b"fake_audio_data")
        
        # Test 1: Simple text with break
        logger.info("Test 1: Simple text with break")
        streamer.append_text("Hello world this is a test <break/> and this continues")
        
        # Test 2: Multiple breaks
        logger.info("Test 2: Multiple breaks")
        streamer.append_text("First sentence <break/> Second sentence <break/> Third sentence")
        
        # Test 3: Text without break (should remain in buffer)
        logger.info("Test 3: Text without break")
        streamer.append_text("This text has no break marker")
        
        # Test 4: Flush remaining text
        logger.info("Test 4: Flush remaining text")
        streamer.flush()
        
        # Print results
        logger.info(f"Total processed chunks: {len(processed_chunks)}")
        for i, chunk in enumerate(processed_chunks):
            logger.info(f"Chunk {i+1}: '{chunk}'")
            
        # Verify expected behavior
        expected_chunks = [
            "Hello world this is a test",
            "and this continues",
            "First sentence",
            "Second sentence", 
            "Third sentence",
            "This text has no break marker"
        ]
        
        success = True
        if len(processed_chunks) != len(expected_chunks):
            logger.error(f"Expected {len(expected_chunks)} chunks, got {len(processed_chunks)}")
            success = False
        else:
            for i, (actual, expected) in enumerate(zip(processed_chunks, expected_chunks)):
                if actual.strip() != expected.strip():
                    logger.error(f"Chunk {i+1} mismatch: expected '{expected}', got '{actual}'")
                    success = False
        
        if success:
            logger.info("✅ All tests passed!")
        else:
            logger.error("❌ Some tests failed!")
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_break_logic()
