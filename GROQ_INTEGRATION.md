# Groq Integration Documentation

This document describes the Groq AI model integration added to the robotics-core-python project.

## Overview

The system now supports Groq AI models in addition to OpenAI models. When a `generatorModel` in the `LocalizationConfig` starts with `groq/`, the system will automatically use the Groq API instead of OpenAI.

## Configuration

### 1. Organization Configuration

Add the Groq API key to your organization configuration in DynamoDB:

```json
{
  "configId": "your_config_id",
  "displayName": "Your Organization",
  // ... other config fields
  "groq": {
    "apiKey": "gsk_your_actual_groq_api_key_here"
  },
  "localization": [
    {
      "displayName": "English",
      "icon": "🇺🇸",
      "language": "en-US",
      "assistantId": "test_assistant",
      "assistantKey": "test_key",
      "generatorModel": "groq/openai/gpt-oss-20b",  // Groq model
      "systemPrompt": "You are a helpful assistant...",
      // ... other localization fields
    },
    {
      "displayName": "Thai",
      "icon": "🇹🇭",
      "language": "th-TH",
      "assistantId": "test_assistant_th",
      "assistantKey": "test_key_th",
      "generatorModel": "gpt-4",  // Regular OpenAI model
      // ... other localization fields
    }
  ]
}
```

### 2. Environment Setup

Make sure the `groq` package is installed:

```bash
pip install groq==0.12.0
```

## Usage

### Detecting Groq Models

Use the `is_groq_model()` function to check if a model string represents a Groq model:

```python
from src.groq_handler import is_groq_model

model = "groq/openai/gpt-oss-20b"
if is_groq_model(model):
    print("This is a Groq model")
```

### Using Groq Handler

```python
from src.groq_handler import GroqHandler, is_groq_model
from src.org_config import load_org_config

# Load organization configuration
config = await load_org_config("your_org_id", "your_config_id")

# Get localization for a specific language
localization = config.get_localization_by_language(config, "en-US")

# Check if the generator model is a Groq model
if is_groq_model(localization.generatorModel):
    # Create Groq handler
    groq_handler = GroqHandler(config)
    
    # Prepare messages (system prompts will be automatically combined)
    messages = [
        {"role": "system", "content": localization.systemPrompt},
        {"role": "user", "content": "User's question here"}
    ]
    
    # Generate response with streaming
    async for chunk in groq_handler.generate_completion_stream(
        model=localization.generatorModel,
        messages=messages,
        temperature=0.7
    ):
        print(chunk, end="")
        
    # Or generate without streaming
    response = await groq_handler.generate_completion(
        model=localization.generatorModel,
        messages=messages,
        temperature=0.7
    )
else:
    # Use regular OpenAI or other model handlers
    pass
```

## Key Features

### 1. Model Format

Groq models should be specified in the format: `groq/model_name`

Examples:
- `groq/openai/gpt-oss-20b`
- `groq/llama-3.1-8b-instant`
- `groq/mixtral-8x7b-32768`

### 2. System Prompt Combination

Groq API only supports one system prompt per conversation. The `GroqHandler` automatically combines multiple system prompts into a single system message.

Input:
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "system", "content": "Always be polite and informative."},
    {"role": "user", "content": "Hello!"}
]
```

Output:
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant.\n\nAlways be polite and informative."},
    {"role": "user", "content": "Hello!"}
]
```

### 3. Streaming Support

Both streaming and non-streaming completions are supported:

```python
# Streaming
async for chunk in groq_handler.generate_completion_stream(model, messages):
    print(chunk, end="")

# Non-streaming
response = await groq_handler.generate_completion(model, messages)
```

## Files Modified/Added

1. **src/org_config.py**: Added `GroqConfig` class and integration into `OrgConfigData`
2. **src/groq_handler.py**: New file containing the Groq API integration
3. **requirements.txt**: Added `groq==0.12.0` dependency
4. **test_groq_integration.py**: Test file demonstrating the integration

## Error Handling

The `GroqHandler` includes comprehensive error handling and logging:

- API key validation
- Network error handling
- Model availability checking
- Detailed error messages with context

## Testing

Run the integration test to verify the setup:

```bash
python test_groq_integration.py
```

This will test:
- Model detection logic
- System prompt combination
- Model name extraction
- Configuration loading

## Production Deployment

1. Ensure your Groq API key is properly configured in the organization settings
2. Update the `generatorModel` field for localizations that should use Groq
3. The system will automatically detect and route requests to the appropriate handler

## API Rate Limits

Be aware of Groq API rate limits and implement appropriate retry logic if needed. The current implementation does not include automatic retry mechanisms.
