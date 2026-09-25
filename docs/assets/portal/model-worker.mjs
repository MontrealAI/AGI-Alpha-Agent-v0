// SPDX-License-Identifier: Apache-2.0
let generator;
self.onmessage = async (event) => {
    try {
        const { prompt, base } = event.data;
        if (
            typeof prompt !== "string" ||
            !prompt.trim() ||
            prompt.length > 2048
        )
            throw new Error("Enter 1–2048 characters.");
        const location = new URL(base);
        if (location.origin !== self.location.origin)
            throw new Error("Model assets must come from this site.");
        if (!generator) {
            const { pipeline, env } = await import(
                new URL("transformers.min.js", location).href
            );
            env.allowRemoteModels = false;
            env.allowLocalModels = true;
            env.localModelPath = new URL("models/", location).href;
            env.backends.onnx.wasm.wasmPaths = location.href;
            env.backends.onnx.wasm.numThreads = 1;
            env.backends.onnx.wasm.proxy = false;
            generator = await pipeline("text-generation", "gpt2", {
                device: "wasm",
                dtype: "q8",
                progress_callback: (info) => {
                    if (info.status === "progress")
                        self.postMessage({
                            type: "progress",
                            message: `Loading ${info.file}: ${Math.floor(info.progress || 0)}%`,
                        });
                    else if (info.status === "ready")
                        self.postMessage({
                            type: "progress",
                            message: "Model loaded. Generating on this device…",
                        });
                },
            });
        }
        self.postMessage({
            type: "progress",
            message: "Generating locally with GPT-2 (32 tokens maximum)…",
        });
        const output = await generator(prompt, {
            max_new_tokens: 32,
            do_sample: false,
            return_full_text: false,
        });
        const answer = output?.[0]?.generated_text;
        if (typeof answer !== "string" || !answer.trim())
            throw new Error("The model returned no text.");
        self.postMessage({
            type: "result",
            text: answer,
            backend: "onnx-wasm-q8",
        });
    } catch (error) {
        generator = undefined;
        self.postMessage({
            type: "error",
            message: `${error.message}. Retry with the full browser build and enough device memory.`,
        });
    }
};
