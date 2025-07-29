import csv
import requests
import base64
import json
import logging
from typing import Dict, Any
import os
from datetime import datetime
import time

try:
    from sseclient import SSEClient
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    logging.warning("sseclient-py not installed. SSE functionality will not be available.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust this to your server URL
ANSWER_ENDPOINT = f"{API_BASE_URL}/api/v1/answer"
ANSWER_SSE_ENDPOINT = f"{API_BASE_URL}/api/v1/answer-sse"
ORG_ID = "spw-internal-3"

def download_audio_file(audio_url: str) -> bytes:
    """Download audio file from URL and return bytes"""
    try:
        response = requests.get(audio_url)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to download audio from {audio_url}: {e}")
        raise

def encode_audio_to_base64(audio_bytes: bytes) -> str:
    """Encode audio bytes to base64 string"""
    return base64.b64encode(audio_bytes).decode('utf-8')

def send_answer_request_sse(transcript: str, audio_url: str, language: str = "en") -> Dict[str, Any]:
    """
    Send request to the SSE answer API endpoint and collect streaming results
    
    Args:
        transcript: The transcript text
        audio_url: URL to download the audio file
        language: Language code (default: "en")
    
    Returns:
        Combined results with timing information
    """
    if not SSE_AVAILABLE:
        raise ImportError("sseclient-py is required for SSE functionality. Install with: pip install sseclient-py")
    
    try:
        # Download and encode audio
        logger.info(f"Downloading audio from: {audio_url}")
        audio_bytes = download_audio_file(audio_url)
        base64_audio = encode_audio_to_base64(audio_bytes)
        
        # Prepare request payload
        payload = {
            "transcript": transcript,
            "language": language,
            "base64_audio": base64_audio,
            "org_id": ORG_ID
        }
        
        # Send request to SSE answer API
        logger.info(f"Sending SSE request to answer API for transcript: {transcript[:50]}...")
        
        # Track timing for each stage
        start_time = time.time()
        stage_timings = {
            'request_start': datetime.now().isoformat(),
            'validation_start': None,
            'validation_complete': None,
            'km_search_start': None,
            'km_search_complete': None,
            'answer_generation_start': None,
            'answer_generation_complete': None,
            'total_duration': None
        }
        
        # Collect results from different stages
        validation_result = None
        km_result = None
        answer_result = None
        
        response = requests.post(ANSWER_SSE_ENDPOINT, json=payload, stream=True)
        response.raise_for_status()
        
        client = SSEClient(response)
        
        for event in client.events():
            try:
                data = json.loads(event.data)
                event_type = data.get('type')
                timestamp = data.get('timestamp')
                
                logger.info(f"SSE Event: {event_type} at {timestamp}")
                
                if event_type == 'status':
                    message = data.get('message', '')
                    if 'validation' in message.lower() and stage_timings['validation_start'] is None:
                        stage_timings['validation_start'] = timestamp
                    elif 'knowledge management' in message.lower() and stage_timings['km_search_start'] is None:
                        stage_timings['km_search_start'] = timestamp
                    elif 'answer generation' in message.lower() and stage_timings['answer_generation_start'] is None:
                        stage_timings['answer_generation_start'] = timestamp
                
                elif event_type == 'validation_result':
                    validation_result = data.get('data')
                    stage_timings['validation_complete'] = timestamp
                    logger.info(f"Validation completed: {validation_result.get('correction', '')[:100]}...")
                
                elif event_type == 'km_result':
                    km_result = data.get('data')
                    stage_timings['km_search_complete'] = timestamp
                    logger.info(f"KM search completed: {len(km_result.get('data', []))} results")
                
                elif event_type == 'answer_result':
                    answer_result = data.get('data')
                    stage_timings['answer_generation_complete'] = timestamp
                    logger.info(f"Answer generated: {answer_result.get('answer', '')[:100]}...")
                
                elif event_type == 'complete':
                    logger.info("Pipeline completed successfully")
                    break
                
                elif event_type == 'error':
                    error_message = data.get('message', 'Unknown error')
                    logger.error(f"SSE Error: {error_message}")
                    raise Exception(f"API Error: {error_message}")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse SSE event data: {event.data}")
                continue
        
        end_time = time.time()
        stage_timings['total_duration'] = end_time - start_time
        
        # Combine all results
        combined_result = {
            'validation_result': validation_result or {},
            'km_result': km_result or {},
            'answer': answer_result.get('answer', '') if answer_result else '',
            'model_used': answer_result.get('model_used', '') if answer_result else '',
            'stage_timings': stage_timings
        }
        
        return combined_result
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def send_answer_request(transcript: str, audio_url: str, language: str = "en") -> Dict[str, Any]:
    """
    Send request to the regular answer API endpoint (non-SSE)
    
    Args:
        transcript: The transcript text
        audio_url: URL to download the audio file
        language: Language code (default: "en")
    
    Returns:
        API response as dictionary
    """
    try:
        # Download and encode audio
        logger.info(f"Downloading audio from: {audio_url}")
        audio_bytes = download_audio_file(audio_url)
        base64_audio = encode_audio_to_base64(audio_bytes)
        
        # Prepare request payload
        payload = {
            "transcript": transcript,
            "language": language,
            "base64_audio": base64_audio,
            "org_id": ORG_ID
        }
        
        # Send request to answer API
        logger.info(f"Sending request to answer API for transcript: {transcript[:50]}...")
        response = requests.post(ANSWER_ENDPOINT, json=payload)
        response.raise_for_status()
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def test_answer_api_from_csv(csv_file_path: str, use_sse: bool = False):
    """
    Read test data from CSV file and send requests to answer API
    
    Args:
        csv_file_path: Path to the CSV file containing test data
        use_sse: Whether to use SSE endpoint for real-time progress updates
    """
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return
    
    if use_sse and not SSE_AVAILABLE:
        logger.error("SSE functionality requested but sseclient-py is not installed")
        logger.info("Install with: pip install sseclient-py")
        return
    
    endpoint_type = "SSE" if use_sse else "Regular"
    logger.info(f"Reading test data from: {csv_file_path}")
    logger.info(f"Using {endpoint_type} API endpoint")
    
    results = []
    row_count = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            row_count += 1
            audio_url = (row.get('audioUrl') or '').strip()
            expected_answer = (row.get('answer') or '').strip()
            transcript = (row.get('transcript') or '').strip()
            
            # Skip rows with missing required data
            if not audio_url:
                logger.warning(f"Row {row_count}: Missing audioUrl, skipping")
                continue
            
            # Determine language based on expected answer content
            # Simple heuristic: if contains Thai characters, use "th", otherwise "en"
            language = "th" if any('\u0e00' <= char <= '\u0e7f' for char in expected_answer) else "en"
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing Row {row_count}")
            logger.info(f"Audio URL: {audio_url}")
            logger.info(f"Expected Answer: {expected_answer}")
            logger.info(f"Transcript: {transcript}")
            logger.info(f"Detected Language: {language}")
            
            try:
                # Send request to answer API (SSE or regular)
                if use_sse:
                    api_response = send_answer_request_sse(transcript, audio_url, language)
                    stage_timings = api_response.get('stage_timings', {})
                else:
                    start_time = time.time()
                    api_response = send_answer_request(transcript, audio_url, language)
                    end_time = time.time()
                    # Create basic timing info for non-SSE requests
                    stage_timings = {
                        'request_start': datetime.now().isoformat(),
                        'total_duration': end_time - start_time
                    }
                
                # Extract the generated answer
                generated_answer = api_response.get('answer', '')
                model_used = api_response.get('model_used', '')
                validation_result = api_response.get('validation_result', {})
                km_result = api_response.get('km_result', {})
                
                # Log results
                logger.info(f"Generated Answer: {generated_answer}")
                logger.info(f"Model Used: {model_used}")
                logger.info(f"Validation Correction: {validation_result.get('correction', '')}")
                logger.info(f"KM Results Count: {len(km_result.get('data', []))}")
                
                # Log timing information for SSE
                if use_sse and stage_timings:
                    logger.info(f"Total Duration: {stage_timings.get('total_duration', 'N/A')} seconds")
                    if stage_timings.get('validation_start') and stage_timings.get('validation_complete'):
                        logger.info(f"Validation: {stage_timings.get('validation_start')} -> {stage_timings.get('validation_complete')}")
                    if stage_timings.get('km_search_start') and stage_timings.get('km_search_complete'):
                        logger.info(f"KM Search: {stage_timings.get('km_search_start')} -> {stage_timings.get('km_search_complete')}")
                    if stage_timings.get('answer_generation_start') and stage_timings.get('answer_generation_complete'):
                        logger.info(f"Answer Generation: {stage_timings.get('answer_generation_start')} -> {stage_timings.get('answer_generation_complete')}")
                
                # Store result for analysis
                result = {
                    'row': row_count,
                    'audio_url': audio_url,
                    'transcript': transcript,
                    'expected_answer': expected_answer,
                    'generated_answer': generated_answer,
                    'model_used': model_used,
                    'language': language,
                    'validation_correction': validation_result.get('correction', ''),
                    'km_results_count': len(km_result.get('data', [])),
                    'stage_timings': stage_timings,
                    'api_type': 'SSE' if use_sse else 'Regular',
                    'success': True
                }
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process row {row_count}: {e}")
                result = {
                    'row': row_count,
                    'audio_url': audio_url,
                    'transcript': transcript,
                    'expected_answer': expected_answer,
                    'generated_answer': '',
                    'model_used': '',
                    'language': language,
                    'validation_correction': '',
                    'km_results_count': 0,
                    'stage_timings': {},
                    'api_type': 'SSE' if use_sse else 'Regular',
                    'success': False,
                    'error': str(e)
                }
                results.append(result)
    
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Total rows processed: {len(results)}")
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    logger.info(f"Successful requests: {len(successful)}")
    logger.info(f"Failed requests: {len(failed)}")
    
    if failed:
        logger.info("\nFailed requests:")
        for result in failed:
            logger.info(f"  Row {result['row']}: {result.get('error', 'Unknown error')}")
    
    return results

def main():
    """Main function to run the test"""
    import sys
    
    # Check command line arguments for SSE mode
    use_sse = '--sse' in sys.argv
    
    csv_file_path = os.path.join(os.path.dirname(__file__), 'test.csv')
    
    logger.info("Starting Answer API Test")
    if use_sse:
        logger.info(f"SSE API Endpoint: {ANSWER_SSE_ENDPOINT}")
    else:
        logger.info(f"Regular API Endpoint: {ANSWER_ENDPOINT}")
    logger.info(f"Organization ID: {ORG_ID}")
    logger.info(f"CSV File: {csv_file_path}")
    
    try:
        results = test_answer_api_from_csv(csv_file_path, use_sse=use_sse)
        
        # Optionally save results to a JSON file
        suffix = '_sse' if use_sse else ''
        output_file = os.path.join(os.path.dirname(__file__), f'test_results{suffix}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to: {output_file}")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")

if __name__ == "__main__":
    main()