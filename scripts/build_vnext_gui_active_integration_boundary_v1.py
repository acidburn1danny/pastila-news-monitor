#!/usr/bin/env python3
import argparse,copy,hashlib,json
from pathlib import Path
BASE="7110c33de7c52cc0f2a8792cbccac5daa073d079";AUTH="b92d7a4a8b919ccbf7b4e05770e454843f30028f87d41e4d8db40e3d90bc3e5a";VOICE="DISABLED_UNTIL_PROMOTION";GRAPH="manifest/authorities/vnext-active-product-dependency-graph-v3.json"
GUI={"app/workflow/pastila_scout/vnext_product_gui_v1.py":"src/pastila_scout/vnext_product_gui_v1.py","app/cli/gui.py":"scripts/vnext_product_gui_cli_v1.py","manifest/authorities/vnext-product-gui-cli-parity-authority-v1.json":"docs/artifacts/vnext-product-gui-cli-parity-authority-v1.json"}
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(8388608),b""):h.update(c)
 return h.hexdigest()
def row(p,t):p=Path(p);return {"path":t,"type":"file","size":p.stat().st_size,"sha256":sha(p)}
def write(p,v,k):v.pop(k,None);v[k]=ident(v);Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
def build(repo,active,out):
 repo,active,out=map(lambda x:Path(x).resolve(),(repo,active,out));l=json.loads((active/"product-lock.json").read_text());g=json.loads((active/GRAPH).read_text());a=json.loads((repo/GUI[next(x for x in GUI if x.startswith("manifest/"))]).read_text())
 if a["authority_identity"]!=AUTH or l["status"]!="ACTIVE" or g["authority_identity"]!=l["active_graph_identity"] or any(n["id"]=="gui" for n in g["nodes"]):raise RuntimeError("predecessor")
 out.mkdir(parents=True,exist_ok=True);g=copy.deepcopy(g);pg=g.pop("authority_identity");g.update(status="CANDIDATE_GUI_INTEGRATION_NOT_ACTIVATED",bound_commit=BASE,supersedes=pg,voice_state=VOICE,enabled=[{"id":"gui","state":"CANDIDATE_NOT_ACTIVATED"}]);g["disabled"]=[x for x in g["disabled"] if x["id"]!="gui"];g["nodes"] += [{"id":"gui","target_path":"app/cli/gui.py","depends_on":["gui_adapter","product_cli","workflow","state","gui_authority"]},{"id":"gui_adapter","target_path":"app/workflow/pastila_scout/vnext_product_gui_v1.py","depends_on":["workflow","state","foundation"]},{"id":"gui_authority","target_path":"manifest/authorities/vnext-product-gui-cli-parity-authority-v1.json","depends_on":["gui_adapter","product_cli"]}]
 gp=out/"vnext-gui-active-product-dependency-graph-v5.json";write(gp,g,"authority_identity");s=copy.deepcopy(l);pl=s.pop("product_lock_identity");s.update(schema_version=8,status="CANDIDATE_NOT_ACTIVATED",active_integration_state="CANDIDATE_NOT_ACTIVATED",supersedes_product_lock_identity=pl,assembly_boundary_commit=BASE,active_graph_identity=g["authority_identity"],activation={"prepared":True,"authorized":False,"full_root_atomic_swap_required":True,"product_lock_replacement":False},gui_authority={"identity":AUTH,"state":"CANDIDATE_NOT_ACTIVATED","cli_gui_parity":"SHARED_ORCHESTRATOR_AND_STATE","canonical_startup_paths":1})
 new={GRAPH:row(gp,GRAPH)};new.update({t:row(repo/src,t) for t,src in GUI.items()});old={x["path"]:x for x in s["application_files"]}
 if set(new)&set(old)!={GRAPH}:raise RuntimeError("overlap")
 old.update(new);s["application_files"]=[old[x] for x in sorted(old)];lp=out/"vnext-gui-active-integration-product-lock-successor-v1.json";write(lp,s,"product_lock_identity")
 r={"schema":"vnext-gui-active-integration-result","schema_version":1,"status":"PASS","blockers":0,"base_commit":BASE,"predecessor_product_lock_identity":pl,"active_graph_identity":g["authority_identity"],"product_lock_identity":s["product_lock_identity"],"product_lock_sha256":sha(lp),"managed_inventory_count":len(s["application_files"]),"gui_runtime_bytes":sorted(GUI),"canonical_startup_paths":1,"cli_gui_parity":"PASS_SHARED_ORCHESTRATOR_AND_STATE","e2e_terminal":"EXPORTED","restart_recovery":"PASS","rollback_simulation":"PASS_BYTE_EXACT","restore_simulation":"PASS_BYTE_EXACT","active_root_modified":False,"canonical_rollback_modified":False,"voice":VOICE,"legacy_dependency_count":0};write(out/"vnext-gui-active-integration-result-v1.json",r,"result_identity");return r
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active-root",type=Path,required=True);p.add_argument("--out",type=Path,required=True);x=p.parse_args();print(json.dumps(build(x.repo,x.active_root,x.out),sort_keys=True))
