"""Source-blind deployment-path closure for semantic-authority capture V2.3.9."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urljoin, urlsplit

from .semantic_authority_capture_orchestrator_v2_3_7 import Capture, canonical
from .semantic_authority_cosign_v2_3_7 import decode_dsse_statement

RUNTIME_COMMIT = "8e6e533b4448ab56040fcc2aefc3de10921ab48e"
REPOSITORY_ID = "1355263083"
REPOSITORY_SLUG = "acidburn1danny/pastila-news-monitor"
COSIGN_SHA256 = "4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71"
TRUSTED_ROOT_SHA256 = "6494e21ea73fa7ee769f85f57d5a3e6a08725eae1e38c755fc3517c9e6bc0b66"
LINUX_LAUNCHER_SHA256 = "62f9af6b03354f8092be0e1780eecb4d18a0715b50123f438dc01f7ab53548fc"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UINT = re.compile(r"^[1-9][0-9]*$")
PROXY_KEYS = frozenset({"http_proxy", "https_proxy", "all_proxy", "no_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"})
SEEDS = (
    ("CROSSREF_RELEASE_INDEX", "GET", "https://www.crossref.org/categories/metadata-retrieval/"),
    ("CROSSREF_ARCHIVE_INDEX", "GET", "https://www.crossref.org/services/metadata-retrieval/public-data-file/"),
    ("OPENALEX_RELEASE_NOTES", "GET", "https://openalex.s3.amazonaws.com/RELEASE_NOTES.txt"),
    ("OPENALEX_MANIFEST_VERSION_INDEX", "GET", "https://openalex.s3.amazonaws.com/?prefix=data%2Fjsonl%2Fmanifest.json&versions="),
)
DISCOVERY_PURPOSES = frozenset({"CROSSREF_RELEASE_INDEX", "CROSSREF_RELEASE_RECORD", "CROSSREF_ARCHIVE_INDEX", "OPENALEX_RELEASE_NOTES", "OPENALEX_MANIFEST_VERSION_INDEX", "OPENALEX_MANIFEST"})
MAX_REQUESTS = 100_000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


DERIVATION_POLICY = {
    "schema": "SEMANTIC_AUTHORITY_ADAPTIVE_REQUEST_DERIVATION_V2_3_9",
    "seed_requests": [list(x) for x in SEEDS],
    "rules": [
        "CROSSREF_SAME_ORIGIN_RELEASE_AND_PAGINATION_LINKS_FROM_CAPTURED_HTML",
        "CROSSREF_PINNED_ARCHIVE_HOST_OBJECTS_FROM_CAPTURED_HTML",
        "OPENALEX_VERSION_IDS_FROM_CAPTURED_S3_XML",
        "OPENALEX_ARCHIVE_OBJECTS_FROM_CAPTURED_MANIFEST_JSON",
    ],
    "ordering": "UTF8_CANONICAL_ASCENDING_NO_REDRAW",
    "unknown_or_malformed": "FAIL_CLOSED",
}
DERIVATION_POLICY_IDENTITY = sha(canonical(DERIVATION_POLICY))
SEED_PLAN_IDENTITY = sha(canonical([list(x) for x in SEEDS]))


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True); self.values: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for key, value in attrs:
                if key.lower() == "href" and value is not None: self.values.append(value)


def _text(payload: bytes) -> str:
    if not payload or len(payload) > 64 * 1024 * 1024 or payload.startswith(b"\xef\xbb\xbf"):
        raise ValueError("discovery payload closure")
    try: return payload.decode("utf-8")
    except UnicodeDecodeError as exc: raise ValueError("discovery UTF-8") from exc


def _allowed_request(purpose: str, method: str, url: str) -> bool:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.port is not None or parsed.username is not None
        or parsed.password is not None or parsed.fragment or ".." in parsed.path or "%" in parsed.path):
        return False
    expected_host = {
        "CROSSREF_RELEASE_INDEX":"www.crossref.org", "CROSSREF_RELEASE_RECORD":"www.crossref.org",
        "CROSSREF_ARCHIVE_INDEX":"www.crossref.org", "CROSSREF_ARCHIVE_OBJECT_HEAD":"api-snapshots-reqpays-crossref.s3.amazonaws.com",
        "OPENALEX_RELEASE_NOTES":"openalex.s3.amazonaws.com", "OPENALEX_MANIFEST_VERSION_INDEX":"openalex.s3.amazonaws.com",
        "OPENALEX_MANIFEST":"openalex.s3.amazonaws.com", "OPENALEX_ARCHIVE_OBJECT_HEAD":"openalex.s3.amazonaws.com",
    }.get(purpose)
    if parsed.hostname != expected_host or method != ("HEAD" if purpose.endswith("OBJECT_HEAD") else "GET"):
        return False
    if purpose == "CROSSREF_RELEASE_INDEX":
        return not parsed.query and bool(re.fullmatch(r"/categories/metadata-retrieval/(?:page/[1-9][0-9]*/)?", parsed.path))
    if purpose == "CROSSREF_RELEASE_RECORD": return not parsed.query and bool(re.fullmatch(r"/blog/[a-z0-9][a-z0-9-]*/", parsed.path))
    if purpose == "CROSSREF_ARCHIVE_INDEX": return url == SEEDS[1][2]
    if purpose == "CROSSREF_ARCHIVE_OBJECT_HEAD": return not parsed.query and parsed.path not in {"", "/"}
    if purpose == "OPENALEX_RELEASE_NOTES": return url == SEEDS[2][2]
    if purpose == "OPENALEX_MANIFEST_VERSION_INDEX":
        return bool(re.fullmatch(r"prefix=data%2Fjsonl%2Fmanifest\.json&versions=(?:&key-marker=[A-Za-z0-9._~-]+&version-id-marker=[A-Za-z0-9._~-]+)?", parsed.query))
    if purpose == "OPENALEX_MANIFEST": return parsed.path == "/data/jsonl/manifest.json" and bool(re.fullmatch(r"versionId=[A-Za-z0-9._~-]+", parsed.query))
    return purpose == "OPENALEX_ARCHIVE_OBJECT_HEAD" and not parsed.query and parsed.path.startswith("/data/jsonl/") and len(parsed.path) > len("/data/jsonl/")


def derive_requests(captures: Mapping[str, tuple[Capture, ...]]) -> tuple[tuple[str, str, str, str], ...]:
    """Derive requests only from captured bytes; the fourth field binds the source bytes."""
    if not captures or not set(captures).issubset(DISCOVERY_PURPOSES):
        raise ValueError("derivation input purpose")
    out: set[tuple[str, str, str, str]] = set()
    for purpose, rows in captures.items():
        if not isinstance(rows, tuple) or not rows: raise ValueError("derivation group")
        for item in rows:
            if not isinstance(item, Capture) or item.purpose != purpose: raise ValueError("derivation capture")
            text = _text(item.payload); source = sha(item.payload)
            if purpose.startswith("CROSSREF_"):
                parser = _Links(); parser.feed(text)
                for raw in parser.values:
                    url = urljoin(item.locator, raw); parsed = urlsplit(url)
                    if parsed.scheme != "https" or parsed.query or parsed.fragment: continue
                    if parsed.hostname == "www.crossref.org" and re.fullmatch(r"/blog/[a-z0-9][a-z0-9-]*/", parsed.path):
                        out.add(("CROSSREF_RELEASE_RECORD", "GET", url, source))
                    elif parsed.hostname == "www.crossref.org" and re.fullmatch(r"/categories/metadata-retrieval/page/[1-9][0-9]*/", parsed.path):
                        out.add(("CROSSREF_RELEASE_INDEX", "GET", url, source))
                    elif parsed.hostname == "api-snapshots-reqpays-crossref.s3.amazonaws.com" and parsed.path not in {"", "/"}:
                        out.add(("CROSSREF_ARCHIVE_OBJECT_HEAD", "HEAD", url, source))
            elif purpose == "OPENALEX_MANIFEST_VERSION_INDEX":
                try: root = ET.fromstring(text)
                except ET.ParseError as exc: raise ValueError("OpenAlex version XML") from exc
                local = lambda node: node.tag.rsplit("}", 1)[-1]
                for node in root.iter():
                    version = (node.text or "").strip()
                    if local(node) == "VersionId" and re.fullmatch(r"[A-Za-z0-9._~-]+", version):
                        out.add(("OPENALEX_MANIFEST", "GET", f"https://openalex.s3.amazonaws.com/data/jsonl/manifest.json?versionId={version}", source))
                values = {local(node):(node.text or "").strip() for node in root.iter() if local(node) in {"IsTruncated","NextKeyMarker","NextVersionIdMarker"}}
                if values.get("IsTruncated") not in {"true", "false"}: raise ValueError("OpenAlex truncation closure")
                if values["IsTruncated"] == "true":
                    key, version = values.get("NextKeyMarker", ""), values.get("NextVersionIdMarker", "")
                    if not re.fullmatch(r"[A-Za-z0-9._~-]+", key) or not re.fullmatch(r"[A-Za-z0-9._~-]+", version): raise ValueError("OpenAlex continuation closure")
                    out.add(("OPENALEX_MANIFEST_VERSION_INDEX", "GET", f"{SEEDS[3][2]}&key-marker={key}&version-id-marker={version}", source))
            elif purpose == "OPENALEX_MANIFEST":
                try: value = json.loads(text)
                except json.JSONDecodeError as exc: raise ValueError("OpenAlex manifest JSON") from exc
                urls: list[str] = []
                def walk(node: object) -> None:
                    if isinstance(node, dict):
                        for key, child in node.items():
                            if key in {"url", "url_path", "path"} and isinstance(child, str): urls.append(child)
                            walk(child)
                    elif isinstance(node, list):
                        for child in node: walk(child)
                walk(value)
                for raw in urls:
                    url = urljoin("https://openalex.s3.amazonaws.com/data/jsonl/", raw)
                    parsed = urlsplit(url)
                    if parsed.scheme == "https" and parsed.hostname == "openalex.s3.amazonaws.com" and parsed.path.startswith("/data/jsonl/") and not parsed.query and not parsed.fragment:
                        out.add(("OPENALEX_ARCHIVE_OBJECT_HEAD", "HEAD", url, source))
    return tuple(sorted(out, key=lambda row: canonical(list(row))))


def initiation_claim(run: Mapping[str, object]) -> dict[str, object]:
    required = {"deployment_identity", "repository_id", "runtime_commit", "workflow_commit", "run_id", "run_attempt", "event_name", "derivation_policy_identity", "seed_plan_identity", "ca_sha256"}
    if (set(run) != required or run["runtime_commit"] != RUNTIME_COMMIT or not HEX40.fullmatch(str(run["workflow_commit"]))
        or run["workflow_commit"] == run["runtime_commit"] or run["repository_id"] != REPOSITORY_ID
        or not UINT.fullmatch(str(run["run_id"])) or run["run_attempt"] != 1 or run["event_name"] != "schedule"
        or run["derivation_policy_identity"] != DERIVATION_POLICY_IDENTITY or run["seed_plan_identity"] != SEED_PLAN_IDENTITY
        or not HEX64.fullmatch(str(run["deployment_identity"])) or not HEX64.fullmatch(str(run["ca_sha256"]))):
        raise ValueError("V2.3.9 run closure")
    return {"domain":"PASTILA_CAPTURE_INITIATION_V2_3_9", **dict(run), "external_parameters":{}}


def validate_final_attestation(summary: Mapping[str, object], run: Mapping[str, object]) -> None:
    claim = initiation_claim(run)
    required = {"initiation_claim", "initiation_subject_sha256", "initiation_rekor_uuid", "initiation_rekor_log_index", "final_rekor_log_index", "runtime_commit", "workflow_commit", "derivation_policy_identity", "seed_plan_identity"}
    if set(summary) != required or summary["initiation_claim"] != claim or summary["initiation_subject_sha256"] != sha(canonical(claim)):
        raise ValueError("initiation/final schema convergence")
    for field in ("initiation_rekor_uuid",):
        if not HEX64.fullmatch(str(summary[field])): raise ValueError("Rekor identity")
    for field in ("initiation_rekor_log_index", "final_rekor_log_index"):
        if not UINT.fullmatch(str(summary[field])): raise ValueError("Rekor index")
    if int(summary["final_rekor_log_index"]) <= int(summary["initiation_rekor_log_index"]): raise ValueError("Rekor ordering")
    for field in ("runtime_commit", "workflow_commit", "derivation_policy_identity", "seed_plan_identity"):
        if summary[field] != run[field]: raise ValueError("final run binding")


@dataclass(frozen=True)
class LinuxVerifier:
    cosign: Path; launcher: Path; trusted_root: Path
    cosign_sha256: str; launcher_sha256: str; trusted_root_sha256: str


def run_linux_verifier(runtime: LinuxVerifier, args: tuple[str, ...]) -> subprocess.CompletedProcess[bytes]:
    for path, expected in ((runtime.cosign, COSIGN_SHA256), (runtime.launcher, runtime.launcher_sha256), (runtime.trusted_root, TRUSTED_ROOT_SHA256)):
        if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path.absolute() or sha(path.read_bytes()) != expected:
            raise ValueError("Linux verifier file pin")
    if runtime.cosign_sha256 != COSIGN_SHA256 or runtime.trusted_root_sha256 != TRUSTED_ROOT_SHA256 or runtime.launcher_sha256 != LINUX_LAUNCHER_SHA256:
        raise ValueError("Linux verifier declared pin")
    if any(key in os.environ for key in PROXY_KEYS): raise ValueError("verifier proxy environment")
    command = ["/usr/bin/bash", str(runtime.launcher), "--launcher-sha256", runtime.launcher_sha256, "--expected-sha256", COSIGN_SHA256, str(runtime.cosign), *args]
    return subprocess.run(command, capture_output=True, timeout=90, check=False, env={"PATH":"/usr/bin:/bin", "HOME":"/nonexistent", "SSL_CERT_FILE":"/dev/null"})


def verify_linux_initiation(*, run: Mapping[str, object], bundle: bytes, bundle_path: Path, repository_slug: str, runtime: LinuxVerifier) -> Mapping[str, object]:
    claim=initiation_claim(run); digest=sha(canonical(claim))
    if (not bundle or not bundle_path.is_file() or bundle_path.is_symlink() or bundle_path.read_bytes()!=bundle
        or repository_slug != REPOSITORY_SLUG):
        raise ValueError("initiation bundle input")
    identity=f"https://github.com/{repository_slug}/.github/workflows/semantic-authority-metadata-capture-v2-3-9.yml@refs/heads/public/v2.3.7-capture"
    result=run_linux_verifier(runtime,("verify-blob-attestation","--offline","--bundle",str(bundle_path),"--trusted-root",str(runtime.trusted_root),"--certificate-identity",identity,"--certificate-oidc-issuer","https://token.actions.githubusercontent.com","--certificate-github-workflow-repository",repository_slug,"--certificate-github-workflow-sha",str(run["workflow_commit"]),"--certificate-github-workflow-trigger","schedule","--digest",digest,"--digestAlg","sha256"))
    if result.returncode or b"Verified OK" not in result.stdout+result.stderr: raise ValueError("Linux Cosign initiation verification")
    statement=decode_dsse_statement(bundle)
    if (set(statement)!={"_type","subject","predicateType","predicate"} or statement["predicateType"]!="https://pastila.invalid/semantic-authority/initiation/v2.3.9"
        or statement["predicate"]!=claim or statement["subject"]!=[{"name":"pastila-capture-initiation.json","digest":{"sha256":digest}}]):
        raise ValueError("V2.3.9 initiation DSSE closure")
    try:
        entries=json.loads(bundle)["verificationMaterial"]["tlogEntries"]
        if not isinstance(entries,list) or len(entries)!=1 or not UINT.fullmatch(str(entries[0]["logIndex"])) or not UINT.fullmatch(str(entries[0]["integratedTime"])): raise ValueError
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as exc: raise ValueError("single Rekor initiation entry") from exc
    return {"initiation_subject_sha256":digest,"initiation_rekor_uuid":sha(canonical(entries[0])),
            "initiation_rekor_log_index":str(entries[0]["logIndex"]),"initiation_rekor_integrated_time":str(entries[0]["integratedTime"]),"verified":True}


@dataclass(frozen=True)
class CaptureExecution:
    captures: tuple[Capture, ...]
    derivations: tuple[tuple[str, str, str, str], ...]


def execute_capture(*, run: Mapping[str, object], bundle: bytes, bundle_path: Path, repository_slug: str, verifier: LinuxVerifier, capture_one: Callable[[str,str,str], Capture]) -> CaptureExecution:
    """Executable adaptive entry: no transport occurs before initiation verification."""
    receipt = verify_linux_initiation(run=run,bundle=bundle,bundle_path=bundle_path,repository_slug=repository_slug,runtime=verifier)
    if receipt.get("verified") is not True or receipt.get("initiation_subject_sha256") != sha(canonical(initiation_claim(run))):
        raise ValueError("cryptographic initiation required")
    if (getattr(capture_one, "production", False) is not True
        or getattr(capture_one, "run_binding", None) != sha(canonical(run))
        or getattr(capture_one, "ca_sha256", None) != run["ca_sha256"]):
        raise ValueError("production capture binding")
    results: list[Capture] = []
    derivation_evidence: list[tuple[str,str,str,str]] = []
    requested: set[tuple[str, str, str]] = set()
    pending = list(SEEDS)
    observed_discovery: set[tuple[str,str,str]] = set()
    while pending:
        purpose, method, url = pending.pop(0)
        key = (purpose, method, url)
        if key in requested: continue
        if not _allowed_request(purpose, method, url): raise ValueError("derived request boundary")
        if len(requested) >= MAX_REQUESTS: raise ValueError("adaptive request bound")
        item = capture_one(purpose, method, url)
        if (not isinstance(item, Capture) or item.purpose != purpose or item.method != method or item.locator != url
            or item.status != 200 or (method == "GET" and not item.payload) or not item.headers
            or not HEX64.fullmatch(item.peer_certificate_sha256) or item.tls_version not in {"TLSv1.2", "TLSv1.3"}):
            raise ValueError("capture response/request binding")
        requested.add(key); results.append(item)
        if purpose in DISCOVERY_PURPOSES:
            observation = (purpose,item.locator,sha(item.payload))
            if observation in observed_discovery: continue
            observed_discovery.add(observation)
            for child_purpose, child_method, child_url, source in derive_requests({purpose:(item,)}):
                child = (child_purpose, child_method, child_url)
                if child not in requested and child not in pending:
                    pending.append(child);derivation_evidence.append((child_purpose,child_method,child_url,source))
    return CaptureExecution(tuple(results),tuple(derivation_evidence))


def main() -> int:
    raise SystemExit("V2.3.9 qualified but workflow deployment is not authorized")


if __name__ == "__main__": main()
