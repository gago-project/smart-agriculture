import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  bulkDeleteSoilRecords,
  deleteSoilRecord,
  fetchSoilRecords,
  updateSoilRecordField,
  uploadSoilExcel,
  type SoilRecord,
  type SoilRecordPage
} from '../services/soilAdminApi';

const PAGE_SIZE = 50;

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
  'soil_anomaly_score'
];

interface Filters {
  city_name: string;
  county_name: string;
  device_sn: string;
  soil_anomaly_type: string;
  sample_time_from: string;
  sample_time_to: string;
}

const emptyPage: SoilRecordPage = {
  rows: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
  total_pages: 0
};

const initialFilters: Filters = {
  city_name: '',
  county_name: '',
  device_sn: '',
  soil_anomaly_type: '',
  sample_time_from: '',
  sample_time_to: ''
};

function valueOf(record: SoilRecord, field: string): string {
  const value = record[field];
  return value === null || value === undefined ? '' : String(value);
}

function compactFilters(filters: Filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim() !== ''));
}

export function SoilAdminPage() {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<SoilRecordPage>(emptyPage);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editFields, setEditFields] = useState<Record<string, string>>({});
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMode, setUploadMode] = useState<'incremental' | 'replace'>('incremental');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    void loadRecords(1);
  }, [loadRecords]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  function updateFilter(field: keyof Filters, value: string) {
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
      const confirmed = window.confirm('全量覆盖将清空并重建 fact_soil_moisture，确认继续吗？');
      if (!confirmed) return;
    }
    setError(null);
    const result = await uploadSoilExcel({ file: uploadFile, mode: uploadMode, confirm_full_replace: uploadMode === 'replace' });
    setMessage(`上传完成：读取 ${result.raw_rows} 行，写入 ${result.loaded_rows} 行`);
    await loadRecords(1);
  }

  async function handleEdit(record: SoilRecord) {
    const recordId = record.record_id;
    const field = editFields[recordId] || 'city_name';
    const nextValue = editValues[recordId] ?? valueOf(record, field);
    const oldValue = valueOf(record, field);
    const confirmed = window.confirm(`确认修改 ${recordId} 的 ${field}：${oldValue} -> ${nextValue}？`);
    if (!confirmed) return;
    const result = await updateSoilRecordField(recordId, field, nextValue);
    setMessage(`已修改 ${result.record_id ?? recordId} 的 ${field}`);
    await refreshCurrentPage();
  }

  async function handleDelete(record: SoilRecord) {
    const confirmed = window.confirm(`确认删除记录 ${record.record_id}？设备：${valueOf(record, 'device_sn')}，时间：${valueOf(record, 'sample_time')}`);
    if (!confirmed) return;
    const result = await deleteSoilRecord(record.record_id);
    setMessage(`已删除 ${result.deleted_count ?? 0} 条记录`);
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
    setMessage(`已删除 ${result.deleted_count ?? 0} 条记录`);
    await refreshCurrentPage();
  }

  return (
    <section className="soil-admin-page" aria-label="墒情数据管理">
      <header className="soil-admin-header">
        <div>
          <h2>墒情数据管理</h2>
          <p>支持 Excel 增量上传、全量覆盖、分页查询、单字段修改和删除。</p>
        </div>
        <button className="danger-outline" onClick={() => void handleBulkDelete()} disabled={selectedIds.length === 0}>
          删除选中
        </button>
      </header>

      {message ? <div className="admin-message success">{message}</div> : null}
      {error ? <div className="admin-message error">{error}</div> : null}

      <div className="admin-card upload-card">
        <label>
          上传 Excel
          <input aria-label="上传 Excel" type="file" accept=".xlsx" onChange={(event) => setUploadFile(event.currentTarget.files?.[0] ?? null)} />
        </label>
        <label>
          上传模式
          <select aria-label="上传模式" value={uploadMode} onChange={(event) => setUploadMode(event.target.value as 'incremental' | 'replace')}>
            <option value="incremental">增量上传（只插入不存在记录）</option>
            <option value="replace">全量覆盖</option>
          </select>
        </label>
        <button onClick={() => void handleUpload()}>开始上传</button>
      </div>

      <div className="admin-card filter-card">
        <label>
          城市
          <input aria-label="城市" value={filters.city_name} onChange={(event) => updateFilter('city_name', event.target.value)} placeholder="如：徐州市" />
        </label>
        <label>
          区县
          <input aria-label="区县" value={filters.county_name} onChange={(event) => updateFilter('county_name', event.target.value)} placeholder="如：睢宁县" />
        </label>
        <label>
          设备 SN
          <input aria-label="设备 SN" value={filters.device_sn} onChange={(event) => updateFilter('device_sn', event.target.value)} placeholder="SNS..." />
        </label>
        <label>
          异常类型
          <select aria-label="异常类型" value={filters.soil_anomaly_type} onChange={(event) => updateFilter('soil_anomaly_type', event.target.value)}>
            <option value="">全部</option>
            <option value="low">低墒</option>
            <option value="high">高墒</option>
            <option value="normal">正常</option>
            <option value="unknown">未知</option>
          </select>
        </label>
        <label>
          开始时间
          <input aria-label="开始时间" value={filters.sample_time_from} onChange={(event) => updateFilter('sample_time_from', event.target.value)} placeholder="2026-04-01 00:00:00" />
        </label>
        <label>
          结束时间
          <input aria-label="结束时间" value={filters.sample_time_to} onChange={(event) => updateFilter('sample_time_to', event.target.value)} placeholder="2026-04-15 00:00:00" />
        </label>
        <button onClick={() => void loadRecords(1)} disabled={isLoading}>查询</button>
      </div>

      <div className="admin-table-toolbar">
        <span>共 {data.total} 条，第 {data.total_pages === 0 ? 0 : data.page} / {data.total_pages} 页</span>
        <div>
          <button onClick={() => void loadRecords(Math.max(1, page - 1))} disabled={isLoading || page <= 1}>上一页</button>
          <button onClick={() => void loadRecords(page + 1)} disabled={isLoading || page >= data.total_pages}>下一页</button>
        </div>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>选择</th>
              <th>设备</th>
              <th>地区</th>
              <th>采样时间</th>
              <th>20cm水分</th>
              <th>异常</th>
              <th>来源</th>
              <th>修改单字段</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((record) => {
              const field = editFields[record.record_id] || 'city_name';
              const newValue = editValues[record.record_id] ?? valueOf(record, field);
              return (
                <tr key={record.record_id}>
                  <td>
                    <input
                      aria-label={`选择 ${record.record_id}`}
                      type="checkbox"
                      checked={selectedSet.has(record.record_id)}
                      onChange={(event) => {
                        setSelectedIds((current) => event.target.checked ? [...current, record.record_id] : current.filter((id) => id !== record.record_id));
                      }}
                    />
                  </td>
                  <td>{record.device_sn}</td>
                  <td>{[record.city_name, record.county_name, record.town_name].filter(Boolean).join(' / ')}</td>
                  <td>{record.sample_time}</td>
                  <td>{record.water20cm}</td>
                  <td>{record.soil_anomaly_type} / {record.soil_anomaly_score}</td>
                  <td>{record.source_file}</td>
                  <td>
                    <div className="edit-inline">
                      <select
                        aria-label={`修改字段 ${record.record_id}`}
                        value={field}
                        onChange={(event) => {
                          const nextField = event.target.value;
                          setEditFields((current) => ({ ...current, [record.record_id]: nextField }));
                          setEditValues((current) => ({ ...current, [record.record_id]: valueOf(record, nextField) }));
                        }}
                      >
                        {EDITABLE_FIELDS.map((item) => <option key={item} value={item}>{item}</option>)}
                      </select>
                      <input
                        aria-label={`新值 ${record.record_id}`}
                        value={newValue}
                        onChange={(event) => setEditValues((current) => ({ ...current, [record.record_id]: event.target.value }))}
                      />
                      <button aria-label={`确认修改 ${record.record_id}`} onClick={() => void handleEdit(record)}>修改</button>
                    </div>
                  </td>
                  <td>
                    <button className="danger-outline" aria-label={`删除 ${record.record_id}`} onClick={() => void handleDelete(record)}>删除</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
