"""Safe application-owned request-authority failures."""


class ApplicationRequestAuthorityError(RuntimeError):
    """Reject invalid application intent or lower authority construction."""


__all__ = ("ApplicationRequestAuthorityError",)
