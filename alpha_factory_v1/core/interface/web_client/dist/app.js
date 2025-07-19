// SPDX-License-Identifier: Apache-2.0
(function(){
  const {useState, useEffect} = React;
  function App(){
    const [horizon, setHorizon] = useState(5);
    const [popSize, setPopSize] = useState(6);
    const [generations, setGenerations] = useState(3);
    const [data, setData] = useState([]);
    const [population, setPopulation] = useState([]);
    const [runs, setRuns] = useState([]);
    const API_BASE = (window.API_BASE_URL || '/api').replace(/\/$/, '');
    const TOKEN = window.API_TOKEN || '';

    async function fetchLatest(){
      try {
        const r = await fetch(`${API_BASE}/results`, {headers: TOKEN ? {Authorization: `Bearer ${TOKEN}`} : {}});
        if(r.ok){
          const body = await r.json();
          setData(body.forecast || []);
          setPopulation(body.population || []);
        }
      } catch {}
    }

    async function fetchRuns(){
      try{
        const r = await fetch(`${API_BASE}/runs`, {headers: TOKEN ? {Authorization: `Bearer ${TOKEN}`} : {}});
        if(r.ok){
          const b = await r.json();
          const ids = (b.ids || []).slice(-20).reverse();
          setRuns(ids);
        }
      } catch {}
    }

    useEffect(()=>{ fetchRuns(); fetchLatest(); },[]);

    async function onSubmit(e){
      e.preventDefault();
      try {
        await fetch(`${API_BASE}/simulate`, {
          method:'POST',
          headers: Object.assign({'Content-Type':'application/json'}, TOKEN ? {Authorization: `Bearer ${TOKEN}`} : {}),
          body: JSON.stringify({horizon:Number(horizon), pop_size:Number(popSize), generations:Number(generations)})
        });
        await fetchLatest();
        await fetchRuns();
      } catch {}
    }

    useEffect(()=>{
      if(!data.length) return;
      const years = data.map(p=>p.year);
      const cap = data.map(p=>p.capability);
      Plotly.react('capability', [{x: years, y: cap, mode:'lines', type:'scatter'}], {margin:{t:20}});
      const bySector = {};
      data.forEach(pt => {
        (pt.sectors || []).forEach(s => {
          bySector[s.name] = bySector[s.name] || {x:[], y:[]};
          bySector[s.name].x.push(pt.year);
          bySector[s.name].y.push(s.energy);
        });
      });
      const traces = Object.keys(bySector).map(name => ({name, x: bySector[name].x, y: bySector[name].y, mode:'lines', type:'scatter'}));
      Plotly.react('sectors', traces, {margin:{t:20}});
    },[data]);

    useEffect(()=>{
      if(!population.length) return;
      Plotly.react('pareto', [{x: population.map(p=>p.effectiveness), y: population.map(p=>p.risk), mode:'markers', type:'scatter', marker:{color: population.map(p=>p.rank)}}], {margin:{t:20}, xaxis:{title:'Effectiveness'}, yaxis:{title:'Risk'}});
    },[population]);

    return React.createElement('div',null,
      React.createElement('h1',null,'AGI Simulation Dashboard'),
      React.createElement('form',{onSubmit:onSubmit},
        React.createElement('label',null,'Horizon ',React.createElement('input',{type:'number',value:horizon,onChange:e=>setHorizon(e.target.value)})),
        React.createElement('label',null,'Population ',React.createElement('input',{type:'number',value:popSize,onChange:e=>setPopSize(e.target.value)})),
        React.createElement('label',null,'Generations ',React.createElement('input',{type:'number',value:generations,onChange:e=>setGenerations(e.target.value)})),
        React.createElement('button',{type:'submit'},'Run simulation')
      ),
      React.createElement('button',{type:'button',onClick:fetchRuns},'Refresh summaries'),
      React.createElement('div',{id:'sectors',style:{width:'100%',height:300}}),
      React.createElement('div',{id:'capability',style:{width:'100%',height:300}}),
      React.createElement('div',{id:'pareto',style:{width:'100%',height:400}}),
      React.createElement('h2',null,'Last 20 simulations'),
      React.createElement('ul',null, runs.map(id => React.createElement('li',{key:id},id)))
    );
  }
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(React.createElement(App));
})();
