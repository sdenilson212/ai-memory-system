import { useEffect, useState } from "react"
import { RefreshCw, CheckCircle, XCircle, Server, HardDrive, Cpu } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { getHealth, getMemoryProfile, type HealthStatus } from "@/api/client"

export default function StatusPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const load = () => {
    setLoading(true)
    Promise.allSettled([getHealth(), getMemoryProfile()])
      .then(([h, p]) => {
        if (h.status === "fulfilled") setHealth(h.value)
        if (p.status === "fulfilled") setProfile(p.value)
        setLastRefresh(new Date())
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const isOnline = health?.status === "ok"

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">系统状态</h1>
          <p className="text-slate-500 text-sm mt-1">
            上次刷新：{lastRefresh.toLocaleTimeString("zh-CN")}
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading} className="gap-2">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          刷新
        </Button>
      </div>

      {/* Connection Status */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Server size={16} />
            引擎连接
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            {isOnline ? (
              <CheckCircle size={20} className="text-green-500" />
            ) : (
              <XCircle size={20} className="text-red-500" />
            )}
            <div>
              <p className="text-sm font-medium">{isOnline ? "引擎正常运行" : "引擎离线或无法连接"}</p>
              <p className="text-xs text-slate-400">FastAPI · localhost:8765</p>
            </div>
            <Badge
              className={`ml-auto ${isOnline ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}
            >
              {isOnline ? "online" : "offline"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "长期记忆条目", value: health?.memory_entries ?? "-", icon: HardDrive, color: "text-blue-600" },
          { label: "知识库条目", value: health?.kb_entries ?? "-", icon: HardDrive, color: "text-emerald-600" },
          { label: "活跃会话", value: health?.active_sessions ?? "-", icon: Cpu, color: "text-violet-600" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="border-0 shadow-sm">
            <CardContent className="pt-5">
              <div className="flex items-center gap-3">
                <Icon size={18} className={color} />
                <div>
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Memory Profile */}
      {profile && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">用户记忆档案</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(profile).map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between items-start py-2">
                    <span className="text-sm text-slate-500 font-medium">{key}</span>
                    <span className="text-sm text-slate-700 text-right max-w-xs">
                      {typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : String(value)}
                    </span>
                  </div>
                  <Separator />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* API Endpoints Reference */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">API 端点参考</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-xs font-mono">
            {[
              { method: "GET", path: "/health", desc: "系统健康检查" },
              { method: "GET", path: "/memory/list", desc: "列出所有记忆" },
              { method: "POST", path: "/memory/save", desc: "保存新记忆" },
              { method: "GET", path: "/memory/recall?query=...", desc: "搜索记忆" },
              { method: "GET", path: "/kb/index", desc: "知识库索引" },
              { method: "GET", path: "/kb/search?query=...", desc: "搜索知识库" },
              { method: "POST", path: "/session/start", desc: "开始新会话" },
              { method: "GET", path: "/session/active/list", desc: "活跃会话列表" },
              { method: "GET", path: "/docs", desc: "Swagger 完整 API 文档" },
            ].map(({ method, path, desc }) => (
              <div key={path} className="flex items-center gap-3 py-1.5 border-b border-slate-100 last:border-0">
                <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${
                  method === "GET" ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"
                }`}>
                  {method}
                </span>
                <span className="text-slate-600 flex-1">{path}</span>
                <span className="text-slate-400 text-right">{desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
