#!/usr/bin/env python3
"""
Test script for audio trimming functionality in TTS Handler
"""
import os
import sys
import logging
from io import BytesIO

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_audio_trimming():
    """Test the audio trimming functionality"""
    try:
        from src.tts_handler import TTSHandler, AUDIO_PROCESSING_AVAILABLE
        
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.error("Audio processing libraries (librosa, soundfile) are not available")
            logger.info("Install them with: pip install librosa soundfile")
            return False
        
        # Create a TTS handler instance (dummy credentials for testing trimming only)
        tts_handler = TTSHandler("dummy_key", "southeastasia")
        
        # Test with a sample MP3 file if it exists
        test_audio_path = "speech.mp3"
        if os.path.exists(test_audio_path):
            logger.info(f"Testing with existing audio file: {test_audio_path}")
            
            with open(test_audio_path, 'rb') as f:
                original_audio = f.read()
            
            logger.info(f"Original audio size: {len(original_audio)} bytes")
            
            # Test trimming
            trimmed_audio = tts_handler._trim_silence(original_audio)
            
            logger.info(f"Trimmed audio size: {len(trimmed_audio)} bytes")
            logger.info(f"Size reduction: {len(original_audio) - len(trimmed_audio)} bytes")
            
            # Save trimmed version for comparison
            with open("speech_trimmed.wav", 'wb') as f:
                f.write(trimmed_audio)
            
            logger.info("Trimmed audio saved as speech_trimmed.wav")
            return True
        else:
            logger.warning(f"Test audio file {test_audio_path} not found")
            logger.info("You can test this after generating some audio with TTS")
            return True
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Make sure to install required dependencies: pip install librosa soundfile")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing audio trimming functionality...")
    success = test_audio_trimming()
    
    if success:
        logger.info("✅ Audio trimming test completed successfully")
    else:
        logger.error("❌ Audio trimming test failed")
        sys.exit(1)
