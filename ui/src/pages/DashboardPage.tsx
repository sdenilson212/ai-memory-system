import { useEffect, useState } from "react"
import { Brain, BookOpen, MessageSquare, Activity } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { getHealth, type HealthStatus } from "@/api/client"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

// 模拟历史趋势数据（实际可从后端扩展）
const mockTrend = [
  { day: "Mon", memories: 12, kb: 5 },
  { day: "Tue", memories: 18, kb: 6 },
  { day: "Wed", memories: 15, kb: 8 },
  { day: "Thu", memories: 23, kb: 9 },
  { day: "Fri", memories: 28, kb: 11 },
  { day: "Sat", memories: 31, kb: 12 },
  { day: "Today", memories: 0, kb: 0 },
]

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    getHealth()
      .then((h) => {
        setHealth(h)
        // 填入今日实际数据
        mockTrend[6].memories = h.memory_entries
        mockTrend[6].kb = h.kb_entries
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const stats = health
    ? [
        {
          label: "长期记忆",
          value: health.memory_entries,
          icon: Brain,
          color: "text-blue-600",
          bg: "bg-blue-50",
          desc: "LTM 条目总数",
        },
        {
          label: "知识库",
          value: health.kb_entries,
          icon: BookOpen,
          color: "text-emerald-600",
          bg: "bg-emerald-50",
          desc: "KB 条目总数",
        },
        {
          label: "活跃会话",
          value: health.active_sessions,
          icon: MessageSquare,
          color: "text-violet-600",
          bg: "bg-violet-50",
          desc: "STM 活跃中",
        },
        {
          label: "系统状态",
          value: health.status === "ok" ? "正常" : "异常",
          icon: Activity,
          color: health.status === "ok" ? "text-green-600" : "text-red-600",
          bg: health.status === "ok" ? "bg-green-50" : "bg-red-50",
          desc: "引擎连接状态",
        },
      ]
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">仪表盘</h1>
          <p className="text-slate-500 text-sm mt-1">AI 记忆系统运行概览</p>
        </div>
        <Badge
          variant={health?.status === "ok" ? "default" : "destructive"}
          className={health?.status === "ok" ? "bg-green-100 text-green-700 hover:bg-green-100" : ""}
        >
          {loading ? "连接中..." : error ? "离线" : "在线"}
        </Badge>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          无法连接到引擎：{error}。请确认 FastAPI 服务已在 localhost:8765 启动。
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4">
        {loading
          ? Array(4)
              .fill(0)
              .map((_, i) => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="pt-6">
                    <div className="h-16 bg-slate-100 rounded" />
                  </CardContent>
                </Card>
              ))
          : stats.map(({ label, value, icon: Icon, color, bg, desc }) => (
              <Card key={label} className="border-0 shadow-sm">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-slate-500">{label}</p>
                      <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
                      <p className="text-xs text-slate-400 mt-1">{desc}</p>
                    </div>
                    <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center`}>
                      <Icon size={20} className={color} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      {/* Chart */}
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">本周记忆增长趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={mockTrend}>
              <defs>
                <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="kbGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Area type="monotone" dataKey="memories" name="记忆" stroke="#3b82f6" fill="url(#memGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="kb" name="知识库" stroke="#10b981" fill="url(#kbGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base font-semibold">快速操作</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "查看全部记忆", href: "/memories", color: "bg-blue-50 text-blue-700 hover:bg-blue-100" },
              { label: "浏览知识库", href: "/knowledge", color: "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" },
              { label: "查看会话", href: "/sessions", color: "bg-violet-50 text-violet-700 hover:bg-violet-100" },
            ].map(({ label, href, color }) => (
              <a
                key={href}
                href={href}
                className={`rounded-lg px-4 py-3 text-sm font-medium text-center transition-colors cursor-pointer ${color}`}
              >
                {label}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
