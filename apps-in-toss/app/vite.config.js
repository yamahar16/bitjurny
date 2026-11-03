import aitDevtools from "@apps-in-toss/devtools/unplugin";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  plugins: [aitDevtools.vite()],
  build: { outDir: "dist" }
});
