"""Publisher-authenticated acquisition and V2.3.1 history assembly (V2.3.4)."""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlsplit

from . import semantic_authority_governance_v2_3_1 as governance
from . import semantic_authority_metadata_proof_v2_3_3 as proof

DOMAIN = "PASTILA_SEMANTIC_AUTHORITY_ACQUISITION_V2_3_4"
ALLOWED_HOSTS = frozenset({"www.crossref.org", "openalex.s3.amazonaws.com", "api-snapshots-reqpays-crossref.s3.amazonaws.com"})
ALLOWED_PURPOSES = frozenset({
    "CROSSREF_RELEASE_INDEX", "CROSSREF_RELEASE_RECORD", "CROSSREF_ARCHIVE_INDEX", "CROSSREF_ARCHIVE_OBJECT_HEAD",
    "OPENALEX_RELEASE_NOTES", "OPENALEX_MANIFEST_VERSION_INDEX", "OPENALEX_MANIFEST",
    "OPENALEX_ARCHIVE_OBJECT_HEAD",
})
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REAL_METADATA_ACQUISITION_READY = False
REMAINING_BLOCKERS = (
    "RFC3161_ATTESTS_CALLER_SUPPLIED_ENVELOPE_BUT_NOT_RESPONSE_ORIGIN_NONREPUDIATION",
    "OPENALEX_VERSION_HISTORY_TO_MANIFEST_VERSION_DERIVATION_NOT_IMPLEMENTED",
    "CROSSREF_ARCHIVE_INDEX_TO_RELEASE_ASSOCIATION_NOT_IMPLEMENTED",
)


def _purpose_url_method_allowed(purpose: str, url: str, method: str) -> bool:
    parts=urlsplit(url)
    if parts.port is not None or "%" in parts.path or ".." in parts.path or "//" in parts.path: return False
    exact={"OPENALEX_RELEASE_NOTES":proof.OPENALEX_NOTES,"CROSSREF_ARCHIVE_INDEX":proof.CROSSREF_ARCHIVE}
    if purpose in exact: return method=="GET" and url==exact[purpose]
    if purpose=="CROSSREF_RELEASE_INDEX": return method=="GET" and bool(re.fullmatch(re.escape(proof.CROSSREF_INDEX)+r"(?:page/[1-9]\d*/)?",url))
    if purpose=="CROSSREF_RELEASE_RECORD": return method=="GET" and parts.hostname=="www.crossref.org" and bool(re.fullmatch(r"/blog/[a-z0-9][a-z0-9-]*/",parts.path)) and not parts.query
    if purpose=="OPENALEX_MANIFEST_VERSION_INDEX": return method=="GET" and url=="https://openalex.s3.amazonaws.com/?prefix=data%2Fjsonl%2Fmanifest.json&versions="
    if purpose=="OPENALEX_MANIFEST": return method=="GET" and parts.hostname=="openalex.s3.amazonaws.com" and parts.path=="/data/jsonl/manifest.json" and bool(re.fullmatch(r"versionId=[A-Za-z0-9._~-]+",parts.query))
    if purpose=="OPENALEX_ARCHIVE_OBJECT_HEAD": return method=="HEAD" and parts.hostname=="openalex.s3.amazonaws.com" and parts.path.startswith("/data/jsonl/") and not parts.query
    if purpose=="CROSSREF_ARCHIVE_OBJECT_HEAD": return method=="HEAD" and parts.hostname=="api-snapshots-reqpays-crossref.s3.amazonaws.com" and parts.path.startswith("/") and not parts.query
    return False


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _validate_archive(commitment: Mapping[str,Any], captures_by_identity: Mapping[str,proof.VerifiedCapture], registry: str) -> None:
    if set(commitment)!={"object_count","total_bytes","merkle_root","leaves"} or not isinstance(commitment["leaves"],list) or not commitment["leaves"]: raise ValueError("archive commitment schema")
    leaves=commitment["leaves"]
    if commitment["object_count"]!=len(leaves) or isinstance(commitment["total_bytes"],bool) or commitment["total_bytes"]!=sum(x.get("BYTE_LENGTH",0) for x in leaves): raise ValueError("archive count/length closure")
    expected_purpose="CROSSREF_ARCHIVE_OBJECT_HEAD" if registry.startswith("CROSSREF_") else "OPENALEX_ARCHIVE_OBJECT_HEAD"
    seen=set();nodes=[]
    for leaf in leaves:
        if set(leaf)!={"VERSIONED_IMMUTABLE_LOCATOR","BYTE_LENGTH","SHA256","HEAD_CAPTURE_IDENTITY"} or leaf["VERSIONED_IMMUTABLE_LOCATOR"] in seen or not HEX64.fullmatch(str(leaf["SHA256"])) or isinstance(leaf["BYTE_LENGTH"],bool) or not isinstance(leaf["BYTE_LENGTH"],int) or leaf["BYTE_LENGTH"]<=0: raise ValueError("archive leaf schema")
        head=captures_by_identity.get(leaf["HEAD_CAPTURE_IDENTITY"])
        if head is None or head.purpose!=expected_purpose or head.method!="HEAD": raise ValueError("archive HEAD provenance closure")
        seen.add(leaf["VERSIONED_IMMUTABLE_LOCATOR"]);nodes.append(hashlib.sha256(b"\0"+proof.canonical(leaf)).digest())
    while len(nodes)>1: nodes=[hashlib.sha256(b"\1"+nodes[i]+(nodes[i+1] if i+1<len(nodes) else nodes[i])).digest() for i in range(0,len(nodes),2)]
    if commitment["merkle_root"]!=nodes[0].hex(): raise ValueError("archive Merkle closure")


def acquire_attested_capture(
    *, url: str, purpose: str, run_identity: str, method: str, ca_file: Path,
    openssl: Path, timestamp: Callable[[bytes], tuple[bytes, str]], timeout: int = 30,
) -> proof.VerifiedCapture:
    """Fetch directly over authenticated TLS, then timestamp the exact capture envelope."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS or parts.username or parts.password or parts.fragment:
        raise ValueError("publisher endpoint outside frozen allowlist")
    if purpose not in ALLOWED_PURPOSES or not _purpose_url_method_allowed(purpose,url,method) or not HEX64.fullmatch(run_identity):
        raise ValueError("capture authority invalid")
    if _sha(ca_file.read_bytes()) != proof.CA_BUNDLE_SHA256:
        raise ValueError("CA bundle identity mismatch")
    context = ssl.create_default_context(cafile=str(ca_file))
    connection = http.client.HTTPSConnection(parts.hostname, parts.port or 443, context=context, timeout=timeout)
    target = parts.path or "/"
    if parts.query: target += "?" + parts.query
    try:
        connection.request(method, target, headers={"Accept-Encoding": "identity", "User-Agent": "Pastila-V2.3.4/1"})
        response = connection.getresponse()
        sock = connection.sock
        if sock is None: raise ValueError("authenticated TLS socket unavailable")
        peer = sock.getpeercert(binary_form=True)
        tls_version = sock.version()
        payload = response.read()
        header_pairs=[(str(k).lower(),str(v)) for k,v in response.getheaders()]
        if len({k for k,_ in header_pairs}) != len(header_pairs): raise ValueError("duplicate response header")
        headers = dict(header_pairs)
    finally:
        connection.close()
    if not peer or tls_version not in {"TLSv1.2", "TLSv1.3"}: raise ValueError("publisher TLS authentication unavailable")
    headers["x-pastila-peer-certificate-sha256"] = _sha(peer)
    headers["x-pastila-tls-version"] = tls_version
    unsigned = proof.Capture(purpose, run_identity, method, url, response.status, headers, payload, b"", "")
    receipt, timestamp_utc = timestamp(proof.canonical(proof._envelope(unsigned)))
    capture = proof.Capture(purpose, run_identity, method, url, response.status, headers, payload, receipt, timestamp_utc)
    return proof.verify_capture(capture, expected_purpose=purpose, expected_url=url, run_identity=run_identity, openssl=openssl, ca_file=ca_file)


def bind_crossref_release_records(parsed: Iterable[Mapping[str,Any]], captures: Iterable[proof.VerifiedCapture]) -> tuple[dict[str,Any],...]:
    """Replace category-page provenance with exact authenticated release-record provenance."""
    rows=tuple(dict(x) for x in parsed); records=tuple(captures)
    by_url={x.url:x for x in records}
    if len(by_url)!=len(records) or set(by_url)!={x.get("official_url") for x in rows}: raise ValueError("Crossref release-record closure")
    output=[]
    for row in rows:
        capture=by_url[row["official_url"]]
        if capture.purpose!="CROSSREF_RELEASE_RECORD" or capture.method!="GET" or not HEX64.fullmatch(capture.identity): raise ValueError("Crossref release-record authority")
        output.append({**row,"source_capture_identity":capture.identity})
    return tuple(output)


def assemble_release_history(
    *, registry: str, parsed_releases: Iterable[Mapping[str, Any]],
    commitments: Mapping[str, Mapping[str, Any]], run_identity: str,
    captures: Iterable[proof.VerifiedCapture], history_receipt: bytes, history_timestamp_utc: str,
    openssl: Path, ca_file: Path,
) -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    """Create exactly the release/history schemas consumed by frozen V2.3.1."""
    if registry not in governance.REGISTRIES or not HEX64.fullmatch(run_identity): raise ValueError("history replay domain")
    releases = tuple(dict(row) for row in parsed_releases)
    captures=tuple(captures); ids=tuple(item.identity for item in captures)
    if not ids or len(ids) != len(set(ids)) or not all(HEX64.fullmatch(x) for x in ids): raise ValueError("capture identity closure")
    captures_by_identity={item.identity:item for item in captures}
    purpose_prefix="CROSSREF_" if registry.startswith("CROSSREF_") else "OPENALEX_"
    if any(item.run_identity != run_identity or not item.purpose.startswith(purpose_prefix) for item in captures): raise ValueError("cross-run or cross-registry capture")
    required_purposes = ({"CROSSREF_RELEASE_INDEX", "CROSSREF_ARCHIVE_INDEX"} if purpose_prefix == "CROSSREF_"
                         else {"OPENALEX_RELEASE_NOTES", "OPENALEX_MANIFEST"})
    if not required_purposes.issubset({item.purpose for item in captures}): raise ValueError("registry evidence classes incomplete")
    expected_ids = {str(row.get("release_id")) for row in releases}
    if set(commitments) != expected_ids: raise ValueError("release/commitment closure")
    rows=[]
    for row in releases:
        if set(row) != {"release_id", "publication_date", "official_url", "source_capture_identity"} or row["source_capture_identity"] not in ids: raise ValueError("parsed release schema or capture closure")
        source_capture=captures_by_identity[row["source_capture_identity"]]
        expected_source="CROSSREF_RELEASE_RECORD" if purpose_prefix=="CROSSREF_" else "OPENALEX_RELEASE_NOTES"
        if source_capture.purpose!=expected_source or source_capture.url!=row["official_url"]: raise ValueError("release-record provenance closure")
        rid=str(row["release_id"]); binding=dict(commitments[rid])
        expected_manifest="CROSSREF_ARCHIVE_INDEX" if purpose_prefix=="CROSSREF_" else "OPENALEX_MANIFEST"
        if set(binding)!={"registry","release_id","release_record_identity","manifest_capture_identity","archive"} or binding["registry"]!=registry or binding["release_id"]!=rid or binding["release_record_identity"]!=row["source_capture_identity"] or binding["manifest_capture_identity"] not in ids or captures_by_identity[binding["manifest_capture_identity"]].purpose!=expected_manifest: raise ValueError("registry manifest binding")
        commitment=dict(binding["archive"])
        _validate_archive(commitment,captures_by_identity,registry)
        archive_identity=_sha(_canonical(binding)); locator_identity=_sha(_canonical([x["VERSIONED_IMMUTABLE_LOCATOR"] for x in commitment["leaves"]]))
        rows.append({"registry":registry,"release_id":rid,"publication_date":row["publication_date"],
          "official_release_record_identity":row["source_capture_identity"],
          "completeness_evidence_identity":_sha(_canonical({"run_identity":run_identity,"captures":sorted(ids),"release_id":rid})),
          "archive_commitment_identity":archive_identity,"immutable_locator_set_identity":locator_identity,"archive_available":True})
    rows=tuple(sorted(rows,key=governance.canonical))
    capture_root=_sha(_canonical(sorted(ids)))
    evidence={"schema":governance.HISTORY_SCHEMA,"governance_identity":governance.GOVERNANCE_IDENTITY,
      "registry":registry,"cutoff_utc":governance.CUTOFF_UTC,"cutoff_date_exclusive":governance.CUTOFF_DATE_EXCLUSIVE.isoformat(),
      "coverage_claim":governance.COVERAGE,"authority_sources":["PUBLISHER_RELEASE_INDEX","PUBLISHER_ARCHIVE_LISTING"],
      "release_count":len(rows),"release_set_sha256":governance.release_set_sha256(rows),"capture_identity":capture_root,
      "verifier_identity":_sha(Path(openssl).read_bytes())}
    attested_payload=dict(evidence)
    evidence["attestation_identity"]=_sha(history_receipt)
    proof.verify_rfc3161(payload=governance.canonical(attested_payload),receipt=history_receipt,openssl=openssl,ca_file=ca_file,
      expected_executable_sha256=proof.OPENSSL_SHA256,expected_ca_sha256=proof.CA_BUNDLE_SHA256,expected_timestamp_utc=history_timestamp_utc)
    evidence["history_timestamp_utc"]=history_timestamp_utc
    return rows,evidence


def select_assembled_predecessor(*, rows: Iterable[Mapping[str, Any]], evidence: Mapping[str, Any],
                                  history_receipt: bytes, registry: str, openssl: Path, ca_file: Path) -> Mapping[str, Any]:
    """Closed runtime entry point: callers cannot replace external verification with `True`."""
    receipt_identity=_sha(history_receipt)
    def verify(payload: bytes, identity: str, verifier_identity: str) -> bool:
        if identity != receipt_identity or verifier_identity != _sha(openssl.read_bytes()): return False
        try:
            proof.verify_rfc3161(payload=payload,receipt=history_receipt,openssl=openssl,ca_file=ca_file,
              expected_executable_sha256=proof.OPENSSL_SHA256,expected_ca_sha256=proof.CA_BUNDLE_SHA256,
              expected_timestamp_utc=evidence["history_timestamp_utc"])
        except (KeyError,ValueError): return False
        return True
    governed=dict(evidence); timestamp=governed.pop("history_timestamp_utc",None)
    if not isinstance(timestamp,str): raise ValueError("history timestamp missing")
    return governance.select_verified_predecessor_release(rows,registry=registry,history_evidence=governed,
      verifier_identity=_sha(openssl.read_bytes()),verify_external_attestation=verify)


def qualification_identity(value: Mapping[str,Any]) -> str:
    body=dict(value);body.pop("qualification_identity",None);return _sha(_canonical(body))


def validate_qualification(value: Mapping[str,Any]) -> None:
    required={"schema","verdict","v2_3_1_governance","v2_3_3_implementation","implementation_sha256","test_sha256","invariants","zero_activity","remaining_blockers","qualification_identity"}
    if set(value)!=required or value["schema"]!="SEMANTIC_AUTHORITY_ACQUISITION_V2_3_4_ZERO_METADATA_QUALIFICATION" or value["verdict"]!="PASS_PUBLISHER_TLS_RFC3161_AND_EXACT_V2_3_1_ASSEMBLY_ZERO_METADATA": raise ValueError("qualification schema")
    test_path=Path(__file__).resolve().parents[2]/"tests"/"test_semantic_authority_acquisition_v2_3_4.py"
    expected={"implementation_sha256":_sha(Path(__file__).read_bytes()),"test_sha256":_sha(test_path.read_bytes())}
    if any(value[k]!=v for k,v in expected.items()) or value["v2_3_1_governance"]!=governance.GOVERNANCE_IDENTITY or value["v2_3_3_implementation"]!=_sha(Path(proof.__file__).read_bytes()): raise ValueError("qualification identity chain")
    invariants={"DIRECT_CA_VALIDATED_TLS_NO_PROXY":"PASS","PURPOSE_SPECIFIC_ENDPOINT_AND_METHOD_ALLOWLIST":"PASS","RFC3161_BINDS_EXACT_CAPTURE_ENVELOPE":"PASS","RUN_AND_REGISTRY_REPLAY_DOMAINS":"PASS","CROSSREF_RELEASE_RECORD_CAPTURE_CLOSURE":"PASS","RELEASE_MANIFEST_COMMITMENT_CLOSURE":"PASS","EXACT_V2_3_1_SCHEMA_ASSEMBLY":"PASS","CLOSED_ATTESTATION_VERIFIER_ENTRYPOINT":"PASS"}
    if value["invariants"]!=invariants or value["remaining_blockers"]!=list(REMAINING_BLOCKERS): raise ValueError("qualification invariant closure")
    expected_zero={"registry_metadata":0,"snapshot_content":0,"frame_execution":0,"source_selection":0,"authority_bases":0,"pilot15":0,"blind_access":0}
    if value["zero_activity"]!=expected_zero or value["qualification_identity"]!=qualification_identity(value): raise ValueError("qualification closure")
