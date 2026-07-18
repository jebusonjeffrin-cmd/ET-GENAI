import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RoleProvider } from "./layout/RoleContext";
import Sidebar from "./components/Sidebar";
import Home from "./pages/Home";
import DocumentLibrary from "./pages/DocumentLibrary";
import KnowledgeGraphExplorer from "./pages/KnowledgeGraphExplorer";
import Copilot from "./pages/Copilot";
import Maintenance from "./pages/Maintenance";
import Admin from "./pages/Admin";

export default function App() {
  return (
    <RoleProvider>
      <BrowserRouter>
        <div className="flex h-screen bg-slate-50 text-slate-900">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/documents" element={<DocumentLibrary />} />
              <Route path="/graph" element={<KnowledgeGraphExplorer />} />
              <Route path="/copilot" element={<Copilot />} />
              <Route path="/maintenance" element={<Maintenance />} />
              <Route path="/admin" element={<Admin />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </RoleProvider>
  );
}
