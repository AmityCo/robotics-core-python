#!/usr/bin/env python3
"""
Fast audio trimming test - comparing different approaches for speed
"""
import os
import sys
import logging
import time
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fast_trimming():
    """Test different approaches to audio trimming for speed comparison"""
    try:
        import librosa
        import soundfile as sf
        import numpy as np
        
        logger.info("Testing fast audio trimming approaches...")
        
        # Test with the sample audio file if it exists
        test_audio_path = "speech.mp3"
        if not os.path.exists(test_audio_path):
            logger.error(f"Test audio file {test_audio_path} not found")
            return False
            
        with open(test_audio_path, 'rb') as f:
            original_audio = f.read()
        
        logger.info(f"Original audio size: {len(original_audio)} bytes")
        
        # Method 1: Optimized librosa approach
        logger.info("\n=== Method 1: Optimized librosa ===")
        start_time = time.time()
        
        audio_buffer = BytesIO(original_audio)
        y, sr = librosa.load(audio_buffer, sr=16000, mono=True, res_type='kaiser_fast')
        
        # Fast trimming with larger frames
        y_trimmed, _ = librosa.effects.trim(
            y, 
            top_db=20,
            frame_length=4096,
            hop_length=1024
        )
        
        output_buffer = BytesIO()
        sf.write(output_buffer, y_trimmed, sr, format='WAV', subtype='PCM_16')
        trimmed_data1 = output_buffer.getvalue()
        
        duration1 = time.time() - start_time
        logger.info(f"Method 1 took: {duration1:.3f}s")
        logger.info(f"Audio: {len(y)/sr:.3f}s -> {len(y_trimmed)/sr:.3f}s")
        
        # Method 2: Simple energy-based trimming (much faster)
        logger.info("\n=== Method 2: Simple energy-based ===")
        start_time = time.time()
        
        audio_buffer = BytesIO(original_audio)
        y2, sr2 = librosa.load(audio_buffer, sr=16000, mono=True, res_type='kaiser_fast')
        
        # Simple energy-based trimming - much faster
        # Calculate RMS energy in chunks
        frame_length = 2048
        energy = []
        for i in range(0, len(y2), frame_length):
            frame = y2[i:i+frame_length]
            rms = np.sqrt(np.mean(frame**2))
            energy.append(rms)
        
        energy = np.array(energy)
        
        # Find start and end based on energy threshold
        threshold = np.max(energy) * 0.01  # 1% of max energy
        
        # Find first and last frames above threshold
        above_threshold = energy > threshold
        if np.any(above_threshold):
            start_frame = np.argmax(above_threshold)
            end_frame = len(above_threshold) - np.argmax(above_threshold[::-1]) - 1
            
            start_sample = start_frame * frame_length
            end_sample = min((end_frame + 1) * frame_length, len(y2))
            
            y2_trimmed = y2[start_sample:end_sample]
        else:
            y2_trimmed = y2  # If no energy detected, keep original
        
        output_buffer2 = BytesIO()
        sf.write(output_buffer2, y2_trimmed, sr2, format='WAV', subtype='PCM_16')
        trimmed_data2 = output_buffer2.getvalue()
        
        duration2 = time.time() - start_time
        logger.info(f"Method 2 took: {duration2:.3f}s")
        logger.info(f"Audio: {len(y2)/sr2:.3f}s -> {len(y2_trimmed)/sr2:.3f}s")
        
        # Method 3: Ultra-fast simple approach
        logger.info("\n=== Method 3: Ultra-fast simple ===")
        start_time = time.time()
        
        audio_buffer = BytesIO(original_audio)
        y3, sr3 = librosa.load(audio_buffer, sr=16000, mono=True, res_type='kaiser_fast')
        
        # Ultra-simple: just remove samples below a certain absolute threshold
        # This is much faster but less sophisticated
        abs_threshold = 0.001  # Adjust based on your needs
        
        # Find first and last non-silent samples
        non_silent = np.abs(y3) > abs_threshold
        if np.any(non_silent):
            start_idx = np.argmax(non_silent)
            end_idx = len(non_silent) - np.argmax(non_silent[::-1]) - 1
            y3_trimmed = y3[start_idx:end_idx+1]
        else:
            y3_trimmed = y3
        
        output_buffer3 = BytesIO()
        sf.write(output_buffer3, y3_trimmed, sr3, format='WAV', subtype='PCM_16')
        trimmed_data3 = output_buffer3.getvalue()
        
        duration3 = time.time() - start_time
        logger.info(f"Method 3 took: {duration3:.3f}s")
        logger.info(f"Audio: {len(y3)/sr3:.3f}s -> {len(y3_trimmed)/sr3:.3f}s")
        
        # Save all results for comparison
        with open("trimmed_method1_optimized.wav", 'wb') as f:
            f.write(trimmed_data1)
        with open("trimmed_method2_energy.wav", 'wb') as f:
            f.write(trimmed_data2)
        with open("trimmed_method3_simple.wav", 'wb') as f:
            f.write(trimmed_data3)
        
        logger.info(f"\n=== Speed Comparison ===")
        logger.info(f"Method 1 (optimized librosa): {duration1:.3f}s")
        logger.info(f"Method 2 (energy-based): {duration2:.3f}s")
        logger.info(f"Method 3 (simple threshold): {duration3:.3f}s")
        
        fastest = min(duration1, duration2, duration3)
        logger.info(f"Fastest method: {fastest:.3f}s")
        
        if duration2 == fastest:
            logger.info("✅ Energy-based method is fastest - recommend using this")
        elif duration3 == fastest:
            logger.info("✅ Simple threshold method is fastest - recommend using this")
        else:
            logger.info("✅ Optimized librosa method is fastest")
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_fast_trimming()
    
    if success:
        logger.info("✅ Fast trimming test completed successfully")
    else:
        logger.error("❌ Fast trimming test failed")
        sys.exit(1)
