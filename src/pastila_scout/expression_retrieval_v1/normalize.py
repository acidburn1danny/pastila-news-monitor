from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[^\w]+", re.UNICODE)


def retrieval_tokens_v1(*values: str) -> frozenset[str]:
    text = " ".join(values)
    normalized = unicodedata.normalize("NFC", text).casefold()
    return frozenset(token for token in _TOKEN_RE.split(normalized) if len(token) > 1)


def diacritic_insensitive_tokens_v1(*values: str) -> frozenset[str]:
    tokens = retrieval_tokens_v1(*values)
    return frozenset(
        "".join(
            character
            for character in unicodedata.normalize("NFD", token)
            if not unicodedata.combining(character)
        )
        for token in tokens
    )
