import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import { fetchCurrentUser, login as loginRequest, logout as logoutRequest, type AuthUser } from '../services/authApi';

export type AuthStatus = 'idle' | 'checking' | 'authenticated' | 'anonymous';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  status: AuthStatus;
  initAuth: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearSession: () => void;
}

const STORAGE_KEY = 'doc-frontend-auth-v1';

const initialState = {
  token: null as string | null,
  user: null as AuthUser | null,
  status: 'idle' as AuthStatus
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,
      initAuth: async () => {
        const { token, user } = get();
        if (!token) {
          set({ token: null, user: null, status: 'anonymous' });
          return;
        }
        if (user) {
          set({ status: 'authenticated' });
          return;
        }
        set({ status: 'checking' });
        try {
          const currentUser = await fetchCurrentUser(token);
          set({ user: currentUser, status: 'authenticated' });
        } catch {
          set({ token: null, user: null, status: 'anonymous' });
        }
      },
      login: async (username, password) => {
        set({ status: 'checking' });
        try {
          const session = await loginRequest(username.trim(), password.trim());
          set({
            token: session.token,
            user: session.user,
            status: 'authenticated'
          });
        } catch (error) {
          set({ token: null, user: null, status: 'anonymous' });
          throw error;
        }
      },
      logout: async () => {
        const { token } = get();
        try {
          if (token) {
            await logoutRequest(token);
          }
        } finally {
          set({ token: null, user: null, status: 'anonymous' });
        }
      },
      clearSession: () => {
        set({ token: null, user: null, status: 'anonymous' });
      }
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        token: state.token
      })
    }
  )
);
