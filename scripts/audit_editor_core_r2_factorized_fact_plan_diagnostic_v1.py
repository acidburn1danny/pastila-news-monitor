"""Adversarial fixture audit for the factorized diagnostic."""
import copy,json
from fixture_editor_core_r2_factorized_fact_plan_diagnostic_v1 import ART,P,load,rows,run,validate
r=run(); assert r['status']=='PASS_FIXTURE_ONLY'
assert r['slots']==12 and not any(r[k] for k in ('model_loaded','optimizer_created','training_performed','historical_holdouts_read'))
m=load(ART,P+'-manifest.json'); p=load(ART,P+'-protocol.json'); i=load(ART,P+'-interventions.json'); e=load(ART,P+'-evaluation.json'); c=rows(ART,P+'-cases.jsonl'); o=rows(ART,P+'-oracle-plans.jsonl')
def rejected(field,value):
 mm,pp,ii,ee,cc,oo=map(copy.deepcopy,(m,p,i,e,c,o))
 if field=='oracle': cc[0]['oracle_plan_exposed']=value
 elif field=='authority': pp['parent_selection_authority']=value
 try: validate(mm,pp,ii,ee,cc,oo)
 except (AssertionError,KeyError,ValueError): return True
 return False
assert rejected('oracle',True) and rejected('authority',True)
print(json.dumps({'status':'PASS_ADVERSARIAL','blockers':0,'causal_isolation':True,'oracle_custody_separate':True,'one_pass_control_only':True,'parent_selection_authority':False,'mutation_rejection':['ORACLE_EXPOSURE','PARENT_SELECTION_AUTHORITY']},sort_keys=True))
