"""V2.3.15 source-blind three-phase deployment boundary."""
from __future__ import annotations
import argparse, json, os, re, subprocess
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from typing import Mapping
from .semantic_authority_capture_orchestrator_v2_3_7 import canonical
from .semantic_authority_deployment_v2_3_9 import (COSIGN_SHA256, DERIVATION_POLICY_IDENTITY,
    LINUX_LAUNCHER_SHA256, REPOSITORY_ID, REPOSITORY_SLUG, RUNTIME_COMMIT,
    SEED_PLAN_IDENTITY, LinuxVerifier, initiation_claim, sha)
from .semantic_authority_deployment_v2_3_10 import FrozenRun, one_shot_guard, run_once, verify_installed_dependency
from .semantic_authority_cosign_v2_3_7 import TRUSTED_ROOT_SHA256
from .semantic_authority_rfc3161_verifier_v2_3_13 import OPENSSL_EXECUTABLE_SHA256, verify_executable

SCHEMA="PASTILA_CAPTURE_DEPLOYMENT_V2_3_15";PAYLOAD_SCHEMA="PASTILA_RFC3161_SCHEDULE_PRECOMMIT_V2_3_15"
DEPLOYMENT_RUNTIME_COMMIT="26f66c54c02e18c05927b91d010290c2f712ca06"
TEMPLATE_PATH="deployment/semantic-authority-metadata-capture-v2-3-14.yml.template"
WORKFLOW_PATH=".github/workflows/semantic-authority-metadata-capture-v2-3-9.yml"
ATTEST_ACTION_COMMIT="1e69f48acb82d1966a394da916b4c1698aa569d6"
UPLOAD_ACTION_COMMIT="ea165f8d65b6e75b540449e92b4886f43607fa02"
DEFAULT_BRANCH_REF="refs/heads/public/v2.3.7-capture"
CA_BUNDLE_SHA256="9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
HEX40=re.compile(r"^[0-9a-f]{40}$");HEX64=re.compile(r"^[0-9a-f]{64}$")
OBJECTS=frozenset({"ca.pem","cosign","deny-network-launcher.sh","openssl","rfc3161-receipt.tsr","rfc3161-root.pem","schedule-precommit.json","trusted-root.json"})

def schedule_payload(v:Mapping[str,object])->bytes:
 keys=("repository_slug","repository_id","default_branch_ref","core_runtime_commit","deployment_runtime_commit","workflow_freeze_commit","workflow_freeze_epoch","workflow_template_sha256","scheduled_utc","schedule_cron","rfc3161_verifier_sha256","rfc3161_root_sha256")
 return canonical({"schema":PAYLOAD_SCHEMA,**{k:v[k] for k in keys}})+b"\n"

def _entry(x:object)->tuple[str,int,str]:
 if not isinstance(x,dict) or set(x)!={"sha256","length","path"}:raise ValueError("object schema")
 path=str(x["path"]);p=PurePosixPath(path);digest=str(x["sha256"]);length=x["length"]
 if "\\" in path or p.is_absolute() or str(p)!=path or ".." in p.parts or p.parts[:2]!=("deployment","objects"):raise ValueError("object path")
 if not HEX64.fullmatch(digest) or not isinstance(length,int) or isinstance(length,bool) or length<=0:raise ValueError("object commitment")
 return digest,length,path

def validate_manifest(v:Mapping[str,object])->None:
 required={"schema","repository_slug","repository_id","default_branch_ref","core_runtime_commit","deployment_runtime_commit","workflow_freeze_commit","workflow_freeze_epoch","workflow_template_sha256","scheduled_utc","schedule_cron","rfc3161_verifier_sha256","rfc3161_root_sha256","ca_sha256","cosign_sha256","launcher_sha256","trusted_root_sha256","derivation_policy_identity","seed_plan_identity","schedule_payload_sha256","objects","deployment_identity","manifest_identity"}
 if set(v)!=required or v["schema"]!=SCHEMA or v["repository_slug"]!=REPOSITORY_SLUG or v["repository_id"]!=REPOSITORY_ID or v["default_branch_ref"]!=DEFAULT_BRANCH_REF or v["core_runtime_commit"]!=RUNTIME_COMMIT or v["deployment_runtime_commit"]!=DEPLOYMENT_RUNTIME_COMMIT:raise ValueError("manifest schema")
 if not HEX40.fullmatch(str(v["workflow_freeze_commit"])) or not HEX64.fullmatch(str(v["workflow_template_sha256"])):raise ValueError("workflow freeze")
 if not isinstance(v["workflow_freeze_epoch"],int) or isinstance(v["workflow_freeze_epoch"],bool) or v["workflow_freeze_epoch"]<=0:raise ValueError("workflow freeze epoch")
 scheduled=datetime.strptime(str(v["scheduled_utc"]),"%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
 if v["schedule_cron"]!=f"{scheduled.minute} {scheduled.hour} {scheduled.day} {scheduled.month} *":raise ValueError("schedule convergence")
 fixed={"rfc3161_verifier_sha256":OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":CA_BUNDLE_SHA256,"ca_sha256":CA_BUNDLE_SHA256,"cosign_sha256":COSIGN_SHA256,"launcher_sha256":LINUX_LAUNCHER_SHA256,"trusted_root_sha256":TRUSTED_ROOT_SHA256,"derivation_policy_identity":DERIVATION_POLICY_IDENTITY,"seed_plan_identity":SEED_PLAN_IDENTITY}
 if any(v[k]!=x for k,x in fixed.items()):raise ValueError("frozen dependency")
 for k in ("rfc3161_root_sha256","ca_sha256","trusted_root_sha256","schedule_payload_sha256","deployment_identity"):
  if not HEX64.fullmatch(str(v[k])):raise ValueError("digest")
 if sha(schedule_payload(v))!=v["schedule_payload_sha256"]:raise ValueError("payload binding")
 rows=v["objects"]
 if not isinstance(rows,dict) or set(rows)!=OBJECTS:raise ValueError("object closure")
 parsed={k:_entry(x) for k,x in rows.items()}
 if len({x[2] for x in parsed.values()})!=len(parsed):raise ValueError("object alias")
 binds={"openssl":"rfc3161_verifier_sha256","rfc3161-root.pem":"rfc3161_root_sha256","ca.pem":"ca_sha256","cosign":"cosign_sha256","deny-network-launcher.sh":"launcher_sha256","trusted-root.json":"trusted_root_sha256","schedule-precommit.json":"schedule_payload_sha256"}
 if any(parsed[n][0]!=v[f] for n,f in binds.items()):raise ValueError("object/pin binding")
 body={k:x for k,x in v.items() if k not in {"deployment_identity","manifest_identity"}}
 if v["deployment_identity"]!=sha(canonical(body)):raise ValueError("deployment identity")
 complete=dict(v);identity=complete.pop("manifest_identity")
 if identity!=sha(canonical(complete)):raise ValueError("manifest identity")

def render_workflow(template:bytes,v:Mapping[str,object])->bytes:
 text=template.decode("utf-8","strict").replace("@SCHEDULE_CRON@",str(v["schedule_cron"])).replace("@ATTEST_ACTION_COMMIT@",ATTEST_ACTION_COMMIT).replace("@UPLOAD_ACTION_COMMIT@",UPLOAD_ACTION_COMMIT)
 if re.search(r"@[A-Z0-9_]+@",text):raise ValueError("unresolved template token")
 return text.encode()

def verify_git(root:Path,v:Mapping[str,object],head:str,*,git_executable:str="/usr/bin/git",isolated:bool=True,deployment_ancestor:str=DEPLOYMENT_RUNTIME_COMMIT)->int:
 if not HEX40.fullmatch(head):raise ValueError("head")
 def git(*args:str)->bytes:
  env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent"} if isolated else None
  r=subprocess.run([git_executable,"-C",str(root),*args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=20,check=False)
  if r.returncode:raise ValueError("git evidence")
  return r.stdout
 actual=git("rev-parse","HEAD").decode("ascii","strict").strip()
 if actual!=head:raise ValueError("executing HEAD mismatch")
 git("merge-base","--is-ancestor",str(v["workflow_freeze_commit"]),head)
 git("merge-base","--is-ancestor",deployment_ancestor,str(v["workflow_freeze_commit"]))
 template=git("show",f"{v['workflow_freeze_commit']}:{TEMPLATE_PATH}")
 if sha(template)!=v["workflow_template_sha256"] or git("show",f"{head}:{WORKFLOW_PATH}")!=render_workflow(template,v):raise ValueError("workflow evidence")
 stamp=git("show","-s","--format=%ct",str(v["workflow_freeze_commit"])).decode("ascii","strict").strip()
 if not stamp.isdigit() or int(stamp)!=v["workflow_freeze_epoch"]:raise ValueError("workflow freeze time")
 return int(stamp)

def verify_worktree(root:Path,v:Mapping[str,object])->None:
 root=root.resolve(strict=True)
 template_input=root/TEMPLATE_PATH;active_input=root/WORKFLOW_PATH
 if template_input.is_symlink() or active_input.is_symlink():raise ValueError("workflow worktree containment")
 template=template_input.resolve(strict=True);active=active_input.resolve(strict=True)
 for path,relative in ((template,TEMPLATE_PATH),(active,WORKFLOW_PATH)):
  if path!=root/PurePosixPath(relative) or not path.is_file():raise ValueError("workflow worktree containment")
 template_bytes=template.read_bytes()
 if sha(template_bytes)!=v["workflow_template_sha256"] or active.read_bytes()!=render_workflow(template_bytes,v):raise ValueError("workflow worktree evidence")

def materialize(v:Mapping[str,object],root:Path)->dict[str,Path]:
 validate_manifest(v);base=root.resolve(strict=True)/"deployment"/"objects";out={}
 if not base.is_dir() or base.is_symlink():raise ValueError("object root")
 for name,row in v["objects"].items():
  digest,length,relative=_entry(row);input_path=root/PurePosixPath(relative)
  if input_path.is_symlink():raise ValueError("object containment")
  path=input_path.resolve(strict=True)
  if path.parent!=base or not path.is_file():raise ValueError("object containment")
  data=path.read_bytes()
  if len(data)!=length or sha(data)!=digest:raise ValueError("object bytes")
  out[name]=path
 if out["schedule-precommit.json"].read_bytes()!=schedule_payload(v):raise ValueError("payload bytes")
 return out

def verify_timestamp(v:Mapping[str,object],o:Mapping[str,Path],*,freeze_epoch:int)->None:
 verify_executable(o["openssl"]);verify_installed_dependency(o["deny-network-launcher.sh"],str(v["launcher_sha256"]))
 base=["/usr/bin/bash",str(o["deny-network-launcher.sh"]),"--launcher-sha256",str(v["launcher_sha256"]),"--expected-sha256",OPENSSL_EXECUTABLE_SHA256,str(o["openssl"])]
 def run(args:list[str]):return subprocess.run(base+args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent"},timeout=30,check=False)
 r=run(["ts","-verify","-data",str(o["schedule-precommit.json"]),"-in",str(o["rfc3161-receipt.tsr"]),"-CAfile",str(o["rfc3161-root.pem"])])
 if r.returncode or (r.stdout.strip(),r.stderr.strip()) not in ((b"Verification: OK",b""),(b"",b"Verification: OK")):raise ValueError("RFC3161 signature")
 r=run(["ts","-reply","-in",str(o["rfc3161-receipt.tsr"]),"-text"]);text=r.stdout.decode("utf-8","strict")
 alg=[x.strip() for x in text.splitlines() if x.strip().startswith("Hash Algorithm:")];times=[x.strip() for x in text.splitlines() if x.strip().startswith("Time stamp:")]
 if r.returncode or r.stderr or alg!=["Hash Algorithm: sha256"] or len(times)!=1:raise ValueError("RFC3161 fields")
 stamped=parsedate_to_datetime(times[0].split(":",1)[1].strip()).astimezone(timezone.utc);scheduled=datetime.strptime(str(v["scheduled_utc"]),"%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
 if stamped.timestamp()<=freeze_epoch or stamped>=scheduled:raise ValueError("RFC3161 phase order")

def load(path:Path)->Mapping[str,object]:
 if not path.is_absolute():path=Path.cwd()/path
 if path.is_symlink():raise ValueError("manifest file")
 path=path.resolve(strict=True)
 if not path.is_file() or path.stat().st_size>1048576:raise ValueError("manifest file")
 v=json.loads(path.read_text("utf-8"));validate_manifest(v);return v

def regular_input(path:Path,root:Path)->Path:
 """Resolve an input once and reject aliases, links, and paths outside the checkout."""
 root=root.resolve(strict=True);candidate=path if path.is_absolute() else Path.cwd()/path
 candidate=Path(os.path.abspath(candidate))
 if not candidate.is_relative_to(root):raise ValueError("input containment")
 cursor=root
 for part in candidate.relative_to(root).parts:
  cursor=cursor/part
  if cursor.is_symlink():raise ValueError("input containment")
 resolved=candidate.resolve(strict=True)
 if not resolved.is_file() or not resolved.is_relative_to(root):raise ValueError("input containment")
 return resolved

def run_claim(v:Mapping[str,object],head:str)->dict[str,object]:
 return {"deployment_identity":v["deployment_identity"],"repository_id":REPOSITORY_ID,"runtime_commit":RUNTIME_COMMIT,"workflow_commit":head,"run_id":os.environ.get("GITHUB_RUN_ID",""),"run_attempt":1,"event_name":"schedule","derivation_policy_identity":DERIVATION_POLICY_IDENTITY,"seed_plan_identity":SEED_PLAN_IDENTITY,"ca_sha256":v["ca_sha256"]}

def runtime_head()->str:
 head=os.environ.get("GITHUB_SHA","");ref=os.environ.get("GITHUB_REF","")
 if not HEX40.fullmatch(head) or ref!=DEFAULT_BRANCH_REF or os.environ.get("GITHUB_EVENT_NAME")!="schedule":raise ValueError("default-branch runtime identity")
 return head

def prepare_initiation(v:Mapping[str,object],head:str,dest:Path)->None:
 run=run_claim(v,head);one_shot_guard(FrozenRun(str(v["scheduled_utc"]),str(v["schedule_cron"]),head,str(v["deployment_identity"]),str(v["ca_sha256"])),os.environ,datetime.now(timezone.utc));claim=initiation_claim(run)
 if dest.exists():raise ValueError("initiation output")
 dest.mkdir();(dest/"pastila-capture-initiation.json").write_bytes(canonical(claim));(dest/"predicate.json").write_bytes(canonical(claim))

def main(argv:list[str]|None=None)->int:
 p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--prepare-initiation",type=Path);p.add_argument("--initiation-bundle",type=Path);p.add_argument("--execute",action="store_true");a=p.parse_args(argv)
 root=Path.cwd().resolve(strict=True);v=load(a.manifest);head=runtime_head()
 # This check is part of the production path, not merely a qualification helper.
 # /usr/bin/git is supplied by the immutable container image named in the workflow.
 verify_git(root,v,head);verify_worktree(root,v);o=materialize(v,root);verify_timestamp(v,o,freeze_epoch=int(v["workflow_freeze_epoch"]))
 if a.prepare_initiation:
  if a.execute or a.initiation_bundle:raise ValueError("phase mode")
  prepare_initiation(v,head,a.prepare_initiation);return 0
 if not a.execute or not a.initiation_bundle:raise ValueError("capture mode")
 runner_temp=os.environ.get("RUNNER_TEMP","")
 if not runner_temp:raise ValueError("runner temporary root")
 bundle_path=regular_input(a.initiation_bundle,Path(runner_temp))
 run=run_claim(v,head);runtime=LinuxVerifier(o["cosign"],o["deny-network-launcher.sh"],o["trusted-root.json"],str(v["cosign_sha256"]),str(v["launcher_sha256"]),str(v["trusted_root_sha256"]))
 frozen=FrozenRun(str(v["scheduled_utc"]),str(v["schedule_cron"]),head,str(v["deployment_identity"]),str(v["ca_sha256"]))
 run_once(config=frozen,environment=os.environ,now=datetime.now(timezone.utc),run=run,bundle=bundle_path.read_bytes(),bundle_path=bundle_path,verifier=runtime,ca_file=o["ca.pem"],output=Path("capture-output"))
 statement=json.loads((Path("capture-output")/"final-attestation-predicate.json").read_text("utf-8"))
 if set(statement)!={"_type","predicateType","subject","predicate"}:raise ValueError("final statement")
 (Path("capture-output")/"final-predicate.json").write_bytes(canonical(statement["predicate"]));return 0
if __name__=="__main__":raise SystemExit(main())
