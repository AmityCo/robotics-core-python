# Audio Trimming API

This document describes the new audio trimming API endpoint that automatically removes silence from audio files.

## Endpoint

`POST /api/v1/audio/trim`

## Description

Downloads audio from a provided URL and returns a trimmed version with silence removed from the beginning, middle, and end. This utilizes the same AudioHelper functionality that's integrated into the answer SSE flow when `auto_trim_silent` is enabled in the organization configuration.

## Request Format

```json
{
    "audio_url": "https://example.com/path/to/audio.wav",
    "silence_threshold": 0.05
}
```

### Parameters

- `audio_url` (required): HTTP/HTTPS URL pointing to the audio file
- `silence_threshold` (optional): Energy threshold for silence detection (default: 0.05 = 5% of max energy)

### Supported Audio Formats

- WAV files (mono, 16-bit, any sample rate)
- Raw PCM data (assumed to be 16-bit mono)

## Response Format

```json
{
    "status": "success",
    "original_size_bytes": 48000,
    "trimmed_size_bytes": 32000,
    "size_reduction_bytes": 16000,
    "size_reduction_percent": 33.33,
    "trimmed_audio_base64": "UklGRhwAAABXQVZFZm10...",
    "audio_format": "wav"
}
```

### Response Fields

- `status`: Success/error status
- `original_size_bytes`: Size of original downloaded audio in bytes
- `trimmed_size_bytes`: Size of trimmed audio in bytes
- `size_reduction_bytes`: Number of bytes removed
- `size_reduction_percent`: Percentage of audio size reduction
- `trimmed_audio_base64`: Base64 encoded trimmed audio data
- `audio_format`: Format of the returned audio ("wav" or "raw-16khz-16bit-mono-pcm")

## Usage Examples

### Python

```python
import requests
import base64

# Trim audio from URL
response = requests.post("http://localhost:8000/api/v1/audio/trim", json={
    "audio_url": "https://example.com/audio.wav",
    "silence_threshold": 0.05
})

if response.status_code == 200:
    result = response.json()
    
    # Get the trimmed audio
    trimmed_audio_data = base64.b64decode(result['trimmed_audio_base64'])
    
    # Save to file
    with open('trimmed_audio.wav', 'wb') as f:
        f.write(trimmed_audio_data)
    
    print(f"Audio trimmed: {result['size_reduction_percent']:.1f}% reduction")
else:
    print(f"Error: {response.text}")
```

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/audio/trim" \
     -H "Content-Type: application/json" \
     -d '{
       "audio_url": "https://example.com/audio.wav",
       "silence_threshold": 0.05
     }'
```

### JavaScript/Fetch

```javascript
const response = await fetch('/api/v1/audio/trim', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        audio_url: 'https://example.com/audio.wav',
        silence_threshold: 0.05
    })
});

if (response.ok) {
    const result = await response.json();
    
    // Convert base64 to blob for download
    const audioData = atob(result.trimmed_audio_base64);
    const audioArray = new Uint8Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
    }
    
    const blob = new Blob([audioArray], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    
    console.log(`Audio trimmed: ${result.size_reduction_percent}% reduction`);
} else {
    console.error('Error:', await response.text());
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid URL, unsupported audio format, etc.)
- `500`: Internal server error

Example error response:

```json
{
    "detail": "Failed to download audio: HTTP 404 Not Found"
}
```

## Integration with Answer SSE Flow

This API uses the same audio trimming functionality that's automatically applied in the answer SSE flow when the `auto_trim_silent` flag is enabled in the organization's `AudioConfig`:

```json
{
    "audio": {
        "multiplierThreadsholds": [...],
        "auto_trim_silent": true
    }
}
```

When `auto_trim_silent` is `true`, incoming audio in the `/api/v1/answer-sse` endpoint will be automatically trimmed before processing begins.

## Testing

Run the test suite to verify the API is working:

```bash
python test_audio_trim_api.py
```

This will test the endpoint with sample audio and verify the trimming functionality.
