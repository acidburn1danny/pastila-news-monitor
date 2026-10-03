from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canon(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: dict, field: str) -> str:
    payload = dict(value)
    actual = payload.pop(field)
    assert hashlib.sha256(canon(payload)).hexdigest() == actual
    return actual


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(repo: Path) -> None:
    artifacts = repo / "docs/artifacts"
    dataset = json.loads((artifacts / "vnext-voice-owner-gold-pack02-v1-dataset-successor.json").read_text(encoding="utf-8"))
    backlog = json.loads((artifacts / "vnext-voice-owner-gold-pack02-v1-backlog.json").read_text(encoding="utf-8"))
    audit = json.loads((artifacts / "vnext-voice-owner-gold-pack02-v1-audit.json").read_text(encoding="utf-8"))
    dataset_id = identity(dataset, "dataset_successor_identity")
    backlog_id = identity(backlog, "backlog_identity")
    audit_id = identity(audit, "audit_identity")
    assert dataset_id == audit["dataset_successor_identity"] == backlog["dataset_successor_identity"]
    assert backlog_id == audit["backlog_identity"]
    assert dataset["predecessor_identity"] == "33ecca512d39dff8d8c4edbdc1b36c2bbe7c09df3369f4972fd4a0615217f76e"
    assert dataset["source_pack"]["sha256"] == "07e9667d269c0bf32c881238fcc2802bbcf1978d465ee673b34c245a9a5d4996"
    admission = rows(repo / dataset["files"]["admission"]["path"])
    admitted = rows(repo / dataset["files"]["admitted_records"]["path"])
    train = rows(repo / dataset["files"]["train"]["path"])
    validation = rows(repo / dataset["files"]["validation"]["path"])
    assert len(admission) == 11 and len(admitted) == 8 and len(train) == 33 and len(validation) == 12
    assert [r["pack_record"] for r in admitted] == [1, 2, 3, 4, 5, 7, 10, 11]
    assert [r["pack_record"] for r in admission if r["admission"] == "REJECTED_FAIL_CLOSED"] == [6, 8, 9]
    assert all(not r["factual_commentary_taxonomy"]["unsupported_fact_admitted"] for r in admitted)
    r11 = next(r for r in admitted if r["pack_record"] == 11)
    assert not r11["factual_commentary_taxonomy"]["shared_participants_coordination_or_causation_inferred"]
    assert dataset["partition"]["holdout_exposure"] == dataset["partition"]["qwen3_bakeoff_exposure"] == 0
    assert len({r["family_identity"] for r in train} & {r["family_identity"] for r in validation}) == 0
    assert len({r["gold_commentary"]["sha256"] for r in train + validation}) == len(train) + len(validation)
    assert dataset["factual_safety"]["unsupported_fact_records"] == 0
    assert dataset["second_experiment_readiness"]["threshold_status"] == "FAIL_CLOSED_NOT_READY"
    assert dataset["second_experiment_readiness"]["pack3_required_before_freeze"]
    assert not dataset["training_performed"] and not dataset["weights_modified"] and not dataset["holdout_accessed"]
    assert not dataset["active_product_modified"] and not dataset["canonical_rollback_modified"]
    assert dataset["voice_state"] == "DISABLED_UNTIL_PROMOTION"
    assert backlog["minimum_pack3"]["train_positive_records"] == 3
    assert backlog["minimum_pack3"]["validation_positive_records"] == 1
    assert backlog["minimum_pack3"]["factual_restraint_independent_records"] == 1
    assert audit["status"] == "PASS_0_INTEGRITY_BLOCKERS" and audit["legacy_dependency_count"] == 0
    print(json.dumps({"status": "PASS", "dataset_successor_identity": dataset_id, "backlog_identity": backlog_id, "audit_identity": audit_id, "records": {"admitted": 8, "rejected": 3}, "holdout_exposure": 0}, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
