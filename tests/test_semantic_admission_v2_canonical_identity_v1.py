from __future__ import annotations

import hashlib

from pastila_scout.semantic_admission_v2.canonical_identity_v1 import canonical_bytes, canonical_identity


def test_canonical_identity_preserves_compact_sorted_utf8_newline_algorithm() -> None:
    value = {"z": "țară", "a": [2, 1]}
    expected = b'{"a":[2,1],"z":"\xc8\x9bar\xc4\x83"}\n'
    assert canonical_bytes(value) == expected
    assert canonical_identity(value) == "sha256:" + hashlib.sha256(expected).hexdigest()


def test_canonical_identity_is_mapping_order_independent() -> None:
    assert canonical_identity({"b": 2, "a": 1}) == canonical_identity({"a": 1, "b": 2})
