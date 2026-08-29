/** 与后端 api/schemas.py 对应的 DTO 类型（前端独立维护，不生成）。 */

export type TaskStatus = "pending" | "running" | "done" | "failed" | "cancelled";

export interface Task {
  id: string;
  instruction: string;
  status: TaskStatus;
  max_steps: number;
  created_at: string;
  finished_at: string | null;
}

export interface Step {
  step_index: number;
  action: Record<string, unknown>;
  success: boolean;
  error: string | null;
  screenshot_url: string | null;
  created_at: string;
}

export interface TaskDetail {
  task: Task;
  steps: Step[];
}

export interface RunnerState {
  running: boolean;
  instruction: string;
  task_id: string | null;
  status: string;
  phase: string | null;
  recent_logs?: LogEntry[];
}

export interface Config {
  llm: {
    base_url: string;
    api_key: string; // 遮蔽值
    has_api_key: boolean;
    model: string;
    temperature: number;
    timeout: number;
    max_retries: number;
  };
  browser: {
    mode: "launch" | "cdp";
    cdp_url: string;
    headless: boolean;
    viewport_width: number;
    viewport_height: number;
    user_agent: string | null;
    auto_focus_window: boolean;
  };
  agent: {
    max_steps: number;
    step_interval_ms: number;
    dom_max_elements: number;
    screenshot_max_edge: number;
    action_retry: number;
  };
  log: {
    level: string;
    rotation: string;
    retention: string;
  };
}

export type ConfigUpdate = {
  llm?: Partial<Config["llm"]> & { api_key?: string | null };
  browser?: Partial<Config["browser"]>;
  agent?: Partial<Config["agent"]>;
  log?: Partial<Config["log"]>;
};

export interface LogEntry {
  time: string;
  level: string;
  source: string;
  message: string;
}

/** WS 事件联合类型 */
export type WsEvent =
  | { type: "snapshot"; runner: RunnerState }
  | { type: "task_started"; instruction: string }
  | { type: "task_finished"; task_id: string | null; status: string; error?: string }
  | {
      type: "step_recorded";
      task_id: string;
      step_index: number;
      action: Record<string, unknown>;
      success: boolean;
      error: string | null;
      screenshot_url: string | null;
    }
  | ({ type: "log" } & LogEntry);
