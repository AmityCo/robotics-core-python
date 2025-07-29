# Validation Request Logging

This feature automatically logs all requests made to the `/api/v1/gemini/validate` endpoint for debugging and analysis purposes.

## Configuration

The logging behavior can be controlled via environment variables:

- `ARC2_LOG_VALIDATION`: Enable/disable validation logging (default: "true")
- `ARC2_VALIDATION_LOG_DIR`: Directory to store validation logs (default: "validation_logs")

## Log Structure

When a validation request is made, the system creates two files:

### 1. Audio File
- **Filename**: `audio_YYYYMMDD_HHMMSS_mmm.wav`
- **Content**: The decoded base64 audio data from the request
- **Format**: WAV audio file

### 2. Request Data File
- **Filename**: `request_YYYYMMDD_HHMMSS_mmm.json`
- **Content**: JSON file containing:
  - Timestamp
  - Request data (transcript, language, prompts, model, etc.)
  - Response data (or error information)
  - Audio file reference
  - Audio size in bytes

## Example Log Entry

```json
{
  "timestamp": "2025-07-08T12:34:56.789",
  "request_data": {
    "transcript": "Hello world",
    "language": "en",
    "system_prompt": "You are a helpful assistant...",
    "user_prompt": "Please validate this audio...",
    "model": "gemini-1.5-pro",
    "generation_config": {...},
    "audio_file": "audio_20250708_123456_789.wav",
    "audio_size_bytes": 48000
  },
  "response_data": {
    "correction": "Hello, world!",
    "search_terms": ["greeting", "world"]
  }
}
```

## Security Considerations

- The `validation_logs/` directory is added to `.gitignore` to prevent committing sensitive data
- Audio files may contain private conversations
- API keys are excluded from the logged data
- Consider implementing log rotation for production use
- Ensure proper file permissions on the log directory

## Disabling Logging

To disable logging, set the environment variable:
```bash
export ARC2_LOG_VALIDATION=false
```

Or modify the `config.py` file directly.
