#!/usr/bin/env python3
"""
Example usage of the updated TTSStreamer with SSMLFormatter
"""
import asyncio
import logging
from src.tts_stream import TTSStreamer
from src.org_config import OrgConfigData, TTSConfig, AzureTTSConfig, TTSModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def audio_callback(text: str, audio_data: bytes):
    """Callback function for when audio is ready"""
    print(f"Audio ready for text: '{text[:50]}...' ({len(audio_data)} bytes)")

async def example_usage():
    """Example of using the updated TTSStreamer"""
    
    # Create mock organization configuration
    tts_models = [
        TTSModel(
            language="en-US",
            name="en-US-AriaNeural", 
            pitch="medium",
            rate="1.0",
            phonemeUrl="https://example.com/phonemes/en-us.json"
        ),
        TTSModel(
            language="th-TH",
            name="th-TH-PremwadeeNeural",
            pitch="medium", 
            rate="1.0",
            phonemeUrl="https://example.com/phonemes/th-th.json"
        )
    ]
    
    azure_tts = AzureTTSConfig(
        subscriptionKey="your-azure-key",
        lexiconURL="https://example.com/lexicons/",
        phonemeUrl="https://example.com/phonemes/global.json",
        models=tts_models
    )
    
    tts_config = TTSConfig(azure=azure_tts)
    
    # Create a minimal org config (you'd normally load this from DynamoDB)
    org_config = type('MockOrgConfig', (), {'tts': tts_config})()
    
    try:
        # Initialize TTS streamer
        streamer = TTSStreamer(
            org_config=org_config,
            language="en-US",
            audio_callback=audio_callback,
            min_words=3,  # Lower threshold for demo
            remove_bracketed_words=True
        )
        
        # Initialize the streamer (loads phonemes)
        await streamer.initialize()
        
        # Simulate streaming text input
        text_chunks = [
            "Hello there, this is",
            " a test of the",
            " streaming TTS system.",
            " It should process text",
            " in chunks and generate",
            " audio for each chunk.",
            " (This text in brackets should be removed)",
            " The end!"
        ]
        
        print("Starting text streaming...")
        for i, chunk in enumerate(text_chunks):
            print(f"Adding chunk {i+1}: '{chunk}'")
            streamer.append_text(chunk)
            
            # Simulate some delay between chunks
            await asyncio.sleep(0.5)
        
        # Flush any remaining text
        print("Flushing remaining text...")
        streamer.flush()
        
        print("Streaming complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(example_usage())
