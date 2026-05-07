import type { ReactNode } from 'react';

import type { Message, Session } from '../types/chat';
import { TurnRenderer } from './TurnRenderer';

interface ChatPanelProps {
  session: Session | null;
  error: string | null;
  onRetry: (message: Message) => Promise<void>;
  selectedAssistantMessageId: string | null;
  onSelectAssistantMessage: (message: Message) => void;
}

function findPreviousUserMessage(messages: Message[], index: number): Message | null {
  for (let i = index - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'user') {
      return messages[i];
    }
  }
  return null;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((part, index) =>
      part.startsWith('**') && part.endsWith('**') ? (
        <strong key={`strong-${index}`}>{part.slice(2, -2)}</strong>
      ) : (
        <span key={`text-${index}`}>{part}</span>
      ),
    );
}

function MessageContent({ message }: { message: Message }) {
  const text = message.content || (message.status === 'streaming' ? '...' : '');
  if (!text) {
    return null;
  }

  const blocks: ReactNode[] = [];
  const listItems: string[] = [];

  const flushList = () => {
    if (!listItems.length) {
      return;
    }
    blocks.push(
      <ul key={`list-${blocks.length}`} className="message-content-list">
        {listItems.map((item, index) => (
          <li key={`item-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>,
    );
    listItems.length = 0;
  };

  for (const line of text.split('\n')) {
    const trimmedLine = line.trim();
    if (!trimmedLine) {
      flushList();
      continue;
    }
    if (line.startsWith('- ') || trimmedLine.startsWith('- ')) {
      listItems.push(trimmedLine.slice(2));
      continue;
    }
    flushList();
    blocks.push(
      <p key={`paragraph-${blocks.length}`} className="message-content-paragraph">
        {renderInlineMarkdown(trimmedLine)}
      </p>,
    );
  }
  flushList();

  return <div className="message-content">{blocks}</div>;
}

export function ChatPanel({
  session,
  error,
  onRetry,
  selectedAssistantMessageId,
  onSelectAssistantMessage,
}: ChatPanelProps) {
  if (!session) {
    return (
      <section className="chat-panel empty">
        <div className="empty-shell">
          <h2>苏农云指挥调度智能</h2>
          <div className="suggestion-grid">
            <article className="suggestion-card">
              <strong>最近墒情怎么样？</strong>
              <span>适合验证最近 7 天概览和最新业务时间基准</span>
            </article>
            <article className="suggestion-card">
              <strong>最近30天，按地区汇总墒情数据</strong>
              <span>适合验证独立地区汇总和原始数据查询链</span>
            </article>
            <article className="suggestion-card">
              <strong>如东县最近怎么样？</strong>
              <span>适合验证地区详情、多轮继承和规则判断</span>
            </article>
            <article className="suggestion-card">
              <strong>按模板输出 SNS00213807 最新预警</strong>
              <span>适合验证预警模板、严格模式和设备事实校验</span>
            </article>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="chat-panel">
      <div className="messages" aria-label="消息列表">
        {session.messages.map((message, index) => {
          const retryMessage = message.status === 'error' ? findPreviousUserMessage(session.messages, index) : null;
          const isSelectable = message.role === 'assistant' && message.status === 'done' && Boolean(message.meta);
          const isSelected = isSelectable && selectedAssistantMessageId === message.id;

          return (
            <article
              key={message.id}
              className={`message-row ${message.role} ${isSelected ? 'is-selected' : ''} ${isSelectable ? 'is-selectable' : ''}`}
            >
              <div className={`message-avatar ${message.role}`}>{message.role === 'user' ? '你' : 'AI'}</div>
              <div
                className={`message ${message.role} ${isSelectable ? 'selectable' : ''} ${isSelected ? 'selected' : ''}`}
                onClick={() => {
                  if (message.role === 'assistant' && isSelectable) {
                    onSelectAssistantMessage(message);
                  }
                }}
              >
                <MessageContent message={message} />
                {message.role === 'assistant' ? <TurnRenderer turn={message.meta?.turn ?? null} /> : null}
                {message.status === 'error' && retryMessage ? (
                  <button className="retry" onClick={() => onRetry(retryMessage)}>
                    重试
                  </button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
      {error ? <p className="error-tip">{error}</p> : null}
    </section>
  );
}
