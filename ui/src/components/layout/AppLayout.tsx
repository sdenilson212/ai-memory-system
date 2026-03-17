import { Outlet } from "react-router-dom"
import Sidebar from "./Sidebar"
import { Toaster } from "@/components/ui/toaster"

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 ml-56 min-h-screen">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
      <Toaster />
    </div>
  )
}
