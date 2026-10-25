# SPDX-License-Identifier: Apache-2.0
import argparse, csv, hashlib, io, json, random
from pathlib import Path

CONTEXTS = {
    'catalog': ('sku', 'item_id', ['name', 'price', 'revision'], 'Compare the store catalog with the supplier export before an update.'),
    'inventory': ('part', 'part_code', ['description', 'quantity', 'warehouse'], 'Reconcile warehouse and stock-control exports before investigating differences.'),
    'assets': ('path', 'asset_path', ['media_type', 'size', 'checksum'], 'Compare two public website asset manifests before a release.'),
    'publications': ('record_id', 'publication_id', ['title', 'year', 'license'], 'Reconcile two publication metadata exports before updating the catalog.'),
}
SIZES = {'low': 80, 'medium': 360, 'high': 1200}
SEED = 2026102501

def csv_text(headers, rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\r\n')
    writer.writerow(headers); writer.writerows(rows)
    return stream.getvalue()

def task(context, level, instance, seed, n=None):
    left_key, right_key, fields, objective = CONTEXTS[context]
    n = n or SIZES[level]
    rng = random.Random(f'{seed}/{context}/{level}/{instance}')
    prefix = context[:3].upper() + str(instance)
    lh = [left_key] + fields + ['left_note']
    rh = [right_key] + fields + ['right_note']
    rows = []
    for i in range(n):
        key = f'{prefix}-{i:05d}'
        if context == 'catalog': vals = [f'Item {i}', f'{(i%99)+1}.{i%100:02d}', 'r'+str(i%5)]
        elif context == 'inventory': vals = [f'Part {i}', str(i%91-5), 'W'+str(i%4)]
        elif context == 'assets': vals = ['text/plain' if i%2 else 'image/svg+xml', str(100+i*7), hashlib.sha256(key.encode()).hexdigest()[:16]]
        else: vals = [f'Open report {i}', str(2000+i%26), 'CC0' if i%2 else 'CC-BY-4.0']
        rows.append([key]+vals+['left source'])
    left = [r[:] for r in rows]
    right = [r[:-1]+['right source'] for i,r in enumerate(rows) if i%13 != 0]
    for row in right:
        if rng.random() < {'low':.06,'medium':.16,'high':.26}[level]: row[2] += ' changed'
        if level == 'high' and rng.random() < .12: row[1] += ', revised\nsecond line'
    for i in range(max(2,n//13)):
        right.append([f'{prefix}-NEW-{i:04d}',f'New item {i}',str(i),'new','right source'])
    if level != 'low':
        left[2][1] = 'Québec – Δ'; right[1][1] = 'Quoted "edition", A'
        left[3][1] = '=1+1'; right[2][1] = '@SUM(A1:A2)'
        left[4][1] = '  +123'; left[5][1] = '\tformula-like label'
        left[6][0] = '001'; right[5][0] = '1'
        left[7][0] = 'Key '; right[6][0] = 'Key'
    if level == 'high':
        for i in range(24):
            left.append(left[20+i][:]); right.append(right[20+i][:])
            left[-1][2] += ' duplicate'
        order = [2,0,4,1,3]
        right = [[r[i] for i in order] for r in right]; rh = [rh[i] for i in order]
    rng.shuffle(left); rng.shuffle(right)
    inp = {'leftCsv':csv_text(lh,left),'rightCsv':csv_text(rh,right),'leftKey':left_key,'rightKey':right_key}
    return {'id':f'{context}-{level}-{instance:02d}','context':context,'complexity':level,'instance':instance,
        'objective':objective,'data_origin':'synthetic controlled nonpersonal records, not a customer engagement',
        'acceptance':'All exact matching pairs, unmatched rows, field differences, grouped actions, exact JSON, safe CSV and source references; no automatic truth resolution.',
        'inputs':inp,'deadline_seconds':30,'base_rows':n}

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['development','confirmation'],required=True);p.add_argument('--out',required=True);a=p.parse_args()
    target=Path(a.out);target.mkdir(parents=True,exist_ok=False)
    if a.phase=='development': tasks=[task('catalog','high',0,917,12),task('inventory','medium',0,917,18)]
    else:
        tasks=[task(c,l,i,SEED) for i in range(1,4) for c in CONTEXTS for l in SIZES]
        rng=random.Random(SEED+1);rng.shuffle(tasks)
        first=next(t for t in tasks if t['id']=='catalog-low-01');tasks.remove(first);tasks.insert(0,first)
    for t in tasks:
        d=target/t['id'];d.mkdir();inp=t['inputs']
        for side in ['left','right']:(d/(side+'.csv')).write_bytes(inp[side+'Csv'].encode())
        (d/'input.json').write_text(json.dumps(inp,ensure_ascii=False,indent=2)+'\n')
        (d/'brief.json').write_text(json.dumps({k:v for k,v in t.items() if k!='inputs'},ensure_ascii=False,indent=2)+'\n')
    manifest={'phase':a.phase,'seed':SEED if a.phase=='confirmation' else 917,'jobs':[t['id'] for t in tasks],'count':len(tasks)}
    (target/'TASKS.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))

if __name__=='__main__':main()
