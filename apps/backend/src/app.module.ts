import { Module } from '@nestjs/common';

import { CommonModule } from './common/common.module';
import { AuthModule } from './auth/auth.module';
import { SoilModule } from './soil/soil.module';
import { ChatModule } from './chat/chat.module';
import { DeveloperModule } from './developer/developer.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    CommonModule,
    AuthModule,
    SoilModule,
    ChatModule,
    DeveloperModule,
    HealthModule,
  ],
})
export class AppModule {}
