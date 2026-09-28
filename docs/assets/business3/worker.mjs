// SPDX-License-Identifier: Apache-2.0
import { solve, verify, parse } from "./engine.mjs?v=1.13.1";
import { artifacts } from "./artifacts.mjs?v=1.13.1";
self.onmessage = async ({ data }) => {
    try {
        const value =
            data.text !== undefined
                ? parse(data.text, data.verify ? 2000000 : 256000)
                : data.input;
        const report = await (data.verify ? verify(value) : solve(value));
        const files = await artifacts(report);
        self.postMessage({ id: data.id, report, files });
    } catch (error) {
        self.postMessage({ id: data.id, error: error.message });
    }
};
