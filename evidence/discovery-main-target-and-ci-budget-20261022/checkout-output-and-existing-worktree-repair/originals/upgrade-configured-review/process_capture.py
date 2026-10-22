import pathlib,json,hashlib,sys,re,datetime
root=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
for name in sys.argv[1:]:
 p=pathlib.Path(name);capture=json.loads(p.read_bytes());resources=[];data={}
 for r in capture["resources"]:
  if "body" not in r:resources.append(r);continue
  b=r["body"].encode();h=sha(b);dest=root/("raw-"+h+".json")
  if dest.exists():assert dest.read_bytes()==b
  else:dest.open("xb").write(b)
  resources.append({k:r[k] for k in ["key","url","fetchedAt"]}|{"file":str(dest),"bytes":len(b),"sha256":h});data[r["key"]]=json.loads(b)
 summary=data.get("summary",{});body=summary.get("body","");m=re.search(r"<!-- codex-review-state:v1 (.*?) -->",body);state=json.loads(m.group(1)) if m else None
 head="bc281cc35faf6aeb9d53910031663e15d1b6f390"
 current_reviews=[r for r in data.get("reviews",[]) if r.get("commit_id")==head]
 current_inlines=[r for r in data.get("inlines",[]) if r.get("original_commit_id")==head]
 obs={"schema":"alpha/exact-bc-configured-review-observation/v1","startedAt":capture["startedAt"],"completedAt":capture["completedAt"],"resources":resources,"summaryCodeReview":state.get("code_review") if state else None,"summaryUpdatedAt":summary.get("updated_at"),"pr":{k:data.get("pr",{}).get(k) for k in ["state","draft","mergeable","mergeable_state","merge_commit_sha"]},"head":data.get("pr",{}).get("head",{}).get("sha"),"base":data.get("pr",{}).get("base",{}).get("sha"),"main":data.get("main",{}).get("object",{}).get("sha"),"currentHeadReviews":[{"id":r["id"],"state":r["state"],"commit":r.get("commit_id"),"submittedAt":r.get("submitted_at"),"body":r.get("body")} for r in current_reviews],"currentHeadOriginalInlines":[{"id":r["id"],"review":r.get("pull_request_review_id"),"path":r.get("path"),"commit":r.get("commit_id"),"originalCommit":r.get("original_commit_id"),"createdAt":r.get("created_at"),"body":r.get("body")} for r in current_inlines],"historicalOriginalInlineIds":[r["id"] for r in data.get("inlines",[]) if r.get("original_commit_id")!=head],"reviewCollectionCount":len(data.get("reviews",[])),"inlineCollectionCount":len(data.get("inlines",[])),"headChecks":[{"id":c["id"],"name":c["name"],"status":c["status"],"conclusion":c.get("conclusion"),"head":c.get("head_sha")} for c in data.get("headChecks",{}).get("check_runs",[])],"syntheticChecks":[{"id":c["id"],"name":c["name"],"status":c["status"],"conclusion":c.get("conclusion"),"head":c.get("head_sha")} for c in data.get("syntheticChecks",{}).get("check_runs",[])],"capture": {"file":str(p),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}}
 stamp=capture["startedAt"].replace(":","").replace(".","");dest=root/("observation-"+stamp+".json");b=(json.dumps(obs,indent=2)+"\n").encode()
 if dest.exists():assert dest.read_bytes()==b
 else:dest.open("xb").write(b)
 print(json.dumps({"file":str(dest),"bytes":len(b),"sha256":sha(b),"summary":obs["summaryCodeReview"],"currentHeadReviews":obs["currentHeadReviews"],"currentHeadOriginalInlines":obs["currentHeadOriginalInlines"],"headChecks":obs["headChecks"]},indent=2))
