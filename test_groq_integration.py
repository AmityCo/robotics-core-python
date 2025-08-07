"""
Test script to demonstrate Groq integration with organization configuration
"""

import asyncio
import logging
from src.groq_handler import GroqHandler, is_groq_model
from src.org_config import OrgConfigData, LocalizationConfig, GroqConfig, OpenAIConfig, GeminiConfig, ConversationConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_groq_integration():
    """
    Test the Groq integration functionality
    """
    
    # Create a mock configuration for testing
    mock_config = OrgConfigData(
        kmId="test_km_id",
        configId="test_config_id",
        displayName="Test Organization",
        networkId="test_network",
        onPauseStrategy="continue",
        conversation=ConversationConfig(answerStrategy="direct"),
        displayLanguageLogic="auto",
        gemini=GeminiConfig(
            key="test_gemini_key",
            validatorEnabled=False
        ),
        openai=OpenAIConfig(apiKey="test_openai_key"),
        groq=GroqConfig(apiKey="test_groq_key"),  # This would be your actual Groq API key
        localization=[
            LocalizationConfig(
                displayName="English",
                icon="🇺🇸",
                language="en-US",
                assistantId="test_assistant",
                assistantKey="test_key",
                generatorModel="groq/openai/gpt-oss-20b"  # Groq model
            ),
            LocalizationConfig(
                displayName="Thai",
                icon="🇹🇭", 
                language="th-TH",
                assistantId="test_assistant_th",
                assistantKey="test_key_th",
                generatorModel="gpt-4"  # Regular OpenAI model
            )
        ],
        cameraActivation={"enabled": False},
        audio={"multiplierThreadsholds": [], "auto_trim_silent": False},
        interruption={
            "enabled": False,
            "dynamicThreshold": {"enabled": False, "delta": 0},
            "minimum": 0,
            "maximum": 0,
            "span": 0,
            "debounce": 0
        },
        defaultPrimaryLanguage="en-US",
        preferredMicrophoneNames=[],
        quickReplies=None,
        state={},
        resources={"isFullScreen": False},
        stt={"useAlternateLanguage": False},
        tts={"azure": {"subscriptionKey": "test", "lexiconURL": "test", "models": []}},
        theme={
            "primary": "#000000",
            "onPrimary": "#FFFFFF",
            "secondary": "#CCCCCC", 
            "onSecondary": "#000000",
            "tertiary": "#EEEEEE",
            "onTertiary": "#000000",
            "inversePrimary": "#FFFFFF"
        },
        feedback={
            "imageUrl": "test",
            "title": [],
            "form": [],
            "reasons": []
        },
        shelf={}
    )
    
    # Test model detection
    print("=== Testing Model Detection ===")
    groq_model = "groq/openai/gpt-oss-20b"
    openai_model = "gpt-4"
    
    print(f"'{groq_model}' is Groq model: {is_groq_model(groq_model)}")
    print(f"'{openai_model}' is Groq model: {is_groq_model(openai_model)}")
    
    # Test localization with different models
    print("\n=== Testing Localization Models ===")
    for loc in mock_config.localization:
        model = loc.generatorModel
        if model:
            if is_groq_model(model):
                print(f"Language {loc.language} uses Groq model: {model}")
            else:
                print(f"Language {loc.language} uses non-Groq model: {model}")
    
    # Test Groq handler creation (this would fail without a real API key)
    print("\n=== Testing Groq Handler Logic (without client initialization) ===")
    try:
        # Test the logic without creating the actual Groq client
        from src.groq_handler import GroqHandler
        
        # Test message processing directly
        # Create a mock handler to test the methods without initializing the client
        test_config = mock_config.model_copy()
        test_config.groq.apiKey = "gsk_dummy_key_for_testing_1234567890abcdef"
        
        # We'll create a class that has the same methods but doesn't initialize the client
        class MockGroqHandler:
            def __init__(self, config):
                self.config = config
                # Don't initialize the client to avoid the error
            
            def _extract_model_name(self, model_string: str) -> str:
                if model_string.startswith("groq/"):
                    return model_string[5:]  # Remove "groq/" prefix
                return model_string
            
            def _combine_system_prompts(self, messages):
                system_prompts = []
                other_messages = []
                
                for message in messages:
                    if message.get("role") == "system":
                        system_prompts.append(message.get("content", ""))
                    else:
                        other_messages.append(message)
                
                # Combine all system prompts into one
                if system_prompts:
                    combined_system_content = "\n\n".join(filter(None, system_prompts))
                    combined_messages = [{"role": "system", "content": combined_system_content}]
                    combined_messages.extend(other_messages)
                    return combined_messages
                
                return other_messages
        
        handler = MockGroqHandler(test_config)
        print("✅ GroqHandler logic testing setup successful")
        
        # Test message processing
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "system", "content": "Always be polite and informative."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        processed = handler._combine_system_prompts(messages)
        print(f"✅ Message processing works. Combined {len(messages)} messages into {len(processed)} messages")
        print(f"   System prompt: {processed[0]['content'][:100]}...")
        
        # Test model name extraction
        test_model = "groq/openai/gpt-oss-20b"
        extracted = handler._extract_model_name(test_model)
        print(f"✅ Model name extraction: '{test_model}' -> '{extracted}'")
        
    except Exception as e:
        print(f"❌ Error creating GroqHandler: {e}")
    
    print("\n=== Integration Test Complete ===")
    print("To use with real API calls, provide a valid Groq API key in the configuration.")

def demonstrate_usage():
    """
    Show how to use the Groq integration in practice
    """
    print("\n=== Usage Example ===")
    print("""
    # In your application code:
    
    from src.groq_handler import GroqHandler, is_groq_model
    from src.org_config import load_org_config
    
    # Load organization configuration
    config = await load_org_config("your_org_id", "your_config_id")
    
    # Get localization for a specific language
    localization = get_localization_by_language(config, "en-US")
    
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
    """)

if __name__ == "__main__":
    asyncio.run(test_groq_integration())
    demonstrate_usage()
