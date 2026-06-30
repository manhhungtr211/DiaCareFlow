import { Header } from '../../components/Header/Header';
import { MessageList } from '../../components/MessageList/MessageList';
import { ChatInput } from '../../components/ChatInput/ChatInput';
import { useChat } from '../../hooks/useChat';
import './ChatPage.css';

export function ChatPage() {
  const { messages, isLoading, sendMessage } = useChat();

  return (
    <div className="chat-page" id="chat-page">
      <Header />
      <main className="chat-page__main">
        <MessageList messages={messages} isLoading={isLoading} />
      </main>
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
