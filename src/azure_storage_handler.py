"""
Azure Storage Handler Module
Handles all interactions with Azure Blob Storage for TTS caching.
"""
import logging
import asyncio
import threading
import concurrent.futures
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import AzureError, ResourceNotFoundError
from .telemetry import telemetry_span, add_span_attributes, record_exception

# Silence Azure Core logging
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
logging.getLogger('azure.storage').setLevel(logging.WARNING)

try:
    from .app_config import config
except ImportError:
    # Handle case where module is imported from different context
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from src.app_config import config

logger = logging.getLogger(__name__)


class AzureStorageHandler:
    """
    Handles all Azure Blob Storage interactions for TTS caching.
    """
    
    def __init__(self):
        """Initialize Azure Storage handler with configuration"""
        self.container_name = config.TTS_CACHE_CONTAINER_NAME
        
        # Initialize blob service client
        if config.AZURE_STORAGE_CONNECTION_STRING:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                config.AZURE_STORAGE_CONNECTION_STRING
            )
        elif config.AZURE_STORAGE_ACCOUNT_NAME and config.AZURE_STORAGE_ACCOUNT_KEY:
            account_url = f"https://{config.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=config.AZURE_STORAGE_ACCOUNT_KEY
            )
        else:
            logger.error("Azure Storage credentials not configured")
            self.blob_service_client = None
        
        # Ensure container exists
        if self.blob_service_client:
            self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure the TTS cache container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error ensuring container exists: {str(e)}")
    
    def get_cached_audio(self, blob_name: str) -> Optional[bytes]:
        """
        Retrieve cached audio from Azure Storage with timeout
        
        Args:
            blob_name: The blob name (e.g., "en-US/neural2/abc123.mp3")
            
        Returns:
            Audio data as bytes, or None if not found or timeout
        """
        with telemetry_span("azure_storage.get_blob", {
            "azure.storage.operation": "get_blob",
            "azure.storage.container": self.container_name,
            "azure.storage.blob": blob_name
        }) as span:
            if not self.blob_service_client:
                logger.warning("Azure Storage not configured, skipping cache lookup")
                add_span_attributes(span, configured=False)
                return None
            
            def _fetch_blob():
                """Internal function to fetch blob data"""
                try:
                    blob_client = self.blob_service_client.get_blob_client(
                        container=self.container_name,
                        blob=blob_name
                    )
                    
                    # Check if blob exists
                    if blob_client.exists():
                        audio_data = blob_client.download_blob().readall()
                        logger.info(f"Retrieved cached audio: {blob_name}, size: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        logger.debug(f"Cached audio not found: {blob_name}")
                        return None
                        
                except ResourceNotFoundError:
                    logger.debug(f"Cached audio not found: {blob_name}")
                    return None
                except AzureError as e:
                    logger.error(f"Azure Storage error retrieving {blob_name}: {str(e)}")
                    raise e
                except Exception as e:
                    logger.error(f"Unexpected error retrieving cached audio {blob_name}: {str(e)}")
                    raise e
            
            # Execute with timeout
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(_fetch_blob)
                    try:
                        audio_data = future.result(timeout=3.0)  # 3 second timeout
                        if audio_data:
                            add_span_attributes(span, found=True, size_bytes=len(audio_data))
                        else:
                            add_span_attributes(span, found=False)
                        return audio_data
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"Timeout retrieving cached audio: {blob_name} (3s)")
                        add_span_attributes(span, found=False, timeout=True)
                        return None
                        
            except Exception as e:
                logger.error(f"Error retrieving cached audio {blob_name}: {str(e)}")
                record_exception(span, e)
                return None
    
    def save_audio_async(self, blob_name: str, audio_data: bytes):
        """
        Save audio to Azure Storage asynchronously (fire and forget)
        
        Args:
            blob_name: The blob name (e.g., "en-US/neural2/abc123.mp3")
            audio_data: Audio data as bytes
        """
        if not self.blob_service_client:
            logger.warning("Azure Storage not configured, skipping cache save")
            return
        
        # Use thread pool for async upload to avoid event loop issues
        def _upload_sync():
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name
                )
                
                # Upload with WAV content type (updated from MP3)
                blob_client.upload_blob(
                    audio_data,
                    content_type="audio/wav",
                    overwrite=True
                )
                
                logger.info(f"Successfully cached audio: {blob_name}, size: {len(audio_data)} bytes")
                
            except Exception as e:
                logger.error(f"Error saving audio {blob_name}: {str(e)}")
        
        # Run upload in a background thread
        thread = threading.Thread(target=_upload_sync, daemon=True)
        thread.start()
    
    def delete_cached_audio(self, blob_name: str) -> bool:
        """
        Delete cached audio from Azure Storage
        
        Args:
            blob_name: The blob name to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.blob_service_client:
            logger.warning("Azure Storage not configured")
            return False
            
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Deleted cached audio: {blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.debug(f"Cached audio not found for deletion: {blob_name}")
            return False
        except AzureError as e:
            logger.error(f"Azure Storage error deleting {blob_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting audio {blob_name}: {str(e)}")
            return False


# Global instance
azure_storage_handler = AzureStorageHandler()
