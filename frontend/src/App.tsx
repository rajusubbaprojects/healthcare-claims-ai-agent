import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_URL = 'http://13.222.27.183:8000';

interface Message {
  role: 'user' | 'agent';
  text: string;
}

const SUGGESTIONS = [
  'What is denial code CO-4?',
  'Look up claim CLM-2026-23363-817E',
  'What is prior authorization?',
  'Help me write an appeal letter',
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'agent',
      text: "Hello! I'm your Healthcare Claims AI Agent. I can help you understand claim denials, look up claim status, explain denial codes, and generate appeal letters. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setShowSuggestions(false);
    setMessages(prev => [...prev, { role: 'user', text }]);
    setInput('');
    setIsLoading(true);

    try {
      const body: any = { message: text };
      if (sessionId) body.session_id = sessionId;

      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (data.response) {
        setSessionId(data.session_id);
        setMessages(prev => [...prev, { role: 'agent', text: data.response }]);
      } else {
        setMessages(prev => [...prev, { role: 'agent', text: 'Sorry, I encountered an error. Please try again.' }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'agent', text: 'Unable to connect to the agent. Please check the API and try again.' }]);
    }

    setIsLoading(false);
    textareaRef.current?.focus();
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const formatText = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/#{1,3} (.*)/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="app">
      <div className="chat-container">
        <div className="chat-header">
          <div className="header-left">
            <div className="status-dot" />
            <span className="header-title">Healthcare Claims AI Agent</span>
          </div>
          <span className="header-badge">powered by Claude</span>
        </div>

        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="avatar">
                {msg.role === 'agent' ? 'HC' : 'You'}
              </div>
              <div
                className="bubble"
                dangerouslySetInnerHTML={{ __html: formatText(msg.text) }}
              />
            </div>
          ))}

          {isLoading && (
            <div className="message agent">
              <div className="avatar">HC</div>
              <div className="bubble typing">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {showSuggestions && (
          <div className="suggestions">
            {SUGGESTIONS.map((s, i) => (
              <button key={i} className="chip" onClick={() => sendMessage(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="input-row">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about a claim, denial code, or appeal..."
            rows={1}
          />
          <button
            className="send-btn"
            onClick={() => sendMessage(input)}
            disabled={isLoading || !input.trim()}
          >
            ➤
          </button>
        </div>
        <div className="disclaimer">
          Session memory active · {API_URL.replace('http://', '')}
        </div>
      </div>
    </div>
  );
}