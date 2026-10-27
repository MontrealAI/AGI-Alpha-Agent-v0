# SPDX-License-Identifier: Apache-2.0
import argparse,collections,gzip,hashlib,importlib.util,itertools,json,pathlib,sys,time
parser=argparse.ArgumentParser(description="Replay the independent order-memory review without overwriting its original evidence.")
parser.add_argument('--data-dir',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent,help="Directory containing the study, frozen config, original review report and transfer_validation.")
parser.add_argument('--output',type=pathlib.Path,help="New JSON report path; refuses to overwrite an existing file. Default: JSON to stdout only.")
args=parser.parse_args()
base=args.data_dir.resolve()
if args.output is not None and args.output.exists():parser.error(f"Output already exists: {args.output}; choose a new path.")
sys.dont_write_bytecode=True
original_source=pathlib.Path(__file__).resolve().with_name('order_transfer_review.original.py.txt')
original_source_hash=hashlib.sha256(original_source.read_bytes()).hexdigest()
original_report=json.loads((base/'adversarial_review_results.json').read_text())
assert original_source_hash==original_report['review_source_sha256']
original_report_hash=hashlib.sha256((base/'adversarial_review_results.json').read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('author_study',base/'order_transfer_study.py'); author=importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
start=time.perf_counter(); cfg=json.loads((base/'transfer_frozen_config.json').read_text()); res=json.loads((base/'transfer_validation/transfer_results.json').read_text())
assert hashlib.sha256((base/'order_transfer_study.py').read_bytes()).hexdigest()==cfg['frozen_source_sha256']==res['source_sha256']
assert hashlib.sha256((base/'transfer_frozen_config.json').read_bytes()).hexdigest()==res['configuration_sha256']
cache={}; corruption=[]; duplicate_cases=0
for n in cfg['new_validation_sizes']:
    names=tuple(chr(65+i) for i in range(n)); pairs=tuple(itertools.combinations(names,2)); words=[''.join(w) for w in itertools.permutations(names)]
    for parity in [False,True]:
        codes=[]
        for w in words:
            vals=[int(w.index(a)<w.index(b)) for a,b in pairs]
            if parity:
                parity_bit=0
                for v in vals: parity_bit^=v
                vals.append(parity_bit)
            codes.append(vals)
        masks={}
        for j in range(len(codes[0])):
            for b in [0,1]: masks[j,b]=sum(1<<i for i,c in enumerate(codes) if c[j]==b)
        cache[n,parity]=(words,codes,masks)
    for w in words:
        vals=[int(w.index(a)<w.index(b)) for a,b in pairs]; doubled=[v for v in vals for _ in range(2)]
        for erased in range(len(doubled)):
            recovered=[doubled[2*j+(erased==2*j)] for j in range(len(vals))]
            assert recovered==vals; duplicate_cases+=1
    w=''.join(names); adjacent=names[1]+names[0]+''.join(names[2:]); other=names[1]+names[2]+names[0]+''.join(names[3:])
    def enc(t):
        v=[int(t.index(a)<t.index(b)) for a,b in pairs]
        return v+[sum(v)%2]
    code=enc(w); mixed=code.copy(); mixed[0]^=1; mixed[-1]=None
    decoded=author.ordinary_library_repair(mixed,pairs,names)
    assert decoded==[adjacent] and adjacent!=w
    target=enc(other); flips=[i for i,(a,b) in enumerate(zip(code,target)) if a!=b]
    assert len(flips)==2 and sum(target)%2==0
    decoded2=author.precedence_oracle(target,pairs,names,True)
    assert decoded2==[other]
    corruption.append({'n':n,'erasure_plus_substitution':{'original':w,'erased_index':len(code)-1,'flipped_index':0,'decoded_unique_wrong':decoded},'two_substitutions':{'original':w,'flipped_indices':flips,'decoded_unique_wrong':decoded2,'parity_detects':False}})
counts=collections.Counter(); digest=hashlib.sha256(); mismatches=[]
with gzip.open(base/'transfer_validation/transfer_cases.jsonl.gz','rb') as f:
    for line in f:
        digest.update(line); row=json.loads(line); parity=row['scheme']=='pairwise_plus_xor'; words,codes,masks=cache[row['n'],parity]
        idx=words.index(row['history']); code=codes[idx]; erased=set(row['erased']); survivors=(1<<len(words))-1
        for j,b in enumerate(code):
            if j not in erased: survivors&=masks[j,b]
        expected=[w for i,w in enumerate(words) if survivors&(1<<i)]
        if expected!=row['recovery_set']: mismatches.append(row)
        counts[(row['n'],row['scheme'],len(erased),len(expected)==1)]+=1
assert digest.hexdigest()==res['case_stream_sha256']; assert not mismatches
out={'review_source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'cases_verified':sum(counts.values()),'independent_bitset_oracle_mismatches':len(mismatches),'stream_hash_matches':True,'source_and_config_hashes_match':True,'duplicate_reference_single_erasure_cases_verified':duplicate_cases,'counterexamples':corruption,'scope_verdict':'Correct within distinct-events-once, known single erasure and noiseless remaining bits; no novelty, hardware count or AI advantage established.','elapsed_seconds':time.perf_counter()-start,'counts':[{'n':k[0],'scheme':k[1],'erasures':k[2],'unique':k[3],'cases':v} for k,v in sorted(counts.items())]}
assert out['cases_verified']==198840 and duplicate_cases==24000
out.update({'execution_kind':'portable_replay_of_preserved_independent_review','original_review_source_sha256':original_source_hash,'original_review_report_sha256':original_report_hash,'original_review_source_preserved_exactly':True,'original_review_report_unchanged':hashlib.sha256((base/'adversarial_review_results.json').read_bytes()).hexdigest()==original_report_hash,'data_directory':str(base),'output_policy':'stdout by default; explicit output uses exclusive creation and never overwrites an existing file'})
assert out['original_review_report_unchanged']
report=json.dumps(out,indent=2)+'\n'
if args.output is not None:
    with args.output.open('x') as f:f.write(report)
print(report,end='')
