"""
Organization Configuration Module
Loads configuration data from AWS DynamoDB based on organization ID with caching
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from .cache_config import create_cache
from .dynamodb_handler import DynamoDBHandler
from .app_config import config as app_config

logger = logging.getLogger(__name__)

# Create dedicated in-memory cache for org config
org_config_cache = create_cache("org_config_memory", backend="mem://", enabled=True)

class LocalizationConfig(BaseModel):
    displayName: str
    icon: str
    language: str
    assistantId: str
    assistantKey: str
    systemPrompt: Optional[str] = """You are a helpful AI assistant. Please provide accurate and helpful responses to user questions.
    Context: {context}
    Current date & time: {current_time}
    """
    affirmationPrompt: Optional[str] = "User Question: {question}"
    validatorTranscriptPromptTemplateUrl: Optional[str] = None
    validatorSystemPromptTemplateUrl: Optional[str] = None
    validatorModel: Optional[str] = None

class GeminiConfig(BaseModel):
    key: str
    validatorEnabled: bool
    validatorTranscriptPromptTemplateUrl: Optional[str] = None
    validatorSystemPromptTemplateUrl: Optional[str] = None

class OpenAIConfig(BaseModel):
    apiKey: str

class ConversationConfig(BaseModel):
    answerStrategy: str

class CameraActivationConfig(BaseModel):
    enabled: bool

class AudioThreshold(BaseModel):
    threadshold: int
    multiier: int
    direction: str

class AudioConfig(BaseModel):
    multiplierThreadsholds: List[AudioThreshold]
    auto_trim_silent: Optional[bool] = False

class DynamicThresholdConfig(BaseModel):
    enabled: bool
    delta: int

class InterruptionConfig(BaseModel):
    enabled: bool
    dynamicThreshold: DynamicThresholdConfig
    minimum: int
    maximum: int
    span: int
    debounce: int

class QuickReplyItem(BaseModel):
    text: str
    query: str
    action: str
    language: str

class QuickReplyLanguage(BaseModel):
    language: str
    items: List[QuickReplyItem]

class QuickReply(BaseModel):
    id: str
    quickReplies: List[QuickReplyLanguage]

class StateConfig(BaseModel):
    ads: Optional[Dict[str, Any]] = None
    init: Optional[Dict[str, Any]] = None
    greeting: Optional[Dict[str, Any]] = None
    selectLanguage: Optional[Dict[str, Any]] = None
    recording: Optional[Dict[str, Any]] = None
    processing: Optional[Dict[str, Any]] = None
    loadingReply: Optional[Dict[str, Any]] = None
    continuing: Optional[Dict[str, Any]] = None
    presenting: Optional[Dict[str, Any]] = None

class ResourcesConfig(BaseModel):
    isFullScreen: bool
    soundEffects: Optional[Dict[str, str]] = None
    avatar: Optional[Dict[str, Any]] = None

class TTSModel(BaseModel):
    language: str
    name: str
    pitch: Optional[str] = None
    rate: Optional[str] = None
    phonemeUrl: Optional[str] = None

class AzureTTSConfig(BaseModel):
    subscriptionKey: str
    lexiconURL: str
    phonemeUrl: Optional[str] = None
    models: List[TTSModel]

class TTSConfig(BaseModel):
    azure: AzureTTSConfig

class ThemeConfig(BaseModel):
    primary: str
    onPrimary: str
    secondary: str
    onSecondary: str
    tertiary: str
    onTertiary: str
    inversePrimary: str

class FeedbackFormItem(BaseModel):
    imageUrl: str
    value: int
    displayTitle: List[Dict[str, str]]

class FeedbackReason(BaseModel):
    imageUrl: str
    value: str
    displayTitle: List[Dict[str, str]]

class FeedbackConfig(BaseModel):
    imageUrl: str
    title: List[Dict[str, str]]
    form: List[FeedbackFormItem]
    reasons: List[FeedbackReason]

class ShelfConfig(BaseModel):
    start: Optional[Dict[str, Any]] = None
    hero: Optional[Dict[str, Any]] = None

class STTConfig(BaseModel):
    useAlternateLanguage: bool

class OrgConfigData(BaseModel):
    kmId: str
    configId: str
    displayName: str
    networkId: str
    onPauseStrategy: str
    linenotifyToken: Optional[str] = None
    conversation: ConversationConfig
    displayLanguageLogic: str
    gemini: GeminiConfig
    openai: OpenAIConfig
    localization: List[LocalizationConfig]
    cameraActivation: CameraActivationConfig
    audio: AudioConfig
    interruption: InterruptionConfig
    defaultPrimaryLanguage: str
    preferredMicrophoneNames: List[str]
    quickReplies: Optional[List[QuickReply]]
    state: StateConfig
    resources: ResourcesConfig
    stt: STTConfig
    tts: TTSConfig
    theme: ThemeConfig
    feedback: FeedbackConfig
    shelf: ShelfConfig

class OrgConfig:
    """
    Organization Configuration Manager
    Handles loading and parsing of organization-specific configuration from AWS DynamoDB with caching
    """
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize the OrgConfig with DynamoDB settings
        
        Args:
            table_name: Name of the DynamoDB table containing organization configurations
                       (defaults to app_config.DYNAMODB_TABLE_NAME)
            region_name: AWS region where the DynamoDB table is located
                        (defaults to app_config.DYNAMODB_REGION)
        """
        self.table_name = table_name or app_config.DYNAMODB_TABLE_NAME
        self.region_name = region_name or app_config.DYNAMODB_REGION
        self.dynamodb_handler = DynamoDBHandler(table_name=self.table_name, region_name=self.region_name)
    
    @org_config_cache.early(ttl="15m", early_ttl="3m")
    async def _load_config_from_db(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from DynamoDB with caching
        
        Args:
            org_id: The organization ID to query for (partition key in DynamoDB as configId)
            
        Returns:
            Raw configuration data if found, None if not found
        """
        logger.info(f"Loading organization config from DynamoDB for orgId: {org_id}")
        
        # Query DynamoDB using org_id as configId (the actual partition key)
        item = await self.dynamodb_handler.get_item(
            key={'configId': org_id}
        )
        
        if item is None:
            logger.warning(f"No configuration found for orgId: {org_id}")
            return None
        
        logger.info(f"Found configuration item for orgId: {org_id}")
        return item
    
    async def load_config(self, org_id: str, config_id: str) -> Optional[OrgConfigData]:
        """
        Load organization configuration from DynamoDB with caching
        
        Args:
            org_id: The organization ID to query for (stored as configId partition key in DynamoDB)
            config_id: The specific configuration ID to find within the organization's config array
            
        Returns:
            OrgConfigData object if found, None if not found
            
        Raises:
            ValueError: If the configuration data is invalid
        """
        logger.info(f"Loading organization config for orgId: {org_id}, configId: {config_id}")
        
        try:
            # Get data from cache or DynamoDB (org_id is used as the configId partition key)
            item = await self._load_config_from_db(org_id)
            
            if item is None:
                return None
            
            # Extract the configValue field
            if 'configValue' not in item:
                raise ValueError(f"No 'configValue' field found in configuration for orgId: {org_id}")
            
            config_value = item['configValue']
            
            # Parse the JSON configuration
            try:
                if isinstance(config_value, str):
                    # If configValue is stored as a JSON string
                    config_data = json.loads(config_value)
                else:
                    # If configValue is already a dict/object
                    config_data = config_value
                
                # config_data should be an array of configurations
                if not isinstance(config_data, list):
                    raise ValueError(f"Expected configValue to be an array for orgId: {org_id}")
                
                if len(config_data) == 0:
                    raise ValueError(f"Empty configuration array for orgId: {org_id}")
                
                # Find the specific config by configId
                target_config = None
                for config_item in config_data:
                    if isinstance(config_item, dict) and config_item.get('configId') == config_id:
                        target_config = config_item
                        break
                
                if target_config is None:
                    logger.warning(f"No configuration found with configId: {config_id} in orgId: {org_id}")
                    return None
                
                # Parse and validate using Pydantic model
                org_config = OrgConfigData.model_validate(target_config)
                logger.info(f"Successfully loaded and validated configuration for organization: {org_config.displayName}")
                
                return org_config
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON configuration for orgId {org_id}: {str(e)}")
                raise ValueError(f"Invalid JSON in configValue for orgId: {org_id}")
            except Exception as e:
                # Enhanced error reporting with validation details
                error_details = str(e)
                
                # Check if it's a Pydantic validation error for more specific details
                if hasattr(e, 'errors'):
                    # Pydantic ValidationError - extract detailed field errors
                    validation_errors = []
                    for error in e.errors():
                        field_path = " -> ".join(str(loc) for loc in error['loc'])
                        error_msg = error['msg']
                        error_type = error['type']
                        validation_errors.append(f"Field '{field_path}': {error_msg} (type: {error_type})")
                    
                    detailed_error = f"Validation failed with {len(validation_errors)} error(s): " + "; ".join(validation_errors)
                    logger.error(f"Failed to validate configuration data for orgId {org_id}, configId {config_id}: {detailed_error}")
                    raise ValueError(f"Invalid configuration structure for orgId: {org_id}, configId: {config_id}. {detailed_error}")
                else:
                    # Generic exception - provide basic error info
                    logger.error(f"Failed to validate configuration data for orgId {org_id}, configId {config_id}: {error_details}")
                    raise ValueError(f"Invalid configuration structure for orgId: {org_id}, configId: {config_id}. Error: {error_details}")
        
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {str(e)}")
            raise
    
    async def list_config_ids(self, org_id: str) -> List[str]:
        """
        List all available configuration IDs for an organization
        
        Args:
            org_id: The organization ID to query for (stored as configId partition key in DynamoDB)
            
        Returns:
            List of configuration IDs available in the organization
            
        Raises:
            ValueError: If the organization data is invalid
        """
        logger.info(f"Listing configuration IDs for orgId: {org_id}")
        
        try:
            # Get data from cache or DynamoDB (org_id is used as the configId partition key)
            item = await self._load_config_from_db(org_id)
            
            if item is None:
                logger.warning(f"No organization found for orgId: {org_id}")
                return []
            
            # Extract the configValue field
            if 'configValue' not in item:
                raise ValueError(f"No 'configValue' field found in organization for orgId: {org_id}")
            
            config_value = item['configValue']
            
            # Parse the JSON configuration
            try:
                if isinstance(config_value, str):
                    config_data = json.loads(config_value)
                else:
                    config_data = config_value
                
                if not isinstance(config_data, list):
                    raise ValueError(f"Expected configValue to be an array for orgId: {org_id}")
                
                # Extract all config IDs
                config_ids = []
                for config_item in config_data:
                    if isinstance(config_item, dict) and 'configId' in config_item:
                        config_ids.append(config_item['configId'])
                
                logger.info(f"Found {len(config_ids)} configurations for orgId: {org_id}")
                return config_ids
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON configuration for orgId {org_id}: {str(e)}")
                raise ValueError(f"Invalid JSON in configValue for orgId: {org_id}")
        
        except Exception as e:
            logger.error(f"Unexpected error listing configurations: {str(e)}")
            raise
    
    def get_localization_by_language(self, config: OrgConfigData, language: str) -> Optional[LocalizationConfig]:
        """
        Get localization configuration for a specific language
        
        Args:
            config: The organization configuration
            language: Language code (e.g., 'en-US', 'th-TH')
            
        Returns:
            LocalizationConfig for the specified language, None if not found
        """
        for localization in config.localization:
            if localization.language == language:
                return localization
        
        logger.warning(f"No localization found for language: {language}")
        return None
    
    def get_default_localization(self, config: OrgConfigData) -> Optional[LocalizationConfig]:
        """
        Get the default localization configuration
        
        Args:
            config: The organization configuration
            
        Returns:
            LocalizationConfig for the default primary language
        """
        return self.get_localization_by_language(config, config.defaultPrimaryLanguage)
    
    def get_available_languages(self, config: OrgConfigData) -> List[str]:
        """
        Get list of all available languages for the organization
        
        Args:
            config: The organization configuration
            
        Returns:
            List of language codes
        """
        return [loc.language for loc in config.localization]
    
    def get_openai_config(self, config: OrgConfigData) -> OpenAIConfig:
        """
        Get the OpenAI configuration
        
        Args:
            config: The organization configuration
            
        Returns:
            OpenAIConfig object
        """
        return config.openai

# Convenience function for quick config loading
async def load_org_config(org_id: str, config_id: str, table_name: str = None, region_name: str = None) -> Optional[OrgConfigData]:
    """
    Convenience function to load organization configuration
    
    Args:
        org_id: The organization ID to load (stored as configId partition key in DynamoDB)
        config_id: The specific configuration ID to find within the organization's config array
        table_name: DynamoDB table name (defaults to app_config.DYNAMODB_TABLE_NAME)
        region_name: AWS region (defaults to app_config.DYNAMODB_REGION)
        
    Returns:
        OrgConfigData object if found, None if not found
    """
    org_config = OrgConfig(table_name=table_name, region_name=region_name)
    return await org_config.load_config(org_id, config_id)

# Convenience function for listing config IDs
async def list_org_config_ids(org_id: str, table_name: str = None, region_name: str = None) -> List[str]:
    """
    Convenience function to list all configuration IDs for an organization
    
    Args:
        org_id: The organization ID to query for (stored as configId partition key in DynamoDB)
        table_name: DynamoDB table name (defaults to app_config.DYNAMODB_TABLE_NAME)
        region_name: AWS region (defaults to app_config.DYNAMODB_REGION)
        
    Returns:
        List of configuration IDs available in the organization
    """
    org_config = OrgConfig(table_name=table_name, region_name=region_name)
    return await org_config.list_config_ids(org_id)

# Example usage
if __name__ == "__main__":
    # Example of how to use the OrgConfig class
    import os
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example org ID and config ID from the sample data
    sample_org_id = "sample_org_123"
    sample_config_id = "45f9aacfe37ff6c7e072326c600a3b60"
    
    async def main():
        try:
            # Load configuration
            config = await load_org_config(sample_org_id, sample_config_id)
            
            if config:
                print(f"Loaded configuration for: {config.displayName}")
                print(f"KM ID: {config.kmId}")
                print(f"Default language: {config.defaultPrimaryLanguage}")
                print(f"Available languages: {[loc.language for loc in config.localization]}")
                print(f"Gemini validator enabled: {config.gemini.validatorEnabled}")
                print(f"OpenAI API Key configured: {'Yes' if config.openai.apiKey else 'No'}")
                
                # Show localization-specific prompts
                default_loc = next((loc for loc in config.localization if loc.language == config.defaultPrimaryLanguage), None)
                if default_loc:
                    print(f"Default language system prompt: {default_loc.systemPrompt}")
                    print(f"Default language affirmation prompt: {default_loc.affirmationPrompt}")
            else:
                print(f"No configuration found for orgId: {sample_org_id}, configId: {sample_config_id}")
                
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
    
    # Run the async function
    asyncio.run(main())
