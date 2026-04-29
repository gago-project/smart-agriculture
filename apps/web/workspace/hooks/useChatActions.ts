import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  archiveChatSession,
  createChatSession,
  fetchChatSession,
  fetchChatSessions,
  sendChat,
} from '../services/chatApi';
import { useChatStore } from '../store/chatStore';
import { useAuthStore } from '../store/authStore';
import type { ChatResponse, ChatSessionDetailResponse, ChatSessionSummary, Message, Session } from '../types/chat';

const SESSION_TITLE_MAX_LENGTH = 20;

function buildSessionTitle(question: string): string {
  return question.trim().slice(0, SESSION_TITLE_MAX_LENGTH) || '新会话';
}

function parseCreatedAt(value?: string, fallback = Date.now()): number {
  if (!value) return fallback;
  const timestamp = Date.parse(value.replace(' ', 'T'));
  return Number.isFinite(timestamp) ? timestamp : fallback;
}

function summaryToSession(summary: ChatSessionSummary): Session {
  return {
    id: summary.session_id,
    title: summary.title || '新会话',
    createdAt: parseCreatedAt(summary.created_at),
    updatedAt: parseCreatedAt(summary.updated_at),
    messages: [],
    hydrated: false,
    lastTurnId: Number(summary.last_turn_id || 0),
  };
}

function responseToAssistantMeta(response: ChatResponse, question: string) {
  return {
    mode: (response.answer_kind || 'unknown') as string,
    data: {
      session_id: response.session_id,
      turn_id: response.turn_id,
      should_query: Boolean(response.query_ref?.has_query),
      answer_kind: response.answer_kind,
      capability: response.capability,
      conversation_closed: Boolean(response.conversation_closed),
    },
    turn: {
      session_id: response.session_id,
      turn_id: response.turn_id,
      answer_kind: response.answer_kind,
      capability: response.capability,
      final_text: response.final_text,
      user_text: question,
      blocks: Array.isArray(response.blocks) ? response.blocks : [],
      primary_block_id: response.topic?.primary_block_id ?? null,
      query_ref: response.query_ref,
    },
  } as const;
}

function turnsToMessages(detail: ChatSessionDetailResponse): Message[] {
  const messages: Message[] = [];
  for (const turn of detail.turns || []) {
    const createdAt = parseCreatedAt(turn.created_at);
    messages.push({
      id: `user:${turn.turn_id}`,
      role: 'user',
      content: turn.user_text || '',
      status: 'done',
      createdAt,
    });
    messages.push({
      id: `assistant:${turn.turn_id}`,
      role: 'assistant',
      content: turn.final_text || '',
      status: 'done',
      createdAt,
      meta: {
        mode: (turn.answer_kind || 'unknown') as string,
        data: {
          session_id: detail.session_id,
          turn_id: turn.turn_id,
          should_query: Boolean(turn.query_ref?.has_query),
          answer_kind: turn.answer_kind,
          capability: turn.capability,
        },
        turn,
      },
    });
  }
  return messages;
}

function detailToSession(detail: ChatSessionDetailResponse): Session {
  return {
    id: detail.session_id,
    title: detail.title || '新会话',
    createdAt: parseCreatedAt(detail.created_at),
    updatedAt: parseCreatedAt(detail.updated_at),
    messages: turnsToMessages(detail),
    hydrated: true,
    lastTurnId: Number(detail.last_turn_id || 0),
  };
}

function isAssistantMessageSelectable(message: Message): boolean {
  return message.role === 'assistant' && message.status === 'done' && Boolean(message.meta?.data?.turn_id);
}

function generateClientMessageId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useChatActions() {
  const authStatus = useAuthStore((state) => state.status);
  const {
    sessions,
    activeSessionId,
    selectedAssistantMessageIds,
    replaceSessions,
    upsertSession,
    patchSession,
    switchSession,
    deleteSession: deleteSessionFromStore,
    addMessage,
    updateMessage,
    selectAssistantMessage: selectAssistantMessageInStore,
  } = useChatStore();
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions],
  );

  useEffect(() => {
    if (authStatus !== 'authenticated') {
      return;
    }
    let cancelled = false;
    setIsLoadingSessions(true);
    void fetchChatSessions()
      .then((payload) => {
        if (cancelled) return;
        replaceSessions((payload.sessions || []).map(summaryToSession));
      })
      .catch((caughtError) => {
        if (cancelled) return;
        setError(caughtError instanceof Error ? caughtError.message : '会话列表加载失败');
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingSessions(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [authStatus, replaceSessions]);

  useEffect(() => {
    if (authStatus !== 'authenticated' || !activeSessionId) {
      return;
    }
    const current = sessions.find((session) => session.id === activeSessionId);
    if (current?.hydrated) {
      return;
    }
    let cancelled = false;
    void fetchChatSession(activeSessionId)
      .then((detail) => {
        if (cancelled) return;
        upsertSession(detailToSession(detail));
      })
      .catch((caughtError) => {
        if (cancelled) return;
        setError(caughtError instanceof Error ? caughtError.message : '会话详情加载失败');
      });
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, authStatus, sessions, upsertSession]);

  const selectedAssistantMessageId = activeSessionId ? (selectedAssistantMessageIds[activeSessionId] ?? null) : null;
  const latestAssistantMessage = useMemo(() => {
    const assistantMessages = activeSession?.messages.filter(isAssistantMessageSelectable) ?? [];
    return assistantMessages.length > 0 ? assistantMessages[assistantMessages.length - 1] : null;
  }, [activeSession]);
  const selectedAssistantMessage = useMemo(() => {
    if (!activeSession) {
      return null;
    }
    if (selectedAssistantMessageId) {
      const matched = activeSession.messages.find((message) => message.id === selectedAssistantMessageId);
      if (matched && isAssistantMessageSelectable(matched)) {
        return matched;
      }
    }
    return latestAssistantMessage;
  }, [activeSession, latestAssistantMessage, selectedAssistantMessageId]);

  useEffect(() => {
    if (!activeSessionId || !latestAssistantMessage) {
      return;
    }
    if (!selectedAssistantMessageId || selectedAssistantMessage?.id !== selectedAssistantMessageId) {
      selectAssistantMessageInStore(activeSessionId, latestAssistantMessage.id);
    }
  }, [
    activeSessionId,
    latestAssistantMessage,
    selectedAssistantMessageId,
    selectAssistantMessageInStore,
    selectedAssistantMessage,
  ]);

  const createSession = useCallback(async (title?: string) => {
    const created = await createChatSession(title || '新会话');
    const session = summaryToSession({
      session_id: created.session_id,
      title: created.title,
      last_turn_id: 0,
    });
    upsertSession(session);
    switchSession(created.session_id);
    return created.session_id;
  }, [switchSession, upsertSession]);

  const deleteSession = useCallback(async (sessionId: string) => {
    await archiveChatSession(sessionId);
    deleteSessionFromStore(sessionId);
  }, [deleteSessionFromStore]);

  const selectAssistantMessage = useCallback((message: Message) => {
    if (!activeSessionId || !isAssistantMessageSelectable(message)) {
      return;
    }
    selectAssistantMessageInStore(activeSessionId, message.id);
  }, [activeSessionId, selectAssistantMessageInStore]);

  const sendQuestion = useCallback(
    async (rawQuestion: string, targetSessionId?: string) => {
      const question = rawQuestion.trim();
      if (!question || isSending) return;

      setIsSending(true);
      setError(null);

      let sessionId = targetSessionId ?? activeSessionId;
      if (!sessionId) {
        sessionId = await createSession(buildSessionTitle(question));
      } else if (targetSessionId) {
        switchSession(targetSessionId);
      }

      const clientMessageId = generateClientMessageId();
      const userMessageId = addMessage(sessionId, { role: 'user', content: question, status: 'done' });
      const assistantMessageId = addMessage(sessionId, {
        role: 'assistant',
        content: '正在查询中...',
        status: 'streaming',
      });

      try {
        const result = await sendChat(sessionId, clientMessageId, question);
        updateMessage(sessionId, assistantMessageId, {
          content: result.final_text,
          status: 'done',
          meta: responseToAssistantMeta(result, question),
        });
        patchSession(sessionId, {
          title: activeSession?.lastTurnId ? activeSession.title : buildSessionTitle(question),
          updatedAt: Date.now(),
          hydrated: true,
          lastTurnId: result.turn_id,
        });
        selectAssistantMessageInStore(sessionId, assistantMessageId);
      } catch (caughtError) {
        const message = caughtError instanceof Error ? caughtError.message : '请求失败，请稍后重试';
        updateMessage(sessionId, assistantMessageId, {
          content: message,
          status: 'error',
        });
        updateMessage(sessionId, userMessageId, {
          content: question,
        });
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [activeSession, activeSessionId, addMessage, createSession, isSending, patchSession, selectAssistantMessageInStore, switchSession, updateMessage],
  );

  const retryForMessage = useCallback(
    async (sessionId: string, message: Message) => {
      if (message.role !== 'user') return;
      await sendQuestion(message.content, sessionId);
    },
    [sendQuestion],
  );

  return {
    sessions,
    activeSessionId,
    activeSession,
    selectedAssistantMessage,
    selectedAssistantMessageId,
    isSending,
    isLoadingSessions,
    error,
    createSession,
    switchSession,
    deleteSession,
    selectAssistantMessage,
    sendQuestion,
    retryForMessage,
  };
}
