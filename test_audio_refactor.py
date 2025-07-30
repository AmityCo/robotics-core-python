#!/usr/bin/env python3
"""
Test script to verify the refactored audio processing functionality
"""
import numpy as np
from src.audio_helper import AudioProcessor

def test_audio_processor():
    """Test the AudioProcessor functionality"""
    print("Testing AudioProcessor with aggressive trimming and mid-silence detection...")
    
    # Create a sample audio processor
    processor = AudioProcessor(silence_threshold=0.01, enable_trimming=True)
    
    # Create some fake PCM audio data (16-bit, 16kHz, mono)
    sample_rate = 16000
    
    # Test 1: Basic trimming with more aggressive settings
    print("\n=== Test 1: Aggressive Start/End Trimming ===")
    duration = 2.0  # 2 seconds
    samples = int(sample_rate * duration)
    
    # Create audio with significant silence padding
    silence_samples = int(0.2 * sample_rate)  # 200ms of silence
    audio_samples = samples - 2 * silence_samples
    
    # Generate a simple tone in the middle
    t = np.linspace(0, audio_samples / sample_rate, audio_samples)
    tone = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)  # 440Hz tone
    
    # Add silence padding
    silence = np.zeros(silence_samples, dtype=np.int16)
    full_audio = np.concatenate([silence, tone, silence])
    
    # Convert to bytes
    audio_bytes = full_audio.tobytes()
    
    print(f"Original audio: {len(audio_bytes)} bytes ({len(full_audio) / sample_rate:.3f}s)")
    
    # Test trimming
    trimmed_bytes = processor.trim_silence(audio_bytes)
    print(f"Trimmed audio: {len(trimmed_bytes)} bytes")
    
    # Test 2: Mid-silence detection and trimming
    print("\n=== Test 2: Mid-Silence Detection ===")
    
    # Create audio with long pause in middle
    tone1_duration = 0.5  # 500ms
    silence_duration = 0.4  # 400ms (should be trimmed to 50ms)
    tone2_duration = 0.5  # 500ms
    
    tone1_samples = int(tone1_duration * sample_rate)
    silence_samples_mid = int(silence_duration * sample_rate)
    tone2_samples = int(tone2_duration * sample_rate)
    
    # Generate tones and silence
    t1 = np.linspace(0, tone1_duration, tone1_samples)
    tone1 = (np.sin(2 * np.pi * 440 * t1) * 16000).astype(np.int16)
    
    mid_silence = np.zeros(silence_samples_mid, dtype=np.int16)
    
    t2 = np.linspace(0, tone2_duration, tone2_samples)
    tone2 = (np.sin(2 * np.pi * 880 * t2) * 16000).astype(np.int16)  # 880Hz tone
    
    # Combine with small start/end silence
    start_silence = np.zeros(int(0.05 * sample_rate), dtype=np.int16)  # 50ms
    end_silence = np.zeros(int(0.05 * sample_rate), dtype=np.int16)  # 50ms
    
    audio_with_mid_silence = np.concatenate([start_silence, tone1, mid_silence, tone2, end_silence])
    mid_silence_bytes = audio_with_mid_silence.tobytes()
    
    print(f"Audio with mid-silence: {len(mid_silence_bytes)} bytes ({len(audio_with_mid_silence) / sample_rate:.3f}s)")
    
    # Test trimming with mid-silence detection
    trimmed_mid_bytes = processor.trim_silence(mid_silence_bytes)
    trimmed_samples = len(trimmed_mid_bytes) // 2  # 16-bit = 2 bytes per sample
    print(f"After trimming: {len(trimmed_mid_bytes)} bytes ({trimmed_samples / sample_rate:.3f}s)")
    
    # Expected: should be around 1.1s (0.5s + 0.05s + 0.5s + minimal padding)
    expected_duration = tone1_duration + 0.05 + tone2_duration  # ~1.05s
    actual_duration = trimmed_samples / sample_rate
    print(f"Expected duration: ~{expected_duration:.3f}s, Actual: {actual_duration:.3f}s")
    
    # Test WAV conversion
    print("\n=== Test 3: WAV Conversion ===")
    wav_bytes = processor.convert_pcm_to_wav(trimmed_mid_bytes)
    print(f"WAV audio: {len(wav_bytes)} bytes")
    
    print("\nAudioProcessor aggressive trimming test completed successfully!")

if __name__ == "__main__":
    test_audio_processor()
