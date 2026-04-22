import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import {
  applySoilImportJob,
  bulkDeleteSoilRecords,
  createSoilImportPreview,
  deleteSoilRecord,
  fetchSoilImportDiff,
  fetchSoilImportJob,
  fetchSoilRecords,
  updateSoilRecordField,
  type SoilImportDiffPage,
  type SoilImportDiffRow,
  type SoilImportDiffType,
  type SoilImportJob,
  type SoilImportMode,
  type SoilImportSummary,
  type SoilRecord,
  type SoilRecordPage,
} from '../services/soilAdminApi';

const DEFAULT_PAGE_SIZE = 50;
const DIFF_PAGE_SIZE = 20;
const PAGE_SIZE_OPTIONS = [20, 50, 100];

const EDITABLE_FIELDS = [
  { key: 'city_name', label: '城市' },
  { key: 'county_name', label: '区县' },
  { key: 'town_name', label: '乡镇' },
  { key: 'device_name', label: '设备名称' },
  { key: 'longitude', label: '经度' },
  { key: 'latitude', label: '纬度' },
  { key: 'water20cm', label: '20cm 水分' },
  { key: 'water40cm', label: '40cm 水分' },
  { key: 'water60cm', label: '60cm 水分' },
  { key: 'water80cm', label: '80cm 水分' },
  { key: 't20cm', label: '20cm 温度' },
  { key: 't40cm', label: '40cm 温度' },
  { key: 't60cm', label: '60cm 温度' },
  { key: 't80cm', label: '80cm 温度' },
  { key: 'soil_anomaly_type', label: '异常类型' },
  { key: 'soil_anomaly_score', label: '异常分值' },
] as const;

type EditableField = (typeof EDITABLE_FIELDS)[number]['key'];

interface Filters {
  city_name: string;
  county_name: string;
  device_sn: string;
  soil_anomaly_type: string;
  sample_time_from: string;
  sample_time_to: string;
}

interface EditModalState {
  record: SoilRecord;
  field: EditableField;
  value: string;
}

const STATUS_LABELS: Record<string, string> = {
  previewing: '预览中',
  ready: '待确认',
  applying: '导入中',
  succeeded: '已完成',
  failed: '失败',
};

const DIFF_TYPE_LABELS: Record<SoilImportDiffType, string> = {
  all: '全部',
  create: '新增',
  update: '有差异',
  unchanged: '无变化',
  delete: '仅覆盖会删除',
  invalid: '无效',
};

const emptyPage: SoilRecordPage = {
  rows: [],
  total: 0,
  page: 1,
  page_size: DEFAULT_PAGE_SIZE,
  total_pages: 0,
};

const emptyDiffPage: SoilImportDiffPage = {
  rows: [],
  total: 0,
  page: 1,
  page_size: DIFF_PAGE_SIZE,
  total_pages: 0,
};

const initialFilters: Filters = {
  city_name: '',
  county_name: '',
  device_sn: '',
  soil_anomaly_type: '',
  sample_time_from: '',
  sample_time_to: '',
};

function compactFilters(filters: Filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim() !== ''));
}

function valueOf(record: SoilRecord, field: string): string {
  const value = record[field];
  return value === null || value === undefined ? '' : String(value);
}

function fieldLabel(field: EditableField) {
  return EDITABLE_FIELDS.find((item) => item.key === field)?.label || field;
}

function statusLabel(status?: string | null) {
  return STATUS_LABELS[status || ''] || status || '未开始';
}

function recordRegion(record: SoilRecord) {
  return [record.city_name, record.county_name, record.town_name].filter(Boolean).join(' / ') || '-';
}

function summaryNumber(summary: SoilImportSummary | null | undefined, key: keyof SoilImportSummary) {
  return Number(summary?.[key] || 0);
}

function progressText(job: SoilImportJob | null) {
  if (!job) return '';
  const action = job.status === 'applying' ? '上传中' : job.status === 'previewing' ? '预览中' : statusLabel(job.status);
  const total = job.total_rows > 0 ? job.total_rows : 0;
  return total > 0 ? `${action} ${job.processed_rows}/${total}` : action;
}

function summarizeRecord(record?: SoilRecord | null) {
  if (!record) return '-';
  return [
    record.device_sn || '-',
    recordRegion(record),
    record.sample_time || '-',
    record.water20cm === null || record.water20cm === undefined || record.water20cm === '' ? '-' : `${record.water20cm}`,
  ].join(' · ');
}

function formatFieldChanges(row: SoilImportDiffRow): string {
  const changes = row.field_changes;
  if (!changes) return '-';
  if (Object.prototype.hasOwnProperty.call(changes, 'reason')) {
    return String((changes as { reason?: string }).reason || '-');
  }
  const fieldChanges = changes as Record<string, { before: unknown; after: unknown }>;
  const keys = Object.keys(fieldChanges);
  if (keys.length === 0) return '-';
  return keys.map((key) => `${key}: ${String(fieldChanges[key]?.before ?? '-') } → ${String(fieldChanges[key]?.after ?? '-')}`).join('；');
}

export function SoilAdminPage() {
  const [draftFilters, setDraftFilters] = useState<Filters>(initialFilters);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [pageJump, setPageJump] = useState('1');
  const [data, setData] = useState<SoilRecordPage>(emptyPage);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editModal, setEditModal] = useState<EditModalState | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [importJob, setImportJob] = useState<SoilImportJob | null>(null);
  const [diffType, setDiffType] = useState<SoilImportDiffType>('all');
  const [diffPage, setDiffPage] = useState(1);
  const [diffData, setDiffData] = useState(emptyDiffPage);
  const [showReplaceConfirm, setShowReplaceConfirm] = useState(false);
  const [replaceConfirmText, setReplaceConfirmText] = useState('');
  const [isLoadingRecords, setIsLoadingRecords] = useState(false);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPreviewStarting, setIsPreviewStarting] = useState(false);
  const [isApplyStarting, setIsApplyStarting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const initialLoadedRef = useRef(false);
  const lastImportStatusRef = useRef<string | null>(null);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const currentPageIds = useMemo(() => data.rows.map((record) => record.record_id), [data.rows]);
  const allPageSelected = currentPageIds.length > 0 && currentPageIds.every((id) => selectedSet.has(id));
  const importSummary = importJob?.summary || null;
  const incrementalApplyRows = summaryNumber(importSummary, 'create_rows');
  const replaceApplyRows = summaryNumber(importSummary, 'valid_rows');

  const loadRecords = useCallback(async (nextPage: number, nextPageSize = pageSize, nextFilters = filters) => {
    setIsLoadingRecords(true);
    setError(null);
    try {
      const result = await fetchSoilRecords({
        page: nextPage,
        page_size: nextPageSize,
        ...compactFilters(nextFilters),
      });
      setData(result);
      setPageJump(String(result.page));
      setSelectedIds([]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '墒情数据加载失败');
    } finally {
      setIsLoadingRecords(false);
    }
  }, [filters, pageSize]);

  useEffect(() => {
    if (initialLoadedRef.current) {
      return;
    }
    initialLoadedRef.current = true;
    void loadRecords(1, DEFAULT_PAGE_SIZE, initialFilters);
  }, [loadRecords]);

  useEffect(() => {
    if (!importJob?.job_id) {
      lastImportStatusRef.current = null;
      return;
    }
    if (!['previewing', 'applying'].includes(importJob.status)) {
      lastImportStatusRef.current = importJob.status;
      return;
    }

    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const nextJob = await fetchSoilImportJob(importJob.job_id);
        if (cancelled) return;
        const previousStatus = lastImportStatusRef.current;
        lastImportStatusRef.current = nextJob.status;
        setImportJob(nextJob);

        if (nextJob.status === 'ready' && previousStatus !== 'ready') {
          setMessage(`预览完成：新增 ${summaryNumber(nextJob.summary, 'create_rows')} 条，存在差异 ${summaryNumber(nextJob.summary, 'update_rows')} 条。`);
        }
        if (nextJob.status === 'succeeded' && previousStatus !== 'succeeded') {
          setMessage(`导入完成：${nextJob.apply_mode === 'replace' ? '全量覆盖' : '增量添加'}已执行。`);
          void loadRecords(1, pageSize, filters);
        }
        if (nextJob.status === 'failed' && previousStatus !== 'failed') {
          setError(nextJob.error_message || '导入任务执行失败');
        }
      } catch (caughtError) {
        if (cancelled) return;
        setError(caughtError instanceof Error ? caughtError.message : '导入任务轮询失败');
      }
    }, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [filters, importJob?.job_id, importJob?.status, loadRecords, pageSize]);

  useEffect(() => {
    if (!importJob?.job_id) {
      setDiffData(emptyDiffPage);
      return;
    }
    if (!['ready', 'applying', 'succeeded'].includes(importJob.status)) {
      return;
    }

    let cancelled = false;
    const jobId = importJob.job_id;
    async function loadDiff() {
      try {
        const result = await fetchSoilImportDiff(jobId, {
          type: diffType,
          page: diffPage,
          page_size: DIFF_PAGE_SIZE,
        });
        if (!cancelled) {
          setDiffData(result);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : '导入 diff 加载失败');
        }
      }
    }

    void loadDiff();
    return () => {
      cancelled = true;
    };
  }, [diffPage, diffType, importJob?.job_id, importJob?.status]);

  function updateDraftFilter(field: keyof Filters, value: string) {
    setDraftFilters((current) => ({ ...current, [field]: value }));
  }

  async function handleSearch() {
    setFilters(draftFilters);
    await loadRecords(1, pageSize, draftFilters);
  }

  async function handleResetFilters() {
    setDraftFilters(initialFilters);
    setFilters(initialFilters);
    await loadRecords(1, pageSize, initialFilters);
  }

  async function handleChangePageSize(nextPageSize: number) {
    setPageSize(nextPageSize);
    await loadRecords(1, nextPageSize, filters);
  }

  async function handleJumpPage() {
    const nextPage = Math.max(1, Number(pageJump || '1'));
    const boundedPage = data.total_pages > 0 ? Math.min(nextPage, data.total_pages) : 1;
    await loadRecords(boundedPage, pageSize, filters);
  }

  function toggleSelectPage(checked: boolean) {
    setSelectedIds(checked ? currentPageIds : []);
  }

  function toggleSelectRecord(recordId: string, checked: boolean) {
    setSelectedIds((current) => checked ? [...new Set([...current, recordId])] : current.filter((item) => item !== recordId));
  }

  function openEditModal(record: SoilRecord, field: EditableField) {
    setEditModal({
      record,
      field,
      value: valueOf(record, field),
    });
  }

  async function handleSaveEdit() {
    if (!editModal) return;
    setIsSubmittingEdit(true);
    setError(null);
    try {
      const result = await updateSoilRecordField(editModal.record.record_id, editModal.field, editModal.value);
      setMessage(`已更新 ${fieldLabel(editModal.field)}：${editModal.record.record_id}`);
      setEditModal(null);
      if (result.record) {
        await loadRecords(data.page || 1, pageSize, filters);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '字段修改失败');
    } finally {
      setIsSubmittingEdit(false);
    }
  }

  async function handleDelete(record: SoilRecord) {
    const confirmed = window.confirm(`确认删除记录 ${record.record_id}？`);
    if (!confirmed) return;
    setIsDeleting(true);
    setError(null);
    try {
      const result = await deleteSoilRecord(record.record_id);
      setMessage(`已删除 ${result.deleted_count ?? 0} 条记录`);
      await loadRecords(Math.max(1, data.page), pageSize, filters);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '删除失败');
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleBulkDelete() {
    if (selectedIds.length === 0) {
      setError('请先选择当前页要删除的记录');
      return;
    }
    const confirmed = window.confirm(`确认删除当前页选中的 ${selectedIds.length} 条记录？`);
    if (!confirmed) return;
    setIsDeleting(true);
    setError(null);
    try {
      const result = await bulkDeleteSoilRecords(selectedIds);
      setMessage(`已删除 ${result.deleted_count ?? 0} 条记录`);
      await loadRecords(Math.max(1, data.page), pageSize, filters);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '批量删除失败');
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleStartPreview() {
    if (!uploadFile) {
      setError('请先选择 Excel 文件');
      return;
    }
    setIsPreviewStarting(true);
    setError(null);
    setMessage(null);
    try {
      const job = await createSoilImportPreview(uploadFile);
      lastImportStatusRef.current = job.status;
      setImportJob(job);
      setDiffType('all');
      setDiffPage(1);
      setDiffData(emptyDiffPage);
      setMessage(`已创建预览任务：${job.filename}`);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '预览任务创建失败');
    } finally {
      setIsPreviewStarting(false);
    }
  }

  async function handleApply(mode: SoilImportMode, confirmFullReplace: boolean) {
    if (!importJob?.job_id) {
      setError('请先生成导入预览');
      return;
    }
    setIsApplyStarting(true);
    setError(null);
    try {
      const job = await applySoilImportJob(importJob.job_id, {
        mode,
        confirm_full_replace: confirmFullReplace,
      });
      lastImportStatusRef.current = job.status;
      setImportJob(job);
      setShowReplaceConfirm(false);
      setReplaceConfirmText('');
      setMessage(mode === 'replace' ? '已开始全量覆盖' : '已开始增量添加');
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '导入启动失败');
    } finally {
      setIsApplyStarting(false);
    }
  }

  return (
    <section className="soil-admin-page" aria-label="墒情数据管理">
      <header className="soil-admin-header">
        <div>
          <h2>墒情数据管理</h2>
          <p>查询、筛选、分页、批量删除、双击字段编辑，以及 Excel 预览后导入。</p>
        </div>
        <div className="admin-toolbar-actions">
          <button className="danger-outline" onClick={() => void handleBulkDelete()} disabled={selectedIds.length === 0 || isDeleting}>
            删除选中
          </button>
          <button onClick={() => void handleSearch()} disabled={isLoadingRecords}>刷新列表</button>
        </div>
      </header>

      {message ? <div className="admin-message success">{message}</div> : null}
      {error ? <div className="admin-message error">{error}</div> : null}

      <div className="soil-admin-layout">
        <div className="admin-card upload-panel">
          <div className="admin-card-title">
            <h3>Excel 导入预览</h3>
            <span className={`admin-status-badge is-${importJob?.status || 'idle'}`}>{statusLabel(importJob?.status)}</span>
          </div>
          <div className="upload-card">
            <label>
              上传 Excel
              <input
                aria-label="上传 Excel"
                type="file"
                accept=".xlsx"
                onChange={(event) => setUploadFile(event.currentTarget.files?.[0] ?? null)}
              />
            </label>
            <label>
              当前文件
              <input value={uploadFile?.name || importJob?.filename || ''} readOnly placeholder="请选择 Excel 文件" />
            </label>
            <button onClick={() => void handleStartPreview()} disabled={!uploadFile || isPreviewStarting || importJob?.status === 'previewing' || importJob?.status === 'applying'}>
              {isPreviewStarting ? '创建中...' : '生成预览'}
            </button>
          </div>

          {importJob ? (
            <div className="admin-progress-card">
              <div className="admin-progress-header">
                <strong>{progressText(importJob)}</strong>
                <span>{importJob.filename}</span>
              </div>
              <progress value={importJob.processed_rows} max={Math.max(importJob.total_rows, 1)} />
            </div>
          ) : null}

          {importSummary ? (
            <>
              <div className="admin-summary-grid">
                <div className="admin-summary-item"><span>原始行</span><strong>{summaryNumber(importSummary, 'raw_rows')}</strong></div>
                <div className="admin-summary-item"><span>有效行</span><strong>{summaryNumber(importSummary, 'valid_rows')}</strong></div>
                <div className="admin-summary-item"><span>无效行</span><strong>{summaryNumber(importSummary, 'invalid_rows')}</strong></div>
                <div className="admin-summary-item"><span>新增</span><strong>{summaryNumber(importSummary, 'create_rows')}</strong></div>
                <div className="admin-summary-item"><span>有差异</span><strong>{summaryNumber(importSummary, 'update_rows')}</strong></div>
                <div className="admin-summary-item"><span>无变化</span><strong>{summaryNumber(importSummary, 'unchanged_rows')}</strong></div>
                <div className="admin-summary-item"><span>覆盖会删</span><strong>{summaryNumber(importSummary, 'delete_rows')}</strong></div>
              </div>
              <div className="admin-import-actions">
                <button
                  onClick={() => void handleApply('incremental', false)}
                  disabled={importJob?.status !== 'ready' || isApplyStarting}
                >
                  增量添加 {incrementalApplyRows} 条
                </button>
                <button
                  className="danger-outline"
                  onClick={() => setShowReplaceConfirm(true)}
                  disabled={importJob?.status !== 'ready' || isApplyStarting}
                >
                  全量覆盖 {replaceApplyRows} 条
                </button>
              </div>
            </>
          ) : null}

          <div className="admin-diff-panel">
            <div className="admin-card-title">
              <h3>Diff 预览</h3>
              <div className="admin-diff-toolbar">
                <select value={diffType} onChange={(event) => { setDiffType(event.target.value as SoilImportDiffType); setDiffPage(1); }} disabled={!importJob}>
                  {Object.entries(DIFF_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table admin-diff-table">
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>记录 ID</th>
                    <th>源行号</th>
                    <th>变化</th>
                    <th>导入数据</th>
                    <th>库内数据</th>
                  </tr>
                </thead>
                <tbody>
                  {diffData.rows.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="admin-empty">先生成预览，再查看 diff 样本。</td>
                    </tr>
                  ) : diffData.rows.map((row) => (
                    <tr key={row.diff_id}>
                      <td><span className={`admin-diff-tag is-${row.diff_type}`}>{DIFF_TYPE_LABELS[row.diff_type]}</span></td>
                      <td>{row.record_id || '-'}</td>
                      <td>{row.source_row || '-'}</td>
                      <td>{formatFieldChanges(row)}</td>
                      <td>{summarizeRecord(row.import_record)}</td>
                      <td>{summarizeRecord(row.db_record)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="admin-table-toolbar">
              <span>Diff 共 {diffData.total} 条，第 {diffData.total_pages === 0 ? 0 : diffData.page} / {diffData.total_pages} 页</span>
              <div>
                <button onClick={() => setDiffPage((current) => Math.max(1, current - 1))} disabled={diffPage <= 1}>上一页</button>
                <button onClick={() => setDiffPage((current) => current + 1)} disabled={diffPage >= diffData.total_pages}>下一页</button>
              </div>
            </div>
          </div>
        </div>

        <div className="admin-card filter-card">
          <div className="admin-card-title">
            <h3>查询与筛选</h3>
            <div className="admin-toolbar-actions">
              <button onClick={() => void handleSearch()} disabled={isLoadingRecords}>查询</button>
              <button onClick={() => void handleResetFilters()} disabled={isLoadingRecords}>重置</button>
            </div>
          </div>
          <label>
            城市
            <input value={draftFilters.city_name} onChange={(event) => updateDraftFilter('city_name', event.target.value)} placeholder="如：徐州市" />
          </label>
          <label>
            区县
            <input value={draftFilters.county_name} onChange={(event) => updateDraftFilter('county_name', event.target.value)} placeholder="如：睢宁县" />
          </label>
          <label>
            设备 SN
            <input value={draftFilters.device_sn} onChange={(event) => updateDraftFilter('device_sn', event.target.value)} placeholder="SNS..." />
          </label>
          <label>
            异常类型
            <select value={draftFilters.soil_anomaly_type} onChange={(event) => updateDraftFilter('soil_anomaly_type', event.target.value)}>
              <option value="">全部</option>
              <option value="low">低墒</option>
              <option value="high">高墒</option>
              <option value="normal">正常</option>
              <option value="unknown">未知</option>
            </select>
          </label>
          <label>
            开始时间
            <input value={draftFilters.sample_time_from} onChange={(event) => updateDraftFilter('sample_time_from', event.target.value)} placeholder="2026-04-01 00:00:00" />
          </label>
          <label>
            结束时间
            <input value={draftFilters.sample_time_to} onChange={(event) => updateDraftFilter('sample_time_to', event.target.value)} placeholder="2026-04-30 23:59:59" />
          </label>
        </div>

        <div className="admin-card">
          <div className="admin-card-title">
            <h3>数据列表</h3>
            <div className="admin-pagination-controls">
              <label className="admin-inline-field">
                每页
                <select value={pageSize} onChange={(event) => void handleChangePageSize(Number(event.target.value))}>
                  {PAGE_SIZE_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="admin-inline-field">
                跳页
                <input value={pageJump} onChange={(event) => setPageJump(event.target.value)} />
              </label>
              <button onClick={() => void handleJumpPage()} disabled={isLoadingRecords}>前往</button>
            </div>
          </div>

          <div className="admin-selection-bar">
            <span>当前筛选共 {data.total} 条，已选中当前页 {selectedIds.length} 条</span>
            <div className="admin-toolbar-actions">
              <button onClick={() => setSelectedIds([])} disabled={selectedIds.length === 0}>清空选择</button>
              <button className="danger-outline" onClick={() => void handleBulkDelete()} disabled={selectedIds.length === 0 || isDeleting}>
                批量删除
              </button>
            </div>
          </div>

          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="全选当前页"
                      checked={allPageSelected}
                      onChange={(event) => toggleSelectPage(event.target.checked)}
                    />
                  </th>
                  <th>设备 SN</th>
                  <th>设备名称</th>
                  <th>城市</th>
                  <th>区县</th>
                  <th>乡镇</th>
                  <th>采样时间</th>
                  <th>20cm 水分</th>
                  <th>20cm 温度</th>
                  <th>异常</th>
                  <th>来源</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.length === 0 ? (
                  <tr>
                    <td colSpan={12} className="admin-empty">暂无符合条件的数据。</td>
                  </tr>
                ) : data.rows.map((record) => (
                  <tr key={record.record_id} className={selectedSet.has(record.record_id) ? 'selected' : ''}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`选择 ${record.record_id}`}
                        checked={selectedSet.has(record.record_id)}
                        onChange={(event) => toggleSelectRecord(record.record_id, event.target.checked)}
                      />
                    </td>
                    <td>{record.device_sn}</td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 'device_name')} title="双击编辑">
                      {record.device_name || '-'}
                    </td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 'city_name')} title="双击编辑">
                      {record.city_name || '-'}
                    </td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 'county_name')} title="双击编辑">
                      {record.county_name || '-'}
                    </td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 'town_name')} title="双击编辑">
                      {record.town_name || '-'}
                    </td>
                    <td>{record.sample_time || '-'}</td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 'water20cm')} title="双击编辑">
                      {record.water20cm ?? '-'}
                    </td>
                    <td className="admin-editable-cell" onDoubleClick={() => openEditModal(record, 't20cm')} title="双击编辑">
                      {record.t20cm ?? '-'}
                    </td>
                    <td>{record.soil_anomaly_type || '-'} / {record.soil_anomaly_score ?? '-'}</td>
                    <td>{record.source_file || '-'}</td>
                    <td>
                      <button className="danger-outline" onClick={() => void handleDelete(record)} disabled={isDeleting}>
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="admin-table-toolbar">
            <span>第 {data.total_pages === 0 ? 0 : data.page} / {data.total_pages} 页</span>
            <div>
              <button onClick={() => void loadRecords(Math.max(1, data.page - 1), pageSize, filters)} disabled={isLoadingRecords || data.page <= 1}>
                上一页
              </button>
              <button onClick={() => void loadRecords(data.page + 1, pageSize, filters)} disabled={isLoadingRecords || data.page >= data.total_pages}>
                下一页
              </button>
            </div>
          </div>
        </div>
      </div>

      {editModal ? (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-label="编辑字段">
            <div className="admin-card-title">
              <h3>字段更新</h3>
              <button onClick={() => setEditModal(null)}>关闭</button>
            </div>
            <div className="admin-modal-body">
              <p><strong>记录 ID：</strong>{editModal.record.record_id}</p>
              <p><strong>设备：</strong>{editModal.record.device_sn || '-'}</p>
              <p><strong>地区：</strong>{recordRegion(editModal.record)}</p>
              <p><strong>字段：</strong>{fieldLabel(editModal.field)}</p>
              <label>
                原值
                <input value={valueOf(editModal.record, editModal.field)} readOnly />
              </label>
              <label>
                新值
                <input
                  value={editModal.value}
                  onChange={(event) => setEditModal((current) => current ? { ...current, value: event.target.value } : current)}
                />
              </label>
            </div>
            <div className="admin-modal-actions">
              <button onClick={() => setEditModal(null)}>取消</button>
              <button onClick={() => void handleSaveEdit()} disabled={isSubmittingEdit}>确认修改</button>
            </div>
          </div>
        </div>
      ) : null}

      {showReplaceConfirm ? (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-label="全量覆盖确认">
            <div className="admin-card-title">
              <h3>全量覆盖二次确认</h3>
              <button onClick={() => { setShowReplaceConfirm(false); setReplaceConfirmText(''); }}>关闭</button>
            </div>
            <div className="admin-modal-body">
              <p>全量覆盖会删除当前库中未出现在本次 Excel 里的记录。</p>
              <p>本次预览中将写入 <strong>{replaceApplyRows}</strong> 条，可能删除 <strong>{summaryNumber(importSummary, 'delete_rows')}</strong> 条。</p>
              <label>
                请输入 <code>全量覆盖</code> 以继续
                <input value={replaceConfirmText} onChange={(event) => setReplaceConfirmText(event.target.value)} />
              </label>
            </div>
            <div className="admin-modal-actions">
              <button onClick={() => { setShowReplaceConfirm(false); setReplaceConfirmText(''); }}>取消</button>
              <button
                className="danger-outline"
                onClick={() => void handleApply('replace', true)}
                disabled={replaceConfirmText !== '全量覆盖' || isApplyStarting}
              >
                确认全量覆盖
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
