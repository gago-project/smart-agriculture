const defaultRecords = [
  {
    id: 'd2d096f5-fc0c-45d4-a0d5-2064fb527c70',
    sn: 'SNS00204333',
    city: '南通市',
    county: '如东县',
    time: '2026-04-20 00:00:00',
    create_time: '2026-04-20 00:00:00',
    water20cm: 83.18,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 20.3,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    lat: 32.328056,
    lon: 120.974167,
  },
  {
    id: 'f8de2c8c-871a-4895-aab4-9501c2b02e94',
    sn: 'SNS00204334',
    city: '南通市',
    county: '如东县',
    time: '2026-04-20 00:00:00',
    create_time: '2026-04-20 00:00:00',
    water20cm: 50.4,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 18.8,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    lat: 32.301111,
    lon: 121.117778,
  },
  {
    id: '5dca6d11-4cb1-401d-95f7-d3dff825f7b5',
    sn: 'SNS00213807',
    city: '镇江市',
    county: '镇江经开区',
    time: '2026-04-20 00:00:00',
    create_time: '2026-04-20 00:00:00',
    water20cm: 41.2,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 19.8,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    lat: 32.1458,
    lon: 119.5623,
  },
  {
    id: '3998f34d-18d8-4aef-9bd5-88973293427c',
    sn: 'SNS00204418',
    city: '淮安市',
    county: '涟水县',
    time: '2026-04-20 00:00:00',
    create_time: '2026-04-20 00:00:00',
    water20cm: 43.37,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: 21.75,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    lat: 33.722,
    lon: 119.188,
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
    template_text: '{{year}} 年 {{month}} 月 {{day}} 日 {{hour}} 时 {{city}} {{county}} SN 编号 {{sn}} 土壤墒情仪监测到相对含水量 {{water20cm}}%，预警等级 {{warning_level}}，请相关主体关注！',
  },
];

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function normalizeRecord(record) {
  return {
    id: '',
    sn: '',
    gatewayid: '',
    sensorid: '',
    unitid: '',
    city: '',
    county: '',
    time: '',
    create_time: '',
    water20cm: null,
    water40cm: null,
    water60cm: null,
    water80cm: null,
    t20cm: null,
    t40cm: null,
    t60cm: null,
    t80cm: null,
    water20cmfieldstate: '',
    water40cmfieldstate: '',
    water60cmfieldstate: '',
    water80cmfieldstate: '',
    t20cmfieldstate: '',
    t40cmfieldstate: '',
    t60cmfieldstate: '',
    t80cmfieldstate: '',
    lat: null,
    lon: null,
    ...record,
    water20cm: toNumber(record?.water20cm),
    water40cm: toNumber(record?.water40cm),
    water60cm: toNumber(record?.water60cm),
    water80cm: toNumber(record?.water80cm),
    t20cm: toNumber(record?.t20cm),
    t40cm: toNumber(record?.t40cm),
    t60cm: toNumber(record?.t60cm),
    t80cm: toNumber(record?.t80cm),
    lat: toNumber(record?.lat),
    lon: toNumber(record?.lon),
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
  const city = String(query.city || '').trim();
  const county = String(query.county || '').trim();
  const sn = String(query.sn || '').trim().toUpperCase();
  const from = String(query.create_time_from || '').trim();
  const to = String(query.create_time_to || '').trim();

  let filtered = [...records].map(normalizeRecord);
  if (city) filtered = filtered.filter((item) => String(item.city || '').includes(city));
  if (county) filtered = filtered.filter((item) => String(item.county || '').includes(county));
  if (sn) filtered = filtered.filter((item) => String(item.sn || '').toUpperCase().includes(sn));
  if (from) filtered = filtered.filter((item) => String(item.create_time || '') >= from);
  if (to) filtered = filtered.filter((item) => String(item.create_time || '') <= to);

  filtered.sort((left, right) => String(right.create_time || '').localeCompare(String(left.create_time || '')));

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
    if (item.id !== recordId) return normalizeRecord(item);
    return normalizeRecord({
      ...item,
      [field]: value,
    });
  });
  const record = nextRecords.find((item) => item.id === recordId);
  if (!record) {
    throw new Error('没有找到要修改的墒情记录');
  }
  return { records: nextRecords, record };
}

export function deleteSoilRecords(records, recordIds) {
  const idSet = new Set(recordIds);
  const nextRecords = records.filter((item) => !idSet.has(item.id)).map(normalizeRecord);
  return {
    records: nextRecords,
    deleted_count: records.length - nextRecords.length,
  };
}

export function mergeImportedRecords(existingRecords, importedRecords, mode) {
  if (mode === 'replace') {
    return importedRecords.map(normalizeRecord);
  }
  const seenIds = new Set(existingRecords.map((item) => item.id));
  const appended = [...existingRecords];
  for (const item of importedRecords.map(normalizeRecord)) {
    if (!seenIds.has(item.id)) {
      seenIds.add(item.id);
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
