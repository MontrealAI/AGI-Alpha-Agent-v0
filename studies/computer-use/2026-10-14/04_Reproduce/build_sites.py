from pathlib import Path
import hashlib,json,re,base64,argparse
ROOT=Path(__file__).resolve().parents[1]
def build(task):
 config=json.loads((ROOT/f'02_Work_Products/Task_{task}/brief.json').read_text())
 template=(ROOT/'04_Reproduce/site_template.html').read_text()
 text=template.replace('__BRAND__',config['brand']).replace('__CONFIG__',json.dumps(config,ensure_ascii=False).replace('<','\\u003c'))
 for tag,token in [('script','__SCRIPT_HASH__'),('style','__STYLE_HASH__')]:
  code=re.search(fr'<{tag}>([\s\S]*?)</{tag}>',text).group(1)
  text=text.replace(token,'sha256-'+base64.b64encode(hashlib.sha256(code.encode()).digest()).decode())
 dest=ROOT/f'02_Work_Products/Task_{task}/after/index.html';dest.write_text(text)
 print(task,hashlib.sha256(dest.read_bytes()).hexdigest())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tasks',nargs='*',default=['A','B']);a=p.parse_args()
 for task in a.tasks:build(task)
