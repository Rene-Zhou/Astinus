import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatBox from './ChatBox';
import type { Message } from '../../api/types';

// Mock translation
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => defaultValue || key,
  }),
}));

// Mock scroll behavior
window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe('ChatBox', () => {
  const mockMessages: Message[] = [
    {
      role: 'user',
      content: 'Hello GM',
      timestamp: '2024-01-01T12:00:00Z',
      turn: 1,
    },
    {
      role: 'assistant',
      content: 'Welcome to the game.',
      timestamp: '2024-01-01T12:00:01Z',
      turn: 1,
    },
  ];

  const mockOnSendMessage = vi.fn();

  it('renders empty state when no messages', () => {
    render(
      <ChatBox
        messages={[]}
        onSendMessage={mockOnSendMessage}
        isStreaming={false}
        streamingContent=""
        disabled={false}
      />
    );
    expect(screen.getByText(/game.startPrompt/i)).toBeInTheDocument();
  });

  it('renders list of messages', () => {
    render(
      <ChatBox
        messages={mockMessages}
        onSendMessage={mockOnSendMessage}
        isStreaming={false}
        streamingContent=""
        disabled={false}
      />
    );

    expect(screen.getByText('Hello GM')).toBeInTheDocument();
    expect(screen.getByText('Welcome to the game.')).toBeInTheDocument();
  });

  it('handles user input submission', () => {
    render(
      <ChatBox
        messages={mockMessages}
        onSendMessage={mockOnSendMessage}
        isStreaming={false}
        streamingContent=""
        disabled={false}
      />
    );

    const input = screen.getByPlaceholderText('game.inputPlaceholder');
    const sendBtn = screen.getByText('game.send');

    fireEvent.change(input, { target: { value: 'My Action' } });
    fireEvent.click(sendBtn);

    expect(mockOnSendMessage).toHaveBeenCalledWith('My Action');
  });

  it('disables input when disabled or streaming', () => {
    render(
      <ChatBox
        messages={[]}
        onSendMessage={mockOnSendMessage}
        isStreaming={true}
        streamingContent="Typing..."
        disabled={false}
      />
    );

    const input = screen.getByPlaceholderText('game.inputPlaceholder');
    expect(input).toBeDisabled();
    expect(screen.getByText('Typing...')).toBeInTheDocument();
  });
});
