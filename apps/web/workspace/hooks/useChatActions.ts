import { useCallback, useMemo, useState } from 'react';
import { sendChat } from '../services/chatApi';
import { simulateStream } from '../services/streamWriter';
import { useChatStore } from '../store/chatStore';
import type { ChatHistoryTurn, Message } from '../types/chat';

const SESSION_TITLE_MAX_LENGTH = 20;

function buildSessionTitle(question: string): string {
  return question.trim().slice(0, SESSION_TITLE_MAX_LENGTH) || '新会话';
}

function toHistory(messages: Message[]): ChatHistoryTurn[] {
  return messages
    .filter((message) => message.status !== 'error' && Boolean(message.content.trim()))
    .map((message) => ({
      role: message.role,
      content: message.content.trim()
    }));
}

export function useChatActions() {
  const { sessions, activeSessionId, createSession, addMessage, updateMessage, switchSession } = useChatStore();
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions]
  );

  const latestEvidenceMessage = useMemo(() => {
    const assistantMessages = activeSession?.messages.filter((message) => message.role === 'assistant' && message.meta) ?? [];
    return assistantMessages.length > 0 ? assistantMessages[assistantMessages.length - 1] : null;
  }, [activeSession]);

  const sendQuestion = useCallback(
    async (rawQuestion: string, targetSessionId?: string, historyOverride?: ChatHistoryTurn[]) => {
      const question = rawQuestion.trim();
      if (!question || isSending) return;

      setIsSending(true);
      setError(null);

      const currentState = useChatStore.getState();
      const sessionId = targetSessionId ?? currentState.activeSessionId ?? createSession(buildSessionTitle(question));
      const existingMessages = useChatStore.getState().sessions.find((session) => session.id === sessionId)?.messages ?? [];
      const history = historyOverride ?? toHistory(existingMessages);
      if (targetSessionId) {
        switchSession(targetSessionId);
      }

      addMessage(sessionId, { role: 'user', content: question, status: 'done' });
      const assistantMessageId = addMessage(sessionId, {
        role: 'assistant',
        content: '',
        status: 'streaming'
      });

      try {
        const result = await sendChat(question, history, sessionId);
        let composed = '';

        await new Promise<void>((resolve) => {
          simulateStream(result.answer, {
            chunkSize: 10,
            intervalMs: 16,
            onChunk: (chunk) => {
              composed += chunk;
              updateMessage(sessionId, assistantMessageId, {
                content: composed,
                status: 'streaming'
              });
            },
            onDone: () => resolve()
          });
        });

        updateMessage(sessionId, assistantMessageId, {
          content: result.answer,
          status: 'done',
          meta: {
            mode: result.mode,
            data: result.data,
            evidence: result.evidence,
            processing: result.processing ?? null
          }
        });
      } catch (caughtError) {
        const message = caughtError instanceof Error ? caughtError.message : '请求失败，请稍后重试';
        updateMessage(sessionId, assistantMessageId, {
          content: message,
          status: 'error'
        });
        setError(message);
      } finally {
        setIsSending(false);
      }
    },
    [addMessage, createSession, isSending, switchSession, updateMessage]
  );

  const retryForMessage = useCallback(
    async (sessionId: string, message: Message) => {
      if (message.role !== 'user') return;
      const session = sessions.find((item) => item.id === sessionId);
      const cutoff = session?.messages.findIndex((item) => item.id === message.id) ?? -1;
      const history = cutoff >= 0 ? toHistory((session?.messages ?? []).slice(0, cutoff)) : [];
      await sendQuestion(message.content, sessionId, history);
    },
    [sendQuestion, sessions]
  );

  return {
    isSending,
    error,
    activeSession,
    latestEvidenceMessage,
    sendQuestion,
    retryForMessage
  };
}
