const REGION_SUFFIXES = {
  city: ['市'],
  county: ['县', '区', '市'],
};

function stripRegionSuffix(name, regionLevel) {
  const normalized = String(name || '').trim();
  for (const suffix of REGION_SUFFIXES[regionLevel] || []) {
    if (normalized.endsWith(suffix) && normalized.length > suffix.length) {
      return normalized.slice(0, -suffix.length);
    }
  }
  return normalized;
}

function pushAlias(mappingMap, aliasName, canonicalName, regionLevel, parentCityName, aliasSource = 'generated_fact') {
  const normalizedAlias = String(aliasName || '').trim();
  const normalizedCanonical = String(canonicalName || '').trim();
  if (!normalizedAlias || normalizedAlias.length < 2 || !normalizedCanonical) {
    return;
  }
  const key = JSON.stringify([
    normalizedAlias,
    normalizedCanonical,
    regionLevel,
    parentCityName || null,
  ]);
  mappingMap.set(key, {
    alias_name: normalizedAlias,
    canonical_name: normalizedCanonical,
    region_level: regionLevel,
    parent_city_name: parentCityName || null,
    alias_source: aliasSource,
    enabled: 1,
  });
}

export function buildRegionAliasRows(records) {
  const mappingMap = new Map();
  for (const record of records) {
    const cityName = String(record.city || '').trim() || null;
    const countyName = String(record.county || '').trim() || null;
    for (const [canonicalName, regionLevel, parentCityName] of [
      [cityName, 'city', null],
      [countyName, 'county', cityName],
    ]) {
      if (!canonicalName) {
        continue;
      }
      pushAlias(mappingMap, canonicalName, canonicalName, regionLevel, parentCityName);
      pushAlias(
        mappingMap,
        stripRegionSuffix(canonicalName, regionLevel),
        canonicalName,
        regionLevel,
        parentCityName,
      );
    }
  }
  return [...mappingMap.values()].sort((left, right) =>
    left.region_level.localeCompare(right.region_level, 'zh-Hans-CN')
    || left.alias_name.localeCompare(right.alias_name, 'zh-Hans-CN')
    || left.canonical_name.localeCompare(right.canonical_name, 'zh-Hans-CN')
    || String(left.parent_city_name || '').localeCompare(String(right.parent_city_name || ''), 'zh-Hans-CN'));
}

function sqlValue(value) {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  return `'${String(value).replaceAll("'", "''")}'`;
}

export function buildRegionAliasSeedSql(rows) {
  const generatedRows = rows.filter((row) => row.alias_source === 'generated_fact');
  const valuesSql = generatedRows.map((row) =>
    `(${sqlValue(row.alias_name)}, ${sqlValue(row.canonical_name)}, ${sqlValue(row.region_level)}, ${sqlValue(row.parent_city_name)}, ${sqlValue(row.alias_source)}, ${row.enabled ?? 1}, '2026-04-22 00:00:00', '2026-04-22 00:00:00')`).join(',\n');
  return [
    '-- BEGIN GENERATED REGION_ALIAS SEED',
    "DELETE FROM region_alias WHERE alias_source = 'generated_fact';",
    'INSERT INTO region_alias (alias_name, canonical_name, region_level, parent_city_name, alias_source, enabled, created_at, updated_at) VALUES',
    valuesSql,
    'ON DUPLICATE KEY UPDATE',
    '  parent_city_name = VALUES(parent_city_name),',
    '  alias_source = VALUES(alias_source),',
    '  enabled = VALUES(enabled),',
    '  updated_at = VALUES(updated_at);',
    '-- END GENERATED REGION_ALIAS SEED',
  ].join('\n');
}

export async function upsertRegionAliasRows(connection, rows) {
  const generatedRows = rows.filter((row) => row.alias_source === 'generated_fact');
  await connection.execute("DELETE FROM region_alias WHERE alias_source = 'generated_fact'");
  if (generatedRows.length === 0) {
    return 0;
  }
  const columns = [
    'alias_name',
    'canonical_name',
    'region_level',
    'parent_city_name',
    'alias_source',
    'enabled',
    'created_at',
    'updated_at',
  ];
  const values = generatedRows.flatMap((row) => [
    row.alias_name,
    row.canonical_name,
    row.region_level,
    row.parent_city_name,
    row.alias_source,
    row.enabled ?? 1,
    '2026-04-22 00:00:00',
    '2026-04-22 00:00:00',
  ]);
  const placeholders = generatedRows.map(() => `(${columns.map(() => '?').join(', ')})`).join(', ');
  await connection.execute(
    `INSERT INTO region_alias (${columns.join(', ')}) VALUES ${placeholders}
     ON DUPLICATE KEY UPDATE
       parent_city_name = VALUES(parent_city_name),
       alias_source = VALUES(alias_source),
       enabled = VALUES(enabled),
       updated_at = VALUES(updated_at)`,
    values,
  );
  return generatedRows.length;
}

export async function refreshGeneratedRegionAliasesFromFacts(connection) {
  const [rows] = await connection.execute(
    `SELECT DISTINCT city, county
     FROM fact_soil_moisture
     WHERE city IS NOT NULL OR county IS NOT NULL`,
  );
  const aliasRows = buildRegionAliasRows(rows);
  const aliasCount = await upsertRegionAliasRows(connection, aliasRows);
  return {
    alias_rows: aliasCount,
    source_rows: rows.length,
  };
}
