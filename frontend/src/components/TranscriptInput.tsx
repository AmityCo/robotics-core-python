import React from 'react';
import { TranscriptInputProps } from '../types';

const TranscriptInput: React.FC<TranscriptInputProps> = ({ value, onChange }) => {
  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>): void => {
    onChange(event.target.value);
  };

  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0;
  const charCount = value.length;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Transcript
      </label>
      <textarea
        value={value}
        onChange={handleChange}
        rows={6}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical"
        placeholder="Enter the audio/video transcript here..."
      />
      <div className="mt-2 flex justify-between text-xs text-gray-500">
        <span>{wordCount} words</span>
        <span>{charCount} characters</span>
      </div>
    </div>
  );
};

export default TranscriptInput;
