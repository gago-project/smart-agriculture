function toNonEmptyString(value) {
  if (typeof value !== 'string') return '';
  return value.trim();
}

export function buildAnalysisContext({ intent, mergedSlots, contextUsed }) {
  const currentSlots = mergedSlots && typeof mergedSlots === 'object' ? mergedSlots : {};
  const inheritedContext = contextUsed && typeof contextUsed === 'object' ? contextUsed : {};
  const queryType = toNonEmptyString(intent);

  const mergedCounty = toNonEmptyString(currentSlots.county);
  if (mergedCounty) {
    return {
      domain: 'soil',
      region_name: mergedCounty,
      region_level: 'county',
      query_type: queryType,
    };
  }

  const mergedCity = toNonEmptyString(currentSlots.city);
  if (mergedCity) {
    return {
      domain: 'soil',
      region_name: mergedCity,
      region_level: 'city',
      query_type: queryType,
    };
  }

  const inheritedCounty = toNonEmptyString(inheritedContext.county);
  if (inheritedCounty) {
    return {
      domain: 'soil',
      region_name: inheritedCounty,
      region_level: 'county',
      query_type: queryType,
    };
  }

  const inheritedCity = toNonEmptyString(inheritedContext.city);
  if (inheritedCity) {
    return {
      domain: 'soil',
      region_name: inheritedCity,
      region_level: 'city',
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
