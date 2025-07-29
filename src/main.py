from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import requests
import uvicorn
import logging
import base64
import json
import os
import asyncio
from datetime import datetime
from src.app_config import config
from src.km_search import (
    KMSearchRequest, 
    KMBatchSearchRequest, 
    KMSearchResponse,
    single_search_km,
    batch_search_km
)
from src.validator import GeminiValidationRequest, validate_with_gemini
from src.generator import OpenAIGenerationRequest, generate_answer_with_openai
from src.org_config import load_org_config
from src.answer_flow_sse import execute_answer_flow_sse, get_validation_prompts_from_org_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ARC2 Server", version="1.0.0")

# Add CORS middleware to allow requests from arc2_live
app.add_middleware(
    CORSMiddleware,
    **config.get_cors_settings()
)

class GeminiValidationRequestLegacy(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    validation_system_prompt: str
    validation_user_prompt: str
    model: str
    generation_config: Dict[str, Any]
    gemini_api_key: str

class ValidateAndSearchRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    validation_system_prompt: str
    validation_user_prompt: str
    model: str
    generation_config: Dict[str, Any]
    gemini_api_key: str
    km_id: str
    km_token: str
    max_results: int = 10

class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    org_id: str  # Organization configuration ID

class GeminiValidationResponse(BaseModel):
    correction: str
    search_terms: Optional[List[str]] = None

def log_validation_request(request: GeminiValidationRequestLegacy, response_data: Dict[str, Any] = None):
    """
    Log validation request data and audio file to the validation logs folder
    """
    if not config.LOG_VALIDATION_REQUESTS:
        return
    
    try:
        # Create logs directory if it doesn't exist
        log_dir = config.VALIDATION_LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        
        # Save audio file
        audio_filename = f"audio_{timestamp}.wav"
        audio_path = os.path.join(log_dir, audio_filename)
        
        try:
            # Decode base64 audio and save to file
            audio_data = base64.b64decode(request.base64_audio)
            with open(audio_path, 'wb') as audio_file:
                audio_file.write(audio_data)
            logger.info(f"Audio saved to: {audio_path}")
        except Exception as e:
            logger.error(f"Failed to save audio file: {str(e)}")
            audio_filename = None
        
        # Prepare request data for logging (excluding base64 audio to save space)
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "request_data": {
                "transcript": request.transcript,
                "language": request.language,
                "validation_system_prompt": request.validation_system_prompt,
                "validation_user_prompt": request.validation_user_prompt,
                "model": request.model,
                "generation_config": request.generation_config,
                "audio_file": audio_filename,
                "audio_size_bytes": len(request.base64_audio) if request.base64_audio else 0
            },
            "response_data": response_data
        }
        
        # Save request data as JSON
        data_filename = f"request_{timestamp}.json"
        data_path = os.path.join(log_dir, data_filename)
        
        with open(data_path, 'w', encoding='utf-8') as data_file:
            json.dump(log_data, data_file, indent=2, ensure_ascii=False)
        
        logger.info(f"Validation request logged: {data_path}")
        
    except Exception as e:
        logger.error(f"Failed to log validation request: {str(e)}")

@app.get("/")
async def root():
    return {"message": "ARC2 Server is running", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2025-07-08T00:00:00Z"}

@app.post("/api/v1/gemini/validate", response_model=Dict[str, Any])
async def validate_with_gemini_endpoint(request: GeminiValidationRequestLegacy):
    """
    Validate transcript and audio with Gemini API
    """
    try:
        # Convert to the new validator request format
        validator_request = GeminiValidationRequest(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=request.validation_system_prompt,
            validation_user_prompt=request.validation_user_prompt,
            model=request.model,
            generation_config=request.generation_config,
            gemini_api_key=request.gemini_api_key
        )
        
        # Use the refactored validator
        result = validate_with_gemini(validator_request)
        
        # Log the validation request and response
        log_validation_request(request, {
            "correction": result.correction,
            "searchTerms": result.search_terms
        })
        
        return {
            "correction": result.correction,
            "searchTerms": result.search_terms
        }

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        # Log the failed request
        log_validation_request(request, {"error": f"Request error: {str(e)}"})
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Log the failed request
        log_validation_request(request, {"error": f"Unexpected error: {str(e)}"})
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.post("/api/v1/km/search", response_model=KMSearchResponse)
async def search_knowledge_management(request: KMSearchRequest):
    """
    Search the knowledge management system via Amity Solutions API
    """
    try:
        return single_search_km(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"KM search failed: {str(e)}")

@app.post("/api/v1/km/batch-search", response_model=KMSearchResponse)
async def batch_search_knowledge_management(request: KMBatchSearchRequest):
    """
    Batch search the knowledge management system via Amity Solutions API
    Performs multiple searches, deduplicates, and returns top results sorted by reranker score
    """
    try:
        return batch_search_km(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch KM search failed: {str(e)}")

@app.post("/api/v1/validate-and-search", response_model=Dict[str, Any])
async def validate_and_search(request: ValidateAndSearchRequest):
    """
    Combined endpoint: Validate transcript and audio with Gemini, then perform KM batch search
    """
    try:
        # First, perform Gemini validation using the refactored validator
        validator_request = GeminiValidationRequest(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=request.validation_system_prompt,
            validation_user_prompt=request.validation_user_prompt,
            model=request.model,
            generation_config=request.generation_config,
            gemini_api_key=request.gemini_api_key
        )
        
        validation_result = validate_with_gemini(validator_request)

        # Now perform KM batch search using the validation result
        search_queries: List[str] = []
        
        # Add correction (main query)
        if validation_result.correction:
            search_queries.append(validation_result.correction)
        
        # Add translated question query combined with its keywords
        search_terms = validation_result.search_terms
        if search_terms.get("translatedQuestion", {}).get("query"):
            translated_query = search_terms["translatedQuestion"]["query"]
            translated_keywords = search_terms["translatedQuestion"].get("keywords", [])
            combined_translated_query = " ".join([translated_query] + translated_keywords)
            search_queries.append(combined_translated_query)
        
        # Add all search queries combined with their keywords
        if search_terms.get("searchQueries") and isinstance(search_terms["searchQueries"], list):
            for search_query in search_terms["searchQueries"]:
                if search_query.get("query"):
                    query = search_query["query"]
                    keywords = search_query.get("keywords", [])
                    combined_query = " ".join([query] + keywords)
                    search_queries.append(combined_query)

        # Remove duplicates and empty strings
        unique_queries = list(set([q for q in search_queries if q and q.strip()]))
        
        logger.info(f"Performing KM batch search with queries: {unique_queries}")

        # Perform KM batch search
        km_request = KMBatchSearchRequest(
            queries=unique_queries,
            language=request.language,
            km_id=request.km_id,
            km_token=request.km_token,
            max_results=request.max_results
        )
        
        km_result = batch_search_km(km_request)
        
        # Log the successful request
        log_validation_request(GeminiValidationRequestLegacy(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=request.validation_system_prompt,
            validation_user_prompt=request.validation_user_prompt,
            model=request.model,
            generation_config=request.generation_config,
            gemini_api_key=request.gemini_api_key
        ), {
            "correction": validation_result.correction,
            "searchTerms": validation_result.search_terms
        })
        
        # Return combined result
        return {
            "validation_result": {
                "correction": validation_result.correction,
                "searchTerms": validation_result.search_terms
            },
            "km_result": km_result.dict()
        }

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        log_validation_request(GeminiValidationRequestLegacy(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=request.validation_system_prompt,
            validation_user_prompt=request.validation_user_prompt,
            model=request.model,
            generation_config=request.generation_config,
            gemini_api_key=request.gemini_api_key
        ), {"error": f"Request error: {str(e)}"})
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        log_validation_request(GeminiValidationRequestLegacy(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=request.validation_system_prompt,
            validation_user_prompt=request.validation_user_prompt,
            model=request.model,
            generation_config=request.generation_config,
            gemini_api_key=request.gemini_api_key
        ), {"error": f"Unexpected error: {str(e)}"})
        raise HTTPException(status_code=500, detail=f"Validate and search failed: {str(e)}")

@app.post("/api/v1/answer", response_model=Dict[str, Any])
async def answer(request: AnswerRequest):
    """
    Complete pipeline: Validate with Gemini, search KM, then generate answer with OpenAI GPT
    Uses organization configuration from DynamoDB to get all necessary parameters
    """
    try:
        # Load organization configuration
        org_config = load_org_config(request.org_id)
        if not org_config:
            raise HTTPException(status_code=404, detail=f"Organization configuration not found for ID: {request.org_id}")
        
        logger.info(f"Loaded org config for: {org_config.displayName} (kmId: {org_config.kmId})")
        
        # Get validation prompts from org config
        validation_system_prompt, validation_user_prompt = get_validation_prompts_from_org_config(org_config, request.language)
        
        # Step 1: Perform Gemini validation using the refactored validator
        validator_request = GeminiValidationRequest(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            validation_system_prompt=validation_system_prompt,
            validation_user_prompt=validation_user_prompt,
            model="gemini-2.5-flash",  # Use default model from Gemini config
            generation_config={
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 64,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json"
            },
            gemini_api_key=org_config.gemini.key
        )
        
        validation_result = validate_with_gemini(validator_request)
        logger.info(f"Validation completed: {validation_result.correction}")

        # Step 2: Perform KM batch search using the validation result
        search_queries: List[str] = []
        
        # Add correction (main query)
        if validation_result.correction:
            search_queries.append(validation_result.correction)
        
        # Add translated question query combined with its keywords
        search_terms = validation_result.search_terms
        if search_terms.get("translatedQuestion", {}).get("query"):
            translated_query = search_terms["translatedQuestion"]["query"]
            translated_keywords = search_terms["translatedQuestion"].get("keywords", [])
            combined_translated_query = " ".join([translated_query] + translated_keywords)
            search_queries.append(combined_translated_query)
        
        # Add all search queries combined with their keywords
        if search_terms.get("searchQueries") and isinstance(search_terms["searchQueries"], list):
            for search_query in search_terms["searchQueries"]:
                if search_query.get("query"):
                    query = search_query["query"]
                    keywords = search_query.get("keywords", [])
                    combined_query = " ".join([query] + keywords)
                    search_queries.append(combined_query)

        # Remove duplicates and empty strings
        unique_queries = list(set([q for q in search_queries if q and q.strip()]))
        
        logger.info(f"Performing KM batch search with queries: {unique_queries}")

        # Perform KM batch search using org config
        km_request = KMBatchSearchRequest(
            queries=unique_queries,
            language=request.language,
            km_id=org_config.kmId,
            km_token=config.ASAP_KM_TOKEN,  # KM token from environment config
            max_results=10  # Default max results
        )
        
        km_result = batch_search_km(km_request)
        logger.info(f"KM search completed: found {len(km_result.data)} results")

        # Step 3: Generate answer using OpenAI GPT with the KM results
        generation_request = OpenAIGenerationRequest(
            org_config_id=request.org_id
        )
        
        generation_result = generate_answer_with_openai(
            generation_request, 
            km_result, 
            {
                "correction": validation_result.correction,
                "searchTerms": validation_result.search_terms
            }
        )
        logger.info(f"Answer generation completed using {generation_result.model_used}")
        
        # Return comprehensive result
        return {
            "validation_result": {
                "correction": validation_result.correction,
                "searchTerms": validation_result.search_terms
            },
            "km_result": km_result.dict(),
            "answer": generation_result.answer,
            "model_used": generation_result.model_used
        }

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")

@app.post("/api/v1/answer-sse")
async def answer_sse(request: AnswerRequest):
    """
    Complete pipeline with Server-Sent Events: Validate with Gemini, search KM, then generate answer with OpenAI GPT
    Sends data stage by stage via SSE for real-time progress updates
    """
    return StreamingResponse(
        execute_answer_flow_sse(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            org_id=request.org_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    if config.DEBUG:
        # Use import string for reload to work properly
        uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
    else:
        # Use app object for production
        uvicorn.run(app, host=config.HOST, port=config.PORT, reload=False)