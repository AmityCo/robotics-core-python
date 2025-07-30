# TTS Stream Updates Summary

## Changes Made

### 1. Integrated Cached Requests Handler

Updated `src/tts_stream.py` to use the cached requests handler from `src/requests_handler.py` for loading phoneme data:

```python
from src.requests_handler import get as cached_get
```

### 2. Updated Phoneme Loading Method

Replaced the direct `requests.get()` call with the cached version:

**Before:**
```python
async def _load_phoneme_data(self, url: str) -> List[TtsPhoneme]:
    try:
        # Add cache busting parameter
        import random
        cache_buster = random.randint(1, 100000)
        full_url = f"{url}?q={cache_buster}"
        
        response = requests.get(full_url, timeout=10)
        # ... rest of the method
```

**After:**
```python
async def _load_phoneme_data(self, url: str) -> List[TtsPhoneme]:
    try:
        logger.info(f"Loading phoneme data from: {url}")
        
        # Use cached requests handler for better performance and caching
        response = await cached_get(url, timeout=10)
        # ... rest of the method
```

### 3. Benefits of This Integration

1. **Automatic Caching**: Phoneme URLs will be automatically cached for 15 minutes with early refresh at 3 minutes
2. **UTF-8 Encoding**: Ensures proper character handling for Thai, Chinese, and other non-ASCII content
3. **Cache Patterns**: Phoneme URLs (containing "phoneme", ".json") will be cached automatically
4. **Performance**: Reduces redundant HTTP requests when loading the same phoneme data
5. **Error Handling**: Better error handling and logging through the requests handler

### 4. Key Features Maintained

- **Text Transformation**: Removes bracketed text and illegal characters
- **Phoneme Processing**: Applies IPA phoneme tags and substitutions
- **SSML Generation**: Creates advanced SSML with:
  - Microsoft-specific silence tags
  - Lexicon support with timestamps
  - Prosody controls (pitch, rate)
  - Language-specific formatting
- **Streaming Support**: Processes text in chunks for real-time TTS

### 5. Cache Behavior

The requests handler will cache phoneme URLs based on these patterns:
- URLs containing "template", "prompt", "phoneme"
- URLs ending in ".txt", ".md", ".json"
- Cache TTL: 15 minutes with early refresh at 3 minutes

### 6. Usage Example

```python
# Initialize TTS streamer with cached phoneme loading
streamer = TTSStreamer(
    org_config=org_config,
    language="en-US",
    audio_callback=audio_callback,
    remove_bracketed_words=True
)

# Initialize (loads phonemes with caching)
await streamer.initialize()

# Use normally - phonemes are now cached
streamer.append_text("Hello world!")
```

## Architecture Benefits

1. **Separation of Concerns**: SSML formatting logic is now in its own class
2. **Caching Integration**: Leverages existing caching infrastructure
3. **Maintainability**: Easier to test and modify SSML generation
4. **Performance**: Cached phoneme loading reduces latency
5. **Compatibility**: Maintains backward compatibility with existing code

The integration ensures that phoneme data is efficiently cached and reused, reducing network overhead and improving TTS performance, especially in high-throughput scenarios.
