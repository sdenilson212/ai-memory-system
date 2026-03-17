import { useEffect, useState } from "react"
import { Play, StopCircle, RefreshCw, Lightbulb, CheckCheck } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/hooks/use-toast"
import {
  listActiveSessions, startSession, endSession, getSessionSuggestions, analyzeText,
  saveMemory, addKB,
  type Session, type SaveSuggestion,
} from "@/api/client"

export default function SessionsPage() {
  const { toast } = useToast()
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [taskType, setTaskType] = useState("conversation")
  const [starting, setStarting] = useState(false)

  // End dialog
  const [endTarget, setEndTarget] = useState<Session | null>(null)
  const [autoFlush, setAutoFlush] = useState(true)
  const [ending, setEnding] = useState(false)
  const [endResult, setEndResult] = useState<Record<string, unknown> | null>(null)

  // Suggestions panel
  const [showAnalyze, setShowAnalyze] = useState(false)
  const [analyzeSessionId, setAnalyzeSessionId] = useState<string | null>(null)
  const [analyzeInputText, setAnalyzeInputText] = useState("")
  const [suggestions, setSuggestions] = useState<SaveSuggestion[]>([])
  const [analyzingId, setAnalyzingId] = useState<string | null>(null)
  const [savingIdx, setSavingIdx] = useState<number | null>(null)
  const [savedIdxs, setSavedIdxs] = useState<Set<number>>(new Set())

  const load = () => {
    setLoading(true)
    listActiveSessions()
      .then((r) => setSessions(r.sessions))
      .catch((e) => toast({ title: "加载失败", description: e.message, variant: "destructive" }))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleStart = () => {
    setStarting(true)
    startSession(taskType)
      .then((s) => {
        toast({ title: "会话已启动", description: `ID: ${s.session_id.slice(0, 8)}...` })
        load()
      })
      .catch((e) => toast({ title: "启动失败", description: e.message, variant: "destructive" }))
      .finally(() => setStarting(false))
  }

  const handleEnd = () => {
    if (!endTarget) return
    setEnding(true)
    endSession(endTarget.session_id, autoFlush)
      .then((r) => {
        setEndResult(r as Record<string, unknown>)
        load()
      })
      .catch((e) => toast({ title: "结束失败", description: e.message, variant: "destructive" }))
      .finally(() => setEnding(false))
  }

  const openSuggest = (sessionId: string) => {
    setAnalyzeSessionId(sessionId)
    setSuggestions([])
    setSavedIdxs(new Set())
    setShowAnalyze(true)
    setAnalyzingId(sessionId)
    getSessionSuggestions(sessionId)
      .then((r) => setSuggestions(r.suggestions))
      .catch((e) => toast({ title: "分析失败", description: e.message, variant: "destructive" }))
      .finally(() => setAnalyzingId(null))
  }

  const runAnalyzeText = () => {
    if (!analyzeInputText.trim()) return
    setAnalyzingId("text")
    analyzeText(analyzeInputText)
      .then((r) => setSuggestions(r.suggestions))
      .catch((e) => toast({ title: "分析失败", description: e.message, variant: "destructive" }))
      .finally(() => setAnalyzingId(null))
  }

  const handleSaveSuggestion = (s: SaveSuggestion, idx: number) => {
    setSavingIdx(idx)
    const promise =
      s.destination === "kb"
        ? addKB({ title: s.content.slice(0, 60), content: s.content, category: s.category, tags: s.tags })
        : saveMemory({ content: s.content, category: s.category, tags: s.tags, source: "ai-detected" })
    promise
      .then(() => {
        toast({ title: "已保存", description: `写入 ${s.destination.toUpperCase()}` })
        setSavedIdxs((prev) => new Set([...prev, idx]))
      })
      .catch((e) => toast({ title: "保存失败", description: e.message, variant: "destructive" }))
      .finally(() => setSavingIdx(null))
  }

  const confColor = (c: number) =>
    c >= 0.85
      ? "bg-green-100 text-green-700"
      : c >= 0.75
      ? "bg-amber-100 text-amber-700"
      : "bg-slate-100 text-slate-600"

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">会话管理</h1>
          <p className="text-slate-500 text-sm mt-1">
            短期记忆 (STM) — {sessions.length} 个活跃会话
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <Select value={taskType} onValueChange={setTaskType}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["conversation", "coding", "research", "writing"].map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleStart} disabled={starting} className="gap-2">
            <Play size={15} /> 新建会话
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setAnalyzeSessionId(null)
              setSuggestions([])
              setSavedIdxs(new Set())
              setAnalyzeInputText("")
              setShowAnalyze(true)
            }}
            className="gap-2"
          >
            <Lightbulb size={15} /> 分析文本
          </Button>
          <Button variant="outline" onClick={load} className="gap-2">
            <RefreshCw size={14} /> 刷新
          </Button>
        </div>
      </div>

      <ScrollArea className="h-[calc(100vh-200px)]">
        {loading ? (
          <div className="space-y-3">
            {Array(3)
              .fill(0)
              .map((_, i) => (
                <div key={i} className="h-24 bg-slate-100 rounded-lg animate-pulse" />
              ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <p className="text-4xl mb-3">💬</p>
            <p>暂无活跃会话</p>
            <p className="text-sm mt-1">点击"新建会话"开始追踪对话</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {sessions.map((s) => (
              <Card key={s.session_id} className="border-0 shadow-sm">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-violet-100 text-violet-700 text-xs">
                          {s.task_type}
                        </Badge>
                        <Badge className="bg-green-100 text-green-700 text-xs">活跃</Badge>
                      </div>
                      <p className="text-sm font-mono text-slate-600">{s.session_id}</p>
                      <div className="flex gap-4 text-xs text-slate-400">
                        <span>启动：{new Date(s.started_at).toLocaleString("zh-CN")}</span>
                        {s.event_count !== undefined && (
                          <span>事件：{s.event_count} 条</span>
                        )}
                        {s.pending_saves_count !== undefined &&
                          s.pending_saves_count > 0 && (
                            <span className="text-amber-600 font-medium">
                              待保存：{s.pending_saves_count} 条
                            </span>
                          )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5 text-blue-600 border-blue-200 hover:bg-blue-50"
                        onClick={() => openSuggest(s.session_id)}
                        disabled={analyzingId === s.session_id}
                      >
                        <Lightbulb size={14} />
                        {analyzingId === s.session_id ? "分析中..." : "建议"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5 text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => {
                          setEndTarget(s)
                          setEndResult(null)
                        }}
                      >
                        <StopCircle size={14} /> 结束
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Suggestions Dialog */}
      <Dialog
        open={showAnalyze}
        onOpenChange={(o) => {
          if (!o) setShowAnalyze(false)
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lightbulb size={18} className="text-amber-500" />
              记忆建议{" "}
              {analyzeSessionId
                ? `— 会话 ${analyzeSessionId.slice(0, 8)}...`
                : "— 文本分析"}
            </DialogTitle>
          </DialogHeader>

          {!analyzeSessionId && (
            <div className="space-y-2">
              <Textarea
                rows={4}
                placeholder="粘贴或输入对话内容，系统会分析并建议值得保存的记忆..."
                value={analyzeInputText}
                onChange={(e) => setAnalyzeInputText(e.target.value)}
              />
              <Button
                onClick={runAnalyzeText}
                disabled={analyzingId === "text" || !analyzeInputText.trim()}
                className="w-full"
              >
                {analyzingId === "text" ? "分析中..." : "开始分析"}
              </Button>
            </div>
          )}

          <Separator />

          {analyzingId && analyzingId !== "text" ? (
            <div className="py-6 text-center text-slate-400">
              <p className="animate-pulse">正在分析会话事件...</p>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="py-6 text-center text-slate-400">
              <p className="text-3xl mb-2">🤔</p>
              <p>
                {analyzeSessionId
                  ? "本会话暂无可建议的记忆"
                  : "点击「开始分析」查看建议"}
              </p>
            </div>
          ) : (
            <ScrollArea className="max-h-80">
              <div className="space-y-3 pr-1">
                {suggestions.map((s, i) => (
                  <Card
                    key={i}
                    className={`border ${
                      savedIdxs.has(i)
                        ? "border-green-200 bg-green-50"
                        : "border-slate-200"
                    }`}
                  >
                    <CardContent className="pt-3 pb-3">
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1.5">
                            <Badge className={`text-xs ${confColor(s.confidence)}`}>
                              {Math.round(s.confidence * 100)}%
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {s.destination.toUpperCase()}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {s.category}
                            </Badge>
                            <span className="text-xs text-slate-400 ml-auto">
                              {s.reason}
                            </span>
                          </div>
                          <p className="text-sm text-slate-700 leading-relaxed">
                            {s.content}
                          </p>
                          {s.tags.length > 0 && (
                            <div className="flex gap-1 mt-1.5">
                              {s.tags.map((t) => (
                                <span
                                  key={t}
                                  className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="shrink-0">
                          {savedIdxs.has(i) ? (
                            <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                              <CheckCheck size={14} /> 已保存
                            </span>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleSaveSuggestion(s, i)}
                              disabled={savingIdx === i}
                              className="text-xs"
                            >
                              {savingIdx === i ? "..." : "保存"}
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAnalyze(false)}>
              关闭
            </Button>
            {suggestions.length > 0 && savedIdxs.size < suggestions.length && (
              <Button
                onClick={() =>
                  suggestions.forEach((s, i) => {
                    if (!savedIdxs.has(i)) handleSaveSuggestion(s, i)
                  })
                }
                disabled={savingIdx !== null}
              >
                全部保存 ({suggestions.length - savedIdxs.size} 条)
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* End Session Dialog */}
      <Dialog
        open={!!endTarget}
        onOpenChange={(open) => {
          if (!open) {
            setEndTarget(null)
            setEndResult(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>结束会话</DialogTitle>
          </DialogHeader>
          {!endResult ? (
            <>
              <div className="space-y-4">
                <p className="text-sm text-slate-600">
                  会话{" "}
                  <span className="font-mono text-xs">
                    {endTarget?.session_id?.slice(0, 16)}...
                  </span>{" "}
                  即将结束。
                </p>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-amber-50 border border-amber-200">
                  <input
                    type="checkbox"
                    id="autoflush"
                    checked={autoFlush}
                    onChange={(e) => setAutoFlush(e.target.checked)}
                    className="w-4 h-4 cursor-pointer"
                  />
                  <label
                    htmlFor="autoflush"
                    className="text-sm text-amber-800 cursor-pointer"
                  >
                    <span className="font-medium">自动保存待保存条目</span>
                    <span className="block text-xs text-amber-600 mt-0.5">
                      将 pending_saves 自动写入 LTM / KB
                    </span>
                  </label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setEndTarget(null)}>
                  取消
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleEnd}
                  disabled={ending}
                >
                  {ending ? "处理中..." : "确认结束"}
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-green-50 border border-green-200">
                  <p className="text-sm font-medium text-green-800">会话已结束</p>
                  {(endResult.flushed_count as number) > 0 && (
                    <p className="text-xs text-green-600 mt-1">
                      自动保存了 {endResult.flushed_count as number} 条记忆到 LTM/KB
                    </p>
                  )}
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border text-xs font-mono text-slate-600 overflow-auto max-h-40">
                  {JSON.stringify(endResult.summary, null, 2)}
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={() => {
                    setEndTarget(null)
                    setEndResult(null)
                  }}
                >
                  关闭
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
