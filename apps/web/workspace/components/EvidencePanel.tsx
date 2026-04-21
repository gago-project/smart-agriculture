import type { Message } from '../types/chat';

interface EvidencePanelProps {
  message: Message | null;
}

function toPrettyJson(input: unknown): string {
  if (input === null || input === undefined) return 'null';
  if (typeof input === 'string') return input;
  try {
    return JSON.stringify(input, null, 2);
  } catch {
    return String(input);
  }
}

function asObject(input: unknown): Record<string, unknown> | null {
  return input && typeof input === 'object' && !Array.isArray(input) ? (input as Record<string, unknown>) : null;
}

function asObjectArray(input: unknown): Array<Record<string, unknown>> {
  return Array.isArray(input)
    ? input.filter((item): item is Record<string, unknown> => Boolean(asObject(item)))
    : [];
}

function toLabelValue(input: unknown): string {
  if (input === null || input === undefined || input === '') return '—';
  if (typeof input === 'string' || typeof input === 'number' || typeof input === 'boolean') return String(input);
  return toPrettyJson(input);
}

function domainLabel(domain: unknown): string {
  if (domain === 'pest') return '虫情';
  if (domain === 'soil' || domain === 'soil_moisture') return '墒情';
  return toLabelValue(domain);
}

function regionLevelLabel(level: unknown): string {
  if (level === 'county') return '区县';
  if (level === 'city') return '市';
  return toLabelValue(level);
}

function formatWindow(window: unknown, kind: 'past' | 'future'): string {
  const parsed = asObject(window);
  if (!parsed) return '—';
  if (kind === 'future' && typeof parsed.horizon_days === 'number') {
    return `未来 ${parsed.horizon_days} 天`;
  }
  if (parsed.window_type === 'months') return `${kind === 'future' ? '未来' : '过去'} ${parsed.window_value} 个月`;
  if (parsed.window_type === 'weeks') return `${kind === 'future' ? '未来' : '过去'} ${parsed.window_value} 周`;
  if (parsed.window_type === 'days') return `${kind === 'future' ? '未来' : '过去'} ${parsed.window_value} 天`;
  if (parsed.window_type === 'all') return '全量历史';
  return toLabelValue(window);
}

function formatShortDate(value: unknown): string {
  if (typeof value !== 'string' || !value) return '—';
  return value.slice(0, 10);
}

export function EvidencePanel({ message }: EvidencePanelProps) {
  const processing = message?.meta?.processing;
  const evidence = asObject(message?.meta?.evidence);
  const responseMeta = asObject(evidence?.response_meta);
  const understanding = asObject(evidence?.request_understanding);
  const analysisContext = asObject(evidence?.analysis_context);
  const historicalQuery = asObject(evidence?.historical_query) ?? evidence;
  const regionLevel = analysisContext?.region_level ?? historicalQuery?.region_level;
  const forecast = asObject(evidence?.forecast);
  const knowledge = asObjectArray(evidence?.knowledge);
  const availableDataRanges = asObjectArray(historicalQuery?.available_data_ranges);
  const noDataReasons = asObjectArray(historicalQuery?.no_data_reasons);
  const recoverySuggestions = asObjectArray(historicalQuery?.recovery_suggestions);
  const executionPlan = Array.isArray(evidence?.execution_plan)
    ? evidence.execution_plan.filter((item): item is string => typeof item === 'string')
    : [];

  return (
    <aside className="evidence-panel">
      <div className="evidence-panel-header">
        <div>
          <h3>分析面板</h3>
          <p>{message?.meta ? '当前显示所选 AI 回复的处理链与证据。' : '点击任意 AI 回复后，这里会显示对应的分析信息。'}</p>
        </div>
        {processing ? <span className={`ai-badge ai-${processing.ai_involvement}`}>AI参与度 {processing.ai_involvement}</span> : null}
      </div>
      {message?.meta ? (
        <>
          {processing ? (
            <section className="processing-panel">
              <h4>处理链</h4>
              <dl className="processing-grid">
                <div>
                  <dt>意图识别</dt>
                  <dd>{processing.intent_recognition}</dd>
                </div>
                <div>
                  <dt>数据查询</dt>
                  <dd>{processing.data_query}</dd>
                </div>
                <div>
                  <dt>答案生成</dt>
                  <dd>{processing.answer_generation}</dd>
                </div>
                <div>
                  <dt>AI参与度</dt>
                  <dd>{processing.ai_involvement}</dd>
                </div>
                {processing.orchestration ? (
                  <div>
                    <dt>编排</dt>
                    <dd>{processing.orchestration}</dd>
                  </div>
                ) : null}
                {processing.memory ? (
                  <div>
                    <dt>记忆</dt>
                    <dd>{processing.memory}</dd>
                  </div>
                ) : null}
              </dl>
            </section>
          ) : null}
          <section className="evidence-section">
            <div className="section-label-row">
              <strong>结果模式</strong>
              <span className="mode-badge">{message.meta.mode ?? 'unknown'}</span>
            </div>
          </section>
          {responseMeta ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>回答元信息</strong>
              </div>
              <dl className="detail-grid">
                <div>
                  <dt>回答置信度</dt>
                  <dd>{toLabelValue(responseMeta.confidence)}</dd>
                </div>
                <div>
                  <dt>来源类型</dt>
                  <dd>
                    {Array.isArray(responseMeta.source_types) && responseMeta.source_types.length > 0
                      ? responseMeta.source_types
                          .filter((item): item is string => typeof item === 'string' && item.length > 0)
                          .join(' / ')
                      : '—'}
                  </dd>
                </div>
                <div>
                  <dt>回退原因</dt>
                  <dd>{toLabelValue(responseMeta.fallback_reason)}</dd>
                </div>
              </dl>
            </section>
          ) : null}
          {understanding ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>问题理解</strong>
              </div>
              <dl className="detail-grid">
                <div>
                  <dt>原问题</dt>
                  <dd>{toLabelValue(understanding.original_question)}</dd>
                </div>
                <div>
                  <dt>解析后</dt>
                  <dd>{toLabelValue(understanding.normalized_question)}</dd>
                </div>
                <div>
                  <dt>补全问题</dt>
                  <dd>{toLabelValue(understanding.resolved_question)}</dd>
                </div>
                <div>
                  <dt>领域</dt>
                  <dd>{domainLabel(understanding.domain)}</dd>
                </div>
                <div>
                  <dt>任务类型</dt>
                  <dd>{toLabelValue(understanding.task_type)}</dd>
                </div>
                <div>
                  <dt>理解引擎</dt>
                  <dd>{toLabelValue(understanding.understanding_engine)}</dd>
                </div>
                <div>
                  <dt>历史窗口</dt>
                  <dd>{formatWindow(understanding.window, 'past')}</dd>
                </div>
                <div>
                  <dt>预测窗口</dt>
                  <dd>{formatWindow(understanding.future_window, 'future')}</dd>
                </div>
                <div>
                  <dt>使用上下文</dt>
                  <dd>{understanding.used_context ? '是' : '否'}</dd>
                </div>
                <div>
                  <dt>忽略废话</dt>
                  <dd>
                    {Array.isArray(understanding.ignored_phrases) && understanding.ignored_phrases.length > 0
                      ? understanding.ignored_phrases.join('、')
                      : '无'}
                  </dd>
                </div>
              </dl>
            </section>
          ) : null}
          {executionPlan.length > 0 ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>执行计划</strong>
              </div>
              <div className="plan-chip-list">
                {executionPlan.map((step) => (
                  <span key={step} className="plan-chip">
                    {step}
                  </span>
                ))}
              </div>
            </section>
          ) : null}
          {historicalQuery || analysisContext ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>历史数据层</strong>
              </div>
              <dl className="detail-grid">
                <div>
                  <dt>数据域</dt>
                  <dd>{domainLabel(analysisContext?.domain)}</dd>
                </div>
                <div>
                  <dt>地区</dt>
                  <dd>{toLabelValue(analysisContext?.region_name)}</dd>
                </div>
                <div>
                  <dt>地区层级</dt>
                  <dd>{regionLevelLabel(regionLevel)}</dd>
                </div>
                <div>
                  <dt>查询类型</dt>
                  <dd>{toLabelValue(analysisContext?.query_type)}</dd>
                </div>
                <div>
                  <dt>查询口径</dt>
                  <dd>{toLabelValue(historicalQuery?.rule)}</dd>
                </div>
                <div>
                  <dt>数据链</dt>
                  <dd>{toLabelValue(historicalQuery?.sql)}</dd>
                </div>
                <div>
                  <dt>起始时间</dt>
                  <dd>{toLabelValue(historicalQuery?.since)}</dd>
                </div>
              </dl>
              {availableDataRanges.length > 0 ? (
                <div className="available-range-block">
                  <strong>可用时间窗</strong>
                  <div className="available-range-list">
                    {availableDataRanges.map((item, index) => (
                      <article key={`${toLabelValue(item.source)}-${index}`} className="available-range-card">
                        <span className="available-range-label">{toLabelValue(item.label)}</span>
                        <span className="available-range-value">
                          {formatShortDate(item.min_time)} 至 {formatShortDate(item.max_time)}
                        </span>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
              {noDataReasons.length > 0 ? (
                <div className="available-range-block">
                  <strong>无数据原因</strong>
                  <div className="available-range-list">
                    {noDataReasons.map((item, index) => (
                      <article key={`${toLabelValue(item.source)}-${toLabelValue(item.code)}-${index}`} className="available-range-card">
                        <span className="available-range-label">{toLabelValue(item.code)}</span>
                        <span className="available-range-value available-range-message">{toLabelValue(item.message)}</span>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
              {recoverySuggestions.length > 0 ? (
                <div className="available-range-block">
                  <strong>恢复建议</strong>
                  <div className="available-range-list">
                    {recoverySuggestions.map((item, index) => {
                      const suggestedQuestions = Array.isArray(item.suggested_questions)
                        ? item.suggested_questions.filter((entry): entry is string => typeof entry === 'string' && entry.length > 0)
                        : [];
                      const singleSuggestedQuestion =
                        typeof item.suggested_question === 'string' && item.suggested_question.length > 0
                          ? item.suggested_question
                          : null;
                      return (
                        <article
                          key={`${toLabelValue(item.source)}-${toLabelValue(item.action)}-${index}`}
                          className="available-range-card recovery-card"
                        >
                          <span className="available-range-label">{toLabelValue(item.title)}</span>
                          <span className="available-range-value available-range-message">{toLabelValue(item.message)}</span>
                          {singleSuggestedQuestion ? <code className="recovery-question">{singleSuggestedQuestion}</code> : null}
                          {suggestedQuestions.length > 0 ? (
                            <div className="recovery-question-list">
                              {suggestedQuestions.map((entry) => (
                                <code key={entry} className="recovery-question">
                                  {entry}
                                </code>
                              ))}
                            </div>
                          ) : null}
                        </article>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}
          {forecast ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>预测层</strong>
              </div>
              <dl className="detail-grid">
                <div>
                  <dt>领域</dt>
                  <dd>{domainLabel(forecast.domain)}</dd>
                </div>
                <div>
                  <dt>模式</dt>
                  <dd>{toLabelValue(forecast.mode)}</dd>
                </div>
                <div>
                  <dt>窗口</dt>
                  <dd>{typeof forecast.horizon_days === 'number' ? `未来 ${forecast.horizon_days} 天` : '—'}</dd>
                </div>
                <div>
                  <dt>风险等级</dt>
                  <dd>{toLabelValue(forecast.risk_level)}</dd>
                </div>
                <div>
                  <dt>置信度</dt>
                  <dd>{toLabelValue(forecast.confidence)}</dd>
                </div>
                {forecast.risk_index !== undefined ? (
                  <div>
                    <dt>风险指数</dt>
                    <dd>{toLabelValue(forecast.risk_index)}</dd>
                  </div>
                ) : null}
                {forecast.projected_score !== undefined ? (
                  <div>
                    <dt>原始预测分</dt>
                    <dd>{toLabelValue(forecast.projected_score)}</dd>
                  </div>
                ) : null}
              </dl>
              {Array.isArray(forecast.top_factors) && forecast.top_factors.length > 0 ? (
                <div className="available-range-block">
                  <strong>关键因子</strong>
                  <div className="available-range-list">
                    <article className="available-range-card">
                      <span className="available-range-value available-range-message">
                        {forecast.top_factors.filter((item): item is string => typeof item === 'string' && item.length > 0).join('、')}
                      </span>
                    </article>
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}
          {knowledge.length > 0 ? (
            <section className="evidence-section">
              <div className="section-label-row">
                <strong>知识层</strong>
              </div>
              <div className="knowledge-list">
                {knowledge.map((item, index) => (
                  <article key={`${item.title ?? 'knowledge'}-${index}`} className="knowledge-card">
                    <strong>{toLabelValue(item.title)}</strong>
                    <p>{toLabelValue(item.snippet)}</p>
                    <div className="knowledge-meta">
                      <span>命中词：{Array.isArray(item.matched_terms) && item.matched_terms.length > 0 ? item.matched_terms.join('、') : '—'}</span>
                      <span>匹配分：{toLabelValue(item.score)}</span>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
          <section className="evidence-section">
            <div className="section-label-row">
              <strong>结果数据</strong>
            </div>
            <pre>{toPrettyJson(message.meta.data)}</pre>
          </section>
          <section className="evidence-section">
            <div className="section-label-row">
              <strong>原始证据</strong>
            </div>
            <pre>{toPrettyJson(evidence)}</pre>
          </section>
        </>
      ) : (
        <div className="evidence-empty">
          <p>暂无证据数据</p>
          <span>发送问题并选择对应的 AI 回复后，这里会展示处理链、摘要和可核验信息。</span>
        </div>
      )}
    </aside>
  );
}
