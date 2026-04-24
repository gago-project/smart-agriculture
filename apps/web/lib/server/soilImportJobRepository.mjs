import crypto from 'node:crypto';

import { buildSoilImportPreview, getApplyRowsForMode } from './soilImportJob.mjs';
import { openMysqlConnection, withMysqlConnection } from './mysql.mjs';
import { refreshGeneratedRegionAliasesFromFacts } from './regionAliasSeed.mjs';
import { parseSoilWorkbookBuffer } from './soilImport.mjs';

const FACT_COLUMNS = [
  'id',
  'sn',
  'gatewayid',
  'sensorid',
  'unitid',
  'city',
  'county',
  'time',
  'create_time',
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  't40cm',
  't60cm',
  't80cm',
  'water20cmfieldstate',
  'water40cmfieldstate',
  'water60cmfieldstate',
  'water80cmfieldstate',
  't20cmfieldstate',
  't40cmfieldstate',
  't60cmfieldstate',
  't80cmfieldstate',
  'lat',
  'lon',
  'source_file',
  'source_sheet',
  'source_row',
];

const FACT_SNAPSHOT_SELECT = `SELECT
  id,
  sn,
  gatewayid,
  sensorid,
  unitid,
  city,
  county,
  DATE_FORMAT(time, '%Y-%m-%d %H:%i:%s') AS time,
  DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
  water20cm,
  water40cm,
  water60cm,
  water80cm,
  t20cm,
  t40cm,
  t60cm,
  t80cm,
  water20cmfieldstate,
  water40cmfieldstate,
  water60cmfieldstate,
  water80cmfieldstate,
  t20cmfieldstate,
  t40cmfieldstate,
  t60cmfieldstate,
  t80cmfieldstate,
  lat,
  lon,
  source_file,
  source_sheet,
  source_row
FROM fact_soil_moisture`;

const RUNNING_IMPORT_JOBS = new Map();

function chunkArray(items, chunkSize) {
  const chunks = [];
  for (let index = 0; index < items.length; index += chunkSize) {
    chunks.push(items.slice(index, index + chunkSize));
  }
  return chunks;
}

function parseJsonField(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (typeof value === 'object') {
    return value;
  }
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function toFactInsertRow(record) {
  return FACT_COLUMNS.map((column) => {
    if (column === 'time' || column === 'create_time') {
      return record[column] || null;
    }
    if (column === 'source_row') {
      return record[column] ?? null;
    }
    return record[column] ?? null;
  });
}

async function loadFactSnapshots(connection) {
  const [rows] = await connection.query(`${FACT_SNAPSHOT_SELECT} ORDER BY id ASC`);
  return rows;
}

async function updateJobProgress(connection, jobId, patch) {
  const fields = [];
  const values = [];
  for (const [key, value] of Object.entries(patch)) {
    fields.push(`${key} = ?`);
    values.push(value);
  }
  if (fields.length === 0) {
    return;
  }
  values.push(jobId);
  await connection.execute(
    `UPDATE soil_import_job SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP WHERE job_id = ?`,
    values,
  );
}

async function insertDiffRows(connection, jobId, diffRows, onProgress) {
  const chunks = chunkArray(diffRows, 200);
  let processed = 0;
  for (const chunk of chunks) {
    const values = chunk.flatMap((row) => [
      jobId,
      row.diff_type,
      row.id,
      row.source_row,
      row.db_record_json ? JSON.stringify(row.db_record_json) : null,
      row.import_record_json ? JSON.stringify(row.import_record_json) : null,
      row.field_changes_json ? JSON.stringify(row.field_changes_json) : null,
    ]);
    const placeholders = chunk.map(() => '(?, ?, ?, ?, ?, ?, ?)').join(', ');
    await connection.execute(
      `INSERT INTO soil_import_job_diff (
        job_id, diff_type, id, source_row, db_record_json, import_record_json, field_changes_json
      ) VALUES ${placeholders}`,
      values,
    );
    processed += chunk.length;
    if (onProgress) {
      await onProgress(processed);
    }
  }
}

async function insertFactRows(connection, records, onProgress) {
  const chunks = chunkArray(records, 200);
  let processed = 0;
  for (const chunk of chunks) {
    const values = chunk.flatMap((record) => toFactInsertRow(record));
    const placeholders = chunk.map(() => `(${FACT_COLUMNS.map(() => '?').join(', ')})`).join(', ');
    await connection.execute(
      `INSERT INTO fact_soil_moisture (${FACT_COLUMNS.join(', ')}) VALUES ${placeholders}`,
      values,
    );
    processed += chunk.length;
    if (onProgress) {
      await onProgress(processed);
    }
  }
}

async function getJobRow(connection, jobId) {
  const [rows] = await connection.execute(
    `SELECT
       job_id,
       filename,
       requested_by_user_id,
       requested_by_username,
       status,
       apply_mode,
       processed_rows,
       total_rows,
       summary_json,
       error_message,
       DATE_FORMAT(finished_at, '%Y-%m-%d %H:%i:%s') AS finished_at,
       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
       DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updated_at
     FROM soil_import_job
     WHERE job_id = ?
     LIMIT 1`,
    [jobId],
  );
  return rows[0] || null;
}

async function formatJob(connection, jobId) {
  const row = await getJobRow(connection, jobId);
  if (!row) {
    throw new Error('导入任务不存在');
  }
  return {
    job_id: row.job_id,
    filename: row.filename,
    requested_by_user_id: row.requested_by_user_id,
    requested_by_username: row.requested_by_username,
    status: row.status,
    apply_mode: row.apply_mode,
    processed_rows: Number(row.processed_rows || 0),
    total_rows: Number(row.total_rows || 0),
    summary: parseJsonField(row.summary_json),
    error_message: row.error_message,
    finished_at: row.finished_at,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function runInBackground(jobId, task) {
  if (RUNNING_IMPORT_JOBS.has(jobId)) {
    return;
  }
  const promise = Promise.resolve()
    .then(task)
    .catch((error) => {
      console.error(`[soil-import-job:${jobId}]`, error);
    })
    .finally(() => {
      RUNNING_IMPORT_JOBS.delete(jobId);
    });
  RUNNING_IMPORT_JOBS.set(jobId, promise);
}

async function runPreviewJob(jobId, filename, contentBase64) {
  const connection = await openMysqlConnection({ connectTimeout: 5000 });
  try {
    const buffer = Buffer.from(contentBase64, 'base64');
    const parsed = parseSoilWorkbookBuffer(buffer, filename);
    const existingRecords = await loadFactSnapshots(connection);
    const preview = buildSoilImportPreview({
      existingRecords,
      importedRecords: parsed.records,
      invalidRows: parsed.invalid_rows,
    });

    if (preview.duplicate_ids?.length) {
      const duplicateMessage = preview.duplicate_ids
        .map((item) => `${item.id} [${item.source_rows.join(', ')}]`)
        .join('；');
      await connection.execute('DELETE FROM soil_import_job_diff WHERE job_id = ?', [jobId]);
      await updateJobProgress(connection, jobId, {
        status: 'failed',
        error_message: `上传文件中存在重复 id：${duplicateMessage}`,
        finished_at: new Date(),
      });
      return;
    }

    await connection.execute('DELETE FROM soil_import_job_diff WHERE job_id = ?', [jobId]);
    await updateJobProgress(connection, jobId, {
      status: 'previewing',
      processed_rows: 0,
      total_rows: preview.diff_rows.length,
      summary_json: JSON.stringify(preview.summary),
      error_message: null,
      finished_at: null,
    });

    await insertDiffRows(connection, jobId, preview.diff_rows, async (processed) => {
      await updateJobProgress(connection, jobId, { processed_rows: processed });
    });

    await updateJobProgress(connection, jobId, {
      status: 'ready',
      processed_rows: preview.diff_rows.length,
      total_rows: preview.diff_rows.length,
      summary_json: JSON.stringify(preview.summary),
      finished_at: new Date(),
    });
  } catch (error) {
    await connection.execute('DELETE FROM soil_import_job_diff WHERE job_id = ?', [jobId]);
    await updateJobProgress(connection, jobId, {
      status: 'failed',
      error_message: error instanceof Error ? error.message.slice(0, 500) : '导入预览失败',
      finished_at: new Date(),
    });
  } finally {
    await connection.end();
  }
}

async function loadImportRecordsForApply(connection, jobId, mode) {
  const diffTypes = mode === 'replace' ? ['create', 'update', 'unchanged'] : ['create'];
  const placeholders = diffTypes.map(() => '?').join(', ');
  const [rows] = await connection.query(
    `SELECT diff_id, import_record_json
     FROM soil_import_job_diff
     WHERE job_id = ?
       AND diff_type IN (${placeholders})
       AND import_record_json IS NOT NULL
     ORDER BY diff_id ASC`,
    [jobId, ...diffTypes],
  );
  return rows.map((row) => parseJsonField(row.import_record_json)).filter(Boolean);
}

async function runApplyJob(jobId, mode) {
  const connection = await openMysqlConnection({ connectTimeout: 5000 });
  const progressConnection = await openMysqlConnection({ connectTimeout: 5000 });

  try {
    const job = await formatJob(connection, jobId);
    const summary = job.summary || {};
    const records = await loadImportRecordsForApply(connection, jobId, mode);
    const totalRows = getApplyRowsForMode(summary, mode);

    await updateJobProgress(progressConnection, jobId, {
      status: 'applying',
      apply_mode: mode,
      processed_rows: 0,
      total_rows: totalRows,
      error_message: null,
      finished_at: null,
    });

    await connection.beginTransaction();
    if (mode === 'replace') {
      await connection.execute('DELETE FROM fact_soil_moisture');
    }

    await insertFactRows(connection, records, async (processed) => {
      await updateJobProgress(progressConnection, jobId, { processed_rows: processed });
    });

    await refreshGeneratedRegionAliasesFromFacts(connection);
    await connection.commit();

    await updateJobProgress(progressConnection, jobId, {
      status: 'applied',
      processed_rows: totalRows,
      total_rows: totalRows,
      finished_at: new Date(),
    });
  } catch (error) {
    try {
      await connection.rollback();
    } catch {
    }
    await updateJobProgress(progressConnection, jobId, {
      status: 'failed',
      error_message: error instanceof Error ? error.message.slice(0, 500) : '导入应用失败',
      finished_at: new Date(),
    });
  } finally {
    await progressConnection.end();
    await connection.end();
  }
}

export async function createSoilImportJob({ filename, contentBase64, operatorUser }) {
  const jobId = crypto.randomUUID();
  await withMysqlConnection(async (connection) => {
    await connection.execute(
      `INSERT INTO soil_import_job (
         job_id, filename, requested_by_user_id, requested_by_username, status, apply_mode,
         processed_rows, total_rows, summary_json, error_message, finished_at
       ) VALUES (?, ?, ?, ?, 'previewing', NULL, 0, 0, NULL, NULL, NULL)`,
      [jobId, filename, operatorUser?.id ?? null, operatorUser?.username ?? null],
    );
  });

  runInBackground(jobId, async () => {
    await runPreviewJob(jobId, filename, contentBase64);
  });

  return await getSoilImportJob(jobId);
}

export async function getSoilImportJob(jobId) {
  return await withMysqlConnection(async (connection) => {
    return await formatJob(connection, jobId);
  });
}

export async function listSoilImportJobDiff(jobId, query = {}) {
  return await withMysqlConnection(async (connection) => {
    const job = await getJobRow(connection, jobId);
    if (!job) {
      throw new Error('导入任务不存在');
    }

    const page = Math.max(1, Number(query.page || 1));
    const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 20)));
    const offset = (page - 1) * pageSize;
    const diffType = String(query.type || '').trim();
    const filters = ['job_id = ?'];
    const params = [jobId];

    if (diffType && diffType !== 'all') {
      filters.push('diff_type = ?');
      params.push(diffType);
    }

    const whereClause = `WHERE ${filters.join(' AND ')}`;
    const [countRows] = await connection.execute(
      `SELECT COUNT(*) AS total FROM soil_import_job_diff ${whereClause}`,
      params,
    );
    const [rows] = await connection.query(
      `SELECT
         diff_id,
         diff_type,
         id,
         source_row,
         db_record_json,
         import_record_json,
         field_changes_json,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at
       FROM soil_import_job_diff
       ${whereClause}
       ORDER BY diff_id ASC
       LIMIT ? OFFSET ?`,
      [...params, pageSize, offset],
    );

    const total = Number(countRows[0]?.total || 0);
    return {
      rows: rows.map((row) => ({
        diff_id: Number(row.diff_id),
        diff_type: row.diff_type,
        id: row.id,
        source_row: row.source_row,
        db_record: parseJsonField(row.db_record_json),
        import_record: parseJsonField(row.import_record_json),
        field_changes: parseJsonField(row.field_changes_json),
        created_at: row.created_at,
      })),
      total,
      page,
      page_size: pageSize,
      total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
      summary: parseJsonField(job.summary_json),
      status: job.status,
    };
  });
}

export async function startSoilImportApplyJob({ jobId, mode, confirmFullReplace }) {
  if (mode === 'replace' && !confirmFullReplace) {
    throw new Error('全量覆盖导入必须显式确认');
  }

  await withMysqlConnection(async (connection) => {
    const job = await formatJob(connection, jobId);
    if (job.status !== 'ready') {
      throw new Error('当前导入任务还不能执行应用');
    }
    const applyRows = getApplyRowsForMode(job.summary || {}, mode);
    await updateJobProgress(connection, jobId, {
      status: 'applying',
      apply_mode: mode,
      processed_rows: 0,
      total_rows: applyRows,
      error_message: null,
      finished_at: null,
    });
  });

  runInBackground(jobId, async () => {
    await runApplyJob(jobId, mode);
  });

  return await getSoilImportJob(jobId);
}
