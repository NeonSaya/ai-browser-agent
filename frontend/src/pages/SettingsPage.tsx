/** 设置页：LLM / 浏览器 / Agent / 日志 配置编辑，api_key 遮蔽。 */

import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Config, ConfigUpdate } from "../types";

export default function SettingsPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    void api.getConfig().then(setConfig);
  }, []);

  if (!config) return <div className="empty">加载配置中…</div>;

  const patch = (fn: (draft: Config) => void) => {
    setConfig((prev) => {
      if (!prev) return prev;
      const next: Config = JSON.parse(JSON.stringify(prev)) as Config;
      fn(next);
      return next;
    });
  };

  const save = async () => {
    if (!config) return;
    setSaving(true);
    setMsg(null);
    try {
      const update: ConfigUpdate = {
        llm: { ...config.llm },
        browser: { ...config.browser },
        agent: { ...config.agent },
        log: { ...config.log },
      };
      // api_key 是遮蔽值时表示未修改：清空，让后端保留已保存的 key
      if (config.llm.api_key.startsWith("****") || config.llm.api_key === "") {
        delete update.llm?.api_key;
      }
      const updated = await api.updateConfig(update);
      setConfig(updated);
      setMsg("保存成功，下个任务生效");
    } catch (e) {
      setMsg(`保存失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="toolbar">
        <h1 style={{ margin: 0 }}>设置</h1>
        <button className="btn" onClick={() => void save()} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </button>
        {msg && <span className="dim-text">{msg}</span>}
      </div>

      <h2>LLM 配置</h2>
      <div className="card form-grid">
        <Field label="Base URL">
          <input
            type="text"
            value={config.llm.base_url}
            onChange={(e) => patch((d) => (d.llm.base_url = e.target.value))}
          />
        </Field>
        <Field label={`API Key${config.llm.has_api_key ? "（已保存，遮蔽显示）" : ""}`}>
          <input
            type="password"
            placeholder={config.llm.has_api_key ? "留空保持原 key" : "输入新的 api_key"}
            value={config.llm.api_key.startsWith("****") ? "" : config.llm.api_key}
            onChange={(e) => patch((d) => (d.llm.api_key = e.target.value))}
          />
        </Field>
        <Field label="模型">
          <input
            type="text"
            value={config.llm.model}
            onChange={(e) => patch((d) => (d.llm.model = e.target.value))}
          />
        </Field>
        <Field label="Temperature">
          <input
            type="number"
            step={0.1}
            min={0}
            max={2}
            value={config.llm.temperature}
            onChange={(e) => patch((d) => (d.llm.temperature = Number(e.target.value)))}
          />
        </Field>
        <Field label="超时（秒）">
          <input
            type="number"
            value={config.llm.timeout}
            onChange={(e) => patch((d) => (d.llm.timeout = Number(e.target.value)))}
          />
        </Field>
        <Field label="重试次数">
          <input
            type="number"
            value={config.llm.max_retries}
            onChange={(e) => patch((d) => (d.llm.max_retries = Number(e.target.value)))}
          />
        </Field>
      </div>

      <h2>浏览器配置</h2>
      <div className="card form-grid">
        <Field label="模式">
          <select
            value={config.browser.mode}
            onChange={(e) => patch((d) => (d.browser.mode = e.target.value as "launch" | "cdp"))}
          >
            <option value="launch">launch（内置浏览器）</option>
            <option value="cdp">cdp（连接已有浏览器）</option>
          </select>
        </Field>
        <Field label="CDP 地址">
          <input
            type="text"
            value={config.browser.cdp_url}
            onChange={(e) => patch((d) => (d.browser.cdp_url = e.target.value))}
          />
        </Field>
        <Field label="视口宽">
          <input
            type="number"
            value={config.browser.viewport_width}
            onChange={(e) => patch((d) => (d.browser.viewport_width = Number(e.target.value)))}
          />
        </Field>
        <Field label="视口高">
          <input
            type="number"
            value={config.browser.viewport_height}
            onChange={(e) => patch((d) => (d.browser.viewport_height = Number(e.target.value)))}
          />
        </Field>
        <Field label="无头模式">
          <select
            value={String(config.browser.headless)}
            onChange={(e) => patch((d) => (d.browser.headless = e.target.value === "true"))}
          >
            <option value="false">关（显示窗口）</option>
            <option value="true">开</option>
          </select>
        </Field>
        <Field label="自动聚焦窗口">
          <select
            value={String(config.browser.auto_focus_window)}
            onChange={(e) =>
              patch((d) => (d.browser.auto_focus_window = e.target.value === "true"))
            }
          >
            <option value="true">开</option>
            <option value="false">关</option>
          </select>
        </Field>
      </div>

      <h2>Agent 配置</h2>
      <div className="card form-grid">
        <Field label="最大步数">
          <input
            type="number"
            value={config.agent.max_steps}
            onChange={(e) => patch((d) => (d.agent.max_steps = Number(e.target.value)))}
          />
        </Field>
        <Field label="步骤间隔（毫秒）">
          <input
            type="number"
            value={config.agent.step_interval_ms}
            onChange={(e) => patch((d) => (d.agent.step_interval_ms = Number(e.target.value)))}
          />
        </Field>
        <Field label="DOM 元素上限">
          <input
            type="number"
            value={config.agent.dom_max_elements}
            onChange={(e) => patch((d) => (d.agent.dom_max_elements = Number(e.target.value)))}
          />
        </Field>
        <Field label="截图最大边长">
          <input
            type="number"
            value={config.agent.screenshot_max_edge}
            onChange={(e) => patch((d) => (d.agent.screenshot_max_edge = Number(e.target.value)))}
          />
        </Field>
        <Field label="动作重试次数">
          <input
            type="number"
            value={config.agent.action_retry}
            onChange={(e) => patch((d) => (d.agent.action_retry = Number(e.target.value)))}
          />
        </Field>
      </div>

      <h2>日志配置</h2>
      <div className="card form-grid">
        <Field label="级别">
          <select
            value={config.log.level}
            onChange={(e) => patch((d) => (d.log.level = e.target.value))}
          >
            {["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </Field>
        <Field label="滚动大小">
          <input
            type="text"
            value={config.log.rotation}
            onChange={(e) => patch((d) => (d.log.rotation = e.target.value))}
          />
        </Field>
        <Field label="保留时长">
          <input
            type="text"
            value={config.log.retention}
            onChange={(e) => patch((d) => (d.log.retention = e.target.value))}
          />
        </Field>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}
