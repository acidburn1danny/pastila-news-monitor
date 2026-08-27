"""Production-authoritative reusable-program IR materialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pastila_scout.voice_eligibility_v2.library import PROGRAM_BY_ID_V1
from pastila_scout.voice_eligibility_v2.models import (
    AtomRoleBindingV1,
    EligibilityStatusV1,
    MechanicEligibilityClaimV1,
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2.models import AtomKind, VoiceFactAtomBundleV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    bundle_payload_identity,
    canonical_identity,
)

from .models import (
    IRSpanV1,
    ProductionAcidCommentaryIRV1_1,
    ProvenanceClassV1,
)

PRODUCTION_PROGRAM_LIBRARY_IDENTITY = (
    "sha256:8099c080958a29301c39cebfd7bc18c96f9892076f058accfdacdc5ba078f823"
)


@dataclass(frozen=True, slots=True)
class ProductionSurfaceV1:
    surface_id: str
    text: str
    provenance_class: ProvenanceClassV1
    permitted_programs: frozenset[str]
    retired: bool = False

    @property
    def utf8_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProductionProgramAuthorityV1:
    program_id: str
    mechanic_id: str
    required_atom_roles: tuple[str, ...]
    boundary_requirements: tuple[str, ...]
    surface_ids: tuple[str, ...]
    safe_parameterization: tuple[str, ...]
    prohibited_bindings: tuple[str, ...]
    cadence_signature: str
    sibling_equivalence_group: str
    repetition_signature: str
    episode_use_ceiling: int
    adjacent_same_mechanic_allowed: bool
    published_episode_cooldown: int
    abstention_conditions: tuple[str, ...]
    insertion_points: tuple[str, ...]
    expression_enrichment_compatible: bool


def _surface(surface_id, text, provenance, *programs, retired=False):
    return ProductionSurfaceV1(
        surface_id, text, provenance, frozenset(programs), retired
    )


_OP = ProvenanceClassV1.DETERMINISTIC_FORMATTING_OR_OPERATOR
_COMIC = ProvenanceClassV1.NONFACTUAL_COMIC_SURFACE
PRODUCTION_SURFACES_V1 = (
    _surface(
        "RF_HAI_SA_NE_IMAGINAM_PUTIN_SCENA_V1",
        "Hai să ne imaginăm puțin scena:",
        _OP,
        "FII_BOUNDED_INTAKE_DIALOGUE_V1",
        "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1",
    ),
    _surface(
        "RF_E_CA_SI_CUM_V1", "E ca și cum", _OP, "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1"
    ),
    _surface(
        "RF_PARCA_VAD_RECLAMA_V1",
        "Parcă văd reclama:",
        _OP,
        "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1",
    ),
    _surface(
        "RO_LA_BANII_ASTIA_V1",
        "La banii ăștia,",
        _OP,
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",
    ),
    _surface(
        "NC_IN_IMAGINATIA_MEA_VARIANTA_PREMIUM_V1",
        "în imaginația mea deja trecem la varianta premium.",
        _COMIC,
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",
    ),
    _surface(
        "NC_IN_CAPUL_MEU_NU_MAI_INCAPE_PE_ECRAN_V1",
        "în capul meu deja nu mai încape pe ecran.",
        _COMIC,
        "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1",
    ),
    _surface(
        "NC_IN_LUMEA_MEA_VARIANTA_DE_INCEPUT_V1",
        "în lumea mea eram încă la varianta de început.",
        _COMIC,
        "NEL_DELAYED_QUANTITY_REVEAL_V1",
    ),
    _surface(
        "NC_ASTEA_DOUA_NU_INCAP_IN_ACEEASI_PROPOZITIE_V1",
        "în mintea mea, astea două nici nu mai încap în aceeași propoziție.",
        _COMIC,
        "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1",
    ),
    _surface(
        "NC_INTAKE_CAT_DE_COMPLICAT_DA_V1",
        "„Bună ziua. Cu ce vă putem ajuta?”\n\n„E puțin complicat.”\n\n„Cât de complicat?”\n\n„Da!”",
        _COMIC,
        "FII_BOUNDED_INTAKE_DIALOGUE_V1",
    ),
    _surface(
        "NC_MENU_CE_URMEAZA_PARTEA_INTERESANTA_V1",
        "CE URMEAZĂ?\n\n□ Nimic special\n\n□ Vedem noi\n\n□ Se rezolvă\n\n☑ Aici începe partea interesantă",
        _COMIC,
        "FII_CLOSED_OPTION_MENU_V1",
    ),
    _surface(
        "NC_SERVICIUL_LASA_CA_VEDEM_V1",
        "SERVICIUL „LASĂ CĂ VEDEM”\n\nRapid.\nSimplu.\nFără complicații.\n\nRezultatul?\n\nAici se termină reclama.",
        _COMIC,
        "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1",
    ),
    _surface(
        "NC_WORKFLOW_START_STOP_NU_MAI_IMPROVIZAM_V1",
        "START\n\nTotul pare în regulă.\n\n↓\n\nÎncă pare în regulă.\n\n↓\n\nAici încep întrebările.\n\n↓\n\nSTOP\n\nDe aici nu mai improvizăm.",
        _COMIC,
        "FII_BOUNDED_SERVICE_WORKFLOW_V1",
    ),
    _surface(
        "NC_SCENA_TOT_NU_STIU_SFARSITUL_EPISODULUI_V1",
        "„Și acum ce facem?”\n\n„Nu știu.”\n\n„Perfect.”\n\nPauză.\n\n„Deci?”\n\n„Tot nu știu.”\n\nSfârșitul episodului.",
        _COMIC,
        "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1",
    ),
    _surface(
        "NC_ANALOGIE_CARTE_TOT_N_AM_AFLAT_NIMIC_V1",
        "ai deschide o carte la întâmplare, ai citi o pagină și ai spune:\n\n„Perfect. Tot n-am aflat nimic.”",
        _COMIC,
        "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1",
    ),
    _surface(
        "NC_ALTERNATIVE_LINGURA_SOSETA_NU_ALEGEM_V1",
        "Hai să inventăm, că aici avem loc: \n\nPoate s-a supărat o lingură pe o furculiță.\n\nPoate o șosetă a plecat să-și caute perechea.\n\nNu alegem niciuna.\nGATA! \n\nAm terminat cu invențiile.",
        _COMIC,
        "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1",
    ),
    _surface(
        "NC_LEDGER_STIM_NU_STIM_IMAGINATIA_DELOC_V1",
        "ȘTIM:\n...\n\nNU ȘTIM:\n...\nȘi aici imaginația ne ajuta fix deloc.\n\nGATA.",
        _COMIC,
        "USF_KNOWN_UNKNOWN_LEDGER_V1",
    ),
    _surface(
        "RF_PARCA_VAD_MENIUL_V1", "Parcă văd meniul:", _OP, "FII_CLOSED_OPTION_MENU_V1"
    ),
    _surface(
        "RF_PARCA_VAD_ASTA_INTR_UN_SHORT_V1",
        "Parcă văd asta într-un Short:",
        _OP,
        "FII_BOUNDED_SERVICE_WORKFLOW_V1",
    ),
    _surface(
        "RF_DAR_STRICT_CA_SCENETA_V1", "Dar, strict ca scenetă:", _OP, retired=True
    ),
)
PRODUCTION_SURFACE_BY_ID_V1 = {item.surface_id: item for item in PRODUCTION_SURFACES_V1}


class ProductionMaterializationError(ValueError):
    pass


_ROLE_LAYOUTS = {
    "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1": (
        "complete_quantity",
        "quantity_object",
    ),
    "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1": ("complete_quantity", "quantity_scope"),
    "NEL_DELAYED_QUANTITY_REVEAL_V1": ("quantity_object", "complete_quantity"),
    "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1": (
        "axis_a",
        "axis_b",
        "same_event_relationship",
    ),
    "FII_BOUNDED_INTAKE_DIALOGUE_V1": (
        "service_or_intake_role",
        "supported_incongruity",
    ),
    "FII_CLOSED_OPTION_MENU_V1": ("service_or_process", "supported_outcome"),
    "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1": (
        "service_or_process",
        "supported_outcome_or_limitation",
    ),
    "FII_BOUNDED_SERVICE_WORKFLOW_V1": ("start_condition", "outcome_or_status"),
    "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1": ("factual_anchor", "exact_target"),
    "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1": ("factual_anchor", "exact_target"),
    "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1": ("factual_anchor", "exact_target"),
    "USF_KNOWN_UNKNOWN_LEDGER_V1": ("known_anchor_a", "known_anchor_b", "exact_target"),
}

_PROGRAM_DETAIL = {
    "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1": (
        ("quantity_atom_id", "quantity_object_atom_id", "optional_purpose_atom_id"),
        ("topical_noun_substitution", "real_specification", "automatic_inflection"),
        "NUMERIC_EXPECTATION_CATEGORY_ESCALATION",
        (
            "incomplete_quantity",
            "unsafe_morphology",
            "value_judgment_risk",
            "repetition_exhausted",
        ),
    ),
    "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1": (
        (
            "primary_quantity_atom_id",
            "optional_secondary_quantity_atom_id",
            "event_object_atom_id",
        ),
        ("derived_statistic", "real_inventory_or_journey", "topical_noun_substitution"),
        "NUMERIC_EXPECTATION_SCALE_VISUALIZATION",
        (
            "ambiguous_quantity_relationship",
            "calculation_required",
            "unsafe_morphology",
            "repetition_exhausted",
        ),
    ),
    "NEL_DELAYED_QUANTITY_REVEAL_V1": (
        ("event_object_atom_id", "complete_quantity_atom_id"),
        ("invented_normal_value", "participant_expectation", "automatic_inflection"),
        "NUMERIC_EXPECTATION_DELAYED_REVEAL",
        (
            "incomplete_quantity",
            "benchmark_implication",
            "unsafe_morphology",
            "repetition_exhausted",
        ),
    ),
    "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1": (
        (
            "quantity_axis_a_atom_id",
            "quantity_axis_b_atom_id",
            "same_event_relationship_atom_id",
        ),
        (
            "division_average_total_conversion",
            "population_alignment_inference",
            "automatic_inflection",
        ),
        "NUMERIC_EXPECTATION_TWO_AXIS",
        (
            "not_exactly_two_axes",
            "ambiguous_same_event_relationship",
            "calculation_required",
            "repetition_exhausted",
        ),
    ),
    "FII_BOUNDED_INTAKE_DIALOGUE_V1": (
        ("intake_role_atom_id", "supported_incongruity_binding_id"),
        ("real_procedure", "open_dialogue_slot", "automatic_speaker_morphology"),
        "FICTIONAL_INTERFACE_INTAKE",
        (
            "unsupported_intake_role",
            "real_actor_ambiguity",
            "epistemic_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "FII_CLOSED_OPTION_MENU_V1": (
        ("service_or_process_atom_id", "supported_outcome_atom_id"),
        ("real_platform_copy", "harmful_option", "dynamic_option_generation"),
        "FICTIONAL_INTERFACE_CLOSED_MENU",
        (
            "real_interface_risk",
            "unsupported_outcome_binding",
            "epistemic_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1": (
        ("service_or_process_atom_id", "supported_outcome_or_limitation_atom_id"),
        (
            "real_entity_attribution",
            "dynamic_slogan",
            "automatic_service_name_derivation",
        ),
        "FICTIONAL_INTERFACE_ADVERTISEMENT",
        (
            "real_advertisement_risk",
            "unsupported_service_binding",
            "reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "FII_BOUNDED_SERVICE_WORKFLOW_V1": (
        ("supported_start_condition_atom_id", "supported_outcome_or_status_atom_id"),
        ("real_stage_assertion", "dynamic_stage_generation", "causal_connective"),
        "FICTIONAL_INTERFACE_SERVICE_WORKFLOW",
        (
            "chronology_inferred",
            "real_mechanism_risk",
            "causal_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1": (
        (
            "factual_anchor_atom_ids",
            "uncertainty_atom_id",
            "qualification_target_atom_id",
        ),
        ("real_actor_in_scene", "event_specific_invented_conduct", "generic_reset"),
        "UNCERTAINTY_FICTION_ISOLATED_SCENE",
        (
            "ambiguous_uncertainty_target",
            "identity_isolation_failure",
            "exact_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1": (
        (
            "event_anchor_atom_ids",
            "uncertainty_atom_id",
            "qualification_target_atom_id",
        ),
        (
            "plausible_event_hypothesis",
            "unbound_background_premise",
            "automatic_comparison_grammar",
        ),
        "UNCERTAINTY_FICTION_ANALOGY_DETOUR",
        (
            "analogy_domain_too_close",
            "background_authority_missing",
            "exact_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1": (
        (
            "event_anchor_atom_ids",
            "uncertainty_atom_id",
            "qualification_target_atom_id",
        ),
        (
            "plausible_alternative",
            "real_person_or_institution",
            "event_noun_in_alternative",
        ),
        "UNCERTAINTY_FICTION_ABSURD_ALTERNATIVES",
        (
            "plausible_alternative",
            "unknown_target_ambiguous",
            "exact_reset_unavailable",
            "repetition_exhausted",
        ),
    ),
    "USF_KNOWN_UNKNOWN_LEDGER_V1": (
        (
            "known_anchor_atom_ids",
            "uncertainty_atom_id",
            "qualification_target_atom_id",
        ),
        ("answer_suggestion", "official_status_imitation", "causal_ordering"),
        "UNCERTAINTY_FICTION_KNOWN_UNKNOWN_LEDGER",
        (
            "fewer_than_two_known_atoms",
            "unknown_target_ambiguous",
            "parallel_grammar_unsafe",
            "repetition_exhausted",
        ),
    ),
}


def _production_program_authority(program_id: str) -> ProductionProgramAuthorityV1:
    spec = PROGRAM_BY_ID_V1[program_id]
    safe, prohibited, sibling, abstain = _PROGRAM_DETAIL[program_id]
    return ProductionProgramAuthorityV1(
        program_id=program_id,
        mechanic_id=spec.mechanic_id.value,
        required_atom_roles=_ROLE_LAYOUTS[program_id],
        boundary_requirements=spec.required_boundary_codes,
        surface_ids=spec.surface_ids,
        safe_parameterization=safe,
        prohibited_bindings=prohibited,
        cadence_signature=spec.cadence_signature,
        sibling_equivalence_group=sibling,
        repetition_signature=f"{spec.mechanic_id.value}/{program_id}/{spec.cadence_signature}",
        episode_use_ceiling=spec.episode_use_ceiling,
        adjacent_same_mechanic_allowed=False,
        published_episode_cooldown=2,
        abstention_conditions=abstain,
        insertion_points=("between_governed_spans", "commentary_conclusion"),
        expression_enrichment_compatible=True,
    )


PRODUCTION_PROGRAMS_V1 = tuple(
    _production_program_authority(spec.program_id) for spec in PROGRAM_BY_ID_V1.values()
)
PRODUCTION_PROGRAM_BY_ID_V1 = {item.program_id: item for item in PRODUCTION_PROGRAMS_V1}


def _canonical_sha(value) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _program_sha(program_id: str) -> str:
    authority = PRODUCTION_PROGRAM_BY_ID_V1[program_id]
    return _canonical_sha(
        {
            "authority": {
                field: getattr(authority, field)
                for field in authority.__dataclass_fields__
            },
            "library_identity": PRODUCTION_PROGRAM_LIBRARY_IDENTITY,
        }
    )


def _validate_governance(*, bundle, eligibility, selection, snapshot, program_id):
    def sealed(value, field):
        return canonical_identity(
            value.model_copy(update={field: "sha256:" + "0" * 64})
        )

    if bundle.bundle_identity != bundle_payload_identity(bundle):
        raise ProductionMaterializationError("stale fact atom bundle")
    if eligibility.result_identity != sealed(eligibility, "result_identity"):
        raise ProductionMaterializationError("stale eligibility result")
    if selection.receipt_identity != sealed(selection, "receipt_identity"):
        raise ProductionMaterializationError("stale selection receipt")
    if snapshot.snapshot_identity != sealed(snapshot, "snapshot_identity"):
        raise ProductionMaterializationError("stale repetition snapshot")
    if eligibility.fact_atom_bundle_identity != bundle.bundle_identity:
        raise ProductionMaterializationError("stale eligibility result")
    if eligibility.repetition_snapshot_identity != snapshot.snapshot_identity:
        raise ProductionMaterializationError("stale repetition snapshot")
    if selection.selection_kind is not SelectionKindV1.PROGRAM:
        raise ProductionMaterializationError("owner selected no commentary")
    if selection.eligibility_result_identity != eligibility.result_identity:
        raise ProductionMaterializationError("stale selection receipt")
    candidate = next(
        (
            x
            for x in eligibility.shortlist
            if x.candidate_id == selection.selected_candidate_id
        ),
        None,
    )
    if candidate is None or candidate.program_id != program_id:
        raise ProductionMaterializationError("selected program mismatch")
    outcome = next(
        (x for x in eligibility.program_outcomes if x.subject_id == program_id), None
    )
    if outcome is None or outcome.status is not EligibilityStatusV1.ELIGIBLE:
        raise ProductionMaterializationError("program is not eligible")
    spec = PROGRAM_BY_ID_V1[program_id]
    if (
        candidate.mechanic_id is not spec.mechanic_id
        or candidate.cadence_signature != spec.cadence_signature
        or candidate.surface_ids != spec.surface_ids
    ):
        raise ProductionMaterializationError("program candidate authority mismatch")
    return candidate


def _validated_atoms(bundle, program_id, atom_roles):
    expected = _ROLE_LAYOUTS.get(program_id)
    if expected is None:
        raise ProductionMaterializationError("unknown production program")
    by_role = {item.role: item.atom_ids for item in atom_roles}
    if tuple(by_role) != expected or any(len(by_role[role]) != 1 for role in expected):
        raise ProductionMaterializationError("atom role pattern mismatch")
    atoms = {item.atom_id: item for item in bundle.atoms}
    try:
        selected = {role: atoms[by_role[role][0]] for role in expected}
    except KeyError as exc:
        raise ProductionMaterializationError("unknown participating atom") from exc
    for role, atom in selected.items():
        if atom.proposition not in {item.passage for item in atom.evidence}:
            raise ProductionMaterializationError(
                "grammatical placement requires exact authority surface"
            )
        quantity_role = role in {"complete_quantity", "axis_a", "axis_b"}
        boundary_role = role == "exact_target"
        if quantity_role and atom.kind is not AtomKind.COMPLETE_QUANTITY:
            raise ProductionMaterializationError("wrong atom role")
        if boundary_role and atom.kind not in {
            AtomKind.ALLEGATION_STATUS,
            AtomKind.UNCERTAINTY_STATUS,
            AtomKind.CAUSAL_BOUNDARY,
            AtomKind.NEGATIVE_BOUNDARY,
        }:
            raise ProductionMaterializationError("wrong boundary atom role")
        if (
            not quantity_role
            and not boundary_role
            and atom.kind is not AtomKind.EVENT_PROPOSITION
        ):
            raise ProductionMaterializationError("wrong event atom role")
    if "exact_target" in selected:
        boundary = selected["exact_target"]
        anchors = {
            atom.atom_id for role, atom in selected.items() if role != "exact_target"
        }
        if not anchors.intersection(boundary.qualification_target_atom_ids):
            raise ProductionMaterializationError("qualification target mismatch")
    return selected


def materialize_production_ir_v1_1(
    *,
    story_binding,
    bundle: VoiceFactAtomBundleV1,
    eligibility: VoiceEligibilityResultV1,
    mechanic_claim: MechanicEligibilityClaimV1,
    selection: VoiceOwnerSelectionReceiptV1,
    repetition_snapshot: VoiceRepetitionSnapshotV1,
    atom_roles: tuple[AtomRoleBindingV1, ...],
    activation_policy_identity: str,
    renderer_identity: str,
    relationship_binding_identities: tuple[str, ...] = (),
    expression_selection=None,
) -> ProductionAcidCommentaryIRV1_1:
    if (
        expression_selection is not None
        and expression_selection.selection_kind.value != "none"
    ):
        raise ProductionMaterializationError("expression activation is zero")
    expression_receipt_identity = (
        expression_selection.receipt_identity
        if expression_selection is not None
        else None
    )
    program_id = next(
        (
            x.program_id
            for x in eligibility.shortlist
            if x.candidate_id == selection.selected_candidate_id
        ),
        "",
    )
    if program_id not in PROGRAM_BY_ID_V1:
        raise ProductionMaterializationError("unknown production program")
    candidate = _validate_governance(
        bundle=bundle,
        eligibility=eligibility,
        selection=selection,
        snapshot=repetition_snapshot,
        program_id=program_id,
    )
    spec = PROGRAM_BY_ID_V1[program_id]
    if (
        mechanic_claim.fact_atom_bundle_identity != bundle.bundle_identity
        or mechanic_claim.mechanic_id is not spec.mechanic_id
        or mechanic_claim.atom_roles != atom_roles
        or mechanic_claim.claim_identity
        != canonical_identity(
            mechanic_claim.model_copy(update={"claim_identity": "sha256:" + "0" * 64})
        )
    ):
        raise ProductionMaterializationError("mechanic claim binding mismatch")
    atoms = _validated_atoms(bundle, program_id, atom_roles)
    surfaces = []
    for surface_id in spec.surface_ids:
        surface = PRODUCTION_SURFACE_BY_ID_V1.get(surface_id)
        if (
            surface is None
            or surface.retired
            or program_id not in surface.permitted_programs
        ):
            raise ProductionMaterializationError("unavailable or retired surface")
        surfaces.append(surface)

    ordered_atoms = [atoms[role] for role in _ROLE_LAYOUTS[program_id]]
    # Only the frozen double-newline layout joins exact, independently governed spans.
    pieces: list[IRSpanV1] = []

    def append(text, provenance, identity):
        if pieces:
            pieces.append(
                IRSpanV1(
                    text="\n\n",
                    provenance_class=_OP,
                    source_identity="FORMAT_DOUBLE_NEWLINE_V1",
                )
            )
        pieces.append(
            IRSpanV1(text=text, provenance_class=provenance, source_identity=identity)
        )

    if program_id.startswith("USF_"):
        for atom in ordered_atoms[:-1]:
            append(
                atom.proposition,
                ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
                atom.atom_id,
            )
        boundary = ordered_atoms[-1]
        append(
            boundary.proposition,
            ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
            boundary.atom_id,
        )
        for surface in surfaces:
            append(surface.text, surface.provenance_class, surface.surface_id)
        append(
            boundary.proposition,
            ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
            boundary.atom_id,
        )
    else:
        for atom in ordered_atoms:
            append(
                atom.proposition,
                ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM,
                atom.atom_id,
            )
        for surface in surfaces:
            append(surface.text, surface.provenance_class, surface.surface_id)
    output = "".join(span.text for span in pieces).encode("utf-8")
    return ProductionAcidCommentaryIRV1_1(
        semantic_draft_revision_identity=story_binding.semantic_draft_revision_identity,
        event_id=story_binding.event_id,
        story_position=bundle.story_position,
        fact_atom_bundle_identity=bundle.bundle_identity,
        mechanic_id=spec.mechanic_id,
        mechanic_eligibility_claim_identity=mechanic_claim.claim_identity,
        realization_program_id=program_id,
        realization_program_sha256=_program_sha(program_id),
        program_eligibility_identity=eligibility.result_identity,
        program_selection_receipt_identity=selection.receipt_identity,
        selected_program_candidate_identity=candidate.candidate_id,
        atom_role_bindings=tuple((item.role, item.atom_ids) for item in atom_roles),
        relationship_binding_identities=relationship_binding_identities,
        expression_selection_receipt_identity=expression_receipt_identity,
        repetition_snapshot_identity=repetition_snapshot.snapshot_identity,
        activation_policy_identity=activation_policy_identity,
        renderer_identity=renderer_identity,
        spans=tuple(pieces),
        repetition_signature=candidate.repetition_signature,
        expected_output_sha256=hashlib.sha256(output).hexdigest(),
    )


__all__ = [
    "PRODUCTION_PROGRAMS_V1",
    "PRODUCTION_PROGRAM_BY_ID_V1",
    "PRODUCTION_PROGRAM_LIBRARY_IDENTITY",
    "PRODUCTION_SURFACES_V1",
    "PRODUCTION_SURFACE_BY_ID_V1",
    "ProductionMaterializationError",
    "ProductionProgramAuthorityV1",
    "ProductionSurfaceV1",
    "materialize_production_ir_v1_1",
]
