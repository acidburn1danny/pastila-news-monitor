import json
from pathlib import Path

import pytest

from pastila_scout.production_core_checkpoint_resume_v6 import (
    CheckpointError, build_receipt, validate_chain, write_receipt,
)


def batches():
    return [
        {
            "materialization": "A" if n <= 6 else "B",
            "repetition": ((n - 1) % 6) // 2 + 1,
            "candidate_alias": "CANDIDATE-A" if n % 2 else "CANDIDATE-B",
            "batch_sha256": f"{n:064x}",
            "batch": [{"global_ordinal": (n - 1) * 200 + i} for i in range(1, 201)],
            "first_global_ordinal": (n - 1) * 200 + 1,
            "last_global_ordinal": n * 200,
        }
        for n in range(1, 13)
    ]


def checkpoint(root: Path, items, ordinal: int, previous):
    directory = root / f"batch-{ordinal:02d}"
    directory.mkdir()
    (directory / "synthetic-observation.json").write_text(json.dumps({"ordinal": ordinal}))
    receipt = build_receipt(
        attempt_identity="a" * 64,
        execution_authority_identity="b" * 64,
        generation_identity="c" * 64,
        checkpoint_ordinal=ordinal,
        previous_checkpoint_identity=previous,
        batch=items[ordinal - 1],
        directory=directory,
    )
    write_receipt(root / f"checkpoint-{ordinal:02d}.json", receipt)
    return receipt["checkpoint_identity"]


def test_smoke_save_restart_resume_all_twelve_without_qualification_rows(tmp_path):
    items = batches()
    previous = None
    for ordinal in range(1, 7):
        previous = checkpoint(tmp_path, items, ordinal, previous)
    assert validate_chain(tmp_path, attempt_identity="a" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items) == (6, previous)
    for ordinal in range(7, 13):
        previous = checkpoint(tmp_path, items, ordinal, previous)
    assert validate_chain(tmp_path, attempt_identity="a" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items) == (12, previous)


def test_resume_rejects_tampered_receipt(tmp_path):
    items = batches()
    checkpoint(tmp_path, items, 1, None)
    path = tmp_path / "checkpoint-01.json"
    value = json.loads(path.read_bytes())
    value["finalized_rows"] = 199
    path.write_text(json.dumps(value))
    with pytest.raises(CheckpointError):
        validate_chain(tmp_path, attempt_identity="a" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items)


def test_resume_rejects_gap_and_wrong_attempt(tmp_path):
    items = batches()
    previous = checkpoint(tmp_path, items, 1, None)
    checkpoint(tmp_path, items, 2, previous)
    (tmp_path / "checkpoint-01.json").unlink()
    with pytest.raises(CheckpointError):
        validate_chain(tmp_path, attempt_identity="a" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items)
    with pytest.raises(CheckpointError):
        validate_chain(tmp_path, attempt_identity="d" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items)


def test_resume_rejects_content_substitution(tmp_path):
    items = batches()
    checkpoint(tmp_path, items, 1, None)
    (tmp_path / "batch-01" / "synthetic-observation.json").write_text("substituted")
    with pytest.raises(CheckpointError):
        validate_chain(tmp_path, attempt_identity="a" * 64, execution_authority_identity="b" * 64, generation_identity="c" * 64, batches=items)


def test_executor_uses_atomic_staging_and_never_replays_accepted_checkpoint():
    source = (Path(__file__).resolve().parents[1] / "scripts/execute_production_core_candidate_qualification_v3.py").read_text("utf-8")
    assert "if checkpoint_ordinal <= accepted_checkpoints:" in source
    assert "os.replace(staging, directory)" in source
    assert "RECOVERED_CONSUMED_ATTEMPT_WITHOUT_TERMINAL_RECORD" not in source
    assert 'attempt.get("preflight") != pre' in source
    assert 'raise SystemExit("resume preflight substitution")' in source
    assert '"production-core-successor-comparative-qualification-generation-v5.json"' in source
    assert '"production-core-successor-candidate-object-manifest-v5.json"' in source
    assert 'globals()["PINNED_ROOTFS_SHA256"]' in source


def test_attempt_preflight_requires_exact_v6_source_closure():
    source = (Path(__file__).resolve().parents[1] / "src/pastila_scout/production_core_candidate_execution_authority_v3.py").read_text("utf-8")
    assert 'or set(sources) != {' in source
    assert '"src/pastila_scout/production_core_checkpoint_resume_v6.py"' in source
    assert '"scripts/launch_production_core_candidate_qualification_v4.py"' in source
    assert '"tests/test_production_core_checkpoint_resume_v6.py"' not in source


def test_authoritative_batch_ordinals_are_not_candidate_payload_fields():
    source = (Path(__file__).resolve().parents[1] / "src/pastila_scout/production_core_candidate_execution_authority_v3.py").read_text("utf-8")
    checkpoint = (Path(__file__).resolve().parents[1] / "src/pastila_scout/production_core_checkpoint_resume_v6.py").read_text("utf-8")
    assert '"first_global_ordinal": selected[0]["global_ordinal"]' in source
    assert '"last_global_ordinal": selected[-1]["global_ordinal"]' in source
    assert 'batch["first_global_ordinal"]' in checkpoint
    assert 'rows[0]["global_ordinal"]' not in checkpoint
