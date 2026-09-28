/* SPDX-License-Identifier: Apache-2.0 */
/* eslint-env browser */
/* global Chart */
/* eslint-disable no-undef */
import {replayChart} from '../../../../assets/replay_chart.js';
replayChart({
  logsUrl: 'assets/logs.json', label: 'Synthetic value (unitless)', color: '#e2c886',
  chartOptions: {
    plugins: {legend: {display: false}, tooltip: {displayColors: false}},
    elements: {point: {radius: 3, hoverRadius: 5}, line: {borderWidth: 2}},
    scales: {
      x: {title: {display: true, text: 'Replay step', color: '#b8c2c5'}, ticks: {color: '#b8c2c5'}, grid: {color: '#28373e'}},
      y: {title: {display: true, text: 'Synthetic value / unitless', color: '#b8c2c5'}, ticks: {color: '#b8c2c5'}, grid: {color: '#28373e'}}
    }
  }
});
