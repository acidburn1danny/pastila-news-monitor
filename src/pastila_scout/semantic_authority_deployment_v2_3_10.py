"""Inert, source-blind production deployment boundary for V2.3.10."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Mapping
from urllib.parse import urlsplit

from .semantic_authority_capture_orchestrator_v2_3_7 import Capture, canonical
from .semantic_authority_deployment_v2_3_9 import (
    MAX_REQUESTS, REPOSITORY_ID, REPOSITORY_SLUG, RUNTIME_COMMIT,
    CaptureExecution, LinuxVerifier, _allowed_request, execute_capture, sha,
    verify_linux_initiation,
)

DOMAIN = "PASTILA_CAPTURE_DEPLOYMENT_V2_3_10"
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
PROXY_KEYS = frozenset(k for stem in ("http_proxy","https_proxy","all_proxy","no_proxy") for k in (stem,stem.upper()))


@dataclass(frozen=True)
class FrozenRun:
    scheduled_utc: str
    schedule_cron: str
    workflow_commit: str
    deployment_identity: str
    ca_sha256: str


def one_shot_guard(config: FrozenRun, environment: Mapping[str, str], now: datetime) -> None:
    expected={"GITHUB_EVENT_NAME":"schedule","GITHUB_RUN_ATTEMPT":"1","GITHUB_REPOSITORY":REPOSITORY_SLUG,
              "GITHUB_REPOSITORY_ID":REPOSITORY_ID,"GITHUB_SHA":config.workflow_commit,"GITHUB_EVENT_SCHEDULE":config.schedule_cron}
    if any(environment.get(k)!=v for k,v in expected.items()) or now.tzinfo is None:
        raise ValueError("one-shot run identity")
    scheduled=datetime.strptime(config.scheduled_utc,"%Y-%m-%dT%H:%M:00Z").replace(tzinfo=timezone.utc)
    if now.astimezone(timezone.utc).replace(second=0,microsecond=0)!=scheduled:
        raise ValueError("missed or delayed one-shot schedule")


class AdaptiveProductionAdapter:
    production=True
    def __init__(self, *, run: Mapping[str, object], ca_file: Path, timeout: int=30):
        if timeout!=30 or not ca_file.is_file() or ca_file.is_symlink() or sha(ca_file.read_bytes())!=run.get("ca_sha256"):
            raise ValueError("production CA/runtime closure")
        self.run_binding=sha(canonical(run)); self.ca_sha256=str(run["ca_sha256"]); self._ca=ca_file; self._timeout=timeout
    def __call__(self,purpose:str,method:str,url:str)->Capture:
        if any(k in os.environ for k in PROXY_KEYS) or not _allowed_request(purpose,method,url): raise ValueError("production request boundary")
        p=urlsplit(url); context=ssl.create_default_context(cafile=str(self._ca)); connection=http.client.HTTPSConnection(p.hostname,443,context=context,timeout=self._timeout)
        target=p.path or "/"; target+=("?"+p.query) if p.query else ""
        try:
            connection.request(method,target,headers={"Accept-Encoding":"identity","User-Agent":"Pastila-Capture/2.3.10"})
            response=connection.getresponse(); payload=response.read(MAX_RESPONSE_BYTES+1); sock=connection.sock
            peer=sock.getpeercert(binary_form=True) if sock else b""; tls=sock.version() if sock else ""
            headers=tuple((str(k).lower(),str(v)) for k,v in response.getheaders())
            if (response.status!=200 or response.getheader("location") is not None or len(payload)>MAX_RESPONSE_BYTES or not peer
                or tls not in {"TLSv1.2","TLSv1.3"} or not headers or len({k for k,_ in headers})!=len(headers)
                or any(k=="content-encoding" and v.lower()!="identity" for k,v in headers)):
                raise ValueError("publisher response closure")
            return Capture(purpose,url,payload,method,response.status,headers,sha(peer),tls)
        finally: connection.close()


def canonical_output(execution: CaptureExecution, run: Mapping[str, object], initiation:Mapping[str,object]) -> tuple[dict[str,bytes],dict[str,object]]:
    required={"initiation_subject_sha256","initiation_rekor_uuid","initiation_rekor_log_index","initiation_rekor_integrated_time","verified"}
    if set(initiation)!=required or initiation["verified"] is not True: raise ValueError("initiation receipt closure")
    files={f"captures/{i:06d}.bin":bytes(item.payload) for i,item in enumerate(execution.captures,1)}
    rows=[]
    for i,item in enumerate(execution.captures,1):
        path=f"captures/{i:06d}.bin"; payload=files[path]
        rows.append({"purpose":item.purpose,"method":item.method,"locator":item.locator,"status":item.status,
                     "headers":[list(x) for x in item.headers],"peer_certificate_sha256":item.peer_certificate_sha256,
                     "tls_version":item.tls_version,"path":path,"length":len(payload),"sha256":sha(payload)})
    manifest={"schema":"PASTILA_CAPTURE_SET_V2_3_10","run":dict(run),"captures":rows,"derivations":[list(x) for x in execution.derivations]}
    manifest["capture_set_identity"]=sha(canonical(manifest))
    predicate={"_type":"https://in-toto.io/Statement/v1","predicateType":"https://pastila.invalid/semantic-authority/final/v2.3.10","subject":[{"name":"capture-set.json","digest":{"sha256":sha(canonical(manifest))}}],"predicate":{"capture_set_identity":manifest["capture_set_identity"],"initiation":dict(initiation),"initiation_claim_sha256":sha(canonical({"domain":"PASTILA_CAPTURE_INITIATION_V2_3_9",**dict(run),"external_parameters":{}}))}}
    files["capture-set.json"]=canonical(manifest)+b"\n"; files["final-attestation-predicate.json"]=canonical(predicate)+b"\n"
    return files,predicate


def persist_once(files: Mapping[str,bytes], output: Path) -> None:
    if output.exists() or not files or len(files)>MAX_REQUESTS+2: raise ValueError("output must be absent")
    closed=[]
    for name,payload in files.items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts or any(part in {"", "."} for part in relative.parts) or not isinstance(payload,bytes):
            raise ValueError("output path")
        closed.append((relative,payload))
    temporary=Path(tempfile.mkdtemp(prefix=f".{output.name}-",dir=output.parent))
    try:
        for relative,payload in closed:
            path=temporary.joinpath(*relative.parts)
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(payload)
        os.replace(temporary,output)
    except BaseException:
        if temporary.exists(): shutil.rmtree(temporary)
        raise


def verify_installed_dependency(path:Path, expected_sha256:str)->None:
    if not path.is_file() or path.is_symlink() or path.resolve(strict=True)!=path.absolute() or sha(path.read_bytes())!=expected_sha256: raise ValueError("immutable dependency")


def install_dependency_once(payload:bytes, destination:Path, expected_sha256:str)->None:
    if destination.exists() or not payload or sha(payload)!=expected_sha256 or not destination.parent.is_dir():
        raise ValueError("dependency installation closure")
    temporary=destination.with_name(f".{destination.name}.partial")
    if temporary.exists(): raise ValueError("dependency partial exists")
    temporary.write_bytes(payload); os.chmod(temporary,0o555); os.replace(temporary,destination)
    verify_installed_dependency(destination,expected_sha256)


def run_once(*, config:FrozenRun, environment:Mapping[str,str], now:datetime, run:Mapping[str,object],
             bundle:bytes, bundle_path:Path, verifier:LinuxVerifier, ca_file:Path, output:Path)->dict[str,object]:
    one_shot_guard(config,environment,now)
    if (run.get("runtime_commit")!=RUNTIME_COMMIT or run.get("workflow_commit")!=config.workflow_commit
        or run.get("deployment_identity")!=config.deployment_identity or run.get("ca_sha256")!=config.ca_sha256):
        raise ValueError("deployment/run convergence")
    initiation=verify_linux_initiation(run=run,bundle=bundle,bundle_path=bundle_path,repository_slug=REPOSITORY_SLUG,runtime=verifier)
    adapter=AdaptiveProductionAdapter(run=run,ca_file=ca_file)
    execution=execute_capture(run=run,bundle=bundle,bundle_path=bundle_path,repository_slug=REPOSITORY_SLUG,verifier=verifier,capture_one=adapter)
    files,predicate=canonical_output(execution,run,initiation); persist_once(files,output)
    return predicate


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--qualification-check",action="store_true"); args=parser.parse_args(argv)
    if not args.qualification_check: raise SystemExit("deployment activation requires separately frozen schedule receipt and manifest")
    return 0


if __name__=="__main__": raise SystemExit(main())
