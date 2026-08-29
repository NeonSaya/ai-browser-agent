import { useState } from "react";
import MonitorPage from "./pages/MonitorPage";
import HistoryPage from "./pages/HistoryPage";
import LogsPage from "./pages/LogsPage";
import SettingsPage from "./pages/SettingsPage";

type Page = "monitor" | "history" | "logs" | "settings";

const NAV: { key: Page; label: string }[] = [
  { key: "monitor", label: "监控" },
  { key: "history", label: "历史" },
  { key: "logs", label: "日志" },
  { key: "settings", label: "设置" },
];

export default function App() {
  const [page, setPage] = useState<Page>("monitor");

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">WebAgent</div>
        <nav>
          {NAV.map((item) => (
            <button
              key={item.key}
              className={page === item.key ? "nav-item active" : "nav-item"}
              onClick={() => setPage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">AI 浏览器自动化</div>
      </aside>
      <main className="content">
        {page === "monitor" && <MonitorPage onGoSettings={() => setPage("settings")} />}
        {page === "history" && <HistoryPage />}
        {page === "logs" && <LogsPage />}
        {page === "settings" && <SettingsPage />}
      </main>
    </div>
  );
}
