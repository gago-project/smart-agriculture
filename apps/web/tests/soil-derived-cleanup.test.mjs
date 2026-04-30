import test from 'node:test';
import assert from 'node:assert/strict';

async function loadCleanupModule() {
  return import(new URL(`../lib/server/soilDerivedCleanup.mjs?ts=${Date.now()}`, import.meta.url));
}

test('cleanup helpers sanitize persisted turn, snapshot, and query-log payloads', async () => {
  const {
    cleanupStoredTurnBlocksValue,
    cleanupStoredSnapshotPayloadValue,
    cleanupStoredQueryLogValue,
  } = await loadCleanupModule();

  const cleanedTurnBlocks = cleanupStoredTurnBlocksValue(
    JSON.stringify([
      {
        block_id: 'block_summary_1',
        block_type: 'summary_card',
        metrics: {
          record_count: 20,
          avg_water20cm: 92.1,
        },
        top_regions: [
          {
            city: '南京市',
            county: '六合区',
            max_risk_score: 88.2,
          },
        ],
      },
    ]),
  );
  assert.deepEqual(cleanedTurnBlocks, [
    {
      block_id: 'block_summary_1',
      block_type: 'summary_card',
      top_regions: [
        {
          city: '南京市',
          county: '六合区',
        },
      ],
    },
  ]);

  const cleanedSnapshot = cleanupStoredSnapshotPayloadValue(
    JSON.stringify({
      city: '南京市',
      county: '六合区',
      sn: 'SNS00213738',
      source_file: 'soil.xlsx',
      source_sheet: 'soil',
      source_row: 2,
      latest_create_time: '2026-04-13 23:59:17',
      water20cm: '80.96',
      risk_score: 67.98,
    }),
  );
  assert.deepEqual(cleanedSnapshot, {
    city: '南京市',
    county: '六合区',
    sn: 'SNS00213738',
    create_time: '2026-04-13 23:59:17',
    water20cm: '80.96',
  });

  const cleanedQueryLog = cleanupStoredQueryLogValue({
    queryType: 'detail',
    value: JSON.stringify({
      metrics: {
        record_count: 20,
      },
      latest_record: {
        city: '南京市',
        county: '六合区',
        source_file: 'soil.xlsx',
        source_sheet: 'soil',
        source_row: 2,
        latest_create_time: '2026-04-13 23:59:17',
        water20cm: '80.96',
        risk_score: 67.98,
      },
    }),
  });
  assert.deepEqual(cleanedQueryLog, {
    latest_record: {
      city: '南京市',
      county: '六合区',
      create_time: '2026-04-13 23:59:17',
      water20cm: '80.96',
    },
  });
});
