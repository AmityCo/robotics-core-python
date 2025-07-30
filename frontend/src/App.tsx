import React, { useState, useRef, useEffect } from 'react';
import VideoUpload from './components/VideoUpload';
import TranscriptInput from './components/TranscriptInput';
import OrgIdInput from './components/OrgIdInput';
import ChatHistoryInput from './components/ChatHistoryInput';
import HistoryPanel from './components/HistoryPanel';
import SSEOutput from './components/SSEOutput';
import ApiUrlInput from './components/ApiUrlInput';
import { sendSSERequest } from './utils/sseClient';
import { localStorageService } from './utils/localStorage';
import { SSEMessage, ChatMessage } from './types';

const App: React.FC = () => {
  const [transcript, setTranscript] = useState<string>(() => {
    return localStorage.getItem('arc2_transcript') || '';
  });
  const [orgId, setOrgId] = useState<string>(() => {
    return localStorage.getItem('arc2_org_id') || '';
  });
  const [language, setLanguage] = useState<string>(() => {
    return localStorage.getItem('arc2_language') || 'en';
  });
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem('arc2_chat_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [base64Audio, setBase64Audio] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [messages, setMessages] = useState<SSEMessage[]>([]);
  const [apiUrl, setApiUrl] = useState<string>(() => {
    // Load API URL from localStorage or use default
    return localStorage.getItem('arc2_api_url') || 'http://localhost:8000';
  });
  const eventSourceRef = useRef<any>(null);

  // Save form fields to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('arc2_transcript', transcript);
  }, [transcript]);

  useEffect(() => {
    localStorage.setItem('arc2_org_id', orgId);
  }, [orgId]);

  useEffect(() => {
    localStorage.setItem('arc2_language', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('arc2_chat_history', JSON.stringify(chatHistory));
  }, [chatHistory]);

  // Save API URL to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('arc2_api_url', apiUrl);
  }, [apiUrl]);

  const handleSubmit = async (): Promise<void> => {
    if (!transcript.trim() || !orgId.trim()) {
      alert('Please provide both transcript and organization ID');
      return;
    }

    if (!base64Audio) {
      alert('Please upload a video/audio file');
      return;
    }

    if (!apiUrl.trim()) {
      alert('Please provide API URL');
      return;
    }

    // Save the request to localStorage before sending
    localStorageService.saveRequest({
      transcript: transcript.trim(),
      language,
      org_id: orgId.trim(),
      chat_history: chatHistory
    });

    setIsProcessing(true);
    setMessages([]);

    try {
      // Close any existing SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Start SSE request
      const eventSource = await sendSSERequest({
        transcript: transcript.trim(),
        language,
        base64_audio: base64Audio,
        org_id: orgId.trim(),
        chat_history: chatHistory
      }, apiUrl.trim());

      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received SSE message:', data);
          setMessages(prev => [...prev, {
            id: Date.now() + Math.random().toString(),
            timestamp: new Date().toISOString(),
            ...data
          }]);
        } catch (error) {
          console.error('Error parsing SSE message:', error);
          setMessages(prev => [...prev, {
            id: Date.now() + Math.random().toString(),
            timestamp: new Date().toISOString(),
            type: 'error' as const,
            message: 'Failed to parse server message',
            raw: event.data
          }]);
        }
      };

      eventSource.onerror = (error: Event | Error) => {
        console.error('SSE Error:', error);
        setMessages(prev => [...prev, {
          id: Date.now() + Math.random().toString(),
          timestamp: new Date().toISOString(),
          type: 'error' as const,
          message: 'Connection error occurred'
        }]);
        setIsProcessing(false);
      };

      eventSource.addEventListener('close', () => {
        setIsProcessing(false);
      });

    } catch (error) {
      console.error('Error starting SSE request:', error);
      setMessages(prev => [...prev, {
        id: Date.now() + Math.random().toString(),
        timestamp: new Date().toISOString(),
        type: 'error' as const,
        message: `Failed to start request: ${(error as Error).message}`
      }]);
      setIsProcessing(false);
    }
  };

  const handleStop = (): void => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsProcessing(false);
    setMessages(prev => [...prev, {
      id: Date.now() + Math.random().toString(),
      timestamp: new Date().toISOString(),
      type: 'status' as const,
      message: 'Request stopped by user'
    }]);
  };

  const handleClear = (): void => {
    setMessages([]);
  };

  const handleClearFormData = (): void => {
    if (window.confirm('Are you sure you want to clear all form data? This action cannot be undone.')) {
      setTranscript('');
      setOrgId('');
      setLanguage('en');
      setChatHistory([]);
      setBase64Audio('');
      setVideoFile(null);
      setApiUrl('http://localhost:8000');
      
      // Clear from localStorage as well
      localStorage.removeItem('arc2_transcript');
      localStorage.removeItem('arc2_org_id');
      localStorage.removeItem('arc2_language');
      localStorage.removeItem('arc2_chat_history');
      localStorage.removeItem('arc2_api_url');
      
      alert('All form data has been cleared.');
    }
  };

  const handleLoadRequest = (request: {
    transcript: string;
    language: string;
    org_id: string;
    chat_history: ChatMessage[];
  }): void => {
    setTranscript(request.transcript);
    setLanguage(request.language);
    setOrgId(request.org_id);
    setChatHistory(request.chat_history);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              ARC2 Server Frontend
            </h1>
            <p className="text-lg text-gray-600">
              AI-powered answer generation with real-time Server-Sent Events
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Input Panel */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-semibold text-gray-800">
                  Input Parameters
                </h2>
                <div className="flex items-center text-xs text-gray-500">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
                  </svg>
                  Auto-saved locally
                </div>
              </div>
              
              <div className="space-y-6">
                <ApiUrlInput apiUrl={apiUrl} onApiUrlChange={setApiUrl} />
                
                <OrgIdInput value={orgId} onChange={setOrgId} />
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="en-US">English</option>
                    <option value="th-TH">Thai</option>
                    <option value="zh-CN">Chinese</option>
                  </select>
                </div>

                <VideoUpload
                  onFileSelect={setVideoFile}
                  onBase64Ready={setBase64Audio}
                />

                <TranscriptInput value={transcript} onChange={setTranscript} />

                <ChatHistoryInput value={chatHistory} onChange={setChatHistory} />

                {/* Action Buttons */}
                <div className="flex flex-col space-y-2">
                  <div className="flex space-x-4">
                    <button
                      onClick={handleSubmit}
                      disabled={isProcessing || !transcript.trim() || !orgId.trim() || !base64Audio || !apiUrl.trim()}
                      className="flex-1 bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isProcessing ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Processing...
                        </span>
                      ) : (
                        'Start Processing'
                      )}
                    </button>
                    
                    {isProcessing && (
                      <button
                        onClick={handleStop}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
                      >
                        Stop
                      </button>
                    )}
                  </div>
                  
                  <button
                    onClick={handleClearFormData}
                    disabled={isProcessing}
                    className="w-full px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Clear All Form Data
                  </button>
                </div>
              </div>
            </div>

            {/* Output Panel */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-gray-800">
                  Real-time Output
                </h2>
                <button
                  onClick={handleClear}
                  disabled={messages.length === 0}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Clear
                </button>
              </div>
              
              <SSEOutput messages={messages} isProcessing={isProcessing} />
            </div>
          </div>

          {/* History Panel */}
          <div className="mt-8">
            <HistoryPanel onLoadRequest={handleLoadRequest} />
          </div>

          {/* Status Bar */}
          <div className="mt-8 bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="text-sm font-medium text-gray-700">Status:</span>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  isProcessing 
                    ? 'bg-yellow-100 text-yellow-800' 
                    : 'bg-green-100 text-green-800'
                }`}>
                  {isProcessing ? 'Processing' : 'Ready'}
                </span>
              </div>
              <div className="text-sm text-gray-500">
                Messages: {messages.length}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
