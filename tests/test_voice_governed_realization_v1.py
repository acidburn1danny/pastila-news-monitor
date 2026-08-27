import hashlib
import json
from datetime import UTC, datetime

from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.voice_governed_realization_v1 import (
    PROGRAM_ID,
    PROMPT_IDENTITY,
    PROMPT_TEMPLATE,
    GovernedNumericRealizerV1,
)

SUMMARY = (
    "Programul Rabla Auto se redeschide pentru persoanele fizice. "
    "Administrația Fondului pentru Mediu pune la dispoziție peste 93 de milioane de lei."
)


def _realize(commentary):
    raw = json.dumps(
        {"decision": "commentary", "commentary": commentary}, ensure_ascii=False
    )
    return GovernedNumericRealizerV1(
        lambda prompt: (raw, "pastila-editor-core-v1.2-experimental")
    ).realize(program_id=PROGRAM_ID, factual_summary=SUMMARY)


def _realize_for_summary(commentary, summary):
    raw = json.dumps(
        {"decision": "commentary", "commentary": commentary}, ensure_ascii=False
    )
    return GovernedNumericRealizerV1(
        lambda prompt: (raw, "pastila-editor-core-v1.2-experimental")
    ).realize(program_id=PROGRAM_ID, factual_summary=summary)


def test_accepts_one_explicitly_nonfactual_coherent_passage():
    result = _realize(
        "În imaginația mea, pușculița tocmai și-a cerut loc de parcare. "
        "Dacă mai crește puțin, îi trebuie și număr de înmatriculare!"
    )

    assert result.commentary is not None
    assert result.receipt is not None
    assert result.receipt.validation_codes == (
        "exact_commentary_contract",
        "no_factual_overlap",
    )
    assert result.model_calls == result.provider_calls == result.model_loads == 1


def test_rejects_figures_currencies_and_literal_truncation():
    quantity = _realize(
        "În imaginația mea, pușculița are 93 de milioane de lei. "
        "Acum își caută garaj!"
    )
    truncated = _realize(
        "În imaginația mea, pușculița caută un garaj [...]. "
        "Probabil vrea și valet!"
    )

    assert quantity.commentary is None
    assert "factual_quantity_or_currency" in quantity.reason_code
    assert truncated.commentary is None
    assert "truncation_artifact" in truncated.reason_code


def test_accepts_story_specific_commentary_without_a_mandatory_opening_frame():
    result = _realize(
        "Răbdarea și-a primit, în sfârșit, propriul ghișeu. "
        "Orarul de lucru rămâne, firește, o surpriză!"
    )
    assert result.commentary is not None
    assert not result.commentary.startswith("În imaginația mea,")


def test_accepts_one_sentence_compressed_landing():
    result = _realize(
        "Răbdarea și-a primit propriul ghișeu, dar orarul rămâne surpriza casei."
    )
    assert result.commentary is not None


def test_rejects_factual_entity_reuse_and_summary_overlap():
    entity = _realize(
        "În imaginația mea, Rabla tocmai și-a comandat un covor roșu. "
        "Mai lipsește fotograful!"
    )
    overlap = _realize(
        "În imaginația mea, programul se redeschide pentru persoanele fizice. "
        "Apoi începe parada!"
    )

    assert entity.commentary is None
    assert "factual_entity_reuse" in entity.reason_code
    assert overlap.commentary is None
    assert "factual_paraphrase_overlap" in overlap.reason_code


def test_provider_failure_abstains_with_auditable_receipt():
    def fail(_prompt):
        raise RuntimeError("offline")

    result = GovernedNumericRealizerV1(fail).realize(
        program_id=PROGRAM_ID, factual_summary=SUMMARY
    )

    assert result.commentary is None
    assert result.reason_code == "governed_realizer_provider_failure"
    assert result.receipt is not None
    assert result.receipt.validation_codes == ("provider_failure",)


def test_explicit_governed_abstention_is_a_successful_auditable_outcome():
    raw = json.dumps(
        {"decision": "abstain", "reason_code": "SERIOUS_OR_SENSITIVE_SURFACE"}
    )
    result = GovernedNumericRealizerV1(
        lambda _prompt: (raw, "pastila-editor-core-v1.2-experimental")
    ).realize(program_id=PROGRAM_ID, factual_summary=SUMMARY)

    assert result.commentary is None
    assert result.reason_code == (
        "governed_realizer_abstained:SERIOUS_OR_SENSITIVE_SURFACE"
    )
    assert result.receipt is not None
    assert result.receipt.validation_codes == (
        "governed_abstention",
        "SERIOUS_OR_SENSITIVE_SURFACE",
    )


def test_markdown_fences_extra_keys_and_unknown_abstention_reasons_fail_closed():
    invalid = (
        '```json\n{"decision":"commentary","commentary":"text suficient de lung."}\n```',
        '{"decision":"commentary","commentary":"text", "extra":true}',
        '{"decision":"abstain","reason_code":"OTHER"}',
    )
    for raw in invalid:
        result = GovernedNumericRealizerV1(
            lambda _prompt, raw=raw: (
                raw,
                "pastila-editor-core-v1.2-experimental",
            )
        ).realize(program_id=PROGRAM_ID, factual_summary=SUMMARY)
        assert result.reason_code == "governed_realizer_validation_failed:invalid_json"


def test_sensitive_surfaces_require_governed_abstention():
    result = _realize_for_summary(
        "În imaginația mea, scena devine o sală de așteptare foarte tăcută. "
        "Până și ceasul preferă să nu facă glume!",
        "Cadavrul unui tânăr dispărut a fost găsit de doi ciobani.",
    )
    assert result.reason_code == (
        "governed_realizer_abstained:SERIOUS_OR_SENSITIVE_SURFACE"
    )
    assert result.model_calls == result.provider_calls == result.model_loads == 0
    assert result.receipt is not None
    assert result.receipt.validation_codes == (
        "policy_abstention",
        "SERIOUS_OR_SENSITIVE_SURFACE",
    )


def test_invented_speech_and_unsupported_intent_fail_closed():
    speech = _realize(
        "În imaginația mea, pușculița a spus «vreau și eu un garaj». "
        "Apoi a decis să plece în concediu!"
    )
    assert "invented_quotation_or_role_knowledge" in speech.reason_code
    assert "unsupported_causality_intent_or_status" in speech.reason_code


def test_repeated_opening_and_fiction_returning_as_fact_fail_closed():
    opening = _realize(
        "Dacă ar fi un film, ghișeul ar primi rolul principal. "
        "Cortina ar cădea înainte de pauză!"
    )
    factual_return = _realize(
        "Ca într-un film, ghișeul ar primi rolul principal. "
        "Dar aici e vorba de oameni care nu au primit ce li se cuvenea!"
    )
    assert "repeated_opening_attractor" in opening.reason_code
    assert "fiction_returns_as_unsupported_fact" in factual_return.reason_code


def test_other_programs_never_call_the_model():
    calls = []
    result = GovernedNumericRealizerV1(
        lambda prompt: calls.append(prompt)
    ).realize(program_id="NEL_DELAYED_QUANTITY_REVEAL_V1", factual_summary=SUMMARY)

    assert result.commentary is None
    assert result.model_calls == 0
    assert calls == []


def test_governed_prompt_identity_binds_exact_unpadded_template_bytes():
    assert PROMPT_TEMPLATE == PROMPT_TEMPLATE.strip()
    assert PROMPT_IDENTITY == "sha256:" + hashlib.sha256(
        PROMPT_TEMPLATE.encode("utf-8")
    ).hexdigest()


def test_full_rendered_governed_prompt_is_accepted_by_request_authority():
    prompt = PROMPT_TEMPLATE.format(factual_summary=SUMMARY)

    request = ApplicationRequestAuthorityV1().build(
        ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA,
            prompt,
            "voice-governed-realization:padding-regression",
            datetime(2026, 8, 25, 18, 0, tzinfo=UTC),
            TimeoutPolicyV2(timeout_seconds=120),
            CancellationTokenV2(cancellation_requested=False),
        )
    )

    assert prompt == prompt.strip()
    assert request.request_intent.request_units[0].messages[0].content == prompt
