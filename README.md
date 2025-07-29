# Robotics Core Python

AI-powered answer generation system with real-time progress updates via Server-Sent Events (SSE).

## Features

- **Multi-stage Pipeline**: Validation → Knowledge Search → Answer Generation
- **Real-time Updates**: SSE support for live progress tracking
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

## Requirements

- Python 3.8+
- FastAPI
- OpenAI API key
- Google Gemini API key
- AWS credentials (for DynamoDB config)
- Amity Solutions KM API access