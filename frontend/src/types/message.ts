export interface Message {
  id: string;
  role: 'user' | 'bot' | 'error';
  session: string;
  content: string;
  isRefused: boolean;
}
