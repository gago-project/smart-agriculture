import { useEffect, useRef, useState } from 'react';
import type { Session } from '../types/chat';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onCreateSession: () => void;
  onSwitchSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onRenameSession,
  onDeleteSession
}: SessionSidebarProps) {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [openMenuSessionId, setOpenMenuSessionId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');
  const sidebarRef = useRef<HTMLElement | null>(null);

  function startRename(session: Session) {
    setEditingSessionId(session.id);
    setOpenMenuSessionId(null);
    setDraftTitle(session.title);
  }

  function submitRename(session: Session) {
    onRenameSession(session.id, draftTitle);
    setEditingSessionId(null);
    setDraftTitle('');
  }

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!sidebarRef.current?.contains(event.target as Node)) {
        setOpenMenuSessionId(null);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
    };
  }, []);

  return (
    <aside className="sidebar" ref={sidebarRef}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">DC</div>
        <div>
          <strong>AI 农情工作台</strong>
          <p>对话与分析</p>
        </div>
      </div>
      <button className="new-chat" onClick={onCreateSession}>
        + 新建会话
      </button>
      <div className="sidebar-section-title">最近会话</div>
      <div className="session-list" aria-label="会话列表">
        {sessions.length === 0 ? <p className="session-empty">新建一个会话，开始提问。</p> : null}
        {sessions.map((session) => (
          <div key={session.id} className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}>
            <button className="session-item-main" aria-label={session.title} onClick={() => onSwitchSession(session.id)}>
              {editingSessionId === session.id ? (
                <input
                  className="session-rename-input"
                  aria-label="会话名称"
                  autoFocus
                  value={draftTitle}
                  onChange={(event) => setDraftTitle(event.target.value)}
                  onClick={(event) => event.stopPropagation()}
                  onBlur={() => submitRename(session)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      submitRename(session);
                    }
                    if (event.key === 'Escape') {
                      event.preventDefault();
                      setEditingSessionId(null);
                      setDraftTitle('');
                    }
                  }}
                />
              ) : (
                <span className="session-item-title">{session.title}</span>
              )}
              <span className="session-item-meta">
                {session.messages.length > 0 ? `${session.messages.length} 条消息` : '空会话'}
              </span>
            </button>
            <div className="session-item-actions">
              <button
                className="session-item-action"
                type="button"
                aria-label={`会话操作 ${session.title}`}
                aria-expanded={openMenuSessionId === session.id}
                onClick={() => {
                  setOpenMenuSessionId((current) => (current === session.id ? null : session.id));
                }}
              >
                ⋯
              </button>
              {openMenuSessionId === session.id ? (
                <div className="session-item-menu" role="menu" aria-label={`会话菜单 ${session.title}`}>
                  <button
                    className="session-item-menu-action"
                    type="button"
                    role="menuitem"
                    onClick={() => startRename(session)}
                  >
                    编辑名称
                  </button>
                  <button
                    className="session-item-menu-action danger"
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setOpenMenuSessionId(null);
                      if (window.confirm(`确认删除会话“${session.title}”吗？`)) {
                        onDeleteSession(session.id);
                      }
                    }}
                  >
                    删除会话
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
