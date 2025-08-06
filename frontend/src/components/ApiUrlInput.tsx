import React from 'react';

interface ApiUrlInputProps {
  apiUrl: string;
  onApiUrlChange: (url: string) => void;
}

const ApiUrlInput: React.FC<ApiUrlInputProps> = ({ apiUrl, onApiUrlChange }) => {
  return (
    <div className="mb-4">
      <label htmlFor="apiUrl" className="block text-sm font-medium text-gray-700 mb-2">
        API URL
      </label>
      <input
        type="url"
        id="apiUrl"
        value={apiUrl}
        onChange={(e) => onApiUrlChange(e.target.value)}
        placeholder="Enter API URL (e.g., http://localhost:8000)"
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
      />
      <p className="mt-1 text-xs text-gray-500">
        Enter the base URL for the API server (without /api/v1/answer-sse)
      </p>
    </div>
  );
};

export default ApiUrlInput;
