import { useState, useCallback } from 'react';
import type { Message } from '../types/message';
import { sendMessage as sendChatMessage } from '../services/chatService';

let messageCounter = 0;

function generateId(): string {
  messageCounter += 1;
  return `msg-${Date.now()}-${messageCounter}`;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (question: string) => {
    // Add user message
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: question,
      isRefused: false,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(question);

      const botMessage: Message = {
        id: generateId(),
        role: response.isError ? 'error' : 'bot',
        content: response.content,
        isRefused: response.isRefused,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch {
      // Fallback error — should not normally reach here
      const errorMessage: Message = {
        id: generateId(),
        role: 'error',
        content: 'Không thể kết nối đến server. Vui lòng thử lại sau.',
        isRefused: false,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, sendMessage };
}
