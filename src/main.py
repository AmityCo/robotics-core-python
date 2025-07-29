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

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ARC2 Server", version="1.0.0")

# Add CORS middleware to allow requests from arc2_live
app.add_middleware(
    CORSMiddleware,
    **config.get_cors_settings()
)

class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    org_id: str  # Organization configuration ID

@app.get("/")
async def root():
    return {"message": "ARC Core Server is running", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2025-07-08T00:00:00Z"}

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