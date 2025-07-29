import { AnswerRequest } from '../types';

/**
 * SSE Client for handling Server-Sent Events from the ARC2 API
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface SSEEventSource {
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((error: Event | Error) => void) | null;
  onopen: ((event?: Event) => void) | null;
  onclose: ((event?: Event) => void) | null;
  addEventListener: (event: string, handler: (event: any) => void) => void;
  close: () => void;
  readyState: number;
}

export const sendSSERequest = async (requestData: AnswerRequest): Promise<SSEEventSource> => {
  const { transcript, language, base64_audio, org_id } = requestData;

  // Validate required fields
  if (!transcript || !org_id || !base64_audio) {
    throw new Error('Missing required fields: transcript, org_id, and base64_audio are required');
  }

  try {
    // Use fetch with streaming for SSE
    const response = await fetch(`${API_BASE_URL}/api/v1/answer-sse`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify({
        transcript,
        language,
        base64_audio,
        org_id
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    // Create a custom EventSource-like object using fetch streaming
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Create EventSource-compatible object
    const eventSource: SSEEventSource = {
      onmessage: null,
      onerror: null,
      onopen: null,
      onclose: null,
      addEventListener: function(event: string, handler: (event: any) => void) {
        if (event === 'message') {
          this.onmessage = handler;
        } else if (event === 'error') {
          this.onerror = handler;
        } else if (event === 'open') {
          this.onopen = (event?: Event) => handler(event);
        } else if (event === 'close') {
          this.onclose = (event?: Event) => handler(event);
        }
      },
      close: function() {
        if (reader) {
          reader.cancel();
        }
        this.readyState = 2; // CLOSED
        if (this.onclose) {
          this.onclose();
        }
      },
      readyState: 1, // OPEN
    };

    // Trigger onopen if handler exists
    if (eventSource.onopen) {
      eventSource.onopen();
    }

    // Start reading the stream
    const readStream = async () => {
      try {
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            // Stream finished
            eventSource.readyState = 2; // CLOSED
            if (eventSource.onclose) {
              eventSource.onclose();
            }
            break;
          }

          // Decode the chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // Remove 'data: ' prefix
              
              if (data.trim() === '') {
                continue; // Skip empty data
              }

              // Create mock event object
              const event: MessageEvent = new MessageEvent('message', {
                data: data,
                lastEventId: '',
                origin: API_BASE_URL,
              });

              // Call the message handler
              if (eventSource.onmessage) {
                eventSource.onmessage(event);
              }
            }
          }
        }
      } catch (error) {
        console.error('Stream reading error:', error);
        eventSource.readyState = 2; // CLOSED
        if (eventSource.onerror) {
          eventSource.onerror(error as Error);
        }
      }
    };

    // Start reading the stream
    readStream();

    return eventSource;

  } catch (error) {
    console.error('SSE request error:', error);
    throw error;
  }
};

/**
 * Alternative implementation using EventSource (if the server supports CORS properly)
 * This is kept as a fallback or for future use
 */
export const sendSSERequestWithEventSource = (requestData: AnswerRequest): EventSource => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { transcript, language, base64_audio, org_id } = requestData;

  // Create URL with query parameters (GET-style)
  const url = new URL(`${API_BASE_URL}/api/v1/answer-sse`);
  
  // Note: EventSource only supports GET requests, so we'd need to modify the backend
  // to accept parameters via query string or use a different approach
  // Future implementation would use these parameters: transcript, language, base64_audio, org_id
  
  const eventSource = new EventSource(url.toString());
  
  return eventSource;
};
