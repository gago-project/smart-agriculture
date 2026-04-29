import { useEffect, useMemo, useState } from 'react';

import { fetchAdminQueryEvidence, fetchAdminQueryEvidenceResult, type AgentQueryEvidencePayload } from '../services/queryEvidenceApi';
import type { ChatMessageData, Message } from '../types/chat';

interface AdminQueryEvidenceSidebarProps {
  message: Message | null;
}

interface EvidenceState {
  loading: boolean;
  data?: AgentQueryEvidencePayload;
  error?: string | null;
}

interface RawResultState {
  loading: boolean;
  data?: unknown;
  error?: string | null;
}

function asObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function asObjectArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(asObject(item)))
    : [];
}

function toMessageData(message: Message | null): ChatMessageData | null {
  if (!message?.meta?.data || typeof message.meta.data !== 'object') {
    return null;
  }
  return message.meta.data;
}

function toLabelValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function prettyJson(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatTimeWindow(value: unknown): string {
  const range = asObject(value);
  if (!range) return '—';
  const startTime = typeof range.start_time === 'string' ? range.start_time : '';
  const endTime = typeof range.end_time === 'string' ? range.end_time : '';
  if (startTime && endTime) {
    return `${startTime} 至 ${endTime}`;
  }
  return '—';
}

function queryTypeLabel(queryType: string): string {
  if (queryType === 'recent_summary') return '概览';
  if (queryType === 'severity_ranking') return '排名';
  if (queryType === 'region_detail') return '地区详情';
  if (queryType === 'device_detail') return '设备详情';
  if (queryType === 'comparison') return '对比';
  if (queryType === 'fallback') return '兜底';
  return queryType || '未知';
}

function pickResultRows(result: unknown): Array<Record<string, unknown>> {
  const directRows = asObjectArray(result);
  if (directRows.length > 0) {
    return directRows;
  }
  const record = asObject(result);
  if (!record) {
    return [];
  }
  const candidateKeys = ['items', 'records', 'alert_records', 'top_alert_regions'];
  for (const key of candidateKeys) {
    const rows = asObjectArray(record[key]);
    if (rows.length > 0) {
      return rows;
    }
  }
  const latestRecord = asObject(record.latest_record);
  if (latestRecord) {
    return [latestRecord];
  }
  return [];
}

function tableColumns(rows: Array<Record<string, unknown>>): string[] {
  const columns = new Set<string>();
  for (const row of rows.slice(0, 5)) {
    Object.keys(row).forEach((key) => columns.add(key));
  }
  return Array.from(columns).slice(0, 8);
}

function resolvePreviewColumns(result: unknown, rows: Array<Record<string, unknown>>): string[] {
  const record = asObject(result);
  const preferred = Array.isArray(record?.preview_columns)
    ? record.preview_columns.filter((column): column is string => typeof column === 'string' && column.trim().length > 0)
    : [];
  if (preferred.length > 0) {
    return preferred;
  }
  return tableColumns(rows);
}

function formatResultChars(resultChars?: number): string {
  const size = Number(resultChars || 0);
  if (!Number.isFinite(size) || size <= 0) return '未知大小';
  if (size < 1024) return `${size} 字符`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(2)} MB`;
}

function ResultPreview({
  value,
  queryId,
  rawValue,
  resultTruncated,
  resultChars,
  canLoadRaw,
}: {
  value: unknown;
  queryId: string;
  rawValue?: unknown;
  resultTruncated?: boolean;
  resultChars?: number;
  canLoadRaw?: boolean;
}) {
  const rows = useMemo(() => pickResultRows(value).slice(0, 10), [value]);
  const columns = useMemo(() => resolvePreviewColumns(value, rows), [rows, value]);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [rawState, setRawState] = useState<RawResultState>({
    loading: false,
    data: rawValue ?? (!resultTruncated ? value : undefined),
    error: null,
  });

  useEffect(() => {
    setDetailsOpen(false);
    setRawState({
      loading: false,
      data: rawValue ?? (!resultTruncated ? value : undefined),
      error: null,
    });
  }, [queryId, rawValue, resultTruncated, value]);

  useEffect(() => {
    if (!detailsOpen || !resultTruncated || !canLoadRaw || !queryId || rawState.loading || rawState.data !== undefined) {
      return;
    }

    let cancelled = false;
    setRawState((current) => ({
      ...current,
      loading: true,
      error: null,
    }));

    void fetchAdminQueryEvidenceResult(queryId)
      .then((payload) => {
        if (cancelled) return;
        setRawState({
          loading: false,
          data: payload.executed_result_json,
          error: null,
        });
      })
      .catch((caughtError) => {
        if (cancelled) return;
        setRawState({
          loading: false,
          data: undefined,
          error: caughtError instanceof Error ? caughtError.message : '原始 JSON 加载失败',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [canLoadRaw, detailsOpen, queryId, rawState.data, rawState.loading, resultTruncated]);

  return (
    <>
      {resultTruncated ? (
        <div className="query-evidence-warning">
          结果较大（{formatResultChars(resultChars)}），默认只展示预览；展开时再按需加载完整 JSON。
        </div>
      ) : null}
      {columns.length > 0 ? (
        <div className="query-evidence-empty small">仅展示关键字段：{columns.join(' / ')}</div>
      ) : null}
      {rows.length > 0 && columns.length > 0 ? (
        <div className="query-evidence-table-wrap">
          <table className="query-evidence-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`row-${index}`}>
                  {columns.map((column) => (
                    <td key={`${index}-${column}`}>{toLabelValue(row[column])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <details
        className="query-evidence-json"
        onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
      >
        <summary>{resultTruncated ? '查看原始 JSON（按需加载）' : '查看原始 JSON'}</summary>
        {!detailsOpen ? null : rawState.loading ? (
          <div className="query-evidence-empty small">原始 JSON 加载中...</div>
        ) : rawState.error ? (
          <div className="admin-message error">{rawState.error}</div>
        ) : (
          <pre>{prettyJson(rawState.data ?? value)}</pre>
        )}
      </details>
    </>
  );
}

export function AdminQueryEvidenceSidebar({ message }: AdminQueryEvidenceSidebarProps) {
  const [evidenceCache, setEvidenceCache] = useState<Record<string, EvidenceState>>({});
  const [selectedEntryIndex, setSelectedEntryIndex] = useState(0);

  const messageData = toMessageData(message);
  const sessionId = typeof messageData?.session_id === 'string' ? messageData.session_id : '';
  const turnId = typeof messageData?.turn_id === 'number' ? messageData.turn_id : 0;
  const shouldQuery = Boolean(messageData?.should_query);
  const cacheKey = sessionId && turnId > 0 ? `${sessionId}:${turnId}` : '';

  useEffect(() => {
    setSelectedEntryIndex(0);
  }, [cacheKey]);

  useEffect(() => {
    if (!cacheKey || !shouldQuery || evidenceCache[cacheKey]?.loading || evidenceCache[cacheKey]?.data) {
      return;
    }

    let cancelled = false;
    setEvidenceCache((current) => ({
      ...current,
      [cacheKey]: {
        loading: true,
        data: current[cacheKey]?.data,
        error: null,
      },
    }));

    void fetchAdminQueryEvidence(sessionId, turnId)
      .then((data) => {
        if (cancelled) return;
        setEvidenceCache((current) => ({
          ...current,
          [cacheKey]: {
            loading: false,
            data,
            error: null,
          },
        }));
      })
      .catch((caughtError) => {
        if (cancelled) return;
        setEvidenceCache((current) => ({
          ...current,
          [cacheKey]: {
            loading: false,
            data: current[cacheKey]?.data,
            error: caughtError instanceof Error ? caughtError.message : '查询证据加载失败',
          },
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [cacheKey, evidenceCache, sessionId, shouldQuery, turnId]);

  const evidenceState = cacheKey ? evidenceCache[cacheKey] : undefined;
  const entries = evidenceState?.data?.entries ?? [];
  const activeEntry = entries[selectedEntryIndex] ?? entries[0] ?? null;
  const resultSource = activeEntry?.result_preview ?? activeEntry?.executed_result_json;
  const rawResultSource = activeEntry?.executed_result_json;
  const isHistoricalGap = Boolean(activeEntry?.missing_fields?.length);

  return (
    <aside className="query-evidence-panel">
      <div className="query-evidence-header">
        <div>
          <h3>查询证据</h3>
          <p>
            {message
              ? '展示当前选中 AI 回复对应的 SQL 审计和结果数据。'
              : '管理员点击任意 AI 回复后，这里会显示该轮查询证据。'}
          </p>
        </div>
      </div>

      {!message ? (
        <div className="query-evidence-empty">请先选择一条 AI 回复。</div>
      ) : !shouldQuery ? (
        <div className="query-evidence-empty">本轮未执行数据库查询。</div>
      ) : evidenceState?.loading ? (
        <div className="query-evidence-empty">查询证据加载中...</div>
      ) : evidenceState?.error ? (
        <div className="admin-message error">{evidenceState.error}</div>
      ) : entries.length === 0 ? (
        <div className="query-evidence-empty">当前未找到该轮查询日志。</div>
      ) : (
        <>
          <section className="query-evidence-section">
            <div className="query-evidence-summary-grid">
              <div>
                <dt>查询轮次</dt>
                <dd>{sessionId}#{turnId}</dd>
              </div>
              <div>
                <dt>查询条数</dt>
                <dd>{entries.length}</dd>
              </div>
              <div>
                <dt>当前步骤</dt>
                <dd>{activeEntry ? `${activeEntry.entry_index}. ${queryTypeLabel(activeEntry.query_type)}` : '—'}</dd>
              </div>
              <div>
                <dt>状态 / 命中</dt>
                <dd>{activeEntry ? `${activeEntry.status} / ${activeEntry.row_count}` : '—'}</dd>
              </div>
              <div>
                <dt>时间窗</dt>
                <dd>{activeEntry ? formatTimeWindow(activeEntry.time_range_json) : '—'}</dd>
              </div>
              <div>
                <dt>记录时间</dt>
                <dd>{activeEntry?.created_at || '—'}</dd>
              </div>
            </div>
          </section>

          {entries.length > 1 ? (
            <section className="query-evidence-section">
              <div className="query-evidence-tab-list">
                {entries.map((entry, index) => (
                  <button
                    key={entry.query_id}
                    type="button"
                    className={`query-evidence-tab ${index === selectedEntryIndex ? 'is-active' : ''}`}
                    onClick={() => setSelectedEntryIndex(index)}
                  >
                    {entry.entry_index}. {queryTypeLabel(entry.query_type)}
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          {isHistoricalGap ? (
            <div className="query-evidence-warning">
              历史日志不完整：缺少 {activeEntry?.missing_fields.join('、')}，当前仅展示接口还能还原出的真实证据。
            </div>
          ) : null}

          <section className="query-evidence-section">
            <div className="query-evidence-section-title">SQL</div>
            {activeEntry?.executed_sql_text ? (
              <pre>{activeEntry.executed_sql_text}</pre>
            ) : (
              <div className="query-evidence-empty small">当前日志没有保存 SQL 审计文本。</div>
            )}
          </section>

          <section className="query-evidence-section">
            <div className="query-evidence-section-title">结果数据</div>
            {resultSource ? (
              <ResultPreview
                value={resultSource}
                queryId={activeEntry?.query_id || ''}
                rawValue={rawResultSource}
                resultTruncated={Boolean(activeEntry?.result_truncated)}
                resultChars={activeEntry?.result_chars}
                canLoadRaw={Boolean(activeEntry?.result_truncated && activeEntry?.has_full_result)}
              />
            ) : (
              <div className="query-evidence-empty small">当前日志没有保存结果数据。</div>
            )}
          </section>
        </>
      )}
    </aside>
  );
}
