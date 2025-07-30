# Audio Trimming Feature

## Overview

The TTS Handler now includes automatic audio trimming functionality to remove silence from the beginning and end of generated speech audio. This addresses the issue where Azure TTS API responses typically include approximately 0.15 seconds of silence at the beginning and end of the audio.

## Implementation Details

### Libraries Used
- **librosa**: For audio processing and silence detection
- **soundfile**: For audio format conversion and I/O operations
- **numpy**: For audio data manipulation

### Key Features

1. **Automatic Silence Trimming**: Removes silence from both beginning and end of audio
2. **Graceful Degradation**: If audio processing libraries are not available, the system falls back to returning original audio
3. **Optimal Threshold**: Uses a 25dB threshold for effective silence detection without over-trimming
4. **Format Consistency**: Maintains 16kHz sample rate to match Azure TTS output
5. **Error Handling**: Comprehensive error handling with fallback to original audio on failures

### Changes Made

#### Requirements Updates
Added new dependencies to `requirements.txt`:
```
librosa==0.10.1
soundfile==0.12.1
```

#### TTS Handler Modifications
1. **New Import Handling**: Added conditional imports with graceful fallback
2. **New Method**: `_trim_silence()` method for audio processing
3. **Integration**: Modified `generate_speech()` to automatically trim audio before caching/returning
4. **Cache Format**: Changed cached audio format from `.mp3` to `.wav` to avoid format conversion complexity

### Performance Impact

- **Duration Reduction**: Typically removes 0.2-1.2 seconds of silence per audio clip
- **Processing Time**: Adds ~2-6 seconds of processing time per audio generation
- **Storage**: WAV format is larger than MP3 but trimming reduces overall duration
- **Caching**: Cached audio is trimmed, so subsequent requests benefit from both speed and shorter duration

### Error Handling

The system includes multiple levels of error handling:
1. **Import Errors**: Falls back to original audio if libraries unavailable
2. **Processing Errors**: Returns original audio if trimming fails
3. **Empty Audio**: Validates audio data before and after processing
4. **Logging**: Comprehensive logging for monitoring and debugging

### Usage

The trimming functionality is automatically applied to all TTS generation requests. No changes are required to existing API calls.

### Testing

Use the test scripts to verify functionality:
```bash
# Test basic audio trimming
python test_audio_trimming_simple.py

# Test integrated TTS handler with trimming
python test_audio_trimming.py
```

### Configuration

The trimming behavior can be adjusted by modifying these parameters in the `_trim_silence()` method:
- `top_db=25`: Silence threshold (lower = more aggressive trimming)
- `frame_length=2048`: Analysis window size
- `hop_length=512`: Analysis step size

### Production Deployment

For Azure App Service deployment:
1. Ensure all dependencies are listed in `requirements.txt`
2. The system gracefully degrades if audio libraries fail to install
3. Consider the additional processing time in timeout configurations
4. Monitor logs for trimming statistics and error rates
