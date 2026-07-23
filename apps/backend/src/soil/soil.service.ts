import { HttpException, Injectable } from '@nestjs/common';

import {
  loadSoilAdminRepository,
  loadSoilImportPreviewService,
  loadSoilImportPreviewCache,
} from '../data/bridge';

/**
 * Wraps the reused soilAdminRepository.mjs / soilImportPreviewService.mjs.
 * Logic/SQL untouched. Error translation mirrors the web routes:
 *  - SoilImportPreviewCacheError -> its own .status (default 400)
 *  - any other Error -> 400 with fallbackMessage
 */
@Injectable()
export class SoilService {
  private async rethrow<T>(
    task: () => Promise<T>,
    fallbackMessage: string,
  ): Promise<T> {
    try {
      return await task();
    } catch (error) {
      const cache = await loadSoilImportPreviewCache();
      if (error instanceof cache.SoilImportPreviewCacheError) {
        throw new HttpException(
          { error: (error as Error).message },
          (error as any).status || 400,
        );
      }
      throw new HttpException(
        { error: error instanceof Error ? error.message : fallbackMessage },
        400,
      );
    }
  }

  async listRecords(query: Record<string, string>) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.listSoilRecords(query);
    }, '墒情记录查询失败');
  }

  async patchRecord(recordId: string, field: string, value: unknown) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.patchSoilRecord(recordId, field, value);
    }, '记录修改失败');
  }

  async deleteRecord(recordId: string) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.removeSoilRecords([recordId]);
    }, '记录删除失败');
  }

  async bulkDelete(ids: unknown[]) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      const safeIds = Array.isArray(ids) ? ids : [];
      return repo.removeSoilRecords(safeIds);
    }, '批量删除失败');
  }

  async listRules() {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.listRuleConfig();
    }, '规则配置查询失败');
  }

  async patchRules(payload: Record<string, unknown>) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.patchRuleConfig(payload);
    }, '规则配置更新失败');
  }

  async upload(payload: {
    filename: string;
    content_base64: string;
    mode: string;
    confirm_full_replace: boolean;
  }) {
    return this.rethrow(async () => {
      const repo = await loadSoilAdminRepository();
      return repo.importSoilWorkbook({
        filename: payload.filename,
        contentBase64: payload.content_base64,
        mode: payload.mode === 'replace' ? 'replace' : 'incremental',
        confirmFullReplace: Boolean(payload.confirm_full_replace),
      });
    }, 'Excel 导入失败');
  }

  async createImportPreview(payload: {
    filename?: string;
    content_base64?: string;
  }) {
    return this.rethrow(async () => {
      const service = await loadSoilImportPreviewService();
      return service.createSoilImportPreview({
        filename: String(payload.filename || 'soil.xlsx'),
        contentBase64: String(payload.content_base64 || ''),
      });
    }, '导入预览创建失败');
  }

  async importPreviewDiff(
    previewToken: string,
    query: { type?: string; page?: string },
  ) {
    return this.rethrow(async () => {
      const service = await loadSoilImportPreviewService();
      return service.listSoilImportPreviewDiffPage(previewToken, {
        type: query.type || 'all',
        page: query.page || '1',
        page_size: '10',
      });
    }, '导入 diff 查询失败');
  }

  async applyImportPreview(
    previewToken: string,
    payload: { mode?: string; confirm_full_replace?: boolean },
  ) {
    return this.rethrow(async () => {
      const service = await loadSoilImportPreviewService();
      return service.applySoilImportPreview({
        previewToken,
        mode: payload.mode === 'replace' ? 'replace' : 'incremental',
        confirmFullReplace: Boolean(payload.confirm_full_replace),
      });
    }, '导入应用失败');
  }
}
