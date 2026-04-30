import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, MouseEvent as ReactMouseEvent } from 'react';
import type { Session } from '../types/chat';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onCreateSession: () => void | Promise<unknown>;
  onSwitchSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void | Promise<unknown>;
  onDeleteSession: (sessionId: string) => void | Promise<unknown>;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onCreateSession,
  onSwitchSession,
  onRenameSession,
  onDeleteSession,
}: SessionSidebarProps) {
  const sidebarRef = useRef<HTMLElement | null>(null);
  const renameInputRef = useRef<HTMLInputElement | null>(null);
  const skipBlurSubmitRef = useRef(false);
  const [menuSessionId, setMenuSessionId] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [savingSessionId, setSavingSessionId] = useState<string | null>(null);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!menuSessionId) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element)) {
        setMenuSessionId(null);
        return;
      }
      if (!sidebarRef.current?.contains(target) || !target.closest('[data-session-menu-root="true"]')) {
        setMenuSessionId(null);
      }
    }

    document.addEventListener('pointerdown', handlePointerDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
    };
  }, [menuSessionId]);

  useEffect(() => {
    if (!editingSessionId || !renameInputRef.current) {
      return;
    }
    renameInputRef.current.focus();
    renameInputRef.current.select();
  }, [editingSessionId]);

  useEffect(() => {
    if (editingSessionId && !sessions.some((session) => session.id === editingSessionId)) {
      setEditingSessionId(null);
      setRenameDraft('');
    }
    if (menuSessionId && !sessions.some((session) => session.id === menuSessionId)) {
      setMenuSessionId(null);
    }
  }, [editingSessionId, menuSessionId, sessions]);

  function startRename(session: Session) {
    skipBlurSubmitRef.current = false;
    setEditingSessionId(session.id);
    setRenameDraft(session.title);
    setMenuSessionId(null);
  }

  function cancelRename() {
    skipBlurSubmitRef.current = true;
    setEditingSessionId(null);
    setRenameDraft('');
  }

  async function submitRename(session: Session) {
    if (savingSessionId === session.id) {
      return;
    }
    if (renameDraft.trim() === session.title.trim()) {
      cancelRename();
      return;
    }
    setSavingSessionId(session.id);
    try {
      await onRenameSession(session.id, renameDraft);
      skipBlurSubmitRef.current = false;
      setEditingSessionId(null);
      setRenameDraft('');
    } catch {
      return;
    } finally {
      setSavingSessionId(null);
    }
  }

  function handleMenuToggle(event: ReactMouseEvent<HTMLButtonElement>, sessionId: string) {
    event.stopPropagation();
    setMenuSessionId((current) => (current === sessionId ? null : sessionId));
  }

  function handleRenameKeyDown(event: KeyboardEvent<HTMLInputElement>, session: Session) {
    if (event.key === 'Enter') {
      event.preventDefault();
      void submitRename(session);
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelRename();
    }
  }

  return (
    <aside className="sidebar" ref={sidebarRef}>
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
            {editingSessionId === session.id ? (
              <div className="session-item-main">
                <input
                  ref={renameInputRef}
                  className="session-rename-input"
                  value={renameDraft}
                  disabled={savingSessionId === session.id}
                  aria-label={`修改会话名称 ${session.title}`}
                  onChange={(event) => setRenameDraft(event.target.value)}
                  onKeyDown={(event) => handleRenameKeyDown(event, session)}
                  onBlur={() => {
                    if (skipBlurSubmitRef.current) {
                      skipBlurSubmitRef.current = false;
                      return;
                    }
                    void submitRename(session);
                  }}
                />
                <span className="session-item-meta">
                  {session.lastTurnId > 0 ? `${session.lastTurnId} 轮对话` : '空会话'}
                </span>
              </div>
            ) : (
              <button className="session-item-main" aria-label={session.title} onClick={() => onSwitchSession(session.id)}>
                <span className="session-item-title">{session.title}</span>
                <span className="session-item-meta">
                  {session.lastTurnId > 0 ? `${session.lastTurnId} 轮对话` : '空会话'}
                </span>
              </button>
            )}
            <div className="session-item-actions" data-session-menu-root="true">
              <button
                className="session-item-action"
                type="button"
                aria-label={`更多操作 ${session.title}`}
                aria-haspopup="menu"
                aria-expanded={menuSessionId === session.id}
                onClick={(event) => handleMenuToggle(event, session.id)}
              >
                ...
              </button>
              {menuSessionId === session.id ? (
                <div className="session-item-menu">
                  <button
                    className="session-item-menu-action"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      startRename(session);
                    }}
                  >
                    修改名称
                  </button>
                  <button
                    className="session-item-menu-action danger"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      setMenuSessionId(null);
                      void onDeleteSession(session.id);
                    }}
                  >
                    归档
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
