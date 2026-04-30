import {
  sanitizeExecutedResult,
  sanitizeSnapshotPayload,
  sanitizeTurnBlocks,
} from './soilResultSanitizer.mjs';

function parseJsonValue(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

export function cleanupStoredTurnBlocksValue(value) {
  const parsed = parseJsonValue(value);
  return sanitizeTurnBlocks(Array.isArray(parsed) ? parsed : []);
}

export function cleanupStoredSnapshotPayloadValue(value) {
  const parsed = parseJsonValue(value);
  return sanitizeSnapshotPayload(parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {});
}

export function cleanupStoredQueryLogValue({ queryType = '', value }) {
  return sanitizeExecutedResult(parseJsonValue(value), { queryType: String(queryType || '') });
}
