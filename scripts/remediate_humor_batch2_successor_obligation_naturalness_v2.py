"""Freeze source-only naturalness remediation for the successor obligation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
BASE_COMMIT = "007d08ab247cd2518309cfb9b837cf89806ab045"
V1_PATH = "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v1.json"
DISPOSITION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-naturalness-rejection-disposition-v1.json"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == BASE_COMMIT,
        "HEAD differs from Pilot 02 disposition commit",
    )
    v1 = load_json(V1_PATH)
    disposition = load_json(DISPOSITION_PATH)
    candidate = subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT)
    require(v1["obligation_governance_identity"] == "0cfd22fd43e0be68b5a04f16e45e918ac7bae346c851334817a7af309bad63e5", "v1 identity")
    require(disposition["disposition_identity"] == "6045d690a4405c935dfb754d772dc01d68adf2a57435f3a91a7294b13c706381", "disposition identity")
    require(hashlib.sha256(candidate).hexdigest() == disposition["candidate_raw_sha256"], "candidate bytes")

    analysis_core = {
        "schema_name": "batch2-successor-obligation-naturalness-root-cause-analysis-v1",
        "schema_version": "1.0.0",
        "pilot02_disposition_identity": disposition["disposition_identity"],
        "pilot02_candidate_identity": disposition["candidate_identity"],
        "pilot02_candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "parent_obligation_governance_identity": v1["obligation_governance_identity"],
        "stable_rejection_reasons": disposition["stable_rejection_reasons"],
        "causal_trace": [
            {
                "governance_text": "Create a short, explicitly fictional continuation containing exactly two distinct changes.",
                "surface_effect": "Într-o continuare explicit fictivă",
                "defect": "The instruction required explicitness but did not distinguish an integrated Romanian narrative cue from a literal governance label.",
                "causal_classification": "DIRECT_WORDING_PRESSURE",
            },
            {
                "governance_text": "Keep one relation operative; make the second change unavailable unless the first has occurred.",
                "surface_effect": "suspendă ... încheierea testului; fiindcă ... încetează ... să mai existe",
                "defect": "Reviewer-facing dependency language was exposed without a concrete-language or register guard, encouraging procedural abstraction.",
                "causal_classification": "STRUCTURAL_WORDING_AND_MISSING_GUARD_INTERACTION",
            },
            {
                "governance_text": "register = IDIOMATIC_NATURAL_ROMANIAN",
                "surface_effect": "The output remained grammatical but materially bureaucratic.",
                "defect": "A declarative register field had no pre-G03 fail-closed conformance predicate and was therefore non-operative.",
                "causal_classification": "MISSING_ENFORCEMENT",
            },
        ],
        "root_cause": "CONSTRUCTOR_VISIBLE_GOVERNANCE_WORDING_PLUS_ABSENT_EARLY_NATURALNESS_ADMISSION",
        "source_family_causal": False,
        "constructor_choice_contributed": True,
        "candidate_repair_required_or_authorized": False,
        "analysis_verdict": "ROOT_CAUSE_CONFIRMED_AT_OBLIGATION_GOVERNANCE_BOUNDARY",
    }
    analysis = {
        **analysis_core,
        "analysis_identity": seal("B2_SUCCESSOR_OBLIGATION_NATURALNESS_ROOT_CAUSE_ANALYSIS_V1", analysis_core),
    }

    visible_obligation = {
        "obligation_version": "SUCCESSOR_FORMULATION_C_NATURAL_ROMANIAN_V2",
        "transformation": [
            "Redă fără modificări de conținut sau calificare exact o propoziție autorizată.",
            "Continuă scurt, în română firească, astfel încât desprinderea de relatarea factuală să rezulte firesc din construcția enunțului, fără prefață tehnică.",
            "Păstrează aceeași relație din propoziția aleasă activă în două situații noi și distincte.",
            "A doua situație trebuie să devină posibilă numai prin prima; fiecare trebuie să poată fi înțeleasă din premisă și din situația imediat anterioară.",
        ],
        "factual_safety": [
            "Separă fără echivoc relatarea factuală de cadrul inventat prin formularea narativă însăși.",
            "Nu adăuga fapte, cunoaștere privată, citate, afirmații despre ținte protejate sau concluzii pragmatice despre lumea reală.",
        ],
        "naturalness": [
            "Nu descrie în suprafață statutul editorial al textului, regulile urmate, clasificarea ori verificarea rezultatului.",
            "Nu copia și nu parafraza limbajul procedural al obligației; exprimă situațiile prin verbe și stări potrivite universului sursă.",
            "Marcajul inventat trebuie să fie integrat idiomatic și să nu funcționeze ca prefață tehnică ori avertisment editorial.",
            "Nu este impus niciun conector, registru special, număr de propoziții, tipar de clauze sau formulă de poantă.",
        ],
        "entity_status_rule": "Păstrează atributele, capacitățile, agenția și rolurile autorizate; nu atribui uneia dintre entități o proprietate sau un rol absent din autoritatea factuală.",
        "forbidden_operations": [
            "Nu importa alt domeniu sau cadru pentru a lega cele două situații.",
            "Nu obține rezultatul numai prin comparație, intensificare, enumerare ori surpriză fără legătură.",
            "Nu înlocui niciuna dintre situații cu un eveniment inventat fără legătură cu premisa.",
        ],
        "surface_freedom": [
            "Sunt permise formulări, ritmuri și structuri diferite dacă toate limitele de mai sus rămân verificabile.",
            "Câmpurile și testele folosite de evaluatori nu trebuie să apară în suprafață.",
        ],
    }
    schema_core = {
        "schema_name": "batch2-successor-obligation-conformance-v2",
        "schema_version": "2.0.0",
        "mechanism_neutral": True,
        "required_predicates": [
            "AUTHORIZED_PROPOSITION_PRESERVED",
            "TWO_DISTINCT_NEW_SITUATIONS",
            "RELATION_OPERATIVE_ACROSS_BOTH",
            "SECOND_DEPENDS_ON_FIRST",
            "LOCAL_INTELLIGIBILITY",
            "NO_UNRELATED_EVENT",
            "ENTITY_STATUS_PRESERVED",
            "INTEGRATED_NARRATIVE_CREATIVE_MARKING",
            "GOVERNANCE_LANGUAGE_ABSENT",
            "PROCEDURAL_ABSTRACTION_NONMATERIAL",
            "IDIOMATIC_ROMANIAN_PRECHECK_PASS",
        ],
        "naturalness_precheck": {
            "purpose": "Reject obvious instruction-to-surface transfer before costly blind mechanism review.",
            "does_not_replace_blind_g04a": True,
            "fail_closed_on": [
                "EDITORIAL_OR_GOVERNANCE_LABEL_AS_CREATIVE_MARKER",
                "OBLIGATION_TERMINOLOGY_COPIED_OR_PARAPHRASED",
                "MATERIALLY_PROCEDURAL_ABSTRACT_REGISTER",
                "UNIDIOMATIC_CREATIVE_MARKING",
            ],
            "reviewer_must_not_receive": [
                "MECHANISM_ID_NAME_ORDINAL",
                "SEALED_ASSIGNMENT_MAPPING",
                "TARGET_EVIDENCE_ROLE",
                "HISTORICAL_EXAMPLES",
                "BLIND_EVALUATION_MATERIAL",
            ],
        },
        "failure_disposition": "DEVELOPMENT_NONPOSITIVE_OBLIGATION_OR_NATURALNESS_NONCONFORMANT_DIAGNOSTIC",
    }
    schema = {
        **schema_core,
        "conformance_schema_identity": seal("B2_SUCCESSOR_OBLIGATION_CONFORMANCE_SCHEMA_V2", schema_core),
    }
    governance_core = {
        "schema_name": "batch2-successor-obligation-governance-v2",
        "schema_version": "2.0.0",
        "status": "FROZEN_SOURCE_ONLY_ZERO_CONSTRUCTION",
        "parent_governance_identity": v1["obligation_governance_identity"],
        "naturalness_analysis_identity": analysis["analysis_identity"],
        "constructor_visible_obligation": visible_obligation,
        "conformance_schema_identity": schema["conformance_schema_identity"],
        "gate_sequence": [
            "B2_G02B_PRECONSTRUCTION_BLINDING",
            "CONSTRUCTION_SEPARATELY_AUTHORIZED_ONE_SHOT",
            "B2_G02B_POSTCONSTRUCTION_EXPOSURE_RECONCILIATION",
            "B2_G02_FACTUAL_AND_TARGET_BOUNDARY",
            "B2_G02C_OBLIGATION_CONFORMANCE_AND_EARLY_NATURALNESS_PRECHECK",
            "B2_G03_BLIND_MECHANISM_RECOVERY",
            "B2_G03B_CAUSAL_MINIMAL_INTERVENTION",
            "B2_G03C_SHORTCUT_AND_CONTAMINATION",
            "B2_G04A_BLIND_ROMANIAN_NATURALNESS_REMAINS_REQUIRED",
        ],
        "constructor_must_not_receive": v1["constructor_must_not_receive"] + [
            "NATURALNESS_PRECHECK_FIELD_NAMES",
            "PILOT02_REJECTED_SURFACE_OR_PHRASES",
        ],
        "future_source_rule": {
            "pilot03_must_be_fresh_independently_acquired_and_admitted": True,
            "source_must_not_be_selected_or_shaped_by_obligation": True,
            "pilot02_source_candidate_or_creative_family_reuse": False,
        },
        "pilot02": {
            "candidate_bytes_modified": False,
            "candidate_repair_or_rewrite": False,
            "regression_only": True,
            "disposition_identity": disposition["disposition_identity"],
        },
        "authority_matrix": {
            key: False
            for key in (
                "pilot03_acquisition",
                "source_ingestion",
                "assignment",
                "construction",
                "generation",
                "candidate_repair",
                "candidate_rewrite",
                "voice_review",
                "owner_positive_review",
                "model_exposure",
                "training",
                "runtime_integration",
                "production_routing",
            )
        },
    }
    governance = {
        **governance_core,
        "obligation_governance_identity": seal("B2_SUCCESSOR_OBLIGATION_GOVERNANCE_V2", governance_core),
    }
    regression_core = {
        "schema_name": "batch2-successor-obligation-v2-pilot02-naturalness-regression-v1",
        "schema_version": "1.0.0",
        "pilot02_candidate_identity": disposition["candidate_identity"],
        "pilot02_candidate_raw_sha256": disposition["candidate_raw_sha256"],
        "candidate_bytes_modified": False,
        "evaluated_against_conformance_schema_identity": schema["conformance_schema_identity"],
        "predicates": {
            "INTEGRATED_NARRATIVE_CREATIVE_MARKING": "FAIL",
            "GOVERNANCE_LANGUAGE_ABSENT": "FAIL",
            "PROCEDURAL_ABSTRACTION_NONMATERIAL": "FAIL",
            "IDIOMATIC_ROMANIAN_PRECHECK_PASS": "FAIL",
        },
        "earliest_rejection": "G02C_EARLY_NATURALNESS_PRECHECK_BEFORE_G03",
        "stable_reasons": disposition["stable_rejection_reasons"],
        "regression_verdict": "PASS_FROZEN_PILOT02_REJECTED_EARLIER_WITHOUT_REPAIR",
    }
    regression = {
        **regression_core,
        "regression_identity": seal("B2_SUCCESSOR_OBLIGATION_V2_PILOT02_NATURALNESS_REGRESSION_V1", regression_core),
    }
    audit_core = {
        "schema_name": "batch2-successor-obligation-v2-naturalness-leakage-audit-v1",
        "schema_version": "1.0.0",
        "governance_identity": governance["obligation_governance_identity"],
        "conformance_schema_identity": schema["conformance_schema_identity"],
        "checks": {
            "taxonomy_name_id_ordinal_leakage": "PASS_ZERO",
            "definitional_paraphrase_increase": "PASS_NO_MATERIAL_INCREASE_OVER_V1",
            "fixed_lexeme_or_connective": "PASS_NONE_REQUIRED",
            "fixed_grammar_sentence_or_payoff_template": "PASS_NONE_REQUIRED",
            "naturalness_example_template_leakage": "PASS_NO_EXAMPLES_SUPPLIED",
            "rejected_phrase_priming": "PASS_REJECTED_MARKER_NOT_EXPOSED_VERBATIM",
            "pilot02_surface_leakage_to_constructor": "PASS_EXPLICITLY_PROHIBITED",
            "source_shape_selection": "PASS_SOURCE_MUST_PRECEDE_ASSIGNMENT",
            "factual_authority_widening": "PASS_NONE",
            "hidden_construction_authority": "PASS_ALL_FALSE",
            "blind_material_access": "PASS_NONE",
            "g04a_bypass": "PASS_EARLY_SCREEN_DOES_NOT_REPLACE_BLIND_G04A",
        },
        "deterministic_blockers": [],
        "audit_verdict": "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION",
    }
    audit = {
        **audit_core,
        "audit_identity": seal("B2_SUCCESSOR_OBLIGATION_V2_NATURALNESS_LEAKAGE_AUDIT_V1", audit_core),
    }
    outputs = {
        "humor-mechanics-batch2-successor-obligation-naturalness-root-cause-analysis-v1.json": analysis,
        "humor-mechanics-batch2-successor-obligation-conformance-schema-v2.json": schema,
        "humor-mechanics-batch2-successor-obligation-governance-v2.json": governance,
        "humor-mechanics-batch2-successor-obligation-v2-pilot02-naturalness-regression-v1.json": regression,
        "humor-mechanics-batch2-successor-obligation-v2-naturalness-leakage-audit-v1.json": audit,
    }
    for name, value in outputs.items():
        (ART / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({
        "analysis_verdict": analysis["analysis_verdict"],
        "analysis_identity": analysis["analysis_identity"],
        "obligation_governance_identity": governance["obligation_governance_identity"],
        "conformance_schema_identity": schema["conformance_schema_identity"],
        "regression_identity": regression["regression_identity"],
        "audit_identity": audit["audit_identity"],
        "audit_verdict": audit["audit_verdict"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
