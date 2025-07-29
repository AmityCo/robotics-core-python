# ARC2 Server Frontend

A React.js + Tailwind CSS web application for testing the ARC2 Server's SSE (Server-Sent Events) endpoint.

## Features

- **Real-time SSE Communication**: Connect to the `/api/v1/answer-sse` endpoint and display real-time progress updates
- **File Upload**: Upload video/audio files and convert them to base64 for API requests
- **Transcript Input**: Enter or edit transcripts with word and character counting
- **Organization Configuration**: Input organization ID for DynamoDB configuration lookup
- **Multi-language Support**: Select from various languages (English, Thai, Chinese, etc.)
- **Live Output Display**: See validation, knowledge management search, and answer generation results in real-time
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Node.js 14+ and npm
- The ARC2 Python server running on `http://localhost:8000`

## Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open your browser and go to `http://localhost:3000`

## Usage

1. **Upload a Video/Audio File**: Click the upload area or drag-and-drop a video or audio file
2. **Enter Organization ID**: Provide the organization ID (e.g., "test-org-1")
3. **Select Language**: Choose the appropriate language from the dropdown
4. **Enter Transcript**: Type or paste the transcript of the audio/video content
5. **Start Processing**: Click "Start Processing" to begin the SSE request
6. **Monitor Output**: Watch real-time updates in the output panel as the server processes your request

## SSE Message Types

The application handles various SSE message types:

- **status**: General status updates
- **validation**: Gemini validation results with corrections and search terms
- **km_search**: Knowledge management search results
- **answer_thinking**: AI reasoning process (if available)
- **answer_stream**: Streaming answer content
- **error**: Error messages
- **complete**: Completion notifications

## API Integration

The frontend communicates with the ARC2 server's `/api/v1/answer-sse` endpoint using:

```javascript
{
  "transcript": "string",
  "language": "string", 
  "base64_audio": "string",
  "org_id": "string"
}
```

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory to override default settings:

```env
REACT_APP_API_URL=http://localhost:8000
```

### Proxy Configuration

The `package.json` includes a proxy configuration to forward API requests to the Python server during development.

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── VideoUpload.js      # File upload component
│   │   ├── TranscriptInput.js  # Transcript input component
│   │   ├── OrgIdInput.js       # Organization ID input
│   │   └── SSEOutput.js        # Real-time output display
│   ├── utils/
│   │   └── sseClient.js        # SSE client utilities
│   ├── App.js                  # Main application component
│   ├── index.js               # React app entry point
│   └── index.css              # Global styles with Tailwind
├── package.json
├── tailwind.config.js
└── postcss.config.js
```

## Development

### Available Scripts

- `npm start`: Start development server
- `npm build`: Build for production
- `npm test`: Run tests
- `npm eject`: Eject from Create React App (not recommended)

### Styling

The application uses Tailwind CSS for styling. The design includes:

- Clean, modern interface
- Responsive grid layout
- Real-time animations for SSE messages
- Color-coded message types
- Custom scrollbars

### Testing the SSE Connection

1. Ensure the ARC2 Python server is running
2. Use the test organization ID provided in your server configuration
3. Upload a sample audio/video file
4. Enter a transcript and start processing
5. Monitor the console for any connection issues

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure the Python server has proper CORS configuration
2. **File Upload Issues**: Check file size limits and supported formats
3. **SSE Connection Fails**: Verify the API URL and server status
4. **No Messages Received**: Check browser console for JavaScript errors

### Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Contributing

1. Follow React best practices
2. Use Tailwind CSS for styling
3. Maintain TypeScript-style prop validation
4. Test SSE functionality thoroughly
5. Update documentation for new features
