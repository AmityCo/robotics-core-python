"""
Audio Helper Module
Handles audio processing operations like silence trimming and format conversion.
"""
import logging
import io
import wave
from typing import Optional

try:
    import numpy as np
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError as e:
    AUDIO_PROCESSING_AVAILABLE = False
    logging.warning(f"numpy not available. Audio trimming will be disabled. Error: {e}")

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Handles audio processing operations including silence trimming and format conversion.
    """
    
    def __init__(self, silence_threshold: float = 0.05, enable_trimming: bool = True):
        """
        Initialize audio processor
        
        Args:
            silence_threshold: Energy threshold for silence detection (0.05 = 5% of max energy)
            enable_trimming: Whether to enable audio trimming (can be disabled for speed)
        """
        self.silence_threshold = silence_threshold
        self.enable_trimming = enable_trimming
    
    def trim_silence(self, audio_data: bytes) -> bytes:
        """
        Trim silence from the beginning and end of audio data
        Ultra-fast implementation for raw PCM data
        
        Args:
            audio_data: Raw PCM audio data as bytes (16-bit, 16kHz, mono)
            
        Returns:
            Trimmed audio data as bytes
        """
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.warning("Audio processing libraries not available. Returning original audio.")
            return audio_data
            
        if not self.enable_trimming:
            logger.debug("Audio trimming disabled, returning original audio.")
            return audio_data
            
        try:
            # Quick optimization: if audio is very small, likely very short, skip trimming
            if len(audio_data) < 8000:  # Less than 0.25 seconds at 16kHz 16-bit (~8KB)
                logger.debug("Audio data very small, skipping trimming for speed")
                return audio_data
            
            # Convert raw PCM bytes directly to numpy array (much faster than librosa.load!)
            # Raw PCM is 16-bit signed integers, little-endian
            y = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0  # Normalize to [-1, 1]
            sr = 16000  # We know it's 16kHz from the format
            
            if len(y) == 0:
                logger.warning("Empty audio data, returning original")
                return audio_data
            
            # Use smaller frame size for more precise trimming
            frame_length = 512  # Smaller frames for better precision (~32ms at 16kHz)
            
            # Calculate RMS energy for each frame (vectorized for speed)
            frames = len(y) // frame_length
            if frames > 0:
                y_frames = y[:frames * frame_length].reshape(-1, frame_length)
                energy = np.sqrt(np.mean(y_frames**2, axis=1))
                
                # Set threshold - make it more sensitive for better trimming
                threshold = np.max(energy) * self.silence_threshold
                
                # Find first and last frames above threshold
                above_threshold = energy > threshold
                if np.any(above_threshold):
                    start_frame = np.argmax(above_threshold)
                    end_frame = len(above_threshold) - np.argmax(above_threshold[::-1]) - 1
                    
                    # Convert frame indices to sample indices with minimal padding
                    start_sample = start_frame * frame_length
                    end_sample = min((end_frame + 1) * frame_length, len(y))
                    
                    # For very precise trimming, do sample-level detection around the frame boundaries
                    # Look backwards from start_sample to find exact start (more aggressive)
                    search_start = max(0, start_sample - frame_length)
                    for i in range(start_sample, search_start - 1, -1):
                        if abs(y[i]) > threshold * 0.3:  # Use even lower threshold for more aggressive detection
                            start_sample = max(0, i - int(0.002 * sr))  # Keep only 2ms padding
                            break
                    
                    # Look forwards from end_sample to find exact end (more aggressive)
                    search_end = min(len(y), end_sample + frame_length)
                    for i in range(end_sample, search_end):
                        if i < len(y) and abs(y[i]) > threshold * 0.3:
                            end_sample = min(len(y), i + int(0.002 * sr))  # Keep only 2ms padding
                    
                    y_trimmed = y[start_sample:end_sample]
                    
                    # Trim excessive mid-audio silence (more than 300ms -> reduce to 50ms)
                    y_trimmed = self._trim_mid_silence(y_trimmed, sr, threshold)
                else:
                    # If no energy detected above threshold, keep original
                    logger.debug("No audio energy detected above threshold, keeping original")
                    y_trimmed = y
                    # Still trim mid-silence even if no clear speech boundaries found
                    y_trimmed = self._trim_mid_silence(y_trimmed, sr, threshold)
            else:
                # For very short audio, do sample-level detection
                threshold = np.max(np.abs(y)) * self.silence_threshold
                
                # Find first non-silent sample (more aggressive)
                start_sample = 0
                for i in range(len(y)):
                    if abs(y[i]) > threshold:
                        start_sample = max(0, i - int(0.001 * sr))  # Keep only 1ms padding
                        break
                
                # Find last non-silent sample (more aggressive)
                end_sample = len(y)
                for i in range(len(y) - 1, -1, -1):
                    if abs(y[i]) > threshold:
                        end_sample = min(len(y), i + int(0.001 * sr))  # Keep only 1ms padding
                        break
                
                y_trimmed = y[start_sample:end_sample]
            
            # Trim excessive mid-audio silence (more than 300ms -> reduce to 50ms)
            y_trimmed = self._trim_mid_silence(y_trimmed, sr, threshold)
            
            # Convert back to raw PCM bytes (will be converted to WAV later)
            y_trimmed_int = (y_trimmed * 32767).astype(np.int16)
            trimmed_data = y_trimmed_int.tobytes()
            
            # Log trimming statistics
            original_duration = len(y) / sr
            trimmed_duration = len(y_trimmed) / sr
            trim_amount = original_duration - trimmed_duration
            
            logger.info(f"Audio trimmed: {original_duration:.3f}s -> {trimmed_duration:.3f}s (removed {trim_amount:.3f}s)")
            
            return trimmed_data
            
        except Exception as e:
            logger.error(f"Error trimming audio: {str(e)}")
            logger.info("Returning original audio data")
            return audio_data
    
    def _trim_mid_silence(self, y: 'np.ndarray', sr: int, threshold: float) -> 'np.ndarray':
        """
        Trim excessive silence in the middle of audio
        Reduces silence longer than 300ms to 50ms
        
        Args:
            y: Audio data as numpy array (normalized to [-1, 1])
            sr: Sample rate
            threshold: Silence threshold
            
        Returns:
            Audio data with mid-silence trimmed
        """
        try:
            if len(y) == 0:
                return y
                
            # Define silence parameters
            max_silence_duration = 0.3  # 300ms
            target_silence_duration = 0.05  # 50ms
            max_silence_samples = int(max_silence_duration * sr)
            target_silence_samples = int(target_silence_duration * sr)
            
            # Use small frame size for precise detection
            frame_length = 256  # ~16ms at 16kHz
            frames = len(y) // frame_length
            
            if frames < 2:  # Too short to have meaningful mid-silence
                return y
            
            # Calculate energy for each frame
            y_frames = y[:frames * frame_length].reshape(-1, frame_length)
            energy = np.sqrt(np.mean(y_frames**2, axis=1))
            
            # Identify silent frames
            silent_frames = energy <= threshold
            
            # Find continuous silent regions
            silent_regions = []
            start_silent = None
            
            for i, is_silent in enumerate(silent_frames):
                if is_silent and start_silent is None:
                    start_silent = i
                elif not is_silent and start_silent is not None:
                    silent_regions.append((start_silent, i - 1))
                    start_silent = None
            
            # Handle case where audio ends with silence
            if start_silent is not None:
                silent_regions.append((start_silent, len(silent_frames) - 1))
            
            # Process each silent region
            if not silent_regions:
                return y
            
            # Build new audio by processing each segment
            new_audio_segments = []
            last_end = 0
            
            for start_frame, end_frame in silent_regions:
                # Convert frame indices to sample indices
                start_sample = start_frame * frame_length
                end_sample = min((end_frame + 1) * frame_length, len(y))
                
                # Add audio before this silent region
                if start_sample > last_end:
                    new_audio_segments.append(y[last_end:start_sample])
                
                # Check if this silent region is long enough to trim
                silence_duration_samples = end_sample - start_sample
                if silence_duration_samples > max_silence_samples:
                    # Replace with shorter silence
                    silence_replacement = np.zeros(target_silence_samples, dtype=y.dtype)
                    new_audio_segments.append(silence_replacement)
                    logger.debug(f"Trimmed mid-silence: {silence_duration_samples / sr:.3f}s -> {target_silence_duration:.3f}s")
                else:
                    # Keep original silence if it's not too long
                    new_audio_segments.append(y[start_sample:end_sample])
                
                last_end = end_sample
            
            # Add remaining audio after the last silent region
            if last_end < len(y):
                new_audio_segments.append(y[last_end:])
            
            # Concatenate all segments
            if new_audio_segments:
                result = np.concatenate(new_audio_segments)
                return result
            else:
                return y
                
        except Exception as e:
            logger.error(f"Error trimming mid-silence: {str(e)}")
            return y
    
    def convert_pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
        """
        Convert raw PCM audio data to WAV format
        
        Args:
            pcm_data: Raw PCM audio data as bytes (16-bit, signed)
            sample_rate: Sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            sample_width: Sample width in bytes (default: 2 for 16-bit)
            
        Returns:
            WAV formatted audio data as bytes
        """
        try:
            # Create a BytesIO buffer to write WAV data
            wav_buffer = io.BytesIO()
            
            # Create WAV file in memory
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)
            
            # Get the WAV data
            wav_data = wav_buffer.getvalue()
            wav_buffer.close()
            
            logger.debug(f"Converted PCM to WAV: {len(pcm_data)} bytes -> {len(wav_data)} bytes")
            return wav_data
            
        except Exception as e:
            logger.error(f"Error converting PCM to WAV: {str(e)}")
            logger.info("Returning original PCM data")
            return pcm_data

# Create a default instance for convenience
default_audio_processor = AudioProcessor()

# Convenience functions for backward compatibility
def trim_silence(audio_data: bytes, silence_threshold: float = 0.05, enable_trimming: bool = True) -> bytes:
    """
    Convenience function to trim silence using default processor
    """
    processor = AudioProcessor(silence_threshold=silence_threshold, enable_trimming=enable_trimming)
    return processor.trim_silence(audio_data)

def convert_pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Convenience function to convert PCM to WAV using default processor
    """
    return default_audio_processor.convert_pcm_to_wav(pcm_data, sample_rate, channels, sample_width)
