import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface WorkspaceUserMenuProps {
  username: string;
  currentPath: string;
  canManageSoilAdmin: boolean;
  canViewAgentLogs: boolean;
  onLogout: () => void;
}

export function WorkspaceUserMenu({
  username,
  currentPath,
  canManageSoilAdmin,
  canViewAgentLogs,
  onLogout
}: WorkspaceUserMenuProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);

  function navigateTo(targetPath: string) {
    setIsOpen(false);
    if (targetPath !== currentPath) {
      router.push(targetPath);
    }
  }

  function handleLogout() {
    setIsOpen(false);
    onLogout();
  }

  return (
    <div className="workspace-menu-root">
      <button
        type="button"
        className="workspace-menu-trigger"
        onClick={() => setIsOpen((current) => !current)}
        aria-expanded={isOpen}
      >
        {username}
      </button>
      {isOpen ? (
        <div className="workspace-menu-panel">
          <button
            type="button"
            className="workspace-menu-item"
            aria-current={currentPath === '/chat' ? 'page' : undefined}
            onClick={() => navigateTo('/chat')}
          >
            问答工作台
          </button>
          {canManageSoilAdmin ? (
            <button
              type="button"
              className="workspace-menu-item"
              aria-current={currentPath === '/admin' ? 'page' : undefined}
              onClick={() => navigateTo('/admin')}
            >
              墒情管理
            </button>
          ) : null}
          {canViewAgentLogs ? (
            <button
              type="button"
              className="workspace-menu-item"
              aria-current={currentPath === '/query-logs' ? 'page' : undefined}
              onClick={() => navigateTo('/query-logs')}
            >
              查询日志
            </button>
          ) : null}
          <div className="workspace-menu-item workspace-menu-item-meta">用户名：{username}</div>
          <button type="button" className="workspace-menu-item workspace-menu-item-danger" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      ) : null}
    </div>
  );
}
