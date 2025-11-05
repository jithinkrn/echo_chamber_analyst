'use client';

import { useState } from 'react';
import { apiService, ChatMessage, ChatResponse } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentQuery, setCurrentQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);

  const sendMessage = async () => {
    if (!currentQuery.trim() || isLoading) return;

    const query = currentQuery.trim();
    setCurrentQuery('');
    setIsLoading(true);

    try {
      const response = await apiService.chat(query, messages);

      const newMessage: ChatMessage = {
        user: query,
        assistant: response.response,
      };

      setMessages(prev => [...prev, newMessage]);
      setLastResponse(response);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        user: query,
        assistant: 'Sorry, I encountered an error while processing your request. Please try again.',
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setLastResponse(null);
  };

  return (
    <div className="w-full bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium text-gray-900">AI Chat Assistant</h3>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear Chat
            </button>
          )}
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Ask questions about your analyzed content using our RAG-powered chatbot
        </p>
      </div>

      {/* Chat Messages */}
      <div className="h-[450px] overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Bot className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Start a conversation with the AI assistant</p>
              <p className="text-sm mt-2">Try asking: "What does EchoChamber Analyst do?"</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className="space-y-4">
              {/* User Message */}
              <div className="flex justify-end">
                <div className="flex max-w-4xl">
                  <div className="bg-blue-600 text-white rounded-lg px-4 py-2">
                    <p className="text-sm">{message.user}</p>
                  </div>
                  <div className="flex-shrink-0 ml-3">
                    <User className="h-6 w-6 text-gray-400" />
                  </div>
                </div>
              </div>

              {/* Assistant Message */}
              <div className="flex justify-start">
                <div className="flex max-w-4xl">
                  <div className="flex-shrink-0 mr-3">
                    <Bot className="h-6 w-6 text-blue-600" />
                  </div>
                  <div className="bg-gray-100 rounded-lg px-4 py-2 prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-strong:font-bold prose-strong:text-gray-900">
                    <ReactMarkdown>
                      {message.assistant}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex max-w-4xl">
              <div className="flex-shrink-0 mr-3">
                <Bot className="h-6 w-6 text-blue-600" />
              </div>
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="px-6 py-4 border-t border-gray-200">
        <div className="flex space-x-4">
          <div className="flex-1">
            <textarea
              value={currentQuery}
              onChange={(e) => setCurrentQuery(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Ask a question about your content..."
              rows={2}
              className="block w-full border border-gray-300 rounded-md px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              disabled={isLoading}
            />
          </div>
          <div className="flex-shrink-0">
            <button
              onClick={sendMessage}
              disabled={!currentQuery.trim() || isLoading}
              className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}