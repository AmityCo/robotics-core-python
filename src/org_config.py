"""
Organization Configuration Module
Loads configuration data from AWS DynamoDB based on organization ID
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from botocore.exceptions import ClientError, NoCredentialsError
from .app_config import config as app_config

logger = logging.getLogger(__name__)

class LocalizationConfig(BaseModel):
    displayName: str
    icon: str
    language: str
    assistantId: str
    assistantKey: str
    validatorTranscriptPromptTemplateUrl: Optional[str] = None
    validatorSystemPromptTemplateUrl: Optional[str] = None

class GeminiConfig(BaseModel):
    key: str
    validatorEnabled: bool
    validatorTranscriptPromptTemplateUrl: Optional[str] = None
    validatorSystemPromptTemplateUrl: Optional[str] = None

class OpenAIConfig(BaseModel):
    apiKey: str

class GeneratorConfig(BaseModel):
    model: Optional[str] = "gpt-4.1-mini"
    generatorUserPromptTemplateUrl: Optional[str] = None
    generatorSystemPromptTemplateUrl: Optional[str] = None

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
    phonemeUrl: Optional[str] = None

class AzureTTSConfig(BaseModel):
    subscriptionKey: str
    lexiconURL: str
    phonemeUrl: str
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
    linenotifyToken: str
    conversation: ConversationConfig
    displayLanguageLogic: str
    gemini: GeminiConfig
    openai: OpenAIConfig
    generator: GeneratorConfig
    localization: List[LocalizationConfig]
    cameraActivation: CameraActivationConfig
    audio: AudioConfig
    interruption: InterruptionConfig
    defaultPrimaryLanguage: str
    preferredMicrophoneNames: List[str]
    quickReplies: List[QuickReply]
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
    Handles loading and parsing of organization-specific configuration from AWS DynamoDB
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
        self._dynamodb = None
        self._table = None
    
    def _get_dynamodb_table(self):
        """Initialize DynamoDB connection if not already done"""
        if self._table is None:
            try:
                # Use AWS credentials from app config if available
                if app_config.AWS_ACCESS_KEY_ID and app_config.AWS_SECRET_ACCESS_KEY:
                    self._dynamodb = boto3.resource(
                        'dynamodb',
                        region_name=self.region_name,
                        aws_access_key_id=app_config.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=app_config.AWS_SECRET_ACCESS_KEY
                    )
                    logger.info(f"Using configured AWS credentials from app config")
                else:
                    # Fall back to default credentials (IAM role, AWS CLI, etc.)
                    self._dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
                    logger.info(f"Using default AWS credentials")
                
                self._table = self._dynamodb.Table(self.table_name)
                logger.info(f"Connected to DynamoDB table: {self.table_name} in region: {self.region_name}")
            except NoCredentialsError:
                logger.error("AWS credentials not found. Please configure AWS credentials.")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to DynamoDB: {str(e)}")
                raise
        return self._table
    
    def load_config(self, config_id: str) -> Optional[OrgConfigData]:
        """
        Load organization configuration from DynamoDB
        
        Args:
            config_id: The configuration ID to query for
            
        Returns:
            OrgConfigData object if found, None if not found
            
        Raises:
            ClientError: If there's an error accessing DynamoDB
            ValueError: If the configuration data is invalid
        """
        logger.info(f"Loading organization config for configId: {config_id}")
        
        try:
            table = self._get_dynamodb_table()
            
            # Query DynamoDB using configId as the key
            response = table.get_item(
                Key={
                    'configId': config_id
                }
            )
            
            if 'Item' not in response:
                logger.warning(f"No configuration found for configId: {config_id}")
                return None
            
            item = response['Item']
            logger.info(f"Found configuration item for configId: {config_id}")
            
            # Extract the configValue field
            if 'configValue' not in item:
                raise ValueError(f"No 'configValue' field found in configuration for configId: {config_id}")
            
            config_value = item['configValue']
            
            # Parse the JSON configuration
            try:
                if isinstance(config_value, str):
                    # If configValue is stored as a JSON string
                    config_data = json.loads(config_value)
                else:
                    # If configValue is already a dict/object
                    config_data = config_value
                
                # The sample shows configValue as an array, so take the first element
                if isinstance(config_data, list) and len(config_data) > 0:
                    config_data = config_data[0]
                elif isinstance(config_data, list) and len(config_data) == 0:
                    raise ValueError(f"Empty configuration array for configId: {config_id}")
                
                # Parse and validate using Pydantic model
                org_config = OrgConfigData.model_validate(config_data)
                logger.info(f"Successfully loaded and validated configuration for organization: {org_config.displayName}")
                
                return org_config
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON configuration for configId {config_id}: {str(e)}")
                raise ValueError(f"Invalid JSON in configValue for configId: {config_id}")
            except Exception as e:
                logger.error(f"Failed to validate configuration data for configId {config_id}: {str(e)}")
                raise ValueError(f"Invalid configuration structure for configId: {config_id}")
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"DynamoDB error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {str(e)}")
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
    
    def get_generator_config(self, config: OrgConfigData) -> GeneratorConfig:
        """
        Get the Generator configuration
        
        Args:
            config: The organization configuration
            
        Returns:
            GeneratorConfig object
        """
        return config.generator

# Convenience function for quick config loading
def load_org_config(config_id: str, table_name: str = None, region_name: str = None) -> Optional[OrgConfigData]:
    """
    Convenience function to load organization configuration
    
    Args:
        config_id: The configuration ID to load
        table_name: DynamoDB table name (defaults to app_config.DYNAMODB_TABLE_NAME)
        region_name: AWS region (defaults to app_config.DYNAMODB_REGION)
        
    Returns:
        OrgConfigData object if found, None if not found
    """
    org_config = OrgConfig(table_name=table_name, region_name=region_name)
    return org_config.load_config(config_id)

# Example usage
if __name__ == "__main__":
    # Example of how to use the OrgConfig class
    import os
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example config ID from the sample data
    sample_config_id = "45f9aacfe37ff6c7e072326c600a3b60"
    
    try:
        # Load configuration
        config = load_org_config(sample_config_id)
        
        if config:
            print(f"Loaded configuration for: {config.displayName}")
            print(f"KM ID: {config.kmId}")
            print(f"Default language: {config.defaultPrimaryLanguage}")
            print(f"Available languages: {[loc.language for loc in config.localization]}")
            print(f"Gemini validator enabled: {config.gemini.validatorEnabled}")
            print(f"OpenAI API Key configured: {'Yes' if config.openai.apiKey else 'No'}")
            print(f"Generator model: {config.generator.model}")
            print(f"Generator transcript prompt URL: {config.generator.generatorUserPromptTemplateUrl}")
        else:
            print(f"No configuration found for ID: {sample_config_id}")
            
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
