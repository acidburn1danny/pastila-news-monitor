"""Safe errors for generation request authority."""


class EditorGenerationAuthorityError(Exception):
    """Raised when generation authority cannot be reconstructed."""


__all__ = ("EditorGenerationAuthorityError",)
