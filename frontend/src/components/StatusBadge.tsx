/** 共享 UI：状态徽章与状态机相位展示。 */

import type { TaskStatus } from "../types";

export function StatusBadge({ status }: { status: TaskStatus }) {
  const map: Record<TaskStatus, { cls: string; label: string }> = {
    pending: { cls: "dim", label: "等待" },
    running: { cls: "accent", label: "运行中" },
    done: { cls: "ok", label: "完成" },
    failed: { cls: "err", label: "失败" },
    cancelled: { cls: "warn", label: "已取消" },
  };
  const item = map[status] ?? { cls: "dim", label: status };
  return <span className={`badge ${item.cls}`}>{item.label}</span>;
}

const PHASES = [
  { key: "perceiving", label: "感知" },
  { key: "reasoning", label: "推理" },
  { key: "executing", label: "执行" },
  { key: "checking", label: "检查" },
] as const;

export function PhaseIndicator({ phase, running }: { phase: string | null; running: boolean }) {
  return (
    <div className="phases">
      {PHASES.map((p) => {
        const active = running && phase === p.key;
        return (
          <span key={p.key} className={active ? "phase active" : "phase"}>
            {p.label}
          </span>
        );
      })}
    </div>
  );
}
