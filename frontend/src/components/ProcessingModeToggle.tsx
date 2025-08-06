import React from 'react';

interface ProcessingModeToggleProps {
  mode: 'normal' | 'keywords' | 'text-only';
  onModeChange: (mode: 'normal' | 'keywords' | 'text-only') => void;
  hasAudio: boolean;
}

const ProcessingModeToggle: React.FC<ProcessingModeToggleProps> = ({ 
  mode, 
  onModeChange, 
  hasAudio 
}) => {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-3">
        Processing Mode
      </label>
      
      <div className="space-y-3">
        {/* Normal Mode */}
        <div className="flex items-center">
          <input
            id="mode-normal"
            name="processing-mode"
            type="radio"
            checked={mode === 'normal'}
            onChange={() => onModeChange('normal')}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
          />
          <label htmlFor="mode-normal" className="ml-3 block text-sm text-gray-900">
            <div className="font-medium">Audio Processing</div>
            <div className="text-gray-500">
              Full validation with audio + transcript (audio upload required)
            </div>
          </label>
        </div>

        {/* Text-only Mode */}
        <div className="flex items-center">
          <input
            id="mode-text-only"
            name="processing-mode"
            type="radio"
            checked={mode === 'text-only'}
            onChange={() => onModeChange('text-only')}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
          />
          <label htmlFor="mode-text-only" className="ml-3 block text-sm text-gray-900">
            <div className="font-medium">Text-only Processing</div>
            <div className="text-gray-500">
              Validation with transcript only (no audio required)
            </div>
          </label>
        </div>

        {/* Keywords Mode */}
        <div className="flex items-center">
          <input
            id="mode-keywords"
            name="processing-mode"
            type="radio"
            checked={mode === 'keywords'}
            onChange={() => onModeChange('keywords')}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
          />
          <label htmlFor="mode-keywords" className="ml-3 block text-sm text-gray-900">
            <div className="font-medium">Keywords Mode</div>
            <div className="text-gray-500">
              Skip validation, use transcript + custom keywords
            </div>
          </label>
        </div>
      </div>

      {/* Mode explanation */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <div className="text-sm text-blue-800">
          {mode === 'normal' && (
            <div>
              <strong>Audio Processing:</strong> Full validation using both audio and transcript. 
              Gemini will analyze the audio and correct the transcript if needed. Requires audio upload.
            </div>
          )}
          {mode === 'text-only' && (
            <div>
              <strong>Text-only Mode:</strong> Validation using transcript only. 
              Gemini will process the text without audio analysis. No audio required. ~100-200ms faster.
            </div>
          )}
          {mode === 'keywords' && (
            <div>
              <strong>Keywords Mode:</strong> Bypass validation completely. 
              Use transcript as-is and provide custom keywords for search. No audio required. ~200-500ms faster.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProcessingModeToggle;
