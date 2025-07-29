# SSE Handler Completion Registry System

## Overview

The `SSEHandler` now implements a completion registry system that ensures the SSE stream doesn't terminate prematurely when multiple concurrent processes (like text generation and TTS processing) are running.

## Problem Solved

Previously, `sse_handler.mark_complete()` would immediately signal completion, causing the SSE loop to exit even if TTS processing was still ongoing. This led to premature termination of the SSE stream.

## New Architecture

### Component Registration

The SSE handler now maintains a registry of components that must complete before the stream ends:

```python
# Register components that need to complete
sse_handler.register_component('text_generation')
sse_handler.register_component('tts_processing')
```

### Component Completion

Each component marks itself as complete when done:

```python
# Text generation completes
sse_handler.mark_component_complete('text_generation')

# TTS processing completes (via callback)
sse_handler.mark_component_complete('tts_processing')
```

### Automatic Stream Termination

The SSE stream only terminates when **all** registered components have completed.

## Implementation Details

### SSEHandler Changes

1. **Registry Storage**: `_completion_registry` dict tracks component states
2. **Thread Safety**: `_registry_lock` protects concurrent access
3. **Automatic Completion**: Only signals complete when all components are done

```python
def mark_component_complete(self, component_name: str):
    with self._registry_lock:
        if component_name in self._completion_registry:
            self._completion_registry[component_name] = True
            
            # Check if all components are complete
            if all(self._completion_registry.values()):
                self.send('complete', message='Answer pipeline completed successfully')
                self.is_complete.set()
```

### TTS Integration

The `TTSStreamer` now supports completion callbacks:

```python
def tts_completion_callback():
    sse_handler.mark_component_complete('tts_processing')

tts_streamer = TTSStreamer(
    org_config, 
    chunk_callback=tts_audio_callback,
    completion_callback=tts_completion_callback
)
```

### Buffer-Level Tracking

Each `TTSBuffer` tracks its processing state and calls completion callback when done:

- When text processing finishes
- When flush operations complete
- When no more text is expected

## Usage Pattern

1. **Initialize SSE Handler**
   ```python
   sse_handler = SSEHandler()
   ```

2. **Register All Components**
   ```python
   sse_handler.register_component('text_generation')
   sse_handler.register_component('tts_processing')  # Only if TTS enabled
   ```

3. **Process Components**
   - Text generation streams chunks and marks complete when done
   - TTS processes chunks and marks complete when all audio is generated

4. **Automatic Termination**
   - SSE stream continues until all components complete
   - Error handling ensures components are marked complete even on failures

## Error Handling

All error paths ensure components are marked complete to prevent hanging:

```python
except Exception as e:
    sse_handler.send_error(f"Error: {str(e)}")
    # Ensure completion to avoid hanging
    sse_handler.mark_component_complete('text_generation')
    sse_handler.mark_component_complete('tts_processing')
```

## Benefits

1. **No Premature Termination**: Stream waits for all processing to complete
2. **Thread Safety**: Multiple components can complete concurrently
3. **Robust Error Handling**: Failures don't cause hanging
4. **Backward Compatibility**: Legacy `mark_complete()` still works
5. **Flexible**: Easy to add new components to track

## Testing

Comprehensive tests verify:
- Component registration and completion
- Concurrent completion from multiple threads
- Message yielding until all components complete
- Error handling and cleanup
- Complete SSE flow simulation

Run tests with:
```bash
python test_completion_registry.py
python test_sse_flow.py
```
