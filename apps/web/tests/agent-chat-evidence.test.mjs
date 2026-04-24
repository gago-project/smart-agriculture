import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAnalysisContext } from '../lib/server/agentChatEvidence.mjs';

test('analysis context prefers county from merged slots', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_region_query',
      mergedSlots: { city: '南通市', county: '如东县' },
      contextUsed: {},
    }),
    {
      domain: 'soil',
      region_name: '如东县',
      region_level: 'county',
      query_type: 'soil_region_query',
    },
  );
});

test('analysis context uses city when county is absent', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_recent_summary',
      mergedSlots: { city: '南京市' },
      contextUsed: {},
    }),
    {
      domain: 'soil',
      region_name: '南京市',
      region_level: 'city',
      query_type: 'soil_recent_summary',
    },
  );
});

test('analysis context can inherit region from context meta', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_anomaly_query',
      mergedSlots: {},
      contextUsed: { inheritance_mode: 'carry_frame', city: '徐州市' },
    }),
    {
      domain: 'soil',
      region_name: '徐州市',
      region_level: 'city',
      query_type: 'soil_anomaly_query',
    },
  );
});

test('analysis context stays blank for device-only queries', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_device_query',
      mergedSlots: { sn: 'SNS00204333' },
      contextUsed: {},
    }),
    {
      domain: 'soil',
      region_name: '',
      region_level: '',
      query_type: 'soil_device_query',
    },
  );
});
