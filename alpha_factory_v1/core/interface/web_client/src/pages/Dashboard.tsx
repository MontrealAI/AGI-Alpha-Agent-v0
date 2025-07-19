// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useState, FormEvent, useRef } from 'react';
import { createSandboxWorker } from '../utils/sandbox';
import Plotly from 'plotly.js-dist';
import D3LineageTree, { LineageNode } from '../D3LineageTree';
import Pareto3D, { PopulationMember } from '../Pareto3D';
import LineageTimeline from '../LineageTimeline';
import { useI18n } from '../IntlContext';
import telemetry from '../Telemetry';
import MemeCloud from '../MemeCloud';

interface SectorData {
  name: string;
  energy: number;
  disrupted?: boolean;
}

interface ForecastPoint {
  year: number;
  capability: number;
  sectors?: SectorData[];
}

export default function Dashboard() {
  const { t } = useI18n();
  const [horizon, setHorizon] = useState(5);
  const [popSize, setPopSize] = useState(6);
  const [generations, setGenerations] = useState(3);
  const [curve, setCurve] = useState('logistic');
  const [energy, setEnergy] = useState(1);
  const [entropy, setEntropy] = useState(1);
  const [adaptive, setAdaptive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [runId, setRunId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<ForecastPoint[]>([]);
  const [population, setPopulation] = useState<PopulationMember[]>([]);
  const [lineage, setLineage] = useState<LineageNode[]>([]);
  const [debate, setDebate] = useState<{ role: string; text: string }[]>([]);
  const [memeUsage, setMemeUsage] = useState<Record<string, number>>({});
  const workerRef = useRef<Worker | null>(null);
  const buffer = useRef<ForecastPoint[]>([]);
  const flushRef = useRef<number | null>(null);

  const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
  const TOKEN = import.meta.env.VITE_API_TOKEN ?? '';
  const HEADERS = TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};

  useEffect(() => {
    createSandboxWorker(new URL('../../arenaWorker.js', import.meta.url)).then(w => {
      workerRef.current = w;
      w.onmessage = (ev) => {
        const { messages, score } = ev.data;
        setDebate(messages);
        setPopulation((pop) => {
          const updated = pop.map((p) => ({ ...p, rank: p.rank + score }));
          updated.sort((a, b) => a.rank - b.rank);
          return updated;
        });
      };
    });
    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
    };
  }, []);

  useEffect(() => {
    fetchLineage().catch(() => null);
    fetchMemes().catch(() => null);
  }, []);

  useEffect(() => {
    if (adaptive) document.body.setAttribute('data-adaptive', 'true');
    else document.body.removeAttribute('data-adaptive');
  }, [adaptive]);

  useEffect(() => {
    if (!timeline.length) return;
    const years = timeline.map((p) => p.year);
    const capability = timeline.map((p) => p.capability);
    Plotly.react('capability', [
      { x: years, y: capability, mode: 'lines', type: 'scatter' },
    ], { margin: { t: 20 } });

    const bySector: Record<string, { x: number[]; y: number[] }> = {};
    for (const pt of timeline) {
      for (const s of pt.sectors ?? []) {
        bySector[s.name] = bySector[s.name] || { x: [], y: [] };
        bySector[s.name].x.push(pt.year);
        bySector[s.name].y.push(s.energy);
      }
    }
    const traces = Object.entries(bySector).map(([name, v]) => ({
      name,
      x: v.x,
      y: v.y,
      mode: 'lines',
      type: 'scatter',
    }));
    Plotly.react('sectors', traces, { margin: { t: 20 } });
  }, [timeline]);

  useEffect(() => {
    if (!population.length) return;
    Plotly.react('pareto', [
      {
        x: population.map((p) => p.effectiveness),
        y: population.map((p) => p.risk),
        mode: 'markers',
        type: 'scatter',
        marker: { color: population.map((p) => p.impact) },
      },
    ], {
      margin: { t: 20 },
      xaxis: { title: 'Effectiveness' },
      yaxis: { title: 'Risk' },
    });
  }, [population]);

  async function fetchResults(id: string) {
    const res = await fetch(`${API_BASE}/results/${id}`, { headers: HEADERS });
    if (!res.ok) return;
    const body = await res.json();
    setTimeline(body.forecast ?? []);
  }

  async function fetchPopulation(id: string) {
    const res = await fetch(`${API_BASE}/population/${id}`, { headers: HEADERS });
    if (!res.ok) return;
    const body = await res.json();
    setPopulation(body.population ?? []);
  }

  async function fetchLineage() {
    const res = await fetch(`${API_BASE}/lineage`, { headers: HEADERS });
    if (!res.ok) return;
    const body = await res.json();
    setLineage(body);
  }

  async function fetchMemes() {
    try {
      const res = await fetch(`${API_BASE}/memes`, { headers: HEADERS });
      if (!res.ok) return;
      const body = await res.json();
      setMemeUsage(body);
    } catch {
      // ignore
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setProgress(0);
    setTimeline([]);
    setPopulation([]);
    buffer.current = [];

    const res = await fetch(`${API_BASE}/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...HEADERS,
      },
      body: JSON.stringify({
        horizon: Number(horizon),
        pop_size: Number(popSize),
        generations: Number(generations),
        curve,
        energy: Number(energy),
        entropy: Number(entropy),
      }),
    });
    if (!res.ok) return;
    const body = await res.json();
    const id = body.id as string;
    setRunId(id);
    telemetry.recordRun(Number(generations));

    const wsBase = API_BASE.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/ws/progress?token=${TOKEN}`);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.id === id && horizon) {
          setProgress(msg.year / horizon);
          buffer.current.push({ year: msg.year, capability: msg.capability });
          if (flushRef.current === null) {
            flushRef.current = window.setTimeout(() => {
              setTimeline([...buffer.current]);
              flushRef.current = null;
            }, 50);
          }
        }
      } catch {
        // ignore non-JSON messages
      }
    };
    ws.onclose = () => {
      if (flushRef.current !== null) {
        clearTimeout(flushRef.current);
        flushRef.current = null;
      }
      setTimeline([...buffer.current]);
      fetchResults(id).catch(() => null);
      fetchPopulation(id).catch(() => null);
      fetchMemes().catch(() => null);
    };
  }

  function share() {
    telemetry.recordShare();
    if (navigator.share) {
      navigator.share({ title: 'AGI Dashboard', url: window.location.href }).catch(() => null);
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href).catch(() => null);
      window.alert(t('alert.urlCopied'));
    }
  }

  return (
    <div>
      <h1>{t('title.dashboard')}</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="horizon-input">{t('label.horizon')}</label>
        <input
          id="horizon-input"
          type="number"
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
        />
        <label htmlFor="pop-input">{t('label.population')}</label>
        <input
          id="pop-input"
          type="number"
          value={popSize}
          onChange={(e) => setPopSize(Number(e.target.value))}
        />
        <label htmlFor="gen-input">{t('label.generations')}</label>
        <input
          id="gen-input"
          type="number"
          value={generations}
          onChange={(e) => setGenerations(Number(e.target.value))}
        />
        <label htmlFor="energy-input">{t('label.energy')}</label>
        <input
          id="energy-input"
          type="number"
          step="any"
          value={energy}
          onChange={(e) => setEnergy(Number(e.target.value))}
        />
        <label htmlFor="entropy-input">{t('label.entropy')}</label>
        <input
          id="entropy-input"
          type="number"
          step="any"
          value={entropy}
          onChange={(e) => setEntropy(Number(e.target.value))}
        />
        <label htmlFor="curve-select">{t('label.curve')}</label>
        <select
          id="curve-select"
          value={curve}
          onChange={(e) => setCurve(e.target.value)}
        >
          <option value="logistic">{t('option.logistic')}</option>
          <option value="linear">{t('option.linear')}</option>
          <option value="exponential">{t('option.exponential')}</option>
        </select>
        <label htmlFor="adaptive">
          <input
            id="adaptive"
            type="checkbox"
            checked={adaptive}
            onChange={(e) => setAdaptive(e.target.checked)}
          />
          {t('label.adaptive')}
        </label>
        <button type="submit">{t('button.run')}</button>
      </form>
      {runId && (
        <p>
          {t('label.runId')}: {runId}{' '}
          <button type="button" onClick={share}>{t('button.share')}</button>
        </p>
      )}
      <progress
        aria-label={t('aria.progress')}
        value={progress}
        max={1}
        className="w-full"
      />
      <div id="sectors" role="img" aria-label="sectors" className="w-full h-[300px]" />
      <div id="capability" role="img" aria-label="capability" className="w-full h-[300px]" />
      <div id="pareto" role="img" aria-label="pareto" className="w-full h-[400px]" />
      <Pareto3D data={population} />
      <ul id="ranking">
        {population.map((p, i) => (
          <li key={i}>{t('label.rank')} {p.rank.toFixed(1)}</li>
        ))}
      </ul>
      <button id="start-debate" type="button" onClick={() => workerRef.current?.postMessage({ hypothesis: 'the proposal' })}>
        {t('button.startDebate')}
      </button>
      <details id="debate-panel">
        <summary>{t('summary.debate')}</summary>
        <ul>
          {debate.map((m, i) => (
            <li key={i}>
              <strong>{m.role}:</strong> {m.text}
            </li>
          ))}
        </ul>
      </details>
      <LineageTimeline data={lineage} />
      <D3LineageTree data={lineage} />
      <MemeCloud counts={memeUsage} />
    </div>
  );
}
