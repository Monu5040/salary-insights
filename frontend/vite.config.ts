import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In development Django answers these paths; in production it serves the built SPA itself,
// so the browser always talks to one origin (design §2).
const backend = "http://localhost:8100";

export default defineConfig(({ command }) => ({
  // Built files are Django static files, under /static/ (design §2); the dev server serves
  // them from the root.
  base: command === "build" ? "/static/" : "/",
  plugins: [react()],
  server: {
    // Project-specific ports, so other local apps on 5173/8000 don't collide.
    port: 5180,
    strictPort: true,
    proxy: {
      "/api": backend,
      "/static": backend,
      "/healthz": backend,
      "/readyz": backend,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Ant Design forms render slowly under jsdom, more so on CI's smaller machines.
    testTimeout: 15_000,
  },
}));
