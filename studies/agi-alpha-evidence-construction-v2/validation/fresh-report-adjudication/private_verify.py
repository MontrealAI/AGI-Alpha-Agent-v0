"""Private curator verification. Run only outside recipient paths. Never imports the constructor."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json,re,hashlib,math,csv,io
from decimal import Decimal
from scipy.stats import t as student_t
R=Path(__file__).resolve().parent
key=json.loads((R/'private_answer_key.json').read_text())
checks=[]
def check(label,condition):
 checks.append({'check':label,'passed':bool(condition)})
 if not condition:raise AssertionError(label)
def plain(e):return ''.join(e.itertext()).strip()
for name,h in key['source_hashes'].items():check('exact_source_hash_'+name,hashlib.sha256((R/name).read_bytes()).hexdigest()==h)
a=ET.parse(R/'pone.0272427.xml').getroot();b=ET.parse(R/'pone.0143177.xml').getroot()
ta=a.find('.//table-wrap[@id="pone.0272427.t003"]/alternatives/table/tbody')
rows=ta.findall('tr');cells=rows[3].findall('td')
check('A_header_and_row',plain(rows[0].find('td'))=='Correct responses' and plain(cells[0])=='Feedback')
v1=[Decimal(v.strip()) for v in plain(cells[1]).split('±')];v0=[Decimal(v.strip()) for v in plain(cells[2]).split('±')]
ka=key['reports']['A']['derived']
check('A_exact_table_values',[float(v1[0]),float(v1[1]),float(v0[0]),float(v0[1])]==[ka['mean_retrieval'],ka['sd_retrieval'],ka['mean_restudy'],ka['sd_restudy']])
foot=plain(a.find('.//fn[@id="t003fn001"]'));check('A_SD_label','standard deviations' in foot)
raw=(R/'Error_correction_PI_Experiment_1.csv').read_text(encoding='cp1252')
delimiter=max([',',';','\t'],key=raw.splitlines()[0].count);records=list(csv.DictReader(io.StringIO(raw),delimiter=delimiter))
groups={}
for rec in records:
 k=(rec['CondiçãoRS'],rec['FeedbackComSem']);groups[k]=groups.get(k,0)+1
check('A_public_data_N_and_four_equal_cell_counts',len(records)==ka['total_experiment'] and len(groups)==4 and set(groups.values())=={ka['n_per_focal_cell']})
n=ka['n_per_focal_cell'];s1,s0=float(v1[1]),float(v0[1]);variances=[s1*s1/n,s0*s0/n]
se=math.sqrt(sum(variances));df=sum(variances)**2/sum(v*v/(n-1) for v in variances);difference=float(v1[0]-v0[0]);margin=student_t.isf(.025,df)*se
check('A_difference_decimal',abs(difference-ka['difference_proportion'])<1e-12)
check('A_uncertainty_reconstruction',abs(se-ka['welch_standard_error'])<1e-12 and max(abs(x-y) for x,y in zip([difference-margin,difference+margin],ka['welch_95_ci']))<1e-10)
tb=b.find('.//table-wrap[@id="pone.0143177.t001"]/alternatives/table/tbody')
vals=[]
for row in tb.findall('tr'):
 vals.append([float(z) for z in re.findall(r'\d*\.\d+',plain(row.findall('td')[1]))])
kb=key['reports']['B']['derived'];check('B_exact_table_values',vals==[[kb['short_effect'],kb['short_SE']],[kb['long_effect'],kb['long_SE']]])
check('B_SE_label','Standard errors' in plain(b.find('.//table-wrap[@id="pone.0143177.t001"]/caption')))
check('B_difference_decimal',float(Decimal(str(vals[1][0]))-Decimal(str(vals[0][0])))==kb['difference'])
check('B_hold_not_fabricated_precision',kb['identified_SE_or_CI_for_difference'] is None)
check('twenty_frozen_criteria',sum(len(r['criteria']) for r in key['reports'].values())==20)
check('no_private_files_in_packet',not any('private' in p.name or 'assemble' in p.name or 'expert' in p.name for p in (R/'source_packet').iterdir()))
report={'status':'passed','checks':checks,'limitations':['B absence of cross-outcome covariance assessed by full main/supplement inspection; no numerical CI can prove that absence.','This verifies source extraction and summary arithmetic, not individual-data replication of author analyses.'],'computed_private':{'A':{'difference':difference,'SE':se,'df':df,'CI95':[difference-margin,difference+margin]},'B':{'difference':kb['difference']}}}
(R/'private_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('Independent source/quantity verification passed; private output stored without printing answer values.')
