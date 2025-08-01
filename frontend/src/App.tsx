import React, { useState, useRef, useEffect } from 'react';
import VideoUpload from './components/VideoUpload';
import TranscriptInput from './components/TranscriptInput';
import OrgIdInput from './components/OrgIdInput';
import ConfigIdInput from './components/ConfigIdInput';
import ChatHistoryInput from './components/ChatHistoryInput';
import KeywordsInput from './components/KeywordsInput';
import ProcessingModeToggle from './components/ProcessingModeToggle';
import HistoryPanel from './components/HistoryPanel';
import SSEOutput from './components/SSEOutput';
import ApiUrlInput from './components/ApiUrlInput';
import { sendSSERequest } from './utils/sseClient';
import { localStorageService } from './utils/localStorage';
import { SSEMessage, ChatMessage } from './types';

const App: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<'answer-sse' | 'audio-trim'>(() => {
    return (localStorage.getItem('arc2_active_tab') as 'answer-sse' | 'audio-trim') || 'answer-sse';
  });

  const [transcript, setTranscript] = useState<string>(() => {
    return localStorage.getItem('arc2_transcript') || '';
  });
  const [orgId, setOrgId] = useState<string>(() => {
    return localStorage.getItem('arc2_org_id') || '';
  });
  const [configId, setConfigId] = useState<string>(() => {
    return localStorage.getItem('arc2_config_id') || '';
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
  const [keywords, setKeywords] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('arc2_keywords');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [processingMode, setProcessingMode] = useState<'normal' | 'keywords' | 'text-only'>(() => {
    return (localStorage.getItem('arc2_processing_mode') as 'normal' | 'keywords' | 'text-only') || 'text-only';
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

  // Audio trimming states
  const [audioUrl, setAudioUrl] = useState<string>(() => {
    return localStorage.getItem('arc2_audio_url') || '';
  });
  const [silenceThreshold, setSilenceThreshold] = useState<number>(() => {
    const saved = localStorage.getItem('arc2_silence_threshold');
    return saved ? parseFloat(saved) : 0.05;
  });
  const [isTrimming, setIsTrimming] = useState<boolean>(false);
  const [trimResult, setTrimResult] = useState<any>(null);

  // Save form fields to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('arc2_transcript', transcript);
  }, [transcript]);

  useEffect(() => {
    localStorage.setItem('arc2_org_id', orgId);
  }, [orgId]);

  useEffect(() => {
    localStorage.setItem('arc2_config_id', configId);
  }, [configId]);

  useEffect(() => {
    localStorage.setItem('arc2_language', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('arc2_chat_history', JSON.stringify(chatHistory));
  }, [chatHistory]);

  useEffect(() => {
    localStorage.setItem('arc2_keywords', JSON.stringify(keywords));
  }, [keywords]);

  useEffect(() => {
    localStorage.setItem('arc2_processing_mode', processingMode);
    
    // Clear audio data when switching away from normal mode
    if (processingMode !== 'normal' && base64Audio) {
      setBase64Audio('');
      setVideoFile(null);
    }
  }, [processingMode, base64Audio]);

  // Save API URL to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('arc2_api_url', apiUrl);
  }, [apiUrl]);

  // Save active tab to localStorage
  useEffect(() => {
    localStorage.setItem('arc2_active_tab', activeTab);
  }, [activeTab]);

  // Save audio trimming values to localStorage
  useEffect(() => {
    localStorage.setItem('arc2_audio_url', audioUrl);
  }, [audioUrl]);

  useEffect(() => {
    localStorage.setItem('arc2_silence_threshold', silenceThreshold.toString());
  }, [silenceThreshold]);

  const handleSubmit = async (): Promise<void> => {
    if (!transcript.trim() || !orgId.trim() || !configId.trim()) {
      alert('Please provide transcript, organization ID, and configuration ID');
      return;
    }

    // Check audio requirement based on processing mode
    if (processingMode === 'normal' && !base64Audio) {
      alert('Please upload a video/audio file for normal processing mode');
      return;
    }

    if (!apiUrl.trim()) {
      alert('Please provide API URL');
      return;
    }

    // Prepare request data based on processing mode
    const requestData: any = {
      transcript: transcript.trim(),
      language,
      org_id: orgId.trim(),
      config_id: configId.trim(),
      chat_history: chatHistory
    };

    // Add optional fields based on mode
    if (processingMode === 'normal') {
      // Normal mode: always include audio (required)
      requestData.base64_audio = base64Audio;
    } else if (processingMode === 'text-only') {
      // Text-only mode: no additional fields needed
      // Audio is not included even if available
    } else if (processingMode === 'keywords') {
      // Keywords mode: include keywords array
      requestData.keywords = keywords;
    }

    // Save the request to localStorage before sending
    localStorageService.saveRequest(requestData);

    setIsProcessing(true);
    setMessages([]);

    try {
      // Close any existing SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Start SSE request
      const eventSource = await sendSSERequest(requestData, apiUrl.trim());

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
      setConfigId('');
      setLanguage('en');
      setChatHistory([]);
      setKeywords([]);
      setProcessingMode('text-only');
      setBase64Audio('');
      setVideoFile(null);
      setApiUrl('http://localhost:8000');
      setAudioUrl('');
      setSilenceThreshold(0.05);
      setTrimResult(null);
      
      // Clear from localStorage as well
      localStorage.removeItem('arc2_transcript');
      localStorage.removeItem('arc2_org_id');
      localStorage.removeItem('arc2_config_id');
      localStorage.removeItem('arc2_language');
      localStorage.removeItem('arc2_chat_history');
      localStorage.removeItem('arc2_keywords');
      localStorage.removeItem('arc2_processing_mode');
      localStorage.removeItem('arc2_api_url');
      localStorage.removeItem('arc2_audio_url');
      localStorage.removeItem('arc2_silence_threshold');
      
      alert('All form data has been cleared.');
    }
  };

  const handleTrimAudio = async (): Promise<void> => {
    if (!audioUrl.trim()) {
      alert('Please provide an audio URL');
      return;
    }

    if (!apiUrl.trim()) {
      alert('Please provide API URL');
      return;
    }

    setIsTrimming(true);
    setTrimResult(null);

    try {
      const response = await fetch(`${apiUrl.trim()}/api/v1/audio/trim`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio_url: audioUrl.trim(),
          silence_threshold: silenceThreshold,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setTrimResult(result);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        setTrimResult({
          status: 'error',
          error: errorData.detail || `HTTP ${response.status}`,
        });
      }
    } catch (error) {
      setTrimResult({
        status: 'error',
        error: `Network error: ${(error as Error).message}`,
      });
    } finally {
      setIsTrimming(false);
    }
  };

  const handleDownloadTrimmedAudio = (): void => {
    if (!trimResult || !trimResult.trimmed_audio_base64) return;

    try {
      // Convert base64 to blob
      const audioData = atob(trimResult.trimmed_audio_base64);
      const audioArray = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }

      const blob = new Blob([audioArray], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);

      // Create download link
      const a = document.createElement('a');
      a.href = url;
      a.download = `trimmed_audio_${Date.now()}.wav`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      alert(`Failed to download audio: ${(error as Error).message}`);
    }
  };

  const handleLoadRequest = (request: {
    transcript: string;
    language: string;
    org_id: string;
    config_id: string;
    chat_history: ChatMessage[];
  }): void => {
    setTranscript(request.transcript);
    setLanguage(request.language);
    setOrgId(request.org_id);
    setConfigId(request.config_id);
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
            <p className="text-sm text-gray-500 mt-1">
              Supports audio-based, text-only, direct keyword processing modes, and audio trimming
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="mb-8">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('answer-sse')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'answer-sse'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <svg className="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Answer SSE Pipeline
                </button>
                <button
                  onClick={() => setActiveTab('audio-trim')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'audio-trim'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <svg className="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                  Audio Trimming
                </button>
              </nav>
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === 'answer-sse' && (
            <>
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
                    
                    <ConfigIdInput value={configId} onChange={setConfigId} />
                    
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

                    <ProcessingModeToggle 
                      mode={processingMode}
                      onModeChange={setProcessingMode}
                      hasAudio={!!base64Audio}
                    />

                    {/* Conditional UI based on processing mode */}
                    {processingMode === 'normal' && (
                      <VideoUpload
                        onFileSelect={setVideoFile}
                        onBase64Ready={setBase64Audio}
                      />
                    )}

                    <TranscriptInput value={transcript} onChange={setTranscript} />

                    {processingMode === 'keywords' && (
                      <KeywordsInput 
                        value={keywords}
                        onChange={setKeywords}
                      />
                    )}

                    <ChatHistoryInput value={chatHistory} onChange={setChatHistory} />

                    {/* Action Buttons */}
                    <div className="flex flex-col space-y-2">
                      <div className="flex space-x-4">
                        <button
                          onClick={handleSubmit}
                          disabled={
                            isProcessing || 
                            !transcript.trim() || 
                            !orgId.trim() || 
                            !configId.trim() || 
                            (processingMode === 'normal' && !base64Audio) ||
                            !apiUrl.trim()
                          }
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
                            <>
                              Start Processing
                              {processingMode === 'keywords' && ' (Skip Validation)'}
                              {processingMode === 'text-only' && ' (Text Only)'}
                            </>
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
                    <span className="text-sm font-medium text-gray-700">Mode:</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      processingMode === 'keywords' 
                        ? 'bg-purple-100 text-purple-800'
                        : processingMode === 'text-only'
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {processingMode === 'keywords' ? 'Keywords (Skip Validation)' : 
                       processingMode === 'text-only' ? 'Text Only' : 'Normal (Audio + Text)'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    Messages: {messages.length}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Audio Trimming Tab Content */}
          {activeTab === 'audio-trim' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Audio Trimming Input Panel */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-semibold text-gray-800">
                    Audio Trimming
                  </h2>
                  <div className="flex items-center text-xs text-gray-500">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    </svg>
                    Remove silence automatically
                  </div>
                </div>
                
                <div className="space-y-6">
                  <ApiUrlInput apiUrl={apiUrl} onApiUrlChange={setApiUrl} />
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Audio URL
                    </label>
                    <input
                      type="url"
                      value={audioUrl}
                      onChange={(e) => setAudioUrl(e.target.value)}
                      placeholder="https://example.com/audio.wav"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                    <p className="mt-1 text-sm text-gray-500">
                      Enter a direct URL to an audio file (WAV or raw PCM format)
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Silence Threshold ({silenceThreshold})
                    </label>
                    <div className="flex items-center space-x-4">
                      <input
                        type="range"
                        min="0.01"
                        max="0.2"
                        step="0.01"
                        value={silenceThreshold}
                        onChange={(e) => setSilenceThreshold(parseFloat(e.target.value))}
                        className="flex-1"
                      />
                      <input
                        type="number"
                        min="0.01"
                        max="0.2"
                        step="0.01"
                        value={silenceThreshold}
                        onChange={(e) => setSilenceThreshold(parseFloat(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      Lower values = more aggressive trimming (default: 0.05 = 5% of max energy)
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-col space-y-2">
                    <button
                      onClick={handleTrimAudio}
                      disabled={isTrimming || !audioUrl.trim() || !apiUrl.trim()}
                      className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isTrimming ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Trimming Audio...
                        </span>
                      ) : (
                        'Trim Audio'
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Audio Trimming Results Panel */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                  Trimming Results
                </h2>
                
                {!trimResult && (
                  <div className="text-center py-12 text-gray-500">
                    <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    </svg>
                    <p>Enter an audio URL and click "Trim Audio" to see results</p>
                  </div>
                )}

                {trimResult && trimResult.status === 'error' && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <div className="flex">
                      <svg className="w-5 h-5 text-red-400 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <div>
                        <h3 className="text-sm font-medium text-red-800">Error</h3>
                        <div className="mt-1 text-sm text-red-700">{trimResult.error}</div>
                      </div>
                    </div>
                  </div>
                )}

                {trimResult && trimResult.status === 'success' && (
                  <div className="space-y-4">
                    <div className="bg-green-50 border border-green-200 rounded-md p-4">
                      <div className="flex">
                        <svg className="w-5 h-5 text-green-400 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <div>
                          <h3 className="text-sm font-medium text-green-800">Success</h3>
                          <div className="mt-1 text-sm text-green-700">Audio trimmed successfully!</div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-gray-50 p-3 rounded-md">
                        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Original Size</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {(trimResult.original_size_bytes / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-md">
                        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Trimmed Size</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {(trimResult.trimmed_size_bytes / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-md">
                        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Size Reduction</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {(trimResult.size_reduction_bytes / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <div className="bg-gray-50 p-3 rounded-md">
                        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">Reduction %</div>
                        <div className="text-lg font-semibold text-gray-900">
                          {trimResult.size_reduction_percent}%
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 p-3 rounded-md">
                      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Audio Format</div>
                      <div className="text-sm text-gray-700">{trimResult.audio_format}</div>
                    </div>

                    <button
                      onClick={handleDownloadTrimmedAudio}
                      className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
                    >
                      <svg className="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download Trimmed Audio
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
