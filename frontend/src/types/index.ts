// SSE Message Types
export interface SSEMessage {
  id: string;
  timestamp: string;
  type: 'status' | 'validation' | 'km_search' | 'answer_thinking' | 'answer_stream' | 'error' | 'complete';
  message?: string;
  content?: string;
  data?: any;
  raw?: string;
}

// API Request Types
export interface AnswerRequest {
  transcript: string;
  language: string;
  base64_audio: string;
  org_id: string;
}

// Validation Data Types
export interface ValidationData {
  correction: string;
  searchTerms?: {
    translatedQuestion?: {
      query: string;
      keywords: string[];
    };
    searchQueries?: Array<{
      query: string;
      keywords: string[];
    }>;
  };
}

// KM Search Result Types
export interface KMSearchResult {
  title?: string;
  content?: string;
  reranker_score?: number;
}

// Component Props Types
export interface VideoUploadProps {
  onFileSelect: (file: File | null) => void;
  onBase64Ready: (base64: string) => void;
}

export interface TranscriptInputProps {
  value: string;
  onChange: (value: string) => void;
}

export interface OrgIdInputProps {
  value: string;
  onChange: (value: string) => void;
}

export interface SSEOutputProps {
  messages: SSEMessage[];
  isProcessing: boolean;
}
