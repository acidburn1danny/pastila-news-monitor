"""Actual-byte-derived, source-blind registry metadata proofs (V2.3.3)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import base64
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlsplit, urlunsplit, urlencode

from .semantic_authority_adapters_v2_2 import verify_rfc3161

PREDECESSOR_GOVERNANCE = "41f202af7e835bfc9bbb048d803ee19e7861719ae4d45f0298035f586d640c52"
DOMAIN = "PASTILA_SEMANTIC_AUTHORITY_METADATA_PROOF_V2_3_3"
CUTOFF_DATE = date(2026, 9, 2)
EARLIEST_CAPTURE = datetime(2026, 9, 2, 17, 31, 2, tzinfo=timezone.utc)
CROSSREF_INDEX = "https://www.crossref.org/categories/metadata-retrieval/"
CROSSREF_ARCHIVE = "https://www.crossref.org/services/metadata-retrieval/public-data-file/"
OPENALEX_NOTES = "https://openalex.s3.amazonaws.com/RELEASE_NOTES.txt"
OPENALEX_MANIFEST = "https://openalex.s3.amazonaws.com/data/jsonl/manifest.json"
OPENSSL_SHA256 = "132616b352a13168391ddbcc2eab22ce52df256b3d4cd2c2c6fc245d22bab62c"
CA_BUNDLE_SHA256 = "9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f"
ADAPTER_IMPLEMENTATION_SHA256 = "cfe13c66dcc22930cd7020e9675a4caa4db24252f229e7fb7c512bd2bdd460df"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REAL_METADATA_ACQUISITION_READY = False
ACQUISITION_BLOCKERS = (
    "RFC3161_PROVES_EXISTENCE_TIME_NOT_PUBLISHER_ORIGIN",
    "CROSSREF_ARCHIVE_LISTING_NOT_INTEGRATED_WITH_RELEASE_HISTORY",
    "OPENALEX_HISTORICAL_MANIFEST_AUTHORITY_NOT_ESTABLISHED",
    "V2_3_3_PROJECTIONS_NOT_ASSEMBLED_INTO_V2_3_1_HISTORY_SCHEMA",
)
QUALIFICATION_REPAIRS = (
    "UNATTESTED_PROJECTED_CROSSREF_RECORD_ACCEPTANCE", "CROSSREF_PAGINATION_AND_TERMINAL_NEGATIVE_SPACE_UNBOUND",
    "CROSSREF_PUBLICATION_TIME_NOT_DERIVED_FROM_CAPTURE_BYTES", "UNATTESTED_OPENALEX_RELEASE_AND_MANIFEST_DATE_ACCEPTANCE",
    "OPENALEX_RELEASE_NOTES_MANIFEST_CROSS_RUN_REPLAY", "ARBITRARY_S3_BUCKET_ACCEPTANCE",
    "NONCANONICAL_S3_TO_HTTPS_LOCATOR_MAPPING", "MANIFEST_OBJECT_CHECKSUM_VERSION_LENGTH_NOT_ATTESTED",
    "CAPTURE_REPLAY_DOMAIN_AND_GOVERNANCE_TIME_UNBOUND", "QUALIFICATION_IDENTITY_CHAIN_REWRITE_ACCEPTANCE",
    "AMBIGUOUS_CASE_FOLDED_OR_INJECTED_CAPTURE_HEADERS", "NONCANONICAL_CAPTURE_AND_PUBLICATION_TIMESTAMPS",
    "UNVERIFIED_DERIVED_CAPTURE_IDENTITIES", "OPENALEX_MANIFEST_SCHEMA_AND_NUMERIC_TYPE_CONFUSION",
    "EMPTY_OR_DUPLICATE_HEAD_OBJECT_SET_ACCEPTANCE", "UNSAFE_S3_VERSION_IDENTIFIER_ACCEPTANCE",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Capture:
    purpose: str; run_identity: str; method: str; url: str; status: int
    headers: Mapping[str, str]; payload: bytes; receipt: bytes; timestamp_utc: str


@dataclass(frozen=True)
class VerifiedCapture:
    purpose: str; run_identity: str; method: str; url: str
    headers: Mapping[str, str]; payload: bytes; identity: str


def _envelope(c: Capture) -> dict[str, Any]:
    normalized = [(str(k).lower(), str(v)) for k, v in c.headers.items()]
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("ambiguous case-folded header")
    if any(not key or "\r" in value or "\n" in value for key, value in normalized):
        raise ValueError("capture header invalid")
    headers = dict(normalized)
    return {"domain": DOMAIN, "governance_identity": PREDECESSOR_GOVERNANCE,
            "purpose": c.purpose, "run_identity": c.run_identity, "method": c.method,
            "url": c.url, "status": c.status, "headers": headers,
            "payload_sha256": sha(c.payload), "payload_length": len(c.payload)}


def verify_capture(c: Capture, *, expected_purpose: str, expected_url: str,
                   run_identity: str, openssl: Path, ca_file: Path) -> VerifiedCapture:
    """Authenticate URL, headers and payload together; reject cross-run replay."""
    if c.purpose != expected_purpose or c.run_identity != run_identity or c.url != expected_url:
        raise ValueError("capture purpose, URL, or replay domain mismatch")
    if not HEX64.fullmatch(run_identity) or c.method not in {"GET", "HEAD"} or c.status != 200:
        raise ValueError("capture execution metadata invalid")
    if c.method == "GET" and not c.payload:
        raise ValueError("GET capture payload missing")
    if c.method == "HEAD" and c.payload:
        raise ValueError("HEAD capture unexpectedly has body")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", c.timestamp_utc):
        raise ValueError("capture timestamp not canonical UTC")
    try:
        timestamp = datetime.fromisoformat(c.timestamp_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("capture timestamp invalid") from exc
    if timestamp.tzinfo is None or timestamp.astimezone(timezone.utc) < EARLIEST_CAPTURE:
        raise ValueError("capture predates frozen governance")
    envelope = _envelope(c)
    verify_rfc3161(payload=canonical(envelope), receipt=c.receipt, openssl=openssl,
                   ca_file=ca_file, expected_executable_sha256=OPENSSL_SHA256,
                   expected_ca_sha256=CA_BUNDLE_SHA256,
                   expected_timestamp_utc=c.timestamp_utc)
    capture_identity = sha(canonical({**envelope, "receipt_sha256": sha(c.receipt), "timestamp_utc": c.timestamp_utc}))
    return VerifiedCapture(c.purpose, c.run_identity, c.method, c.url,
                           envelope["headers"], c.payload, capture_identity)


class _CrossrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.in_heading=False; self.link=None; self.text=[]; self.next_url=None
        self.in_article=False; self.article_date=None
        self.records=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs); classes=set(attrs.get("class","").split())
        if tag == "article": self.in_article=True; self.article_date=None
        if tag == "time" and self.in_article and attrs.get("datetime"): self.article_date=attrs["datetime"]
        if tag in {"h2","h3"}: self.in_heading=True; self.link=None; self.text=[]
        if tag=="a" and self.in_heading and attrs.get("href"): self.link=attrs["href"]
        if tag=="a" and "next" in classes and attrs.get("href"): self.next_url=attrs["href"]
    def handle_data(self,data):
        if self.in_heading:self.text.append(data)
    def handle_endtag(self,tag):
        if tag in {"h2","h3"} and self.in_heading:
            title=" ".join("".join(self.text).split())
            match=re.fullmatch(r"(20\d{2}) public data file now available",title,re.I)
            if match and self.link:
                if not self.in_article or not self.article_date: raise ValueError("Crossref publication time missing")
                self.records.append((match.group(1),self.link,self.article_date))
            self.in_heading=False
        if tag == "article": self.in_article=False; self.article_date=None


def parse_crossref_history(pages: Iterable[VerifiedCapture]) -> tuple[dict[str, Any], ...]:
    """Derive records and pagination only from verified publisher HTML bytes."""
    pages=tuple(pages)
    if not pages: raise ValueError("Crossref history empty")
    records=[]; seen=set(); run_identity=pages[0].run_identity
    for index,page in enumerate(pages,1):
        expected=CROSSREF_INDEX if index==1 else f"{CROSSREF_INDEX}page/{index}/"
        if page.purpose!="CROSSREF_RELEASE_INDEX" or page.method!="GET" or page.url!=expected or page.run_identity != run_identity or not HEX64.fullmatch(page.identity):
            raise ValueError("Crossref verified page sequence mismatch")
        parser=_CrossrefParser(); parser.feed(page.payload.decode("utf-8"))
        expected_next=None if index==len(pages) else f"{CROSSREF_INDEX}page/{index+1}/"
        if parser.next_url!=expected_next: raise ValueError("Crossref pagination/terminal closure failure")
        for year,url,published in parser.records:
            if url in seen or not url.startswith("https://www.crossref.org/blog/"):
                raise ValueError("Crossref release alias or authority mismatch")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", published): raise ValueError("Crossref publication time not canonical UTC")
            published_at=datetime.fromisoformat(published.replace("Z", "+00:00"))
            if str(published_at.year) != year: raise ValueError("Crossref publication time invalid")
            seen.add(url); records.append({"release_id":year,"publication_date":published_at.date().isoformat(),"official_url":url,"source_capture_identity":page.identity})
    if not records or len({r["release_id"] for r in records})!=len(records):
        raise ValueError("Crossref release identity ambiguity")
    return tuple(sorted(records,key=lambda r:r["release_id"]))


def parse_openalex_history(notes: VerifiedCapture, manifest: VerifiedCapture) -> dict[str, Any]:
    """Derive release and manifest dates from their independently verified bytes."""
    if (notes.purpose,notes.method,notes.url)!=("OPENALEX_RELEASE_NOTES","GET",OPENALEX_NOTES): raise ValueError("OpenAlex notes capture mismatch")
    manifest_parts=urlsplit(manifest.url)
    if (manifest.purpose,manifest.method,manifest_parts.scheme,manifest_parts.netloc,manifest_parts.path)!=("OPENALEX_MANIFEST","GET","https","openalex.s3.amazonaws.com","/data/jsonl/manifest.json") or not re.fullmatch(r"versionId=[A-Za-z0-9._~-]+",manifest_parts.query): raise ValueError("OpenAlex versioned manifest capture mismatch")
    if notes.run_identity != manifest.run_identity or not all(HEX64.fullmatch(x.identity) for x in (notes,manifest)): raise ValueError("OpenAlex cross-run replay or identity")
    dates=re.findall(r"(?m)^RELEASE (\d{4}-\d{2}-\d{2})\s*$",notes.payload.decode("utf-8"))
    if not dates or len(dates)!=len(set(dates)): raise ValueError("OpenAlex release history missing or duplicate")
    release_dates=[date.fromisoformat(x) for x in dates]
    if release_dates!=sorted(release_dates,reverse=True): raise ValueError("OpenAlex release history order invalid")
    before=[x for x in release_dates if x<CUTOFF_DATE]
    if not before: raise ValueError("OpenAlex predecessor absent")
    chosen=max(before); value=json.loads(manifest.payload)
    if not isinstance(value,dict) or set(value)!={"date","entities"} or not isinstance(value["entities"],list): raise ValueError("OpenAlex manifest schema mismatch")
    manifest_date=date.fromisoformat(value["date"])
    if manifest_date not in {chosen,chosen+timedelta(days=1)}:
        raise ValueError("OpenAlex release/manifest reconciliation failure")
    if any(not isinstance(entity,dict) or set(entity)!={"entity_type","files"} or not isinstance(entity["files"],list) for entity in value["entities"]): raise ValueError("OpenAlex entity schema mismatch")
    files=[item for entity in value["entities"] for item in entity["files"]]
    if any(not isinstance(item,dict) or set(item)!={"url","meta"} or not isinstance(item["meta"],dict) or set(item["meta"])!={"content_length"} or isinstance(item["meta"]["content_length"],bool) or not isinstance(item["meta"]["content_length"],int) or item["meta"]["content_length"]<=0 for item in files): raise ValueError("OpenAlex file schema mismatch")
    locators=[item.get("url") for item in files]
    if not files or len(locators)!=len(set(locators)) or any(not isinstance(x,str) or not x.startswith("s3://openalex/data/jsonl/") for x in locators):
        raise ValueError("OpenAlex manifest object closure failure")
    return {"release_date":chosen.isoformat(),"manifest_date":manifest_date.isoformat(),
            "release_history":tuple(x.isoformat() for x in release_dates),
            "manifest_capture_identity":manifest.identity,"notes_capture_identity":notes.identity,
            "objects":tuple(sorted(({"locator":item["url"],"byte_length":item["meta"]["content_length"]} for item in files),key=lambda x:x["locator"].encode()))}


def bind_attested_checksums(manifest_objects: Iterable[Mapping[str, Any]], heads: Iterable[VerifiedCapture], *, registry: str, run_identity: str) -> dict[str, Any]:
    """Bind every manifest object to an attested HEAD checksum and S3 version."""
    manifest=tuple(dict(x) for x in manifest_objects); heads=tuple(heads)
    if registry not in {"CROSSREF","OPENALEX"}: raise ValueError("registry")
    prefix="s3://openalex/data/jsonl/" if registry=="OPENALEX" else "s3://api-snapshots-reqpays-crossref/"
    expected={x.get("locator"):x for x in manifest}
    if not manifest or len(expected)!=len(manifest) or any(set(x)!={"locator","byte_length"} or not isinstance(x["locator"],str) or not x["locator"].startswith(prefix) or isinstance(x["byte_length"],bool) or not isinstance(x["byte_length"],int) or x["byte_length"]<=0 for x in manifest): raise ValueError("manifest locator set invalid")
    if not HEX64.fullmatch(run_identity): raise ValueError("replay domain invalid")
    observed={h.url:h for h in heads}
    if len(observed)!=len(heads): raise ValueError("duplicate HEAD capture")
    https_expected={
        "https://" + urlsplit(k).netloc + ".s3.amazonaws.com" + urlsplit(k).path: v
        for k,v in expected.items()
    }
    if set(observed)!=set(https_expected): raise ValueError("HEAD/manifest object-set closure failure")
    leaves=[]
    for url,spec in sorted(https_expected.items(),key=lambda pair:pair[0].encode()):
        h=observed[url]
        if h.purpose!=f"{registry}_ARCHIVE_OBJECT_HEAD" or h.method!="HEAD" or h.run_identity != run_identity: raise ValueError("checksum capture purpose/replay mismatch")
        version=h.headers.get("x-amz-version-id"); checksum=h.headers.get("x-amz-checksum-sha256"); length=h.headers.get("content-length")
        try: decoded=base64.b64decode(checksum,validate=True).hex(); parsed_length=int(length)
        except (TypeError,ValueError): raise ValueError("attested checksum metadata invalid")
        if not isinstance(version,str) or not re.fullmatch(r"[A-Za-z0-9._~-]+",version) or len(decoded)!=64 or parsed_length!=spec["byte_length"] or not HEX64.fullmatch(h.identity): raise ValueError("attested checksum/version/length/identity mismatch")
        source=urlsplit(spec["locator"]); locator=urlunsplit((source.scheme,source.netloc,source.path,urlencode({"versionId":version}),""))
        leaf={"VERSIONED_IMMUTABLE_LOCATOR":locator,"BYTE_LENGTH":parsed_length,"SHA256":decoded,"HEAD_CAPTURE_IDENTITY":h.identity};leaves.append(leaf)
    nodes=[hashlib.sha256(b"\0"+canonical(x)).digest() for x in leaves]
    while len(nodes)>1:nodes=[hashlib.sha256(b"\1"+nodes[i]+(nodes[i+1] if i+1<len(nodes) else nodes[i])).digest() for i in range(0,len(nodes),2)]
    return {"object_count":len(leaves),"total_bytes":sum(x["BYTE_LENGTH"] for x in leaves),"merkle_root":nodes[0].hex(),"leaves":leaves}


def qualification_identity(value: Mapping[str,Any]) -> str:
    body=dict(value);body.pop("qualification_identity",None);return sha(canonical(body))


def validate_qualification(value: Mapping[str,Any]) -> None:
    required={"schema","verdict","predecessor_governance","implementation_sha256","test_sha256","dependencies","proofs","blockers_repaired","remaining_blockers","real_metadata_acquired","snapshot_content_acquired","frame_executed","source_selected","authority_basis_created","pilot15_prepared","blind_access","qualification_identity"}
    if set(value)!=required or value["schema"]!="SEMANTIC_AUTHORITY_METADATA_PROOF_V2_3_3_QUALIFICATION" or value["verdict"]!="PASS_ACTUAL_BYTE_DERIVED_METADATA_PROOF_INTEGRATION_ZERO_REAL_ACQUISITION":raise ValueError("qualification schema/verdict")
    test_path = Path(__file__).resolve().parents[2] / "tests" / "test_semantic_authority_metadata_proof_v2_3_3.py"
    actual_identities = {"implementation_sha256": sha(Path(__file__).read_bytes()), "test_sha256": sha(test_path.read_bytes())}
    if value["predecessor_governance"]!=PREDECESSOR_GOVERNANCE or any(value.get(k) != digest for k,digest in actual_identities.items()):raise ValueError("identity chain")
    dependencies={"adapter_implementation_sha256":ADAPTER_IMPLEMENTATION_SHA256,"openssl_executable_sha256":OPENSSL_SHA256,"ca_bundle_sha256":CA_BUNDLE_SHA256}
    if value["dependencies"] != dependencies: raise ValueError("dependency identity chain")
    expected={"RFC3161_CANONICAL_ENVELOPE":"PASS","CROSSREF_ACTUAL_HTML_AND_PAGINATION":"PASS","OPENALEX_ACTUAL_NOTES_AND_MANIFEST":"PASS","MANIFEST_TO_ATTESTED_HEAD_CLOSURE":"PASS","REGISTRY_LOCATOR_ALLOWLIST":"PASS","REPLAY_DOMAIN":"PASS"}
    if value["proofs"]!=expected:raise ValueError("proof closure")
    if value["blockers_repaired"] != list(QUALIFICATION_REPAIRS) or value["remaining_blockers"] != list(ACQUISITION_BLOCKERS): raise ValueError("audit finding closure")
    for key in ("real_metadata_acquired","snapshot_content_acquired","frame_executed","source_selected","authority_basis_created","pilot15_prepared","blind_access"):
        if value[key] not in (0,False):raise ValueError(key)
    if value["qualification_identity"]!=qualification_identity(value):raise ValueError("qualification identity")
