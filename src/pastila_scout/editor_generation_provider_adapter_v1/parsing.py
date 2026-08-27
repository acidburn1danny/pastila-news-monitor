"""Sole strict JSON-mode validation boundary."""

from pydantic import BaseModel, ValidationError

from pastila_scout.editor.generation.provider import ProviderStructuredOutputError

_MALFORMED = "MALFORMED_JSON: Provider returned malformed structured output."
_SCHEMA = "SCHEMA_VALIDATION_FAILED: Provider returned structured output that failed schema validation."


def validate_generated_model[T: BaseModel](text: str, schema: type[T]) -> T:
    outcome, value, detail = _validate(text, schema)
    del text, schema
    if outcome == "success":
        return value
    del value
    message = _MALFORMED if outcome == "malformed" else _SCHEMA
    error = ProviderStructuredOutputError(f"{message} {detail}"[:600])
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


def _validate[T: BaseModel](
    text: object, schema: object
) -> tuple[str, T | None, str]:
    try:
        return "success", schema.model_validate_json(text, strict=True), ""
    except ValidationError as raw:
        details = raw.errors(
            include_url=False, include_context=False, include_input=False
        )
        malformed = len(details) == 1 and details[0].get("type") == "json_invalid"
        detail = "; ".join(
            f"{item.get('type', 'validation_error')}@{'.'.join(map(str, item.get('loc', ()))) or '$'}"
            for item in details[:8]
        )[:400]
        del raw, details, text, schema
        return ("malformed" if malformed else "schema"), None, detail
    except Exception:  # noqa: BLE001
        del text, schema
        return "schema", None, "unexpected_validation_error@$"


__all__: tuple[str, ...] = ()
