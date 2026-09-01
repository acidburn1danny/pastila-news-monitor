import hashlib
import json
from pathlib import Path


ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def seal(namespace, value):
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def test_v5_3_1_integration_artifacts_are_sealed_and_non_authorizing():
    provider = load("humor-mechanics-batch2-development-constructor-v5-3-1-realization-provider-implementation.json")
    emitter = load("humor-mechanics-batch2-development-constructor-v5-3-1-candidate-emitter-implementation.json")
    combined = load("humor-mechanics-batch2-development-constructor-implementation-v5-3-1.json")
    audit = load("humor-mechanics-batch2-development-constructor-v5-3-1-runtime-static-audit-v1.json")
    for value, field, namespace in (
        (provider, "realization_provider_identity", "B2_CONSTRUCTOR_V5_3_1_REALIZATION_PROVIDER"),
        (emitter, "candidate_emitter_identity", "B2_CONSTRUCTOR_V5_3_1_CANDIDATE_EMITTER"),
        (combined, "constructor_implementation_identity", "B2_CONSTRUCTOR_IMPLEMENTATION_V5_3_1"),
        (audit, "static_audit_identity", "B2_CONSTRUCTOR_V5_3_1_RUNTIME_STATIC_AUDIT_V1"),
    ):
        core = dict(value); identity = core.pop(field)
        assert identity == seal(namespace, core)
    assert audit["verdict"] == "PASS_V5_3_1_PROVIDER_EMITTER_INTEGRATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE"
    assert audit["enumerated_ambele_ambelor_alignment"] == "PASS_ACCEPTED_WITH_COORDINATES"
    assert audit["missing_coordinates_or_absent_text"] == "PASS_FAIL_CLOSED"
    assert audit["unlicensed_synonymy_paraphrase_fuzzy_or_semantic_guessing"] == "PASS_FAIL_CLOSED"
    assert audit["v5_3_role_affordance_entity_edge_and_terminal_guards"] == "PASS_PRESERVED_UNCHANGED"
    assert audit["pilot11_capability_state"] == "PRESERVED_CONSUMED_1_OF_1_NO_RETRY"
    assert audit["constructor_invocations"] == audit["provider_invocations"] == audit["emitter_invocations"] == 0
    assert audit["candidate_surfaces"] == 0 and audit["release_authority"] is False
