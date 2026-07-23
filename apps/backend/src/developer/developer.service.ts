import { HttpException, Injectable } from '@nestjs/common';

import {
  loadAgentLogRepository,
  loadRealConversationLibrary,
} from '../data/bridge';

/**
 * Wraps agentLogRepository.mjs (agent_query_log) and realConversationLibrary.mjs
 * (markdown case file). Logic untouched; generic errors -> 400 like the web routes.
 */
@Injectable()
export class DeveloperService {
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

  async listQueryLogs(query: Record<string, string>) {
    return this.rethrow(async () => {
      const repo = await loadAgentLogRepository();
      return repo.listAgentQueryLogs(query);
    }, '查询日志加载失败');
  }

  async getQueryLogDetail(queryId: string) {
    return this.rethrow(async () => {
      const repo = await loadAgentLogRepository();
      return repo.getAgentQueryLogDetail(queryId);
    }, '查询日志详情加载失败');
  }

  async listRealConversationCases() {
    return this.rethrow(async () => {
      const lib = await loadRealConversationLibrary();
      const cases = await lib.listRealConversationCases();
      return { total_count: cases.length, cases };
    }, '真实问答库加载失败');
  }
}
