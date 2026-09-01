"""Consume exactly one Pilot 10 V5.2 capability and freeze the observed result."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import (
    ConstructorPacketCapabilityV1,
    prepare_development_constructor_access_v1,
)
from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode
from pastila_scout.humor_batch2_development_constructor_v5_2_runtime import (
    NodeLexicalization,
    emit_candidate_utf8,
    realize_typed_plan,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_COMMIT = "84b4fe215683c9a5fb82e94a8c13ae6c97807179"
RELEASE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-constructor-access-release-v5-2.json"
RUNNER_PATH = "scripts/run_humor_batch2_development_pilot10_construction_once_v5_2.py"
CANDIDATE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-v1.txt"
EVIDENCE = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-construction-attempt01-v1.json"
ACCESS_PATH = "src/pastila_scout/humor_batch2_constructor_access_v1.py"
RUNTIME_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"
ENFORCEMENT_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_2.py"
ACCESS_SHA = "73e51e5f9cffecac72fcb0b5cf037b54b01dee9dcd0d3b8b23408dc6d13fbbc6"
RUNTIME_SHA = "bde911af41fc95772590f5ab86c1fc0ac39ae98937366e6c312e0a709429f3e7"
ENFORCEMENT_SHA = "ec8ddecb00d64f96d5d8742befd270305f9a16be5d907eae19e33ecbdee280e1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def committed(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def lexicalizations() -> tuple[NodeLexicalization, ...]:
    return (
        NodeLexicalization(
            node_id="L1",
            clause=("Într-un registru imaginar, aprobarea și mutarea lăzii, dacă greutatea și numărul "
                    "etichetei corespund documentului, pornesc regula depozitului: orice spațiu care "
                    "primește lada devine material horticol provizoriu."),
            actor_surface="aprobarea și mutarea lăzii",
            predicate_surface="pornesc regula depozitului",
            patient_surface="dacă greutatea și numărul etichetei corespund documentului",
            produced_operand_surfaces=(("INVENTED_RELATION_1", "regula depozitului"),),
            terminal_result=False,
        ),
        NodeLexicalization(
            node_id="L2",
            clause=("Regula depozitului prinde astfel zona destinată materialelor horticole în propriul "
                    "inventar și o transformă în zona devenită material horticol."),
            actor_surface="regula depozitului",
            predicate_surface="o transformă",
            patient_surface="zona destinată materialelor horticole",
            produced_operand_surfaces=(("INVENTED_RELATION_2", "zona devenită material horticol"),),
            terminal_result=False,
        ),
        NodeLexicalization(
            node_id="RESULT",
            clause=("Zona devenită material horticol aplică apoi aprobarea și mutarea lăzii chiar "
                    "depozitului: depozitul primește eticheta APROBAT și este mutat în el însuși."),
            actor_surface="zona devenită material horticol",
            predicate_surface="aplică apoi",
            patient_surface="aprobarea și mutarea lăzii",
            produced_operand_surfaces=(),
            terminal_result=True,
        ),
    )


def main() -> None:
    if CANDIDATE.exists() or EVIDENCE.exists():
        raise SystemExit("Pilot 10 construction attempt already consumed")
    execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", RELEASE_COMMIT, execution_commit], cwd=ROOT).returncode:
        raise SystemExit("release commit is not an ancestor")
    runner = (ROOT / RUNNER_PATH).read_bytes()
    if committed(execution_commit, RUNNER_PATH) != runner:
        raise SystemExit("runner is not exact committed execution source")
    for path, expected in ((ACCESS_PATH, ACCESS_SHA), (RUNTIME_PATH, RUNTIME_SHA), (ENFORCEMENT_PATH, ENFORCEMENT_SHA)):
        raw = (ROOT / path).read_bytes()
        if committed(execution_commit, path) != raw or hashlib.sha256(raw).hexdigest() != expected:
            raise SystemExit(f"execution source identity: {path}")

    release_bytes = committed(RELEASE_COMMIT, RELEASE_PATH)
    prepared = prepare_development_constructor_access_v1(release_bytes=release_bytes)
    if prepared.release_identity != "746d3bc3c8af78b41a83a3e610d43cd89cc90d1163dac036d1af5ad8dca2fb89":
        raise SystemExit("release identity")
    if prepared.packet_identity != "7d894969dfeed0703ee31f4fe3223ef9dfbdd3fbe873f2ac6d6e02054e8694aa":
        raise SystemExit("packet identity")

    capability = ConstructorPacketCapabilityV1(prepared)
    packet_bytes = capability.read_constructor_packet()
    packet = json.loads(packet_bytes)
    plan = tuple(TypedPlanNode(
        node_id=node["node_id"], bound_actor_id=node["bound_actor_id"], actor_role=node["actor_role"],
        predicate_id=node["predicate_id"], bound_patient_id=node["bound_patient_id"],
        predecessor_node_ids=tuple(node["predecessor_node_ids"]), introduces_ids=tuple(node["introduces_ids"]),
        source_provenance=node["source_provenance"], nonfactual_scope=node["nonfactual_scope"],
    ) for node in packet["proposition_derived_typed_plan"])

    provider_invocations = emitter_invocations = 0
    candidate_bytes: bytes | None = None
    failure_code: str | None = None
    try:
        # Sole authorized construction attempt and sole provider invocation.
        provider_invocations = 1
        draft = realize_typed_plan(exact_source=packet["exact_authorized_visible_context_utf8"],
                                   typed_plan=plan, lexicalizations=lexicalizations())
        # Sole emitter invocation. It validates V5.2 conformance before returning bytes.
        emitter_invocations = 1
        candidate_bytes = emit_candidate_utf8(typed_plan=plan, draft=draft)
        terminal = "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY_FRAGMENT_COLLISION_PENDING"
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        terminal = "FAIL_CLOSED_PRE_EMISSION_CONFORMANCE_NO_CANDIDATE"
        failure_code = f"{type(exc).__name__}: {exc}"

    if candidate_bytes is not None:
        candidate_bytes.decode("utf-8")
        candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()
        candidate_id = seal("B2_DEVELOPMENT_PILOT10_CANDIDATE_V1", {
            "constructor_packet_identity": prepared.packet_identity,
            "raw_surface_sha256": candidate_sha,
            "attempt_ordinal": 1,
            "partition": "DEVELOPMENT",
        })
        creative_family = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
            "sealed_assignment_identity": packet["immutable_assignment_identity"],
            "source_commitment": packet["closed_factual_authority_envelope"]["source_commitment"],
            "candidate_identity": candidate_id,
        })
        creative_marker_family = seal("B2_CREATIVE_MARKER_FAMILY_V5_2", {
            "candidate_identity": candidate_id,
            "construction_revision_family_id": packet["construction_revision_family_id"],
        })
        CANDIDATE.write_bytes(candidate_bytes)
    else:
        candidate_sha = candidate_id = None
        creative_family = creative_marker_family = "UNASSIGNED"

    candidate_material = candidate_bytes or b""
    forbidden = (b"HMCV1-", b"ABSURD_LOGICAL_EXTENSION", b"mechanism_id", b"mechanism_name",
                 b"answer_key", b"witness", b"operand", b"predecessor")
    hidden = any(token.lower() in candidate_material.lower() for token in forbidden)
    conformance_pass = candidate_bytes is not None and not hidden
    core = {
        "schema_name": "batch2-development-pilot10-construction-attempt01-v1",
        "schema_version": "1.0.0",
        "execution_source_commit": execution_commit,
        "constructor_access_source_sha256": ACCESS_SHA,
        "realization_runtime_source_sha256": RUNTIME_SHA,
        "pre_emission_enforcement_source_sha256": ENFORCEMENT_SHA,
        "release_commit": RELEASE_COMMIT,
        "release_identity": prepared.release_identity,
        "constructor_facing_packet_identity": prepared.packet_identity,
        "constructor_contract_identity": packet["constructor_contract_identity"],
        "constructor_implementation_identity": packet["constructor_implementation_identity"],
        "realization_provider_identity": packet["realization_provider_identity"],
        "candidate_emitter_identity": packet["candidate_emitter_identity"],
        "constructor_source_compatibility_identity": packet["constructor_source_compatibility_identity"],
        "pre_emission_governance_identity": packet["pre_emission_governance_identity"],
        "pre_emission_conformance_schema_identity": packet["pre_emission_conformance_schema_identity"],
        "pre_emission_enforcement_identity": packet["pre_emission_enforcement_identity"],
        "fragment_denyset_identity": packet["fragment_denyset_identity"],
        "selected_proposition_id": packet["selected_proposition_id"],
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "typed_plan_commitment": packet["typed_plan_commitment"],
        "attempt": {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1,
                    "provider_invocations": provider_invocations, "emitter_invocations": emitter_invocations},
        "terminal_classification": terminal,
        "failure_code": failure_code,
        "pre_emission_conformance": {
            "verdict": "PASS_PRE_EMISSION_REALIZATION_CONFORMANCE" if conformance_pass else "FAIL_CLOSED_NO_EMISSION",
            "causal_nodes_realized": 3 if conformance_pass else None, "causal_nodes_required": 3,
            "causal_edges_realized": 2 if conformance_pass else None, "causal_edges_required": 2,
            "typed_operand_continuity": "PASS" if conformance_pass else "NOT_ESTABLISHED",
            "terminal_result_witnesses": 1 if conformance_pass else 0,
            "collapsed_summarized_placeholder_or_asserted_relations": "ABSENT" if conformance_pass else "NOT_ESTABLISHED",
            "instruction_governance_plan_meta_language_transfer": "ABSENT" if conformance_pass else "NOT_ESTABLISHED",
            "validation_preceded_candidate_persistence_and_emission": True,
        },
        "candidate_identity": candidate_id,
        "candidate_surface_sha256": candidate_sha,
        "candidate_surface_byte_length": len(candidate_bytes) if candidate_bytes else None,
        "candidate_surface_present": candidate_bytes is not None,
        "candidate_partition": "DEVELOPMENT" if candidate_id else None,
        "creative_premise_family_id": creative_family,
        "creative_marker_family_id": creative_marker_family,
        "capability": {"state": "CONSUMED_1_OF_1", "single_use": True, "reads": 1, "remaining": 0,
                       "constructor_visible_sha256": hashlib.sha256(packet_bytes).hexdigest()},
        "constructor_exposure_reconciliation": {
            "authorized_packet_only": True, "exact_selected_source_span_only": True,
            "sealed_mapping_exposed": False, "blind_material_exposed": False,
            "repository_or_filesystem_access_by_constructor": False, "environment_or_cli_access": False,
            "logs_cache_temp_process_or_network_access": False, "hidden_mechanism_metadata_introduced": hidden,
        },
        "post_construction_g02b_verdict": "PASS" if not hidden else "FAIL_HIDDEN_METADATA",
        "fragment_collision_evaluation": "NOT_PERFORMED_REQUIRES_SEPARATE_AUTHORIZATION_BEFORE_G02",
        "g02_eligibility": False,
        "retry_authority": False, "repair_authority": False, "selection_authority": False,
        "authority_matrix": {key: False for key in ("fragment_collision_evaluation", "g02", "g02c", "g03",
                              "romanian_naturalness", "voice", "owner_review", "g04b_pool_certification",
                              "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    evidence = {**core, "evidence_identity": seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTION_ATTEMPT01_V1", core)}
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"terminal_classification": terminal, "candidate_identity": candidate_id,
                      "candidate_surface_sha256": candidate_sha, "creative_premise_family_id": creative_family,
                      "creative_marker_family_id": creative_marker_family, "pre_emission_conformance": evidence["pre_emission_conformance"]["verdict"],
                      "capability_state": "CONSUMED_1_OF_1", "constructor_invocations": 1,
                      "provider_invocations": provider_invocations, "emitter_invocations": emitter_invocations,
                      "evidence_identity": evidence["evidence_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
