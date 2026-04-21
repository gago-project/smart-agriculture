import { NextResponse } from 'next/server';
import { requireRequestUser } from '../../../../lib/server/auth.mjs';

const SONIOX_TEMP_KEY_URL = 'https://api.soniox.com/v1/auth/temporary-api-key';
const SONIOX_WEBSOCKET_URL = 'wss://stt-rt.soniox.com/transcribe-websocket';
const SONIOX_MODEL = 'stt-rt-preview';

export async function POST(request: Request) {
  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }
  const sonioxApiKey = process.env.SONIOX_API_KEY ?? '';
  const expiresInSeconds = Number(process.env.SONIOX_TEMP_KEY_EXPIRES_IN_SECONDS ?? '300');

  if (!sonioxApiKey) {
    return NextResponse.json({ error: 'SONIOX_API_KEY is not configured' }, { status: 503 });
  }

  try {
    const response = await fetch(SONIOX_TEMP_KEY_URL, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${sonioxApiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ usage_type: 'transcribe_websocket', expires_in_seconds: expiresInSeconds })
    });

    if (!response.ok) {
      const detail = await response.text();
      return NextResponse.json({ error: 'Failed to create Soniox temporary key', detail }, { status: 502 });
    }

    const payload = await response.json();
    return NextResponse.json({
      api_key: payload.api_key,
      expires_at: payload.expires_at,
      websocket_url: SONIOX_WEBSOCKET_URL,
      model: SONIOX_MODEL
    });
  } catch (error) {
    return NextResponse.json({
      error: 'Failed to create Soniox temporary key',
      detail: error instanceof Error ? error.message : 'unknown_error'
    }, { status: 502 });
  }
}
