import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def _load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def _seal(namespace: str, value: dict) -> str:
    encoded = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_v5_3_runtime_artifacts_are_self_verifying_and_non_authorizing() -> None:
    files = [
        ("humor-mechanics-batch2-development-constructor-v5-3-realization-provider-implementation.json", "realization_provider_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_3_REALIZATION_PROVIDER_IMPLEMENTATION"),
        ("humor-mechanics-batch2-development-constructor-v5-3-candidate-emitter-implementation.json", "candidate_emitter_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_3_CANDIDATE_EMITTER_IMPLEMENTATION"),
        ("humor-mechanics-batch2-development-constructor-implementation-v5-3.json", "constructor_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_3"),
        ("humor-mechanics-batch2-development-constructor-v5-3-runtime-static-audit-v1.json", "static_audit_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_3_RUNTIME_STATIC_AUDIT_V1"),
    ]
    for name, field, namespace in files:
        artifact = _load(name)
        identity = artifact.pop(field)
        assert identity == _seal(namespace, artifact)
        assert artifact.get("release_authority", False) is False
    audit = _load(files[-1][0])
    assert audit["constructor_invocations"] == 0
    assert audit["candidate_surfaces_created_or_persisted"] == 0
    assert audit["pilot10_failure_class"] == "PASS_FAIL_CLOSED_BEFORE_REALIZATION"
