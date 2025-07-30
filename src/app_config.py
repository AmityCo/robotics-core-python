import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

class AppConfig:
    """Configuration class for ARC2 Server"""
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Timeout settings
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Logging settings
    LOG_VALIDATION_REQUESTS = os.getenv("LOG_VALIDATION", "true").lower() == "true"
    VALIDATION_LOG_DIR = os.getenv("VALIDATION_LOG_DIR", "validation_logs")
    
    # External API URLs
    GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    OPENAI_API_BASE_URL = "https://api.openai.com/v1"
    AMITY_KM_API_URL = "https://api.amitysolutions.com/api/v1/km/search"
    
    # AWS settings
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # DynamoDB settings
    DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "RoboticConfigureTable-prod")
    DYNAMODB_REGION = os.getenv("DYNAMODB_REGION", "ap-southeast-1")
    
    # Azure Storage settings for TTS caching
    AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    TTS_CACHE_CONTAINER_NAME = os.getenv("TTS_CACHE_CONTAINER_NAME", "tts-cache")
    
    # KM API settings
    ASAP_KM_TOKEN = os.getenv("ASAP_KM_TOKEN", "")
    
    @classmethod
    def get_cors_settings(cls) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            "allow_origins": cls.CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

config = AppConfig()
