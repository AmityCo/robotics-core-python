import { SavedRequest, ChatMessage } from '../types';

const STORAGE_KEY = 'arc2_request_history';
const MAX_HISTORY_ITEMS = 10;

export interface LocalStorageService {
  saveRequest: (request: {
    transcript: string;
    language: string;
    org_id: string;
    config_id: string;
    chat_history: ChatMessage[];
  }) => void;
  getRequestHistory: () => SavedRequest[];
  loadRequest: (timestamp: string) => SavedRequest | null;
  clearHistory: () => void;
}

export const localStorageService: LocalStorageService = {
  saveRequest: (request) => {
    try {
      const history = localStorageService.getRequestHistory();
      const newRequest: SavedRequest = {
        ...request,
        timestamp: new Date().toISOString()
      };
      
      // Add new request to the beginning and limit to MAX_HISTORY_ITEMS
      const updatedHistory = [newRequest, ...history].slice(0, MAX_HISTORY_ITEMS);
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedHistory));
    } catch (error) {
      console.error('Failed to save request to localStorage:', error);
    }
  },

  getRequestHistory: (): SavedRequest[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return [];
      
      const history = JSON.parse(stored);
      // Validate the structure
      if (Array.isArray(history)) {
        return history.filter((item: any) => 
          item && 
          typeof item.transcript === 'string' &&
          typeof item.language === 'string' &&
          typeof item.org_id === 'string' &&
          typeof item.timestamp === 'string' &&
          Array.isArray(item.chat_history)
        );
      }
      return [];
    } catch (error) {
      console.error('Failed to load request history from localStorage:', error);
      return [];
    }
  },

  loadRequest: (timestamp: string): SavedRequest | null => {
    try {
      const history = localStorageService.getRequestHistory();
      return history.find(item => item.timestamp === timestamp) || null;
    } catch (error) {
      console.error('Failed to load specific request from localStorage:', error);
      return null;
    }
  },

  clearHistory: () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear request history from localStorage:', error);
    }
  }
};

// Additional utility functions
export const formatTimestamp = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  } catch {
    return timestamp;
  }
};

export const truncateText = (text: string, maxLength: number = 50): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};
