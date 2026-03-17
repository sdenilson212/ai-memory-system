import { BrowserRouter, Routes, Route } from "react-router-dom"
import AppLayout from "./components/layout/AppLayout"
import DashboardPage from "./pages/DashboardPage"
import MemoriesPage from "./pages/MemoriesPage"
import KnowledgePage from "./pages/KnowledgePage"
import SessionsPage from "./pages/SessionsPage"
import StatusPage from "./pages/StatusPage"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/memories" element={<MemoriesPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/status" element={<StatusPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
