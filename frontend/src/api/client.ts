/** REST API 客户端：同源访问（开发模式经 Vite 代理）。 */

import type { Config, ConfigUpdate, LogEntry, Task, TaskDetail } from "../types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* 忽略非 JSON 响应 */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  createTask: (instruction: string) =>
    request<{ started: boolean }>("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),

  cancelTask: () =>
    request<{ cancelling: boolean }>("/api/tasks/current/cancel", { method: "POST" }),

  listTasks: (limit = 100) => request<Task[]>(`/api/tasks?limit=${limit}`),

  getTask: (id: string) => request<TaskDetail>(`/api/tasks/${id}`),

  getConfig: () => request<Config>("/api/config"),

  updateConfig: (update: ConfigUpdate) =>
    request<Config>("/api/config", {
      method: "PUT",
      body: JSON.stringify(update),
    }),

  getLogs: (limit = 200) =>
    request<{ entries: LogEntry[] }>(`/api/logs?limit=${limit}`),
};
