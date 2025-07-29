# AnswerRequest Improvement Summary

## Overview
The `AnswerRequest` class has been simplified to only require essential input parameters, while all configuration-dependent parameters are now loaded from the organization configuration in DynamoDB.

## Changes Made

### 1. Simplified AnswerRequest Model
**Before:**
```python
class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    validation_system_prompt: str
    validation_user_prompt: str
    org_config_id: str
    generation_system_prompt: Optional[str] = None
    generation_user_prompt: Optional[str] = None
    gemini_model: str
    gemini_generation_config: Dict[str, Any]
    gemini_api_key: str
    openai_model: Optional[str] = None
    openai_temperature: Optional[float] = None
    openai_max_tokens: Optional[int] = None
    openai_api_key: Optional[str] = None
    km_id: str
    km_token: str
    max_results: int = 10
```

**After:**
```python
class AnswerRequest(BaseModel):
    transcript: str
    language: str
    base64_audio: str
    org_id: str  # Organization configuration ID
```

### 2. New Helper Function
Added `get_validation_prompts_from_org_config()` function that:
- Loads validation prompts from organization configuration URLs
- Tries localization-specific URLs first, then falls back to Gemini config URLs
- Handles HTTP requests with proper error handling and timeouts
- Supports multiple languages with fallback to default primary language

### 3. Updated Answer Endpoint Logic
The `/api/v1/answer` endpoint now:
- Loads organization configuration using `load_org_config(request.org_id)`
- Extracts validation prompts from org config URLs
- Uses org config's Gemini API key and default model settings
- Uses org config's Knowledge Management ID (`kmId`)
- Uses environment-configured KM token from `config.KM_TOKEN`

### 4. Environment Configuration Added
Added to `app_config.py`:
```python
KM_TOKEN = os.getenv("ARC2_KM_TOKEN", "")
```

## Benefits

### 1. Simplified API Interface
- Clients only need to provide 4 essential parameters
- Reduced complexity in API integration
- Less prone to configuration errors

### 2. Centralized Configuration Management
- All organization-specific settings are managed in DynamoDB
- Consistent configuration across all services
- Easy to update prompts and settings without code changes

### 3. Better Security
- API keys are stored securely in organization configuration
- No need to pass sensitive information in API requests
- Centralized credential management

### 4. Language Support
- Automatic selection of language-specific prompts
- Fallback mechanism for unsupported languages
- Consistent multilingual behavior

## Usage Example

**Before (complex request):**
```json
{
  "transcript": "Hello, can you help me?",
  "language": "en-US", 
  "base64_audio": "dGVzdCBhdWRpbw==",
  "validation_system_prompt": "You are a helpful assistant...",
  "validation_user_prompt": "Please validate this transcript...",
  "org_config_id": "45f9aacfe37ff6c7e072326c600a3b60",
  "gemini_model": "gemini-1.5-flash",
  "gemini_generation_config": {...},
  "gemini_api_key": "AIza...",
  "km_id": "km_123",
  "km_token": "token_456",
  "max_results": 10
}
```

**After (simple request):**
```json
{
  "transcript": "Hello, can you help me?",
  "language": "en-US",
  "base64_audio": "dGVzdCBhdWRpbw==", 
  "org_id": "45f9aacfe37ff6c7e072326c600a3b60"
}
```

## Configuration Requirements

### Environment Variables
- `ARC2_KM_TOKEN`: Knowledge Management API token
- `ARC2_DYNAMODB_TABLE_NAME`: DynamoDB table name (default: "RoboticConfigureTable-prod")
- `ARC2_DYNAMODB_REGION`: AWS region (default: "ap-southeast-1")

### Organization Configuration Structure
The organization configuration in DynamoDB must include:
- `kmId`: Knowledge Management system ID
- `gemini.key`: Gemini API key
- `gemini.validatorEnabled`: Whether validation is enabled
- `localization[].validatorSystemPromptTemplateUrl`: Language-specific system prompt URLs
- `localization[].validatorTranscriptPromptTemplateUrl`: Language-specific user prompt URLs
- `defaultPrimaryLanguage`: Fallback language code

## Migration Notes
- Existing clients need to be updated to use the new simplified request format
- All organization configurations must be properly set up in DynamoDB
- Environment variable `ARC2_KM_TOKEN` must be configured
- Prompt template URLs in organization configuration must be accessible and return valid prompt text

## Testing
The changes have been validated to ensure:
- ✅ Request validation works correctly
- ✅ Only required fields are accepted
- ✅ No extra optional fields are included
- ✅ Pydantic model structure is correct
