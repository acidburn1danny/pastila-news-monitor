"""Build the publication identity for the fixture-only hybrid runtime boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
OUTPUT = ART / "editor-core-source-bound-hybrid-runtime-boundary-v1.json"
FILES = (
    "scripts/editor_core_source_bound_hybrid_runtime_v1.py",
    "scripts/preflight_editor_core_source_bound_hybrid_runtime_v1.py",
    "scripts/smoke_editor_core_source_bound_hybrid_runtime_v1.py",
    "scripts/run_editor_core_source_bound_hybrid_runtime_v1.sh",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


core = {
    "schema": "editor-source-bound-hybrid-runtime-boundary",
    "schema_version": 1,
    "status": "FIXTURE_ONLY_NO_REAL_EXECUTION_AUTHORITY",
    "source_commit": "50c103a5cf7238588789ed3600693ff4ac2ba053",
    "source_tree": "8687172d3ba0769d4fc2fe70212ca7f28423b2cd",
    "pack_identity": "bbad139fde613c1c912cd53992b4c2be047d73180f6a6ae732dc6348461d28f9",
    "protocol_identity": "5a5ef79af85a3b58b3c0e2f46be3f9e3dd573d75dae361c6d6df88588f7c1aea",
    "tokenizer_sha256": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    "parent": "R2_STEP_9",
    "parent_adapter_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
    "arms": ["B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID"],
    "seeds": [161803, 271828, 314159],
    "slots": 9,
    "output_isolation": "DISTINCT_NEW_EMPTY_ROOT_PER_ARM_SEED",
    "verifier": "LEDGER_BOUND_FAIL_CLOSED",
    "fallback": "DETERMINISTIC_EXTRACTIVE_REQUIRED_ATOMS",
    "oracle_fixture_upper_bound": True,
    "autonomous_ledger_construction_claimed": False,
    "real_route_requires_independent_selection_curation": True,
    "files": {name: sha(ROOT / name) for name in FILES},
    "model_load_authorized": False,
    "inference_authorized": False,
    "optimizer_creation_authorized": False,
    "training_authorized": False,
    "execution_authority": False,
    "successor_candidate_authorized": False,
    "historical_holdouts_allowed": False,
    "parent_selection_authority": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "voice_or_chief_editor_objective": False,
}
identity = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
boundary = {**core, "runtime_boundary_identity": identity}
OUTPUT.write_bytes((json.dumps(boundary, sort_keys=True, indent=2) + "\n").encode("utf-8"))
print(json.dumps({"status": "PASS_BUILD", "runtime_boundary_identity": identity}, sort_keys=True))
