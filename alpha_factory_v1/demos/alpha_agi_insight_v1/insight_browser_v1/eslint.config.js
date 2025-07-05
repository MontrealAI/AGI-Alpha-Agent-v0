// SPDX-License-Identifier: Apache-2.0
import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
    js.configs.recommended,
    {
        files: ["**/*.ts"],
        languageOptions: {
            parser: tsParser,
            sourceType: "module",
            ecmaVersion: "latest",
        },
        plugins: { "@typescript-eslint": tsPlugin },
        rules: { ...tsPlugin.configs.recommended.rules },
    },
    {
        files: ["tests/**/*.{js,ts}"],
        languageOptions: {
            globals: { jest: "readonly" },
        },
    },
];
