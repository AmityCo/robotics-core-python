import * as React from 'react';

interface SSEMessage {
  id: string;
  type: string;
  message?: string;
  content?: string;
  timestamp: string;
  data?: any;
}

interface SSEOutputProps {
  messages: SSEMessage[];
  isProcessing: boolean;
}

const SSEOutput = ({ messages, isProcessing }: SSEOutputProps) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const prevMessageCountRef = React.useRef(0);
  const [userHasScrolled, setUserHasScrolled] = React.useState(false);

  // Only auto-scroll when new messages arrive and user hasn't manually scrolled
  React.useEffect(() => {
    if (messages.length > prevMessageCountRef.current && !userHasScrolled) {
      if (messagesEndRef.current) {
        // messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }
    prevMessageCountRef.current = messages.length;
  }, [messages, userHasScrolled]);

  // Handle user scroll to detect manual scrolling
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50; // 50px threshold
    setUserHasScrolled(!isAtBottom);
  };

  // Group consecutive answer_chunk messages together
  const groupedMessages = React.useMemo(() => {
    const grouped: Array<SSEMessage & { isGrouped?: boolean; groupedContent?: string }> = [];
    let currentAnswerGroup: string[] = [];
    let currentAnswerStartId: string = '';

    messages.forEach((message, index) => {
      if (message.type === 'answer_chunk') {
        if (currentAnswerGroup.length === 0) {
          currentAnswerStartId = message.id;
        }
        const content = message.data?.content || message.content || message.message || '';
        currentAnswerGroup.push(content);
      } else {
        // If we have accumulated answer chunks, add them as a single grouped message
        if (currentAnswerGroup.length > 0) {
          grouped.push({
            id: currentAnswerStartId,
            type: 'answer_chunk',
            timestamp: messages[index - 1]?.timestamp || message.timestamp,
            isGrouped: true,
            groupedContent: currentAnswerGroup.join('')
          });
          currentAnswerGroup = [];
        }
        grouped.push(message);
      }
    });

    // Handle any remaining answer chunks at the end
    if (currentAnswerGroup.length > 0) {
      grouped.push({
        id: currentAnswerStartId,
        type: 'answer_chunk',
        timestamp: messages[messages.length - 1]?.timestamp || new Date().toISOString(),
        isGrouped: true,
        groupedContent: currentAnswerGroup.join('')
      });
    }

    return grouped;
  }, [messages]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const decodeContent = (content: string) => {
    // Handle HTML entities and ensure proper UTF-8 display
    try {
      // Create a temporary element to decode HTML entities
      const textarea = document.createElement('textarea');
      textarea.innerHTML = content;
      let decoded = textarea.value;
      
      // Clean up any remaining encoding artifacts and common Thai character issues
      decoded = decoded
        // Remove </s> tags
        .replace(/<\/s>/g, '')
        // Remove [meta:docs] content
        .replace(/\[meta:docs\].*$/, '')
        // Fix common UTF-8 encoding issues for Thai characters
        .replace(/Ã /g, 'อ')
        .replace(/Ã¸/g, 'อ')
        .replace(/Ã¹/g, 'ู')
        .replace(/Ã/g, 'ี')
        .replace(/Ã¡/g, 'า')
        .replace(/Ã¨/g, 'ห')
        .replace(/Ã/g, 'น')
        .replace(/Ã¢/g, 'ใ')
        .replace(/Ã­/g, 'ย')
        .replace(/Ã¯/g, 'ไ')
        .replace(/Ã°/g, 'ร')
        .replace(/à¸/g, '')
        // Additional Thai character fixes
        .replace(/à¸à¸³/g, 'อยู่')
        .replace(/à¸à¸²à¸¡/g, 'ที่')
        .replace(/à¸à¸µà¹/g, 'ที่')
        // Trim whitespace
        .trim();
      
      return decoded;
    } catch (error) {
      console.warn('Error decoding content:', error);
      // Fallback: just clean up basic artifacts
      return content
        .replace(/<\/s>/g, '')
        .replace(/\[meta:docs\].*$/, '')
        .trim();
    }
  };

  const renderMessageContent = (message: SSEMessage & { isGrouped?: boolean; groupedContent?: string }) => {
    let content = '';

    // Handle grouped answer chunks
    if (message.isGrouped && message.groupedContent) {
      content = message.groupedContent;
    }
    // Handle different message formats
    else if (message.message) {
      content = message.message;
    }
    else if (message.content) {
      content = message.content;
    }
    else if (message.data) {
      switch (message.type) {
        case 'validation_result':
          content = `Validation: ${message.data.correction || 'Processing validation...'}`;
          break;
        
        case 'km_result':
          const kmData = message.data;
          if (kmData.total && kmData.data && kmData.data.length > 0) {
            const doc = kmData.data[0].document;
            content = `Found ${kmData.total} result(s): ${doc.content}`;
          } else {
            content = `Knowledge search completed (${kmData.total || 0} results)`;
          }
          break;
        
        case 'thinking':
          content = `AI Thinking: ${message.data.content || 'Processing...'}`;
          break;
        
        case 'answer_chunk':
          content = message.data.content || '';
          break;
        
        default:
          content = JSON.stringify(message.data, null, 2);
      }
    }
    else {
      content = 'Unknown message format';
    }

    // Decode the content to fix encoding issues
    return decodeContent(content);
  };

  const getMessageStyle = (type: string) => {
    switch (type) {
      case 'status':
        return 'bg-blue-50 border-blue-200';
      case 'validation_result':
        return 'bg-green-50 border-green-200';
      case 'km_result':
        return 'bg-purple-50 border-purple-200';
      case 'thinking':
        return 'bg-yellow-50 border-yellow-200';
      case 'answer_chunk':
        return 'bg-gray-50 border-gray-200';
      case 'complete':
        return 'bg-green-100 border-green-300';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  if (messages.length === 0 && !isProcessing) {
    return (
      <div className="flex items-center justify-center text-gray-500">
        <div className="text-center">
          <p className="mt-2">No messages yet</p>
          <p className="text-sm">Start processing to see real-time output</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="overflow-y-auto space-y-3 pr-2" onScroll={handleScroll}>
        {groupedMessages.map((message) => (
          <div
            key={message.id}
            className={`p-3 rounded-lg border ${getMessageStyle(message.type)}`}
          >
            <div className="flex items-start space-x-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-700 uppercase tracking-wide">
                    {message.isGrouped && message.type === 'answer_chunk' ? 'Final Answer' : message.type}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(message.timestamp)}
                  </span>
                </div>
                <div className="text-sm text-gray-800">
                  <div className="whitespace-pre-wrap">
                    {renderMessageContent(message)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {isProcessing && (
          <div className="p-3 rounded-lg border bg-blue-50 border-blue-200">
            <div className="flex items-center space-x-3">
              <div className="text-sm text-blue-700">
                Waiting for more data...
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Scroll to bottom button - only show when user has scrolled up */}
      {userHasScrolled && (
        <button
          onClick={() => {
            setUserHasScrolled(false);
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="absolute bottom-4 right-4 bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-full shadow-lg transition-colors duration-200"
          title="Scroll to bottom"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>
      )}
    </div>
  );
};

export default SSEOutput;
