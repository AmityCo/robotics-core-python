# Answer API Test

This test script reads test data from `test/test.csv` and sends requests to the `/api/v1/answer` endpoint.

## Prerequisites

1. Make sure your FastAPI server is running (usually on http://localhost:8000)
2. Ensure the organization configuration "spw-internal-4" exists in your system

## Running the Test

### Option 1: Run directly
```bash
cd test
python test_answer.py
```

### Option 2: Run from project root
```bash
python run_test.py
```

### Option 3: Run as module
```bash
python -m test.test_answer
```

## Test Data Format

The CSV file should have the following columns:
- `audioUrl`: URL to the audio file to download
- `answer`: Expected answer (used for language detection)
- `original_s3_url`: Original S3 URL (optional, not used in test)
- `transcript`: The transcript text to send (optional)

## Output

The test will:
1. Download audio files from the provided URLs
2. Encode them to base64
3. Send requests to the answer API with organization ID "spw-internal-4"
4. Log detailed results for each request
5. Save results to `test/test_results.json`

## Language Detection

The script automatically detects the language based on the expected answer:
- If the answer contains Thai characters, it uses language "th"
- Otherwise, it uses language "en"

## Configuration

You can modify these settings in `test_answer.py`:
- `API_BASE_URL`: Change if your server runs on a different URL/port
- `ORG_ID`: Change to use a different organization configuration
