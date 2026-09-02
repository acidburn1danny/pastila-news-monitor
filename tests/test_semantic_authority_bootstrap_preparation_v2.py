import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/artifacts/semantic-contract-v2-external-general-semantic-authority-source-request-v1.json"
PROTOCOL = ROOT / "docs/artifacts/semantic-contract-v2-independent-semantic-authority-admission-protocol-v1.json"


def identity(record, field):
    body = {key: value for key, value in record.items() if key != field}
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_preparation_identities_and_binding_are_canonical():
    request = load(REQUEST)
    protocol = load(PROTOCOL)
    assert request["request_identity"] == identity(request, "request_identity")
    assert protocol["protocol_identity"] == identity(protocol, "protocol_identity")
    assert protocol["authority_source_request_identity"] == request["request_identity"]
    assert request["bootstrap_architecture_identity"] == protocol["bootstrap_architecture_identity"]


def test_preparation_is_content_free_and_non_operational():
    request = load(REQUEST)
    protocol = load(PROTOCOL)
    assert request["semantic_authority_content_created"] is False
    assert request["authority_basis_created_or_admitted"] is False
    assert protocol["semantic_content_created"] is False
    assert protocol["authority_bases_created"] == 0
    assert protocol["authority_bases_admitted"] == 0
    assert request["curriculum_population_started"] is False
    assert protocol["population_started"] is False
    assert request["pilot15_prepared"] is False
    assert protocol["pilot15_prepared"] is False
    assert request["blind_or_future_family_access"] is False
    assert protocol["blind_or_future_family_access"] is False


def test_protocol_preserves_non_circular_role_separation():
    protocol = load(PROTOCOL)
    roles = protocol["role_separation"]["minimum_mandatory_distinct_roles"]
    assert len(roles) == len(set(roles)) == 4
    assert protocol["role_separation"]["component_may_author_and_verify_same_authority"] is False
    guarantees = set(protocol["anti_circularity_guarantees"])
    assert "AUTHORITY_PREEXISTS_CANDIDATE_IDENTITY" in guarantees
    assert "ADMISSION_RECEIPT_CANDIDATE_IDENTITY_IS_NULL" in guarantees
    assert "CANDIDATE_BOUND_EVIDENCE_CANNOT_BE_PROMOTED_BACK_TO_SOURCE_OR_BASIS" in guarantees
    assert protocol["later_consumption_gate"]["dynamic_authority_extension"] is False


def test_source_request_forbids_downstream_shaping_and_fixture_promotion():
    request = load(REQUEST)
    declarations = set(request["independence_declarations"])
    assert "NOT_SELECTED_OR_SHAPED_FOR_ANY_FUTURE_CANDIDATE" in declarations
    assert "NOT_SELECTED_OR_SHAPED_FOR_ANY_MECHANISM_LABEL_OR_POOL_NEED" in declarations
    assert "NO_BLIND_OR_FUTURE_FAMILY_MATERIAL_USED" in declarations
    assert any("SYNTHETIC_QUALIFICATION_FIXTURE" in item for item in request["legitimate_source_criteria"])
