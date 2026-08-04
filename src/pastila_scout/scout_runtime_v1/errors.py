"""Application-owned errors for inert Scout runtime composition."""


class ScoutRuntimeCompositionError(RuntimeError):
    """The injected Scout runtime composition is invalid."""


__all__ = ("ScoutRuntimeCompositionError",)
