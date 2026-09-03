"""V2.3.15 source-blind three-phase deployment boundary."""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, tempfile, urllib.request
from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from typing import Mapping
from .semantic_authority_capture_orchestrator_v2_3_7 import canonical
from .semantic_authority_deployment_v2_3_9 import (COSIGN_SHA256, DERIVATION_POLICY_IDENTITY,
    LINUX_LAUNCHER_SHA256, REPOSITORY_ID, REPOSITORY_SLUG, RUNTIME_COMMIT,
    SEED_PLAN_IDENTITY, LinuxVerifier, initiation_claim, sha, verify_linux_initiation)
from .semantic_authority_deployment_v2_3_10 import MAX_SCHEDULE_DELAY, FrozenRun, one_shot_guard, verify_installed_dependency
from .semantic_authority_cosign_v2_3_7 import TRUSTED_ROOT_SHA256
from .semantic_authority_rfc3161_verifier_v2_3_13 import OPENSSL_EXECUTABLE_SHA256, verify_executable

SCHEMA="PASTILA_CAPTURE_DEPLOYMENT_V2_3_15";PAYLOAD_SCHEMA="PASTILA_RFC3161_SCHEDULE_PRECOMMIT_V2_3_15"
ATTESTATION_ONLY_SUBJECT_SCHEMA="PASTILA_PRE_CAPTURE_ACTIVATION_STATE_V2_3_15"
ATTESTATION_ONLY_PREDICATE_TYPE="https://pastila.invalid/semantic-authority/pre-capture-activation/v2.3.15"
DEPLOYMENT_RUNTIME_COMMIT="26f66c54c02e18c05927b91d010290c2f712ca06"
TEMPLATE_PATH="deployment/semantic-authority-metadata-capture-v2-3-14.yml.template"
WORKFLOW_PATH=".github/workflows/semantic-authority-metadata-capture-v2-3-9.yml"
ATTEST_ACTION_COMMIT="1e69f48acb82d1966a394da916b4c1698aa569d6"
UPLOAD_ACTION_COMMIT="ea165f8d65b6e75b540449e92b4886f43607fa02"
DEFAULT_BRANCH_REF="refs/heads/public/v2.3.7-capture"
CA_BUNDLE_SHA256="9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
RFC3161_TSA_ENDPOINT="http://timestamp.digicert.com"
RFC3161_TSA_METHOD="POST";RFC3161_QUERY_CONTENT_TYPE="application/timestamp-query";RFC3161_REPLY_CONTENT_TYPE="application/timestamp-reply"
RFC3161_TSA_REDIRECTS=0;RFC3161_TSA_ATTEMPTS=1;RFC3161_TSA_NONCE=True;RFC3161_TSA_CERT_REQ=True
RFC3161_ROOT_SHA256="ce7d6b44f5d510391be98c8d76b18709400a30cd87659bfebe1c6f97ff5181ee"
RFC3161_INTERMEDIATE_SHA256="0edab770d65632eefbe6ccdb61034e224facf49a960acdf82ae13c64fa0a3519"
RFC3161_MAX_QUERY_BYTES=65536;RFC3161_MAX_REPLY_BYTES=1048576;RFC3161_TIMEOUT_SECONDS=20
HEX40=re.compile(r"^[0-9a-f]{40}$");HEX64=re.compile(r"^[0-9a-f]{64}$")
OBJECTS=frozenset({"ca.pem","cosign","deny-network-launcher.sh","openssl","rfc3161-request.tsq","rfc3161-receipt.tsr","rfc3161-root.pem","rfc3161-intermediate.pem","schedule-precommit.json","trusted-root.json"})
REQUEST_OBJECTS=frozenset({"deny-network-launcher.sh","openssl","rfc3161-request.tsq","schedule-precommit.json"})
RESPONSE_PROOF_OBJECTS=frozenset({"rfc3161-receipt.tsr","rfc3161-response.headers","rfc3161-receipt-record.json"})
REQUEST_AUTHORITY_SCHEMA="PASTILA_RFC3161_REQUEST_AUTHORITY_V1"
SCHEDULE_SELECTION_RULE="FIRST_UTC_HOUR_AT_LEAST_12_HOURS_AFTER_REPLACEMENT_FREEZE"
SCHEDULE_KEYS=("repository_slug","repository_id","default_branch_ref","core_runtime_commit","deployment_runtime_commit","workflow_freeze_commit","workflow_freeze_epoch","workflow_template_sha256","schedule_selection_rule","scheduled_utc","schedule_cron","rfc3161_tsa_endpoint","rfc3161_tsa_method","rfc3161_query_content_type","rfc3161_reply_content_type","rfc3161_tsa_redirects","rfc3161_tsa_attempts","rfc3161_tsa_nonce","rfc3161_tsa_cert_req","rfc3161_verifier_sha256","rfc3161_root_sha256","rfc3161_intermediate_sha256")

@dataclass(frozen=True)
class RequestSnapshot:
 schedule_bytes:bytes
 query_bytes:bytes
 openssl_bytes:bytes
 launcher_bytes:bytes
 openssl_path:Path
 launcher_path:Path

def derive_schedule(freeze_epoch:int)->tuple[str,str]:
 if not isinstance(freeze_epoch,int) or isinstance(freeze_epoch,bool) or freeze_epoch<=0:raise ValueError("workflow freeze epoch")
 threshold=datetime.fromtimestamp(freeze_epoch,tz=timezone.utc)+timedelta(hours=12)
 scheduled=threshold.replace(minute=0,second=0,microsecond=0)
 if scheduled<threshold:scheduled+=timedelta(hours=1)
 return scheduled.strftime("%Y-%m-%dT%H:%M:00Z"),f"{scheduled.minute} {scheduled.hour} {scheduled.day} {scheduled.month} *"

def schedule_payload(v:Mapping[str,object])->bytes:
 return canonical({"schema":PAYLOAD_SCHEMA,**{k:v[k] for k in SCHEDULE_KEYS}})+b"\n"

class _RejectRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):raise ValueError("RFC3161 redirect")

def _openssl(v:Mapping[str,object],o:Mapping[str,Path]|RequestSnapshot,args:list[str],*,input_bytes:bytes|None=None):
 openssl=o.openssl_path if isinstance(o,RequestSnapshot) else o["openssl"]
 launcher=o.launcher_path if isinstance(o,RequestSnapshot) else o["deny-network-launcher.sh"]
 launcher_sha256=str(v.get("launcher_sha256",LINUX_LAUNCHER_SHA256))
 verify_executable(openssl);verify_installed_dependency(launcher,launcher_sha256)
 base=["/usr/bin/bash",str(launcher),"--launcher-sha256",launcher_sha256,"--expected-sha256",OPENSSL_EXECUTABLE_SHA256,str(openssl)]
 return subprocess.run(base+args,input=input_bytes,stdin=subprocess.DEVNULL if input_bytes is None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent"},timeout=30,check=False)

def verify_rfc3161_query(v:Mapping[str,object],o:Mapping[str,Path]|RequestSnapshot)->bytes:
 query=_bound_rfc3161_query(v,o)
 r=_openssl(v,o,["ts","-query","-in","/dev/stdin","-text"],input_bytes=query)
 if r.returncode or r.stderr:raise ValueError("RFC3161 query parse")
 lines=[x.strip() for x in r.stdout.decode("utf-8","strict").splitlines()]
 if [x for x in lines if x.startswith("Hash Algorithm:")]!=["Hash Algorithm: sha256"]:raise ValueError("RFC3161 query algorithm")
 if [x for x in lines if x.startswith("Certificate required:")]!=["Certificate required: yes"]:raise ValueError("RFC3161 query certReq")
 nonce=[x for x in lines if x.startswith("Nonce:")]
 if len(nonce)!=1 or not re.fullmatch(r"Nonce:\s+0x[0-9A-Fa-f]+",nonce[0]):raise ValueError("RFC3161 query nonce")
 try:
  start=lines.index("Message data:")+1;end=next(i for i in range(start,len(lines)) if not re.match(r"^[0-9A-Fa-f]{4}\s*-",lines[i]))
 except (ValueError,StopIteration):raise ValueError("RFC3161 query imprint") from None
 chunks=[]
 for line in lines[start:end]:
  if not re.match(r"^[0-9A-Fa-f]{4}\s*-",line):raise ValueError("RFC3161 query imprint")
  chunks.extend(re.findall(r"[0-9A-Fa-f]{2}",line.split("-",1)[1][:49]))
 imprint="".join(chunks)
 if imprint.lower()!=sha(schedule_payload(v)):raise ValueError("RFC3161 query imprint")
 return query

def _bound_rfc3161_query(v:Mapping[str,object],o:Mapping[str,Path]|RequestSnapshot)->bytes:
 query=o.query_bytes if isinstance(o,RequestSnapshot) else o["rfc3161-request.tsq"].read_bytes()
 if not query or len(query)>RFC3161_MAX_QUERY_BYTES or sha(query)!=v["rfc3161_request_sha256"]:raise ValueError("RFC3161 query bytes")
 return query

def verify_rfc3161_submission_authority(v:Mapping[str,object],o:RequestSnapshot,root:Path,*,git_executable:str="/usr/bin/git",isolated:bool=True,deployment_ancestor:str=DEPLOYMENT_RUNTIME_COMMIT)->None:
 validate_request_authority(v)
 if not isinstance(o,RequestSnapshot):raise ValueError("RFC3161 immutable request snapshot")
 committed={"schedule-precommit.json":o.schedule_bytes,"rfc3161-request.tsq":o.query_bytes,"openssl":o.openssl_bytes,"deny-network-launcher.sh":o.launcher_bytes}
 if any(len(committed[name])!=v["objects"][name]["length"] or sha(committed[name])!=v["objects"][name]["sha256"] for name in REQUEST_OBJECTS):raise ValueError("RFC3161 request snapshot bytes")
 if o.schedule_bytes!=schedule_payload(v):raise ValueError("RFC3161 schedule preimage")
 root=root.resolve(strict=True)
 def git(*args:str)->bytes:
  env={"PATH":"/usr/bin:/bin","HOME":"/nonexistent"} if isolated else None
  r=subprocess.run([git_executable,"-C",str(root),*args],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=20,check=False)
  if r.returncode:raise ValueError("RFC3161 freeze git evidence")
  return r.stdout
 head=git("rev-parse","HEAD").decode("ascii","strict").strip()
 freeze=str(v["workflow_freeze_commit"])
 if head!=freeze:raise ValueError("RFC3161 freeze must equal HEAD")
 git("merge-base","--is-ancestor",deployment_ancestor,freeze)
 template=git("show",f"{freeze}:{TEMPLATE_PATH}")
 if sha(template)!=v["workflow_template_sha256"]:raise ValueError("RFC3161 freeze template")
 stamp=git("show","-s","--format=%ct",freeze).decode("ascii","strict").strip()
 if not stamp.isdigit() or int(stamp)!=v["workflow_freeze_epoch"]:raise ValueError("RFC3161 freeze epoch")

def submit_rfc3161_query(v:Mapping[str,object],o:RequestSnapshot,*,root:Path)->bytes:
 verify_rfc3161_submission_authority(v,o,root)
 query=verify_rfc3161_query(v,o)
 request=urllib.request.Request(RFC3161_TSA_ENDPOINT,data=query,method=RFC3161_TSA_METHOD,headers={"Content-Type":RFC3161_QUERY_CONTENT_TYPE,"Accept":RFC3161_REPLY_CONTENT_TYPE})
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_RejectRedirect())
 with opener.open(request,timeout=RFC3161_TIMEOUT_SECONDS) as response:
  if response.status!=200 or response.geturl()!=RFC3161_TSA_ENDPOINT:raise ValueError("RFC3161 response authority")
  if response.headers.get_content_type()!=RFC3161_REPLY_CONTENT_TYPE:raise ValueError("RFC3161 response content type")
  receipt=response.read(RFC3161_MAX_REPLY_BYTES+1)
 if not receipt or len(receipt)>RFC3161_MAX_REPLY_BYTES:raise ValueError("RFC3161 response size")
 return receipt

def _entry(x:object)->tuple[str,int,str]:
 if not isinstance(x,dict) or set(x)!={"sha256","length","path"}:raise ValueError("object schema")
 path=str(x["path"]);p=PurePosixPath(path);digest=str(x["sha256"]);length=x["length"]
 if "\\" in path or p.is_absolute() or str(p)!=path or ".." in p.parts or p.parts[:2]!=("deployment","objects"):raise ValueError("object path")
 if not HEX64.fullmatch(digest) or not isinstance(length,int) or isinstance(length,bool) or length<=0:raise ValueError("object commitment")
 return digest,length,path

def validate_request_authority(v:Mapping[str,object])->None:
 required={"schema",*SCHEDULE_KEYS,"schedule_payload_sha256","rfc3161_request_sha256","objects","request_authority_identity"}
 if set(v)!=required or v["schema"]!=REQUEST_AUTHORITY_SCHEMA:raise ValueError("RFC3161 request authority schema")
 if v["repository_slug"]!=REPOSITORY_SLUG or v["repository_id"]!=REPOSITORY_ID or v["default_branch_ref"]!=DEFAULT_BRANCH_REF or v["core_runtime_commit"]!=RUNTIME_COMMIT or v["deployment_runtime_commit"]!=DEPLOYMENT_RUNTIME_COMMIT:raise ValueError("RFC3161 request repository authority")
 if not HEX40.fullmatch(str(v["workflow_freeze_commit"])) or not isinstance(v["workflow_freeze_epoch"],int) or isinstance(v["workflow_freeze_epoch"],bool) or v["workflow_freeze_epoch"]<=0:raise ValueError("RFC3161 request freeze")
 if not HEX64.fullmatch(str(v["workflow_template_sha256"])) or v["schedule_selection_rule"]!=SCHEDULE_SELECTION_RULE:raise ValueError("RFC3161 request schedule authority")
 if (v["scheduled_utc"],v["schedule_cron"])!=derive_schedule(v["workflow_freeze_epoch"]):raise ValueError("RFC3161 request deterministic schedule")
 fixed={"rfc3161_tsa_endpoint":RFC3161_TSA_ENDPOINT,"rfc3161_tsa_method":RFC3161_TSA_METHOD,"rfc3161_query_content_type":RFC3161_QUERY_CONTENT_TYPE,"rfc3161_reply_content_type":RFC3161_REPLY_CONTENT_TYPE,"rfc3161_tsa_redirects":RFC3161_TSA_REDIRECTS,"rfc3161_tsa_attempts":RFC3161_TSA_ATTEMPTS,"rfc3161_tsa_nonce":RFC3161_TSA_NONCE,"rfc3161_tsa_cert_req":RFC3161_TSA_CERT_REQ,"rfc3161_verifier_sha256":OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":RFC3161_ROOT_SHA256,"rfc3161_intermediate_sha256":RFC3161_INTERMEDIATE_SHA256}
 if any(v[k]!=x for k,x in fixed.items()):raise ValueError("RFC3161 request frozen profile")
 if v["schedule_payload_sha256"]!=sha(schedule_payload(v)) or not HEX64.fullmatch(str(v["rfc3161_request_sha256"])):raise ValueError("RFC3161 request digest")
 rows=v["objects"]
 if not isinstance(rows,dict) or set(rows)!=REQUEST_OBJECTS:raise ValueError("RFC3161 request object closure")
 parsed={k:_entry(x) for k,x in rows.items()}
 binds={"openssl":"rfc3161_verifier_sha256","deny-network-launcher.sh":"launcher_sha256","rfc3161-request.tsq":"rfc3161_request_sha256","schedule-precommit.json":"schedule_payload_sha256"}
 # The launcher is fixed by the deployment runtime even though it is not part of the timestamp payload.
 if parsed["deny-network-launcher.sh"][0]!=LINUX_LAUNCHER_SHA256 or any(parsed[n][0]!=v[f] for n,f in binds.items() if n!="deny-network-launcher.sh"):raise ValueError("RFC3161 request object binding")
 body=dict(v);identity=body.pop("request_authority_identity")
 if identity!=sha(canonical(body)):raise ValueError("RFC3161 request authority identity")

def materialize_request(v:Mapping[str,object],root:Path)->RequestSnapshot:
 validate_request_authority(v);base=root.resolve(strict=True)/"deployment"/"objects";paths={};data_by_name={}
 if not base.is_dir() or base.is_symlink():raise ValueError("object root")
 for name,row in v["objects"].items():
  digest,length,relative=_entry(row);input_path=root/PurePosixPath(relative)
  if input_path.is_symlink():raise ValueError("object containment")
  path=input_path.resolve(strict=True)
  if path.parent!=base or not path.is_file():raise ValueError("object containment")
  data=path.read_bytes()
  if len(data)!=length or sha(data)!=digest:raise ValueError("object bytes")
  paths[name]=path;data_by_name[name]=data
 if data_by_name["schedule-precommit.json"]!=schedule_payload(v):raise ValueError("payload bytes")
 return RequestSnapshot(data_by_name["schedule-precommit.json"],data_by_name["rfc3161-request.tsq"],data_by_name["openssl"],data_by_name["deny-network-launcher.sh"],paths["openssl"],paths["deny-network-launcher.sh"])

def verify_response_proof_closure(root:Path,proof_objects:Mapping[str,object])->None:
 base=root.resolve(strict=True)/"deployment"/"objects"
 if set(proof_objects)!=RESPONSE_PROOF_OBJECTS:raise ValueError("RFC3161 response proof closure")
 for name,row in proof_objects.items():
  digest,length,relative=_entry(row);input_path=root/PurePosixPath(relative)
  if input_path.is_symlink():raise ValueError("RFC3161 response proof object")
  path=input_path.resolve(strict=True);data=path.read_bytes()
  if path.parent!=base or len(data)!=length or sha(data)!=digest:raise ValueError("RFC3161 response proof object")

def validate_manifest(v:Mapping[str,object])->None:
 required={"schema","repository_slug","repository_id","default_branch_ref","core_runtime_commit","deployment_runtime_commit","workflow_freeze_commit","workflow_freeze_epoch","workflow_template_sha256","schedule_selection_rule","scheduled_utc","schedule_cron","rfc3161_tsa_endpoint","rfc3161_tsa_method","rfc3161_query_content_type","rfc3161_reply_content_type","rfc3161_tsa_redirects","rfc3161_tsa_attempts","rfc3161_tsa_nonce","rfc3161_tsa_cert_req","rfc3161_verifier_sha256","rfc3161_root_sha256","rfc3161_intermediate_sha256","rfc3161_request_sha256","ca_sha256","cosign_sha256","launcher_sha256","trusted_root_sha256","derivation_policy_identity","seed_plan_identity","schedule_payload_sha256","objects","deployment_identity","manifest_identity"}
 if set(v)!=required or v["schema"]!=SCHEMA or v["repository_slug"]!=REPOSITORY_SLUG or v["repository_id"]!=REPOSITORY_ID or v["default_branch_ref"]!=DEFAULT_BRANCH_REF or v["core_runtime_commit"]!=RUNTIME_COMMIT or v["deployment_runtime_commit"]!=DEPLOYMENT_RUNTIME_COMMIT:raise ValueError("manifest schema")
 if not HEX40.fullmatch(str(v["workflow_freeze_commit"])) or not HEX64.fullmatch(str(v["workflow_template_sha256"])):raise ValueError("workflow freeze")
 if not isinstance(v["workflow_freeze_epoch"],int) or isinstance(v["workflow_freeze_epoch"],bool) or v["workflow_freeze_epoch"]<=0:raise ValueError("workflow freeze epoch")
 if v["schedule_selection_rule"]!=SCHEDULE_SELECTION_RULE:raise ValueError("schedule authority binding")
 scheduled=datetime.strptime(str(v["scheduled_utc"]),"%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
 if v["schedule_cron"]!=f"{scheduled.minute} {scheduled.hour} {scheduled.day} {scheduled.month} *":raise ValueError("schedule convergence")
 if (v["scheduled_utc"],v["schedule_cron"])!=derive_schedule(v["workflow_freeze_epoch"]):raise ValueError("deterministic schedule selection")
 fixed={"rfc3161_tsa_endpoint":RFC3161_TSA_ENDPOINT,"rfc3161_tsa_method":RFC3161_TSA_METHOD,"rfc3161_query_content_type":RFC3161_QUERY_CONTENT_TYPE,"rfc3161_reply_content_type":RFC3161_REPLY_CONTENT_TYPE,"rfc3161_tsa_redirects":RFC3161_TSA_REDIRECTS,"rfc3161_tsa_attempts":RFC3161_TSA_ATTEMPTS,"rfc3161_tsa_nonce":RFC3161_TSA_NONCE,"rfc3161_tsa_cert_req":RFC3161_TSA_CERT_REQ,"rfc3161_verifier_sha256":OPENSSL_EXECUTABLE_SHA256,"rfc3161_root_sha256":RFC3161_ROOT_SHA256,"rfc3161_intermediate_sha256":RFC3161_INTERMEDIATE_SHA256,"ca_sha256":CA_BUNDLE_SHA256,"cosign_sha256":COSIGN_SHA256,"launcher_sha256":LINUX_LAUNCHER_SHA256,"trusted_root_sha256":TRUSTED_ROOT_SHA256,"derivation_policy_identity":DERIVATION_POLICY_IDENTITY,"seed_plan_identity":SEED_PLAN_IDENTITY}
 if any(v[k]!=x for k,x in fixed.items()):raise ValueError("frozen dependency")
 for k in ("rfc3161_root_sha256","rfc3161_intermediate_sha256","rfc3161_request_sha256","ca_sha256","trusted_root_sha256","schedule_payload_sha256","deployment_identity"):
  if not HEX64.fullmatch(str(v[k])):raise ValueError("digest")
 if sha(schedule_payload(v))!=v["schedule_payload_sha256"]:raise ValueError("payload binding")
 rows=v["objects"]
 if not isinstance(rows,dict) or set(rows)!=OBJECTS:raise ValueError("object closure")
 parsed={k:_entry(x) for k,x in rows.items()}
 if len({x[2] for x in parsed.values()})!=len(parsed):raise ValueError("object alias")
 binds={"openssl":"rfc3161_verifier_sha256","rfc3161-root.pem":"rfc3161_root_sha256","rfc3161-intermediate.pem":"rfc3161_intermediate_sha256","rfc3161-request.tsq":"rfc3161_request_sha256","ca.pem":"ca_sha256","cosign":"cosign_sha256","deny-network-launcher.sh":"launcher_sha256","trusted-root.json":"trusted_root_sha256","schedule-precommit.json":"schedule_payload_sha256"}
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
 query=verify_rfc3161_query(v,o)
 r=_openssl(v,o,["ts","-verify","-queryfile","/dev/stdin","-in",str(o["rfc3161-receipt.tsr"]),"-CAfile",str(o["rfc3161-root.pem"]),"-untrusted",str(o["rfc3161-intermediate.pem"])],input_bytes=query)
 if r.returncode or (r.stdout.strip(),r.stderr.strip()) not in ((b"Verification: OK",b""),(b"",b"Verification: OK")):raise ValueError("RFC3161 signature")
 r=_openssl(v,o,["ts","-reply","-in",str(o["rfc3161-receipt.tsr"]),"-text"]);text=r.stdout.decode("utf-8","strict")
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

def complete_attestation_only(v:Mapping[str,object],head:str,bundle_path:Path,objects:Mapping[str,Path],output:Path)->dict[str,object]:
 run=run_claim(v,head)
 frozen=FrozenRun(str(v["scheduled_utc"]),str(v["schedule_cron"]),head,str(v["deployment_identity"]),str(v["ca_sha256"]))
 one_shot_guard(frozen,os.environ,datetime.now(timezone.utc))
 runtime=LinuxVerifier(objects["cosign"],objects["deny-network-launcher.sh"],objects["trusted-root.json"],str(v["cosign_sha256"]),str(v["launcher_sha256"]),str(v["trusted_root_sha256"]))
 initiation=verify_linux_initiation(run=run,bundle=bundle_path.read_bytes(),bundle_path=bundle_path,repository_slug=REPOSITORY_SLUG,runtime=runtime)
 prohibitions={"capture_executed":False,"publisher_metadata_acquired":False,"registry_metadata_acquired":False}
 subject={"schema":ATTESTATION_ONLY_SUBJECT_SCHEMA,"mode":"ATTESTATION_ONLY_PRE_CAPTURE","repository":REPOSITORY_SLUG,
          "repository_id":REPOSITORY_ID,"workflow_commit":head,"deployment_identity":v["deployment_identity"],
          "scheduled_utc":v["scheduled_utc"],"schedule_cron":v["schedule_cron"],"initiation":initiation,"prohibitions":prohibitions}
 predicate={"mode":subject["mode"],"deployment_identity":v["deployment_identity"],"scheduled_utc":v["scheduled_utc"],
            "schedule_cron":v["schedule_cron"],"initiation":initiation,"prohibitions":prohibitions}
 if output.exists():raise ValueError("attestation-only output must be absent")
 temporary=Path(tempfile.mkdtemp(prefix=f".{output.name}-",dir=output.parent))
 try:
  (temporary/"pre-capture-deployment-state.json").write_bytes(canonical(subject)+b"\n")
  (temporary/"final-predicate.json").write_bytes(canonical(predicate)+b"\n")
  os.replace(temporary,output)
 except BaseException:
  if temporary.exists():shutil.rmtree(temporary)
  raise
 return subject

def main(argv:list[str]|None=None)->int:
 p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--prepare-initiation",type=Path);p.add_argument("--initiation-bundle",type=Path);p.add_argument("--complete-attestation-only",action="store_true");a=p.parse_args(argv)
 root=Path.cwd().resolve(strict=True);v=load(a.manifest);head=runtime_head()
 # This check is part of the production path, not merely a qualification helper.
 # /usr/bin/git is supplied by the immutable container image named in the workflow.
 verify_git(root,v,head);verify_worktree(root,v);o=materialize(v,root);verify_timestamp(v,o,freeze_epoch=int(v["workflow_freeze_epoch"]))
 if a.prepare_initiation:
  if a.complete_attestation_only or a.initiation_bundle:raise ValueError("phase mode")
  prepare_initiation(v,head,a.prepare_initiation);return 0
 if not a.complete_attestation_only or not a.initiation_bundle:raise ValueError("attestation-only mode")
 runner_temp=os.environ.get("RUNNER_TEMP","")
 if not runner_temp:raise ValueError("runner temporary root")
 bundle_path=regular_input(a.initiation_bundle,Path(runner_temp))
 complete_attestation_only(v,head,bundle_path,o,Path("attestation-only-output"));return 0
if __name__=="__main__":raise SystemExit(main())
