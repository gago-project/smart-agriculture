import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';

import { AdminGuard } from '../common/auth.guard';
import { SoilService } from './soil.service';

/**
 * Mirrors apps/web/app/api/admin/soil/*. All endpoints require admin (AdminGuard).
 * Base path kept as /admin/soil so it 1:1 matches the web route tree.
 */
@Controller('admin/soil')
@UseGuards(AdminGuard)
export class SoilController {
  constructor(private readonly soil: SoilService) {}

  // GET /admin/soil/records
  @Get('records')
  listRecords(@Query() q: Record<string, string>) {
    return this.soil.listRecords({
      page: q.page || '1',
      page_size: q.page_size || '50',
      city: q.city || '',
      county: q.county || '',
      sn: q.sn || '',
      create_time_from: q.create_time_from || '',
      create_time_to: q.create_time_to || '',
    });
  }

  // PATCH /admin/soil/records/:recordId
  @Patch('records/:recordId')
  patchRecord(
    @Param('recordId') recordId: string,
    @Body() body: { field: string; value: unknown },
  ) {
    return this.soil.patchRecord(recordId, body?.field, body?.value);
  }

  // DELETE /admin/soil/records/:recordId
  @Delete('records/:recordId')
  deleteRecord(@Param('recordId') recordId: string) {
    return this.soil.deleteRecord(recordId);
  }

  // POST /admin/soil/records/bulk-delete
  @Post('records/bulk-delete')
  bulkDelete(@Body() body: { ids?: unknown[] }) {
    return this.soil.bulkDelete(Array.isArray(body?.ids) ? body.ids : []);
  }

  // GET /admin/soil/rules
  @Get('rules')
  listRules() {
    return this.soil.listRules();
  }

  // PATCH /admin/soil/rules
  @Patch('rules')
  patchRules(@Body() body: Record<string, unknown>) {
    return this.soil.patchRules(body || {});
  }

  // POST /admin/soil/upload
  @Post('upload')
  upload(
    @Body()
    body: {
      filename: string;
      content_base64: string;
      mode: string;
      confirm_full_replace: boolean;
    },
  ) {
    return this.soil.upload(body);
  }

  // POST /admin/soil/import-preview
  @Post('import-preview')
  createImportPreview(
    @Body() body: { filename?: string; content_base64?: string },
  ) {
    return this.soil.createImportPreview(body || {});
  }

  // GET /admin/soil/import-preview/:previewToken/diff
  @Get('import-preview/:previewToken/diff')
  importPreviewDiff(
    @Param('previewToken') previewToken: string,
    @Query() q: { type?: string; page?: string },
  ) {
    return this.soil.importPreviewDiff(previewToken, q);
  }

  // POST /admin/soil/import-preview/:previewToken/apply
  @Post('import-preview/:previewToken/apply')
  applyImportPreview(
    @Param('previewToken') previewToken: string,
    @Body() body: { mode?: string; confirm_full_replace?: boolean },
  ) {
    return this.soil.applyImportPreview(previewToken, body || {});
  }
}
