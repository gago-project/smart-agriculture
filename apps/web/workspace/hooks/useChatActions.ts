import { useCallback, useEffect, useMemo, useState } from 'react';
import { sendChat } from '../services/chatApi';
import { useChatStore } from '../store/chatStore';
import type { ChatResponse, Message, Session } from '../types/chat';

const SESSION_TITLE_MAX_LENGTH = 20;

function buildSessionTitle(question: string): string {
  return question.trim().slice(0, SESSION_TITLE_MAX_LENGTH) || '新会话';
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

function isAssistantMessageSelectable(message: Message): boolean {
  return message.role === 'assistant' && message.status === 'done' && Boolean(message.meta?.data?.turn_id);
}

function generateUuid() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }
  return `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildLocalSession(title = '新会话'): Session {
  const now = Date.now();
  return {
    id: generateUuid(),
    title,
    createdAt: now,
    updatedAt: now,
    messages: [],
    lastTurnId: 0,
    currentContext: null,
  };
}

export function useChatActions() {
  const {
    sessions,
    activeSessionId,
    selectedAssistantMessageIds,
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

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions],
  );

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
    const session = buildLocalSession(title || '新会话');
    upsertSession(session);
    switchSession(session.id);
    return session.id;
  }, [switchSession, upsertSession]);

  const deleteSession = useCallback(async (sessionId: string) => {
    deleteSessionFromStore(sessionId);
  }, [deleteSessionFromStore]);

  const renameSession = useCallback(async (sessionId: string, title: string) => {
    const nextTitle = buildSessionTitle(title);
    patchSession(sessionId, {
      title: nextTitle,
      updatedAt: Date.now(),
    });
    return {
      session_id: sessionId,
      title: nextTitle,
    };
  }, [patchSession]);

  const selectAssistantMessage = useCallback((message: Message) => {
    if (!activeSessionId || !isAssistantMessageSelectable(message)) {
      return;
    }
    selectAssistantMessageInStore(activeSessionId, message.id);
  }, [activeSessionId, selectAssistantMessageInStore]);

  const sendQuestion = useCallback(
    async (rawQuestion: string, targetSessionId?: string) => {
      const question = rawQuestion.trim();
      if (!question || isSending) {
        return;
      }

      setIsSending(true);
      setError(null);

      let sessionId = targetSessionId ?? activeSessionId;
      if (!sessionId) {
        sessionId = await createSession(buildSessionTitle(question));
      } else if (targetSessionId) {
        switchSession(targetSessionId);
      }

      const session = useChatStore.getState().sessions.find((item) => item.id === sessionId) ?? null;
      const turnId = session ? session.lastTurnId + 1 : 1;
      const currentContext = session?.currentContext ?? null;
      const clientMessageId = generateUuid();
      const userMessageId = addMessage(sessionId, {
        role: 'user',
        content: question,
        status: 'done',
      });
      const assistantMessageId = addMessage(sessionId, {
        role: 'assistant',
        content: '正在查询中...',
        status: 'streaming',
      });

      try {
        const result = await sendChat(sessionId, turnId, clientMessageId, question, currentContext);
        updateMessage(sessionId, assistantMessageId, {
          content: result.final_text,
          status: 'done',
          meta: responseToAssistantMeta(result, question),
        });
        const latestSession = useChatStore.getState().sessions.find((item) => item.id === sessionId) ?? session;
        patchSession(sessionId, {
          title: latestSession && latestSession.lastTurnId > 0 ? latestSession.title : buildSessionTitle(question),
          updatedAt: Date.now(),
          lastTurnId: result.turn_id,
          currentContext: result.turn_context ?? currentContext,
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
    [
      activeSessionId,
      addMessage,
      createSession,
      isSending,
      patchSession,
      selectAssistantMessageInStore,
      switchSession,
      updateMessage,
    ],
  );

  const retryForMessage = useCallback(
    async (sessionId: string, message: Message) => {
      if (message.role !== 'user') {
        return;
      }
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
    error,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    selectAssistantMessage,
    sendQuestion,
    retryForMessage,
  };
}
