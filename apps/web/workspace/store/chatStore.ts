import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ChatMessageData, Message, MessageMeta, Session } from '../types/chat';

interface SessionPatch {
  title?: string;
  createdAt?: number;
  updatedAt?: number;
  hydrated?: boolean;
  lastTurnId?: number;
  messages?: Message[];
}

interface AddMessageInput {
  role: Message['role'];
  content: string;
  status: Message['status'];
  meta?: MessageMeta;
}

interface UpdateMessageInput {
  content?: string;
  status?: Message['status'];
  meta?: MessageMeta;
}

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  selectedAssistantMessageIds: Record<string, string>;
  replaceSessions: (sessions: Session[]) => void;
  upsertSession: (session: Session) => void;
  patchSession: (sessionId: string, patch: SessionPatch) => void;
  switchSession: (sessionId: string | null) => void;
  deleteSession: (sessionId: string) => void;
  addMessage: (sessionId: string, input: AddMessageInput) => string;
  updateMessage: (sessionId: string, messageId: string, patch: UpdateMessageInput) => void;
  selectAssistantMessage: (sessionId: string, messageId: string | null) => void;
}

const STORAGE_KEY = 'doc-frontend-chat-v3';
const STORAGE_VERSION = 2;

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

function compactMessageData(data?: ChatMessageData | null): ChatMessageData | null {
  if (!data || typeof data !== 'object') {
    return null;
  }

  const next: ChatMessageData = {};
  if (typeof data.session_id === 'string' && data.session_id.trim()) {
    next.session_id = data.session_id.trim();
  }
  if (typeof data.turn_id === 'number' && Number.isInteger(data.turn_id) && data.turn_id > 0) {
    next.turn_id = data.turn_id;
  }
  if (typeof data.should_query === 'boolean') {
    next.should_query = data.should_query;
  }
  if (typeof data.answer_kind === 'string' && data.answer_kind.trim()) {
    next.answer_kind = data.answer_kind.trim();
  }
  if (typeof data.capability === 'string' && data.capability.trim()) {
    next.capability = data.capability.trim();
  }
  if (typeof data.conversation_closed === 'boolean') {
    next.conversation_closed = data.conversation_closed;
  }

  return Object.keys(next).length > 0 ? next : null;
}

function compactMessageMeta(meta?: MessageMeta): MessageMeta | undefined {
  if (!meta || typeof meta !== 'object') {
    return undefined;
  }

  const next: MessageMeta = {};
  if (typeof meta.mode === 'string' && meta.mode.trim()) {
    next.mode = meta.mode.trim();
  }

  const compactData = compactMessageData(meta.data ?? null);
  if (compactData) {
    next.data = compactData;
  }

  return Object.keys(next).length > 0 ? next : undefined;
}

function compactSelectedAssistantMessageIds(value: unknown): Record<string, string> {
  if (!value || typeof value !== 'object') {
    return {};
  }

  return Object.fromEntries(
    Object.entries(value)
      .filter(([sessionId, messageId]) => Boolean(sessionId) && typeof messageId === 'string' && messageId.trim())
      .map(([sessionId, messageId]) => [sessionId, messageId.trim()]),
  );
}

function compactPersistedSessions(sessions: Session[]): Session[] {
  return Array.isArray(sessions)
    ? sessions.map((session) => ({
        ...ensureSessionShape(session),
        messages: (session.messages || []).map((message) => ({
          ...message,
          meta: compactMessageMeta(message.meta),
        })),
      }))
    : [];
}

function sortSessions(sessions: Session[]): Session[] {
  return [...sessions].sort((left, right) => right.updatedAt - left.updatedAt);
}

function ensureSessionShape(session: Session): Session {
  return {
    id: String(session.id || ''),
    title: String(session.title || '新会话'),
    createdAt: Number(session.createdAt || Date.now()),
    updatedAt: Number(session.updatedAt || Date.now()),
    messages: Array.isArray(session.messages) ? session.messages : [],
    hydrated: Boolean(session.hydrated),
    lastTurnId: Number(session.lastTurnId || 0),
  };
}

function withSessionUpdate(sessions: Session[], sessionId: string, updater: (session: Session) => Session): Session[] {
  let found = false;
  const nextSessions = sessions.map((session) => {
    if (session.id !== sessionId) {
      return session;
    }
    found = true;
    return updater(session);
  });
  return found ? nextSessions : sessions;
}

const initialState = {
  sessions: [] as Session[],
  activeSessionId: null as string | null,
  selectedAssistantMessageIds: {} as Record<string, string>,
};

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      ...initialState,
      replaceSessions: (sessions) => {
        set((state) => {
          const existingById = new Map(state.sessions.map((session) => [session.id, session]));
          const nextSessions = sessions.map((session) => {
            const normalized = ensureSessionShape(session);
            const existing = existingById.get(normalized.id);
            return existing
              ? {
                  ...normalized,
                  messages: normalized.messages.length > 0 ? normalized.messages : existing.messages,
                  hydrated: normalized.hydrated || existing.hydrated,
                  lastTurnId: Math.max(normalized.lastTurnId, existing.lastTurnId),
                }
              : normalized;
          });
          return {
            sessions: sortSessions(nextSessions),
            activeSessionId:
              state.activeSessionId && nextSessions.some((session) => session.id === state.activeSessionId)
                ? state.activeSessionId
                : nextSessions[0]?.id ?? null,
          };
        });
      },
      upsertSession: (session) => {
        const normalized = ensureSessionShape(session);
        set((state) => {
          const existing = state.sessions.find((item) => item.id === normalized.id);
          const nextSessions = existing
            ? withSessionUpdate(state.sessions, normalized.id, () => ({
                ...normalized,
                messages: normalized.messages.length > 0 ? normalized.messages : existing.messages,
                hydrated: normalized.hydrated || existing.hydrated,
                lastTurnId: Math.max(normalized.lastTurnId, existing.lastTurnId),
              }))
            : [...state.sessions, normalized];
          return {
            sessions: sortSessions(nextSessions),
            activeSessionId: state.activeSessionId ?? normalized.id,
          };
        });
      },
      patchSession: (sessionId, patch) => {
        set((state) => ({
          sessions: sortSessions(
            withSessionUpdate(state.sessions, sessionId, (session) => ({
              ...session,
              ...patch,
              updatedAt: patch.updatedAt ?? session.updatedAt,
              messages: patch.messages ?? session.messages,
              hydrated: patch.hydrated ?? session.hydrated,
              lastTurnId: patch.lastTurnId ?? session.lastTurnId,
            })),
          ),
        }));
      },
      switchSession: (sessionId) => {
        set({ activeSessionId: sessionId });
      },
      deleteSession: (sessionId) => {
        set((state) => {
          const nextSessions = state.sessions.filter((session) => session.id !== sessionId);
          return {
            sessions: nextSessions,
            activeSessionId:
              state.activeSessionId === sessionId ? nextSessions[0]?.id ?? null : state.activeSessionId,
            selectedAssistantMessageIds: Object.fromEntries(
              Object.entries(state.selectedAssistantMessageIds).filter(([key]) => key !== sessionId),
            ),
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
          meta: input.meta,
        };

        set((state) => ({
          sessions: sortSessions(
            withSessionUpdate(state.sessions, sessionId, (session) => ({
              ...session,
              updatedAt: Date.now(),
              messages: [...session.messages, nextMessage],
            })),
          ),
        }));

        return messageId;
      },
      updateMessage: (sessionId, messageId, patch) => {
        set((state) => ({
          sessions: sortSessions(
            withSessionUpdate(state.sessions, sessionId, (session) => ({
              ...session,
              updatedAt: Date.now(),
              messages: session.messages.map((message) => {
                if (message.id !== messageId) return message;
                return {
                  ...message,
                  content: patch.content ?? message.content,
                  status: patch.status ?? message.status,
                  meta: patch.meta ?? message.meta,
                };
              }),
            })),
          ),
        }));
      },
      selectAssistantMessage: (sessionId, messageId) => {
        set((state) => ({
          selectedAssistantMessageIds: messageId
            ? {
                ...state.selectedAssistantMessageIds,
                [sessionId]: messageId,
              }
            : Object.fromEntries(
                Object.entries(state.selectedAssistantMessageIds).filter(([key]) => key !== sessionId),
              ),
        }));
      },
    }),
    {
      name: STORAGE_KEY,
      version: STORAGE_VERSION,
      migrate: (persistedState) => {
        const state = persistedState as Partial<ChatState> | undefined;
        return {
          ...initialState,
          activeSessionId: typeof state?.activeSessionId === 'string' ? state.activeSessionId : null,
          selectedAssistantMessageIds: compactSelectedAssistantMessageIds(state?.selectedAssistantMessageIds),
        };
      },
      partialize: (state) => ({
        activeSessionId: state.activeSessionId,
        selectedAssistantMessageIds: compactSelectedAssistantMessageIds(state.selectedAssistantMessageIds),
      }),
    },
  ),
);
