import { useEffect, useRef, useState } from 'react';
import pkg from '../../package.json';
import type { KeyboardEvent, MouseEvent as ReactMouseEvent } from 'react';
import type { Message, Session } from '../types/chat';

interface SessionSidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onCreateSession: () => void | Promise<unknown>;
  onSwitchSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => void | Promise<unknown>;
  onDeleteSession: (sessionId: string) => void | Promise<unknown>;
}

interface SearchResult {
  session: Session;
  tag: '标题' | '问题' | '回答';
  titleSnippet: { prefix: string; match: string; suffix: string } | null;
  bodySnippet: { prefix: string; match: string; suffix: string } | null;
}

function getSnippet(
  text: string,
  query: string,
): { prefix: string; match: string; suffix: string } | null {
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx < 0) return null;
  const CTX = 28;
  const start = Math.max(0, idx - CTX);
  const end = Math.min(text.length, idx + query.length + CTX);
  return {
    prefix: (start > 0 ? '…' : '') + text.slice(start, idx),
    match: text.slice(idx, idx + query.length),
    suffix: text.slice(idx + query.length, end) + (end < text.length ? '…' : ''),
  };
}

function computeSearchResults(sessions: Session[], query: string): SearchResult[] {
  const q = query.trim();
  if (!q) return [];

  const results: SearchResult[] = [];
  for (const session of sessions) {
    const titleSnippet = getSnippet(session.title, q);
    if (titleSnippet) {
      results.push({ session, tag: '标题', titleSnippet, bodySnippet: null });
      continue;
    }

    let matched: { tag: '问题' | '回答'; message: Message } | null = null;
    for (const message of session.messages) {
      if (message.role === 'user') {
        if (message.content.toLowerCase().includes(q.toLowerCase())) {
          matched = { tag: '问题', message };
          break;
        }
      } else {
        const text = message.meta?.turn?.final_text ?? message.content;
        if (text.toLowerCase().includes(q.toLowerCase())) {
          matched = { tag: '回答', message };
          break;
        }
      }
    }

    if (matched) {
      const text =
        matched.tag === '回答'
          ? (matched.message.meta?.turn?.final_text ?? matched.message.content)
          : matched.message.content;
      results.push({
        session,
        tag: matched.tag,
        titleSnippet: null,
        bodySnippet: getSnippet(text, q),
      });
    }
  }

  return results;
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
  const [searchQuery, setSearchQuery] = useState('');

  const searchResults = computeSearchResults(sessions, searchQuery);
  const isSearching = searchQuery.trim().length > 0;

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

  function handleSearchResultClick(sessionId: string) {
    onSwitchSession(sessionId);
    setSearchQuery('');
  }

  return (
    <aside className="sidebar" ref={sidebarRef}>
      <div className="sidebar-brand">
        <div className="sidebar-brand-copy">
          <strong>苏农云指挥调度智能<span className="sidebar-version">v{pkg.version}</span></strong>
          <p>本地会话</p>
        </div>
      </div>
      <button className="new-chat" onClick={() => void onCreateSession()}>
        <span className="new-chat-icon">+</span>
        <span>新建会话</span>
      </button>
      <div className="sidebar-search">
        <input
          className="sidebar-search-input"
          type="search"
          placeholder="搜索会话、问题、回答…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>
      <div className="sidebar-section-title">
        {isSearching ? `搜索结果（${searchResults.length}）` : '最近会话'}
      </div>
      {isSearching ? (
        <div className="session-list" aria-label="搜索结果">
          {searchResults.length === 0 ? (
            <p className="session-empty">未找到匹配的会话。</p>
          ) : null}
          {searchResults.map(({ session, tag, titleSnippet, bodySnippet }) => (
            <button
              key={session.id}
              className={`search-result-item ${session.id === activeSessionId ? 'active' : ''}`}
              onClick={() => handleSearchResultClick(session.id)}
            >
              <div className="search-result-header">
                <span className="search-result-title">
                  {titleSnippet ? (
                    <>
                      {titleSnippet.prefix}
                      <mark className="search-highlight">{titleSnippet.match}</mark>
                      {titleSnippet.suffix}
                    </>
                  ) : (
                    session.title
                  )}
                </span>
                <span className="search-result-tag">{tag}</span>
              </div>
              {bodySnippet ? (
                <p className="search-result-snippet">
                  {bodySnippet.prefix}
                  <mark className="search-highlight">{bodySnippet.match}</mark>
                  {bodySnippet.suffix}
                </p>
              ) : null}
            </button>
          ))}
        </div>
      ) : (
        <div className="session-list" aria-label="会话列表">
          {sessions.length === 0 ? <p className="session-empty">新建一个会话，开始提问。</p> : null}
          {sessions.map((session) => {
            const isMenuOpen = menuSessionId === session.id;

            return (
              <div
                key={session.id}
                className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
                data-menu-open={isMenuOpen ? 'true' : 'false'}
              >
                <div className="session-item-surface">
                  {editingSessionId === session.id ? (
                    <div className="session-item-main">
                      <div className="session-item-title-row">
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
                      </div>
                      <div className="session-item-meta-row">
                        <span className="session-item-meta">
                          {session.lastTurnId > 0 ? `${session.lastTurnId} 轮对话` : '空会话'}
                        </span>
                        {session.id === activeSessionId ? <span className="session-item-status">当前</span> : null}
                      </div>
                    </div>
                  ) : (
                    <button className="session-item-main" aria-label={session.title} onClick={() => onSwitchSession(session.id)}>
                      <div className="session-item-title-row">
                        <span className="session-item-title">{session.title}</span>
                      </div>
                      <div className="session-item-meta-row">
                        <span className="session-item-meta">
                          {session.lastTurnId > 0 ? `${session.lastTurnId} 轮对话` : '空会话'}
                        </span>
                        {session.id === activeSessionId ? <span className="session-item-status">当前</span> : null}
                      </div>
                    </button>
                  )}
                  <div className="session-item-actions" data-session-menu-root="true">
                    <button
                      className="session-item-action"
                      type="button"
                      aria-label={`更多操作 ${session.title}`}
                      aria-haspopup="menu"
                      aria-expanded={isMenuOpen}
                      onClick={(event) => handleMenuToggle(event, session.id)}
                    >
                      ⋯
                    </button>
                    {isMenuOpen ? (
                      <div className="session-item-menu" data-session-menu-root="true">
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
                          删除
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}
