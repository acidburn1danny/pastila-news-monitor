import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "docs"
    / "artifacts"
    / ("application-wide-canonical-wsl-execution-boundary-v1.json")
)
SUCCESSOR = ROOT / "docs/artifacts/canonical-wsl-boundary-v1-1-core-rebinding.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_canonical_identity_and_all_implementation_hashes_rederive():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == value["canonical_identity"]
    )
    implementation = value["implementation"]
    assert (
        _sha(ROOT / implementation["boundary_path"])
        == implementation["boundary_sha256"]
    )
    assert (
        _sha(ROOT / implementation["package_path"]) == implementation["package_sha256"]
    )
    assert (
        _sha(ROOT / implementation["architecture_path"])
        == implementation["architecture_sha256"]
    )
    successor = json.loads(SUCCESSOR.read_text("utf-8"))
    predecessor = successor["approved_predecessor"]
    assert (
        predecessor["frozen_v1_core_v1_2_sha256"] == implementation["core_v1_2_sha256"]
    )
    assert (
        predecessor["frozen_v1_core_v1_1_sha256"] == implementation["core_v1_1_sha256"]
    )
    assert (
        _sha(ROOT / "src/pastila_scout/experimental_core_v1_2.py")
        == successor["binding"]["core_v1_2_sha256"]
    )
    assert (
        _sha(ROOT / "src/pastila_scout/experimental_core_v1_1.py")
        == successor["binding"]["core_v1_1_sha256"]
    )


def test_authority_and_frozen_evidence_boundaries_are_explicit():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    authority = value["authority_separation"]
    assert not authority["boundary_owns_prompt"]
    assert not authority["boundary_owns_model_adapter_or_tokenizer"]
    assert not authority["boundary_makes_semantic_or_eligibility_decisions"]
    assert not authority["boundary_authorizes_execution"]
    frozen = value["frozen_evidence_policy"]
    assert not frozen["historical_artifacts_rewritten"]
    assert not frozen["legacy_launcher_bytes_modified"]
    assert value["inventory"]["grandfathered_frozen_evaluation_launchers"] == 16


def test_live_preflight_was_zero_model_and_packaging_does_not_install_wsl():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["operational_preflight"]["result"] == "PASS_ZERO_MODEL"
    assert value["operational_preflight"]["model_loads"] == 0
    assert value["operational_preflight"]["inference_calls"] == 0
    assert not value["packaging"]["installer_installs_or_modifies_wsl"]
    assert not value["packaging"][
        "installer_bundles_distro_models_adapters_or_linux_python"
    ]
