import {loadRuntime} from '../../../assets/pyodide_demo.js';

let pyodide;

async function loadDefaultData() {
  const [forecast, population, tree] = await Promise.all([
    fetch('forecast.json').then(r => r.json()),
    fetch('population.json').then(r => r.json()),
    fetch('tree.json').then(r => r.json()),
  ]);
  return {forecast, population, tree};
}

function renderCharts(forecastData, popData, treeData) {
  const years = forecastData.years;
  const capability = forecastData.capability;
  const sectors = forecastData.sectors;
  const solutions = popData.solutions;

  const capTrace = {
    x: years,
    y: capability,
    mode: 'lines+markers',
    name: 'AGI Capability',
    line: {color: '#d62728', width: 3},
    marker: {size: 6, symbol: 'circle', color: '#d62728'},
  };
  const capLayout = {
    margin: {t: 30, r: 20, l: 40, b: 40},
    xaxis: {title: 'Year', tickmode: 'array', tickvals: years},
    yaxis: {title: 'AGI Capability (T_AGI)', rangemode: 'tozero'},
    title: {text: 'AGI Capability vs Time', font: {size: 16}},
  };
  Plotly.newPlot('capability-chart', [capTrace], capLayout, {
    displayModeBar: false,
    responsive: true,
  });

  const timelineTraces = sectors.map(sector => {
    const symbols = sector.values.map((_, idx) =>
      years[idx] ==== sector.disruptionYear ? 'star' : 'circle'
    );
    const sizes = sector.values.map((_, idx) =>
      years[idx] ==== sector.disruptionYear ? 12 : 6
    );
    return {
      x: years,
      y: sector.values,
      mode: 'lines+markers',
      name: sector.name,
      line: {width: 2},
      marker: {
        size: sizes,
        symbol: symbols,
        line: {width: 1, color: '#000'},
      },
    };
  });
  const timelineLayout = {
    margin: {t: 30, r: 20, l: 40, b: 40},
    xaxis: {title: 'Year', tickmode: 'array', tickvals: years},
    yaxis: {title: 'Sector Performance Index', rangemode: 'tozero'},
    title: {text: 'Sector Performance and Disruption Jumps', font: {size: 16}},
    legend: {orientation: 'h', x: 0, y: -0.2},
  };
  Plotly.newPlot('timeline-chart', timelineTraces, timelineLayout, {
    displayModeBar: false,
    responsive: true,
  });

  const frontierPoints = solutions.filter(s => s.frontier);
  const otherPoints = solutions.filter(s => !s.frontier);
  const traceOthers = {
    x: otherPoints.map(p => p.time),
    y: otherPoints.map(p => p.value),
    mode: 'markers',
    name: 'Other Solutions',
    marker: {color: 'rgba(100,100,100,0.5)', size: 8, symbol: 'circle'},
    hovertemplate: 'Time: %{x} yr<br>Value: %{y} trillion<extra></extra>',
  };
  const traceFrontier = {
    x: frontierPoints.map(p => p.time),
    y: frontierPoints.map(p => p.value),
    mode: 'markers+lines',
    name: 'Pareto Frontier',
    marker: {color: '#1f77b4', size: 10, symbol: 'diamond'},
    line: {color: '#1f77b4', dash: 'solid', width: 2},
    hovertemplate: 'Time: %{x} yr<br>Value: %{y} trillion<extra></extra>',
  };
  const paretoLayout = {
    margin: {t: 30, r: 20, l: 50, b: 50},
    xaxis: {title: 'Time to Disruption (years)', dtick: 1, range: [0.5, 5.5]},
    yaxis: {title: 'Economic Value (USD trillions)', rangemode: 'tozero'},
    title: {text: 'Evolved Solutions Trade-off (Value vs Time)', font: {size: 16}},
    legend: {x: 0.02, y: 0.98},
  };
  Plotly.newPlot('pareto-chart', [traceOthers, traceFrontier], paretoLayout, {
    displayModeBar: false,
    responsive: true,
  });

  const container = document.getElementById('tree-container');
  const width = container.clientWidth;
  const height = container.clientHeight;
  const svg = d3
    .select('#tree-container')
    .append('svg')
    .attr('width', width)
    .attr('height', height);
  const g = svg.append('g').attr('transform', 'translate(40,40)');
  const root = d3.hierarchy(treeData);
  const treeLayout = d3.tree().size([height - 80, width - 80]);
  treeLayout(root);
  const linkPath = d3
    .linkHorizontal()
    .x(d => d.y)
    .y(d => d.x);
  const nodesData = root.descendants();
  let index = 0;
  function addNext() {
    if (index >= nodesData.length) {
      highlightPath();
      return;
    }
    const nd = nodesData[index];
    const parent = nd.parent;
    if (parent) {
      const newLink = g
        .append('path')
        .attr('class', 'link')
        .attr('d', linkPath({source: parent, target: nd}))
        .style('opacity', 0);
      const length = newLink.node().getTotalLength();
      newLink
        .attr('stroke-dasharray', `${length} ${length}`)
        .attr('stroke-dashoffset', length)
        .transition()
        .duration(500)
        .style('opacity', 1)
        .attr('stroke-dashoffset', 0);
    }
    const nodeG = g
      .append('g')
      .attr('class', 'node')
      .attr('transform', `translate(${nd.y},${nd.x})`)
      .style('opacity', 0);
    nodeG.append('circle').attr('r', 5);
    nodeG.append('text').attr('dx', 8).attr('dy', 3).text(nd.data.name);
    nodeG.transition().duration(500).style('opacity', 1);
    index += 1;
    setTimeout(addNext, 600);
  }
  function highlightPath() {
    const bestPath = root.data.bestPath || [];
    bestPath.forEach((name, idx) => {
      setTimeout(() => {
        g.selectAll('.node')
          .filter(d => d.data.name ==== name)
          .select('circle')
          .transition()
          .duration(400)
          .attr('fill', '#d62728');
        if (idx > 0) {
          const prev = bestPath[idx - 1];
          g.selectAll('.link')
            .filter(d => d.source.data.name ==== prev && d.target.data.name ==== name)
            .transition()
            .duration(400)
            .attr('stroke', '#d62728');
        }
      }, idx * 800);
    });
  }
  addNext();

  const logsElement = document.getElementById('logs-panel');
  logsElement.textContent = '';
  const logLines = [
    '[PlanningAgent] Initializing high-level plan and setting 5-year insight horizon.',
    '[ResearchAgent] Gathering domain data for all sectors (offline knowledge base).',
    '[StrategyAgent] Scoring sectors by AGI disruption risk…',
    '[StrategyAgent] -> Top sector identified: Transportation (imminent AGI impact).',
    '[MarketAgent] Estimating economic upside for Transportation: ~$1.5 trillion in first year.',
    '[CodeGenAgent] Generating prototype AGI solutions for Transportation sector.',
    '[SafetyGuardianAgent] Reviewing proposed strategies for alignment with safety policies.',
    '[PlanningAgent] Plan updated. Next target sector: Finance (year 2).',
    '[MemoryAgent] Logging outcome of year 1 disruption (Transportation) to ledger.',
    '----',
    '[PlanningAgent] Proceeding to next iteration with refined strategies…',
  ];
  let logIndex = 0;
  function stepLog() {
    logsElement.textContent += `${logLines[logIndex]}\n`;
    logIndex += 1;
    if (logIndex < logLines.length) {
      setTimeout(stepLog, 1000);
    }
  }
  stepLog();
}

async function runOffline() {
  try {
    if (!pyodide) {
      pyodide = await loadRuntime();
    }
  } catch (err) {
    console.warn('Pyodide failed to load', err);
  }
  const {forecast, population, tree} = await loadDefaultData();
  renderCharts(forecast, population, tree);
}

async function runOnline(key) {
  try {
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [{
          role: 'user',
          content: 'Return JSON with keys "forecast", "population" and "tree" similar to the demo dataset.'
        }],
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const text = data.choices?.[0]?.message?.content || '{}';
    const parsed = JSON.parse(text);
    if (parsed.forecast && parsed.population && parsed.tree) {
      renderCharts(parsed.forecast, parsed.population, parsed.tree);
    } else {
      throw new Error('Unexpected response');
    }
  } catch (err) {
    console.error('OpenAI request failed', err);
    await runOffline();
  }
}

document.getElementById('offline-mode')?.addEventListener('click', runOffline);
document.getElementById('online-mode')?.addEventListener('click', async () => {
  const key = window.prompt('Enter OpenAI API key');
  if (key) await runOnline(key);
});

runOffline();

document.getElementById('toggle-logs').addEventListener('click', () => {
  const panel = document.getElementById('logs-panel');
  panel.classList.toggle('hidden');
  const expanded = !panel.classList.contains('hidden');
  document.getElementById('toggle-logs').setAttribute('aria-expanded', expanded.toString());
});
