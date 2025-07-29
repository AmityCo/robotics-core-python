import React from 'react';
import { OrgIdInputProps } from '../types';

const OrgIdInput: React.FC<OrgIdInputProps> = ({ value, onChange }) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    onChange(event.target.value);
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Organization ID
      </label>
      <input
        type="text"
        value={value}
        onChange={handleChange}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder="Enter organization ID (e.g., test-org-1)"
      />
      <p className="mt-1 text-xs text-gray-500">
        This ID is used to load organization-specific configuration from DynamoDB
      </p>
    </div>
  );
};

export default OrgIdInput;
