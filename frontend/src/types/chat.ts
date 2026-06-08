export interface TopicSummary {
  id: string
  topic_name: string
  created_at: string
  message_count: number
}

export interface ToolCallInfo {
  tool_name: string
  arguments: Record<string, unknown>
  result?: string
}

export interface ModifiedFile {
  path: string
  change_type: "created" | "modified" | "deleted"
  pre_content: string
  post_content: string
}

export interface FileChangeActionData {
  files: ModifiedFile[]
}

export interface PatternScoreEvent {
  pattern_name: string
  category: "positive" | "negative" | "neutral" | string
  delta: number
  timestamp: string
}

export interface PatternScoreActionData {
  events: PatternScoreEvent[]
}

export interface ChatMessage {
  role: "user" | "assistant" | "action"
  timestamp: string
  content: string
  checkpoint_sha?: string
  tool_calls?: ToolCallInfo[]
  reasoning_content?: string
  // action role fields
  action_type?: string    // e.g. "file_change" | "pattern_score_change"
  action_status?: string  // e.g. "completed"
  action_data?: Record<string, unknown>
  // deprecated — kept for backward compat with old topic JSON
  modified_files?: ModifiedFile[]
}

export interface Topic {
  id: string
  topic_name: string
  created_at: string
  messages: ChatMessage[]
}

export type SSEEvent =
  | { type: "thinking_start" }
  | { type: "thinking_token"; token: string }
  | { type: "thinking_end" }
  | { type: "text_token"; token: string }
  | { type: "tool_call"; name: string; arguments: Record<string, unknown> }
  | { type: "tool_result"; name: string; result: string }
  | { type: "research_message"; agent_name: string; content: string; msg_type: string }
  | { type: "done"; new_messages: ChatMessage[]; modified_files: ModifiedFile[] }
  | { type: "error"; message: string }
