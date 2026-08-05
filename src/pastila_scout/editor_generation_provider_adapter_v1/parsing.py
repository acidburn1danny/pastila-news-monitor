"""Sole strict JSON-mode validation boundary."""

from pydantic import BaseModel, ValidationError

from pastila_scout.editor.generation.provider import ProviderStructuredOutputError

_MALFORMED = "Provider returned malformed structured output."
_SCHEMA = "Provider returned structured output that failed schema validation."


def validate_generated_model[T: BaseModel](text: str, schema: type[T]) -> T:
    outcome, value = _validate(text, schema)
    del text, schema
    if outcome == "success":
        return value
    del value
    error = ProviderStructuredOutputError(
        _MALFORMED if outcome == "malformed" else _SCHEMA
    )
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


def _validate[T: BaseModel](text: object, schema: object) -> tuple[str, T | None]:
    try:
        return "success", schema.model_validate_json(text, strict=True)
    except ValidationError as raw:
        details = raw.errors(
            include_url=False, include_context=False, include_input=False
        )
        malformed = len(details) == 1 and details[0].get("type") == "json_invalid"
        del raw, details, text, schema
        return ("malformed" if malformed else "schema"), None
    except Exception:  # noqa: BLE001
        del text, schema
        return "schema", None


__all__: tuple[str, ...] = ()
