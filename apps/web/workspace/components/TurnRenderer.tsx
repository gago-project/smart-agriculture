import { useEffect, useState } from 'react';

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

function ListBlock({ turn, block }: { turn: ChatTurnView; block: ChatBlock }) {
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

  async function changePage(nextPage: number) {
    if (!turn.session_id || !turn.turn_id || !viewBlock.block_id || nextPage === page || loading) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const nextBlock = await fetchChatBlock(turn.session_id, turn.turn_id, viewBlock.block_id, nextPage);
      setViewBlock(nextBlock);
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
        <span>{pagination?.total_count ?? 0} 条</span>
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
  const metrics = (block.metrics as Record<string, unknown>) || {};
  const topRegions = Array.isArray(block.top_regions) ? (block.top_regions as Array<Record<string, unknown>>) : [];
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || '墒情概览'}</strong>
        <span>{timeWindowLabel(block.time_window)}</span>
      </header>
      <div className="turn-block-metrics">
        <div>20cm 平均含水量：{toLabelValue(metrics.avg_water20cm)}%</div>
        <div>记录数：{toLabelValue(metrics.record_count)}</div>
        <div>点位数：{toLabelValue(metrics.device_count)}</div>
        <div>地区数：{toLabelValue(metrics.region_count)}</div>
        <div>最新记录时间：{toLabelValue(metrics.latest_create_time)}</div>
      </div>
      {topRegions.length > 0 ? (
        <BlockTable columns={['city', 'county', 'record_count', 'device_count', 'avg_water20cm', 'latest_create_time']} rows={topRegions} />
      ) : null}
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

function CompareBlock({ block }: { block: ChatBlock }) {
  const rows = Array.isArray(block.rows) ? (block.rows as Array<Record<string, unknown>>) : [];
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || '对比结果'}</strong>
        <span>{timeWindowLabel(block.time_window)}</span>
      </header>
      <BlockTable columns={['entity', 'record_count', 'device_count', 'region_count', 'avg_water20cm', 'latest_create_time']} rows={rows} />
    </section>
  );
}

function RuleOrTemplateBlock({ block }: { block: ChatBlock }) {
  return (
    <section className="turn-block">
      <header className="turn-block-header">
        <strong>{block.title || toLabelValue(block.template_name || block.rule_name || '配置详情')}</strong>
      </header>
      {'template_text' in block && typeof block.template_text === 'string' ? (
        <pre className="turn-block-pre">{block.template_text}</pre>
      ) : null}
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

  const visibleBlocks = turn.blocks.filter((block) => block?.display_mode !== 'evidence_only');
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
        if (block.block_type === 'list_table') {
          return <ListBlock key={block.block_id} turn={turn} block={block} />;
        }
        if (block.block_type === 'group_table') {
          return (
            <section className="turn-block" key={block.block_id}>
              <header className="turn-block-header">
                <strong>{block.title || '分组汇总'}</strong>
                <span>{toLabelValue(block.group_by)}</span>
              </header>
              <BlockTable
                columns={['group_key', 'record_count', 'device_count', 'avg_water20cm', 'latest_create_time']}
                rows={Array.isArray(block.rows) ? (block.rows as Array<Record<string, unknown>>) : []}
              />
            </section>
          );
        }
        if (block.block_type === 'detail_card') {
          return <DetailBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'compare_card') {
          return <CompareBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'rule_card' || block.block_type === 'template_card') {
          return <RuleOrTemplateBlock key={block.block_id} block={block} />;
        }
        if (block.block_type === 'guidance_card' || block.block_type === 'fallback_card') {
          return null;
        }
        return <SimpleTextBlock key={block.block_id} block={block} />;
      })}
    </div>
  );
}
