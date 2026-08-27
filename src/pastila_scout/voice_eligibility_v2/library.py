"""Closed reusable-program eligibility metadata frozen for Voice V2."""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.voice_deterministic_v2.models import MechanicIdV1

PROGRAM_LIBRARY_SHA256 = (
    "sha256:8099c080958a29301c39cebfd7bc18c96f9892076f058accfdacdc5ba078f823"
)


@dataclass(frozen=True, slots=True)
class ProgramEligibilitySpecV1:
    program_id: str
    mechanic_id: MechanicIdV1
    minimum_event_propositions: int
    minimum_complete_quantities: int
    requires_boundary_atom: bool
    required_boundary_codes: tuple[str, ...]
    surface_ids: tuple[str, ...]
    cadence_signature: str
    episode_use_ceiling: int = 1


def _spec(program_id, mechanic, props, quantities, boundary, codes, surfaces, cadence):
    return ProgramEligibilitySpecV1(
        program_id,
        mechanic,
        props,
        quantities,
        boundary,
        tuple(codes),
        tuple(surfaces),
        cadence,
    )


PROGRAM_SPECS_V1 = (
    _spec(
        "FII_BOUNDED_INTAKE_DIALOGUE_V1",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        2,
        0,
        False,
        ("no_real_actor_projection", "no_real_quote", "preserve_epistemic_status"),
        ("RF_HAI_SA_NE_IMAGINAM_PUTIN_SCENA_V1", "NC_INTAKE_CAT_DE_COMPLICAT_DA_V1"),
        "fiction_marker/intake_question/requester_answer/incongruity_close",
    ),
    _spec(
        "FII_BOUNDED_SERVICE_WORKFLOW_V1",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        2,
        0,
        False,
        ("no_inferred_chronology", "no_real_mechanism", "preserve_causal_unknown"),
        (
            "RF_PARCA_VAD_ASTA_INTR_UN_SHORT_V1",
            "NC_WORKFLOW_START_STOP_NU_MAI_IMPROVIZAM_V1",
        ),
        "fiction_marker/stage_1/stage_2/event_contradiction_stage/result/reset",
    ),
    _spec(
        "FII_CLOSED_OPTION_MENU_V1",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        2,
        0,
        False,
        ("no_institutional_intent", "no_operational_guidance", "no_real_interface"),
        ("RF_PARCA_VAD_MENIUL_V1", "NC_MENU_CE_URMEAZA_PARTEA_INTERESANTA_V1"),
        "fiction_marker/menu_title/ordinary_options/selected_incongruity/factual_close",
    ),
    _spec(
        "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        2,
        0,
        False,
        ("no_real_brand", "no_real_promise_or_guarantee", "preserve_epistemic_status"),
        ("RF_PARCA_VAD_RECLAMA_V1", "NC_SERVICIUL_LASA_CA_VEDEM_V1"),
        "fiction_marker/ad_identity/promise_sequence/limitation_or_reversal/factual_reset",
    ),
    _spec(
        "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1",
        MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        1,
        1,
        False,
        ("no_arithmetic_conversion_ratio_or_average", "no_real_physical_display_claim"),
        ("NC_IN_CAPUL_MEU_NU_MAI_INCAPE_PE_ECRAN_V1",),
        "quantity_beats/accumulation_pause/fictional_scale_image",
    ),
    _spec(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",
        MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        1,
        1,
        False,
        (
            "no_value_judgment",
            "preserve_approximation_attribution_period_denominator_scope",
        ),
        ("RO_LA_BANII_ASTIA_V1", "NC_IN_IMAGINATIA_MEA_VARIANTA_PREMIUM_V1"),
        "quantity_anchor/category_shift/fictional_upgrade/boundary",
    ),
    _spec(
        "NEL_DELAYED_QUANTITY_REVEAL_V1",
        MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        1,
        1,
        False,
        ("fiction_is_not_real_benchmark", "no_normative_quantity_judgment"),
        ("NC_IN_LUMEA_MEA_VARIANTA_DE_INCEPUT_V1",),
        "object_open/fictional_low_scale/pause/exact_quantity_reveal",
    ),
    _spec(
        "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1",
        MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        1,
        2,
        False,
        ("axes_remain_separate", "no_causality_equivalence_or_derived_value"),
        ("NC_ASTEA_DOUA_NU_INCAP_IN_ACEEASI_PROPOZITIE_V1",),
        "axis_a/axis_b/alternating_recall/fictional_contrast_close",
    ),
    _spec(
        "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1",
        MechanicIdV1.UNCERTAINTY_SANDWICHED_FICTION,
        1,
        0,
        True,
        ("all_alternatives_impossible_or_absurd", "byte_exact_reset", "none_selected"),
        ("NC_ALTERNATIVE_LINGURA_SOSETA_NU_ALEGEM_V1",),
        "uncertainty/frame_open/alternative_a/alternative_b/escalation/no_selection/exact_reset",
    ),
    _spec(
        "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1",
        MechanicIdV1.UNCERTAINTY_SANDWICHED_FICTION,
        1,
        0,
        True,
        (
            "byte_exact_reset",
            "distinct_analogy_domain",
            "no_event_actor_or_unknown_slot_in_analogy",
        ),
        ("RF_E_CA_SI_CUM_V1", "NC_ANALOGIE_CARTE_TOT_N_AM_AFLAT_NIMIC_V1"),
        "uncertainty/analogy_departure/distinct_domain_scene/return/exact_reset",
    ),
    _spec(
        "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1",
        MechanicIdV1.UNCERTAINTY_SANDWICHED_FICTION,
        1,
        0,
        True,
        (
            "byte_exact_uncertainty_reset",
            "fictional_actor_identity_isolation",
            "no_plausible_explanation",
        ),
        (
            "RF_HAI_SA_NE_IMAGINAM_PUTIN_SCENA_V1",
            "NC_SCENA_TOT_NU_STIU_SFARSITUL_EPISODULUI_V1",
        ),
        "anchor/uncertainty/frame_open/scene/frame_close/exact_reset",
    ),
    _spec(
        "USF_KNOWN_UNKNOWN_LEDGER_V1",
        MechanicIdV1.UNCERTAINTY_SANDWICHED_FICTION,
        2,
        0,
        True,
        (
            "byte_exact_reset",
            "known_atoms_not_synthesized",
            "unknown_slot_remains_empty",
        ),
        ("NC_LEDGER_STIM_NU_STIM_IMAGINATIA_DELOC_V1",),
        "known_a/known_b/unknown_slot/comic_absence_label/exact_reset",
    ),
)

PROGRAM_BY_ID_V1 = {item.program_id: item for item in PROGRAM_SPECS_V1}
REUSABLE_MECHANICS_V1 = frozenset(item.mechanic_id for item in PROGRAM_SPECS_V1)

__all__ = [
    "PROGRAM_BY_ID_V1",
    "PROGRAM_LIBRARY_SHA256",
    "PROGRAM_SPECS_V1",
    "REUSABLE_MECHANICS_V1",
    "ProgramEligibilitySpecV1",
]
