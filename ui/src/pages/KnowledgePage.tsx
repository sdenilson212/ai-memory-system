import { useEffect, useState } from "react"
import { Search, Plus, Trash2, Edit2, Upload } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import {
  getKBIndex, searchKB, addKB, updateKB, deleteKB, importKBText,
  type KBEntry,
} from "@/api/client"

const CATEGORIES = ["all", "personal", "professional", "technical", "preference", "knowledge"]
const CONF_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-red-100 text-red-700",
}

export default function KnowledgePage() {
  const { toast } = useToast()
  const [entries, setEntries] = useState<KBEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("all")

  // Add dialog
  const [showAdd, setShowAdd] = useState(false)
  const [editEntry, setEditEntry] = useState<KBEntry | null>(null)
  const [newTitle, setNewTitle] = useState("")
  const [newContent, setNewContent] = useState("")
  const [newCategory, setNewCategory] = useState("personal")
  const [newTags, setNewTags] = useState("")
  const [newConf, setNewConf] = useState("high")
  const [saving, setSaving] = useState(false)

  // Import
  const [showImport, setShowImport] = useState(false)
  const [importText, setImportText] = useState("")
  const [importCat, setImportCat] = useState("personal")
  const [importing, setImporting] = useState(false)

  const load = () => {
    setLoading(true)
    getKBIndex()
      .then((r) => {
        const all = r.entries
        setEntries(category === "all" ? all : all.filter((e) => e.category === category))
      })
      .catch((e) => toast({ title: "加载失败", description: e.message, variant: "destructive" }))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [category])

  const handleSearch = () => {
    if (!search.trim()) { load(); return }
    searchKB(search, category === "all" ? undefined : category)
      .then((r) => setEntries(r.results))
      .catch((e) => toast({ title: "搜索失败", description: e.message, variant: "destructive" }))
  }

  const handleSave = () => {
    if (!newTitle.trim() || !newContent.trim()) return
    setSaving(true)
    const tags = newTags.split(",").map((t) => t.trim()).filter(Boolean)
    addKB({ title: newTitle, content: newContent, category: newCategory, tags, confidence: newConf })
      .then(() => {
        toast({ title: "已添加到知识库" })
        setShowAdd(false)
        load()
      })
      .catch((e) => toast({ title: "添加失败", description: e.message, variant: "destructive" }))
      .finally(() => setSaving(false))
  }

  const handleUpdate = () => {
    if (!editEntry) return
    setSaving(true)
    const tags = newTags.split(",").map((t) => t.trim()).filter(Boolean)
    updateKB(editEntry.id, { title: newTitle, content: newContent, tags })
      .then(() => {
        toast({ title: "更新成功" })
        setEditEntry(null)
        load()
      })
      .catch((e) => toast({ title: "更新失败", description: e.message, variant: "destructive" }))
      .finally(() => setSaving(false))
  }

  const handleDelete = (id: string) => {
    deleteKB(id)
      .then(() => {
        toast({ title: "已删除" })
        setEntries((prev) => prev.filter((e) => e.id !== id))
      })
      .catch((e) => toast({ title: "删除失败", description: e.message, variant: "destructive" }))
  }

  const handleImport = () => {
    if (!importText.trim()) return
    setImporting(true)
    importKBText({ text: importText, category: importCat })
      .then((r) => {
        toast({ title: `导入成功，共 ${r.imported_count} 条` })
        setShowImport(false)
        setImportText("")
        load()
      })
      .catch((e) => toast({ title: "导入失败", description: e.message, variant: "destructive" }))
      .finally(() => setImporting(false))
  }

  const openEdit = (entry: KBEntry) => {
    setEditEntry(entry)
    setNewTitle(entry.title)
    setNewContent(entry.content)
    setNewCategory(entry.category)
    setNewTags(entry.tags.join(", "))
    setNewConf(entry.confidence)
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">知识库</h1>
          <p className="text-slate-500 text-sm mt-1">结构化知识条目 (KB) — {entries.length} 条</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowImport(true)} className="gap-2">
            <Upload size={15} /> 批量导入
          </Button>
          <Button onClick={() => { setShowAdd(true); setNewTitle(""); setNewContent(""); setNewTags(""); setNewCategory("personal"); setNewConf("high") }} className="gap-2">
            <Plus size={16} /> 新增条目
          </Button>
        </div>
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="搜索知识库..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>{c === "all" ? "全部分类" : c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={handleSearch}>搜索</Button>
        {search && <Button variant="ghost" onClick={() => { setSearch(""); load() }}>清除</Button>}
      </div>

      {/* List */}
      <ScrollArea className="h-[calc(100vh-240px)]">
        {loading ? (
          <div className="space-y-3">
            {Array(4).fill(0).map((_, i) => (
              <div key={i} className="h-28 bg-slate-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <p className="text-4xl mb-3">📚</p>
            <p>暂无知识条目</p>
          </div>
        ) : (
          <div className="space-y-3 pr-2">
            {entries.map((entry) => (
              <Card key={entry.id} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-sm text-slate-900 truncate">{entry.title}</p>
                        <Badge className={`text-xs shrink-0 ${CONF_COLORS[entry.confidence] || CONF_COLORS.medium}`}>
                          {entry.confidence}
                        </Badge>
                        <Badge variant="outline" className="text-xs shrink-0">{entry.category}</Badge>
                        <span className="text-xs text-slate-400 ml-auto">
                          {entry.created_at ? new Date(entry.created_at).toLocaleDateString("zh-CN") : ""}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 leading-relaxed line-clamp-2">{entry.content}</p>
                      {entry.tags.length > 0 && (
                        <div className="flex gap-1 mt-2">
                          {entry.tags.map((t) => (
                            <span key={t} className="text-xs text-slate-500 bg-slate-100 rounded px-1.5 py-0.5">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 shrink-0">
                      <button onClick={() => openEdit(entry)} className="p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 cursor-pointer">
                        <Edit2 size={14} />
                      </button>
                      <button onClick={() => handleDelete(entry.id)} className="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 cursor-pointer">
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
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>新增知识条目</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-slate-700">标题</label>
              <Input className="mt-1" placeholder="简短标题..." value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">内容</label>
              <Textarea className="mt-1" rows={4} placeholder="详细内容..." value={newContent} onChange={(e) => setNewContent(e.target.value)} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-sm font-medium text-slate-700">分类</label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.filter(c => c !== "all").map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">置信度</label>
                <Select value={newConf} onValueChange={setNewConf}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">high</SelectItem>
                    <SelectItem value="medium">medium</SelectItem>
                    <SelectItem value="low">low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-700">标签</label>
                <Input className="mt-1" placeholder="a, b" value={newTags} onChange={(e) => setNewTags(e.target.value)} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdd(false)}>取消</Button>
            <Button onClick={handleSave} disabled={saving || !newTitle.trim() || !newContent.trim()}>
              {saving ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editEntry} onOpenChange={(open) => !open && setEditEntry(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>编辑知识条目</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-slate-700">标题</label>
              <Input className="mt-1" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">内容</label>
              <Textarea className="mt-1" rows={4} value={newContent} onChange={(e) => setNewContent(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">标签</label>
              <Input className="mt-1" value={newTags} onChange={(e) => setNewTags(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditEntry(null)}>取消</Button>
            <Button onClick={handleUpdate} disabled={saving}>{saving ? "更新中..." : "保存更改"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={showImport} onOpenChange={setShowImport}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>批量导入文本</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-slate-500">将长文本粘贴到下方，系统会自动按段落拆分为多条知识条目。</p>
            <Textarea rows={8} placeholder="粘贴文本内容..." value={importText} onChange={(e) => setImportText(e.target.value)} />
            <div>
              <label className="text-sm font-medium text-slate-700">默认分类</label>
              <Select value={importCat} onValueChange={setImportCat}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.filter(c => c !== "all").map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImport(false)}>取消</Button>
            <Button onClick={handleImport} disabled={importing || !importText.trim()}>
              {importing ? "导入中..." : "开始导入"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
