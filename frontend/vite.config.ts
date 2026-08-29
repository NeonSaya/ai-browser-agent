import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发模式：/api 代理到本机 FastAPI；生产模式：前端由 FastAPI 静态托管，无需代理
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
