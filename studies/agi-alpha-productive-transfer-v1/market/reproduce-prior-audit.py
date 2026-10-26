# SPDX-License-Identifier: Apache-2.0
"""Portable adapter for the preserved prior audit; no audit logic is rewritten.

Requires Python 3.11+ and only its standard library. The data archive can be used
independently of the original workspace. --verify-only checks bytes and AST
derivation without running the 19,440-history arithmetic audit.
"""
import argparse
import ast
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time

ORIGINAL_AUDIT_SHA256='e7720802d65609d81c6633cadb90bd6f4a3888ab5a08fce16ab190384ca27c97'
PRIOR_RECEIPT_SHA256='fdf9de7e7bc81689dfbde4428f2db96b94096b00544ff273527cd6533cd7034e'
CAMPAIGNS=(('primary','market/results/primary-01'),
 ('exploratory','market/exploratory/results-01'),
 ('policy-diagnostic','market/policy-diagnostic/results-01'))

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def assignment_name(node):
    return node.targets[0].id if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) else None

def derive(source,data_root,out):
    """Replace exactly two complete assignment lines, then compare all other AST."""
    before=ast.parse(source)
    targets={}
    for node in before.body:
        name=assignment_name(node)
        if name in {'origin','out'}:
            if name in targets:raise ValueError('Repeated path assignment in preserved source')
            targets[name]=node
    if set(targets)!={'origin','out'}:raise ValueError('Expected exactly the origin and out assignments')
    lines=source.splitlines(keepends=True)
    for name,value in [('origin',data_root),('out',out)]:
        node=targets[name]
        if node.lineno!=node.end_lineno or node.col_offset!=0:
            raise ValueError('Only the original single-line top-level assignments may be replaced')
        lines[node.lineno-1]=f'{name} = pathlib.Path({str(value)!r})\n'
    derived=''.join(lines);after=ast.parse(derived)
    if len(before.body)!=len(after.body):raise ValueError('AST statement count changed')
    def unchanged(tree):
        return ast.dump(ast.Module(body=[n for n in tree.body if assignment_name(n) not in {'origin','out'}],
          type_ignores=tree.type_ignores),include_attributes=False)
    if unchanged(before)!=unchanged(after):raise ValueError('Audit logic outside the two path assignments changed')
    for name,value in [('origin',data_root),('out',out)]:
        nodes=[n for n in after.body if assignment_name(n)==name]
        expected=ast.parse(f'{name} = pathlib.Path({str(value)!r})').body[0]
        if len(nodes)!=1 or ast.dump(nodes[0],include_attributes=False)!=ast.dump(expected,include_attributes=False):
            raise ValueError('Adapted path expression differs from the declared literal')
    compile(derived,'audit_original.portable.py','exec')
    return derived,hashlib.sha256(unchanged(before).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=pathlib.Path,required=True,
      help='Extracted AGI_ALPHA_Prior_Audit_Inputs directory, or its immediate parent')
    parser.add_argument('--out',type=pathlib.Path,required=True,help='New output directory; existing paths are refused')
    parser.add_argument('--verify-only',action='store_true',help='Verify all input hashes and path-only AST derivation without rerunning the full audit')
    args=parser.parse_args();started=time.perf_counter();cpu=time.process_time()
    data=args.data_root.expanduser().resolve();out=args.out.expanduser().resolve()
    if not (data/'market').is_dir() and (data/'AGI_ALPHA_Prior_Audit_Inputs/market').is_dir():
        data=data/'AGI_ALPHA_Prior_Audit_Inputs'
    if out.exists():parser.error('Output path already exists; preserved evidence will not be overwritten')
    if out==data or data in out.parents:parser.error('Output must be outside the immutable extracted data directory')
    here=pathlib.Path(__file__).resolve().parent
    auditor=here/'audit_original.py';receipt=here/'prior-audit.json'
    if sha(auditor)!=ORIGINAL_AUDIT_SHA256:parser.error('Preserved audit_original.py source identity does not match')
    if sha(receipt)!=PRIOR_RECEIPT_SHA256:parser.error('Preserved prior-audit.json identity does not match')
    prior=json.loads(receipt.read_text());manifest_path=data/'SOURCE_MANIFEST.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('schema')!='agi-alpha-prior-audit-input-manifest/v1':parser.error('Expected the complete prior-input source manifest')
    identities=[];seen=set()
    for item in manifest['files']:
        rel=item['path'];path=(data/rel).resolve()
        if path==data or data not in path.parents or rel in seen:parser.error('Unsafe or duplicate manifest path')
        seen.add(rel)
        identity={'path':rel,'bytes':path.stat().st_size,'sha256':sha(path)}
        if identity['bytes']!=item['bytes'] or identity['sha256']!=item['sha256']:
            parser.error(f'Input does not match its manifest: {rel}')
        identities.append(identity)
    required={'market/src/market.mjs','LICENSE'}
    for _,rel in CAMPAIGNS:
        required.update(f'{rel}/{name}' for name in ['complete-runs.jsonl.gz','completion.json','configurations.json','outcomes.jsonl'])
    if not required.issubset(seen):parser.error('A required original audit input is absent from the manifest')
    actual={x['path']:x for x in identities};previous={x['campaign']:x for x in prior['source_identities']}
    for campaign,rel in CAMPAIGNS:
        current=actual[f'{rel}/complete-runs.jsonl.gz'];original=previous[campaign]
        if current['sha256']!=original['sha256'] or current['bytes']!=original['bytes']:
            parser.error(f'Archive differs from the already audited original: {campaign}')
        completion=json.loads((data/rel/'completion.json').read_text())
        if completion['completeRunsSHA256']!=current['sha256']:parser.error('Original completion receipt does not bind its archive')
    if actual['market/src/market.mjs']['sha256']!=prior['original_market_core_sha256']:
        parser.error('Original market core differs from the already audited source')
    source=auditor.read_text();derived,logic_sha=derive(source,data,out)
    out.mkdir(parents=True,exist_ok=False)
    record={'schema':'agi-alpha-portable-prior-audit-derivation/v1',
      'createdUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'status':'INPUTS_AND_PATH_ONLY_DERIVATION_VERIFIED','dataRoot':str(data),'outputRoot':str(out),
      'originalAuditSHA256':ORIGINAL_AUDIT_SHA256,'priorReceiptSHA256':PRIOR_RECEIPT_SHA256,
      'sourceManifestSHA256':sha(manifest_path),'inputIdentities':identities,
      'replacedAssignments':['origin','out'],'unchangedOtherLogicASTSHA256':logic_sha,
      'derivedSourceSHA256':hashlib.sha256(derived.encode()).hexdigest(),
      'wrapperSHA256':sha(pathlib.Path(__file__)),'verifyOnly':args.verify_only,
      'fullAuditExecuted':False,'monetaryCostCents':None,'authoringInferenceCostCents':None,'humanMinutes':None,
      'boundary':'Physical process measurements are not human wages or complete monetary costs. Prior accounting validation is not demand calibration.'}
    with (out/'portable-derivation.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    status=0
    if not args.verify_only:
        with tempfile.TemporaryDirectory(prefix='path-only-audit-',dir=out) as temporary:
            script=pathlib.Path(temporary)/'audit_original.portable.py';script.write_text(derived)
            result=subprocess.run([sys.executable,str(script)],check=False)
            status=result.returncode
    completion={'schema':'agi-alpha-portable-prior-audit-completion/v1','verifyOnly':args.verify_only,
      'fullAuditExecuted':not args.verify_only,'exitCode':status,'sourceSHA256After':sha(auditor),
      'preservedAuditSourceUnchanged':sha(auditor)==ORIGINAL_AUDIT_SHA256,
      'fullAuditReceiptSHA256':sha(out/'prior-audit.json') if (out/'prior-audit.json').exists() else None,
      'wallSeconds':time.perf_counter()-started,'wrapperCpuSeconds':time.process_time()-cpu,
      'monetaryCostCents':None,'authoringInferenceCostCents':None,'humanMinutes':None}
    with (out/'portable-completion.json').open('x') as f:json.dump(completion,f,indent=2);f.write('\n')
    print(json.dumps({'status':'PASS' if status==0 else 'FAIL','verifyOnly':args.verify_only,
      'fullAuditExecuted':not args.verify_only,'verifiedFiles':len(identities),'out':str(out)}))
    return status

if __name__=='__main__':raise SystemExit(main())
