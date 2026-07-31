"""Stable public validation failures for Module 2.9."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainValidationIssue:
    """Machine-readable validation issue independent of Pydantic internals."""

    code: str
    artifact_reference: str
    field_reference: str | None = None
    artifact_type: str | None = None
    field_path: tuple[str | int, ...] = ()
    related_references: tuple[str, ...] = ()
    message_key: str | None = None


class DomainValidationError(Exception):
    """Public aggregate validation error with stable structured issues."""

    def __init__(self, issues: tuple[DomainValidationIssue, ...]):
        self.issues = issues
        super().__init__(",".join(issue.code for issue in issues))


__all__ = ("DomainValidationError", "DomainValidationIssue")
