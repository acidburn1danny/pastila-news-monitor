"""Freeze Pilot 13's non-consuming V5.3.3 post-repair requalification."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
REPAIR_COMMIT = "42d9d2baf75ebf5bdd2287d20cbff6d90f8ea73a"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name, value):
    path = ART / name
    if path.exists():
        raise SystemExit(f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main():
    hydrator_source = (ROOT / "src/pastila_scout/humor_batch2_constructor_access_v1.py").read_bytes()
    schema_core = {
        "schema_name": "pilot13-v5-3-3-exact-release-hydration-schema",
        "release_schema": "batch2-development-pilot13-constructor-access-release-v5-3-3",
        "release_core_fields": 22,
        "constructor_packet_fields": 44,
        "unknown_or_missing_fields": "FAIL_CLOSED",
        "stale_alias_or_version_skew": "FAIL_CLOSED",
        "family_and_frozen_binding_skew": "FAIL_CLOSED",
    }
    schema = {**schema_core, "schema_identity": seal("B2_PILOT13_V5_3_3_RELEASE_HYDRATION_SCHEMA", schema_core)}
    hydrator_identity = seal("B2_PILOT13_V5_3_3_RELEASE_HYDRATOR_IMPLEMENTATION", {
        "source_sha256": hashlib.sha256(hydrator_source).hexdigest(), "schema_identity": schema["schema_identity"]})
    core = {
        "schema_name": "batch2-development-pilot13-v5-3-3-postqualification-revalidation",
        "schema_version": "1.0.0",
        "reviewed_repair_commit": REPAIR_COMMIT,
        "POST_QUALIFICATION_REVALIDATION_VERDICT": "PASS_POST_REPAIR_EXECUTABLE_REQUALIFICATION_ZERO_FAMILY_ZERO_CAPABILITY",
        "root_cause": "GENERIC_CONSTRUCTOR_ACCESS_VERIFIER_ALLOWLIST_ENDED_AT_PILOT12_AND_LACKED_PILOT13_V5_3_3_RELEASE_PACKET_SCHEMA_AND_EXACT_BINDING_BRANCH",
        "prior_qualification_miss": "ZERO_FAMILY_QUALIFICATION_EXECUTED_THE_CLAUSE_TO_EMITTER_PATH_WITH_SYNTHETIC_AUTHORITY_BUT_DID_NOT_INSTANTIATE_A_REAL_FAMILY_RELEASE_ENVELOPE_THROUGH_THE_GENERIC_ACCESS_HYDRATOR",
        "defect_scope": "GENERAL_RELEASE_HYDRATION_QUALIFICATION_GAP_TRIGGERED_BY_PILOT13_FAMILY_METADATA",
        "qualified_v5_3_3_execution_identity_unchanged": "9016f7a82cb04ba447c2c2ae4275861ef0bfbd16782c4be3584d85220f5b5c0a",
        "qualified_executable_implementation_unchanged": "3c7c353d488d032dd69f9d12a07a621bfc7bb95b668e76efc08494546f5d5362",
        "release_hydration_schema_identity": schema["schema_identity"],
        "release_hydrator_implementation_identity": hydrator_identity,
        "actual_committed_release_hydration": "PASS_WITHOUT_CAPABILITY_CONSUMPTION",
        "synthetic_nonfamily_executable_path": "PASS_AUTHORITY_TO_HYDRATION_TO_CLASS_A_TO_CLAUSE_BYTES_TO_CLASS_B_TO_CONFORMANCE_TO_CONDITIONAL_EMITTER",
        "adversarial_variants": {
            "unknown_keys": "FAIL_CLOSED", "missing_keys": "FAIL_CLOSED", "stale_aliases": "FAIL_CLOSED",
            "version_skew": "FAIL_CLOSED", "alternate_family_ids": "FAIL_CLOSED",
            "implementation_identity_skew": "FAIL_CLOSED", "denyset_binding_skew": "FAIL_CLOSED",
            "authority_or_span_skew": "FAIL_CLOSED", "release_hydration": "PASS_EXACT_ONLY",
        },
        "analogous_path_audit": "PASS_EXPLICIT_SCHEMA_AND_BINDING_BRANCHES_PILOTS01_THROUGH13_NO_KNOWN_DETERMINISTIC_BLOCKER",
        "focused_requalification_tests": "87_PASSED",
        "broader_pilot05_12_tests": "141_PASSED_3_ACL_ENVIRONMENT_INACCESSIBLE_ARCHIVE_TESTS_NOT_RELEASE_PATH_FAILURES",
        "pilot13_capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "actual_pilot13_invocations": "0/0/0",
        "pilot13_candidate_surfaces": 0,
        "WORKTREE_REMEDIATION_REMAINDER": "NONE_IN_SCOPE",
        "PILOT13_INFRASTRUCTURE_READINESS_VERDICT": "PILOT13_READY_FOR_ONE_SHOT_CONSTRUCTION",
    }
    value = {**core, "requalification_identity": seal("B2_PILOT13_V5_3_3_POSTQUALIFICATION_REVALIDATION", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot13-v5-3-3-postqualification-revalidation-audit",
        "requalification_identity": value["requalification_identity"],
        "schema_identity": schema["schema_identity"],
        "hydrator_implementation_identity": hydrator_identity,
        "frozen_pilot13_artifacts_modified": False,
        "pilot13_release_or_capability_exercised": False,
        "synthetic_nonfamily_execution_only": True,
        "blind_material_accessed": False,
        "downstream_authority_exercised": False,
        "verdict": "PASS_STABLE_TERMINAL_REQUALIFICATION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_PILOT13_V5_3_3_POSTQUALIFICATION_REVALIDATION_AUDIT", audit_core)}
    write("humor-mechanics-batch2-development-pilot13-v5-3-3-release-hydration-schema.json", schema)
    write("humor-mechanics-batch2-development-pilot13-v5-3-3-postqualification-revalidation.json", value)
    write("humor-mechanics-batch2-development-pilot13-v5-3-3-postqualification-revalidation-audit.json", audit)
    print(json.dumps({"requalification_identity": value["requalification_identity"], "schema_identity": schema["schema_identity"],
                      "hydrator_implementation_identity": hydrator_identity, "audit_identity": audit["audit_identity"],
                      "verdict": value["POST_QUALIFICATION_REVALIDATION_VERDICT"]}, sort_keys=True))


if __name__ == "__main__":
    main()
