"""Fresh adversarial audit of final V10 adapters and equivalence closure."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,stat
from pathlib import Path

EXPECTED={
 "v1.1":{"candidate":"pastila-editor-core-v1.1-json-successor-v10","contract_candidate":"pastila-editor-core-v1.1-json-successor","receipt":"15c39a923fc10dc9145710ed74d94d872c3854e2bac56ba2e51ac13483e9921b","checkpoint":"2723d9f0cac7133239f2d5e37afb5022beb49183a61cb911339762e753a2b6b3","corpus":"12ce4c7aeb257e9d5c1a92dd8c5d75d1e998819ecd19eddafa0e42cab83072f1","config":"be4f28f967bdc128094e06a3092f9be27ddbaf03ac5fdb270d2cfd036b3f10ae","predecessor":"ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c","development":"a2cdfd141c394969fc66a5728186693ef47b83ed491d1c37fffd14642a42724a","shadow":"e0adbfdaf7df1ac7365692c4ceae90bee62b5c07349521ec333f721c668304f3","development_gates":{"A":"88a03f853709dca50a04528b7a0a577b37fcfd14bbd2e06d0c8d7fee3cf0769e","B":"c588bc680dc15c10f5c9bbfce576538ddddb4ab0136bfa39791617c7639734f9"},"shadow_gates":{"A":"021401af76fc8bb7856f5b2044b4667537bdea001f34cc82f815e5e1f7d1f1a4","B":"aa26c42479d2e41b6caa87251f3b2b53c06380582b39a947a54a4396555204cf"}},
 "v1.2":{"candidate":"pastila-editor-core-v1.2-json-successor-v10","contract_candidate":"pastila-editor-core-v1.2-json-successor","receipt":"f716f48db091d51263cab72ca97df1e8930d09194b11fa3dd0be618739f8b46a","checkpoint":"6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1","corpus":"5491630f3b959f890a74cce3075a9a2e976304138e342c379d4e5fd6a0a9641c","config":"f7c2cd9bbadea3fd845c49456c95a6ca6e420d34d868113e4df6d4729216527c","predecessor":"a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8","development":"8cdf2da9aff237a26cf6f966f6cf977b75977ac83b9a68ba9317f4ee848581a6","shadow":"74d79f07c2f8bc7b0182e255e2119d7c15d9e4f4642f99adef7654d9cd7754ce","development_gates":{"A":"ce83d5381c9d7f76c8d8ac5ee253315e66093412f07a64ec34ecb5d689cc7447","B":"131454fae5f7cd39e85b34be4bfda97d3725fafa8343e2e2ee5603092c3f67f7"},"shadow_gates":{"A":"b4ff9e7b1b65392265689dbb876bccf266babd2f6b0afb030aadc27d9572972f","B":"511d02f492bee00819950d5700fd839d3c600c76efc77412e60235c42905870e"}},
}
ROOTFS="9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826";MODEL="f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39";CONTRACT="eb2ab0914175f0f9ae50882c4c96fbc792cfee1fe40fa39740b9ef8f58a1825d";AUTHORITY="cda69071c31cacd50cd6ace67fa7c7955df431ad6f0ad9035d12a7df414e3d7b"
GATE_LAUNCHER="f3e9b5aad5ef0bebc8ed029f367a74b7d07eb15c63f8a30d636abff0abf1248f"
def canonical(v):return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=(",",":"),sort_keys=True).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
 digest=hashlib.sha256()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b""):digest.update(chunk)
 return digest.hexdigest()
def load(path):return json.loads(path.read_bytes())
def sealed(value,field):
 core=dict(value);claimed=core.pop(field)
 if sha(canonical(core))!=claimed:raise ValueError(f"invalid seal {field}")
 return claimed
def flat(root):
 entries=sorted(root.iterdir(),key=lambda p:p.name.encode())
 if [p.name for p in entries]!=["README.md","adapter_config.json","adapter_model.safetensors","training-receipt.json"]:raise ValueError("adapter closure mismatch")
 records=[]
 for p in entries:
  if p.is_symlink() or not p.is_file() or p.stat().st_mode&(stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH):raise ValueError("adapter path not closed read-only")
  raw=p.read_bytes();records.append(p.name.encode()+b"\0"+len(raw).to_bytes(8,"big")+hashlib.sha256(raw).digest())
 return sha(b"".join(records))
def object_manifest(root):
 records=[]
 for path in sorted(root.iterdir(),key=lambda p:p.name.encode()):
  if path.is_symlink() or not path.is_file():raise ValueError("model object closure mismatch")
  size=path.stat().st_size;records.append(path.name.encode()+b"\0"+size.to_bytes(8,"big")+bytes.fromhex(file_sha(path)))
 if not records:raise ValueError("empty model object")
 return sha(b"".join(records))
def rows(path):return [json.loads(line) for line in path.read_text("utf-8").splitlines()]
def audit_gate(root,count,identity):
 receipt=load(root/"gate-receipt.json")
 if sealed(receipt,"gate_identity")!=identity or receipt["status"]!="PASS" or receipt["rows"]!=count or receipt["qualification_attempt_consumed"] or receipt["adjudication_performed"] or receipt["promotion_effect"]:raise ValueError("gate receipt mismatch")
 observations=[]
 for i in range(1,count+1):
  raw=(root/f"{i:03d}.json").read_bytes();value=json.loads(raw)
  if raw!=canonical(value) or not all(value[k] for k in ("terminal_eos","canonical_json","nfc","within_byte_ceiling")) or value["repeated_8gram_ceiling"]>3:raise ValueError("gate observation mismatch")
  observations.append(raw)
 return receipt,observations
def contract_module(path):
 spec=importlib.util.spec_from_file_location("audit_contract",path);module=importlib.util.module_from_spec(spec)
 if spec.loader is None:raise ValueError("contract import")
 spec.loader.exec_module(module);return module
def main():
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--runtime",type=Path,required=True);p.add_argument("--development",type=Path,required=True);p.add_argument("--rootfs",type=Path,required=True);p.add_argument("--model",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 art=a.repo/"docs/artifacts";contract_path=a.repo/"src/pastila_scout/production_core_execution_contract_v10.py"
 if sha(contract_path.read_bytes())!=CONTRACT:raise ValueError("contract source mismatch")
 launcher=a.repo/"scripts/launch_production_core_successor_development_gate_v10.sh";launcher_source=launcher.read_text("utf-8")
 if sha(launcher.read_bytes())!=GATE_LAUNCHER or not all(w in launcher_source for w in ("unshare --mount --net","HF_HUB_OFFLINE=1","TRANSFORMERS_OFFLINE=1","mount -o remount,bind,ro")):raise ValueError("gate boundary mismatch")
 if a.rootfs.is_symlink() or not a.rootfs.is_file() or file_sha(a.rootfs)!=ROOTFS:raise ValueError("rootfs object mismatch")
 if object_manifest(a.model)!=MODEL:raise ValueError("base model object mismatch")
 contract=contract_module(contract_path);authority=load(art/"production-core-training-runtime-authority-v10-3.json")
 if authority["training_runtime_authority_identity"]!=AUTHORITY or authority["observation"]["execution_contract_sha256"]!=CONTRACT:raise ValueError("training authority mismatch")
 qualification=load(art/"production-core-candidate-request-manifest-v2.json");qids={r["case_id"] for r in qualification["requests"]};seen={"qualification":qids};adapters={}
 for tag,e in EXPECTED.items():
  full=a.runtime/f"full-{tag}-v10-3";receipt=load(full/"training-receipt.json")
  if sealed(receipt,"receipt_identity")!=e["receipt"] or receipt["candidate"]!=e["candidate"] or receipt["optimizer"]!="PAGED_ADAMW_8BIT" or receipt["optimizer_steps"]!=60 or receipt["checkpoint_count"]!=60 or receipt["final_checkpoint_identity"]!=e["checkpoint"] or receipt["rootfs_sha256"]!=ROOTFS or receipt["base_model_manifest_sha256"]!=MODEL or receipt["corpus_sha256"]!=e["corpus"] or receipt["config_sha256"]!=e["config"] or receipt["predecessor_adapter_manifest_sha256"]!=e["predecessor"] or not all(receipt[k] for k in ("triton_compile_load","backward_4bit","save_reload","authority_mounts_read_only")) or receipt["network_activity"] or receipt["qualification_attempt_consumed"]:raise ValueError("training receipt mismatch")
  mats={label:a.runtime/"materializations"/f"{tag}-{label}" for label in "AB"};identities={k:flat(v) for k,v in mats.items()}
  if identities["A"]!=identities["B"] or any((mats[x]/"training-receipt.json").read_bytes()!=(full/"training-receipt.json").read_bytes() for x in "AB"):raise ValueError("adapter materialization mismatch")
  dev_corpus=a.development/f"pastila-editor-core-{tag}-json-successor-v10-development-v10.jsonl";shadow_corpus=art/f"pastila-editor-core-{tag}-json-successor-v10-shadow.jsonl";train_corpus=art/f"pastila-editor-core-{tag}-json-successor-v10-train.jsonl"
  if sha(dev_corpus.read_bytes())!=e["development"] or sha(shadow_corpus.read_bytes())!=e["shadow"] or sha(train_corpus.read_bytes())!=e["corpus"]:raise ValueError("corpus hash mismatch")
  partitions={"train":rows(train_corpus),"development":rows(dev_corpus),"shadow":rows(shadow_corpus)}
  ids={name:{r["example_id"] for r in values} for name,values in partitions.items()}
  if any(ids[x]&ids[y] for x,y in (("train","development"),("train","shadow"),("development","shadow"))) or any(value&qids for value in ids.values()):raise ValueError("partition leakage")
  editorial_path=a.repo/(".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt" if tag=="v1.1" else ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt");editorial=editorial_path.read_bytes()
  for name,values in partitions.items():
   for row in values:
    user=row["user_prompt"] if name=="development" else row["messages"][1]["content"]
    if contract.assert_phase_equivalence(candidate=e["contract_candidate"],editorial_prompt=editorial,user_prompt=user)!=contract.projection_identity(row["messages"][:2]):raise ValueError("phase equivalence mismatch")
  gate_data={}
  for phase,count,key in (("development",72,"development_gates"),("shadow",240,"shadow_gates")):
   got={}
   for label in "AB":got[label]=audit_gate(a.runtime/phase/f"{tag}-{label}",count,e[key][label])
   if got["A"][1]!=got["B"][1]:raise ValueError("gate reproducibility mismatch")
   gate_data[phase]={label:got[label][0]["gate_identity"] for label in "AB"}
  adapters[e["candidate"]]={"training_receipt_identity":e["receipt"],"final_checkpoint_identity":e["checkpoint"],"content_identity":identities["A"],"materializations":identities,"development_gate_identities":gate_data["development"],"shadow_gate_identities":gate_data["shadow"],"development_rows":72,"shadow_rows":240}
 core={"schema":"pastila-production-core-v10-final-adapter-equivalence-audit","schema_version":1,"status":"PASS_ZERO_BLOCKERS_ZERO_QUALIFICATION_ATTEMPTS","training_runtime_authority_identity":AUTHORITY,"execution_contract_sha256":CONTRACT,"base_model_manifest_sha256":MODEL,"rootfs_sha256":ROOTFS,"adapters":adapters,"partition_cardinality":{"training":960,"development":144,"shadow":480,"qualification_used":0},"materializations_byte_identical":True,"phase_projection_equivalent":True,"host_fallback":False,"network_activity":False,"candidate_execution_performed":False,"qualification_attempt_consumed":False,"retry_or_redraw":False,"adjudication_performed":False,"promotion_effect":False,"blockers":[]}
 value={**core,"audit_identity":sha(canonical(core))};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n");print(value["audit_identity"]);return 0
if __name__=="__main__":raise SystemExit(main())
