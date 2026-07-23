import {
  Controller,
  ForbiddenException,
  Get,
  Param,
  Query,
  Req,
  UseGuards,
} from '@nestjs/common';

import { AuthGuard, RoleGuard, AuthedRequest } from '../common/auth.guard';
import { DeveloperService } from './developer.service';

const ALLOWED_USERNAME = 'gago-dev';

/**
 * Mirrors apps/web/app/api/developer/*.
 *  - agent/query-logs*  require role in {admin, developer}  (RoleGuard)
 *  - soil/real-conversation-library requires auth + username === 'gago-dev'
 */
@Controller('developer')
export class DeveloperController {
  constructor(private readonly developer: DeveloperService) {}

  // GET /developer/agent/query-logs
  @Get('agent/query-logs')
  @UseGuards(RoleGuard(['admin', 'developer']))
  listQueryLogs(@Query() q: Record<string, string>) {
    return this.developer.listQueryLogs({
      page: q.page || '1',
      page_size: q.page_size || '30',
      keyword: q.keyword || '',
      session_id: q.session_id || '',
      query_type: q.query_type || '',
      intent: q.intent || '',
      status: q.status || '',
      created_at_from: q.created_at_from || '',
      created_at_to: q.created_at_to || '',
    });
  }

  // GET /developer/agent/query-logs/:queryId
  @Get('agent/query-logs/:queryId')
  @UseGuards(RoleGuard(['admin', 'developer']))
  getQueryLogDetail(@Param('queryId') queryId: string) {
    return this.developer.getQueryLogDetail(queryId);
  }

  // GET /developer/soil/real-conversation-library
  @Get('soil/real-conversation-library')
  @UseGuards(AuthGuard)
  listRealConversationCases(@Req() req: AuthedRequest) {
    if (req.authUser?.username !== ALLOWED_USERNAME) {
      throw new ForbiddenException('permission denied');
    }
    return this.developer.listRealConversationCases();
  }
}
