"""Frozen allowlist for the eight-case deterministic Voice proof."""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.voice_deterministic_v2.models import (
    AbstentionReasonV1,
    MechanicIdV1,
)


@dataclass(frozen=True, slots=True)
class FrozenProofCaseV1:
    proof_id: str
    source_record_id: str
    mechanic_id: MechanicIdV1
    realization_program_id: str
    realization_program_sha256: str | None
    expected_output_sha256: str | None
    expected_abstention_reason: AbstentionReasonV1 | None
    repetition_signature: str


FROZEN_PROOF_CASES_V1: dict[str, FrozenProofCaseV1] = {
    "P1": FrozenProofCaseV1(
        "P1",
        "story-v1:30:07",
        MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
        "RP_P1_NUMERIC_EXPECTATION_LADDER_OWNER_V1",
        "cb229d2dbd275cabac0e2b4a5cd8750b912a9444faa286967f12ca14ee843433",
        "f398e2c4ae8aec87a645a0b2b8915b0420272873116d96d68dd4e84a02921dbc",
        None,
        "NUMERIC_EXPECTATION/APPROX_RON_37000/THREE_STEP_LADDER",
    ),
    "P2": FrozenProofCaseV1(
        "P2",
        "story-v1:31:04",
        MechanicIdV1.UNCERTAINTY_SANDWICHED_FICTION,
        "RP_P2_UNCERTAINTY_SANDWICHED_FICTION_OWNER_V1",
        "8fd6517f6b97c4a98a1f1d29c1ab4cfb7eacf928cd727f2d347acf442d35d6e0",
        "f52d37acf269324407441e9ffa670f48c1586eca7a5ac71f02a298d36a05ff8e",
        None,
        "UNCERTAINTY_SANDWICH/ACCIDENT_CAUSE_AND_OFFICER_REASON",
    ),
    "P3": FrozenProofCaseV1(
        "P3",
        "story-v1:29:06",
        MechanicIdV1.SUPPORTED_ROLE_REVERSAL,
        "RP_P3_SUPPORTED_ROLE_REVERSAL_OWNER_V1_1",
        "c464989253c84843a25006bc146a8dc7bf3a4fefcde6b86564a9be12bb1b7cca",
        "d4b542b8925b4734492f400820539dfc87951ca00618deedd521b7851af58cfc",
        None,
        "ROLE_REVERSAL/PROSECUTOR_TO_ACCUSED/FICTIONAL_ACTOR_ISOLATED",
    ),
    "P4": FrozenProofCaseV1(
        "P4",
        "story-v1:33:05",
        MechanicIdV1.BACKGROUND_CAPABILITY_EVENT_CONTRAST,
        "RP_P4_BACKGROUND_CAPABILITY_EVENT_CONTRAST_OWNER_V1_1",
        "ab6c0d64c6df0326901235a8e4c022782608500975f40288dee875da45fb62f3",
        "6dd95af7d6afc5fa1b903c7b818341e9bc65052242964edd73a7bebbf0c05ffa",
        None,
        "BACKGROUND_CONTRAST/US_CYBER_ORBIT/MINNESOTA_WATER_MANUAL_FALLBACK",
    ),
    "P5": FrozenProofCaseV1(
        "P5",
        "candidate-story-v2:25:02",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        "RP_P5_FICTIONAL_INTERFACE_OWNER_V1_1",
        "10266891d1b8cba642b9ccb948a3c4da51cdedb62dfa0802a1acca72b9b361a3",
        "4963fe666bea64d48f71a52d059c9b26ddad999538ca116c97fcf13bf4c226d9",
        None,
        "FICTIONAL_INTERFACE/COURIER_FRAUD/REVERSED_DELIVERY_FLOW",
    ),
    "P6": FrozenProofCaseV1(
        "P6",
        "candidate-story-v2:26:04",
        MechanicIdV1.PROCEDURAL_ESCALATION_TO_DOMAIN_METAPHOR,
        "RP_P6_PROCEDURAL_ESCALATION_DOMAIN_METAPHOR_OWNER_V1_1",
        "573a5dea26d398b74ca85252bee67fe187f8ee8b1aab136a0c28812e274c9035",
        "d75ca3067b9ae654a36d3626d2492a74ab447c14d28b6617241873269f8ce984",
        None,
        "PROCEDURAL_ESCALATION/AUDIOVISUAL_FINES_TO_LICENCE_WITHDRAWAL",
    ),
    "P7": FrozenProofCaseV1(
        "P7",
        "story-v1:32:07",
        MechanicIdV1.SUPPORTED_TERM_NONLITERALIZATION,
        "P7_AUTHORITY_DRIVEN_ABSTENTION_V1",
        None,
        None,
        AbstentionReasonV1.AMBIGUOUS_FACT_ATOM,
        "AUTHORITY_CONFLICT/SEPARATE_FUEL_REPORTS/NO_FLATTENING",
    ),
    "P8": FrozenProofCaseV1(
        "P8",
        "candidate-story-v2:25:04",
        MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        "P8_REPETITION_BUDGET_ABSTENTION_V1",
        None,
        None,
        AbstentionReasonV1.REPETITION_BUDGET_EXHAUSTED,
        "FICTIONAL_INTERFACE/SERVICE_ROLE/EPISODE_CEILING",
    ),
}

APPROVED_CALLBACK_IDS_V1 = frozenset(
    {
        "CALLBACK_CU_ATENTIE_SI_INGRIJORARE_V1",
        "Q9-CALLBACK-SCHIMB-DE-MAME-ROLE-EXCHANGE-V1",
        "CALLBACK_CYBERSECURITY_OFFLINE_ISOLATION_V1",
    }
)

APPROVED_NONLITERAL_MAPPING_IDS_V1 = frozenset(
    {
        "P2_PROOF_SPECIFIC_KICK_PARAPHRASE_BOUND_TO_P2-EF-02",
        "SCOATE_L_DIN_INTERNET_APPROVED",
        "ROLE_POSITION_CHANGED_BY_PREVENTIVE_ARREST",
    }
)

EVIDENCE_ONLY_STRUCTURE_IDS_V1 = frozenset(
    {
        "Q8",
        "EPISODIC_NONCAUSAL_CALLBACK_MODIFIER_V1",
    }
)


__all__ = [
    "APPROVED_CALLBACK_IDS_V1",
    "APPROVED_NONLITERAL_MAPPING_IDS_V1",
    "EVIDENCE_ONLY_STRUCTURE_IDS_V1",
    "FROZEN_PROOF_CASES_V1",
    "FrozenProofCaseV1",
]
