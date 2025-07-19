// SPDX-License-Identifier: Apache-2.0
(function () {
  const { useState, useEffect } = React;
  function App() {
    const [timeline, setTimeline] = useState([]);
    const [sectors, setSectors] = useState([]);
    const API_BASE = '/api';
    const TOKEN = '';
    const HEADERS = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
    useEffect(() => {
      if (!timeline.length) return;
      Plotly.react('capability', [{
        x: timeline.map(p => p.year),
        y: timeline.map(p => p.capability),
        mode: 'lines', type: 'scatter'
      }], { margin: { t: 20 } });
    }, [timeline]);
    async function fetchResults(id) {
      try {
        const r = await fetch(`${API_BASE}/results/${id}`, { headers: HEADERS });
        if (!r.ok) return;
        const b = await r.json();
        const names = new Set();
        for (const p of b.forecast || []) {
          for (const s of p.affected || []) names.add(s);
        }
        setSectors(Array.from(names));
      } catch {}
    }
    async function startRun() {
      setTimeline([]);
      setSectors([]);
      const r = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...HEADERS },
        body: JSON.stringify({ horizon: 5, pop_size: 6, generations: 3 })
      });
      if (!r.ok) return;
      const data = await r.json();
      const id = data.id;
      const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/progress?token=${TOKEN}`);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.id === id) setTimeline(t => t.concat([msg]));
        } catch {}
      };
      ws.onclose = () => { fetchResults(id).catch(() => null); };
    }
    return React.createElement('div', null,
      React.createElement('h1', null, 'α‑AGI Insight Demo'),
      React.createElement('button', { onClick: startRun }, 'Run simulation'),
      React.createElement('div', { id: 'capability', style: { width: '100%', height: 300 } }),
      sectors.length ? React.createElement('div', null,
        React.createElement('h2', null, 'Disrupted sectors'),
        React.createElement('ul', null, sectors.map(s => React.createElement('li', { key: s }, s)))) : null
    );
  }
  ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
})();
