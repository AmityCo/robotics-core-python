import json
import logging
import threading
import time
import base64
import os
from datetime import datetime
from queue import Empty, Queue
from typing import Any, Generator

# Configure logger
logger = logging.getLogger(__name__)


class SSEHandler:
    """
    Handles Server-Sent Events (SSE) communication with a thread-safe queue system.
    Allows multiple threads to send SSE messages through a single yielding interface.
    """

    def __init__(self):
        self.queue = Queue()
        self.is_complete = threading.Event()
        self.error_occurred = threading.Event()

        # Registry for tracking multiple completion states
        self._completion_registry = {}

    def send(self, message_type: str, data: Any = None, message: str = None):
        """
        Send an SSE message. Thread-safe method that can be called from any thread.

        Args:
            message_type: Type of the SSE message (status, error, answer_chunk, etc.)
            data: Data payload for the message
            message: Simple message string (used for status/error messages)
        """
        sse_data = {
            'type': message_type,
            'timestamp': datetime.now().isoformat()
        }

        if data is not None:
            sse_data['data'] = data
        if message is not None:
            sse_data['message'] = message

        # Put the formatted SSE message into the queue
        sse_message = f"data: {json.dumps(sse_data)}\n\n"
        self.queue.put(sse_message)
        logger.debug(f"SSE message queued: {message_type}")

    def send_error(self, error_message: str):
        """Send an error message and mark that an error occurred."""
        self.send('error', message=error_message)
        self.error_occurred.set()

    def playAudio(self, fileName: str):
        """
        Play an audio file by emitting it through SSE.
        
        Args:
            fileName: Name of the audio file (should be in the audio directory)
        """
        try:
            # Construct path to audio file (assuming it's in the audio directory relative to current work dir)
            audio_path = os.path.join(os.getcwd(), 'audio', fileName)

            if os.path.exists(audio_path):
                with open(audio_path, 'rb') as audio_file:
                    audio_data = audio_file.read()
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    audio_payload = {
                        'audioDataLength': len(audio_base64),
                        'audio_size': len(audio_data),
                        'audio_format': 'raw-16khz-16bit-mono-pcm',
                        'audio_data': audio_base64
                    }
                    self.send('audio', data=audio_payload)
                    logger.info(f"Emitted audio file: {fileName} (size: {len(audio_data)} bytes)")
            else:
                logger.warning(f"Audio file not found at: {audio_path}")
        except Exception as e:
            logger.warning(f"Failed to emit audio file {fileName}: {str(e)}")

    def register_component(self, component_name: str):
        """
        Register a component that needs to complete before the handler finishes.

        Args:
            component_name: Name of the component (e.g., 'text_generation', 'tts_processing')
        """
        self._completion_registry[component_name] = False
        logger.debug(f"Registered component: {component_name}")

    def mark_component_complete(self, component_name: str):
        """
        Mark a specific component as complete.

        Args:
            component_name: Name of the component that has completed
        """
        if component_name in self._completion_registry:
            # Only mark as complete if not already complete
            if not self._completion_registry[component_name]:
                self._completion_registry[component_name] = True
                logger.debug(f"Component completed: {component_name}")

                # Check if all components are complete
                if all(self._completion_registry.values()):
                    self.send('complete', message='Answer pipeline completed successfully')
                    self.is_complete.set()
                    logger.info("All components completed, marking handler as complete")
            else:
                logger.debug(f"Component {component_name} already marked as complete")
        else:
            logger.warning(f"Attempted to mark unknown component as complete: {component_name}")

    def mark_complete(self):
        """Mark the processing as complete (legacy method - use register_component/mark_component_complete instead)."""
        self.send('complete', message='Answer pipeline completed successfully')
        self.is_complete.set()

    def are_all_components_complete(self) -> bool:
        """Check if all registered components are complete."""
        return len(self._completion_registry) > 0 and all(self._completion_registry.values())

    def yield_messages(self) -> Generator[str, None, None]:
        """
        Generator that yields SSE messages from the queue.
        This should be called from the main thread that handles the HTTP response.
        """
        while True:
            try:
                # Check if we're done and queue is empty
                if self.is_complete.is_set() and self.queue.empty():
                    break

                # Check if an error occurred and queue is empty
                if self.error_occurred.is_set() and self.queue.empty():
                    break

                # Try to get a message from the queue with a timeout
                try:
                    message = self.queue.get(timeout=0.1)
                    yield message
                    self.queue.task_done()
                except Empty:
                    # No message available, continue checking
                    # sleep for 50 ms
                    time.sleep(0.05)
                    continue

            except Exception as e:
                logger.error(f"Error in SSE message yielding: {str(e)}")
                error_data = {
                    'type': 'error',
                    'message': f"SSE handler error: {str(e)}",
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break
        logger.info("Answer flow SSE execution ended")