"""CLI-safe provider-run failures."""


class ProviderRunCLIError(RuntimeError):
    """Report a fixed application composition or execution failure."""


__all__ = ("ProviderRunCLIError",)
