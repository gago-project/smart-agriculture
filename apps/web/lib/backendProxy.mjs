import { NextResponse } from 'next/server';

/**
 * Switch-style backend proxy (Phase 1 前后端分离).
 *
 * When `process.env.BACKEND_BASE_URL` is set, route handlers call
 * `proxyToBackend(request, backendPath)` at the TOP of the handler to forward
 * the request to the local NestJS backend instead of hitting MySQL directly.
 * When the env var is unset, callers never invoke this and behaviour is
 * byte-for-byte identical to before (pure fallback / rollback).
 *
 * Auth model note: this web app uses NO cookies. The client stores the session
 * token in localStorage and sends it as `Authorization: Bearer <token>` on every
 * authenticated request. So proxying auth is simply forwarding that incoming
 * Authorization header to the backend — there is no cookie to read or translate.
 */

const DEFAULT_TIMEOUT_MS = 20_000;

/** Methods that never carry a request body. */
const BODYLESS_METHODS = new Set(['GET', 'HEAD', 'DELETE']);

function backendBaseUrl() {
  const raw = process.env.BACKEND_BASE_URL || '';
  // Trim a single trailing slash so `base + '/auth/login'` never doubles up.
  return raw.replace(/\/+$/, '');
}

/**
 * Whether proxy mode is active. Handlers use this for their early-return gate.
 */
export function isBackendProxyEnabled() {
  return Boolean(process.env.BACKEND_BASE_URL);
}

/**
 * Build the request headers to send to the backend:
 *  - forward Authorization (Bearer token) as-is — this is the whole auth story
 *  - forward Content-Type / Accept when present
 *  - forward Origin + X-Forwarded-Host + client IP for the backend's context
 * We deliberately do NOT forward hop-by-hop headers (host, connection, etc.).
 */
function buildForwardHeaders(request, extraHeaders) {
  const headers = new Headers();

  const passthrough = ['authorization', 'content-type', 'accept', 'accept-language'];
  for (const name of passthrough) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  // Origin (fall back to nothing rather than inventing one).
  const origin = request.headers.get('origin');
  if (origin) headers.set('origin', origin);

  // Original host for the backend to reconstruct absolute URLs / logging.
  const forwardedHost =
    request.headers.get('x-forwarded-host') || request.headers.get('host');
  if (forwardedHost) headers.set('x-forwarded-host', forwardedHost);

  const forwardedProto = request.headers.get('x-forwarded-proto');
  if (forwardedProto) headers.set('x-forwarded-proto', forwardedProto);

  // Client IP chain.
  const priorFor = request.headers.get('x-forwarded-for');
  const clientIp =
    request.headers.get('x-real-ip') ||
    (priorFor ? priorFor.split(',')[0].trim() : '');
  if (priorFor) {
    headers.set('x-forwarded-for', priorFor);
  } else if (clientIp) {
    headers.set('x-forwarded-for', clientIp);
  }
  if (clientIp) headers.set('x-real-ip', clientIp);

  if (extraHeaders) {
    for (const [k, v] of Object.entries(extraHeaders)) {
      if (v != null) headers.set(k, String(v));
    }
  }

  return headers;
}

/**
 * Forward a Next.js request to the backend and return the backend's response
 * (status + body) as a NextResponse, preserving 401/403/400/etc.
 *
 * @param {import('next/server').NextRequest} request
 * @param {string} backendPath  backend path WITHOUT the leading /api, e.g. 'admin/soil/records' or '/auth/login'
 * @param {object} [opts]
 * @param {string} [opts.method]  override method (defaults to request.method)
 * @param {BodyInit|null} [opts.body]  override body (e.g. a re-serialized JSON body)
 * @param {Record<string,string>} [opts.headers]  extra headers to add/override
 * @param {number} [opts.timeoutMs]
 */
export async function proxyToBackend(request, backendPath, opts = {}) {
  const base = backendBaseUrl();
  if (!base) {
    // Should never happen (handlers gate on isBackendProxyEnabled) but be safe.
    return NextResponse.json({ error: 'backend not configured' }, { status: 502 });
  }

  const method = (opts.method || request.method || 'GET').toUpperCase();
  const path = backendPath.startsWith('/') ? backendPath : `/${backendPath}`;
  // Preserve the original query string.
  const search = request.nextUrl ? request.nextUrl.search : '';
  const targetUrl = `${base}${path}${search || ''}`;

  const headers = buildForwardHeaders(request, opts.headers);

  let body;
  if (BODYLESS_METHODS.has(method)) {
    body = undefined;
  } else if (Object.prototype.hasOwnProperty.call(opts, 'body')) {
    body = opts.body;
  } else {
    // Stream the original request body through. This transparently handles
    // JSON, text, and (if it ever appears) multipart uploads without buffering.
    // The original content-type header was already forwarded above.
    const raw = await request.arrayBuffer();
    body = raw.byteLength > 0 ? raw : undefined;
  }

  const controller = new AbortController();
  const timeoutMs = opts.timeoutMs || DEFAULT_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let backendResponse;
  try {
    backendResponse = await fetch(targetUrl, {
      method,
      headers,
      body,
      // Node fetch requires duplex for streaming request bodies; arrayBuffer
      // bodies don't, but set it defensively for any BodyInit.
      ...(body != null ? { duplex: 'half' } : {}),
      redirect: 'manual',
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timer);
    const aborted = error && error.name === 'AbortError';
    return NextResponse.json(
      { error: aborted ? 'backend request timed out' : 'backend unavailable' },
      { status: 502 },
    );
  }
  clearTimeout(timer);

  const contentType = backendResponse.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');

  // For JSON errors, normalize NestJS's default exception shape
  // ({ statusCode, message, error }) into the web contract's { error: <msg> }
  // so the client's extractError (reads payload.error) sees the same human
  // string it did before (e.g. "authentication required", "admin required").
  // Successful bodies and service-level { error } bodies pass through unchanged.
  if (isJson && !backendResponse.ok) {
    const text = await backendResponse.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
    if (data && typeof data === 'object' && !('error' in data) && 'message' in data) {
      const message = Array.isArray(data.message) ? data.message.join('; ') : data.message;
      return NextResponse.json({ error: String(message) }, { status: backendResponse.status });
    }
    return new NextResponse(text, {
      status: backendResponse.status,
      headers: { 'content-type': contentType },
    });
  }

  // Return status + body verbatim. Copy a safe subset of response headers.
  const responseBody = await backendResponse.arrayBuffer();
  const outHeaders = new Headers();
  if (contentType) outHeaders.set('content-type', contentType);
  const contentDisposition = backendResponse.headers.get('content-disposition');
  if (contentDisposition) outHeaders.set('content-disposition', contentDisposition);

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: outHeaders,
  });
}

/**
 * Read the backend response as JSON, tolerating empty/non-JSON bodies.
 * Returns { ok, status, data }. Used by the auth routes that need to
 * reshape the payload (e.g. map expiresAt -> expires_at).
 */
export async function fetchBackendJson(request, backendPath, opts = {}) {
  const base = backendBaseUrl();
  if (!base) {
    return { ok: false, status: 502, data: { error: 'backend not configured' } };
  }

  const method = (opts.method || request.method || 'GET').toUpperCase();
  const path = backendPath.startsWith('/') ? backendPath : `/${backendPath}`;
  const search = request.nextUrl ? request.nextUrl.search : '';
  const targetUrl = `${base}${path}${search || ''}`;

  const headers = buildForwardHeaders(request, opts.headers);

  let body;
  if (BODYLESS_METHODS.has(method)) {
    body = undefined;
  } else if (Object.prototype.hasOwnProperty.call(opts, 'body')) {
    body = opts.body;
    if (body != null && !headers.has('content-type')) {
      headers.set('content-type', 'application/json');
    }
  } else {
    const raw = await request.arrayBuffer();
    body = raw.byteLength > 0 ? raw : undefined;
  }

  const controller = new AbortController();
  const timeoutMs = opts.timeoutMs || DEFAULT_TIMEOUT_MS;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(targetUrl, {
      method,
      headers,
      body,
      ...(body != null ? { duplex: 'half' } : {}),
      redirect: 'manual',
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timer);
    const aborted = error && error.name === 'AbortError';
    return {
      ok: false,
      status: 502,
      data: { error: aborted ? 'backend request timed out' : 'backend unavailable' },
    };
  }
  clearTimeout(timer);

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }

  return { ok: response.ok, status: response.status, data };
}
