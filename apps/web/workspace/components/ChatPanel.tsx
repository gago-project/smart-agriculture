import type { Message, Session } from '../types/chat';

interface ChatPanelProps {
  session: Session | null;
  error: string | null;
  selectedEvidenceMessageId: string | null;
  onRetry: (message: Message) => Promise<void>;
  onSelectEvidenceMessage: (messageId: string) => void;
}

function findPreviousUserMessage(messages: Message[], index: number): Message | null {
  for (let i = index - 1; i >= 0; i -= 1) {
    if (messages[i].role === 'user') {
      return messages[i];
    }
  }
  return null;
}

export function ChatPanel({ session, error, selectedEvidenceMessageId, onRetry, onSelectEvidenceMessage }: ChatPanelProps) {
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
              <strong>最近30天，哪些地区墒情异常最多？</strong>
              <span>适合验证墒情异常统计与处理链</span>
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
          const selectable = message.role === 'assistant' && Boolean(message.meta);
          const selected = selectable && message.id === selectedEvidenceMessageId;
          const aiInvolvement = message.role === 'assistant' ? message.meta?.processing?.ai_involvement : null;

          return (
            <article key={message.id} className={`message-row ${message.role}`}>
              <div className={`message-avatar ${message.role}`}>{message.role === 'user' ? '你' : 'AI'}</div>
              <div
                className={`message ${message.role}${selectable ? ' selectable' : ''}${selected ? ' selected' : ''}`}
                role={selectable ? 'button' : undefined}
                tabIndex={selectable ? 0 : undefined}
                aria-pressed={selectable ? selected : undefined}
                onClick={selectable ? () => onSelectEvidenceMessage(message.id) : undefined}
                onKeyDown={
                  selectable
                    ? (event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          onSelectEvidenceMessage(message.id);
                        }
                      }
                    : undefined
                }
              >
                {aiInvolvement ? (
                  <header className="message-header message-header-badge-only">
                    <span className={`ai-badge ai-${aiInvolvement}`}>AI参与度 {aiInvolvement}</span>
                  </header>
                ) : null}
                <p>{message.content || (message.status === 'streaming' ? '...' : '')}</p>
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
