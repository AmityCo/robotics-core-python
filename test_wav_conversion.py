#!/usr/bin/env python3
"""
Test script to verify PCM to WAV conversion functionality
"""
import sys
import os
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tts_handler import TTSHandler

def test_pcm_to_wav_conversion():
    """Test the PCM to WAV conversion functionality"""
    print("Testing PCM to WAV conversion...")
    
    # Create a test TTS handler (we don't need real Azure credentials for this test)
    tts_handler = TTSHandler("dummy_key", "southeastasia")
    
    # Create sample PCM data (1 second of 440Hz sine wave at 16kHz, 16-bit)
    sample_rate = 16000
    duration = 1.0  # 1 second
    frequency = 440  # A4 note
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    sine_wave = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM format
    pcm_data = (sine_wave * 32767).astype(np.int16).tobytes()
    
    print(f"Original PCM data size: {len(pcm_data)} bytes")
    
    # Test conversion
    wav_data = tts_handler._convert_pcm_to_wav(pcm_data, sample_rate=sample_rate)
    
    print(f"Converted WAV data size: {len(wav_data)} bytes")
    
    # Verify WAV header (should start with 'RIFF')
    if wav_data[:4] == b'RIFF':
        print("✅ WAV conversion successful - proper RIFF header found")
        
        # Check for WAV signature
        if wav_data[8:12] == b'WAVE':
            print("✅ WAV format signature found")
        else:
            print("❌ WAV format signature not found")
            
        # Save test file for verification
        with open('test_output.wav', 'wb') as f:
            f.write(wav_data)
        print("✅ Test WAV file saved as 'test_output.wav'")
        
    else:
        print("❌ WAV conversion failed - no RIFF header found")
    
    return wav_data is not None and len(wav_data) > len(pcm_data)

if __name__ == "__main__":
    success = test_pcm_to_wav_conversion()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
