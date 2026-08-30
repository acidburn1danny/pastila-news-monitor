"""Independent zero-ingestion verification for Development Pilot 01."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "owner-source-v1.txt"
DECLARATION = ROOT / "owner-declaration-v1.json"
PRE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-preingestion-v1.json"
PACKET = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot01-signing-packet-v1.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: object) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    source = SOURCE.read_bytes()
    declaration_bytes = DECLARATION.read_bytes()
    require(hashlib.sha256(source).hexdigest() == "84261f1a6b97f951f70a1b86d42114da9703996607d43d2fc3779bffd7a97cb2", "source hash")
    require(hashlib.sha256(declaration_bytes).hexdigest() == "26712ba98a4022dc72d1a41b6c178665fbd7cb27aeb76da1aa08ff02b960aa81", "declaration hash")
    require(not source.startswith(b"\xef\xbb\xbf") and b"\r" not in source and source.endswith(b"\n") and not source.endswith(b"\n\n"), "source format")
    text = source.decode("utf-8")
    declaration = json.loads(declaration_bytes)
    require(declaration["contributor"]["legal_identity"] == "urn:pastila:party:pastila-acida-owner-v1", "public legal identity")
    require(declaration["contributor"]["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    pre, packet = json.loads(PRE.read_text(encoding="utf-8")), json.loads(PACKET.read_text(encoding="utf-8"))
    pre_core = dict(pre); actual_pre = pre_core.pop("preingestion_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_PREINGESTION_V1", pre_core) == actual_pre, "preingestion seal")
    require(packet["packet_identity"] == seal("B2_DEVELOPMENT_PILOT01_SIGNING_PACKET_V1", packet["packet_core"]), "packet seal")
    require(packet["packet_core"]["preingestion_identity"] == actual_pre, "packet preingestion binding")
    require(pre["partition"] == "DEVELOPMENT" and pre["factual_authority_envelope"]["creative_premise_family_id"] == "UNASSIGNED", "partition/creative premise")
    require(pre["ingested"] is False and pre["archive_write"] is False and packet["source_ingested"] is False and packet["archive_written"] is False, "zero ingestion")
    require(packet["ledger_events_appended"] == 0 and all(x["signature_status"] == "AWAITING_OWNER_CONTROLLED_SIGNATURE" for x in packet["signature_requests"]), "zero signing/ledger append")
    for proposition in pre["factual_authority_envelope"]["propositions"]:
        for name in ("subject", "predicate", "object"):
            span = proposition[name]
            cs, ce = span["character_coordinates"]
            bs, be = span["utf8_byte_coordinates"]
            chars = text[cs:ce].encode("utf-8")
            require(chars == source[bs:be], f"coordinate disagreement {proposition['proposition_id']} {name}")
            require(hashlib.sha256(chars).hexdigest() == span["sha256"], f"span hash {proposition['proposition_id']} {name}")
    requests = packet["signature_requests"]
    require(len(requests) == 8, "signature count")
    require(len({x["challenge"]["nonce"] for x in requests}) == 8, "nonce uniqueness")
    require(len({(x["operation_ordinal"], x["role"]) for x in requests}) == 8, "request uniqueness")
    for item in requests:
        challenge = item["challenge"]
        core = dict(challenge); identity = core.pop("challenge_identity")
        require(seal("B2_PILOT01_SIGNING_CHALLENGE_V1", core) == identity, "challenge seal")
        require(challenge["packet_identity"] == packet["packet_identity"] and challenge["preingestion_identity"] == actual_pre, "challenge binding")
        require(challenge["grants_operational_content_access"] is False, "hidden authority")
    forbidden = ["immutable_ingestion", "archive_write", "content_access", "construction", "generation", "model_exposure", "training", "runtime_integration", "production_routing"]
    require(all(pre["authority_matrix"][x] is False for x in forbidden), "authority matrix")
    require(source not in PRE.read_bytes() and source not in PACKET.read_bytes(), "source leaked into artifacts")
    print(json.dumps({"verdict": "PASS_PREINGESTION_READY_FOR_CUSTODIAL_SIGNATURES", "preingestion_identity": actual_pre,
                      "packet_identity": packet["packet_identity"], "propositions": len(pre["factual_authority_envelope"]["propositions"]),
                      "signature_requests": len(requests), "ingestion": False, "archive_write": False}, sort_keys=True))


if __name__ == "__main__":
    main()
