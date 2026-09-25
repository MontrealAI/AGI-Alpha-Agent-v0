// SPDX-License-Identifier: Apache-2.0

declare global {
  interface Window {
    toast?: (msg: string) => void;
    setLlmOffline?: (offline: boolean) => void;
    setLlmApiKey?: (key: string) => void;
    llmChat?: (prompt: string) => Promise<string> | string;
    PINNER_TOKEN?: string;
    OPENAI_API_KEY?: string;
    OTEL_ENDPOINT?: string;
    IPFS_GATEWAY?: string;
    USE_GPU?: boolean;
    DEBUG?: boolean;
    pop?: import('./state/serializer').Individual[];
    coldZone?: unknown;
    recordedPrompts?: string[];
  }
}

export {};
