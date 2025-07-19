// SPDX-License-Identifier: Apache-2.0
import React, { useEffect, useState, FormEvent } from 'react';
import Plotly from 'plotly.js-dist';
import { useI18n } from './IntlContext';
import telemetry from './Telemetry';

interface SectorData {
  name: string;
  energy: number;
}

interface ForecastPoint {
  year: number;
  capability: number;
  sectors: SectorData[];
}

interface PopulationMember {
  effectiveness: number;
  risk: number;
  complexity: number;
  rank: number;
  impact: number;
}

interface ResultsResponse {
  forecast: ForecastPoint[];
  population?: PopulationMember[];
}

interface RunsResponse {
  ids: string[];
}

export default function App() {
  const { t } = useI18n();
  const [horizon, setHorizon] = useState(5);
  const [popSize, setPopSize] = useState(6);
  const [generations, setGenerations] = useState(3);
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [population, setPopulation] = useState<PopulationMember[]>([]);
  const [runs, setRuns] = useState<string[]>([]);
  const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '');
  const TOKEN = import.meta.env.VITE_API_TOKEN ?? '';

  useEffect(() => {
    telemetry.requestConsent(t('telemetry_consent'));
  }, [t]);

  useEffect(() => {
    refreshRuns();
    fetchLatest();
  }, []);

  async function fetchLatest() {
    try {
      const res = await fetch(`${API_BASE}/results`, {
        headers: TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {},
      });
      if (res.ok) {
        const body: ResultsResponse = await res.json();
        setData(body.forecast);
        setPopulation(body.population ?? []);
      }
    } catch {
      // ignore
    }
  }

  async function refreshRuns() {
    try {
      const res = await fetch(`${API_BASE}/runs`, {
        headers: TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {},
      });
      if (res.ok) {
        const body: RunsResponse = await res.json();
        setRuns(body.ids.slice(-20).reverse());
      }
    } catch {
      // ignore
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
        },
        body: JSON.stringify({
          horizon: Number(horizon),
          pop_size: Number(popSize),
          generations: Number(generations),
        }),
      });
      await fetchLatest();
      await refreshRuns();
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    if (!data.length) return;
    const years = data.map((p) => p.year);
    const cap = data.map((p) => p.capability);
    Plotly.react('capability', [
      { x: years, y: cap, mode: 'lines', type: 'scatter' },
    ], { margin: { t: 20 } });

    const bySector: Record<string, { x: number[]; y: number[] }> = {};
    for (const pt of data) {
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
  }, [data]);

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

  return (
    <div>
      <h1>{t('title.dashboard')}</h1>
      <form onSubmit={onSubmit}>
        <label htmlFor="horizon-input-app">{t('label.horizon')}</label>
        <input
          id="horizon-input-app"
          type="number"
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
        />
        <label htmlFor="pop-input-app">{t('label.population')}</label>
        <input
          id="pop-input-app"
          type="number"
          value={popSize}
          onChange={(e) => setPopSize(Number(e.target.value))}
        />
        <label htmlFor="gen-input-app">{t('label.generations')}</label>
        <input
          id="gen-input-app"
          type="number"
          value={generations}
          onChange={(e) => setGenerations(Number(e.target.value))}
        />
        <button type="submit">{t('button.run')}</button>
      </form>
      <button type="button" onClick={refreshRuns}>{t('label.refresh')}</button>
      <div id="sectors" role="img" aria-label="sectors" className="w-full h-[300px]" />
      <div id="capability" role="img" aria-label="capability" className="w-full h-[300px]" />
      <div id="pareto" role="img" aria-label="pareto" className="w-full h-[400px]" />
      <h2>{t('heading.lastRuns')}</h2>
      <ul>
        {runs.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </div>
  );
}
