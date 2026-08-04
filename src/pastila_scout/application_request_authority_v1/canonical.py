"""Deterministic semantics for one generic application generation request."""

from pastila_scout.provider_v2.canonical import semantic_sha256

_DOMAIN = "module-3.6-application-request-authority-v1"


def application_request_semantics(reference: str, prompt: str) -> dict[str, object]:
    """Return the complete provider-neutral application intent semantics."""
    return {
        "domain": _DOMAIN,
        "request_reference": reference,
        "prompt": prompt,
        "units": (
            {
                "ordinal": 0,
                "messages": ({"ordinal": 0, "role": "generation", "content": prompt},),
            },
        ),
    }


def application_request_seals(
    reference: str, prompt: str
) -> tuple[str, str, str, str, str, str]:
    """Derive stable plan, draft, request, and unit authority references."""
    semantics = application_request_semantics(reference, prompt)
    intent_hash = semantic_sha256(semantics)
    draft_hash = semantic_sha256(
        {"domain": f"{_DOMAIN}-draft", "reference": reference, "prompt": prompt}
    )
    plan_identity = f"scout:application-execution-plan-v1:{intent_hash}"
    plan_fingerprint = semantic_sha256(
        {
            "domain": f"{_DOMAIN}-plan-seal",
            "identity": plan_identity,
            "semantics": semantics,
        }
    )
    return (
        f"application-execution-plan-v1:{intent_hash}",
        plan_identity,
        plan_fingerprint,
        f"application-draft-v1:{draft_hash}",
        draft_hash,
        f"application-request-unit-v1:{intent_hash}",
    )


__all__ = ("application_request_seals", "application_request_semantics")
