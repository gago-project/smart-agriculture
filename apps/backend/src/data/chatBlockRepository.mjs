import { isPaginatedTableBlockType } from '../chatBlockContract.mjs';
import { withMysqlConnection } from './mysql.mjs';
import { sanitizeTurnBlocks } from './soilResultSanitizer.mjs';

const SNAPSHOT_PAGE_SIZE_DEFAULT = 10;

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

function toPositiveInt(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
}

function clampPageSize(pageSize) {
  return Math.min(SNAPSHOT_PAGE_SIZE_DEFAULT, Math.max(1, toPositiveInt(pageSize, SNAPSHOT_PAGE_SIZE_DEFAULT)));
}

export async function getChatBlockPageBySnapshot({ snapshotId, blockType, page, pageSize }) {
  const normalizedSnapshotId = String(snapshotId || '').trim();
  const normalizedBlockType = String(blockType || '').trim();
  const safePage = Math.max(1, toPositiveInt(page, 1));
  const safePageSize = clampPageSize(pageSize);

  if (!normalizedSnapshotId) {
    throw new Error('snapshot_id is required');
  }
  if (!isPaginatedTableBlockType(normalizedBlockType)) {
    throw new Error('block_type is invalid');
  }

  return await withMysqlConnection(async (connection) => {
    const [snapshotRows] = await connection.execute(
      `SELECT total_count
       FROM agent_result_snapshot
       WHERE snapshot_id = ?
       LIMIT 1`,
      [normalizedSnapshotId],
    );
    const snapshotRow = snapshotRows[0];
    if (!snapshotRow) {
      throw new Error('结果快照不存在或已过期');
    }

    const totalCount = Number(snapshotRow.total_count || 0);
    const totalPages = totalCount <= 0 ? 0 : Math.ceil(totalCount / safePageSize);
    const offset = (safePage - 1) * safePageSize;
    const [itemRows] = await connection.query(
      `SELECT payload_json
       FROM agent_result_snapshot_item
       WHERE snapshot_id = ?
       ORDER BY row_index ASC
       LIMIT ? OFFSET ?`,
      [normalizedSnapshotId, safePageSize, offset],
    );
    const rows = itemRows.map((row) => parseJsonValue(row.payload_json) || {});
    const sanitizedBlock = sanitizeTurnBlocks([
      {
        block_id: `snapshot:${normalizedSnapshotId}`,
        block_type: normalizedBlockType,
        rows,
      },
    ])[0] || { rows: [] };

    return {
      block_type: normalizedBlockType,
      rows: Array.isArray(sanitizedBlock.rows) ? sanitizedBlock.rows : [],
      pagination: {
        snapshot_id: normalizedSnapshotId,
        page: safePage,
        page_size: safePageSize,
        total_count: totalCount,
        total_pages: totalPages,
      },
    };
  });
}
