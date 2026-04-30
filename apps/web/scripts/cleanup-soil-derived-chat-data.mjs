import { withMysqlTransaction } from '../lib/server/mysql.mjs';
import {
  cleanupStoredQueryLogValue,
  cleanupStoredSnapshotPayloadValue,
  cleanupStoredTurnBlocksValue,
} from '../lib/server/soilDerivedCleanup.mjs';

function normalizeForComparison(value) {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeForComparison(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, normalizeForComparison(value[key])]),
    );
  }
  return value;
}

function stableJson(value) {
  return JSON.stringify(normalizeForComparison(value ?? null));
}

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

function parseFlags(argv) {
  return {
    apply: argv.includes('--apply'),
  };
}

async function collectTurnUpdates(connection) {
  const [rows] = await connection.query(
    `SELECT id, blocks_json
     FROM agent_chat_turn
     WHERE blocks_json IS NOT NULL`,
  );
  const updates = [];
  for (const row of rows) {
    const cleaned = cleanupStoredTurnBlocksValue(row.blocks_json);
    if (stableJson(cleaned) !== stableJson(parseJsonValue(row.blocks_json))) {
      updates.push({ id: Number(row.id), blocks_json: cleaned });
    }
  }
  return updates;
}

async function collectSnapshotUpdates(connection) {
  const [rows] = await connection.query(
    `SELECT snapshot_id, row_index, payload_json
     FROM agent_result_snapshot_item
     WHERE payload_json IS NOT NULL`,
  );
  const updates = [];
  for (const row of rows) {
    const cleaned = cleanupStoredSnapshotPayloadValue(row.payload_json);
    if (stableJson(cleaned) !== stableJson(parseJsonValue(row.payload_json))) {
      updates.push({
        snapshot_id: String(row.snapshot_id),
        row_index: Number(row.row_index),
        payload_json: cleaned,
      });
    }
  }
  return updates;
}

async function collectQueryLogUpdates(connection) {
  const [rows] = await connection.query(
    `SELECT query_id, query_type, executed_result_json, result_digest_json
     FROM agent_query_log
     WHERE executed_result_json IS NOT NULL
        OR result_digest_json IS NOT NULL`,
  );
  const updates = [];
  for (const row of rows) {
    const queryType = String(row.query_type || '');
    const executedResult = cleanupStoredQueryLogValue({
      queryType,
      value: row.executed_result_json,
    });
    const resultDigest = cleanupStoredQueryLogValue({
      queryType,
      value: row.result_digest_json,
    });
    if (
      stableJson(executedResult) !== stableJson(parseJsonValue(row.executed_result_json))
      || stableJson(resultDigest) !== stableJson(parseJsonValue(row.result_digest_json))
    ) {
      updates.push({
        query_id: String(row.query_id),
        executed_result_json: executedResult,
        result_digest_json: resultDigest,
      });
    }
  }
  return updates;
}

async function applyUpdates(connection, turnUpdates, snapshotUpdates, queryLogUpdates) {
  for (const row of turnUpdates) {
    await connection.execute(
      `UPDATE agent_chat_turn
       SET blocks_json = ?
       WHERE id = ?`,
      [stableJson(row.blocks_json), row.id],
    );
  }

  for (const row of snapshotUpdates) {
    await connection.execute(
      `UPDATE agent_result_snapshot_item
       SET payload_json = ?
       WHERE snapshot_id = ? AND row_index = ?`,
      [stableJson(row.payload_json), row.snapshot_id, row.row_index],
    );
  }

  for (const row of queryLogUpdates) {
    await connection.execute(
      `UPDATE agent_query_log
       SET executed_result_json = ?,
           result_digest_json = ?
       WHERE query_id = ?`,
      [
        stableJson(row.executed_result_json),
        stableJson(row.result_digest_json),
        row.query_id,
      ],
    );
  }
}

async function main() {
  const { apply } = parseFlags(process.argv.slice(2));
  const summary = await withMysqlTransaction(async (connection) => {
    const turnUpdates = await collectTurnUpdates(connection);
    const snapshotUpdates = await collectSnapshotUpdates(connection);
    const queryLogUpdates = await collectQueryLogUpdates(connection);

    if (apply) {
      await applyUpdates(connection, turnUpdates, snapshotUpdates, queryLogUpdates);
    }

    return {
      mode: apply ? 'apply' : 'dry-run',
      agent_chat_turn: turnUpdates.length,
      agent_result_snapshot_item: snapshotUpdates.length,
      agent_query_log: queryLogUpdates.length,
    };
  });

  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
