# Keywords API Enhancement

## Overview

The `/api/v1/answer-sse` endpoint has been enhanced to support an optional `keywords` parameter that allows skipping the Gemini validation step when keywords are provided directly.

## API Changes

### Request Model Updates

The `AnswerRequest` model now includes an optional `keywords` field:

```python
class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: Optional[str] = None  # Already optional for text-only requests
    org_id: str
    config_id: str
    chat_history: List[ChatMessage] = []
    keywords: Optional[List[str]] = None  # NEW: Skip validation when provided
```

### Behavior Changes

1. **When `keywords` is provided (even if empty array):**
   - Gemini validation step is completely skipped
   - The transcript is used as-is for the "correction"
   - The provided keywords are used directly for KM search
   - Processing is faster since validation is bypassed

2. **When `keywords` is `None` or not provided:**
   - Normal flow continues with Gemini validation
   - Backward compatibility is maintained

3. **When `base64_audio` is `None`:**
   - Text-only validation is performed (if keywords not provided)
   - Audio is not sent to Gemini API

## Usage Examples

### Example 1: Skip validation with specific keywords

```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US",
  "org_id": "my-org",
  "config_id": "my-config",
  "keywords": ["weather", "forecast", "today"]
}
```

### Example 2: Skip validation with empty keywords

```json
{
  "transcript": "Hello world",
  "language": "en-US", 
  "org_id": "my-org",
  "config_id": "my-config",
  "keywords": []
}
```

### Example 3: Normal validation (backward compatible)

```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US",
  "base64_audio": "base64encodedaudio...",
  "org_id": "my-org",
  "config_id": "my-config"
}
```

### Example 4: Text-only validation (no audio)

```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US",
  "org_id": "my-org", 
  "config_id": "my-config"
}
```

## SSE Event Changes

When keywords are provided, you'll see a different status message:

```
event: status
data: {"message": "Skipping validation - using provided keywords"}

event: validation_result  
data: {"correction": "What is the weather like today?", "keywords": ["weather", "forecast", "today"]}
```

## Use Cases

1. **Pre-processed queries:** When you already know the keywords and want to skip validation for faster response
2. **Testing:** When you want to test KM search and answer generation without validation overhead
3. **Bulk processing:** When processing many similar queries where validation adds unnecessary latency
4. **Custom validation:** When you have your own validation logic and want to use this API for KM search + generation only

## Performance Benefits

- Reduces API latency by ~200-500ms per request (depending on Gemini response time)
- Reduces external API calls (no Gemini validation request)
- Allows for more predictable response times
- Reduces costs associated with Gemini API usage

## Backward Compatibility

All existing API calls will continue to work exactly as before. The `keywords` parameter is optional and defaults to `None`, which triggers the normal validation flow.
