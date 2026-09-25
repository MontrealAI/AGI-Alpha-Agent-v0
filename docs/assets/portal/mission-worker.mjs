// SPDX-License-Identifier: Apache-2.0
import { runMission } from "./mission-engine.mjs";
self.onmessage = (event) => {
    try {
        const result = runMission(event.data, (message) =>
            self.postMessage({ type: "progress", message }),
        );
        self.postMessage({ type: "result", result });
    } catch (error) {
        self.postMessage({ type: "error", message: error.message });
    }
};
