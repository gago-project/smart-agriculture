import { useEffect, useState } from 'react';

import { isPaginatedTableBlockType, paginatedTableTotalUnit } from '../../lib/chatBlockContract.mjs';
import { fetchChatBlock } from '../services/chatApi';
import type { ChatBlock, ChatTurnView } from '../types/chat';

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

function timeWindowLabel(value: unknown): string {
  if (!value || typeof value !== 'object') return '—';
  const range = value as Record<string, unknown>;
  const start = typeof range.start_time === 'string' ? range.start_time : '';
  const end = typeof range.end_time === 'string' ? range.end_time : '';
  if (!start || !end) return '—';
  return `${start} 至 ${end}`;
}

function BlockTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}) {
  if (!columns.length || !rows.length) {
    return <div className="turn-block-empty">当前没有可展示的数据。</div>;
  }
  return (
    <div className="turn-block-table-wrap">
      <table className="turn-block-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {columns.map((column) => (
                <td key={`${rowIndex}-${column}`}>{toLabelValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PaginatedTableBlock({ block }: { block: ChatBlock }) {
  const [viewBlock, setViewBlock] = useState(block);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setViewBlock(block);
    setLoading(false);
    setError(null);
  }, [block]);

  const pagination = viewBlock.pagination;
  const page = typeof pagination?.page === 'number' ? pagination.page : 1;
  const totalPages = typeof pagination?.total_pages === 'number' ? pagination.total_pages : 0;
  const totalUnit = paginatedTableTotalUnit(viewBlock.block_type);

  async function changePage(nextPage: number) {
    const snapshotId = typeof pagination?.snapshot_id === 'string' ? pagination.snapshot_id : '';
    const pageSize = typeof pagination?.page_size === 'number' ? pagination.page_size : 10;
    if (!snapshotId || nextPage === page || loading) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const nextBlock = await fetchChatBlock(snapshotId, viewBlock.block_type, nextPage, pageSize);
      setViewBlock((current) => ({
        ...current,
        ...nextBlock,
        rows: Array.isArray(nextBlock.rows) ? nextBlock.rows : current.rows,
        pagination: nextBlock.pagination ?? current.pagination,
      }));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : '分页加载失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{viewBlock.title || '点位列表'}</strong>
        <span>{pagination?.total_count ?? 0} {totalUnit}</span>
      </header>
      <BlockTable
        columns={Array.isArray(viewBlock.columns) ? viewBlock.columns : []}
        rows={Array.isArray(viewBlock.rows) ? (viewBlock.rows as Array<Record<string, unknown>>) : []}
      />
      {error ? <div className="turn-block-error">{error}</div> : null}
      {pagination && totalPages > 1 ? (
        <div className="turn-block-pagination">
          <button type="button" disabled={loading || page <= 1} onClick={() => void changePage(page - 1)}>
            上一页
          </button>
          <span>
            第 {page} / {totalPages} 页
          </span>
          <button type="button" disabled={loading || page >= totalPages} onClick={() => void changePage(page + 1)}>
            下一页
          </button>
        </div>
      ) : null}
    </section>
  );
}

function SummaryBlock({ block }: { block: ChatBlock }) {
  const topRegions = Array.isArray(block.top_regions) ? (block.top_regions as Array<Record<string, unknown>>) : [];
  const regionColumns = topRegions.some(
    (row) => row && typeof row === 'object' && ('alert_device_count' in row || 'alert_record_count' in row || 'latest_alert_time' in row),
  )
    ? ['city', 'county', 'alert_device_count', 'alert_record_count', 'latest_alert_time']
    : ['city', 'county'];
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || '墒情概览'}</strong>
        <span>{timeWindowLabel(block.time_window)}</span>
      </header>
      {topRegions.length > 0 ? (
        <BlockTable columns={regionColumns} rows={topRegions} />
      ) : (
        <div className="turn-block-empty">当前没有可展示的原始字段。</div>
      )}
    </section>
  );
}

function DetailBlock({ block }: { block: ChatBlock }) {
  const latestRecord =
    block.latest_record && typeof block.latest_record === 'object' && !Array.isArray(block.latest_record)
      ? (block.latest_record as Record<string, unknown>)
      : null;
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || '详情'}</strong>
        <span>{timeWindowLabel(block.time_window)}</span>
      </header>
      {latestRecord ? (
        <BlockTable columns={Object.keys(latestRecord)} rows={[latestRecord]} />
      ) : (
        <div className="turn-block-empty">当前没有详情记录。</div>
      )}
    </section>
  );
}

function FieldBlock({ block }: { block: ChatBlock }) {
  const values =
    block.values && typeof block.values === 'object' && !Array.isArray(block.values)
      ? (block.values as Record<string, unknown>)
      : null;
  if (block.field_mode === 'aggregate') {
    return (
      <section className="turn-block">
        <header className="turn-block-header">
          <strong>{block.title || '字段结果'}</strong>
          <span>{timeWindowLabel(block.time_window)}</span>
        </header>
        <div className="turn-block-empty">
          {toLabelValue(block.field)} {toLabelValue(block.aggregation)} = {toLabelValue(block.value)}
        </div>
      </section>
    );
  }
  if (values) {
    return (
      <section className="turn-block">
        <header className="turn-block-header">
          <strong>{block.title || '字段结果'}</strong>
          <span>{timeWindowLabel(block.time_window)}</span>
        </header>
        <BlockTable columns={Object.keys(values)} rows={[values]} />
      </section>
    );
  }
  return <SimpleTextBlock block={block} />;
}

function CompareBlock({ block }: { block: ChatBlock }) {
  const rows = Array.isArray(block.rows) ? (block.rows as Array<Record<string, unknown>>) : [];
  const columns =
    Array.isArray(block.columns) && block.columns.length > 0
      ? (block.columns as string[])
      : rows[0]
        ? Object.keys(rows[0])
        : [];
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || '对比结果'}</strong>
        <span>{timeWindowLabel(block.time_window)}</span>
      </header>
      <BlockTable columns={columns} rows={rows} />
    </section>
  );
}

function RuleBlock({ block }: { block: ChatBlock }) {
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || toLabelValue(block.rule_name || '配置详情')}</strong>
      </header>
      {'thresholds' in block && block.thresholds ? (
        <pre className="turn-block-pre">{JSON.stringify(block.thresholds, null, 2)}</pre>
      ) : null}
    </section>
  );
}

function SimpleTextBlock({ block }: { block: ChatBlock }) {
  return (
    <section className="turn-block">
      <div>{block.text || '暂无内容'}</div>
    </section>
  );
}

export function TurnRenderer({ turn }: { turn: ChatTurnView | null | undefined }) {
  if (!turn || !Array.isArray(turn.blocks) || turn.blocks.length === 0) {
    return null;
  }

  const visibleBlocks = turn.blocks.filter(
    (block) => block?.display_mode !== 'evidence_only' && block?.block_type !== 'count_card',
  );
  if (visibleBlocks.length === 0) {
    return null;
  }

  return (
    <div className="turn-block-list">
      {visibleBlocks.map((block) => {
        if (!block?.block_id) {
          return null;
        }
        if (block.display_mode === 'evidence_only') {
          return null;
        }
        if (block.block_type === 'summary_card') {
          return <SummaryBlock key={block.block_id} block={block} />;
        }
        if (isPaginatedTableBlockType(block.block_type)) {
          return <PaginatedTableBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'field_card') {
          return <FieldBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'detail_card') {
          return <DetailBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'compare_card') {
          return <CompareBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'rule_card') {
          return <RuleBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'template_card') {
          return null;
        }
        if (block.block_type === 'guidance_card' || block.block_type === 'fallback_card') {
          return null;
        }
        return <SimpleTextBlock key={block.block_id} block={block} />;
      })}
    </div>
  );
}
