"""Fail-closed executable CLI and deployment identity convergence for V2.3.11."""
from __future__ import annotations
import argparse, json, os, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
from .semantic_authority_capture_orchestrator_v2_3_7 import canonical
from .semantic_authority_deployment_v2_3_9 import LinuxVerifier, REPOSITORY_ID, REPOSITORY_SLUG, RUNTIME_COMMIT, sha
from .semantic_authority_deployment_v2_3_10 import FrozenRun, run_once, verify_installed_dependency

SCHEMA="PASTILA_CAPTURE_DEPLOYMENT_V2_3_11"
HEX40=re.compile(r"^[0-9a-f]{40}$");HEX64=re.compile(r"^[0-9a-f]{64}$");UINT=re.compile(r"^[1-9][0-9]*$")

def validate_manifest(value:Mapping[str,object])->None:
    required={"schema","repository_slug","repository_id","core_runtime_commit","deployment_runtime_commit","workflow_commit","deployment_identity","scheduled_utc","schedule_cron","ca_sha256","cosign_sha256","launcher_sha256","trusted_root_sha256","derivation_policy_identity","seed_plan_identity","manifest_identity"}
    if set(value)!=required or value["schema"]!=SCHEMA or value["repository_slug"]!=REPOSITORY_SLUG or value["repository_id"]!=REPOSITORY_ID:raise ValueError("manifest schema/repository")
    if (value["core_runtime_commit"]!=RUNTIME_COMMIT or not HEX40.fullmatch(str(value["deployment_runtime_commit"])) or not HEX40.fullmatch(str(value["workflow_commit"]))
        or len({value["core_runtime_commit"],value["deployment_runtime_commit"],value["workflow_commit"]})!=3):raise ValueError("runtime/workflow identity separation")
    for key in ("deployment_identity","ca_sha256","cosign_sha256","launcher_sha256","trusted_root_sha256","derivation_policy_identity","seed_plan_identity"):
        if not HEX64.fullmatch(str(value[key])):raise ValueError("manifest digest")
    deployment_body={k:v for k,v in value.items() if k not in {"deployment_identity","manifest_identity"}}
    if value["deployment_identity"]!=sha(canonical(deployment_body)):raise ValueError("deployment identity")
    body=dict(value);identity=body.pop("manifest_identity")
    if identity!=sha(canonical(body)):raise ValueError("manifest identity")
    frozen=FrozenRun(str(value["scheduled_utc"]),str(value["schedule_cron"]),str(value["workflow_commit"]),str(value["deployment_identity"]),str(value["ca_sha256"]))
    # Validate timestamp/cron syntax without pretending a run is occurring.
    scheduled=datetime.strptime(frozen.scheduled_utc,"%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
    if frozen.schedule_cron!=f"{scheduled.minute} {scheduled.hour} {scheduled.day} {scheduled.month} *":raise ValueError("manifest schedule")

def _load(path:Path)->Mapping[str,object]:
    if not path.is_file() or path.is_symlink() or len(path.read_bytes())>1024*1024:raise ValueError("manifest file")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):raise ValueError("manifest object")
    validate_manifest(value);return value

def checkout_commit(root:Path)->str:
    result=subprocess.run(["/usr/bin/git","-C",str(root),"rev-parse","HEAD"],capture_output=True,check=False,timeout=15,env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent"})
    value=result.stdout.decode("ascii",errors="strict").strip() if result.returncode==0 else ""
    if not HEX40.fullmatch(value):raise ValueError("checkout commit evidence")
    return value

def execute(manifest:Mapping[str,object],*,checkout_sha:str,bundle:Path,cosign:Path,launcher:Path,trusted_root:Path,ca:Path,output:Path,now:datetime)->dict[str,object]:
    validate_manifest(manifest)
    if checkout_sha!=manifest["deployment_runtime_commit"]:raise ValueError("deployment runtime checkout")
    for path,key in ((cosign,"cosign_sha256"),(launcher,"launcher_sha256"),(trusted_root,"trusted_root_sha256"),(ca,"ca_sha256")):verify_installed_dependency(path,str(manifest[key]))
    run={"deployment_identity":manifest["deployment_identity"],"repository_id":REPOSITORY_ID,"runtime_commit":manifest["core_runtime_commit"],"workflow_commit":manifest["workflow_commit"],"run_id":os.environ.get("GITHUB_RUN_ID",""),"run_attempt":1,"event_name":"schedule","derivation_policy_identity":manifest["derivation_policy_identity"],"seed_plan_identity":manifest["seed_plan_identity"],"ca_sha256":manifest["ca_sha256"]}
    frozen=FrozenRun(str(manifest["scheduled_utc"]),str(manifest["schedule_cron"]),str(manifest["workflow_commit"]),str(manifest["deployment_identity"]),str(manifest["ca_sha256"]))
    verifier=LinuxVerifier(cosign,launcher,trusted_root,str(manifest["cosign_sha256"]),str(manifest["launcher_sha256"]),str(manifest["trusted_root_sha256"]))
    return run_once(config=frozen,environment=os.environ,now=now,run=run,bundle=bundle.read_bytes(),bundle_path=bundle,verifier=verifier,ca_file=ca,output=output)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--bundle",type=Path,required=True);p.add_argument("--cosign",type=Path,required=True);p.add_argument("--launcher",type=Path,required=True);p.add_argument("--trusted-root",type=Path,required=True);p.add_argument("--ca",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args(argv)
    execute(_load(a.manifest),checkout_sha=checkout_commit(Path.cwd()),bundle=a.bundle,cosign=a.cosign,launcher=a.launcher,trusted_root=a.trusted_root,ca=a.ca,output=a.output,now=datetime.now(timezone.utc));return 0
if __name__=="__main__":raise SystemExit(main())
