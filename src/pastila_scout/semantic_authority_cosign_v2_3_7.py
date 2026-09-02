"""Real Cosign/TUF and deny-network verifier boundary for V2.3.7."""
from __future__ import annotations
import base64,hashlib,json,re,subprocess
from pathlib import Path
from typing import Any,Mapping
from . import semantic_authority_public_attestation_v2_3_6 as v236

COSIGN_VERSION="v3.1.3"
COSIGN_LINUX_SHA256="4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71"
CHECKSUMS_SHA256="aec2a6f68d307b09ae196e388dc691a146fa8bdba7fcce9ca4ca41b918adfa63"
CHECKSUM_BUNDLE_SHA256="976bcb216e45ed0274e464e2e16d81e84cc85a69b3ed6e3488c1e7cda116379a"
TRUSTED_ROOT_SHA256="6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66"
TRUSTED_ROOT_LENGTH=6787
TUF_ROOT_V1_SHA256="cd7549b15e7b4e660a89c950bca1bce262a524a5cf909952b66951b5c8667bc6"
TUF_TIMESTAMP_SHA256="7f3be01f12aca118c993f0f3831ba51f0c4cd11c1ce29941ab9f0ffb1ea26f45"
TUF_SNAPSHOT_V165_SHA256="8f784ab614ec62bfdd5f568eb2a2e3011668449ba235ed4eb7befa99f8469933"
TUF_TARGETS_V14_SHA256="6a697f7f8908c8ab26c11786ecb490b54acec97fa8c802e399f065f8a0cc1acd"
WSL_SHA256="7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757"
CONTAINMENT_DEPENDENCY_ROOT="389e3366b3b7ac7a241032a7b4883d19d7b449428ea019e0a6fae650d24b500b"
HEX64=re.compile(r"^[0-9a-f]{64}$")

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def canonical(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def identity(v:Mapping[str,Any],field:str)->str:
 body=dict(v);body.pop(field,None);return sha(canonical(body))

def qualify_supply_chain(*,cosign:Path,checksums:Path,checksum_bundle:Path,trusted_root:Path,tuf_root:Path,timestamp:Path,snapshot:Path,targets:Path)->None:
 """Close hashes, signed checksum subject, and TUF target length/digest."""
 files=((cosign,COSIGN_LINUX_SHA256),(checksums,CHECKSUMS_SHA256),(checksum_bundle,CHECKSUM_BUNDLE_SHA256),(trusted_root,TRUSTED_ROOT_SHA256),(tuf_root,TUF_ROOT_V1_SHA256),(timestamp,TUF_TIMESTAMP_SHA256),(snapshot,TUF_SNAPSHOT_V165_SHA256),(targets,TUF_TARGETS_V14_SHA256))
 if any(not p.is_file() or p.is_symlink() or sha(p.read_bytes())!=h for p,h in files):raise ValueError("supply-chain file pin")
 lines=checksums.read_text(encoding="utf-8").splitlines()
 if lines.count(f"{COSIGN_LINUX_SHA256}  cosign-linux-amd64")!=1:raise ValueError("Cosign checksum closure")
 timestamp_value=json.loads(timestamp.read_text(encoding="utf-8"))
 snapshot_value=json.loads(snapshot.read_text(encoding="utf-8"))
 targets_value=json.loads(targets.read_text(encoding="utf-8"))
 if timestamp_value["signed"].get("version")!=772 or timestamp_value["signed"].get("meta")!={"snapshot.json":{"version":165}}:raise ValueError("TUF timestamp closure")
 if snapshot_value["signed"].get("version")!=165 or snapshot_value["signed"].get("meta",{}).get("targets.json")!={"version":14}:raise ValueError("TUF snapshot closure")
 if json.loads(tuf_root.read_text(encoding="utf-8"))["signed"].get("version")!=1 or targets_value["signed"].get("version")!=14:raise ValueError("TUF version closure")
 target=targets_value["signed"]["targets"]["trusted_root.json"]
 if target!={"hashes":{"sha256":TRUSTED_ROOT_SHA256},"length":TRUSTED_ROOT_LENGTH}:raise ValueError("TUF trusted-root target")
 root=json.loads(trusted_root.read_text(encoding="utf-8"))
 if root.get("mediaType")!="application/vnd.dev.sigstore.trustedroot+json;version=0.1" or len(root.get("certificateAuthorities",[]))<1 or len(root.get("tlogs",[]))<1:raise ValueError("trusted-root schema")

def run_contained(*,wsl:Path,distribution:str,launcher_host:Path,launcher_linux:str,launcher_sha256:str,cosign_linux:str,args:list[str])->subprocess.CompletedProcess:
 """Run only through the hash-pinned WSL user/network namespace launcher."""
 if not HEX64.fullmatch(launcher_sha256) or not HEX64.fullmatch(COSIGN_LINUX_SHA256):raise ValueError("launcher pins")
 if not wsl.is_file() or wsl.is_symlink() or sha(wsl.read_bytes())!=WSL_SHA256:raise ValueError("WSL executable pin")
 if not launcher_host.is_file() or launcher_host.is_symlink() or sha(launcher_host.read_bytes())!=launcher_sha256:raise ValueError("launcher hash")
 if not launcher_linux.startswith("/mnt/") or not cosign_linux.startswith("/mnt/"):raise ValueError("noncanonical WSL path")
 command=[str(wsl),"--distribution",distribution,"--user","root","--exec","bash",launcher_linux,"--launcher-sha256",launcher_sha256,"--expected-sha256",COSIGN_LINUX_SHA256,cosign_linux,*args]
 return subprocess.run(command,capture_output=True,timeout=90,check=False,env={"SystemRoot":r"C:\Windows","WINDIR":r"C:\Windows"})

def verify_release_checksum_bundle(*,wsl:Path,distribution:str,launcher_host:Path,launcher_linux:str,launcher_sha256:str,cosign_linux:str,bundle_linux:str,trusted_root_linux:str,checksums_linux:str)->None:
 """Verify the signed upstream checksum manifest with the real contained CLI."""
 result=run_contained(wsl=wsl,distribution=distribution,launcher_host=launcher_host,launcher_linux=launcher_linux,launcher_sha256=launcher_sha256,cosign_linux=cosign_linux,args=["verify-blob","--bundle",bundle_linux,"--trusted-root",trusted_root_linux,"--certificate-identity","keyless@projectsigstore.iam.gserviceaccount.com","--certificate-oidc-issuer","https://accounts.google.com",checksums_linux])
 if result.returncode or b"Verified OK" not in result.stderr+result.stdout:raise ValueError("Cosign signed-release verification")

def verify_blob_attestation(*,wsl:Path,distribution:str,launcher_host:Path,launcher_linux:str,launcher_sha256:str,cosign_linux:str,bundle_linux:str,trusted_root_linux:str,digest:str,certificate_identity:str,oidc_issuer:str,github_repository:str|None=None,github_sha:str|None=None,github_trigger:str|None=None)->None:
 """Cryptographically verify an offline Sigstore attestation under OS isolation."""
 if not HEX64.fullmatch(digest):raise ValueError("subject digest")
 args=["verify-blob-attestation","--bundle",bundle_linux,"--trusted-root",trusted_root_linux,"--certificate-identity",certificate_identity,"--certificate-oidc-issuer",oidc_issuer,"--digest",digest,"--digestAlg","sha256"]
 claims=(("--certificate-github-workflow-repository",github_repository),("--certificate-github-workflow-sha",github_sha),("--certificate-github-workflow-trigger",github_trigger))
 if any(value is None for _,value in claims) and not all(value is None for _,value in claims):raise ValueError("partial GitHub certificate claims")
 for flag,value in claims:
  if value is not None:args.extend((flag,value))
 result=run_contained(wsl=wsl,distribution=distribution,launcher_host=launcher_host,launcher_linux=launcher_linux,launcher_sha256=launcher_sha256,cosign_linux=cosign_linux,args=args)
 if result.returncode or b"Verified OK" not in result.stderr+result.stdout:raise ValueError("Cosign attestation verification")

def decode_dsse_statement(bundle:bytes)->Mapping[str,Any]:
 try:
  value=json.loads(bundle);envelope=value["dsseEnvelope"]
  if set(envelope)!={"payload","payloadType","signatures"} or envelope["payloadType"]!="application/vnd.in-toto+json":raise ValueError
  statement=json.loads(base64.b64decode(envelope["payload"],validate=True))
 except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:raise ValueError("Sigstore DSSE bundle schema") from exc
 if statement.get("_type") not in {"https://in-toto.io/Statement/v0.1","https://in-toto.io/Statement/v1"}:raise ValueError("in-toto statement type")
 return statement

def validate_deployment_manifest(v:Mapping[str,Any],*,v236_governance:Mapping[str,Any],v236_deployment:Mapping[str,Any])->None:
 v236.validate_deployment(v236_deployment,v236_governance)
 required={"schema","v2_3_6_governance_identity","v2_3_6_deployment_identity","repository_slug","repository_id","owner_id","workflow_commit","workflow_blob_sha256","schedule_precommit_identity","cosign_sha256","launcher_sha256","wsl_sha256","containment_dependency_root","trusted_root_sha256","tuf_root_version","tuf_snapshot_version","tuf_targets_version","deployment_identity"}
 if set(v)!=required or v["schema"]!="SEMANTIC_AUTHORITY_PUBLIC_ATTESTATION_DEPLOYMENT_V2_3_7" or v["v2_3_6_governance_identity"]!=v236_governance["governance_identity"] or v["v2_3_6_deployment_identity"]!=v236_deployment["deployment_identity"]:raise ValueError("deployment manifest schema/lineage")
 for field in ("repository_slug","repository_id","owner_id","workflow_commit","workflow_blob_sha256"):
  if v[field]!=v236_deployment[field]:raise ValueError("V2.3.6 deployment binding")
 if not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+",str(v["repository_slug"])) or not all(str(v[x]).isdigit() and int(v[x])>0 for x in ("repository_id","owner_id")):raise ValueError("repository identity")
 if not re.fullmatch(r"[0-9a-f]{40}",str(v["workflow_commit"])):raise ValueError("workflow commit")
 for field in ("workflow_blob_sha256","schedule_precommit_identity","cosign_sha256","launcher_sha256","wsl_sha256","containment_dependency_root","trusted_root_sha256"):
  if not HEX64.fullmatch(str(v[field])):raise ValueError("deployment hash")
 if v["cosign_sha256"]!=COSIGN_LINUX_SHA256 or v["wsl_sha256"]!=WSL_SHA256 or v["containment_dependency_root"]!=CONTAINMENT_DEPENDENCY_ROOT or v["trusted_root_sha256"]!=TRUSTED_ROOT_SHA256:raise ValueError("verifier trust skew")
 if (v["tuf_root_version"],v["tuf_snapshot_version"],v["tuf_targets_version"])!=(1,165,14):raise ValueError("TUF version skew")
 if v["deployment_identity"]!=identity(v,"deployment_identity"):raise ValueError("deployment identity")
