import js from "@eslint/js";
import globals from "globals";
import react from "eslint-plugin-react";

export default [
  { ignores: ["dist", "coverage", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    plugins: { react },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      "react/jsx-uses-vars": "error",
      "react/jsx-uses-react": "off",
    },
  },
  {
    files: ["**/*.test.{js,jsx}", "vite.config.js"],
    languageOptions: { globals: { ...globals.node } },
  },
];
