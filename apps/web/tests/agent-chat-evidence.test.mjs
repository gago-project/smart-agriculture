import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAnalysisContext } from '../lib/server/agentChatEvidence.mjs';

test('analysis context derives region from answer_facts entity_name', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_region_query',
      toolTrace: [{ tool_name: 'query_soil_detail', tool_args: { region_name: '如东县' }, result_summary: {} }],
      answerFacts: { entity_type: 'region', entity_name: '如东县', record_count: 5 },
    }),
    {
      domain: 'soil',
      region_name: '如东县',
      region_level: 'region',
      query_type: 'soil_region_query',
    },
  );
});

test('analysis context falls back to first tool args when facts lack entity_name', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_recent_summary',
      toolTrace: [{ tool_name: 'query_soil_summary', tool_args: { region_name: '南京市' }, result_summary: {} }],
      answerFacts: {},
    }),
    {
      domain: 'soil',
      region_name: '南京市',
      region_level: 'region',
      query_type: 'soil_recent_summary',
    },
  );
});

test('analysis context stays blank when no region can be derived', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_recent_summary',
      toolTrace: [],
      answerFacts: {},
    }),
    {
      domain: 'soil',
      region_name: '',
      region_level: '',
      query_type: 'soil_recent_summary',
    },
  );
});

test('analysis context handles device queries without region level', () => {
  assert.deepEqual(
    buildAnalysisContext({
      intent: 'soil_device_query',
      toolTrace: [{ tool_name: 'query_soil_detail', tool_args: { sn: 'SNS00204333' }, result_summary: {} }],
      answerFacts: { entity_type: 'device', entity_name: 'SNS00204333', record_count: 3 },
    }),
    {
      domain: 'soil',
      region_name: 'SNS00204333',
      region_level: '',
      query_type: 'soil_device_query',
    },
  );
});
