"""Single content-addressed rendering and generation contract for Core V10."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

EDITORIAL_PROMPT_SHA256 = {
    "pastila-editor-core-v1.1-json-successor": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    "pastila-editor-core-v1.2-json-successor": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
}
OUTPUT_PROTOCOL = (
    "PROTOCOL STRUCTURAL OBLIGATORIU, CU PRIORITATE PENTRU FORMA RASPUNSULUI: "
    "returneaza exact un obiect JSON compact NFC UTF-8. Primul byte este { si "
    "ultimul byte este }, urmat imediat de EOS/EOF. Nu folosi Markdown, backticks, "
    "fence-uri, whitespace extern, explicatii, continuari sau al doilea obiect. "
    "Respecta exact schema, ordinea campurilor si identity-urile din cererea user."
)
GENERATION_POLICY = {
    "do_sample": False,
    "num_beams": 1,
    "repetition_penalty": "1.0",
    "max_new_tokens": 6268,
    "maximum_utf8_bytes": 6268,
    "eos_token": "TOKENIZER_EOS",
    "pad_token": "TOKENIZER_PAD_OR_EOS",
    "use_cache": True,
    "byte_ceiling_poll_tokens": 32,
}
PHASES = ("TRAINING", "DEVELOPMENT", "SHADOW_QUALIFICATION", "QUALIFICATION")
CONSUMER_ENTRYPOINTS = {
    "TRAINING": "render_training_messages",
    "DEVELOPMENT": "render_development_messages",
    "SHADOW_QUALIFICATION": "render_shadow_qualification_messages",
    "QUALIFICATION": "render_qualification_messages",
}


class ExecutionContractError(ValueError):
    pass


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compose_system_prompt(candidate: str, editorial_prompt: bytes) -> str:
    expected = EDITORIAL_PROMPT_SHA256.get(candidate)
    if expected is None or sha256(editorial_prompt) != expected:
        raise ExecutionContractError("editorial prompt authority mismatch")
    try:
        editorial = editorial_prompt.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ExecutionContractError("editorial prompt is not UTF-8") from exc
    return editorial + "\n\n" + OUTPUT_PROTOCOL


def render_messages(*, phase: str, candidate: str, editorial_prompt: bytes, user_prompt: str) -> tuple[dict[str, str], dict[str, str]]:
    if phase not in PHASES or type(user_prompt) is not str or not user_prompt or user_prompt != user_prompt.strip():
        raise ExecutionContractError("execution projection rejected")
    return (
        {"role": "system", "content": compose_system_prompt(candidate, editorial_prompt)},
        {"role": "user", "content": user_prompt},
    )


def render_training_messages(*, candidate: str, editorial_prompt: bytes, user_prompt: str):
    return render_messages(phase="TRAINING", candidate=candidate, editorial_prompt=editorial_prompt, user_prompt=user_prompt)


def render_development_messages(*, candidate: str, editorial_prompt: bytes, user_prompt: str):
    return render_messages(phase="DEVELOPMENT", candidate=candidate, editorial_prompt=editorial_prompt, user_prompt=user_prompt)


def render_shadow_qualification_messages(*, candidate: str, editorial_prompt: bytes, user_prompt: str):
    return render_messages(phase="SHADOW_QUALIFICATION", candidate=candidate, editorial_prompt=editorial_prompt, user_prompt=user_prompt)


def render_qualification_messages(*, candidate: str, editorial_prompt: bytes, user_prompt: str):
    return render_messages(phase="QUALIFICATION", candidate=candidate, editorial_prompt=editorial_prompt, user_prompt=user_prompt)


def projection_identity(messages: Sequence[Mapping[str, str]]) -> str:
    if tuple(tuple(row) for row in messages) != (("role", "content"), ("role", "content")):
        raise ExecutionContractError("message shape mismatch")
    return sha256(canonical(list(messages)))


def assert_phase_equivalence(*, candidate: str, editorial_prompt: bytes, user_prompt: str) -> str:
    projections = {
        phase: render_messages(phase=phase, candidate=candidate, editorial_prompt=editorial_prompt, user_prompt=user_prompt)
        for phase in PHASES
    }
    identities = {phase: projection_identity(messages) for phase, messages in projections.items()}
    if len(set(identities.values())) != 1:
        raise ExecutionContractError("phase projection divergence")
    return next(iter(identities.values()))


def contract_core() -> dict[str, object]:
    return {
        "schema": "pastila-production-core-unified-execution-contract",
        "schema_version": 10,
        "phases": list(PHASES),
        "consumer_entrypoints": CONSUMER_ENTRYPOINTS,
        "editorial_prompt_sha256": EDITORIAL_PROMPT_SHA256,
        "output_protocol_sha256": sha256(OUTPUT_PROTOCOL.encode()),
        "system_composition": "EDITORIAL_BYTES_UTF8 + LF_LF + OUTPUT_PROTOCOL",
        "message_shape": ["system", "user"],
        "chat_template": {"add_generation_prompt": True, "fix_mistral_regex": True},
        "generation_policy": GENERATION_POLICY,
        "post_generation_repair": False,
        "qualification_or_holdout_content_in_development": False,
        "fail_closed_on_any_projection_difference": True,
    }


def contract_identity() -> str:
    return sha256(canonical(contract_core()))


__all__ = [
    "CONSUMER_ENTRYPOINTS", "EDITORIAL_PROMPT_SHA256", "ExecutionContractError", "GENERATION_POLICY",
    "OUTPUT_PROTOCOL", "PHASES", "assert_phase_equivalence", "canonical",
    "compose_system_prompt", "contract_core", "contract_identity",
    "projection_identity", "render_development_messages", "render_messages",
    "render_qualification_messages", "render_shadow_qualification_messages",
    "render_training_messages", "sha256",
]
