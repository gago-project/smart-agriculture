import { useEffect, useRef, useState } from 'react';

import { fetchRealConversationLibrary, type RealConversationCase } from '../services/realConversationApi';
import { clearChatLocalState } from '../store/chatStore';

const GAGO_DEV_USERNAME = 'gago-dev';
const SESSION_TITLE_MAX_LENGTH = 36;

type AutoRunPhase = 'idle' | 'preparing' | 'running' | 'done' | 'error';

export interface GagoDevAutoRunStatus {
  enabled: boolean;
  phase: AutoRunPhase;
  totalCases: number;
  completedCases: number;
  currentLabel: string | null;
  message: string | null;
}

interface UseGagoDevAutoRunnerOptions {
  username?: string | null;
  lastLoginAt: number | null;
  enabled: boolean;
  createSession: (title?: string, options?: { activate?: boolean }) => Promise<string>;
  sendQuestion: (
    question: string,
    targetSessionId?: string,
    options?: { focusSession?: boolean; propagateError?: boolean },
  ) => Promise<void>;
  switchSession: (sessionId: string | null) => void;
}

function buildSingleTurnSessionTitle(total: number) {
  return `真实问答自动回归（单轮 ${total} 条）`;
}

function buildMultiTurnSessionTitle(testCase: RealConversationCase) {
  const compactQuestion = testCase.question.trim().slice(0, SESSION_TITLE_MAX_LENGTH);
  return `真实问答自动回归 #${String(testCase.id).padStart(3, '0')} ${compactQuestion}`;
}

function buildCurrentLabel(testCase: RealConversationCase, turnIndex: number) {
  const currentTurn = testCase.turns[turnIndex] ?? testCase.question;
  if (testCase.turns.length <= 1) {
    return `#${testCase.id} ${currentTurn}`;
  }
  return `#${testCase.id} 第 ${turnIndex + 1}/${testCase.turns.length} 轮：${currentTurn}`;
}

export function useGagoDevAutoRunner({
  username,
  lastLoginAt,
  enabled,
  createSession,
  sendQuestion,
  switchSession,
}: UseGagoDevAutoRunnerOptions): GagoDevAutoRunStatus {
  const [status, setStatus] = useState<GagoDevAutoRunStatus>({
    enabled: false,
    phase: 'idle',
    totalCases: 0,
    completedCases: 0,
    currentLabel: null,
    message: null,
  });
  const lastRunMarkerRef = useRef<number | null>(null);
  const createSessionRef = useRef(createSession);
  const sendQuestionRef = useRef(sendQuestion);
  const switchSessionRef = useRef(switchSession);
  const isEnabled = enabled && username === GAGO_DEV_USERNAME;

  useEffect(() => {
    createSessionRef.current = createSession;
  }, [createSession]);

  useEffect(() => {
    sendQuestionRef.current = sendQuestion;
  }, [sendQuestion]);

  useEffect(() => {
    switchSessionRef.current = switchSession;
  }, [switchSession]);

  useEffect(() => {
    if (!isEnabled || !lastLoginAt) {
      return;
    }
    if (lastRunMarkerRef.current === lastLoginAt) {
      return;
    }

    lastRunMarkerRef.current = lastLoginAt;
    let cancelled = false;
    let totalCases = 0;
    let completedCases = 0;
    let currentLabel: string | null = null;

    void (async () => {
      setStatus({
        enabled: true,
        phase: 'preparing',
        totalCases: 0,
        completedCases: 0,
        currentLabel: null,
        message: '正在清理本地聊天状态，并准备自动回归真实问答库...',
      });

      clearChatLocalState();

      const library = await fetchRealConversationLibrary();
      if (cancelled) {
        return;
      }
      totalCases = library.totalCount;

      const singleTurnCases = library.cases.filter((testCase) => testCase.turns.length === 1);
      let singleTurnSessionId: string | null = null;
      if (singleTurnCases.length > 0) {
        singleTurnSessionId = await createSessionRef.current(buildSingleTurnSessionTitle(singleTurnCases.length), { activate: true });
      }

      setStatus({
        enabled: true,
        phase: 'running',
        totalCases,
        completedCases,
        currentLabel: null,
        message: `已加载 ${totalCases} 条真实问答，正在按顺序逐条发问并展示回答...`,
      });

      for (const testCase of library.cases) {
        if (cancelled) {
          return;
        }

        const turns = testCase.turns.length > 0 ? testCase.turns : [testCase.question];
        const sessionId =
          turns.length === 1
            ? singleTurnSessionId
            : await createSessionRef.current(buildMultiTurnSessionTitle(testCase), { activate: false });

        if (!sessionId) {
          continue;
        }

        switchSessionRef.current(sessionId);

        for (let turnIndex = 0; turnIndex < turns.length; turnIndex += 1) {
          if (cancelled) {
            return;
          }

          currentLabel = buildCurrentLabel(testCase, turnIndex);
          setStatus({
            enabled: true,
            phase: 'running',
            totalCases,
            completedCases,
            currentLabel,
            message:
              turns.length === 1
                ? '单轮真实问答会在当前会话里逐条展示，便于直接观察上下文和回答效果。'
                : '多轮真实问答会单独使用一个会话，并切到当前会话逐轮展示。',
          });

          await sendQuestionRef.current(turns[turnIndex], sessionId, {
            focusSession: true,
            propagateError: true,
          });
        }

        completedCases += 1;
        setStatus({
          enabled: true,
          phase: 'running',
          totalCases,
          completedCases,
          currentLabel: turns[turns.length - 1] ?? testCase.question,
          message: `已完成 ${completedCases}/${totalCases} 条真实问答。`,
        });
      }

      setStatus({
        enabled: true,
        phase: 'done',
        totalCases,
        completedCases,
        currentLabel: null,
        message: `自动回归已完成，共执行 ${completedCases} 条真实问答。`,
      });
    })().catch((error) => {
      if (cancelled) {
        return;
      }
      setStatus({
        enabled: true,
        phase: 'error',
        totalCases,
        completedCases,
        currentLabel,
        message: error instanceof Error ? error.message : '真实问答自动回归失败',
      });
    });

    return () => {
      cancelled = true;
    };
  }, [isEnabled, lastLoginAt]);

  return isEnabled
    ? status
    : {
        enabled: false,
        phase: 'idle',
        totalCases: 0,
        completedCases: 0,
        currentLabel: null,
        message: null,
      };
}
