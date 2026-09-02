"""Fail-closed orchestration for the public V2.3.7 metadata capture run."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable, Mapping
from urllib.parse import urlsplit

SCHEMA = "SEMANTIC_AUTHORITY_CAPTURE_ORCHESTRATOR_V2_3_7"
PURPOSES = (
    "CROSSREF_RELEASE_INDEX",
    "CROSSREF_RELEASE_RECORD",
    "CROSSREF_ARCHIVE_INDEX",
    "CROSSREF_ARCHIVE_OBJECT_HEAD",
    "OPENALEX_RELEASE_NOTES",
    "OPENALEX_MANIFEST_VERSION_INDEX",
    "OPENALEX_MANIFEST",
    "OPENALEX_ARCHIVE_OBJECT_HEAD",
)
CHECKOUT_SHA = "d23441a48e516b6c34aea4fa41551a30e30af803"
ATTEST_SHA = "1e69f48acb82d1966a394da916b4c1698aa569d6"
CONTAINER = "python@sha256:edf6433343f65f94707985869aeaafe8beadaeaee11c4bc02068fca52dce28dd"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
UINT = re.compile(r"^[1-9][0-9]*$")
REPOSITORY_ID = "1355263083"
HOSTS = {
    "CROSSREF_RELEASE_INDEX": "www.crossref.org",
    "CROSSREF_RELEASE_RECORD": "www.crossref.org",
    "CROSSREF_ARCHIVE_INDEX": "www.crossref.org",
    "CROSSREF_ARCHIVE_OBJECT_HEAD": "api-snapshots-reqpays-crossref.s3.amazonaws.com",
    "OPENALEX_RELEASE_NOTES": "openalex.s3.amazonaws.com",
    "OPENALEX_MANIFEST_VERSION_INDEX": "openalex.s3.amazonaws.com",
    "OPENALEX_MANIFEST": "openalex.s3.amazonaws.com",
    "OPENALEX_ARCHIVE_OBJECT_HEAD": "openalex.s3.amazonaws.com",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Capture:
    purpose: str
    locator: str
    payload: bytes
    method: str = "GET"
    status: int = 200
    headers: tuple[tuple[str,str], ...] = ()
    peer_certificate_sha256: str = ""
    tls_version: str = ""


@dataclass(frozen=True)
class OrchestrationResult:
    manifest: Mapping[str, object]
    capture_files: Mapping[str, bytes]


def _validate_locator(item: Capture) -> None:
    parsed = urlsplit(item.locator)
    expected_method = "HEAD" if item.purpose.endswith("OBJECT_HEAD") else "GET"
    if (
        parsed.scheme != "https"
        or parsed.hostname != HOSTS[item.purpose]
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or item.method != expected_method
        or ".." in parsed.path
        or "%" in parsed.path
    ):
        raise ValueError("publisher locator/method outside frozen boundary")


def validate_pins(pins: Mapping[str, object]) -> None:
    required = {"schema", "actions", "container", "python", "runtime_dependencies", "pins_identity"}
    if set(pins) != required or pins["schema"] != "SEMANTIC_AUTHORITY_CAPTURE_DEPENDENCY_PINS_V2_3_7":
        raise ValueError("dependency pin schema")
    if pins["actions"] != {"actions/checkout": CHECKOUT_SHA, "actions/attest": ATTEST_SHA}:
        raise ValueError("action pins")
    if pins["container"] != CONTAINER or pins["python"] != "3.14.0" or pins["runtime_dependencies"] != []:
        raise ValueError("runtime pins")
    body = dict(pins); body.pop("pins_identity")
    if pins["pins_identity"] != sha256(canonical(body)):
        raise ValueError("pins identity")


def orchestrate(
    *,
    run: Mapping[str, object],
    pins: Mapping[str, object],
    verify_initiation: Callable[[Mapping[str, object]], Mapping[str, object]],
    capture: Callable[[str], tuple[Capture, ...]],
) -> OrchestrationResult:
    """Capture exactly once in frozen order after transparency initiation verifies.

    The callable boundary exists for qualification. Production supplies the
    publisher-origin-authenticated V2.3.x capture adapter; callers cannot add,
    remove, reorder, retry, or redraw requests.
    """
    validate_pins(pins)
    required = {"deployment_identity", "repository_id", "workflow_commit", "run_id", "run_attempt", "event_name"}
    if (
        set(run) != required
        or run["event_name"] != "schedule"
        or run["run_attempt"] != 1
        or run["repository_id"] != REPOSITORY_ID
        or not HEX64.fullmatch(str(run["deployment_identity"]))
        or not HEX40.fullmatch(str(run["workflow_commit"]))
        or not UINT.fullmatch(str(run["run_id"]))
    ):
        raise ValueError("run identity closure")
    initiation = verify_initiation(run)  # must complete before the first transport call
    expected_initiation = {
        "verified": True,
        "deployment_identity": run["deployment_identity"],
        "repository_id": run["repository_id"],
        "workflow_commit": run["workflow_commit"],
        "run_id": run["run_id"],
        "run_attempt": 1,
    }
    if not isinstance(initiation, Mapping) or any(initiation.get(k) != v for k, v in expected_initiation.items()):
        raise ValueError("transparency initiation receipt")
    if set(initiation) != {*expected_initiation, "rekor_uuid", "rekor_log_index", "bundle_sha256"}:
        raise ValueError("transparency initiation receipt schema")
    if not HEX64.fullmatch(str(initiation["rekor_uuid"])) or not HEX64.fullmatch(str(initiation["bundle_sha256"])) or not UINT.fullmatch(str(initiation["rekor_log_index"])):
        raise ValueError("transparency initiation proof identity")
    adapter_binding=getattr(capture,"run_binding",sha256(canonical(run)))
    if adapter_binding!=sha256(canonical(run)):
        raise ValueError("capture adapter/run binding")
    records: list[dict[str, object]] = []
    capture_files: dict[str, bytes] = {}
    seen: set[str] = set()
    for purpose in PURPOSES:
        items = capture(purpose)
        if not isinstance(items, tuple) or not items or purpose in seen:
            raise ValueError("capture group closure")
        group_locators: set[str] = set()
        for item in items:
            if (not isinstance(item, Capture) or item.purpose != purpose or item.status != 200 or not item.locator
                or (not item.payload and item.method!="HEAD") or item.locator in group_locators):
                raise ValueError("capture closure")
            _validate_locator(item)
            if getattr(capture,"production",False):
                if not item.headers or not HEX64.fullmatch(item.peer_certificate_sha256) or item.tls_version not in {"TLSv1.2","TLSv1.3"}:
                    raise ValueError("production TLS evidence closure")
            group_locators.add(item.locator)
            path=f"captures/{len(records)+1:05d}-{purpose.lower()}.bin"
            capture_files[path]=bytes(item.payload)
            records.append({"purpose": purpose, "method": item.method, "locator": item.locator, "path": path, "length": len(item.payload), "sha256": sha256(item.payload),"headers":[list(x) for x in item.headers],"peer_certificate_sha256":item.peer_certificate_sha256,"tls_version":item.tls_version})
        seen.add(purpose)
    if tuple(dict.fromkeys(x["purpose"] for x in records)) != PURPOSES:
        raise ValueError("capture order")
    manifest = {"schema": SCHEMA, "run": dict(run), "initiation": dict(initiation), "pins_identity": pins["pins_identity"], "captures": records}
    manifest["capture_set_identity"] = sha256(canonical(manifest))
    return OrchestrationResult(manifest, capture_files)


def main() -> int:
    # Activation is deliberately impossible until a separately frozen deployment
    # manifest and production adapter are installed.
    raise SystemExit("capture orchestration frozen but deployment not activated")


if __name__ == "__main__":
    main()
