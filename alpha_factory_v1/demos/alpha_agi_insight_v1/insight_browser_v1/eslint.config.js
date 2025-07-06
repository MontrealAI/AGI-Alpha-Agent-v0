// SPDX-License-Identifier: Apache-2.0
import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

const browserGlobals = {
    window: "readonly",
    document: "readonly",
    self: "readonly",
    fetch: "readonly",
    navigator: "readonly",
    location: "readonly",
    localStorage: "readonly",
    Event: "readonly",
    DOMException: "readonly",
    indexedDB: "readonly",
    btoa: "readonly",
    crypto: "readonly",
    Blob: "readonly",
    URL: "readonly",
    importScripts: "readonly",
    caches: "readonly",
    console: "readonly",
    workbox: "readonly",
    d3: "readonly",
    performance: "readonly",
    requestAnimationFrame: "readonly",
    clearTimeout: "readonly",
    setTimeout: "readonly",
    File: "readonly",
    HashChangeEvent: "readonly",
    MessageEvent: "readonly",
};

export default [
    {
        ignores: [
            "dist/**",
            "lib/**",
            "wasm/**",
            "wasm_llm/**",
            "build/**",
            "docs/**",
            "../../../../docs/**",
            "*.min.js",
        ],
    },
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
        files: ["tests/**/*.{js,ts,mjs}"],
        languageOptions: {
            globals: {
                jest: "readonly",
                test: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterAll: "readonly",
                ...browserGlobals,
                process: "readonly",
                global: "readonly",
            },
        },
    },
    {
        files: ["**/*.js"],
        languageOptions: {
            sourceType: "module",
            ecmaVersion: "latest",
            globals: {
                ...browserGlobals,
                process: "readonly",
                module: "readonly",
                require: "readonly",
                global: "readonly",
                __dirname: "readonly",
                __filename: "readonly",
            },
        },
    },
];
