import { useState } from 'react';

interface LoginPageProps {
  onSubmit: (username: string, password: string) => Promise<void>;
  isSubmitting: boolean;
  error: string | null;
}

export function LoginPage({ onSubmit, isSubmitting, error }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">AI 农情工作台</div>
        <h1 className="auth-title">账号登录</h1>
        <p className="auth-subtitle">使用数据库账号进入工作台</p>
        <form
          className="auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await onSubmit(username.trim(), password.trim());
          }}
        >
          <label className="auth-field">
            <span>用户名</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label className="auth-field">
            <span>密码</span>
            <div className="auth-password-row">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
              <button
                className="auth-password-toggle"
                type="button"
                onClick={() => setShowPassword((current) => !current)}
              >
                {showPassword ? '隐藏' : '显示'}
              </button>
            </div>
          </label>
          {error ? <div className="auth-error">{error}</div> : null}
          <button
            className="auth-submit"
            type="submit"
            disabled={isSubmitting || !username.trim() || !password.trim()}
          >
            {isSubmitting ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}
