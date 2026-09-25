// SPDX-License-Identifier: Apache-2.0
import { analyseScenario, architectSearch } from "./engine.mjs";

self.onmessage = ({ data }) => {
    try {
        const result =
            data.kind === "architect"
                ? architectSearch(data.scenario)
                : analyseScenario(data.scenario);
        self.postMessage({ result });
    } catch (error) {
        self.postMessage({ error: error.message });
    }
};
