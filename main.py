from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uvicorn
import logging
import base64
from src.app_config import config
from src.models import ChatMessage
from src.answer_flow_sse import execute_answer_flow_sse, get_validation_prompts_from_org_config
from src.telemetry import configure_telemetry, instrument_fastapi
from src.audio_helper import AudioProcessor

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Silence Azure Core logging
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.storage').setLevel(logging.WARNING)
logging.getLogger('azure.monitor.opentelemetry.exporter.export._base').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize telemetry before creating the FastAPI app
configure_telemetry()

app = FastAPI(title="ARC2 Server", version="1.0.0")

# Instrument FastAPI for telemetry
instrument_fastapi(app)

# Add CORS middleware to allow requests from arc2_live
app.add_middleware(
    CORSMiddleware,
    **config.get_cors_settings()
)

class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: Optional[str] = None  # Made optional to support text-only requests
    org_id: str  # Organization ID (partition key)
    config_id: str  # Configuration ID within the organization
    chat_history: List[ChatMessage] = []  # Previous conversation history
    keywords: Optional[List[str]] = None  # If provided, skip validation and use directly

class AudioTrimRequest(BaseModel):
    audio_url: HttpUrl
    silence_threshold: Optional[float] = 0.05  # Energy threshold for silence detection (0.05 = 5% of max energy)
    
class AudioTrimResponse(BaseModel):
    status: str
    original_size_bytes: int
    trimmed_size_bytes: int
    size_reduction_bytes: int
    size_reduction_percent: float
    trimmed_audio_base64: str
    audio_format: str

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
    Supports both audio-based and text-only requests (when base64_audio is not provided)
    If keywords are provided directly, validation step is skipped
    """
    return StreamingResponse(
        execute_answer_flow_sse(
            transcript=request.transcript,
            language=request.language,
            base64_audio=request.base64_audio,
            org_id=request.org_id,
            config_id=request.config_id,
            chat_history=request.chat_history or [],
            keywords=request.keywords
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/api/v1/audio/trim", response_model=AudioTrimResponse)
async def trim_audio_from_url(request: AudioTrimRequest):
    """
    Download audio from URL and return the trimmed version with silence removed.
    Automatically trims silence from the beginning, middle, and end of the audio.
    
    Args:
        request: AudioTrimRequest containing the audio URL and optional silence threshold
        
    Returns:
        AudioTrimResponse with trimmed audio data and statistics
        
    Raises:
        HTTPException: If audio download fails or processing encounters an error
    """
    try:
        logger.info(f"Starting audio trimming for URL: {request.audio_url}")
        
        # Download audio from URL
        try:
            # Use requests instead of httpx for now to avoid dependency issues
            import requests
            response = requests.get(str(request.audio_url), timeout=30)
            response.raise_for_status()
            audio_data = response.content
            logger.info(f"Downloaded audio: {len(audio_data)} bytes from {request.audio_url}")
        except requests.RequestException as e:
            logger.error(f"Failed to download audio from {request.audio_url}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error downloading audio: {str(e)}")
        
        # Validate audio data
        if not audio_data:
            raise HTTPException(status_code=400, detail="Downloaded audio file is empty")
        
        if len(audio_data) < 1000:  # Less than 1KB is likely not valid audio
            raise HTTPException(status_code=400, detail="Downloaded audio file is too small to be valid")
        
        # Check if it's a WAV file and extract PCM data if needed
        try:
            if audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
                # It's a WAV file, extract PCM data
                import wave
                import io
                
                wav_buffer = io.BytesIO(audio_data)
                with wave.open(wav_buffer, 'rb') as wav_file:
                    # Validate WAV format
                    channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()
                    framerate = wav_file.getframerate()
                    
                    logger.info(f"WAV file info: {channels} channels, {sample_width} bytes/sample, {framerate} Hz")
                    
                    # For now, we expect mono 16-bit audio
                    if channels != 1:
                        raise HTTPException(status_code=400, detail=f"Only mono audio is supported, got {channels} channels")
                    if sample_width != 2:
                        raise HTTPException(status_code=400, detail=f"Only 16-bit audio is supported, got {sample_width * 8}-bit")
                    
                    # Extract PCM data
                    pcm_data = wav_file.readframes(wav_file.getnframes())
                    logger.info(f"Extracted PCM data: {len(pcm_data)} bytes")
            else:
                # Assume it's raw PCM data
                pcm_data = audio_data
                logger.info(f"Treating as raw PCM data: {len(pcm_data)} bytes")
        except Exception as e:
            logger.error(f"Error processing audio format: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Error processing audio format: {str(e)}")
        
        # Create audio processor and trim silence
        try:
            audio_processor = AudioProcessor(
                silence_threshold=request.silence_threshold, 
                enable_trimming=True
            )
            trimmed_pcm_data = audio_processor.trim_silence(pcm_data)
            logger.info(f"Audio trimming completed: {len(pcm_data)} -> {len(trimmed_pcm_data)} bytes")
        except Exception as e:
            logger.error(f"Error trimming audio: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error trimming audio: {str(e)}")
        
        # Convert trimmed PCM back to WAV format for output
        try:
            trimmed_wav_data = audio_processor.convert_pcm_to_wav(trimmed_pcm_data)
            logger.info(f"Converted to WAV format: {len(trimmed_wav_data)} bytes")
        except Exception as e:
            logger.error(f"Error converting to WAV: {str(e)}")
            # If conversion fails, use raw PCM
            trimmed_wav_data = trimmed_pcm_data
            logger.info("Using raw PCM data as fallback")
        
        # Encode to base64
        try:
            trimmed_base64 = base64.b64encode(trimmed_wav_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding to base64: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error encoding audio to base64: {str(e)}")
        
        # Calculate statistics
        original_size = len(audio_data)
        trimmed_size = len(trimmed_wav_data)
        size_reduction = original_size - trimmed_size
        size_reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"Audio trimming completed successfully: {original_size} -> {trimmed_size} bytes "
                   f"({size_reduction_percent:.1f}% reduction)")
        
        return AudioTrimResponse(
            status="success",
            original_size_bytes=original_size,
            trimmed_size_bytes=trimmed_size,
            size_reduction_bytes=size_reduction,
            size_reduction_percent=round(size_reduction_percent, 2),
            trimmed_audio_base64=trimmed_base64,
            audio_format="wav" if trimmed_wav_data.startswith(b'RIFF') else "raw-16khz-16bit-mono-pcm"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in audio trimming API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    if config.DEBUG:
        # Use import string for reload to work properly
        uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
    else:
        # Use app object for production
        uvicorn.run(app, host=config.HOST, port=config.PORT, reload=False)