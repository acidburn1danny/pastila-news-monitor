"""Private contracts for future explicit request-context authorities."""

from datetime import datetime
from typing import Protocol


class _SmokeExecutionRequestIdentitySourceV2(Protocol):  # noqa: PYI046
    def get_execution_request_id(self) -> str: ...


class _SmokeExecutionTimestampSourceV2(Protocol):  # noqa: PYI046
    def get_requested_at(self) -> datetime: ...


__all__: tuple[str, ...] = ()
