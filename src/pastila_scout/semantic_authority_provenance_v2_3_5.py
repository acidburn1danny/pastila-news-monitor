"""Independent response provenance and registry association rules (V2.3.5)."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from . import semantic_authority_metadata_proof_v2_3_3 as proof

DOMAIN="PASTILA_SEMANTIC_AUTHORITY_PUBLISHER_RESPONSE_PROVENANCE_V2_3_5"
HEX64=re.compile(r"^[0-9a-f]{64}$")
OPENALEX_VERSION_INDEX="https://openalex.s3.amazonaws.com/?prefix=data%2Fjsonl%2Fmanifest.json&versions="
MIN_NOTARY_QUORUM=2
REAL_METADATA_ACQUISITION_READY=False
REMAINING_BLOCKERS=("INDEPENDENT_NOTARY_ENDPOINTS_KEYS_AND_APPOINTMENTS_NOT_YET_FROZEN",)


def canonical(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()


def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()


def response_claim(capture:proof.VerifiedCapture)->dict[str,Any]:
    return {"domain":DOMAIN,"v2_3_3_domain":proof.DOMAIN,"run_identity":capture.run_identity,
      "purpose":capture.purpose,"method":capture.method,"url":capture.url,"headers":dict(capture.headers),
      "payload_sha256":sha(capture.payload),"payload_length":len(capture.payload),"capture_identity":capture.identity}


def _verify_ed25519(message:bytes,signature:bytes,key_path,expected_key_sha256:str,openssl_path)->None:
    if sha(Path(key_path).read_bytes())!=expected_key_sha256 or sha(Path(openssl_path).read_bytes())!=proof.OPENSSL_SHA256:raise ValueError("notary verifier pin mismatch")
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);msg=root/"message";sig=root/"signature";msg.write_bytes(message);sig.write_bytes(signature)
        run=subprocess.run([str(openssl_path),"pkeyutl","-verify","-pubin","-inkey",str(key_path),"-rawin","-in",str(msg),"-sigfile",str(sig)],capture_output=True,timeout=30,check=False)
    if run.returncode:raise ValueError("notary signature invalid")


def verify_notary_quorum(capture:proof.VerifiedCapture, statements:Iterable[Mapping[str,Any]], *,
                          pinned_public_keys:Mapping[str,tuple[Any,str]], openssl_path, required:int=MIN_NOTARY_QUORUM)->dict[str,Any]:
    """Require independent signatures over the exact observed response claim."""
    if required<2 or len(pinned_public_keys)<required or not HEX64.fullmatch(capture.run_identity):raise ValueError("notary quorum policy")
    claim=response_claim(capture);claim_identity=sha(canonical(claim));accepted=[]
    seen=set()
    for raw in statements:
        item=dict(raw)
        if set(item)!={"schema","notary_id","claim_identity","observed_at_utc","signature"} or item["schema"]!="PUBLISHER_RESPONSE_NOTARY_ATTESTATION_V2_3_5":raise ValueError("notary statement schema")
        notary=item["notary_id"]
        if notary in seen or notary not in pinned_public_keys or item["claim_identity"]!=claim_identity:raise ValueError("notary identity or claim binding")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",str(item["observed_at_utc"])):raise ValueError("notary time")
        message=canonical({k:item[k] for k in ("schema","notary_id","claim_identity","observed_at_utc")})
        try:
            signature=base64.b64decode(item["signature"],validate=True);key_path,key_sha256=pinned_public_keys[notary]
            _verify_ed25519(message,signature,key_path,key_sha256,openssl_path)
        except Exception as exc:raise ValueError("notary signature invalid") from exc
        seen.add(notary);accepted.append(sha(message+signature))
    if len(accepted)<required:raise ValueError("independent notary quorum absent")
    return {"claim_identity":claim_identity,"quorum":len(accepted),"attestation_identities":sorted(accepted)}


def _version_url(key_marker:str|None=None,version_marker:str|None=None)->str:
    query=[("prefix","data/jsonl/manifest.json"),("versions","")]
    if key_marker is not None:query.extend((("key-marker",key_marker),("version-id-marker",version_marker or "")))
    return "https://openalex.s3.amazonaws.com/?"+urlencode(query)


def parse_openalex_manifest_version_history(pages:Iterable[proof.VerifiedCapture])->tuple[dict[str,Any],...]:
    """Parse a complete, marker-closed S3 ListObjectVersions history."""
    pages=tuple(pages)
    if not pages:raise ValueError("OpenAlex version history empty")
    run=pages[0].run_identity;expected=OPENALEX_VERSION_INDEX;versions=[];seen=set()
    ns="{http://s3.amazonaws.com/doc/2006-03-01/}"
    for index,page in enumerate(pages):
        if page.purpose!="OPENALEX_MANIFEST_VERSION_INDEX" or page.method!="GET" or page.run_identity!=run or page.url!=expected or not HEX64.fullmatch(page.identity):raise ValueError("OpenAlex version page chain")
        try:root=ET.fromstring(page.payload)
        except ET.ParseError as exc:raise ValueError("OpenAlex version XML") from exc
        if root.tag!=ns+"ListVersionsResult" or root.findtext(ns+"Name")!="openalex" or root.findtext(ns+"Prefix")!="data/jsonl/manifest.json":raise ValueError("OpenAlex version authority")
        for node in root.findall(ns+"Version"):
            key=node.findtext(ns+"Key");version=node.findtext(ns+"VersionId");modified=node.findtext(ns+"LastModified")
            if key!="data/jsonl/manifest.json" or not version or version in seen or not modified:raise ValueError("OpenAlex manifest version record")
            when=datetime.fromisoformat(modified.replace("Z","+00:00"))
            if when.tzinfo is None:raise ValueError("OpenAlex version time")
            seen.add(version);versions.append({"version_id":version,"last_modified_utc":when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"source_capture_identity":page.identity})
        truncated=root.findtext(ns+"IsTruncated")
        if truncated=="true":
            key_marker=root.findtext(ns+"NextKeyMarker");version_marker=root.findtext(ns+"NextVersionIdMarker")
            if not key_marker or not version_marker or index+1>=len(pages):raise ValueError("OpenAlex pagination marker closure")
            expected=_version_url(key_marker,version_marker)
        elif truncated=="false":
            if index!=len(pages)-1:raise ValueError("OpenAlex pages after terminal")
            expected=""
        else:raise ValueError("OpenAlex truncation state")
    if expected or not versions:raise ValueError("OpenAlex terminal/history closure")
    return tuple(sorted(versions,key=lambda x:(x["last_modified_utc"],x["version_id"])))


class _ArchiveLinks(HTMLParser):
    def __init__(self):super().__init__();self.current=None;self.text=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="a" and attrs.get("href"):self.current=attrs["href"];self.text=[]
    def handle_data(self,data):
        if self.current:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.current:self.links.append((" ".join("".join(self.text).split()),self.current));self.current=None


def bind_crossref_archive_associations(release_records:Iterable[Mapping[str,Any]], archive_index:proof.VerifiedCapture)->dict[str,dict[str,Any]]:
    """Associate each release to exactly one archive link visibly naming its year."""
    if archive_index.purpose!="CROSSREF_ARCHIVE_INDEX" or archive_index.method!="GET" or archive_index.url!=proof.CROSSREF_ARCHIVE or not HEX64.fullmatch(archive_index.identity):raise ValueError("Crossref archive authority")
    records=tuple(dict(x) for x in release_records);parser=_ArchiveLinks();parser.feed(archive_index.payload.decode("utf-8"));output={}
    for row in records:
        year=str(row.get("release_id"))
        matches=[url for text,url in parser.links if re.search(rf"(?<!\d){re.escape(year)}(?!\d)",text)]
        allowed=[url for url in matches if url.startswith("https://api-snapshots-reqpays-crossref.s3.amazonaws.com/") or url.startswith("https://academictorrents.com/details/")]
        if len(allowed)!=1:raise ValueError("Crossref release/archive association ambiguous or absent")
        output[year]={"release_id":year,"release_record_identity":row["source_capture_identity"],"archive_index_capture_identity":archive_index.identity,"archive_url":allowed[0]}
    if len(output)!=len(records):raise ValueError("Crossref association closure")
    return output


def qualification_identity(value:Mapping[str,Any])->str:
    body=dict(value);body.pop("qualification_identity",None);return sha(canonical(body))


def validate_qualification(value:Mapping[str,Any])->None:
    required={"schema","verdict","v2_3_1_governance","v2_3_3_implementation","v2_3_4_implementation","implementation_sha256","test_sha256","invariants","remaining_blockers","zero_activity","qualification_identity"}
    if set(value)!=required or value["schema"]!="SEMANTIC_AUTHORITY_PROVENANCE_V2_3_5_ZERO_METADATA_QUALIFICATION" or value["verdict"]!="PASS_INDEPENDENT_NOTARY_AND_REGISTRY_DERIVATION_DESIGN_ZERO_METADATA":raise ValueError("qualification schema")
    import pastila_scout.semantic_authority_acquisition_v2_3_4 as acquisition
    test_path=Path(__file__).resolve().parents[2]/"tests"/"test_semantic_authority_provenance_v2_3_5.py"
    expected={"implementation_sha256":sha(Path(__file__).read_bytes()),"test_sha256":sha(test_path.read_bytes()),"v2_3_3_implementation":sha(Path(proof.__file__).read_bytes()),"v2_3_4_implementation":sha(Path(acquisition.__file__).read_bytes())}
    if value["v2_3_1_governance"]!="41f202af7e835bfc9bbb048d803ee19e7861719ae4d45f0298035f586d640c52" or any(value[k]!=v for k,v in expected.items()):raise ValueError("qualification identity chain")
    invariants={"INDEPENDENT_NOTARY_QUORUM":"PASS","PINNED_OPENSSL_ED25519_VERIFICATION":"PASS","EXACT_RESPONSE_CLAIM_BINDING":"PASS","OPENALEX_S3_VERSION_PAGINATION_CLOSURE":"PASS","CROSSREF_ARCHIVE_RELEASE_ASSOCIATION":"PASS","REAL_ACQUISITION_GATE":"FAIL_CLOSED_PENDING_NOTARY_APPOINTMENTS"}
    zero={"registry_metadata":0,"snapshot_objects":0,"frame_execution":0,"source_selection":0,"authority_bases":0,"pilot15":0,"blind_access":0}
    if value["invariants"]!=invariants or value["remaining_blockers"]!=list(REMAINING_BLOCKERS) or value["zero_activity"]!=zero or value["qualification_identity"]!=qualification_identity(value):raise ValueError("qualification closure")
