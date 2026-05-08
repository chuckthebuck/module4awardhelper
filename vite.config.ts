import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  build: {
    lib: {
      entry: "modules/four_award/frontend/entry.ts",
      formats: ["es"],
      fileName: () => "four-award-app.js",
      cssFileName: "style",
    },
    outDir: "modules/four_award/static",
    emptyOutDir: true,
    cssCodeSplit: false,
  },
});
