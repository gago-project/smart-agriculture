import { withMysqlConnection } from '../lib/server/mysql.mjs';
import { buildRegionAliasRows, buildRegionAliasSeedSql } from '../lib/server/regionAliasSeed.mjs';

// Generate the static `region_alias` seed block, including `alias_source`, from current local MySQL facts.
async function loadFactRegionRecords() {
  return await withMysqlConnection(async (connection) => {
    const [rows] = await connection.execute(
      `SELECT DISTINCT city_name, county_name, town_name
       FROM fact_soil_moisture
       WHERE city_name IS NOT NULL OR county_name IS NOT NULL OR town_name IS NOT NULL`,
    );
    return rows;
  });
}

const rows = buildRegionAliasRows(await loadFactRegionRecords());
process.stdout.write(`${buildRegionAliasSeedSql(rows)}\n`);
