#!/usr/bin/env python3
"""
Simple test script for audio trimming functionality - tests only the core trimming logic
"""
import os
import sys
import logging
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_audio_trimming_isolated():
    """Test only the audio trimming functionality without dependencies"""
    try:
        # Test the audio processing imports directly
        import librosa
        import soundfile as sf
        import numpy as np
        
        logger.info("✅ Audio processing libraries imported successfully")
        
        # Test with the sample audio file if it exists
        test_audio_path = "speech.mp3"
        if os.path.exists(test_audio_path):
            logger.info(f"Testing with existing audio file: {test_audio_path}")
            
            with open(test_audio_path, 'rb') as f:
                original_audio = f.read()
            
            logger.info(f"Original audio size: {len(original_audio)} bytes")
            
            # Test basic audio processing functionality
            audio_buffer = BytesIO(original_audio)
            
            # Load audio using librosa (this handles MP3 format)
            y, sr = librosa.load(audio_buffer, sr=None, mono=True)
            
            if len(y) == 0:
                logger.warning("Empty audio data")
                return False
            
            logger.info(f"Audio loaded: {len(y)} samples at {sr}Hz, duration: {len(y)/sr:.3f}s")
            
            # Trim silence from beginning and end
            y_trimmed, _ = librosa.effects.trim(y, top_db=25, frame_length=2048, hop_length=512)
            
            if len(y_trimmed) == 0:
                logger.warning("Audio completely trimmed")
                return False
            
            # Convert back to bytes
            output_buffer = BytesIO()
            
            # Ensure 16kHz sample rate
            if sr != 16000:
                y_trimmed = librosa.resample(y_trimmed, orig_sr=sr, target_sr=16000)
                sr = 16000
            
            # Write as WAV format
            sf.write(output_buffer, y_trimmed, sr, format='WAV', subtype='PCM_16')
            trimmed_data = output_buffer.getvalue()
            
            # Log trimming statistics
            original_duration = len(y) / (sr if sr else 16000)
            trimmed_duration = len(y_trimmed) / sr
            trim_amount = original_duration - trimmed_duration
            
            logger.info(f"Audio trimmed: {original_duration:.3f}s -> {trimmed_duration:.3f}s (removed {trim_amount:.3f}s)")
            logger.info(f"Original size: {len(original_audio)} bytes -> Trimmed size: {len(trimmed_data)} bytes")
            
            # Save trimmed version for comparison
            with open("speech_trimmed_test.wav", 'wb') as f:
                f.write(trimmed_data)
            
            logger.info("✅ Trimmed audio saved as speech_trimmed_test.wav")
            return True
        else:
            logger.warning(f"Test audio file {test_audio_path} not found")
            logger.info("Creating a simple test tone to verify trimming works...")
            
            # Generate a test tone with silence padding
            sr = 16000
            duration = 2.0  # 2 seconds
            freq = 440  # A4 note
            
            # Create a test signal with silence at beginning and end
            t = np.linspace(0, duration, int(sr * duration), False)
            tone = np.sin(freq * 2.0 * np.pi * t) * 0.3
            
            # Add 0.2 seconds of silence at beginning and end
            silence_samples = int(0.2 * sr)
            silence = np.zeros(silence_samples)
            
            full_signal = np.concatenate([silence, tone, silence])
            
            logger.info(f"Created test signal: {len(full_signal)/sr:.3f}s total")
            
            # Test trimming
            trimmed_signal, _ = librosa.effects.trim(full_signal, top_db=25)
            
            logger.info(f"Trimmed signal: {len(trimmed_signal)/sr:.3f}s (removed {(len(full_signal) - len(trimmed_signal))/sr:.3f}s)")
            
            # Save test files
            output_buffer = BytesIO()
            sf.write(output_buffer, trimmed_signal, sr, format='WAV', subtype='PCM_16')
            trimmed_data = output_buffer.getvalue()
            
            with open("test_tone_trimmed.wav", 'wb') as f:
                f.write(trimmed_data)
            
            logger.info("✅ Test tone trimming completed successfully")
            return True
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Make sure to install required dependencies: pip install librosa soundfile")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing audio trimming functionality (isolated)...")
    success = test_audio_trimming_isolated()
    
    if success:
        logger.info("✅ Audio trimming test completed successfully")
    else:
        logger.error("❌ Audio trimming test failed")
        sys.exit(1)
