import { refreshGeneratedRegionAliasesFromFacts } from './regionAliasSeed.mjs';
import { parseSoilWorkbookBuffer } from './soilImport.mjs';
import { withMysqlConnection } from './mysql.mjs';

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

const SELECT_FACT_SQL = `SELECT
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

function chunkArray(items, chunkSize) {
  const chunks = [];
  for (let index = 0; index < items.length; index += chunkSize) {
    chunks.push(items.slice(index, index + chunkSize));
  }
  return chunks;
}

function toDbRecord(record) {
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

async function insertFactRows(connection, records, options = {}) {
  if (records.length === 0) {
    return 0;
  }
  const insertKeyword = options.ignoreDuplicates ? 'INSERT IGNORE' : 'INSERT';
  let insertedRows = 0;

  for (const chunk of chunkArray(records, 200)) {
    const values = chunk.flatMap((record) => toDbRecord(record));
    const placeholders = chunk.map(() => `(${FACT_COLUMNS.map(() => '?').join(', ')})`).join(', ');
    const [result] = await connection.execute(
      `${insertKeyword} INTO fact_soil_moisture (${FACT_COLUMNS.join(', ')}) VALUES ${placeholders}`,
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
    if (query.city) {
      filters.push('city LIKE ?');
      params.push(`%${query.city}%`);
    }
    if (query.county) {
      filters.push('county LIKE ?');
      params.push(`%${query.county}%`);
    }
    if (query.sn) {
      filters.push('sn LIKE ?');
      params.push(`%${query.sn}%`);
    }
    if (query.create_time_from) {
      filters.push('create_time >= ?');
      params.push(query.create_time_from);
    }
    if (query.create_time_to) {
      filters.push('create_time <= ?');
      params.push(query.create_time_to);
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
      `${SELECT_FACT_SQL}
       ${whereClause}
       ORDER BY create_time DESC
       LIMIT ? OFFSET ?`,
      [...params, pageSize, offset],
    );
    const total = Number(countRows[0]?.total || 0);
    return {
      rows,
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

  if (mode === 'replace' && !confirmFullReplace) {
    throw new Error('全量覆盖导入必须显式确认');
  }

  return await withMysqlConnection(async (connection) => {
    await connection.beginTransaction();
    try {
      if (mode === 'replace') {
        await connection.execute('DELETE FROM fact_soil_moisture');
      }

      const loadedRows = await insertFactRows(connection, parsed.records, {
        ignoreDuplicates: mode === 'incremental',
      });

      await refreshGeneratedRegionAliasesFromFacts(connection);
      await connection.commit();

      return {
        filename,
        mode,
        raw_rows: parsed.raw_rows,
        loaded_rows: loadedRows,
        invalid_rows: parsed.invalid_rows?.length ?? 0,
      };
    } catch (error) {
      await connection.rollback();
      throw error;
    }
  });
}

export async function patchSoilRecord(id, field, value) {
  return await withMysqlConnection(async (connection) => {
    const editable = new Set([
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
    ]);
    if (!editable.has(field)) {
      throw new Error('当前字段不允许通过后台修改');
    }

    await connection.execute(`UPDATE fact_soil_moisture SET ${field} = ? WHERE id = ?`, [value, id]);
    await refreshGeneratedRegionAliasesFromFacts(connection);

    const [rows] = await connection.execute(
      `${SELECT_FACT_SQL} WHERE id = ? LIMIT 1`,
      [id],
    );
    return {
      id,
      field,
      new_value: value,
      record: rows[0] || null,
    };
  });
}

export async function removeSoilRecords(ids) {
  return await withMysqlConnection(async (connection) => {
    if (ids.length === 0) return { deleted_count: 0 };
    const placeholders = ids.map(() => '?').join(', ');
    const [result] = await connection.execute(
      `DELETE FROM fact_soil_moisture WHERE id IN (${placeholders})`,
      ids,
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
