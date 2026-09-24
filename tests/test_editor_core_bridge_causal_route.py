from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_editor_core_editorial_mechanics_bridge import ART, PREFIX, compact  # noqa: E402
from prepare_editor_core_bridge_blind_scoring import prepare  # noqa: E402
from project_editor_core_bridge_causal_runs import SEEDS, project  # noqa: E402
from train_editor_core_bridge_causal_pilot import fixture_smoke, validate_config  # noqa: E402


@pytest.mark.parametrize("arm", ["A1", "A2"])
@pytest.mark.parametrize("seed", SEEDS)
def test_six_distinct_bound_specs_fixture_only(arm, seed):
    corpus, spec = project(arm, seed)
    assert len(corpus.splitlines()) == 96
    result = fixture_smoke(spec)
    assert result["status"] == "PASS_FIXTURE_ONLY"
    assert result["optimizer_steps_executed"] == 0


def test_config_mutation_fails_closed():
    corpus, spec = project("A1", SEEDS[0])
    changed = dict(spec)
    changed["arm"] = "A2"
    with pytest.raises(ValueError, match="identity"):
        validate_config(changed, spec["training_corpus_sha256"], len(corpus.splitlines()))


def fixture_responses(root: Path):
    requests = [json.loads(line) for line in (ART / f"{PREFIX}-development-requests.jsonl").read_bytes().splitlines()]
    for name in ("r2", *(f"{arm.lower()}-seed-{seed}" for arm in ("A1", "A2") for seed in SEEDS)):
        rows = []
        for row in requests:
            request = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
            rows.append({"case_id": row["example_id"], "request_identity": request["request_identity"],
                         "response": "fixture response " + hashlib.sha256(name.encode()).hexdigest()[:12]})
        (root / f"{name}.jsonl").write_bytes(b"".join(compact(row).encode("utf-8") + b"\n" for row in rows))


def test_blind_packet_and_sealed_mapping_fixture(tmp_path):
    responses, packets, reference, custody = (tmp_path / name for name in ("responses", "packets", "reference", "custody"))
    for path in (responses, packets, reference, custody):
        path.mkdir()
    reference.chmod(0o700)
    custody.chmod(0o700)
    fixture_responses(responses)
    result = prepare(responses, packets, reference, custody, permutation=lambda: [1, 0])
    assert result["primary_pair_packets"] == 72 and result["later_reference_packets"] == 24
    assert len(list(packets.iterdir())) == 72
    assert len(list(reference.iterdir())) == 24
    packet = json.loads(next(packets.iterdir()).read_bytes())
    assert all("arm" not in item for item in packet["options"])
    assert "A1" not in json.dumps(packet) and "A2" not in json.dumps(packet)
    mapping = json.loads((custody / "sealed-arm-map.json").read_bytes())
    assert len(mapping["packets"]) == 96


def test_blind_scoring_rejects_overlap_and_replay(tmp_path):
    responses, packets, reference, custody = (tmp_path / name for name in ("responses", "packets", "reference", "custody"))
    for path in (responses, packets, reference, custody):
        path.mkdir()
    reference.chmod(0o700)
    custody.chmod(0o700)
    fixture_responses(responses)
    with pytest.raises(ValueError, match="separation"):
        prepare(responses, packets, reference, packets)
    prepare(responses, packets, reference, custody, permutation=lambda: [1, 0])
    with pytest.raises(ValueError, match="overwrite"):
        prepare(responses, packets, reference, custody)
