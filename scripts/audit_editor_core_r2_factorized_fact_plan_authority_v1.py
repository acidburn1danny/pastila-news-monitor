import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def main():
 subprocess.run([sys.executable,"-B",str(ROOT/"scripts/build_editor_core_r2_factorized_fact_plan_authority_v1.py")],check=True,capture_output=True)
 d=json.loads((ROOT/"docs/artifacts/editor-core-r2-factorized-fact-plan-execution-authority-v1.json").read_text()); checks=[]
 checks += [len(d["slots"])==12,len({x["slot_id"] for x in d["slots"]})==12,len({x["output_slug"] for x in d["slots"]})==12]
 checks += [d["fresh_exact_tokenizer_zero_step_per_slot"],d["distinct_empty_output_root_per_slot"],not d["retry_authorized"],d["stop_on_first_failure"],not d["real_runs_authorized_in_build_task"],not d["parent_selection_authority"]]
 for key,name in (("worker_sha256","editor_core_r2_factorized_fact_plan_slot_v1.py"),("supervisor_sha256","supervise_editor_core_r2_factorized_fact_plan_v1.py"),("verifier_sha256","verify_editor_core_r2_factorized_fact_plan_authority_v1.py"),("preflight_sha256","preflight_editor_core_r2_factorized_fact_plan_runtime_v1.py")): checks.append(d[key]==hashlib.sha256((ROOT/"scripts"/name).read_bytes()).hexdigest())
 r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/supervise_editor_core_r2_factorized_fact_plan_v1.py"),"--output-root",str(ROOT/"NEVER_CREATED_FIXTURE"),"--fixture-only"],capture_output=True,text=True,check=True); checks.append(json.loads(r.stdout)["slots"]==12 and not (ROOT/"NEVER_CREATED_FIXTURE").exists())
 r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/supervise_editor_core_r2_factorized_fact_plan_v1.py"),"--output-root",str(ROOT/"NEVER_CREATED_BLOCKED")],capture_output=True,text=True); checks.append(r.returncode!=0 and "separate owner authorization required" in r.stderr and not (ROOT/"NEVER_CREATED_BLOCKED").exists())
 print(json.dumps({"status":"PASS" if all(checks) else "BLOCKED","blockers":0 if all(checks) else 1,"checks":len(checks),"model_loaded":False,"optimizer_created":False,"training_performed":False},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
if __name__=="__main__": main()
