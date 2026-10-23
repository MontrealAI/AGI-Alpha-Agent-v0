import hashlib,json,random
from pathlib import Path

root=Path(__file__).resolve().parent
rng=random.Random(20261023161712643)
def graph_task(index,kind,small=False):
    n=(5+index%4) if small else (8+index%9)
    nodes=[f'n{i}' for i in range(n)]
    edges=[{'from':nodes[i],'to':nodes[i+1],'weight':rng.randint(1,3)} for i in range(n-1)]
    edges += [{'from':nodes[0],'to':nodes[2],'weight':1},{'from':nodes[1],'to':nodes[3],'weight':2}]
    for i in range(n-3):
        if rng.random()<0.25: edges.append({'from':nodes[i],'to':nodes[min(n-1,i+3)],'weight':1})
    rng.shuffle(edges)
    order=list(nodes);rng.shuffle(order)
    seeds=[{'node':nodes[0],'amount':1+index%3}]
    if kind=='remediation-impact': seeds.append({'node':nodes[2],'amount':1})
    return {'schema':'tae/mission-v1','missionId':f'{kind}-{index:02d}', 'kind':kind,'graph':{'nodes':order,'edges':edges},'seeds':seeds,'targets':nodes[-min(4,n):]}
def flat_task(i):
    return {'schema':'tae/mission-v1','missionId':f'flat-{i:02d}','kind':'flat-reduction','rows':[{'group':f'g{j%3}','amount':((-1)**j)*(j+i+1)} for j in range(7+i)]}
missions=[graph_task(i,'bom-demand') for i in range(16)]+[graph_task(i,'remediation-impact') for i in range(16)]+[flat_task(i) for i in range(8)]
invalid=[]
for i in range(8):
    task=graph_task(i,'bom-demand',True);task['missionId']=f'invalid-{i:02d}';nodes=task['graph']['nodes'];edges=task['graph']['edges']
    if i==0: edges.append({'from':'n3','to':'n0','weight':1})
    elif i==1: nodes.append(nodes[0])
    elif i==2: edges[0]['to']='absent'
    elif i==3: edges[0]['weight']=1.5
    elif i==4: task['seeds'][0]['amount']=-1
    elif i==5: task['targets'].append('absent')
    elif i==6: task['kind']='unsupported-continuous-system'
    else:
        for edge in edges: edge['weight']=1_000_000
        task['seeds'][0]['amount']=1_000_000
    invalid.append(task)
missions+=invalid
bank={'graph':[graph_task(i,'bom-demand',True) for i in range(24)],'arithmetic':[graph_task(i+30,'bom-demand',True) for i in range(16)],'boolean':[graph_task(i+60,'remediation-impact',True) for i in range(16)],'flat':[flat_task(i+10) for i in range(8)]}
criteria={'schema':'tae.criteria.v1','frozenAt':'2026-10-23T16:18:38Z','study':'Writer4 mission-relative revalidation','population':{'total':48,'bom':16,'remediation':16,'flat':8,'invalid':8},'missionSchema':'tae/mission-v1','acceptance':'Exact target integers equal independent path-enumeration / reachability reference; invalid requests must refuse; fresh artifact receipt bound to exact mission, capability, checker and criteria. Historical evidence grants no current proof or authority.','limits':{'maxNodes':64,'maxEdges':256,'maxRows':2000,'maxAbsoluteOutput':1000000,'maxWorkers':2,'newPaidInfrastructure':False},'variants':['sliced','full-replay','no-inheritance','no-construction','old-algebra','direct-specialist'],'alternativeThreshold':{'metric':'at least 50 percent fewer repeated module qualification cases than full replay','requires':'identical acceptance/rejection decisions and fresh input/output checking on every mission, including explicit corruption/stale-context controls','economicImplication':'none without external usefulness and complete attributable costs'},'commercialTarget':{'maximumFullyAttributableUSD':100,'minimumRealizableIncrementalUSD':10000,'revenueEvidence':'absent','fullCostEvidence':'unknown','targetPredeclared':True},'qualificationBankCounts':{k:len(v) for k,v in bank.items()},'load':{'concurrency':[1,2],'missionVolumes':[8,32,128],'quality':'exact output; valid/invalid denominators separate','timing':'wall and CPU; report source qualification separately from warm task throughput'},'blindness':'Held-out task bytes and checker reside outside enterprise source directory. Proposer instructed not to inspect them. Same-controller process boundary, not hostile OS isolation or institutional blindness.','expert':'supplied deterministic direct specialist algorithm, no recruited human expert','uncertainty':'finite population with repeated seeds; descriptive intervals do not imply generalization','noPosthocTuning':'scored failures retained; fixes require a new version and separate rerun; original runs retained'}
for name,value in [('missions.json',missions),('qualification-bank.json',bank),('criteria.json',criteria)]:
    (root/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
manifest={'schema':'tae.evaluation-freeze.v1','timestamp':criteria['frozenAt'],'files':[]}
for name in ['generate-bank.py','missions.json','qualification-bank.json','criteria.json']:
    data=(root/name).read_bytes();manifest['files'].append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(root/'FREEZE.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
