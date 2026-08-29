/** WebSocket 事件流：自动重连 + 订阅回调。 */

import { useEffect, useRef } from "react";
import type { WsEvent } from "../types";

type Handler = (event: WsEvent) => void;

export function useWsEvents(onEvent: Handler) {
  // 用 ref 保存最新回调，避免重连逻辑因回调变化而重建
  const handlerRef = useRef<Handler>(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/api/ws`;
    let ws: WebSocket | null = null;
    let closed = false;
    let retryTimer: number | undefined;

    const connect = () => {
      ws = new WebSocket(url);
      ws.onmessage = (msg) => {
        try {
          handlerRef.current(JSON.parse(msg.data) as WsEvent);
        } catch {
          /* 忽略无法解析的帧 */
        }
      };
      ws.onclose = () => {
        if (!closed) {
          retryTimer = window.setTimeout(connect, 2000); // 断线 2s 重连
        }
      };
    };

    connect();
    return () => {
      closed = true;
      if (retryTimer !== undefined) clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);
}
