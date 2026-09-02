"""Production HTTPS capture and cryptographic initiation binding for V2.3.7."""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import re
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from . import semantic_authority_cosign_v2_3_7 as cosign
from .semantic_authority_capture_orchestrator_v2_3_7 import Capture, HOSTS, PURPOSES, canonical, sha256

DOMAIN = "PASTILA_CAPTURE_ADAPTER_V2_3_8"
INITIATION_PREDICATE = "https://pastila.invalid/semantic-authority/initiation/v2.3.7"
WORKFLOW_PATH = ".github/workflows/semantic-authority-metadata-capture-v2-3-6.yml"
PUBLIC_REF = "refs/heads/public/v2.3.7-capture"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UINT = re.compile(r"^[1-9][0-9]*$")
PROXY_KEYS = frozenset({"http_proxy","https_proxy","all_proxy","no_proxy","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY"})
MAX_RESPONSE_BYTES = 64 * 1024 * 1024


def request_plan_identity(requests: Mapping[str, tuple[tuple[str,str],...]]) -> str:
    return sha256(canonical([{"purpose":p,"requests":[{"method":m,"url":u} for m,u in rows]} for p,rows in requests.items()]))


@dataclass(frozen=True)
class CosignRuntime:
    wsl: Path
    distribution: str
    launcher_host: Path
    launcher_linux: str
    launcher_sha256: str
    cosign_linux: str
    bundle_host: Path
    bundle_linux: str
    trusted_root_host: Path
    trusted_root_linux: str


def _expected_wsl_path(path: Path) -> str:
    resolved=path.resolve(strict=True)
    drive=resolved.drive.rstrip(":").lower()
    if len(drive)!=1 or not drive.isalpha(): raise ValueError("non-drive host path")
    suffix=resolved.as_posix().split(":",1)[1]
    return f"/mnt/{drive}{suffix}"


def _initiation_claim(run: Mapping[str, object]) -> dict[str, object]:
    return {
        "domain": DOMAIN,
        "deployment_identity": run["deployment_identity"],
        "repository_id": run["repository_id"],
        "workflow_commit": run["workflow_commit"],
        "run_id": run["run_id"],
        "run_attempt": run["run_attempt"],
        "event_name": run["event_name"],
        "external_parameters": {},
    }


def verify_initiation_bundle(*, bundle: bytes, run: Mapping[str, object], repository_slug: str, runtime: CosignRuntime) -> dict[str, object]:
    """Run the pinned offline verifier, then bind its DSSE statement to this run."""
    required={"deployment_identity","repository_id","workflow_commit","run_id","run_attempt","event_name"}
    if (set(run)!=required or not bundle or not re.fullmatch(r"[a-z0-9_.-]+/[a-z0-9_.-]+", repository_slug)
        or not HEX64.fullmatch(str(run["deployment_identity"])) or not re.fullmatch(r"[0-9a-f]{40}",str(run["workflow_commit"]))
        or not UINT.fullmatch(str(run["repository_id"])) or not UINT.fullmatch(str(run["run_id"]))
        or run["run_attempt"]!=1 or run["event_name"]!="schedule"):
        raise ValueError("initiation input")
    if not runtime.bundle_host.is_file() or runtime.bundle_host.is_symlink() or runtime.bundle_host.read_bytes()!=bundle:
        raise ValueError("Cosign/decoder bundle byte split")
    if runtime.bundle_linux!=_expected_wsl_path(runtime.bundle_host):
        raise ValueError("bundle host/WSL path split")
    if (not runtime.trusted_root_host.is_file() or runtime.trusted_root_host.is_symlink()
        or sha256(runtime.trusted_root_host.read_bytes())!=cosign.TRUSTED_ROOT_SHA256
        or runtime.trusted_root_linux!=_expected_wsl_path(runtime.trusted_root_host)):
        raise ValueError("trusted-root host/WSL binding")
    claim = _initiation_claim(run)
    digest = sha256(canonical(claim))
    cosign.verify_blob_attestation(
        wsl=runtime.wsl, distribution=runtime.distribution, launcher_host=runtime.launcher_host,
        launcher_linux=runtime.launcher_linux, launcher_sha256=runtime.launcher_sha256,
        cosign_linux=runtime.cosign_linux, bundle_linux=runtime.bundle_linux,
        trusted_root_linux=runtime.trusted_root_linux, digest=digest,
        certificate_identity=f"https://github.com/{repository_slug}/{WORKFLOW_PATH}@{PUBLIC_REF}", oidc_issuer="https://token.actions.githubusercontent.com",
        github_repository=repository_slug, github_sha=str(run["workflow_commit"]), github_trigger="schedule",
    )
    statement = cosign.decode_dsse_statement(bundle)
    if set(statement) != {"_type","subject","predicateType","predicate"} or statement["predicateType"] != INITIATION_PREDICATE or statement["predicate"] != claim:
        raise ValueError("initiation statement closure")
    if statement["subject"] != [{"name":"pastila-capture-initiation.json","digest":{"sha256":digest}}]:
        raise ValueError("initiation subject closure")
    try:
        entry=json.loads(bundle)["verificationMaterial"]["tlogEntries"]
        if not isinstance(entry,list) or len(entry)!=1: raise ValueError
        entry=entry[0]
        log_index=str(entry["logIndex"]); integrated=str(entry["integratedTime"])
        if not UINT.fullmatch(log_index) or not UINT.fullmatch(integrated): raise ValueError
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
        raise ValueError("single transparency entry required") from exc
    return {
        "verified":True,"deployment_identity":run["deployment_identity"],"repository_id":run["repository_id"],
        "workflow_commit":run["workflow_commit"],"run_id":run["run_id"],"run_attempt":1,
        "rekor_uuid":sha256(canonical(entry)),"rekor_log_index":log_index,"bundle_sha256":sha256(bundle),
    }


def _allowed(purpose: str, method: str, url: str) -> bool:
    if purpose not in PURPOSES: return False
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!=HOSTS[purpose] or p.port is not None or p.username or p.password or p.fragment or ".." in p.path or "%" in p.path: return False
    expected="HEAD" if purpose.endswith("OBJECT_HEAD") else "GET"
    if method!=expected: return False
    exact={
        "CROSSREF_RELEASE_INDEX":"https://www.crossref.org/categories/metadata-retrieval/",
        "CROSSREF_ARCHIVE_INDEX":"https://www.crossref.org/services/metadata-retrieval/public-data-file/",
        "OPENALEX_RELEASE_NOTES":"https://openalex.s3.amazonaws.com/RELEASE_NOTES.txt",
        "OPENALEX_MANIFEST_VERSION_INDEX":"https://openalex.s3.amazonaws.com/?prefix=data%2Fjsonl%2Fmanifest.json&versions=",
    }
    if purpose in exact: return url==exact[purpose] or (purpose=="CROSSREF_RELEASE_INDEX" and bool(re.fullmatch(re.escape(exact[purpose])+r"page/[1-9][0-9]*/",url)))
    if purpose=="CROSSREF_RELEASE_RECORD": return bool(re.fullmatch(r"/blog/[a-z0-9][a-z0-9-]*/",p.path)) and not p.query
    if purpose=="OPENALEX_MANIFEST": return p.path=="/data/jsonl/manifest.json" and bool(re.fullmatch(r"versionId=[A-Za-z0-9._~-]+",p.query))
    if purpose=="OPENALEX_ARCHIVE_OBJECT_HEAD": return p.path.startswith("/data/jsonl/") and len(p.path)>len("/data/jsonl/") and not p.query
    if purpose=="CROSSREF_ARCHIVE_OBJECT_HEAD": return len(p.path)>1 and not p.query
    return False


class ProductionCaptureAdapter:
    """Direct-TLS adapter over a frozen, derivation-verified request plan."""
    def __init__(self, *, requests: Mapping[str, tuple[tuple[str,str],...]], expected_plan_identity: str, run_binding: str, ca_file: Path, ca_sha256: str, timeout: int=30):
        if tuple(requests)!=PURPOSES or request_plan_identity(requests)!=expected_plan_identity or not HEX64.fullmatch(run_binding) or not HEX64.fullmatch(ca_sha256) or timeout!=30:
            raise ValueError("capture plan closure")
        if not ca_file.is_file() or ca_file.is_symlink() or sha256(ca_file.read_bytes())!=ca_sha256:
            raise ValueError("CA bundle pin")
        closed={}
        all_urls=set()
        for purpose, rows in requests.items():
            if not isinstance(rows,tuple) or not rows: raise ValueError("empty request group")
            normalized=[]
            for row in rows:
                if not isinstance(row,tuple) or len(row)!=2 or not _allowed(purpose,row[0],row[1]) or row[1] in all_urls: raise ValueError("request plan authority")
                all_urls.add(row[1]); normalized.append(row)
            closed[purpose]=tuple(normalized)
        self._requests=closed; self.run_binding=run_binding; self.plan_identity=expected_plan_identity; self._ca_file=ca_file; self._timeout=timeout; self.production=True

    def __call__(self, purpose: str) -> tuple[Capture,...]:
        if purpose not in self._requests or any(key in os.environ for key in PROXY_KEYS): raise ValueError("capture environment/purpose")
        return tuple(self._fetch(purpose,method,url) for method,url in self._requests[purpose])

    def _fetch(self, purpose: str, method: str, url: str) -> Capture:
        p=urlsplit(url); context=ssl.create_default_context(cafile=str(self._ca_file))
        connection=http.client.HTTPSConnection(p.hostname,443,context=context,timeout=self._timeout)
        target=p.path or "/"; target += ("?"+p.query) if p.query else ""
        try:
            connection.request(method,target,headers={"Accept-Encoding":"identity","User-Agent":"Pastila-Capture/2.3.8"})
            response=connection.getresponse(); payload=response.read(MAX_RESPONSE_BYTES+1)
            sock=connection.sock; peer=sock.getpeercert(binary_form=True) if sock is not None else b""; tls=sock.version() if sock is not None else None
            if not peer or tls not in {"TLSv1.2","TLSv1.3"}: raise ValueError("authenticated TLS evidence")
            if response.status!=200 or len(payload)>MAX_RESPONSE_BYTES or response.getheader("location") is not None: raise ValueError("publisher response closure")
            pairs=tuple((str(k).lower(),str(v)) for k,v in response.getheaders()); names=[k for k,_ in pairs]
            if len(names)!=len(set(names)) or any(k=="content-encoding" and v.lower()!="identity" for k,v in pairs): raise ValueError("response header closure")
        finally:
            connection.close()
        return Capture(purpose,url,payload,method,response.status,pairs,sha256(peer),tls)
