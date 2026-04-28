import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, MessageMeta, MessageRole, MessageStatus, Session } from '../types/chat';

interface AddMessageInput {
  role: MessageRole;
  content: string;
  status: MessageStatus;
  meta?: MessageMeta;
}

interface UpdateMessageInput {
  content?: string;
  status?: MessageStatus;
  meta?: MessageMeta;
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  selectedAssistantMessageIds: Record<string, string>;
  createSession: (title?: string) => string;
  switchSession: (sessionId: string) => void;
  renameSession: (sessionId: string, title: string) => void;
  deleteSession: (sessionId: string) => void;
  addMessage: (sessionId: string, input: AddMessageInput) => string;
  updateMessage: (sessionId: string, messageId: string, patch: UpdateMessageInput) => void;
  selectAssistantMessage: (sessionId: string, messageId: string | null) => void;
}

const STORAGE_KEY = 'doc-frontend-chat-v2';

function id() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  if (typeof globalThis.crypto?.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    globalThis.crypto.getRandomValues(bytes);
    const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
  }
  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function withSessionUpdate(sessions: Session[], sessionId: string, fn: (session: Session) => Session): Session[] {
  return sessions.map((session) => {
    if (session.id !== sessionId) return session;
    return fn(session);
  });
}

const initialState = {
  sessions: [] as Session[],
  activeSessionId: null as string | null,
  selectedAssistantMessageIds: {} as Record<string, string>
};

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      ...initialState,
      createSession: (title = '新会话') => {
        const sessionId = id();
        const now = Date.now();
        const session: Session = {
          id: sessionId,
          title,
          createdAt: now,
          updatedAt: now,
          messages: []
        };
        set((state) => ({
          sessions: [...state.sessions, session],
          activeSessionId: sessionId
        }));
        return sessionId;
      },
      switchSession: (sessionId: string) => {
        set({ activeSessionId: sessionId });
      },
      renameSession: (sessionId, title) => {
        const nextTitle = title.trim();
        set((state) => ({
          sessions: withSessionUpdate(state.sessions, sessionId, (session) => ({
            ...session,
            updatedAt: Date.now(),
            title: nextTitle || session.title
          }))
        }));
      },
      deleteSession: (sessionId) => {
        set((state) => {
          const currentIndex = state.sessions.findIndex((session) => session.id === sessionId);
          if (currentIndex < 0) {
            return state;
          }
          const nextSessions = state.sessions.filter((session) => session.id !== sessionId);
          let nextActiveSessionId = state.activeSessionId;
          if (state.activeSessionId === sessionId) {
            const fallbackSession = nextSessions[currentIndex] ?? nextSessions[currentIndex - 1] ?? null;
            nextActiveSessionId = fallbackSession?.id ?? null;
          }
          return {
            sessions: nextSessions,
            activeSessionId: nextActiveSessionId,
            selectedAssistantMessageIds: Object.fromEntries(
              Object.entries(state.selectedAssistantMessageIds).filter(([key]) => key !== sessionId)
            )
          };
        });
      },
      addMessage: (sessionId, input) => {
        const messageId = id();
        const nextMessage: Message = {
          id: messageId,
          role: input.role,
          content: input.content,
          status: input.status,
          createdAt: Date.now(),
          meta: input.meta
        };

        set((state) => ({
          sessions: withSessionUpdate(state.sessions, sessionId, (session) => ({
            ...session,
            updatedAt: Date.now(),
            messages: [...session.messages, nextMessage]
          }))
        }));

        return messageId;
      },
      updateMessage: (sessionId, messageId, patch) => {
        set((state) => ({
          sessions: withSessionUpdate(state.sessions, sessionId, (session) => ({
            ...session,
            updatedAt: Date.now(),
            messages: session.messages.map((message) => {
              if (message.id !== messageId) return message;
              return {
                ...message,
                content: patch.content ?? message.content,
                status: patch.status ?? message.status,
                meta: patch.meta ?? message.meta
              };
            })
          }))
        }));
      },
      selectAssistantMessage: (sessionId, messageId) => {
        set((state) => ({
          selectedAssistantMessageIds: messageId
            ? {
                ...state.selectedAssistantMessageIds,
                [sessionId]: messageId
              }
            : Object.fromEntries(
                Object.entries(state.selectedAssistantMessageIds).filter(([key]) => key !== sessionId)
              )
        }));
      }
    }),
    {
      name: STORAGE_KEY,
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        selectedAssistantMessageIds: state.selectedAssistantMessageIds
      })
    }
  )
);
