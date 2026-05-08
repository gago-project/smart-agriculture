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
import { useGagoDevAutoRunner } from './hooks/useGagoDevAutoRunner';
import { useAuthStore } from './store/authStore';

const SHOW_ADMIN_QUERY_EVIDENCE = false;

export default function App() {
  const pathname = usePathname();
  const router = useRouter();
  const authStatus = useAuthStore((state) => state.status);
  const authUser = useAuthStore((state) => state.user);
  const lastLoginAt = useAuthStore((state) => state.lastLoginAt);
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
  const canAccessChatEvidence = authUser?.role === 'admin';
  const showChatEvidence = canAccessChatEvidence && SHOW_ADMIN_QUERY_EVIDENCE;
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
  const gagoDevAutoRun = useGagoDevAutoRunner({
    username: authUser?.username ?? null,
    lastLoginAt,
    enabled: currentView === 'chat',
    createSession,
    sendQuestion,
    switchSession,
  });
  const gagoDevAutoRunBannerText = gagoDevAutoRun.currentLabel
    ? `${gagoDevAutoRun.completedCases}/${gagoDevAutoRun.totalCases} 当前：${gagoDevAutoRun.currentLabel}`
    : gagoDevAutoRun.message ||
      (gagoDevAutoRun.phase === 'running' || gagoDevAutoRun.phase === 'done'
        ? `${gagoDevAutoRun.completedCases}/${gagoDevAutoRun.totalCases}`
        : '准备中');

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
          <div className="workspace-title-group">
            <span className="workspace-kicker">Smart Agriculture Workspace</span>
            <h1 className="workspace-title">苏农云指挥调度智能</h1>
            <p className="workspace-subtitle">面向墒情、预警与处置链路的本地智能工作台</p>
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
          <div className={`chat-workspace ${showChatEvidence ? 'with-query-evidence' : ''}`}>
            <div className="chat-column">
              {gagoDevAutoRun.enabled ? (
                <section
                  aria-label="gago-dev 自动真实问答回归"
                  className={`auto-run-banner auto-run-banner--${gagoDevAutoRun.phase}`}
                >
                  <span>{gagoDevAutoRunBannerText}</span>
                </section>
              ) : null}
              <ChatPanel
                session={activeSession}
                error={error}
                evidenceSelectionEnabled={showChatEvidence}
                selectedAssistantMessageId={showChatEvidence ? selectedAssistantMessageId : null}
                onSelectAssistantMessage={showChatEvidence ? selectAssistantMessage : undefined}
                onRetry={async (message) => retryForMessage(activeSessionId!, message)}
              />
              <Composer isSending={isSending} onSend={sendQuestion} />
            </div>
            {showChatEvidence ? <AdminQueryEvidenceSidebar message={selectedAssistantMessage} /> : null}
          </div>
        )}
      </main>
    </div>
  );
}
