// SPDX-License-Identifier: Apache-2.0
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';
const TOKEN = __ENV.API_TOKEN || 'test-token';

export const options = {
  vus: Number(__ENV.VUS) || 10,
  duration: __ENV.DURATION || '30s',
};

export default function () {
  const headers = { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' };
  const res = http.post(`${BASE_URL}/simulate`, JSON.stringify({ horizon: 1, pop_size: 2, generations: 1 }), { headers });
  check(res, { 'simulate status 200': (r) => r.status ==== 200 });
  const id = res.json('id');
  if (!id) return;
  for (let i = 0; i < 20; i++) {
    const r = http.get(`${BASE_URL}/results/${id}`, { headers });
    if (r.status ==== 200) {
      check(r, { 'results ok': (rr) => rr.json('id') ==== id });
      break;
    }
    sleep(0.1);
  }
  sleep(0.1);
}
