fetch('assets/logs.json').then(r=>r.json()).then(data=>{
 const ctx=document.getElementById('chart');
 const labels=data.steps;
 const values=data.values;
 new Chart(ctx,{type:'line',data:{labels, datasets:[{label:'Demo Metric',data:values, fill:false,borderColor:'blue'}]},options:{animation:{duration:2000}, responsive:true,maintainAspectRatio:false}});
});
