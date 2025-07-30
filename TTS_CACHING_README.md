# Enhanced TTS Handler with Azure Storage Caching

## Overview

The TTS Handler has been enhanced with intelligent caching using Azure Blob Storage. This improvement significantly reduces API calls to Azure TTS and improves response times for repeated text-to-speech requests.

## Features

### 🚀 Intelligent Caching
- **Automatic Cache Lookup**: Before making TTS API calls, the system checks if audio already exists in cache
- **Background Cache Storage**: Generated audio is saved to Azure Storage asynchronously without blocking response
- **Smart Cache Keys**: Uses format `{language}/{model}/{text_hash}.mp3` for organized storage

### 🎯 Auto-Detection
- **Language Detection**: Automatically extracts language from SSML voice tags
- **Model Detection**: Determines TTS model type (neural2/standard) from voice names
- **Fallback Defaults**: Uses sensible defaults when detection fails

### 📁 Organized Storage Structure
```
tts-cache/
├── en-US/
│   ├── neural2/
│   │   ├── abc123def456.mp3
│   │   └── def789ghi012.mp3
│   └── standard/
│       └── hij345klm678.mp3
├── th-TH/
│   └── neural2/
│       └── nop901qrs234.mp3
└── es-ES/
    └── neural2/
        └── tuv567wxy890.mp3
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Azure Storage Configuration (choose one method)

# Method 1: Connection String (recommended)
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=youraccount;AccountKey=yourkey;EndpointSuffix=core.windows.net"

# Method 2: Account Name + Key
AZURE_STORAGE_ACCOUNT_NAME="yourstorageaccount"
AZURE_STORAGE_ACCOUNT_KEY="yourstoragekey"

# Container name for TTS cache
TTS_CACHE_CONTAINER_NAME="tts-cache"

# Existing Azure TTS configuration
AZURE_TTS_SUBSCRIPTION_KEY="your_azure_tts_key"
```

### Dependencies

New dependencies added to `requirements.txt`:
```
azure-storage-blob==12.24.0
azure-identity==1.19.0
```

## Usage

### Basic Usage (Auto-Detection)

```python
from src.tts_handler import TTSHandler

# Initialize
tts_handler = TTSHandler(subscription_key="your_key")

# Generate speech with auto-detection
ssml_content = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="en-US-AriaNeural">
        <prosody rate="medium" pitch="medium">
            Hello, this is a cached TTS example!
        </prosody>
    </voice>
</speak>'''

audio_data = tts_handler.generate_speech(ssml_content)
```

### Explicit Parameters

```python
# Specify language and model explicitly
audio_data = tts_handler.generate_speech(
    ssml_content, 
    language="en-US", 
    model="neural2"
)
```

### Cache Management

```python
# Check cache information
cache_info = tts_handler.get_cache_info("Hello world", "en-US", "neural2")
print(f"Cached: {cache_info['is_cached']}")
print(f"Cache key: {cache_info['cache_key']}")

# Clear specific cache entry
success = tts_handler.clear_cache_for_text("Hello world", "en-US", "neural2")
```

## How It Works

### Cache Flow

1. **Request Received**: `generate_speech()` called with SSML
2. **Parameter Extraction**: Language and model extracted from SSML (if not provided)
3. **Text Extraction**: Plain text content extracted from SSML for hashing
4. **Cache Key Generation**: Format: `{language}/{model}/{hash}.mp3`
5. **Cache Lookup**: Check Azure Storage for existing audio file
6. **Cache Hit**: Return cached audio immediately
7. **Cache Miss**: Generate via Azure TTS API
8. **Background Cache**: Save new audio to Azure Storage asynchronously
9. **Return Audio**: Send audio data to client

### Hash Generation

The cache key uses SHA-256 hash of:
- Plain text content (SSML tags removed)
- Language code
- Model name

This ensures unique cache entries for different combinations while being deterministic.

### Asynchronous Caching

Audio files are saved to Azure Storage in the background using `asyncio.create_task()`. This means:
- ✅ No blocking of response to client
- ✅ Fire-and-forget reliability
- ✅ Improved user experience

## Performance Benefits

### First Request (Cache Miss)
- Time: ~1-3 seconds (Azure TTS API call)
- Storage: Audio saved to cache asynchronously

### Subsequent Requests (Cache Hit)
- Time: ~50-200ms (Azure Storage retrieval)
- Improvement: **85-95% faster response time**

## Testing

### Run the Test Suite
```bash
# Set required environment variables
export AZURE_TTS_SUBSCRIPTION_KEY="your_key"
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"

# Run the caching test
python test_tts_caching.py

# Run the example
python example_enhanced_tts.py
```

### Expected Test Output
```
=== Testing TTS Caching ===
First call (should generate fresh audio)...
✓ First call successful: 45678 bytes in 2.34 seconds
Waiting for cache save to complete...
Second call (should use cached audio)...
✓ Second call successful: 45678 bytes in 0.15 seconds
✓ Audio data matches between calls
✓ Cache significantly faster (0.15s vs 2.34s)
Cache info: {'cache_key': 'en-US/neural2/abc123def456.mp3', 'is_cached': True, 'audio_size': 45678}
=== Test Complete ===
```

## Error Handling

The system gracefully handles various error scenarios:

- **Azure Storage Unavailable**: Falls back to direct TTS API calls
- **Cache Retrieval Errors**: Generates fresh audio via TTS API
- **Cache Save Errors**: Logs error but doesn't affect response
- **Invalid SSML**: Uses fallback text extraction
- **Network Issues**: Appropriate timeouts and retries

## Monitoring and Logging

Enhanced logging provides visibility into caching performance:

```
INFO: Using cached audio: en-US/neural2/abc123def456.mp3
INFO: Generated and cached new audio: th-TH/neural2/def789ghi012.mp3
DEBUG: Generating new audio for: es-ES/neural2/hij345klm678.mp3
```

## Security Considerations

- **Access Control**: Use Azure Storage access keys or managed identities
- **Network Security**: All communications use HTTPS
- **Data Privacy**: Audio files are stored with hash-based filenames (no personal data in filenames)
- **Container Isolation**: TTS cache uses dedicated container

## Future Enhancements

Potential improvements for future versions:

1. **TTL (Time To Live)**: Automatic cache expiration
2. **Cache Size Management**: LRU eviction policies
3. **Compression**: Additional audio compression for storage optimization
4. **Analytics**: Cache hit/miss rate monitoring
5. **Multi-Region**: Geographic distribution of cache
6. **Batch Operations**: Bulk cache management operations

## Troubleshooting

### Common Issues

**Cache not working**:
- Check Azure Storage connection string
- Verify container permissions
- Check network connectivity

**Slow performance**:
- Verify Azure Storage region proximity
- Check network bandwidth
- Monitor Azure Storage metrics

**High storage costs**:
- Implement cache cleanup policies
- Monitor storage usage
- Consider cache size limits

### Debug Mode

Enable debug logging for detailed cache operations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed information about cache lookups, saves, and Azure Storage operations.
