export const APP_NAME = 'Smart Agriculture';

export const SOIL_ANSWER_TYPES = [
  'soil_summary_answer',
  'soil_ranking_answer',
  'soil_detail_answer',
  'guidance_answer',
  'fallback_answer',
] as const;

export const SOIL_OUTPUT_MODES = [
  'normal',
  'anomaly_focus',
  'warning_mode',
  'advice_mode',
] as const;

export const SOIL_GUIDANCE_REASONS = [
  'safe_hint',
  'clarification',
  'boundary',
  'closing',
] as const;

export const SOIL_FALLBACK_REASONS = [
  'no_data',
  'entity_not_found',
  'tool_missing',
  'tool_blocked',
  'fact_check_failed',
  'unknown',
] as const;

export type SoilAnswerType = (typeof SOIL_ANSWER_TYPES)[number];
export type SoilOutputMode = (typeof SOIL_OUTPUT_MODES)[number];
export type SoilGuidanceReason = (typeof SOIL_GUIDANCE_REASONS)[number];
export type SoilFallbackReason = (typeof SOIL_FALLBACK_REASONS)[number];
