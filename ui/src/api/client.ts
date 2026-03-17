// api/client.ts — 封装所有对 FastAPI 后端的请求
const BASE = "/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.detail || err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  id: string
  content: string
  category: string
  tags: string[]
  source: string
  sensitive: boolean
  created_at: string
  updated_at?: string
}

export interface KBEntry {
  id: string
  title: string
  content: string
  category: string
  tags: string[]
  confidence: string
  confirmed: boolean
  created_at?: string
  updated_at?: string
}

export interface Session {
  session_id: string
  task_type: string
  started_at: string
  is_active: boolean
  event_count?: number
  pending_saves_count?: number
  context?: Record<string, unknown>
}

export interface HealthStatus {
  status: string
  memory_entries: number
  kb_entries: number
  active_sessions: number
}

export interface SearchResult<T> {
  query: string
  count: number
  results: T[]
}

// ── Health ─────────────────────────────────────────────────────────────────────

export const getHealth = () => request<HealthStatus>("/health")

// ── Memory (LTM) ───────────────────────────────────────────────────────────────

export const listMemories = (category?: string, limit = 50) =>
  request<{ count: number; entries: MemoryEntry[] }>(
    `/memory/list?limit=${limit}${category ? `&category=${category}` : ""}`
  )

export const recallMemory = (query: string, category?: string, max = 10) =>
  request<SearchResult<MemoryEntry>>(
    `/memory/recall?query=${encodeURIComponent(query)}&max_results=${max}${category ? `&category=${category}` : ""}`
  )

export const saveMemory = (data: {
  content: string
  category?: string
  source?: string
  tags?: string[]
}) =>
  request<{ success: boolean; entry_id: string }>("/memory/save", {
    method: "POST",
    body: JSON.stringify(data),
  })

export const updateMemory = (
  id: string,
  data: { content?: string; tags?: string[]; category?: string }
) =>
  request<{ success: boolean; entry_id: string; updated_at: string }>(
    `/memory/${id}`,
    { method: "PUT", body: JSON.stringify(data) }
  )

export const deleteMemory = (id: string) =>
  request<{ success: boolean }>(`/memory/${id}`, {
    method: "DELETE",
    body: JSON.stringify({ confirm: true }),
  })

export const getMemoryProfile = () =>
  request<Record<string, unknown>>("/memory/profile")

// ── Knowledge Base ─────────────────────────────────────────────────────────────

export const listKB = (category?: string, limit = 50) =>
  request<{ count: number; entries: KBEntry[] }>(
    `/kb/index${category ? `?category=${category}` : ""}`
  ).then((r) => r)

export const getKBIndex = () =>
  request<{ entries: KBEntry[] }>("/kb/index")

export const searchKB = (query: string, category?: string, topK = 5) =>
  request<SearchResult<KBEntry>>(
    `/kb/search?query=${encodeURIComponent(query)}&top_k=${topK}${category ? `&category=${category}` : ""}`
  )

export const addKB = (data: {
  title: string
  content: string
  category?: string
  tags?: string[]
  confidence?: string
}) =>
  request<{ success: boolean; entry_id: string; title: string }>("/kb/add", {
    method: "POST",
    body: JSON.stringify(data),
  })

export const updateKB = (
  id: string,
  data: { title?: string; content?: string; tags?: string[]; confirmed?: boolean }
) =>
  request<{ success: boolean; entry_id: string }>(`/kb/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })

export const deleteKB = (id: string) =>
  request<{ success: boolean }>(`/kb/${id}`, {
    method: "DELETE",
    body: JSON.stringify({ confirm: true }),
  })

export const importKBText = (data: {
  text: string
  category?: string
  source?: string
  title_prefix?: string
}) =>
  request<{ success: boolean; imported_count: number; entries: { id: string; title: string }[] }>(
    "/kb/import",
    { method: "POST", body: JSON.stringify(data) }
  )

// ── Session (STM) ──────────────────────────────────────────────────────────────

export const listActiveSessions = () =>
  request<{ sessions: Session[] }>("/session/active/list")

export const startSession = (task_type = "conversation") =>
  request<Session>("/session/start", {
    method: "POST",
    body: JSON.stringify({ task_type }),
  })

export const getSessionStatus = (id: string) =>
  request<Session>(`/session/${id}/status`)

export const endSession = (id: string, auto_flush = false) =>
  request<{ success: boolean; summary: Record<string, unknown>; flushed_count: number }>(
    `/session/${id}/end`,
    { method: "POST", body: JSON.stringify({ auto_flush }) }
  )

export interface SaveSuggestion {
  content: string
  destination: "ltm" | "kb"
  category: string
  confidence: number
  reason: string
  tags: string[]
}

export const getSessionSuggestions = (id: string) =>
  request<{ session_id: string; suggestion_count: number; suggestions: SaveSuggestion[] }>(
    `/session/${id}/suggestions`
  )

export const analyzeText = (text: string) =>
  request<{ suggestion_count: number; suggestions: SaveSuggestion[] }>(
    "/session/analyze",
    { method: "POST", body: JSON.stringify({ text }) }
  )
