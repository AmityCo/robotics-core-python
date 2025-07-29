# Chat History Support for /answer-sse API

## Overview

The `/answer-sse` API now supports chat history, allowing clients to provide previous conversation context that will be used in both Gemini validation and OpenAI answer generation.

## Features

- **Optional chat history**: Previous conversation messages can be included in requests
- **Full backward compatibility**: Existing API calls work without any changes
- **Context-aware validation**: Gemini validation considers chat history for better transcript correction
- **Context-aware generation**: OpenAI generation uses chat history for more relevant responses

## Request Format

### With Chat History

```json
{
  "transcript": "Can you help me reset my password?",
  "language": "en",
  "base64_audio": "<base64-encoded-audio>",
  "org_id": "your-org-id",
  "chat_history": [
    {
      "role": "user",
      "content": "Hi, I'm having trouble accessing my account dashboard."
    },
    {
      "role": "assistant", 
      "content": "I'd be happy to help you with your account dashboard access. Can you tell me what specific error or issue you're encountering?"
    },
    {
      "role": "user",
      "content": "It keeps saying 'Access Denied' when I try to log in."
    },
    {
      "role": "assistant",
      "content": "I see you're getting an 'Access Denied' error. Let me help you troubleshoot this."
    }
  ]
}
```

### Without Chat History (Backward Compatible)

```json
{
  "transcript": "Can you help me reset my password?",
  "language": "en", 
  "base64_audio": "<base64-encoded-audio>",
  "org_id": "your-org-id"
}
```

## Chat Message Format

Each message in `chat_history` must have:

- `role`: Either "user" or "assistant"
- `content`: The message content as a string

## How It Works

### Gemini Validation
- Chat history messages are prepended to the Gemini API call contents array
- User messages become `role: "user"` in Gemini format  
- Assistant messages become `role: "model"` in Gemini format
- Current transcript with audio is added as the final user message

### OpenAI Generation
- Chat history messages are prepended to the OpenAI messages array
- System prompt is added first
- Chat history follows in chronological order
- Current question is added as the final user message

## Example Usage

### Python Client

```python
import requests
import json

# Request with chat history
payload = {
    "transcript": "How do I change my email address?",
    "language": "en",
    "base64_audio": encoded_audio,
    "org_id": "your-org-id",
    "chat_history": [
        {"role": "user", "content": "I need to update my profile"},
        {"role": "assistant", "content": "I can help you update your profile. What would you like to change?"}
    ]
}

response = requests.post(
    "http://localhost:8000/api/v1/answer-sse",
    json=payload,
    stream=True
)

# Process SSE response...
```

### JavaScript/TypeScript Client

```typescript
const payload = {
  transcript: "How do I change my email address?",
  language: "en",
  base64_audio: encodedAudio,
  org_id: "your-org-id",
  chat_history: [
    { role: "user", content: "I need to update my profile" },
    { role: "assistant", content: "I can help you update your profile. What would you like to change?" }
  ]
};

const response = await fetch('http://localhost:8000/api/v1/answer-sse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});

// Process SSE stream...
```

## Migration Guide

### For Existing Clients
No changes required! Existing API calls will continue to work exactly as before.

### For New Implementations
Simply add the optional `chat_history` field to include conversation context.

## Benefits

1. **Better Context Understanding**: AI models can understand the conversation flow
2. **More Relevant Responses**: Answers consider previous discussion points
3. **Improved User Experience**: More natural, context-aware conversations
4. **Backward Compatible**: No breaking changes for existing integrations