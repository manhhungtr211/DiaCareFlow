import type { Message } from '../../types/message';
import './ChatBubble.css';

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const roleClass = `chat-bubble--${message.role}`;
  const refusedClass = message.isRefused ? 'chat-bubble--refused' : '';

  return (
    <div className={`chat-bubble ${roleClass} ${refusedClass}`}>
      {message.role === 'bot' && (
        <div className="chat-bubble__avatar">
          <span className="chat-bubble__avatar-icon">🩺</span>
        </div>
      )}

      <div className="chat-bubble__content">
        {message.isRefused && (
          <span className="chat-bubble__warning-icon" aria-label="Cảnh báo">
            ⚠️
          </span>
        )}

        {message.role === 'error' && (
          <span className="chat-bubble__error-icon" aria-label="Lỗi">
            ❌
          </span>
        )}

        <p className="chat-bubble__text">{message.content}</p>
      </div>
    </div>
  );
}
