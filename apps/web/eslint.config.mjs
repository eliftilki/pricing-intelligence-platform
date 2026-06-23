import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import { defineConfig } from "eslint/config";

const eslintConfig = defineConfig([
  {
    ignores: [
    "node_modules/**",
    ".npm-cache/**",
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    ],
  },
  ...nextVitals,
  ...nextTs,
]);

export default eslintConfig;
