/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env browser */
/* global Chart */
/* eslint-disable no-undef */
import { replayChart } from "../../../../assets/replay_chart.js";
replayChart({
    logsUrl: "assets/logs.json",
    label: "Original sample index (unitless)",
    color: "#9a4b2c",
    chartOptions: {
        scales: {
            y: { title: { display: true, text: "Sample index (unitless)" } },
            x: { title: { display: true, text: "Sample step" } },
        },
    },
});
