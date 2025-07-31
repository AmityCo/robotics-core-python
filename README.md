# Robotics Core Python

AI-powered answer generation system with real-time progress updates via Server-Sent Events (SSE).

## Features

- **Multi-stage Pipeline**: Validation → Knowledge Search → Answer Generation
- **Real-time Updates**: SSE support for live progress tracking
- **Flexible Input**: Supports audio-based, text-only, and direct keyword input
- **Skip Validation**: Optional keywords parameter to bypass validation step
- **Organization Configuration**: Dynamic config from DynamoDB
- **Multiple AI Models**: Gemini for validation, OpenAI for generation
- **Knowledge Management**: Integration with Amity Solutions KM API

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python src/main.py
   ```

3. Test the APIs:
   ```bash
   # Regular API
   python test/test_answer.py
   
   # SSE API with real-time updates
   python test/test_answer.py --sse
   ```

## API Endpoints

### Regular Answer API
- **POST** `/api/v1/answer` - Complete pipeline with single response

### SSE Answer API ✨ NEW
- **POST** `/api/v1/answer-sse` - Real-time pipeline with progress updates

### Other Endpoints
- **POST** `/api/v1/gemini/validate` - Gemini validation only
- **POST** `/api/v1/km/search` - Knowledge management search
- **POST** `/api/v1/km/batch-search` - Batch knowledge management search

## Enhanced API Features ✨ NEW

### Flexible Input Modes

The SSE API now supports three input modes:

1. **Audio + Text (Default)**: Full validation with audio and transcript
2. **Text-only**: Validation with transcript only (no audio required)
3. **Direct Keywords**: Skip validation entirely and use provided keywords

### Request Parameters

```json
{
  "transcript": "string",              // Required: User's transcript
  "language": "string",               // Required: Language code (e.g., "en-US")
  "base64_audio": "string | null",    // Optional: Base64 encoded audio
  "org_id": "string",                 // Required: Organization ID
  "config_id": "string",              // Required: Configuration ID
  "chat_history": [],                 // Optional: Previous conversation
  "keywords": ["string"] | null       // Optional: Skip validation if provided
}
```

### Usage Examples

#### 1. Audio-based Processing (Traditional)
```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US",
  "base64_audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEA...",
  "org_id": "my-org",
  "config_id": "my-config"
}
```

#### 2. Text-only Processing
```json
{
  "transcript": "What is the weather like today?", 
  "language": "en-US",
  "org_id": "my-org",
  "config_id": "my-config"
}
```

#### 3. Skip Validation with Keywords
```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US", 
  "org_id": "my-org",
  "config_id": "my-config",
  "keywords": ["weather", "forecast", "today"]
}
```

#### 4. Skip Validation with Empty Keywords
```json
{
  "transcript": "What is the weather like today?",
  "language": "en-US",
  "org_id": "my-org", 
  "config_id": "my-config",
  "keywords": []
}
```

### Performance Benefits

- **Text-only**: ~100-200ms faster (no audio processing)
- **Skip validation**: ~200-500ms faster (no Gemini API call)
- **Reduced costs**: Fewer external API calls when validation is skipped

## Documentation

- [SSE Implementation Guide](SSE_README.md) - Detailed SSE documentation
- [Organization Configuration](ORG_CONFIG.md) - Config management
- [Validation Logging](VALIDATION_LOGGING.md) - Logging setup

## Demo Scripts

- `demo_sse.py` - Interactive SSE demonstration
- `compare_apis.py` - Compare regular vs SSE performance
- `test_sse_setup.py` - Verify SSE functionality

## Testing

The test suite supports both regular and SSE modes:

```bash
# Test regular API
python test/test_answer.py

# Test SSE API with timing
python test/test_answer.py --sse
```

Results include detailed timing information for performance analysis.

## Architecture

```
Client Request
     ↓
FastAPI Server
     ↓
┌─── Gemini Validation ───┐
│    (SSE: validation_result) │
└─────────────────────────┘
     ↓
┌─── KM Batch Search ────┐
│    (SSE: km_result)        │
└─────────────────────────┘
     ↓
┌─── OpenAI Generation ──┐
│    (SSE: answer_result)    │
└─────────────────────────┘
     ↓
Final Response / SSE Complete
```

## Client Integration Guide

### Creating an SSE Client

The `/api/v1/answer-sse` endpoint provides real-time progress updates via Server-Sent Events. Here's how to integrate with it:

#### Python Client Example

```python
import requests
import json

def handle_sse_response(transcript, language, org_id, base64_audio=None, keywords=None):
    payload = {
        "transcript": transcript,
        "language": language,
        "org_id": org_id
    }
    
    # Add optional fields
    if base64_audio:
        payload["base64_audio"] = base64_audio
    if keywords is not None:  # Allow empty list
        payload["keywords"] = keywords
    
    response = requests.post(
        "http://localhost:8000/api/v1/answer-sse",
        json=payload,
        stream=True,
        timeout=30
    )
    
    for line in response.iter_lines():
        if line and line.startswith(b'data: '):
            try:
                data = json.loads(line[6:].decode('utf-8'))
                event_type = data.get('type')
                
                # Handle different event types
                if event_type == 'status':
                    print(f"Status: {data.get('message')}")
                elif event_type == 'validation_result':
                    print(f"Validation: {data['data']['correction']}")
                    print(f"Keywords: {data['data']['keywords']}")
                elif event_type == 'km_result':
                    print(f"KM Search: {len(data['data']['data'])} results")
                elif event_type == 'answer_chunk':
                    print(data['data']['content'], end='', flush=True)
                elif event_type == 'complete':
                    print("\nPipeline completed!")
                    break
                elif event_type == 'error':
                    print(f"Error: {data.get('message')}")
                    break
                    
            except json.JSONDecodeError:
                continue

# Usage examples:
# handle_sse_response("Hello", "en-US", "org1")  # Text-only
# handle_sse_response("Hello", "en-US", "org1", keywords=["greeting"])  # Skip validation
# handle_sse_response("Hello", "en-US", "org1", "audio_data", keywords=[])  # Skip with empty keywords
```

#### JavaScript/TypeScript Client Example

```typescript
interface SSEEvent {
  type: string;
  timestamp: string;
  data?: any;
  message?: string;
}

interface RequestData {
  transcript: string;
  language: string;
  org_id: string;
  base64_audio?: string;  // Optional
  keywords?: string[];    // Optional - skip validation if provided
}

async function handleSSE(requestData: RequestData) {
  const response = await fetch('http://localhost:8000/api/v1/answer-sse', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(requestData)
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  if (!reader) return;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: SSEEvent = JSON.parse(line.slice(6));
            
            switch (event.type) {
              case 'status':
                console.log(`Status: ${event.message}`);
                // Check if validation was skipped
                if (event.message?.includes('skipping validation')) {
                  console.log('✅ Validation skipped due to provided keywords');
                }
                break;
              case 'validation_result':
                console.log('Validation completed:', event.data);
                console.log('Keywords:', event.data.keywords);
                break;
              case 'km_result':
                console.log('KM search completed:', event.data);
                break;
              case 'answer_chunk':
                document.getElementById('answer')!.textContent += event.data.content;
                break;
              case 'thinking':
                console.log('AI thinking:', event.data.content);
                break;
              case 'metadata':
                console.log('Metadata:', event.data);
                break;
              case 'tts_audio':
                // Handle TTS audio data
                playAudio(event.data);
                break;
              case 'complete':
                console.log('Pipeline completed successfully!');
                return;
              case 'error':
                console.error('Error:', event.message);
                return;
            }
          } catch (e) {
            // Skip invalid JSON lines
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Usage examples:
// handleSSE({ transcript: "Hello", language: "en-US", org_id: "org1" });  // Text-only
// handleSSE({ transcript: "Hello", language: "en-US", org_id: "org1", keywords: ["greeting"] });  // Skip validation
// handleSSE({ transcript: "Hello", language: "en-US", org_id: "org1", keywords: [] });  // Skip with empty keywords
```

#### Kotlin Client Example

```kotlin
import kotlinx.coroutines.*
import kotlinx.serialization.*
import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.ByteArrayOutputStream
import java.util.Base64

@Serializable
data class SSERequest(
    val transcript: String,
    val language: String,
    val base64_audio: String,
    val org_id: String
)

@Serializable
data class SSEEvent(
    val type: String,
    val timestamp: String,
    val data: JsonElement? = null,
    val message: String? = null
)

@Serializable
data class TTSAudioData(
    val text: String,
    val language: String,
    val audio_size: Int,
    val audio_data: String? = null,
    val audio_format: String,
    val chunk_index: Int? = null,
    val total_chunks: Int? = null,
    val is_final: Boolean? = null
)

class SSEClient {
    private val client = OkHttpClient.Builder()
        .readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
        .build()
    private val json = Json { 
        ignoreUnknownKeys = true
        isLenient = true
    }
    
    // Buffer for chunked audio data
    private val audioBuffers = mutableMapOf<String, ChunkedAudioBuffer>()

    data class ChunkedAudioBuffer(
        val chunks: MutableMap<Int, String> = mutableMapOf(),
        var totalChunks: Int = 0,
        var text: String = "",
        var language: String = "",
        var format: String = "",
        var totalSize: Int = 0
    ) {
        fun isComplete(): Boolean = chunks.size == totalChunks && totalChunks > 0
        
        fun getCompleteAudioData(): ByteArray? {
            if (!isComplete()) return null
            
            val completeBase64 = StringBuilder()
            for (i in 0 until totalChunks) {
                chunks[i]?.let { completeBase64.append(it) }
                    ?: return null // Missing chunk
            }
            
            return try {
                Base64.getDecoder().decode(completeBase64.toString())
            } catch (e: Exception) {
                println("Failed to decode complete audio data: ${e.message}")
                null
            }
        }
    }

    suspend fun handleSSE(
        transcript: String,
        language: String,
        orgId: String,
        base64Audio: String = "",
        onEvent: (SSEEvent) -> Unit,
        onCompleteAudio: ((text: String, audioData: ByteArray, format: String, language: String) -> Unit)? = null
    ) = withContext(Dispatchers.IO) {
        val requestData = SSERequest(
            transcript = transcript,
            language = language,
            base64_audio = base64Audio,
            org_id = orgId
        )

        val requestBody = json.encodeToString(requestData)
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("http://localhost:8000/api/v1/answer-sse")
            .post(requestBody)
            .addHeader("Accept", "text/event-stream")
            .addHeader("Cache-Control", "no-cache")
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw Exception("HTTP ${response.code}: ${response.message}")
            }

            val reader = BufferedReader(InputStreamReader(response.body!!.byteStream()))
            var lineBuffer = StringBuilder()
            
            try {
                reader.lineSequence().forEach { line ->
                    if (line.startsWith("data: ")) {
                        try {
                            val eventData = line.substring(6)
                            
                            // Handle potentially large JSON by streaming parse
                            val event = try {
                                json.decodeFromString<SSEEvent>(eventData)
                            } catch (e: Exception) {
                                // If JSON is too large or malformed, skip gracefully
                                println("Skipping malformed SSE event: ${e.message}")
                                return@forEach
                            }
                            
                            // Handle chunked audio specifically
                            if (event.type == "tts_audio") {
                                handleTTSAudio(event, onCompleteAudio)
                            }
                            
                            onEvent(event)
                            
                            // Break on completion or error
                            if (event.type == "complete" || event.type == "error") {
                                return@forEach
                            }
                        } catch (e: Exception) {
                            // Log but continue processing other events
                            println("Failed to parse SSE event: ${e.message}")
                        }
                    }
                }
            } catch (e: Exception) {
                println("Error reading SSE stream: ${e.message}")
            }
        }
    }
    
    private fun handleTTSAudio(
        event: SSEEvent,
        onCompleteAudio: ((String, ByteArray, String, String) -> Unit)?
    ) {
        try {
            val audioData = json.decodeFromJsonElement<TTSAudioData>(
                event.data ?: return
            )
            
            // Check if this is chunked audio
            if (audioData.chunk_index != null && audioData.total_chunks != null) {
                handleChunkedAudio(audioData, onCompleteAudio)
            } else {
                // Handle single chunk audio (current implementation)
                audioData.audio_data?.let { base64Data ->
                    try {
                        val audioBytes = Base64.getDecoder().decode(base64Data)
                        onCompleteAudio?.invoke(
                            audioData.text,
                            audioBytes,
                            audioData.audio_format,
                            audioData.language
                        )
                    } catch (e: Exception) {
                        println("Failed to decode audio data: ${e.message}")
                    }
                }
            }
        } catch (e: Exception) {
            println("Failed to parse TTS audio data: ${e.message}")
        }
    }
    
    private fun handleChunkedAudio(
        audioData: TTSAudioData,
        onCompleteAudio: ((String, ByteArray, String, String) -> Unit)?
    ) {
        val audioId = "${audioData.text.hashCode()}_${audioData.language}"
        val buffer = audioBuffers.getOrPut(audioId) { ChunkedAudioBuffer() }
        
        // Update buffer metadata
        buffer.text = audioData.text
        buffer.language = audioData.language
        buffer.format = audioData.audio_format
        buffer.totalSize = audioData.audio_size
        buffer.totalChunks = audioData.total_chunks ?: 1
        
        // Add chunk data
        audioData.chunk_index?.let { chunkIndex ->
            audioData.audio_data?.let { chunkData ->
                buffer.chunks[chunkIndex] = chunkData
            }
        }
        
        // Check if audio is complete
        if (buffer.isComplete() || audioData.is_final == true) {
            buffer.getCompleteAudioData()?.let { completeAudio ->
                onCompleteAudio?.invoke(
                    buffer.text,
                    completeAudio,
                    buffer.format,
                    buffer.language
                )
            }
            // Clean up buffer
            audioBuffers.remove(audioId)
        }
    }
}

// Usage example with robust audio handling
suspend fun main() {
    val sseClient = SSEClient()
    
    sseClient.handleSSE(
        transcript = "What are the office hours?",
        language = "en",
        orgId = "example-org-123",
        onEvent = { event ->
            when (event.type) {
                "status" -> {
                    println("Status: ${event.message}")
                }
                "validation_result" -> {
                    val data = event.data?.jsonObject
                    val correction = data?.get("correction")?.jsonPrimitive?.content
                    println("Validation: $correction")
                }
                "km_result" -> {
                    val data = event.data?.jsonObject
                    val results = data?.get("data")?.jsonArray
                    println("KM Search: ${results?.size} results")
                }
                "answer_chunk" -> {
                    val content = event.data?.jsonObject?.get("content")?.jsonPrimitive?.content
                    print(content)
                }
                "thinking" -> {
                    val content = event.data?.jsonObject?.get("content")?.jsonPrimitive?.content
                    println("AI thinking: $content")
                }
                "metadata" -> {
                    val docIds = event.data?.jsonObject?.get("doc_ids")?.jsonPrimitive?.content
                    println("Sources: $docIds")
                }
                "tts_audio" -> {
                    // Audio handling is done in onCompleteAudio callback
                    println("Received TTS audio chunk")
                }
                "complete" -> {
                    println("\nPipeline completed successfully!")
                }
                "error" -> {
                    println("Error: ${event.message}")
                }
            }
        },
        onCompleteAudio = { text, audioData, format, language ->
            println("Complete audio ready: ${text.take(50)}... (${audioData.size} bytes, $format)")
            // Play audio here
            playAudio(audioData, format)
        }
    )
}

// Audio playback function (implement based on your platform)
fun playAudio(audioData: ByteArray, format: String) {
    // Android: Use MediaPlayer with temporary file or AudioTrack
    // Desktop: Use javax.sound.sampled or external library
    println("Playing audio: ${audioData.size} bytes in $format format")
}

// For Android projects, add these dependencies to build.gradle.kts:
/*
dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
    implementation("com.squareup.okhttp3:okhttp:4.11.0")
}
*/
```

### Available SSE Events

The SSE endpoint emits the following event types:

| Event Type | Description | Data Structure |
|------------|-------------|----------------|
| `status` | Pipeline progress updates | `{ message: string }` |
| `validation_result` | Gemini validation completed | `{ correction: string, keywords: string[] }` |
| `km_result` | Knowledge management search results | `{ data: {documentId: string, document: {id: string, metadata: string, publicId: string, sampleQuestions: string, content: string }, rerankerScore: number, score: number }[], total: number }` |
| `answer_chunk` | Streaming answer content | `{ content: string }` |
| `thinking` | AI reasoning process (optional) | `{ content: string }` |
| `metadata` | Answer metadata (confidence, sources) | `{ doc_ids: string }` |
| `tts_audio` | Text-to-speech audio data | `{ text: string, language: string, audio_size: number, audio_data: string, audio_format: string, chunk_index?: number, total_chunks?: number, is_final?: boolean }` |
| `complete` | Pipeline finished successfully | `{ message: string }` |
| `error` | Error occurred | `{ message: string }` |

### TTS Audio Handling Considerations

**Large Audio Data**: TTS audio files can be quite large (40KB-200KB+) when base64-encoded. This can cause issues with:

- **SSE Message Size Limits**: Some browsers/servers limit individual SSE event sizes
- **Memory Usage**: Large base64 strings can cause memory spikes
- **Network Buffering**: Large chunks may cause buffering problems
- **JSON Parsing Performance**: Very large JSON payloads are slow to parse

**Current Implementation**: Audio is sent as a single large base64-encoded chunk in the `audio_data` field.

**Recommended Client-Side Solutions**:
1. **Streaming JSON Parser**: Use streaming JSON parsers for large events
2. **Memory Management**: Immediately decode and release base64 strings
3. **Timeout Handling**: Set appropriate timeouts for large audio chunks
4. **Chunked Audio Support**: Implement support for potential future chunked audio (see Kotlin example above)

**Future Enhancements**: The server may implement audio chunking for very large files:
- `chunk_index`: Index of current chunk (0-based)
- `total_chunks`: Total number of chunks for this audio
- `is_final`: Whether this is the final chunk
- Clients should buffer chunks and reassemble complete audio

### Event Flow Sequence

1. **status**: "Starting answer pipeline"
2. **status**: "Starting validation with Gemini"
3. **validation_result**: Corrected transcript and search terms
4. **status**: "Starting knowledge management search"
5. **km_result**: Search results from knowledge base
6. **status**: "Starting answer generation with OpenAI"
7. **answer_chunk**: Streaming answer content (multiple events)
8. **thinking**: AI reasoning (if enabled)
9. **metadata**: Answer metadata and sources
10. **tts_audio**: Audio data (if TTS enabled)
11. **complete**: Pipeline finished

### Error Handling

Always handle these scenarios:
- Network timeouts (use appropriate timeout values)
- JSON parsing errors for malformed events
- Connection drops (implement reconnection logic)
- Error events from the server

### Demo Usage

See working examples in:
- `demo_sse.py` - Python CLI demonstration
- `frontend/src/utils/sseClient.ts` - React/TypeScript implementation

## Requirements

- Python 3.8+
- FastAPI
- OpenAI API key
- Google Gemini API key
- AWS credentials (for DynamoDB config)
- Amity Solutions KM API access