import crypto from 'node:crypto';

import { classifySoilAnomaly } from './soilAdminStore.mjs';
import { refreshGeneratedRegionAliasesFromFacts } from './regionAliasSeed.mjs';
import { parseSoilWorkbookBuffer } from './soilImport.mjs';
import { withMysqlConnection } from './mysql.mjs';

const FACT_INSERT_COLUMNS = [
  'record_id',
  'batch_id',
  'device_sn',
  'gateway_id',
  'sensor_id',
  'unit_id',
  'device_name',
  'city_name',
  'county_name',
  'town_name',
  'sample_time',
  'create_time',
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  't40cm',
  't60cm',
  't80cm',
  'water20cm_field_state',
  'water40cm_field_state',
  'water60cm_field_state',
  'water80cm_field_state',
  't20cm_field_state',
  't40cm_field_state',
  't60cm_field_state',
  't80cm_field_state',
  'soil_anomaly_type',
  'soil_anomaly_score',
  'longitude',
  'latitude',
  'source_file',
  'source_sheet',
  'source_row',
];

function makeBatchId() {
  return crypto.randomUUID();
}

function chunkArray(items, chunkSize) {
  const chunks = [];
  for (let index = 0; index < items.length; index += chunkSize) {
    chunks.push(items.slice(index, index + chunkSize));
  }
  return chunks;
}

function toDbRecord(record, batchId) {
  return [
    record.record_id,
    batchId,
    record.device_sn,
    record.gateway_id || null,
    record.sensor_id || null,
    record.unit_id || null,
    record.device_name || null,
    record.city_name || null,
    record.county_name || null,
    record.town_name || null,
    record.sample_time,
    record.create_time || record.sample_time || null,
    record.water20cm,
    record.water40cm,
    record.water60cm,
    record.water80cm,
    record.t20cm,
    record.t40cm,
    record.t60cm,
    record.t80cm,
    record.water20cm_field_state || null,
    record.water40cm_field_state || null,
    record.water60cm_field_state || null,
    record.water80cm_field_state || null,
    record.t20cm_field_state || null,
    record.t40cm_field_state || null,
    record.t60cm_field_state || null,
    record.t80cm_field_state || null,
    record.soil_anomaly_type || null,
    record.soil_anomaly_score,
    record.longitude,
    record.latitude,
    record.source_file || null,
    record.source_sheet || null,
    record.source_row ?? null,
  ];
}

function fromDbRecord(row) {
  return {
    record_id: row.record_id,
    device_sn: row.device_sn,
    gateway_id: row.gateway_id,
    sensor_id: row.sensor_id,
    unit_id: row.unit_id,
    city_name: row.city_name,
    county_name: row.county_name,
    town_name: row.town_name,
    device_name: row.device_name,
    sample_time: row.sample_time,
    create_time: row.create_time,
    water20cm: row.water20cm,
    water40cm: row.water40cm,
    water60cm: row.water60cm,
    water80cm: row.water80cm,
    t20cm: row.t20cm,
    t40cm: row.t40cm,
    t60cm: row.t60cm,
    t80cm: row.t80cm,
    water20cm_field_state: row.water20cm_field_state,
    water40cm_field_state: row.water40cm_field_state,
    water60cm_field_state: row.water60cm_field_state,
    water80cm_field_state: row.water80cm_field_state,
    t20cm_field_state: row.t20cm_field_state,
    t40cm_field_state: row.t40cm_field_state,
    t60cm_field_state: row.t60cm_field_state,
    t80cm_field_state: row.t80cm_field_state,
    latitude: row.latitude,
    longitude: row.longitude,
    soil_anomaly_type: row.soil_anomaly_type,
    soil_anomaly_score: row.soil_anomaly_score,
    source_file: row.source_file,
    source_sheet: row.source_sheet,
    source_row: row.source_row,
  };
}

async function insertFactRows(connection, records, batchId, options = {}) {
  const insertKeyword = options.ignoreDuplicates ? 'INSERT IGNORE' : 'INSERT';
  let insertedRows = 0;

  for (const chunk of chunkArray(records, 200)) {
    const values = chunk.flatMap((record) => toDbRecord(record, batchId));
    const placeholders = chunk.map(() => `(${FACT_INSERT_COLUMNS.map(() => '?').join(', ')})`).join(', ');
    const [result] = await connection.execute(
      `${insertKeyword} INTO fact_soil_moisture (${FACT_INSERT_COLUMNS.join(', ')}) VALUES ${placeholders}`,
      values,
    );
    insertedRows += Number(result.affectedRows || 0);
  }

  return insertedRows;
}

export async function listSoilRecords(query) {
  return await withMysqlConnection(async (connection) => {
    const filters = [];
    const params = [];
    if (query.city_name) {
      filters.push('city_name LIKE ?');
      params.push(`%${query.city_name}%`);
    }
    if (query.county_name) {
      filters.push('county_name LIKE ?');
      params.push(`%${query.county_name}%`);
    }
    if (query.device_sn) {
      filters.push('device_sn LIKE ?');
      params.push(`%${query.device_sn}%`);
    }
    if (query.soil_anomaly_type) {
      filters.push('soil_anomaly_type = ?');
      params.push(query.soil_anomaly_type);
    }
    if (query.sample_time_from) {
      filters.push('sample_time >= ?');
      params.push(query.sample_time_from);
    }
    if (query.sample_time_to) {
      filters.push('sample_time <= ?');
      params.push(query.sample_time_to);
    }
    const whereClause = filters.length > 0 ? `WHERE ${filters.join(' AND ')}` : '';
    const page = Math.max(1, Number(query.page || 1));
    const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 50)));
    const offset = (page - 1) * pageSize;

    const [countRows] = await connection.execute(
      `SELECT COUNT(*) AS total FROM fact_soil_moisture ${whereClause}`,
      params,
    );
    const [rows] = await connection.query(
      `SELECT
         record_id,
         device_sn,
         city_name,
         county_name,
         town_name,
         device_name,
         DATE_FORMAT(sample_time, '%Y-%m-%d %H:%i:%s') AS sample_time,
         water20cm,
         water40cm,
         water60cm,
         water80cm,
         t20cm,
         t40cm,
         t60cm,
         t80cm,
         latitude,
         longitude,
         soil_anomaly_type,
         soil_anomaly_score,
         source_file,
         source_sheet,
         source_row
       FROM fact_soil_moisture
       ${whereClause}
       ORDER BY sample_time DESC
       LIMIT ? OFFSET ?`,
      [...params, pageSize, offset],
    );
    const total = Number(countRows[0]?.total || 0);
    return {
      rows: rows.map(fromDbRecord),
      total,
      page,
      page_size: pageSize,
      total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
    };
  });
}

export async function importSoilWorkbook({ filename, contentBase64, mode, confirmFullReplace }) {
  const buffer = Buffer.from(contentBase64, 'base64');
  const parsed = parseSoilWorkbookBuffer(buffer, filename);
  const batchId = makeBatchId();
  const sourceName = 'soil_admin_upload';

  if (mode === 'replace' && !confirmFullReplace) {
    throw new Error('全量覆盖导入必须显式确认');
  }

  return await withMysqlConnection(async (connection) => {
    await connection.execute(
      `INSERT INTO etl_import_batch (
         batch_id, source_name, source_file, started_at, finished_at, status, raw_row_count, loaded_row_count, note
       ) VALUES (?, ?, ?, NOW(), NULL, 'processing', ?, 0, NULL)`,
      [batchId, sourceName, filename, parsed.raw_rows],
    );

    let loadedRows = 0;
    try {
      await connection.beginTransaction();
      if (mode === 'replace') {
        await connection.execute('DELETE FROM fact_soil_moisture');
      }

      loadedRows = await insertFactRows(connection, parsed.records, batchId, {
        ignoreDuplicates: mode === 'incremental',
      });

      await connection.execute(
        `UPDATE etl_import_batch
         SET finished_at = NOW(), status = 'success', loaded_row_count = ?, note = NULL
         WHERE batch_id = ?`,
        [loadedRows, batchId],
      );
      await refreshGeneratedRegionAliasesFromFacts(connection);
      await connection.commit();
    } catch (error) {
      await connection.rollback();
      await connection.execute(
        `UPDATE etl_import_batch
         SET finished_at = NOW(), status = 'failed', loaded_row_count = ?, note = ?
         WHERE batch_id = ?`,
        [loadedRows, error instanceof Error ? error.message.slice(0, 500) : 'import failed', batchId],
      );
      throw error;
    }

    return {
      filename,
      mode,
      batch_id: batchId,
      raw_rows: parsed.raw_rows,
      loaded_rows: loadedRows,
      invalid_rows: parsed.invalid_rows?.length ?? 0,
    };
  });
}

export async function patchSoilRecord(recordId, field, value) {
  return await withMysqlConnection(async (connection) => {
    const editable = new Set([
      'city_name', 'county_name', 'town_name', 'device_name', 'longitude', 'latitude', 'water20cm',
      'water40cm', 'water60cm', 'water80cm', 't20cm', 't40cm', 't60cm', 't80cm', 'soil_anomaly_type',
      'soil_anomaly_score',
    ]);
    if (!editable.has(field)) {
      throw new Error('当前字段不允许通过后台修改');
    }
    if (field === 'water20cm') {
      const anomaly = classifySoilAnomaly(value);
      await connection.execute(
        `UPDATE fact_soil_moisture
         SET water20cm = ?, soil_anomaly_type = ?, soil_anomaly_score = ?
         WHERE record_id = ?`,
        [value, anomaly.soil_anomaly_type, anomaly.soil_anomaly_score, recordId],
      );
    } else {
      await connection.execute(`UPDATE fact_soil_moisture SET ${field} = ? WHERE record_id = ?`, [value, recordId]);
    }

    await refreshGeneratedRegionAliasesFromFacts(connection);

    const [rows] = await connection.execute(
      `SELECT
         record_id, device_sn, gateway_id, sensor_id, unit_id, city_name, county_name, town_name, device_name,
         DATE_FORMAT(sample_time, '%Y-%m-%d %H:%i:%s') AS sample_time,
         DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,
         water20cm, water40cm, water60cm, water80cm, t20cm, t40cm, t60cm, t80cm,
         water20cm_field_state, water40cm_field_state, water60cm_field_state, water80cm_field_state,
         t20cm_field_state, t40cm_field_state, t60cm_field_state, t80cm_field_state,
         latitude, longitude, soil_anomaly_type, soil_anomaly_score, source_file, source_sheet, source_row
       FROM fact_soil_moisture WHERE record_id = ? LIMIT 1`,
      [recordId],
    );
    return {
      record_id: recordId,
      field,
      new_value: value,
      record: rows[0] ? fromDbRecord(rows[0]) : null,
    };
  });
}

export async function removeSoilRecords(recordIds) {
  return await withMysqlConnection(async (connection) => {
    if (recordIds.length === 0) return { deleted_count: 0 };
    const placeholders = recordIds.map(() => '?').join(', ');
    const [result] = await connection.execute(
      `DELETE FROM fact_soil_moisture WHERE record_id IN (${placeholders})`,
      recordIds,
    );
    const deletedCount = Number(result.affectedRows || 0);
    if (deletedCount > 0) {
      await refreshGeneratedRegionAliasesFromFacts(connection);
    }
    return { deleted_count: deletedCount };
  });
}

export async function listRuleConfig() {
  return await withMysqlConnection(async (connection) => {
    const [rules] = await connection.execute(
      'SELECT rule_code AS rule_id, rule_name, rule_scope AS rule_type, rule_definition_json, enabled FROM metric_rule ORDER BY rule_code ASC',
    );
    const [templates] = await connection.execute(
      'SELECT template_id, template_name, template_text, version AS render_mode FROM warning_template ORDER BY template_id ASC',
    );
    return { rules, templates };
  });
}

export async function patchRuleConfig(payload) {
  const { rule_id, template_id, rule_definition_json, enabled, template_text } = payload;
  return await withMysqlConnection(async (connection) => {
    if (rule_id) {
      await connection.execute(
        'UPDATE metric_rule SET rule_definition_json = ?, enabled = ?, updated_at = NOW() WHERE rule_code = ?',
        [rule_definition_json, enabled ? 1 : 0, rule_id],
      );
    }
    if (template_id) {
      await connection.execute(
        'UPDATE warning_template SET template_text = ?, updated_at = NOW() WHERE template_id = ?',
        [template_text, template_id],
      );
    }
    return listRuleConfig();
  });
}
