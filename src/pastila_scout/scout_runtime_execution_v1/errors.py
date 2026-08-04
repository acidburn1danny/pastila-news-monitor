"""Application-owned failures for the opt-in Scout execution bridge."""


class ScoutRuntimeExecutionError(RuntimeError):
    """The opt-in Scout provider-neutral execution path failed."""


__all__ = ("ScoutRuntimeExecutionError",)
