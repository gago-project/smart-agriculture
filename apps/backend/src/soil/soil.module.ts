import { Module } from '@nestjs/common';

import { SoilController } from './soil.controller';
import { SoilService } from './soil.service';

@Module({
  controllers: [SoilController],
  providers: [SoilService],
})
export class SoilModule {}
