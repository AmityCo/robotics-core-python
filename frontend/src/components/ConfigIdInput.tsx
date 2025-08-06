import React from 'react';
import { ConfigIdInputProps } from '../types';

const ConfigIdInput: React.FC<ConfigIdInputProps> = ({ value, onChange }) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange(event.target.value);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Configuration ID
      </label>
      <input
        type="text"
        value={value}
        onChange={handleChange}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder="Enter configuration ID (e.g., 45f9aacfe37ff6c7e072326c600a3b60)"
      />
      <p className="mt-1 text-xs text-gray-500">
        This ID is used to select a specific configuration within the organization
      </p>
    </div>
  );
};

export default ConfigIdInput;
