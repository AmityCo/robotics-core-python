import React, { useState, useEffect } from 'react';
import { SavedRequest, ChatMessage } from '../types';
import { localStorageService, formatTimestamp, truncateText } from '../utils/localStorage';

interface HistoryPanelProps {
  onLoadRequest: (request: {
    transcript: string;
    language: string;
    org_id: string;
    chat_history: ChatMessage[];
  }) => void;
}

const HistoryPanel: React.FC<HistoryPanelProps> = ({ onLoadRequest }) => {
  const [history, setHistory] = useState<SavedRequest[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    const savedHistory = localStorageService.getRequestHistory();
    setHistory(savedHistory);
  };

  const handleLoadRequest = (request: SavedRequest) => {
    onLoadRequest({
      transcript: request.transcript,
      language: request.language,
      org_id: request.org_id,
      chat_history: request.chat_history
    });
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear all saved requests?')) {
      localStorageService.clearHistory();
      setHistory([]);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          Request History ({history.length})
        </h3>
        <div className="flex space-x-2">
          {history.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Clear All
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-3">
          {history.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">
              No saved requests yet. Submit a request to save it automatically.
            </p>
          ) : (
            <div className="max-h-64 overflow-y-auto space-y-2">
              {history.map((request, index) => (
                <div
                  key={request.timestamp}
                  className="border border-gray-200 rounded-md p-3 hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleLoadRequest(request)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="text-xs font-medium text-gray-600">
                          {formatTimestamp(request.timestamp)}
                        </span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {request.language}
                        </span>
                        <span className="text-xs text-gray-500">
                          Org: {truncateText(request.org_id, 15)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 truncate mb-1">
                        <strong>Transcript:</strong> {truncateText(request.transcript, 60)}
                      </p>
                      {request.chat_history.length > 0 && (
                        <p className="text-xs text-gray-500">
                          Chat history: {request.chat_history.length} messages
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleLoadRequest(request);
                      }}
                      className="ml-2 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Load
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!isExpanded && history.length > 0 && (
        <div className="text-sm text-gray-600">
          <p>Recent: {truncateText(history[0]?.transcript || '', 40)}</p>
          <p className="text-xs text-gray-500 mt-1">
            {formatTimestamp(history[0]?.timestamp || '')}
          </p>
        </div>
      )}
    </div>
  );
};

export default HistoryPanel;
