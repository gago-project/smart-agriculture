/**
 * Bridge between NestJS (CommonJS/TS) and the reused ESM `.mjs` data layer copied
 * verbatim from apps/web/lib/server. CommonJS can only load ESM via a *real* dynamic
 * import(). TypeScript with module:"commonjs" would down-level `import()` to
 * `require()`, which cannot load ESM — so we build the dynamic import via `new Function`
 * to keep a native `import()` that Node executes at runtime.
 *
 * The .mjs files are emitted next to the compiled JS (dist/data/*.mjs) via the
 * nest-cli.json "assets" rule, so the resolved absolute path is valid in the built app.
 *
 * NOTHING in the .mjs files is modified — SQL / scrypt / session logic is untouched.
 */
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';

// Native dynamic import that survives commonjs down-levelling.
const nativeImport: (specifier: string) => Promise<any> = new Function(
  'specifier',
  'return import(specifier)',
) as any;

function importMjs(fileName: string): Promise<any> {
  // __dirname === dist/data (built) or src/data (ts-node); the .mjs sits alongside.
  const url = pathToFileURL(join(__dirname, fileName)).href;
  return nativeImport(url);
}

// Auth (auth.mjs -> authCore.mjs -> authRepository.mjs -> mysql.mjs)
export function loadAuth() {
  return importMjs('auth.mjs');
}

export function loadAuthCore() {
  return importMjs('authCore.mjs');
}

// Soil admin repository (records / rules / import)
export function loadSoilAdminRepository() {
  return importMjs('soilAdminRepository.mjs');
}

// Soil import preview service + its cache error type
export function loadSoilImportPreviewService() {
  return importMjs('soilImportPreviewService.mjs');
}

export function loadSoilImportPreviewCache() {
  return importMjs('soilImportPreviewCache.mjs');
}

// Developer: agent query logs + real conversation library
export function loadAgentLogRepository() {
  return importMjs('agentLogRepository.mjs');
}

export function loadRealConversationLibrary() {
  return importMjs('realConversationLibrary.mjs');
}

// Chat: agent chat turn runtime + chat block repository (session-scoped blocks)
export function loadAgentChatRuntime() {
  return importMjs('agentChatRuntime.mjs');
}

export function loadChatBlockRepository() {
  return importMjs('chatBlockRepository.mjs');
}

// Raw mysql helpers (health ping)
export function loadMysql() {
  return importMjs('mysql.mjs');
}
