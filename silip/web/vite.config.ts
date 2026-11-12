/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local dev: /api/* goes to uvicorn on :8000. In AWS, CloudFront routes /api/* to the API Lambda.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
