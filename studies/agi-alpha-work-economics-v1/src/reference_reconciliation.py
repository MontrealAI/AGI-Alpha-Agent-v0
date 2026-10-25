import argparse, csv, hashlib, io, json, re, sqlite3, sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


def parse(text, key):
    rows = list(csv.reader(io.StringIO(text.lstrip('\ufeff'), newline=''), strict=True))
    if not rows or not rows[0] or len(set(rows[0])) != len(rows[0]) or key not in rows[0]:
        raise ValueError('Invalid headers or selected key')
    headers, data = rows[0], rows[1:]
    if any(len(row) != len(headers) for row in data):
        raise ValueError('Inconsistent row width')
    if any(row[headers.index(key)] == '' for row in data):
        raise ValueError('Empty exact key')
    return headers, data, headers.index(key)


def reference(inp):
    lh, left, lk = parse(inp['leftCsv'], inp['leftKey'])
    rh, right, rk = parse(inp['rightCsv'], inp['rightKey'])
    db = sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE l (i INTEGER PRIMARY KEY, k TEXT COLLATE BINARY); CREATE TABLE r (i INTEGER PRIMARY KEY, k TEXT COLLATE BINARY);')
    db.executemany('INSERT INTO l VALUES (?,?)', [(i, row[lk]) for i, row in enumerate(left)])
    db.executemany('INSERT INTO r VALUES (?,?)', [(i, row[rk]) for i, row in enumerate(right)])
    pairs = [list(p) for p in db.execute('SELECT l.i,r.i FROM l JOIN r ON l.k=r.k ORDER BY l.i,r.i')]
    missing_left = [r[0] for r in db.execute('SELECT l.i FROM l WHERE NOT EXISTS(SELECT 1 FROM r WHERE r.k=l.k) ORDER BY l.i')]
    missing_right = [r[0] for r in db.execute('SELECT r.i FROM r WHERE NOT EXISTS(SELECT 1 FROM l WHERE l.k=r.k) ORDER BY r.i')]
    db.close()
    fields = [(name, i, rh.index(name)) for i, name in enumerate(lh) if i != lk and name in rh and rh.index(name) != rk]
    conflicts = [(a, b, name, left[a][i], right[b][j], fi) for a, b in pairs for fi, (name, i, j) in enumerate(fields) if left[a][i] != right[b][j]]
    diffs = []
    for a, b, name, lv, rv, fi in conflicts:
        diffs.append({'occurrence':f'conflict:{a}:{b}', 'key':left[a][lk], 'kind':'conflict', 'leftRow':a + 1, 'rightRow':b + 1, 'field':name, 'leftValue':lv, 'rightValue':rv})
    for i in missing_left:
        diffs.append({'occurrence':f'left:{i}', 'key':left[i][lk], 'kind':'missing_from_right', 'leftRow':i + 1, 'rightRow':'', 'field':'', 'leftValue':json.dumps(left[i], ensure_ascii=False, separators=(',',':')), 'rightValue':''})
    for i in missing_right:
        diffs.append({'occurrence':f'right:{i}', 'key':right[i][rk], 'kind':'missing_from_left', 'leftRow':'', 'rightRow':i + 1, 'field':'', 'leftValue':'', 'rightValue':json.dumps(right[i], ensure_ascii=False, separators=(',',':'))})
    return {'left_headers':lh, 'left_rows':left, 'left_key_index':lk, 'right_headers':rh, 'right_rows':right, 'right_key_index':rk, 'pairs':pairs, 'missing_left':missing_left, 'missing_right':missing_right, 'shared_fields':fields, 'conflicts':conflicts, 'differences':diffs}


def frozen(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',',':'))


def csv_rows(text):
    return list(csv.reader(io.StringIO(text, newline=''), strict=True))


def safe(value):
    s = str(value)
    return "'" + s if re.match(r'^(?:\s*[=+\-@]|[\t\r\n])', s) else s


def verify_guide(inp, result):
    expected = reference(inp)
    checks, failures = [], []
    def check(name, passed, detail=None):
        checks.append(name)
        if not passed: failures.append({'check':name, 'detail':detail})
    check('schema', result.get('schema') == 'ti-catalogue-result/v1')
    for side in ['left','right']:
        raw=inp[side+'Csv'].encode()
        check(side+'_input_identity', result.get(side+'Identity') == {'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)})
    fields=['occurrence','key','kind','leftRow','rightRow','field','leftValue','rightValue']
    actual=result.get('differences',[])
    check('exact_difference_multiset', Counter(frozen({k:d.get(k) for k in fields}) for d in actual) == Counter(frozen(d) for d in expected['differences']))
    check('unique_difference_ids', len({d.get('id') for d in actual}) == len(actual))
    observed=result.get('metrics',{})
    pairs=expected['pairs']; diffs=expected['differences']
    want={'leftRows':len(expected['left_rows']), 'rightRows':len(expected['right_rows']), 'matchedPairs':len(pairs), 'unmatchedRows':len(expected['missing_left'])+len(expected['missing_right']), 'unmatchedKeys':len({d['key'] for d in diffs if d['kind']!='conflict'}), 'conflictingPairs':len({(a,b) for a,b,*_ in expected['conflicts']}), 'fieldDifferences':len(expected['conflicts']), 'actionGroups':len({d['key'] for d in diffs}), 'evidenceReferences':len({d['occurrence'] for d in diffs}), 'comparedColumns':[x[0] for x in expected['shared_fields']]}
    for key,value in want.items(): check('metric_'+key, observed.get(key)==value, {'expected':value,'actual':observed.get(key)})
    for side in ['left','right']:
        rows=expected[side+'_rows']; ki=expected[side+'_key_index']; counts=Counter(row[ki] for row in rows)
        check('metric_'+side+'_duplicates', observed.get(side+'Duplicates')=={'keys':sum(v>1 for v in counts.values()),'extraRows':sum(v-1 for v in counts.values())})
        check('metric_'+side+'_unshared', observed.get('unshared'+side.title())==[h for i,h in enumerate(expected[side+'_headers']) if i!=ki and h not in want['comparedColumns']])
    actions=result.get('resolution',{}).get('actions',[])
    desired={}
    for d in diffs: desired.setdefault(d['key'],set()).add(d['occurrence'])
    check('action_group_keys', Counter(a.get('key') for a in actions)==Counter(desired.keys()))
    allrefs=[]
    for action in actions:
        refs=action.get('occurrences',[]); allrefs.extend(refs)
        check('action_'+str(action.get('id'))+'_coverage', set(refs)==desired.get(action.get('key'),set()) and len(refs)==len(set(refs)))
        members=[d for d in actual if d.get('key')==action.get('key')]
        check('action_'+str(action.get('id'))+'_bindings', all(d.get('action')==action.get('id') for d in members))
        source=[d for d in diffs if d['key']==action.get('key')]
        left_indices=sorted({d['leftRow']-1 for d in source if d['leftRow']!=''})
        right_indices=sorted({d['rightRow']-1 for d in source if d['rightRow']!=''})
        check('action_'+str(action.get('id'))+'_left_rows',action.get('leftRows')==left_indices)
        check('action_'+str(action.get('id'))+'_right_rows',action.get('rightRows')==right_indices)
        kinds={d['kind'] for d in source}
        typ='missing_from_left' if 'missing_from_left' in kinds else 'missing_from_right' if 'missing_from_right' in kinds else 'review_shared_values'
        check('action_'+str(action.get('id'))+'_type',action.get('type')==typ)
        next_step='Check whether this key belongs in the other catalog; retain every referenced occurrence before deciding.' if typ!='review_shared_values' else 'Review all referenced differences for this exact key and choose the authoritative values; do not auto-overwrite.'
        check('action_'+str(action.get('id'))+'_next_step',action.get('nextStep')==next_step)
    check('complete_reference_coverage', Counter(allrefs)==Counter(set(d['occurrence'] for d in diffs)))
    resolution=result.get('resolution',{})
    check('coverage_counts',resolution.get('coverage')=={'originalOccurrences':want['evidenceReferences'],'coveredOccurrences':want['evidenceReferences'],'complete':True,'missing':[],'duplicates':[]})
    burden=resolution.get('burden',{})
    check('burden_counts',burden=={'pairwiseReviewItems':want['evidenceReferences'],'groupedActions':want['actionGroups'],'groupingReduction':want['evidenceReferences']-want['actionGroups'],'timeSavedClaim':False,'sameTaskSuperiority':False})
    check('no_group_automatic_truth_resolution',resolution.get('automaticallyResolved') is False and resolution.get('externalAuthority') is False)
    limitations=result.get('limitations',{})
    check('no_automatic_truth_resolution', limitations.get('automaticallyResolved') is False)
    check('no_undeclared_authority', limitations.get('authority') == 'none')
    return {'checks':len(checks),'failures':failures,'accepted':not failures,'expected_counts':want,'oracle':'Python csv + independent SQLite exact join; no producer imports'}


def verify_native(inp, directory):
    expected=reference(inp); p=Path(directory); failures=[]; checks=[]
    def check(name,passed):
        checks.append(name)
        if not passed: failures.append({'check':name})
    joined=[['left.'+x for x in expected['left_headers']]+['right.'+x for x in expected['right_headers']]]
    joined += [expected['left_rows'][a]+expected['right_rows'][b] for a,b in expected['pairs']]
    artifacts={'joined.csv':joined, 'unmatched-left.csv':[expected['left_headers']]+[expected['left_rows'][i] for i in expected['missing_left']], 'unmatched-right.csv':[expected['right_headers']]+[expected['right_rows'][i] for i in expected['missing_right']], 'conflicts.csv':[['key','left_data_row','right_data_row','field','left_value','right_value']]+[[expected['left_rows'][a][expected['left_key_index']],a+1,b+1,name,lv,rv] for a,b,name,lv,rv,_ in expected['conflicts']]}
    for name,rows in artifacts.items():
        target=p/name
        check(name+'_present',target.is_file())
        if target.is_file():
            actual=csv_rows(target.read_text()); want=[[safe(v) for v in row] for row in rows]
            check(name+'_headers',actual[:1]==want[:1]); check(name+'_records',Counter(map(tuple,actual[1:]))==Counter(map(tuple,want[1:])))
    exact_path=p/'exact-result.json'
    check('exact_json_present',exact_path.is_file())
    if exact_path.is_file():
        data=json.loads(exact_path.read_text()); mission=data.get('mission',{}); result=data.get('result',{})
        check('exact_json_schema',data.get('schemaVersion')==1)
        for side in ['left','right']:
            check(side+'_exact_rows',mission.get(side,{}).get('rows')==expected[side+'_rows'])
            check(side+'_exact_headers',mission.get(side,{}).get('headers')==expected[side+'_headers'])
            check(side+'_exact_key',mission.get(side,{}).get('key')==inp[side+'Key'] and mission.get(side,{}).get('keyIndex')==expected[side+'_key_index'])
        methods=result.get('strategies',[])
        check('all_four_methods',Counter(x.get('strategyId') for x in methods)==Counter(['nested_scan','fixed_right_hash','smaller_side_hash','sort_merge']))
        for method in methods:
            check('method_'+method.get('strategyId','unknown')+'_pairs',method.get('pairs')==expected['pairs'])
        rec=result.get('reconciliation',{})
        check('exact_unmatched_left',rec.get('unmatchedLeft')==expected['missing_left']);check('exact_unmatched_right',rec.get('unmatchedRight')==expected['missing_right'])
        check('exact_matched_count',rec.get('matchedPairs')==len(expected['pairs']))
        check('exact_shared_fields',rec.get('sharedFields')==[{'name':name,'leftColumn':i,'rightColumn':j} for name,i,j in expected['shared_fields']])
        actual_conflicts=[]
        for c in rec.get('conflicts',[]):
            actual_conflicts.extend((c.get('leftIndex'),c.get('rightIndex'),fi) for fi in c.get('fieldIndices',[]))
        check('exact_conflict_fields',Counter(actual_conflicts)==Counter((a,b,fi) for a,b,name,lv,rv,fi in expected['conflicts']))
        comparison=p/'comparison.json'
        check('comparison_present',comparison.is_file())
        if comparison.is_file(): check('comparison_consistency',json.loads(comparison.read_text())==result)
    return {'checks':len(checks),'failures':failures,'accepted':not failures,'oracle':'Python csv + independent SQLite exact join; no producer imports'}


class MetricParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.metrics={}; self.stack=[]; self.text=[]; self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs); self.stack.append((tag,attrs.get('data-metric'))) if tag not in ['meta','br','hr','img','input','link'] else None
        if attrs.get('data-metric'): self.metrics.setdefault(attrs['data-metric'],[])
        if tag=='a' and attrs.get('href'): self.links.append(attrs['href'])
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag: self.stack=self.stack[:i]; break
    def handle_data(self,data):
        self.text.append(data)
        for _,key in self.stack:
            if key: self.metrics[key].append(data)


def verify_exports(inp,result,directory):
    p=Path(directory); checks=[]; failures=[]
    def check(name,passed,detail=None):
        checks.append(name)
        if not passed: failures.append({'check':name,'detail':detail})
    fields=['id','occurrence','action','key','kind','leftRow','rightRow','field','leftValue','rightValue']
    rows=[fields]+[[safe(d.get(k,'')) for k in fields] for d in result.get('differences',[])]
    target=p/'all-differences.csv';check('all_differences_present',target.is_file())
    if target.is_file():
        actual=csv_rows(target.read_text());check('all_differences_headers',actual[:1]==rows[:1]);check('all_differences_values',Counter(map(tuple,actual[1:]))==Counter(map(tuple,rows[1:])))
    actions=result.get('resolution',{}).get('actions',[])
    want=[['action','exact_key','type','left_data_rows','right_data_rows','original_review_occurrences','next_step']]
    for a in actions:
        want.append([safe(v) for v in [a['id'],a['key'],a['type'],';'.join(str(i+1) for i in a['leftRows']),';'.join(str(i+1) for i in a['rightRows']),';'.join(a['occurrences']),a['nextStep']]])
    target=p/'action-plan.csv';check('action_plan_present',target.is_file())
    if target.is_file():
        actual=csv_rows(target.read_text());check('action_plan_headers',actual[:1]==want[:1]);check('action_plan_values',Counter(map(tuple,actual[1:]))==Counter(map(tuple,want[1:])))
    summary_path=p/'summary.json';check('summary_present',summary_path.is_file())
    if summary_path.is_file():
        summary=json.loads(summary_path.read_text())
        check('summary_schema',summary.get('schema')=='work-economics-delivery/v1')
        check('summary_metrics',summary.get('metrics')==result.get('metrics'))
        check('summary_no_automatic_truth_correction',summary.get('automatic_source_correction') is False)
        check('summary_new_human_trial_not_run',summary.get('new_human_trial')=='NOT_RUN')
        check('summary_market_comparison_modelled',summary.get('market_comparison')=='MODELLED_WITH_SOURCED_BENCHMARKS')
        check('summary_complete_cost_unknown',summary.get('fully_allocated_cost')=='UNKNOWN')
        check('summary_source_commit',summary.get('source_commit')=='f836f06e8351e64db1da770e16e304b5feb01f28')
        check('summary_review_decision',summary.get('decision')=='REVIEW_EXCEPTIONS')
        check('summary_job_id_present',isinstance(summary.get('job_id'),str) and bool(summary['job_id']))
        retained=summary.get('retained_capability_sha256')
        check('summary_retained_hash',retained is None or isinstance(retained,str) and bool(re.fullmatch('[0-9a-f]{64}',retained)))
        check('summary_limitations_present',isinstance(summary.get('limitations'),list) and len(summary['limitations'])>0)
    html_path=p/'summary.html';check('summary_html_present',html_path.is_file())
    if html_path.is_file():
        parser=MetricParser();parser.feed(html_path.read_text())
        text=' '.join(parser.text)
        check('summary_html_source_owner_decision','Conflicts require a source-owner decision.' in text)
        for key,value in result.get('metrics',{}).items():
            if isinstance(value,int):
                rendered=''.join(parser.metrics.get(key,[])).strip().replace(',','')
                check('summary_html_metric_'+key,rendered==str(value),{'actual':rendered,'expected':str(value)})
        local_links=[x.split('#')[0] for x in parser.links if not re.match(r'^(?:[a-z]+:|#)',x)]
        check('summary_html_local_links',all((p/x).is_file() for x in local_links))
    return {'checks':len(checks),'failures':failures,'accepted':not failures,'oracle':'CSV export safety, summary cross-check and local-link inspection'}


def verify_all(inp,directory):
    p=Path(directory); guide_path=p/'guide-result.json'
    if not guide_path.is_file(): return {'checks':1,'failures':[{'check':'guide_result_present'}],'accepted':False}
    result=json.loads(guide_path.read_text())
    sections={'native':verify_native(inp,p),'guide':verify_guide(inp,result),'exports':verify_exports(inp,result,p)}
    return {'checks':sum(v['checks'] for v in sections.values()),'failures':[dict(section=k,**f) for k,v in sections.items() for f in v['failures']],'accepted':all(v['accepted'] for v in sections.values()),'sections':sections,'oracle':'Independent-role Python CSV/SQLite reference; producer modules are not imported; new human trial NOT RUN; market comparison MODELLED_WITH_SOURCED_BENCHMARKS'}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('--guide-result'); ap.add_argument('--native-dir'); ap.add_argument('--all-dir'); ap.add_argument('--out'); args=ap.parse_args()
    inp=json.loads(Path(args.input).read_text())
    report=verify_all(inp,args.all_dir) if args.all_dir else verify_guide(inp,json.loads(Path(args.guide_result).read_text())) if args.guide_result else verify_native(inp,args.native_dir)
    raw=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.out: Path(args.out).write_text(raw)
    print(raw,end=''); return 0 if report['accepted'] else 1


if __name__=='__main__': sys.exit(main())
