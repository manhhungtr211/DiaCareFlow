export interface Message {
  id: string;
  role: 'user' | 'bot' | 'error';
  content: string;
  isRefused: boolean;
}
