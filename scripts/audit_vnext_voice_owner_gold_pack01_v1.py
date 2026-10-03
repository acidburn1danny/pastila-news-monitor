from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def verify(path: Path, field: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    claimed = value.pop(field)
    assert hashlib.sha256(canon(value)).hexdigest() == claimed
    value[field] = claimed
    return value


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(repo: Path) -> None:
    art = repo / "docs/artifacts"
    dataset = verify(art / "vnext-voice-owner-gold-pack01-v1-dataset-successor.json", "dataset_successor_identity")
    backlog = verify(art / "vnext-voice-owner-gold-pack01-v1-backlog-delta.json", "backlog_delta_identity")
    audit = verify(art / "vnext-voice-owner-gold-pack01-v1-audit.json", "audit_identity")
    admitted = rows(art / "vnext-voice-owner-gold-pack01-v1-admission.jsonl")
    train = rows(art / "vnext-voice-owner-gold-pack01-v1-train-successor.jsonl")
    validation = rows(art / "vnext-voice-owner-gold-pack01-v1-validation-successor.jsonl")

    assert dataset["predecessor_identity"] == "cbc0001c54bad87f17d082e6a4ce09fceee0c23deaaa650129e2c003847cc935"
    assert dataset["admission_backlog_predecessor_identity"] == "2af65f4653a62bbd55e1b0747cab3d99dcf0de324c2e04ef070db12978f8eacb"
    assert backlog["dataset_successor_identity"] == dataset["dataset_successor_identity"]
    assert audit["dataset_successor_identity"] == dataset["dataset_successor_identity"]
    assert audit["backlog_delta_identity"] == backlog["backlog_delta_identity"]
    assert len(admitted) == 10 and len(train) == 25 and len(validation) == 12
    assert len({r["record_identity"] for r in admitted}) == 10
    assert len({r["gold_commentary"]["sha256"] for r in admitted}) == 10
    assert all(r["gold_commentary"]["rewritten"] is False for r in admitted)
    assert all(r["gold_commentary"]["normalized"] is False for r in admitted)
    assert all(r["training_eligible"] is True for r in admitted)
    assert all(r["factual_commentary_taxonomy"]["unsupported_fact_admitted"] is False for r in admitted)
    assert all(r["target_policy"]["protected_target_is_satire_target"] is False for r in admitted)
    train_families = {r["family_identity"] for r in train}
    validation_families = {r["family_identity"] for r in validation}
    assert train_families.isdisjoint(validation_families)
    assert dataset["partition"]["holdout_exposure"] == 0
    assert dataset["partition"]["qwen3_bakeoff_exposure"] == 0
    assert dataset["training_performed"] is False
    assert dataset["active_product_modified"] is False
    assert dataset["canonical_rollback_modified"] is False
    assert dataset["voice_state"] == "DISABLED_UNTIL_PROMOTION"
    assert audit["status"] == "PASS_0_INTEGRITY_BLOCKERS"
    print(json.dumps({
        "status": "PASS",
        "dataset_successor_identity": dataset["dataset_successor_identity"],
        "backlog_delta_identity": backlog["backlog_delta_identity"],
        "audit_identity": audit["audit_identity"],
        "admitted": len(admitted),
        "train": len(train),
        "validation": len(validation),
    }, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
