import test from 'node:test';
import assert from 'node:assert/strict';

async function loadSanitizerModule() {
  return import(new URL(`../lib/server/soilResultSanitizer.mjs?ts=${Date.now()}`, import.meta.url));
}

test('sanitizeTurnBlocks keeps only raw soil columns in stored chat blocks', async () => {
  const { sanitizeTurnBlocks } = await loadSanitizerModule();
  const legacyBlocks = [
    {
      block_id: 'block_summary_1',
      block_type: 'summary_card',
      title: '当前整体墒情',
      metrics: {
        record_count: 15810,
        avg_water20cm: 95.31,
        alert_device_count: 42,
        alert_record_count: 252,
      },
      top_regions: [
        {
          city: '淮安市',
          county: '金湖县',
          max_risk_score: 155.3,
          alert_device_count: 3,
          device_count: 3,
          latest_create_time: '2026-04-13 23:59:17',
        },
      ],
      alert_records_snapshot_id: 'snap_alert',
      focus_devices_snapshot_id: 'snap_device',
    },
    {
      block_id: 'block_group_2',
      block_type: 'group_table',
      title: '地区汇总',
      rows: [
        {
          group_key: '南京市-六合区',
          device_count: 15,
          max_risk_score: 88.02,
          warning_level: 'heavy_drought',
        },
      ],
    },
    {
      block_id: 'block_list_3',
      block_type: 'list_table',
      title: '点位详情',
      columns: ['city', 'county', 'sn', 'latest_create_time', 'water20cm', 'entity_key', 'risk_score'],
      rows: [
        {
          city: '南京市',
          county: '六合区',
          sn: 'SNS00213738',
          latest_create_time: '2026-04-13 23:59:17',
          water20cm: '80.96',
          entity_key: 'SNS00213738',
          risk_score: 67.98,
        },
      ],
    },
  ];

  const cleaned = sanitizeTurnBlocks(legacyBlocks);

  assert.deepEqual(cleaned[0].metrics, {
    record_count: 15810,
    avg_water20cm: 95.31,
  });
  assert.deepEqual(cleaned[0].top_regions, [
    {
      city: '淮安市',
      county: '金湖县',
    },
  ]);
  assert.equal('alert_records_snapshot_id' in cleaned[0], false);
  assert.equal('focus_devices_snapshot_id' in cleaned[0], false);
  assert.deepEqual(cleaned[1].rows, [
    {
      city: '南京市',
      county: '六合区',
    },
  ]);
  assert.deepEqual(cleaned[1].columns, ['city', 'county']);
  assert.deepEqual(cleaned[2].columns, ['city', 'county', 'sn', 'create_time', 'water20cm']);
  assert.deepEqual(cleaned[2].rows, [
    {
      city: '南京市',
      county: '六合区',
      sn: 'SNS00213738',
      create_time: '2026-04-13 23:59:17',
      water20cm: '80.96',
    },
  ]);
  assert.doesNotMatch(
    JSON.stringify(cleaned),
    /max_risk_score|alert_record_count|alert_device_count|warning_level|entity_key|latest_create_time|risk_score/,
  );
});

test('sanitizeExecutedResult keeps only raw soil rows in stored query evidence', async () => {
  const { sanitizeExecutedResult } = await loadSanitizerModule();
  const legacyEvidence = {
    metrics: {
      record_count: 15810,
      avg_water20cm: 95.31,
      alert_record_count: 252,
    },
    top_regions: [
      {
        city: '淮安市',
        county: '金湖县',
        max_risk_score: 155.3,
        alert_device_count: 3,
      },
    ],
    rows: [
      {
        group_key: '南京市-六合区',
        record_count: 15,
        max_risk_score: 88.02,
      },
    ],
    latest_record: {
      city: '南京市',
      county: '六合区',
      sn: 'SNS00213738',
      latest_create_time: '2026-04-13 23:59:17',
      water20cm: '80.96',
      risk_score: 67.98,
    },
  };

  const cleaned = sanitizeExecutedResult(legacyEvidence);

  assert.deepEqual(cleaned, {
    metrics: {
      record_count: 15810,
      avg_water20cm: 95.31,
    },
    top_regions: [
      {
        city: '淮安市',
        county: '金湖县',
      },
    ],
    rows: [
      {
        city: '南京市',
        county: '六合区',
      },
    ],
    latest_record: {
      city: '南京市',
      county: '六合区',
      sn: 'SNS00213738',
      create_time: '2026-04-13 23:59:17',
      water20cm: '80.96',
    },
  });
  assert.doesNotMatch(
    JSON.stringify(cleaned),
    /max_risk_score|alert_record_count|alert_device_count|latest_create_time|risk_score/,
  );
});

test('sanitizeSnapshotPayload keeps only raw soil columns and rewrites legacy create_time alias', async () => {
  const { sanitizeSnapshotPayload } = await loadSanitizerModule();

  const cleaned = sanitizeSnapshotPayload({
    city: '南京市',
    county: '六合区',
    sn: 'SNS00213738',
    latest_create_time: '2026-04-13 23:59:17',
    water20cm: '80.96',
    entity_key: 'SNS00213738',
    risk_score: 67.98,
    display_label: '未达到预警条件',
  });

  assert.deepEqual(cleaned, {
    city: '南京市',
    county: '六合区',
    sn: 'SNS00213738',
    create_time: '2026-04-13 23:59:17',
    water20cm: '80.96',
  });
  assert.doesNotMatch(JSON.stringify(cleaned), /latest_create_time|entity_key|risk_score|display_label/);
});
