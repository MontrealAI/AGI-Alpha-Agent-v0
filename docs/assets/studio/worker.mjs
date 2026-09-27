// SPDX-License-Identifier: Apache-2.0
import { solve, verify } from "./engine.mjs";
self.onmessage = ({ data }) => {
    try {
        self.postMessage({
            report: data.report ? verify(data.report) : solve(data.input),
        });
    } catch (error) {
        self.postMessage({ error: error.message });
    }
};
