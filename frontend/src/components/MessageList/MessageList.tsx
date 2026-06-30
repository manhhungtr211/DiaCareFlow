import { useEffect, useRef } from 'react';
import type { Message } from '../../types/message';
import { ChatBubble } from '../ChatBubble/ChatBubble';
import { LoadingIndicator } from '../LoadingIndicator/LoadingIndicator';
import './MessageList.css';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="message-list" id="message-list">
      {messages.length === 0 && !isLoading && (
        <div className="message-list__empty">
          <div className="message-list__empty-icon">🩺</div>
          <h2 className="message-list__empty-title">
            Chào mừng bạn đến với DiaCareFlow
          </h2>
          <p className="message-list__empty-text">
            Hãy đặt câu hỏi về tiểu đường để bắt đầu cuộc trò chuyện.
          </p>
          <div className="message-list__suggestions">
            <span className="message-list__suggestion">Tiền tiểu đường là gì?</span>
            <span className="message-list__suggestion">Chỉ số đường huyết bình thường?</span>
            <span className="message-list__suggestion">Chế độ ăn cho người tiểu đường?</span>
          </div>
        </div>
      )}

      {messages.map((msg) => (
        <ChatBubble key={msg.id} message={msg} />
      ))}

      {isLoading && <LoadingIndicator />}

      <div ref={bottomRef} className="message-list__anchor" />
    </div>
  );
}
