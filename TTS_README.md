# TTS Streaming Integration

This document describes the Text-to-Speech (TTS) streaming integration that automatically converts answer chunks to speech as they're generated.

## Overview

The TTS streaming system buffers incoming text chunks from the answer flow and sends them to Azure Cognitive Services TTS API when they meet certain criteria:

- **Word threshold**: 3 or more words
- **Time threshold**: Text has waited for more than 2 seconds
- **Immediate flush**: When the answer generation is complete

## Architecture

```
Answer Flow → TTS Buffer → Azure TTS API → Audio Output
     ↓             ↓            ↓            ↓
answer_chunk → text buffer → SSML request → MP3 audio
```

## Components

### 1. TTSBuffer Class

Handles buffering and threshold logic for individual text streams.

**Key Features:**
- Thread-safe text accumulation
- Configurable word and time thresholds  
- Automatic timer-based flushing
- SSML generation with proper escaping

### 2. TTSStreamer Class

Manages multiple language buffers and coordinates with organization configuration.

**Key Features:**
- Multi-language support
- Organization-specific TTS models
- Voice configuration management
- Centralized audio callback handling

### 3. Integration with Answer Flow

The answer flow automatically sends `answer_chunk` events to the TTS streamer:

```python
# In answer_flow_sse.py
if tts_streamer and chunk.strip():
    tts_streamer.add_text_chunk(chunk, language)
```

## Configuration

TTS configuration is loaded from the organization config via DynamoDB:

```json
{
  "tts": {
    "azure": {
      "subscriptionKey": "your-azure-tts-key",
      "lexiconURL": "",
      "phonemeUrl": "", 
      "models": [
        {
          "language": "en-US",
          "name": "en-US-JennyNeural",
          "pitch": "+10%",
          "phonemeUrl": "https://..."
        }
      ]
    }
  }
}
```

## Azure TTS API Integration

The system uses the Azure Cognitive Services TTS endpoint:

```
POST https://southeastasia.tts.speech.microsoft.com/cognitiveservices/v1
Content-Type: application/ssml+xml
Ocp-Apim-Subscription-Key: {subscription_key}
X-Microsoft-OutputFormat: audio-16khz-128kbitrate-mono-mp3
```

## Usage

### Automatic Integration

TTS is automatically enabled when:
1. Organization config contains valid Azure TTS settings
2. TTS models are configured for the request language
3. Answer flow generates `answer_chunk` events

### Manual Usage

```python
from src.tts_stream import TTSStreamer
from src.org_config import load_org_config

# Load org config
org_config = load_org_config("your-config-id")

# Create streamer with callback
def audio_ready(text: str, language: str, audio_data: bytes):
    print(f"Audio ready: {len(audio_data)} bytes for '{text}'")

streamer = TTSStreamer(org_config, chunk_callback=audio_ready)

# Add text chunks
streamer.add_text_chunk("Hello", "en-US")
streamer.add_text_chunk(" world", "en-US") 
streamer.add_text_chunk(" this is a test", "en-US")  # Triggers TTS

# Flush remaining
streamer.flush_all()
```

## Buffering Logic

### Word Threshold
- Counts words by splitting on whitespace
- Default minimum: 3 words
- Prevents very short utterances

### Time Threshold  
- Tracks time since first text in buffer
- Default timeout: 2 seconds
- Ensures responsive speech for slow generation

### Example Flow
```
Time 0.0s: "Hello" → Buffer: "Hello" (1 word, wait)
Time 0.1s: " world" → Buffer: "Hello world" (2 words, wait) 
Time 0.2s: " this" → Buffer: "Hello world this" (3 words, TRIGGER TTS)
Time 0.3s: " is" → Buffer: "is" (1 word, wait)
Time 2.4s: [timeout] → Buffer: "is" (1 word, TRIGGER TTS)
```

## Error Handling

The system gracefully handles:
- Missing TTS configuration
- Invalid Azure credentials
- Network failures
- Malformed text content
- Unsupported languages

Errors are logged but don't interrupt the answer flow.

## Testing

### Basic Test
```bash
python test_tts_integration.py
```

### Demo with Real Config
```bash
export DEMO_ORG_CONFIG_ID="your-config-id"
python demo_tts_integration.py
```

### Integration Test
```bash
# Test complete answer flow with TTS
python -m pytest test/ -v -k tts
```

## Performance Considerations

- **Concurrent Processing**: TTS generation runs in background threads
- **Memory Usage**: Audio data is generated in chunks, not stored
- **Latency**: ~200-500ms per TTS request to Azure
- **Rate Limiting**: Azure TTS has request rate limits

## Monitoring

Key metrics to monitor:
- TTS generation latency
- Buffer trigger rates (words vs time)
- Azure API error rates
- Audio chunk sizes

## Troubleshooting

### Common Issues

1. **No audio generated**
   - Check Azure subscription key
   - Verify TTS models in org config
   - Ensure language is supported

2. **Slow audio generation**
   - Check network connectivity to Azure
   - Monitor Azure service status
   - Consider adjusting buffer thresholds

3. **Poor audio quality**
   - Verify SSML formatting
   - Check text cleaning/escaping
   - Try different voice models

### Debug Logging

Enable debug logging to see detailed TTS processing:

```python
import logging
logging.getLogger('src.tts_stream').setLevel(logging.DEBUG)
```

## Future Enhancements

- **Streaming Audio**: Support for streaming audio output
- **Voice Cloning**: Custom voice model integration  
- **SSML Features**: Advanced prosody and emphasis
- **Caching**: Audio caching for repeated phrases
- **Quality Control**: Audio quality validation
