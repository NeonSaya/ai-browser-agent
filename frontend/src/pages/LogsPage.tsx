/** 日志页：实时日志流（WS）+ 历史缓冲（REST）。 */

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useWsEvents } from "../api/ws";
import type { LogEntry, WsEvent } from "../types";

const LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] as const;

export default function LogsPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [minLevel, setMinLevel] = useState(1); // 默认 INFO 及以上
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 挂载时拉取环形缓冲中的历史日志
    void api.getLogs(500).then((r) => setEntries(r.entries));
  }, []);

  useWsEvents((event: WsEvent) => {
    if (event.type === "log") {
      const { type: _type, ...entry } = event;
      setEntries((prev) => [...prev.slice(-499), entry]);
    }
  });

  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [entries, autoScroll]);

  const visible = entries.filter((e) => LEVELS.indexOf(e.level as (typeof LEVELS)[number]) >= minLevel);

  return (
    <div>
      <div className="toolbar">
        <h1 style={{ margin: 0 }}>日志</h1>
        <select
          style={{ width: 160 }}
          value={minLevel}
          onChange={(e) => setMinLevel(Number(e.target.value))}
        >
          {LEVELS.map((l, i) => (
            <option key={l} value={i}>
              {l} 及以上
            </option>
          ))}
        </select>
        <label className="dim-text">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />{" "}
          自动滚动
        </label>
        <button className="btn ghost" onClick={() => setEntries([])}>
          清空显示
        </button>
      </div>

      <div className="card log-viewer" ref={listRef}>
        {visible.length === 0 ? (
          <div className="empty">暂无日志</div>
        ) : (
          visible.map((e, i) => (
            <div key={i} className={`log-line log-${e.level.toLowerCase()}`}>
              <span className="log-time">{e.time}</span>
              <span className="log-level">{e.level}</span>
              <span className="log-source">{e.source}</span>
              <span>{e.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
