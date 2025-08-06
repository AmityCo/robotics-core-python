#!/usr/bin/env python3
"""
Test script for the audio trimming API endpoint.
Tests the /api/v1/audio/trim endpoint with sample audio data.
"""

import requests
import base64
import json
import logging
import os
import sys
import tempfile
import wave
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_wav_file_with_silence(filename, duration_seconds=2.0, sample_rate=16000):
    """
    Create a test WAV file with silence at beginning and end
    
    Args:
        filename: Path to save the WAV file
        duration_seconds: Total duration of audio
        sample_rate: Sample rate in Hz
        
    Returns:
        Path to the created WAV file
    """
    total_samples = int(duration_seconds * sample_rate)
    
    # Create audio with silence at start (0.4s), speech in middle (1.2s), silence at end (0.4s)
    silence_samples = int(0.4 * sample_rate)
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
    
    # Convert to 16-bit PCM
    audio_int16 = (audio_signal * 32767).astype(np.int16)
    
    # Write to WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)      # Mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)  # 16kHz
        wav_file.writeframes(audio_int16.tobytes())
    
    logger.info(f"Created test WAV file: {filename} ({duration_seconds}s, {len(audio_int16)} samples)")
    return filename


def test_audio_trim_api_local_file():
    """Test the audio trimming API with a local file served via simple HTTP server"""
    
    # Base URL for the API (adjust if running on different host/port)
    api_base_url = "http://localhost:8000"
    
    try:
        # Create a temporary WAV file with silence
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            test_wav_path = temp_file.name
        
        create_test_wav_file_with_silence(test_wav_path, duration_seconds=2.0)
        
        # For this test, we'll need to host the file somewhere accessible
        # For now, let's test with a publicly accessible audio URL
        # You can replace this with your own test audio URL
        test_audio_url = "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
        
        logger.info(f"Testing audio trimming API with URL: {test_audio_url}")
        
        # Prepare the request
        request_data = {
            "audio_url": test_audio_url,
            "silence_threshold": 0.05
        }
        
        # Make the API request
        response = requests.post(
            f"{api_base_url}/api/v1/audio/trim",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info("✓ Audio trimming API test successful!")
            logger.info(f"  Status: {result['status']}")
            logger.info(f"  Original size: {result['original_size_bytes']} bytes")
            logger.info(f"  Trimmed size: {result['trimmed_size_bytes']} bytes")
            logger.info(f"  Size reduction: {result['size_reduction_bytes']} bytes ({result['size_reduction_percent']:.1f}%)")
            logger.info(f"  Audio format: {result['audio_format']}")
            logger.info(f"  Base64 audio length: {len(result['trimmed_audio_base64'])} characters")
            
            # Optionally save the trimmed audio
            try:
                trimmed_audio_data = base64.b64decode(result['trimmed_audio_base64'])
                with tempfile.NamedTemporaryFile(suffix='_trimmed.wav', delete=False) as output_file:
                    output_file.write(trimmed_audio_data)
                    logger.info(f"  Saved trimmed audio to: {output_file.name}")
            except Exception as e:
                logger.warning(f"  Could not save trimmed audio: {str(e)}")
            
            return True
        else:
            logger.error(f"❌ API request failed with status {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Could not connect to API server. Make sure the server is running on http://localhost:8000")
        logger.info("  Start the server with: python main.py")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {str(e)}")
        return False
    finally:
        # Clean up temporary file
        try:
            if 'test_wav_path' in locals():
                os.unlink(test_wav_path)
        except:
            pass


def test_with_custom_url():
    """Test with a custom audio URL provided by user"""
    print("\n" + "="*50)
    print("CUSTOM AUDIO URL TEST")
    print("="*50)
    
    audio_url = input("Enter an audio URL to test (or press Enter to skip): ").strip()
    
    if not audio_url:
        logger.info("Skipping custom URL test")
        return True
    
    api_base_url = "http://localhost:8000"
    
    try:
        logger.info(f"Testing with custom URL: {audio_url}")
        
        request_data = {
            "audio_url": audio_url,
            "silence_threshold": 0.05
        }
        
        response = requests.post(
            f"{api_base_url}/api/v1/audio/trim",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✓ Custom URL test successful!")
            logger.info(f"  Original size: {result['original_size_bytes']} bytes")
            logger.info(f"  Trimmed size: {result['trimmed_size_bytes']} bytes")
            logger.info(f"  Reduction: {result['size_reduction_percent']:.1f}%")
            return True
        else:
            logger.error(f"❌ Custom URL test failed: {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Custom URL test failed: {str(e)}")
        return False


def main():
    """Run the audio trimming API tests"""
    logger.info("Starting audio trimming API tests")
    
    print("🎵 Audio Trimming API Test Suite")
    print("=" * 40)
    
    # Test with a known working audio URL
    success = test_audio_trim_api_local_file()
    
    if success:
        # Offer to test with custom URL
        test_with_custom_url()
    
    if success:
        print("\n🎉 Audio trimming API tests completed successfully!")
        print("\nAPI Usage Example:")
        print("POST /api/v1/audio/trim")
        print("Content-Type: application/json")
        print(json.dumps({
            "audio_url": "https://example.com/audio.wav",
            "silence_threshold": 0.05
        }, indent=2))
    else:
        print("\n❌ Some tests failed. Please check the server is running and try again.")


if __name__ == "__main__":
    main()
