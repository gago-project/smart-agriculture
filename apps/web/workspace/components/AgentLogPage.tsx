import { useCallback, useEffect, useState } from 'react';

import { fetchAgentQueryLogs, type AgentQueryLogPage } from '../services/agentLogApi';

const PAGE_SIZE = 30;

interface Filters {
  keyword: string;
  session_id: string;
  query_type: string;
  intent: string;
  status: string;
  created_at_from: string;
  created_at_to: string;
}

const initialFilters: Filters = {
  keyword: '',
  session_id: '',
  query_type: '',
  intent: '',
  status: '',
  created_at_from: '',
  created_at_to: ''
};

const emptyPage: AgentQueryLogPage = {
  rows: [],
  total: 0,
  page: 1,
  page_size: PAGE_SIZE,
  total_pages: 0
};

const queryTypeOptions = [
  { value: '', label: '全部' },
  { value: 'recent_summary', label: 'recent_summary｜概览' },
  { value: 'severity_ranking', label: 'severity_ranking｜排名' },
  { value: 'region_detail', label: 'region_detail｜地区详情' },
  { value: 'device_detail', label: 'device_detail｜设备详情' },
  { value: 'anomaly_list', label: 'anomaly_list｜异常列表' },
  { value: 'latest_record', label: 'latest_record｜最新记录' },
  { value: 'fallback', label: 'fallback｜兜底' }
];

const intentOptions = [
  { value: '', label: '全部' },
  { value: 'soil_recent_summary', label: 'soil_recent_summary｜墒情概览' },
  { value: 'soil_severity_ranking', label: 'soil_severity_ranking｜排名对比' },
  { value: 'soil_region_query', label: 'soil_region_query｜地区查询' },
  { value: 'soil_device_query', label: 'soil_device_query｜设备查询' },
  { value: 'soil_anomaly_query', label: 'soil_anomaly_query｜异常分析' },
  { value: 'soil_warning_generation', label: 'soil_warning_generation｜预警生成' },
  { value: 'soil_metric_explanation', label: 'soil_metric_explanation｜指标解释' },
  { value: 'soil_management_advice', label: 'soil_management_advice｜管理建议' },
  { value: 'clarification_needed', label: 'clarification_needed｜澄清' },
  { value: 'out_of_scope', label: 'out_of_scope｜边界外' }
];

function compactFilters(filters: Filters) {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim() !== ''));
}

function preview(value: string | null | undefined, maxLength = 80) {
  const normalized = String(value || '').trim();
  if (!normalized) return '-';
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

export function AgentLogPage() {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AgentQueryLogPage>(emptyPage);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLogs = useCallback(async (nextPage: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchAgentQueryLogs({ page: nextPage, page_size: PAGE_SIZE, ...compactFilters(filters) });
      setData(result);
      setPage(result.page);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '查询日志加载失败');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadLogs(1);
  }, [loadLogs]);

  function updateFilter(field: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  return (
    <section className="soil-admin-page" aria-label="开发查询日志">
      <header className="soil-admin-header">
        <div>
          <h2>开发查询日志</h2>
          <p>只读查看用户问题、最终回答、意图、查询计划、数据行数和执行状态，方便排查和优化 Agent。</p>
        </div>
        <button onClick={() => void loadLogs(page)} disabled={isLoading}>刷新</button>
      </header>

      {error ? <div className="admin-message error">{error}</div> : null}

      <div className="admin-card filter-card">
        <label>
          关键词
          <input aria-label="关键词" value={filters.keyword} onChange={(event) => updateFilter('keyword', event.target.value)} placeholder="问题 / 回答 / session" />
        </label>
        <label>
          Session
          <input aria-label="Session" value={filters.session_id} onChange={(event) => updateFilter('session_id', event.target.value)} placeholder="session_id" />
        </label>
        <label>
          查询类型
          <select aria-label="查询类型" value={filters.query_type} onChange={(event) => updateFilter('query_type', event.target.value)}>
            {queryTypeOptions.map((option) => (
              <option key={option.value || 'all'} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          意图
          <select aria-label="意图" value={filters.intent} onChange={(event) => updateFilter('intent', event.target.value)}>
            {intentOptions.map((option) => (
              <option key={option.value || 'all'} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label>
          状态
          <select aria-label="状态" value={filters.status} onChange={(event) => updateFilter('status', event.target.value)}>
            <option value="">全部</option>
            <option value="success">success</option>
            <option value="empty">empty</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          开始时间
          <input aria-label="开始时间" value={filters.created_at_from} onChange={(event) => updateFilter('created_at_from', event.target.value)} placeholder="2026-04-21 00:00:00" />
        </label>
        <label>
          结束时间
          <input aria-label="结束时间" value={filters.created_at_to} onChange={(event) => updateFilter('created_at_to', event.target.value)} placeholder="2026-04-21 23:59:59" />
        </label>
        <button onClick={() => void loadLogs(1)} disabled={isLoading}>查询</button>
      </div>

      <div className="admin-table-toolbar">
        <span>共 {data.total} 条，第 {data.total_pages === 0 ? 0 : data.page} / {data.total_pages} 页</span>
        <div>
          <button onClick={() => void loadLogs(Math.max(1, page - 1))} disabled={isLoading || page <= 1}>上一页</button>
          <button onClick={() => void loadLogs(page + 1)} disabled={isLoading || page >= data.total_pages}>下一页</button>
        </div>
      </div>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>问题</th>
              <th>回答</th>
              <th>意图 / 类型</th>
              <th>状态</th>
              <th>行数</th>
              <th>Session</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((log) => (
              <tr key={log.query_id}>
                <td>{log.created_at}</td>
                <td>{preview(log.request_text, 70)}</td>
                <td>{preview(log.response_text, 90)}</td>
                <td>{log.intent || '-'} / {log.answer_type || log.query_type || '-'}</td>
                <td>{log.status}</td>
                <td>{log.row_count}</td>
                <td>{log.session_id}#{log.turn_id}</td>
              </tr>
            ))}
            {data.rows.length === 0 ? (
              <tr>
                <td colSpan={7}>暂无查询日志</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
