import {
  Body,
  Controller,
  Get,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';

import { AuthGuard } from '../common/auth.guard';
import { ChatService } from './chat.service';

/**
 * Mirrors apps/web/app/api/agent/chat/route.ts + chat-block/route.ts.
 * Both require an authenticated user (AuthGuard -> 401 when no/invalid token),
 * matching the web routes' requireRequestUser gate.
 *
 * NOTE ON METHODS: the web chat-block route is a GET with query params and the
 * web client (workspace/services/chatApi.ts) calls it with GET; the switch-style
 * proxy forwards the original method + query string verbatim, so this endpoint
 * is a GET to match 1:1.
 */
@Controller('agent')
@UseGuards(AuthGuard)
export class ChatController {
  constructor(private readonly chat: ChatService) {}

  // POST /agent/chat
  @Post('chat')
  chatTurn(@Body() body: Record<string, unknown>) {
    return this.chat.chat(body || {});
  }

  // GET /agent/chat-block
  @Get('chat-block')
  chatBlock(@Query() q: Record<string, string>) {
    return this.chat.chatBlock({
      snapshotId: q.snapshot_id || '',
      blockType: q.block_type || '',
      page: Number(q.page || '1'),
      pageSize: Number(q.page_size || '10'),
    });
  }
}
