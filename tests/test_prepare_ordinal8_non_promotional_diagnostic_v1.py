import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parents[1]
    / "scripts/prepare_ordinal8_non_promotional_diagnostic_v1.py"
)
SPEC = importlib.util.spec_from_file_location("diagnostic_prep", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def packet(case_id: str, coordinate: str) -> bytes:
    core = {
        "schema": "pastila-production-core-blind-adjudication-packet",
        "schema_version": 1,
        "qualification_generation_sha256": module.GENERATION,
        "corpus_sha256": module.CORPUS,
        "case": {
            "case_id": case_id,
            "request_identity": "sha256:" + module.digest(case_id.encode()),
        },
        "candidate_alias": "CANDIDATE-A",
        "candidate_output_sha256": module.digest(case_id.encode()),
        "candidate_output_validation": {
            "status": "PASS",
            "failure_code": None,
            "failure_detail": None,
        },
        "execution_receipt_identity": module.digest(coordinate.encode()),
        "rubric_sha256": module.RUBRIC,
        "adjudicator_registry_identity": module.SOURCE_PACKET_REGISTRY,
    }
    return module.canonical(
        {**core, "packet_identity": module.digest(module.canonical(core))}
    )


def make_runtime(root: Path) -> Path:
    for folder, _, _ in module.ROLES.values():
        for materialization in ("materialization-A", "materialization-B"):
            for repetition in ("repetition-1", "repetition-2", "repetition-3"):
                for case_id in module.CASES:
                    relative = Path(materialization, repetition, "CANDIDATE-A")
                    target = root / folder / relative / f"{case_id}.blind.json"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(
                        packet(case_id, f"{case_id}:{materialization}:{repetition}")
                    )
    return root


def test_manifest_is_content_addressed_non_promotional_and_non_compensating(tmp_path):
    runtime = make_runtime(tmp_path / "runtime")
    rows = module.collect(runtime / "adjudicator-a-v8")
    value = module.manifest("ADJUDICATOR_A", *module.ROLES["ADJUDICATOR_A"][1:], rows)
    identity = value.pop("package_identity")
    assert identity == module.digest(module.canonical(value))
    assert value["purpose"] == "NON_PROMOTIONAL_DIAGNOSTIC"
    assert (
        value["source_packet_adjudicator_registry_identity"]
        == module.SOURCE_PACKET_REGISTRY
    )
    assert (
        value["diagnostic_adjudicator_registry_identity"] == module.DIAGNOSTIC_REGISTRY
    )
    assert value["packet_count"] == 12
    assert [family["repetition_count"] for family in value["families"]] == [6, 6]
    assert value["constraints"] == {
        "hard_gate_result_unchanged": True,
        "hard_gate_compensation_permitted": False,
        "candidate_qualification_effect": False,
        "candidate_promotion_effect": False,
        "retry_or_redraw_permitted": False,
        "new_run_authorized": False,
        "structurally_invalid_outputs_included": False,
    }


def test_role_selection_materializes_only_requested_role_and_preserves_bytes(tmp_path):
    runtime = make_runtime(tmp_path / "runtime")
    output = tmp_path / "diagnostic"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime-root",
            str(runtime),
            "--output",
            str(output),
            "--role",
            "ADJUDICATOR_B",
        ],
        check=True,
        capture_output=True,
    )
    assert not (output / "ADJUDICATOR_A").exists()
    produced = sorted((output / "ADJUDICATOR_B" / "packets").rglob("*.blind.json"))
    source = sorted((runtime / "adjudicator-b-v8").rglob("*.blind.json"))
    assert len(produced) == len(source) == 12
    assert [item.read_bytes() for item in produced] == [
        item.read_bytes() for item in source
    ]


def test_a_and_b_source_exports_must_be_byte_identical(tmp_path):
    runtime = make_runtime(tmp_path / "runtime")
    changed = next((runtime / "adjudicator-b-v8").rglob("*.blind.json"))
    changed.write_bytes(changed.read_bytes() + b" ")
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime-root",
            str(runtime),
            "--output",
            str(tmp_path / "diagnostic"),
        ],
        check=False,
        capture_output=True,
    )
    assert run.returncode != 0
    assert (
        b"canonical JSON object" in run.stderr
        or b"source packet bytes differ" in run.stderr
    )


def test_extra_structurally_valid_packet_fails_cardinality(tmp_path):
    source = make_runtime(tmp_path / "runtime") / "adjudicator-a-v8"
    extra = source / "materialization-A/repetition-1/CANDIDATE-A/extra.blind.json"
    extra.write_bytes(packet("pcq-eos-001", "extra"))
    with pytest.raises(ValueError, match="exactly 12"):
        module.collect(source)


def test_packet_symlink_is_rejected_before_read(tmp_path, monkeypatch):
    source = make_runtime(tmp_path / "runtime") / "adjudicator-a-v8"
    target = next(source.rglob("*.blind.json"))
    original = Path.is_symlink

    def substituted(path):
        return path == target or original(path)

    monkeypatch.setattr(Path, "is_symlink", substituted)
    with pytest.raises(ValueError, match="symlinked packet path rejected"):
        module.collect(source)


def test_existing_output_fails_without_overwrite(tmp_path):
    runtime = make_runtime(tmp_path / "runtime")
    output = tmp_path / "diagnostic"
    output.mkdir()
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--runtime-root",
            str(runtime),
            "--output",
            str(output),
            "--role",
            "ADJUDICATOR_B",
        ],
        check=False,
        capture_output=True,
    )
    assert run.returncode != 0
    assert list(output.iterdir()) == []
