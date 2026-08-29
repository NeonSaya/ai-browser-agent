/** 历史页：任务列表 + 步骤详情与截图回放。 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import type { Task, TaskDetail } from "../types";

export default function HistoryPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState<TaskDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setTasks(await api.listTasks());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openDetail = async (id: string) => {
    setSelected(await api.getTask(id));
  };

  const fmt = (iso: string) => new Date(iso).toLocaleString("zh-CN", { hour12: false });

  return (
    <div>
      <div className="toolbar">
        <h1 style={{ margin: 0 }}>任务历史</h1>
        <button className="btn ghost" onClick={() => void refresh()} disabled={loading}>
          刷新
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="empty">还没有历史任务</div>
      ) : (
        tasks.map((t) => (
          <div key={t.id} className="card task-card" onClick={() => void openDetail(t.id)}>
            <div className="toolbar">
              <StatusBadge status={t.status} />
              <span className="dim-text">{fmt(t.created_at)}</span>
            </div>
            <div className="task-instruction">{t.instruction}</div>
          </div>
        ))
      )}

      {selected && (
        <div className="modal-mask" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="toolbar">
              <StatusBadge status={selected.task.status} />
              <span className="dim-text">{selected.task.instruction}</span>
              <button className="btn ghost" onClick={() => setSelected(null)}>
                关闭
              </button>
            </div>
            {selected.steps.length === 0 ? (
              <div className="empty">该任务没有记录到步骤</div>
            ) : (
              selected.steps.map((s) => (
                <div key={s.step_index} className="step">
                  <div className="step-index">{s.step_index}</div>
                  <div className="step-body">
                    <div className="step-action">
                      {String(s.action.action_type ?? "?")}
                      {s.success ? (
                        <span className="badge ok" style={{ marginLeft: 8 }}>
                          成功
                        </span>
                      ) : (
                        <span className="badge err" style={{ marginLeft: 8 }}>
                          失败
                        </span>
                      )}
                    </div>
                    {(s.action.reason as string) && (
                      <div className="step-reason">{s.action.reason as string}</div>
                    )}
                    {s.error && <div className="step-error">{s.error}</div>}
                    {s.screenshot_url && (
                      <img
                        className="step-thumb"
                        src={s.screenshot_url}
                        alt={`步骤 ${s.step_index}`}
                        onClick={() => window.open(s.screenshot_url as string, "_blank")}
                      />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
