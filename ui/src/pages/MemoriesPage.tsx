import { useEffect, useState } from "react"
import { Search, Plus, Trash2, Edit2, Tag, Lock } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useToast } from "@/hooks/use-toast"
import {
  listMemories, recallMemory, saveMemory, updateMemory, deleteMemory,
  type MemoryEntry,
} from "@/api/client"

const CATEGORIES = ["all", "preference", "fact", "goal", "skill", "relationship", "event", "other"]
const CAT_COLORS: Record<string, string> = {
  preference: "bg-blue-100 text-blue-700",
  fact: "bg-slate-100 text-slate-700",
  goal: "bg-amber-100 text-amber-700",
  skill: "bg-green-100 text-green-700",
  relationship: "bg-pink-100 text-pink-700",
  event: "bg-violet-100 text-violet-700",
  other: "bg-gray-100 text-gray-700",
}

export default function MemoriesPage() {
  const { toast } = useToast()
  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("all")
  const [isSearching, setIsSearching] = useState(false)

  // Dialog states
  const [showAdd, setShowAdd] = useState(false)
  const [editEntry, setEditEntry] = useState<MemoryEntry | null>(null)
  const [newContent, setNewContent] = useState("")
  const [newCategory, setNewCategory] = useState("other")
  const [newTags, setNewTags] = useState("")
  const [saving, setSaving] = useState(false)

  const load = (cat?: string) => {
    setLoading(true)
    listMemories(cat === "all" ? undefined : cat)
      .then((r) => setEntries(r.entries))
      .catch((e) => toast({ title: "加载失败", description: e.message, variant: "destructive" }))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(category) }, [category])

  const handleSearch = () => {
    if (!search.trim()) { load(category); return }
    setIsSearching(true)
    recallMemory(search, category === "all" ? undefined : category)
      .then((r) => setEntries(r.results))
      .catch((e) => toast({ title: "搜索失败", description: e.message, variant: "destructive" }))
      .finally(() => setIsSearching(false))
  }

  const handleSave = () => {
    if (!newContent.trim()) return
    setSaving(true)
    const tags = newTags.split(",").map((t) => t.trim()).filter(Boolean)
    saveMemory({ content: newContent, category: newCategory, tags })
      .then(() => {
        toast({ title: "保存成功" })
        setShowAdd(false)
        setNewContent(""); setNewTags(""); setNewCategory("other")
        load(category)
      })
      .catch((e) => toast({ title: "保存失败", description: e.message, variant: "destructive" }))
      .finally(() => setSaving(false))
  }

  const handleUpdate = () => {
    if (!editEntry) return
    setSaving(true)
    const tags = newTags.split(",").map((t) => t.trim()).filter(Boolean)
    updateMemory(editEntry.id, { content: newContent, category: newCategory, tags })
      .then(() => {
        toast({ title: "更新成功" })
        setEditEntry(null)
        load(category)
      })
      .catch((e) => toast({ title: "更新失败", description: e.message, variant: "destructive" }))
      .finally(() => setSaving(false))
  }

  const handleDelete = (id: string) => {
    deleteMemory(id)
      .then(() => {
        toast({ title: "已删除" })
        setEntries((prev) => prev.filter((e) => e.id !== id))
      })
      .catch((e) => toast({ title: "删除失败", description: e.message, variant: "destructive" }))
  }

  const openEdit = (entry: MemoryEntry) => {
    setEditEntry(entry)
    setNewContent(entry.content)
    setNewCategory(entry.category)
    setNewTags(entry.tags.join(", "))
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">记忆库</h1>
          <p className="text-slate-500 text-sm mt-1">长期记忆 (LTM) — {entries.length} 条</p>
        </div>
        <Button onClick={() => { setShowAdd(true); setNewContent(""); setNewTags(""); setNewCategory("other") }} className="gap-2">
          <Plus size={16} /> 新增记忆
        </Button>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="搜索记忆内容..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>{c === "all" ? "全部分类" : c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={handleSearch} disabled={isSearching}>
          {isSearching ? "搜索中..." : "搜索"}
        </Button>
        {search && (
          <Button variant="ghost" onClick={() => { setSearch(""); load(category) }}>清除</Button>
        )}
      </div>

      {/* List */}
      <ScrollArea className="h-[calc(100vh-240px)]">
        {loading ? (
          <div className="space-y-3">
            {Array(5).fill(0).map((_, i) => (
              <div key={i} className="h-24 bg-slate-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <p className="text-4xl mb-3">🧠</p>
            <p>暂无记忆条目</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {entries.map((entry) => (
              <Card key={entry.id} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={`text-xs px-2 py-0.5 ${CAT_COLORS[entry.category] || CAT_COLORS.other}`}>
                          {entry.category}
                        </Badge>
                        {entry.sensitive && (
                          <span className="flex items-center gap-1 text-xs text-amber-600">
                            <Lock size={11} /> 敏感
                          </span>
                        )}
                        <span className="text-xs text-slate-400 ml-auto">
                          {new Date(entry.created_at).toLocaleDateString("zh-CN")}
                        </span>
                      </div>
                      <p className="text-sm text-slate-700 leading-relaxed">{entry.content}</p>
                      {entry.tags.length > 0 && (
                        <div className="flex items-center gap-1 mt-2">
                          <Tag size={11} className="text-slate-400" />
                          {entry.tags.map((t) => (
                            <span key={t} className="text-xs text-slate-500 bg-slate-100 rounded px-1.5 py-0.5">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button
                        onClick={() => openEdit(entry)}
                        className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 cursor-pointer"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 cursor-pointer"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Add Dialog */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增记忆</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700">内容</label>
              <Textarea
                className="mt-1"
                rows={4}
                placeholder="记录一条记忆，例如：我喜欢深色主题界面..."
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-slate-700">分类</label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.filter((c) => c !== "all").map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">标签（逗号分隔）</label>
                <Input className="mt-1" placeholder="ui, 偏好" value={newTags} onChange={(e) => setNewTags(e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdd(false)}>取消</Button>
            <Button onClick={handleSave} disabled={saving || !newContent.trim()}>
              {saving ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editEntry} onOpenChange={(open) => !open && setEditEntry(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑记忆</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-slate-700">内容</label>
              <Textarea className="mt-1" rows={4} value={newContent} onChange={(e) => setNewContent(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-slate-700">分类</label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.filter((c) => c !== "all").map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">标签</label>
                <Input className="mt-1" value={newTags} onChange={(e) => setNewTags(e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditEntry(null)}>取消</Button>
            <Button onClick={handleUpdate} disabled={saving}>
              {saving ? "更新中..." : "保存更改"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
