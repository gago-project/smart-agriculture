export type ChatMode = 'business' | 'guidance' | 'fallback' | 'unknown';
export type MessageRole = 'user' | 'assistant';
export type MessageStatus = 'pending' | 'streaming' | 'done' | 'error';
export type ChatCapability = 'summary' | 'list' | 'group' | 'detail' | 'compare' | 'count' | 'field' | 'rule' | 'template' | 'none';
export type ChatTurnContext = Record<string, unknown> | null;

export interface ChatTopic {
  topic_family?: 'data' | 'rule' | 'template' | string | null;
  active_topic_turn_id?: number | null;
  primary_block_id?: string | null;
}

export interface ChatQueryRef {
  has_query: boolean;
  snapshot_ids: string[];
}

export interface ChatPagination {
  snapshot_id: string;
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export interface ChatBlock {
  block_id: string;
  block_type:
    | 'summary_card'
    | 'count_card'
    | 'list_table'
    | 'group_table'
    | 'field_card'
    | 'detail_card'
    | 'compare_card'
    | 'rule_card'
    | 'template_card'
    | 'guidance_card'
    | 'fallback_card';
  display_mode?: 'chat' | 'evidence_only';
  title?: string;
  text?: string;
  columns?: string[];
  rows?: Array<Record<string, unknown>>;
  metrics?: Record<string, unknown>;
  top_regions?: Array<Record<string, unknown>>;
  latest_record?: Record<string, unknown>;
  time_window?: Record<string, unknown>;
  thresholds?: Record<string, unknown>;
  template_text?: string;
  pagination?: ChatPagination;
  [key: string]: unknown;
}

export interface ChatTurnView {
  session_id: string;
  turn_id: number;
  answer_kind: ChatMode | string;
  capability: ChatCapability | string;
  final_text: string;
  user_text: string;
  blocks: ChatBlock[];
  primary_block_id?: string | null;
  query_ref: ChatQueryRef;
  created_at?: string;
}

export interface ChatMessageData {
  session_id?: string;
  turn_id?: number;
  should_query?: boolean;
  answer_kind?: string;
  capability?: string;
  conversation_closed?: boolean;
}

export interface MessageMeta {
  mode?: ChatMode | string;
  data?: ChatMessageData | null;
  turn?: ChatTurnView | null;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  createdAt: number;
  meta?: MessageMeta;
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
  lastTurnId: number;
  currentContext: ChatTurnContext;
}

export interface ChatResponse {
  session_id: string;
  turn_id: number;
  answer_kind: ChatMode | string;
  capability: ChatCapability | string;
  final_text: string;
  blocks: ChatBlock[];
  topic: ChatTopic;
  query_ref: ChatQueryRef;
  turn_context?: ChatTurnContext;
  conversation_closed: boolean;
  session_reset: boolean;
}

export interface ChatBlockResponse {
  block_type?: ChatBlock['block_type'];
  rows?: Array<Record<string, unknown>>;
  pagination?: ChatPagination;
}

export interface ChatApiErrorPayload {
  error?: string;
}
