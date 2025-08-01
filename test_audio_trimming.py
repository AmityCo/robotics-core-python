#!/usr/bin/env python3
"""
Test script for audio trimming functionality in answer flow SSE.
Tests the auto_trim_silent feature with organization configuration.
"""

import asyncio
import base64
import logging
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.org_config import OrgConfigData, AudioConfig, AudioThreshold
from src.answer_flow_sse import trim_audio_if_enabled
from src.audio_helper import AudioProcessor
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_audio_data(duration_seconds=2.0, sample_rate=16000, with_silence=True):
    """
    Create test audio data with silence at beginning and end
    
    Args:
        duration_seconds: Total duration of audio
        sample_rate: Sample rate in Hz
        with_silence: Whether to add silence at beginning and end
        
    Returns:
        Raw PCM audio data as bytes
    """
    total_samples = int(duration_seconds * sample_rate)
    
    if with_silence:
        # Create audio with silence at start (0.3s), speech in middle (1.4s), silence at end (0.3s)
        silence_samples = int(0.3 * sample_rate)
        speech_samples = total_samples - (2 * silence_samples)
        
        # Generate test tone for speech part (440 Hz sine wave)
        t = np.linspace(0, speech_samples / sample_rate, speech_samples)
        speech_signal = 0.3 * np.sin(2 * np.pi * 440 * t)  # 30% volume
        
        # Combine: silence + speech + silence
        audio_signal = np.concatenate([
            np.zeros(silence_samples),  # Start silence
            speech_signal,             # Speech in middle
            np.zeros(silence_samples)   # End silence
        ])
    else:
        # Create continuous speech without silence
        t = np.linspace(0, duration_seconds, total_samples)
        audio_signal = 0.3 * np.sin(2 * np.pi * 440 * t)  # 30% volume
    
    # Convert to 16-bit PCM
    audio_int16 = (audio_signal * 32767).astype(np.int16)
    return audio_int16.tobytes()


def create_mock_org_config(auto_trim_enabled=True):
    """
    Create a mock organization configuration for testing
    
    Args:
        auto_trim_enabled: Whether to enable auto trimming
        
    Returns:
        Mock OrgConfigData object
    """
    # Create mock audio config
    audio_thresholds = [
        AudioThreshold(threadshold=100, multiier=2, direction="up")
    ]
    
    audio_config = AudioConfig(
        multiplierThreadsholds=audio_thresholds,
        auto_trim_silent=auto_trim_enabled
    )
    
    # Create a minimal mock org config with just the audio field
    class MockOrgConfig:
        def __init__(self, audio_config):
            self.audio = audio_config
            self.displayName = "Test Organization"
            self.kmId = "test_km_id"
    
    return MockOrgConfig(audio_config)


def test_audio_trimming_enabled():
    """Test audio trimming when auto_trim_silent is enabled"""
    logger.info("Testing audio trimming with auto_trim_silent=True")
    
    # Create test audio with silence
    audio_data = create_test_audio_data(duration_seconds=2.0, with_silence=True)
    base64_audio = base64.b64encode(audio_data).decode('utf-8')
    
    # Create org config with trimming enabled
    org_config = create_mock_org_config(auto_trim_enabled=True)
    
    # Test trimming
    trimmed_base64_audio = trim_audio_if_enabled(org_config, base64_audio)
    
    # Decode and compare
    original_data = base64.b64decode(base64_audio)
    trimmed_data = base64.b64decode(trimmed_base64_audio)
    
    logger.info(f"Original audio size: {len(original_data)} bytes")
    logger.info(f"Trimmed audio size: {len(trimmed_data)} bytes")
    
    # Trimmed audio should be smaller than original
    assert len(trimmed_data) < len(original_data), "Trimmed audio should be smaller than original"
    
    # Calculate reduction
    reduction_percent = ((len(original_data) - len(trimmed_data)) / len(original_data)) * 100
    logger.info(f"Size reduction: {reduction_percent:.1f}%")
    
    logger.info("✓ Audio trimming enabled test passed")


def test_audio_trimming_disabled():
    """Test audio trimming when auto_trim_silent is disabled"""
    logger.info("Testing audio trimming with auto_trim_silent=False")
    
    # Create test audio with silence
    audio_data = create_test_audio_data(duration_seconds=2.0, with_silence=True)
    base64_audio = base64.b64encode(audio_data).decode('utf-8')
    
    # Create org config with trimming disabled
    org_config = create_mock_org_config(auto_trim_enabled=False)
    
    # Test trimming
    result_base64_audio = trim_audio_if_enabled(org_config, base64_audio)
    
    # Should return the same audio
    assert result_base64_audio == base64_audio, "Audio should be unchanged when trimming is disabled"
    
    logger.info("✓ Audio trimming disabled test passed")


def test_no_audio_data():
    """Test trimming with None audio data"""
    logger.info("Testing audio trimming with None audio data")
    
    # Create org config with trimming enabled
    org_config = create_mock_org_config(auto_trim_enabled=True)
    
    # Test with None audio
    result = trim_audio_if_enabled(org_config, None)
    
    # Should return None
    assert result is None, "Should return None when input is None"
    
    logger.info("✓ No audio data test passed")


def test_audio_processor_directly():
    """Test the AudioProcessor directly to verify it's working"""
    logger.info("Testing AudioProcessor directly")
    
    # Create test audio with silence
    audio_data = create_test_audio_data(duration_seconds=1.0, with_silence=True)
    
    # Create audio processor
    processor = AudioProcessor(silence_threshold=0.05, enable_trimming=True)
    
    # Trim silence
    trimmed_data = processor.trim_silence(audio_data)
    
    logger.info(f"Original audio size: {len(audio_data)} bytes")
    logger.info(f"Trimmed audio size: {len(trimmed_data)} bytes")
    
    # Trimmed should be smaller
    assert len(trimmed_data) < len(audio_data), "AudioProcessor should trim audio"
    
    logger.info("✓ AudioProcessor direct test passed")


def main():
    """Run all tests"""
    logger.info("Starting audio trimming tests")
    
    try:
        test_no_audio_data()
        test_audio_trimming_disabled()
        test_audio_processor_directly()
        test_audio_trimming_enabled()
        
        logger.info("🎉 All tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
