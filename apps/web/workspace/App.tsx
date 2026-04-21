'use client';

import { useEffect, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { Composer } from './components/Composer';
import { LoginPage } from './components/LoginPage';
import { SessionSidebar } from './components/SessionSidebar';
import { AgentLogPage } from './components/AgentLogPage';
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
  const { activeSession, error, isSending, retryForMessage, sendQuestion } = useChatActions();
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmittingLogin, setIsSubmittingLogin] = useState(false);
  const [workspaceView, setWorkspaceView] = useState<'chat' | 'soil-admin' | 'agent-logs'>('chat');
  const canManageSoilAdmin = authUser?.role === 'admin';
  const canViewAgentLogs = authUser?.role === 'admin' || authUser?.role === 'developer';

  useEffect(() => {
    void initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (!canManageSoilAdmin && workspaceView === 'soil-admin') {
      setWorkspaceView('chat');
    }
  }, [canManageSoilAdmin, workspaceView]);

  useEffect(() => {
    if (!canViewAgentLogs && workspaceView === 'agent-logs') {
      setWorkspaceView('chat');
    }
  }, [canViewAgentLogs, workspaceView]);

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
            {canViewAgentLogs ? (
              <button className="workspace-nav-button" onClick={() => setWorkspaceView(workspaceView === 'agent-logs' ? 'chat' : 'agent-logs')}>
                {workspaceView === 'agent-logs' ? '返回问答' : '查询日志'}
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
        ) : workspaceView === 'agent-logs' ? (
          <AgentLogPage />
        ) : (
          <>
            <ChatPanel
              session={activeSession}
              error={error}
              onRetry={async (message) => retryForMessage(activeSessionId!, message)}
            />
            <Composer isSending={isSending} onSend={sendQuestion} />
          </>
        )}
      </main>
    </div>
  );
}
