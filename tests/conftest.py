"""Explicit prerequisites for owner-held historical evidence tests."""

from __future__ import annotations

from pathlib import Path

import pytest

_OWNER_EVIDENCE_PREREQUISITES = {
    "test_humor_batch2_development_pilot02_preingestion_v1.py": ("owner-source-pilot02-v1.txt",),
    "test_humor_batch2_development_pilot03_preingestion_v1.py": ("owner-source-pilot03-v1.txt",),
    "test_humor_batch2_development_pilot04_preingestion_v1.py": ("owner-source-pilot04-v1.txt",),
    "test_humor_batch2_development_pilot05_preingestion_v1.py": ("owner-source-pilot05-v1.txt",),
    "test_humor_batch2_development_pilot06_preingestion_v1.py": ("owner-source-pilot06-v1.txt",),
    "test_humor_batch2_development_pilot08_preingestion_preparation_v1.py": ("owner-source-pilot08-v1.txt",),
    "test_humor_batch2_development_pilot09_preingestion_preparation_v1.py": ("owner-source-pilot09-v1.txt",),
    "test_humor_batch2_development_pilot10_preingestion_preparation_v1.py": ("owner-source-pilot10-v1.txt",),
    "test_humor_batch2_development_pilot11_preingestion_preparation_v1.py": ("owner-source-pilot11-v1.txt",),
    "test_humor_batch2_development_pilot12_preingestion_preparation_v1.py": ("owner-source-pilot12-v1.txt",),
    "test_humor_batch2_development_pilot12_preingestion_validation_v1.py": ("owner-source-pilot12-v1.txt",),
    "test_humor_batch2_development_pilot13_preingestion_v1.py": ("owner-source-pilot13-v1.txt", "owner-declaration-pilot13-v1.json"),
    "test_humor_batch2_development_pilot13_preingestion_validation_artifact.py": ("owner-source-pilot13-v1.txt", "owner-declaration-pilot13-v1.json"),
    "test_humor_batch2_development_pilot14_preingestion_validation.py": ("owner-source-pilot14-v1.txt",),
}

_HISTORICAL_IDENTITY_MODULES = {
    "test_semantic_admission_v2_case01_issued_authority_v1_2_1_durable_label_bound.py",
    "test_semantic_admission_v2_case01_issued_authority_v1_2_1_generation_telemetry_bound.py",
    "test_semantic_admission_v2_case01_issued_authority_v1_2_1_host_evidence_domain_bound.py",
    "test_semantic_admission_v2_gate_f_constrained_runner_identity_reconciliation_v1.py",
    "test_semantic_admission_v2_gate_f_constrained_runner_v1.py",
    "test_semantic_admission_v2_stage_p_constraint_failure_propagation_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_binding_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_case01_probe_binding_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_character_controller_v1_evidence.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_incremental_tracker_v2_evidence.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_projector_payload_binding_v2.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_application_request_policy_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_issuance_packet_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_issuance_packet_v1_2.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_issued_authority_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_issued_authority_v1_2.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_case01_transport_failure_static_remediation_v1.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_prompt_request_renderer_v1_evidence.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1_evidence.py",
    "test_semantic_admission_v2_stage_p_construction_obligation_v2_token_projector_feasibility_design_v1.py",
    "test_semantic_admission_v2_stage_p_construction_role_candidate_v1.py",
    "test_semantic_admission_v2_stage_p_construction_role_candidate_v1_evidence.py",
    "test_semantic_admission_v2_stage_p_construction_role_case01_probe_binding_v1.py",
    "test_semantic_admission_v2_stage_p_construction_role_case01_receipt_v1_1_probe_binding.py",
    "test_semantic_admission_v2_stage_p_construction_role_evaluator_binding_v1.py",
    "test_semantic_admission_v2_stage_p_construction_role_runner_binding_v1.py",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-historical-evidence",
        action="store_true",
        default=False,
        help="run the explicitly authorized superseded identity/evidence modules",
    )
    parser.addoption(
        "--run-owner-evidence",
        action="store_true",
        default=False,
        help="run the explicitly authorized owner-held evidence modules",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "owner_evidence: requires deliberately untracked owner evidence"
    )
    config.addinivalue_line(
        "markers", "historical_identity: validates a superseded evidence snapshot"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    root = Path(__file__).resolve().parents[1]
    for item in items:
        module_name = Path(str(item.path)).name
        if module_name in _HISTORICAL_IDENTITY_MODULES:
            item.add_marker(pytest.mark.historical_identity)
            if not config.getoption("--run-historical-evidence"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="superseded identity snapshot; use --run-historical-evidence"
                    )
                )
                continue
        required = _OWNER_EVIDENCE_PREREQUISITES.get(module_name)
        if required is None:
            continue
        item.add_marker(pytest.mark.owner_evidence)
        missing = tuple(name for name in required if not (root / name).is_file())
        if missing and not config.getoption("--run-owner-evidence"):
            item.add_marker(
                pytest.mark.skip(
                    reason="owner-held evidence suite disabled; use --run-owner-evidence"
                )
            )
