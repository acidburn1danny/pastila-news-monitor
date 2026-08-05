"""Safe errors for Editor generation runtime composition."""


class EditorGenerationRuntimeCompositionError(Exception):
    """Fixed application-owned runtime composition failure."""

    def __repr__(self) -> str:
        return f"EditorGenerationRuntimeCompositionError({str(self)!r})"


__all__ = ("EditorGenerationRuntimeCompositionError",)
