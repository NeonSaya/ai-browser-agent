/** 监控页：创建任务 + 实时状态/步骤/截图 + 取消。 */

import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useWsEvents } from "../api/ws";
import { PhaseIndicator, StatusBadge } from "../components/StatusBadge";
import type { RunnerState, Step, TaskStatus, WsEvent } from "../types";

export default function MonitorPage({ onGoSettings }: { onGoSettings: () => void }) {
  const [instruction, setInstruction] = useState("");
  const [runner, setRunner] = useState<RunnerState | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [finishedStatus, setFinishedStatus] = useState<TaskStatus | null>(null);
  // null = 尚未加载完成；true/false = 是否已配置 API Key
  const [hasApiKey, setHasApiKey] = useState<boolean | null>(null);

  useWsEvents((event: WsEvent) => {
    switch (event.type) {
      case "snapshot":
        setRunner(event.runner);
        break;
      case "task_started":
        setError(null);
        setFinishedStatus(null);
        setSteps([]);
        setRunner((prev) =>
          prev ? { ...prev, running: true, instruction: event.instruction, status: "running" } : prev
        );
        break;
      case "step_recorded":
        setSteps((prev) => [...prev, { ...event, created_at: new Date().toISOString() }]);
        break;
      case "task_finished":
        setFinishedStatus(event.status as TaskStatus);
        setRunner((prev) => (prev ? { ...prev, running: false, status: event.status } : prev));
        if (event.error) setError(event.error);
        break;
    }
  });

  // 进入页面时：拉取配置，检测是否已配置 API Key
  useEffect(() => {
    setError(null);
    api
      .getConfig()
      .then((c) => setHasApiKey(c.llm.has_api_key))
      .catch(() => setHasApiKey(null)); // 加载失败时不阻塞用户操作
  }, []);

  const running = runner?.running ?? false;

  const submit = async () => {
    if (!instruction.trim()) return;
    if (hasApiKey === false) {
      setError("尚未配置 API Key，请先前往「设置」页配置");
      return;
    }
    setError(null);
    try {
      await api.createTask(instruction);
      setFinishedStatus(null);
      setSteps([]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "创建任务失败");
    }
  };

  const cancel = async () => {
    try {
      await api.cancelTask();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "取消失败");
    }
  };

  const latest = [...steps].reverse().find((s) => s.screenshot_url);

  return (
    <div>
      <h1>任务监控</h1>

      {hasApiKey === false && (
        <div className="apikey-banner">
          <span>尚未配置 API Key，无法启动任务</span>
          <button className="btn" onClick={onGoSettings}>
            前往设置
          </button>
        </div>
      )}

      <div className="card">
        <textarea
          value={instruction}
          placeholder="用自然语言描述任务，例如：打开百度，搜索 playwright，进入官网"
          onChange={(e) => setInstruction(e.target.value)}
          disabled={running}
        />
        <div className="toolbar">
          <button className="btn" onClick={submit} disabled={running || !instruction.trim()}>
            启动任务
          </button>
          <button className="btn danger" onClick={cancel} disabled={!running}>
            取消任务
          </button>
          {finishedStatus && !running && (
            <span>
              上个任务结果：<StatusBadge status={finishedStatus} />
            </span>
          )}
        </div>
        {error && <div className="error-text">{error}</div>}
      </div>

      {runner && (
        <div className="card">
          <div className="toolbar">
            <StatusBadge status={(runner.status as TaskStatus) ?? "pending"} />
            <span className="dim-text">{runner.instruction}</span>
          </div>
          <PhaseIndicator phase={runner.phase} running={running} />
        </div>
      )}

      <h2>步骤时间线（{steps.length}）</h2>
      {steps.length === 0 ? (
        <div className="empty">启动任务后，AI 的每一步操作会实时显示在这里</div>
      ) : (
        <div className="step-list">
          {steps.map((s) => (
            <StepItem key={`${s.step_index}-${steps.indexOf(s)}`} step={s} />
          ))}
        </div>
      )}

      {latest?.screenshot_url && (
        <>
          <h2>最新截图</h2>
          <div className="card screenshot-card">
            <img
              src={latest.screenshot_url}
              alt={`步骤 ${latest.step_index} 截图`}
              style={{ maxWidth: "100%" }}
            />
          </div>
        </>
      )}
    </div>
  );
}

function StepItem({ step }: { step: Step }) {
  const action = step.action as Record<string, unknown>;
  const type = String(action.action_type ?? "?");
  const detail =
    (action.input_text as string) ??
    (action.url as string) ??
    (action.dom_selector as string) ??
    "";
  const reason = (action.reason as string) ?? "";

  return (
    <div className="step">
      <div className="step-index">{step.step_index}</div>
      <div className="step-body">
        <div className="step-action">
          {type}
          {detail && <span className="dim-text"> · {detail}</span>}
          {step.success ? (
            <span className="badge ok" style={{ marginLeft: 8 }}>
              成功
            </span>
          ) : (
            <span className="badge err" style={{ marginLeft: 8 }}>
              失败
            </span>
          )}
        </div>
        {reason && <div className="step-reason">{reason}</div>}
        {step.error && <div className="step-error">{step.error}</div>}
        {step.screenshot_url && (
          <a href={step.screenshot_url} target="_blank" rel="noreferrer">
            查看截图
          </a>
        )}
      </div>
    </div>
  );
}
