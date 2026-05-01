const RAW_SOIL_FIELDS = [
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
];

const RAW_SOIL_FIELD_SET = new Set(RAW_SOIL_FIELDS);

const DERIVED_KEYS = new Set([
  'entity_key',
  'soil_status',
  'warning_level',
  'risk_score',
  'display_label',
  'rule_version',
  'alert_count',
  'avg_risk_score',
  'max_risk_score',
  'winner_basis',
  'status_counts',
  'top_alert_regions',
]);

const LEGACY_BLOCK_KEYS = new Set([
  'alert_records_snapshot_id',
  'focus_devices_snapshot_id',
]);

const GROUP_METRIC_FIELDS = ['alert_device_count', 'alert_record_count', 'latest_alert_time'];
const CARD_META_FIELDS = ['count', 'measure', 'data_focus', 'field_mode', 'field', 'fields', 'values', 'aggregation', 'value', 'metric', 'compare_mode', 'winner', 'left_value', 'right_value'];

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stripDerivedKeysDeep(value) {
  if (Array.isArray(value)) {
    return value.map((item) => stripDerivedKeysDeep(item));
  }
  if (!isPlainObject(value)) {
    return value;
  }
  const next = {};
  for (const [key, nestedValue] of Object.entries(value)) {
    if (DERIVED_KEYS.has(key) || LEGACY_BLOCK_KEYS.has(key)) {
      continue;
    }
    next[key] = stripDerivedKeysDeep(nestedValue);
  }
  return next;
}

function parseLegacyGroupKey(groupKey) {
  const label = typeof groupKey === 'string' ? groupKey.trim() : '';
  if (!label) {
    return {};
  }
  if (label.includes('-')) {
    const [city, county] = label.split('-', 2);
    return {
      ...(city ? { city } : {}),
      ...(county ? { county } : {}),
    };
  }
  if (label.endsWith('市')) {
    return { city: label };
  }
  return { county: label };
}

function sanitizeSnapshotPayload(value) {
  if (!isPlainObject(value)) {
    return value;
  }
  const cleaned = stripDerivedKeysDeep(value);
  const next = {};
  for (const field of RAW_SOIL_FIELDS) {
    if (field in cleaned) {
      next[field] = cleaned[field];
    }
  }
  if (!('create_time' in next) && typeof cleaned.latest_create_time === 'string' && cleaned.latest_create_time.trim()) {
    next.create_time = cleaned.latest_create_time.trim();
  }
  return next;
}

function sanitizeRawRows(rows) {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row) => sanitizeSnapshotPayload(row))
    .filter((row) => isPlainObject(row) && Object.keys(row).length > 0);
}

function sanitizeRegionRows(rows) {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row) => {
      if (!isPlainObject(row)) {
        return null;
      }
      const cleaned = stripDerivedKeysDeep(row);
      const next = {};
      if (typeof cleaned.city === 'string' && cleaned.city.trim()) {
        next.city = cleaned.city.trim();
      }
      if (typeof cleaned.county === 'string' && cleaned.county.trim()) {
        next.county = cleaned.county.trim();
      }
      for (const field of GROUP_METRIC_FIELDS) {
        if (field in cleaned) {
          next[field] = cleaned[field];
        }
      }
      return Object.keys(next).length > 0 ? next : null;
    })
    .filter(Boolean);
}

function sanitizeGroupRows(rows, groupBy) {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row) => {
      if (!isPlainObject(row)) {
        return null;
      }
      const cleaned = stripDerivedKeysDeep(row);
      const legacyParts = parseLegacyGroupKey(cleaned.group_key);
      const city = typeof cleaned.city === 'string' && cleaned.city.trim() ? cleaned.city.trim() : legacyParts.city;
      const county = typeof cleaned.county === 'string' && cleaned.county.trim() ? cleaned.county.trim() : legacyParts.county;
      if (groupBy === 'city') {
        return city ? { city } : null;
      }
      if (groupBy === 'county') {
        const next = {};
        if (city) next.city = city;
        if (county) next.county = county;
        return Object.keys(next).length > 0 ? next : null;
      }
      const next = {};
      if (city) next.city = city;
      if (county) next.county = county;
      return Object.keys(next).length > 0 ? next : null;
    })
    .filter(Boolean);
}

function sanitizeColumns(columns) {
  if (!Array.isArray(columns)) {
    return [];
  }
  const normalized = [];
  for (const column of columns) {
    if (typeof column !== 'string') {
      continue;
    }
    if (column === 'latest_create_time') {
      normalized.push('create_time');
      continue;
    }
    if (RAW_SOIL_FIELD_SET.has(column) || GROUP_METRIC_FIELDS.includes(column)) {
      normalized.push(column);
    }
  }
  return Array.from(new Set(normalized));
}

function inferColumnsFromRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return [];
  }
  return RAW_SOIL_FIELDS.filter((field) => rows.some((row) => isPlainObject(row) && field in row));
}

function sanitizeTableColumns(columns, rows) {
  const cleanedColumns = sanitizeColumns(columns);
  return cleanedColumns.length > 0 ? cleanedColumns : inferColumnsFromRows(rows);
}

const TABLE_BLOCK_SANITIZERS = {
  list_table(cleaned) {
    cleaned.rows = sanitizeRawRows(cleaned.rows);
    cleaned.columns = sanitizeTableColumns(cleaned.columns, cleaned.rows);
    return cleaned;
  },
  group_table(cleaned) {
    cleaned.rows = sanitizeGroupRows(cleaned.rows, cleaned.group_by);
    cleaned.columns = sanitizeTableColumns(cleaned.columns, cleaned.rows);
    return cleaned;
  },
};

function sanitizeTurnBlock(block) {
  if (!isPlainObject(block)) {
    return block;
  }
  if (block.block_type === 'rule_card' || block.block_type === 'template_card') {
    return { ...block };
  }
  const cleaned = stripDerivedKeysDeep(block);
  if (cleaned.block_type === 'summary_card') {
    delete cleaned.metrics;
    if (Array.isArray(cleaned.top_regions)) {
      cleaned.top_regions = sanitizeRegionRows(cleaned.top_regions);
    }
    return cleaned;
  }
  if (cleaned.block_type === 'detail_card') {
    delete cleaned.metrics;
    if (isPlainObject(cleaned.latest_record)) {
      cleaned.latest_record = sanitizeSnapshotPayload(cleaned.latest_record);
    }
    return cleaned;
  }
  if (cleaned.block_type === 'count_card' || cleaned.block_type === 'field_card') {
    for (const field of CARD_META_FIELDS) {
      if (field in block) {
        cleaned[field] = stripDerivedKeysDeep(block[field]);
      }
    }
    return cleaned;
  }
  if (typeof cleaned.block_type === 'string' && TABLE_BLOCK_SANITIZERS[cleaned.block_type]) {
    return TABLE_BLOCK_SANITIZERS[cleaned.block_type](cleaned);
  }
  if (cleaned.block_type === 'compare_card') {
    delete cleaned.metrics;
    for (const field of CARD_META_FIELDS) {
      if (field in block) {
        cleaned[field] = stripDerivedKeysDeep(block[field]);
      }
    }
    cleaned.rows = Array.isArray(cleaned.rows) ? stripDerivedKeysDeep(cleaned.rows) : [];
    cleaned.columns = Array.isArray(cleaned.columns) ? cleaned.columns.filter((item) => typeof item === 'string') : [];
    return cleaned;
  }
  return cleaned;
}

export function sanitizeTurnBlocks(blocks) {
  return Array.isArray(blocks) ? blocks.map((block) => sanitizeTurnBlock(block)) : [];
}

export function sanitizeExecutedResult(value, { queryType = '' } = {}) {
  if (queryType === 'rule' || queryType === 'template') {
    return value;
  }
  if (!isPlainObject(value)) {
    return value;
  }
  const cleaned = stripDerivedKeysDeep(value);
  delete cleaned.metrics;
  if (Array.isArray(cleaned.top_regions)) {
    cleaned.top_regions = sanitizeRegionRows(cleaned.top_regions);
  }
  if (isPlainObject(cleaned.latest_record)) {
    cleaned.latest_record = sanitizeSnapshotPayload(cleaned.latest_record);
  }
  if (Array.isArray(cleaned.rows)) {
    cleaned.rows =
      queryType === 'group'
        ? sanitizeGroupRows(cleaned.rows, cleaned.group_by)
        : sanitizeGroupRows(cleaned.rows, 'region').length > 0 && cleaned.rows.some((row) => isPlainObject(row) && 'group_key' in row)
          ? sanitizeGroupRows(cleaned.rows, cleaned.group_by || 'region')
          : sanitizeRawRows(cleaned.rows);
  }
  if (Array.isArray(cleaned.items)) {
    cleaned.items = sanitizeRawRows(cleaned.items);
  }
  if (Array.isArray(cleaned.records)) {
    cleaned.records = sanitizeRawRows(cleaned.records);
  }
  return cleaned;
}

export { sanitizeSnapshotPayload };
