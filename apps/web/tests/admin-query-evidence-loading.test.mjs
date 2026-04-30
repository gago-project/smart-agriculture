import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const sidebarSource = readFileSync(new URL('../workspace/components/AdminQueryEvidenceSidebar.tsx', import.meta.url), 'utf8');

test('query evidence sidebar does not self-cancel the main evidence request during loading rerenders', () => {
  assert.match(sidebarSource, /fetchAdminQueryEvidence\(/);
  assert.doesNotMatch(
    sidebarSource,
    /\[\s*cacheKey,\s*evidenceCache,\s*sessionId,\s*shouldQuery,\s*turnId\s*\]/,
  );
});

test('query evidence sidebar does not self-cancel lazy raw JSON requests during loading rerenders', () => {
  assert.match(sidebarSource, /fetchAdminQueryEvidenceResult\(/);
  assert.doesNotMatch(
    sidebarSource,
    /\[\s*canLoadRaw,\s*detailsOpen,\s*queryId,\s*rawState\.data,\s*rawState\.loading,\s*resultTruncated\s*\]/,
  );
});
