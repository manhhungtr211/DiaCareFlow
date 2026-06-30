import { FormEvent, useState, useRef, useEffect } from 'react';
import './ChatInput.css';

interface ChatInputProps {
  onSend: (question: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [isShaking, setIsShaking] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();

    if (!trimmed) {
      // T027: Empty input validation — shake animation
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 500);
      return;
    }

    onSend(trimmed);
    setInput('');
  }

  return (
    <form
      className="chat-input"
      onSubmit={handleSubmit}
      id="chat-input-form"
    >
      <div className={`chat-input__wrapper ${isShaking ? 'chat-input__wrapper--shake' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="chat-input__field"
          id="chat-input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Nhập câu hỏi về tiểu đường..."
          disabled={isLoading}
          maxLength={2000}
          autoComplete="off"
        />
        <button
          type="submit"
          className="chat-input__send-btn"
          id="chat-send-button"
          disabled={isLoading}
          aria-label="Gửi tin nhắn"
        >
          {isLoading ? (
            <span className="chat-input__spinner" />
          ) : (
            <svg
              className="chat-input__send-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
    </form>
  );
}
