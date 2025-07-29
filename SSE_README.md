# Server-Sent Events (SSE) Support

The Answer API now supports Server-Sent Events (SSE) for real-time progress updates during the answer generation pipeline.

## New Endpoints

### SSE Answer Endpoint
- **URL**: `/api/v1/answer-sse`
- **Method**: POST
- **Content-Type**: `application/json`
- **Response**: `text/plain` (Server-Sent Events stream)

### Original Answer Endpoint (unchanged)
- **URL**: `/api/v1/answer`
- **Method**: POST
- **Content-Type**: `application/json`
- **Response**: `application/json`

## SSE Event Types

The SSE endpoint sends different types of events during the pipeline execution:

1. **status** - Progress updates
   ```json
   {
     "type": "status",
     "message": "Starting validation with Gemini",
     "timestamp": "2025-01-30T10:30:00.000Z"
   }
   ```

2. **validation_result** - Gemini validation results
   ```json
   {
     "type": "validation_result",
     "data": {
       "correction": "User corrected query",
       "searchTerms": {...}
     },
     "timestamp": "2025-01-30T10:30:05.000Z"
   }
   ```

3. **km_result** - Knowledge Management search results
   ```json
   {
     "type": "km_result",
     "data": {
       "data": [...],
       "total": 10
     },
     "timestamp": "2025-01-30T10:30:10.000Z"
   }
   ```

4. **answer_result** - Final generated answer
   ```json
   {
     "type": "answer_result",
     "data": {
       "answer": "Generated answer text",
       "model_used": "gpt-4"
     },
     "timestamp": "2025-01-30T10:30:15.000Z"
   }
   ```

5. **complete** - Pipeline completion
   ```json
   {
     "type": "complete",
     "message": "Answer pipeline completed successfully",
     "timestamp": "2025-01-30T10:30:15.000Z"
   }
   ```

6. **error** - Error occurred
   ```json
   {
     "type": "error",
     "message": "Error description",
     "timestamp": "2025-01-30T10:30:05.000Z"
   }
   ```

## Testing

### Install SSE Client Dependencies

```bash
pip install sseclient-py
```

### Running Tests

1. **Regular API Test**:
   ```bash
   python test/test_answer.py
   ```

2. **SSE API Test**:
   ```bash
   python test/test_answer.py --sse
   ```

### Test Results

The test results now include timing information for each stage:

```json
{
  "row": 1,
  "audio_url": "...",
  "transcript": "...",
  "expected_answer": "...",
  "generated_answer": "...",
  "model_used": "gpt-4",
  "language": "en",
  "validation_correction": "...",
  "km_results_count": 5,
  "stage_timings": {
    "request_start": "2025-01-30T10:30:00.000Z",
    "validation_start": "2025-01-30T10:30:00.100Z",
    "validation_complete": "2025-01-30T10:30:05.000Z",
    "km_search_start": "2025-01-30T10:30:05.100Z",
    "km_search_complete": "2025-01-30T10:30:10.000Z",
    "answer_generation_start": "2025-01-30T10:30:10.100Z",
    "answer_generation_complete": "2025-01-30T10:30:15.000Z",
    "total_duration": 15.0
  },
  "api_type": "SSE",
  "success": true
}
```

## Example JavaScript Client

```javascript
const eventSource = new EventSource('/api/v1/answer-sse', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    transcript: "Hello world",
    language: "en",
    base64_audio: "...",
    org_id: "your-org-id"
  })
});

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'status':
      console.log('Status:', data.message);
      break;
    case 'validation_result':
      console.log('Validation:', data.data.correction);
      break;
    case 'km_result':
      console.log('KM Results:', data.data.data.length);
      break;
    case 'answer_result':
      console.log('Answer:', data.data.answer);
      break;
    case 'complete':
      console.log('Pipeline completed');
      eventSource.close();
      break;
    case 'error':
      console.error('Error:', data.message);
      eventSource.close();
      break;
  }
};
```

## Performance Benefits

- **Real-time feedback**: Users can see progress as it happens
- **Better UX**: No more waiting for long-running requests
- **Debugging**: Stage-by-stage timing helps identify bottlenecks
- **Resilience**: Can handle longer processing times without timeouts
