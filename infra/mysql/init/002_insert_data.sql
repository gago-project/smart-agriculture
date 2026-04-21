-- Business bootstrap data for Smart Agriculture.
--
-- Docker MySQL executes this file after `001_init_tables.sql`.  Keep this
-- file limited to non-secret business data: import batch metadata, soil rules,
-- warning templates, and soil fact rows.  Authentication users and password
-- hashes must stay in local-only files outside this init directory.

USE smart_agriculture;

INSERT INTO etl_import_batch (
  batch_id, source_name, source_file, started_at, finished_at, status, raw_row_count, loaded_row_count, note
) VALUES (
  '11111111-1111-1111-1111-111111111111',
  '墒情导入',
  '土壤墒情仪数据(2).xlsx',
  '2026-04-20 00:00:00',
  '2026-04-20 00:05:00',
  'success',
  22,
  22,
  NULL
) ON DUPLICATE KEY UPDATE
  source_name = VALUES(source_name),
  source_file = VALUES(source_file),
  finished_at = VALUES(finished_at),
  status = VALUES(status),
  raw_row_count = VALUES(raw_row_count),
  loaded_row_count = VALUES(loaded_row_count),
  note = VALUES(note);

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
  '{"document_name":"江苏省农业农村指挥调度平台预警规则及发布模版.pdf","priority_semantics":"smaller_number_higher_priority","final_status_mode":"single_final_status","allow_multi_match_candidates":true,"rules":[{"rule_name":"表层重旱预警","condition":"water20cm < 50","warning_level":"heavy_drought","priority":10},{"rule_name":"表层涝渍预警","condition":"water20cm >= 150","warning_level":"waterlogging","priority":20},{"rule_name":"设备故障预警","condition":"water20cm = 0 and t20cm = 0","warning_level":"device_fault","priority":5}],"template":{"template_type":"soil_warning","template_text":"{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city_name}} {{county_name}} SN 编号 {{device_sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请大田/设施大棚/林果相关主体关注！"},"allow_template_output":true}',
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
  '{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city_name}} {{county_name}} SN 编号 {{device_sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请大田/设施大棚/林果相关主体关注！',
  JSON_ARRAY('year', 'month', 'day', 'hour', 'city_name', 'county_name', 'device_sn', 'water20cm', 'warning_level'),
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

INSERT INTO fact_soil_moisture (
  record_id, batch_id, device_sn, gateway_id, sensor_id, unit_id, device_name,
  city_name, county_name, town_name, sample_time, create_time,
  water20cm, water40cm, water60cm, water80cm,
  t20cm, t40cm, t60cm, t80cm,
  water20cm_field_state, water40cm_field_state, water60cm_field_state, water80cm_field_state,
  t20cm_field_state, t40cm_field_state, t60cm_field_state, t80cm_field_state,
  soil_anomaly_type, soil_anomaly_score, longitude, latitude,
  source_file, source_sheet, source_row
) VALUES
('d2d096f5-fc0c-45d4-a0d5-2064fb527c70','11111111-1111-1111-1111-111111111111','SNS00204333',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',83.18,NULL,NULL,NULL,20.30,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,120.974167,32.328056,'土壤墒情仪数据(2).xlsx',NULL,1),
('7bc174b7-8fae-4102-aa84-6136ac14ef4a','11111111-1111-1111-1111-111111111111','SNS00204333',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-13 00:00:00','2026-04-13 00:00:00',78.60,NULL,NULL,NULL,19.50,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,120.974167,32.328056,'土壤墒情仪数据(2).xlsx',NULL,22),
('f8de2c8c-871a-4895-aab4-9501c2b02e94','11111111-1111-1111-1111-111111111111','SNS00204334',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',50.40,NULL,NULL,NULL,18.80,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,121.117778,32.301111,'土壤墒情仪数据(2).xlsx',NULL,2),
('1688f330-8696-456f-b11f-3c1668004ebc','11111111-1111-1111-1111-111111111111','SNS00204335',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',0,NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'device_fault',100.0000,120.908889,32.298056,'土壤墒情仪数据(2).xlsx',NULL,3),
('e0deb83b-2d04-4bdc-ad9c-e123feca5032','11111111-1111-1111-1111-111111111111','SNS00204336',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',0,NULL,NULL,NULL,0,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'device_fault',100.0000,121.135114,32.442277,'土壤墒情仪数据(2).xlsx',NULL,4),
('94571d94-b35f-41e4-9b0f-1755ae407538','11111111-1111-1111-1111-111111111111','SNS00204337',NULL,NULL,NULL,NULL,'南通市','如东县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',0,NULL,NULL,NULL,22.10,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'heavy_drought',100.0000,121.151217,32.422574,'土壤墒情仪数据(2).xlsx',NULL,5),
('8422588b-ac1f-46a4-982b-ea0aa9ffda61','11111111-1111-1111-1111-111111111111','SNS00204406',NULL,NULL,NULL,NULL,'泰州市','姜堰区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',61.42,NULL,NULL,NULL,20.13,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,120.164189,32.361654,'土壤墒情仪数据(2).xlsx',NULL,6),
('054db09e-bff8-4b4b-81c6-1b70860d9dd4','11111111-1111-1111-1111-111111111111','SNS00204407',NULL,NULL,NULL,NULL,'泰州市','姜堰区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',73.69,NULL,NULL,NULL,21.75,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,120.057175,32.627725,'土壤墒情仪数据(2).xlsx',NULL,7),
('9af37b71-5330-4690-967e-39b73a78a6dc','11111111-1111-1111-1111-111111111111','SNS00204409',NULL,NULL,NULL,NULL,'淮安市','洪泽区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',73.62,NULL,NULL,NULL,21.63,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,118.808000,33.206000,'土壤墒情仪数据(2).xlsx',NULL,8),
('c8c4756a-b1aa-42f6-8e23-008c1df3eac2','11111111-1111-1111-1111-111111111111','SNS00204410',NULL,NULL,NULL,NULL,'淮安市','洪泽区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',64.31,NULL,NULL,NULL,20.88,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,118.900000,33.235000,'土壤墒情仪数据(2).xlsx',NULL,9),
('91f947f8-b20f-4c55-bc12-f8df23940d89','11111111-1111-1111-1111-111111111111','SNS00204411',NULL,NULL,NULL,NULL,'淮安市','淮安区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',122.67,NULL,NULL,NULL,21.01,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.279958,33.515167,'土壤墒情仪数据(2).xlsx',NULL,10),
('f2110afe-f7a8-40d2-9b5e-2c49950d6520','11111111-1111-1111-1111-111111111111','SNS00204412',NULL,NULL,NULL,NULL,'淮安市','淮安区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',128.26,NULL,NULL,NULL,16.61,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.282830,33.651582,'土壤墒情仪数据(2).xlsx',NULL,11),
('53e9321d-7c41-4287-a7bb-f57c4a6e67e5','11111111-1111-1111-1111-111111111111','SNS00204413',NULL,NULL,NULL,NULL,'淮安市','淮安区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',123.10,NULL,NULL,NULL,17.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.414587,33.682268,'土壤墒情仪数据(2).xlsx',NULL,12),
('c0298707-c136-4560-93aa-07c7cebfa94a','11111111-1111-1111-1111-111111111111','SNS00204414',NULL,NULL,NULL,NULL,'淮安市','淮安区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',103.39,NULL,NULL,NULL,22.06,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.370259,33.459709,'土壤墒情仪数据(2).xlsx',NULL,13),
('501388cc-211f-41ab-a1f8-e1df6f54284f','11111111-1111-1111-1111-111111111111','SNS00204415',NULL,NULL,NULL,NULL,'淮安市','涟水县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',101.54,NULL,NULL,NULL,22.38,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.297977,34.027515,'土壤墒情仪数据(2).xlsx',NULL,14),
('f6e93156-a851-4c76-87df-a28febfc4cf8','11111111-1111-1111-1111-111111111111','SNS00204416',NULL,NULL,NULL,NULL,'淮安市','涟水县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',85.66,NULL,NULL,NULL,20.31,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,119.288335,34.042366,'土壤墒情仪数据(2).xlsx',NULL,15),
('3998f34d-18d8-4aef-9bd5-88973293427c','11111111-1111-1111-1111-111111111111','SNS00204418',NULL,NULL,NULL,NULL,'淮安市','涟水县',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',43.37,NULL,NULL,NULL,21.75,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'heavy_drought',96.6300,119.188000,33.722000,'土壤墒情仪数据(2).xlsx',NULL,16),
('065db012-c06c-46cc-95b8-7fbdec0a0122','11111111-1111-1111-1111-111111111111','SNS00204419',NULL,NULL,NULL,NULL,'徐州市','邳州市',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',89.31,NULL,NULL,NULL,20.69,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,117.864100,34.247800,'土壤墒情仪数据(2).xlsx',NULL,17),
('61c09b93-0ce9-4eca-adb5-891c33a15706','11111111-1111-1111-1111-111111111111','SNS00204420',NULL,NULL,NULL,NULL,'徐州市','邳州市',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',119.57,NULL,NULL,NULL,22.00,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,117.856500,34.455900,'土壤墒情仪数据(2).xlsx',NULL,18),
('2ca35b23-66a0-40c2-ba53-e399dd92aff5','11111111-1111-1111-1111-111111111111','SNS00204421',NULL,NULL,NULL,NULL,'徐州市','邳州市',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',66.78,NULL,NULL,NULL,19.56,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,117.725400,34.200680,'土壤墒情仪数据(2).xlsx',NULL,19),
('9e4f74af-cbd4-44e1-a5c9-97e9ae9c9290','11111111-1111-1111-1111-111111111111','SNS00204422',NULL,NULL,NULL,NULL,'徐州市','邳州市',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',79.49,NULL,NULL,NULL,21.88,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,117.874200,34.191400,'土壤墒情仪数据(2).xlsx',NULL,20),
('5dca6d11-4cb1-401d-95f7-d3dff825f7b5','11111111-1111-1111-1111-111111111111','SNS00213807',NULL,NULL,NULL,'镇江经开区墒情仪', '镇江市','镇江经开区',NULL,'2026-04-20 00:00:00','2026-04-20 00:00:00',41.20,NULL,NULL,NULL,19.80,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'heavy_drought',98.8000,119.562300,32.145800,'土壤墒情仪数据(2).xlsx',NULL,21)
ON DUPLICATE KEY UPDATE
  sample_time = VALUES(sample_time),
  create_time = VALUES(create_time),
  water20cm = VALUES(water20cm),
  t20cm = VALUES(t20cm),
  city_name = VALUES(city_name),
  county_name = VALUES(county_name),
  soil_anomaly_type = VALUES(soil_anomaly_type),
  soil_anomaly_score = VALUES(soil_anomaly_score),
  source_file = VALUES(source_file),
  source_row = VALUES(source_row);
