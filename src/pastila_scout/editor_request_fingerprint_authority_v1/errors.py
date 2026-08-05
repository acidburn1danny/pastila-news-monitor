"""Safe public error for Editor request fingerprint authority."""


class EditorRequestFingerprintAuthorityError(Exception):
    """Raised when request fingerprint authority cannot be established."""


__all__ = ("EditorRequestFingerprintAuthorityError",)
