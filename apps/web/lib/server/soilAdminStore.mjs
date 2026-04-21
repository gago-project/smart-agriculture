const defaultRecords = [
  {
    record_id: 'd2d096f5-fc0c-45d4-a0d5-2064fb527c70',
    device_sn: 'SNS00204333',
    city_name: '南通市',
    county_name: '如东县',
    town_name: '',
    device_name: '土壤墒情仪-04333',
    sample_time: '2026-04-20 00:00:00',
    water20cm: 83.18,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 20.3,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    latitude: 32.328056,
    longitude: 120.974167,
    source_file: '土壤墒情仪数据(2).xlsx',
    source_sheet: 'Sheet1',
    source_row: 2,
  },
  {
    record_id: 'f8de2c8c-871a-4895-aab4-9501c2b02e94',
    device_sn: 'SNS00204334',
    city_name: '南通市',
    county_name: '如东县',
    town_name: '',
    device_name: '土壤墒情仪-04334',
    sample_time: '2026-04-20 00:00:00',
    water20cm: 50.4,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 18.8,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    latitude: 32.301111,
    longitude: 121.117778,
    source_file: '土壤墒情仪数据(2).xlsx',
    source_sheet: 'Sheet1',
    source_row: 3,
  },
  {
    record_id: '5dca6d11-4cb1-401d-95f7-d3dff825f7b5',
    device_sn: 'SNS00213807',
    city_name: '镇江市',
    county_name: '镇江经开区',
    town_name: '',
    device_name: '镇江经开区墒情仪',
    sample_time: '2026-04-20 00:00:00',
    water20cm: 41.2,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 19.8,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    latitude: 32.1458,
    longitude: 119.5623,
    source_file: '土壤墒情仪数据(2).xlsx',
    source_sheet: 'Sheet1',
    source_row: 21,
  },
  {
    record_id: '3998f34d-18d8-4aef-9bd5-88973293427c',
    device_sn: 'SNS00204418',
    city_name: '淮安市',
    county_name: '涟水县',
    town_name: '',
    device_name: '土壤墒情仪-04418',
    sample_time: '2026-04-20 00:00:00',
    water20cm: 43.37,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 21.75,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    latitude: 33.722,
    longitude: 119.188,
    source_file: '土壤墒情仪数据(2).xlsx',
    source_sheet: 'Sheet1',
    source_row: 16,
  },
];

const defaultRules = [
  {
    rule_id: 'soil_warning_v1',
    rule_name: '墒情预警规则V1',
    rule_type: 'soil_warning',
    rule_definition_json: JSON.stringify({
      document_name: '江苏省农业农村指挥调度平台预警规则及发布模版.pdf',
      soil_warning_v1: [
        { rule_name: '表层重旱预警', condition: 'water20cm < 50', warning_level: 'heavy_drought' },
        { rule_name: '表层涝渍预警', condition: 'water20cm >= 150', warning_level: 'waterlogging' },
        { rule_name: '设备故障预警', condition: 'water20cm = 0 and t20cm = 0', warning_level: 'device_fault' },
      ],
      if_not_triggered: '仍可按模板输出当前监测结果，但需明确标注为未达到预警条件',
    }, null, 2),
    enabled: true,
  },
];

const defaultTemplates = [
  {
    template_id: 'soil_warning_template_v1',
    template_name: '墒情预警模板V1',
    render_mode: 'strict',
    template_text: '{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city_name}} {{county_name}} SN 编号 {{device_sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请相关主体关注！',
  },
];

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function classifySoilAnomaly(water20cm) {
  const numeric = toNumber(water20cm);
  if (numeric === null) {
    return { soil_anomaly_type: 'unknown', soil_anomaly_score: 0 };
  }
  if (numeric < 50) {
    return { soil_anomaly_type: 'low', soil_anomaly_score: Number((50 - numeric).toFixed(2)) };
  }
  if (numeric >= 150) {
    return { soil_anomaly_type: 'high', soil_anomaly_score: Number((numeric - 150).toFixed(2)) };
  }
  return { soil_anomaly_type: 'normal', soil_anomaly_score: Number(Math.abs(100 - numeric).toFixed(2)) };
}

export function normalizeRecord(record) {
  const anomaly = classifySoilAnomaly(record.water20cm);
  return {
    town_name: '',
    device_name: record.device_name || '',
    water20cm: null,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: null,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    latitude: null,
    longitude: null,
    source_file: '',
    source_sheet: '',
    source_row: null,
    ...record,
    ...anomaly,
  };
}

export function createDefaultAdminState() {
  return {
    records: defaultRecords.map(normalizeRecord),
    rules: defaultRules.map((item) => ({ ...item })),
    templates: defaultTemplates.map((item) => ({ ...item })),
  };
}

export function querySoilRecords(records, query) {
  const page = Math.max(1, Number(query.page || 1));
  const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 50)));
  const cityName = String(query.city_name || '').trim();
  const countyName = String(query.county_name || '').trim();
  const deviceSn = String(query.device_sn || '').trim().toUpperCase();
  const anomalyType = String(query.soil_anomaly_type || '').trim();
  const from = String(query.sample_time_from || '').trim();
  const to = String(query.sample_time_to || '').trim();

  let filtered = [...records].map(normalizeRecord);
  if (cityName) filtered = filtered.filter((item) => String(item.city_name || '').includes(cityName));
  if (countyName) filtered = filtered.filter((item) => String(item.county_name || '').includes(countyName));
  if (deviceSn) filtered = filtered.filter((item) => String(item.device_sn || '').toUpperCase().includes(deviceSn));
  if (anomalyType) filtered = filtered.filter((item) => item.soil_anomaly_type === anomalyType);
  if (from) filtered = filtered.filter((item) => String(item.sample_time || '') >= from);
  if (to) filtered = filtered.filter((item) => String(item.sample_time || '') <= to);

  filtered.sort((left, right) => String(right.sample_time || '').localeCompare(String(left.sample_time || '')));

  const total = filtered.length;
  const totalPages = total === 0 ? 0 : Math.ceil(total / pageSize);
  const start = (page - 1) * pageSize;
  return {
    rows: filtered.slice(start, start + pageSize),
    total,
    page,
    page_size: pageSize,
    total_pages: totalPages,
  };
}

export function updateSoilRecordField(records, recordId, field, value) {
  const nextRecords = records.map((item) => {
    if (item.record_id !== recordId) return normalizeRecord(item);
    return normalizeRecord({
      ...item,
      [field]: value,
    });
  });
  const record = nextRecords.find((item) => item.record_id === recordId);
  if (!record) {
    throw new Error('没有找到要修改的墒情记录');
  }
  return { records: nextRecords, record };
}

export function deleteSoilRecords(records, recordIds) {
  const idSet = new Set(recordIds);
  const nextRecords = records.filter((item) => !idSet.has(item.record_id)).map(normalizeRecord);
  return {
    records: nextRecords,
    deleted_count: records.length - nextRecords.length,
  };
}

export function mergeImportedRecords(existingRecords, importedRecords, mode) {
  if (mode === 'replace') {
    return importedRecords.map(normalizeRecord);
  }
  const seenKeys = new Set(existingRecords.map((item) => `${item.record_id}:${item.device_sn}:${item.sample_time}`));
  const appended = [...existingRecords];
  for (const item of importedRecords.map(normalizeRecord)) {
    const key = `${item.record_id}:${item.device_sn}:${item.sample_time}`;
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      appended.push(item);
    }
  }
  return appended;
}

export function updateRuleDefinition(rules, ruleId, ruleDefinitionJson, enabled) {
  const nextRules = rules.map((item) => item.rule_id === ruleId ? {
    ...item,
    rule_definition_json: ruleDefinitionJson,
    enabled: enabled ?? item.enabled,
  } : { ...item });
  const rule = nextRules.find((item) => item.rule_id === ruleId);
  if (!rule) {
    throw new Error('没有找到要更新的规则');
  }
  return { rules: nextRules, rule };
}

export function updateTemplateText(templates, templateId, templateText) {
  const nextTemplates = templates.map((item) => item.template_id === templateId ? {
    ...item,
    template_text: templateText,
  } : { ...item });
  const template = nextTemplates.find((item) => item.template_id === templateId);
  if (!template) {
    throw new Error('没有找到要更新的模板');
  }
  return { templates: nextTemplates, template };
}
