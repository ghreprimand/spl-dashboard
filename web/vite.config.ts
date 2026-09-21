import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: process.env.SPL_API_TARGET ?? "http://localhost:8000",
        changeOrigin: false,
      },
      "/ws": {
        target: (process.env.SPL_API_TARGET ?? "http://localhost:8000").replace(
          /^http/,
          "ws",
        ),
        ws: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
