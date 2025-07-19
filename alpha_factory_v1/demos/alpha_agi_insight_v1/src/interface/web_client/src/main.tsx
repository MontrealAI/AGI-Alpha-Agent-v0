// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import Plotly from 'plotly.js-dist';

interface ProgressMsg {
  id: string;
  year: number;
  capability: number;
}

interface ForecastPoint {
  year: number;
  capability: number;
  affected?: string[];
}

interface ResultsResponse {
  forecast: ForecastPoint[];
}

function App() {
  const [runId, setRunId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<ProgressMsg[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
  const TOKEN = import.meta.env.VITE_API_TOKEN ?? '';
  const HEADERS = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};

  useEffect(() => {
    if (!timeline.length) return;
    Plotly.react(
      'capability',
      [
        {
          x: timeline.map((p) => p.year),
          y: timeline.map((p) => p.capability),
          mode: 'lines',
          type: 'scatter',
        },
      ],
      { margin: { t: 20 } },
    );
  }, [timeline]);

  async function fetchResults(id: string) {
    try {
      const res = await fetch(`${API_BASE}/results/${id}`, { headers: HEADERS });
      if (!res.ok) return;
      const body: ResultsResponse = await res.json();
      const names = new Set<string>();
      for (const p of body.forecast) {
        for (const s of p.affected ?? []) {
          names.add(s);
        }
      }
      setSectors([...names]);
    } catch {
      // ignore
    }
  }

  async function startRun() {
    setTimeline([]);
    setSectors([]);
    const res = await fetch(`${API_BASE}/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...HEADERS,
      },
      body: JSON.stringify({ horizon: 5, pop_size: 6, generations: 3 }),
    });
    if (!res.ok) return;
    const body = await res.json();
    const id = body.id as string;
    setRunId(id);
    const wsBase = API_BASE.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/ws/progress?token=${TOKEN}`);
    ws.onmessage = (ev) => {
      try {
        const msg: ProgressMsg = JSON.parse(ev.data);
        if (msg.id === id) {
          setTimeline((t) => [...t, msg]);
        }
      } catch {
        // ignore non-JSON messages
      }
    };
    ws.onclose = () => {
      fetchResults(id).catch(() => null);
    };
  }

  return (
    <div>
      <h1>α‑AGI Insight Demo</h1>
      <button type="button" onClick={startRun}>Run simulation</button>
      <div id="capability" style={{ width: '100%', height: 300 }} />
      {sectors.length > 0 && (
        <div>
          <h2>Disrupted sectors</h2>
          <ul>
            {sectors.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
