import { HttpException, Injectable } from '@nestjs/common';

import {
  loadAgentChatRuntime,
  loadChatBlockRepository,
} from '../data/bridge';

/**
 * Mirrors apps/web/app/api/agent/chat/route.ts + chat-block/route.ts.
 *
 * chat: runs one agent chat turn (persists/reads session blocks via
 * chatBlockRepository, calls the agent). The agent is reached DIRECTLY at
 * AGENT_BASE_URL (backend .env: http://localhost:18010) — not via a tunnel.
 *
 * chat-block: paginated read of a snapshot's blocks.
 *
 * Reused .mjs logic (SQL / agent call) is untouched; generic errors -> 400
 * like the web routes.
 */
@Injectable()
export class ChatService {
  private agentBaseUrl(): string {
    return process.env.AGENT_BASE_URL || 'http://agent:8000';
  }

  private async rethrow<T>(
    task: () => Promise<T>,
    fallbackMessage: string,
  ): Promise<T> {
    try {
      return await task();
    } catch (error) {
      throw new HttpException(
        { error: error instanceof Error ? error.message : fallbackMessage },
        400,
      );
    }
  }

  /** POST /agent/chat — mirrors web agent/chat route validation + runtime call. */
  async chat(payload: any) {
    const sessionId = String(payload?.session_id || '').trim();
    const turnId = Number(payload?.turn_id || 0);
    const clientMessageId = String(payload?.client_message_id || '').trim();
    const currentContext =
      payload?.current_context &&
      typeof payload.current_context === 'object' &&
      !Array.isArray(payload.current_context)
        ? payload.current_context
        : null;
    const message = String(payload?.message || '').trim();
    const timezone =
      String(payload?.timezone || 'Asia/Shanghai').trim() || 'Asia/Shanghai';

    if (!sessionId) {
      throw new HttpException({ error: 'session_id is required' }, 400);
    }
    if (!Number.isInteger(turnId) || turnId <= 0) {
      throw new HttpException({ error: 'turn_id is required' }, 400);
    }
    if (!clientMessageId) {
      throw new HttpException({ error: 'client_message_id is required' }, 400);
    }
    if (!message) {
      throw new HttpException({ error: 'message is required' }, 400);
    }

    return this.rethrow(async () => {
      const runtime = await loadAgentChatRuntime();
      return runtime.runAgentChatTurn({
        sessionId,
        turnId,
        clientMessageId,
        currentContext,
        message,
        timezone,
        agentBaseUrl: this.agentBaseUrl(),
      });
    }, 'chat request failed');
  }

  /** POST /agent/chat-block — mirrors web chat-block route (paginated snapshot blocks). */
  async chatBlock(query: {
    snapshotId: string;
    blockType: string;
    page: number;
    pageSize: number;
  }) {
    return this.rethrow(async () => {
      const repo = await loadChatBlockRepository();
      return repo.getChatBlockPageBySnapshot({
        snapshotId: query.snapshotId,
        blockType: query.blockType,
        page: query.page,
        pageSize: query.pageSize,
      });
    }, '区块数据加载失败');
  }
}
