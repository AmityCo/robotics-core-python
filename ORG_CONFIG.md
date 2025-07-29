# Organization Configuration Module (OrgConfig)

This module provides functionality to load organization-specific configuration data from AWS DynamoDB. It uses the `configId` as the query key and parses the `configValue` field containing JSON configuration data.

## Features

- **DynamoDB Integration**: Connects to AWS DynamoDB to fetch organization configurations
- **Type Safety**: Uses Pydantic models for data validation and type checking  
- **Language Support**: Handles multiple localization configurations per organization
- **Configuration Parsing**: Automatically parses and validates complex JSON configuration structures
- **Helper Methods**: Provides convenient methods to access language-specific configurations

## Setup

### 1. Install Dependencies

The module requires `boto3` for AWS DynamoDB access. Install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. AWS Configuration

Configure your AWS credentials using one of these methods:

**Option A: AWS CLI**
```bash
aws configure
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: IAM Roles** (recommended for production)
Use IAM roles when running on EC2, Lambda, or other AWS services.

### 3. DynamoDB Table Structure

Ensure your DynamoDB table has the following structure:

- **Table Name**: `OrganizationConfigs` (configurable)
- **Partition Key**: `configId` (String)
- **Required Field**: `configValue` containing the JSON configuration data

## Usage

### Basic Usage

```python
from src.org_config import load_org_config

# Load configuration by ID
config_id = "45f9aacfe37ff6c7e072326c600a3b60"
config = load_org_config(config_id)

if config:
    print(f"Organization: {config.displayName}")
    print(f"KM ID: {config.kmId}")
    print(f"Default Language: {config.defaultPrimaryLanguage}")
else:
    print("Configuration not found")
```

### Advanced Usage

```python
from src.org_config import OrgConfig

# Initialize with custom table name and region
org_config = OrgConfig(
    table_name="MyOrgConfigs",
    region_name="ap-southeast-1"
)

# Load configuration
config = org_config.load_config(config_id)

if config:
    # Get language-specific configuration
    en_config = org_config.get_localization_by_language(config, "en-US")
    th_config = org_config.get_localization_by_language(config, "th-TH")
    
    # Get default language configuration
    default_config = org_config.get_default_localization(config)
    
    # Get all available languages
    languages = org_config.get_available_languages(config)
    print(f"Supported languages: {languages}")
```

## Configuration Structure

The module expects the following JSON structure in the `configValue` field:

```json
[
    {
        "kmId": "5473",
        "configId": "45f9aacfe37ff6c7e072326c600a3b60",
        "displayName": "Siam-Piwat",
        "networkId": "66cef064ffce05001cafe0f1",
        "defaultPrimaryLanguage": "en-US",
        "gemini": {
            "key": "API_KEY",
            "validatorEnabled": true,
            "validatorTranscriptPromptTemplateUrl": "...",
            "validatorSystemPromptTemplateUrl": "..."
        },
        "localization": [
            {
                "displayName": "English",
                "icon": "https://example.com/flags/us.png",
                "language": "en-US",
                "assistantId": "4051",
                "assistantKey": "...",
                "validatorTranscriptPromptTemplateUrl": "...",
                "validatorSystemPromptTemplateUrl": "..."
            }
        ],
        "conversation": {
            "answerStrategy": "TAG"
        },
        "cameraActivation": {
            "enabled": true
        },
        "interruption": {
            "enabled": true,
            "dynamicThreshold": {
                "enabled": false,
                "delta": 1000
            },
            "minimum": 40000,
            "maximum": 100000,
            "span": 500,
            "debounce": 3000
        },
        "quickReplies": [...],
        "state": {...},
        "resources": {...},
        "tts": {...},
        "theme": {...},
        "feedback": {...},
        "shelf": {...}
    }
]
```

## Key Configuration Fields

### Core Settings
- `kmId`: Knowledge Management system ID
- `configId`: Unique configuration identifier
- `displayName`: Human-readable organization name
- `defaultPrimaryLanguage`: Default language code (e.g., "en-US")

### Gemini AI Settings
- `gemini.key`: Gemini API key
- `gemini.validatorEnabled`: Whether validation is enabled
- `gemini.validatorTranscriptPromptTemplateUrl`: URL for transcript validation prompts
- `gemini.validatorSystemPromptTemplateUrl`: URL for system validation prompts

### Localization
- `localization[]`: Array of language-specific configurations
- Each localization includes:
  - `language`: Language code (e.g., "en-US", "th-TH")
  - `displayName`: Language display name
  - `assistantId`: Language-specific assistant ID
  - `assistantKey`: Language-specific assistant key
  - `validatorTranscriptPromptTemplateUrl`: Language-specific validation URLs

### Other Settings
- `conversation.answerStrategy`: Answer generation strategy
- `cameraActivation.enabled`: Camera feature toggle
- `interruption`: Voice interruption settings
- `quickReplies`: Predefined quick reply configurations
- `theme`: UI theme colors and styling
- `resources`: Avatar and multimedia resources
- `tts`: Text-to-speech configuration
- `feedback`: User feedback form configuration

## Error Handling

The module provides comprehensive error handling:

```python
try:
    config = load_org_config(config_id)
except NoCredentialsError:
    print("AWS credentials not found")
except ClientError as e:
    print(f"DynamoDB error: {e}")
except ValueError as e:
    print(f"Invalid configuration data: {e}")
```

## Testing

Run the test script to verify functionality:

```bash
python test_org_config.py
```

The test script will:
1. Validate the configuration data structure
2. Attempt to load configuration from DynamoDB
3. Display configuration details if successful
4. Provide troubleshooting tips if errors occur

## Integration with Existing Code

The OrgConfig module can be integrated into your existing FastAPI application:

```python
from src.org_config import load_org_config

@app.post("/api/v1/answer")
async def answer(request: AnswerRequest):
    # Load organization-specific configuration
    org_config = load_org_config(request.org_config_id)
    
    if not org_config:
        raise HTTPException(status_code=404, detail="Organization configuration not found")
    
    # Use organization-specific settings
    gemini_api_key = org_config.gemini.key
    km_id = org_config.kmId
    
    # Get language-specific assistant settings
    localization = get_localization_by_language(org_config, request.language)
    if localization:
        assistant_id = localization.assistantId
        assistant_key = localization.assistantKey
    
    # Continue with your existing logic...
```

## Security Considerations

- **API Keys**: The configuration contains sensitive API keys. Ensure proper AWS IAM permissions.
- **Access Control**: Limit DynamoDB access to authorized applications only.
- **Encryption**: Consider encrypting sensitive fields in DynamoDB.
- **Logging**: Avoid logging sensitive configuration data like API keys.

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Configure AWS credentials properly
   - Check IAM permissions for DynamoDB access

2. **Table Not Found**
   - Verify table name and region
   - Ensure table exists in the specified AWS account

3. **Configuration Not Found**
   - Check the `configId` value
   - Verify the item exists in DynamoDB

4. **JSON Parse Error**
   - Validate the JSON structure in `configValue`
   - Ensure all required fields are present

5. **Validation Error**
   - Check that the configuration matches the expected Pydantic model structure
   - Review any missing or incorrectly typed fields
