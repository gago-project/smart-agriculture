import { Global, Module } from '@nestjs/common';

import { AuthService } from './auth.service';
import { AuthGuard, AdminGuard } from './auth.guard';

@Global()
@Module({
  providers: [AuthService, AuthGuard, AdminGuard],
  exports: [AuthService, AuthGuard, AdminGuard],
})
export class CommonModule {}
