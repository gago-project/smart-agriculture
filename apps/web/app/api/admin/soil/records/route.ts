import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { listSoilRecords } from '../../../../../lib/server/soilAdminRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const searchParams = request.nextUrl.searchParams;
    const result = await listSoilRecords({
      page: searchParams.get('page') || '1',
      page_size: searchParams.get('page_size') || '50',
      city_name: searchParams.get('city_name') || '',
      county_name: searchParams.get('county_name') || '',
      device_sn: searchParams.get('device_sn') || '',
      soil_anomaly_type: searchParams.get('soil_anomaly_type') || '',
      sample_time_from: searchParams.get('sample_time_from') || '',
      sample_time_to: searchParams.get('sample_time_to') || '',
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '墒情记录查询失败' }, { status: 400 });
  }
}
