-- Business bootstrap data for Smart Agriculture.
--
-- Docker MySQL executes this file after `001_init_tables.sql`. Keep this file
-- limited to non-secret business rules and warning templates. Full soil fact
-- rows live in `003_insert_soil_data.sql` so the heavy data seed can be audited
-- independently from the smaller rule/template bootstrap.

SET NAMES utf8mb4;
SET character_set_client = utf8mb4;
SET character_set_connection = utf8mb4;
SET character_set_results = utf8mb4;

USE smart_agriculture;

INSERT INTO metric_rule (
  rule_code, rule_name, rule_scope, rule_definition_json, enabled, updated_at
) VALUES
(
  'soil_anomaly_v1',
  '墒情异常分析规则V1',
  'soil_moisture',
  '{"scope":"soil_moisture","rules":[{"rule_name":"表层重旱预警","condition":"water20cm < 50","status":"heavy_drought"},{"rule_name":"表层涝渍预警","condition":"water20cm >= 150","status":"waterlogging"},{"rule_name":"设备故障预警","condition":"water20cm = 0 and t20cm = 0","status":"device_fault"}]}',
  1,
  '2026-04-20 00:00:00'
),
(
  'soil_warning_v1',
  '墒情预警规则V1',
  'soil_moisture',
  '{"document_name":"江苏省农业农村指挥调度平台预警规则及发布模版.pdf","priority_semantics":"smaller_number_higher_priority","final_status_mode":"single_final_status","allow_multi_match_candidates":true,"rules":[{"rule_name":"表层重旱预警","condition":"water20cm < 50","warning_level":"heavy_drought","priority":10},{"rule_name":"表层涝渍预警","condition":"water20cm >= 150","warning_level":"waterlogging","priority":20},{"rule_name":"设备故障预警","condition":"water20cm = 0 and t20cm = 0","warning_level":"device_fault","priority":5}],"template":{"template_type":"soil_warning","template_text":"{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city}} {{county}} SN 编号 {{sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请大田/设施大棚/林果相关主体关注！"},"allow_template_output":true}',
  1,
  '2026-04-20 00:00:00'
) ON DUPLICATE KEY UPDATE
  rule_name = VALUES(rule_name),
  rule_scope = VALUES(rule_scope),
  rule_definition_json = VALUES(rule_definition_json),
  enabled = VALUES(enabled),
  updated_at = VALUES(updated_at);

INSERT INTO warning_template (
  template_id, domain, warning_type, audience, template_name, template_text, required_fields_json, version, enabled, created_at, updated_at
) VALUES (
  'soil_warning_template_v1',
  'soil_moisture',
  'soil_warning',
  'general',
  '墒情预警模板V1',
  '{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city}} {{county}} SN 编号 {{sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请大田/设施大棚/林果相关主体关注！',
  JSON_ARRAY('year', 'month', 'day', 'hour', 'city', 'county', 'sn', 'water20cm', 'warning_level'),
  'v1',
  1,
  '2026-04-20 00:00:00',
  '2026-04-20 00:00:00'
) ON DUPLICATE KEY UPDATE
  domain = VALUES(domain),
  warning_type = VALUES(warning_type),
  audience = VALUES(audience),
  template_name = VALUES(template_name),
  template_text = VALUES(template_text),
  required_fields_json = VALUES(required_fields_json),
  version = VALUES(version),
  enabled = VALUES(enabled),
  updated_at = VALUES(updated_at);
