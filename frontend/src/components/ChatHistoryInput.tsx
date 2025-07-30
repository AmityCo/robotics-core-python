import React, { useState } from 'react';
import { ChatHistoryInputProps, ChatMessage } from '../types';

const ChatHistoryInput: React.FC<ChatHistoryInputProps> = ({ value, onChange }) => {
  const [newRole, setNewRole] = useState<'user' | 'assistant'>('user');
  const [newContent, setNewContent] = useState<string>('');
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const addMessage = () => {
    if (newContent.trim()) {
      const newMessage: ChatMessage = {
        role: newRole,
        content: newContent.trim()
      };
      onChange([...value, newMessage]);
      setNewContent('');
    }
  };

  const removeMessage = (index: number) => {
    const updatedHistory = value.filter((_, i) => i !== index);
    onChange(updatedHistory);
  };

  const updateMessage = (index: number, field: keyof ChatMessage, newValue: string) => {
    const updatedHistory = value.map((msg, i) => 
      i === index ? { ...msg, [field]: newValue } : msg
    );
    onChange(updatedHistory);
  };

  const clearHistory = () => {
    onChange([]);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">
          Chat History ({value.length} messages)
        </label>
        <div className="flex space-x-2">
          {value.length > 0 && (
            <button
              type="button"
              onClick={clearHistory}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Clear All
            </button>
          )}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {/* Existing Messages */}
          {value.length > 0 && (
            <div className="space-y-3 max-h-64 overflow-y-auto border border-gray-200 rounded-md p-3">
              {value.map((message, index) => (
                <div key={index} className="bg-gray-50 rounded-md p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <select
                      value={message.role}
                      onChange={(e) => updateMessage(index, 'role', e.target.value)}
                      className="text-sm border border-gray-300 rounded px-2 py-1"
                    >
                      <option value="user">User</option>
                      <option value="assistant">Assistant</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => removeMessage(index)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                  <textarea
                    value={message.content}
                    onChange={(e) => updateMessage(index, 'content', e.target.value)}
                    className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 resize-none"
                    rows={2}
                    placeholder="Message content..."
                  />
                </div>
              ))}
            </div>
          )}

          {/* Add New Message */}
          <div className="border border-gray-300 rounded-md p-3 space-y-3">
            <div className="flex items-center space-x-3">
              <label className="text-sm font-medium text-gray-700">Add Message:</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as 'user' | 'assistant')}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="user">User</option>
                <option value="assistant">Assistant</option>
              </select>
            </div>
            <div className="flex space-x-2">
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="Enter message content..."
                className="flex-1 text-sm border border-gray-300 rounded-md px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && e.ctrlKey) {
                    addMessage();
                  }
                }}
              />
              <button
                type="button"
                onClick={addMessage}
                disabled={!newContent.trim()}
                className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add
              </button>
            </div>
            <p className="text-xs text-gray-500">Tip: Press Ctrl+Enter to add message</p>
          </div>
        </div>
      )}

      {!isExpanded && value.length > 0 && (
        <div className="text-sm text-gray-600 bg-gray-50 rounded-md p-2">
          Preview: {value.slice(-2).map((msg, i) => (
            <span key={i} className="block truncate">
              <strong>{msg.role}:</strong> {msg.content.substring(0, 50)}
              {msg.content.length > 50 ? '...' : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatHistoryInput;
