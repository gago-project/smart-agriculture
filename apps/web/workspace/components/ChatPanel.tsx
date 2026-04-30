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
          <h2>AI 农情工作台</h2>
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
                <p>{message.content || (message.status === 'streaming' ? '...' : '')}</p>
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
