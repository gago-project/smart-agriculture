'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { AdminQueryEvidenceSidebar } from './components/AdminQueryEvidenceSidebar';
import { ChatPanel } from './components/ChatPanel';
import { Composer } from './components/Composer';
import { LoginPage } from './components/LoginPage';
import { SessionSidebar } from './components/SessionSidebar';
import { AgentLogPage } from './components/AgentLogPage';
import { SoilAdminPage } from './components/SoilAdminPage';
import { WorkspaceUserMenu } from './components/WorkspaceUserMenu';
import { useChatActions } from './hooks/useChatActions';
import { useAuthStore } from './store/authStore';

export default function App() {
  const pathname = usePathname();
  const router = useRouter();
  const authStatus = useAuthStore((state) => state.status);
  const authUser = useAuthStore((state) => state.user);
  const initAuth = useAuthStore((state) => state.initAuth);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const {
    sessions,
    activeSessionId,
    activeSession,
    error,
    isSending,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    retryForMessage,
    sendQuestion,
    selectedAssistantMessage,
    selectedAssistantMessageId,
    selectAssistantMessage,
  } = useChatActions();
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmittingLogin, setIsSubmittingLogin] = useState(false);
  const canManageSoilAdmin = authUser?.role === 'admin';
  const canViewChatEvidence = authUser?.role === 'admin';
  const canViewAgentLogs = authUser?.role === 'admin' || authUser?.role === 'developer';
  const isRedirectingWorkspaceRoute =
    authStatus === 'authenticated' &&
    Boolean(authUser) &&
    (pathname === '/' ||
      (pathname === '/admin' && !canManageSoilAdmin) ||
      (pathname === '/query-logs' && !canViewAgentLogs));
  const currentView =
    pathname === '/admin' && canManageSoilAdmin
      ? 'soil-admin'
      : pathname === '/query-logs' && canViewAgentLogs
        ? 'agent-logs'
        : 'chat';

  useEffect(() => {
    void initAuth();
  }, [initAuth]);

  useEffect(() => {
    if (authStatus !== 'authenticated' || !authUser) {
      return;
    }

    if (pathname === '/') {
      router.replace('/chat');
      return;
    }

    if (pathname === '/admin' && !canManageSoilAdmin) {
      router.replace('/chat');
      return;
    }

    if (pathname === '/query-logs' && !canViewAgentLogs) {
      router.replace('/chat');
    }
  }, [authStatus, authUser, canManageSoilAdmin, canViewAgentLogs, pathname, router]);

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

  if (isRedirectingWorkspaceRoute) {
    return (
      <div className="auth-shell">
        <div className="auth-card auth-loading">正在跳转工作台...</div>
      </div>
    );
  }

  return (
    <div className="layout">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onCreateSession={createSession}
        onSwitchSession={switchSession}
        onRenameSession={renameSession}
        onDeleteSession={deleteSession}
      />
      <main className="main">
        <header className="workspace-header">
          <div>
            <h1 className="workspace-title">AI 农情工作台</h1>
          </div>
          <WorkspaceUserMenu
            username={authUser.username}
            currentPath={pathname}
            canManageSoilAdmin={canManageSoilAdmin}
            canViewAgentLogs={canViewAgentLogs}
            onLogout={() => void logout()}
          />
        </header>
        {currentView === 'soil-admin' ? (
          <SoilAdminPage />
        ) : currentView === 'agent-logs' ? (
          <AgentLogPage />
        ) : (
          <div className={`chat-workspace ${canViewChatEvidence ? 'with-query-evidence' : ''}`}>
            <div className="chat-column">
              <ChatPanel
                session={activeSession}
                error={error}
                selectedAssistantMessageId={selectedAssistantMessageId}
                onSelectAssistantMessage={selectAssistantMessage}
                onRetry={async (message) => retryForMessage(activeSessionId!, message)}
              />
              <Composer isSending={isSending} onSend={sendQuestion} />
            </div>
            {canViewChatEvidence ? <AdminQueryEvidenceSidebar message={selectedAssistantMessage} /> : null}
          </div>
        )}
      </main>
    </div>
  );
}
