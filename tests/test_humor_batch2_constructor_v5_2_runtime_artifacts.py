import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load_sealed(name, field, namespace):
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    core = dict(value); identity = core.pop(field)
    assert identity == seal(namespace, core)
    return value


def test_v5_2_runtime_artifacts_are_sealed_and_non_authorizing():
    provider = load_sealed("humor-mechanics-batch2-development-constructor-v5-2-realization-provider-implementation.json", "realization_provider_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_2_REALIZATION_PROVIDER_IMPLEMENTATION")
    emitter = load_sealed("humor-mechanics-batch2-development-constructor-v5-2-candidate-emitter-implementation.json", "candidate_emitter_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_2_CANDIDATE_EMITTER_IMPLEMENTATION")
    implementation = load_sealed("humor-mechanics-batch2-development-constructor-implementation-v5-2.json", "constructor_implementation_identity", "B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_2")
    audit = load_sealed("humor-mechanics-batch2-development-constructor-v5-2-runtime-static-audit-v1.json", "static_audit_identity", "B2_DEVELOPMENT_CONSTRUCTOR_V5_2_RUNTIME_STATIC_AUDIT_V1")
    assert provider["lexicalization_coverage"] == "EXACT_N_OF_N"
    assert emitter["required_coverage"] == {"nodes": "N_OF_N", "edges": "E_OF_E", "terminal_result": "1_OF_1"}
    assert implementation["constructor_invocations"] == implementation["candidate_surfaces_created_or_emitted"] == 0
    assert implementation["release_authority"] is False and implementation["construction_authority"] is False
    assert audit["constructor_invocations"] == audit["realizer_invocations"] == audit["emitter_invocations"] == 0
    assert audit["candidate_surfaces_created_or_persisted"] == 0
    assert audit["constructor_release"] == "NOT_PERFORMED"
    assert audit["verdict"].endswith("ZERO_CONSTRUCTION_NO_RELEASE")
