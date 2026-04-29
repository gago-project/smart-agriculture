import type { Session } from '../types/chat';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onCreateSession: () => void | Promise<unknown>;
  onSwitchSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void | Promise<unknown>;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onDeleteSession,
}: SessionSidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">DC</div>
        <div>
          <strong>AI 农情工作台</strong>
          <p>服务端会话</p>
        </div>
      </div>
      <button className="new-chat" onClick={() => void onCreateSession()}>
        + 新建会话
      </button>
      <div className="sidebar-section-title">最近会话</div>
      <div className="session-list" aria-label="会话列表">
        {sessions.length === 0 ? <p className="session-empty">新建一个会话，开始提问。</p> : null}
        {sessions.map((session) => (
          <div key={session.id} className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}>
            <button className="session-item-main" aria-label={session.title} onClick={() => onSwitchSession(session.id)}>
              <span className="session-item-title">{session.title}</span>
              <span className="session-item-meta">
                {session.lastTurnId > 0 ? `${session.lastTurnId} 轮对话` : '空会话'}
              </span>
            </button>
            <div className="session-item-actions">
              <button
                className="session-item-action"
                type="button"
                aria-label={`归档会话 ${session.title}`}
                onClick={() => void onDeleteSession(session.id)}
              >
                归档
              </button>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
