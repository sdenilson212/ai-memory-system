import { NavLink } from "react-router-dom"
import { Brain, BookOpen, MessageSquare, LayoutDashboard, Activity } from "lucide-react"
import { cn } from "@/lib/utils"

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "仪表盘" },
  { to: "/memories", icon: Brain, label: "记忆库" },
  { to: "/knowledge", icon: BookOpen, label: "知识库" },
  { to: "/sessions", icon: MessageSquare, label: "会话" },
  { to: "/status", icon: Activity, label: "系统状态" },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-slate-900 text-slate-100 flex flex-col z-20">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-700">
        <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center">
          <Brain size={18} className="text-white" />
        </div>
        <div>
          <p className="font-semibold text-sm leading-tight">AI Memory</p>
          <p className="text-xs text-slate-400">记忆管理系统</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-slate-700">
        <p className="text-xs text-slate-500">Engine: localhost:8765</p>
      </div>
    </aside>
  )
}
