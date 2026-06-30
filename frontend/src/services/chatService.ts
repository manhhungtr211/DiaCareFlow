const API_BASE_URL = '/api';

/**
 * Refusal detection patterns — check if the bot response is a policy refusal.
 * These patterns match typical refusal phrases from the DiaCareFlow agent.
 */
const REFUSAL_PATTERNS = [
  'xin lỗi, tôi không thể',
  'tôi không được phép',
  'không thể kê đơn',
  'không thể chẩn đoán',
  'vượt quá phạm vi',
  'ngoài khả năng',
  'không thể tư vấn điều trị',
];

export interface ChatResponse {
  content: string;
  isRefused: boolean;
  isError: boolean;
}

/**
 * Detect if a response text contains refusal patterns.
 */
function detectRefusal(text: string): boolean {
  const lowerText = text.toLowerCase();
  return REFUSAL_PATTERNS.some((pattern) => lowerText.includes(pattern));
}

/**
 * Send a chat message to the backend API.
 * Backend returns a raw string (response_model=str), parsed via .text().
 *
 * @param question - The user's question text
 * @returns ChatResponse with content, refusal flag, and error flag
 */
export async function sendMessage(question: string): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      if (response.status >= 500) {
        // E2: Backend internal error
        return {
          content: 'Đã xảy ra lỗi hệ thống. Vui lòng thử lại.',
          isRefused: false,
          isError: true,
        };
      }
      return {
        content: `Lỗi: Server trả về mã ${response.status}. Vui lòng thử lại.`,
        isRefused: false,
        isError: true,
      };
    }

    const text = await response.text();
    // Remove surrounding quotes if backend wraps the string in JSON quotes
    const content = text.replace(/^"|"$/g, '').replace(/\\n/g, '\n');

    return {
      content,
      isRefused: detectRefusal(content),
      isError: false,
    };
  } catch (error: unknown) {
    // E1: Network error — backend not running or unreachable
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return {
        content: 'Không thể kết nối đến server. Vui lòng thử lại sau.',
        isRefused: false,
        isError: true,
      };
    }
    return {
      content: 'Không thể kết nối đến server. Vui lòng thử lại sau.',
      isRefused: false,
      isError: true,
    };
  }
}
