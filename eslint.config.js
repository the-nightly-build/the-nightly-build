import js from "@eslint/js";
import globals from "globals";

export default [
  {
    ignores: ["node_modules/", "press/", "press-check/", ".venv/"],
  },
  js.configs.recommended,
  {
    // nb.js is an engine-owned browser IIFE; Chart.js is loaded from a CDN.
    files: ["engine/assets/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser, Chart: "readonly" },
    },
  },
  {
    // Node config files (this file, etc.).
    files: ["*.config.js"],
    languageOptions: { globals: globals.node },
  },
  {
    // Node ESM behavior tests for the browser runtime.
    files: ["tests/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: globals.node,
    },
  },
];
