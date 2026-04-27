function toNonEmptyString(value) {
  if (typeof value !== 'string') return '';
  return value.trim();
}

export function buildAnalysisContext({ intent, toolTrace, answerFacts }) {
  const queryType = toNonEmptyString(intent);
  const facts = answerFacts && typeof answerFacts === 'object' ? answerFacts : {};
  const trace = Array.isArray(toolTrace) ? toolTrace : [];

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
      region_level: 'region',
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
