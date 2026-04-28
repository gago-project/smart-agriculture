function toNonEmptyString(value) {
  if (typeof value !== 'string') return '';
  return value.trim();
}

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
}

function deriveWindowFromArtifacts({ toolTrace, queryLogEntries }) {
  for (const entry of queryLogEntries) {
    const range = asObject(entry?.time_range_json) || asObject(entry?.time_window);
    const startTime = toNonEmptyString(range?.start_time);
    const endTime = toNonEmptyString(range?.end_time);
    if (startTime && endTime) {
      return {
        start_time: startTime,
        end_time: endTime,
        source: toNonEmptyString(range?.time_source || range?.source || 'query'),
        inherited: Boolean(range?.inherited),
      };
    }
  }

  for (const entry of toolTrace) {
    const args = asObject(entry?.tool_args);
    const startTime = toNonEmptyString(args?.start_time);
    const endTime = toNonEmptyString(args?.end_time);
    if (startTime && endTime) {
      return {
        start_time: startTime,
        end_time: endTime,
        source: 'tool_args',
        inherited: false,
      };
    }
  }

  return null;
}

export function buildAnalysisContext({ intent, toolTrace, answerFacts, queryLogEntries }) {
  const queryType = toNonEmptyString(intent);
  const facts = answerFacts && typeof answerFacts === 'object' ? answerFacts : {};
  const trace = Array.isArray(toolTrace) ? toolTrace : [];
  const logs = Array.isArray(queryLogEntries) ? queryLogEntries : [];

  // Derive region from answer facts (detail/summary/ranking results carry entity_name)
  const entityName = toNonEmptyString(facts.entity_name || facts.region_name || '');
  const entityType = toNonEmptyString(facts.entity_type || '');

  if (entityName) {
    return {
      domain: 'soil',
      region_name: entityName,
      region_level: entityType === 'device' ? '' : (entityType || 'region'),
      query_type: queryType,
    };
  }

  // Fall back to first tool call args for region hint
  const firstToolArgs = trace.length > 0 ? (trace[0].tool_args || {}) : {};
  const argRegion = toNonEmptyString(firstToolArgs.region_name || firstToolArgs.county || firstToolArgs.city || '');
  if (argRegion) {
    return {
      domain: 'soil',
      region_name: argRegion,
      region_level: firstToolArgs.county ? 'county' : (firstToolArgs.city ? 'city' : 'region'),
      query_type: queryType,
    };
  }

  const firstResolvedArgs = logs.length > 0 ? (asObject(logs[0]?.resolved_args_json) || asObject(logs[0]?.filters_json) || {}) : {};
  const resolvedRegion = toNonEmptyString(firstResolvedArgs.county || firstResolvedArgs.city || '');
  if (resolvedRegion) {
    return {
      domain: 'soil',
      region_name: resolvedRegion,
      region_level: firstResolvedArgs.county ? 'county' : (firstResolvedArgs.city ? 'city' : ''),
      query_type: queryType,
    };
  }

  return {
    domain: 'soil',
    region_name: '',
    region_level: '',
    query_type: queryType,
  };
}

export function buildRequestUnderstanding({ question, intent, inputType, toolTrace, queryLogEntries }) {
  const trace = Array.isArray(toolTrace) ? toolTrace : [];
  const logs = Array.isArray(queryLogEntries) ? queryLogEntries : [];
  const window = deriveWindowFromArtifacts({ toolTrace: trace, queryLogEntries: logs });
  const usedContext = logs.some((entry) => {
    const range = asObject(entry?.time_range_json) || asObject(entry?.time_window);
    return Boolean(range?.inherited || entry?.used_context || entry?.context_used);
  });

  return {
    original_question: question,
    normalized_question: question,
    resolved_question: question,
    domain: 'soil',
    task_type: intent,
    understanding_engine: 'restricted-flow',
    used_context: usedContext,
    ignored_phrases: inputType === 'meaningless_input' ? [question] : [],
    window: window || {},
    future_window: null,
  };
}
