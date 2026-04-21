'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { Composer } from './components/Composer';
import { EvidencePanel } from './components/EvidencePanel';
import { LoginPage } from './components/LoginPage';
import { SessionSidebar } from './components/SessionSidebar';
import { SoilAdminPage } from './components/SoilAdminPage';
import { useChatActions } from './hooks/useChatActions';
import { useAuthStore } from './store/authStore';
import { useChatStore } from './store/chatStore';

export default function App() {
  const authStatus = useAuthStore((state) => state.status);
  const authUser = useAuthStore((state) => state.user);
  const initAuth = useAuthStore((state) => state.initAuth);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const { sessions, activeSessionId, createSession, switchSession, renameSession, deleteSession } = useChatStore();
  const { activeSession, error, isSending, latestEvidenceMessage, retryForMessage, sendQuestion } = useChatActions();
  const [selectedEvidenceMessageId, setSelectedEvidenceMessageId] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmittingLogin, setIsSubmittingLogin] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<'chat' | 'soil-admin'>('chat');
  const previousSessionIdRef = useRef<string | null>(null);
  const previousLatestEvidenceIdRef = useRef<string | null>(null);
  const canManageSoilAdmin = authUser?.role === 'admin';

  const evidenceMessages = useMemo(
    () => activeSession?.messages.filter((message) => message.role === 'assistant' && Boolean(message.meta)) ?? [],
    [activeSession]
  );

  const selectedEvidenceMessage = useMemo(() => {
    if (selectedEvidenceMessageId) {
      const selected = evidenceMessages.find((message) => message.id === selectedEvidenceMessageId);
      if (selected) return selected;
    }
    return latestEvidenceMessage;
  }, [evidenceMessages, latestEvidenceMessage, selectedEvidenceMessageId]);

  useEffect(() => {
    void initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (!canManageSoilAdmin && workspaceView === 'soil-admin') {
      setWorkspaceView('chat');
    }
  }, [canManageSoilAdmin, workspaceView]);

  useEffect(() => {
    const sessionChanged = previousSessionIdRef.current !== activeSessionId;
    const previousLatestId = previousLatestEvidenceIdRef.current;

    previousSessionIdRef.current = activeSessionId;
    previousLatestEvidenceIdRef.current = latestEvidenceMessage?.id ?? null;

    setSelectedEvidenceMessageId((current) => {
      if (!latestEvidenceMessage) return null;
      const stillExists = current ? evidenceMessages.some((message) => message.id === current) : false;
      const shouldFollowLatest =
        sessionChanged ||
        current === null ||
        !stillExists ||
        current === previousLatestId;

      return shouldFollowLatest ? latestEvidenceMessage.id : current;
    });
  }, [activeSessionId, evidenceMessages, latestEvidenceMessage]);

  if (authStatus === 'idle' || authStatus === 'checking') {
    return (
      <div className="auth-shell">
        <div className="auth-card auth-loading">正在验证登录状态...</div>
      </div>
    );
  }

  if (authStatus !== 'authenticated' || !authUser) {
    return (
      <LoginPage
        isSubmitting={isSubmittingLogin}
        error={authError}
        onSubmit={async (username, password) => {
          setIsSubmittingLogin(true);
          setAuthError(null);
          try {
            await login(username, password);
          } catch (caughtError) {
            setAuthError(caughtError instanceof Error ? caughtError.message : '登录失败，请稍后重试');
          } finally {
            setIsSubmittingLogin(false);
          }
        }}
      />
    );
  }

  return (
    <div className="layout">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onCreateSession={() => createSession()}
        onSwitchSession={switchSession}
        onRenameSession={renameSession}
        onDeleteSession={deleteSession}
      />
      <main className="main">
        <header className="workspace-header">
          <div>
            <h1 className="workspace-title">AI 农情工作台</h1>
          </div>
          <div className="workspace-userbar">
            {canManageSoilAdmin ? (
              <button className="workspace-nav-button" onClick={() => setWorkspaceView(workspaceView === 'soil-admin' ? 'chat' : 'soil-admin')}>
                {workspaceView === 'soil-admin' ? '返回问答' : '墒情管理'}
              </button>
            ) : null}
            <span className="workspace-user">{authUser.username}</span>
            <button className="workspace-logout" onClick={() => void logout()}>
              退出登录
            </button>
          </div>
        </header>
        {workspaceView === 'soil-admin' ? (
          <SoilAdminPage />
        ) : (
          <>
            <ChatPanel
              session={activeSession}
              error={error}
              selectedEvidenceMessageId={selectedEvidenceMessageId}
              onRetry={async (message) => retryForMessage(activeSessionId!, message)}
              onSelectEvidenceMessage={setSelectedEvidenceMessageId}
            />
            <Composer isSending={isSending} onSend={sendQuestion} />
          </>
        )}
      </main>
      <EvidencePanel message={workspaceView === 'soil-admin' ? null : selectedEvidenceMessage} />
    </div>
  );
}
