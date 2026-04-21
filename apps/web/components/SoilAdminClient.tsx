'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  bulkDeleteSoilRecords,
  deleteSoilRecord,
  fetchRuleConfig,
  fetchSoilRecords,
  type RuleConfig,
  type SoilRecord,
  type SoilRecordPage,
  type TemplateConfig,
  updateRuleConfig,
  updateSoilRecordField,
  uploadSoilExcel,
} from '../lib/client/soilAdminApi';

const PAGE_SIZE = 20;

const EDITABLE_FIELDS = [
  'city_name',
  'county_name',
  'town_name',
  'device_name',
  'longitude',
  'latitude',
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  'soil_anomaly_type',
  'soil_anomaly_score',
] as const;

const EMPTY_PAGE: SoilRecordPage = { rows: [], total: 0, page: 1, page_size: PAGE_SIZE, total_pages: 0 };

function compactFilters(filters: Record<string, string>) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim() !== ''));
}

function valueOf(record: SoilRecord, field: string) {
  const value = record[field];
  return value === null || value === undefined ? '' : String(value);
}

export function SoilAdminClient() {
  const [filters, setFilters] = useState({
    city_name: '',
    county_name: '',
    device_sn: '',
    soil_anomaly_type: '',
    sample_time_from: '',
    sample_time_to: '',
  });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<SoilRecordPage>(EMPTY_PAGE);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editFields, setEditFields] = useState<Record<string, string>>({});
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMode, setUploadMode] = useState<'incremental' | 'replace'>('incremental');
  const [rules, setRules] = useState<RuleConfig[]>([]);
  const [templates, setTemplates] = useState<TemplateConfig[]>([]);
  const [draftRules, setDraftRules] = useState<Record<string, string>>({});
  const [draftTemplates, setDraftTemplates] = useState<Record<string, string>>({});
  const [draftEnabled, setDraftEnabled] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const loadRecords = useCallback(async (nextPage: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchSoilRecords({ page: nextPage, page_size: PAGE_SIZE, ...compactFilters(filters) });
      setData(result);
      setPage(result.page);
      setSelectedIds([]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '墒情数据加载失败');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  const loadRuleConfig = useCallback(async () => {
    try {
      const result = await fetchRuleConfig();
      setRules(result.rules);
      setTemplates(result.templates);
      setDraftRules(Object.fromEntries(result.rules.map((item) => [item.rule_id, item.rule_definition_json])));
      setDraftEnabled(Object.fromEntries(result.rules.map((item) => [item.rule_id, Boolean(item.enabled)])));
      setDraftTemplates(Object.fromEntries(result.templates.map((item) => [item.template_id, item.template_text])));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '规则配置加载失败');
    }
  }, []);

  useEffect(() => {
    void loadRecords(1);
    void loadRuleConfig();
  }, [loadRecords, loadRuleConfig]);

  function updateFilter(field: keyof typeof filters, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  async function refreshCurrentPage() {
    await loadRecords(page);
  }

  async function handleUpload() {
    if (!uploadFile) {
      setError('请先选择 Excel 文件');
      return;
    }
    if (uploadMode === 'replace') {
      const confirmed = window.confirm('全量覆盖将替换当前墒情记录，确认继续吗？');
      if (!confirmed) return;
    }
    setError(null);
    const result = await uploadSoilExcel({
      file: uploadFile,
      mode: uploadMode,
      confirm_full_replace: uploadMode === 'replace',
    });
    setMessage(`上传完成：读取 ${result.raw_rows} 行，写入 ${result.loaded_rows} 行`);
    await loadRecords(1);
  }

  async function handleEdit(record: SoilRecord) {
    const field = editFields[record.record_id] || 'city_name';
    const nextValue = editValues[record.record_id] ?? valueOf(record, field);
    const confirmed = window.confirm(`确认修改 ${record.record_id} 的 ${field}：${valueOf(record, field)} -> ${nextValue}？`);
    if (!confirmed) return;
    const result = await updateSoilRecordField(record.record_id, field, nextValue);
    setMessage(`已修改 ${result.record_id} 的 ${field}`);
    await refreshCurrentPage();
  }

  async function handleDelete(record: SoilRecord) {
    const confirmed = window.confirm(`确认删除记录 ${record.record_id}？设备：${record.device_sn}，时间：${record.sample_time}`);
    if (!confirmed) return;
    const result = await deleteSoilRecord(record.record_id);
    setMessage(`已删除 ${result.deleted_count} 条记录`);
    await refreshCurrentPage();
  }

  async function handleBulkDelete() {
    if (selectedIds.length === 0) {
      setError('请先选择要删除的记录');
      return;
    }
    const confirmed = window.confirm(`确认删除选中的 ${selectedIds.length} 条墒情记录？`);
    if (!confirmed) return;
    const result = await bulkDeleteSoilRecords(selectedIds);
    setMessage(`已删除 ${result.deleted_count} 条记录`);
    await refreshCurrentPage();
  }

  async function handleSaveRule(ruleId: string) {
    const result = await updateRuleConfig({
      rule_id: ruleId,
      rule_definition_json: draftRules[ruleId] || '',
      enabled: draftEnabled[ruleId],
    });
    setRules(result.rules);
    setTemplates(result.templates);
    setMessage(`规则 ${ruleId} 已更新`);
  }

  async function handleSaveTemplate(templateId: string) {
    const result = await updateRuleConfig({
      template_id: templateId,
      template_text: draftTemplates[templateId] || '',
    });
    setRules(result.rules);
    setTemplates(result.templates);
    setMessage(`模板 ${templateId} 已更新`);
  }

  return (
    <main className="page">
      <section className="hero">
        <span className="badge">Admin Console</span>
        <h1>墒情导入与规则管理</h1>
        <p>这里接管 Excel 导入、服务端分页查询、单条/批量删除、字段修正，以及墒情规则与模板维护。当前优先走 Next 后端；MySQL 不可用时自动降级到本地运行时数据。</p>
      </section>

      {message ? <div className="admin-message success">{message}</div> : null}
      {error ? <div className="admin-message error">{error}</div> : null}

      <section className="admin-grid">
        <div className="admin-column">
          <div className="card admin-card">
            <h2>Excel 导入</h2>
            <div className="admin-form">
              <label>
                上传 Excel
                <input className="input" type="file" accept=".xlsx" onChange={(event) => setUploadFile(event.currentTarget.files?.[0] ?? null)} />
              </label>
              <label>
                上传模式
                <select className="input" value={uploadMode} onChange={(event) => setUploadMode(event.target.value as 'incremental' | 'replace')}>
                  <option value="incremental">增量上传</option>
                  <option value="replace">全量覆盖</option>
                </select>
              </label>
              <button className="button" type="button" onClick={() => void handleUpload()}>开始上传</button>
            </div>
          </div>

          <div className="card admin-card">
            <div className="admin-toolbar">
              <h2>墒情记录</h2>
              <button className="button secondary" type="button" onClick={() => void handleBulkDelete()} disabled={selectedIds.length === 0}>删除选中</button>
            </div>
            <div className="admin-filters">
              <input className="input" value={filters.city_name} onChange={(event) => updateFilter('city_name', event.target.value)} placeholder="城市" />
              <input className="input" value={filters.county_name} onChange={(event) => updateFilter('county_name', event.target.value)} placeholder="区县" />
              <input className="input" value={filters.device_sn} onChange={(event) => updateFilter('device_sn', event.target.value)} placeholder="设备 SN" />
              <select className="input" value={filters.soil_anomaly_type} onChange={(event) => updateFilter('soil_anomaly_type', event.target.value)}>
                <option value="">全部异常类型</option>
                <option value="low">低墒</option>
                <option value="high">高墒</option>
                <option value="normal">正常</option>
                <option value="unknown">未知</option>
              </select>
              <input className="input" value={filters.sample_time_from} onChange={(event) => updateFilter('sample_time_from', event.target.value)} placeholder="开始时间" />
              <input className="input" value={filters.sample_time_to} onChange={(event) => updateFilter('sample_time_to', event.target.value)} placeholder="结束时间" />
              <button className="button" type="button" onClick={() => void loadRecords(1)} disabled={isLoading}>查询</button>
            </div>
            <div className="admin-pagination">
              <span>共 {data.total} 条，第 {data.total_pages === 0 ? 0 : data.page} / {data.total_pages} 页</span>
              <div className="actions">
                <button className="button secondary" type="button" onClick={() => void loadRecords(Math.max(1, page - 1))} disabled={page <= 1 || isLoading}>上一页</button>
                <button className="button secondary" type="button" onClick={() => void loadRecords(page + 1)} disabled={page >= data.total_pages || isLoading}>下一页</button>
              </div>
            </div>
            <div className="table-wrap">
              <table className="table admin-table">
                <thead>
                  <tr>
                    <th>选中</th>
                    <th>设备</th>
                    <th>地区</th>
                    <th>采样时间</th>
                    <th>20cm</th>
                    <th>异常</th>
                    <th>来源</th>
                    <th>字段修改</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((record) => {
                    const field = editFields[record.record_id] || 'city_name';
                    const nextValue = editValues[record.record_id] ?? valueOf(record, field);
                    return (
                      <tr key={record.record_id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedSet.has(record.record_id)}
                            onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, record.record_id] : current.filter((item) => item !== record.record_id))}
                          />
                        </td>
                        <td>{record.device_sn}</td>
                        <td>{[record.city_name, record.county_name, record.town_name].filter(Boolean).join(' / ')}</td>
                        <td>{record.sample_time}</td>
                        <td>{record.water20cm ?? '-'}</td>
                        <td>{record.soil_anomaly_type} / {record.soil_anomaly_score}</td>
                        <td>{record.source_file || '-'}</td>
                        <td>
                          <div className="edit-inline">
                            <select className="input" value={field} onChange={(event) => {
                              const nextField = event.target.value;
                              setEditFields((current) => ({ ...current, [record.record_id]: nextField }));
                              setEditValues((current) => ({ ...current, [record.record_id]: valueOf(record, nextField) }));
                            }}>
                              {EDITABLE_FIELDS.map((item) => <option key={item} value={item}>{item}</option>)}
                            </select>
                            <input className="input" value={nextValue} onChange={(event) => setEditValues((current) => ({ ...current, [record.record_id]: event.target.value }))} />
                            <button className="button secondary" type="button" onClick={() => void handleEdit(record)}>修改</button>
                          </div>
                        </td>
                        <td>
                          <button className="button secondary danger" type="button" onClick={() => void handleDelete(record)}>删除</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="admin-column">
          <div className="card admin-card">
            <h2>规则管理</h2>
            <div className="config-stack">
              {rules.map((rule) => (
                <div className="config-item" key={rule.rule_id}>
                  <div className="config-head">
                    <div>
                      <strong>{rule.rule_name}</strong>
                      <p>{rule.rule_id} · {rule.rule_type}</p>
                    </div>
                    <label className="switch-inline">
                      <input
                        type="checkbox"
                        checked={draftEnabled[rule.rule_id] ?? Boolean(rule.enabled)}
                        onChange={(event) => setDraftEnabled((current) => ({ ...current, [rule.rule_id]: event.target.checked }))}
                      />
                      启用
                    </label>
                  </div>
                  <textarea
                    value={draftRules[rule.rule_id] ?? rule.rule_definition_json}
                    onChange={(event) => setDraftRules((current) => ({ ...current, [rule.rule_id]: event.target.value }))}
                  />
                  <button className="button" type="button" onClick={() => void handleSaveRule(rule.rule_id)}>保存规则</button>
                </div>
              ))}
            </div>
          </div>

          <div className="card admin-card">
            <h2>模板管理</h2>
            <div className="config-stack">
              {templates.map((template) => (
                <div className="config-item" key={template.template_id}>
                  <div className="config-head">
                    <div>
                      <strong>{template.template_name}</strong>
                      <p>{template.template_id} · {template.render_mode}</p>
                    </div>
                  </div>
                  <textarea
                    value={draftTemplates[template.template_id] ?? template.template_text}
                    onChange={(event) => setDraftTemplates((current) => ({ ...current, [template.template_id]: event.target.value }))}
                  />
                  <button className="button" type="button" onClick={() => void handleSaveTemplate(template.template_id)}>保存模板</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
