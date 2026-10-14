import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// En développement, l'API tourne sur http://127.0.0.1:8000 (`ARISTOTE_MOCK=1 aristote serve`).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
