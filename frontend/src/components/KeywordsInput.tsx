import React, { useState } from 'react';

interface KeywordsInputProps {
  value: string[];
  onChange: (keywords: string[]) => void;
}

const KeywordsInput: React.FC<KeywordsInputProps> = ({ value, onChange }) => {
  const [inputValue, setInputValue] = useState<string>('');

  const addKeyword = () => {
    const keyword = inputValue.trim();
    if (keyword && !value.includes(keyword)) {
      onChange([...value, keyword]);
      setInputValue('');
    }
  };

  const removeKeyword = (index: number) => {
    const newKeywords = value.filter((_, i) => i !== index);
    onChange(newKeywords);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addKeyword();
    }
  };

  const clearAllKeywords = () => {
    onChange([]);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Keywords (Optional)
        <span className="text-xs text-gray-500 ml-2">
          • If provided, validation step will be skipped
        </span>
      </label>
      
      {/* Keywords display */}
      <div className="mb-3">
        {value.length > 0 && (
          <div className="flex flex-wrap gap-2 p-3 bg-gray-50 rounded-md border">
            {value.map((keyword, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {keyword}
                <button
                  type="button"
                  onClick={() => removeKeyword(index)}
                  className="ml-1.5 inline-flex items-center justify-center w-4 h-4 rounded-full text-blue-600 hover:bg-blue-200 hover:text-blue-800 focus:outline-none"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Input field */}
      <div className="flex space-x-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Enter keyword and press Enter"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
        <button
          type="button"
          onClick={addKeyword}
          disabled={!inputValue.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Add
        </button>
      </div>

      {/* Helper buttons */}
      {value.length > 0 && (
        <div className="mt-2 flex space-x-2">
          <button
            type="button"
            onClick={clearAllKeywords}
            className="text-xs text-red-600 hover:text-red-800 underline"
          >
            Clear all keywords
          </button>
          <span className="text-xs text-gray-500">
            ({value.length} keyword{value.length !== 1 ? 's' : ''})
          </span>
        </div>
      )}

      {/* Info box */}
      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">
              Keywords Mode
            </h3>
            <div className="mt-2 text-sm text-yellow-700">
              <ul className="list-disc list-inside space-y-1">
                <li>If keywords are provided (even empty list), Gemini validation will be skipped</li>
                <li>Transcript will be used as-is for knowledge search and answer generation</li>
                <li>This reduces processing time by ~200-500ms</li>
                <li>Leave empty to use normal validation process</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeywordsInput;
