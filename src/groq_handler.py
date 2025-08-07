"""
Groq AI Model Handler
Handles Groq API requests for models with groq/ prefix
"""

import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from groq import Groq
from .org_config import OrgConfigData, LocalizationConfig

logger = logging.getLogger(__name__)

class GroqHandler:
    """
    Handler for Groq AI models
    Supports streaming and non-streaming completions
    """
    
    def __init__(self, config: OrgConfigData):
        """
        Initialize the Groq handler with organization configuration
        
        Args:
            config: Organization configuration containing Groq API key
        """
        self.config = config
        # Set the API key in environment variable for Groq client
        import os
        os.environ['GROQ_API_KEY'] = config.groq.apiKey
        # Initialize Groq client (it will pick up the API key from environment)
        self.client = Groq()
    
    def _extract_model_name(self, model_string: str) -> str:
        """
        Extract the actual model name from groq/model_name format
        
        Args:
            model_string: Model string in format "groq/model_name"
            
        Returns:
            The model name without the groq/ prefix
        """
        if model_string.startswith("groq/"):
            return model_string[5:]  # Remove "groq/" prefix
        return model_string
    
    def _combine_system_prompts(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Combine multiple system prompts into a single system message
        Groq only supports one system prompt, so we need to merge them
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of messages with combined system prompts
        """
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
    
    async def generate_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_completion_tokens: int = 8192,
        top_p: float = 1.0,
        reasoning_effort: str = "medium",
        stream: bool = False,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generate a completion using Groq API (non-streaming)
        
        Args:
            model: Model string in format "groq/model_name"
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_completion_tokens: Maximum tokens in completion
            top_p: Top-p sampling parameter
            reasoning_effort: Reasoning effort level
            stream: Whether to use streaming (ignored for this method)
            stop: Stop sequences
            
        Returns:
            Generated completion text
        """
        try:
            # Extract model name and combine system prompts
            model_name = self._extract_model_name(model)
            processed_messages = self._combine_system_prompts(messages)
            
            logger.info(f"Generating completion with Groq model: {model_name}")
            
            # Make the API call
            completion = self.client.chat.completions.create(
                model=model_name,
                messages=processed_messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                top_p=top_p,
                reasoning_effort=reasoning_effort,
                stream=False,
                stop=stop
            )
            
            response_content = completion.choices[0].message.content
            logger.info(f"Successfully generated completion with {len(response_content)} characters")
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error generating Groq completion: {str(e)}")
            raise
    
    async def generate_completion_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 1.0,
        max_completion_tokens: int = 8192,
        top_p: float = 1.0,
        reasoning_effort: str = "medium",
        stop: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a completion using Groq API with streaming
        
        Args:
            model: Model string in format "groq/model_name"
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_completion_tokens: Maximum tokens in completion
            top_p: Top-p sampling parameter
            reasoning_effort: Reasoning effort level
            stop: Stop sequences
            
        Yields:
            Chunks of generated text as they become available
        """
        try:
            # Extract model name and combine system prompts
            model_name = self._extract_model_name(model)
            processed_messages = self._combine_system_prompts(messages)
            
            logger.info(f"Starting streaming completion with Groq model: {model_name}")
            
            # Make the streaming API call
            completion = self.client.chat.completions.create(
                model=model_name,
                messages=processed_messages,
                temperature=temperature,
                max_completion_tokens=max_completion_tokens,
                top_p=top_p,
                reasoning_effort=reasoning_effort,
                stream=True,
                stop=stop
            )
            
            # Yield chunks as they arrive
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info("Successfully completed streaming generation")
            
        except Exception as e:
            logger.error(f"Error in Groq streaming completion: {str(e)}")
            raise

def is_groq_model(model: str) -> bool:
    """
    Check if a model string represents a Groq model
    
    Args:
        model: Model string to check
        
    Returns:
        True if the model is a Groq model (starts with "groq/")
    """
    return model and model.startswith("groq/")

async def create_groq_handler(config: OrgConfigData) -> GroqHandler:
    """
    Factory function to create a GroqHandler instance
    
    Args:
        config: Organization configuration
        
    Returns:
        Configured GroqHandler instance
    """
    return GroqHandler(config)

# Example usage
if __name__ == "__main__":
    import asyncio
    from .org_config import load_org_config
    
    async def test_groq_handler():
        """
        Test function for GroqHandler
        """
        # Load configuration (you'll need to provide actual org_id and config_id)
        config = await load_org_config("test_org", "test_config")
        
        if not config:
            print("Could not load configuration")
            return
        
        # Create handler
        handler = GroqHandler(config)
        
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Test non-streaming completion
        try:
            response = await handler.generate_completion(
                model="groq/openai/gpt-oss-20b",
                messages=messages,
                temperature=0.7
            )
            print(f"Non-streaming response: {response}")
        except Exception as e:
            print(f"Non-streaming error: {e}")
        
        # Test streaming completion
        try:
            print("Streaming response: ", end="")
            async for chunk in handler.generate_completion_stream(
                model="groq/openai/gpt-oss-20b",
                messages=messages,
                temperature=0.7
            ):
                print(chunk, end="")
            print()  # New line after streaming
        except Exception as e:
            print(f"Streaming error: {e}")
    
    # Run the test
    asyncio.run(test_groq_handler())
