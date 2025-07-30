#!/usr/bin/env python3
"""
Test different audio loading approaches for ultra-fast trimming
"""
import os
import sys
import time
import logging
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_loading_approaches():
    """Test different approaches to audio loading for speed"""
    try:
        import librosa
        import soundfile as sf
        import numpy as np
        
        test_audio_path = "speech.mp3"
        if not os.path.exists(test_audio_path):
            logger.error(f"Test audio file {test_audio_path} not found")
            return False
            
        with open(test_audio_path, 'rb') as f:
            original_audio = f.read()
        
        logger.info(f"Original audio size: {len(original_audio)} bytes")
        
        # Method 1: Current approach
        logger.info("\n=== Method 1: Current librosa.load ===")
        start_time = time.time()
        
        audio_buffer = BytesIO(original_audio)
        y1, sr1 = librosa.load(audio_buffer, sr=16000, mono=True, res_type='kaiser_fast')
        
        duration1 = time.time() - start_time
        logger.info(f"Method 1 took: {duration1:.3f}s to load {len(y1)/sr1:.3f}s of audio")
        
        # Method 2: Try pydub for faster loading
        try:
            from pydub import AudioSegment
            import io
            
            logger.info("\n=== Method 2: pydub loading ===")
            start_time = time.time()
            
            audio_buffer = BytesIO(original_audio)
            audio_segment = AudioSegment.from_mp3(audio_buffer)
            
            # Convert to numpy array
            samples = audio_segment.get_array_of_samples()
            y2 = np.array(samples).astype(np.float32) / 32768.0  # Normalize to [-1, 1]
            sr2 = audio_segment.frame_rate
            
            # Convert to 16kHz if needed
            if sr2 != 16000:
                y2 = librosa.resample(y2, orig_sr=sr2, target_sr=16000)
                sr2 = 16000
            
            duration2 = time.time() - start_time
            logger.info(f"Method 2 took: {duration2:.3f}s to load {len(y2)/sr2:.3f}s of audio")
            
        except ImportError:
            logger.info("pydub not available, skipping Method 2")
            duration2 = float('inf')
        
        # Method 3: Direct soundfile approach (if input was WAV)
        logger.info("\n=== Method 3: Direct soundfile (requires WAV) ===")
        logger.info("This would be much faster for WAV input files")
        
        # Method 4: Minimal processing approach - skip complex loading
        logger.info("\n=== Method 4: Minimal processing check ===")
        start_time = time.time()
        
        # Quick check: if audio is very short, maybe skip trimming entirely
        audio_buffer = BytesIO(original_audio)
        
        # Try to get duration without full decode
        try:
            import mutagen
            from mutagen.mp3 import MP3
            
            audio_buffer.seek(0)
            mp3_info = MP3(audio_buffer)
            duration_seconds = mp3_info.info.length
            
            duration4 = time.time() - start_time
            logger.info(f"Method 4 took: {duration4:.3f}s to get duration: {duration_seconds:.3f}s")
            
            # If audio is very short (< 2 seconds), maybe skip trimming
            if duration_seconds < 2.0:
                logger.info("Audio too short, could skip trimming entirely")
                
        except ImportError:
            logger.info("mutagen not available for quick duration check")
            duration4 = float('inf')
        
        # Show results
        logger.info(f"\n=== Speed Comparison ===")
        logger.info(f"Method 1 (librosa.load): {duration1:.3f}s")
        if duration2 != float('inf'):
            logger.info(f"Method 2 (pydub): {duration2:.3f}s")
        if duration4 != float('inf'):
            logger.info(f"Method 4 (duration check): {duration4:.3f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_loading_approaches()
