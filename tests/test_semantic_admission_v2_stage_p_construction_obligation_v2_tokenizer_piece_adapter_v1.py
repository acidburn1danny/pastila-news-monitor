from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_CONFIGURATION, DECODER_IDENTITY, DECODER_MECHANISM_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY,
    SPECIAL_TOKEN_IDS, TOKENIZER_IDENTITY, TOKENIZER_IMPLEMENTATION,
    TOKENIZERS_NATIVE_SHA256, TOKENIZERS_PYTHON_WRAPPER_IDENTITY,
    TOKENIZERS_VERSION,
    TRANSFORMERS_VERSION, VOCABULARY_SIZE, TokenizerRuntimeIdentityV1,
    extract_identity_bound_token_pieces_v1,
)


class ByteLevel:
    __module__ = "tokenizers.decoders"
    def __getstate__(self):
        import json
        return json.dumps(DECODER_CONFIGURATION)


class TokenizersBackend:
    __module__ = "transformers.tokenization_utils_tokenizers"
    eos_token_id = EOS_TOKEN_ID
    all_special_ids = tuple(sorted(SPECIAL_TOKEN_IDS))
    decoder = ByteLevel()

    def __init__(self) -> None:
        self.decode_calls = 0

    def __len__(self) -> int:
        return VOCABULARY_SIZE

    def decode(self, token_ids, *, skip_special_tokens, clean_up_tokenization_spaces):
        self.decode_calls += 1
        assert skip_special_tokens is True
        assert clean_up_tokenization_spaces is False
        def piece(token_id):
            if token_id == 12:
                return "\x00"
            return "" if token_id in SPECIAL_TOKEN_IDS else chr(0x20 + token_id % 90)
        return "".join(piece(token_id) for token_id in token_ids)


def identity() -> TokenizerRuntimeIdentityV1:
    return TokenizerRuntimeIdentityV1(
        TOKENIZER_IDENTITY, DECODER_IDENTITY, TRANSFORMERS_VERSION,
        TOKENIZER_IMPLEMENTATION, VOCABULARY_SIZE, EOS_TOKEN_ID,
        tuple(sorted(SPECIAL_TOKEN_IDS)), PROJECTOR_FREEZE_IDENTITY,
    )


def extract(tokenizer, runtime_identity=None):
    return extract_identity_bound_token_pieces_v1(
        tokenizer=tokenizer, identity=runtime_identity or identity(),
        canonical_tokenizer_type=type(tokenizer),
        canonical_decoder_type=type(tokenizer.decoder),
        tokenizers_version=TOKENIZERS_VERSION,
        native_extension_path="/runtime/tokenizers/tokenizers.abi3.so",
        native_extension_sha256=TOKENIZERS_NATIVE_SHA256,
        python_wrapper_identity=TOKENIZERS_PYTHON_WRAPPER_IDENTITY)


@pytest.mark.parametrize("field,value", [
    ("tokenizer_identity", "sha256:" + "0" * 64),
    ("decoder_identity", "different"),
    ("transformers_version", "5.15.1"),
    ("tokenizer_implementation", "OtherBackend"),
    ("vocabulary_size", VOCABULARY_SIZE - 1),
    ("eos_token_id", 3),
    ("special_token_ids", (0, 1, 2)),
    ("projector_freeze_identity", "0" * 64),
])
def test_identity_mismatch_fails_before_decode(field, value):
    tokenizer = TokenizersBackend()
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        extract(tokenizer, replace(identity(), **{field: value}))
    assert tokenizer.decode_calls == 0


def test_extracts_complete_immutable_piece_bundle():
    tokenizer = TokenizersBackend()
    bundle = extract(tokenizer)
    assert tokenizer.decode_calls == 2 * VOCABULARY_SIZE
    assert len(bundle.token_pieces) == VOCABULARY_SIZE
    assert bundle.token_pieces[12] == "\x00"
    assert bundle.excluded_token_ids == frozenset((0, 1, 11))
    assert bundle.eos_token_id == 2
    assert bundle.tokenizer_identity == TOKENIZER_IDENTITY
    assert bundle.decoder_mechanism_identity == DECODER_MECHANISM_IDENTITY
    with pytest.raises(TypeError):
        bundle.token_pieces[12] = "changed"


def test_binds_distinct_initial_and_continuation_decoder_pieces():
    class TokenizersBackend:
        __module__ = "transformers.tokenization_utils_tokenizers"
        eos_token_id = EOS_TOKEN_ID
        all_special_ids = tuple(sorted(SPECIAL_TOKEN_IDS))
        decoder = ByteLevel()

        def __init__(self):
            self.decode_calls = 0

        def __len__(self):
            return VOCABULARY_SIZE

        def decode(self, token_ids, **kwargs):
            self.decode_calls += 1
            pieces = ["word" if token_id == 12 else (
                "" if token_id in SPECIAL_TOKEN_IDS else chr(0x20 + token_id % 90))
                for token_id in token_ids]
            return "".join(
                piece if index == 0 else (" " + piece if piece == "word" else piece)
                for index, piece in enumerate(pieces))

    bundle = extract(TokenizersBackend())
    assert bundle.initial_token_pieces[12] == "word"
    assert bundle.token_pieces[12] == " word"


def test_excludes_noncompositional_utf8_replacement_tokens():
    class TokenizersBackend:
        __module__ = "transformers.tokenization_utils_tokenizers"
        eos_token_id = EOS_TOKEN_ID
        all_special_ids = tuple(sorted(SPECIAL_TOKEN_IDS))
        decoder = ByteLevel()

        def __init__(self):
            self.decode_calls = 0

        def __len__(self):
            return VOCABULARY_SIZE

        def decode(self, token_ids, **kwargs):
            self.decode_calls += 1
            if 13 in token_ids:
                return "\ufffd" * token_ids.count(13)
            return "".join(
                "" if token_id in SPECIAL_TOKEN_IDS
                else chr(0x20 + token_id % 90)
                for token_id in token_ids
            )

    tokenizer = TokenizersBackend()
    bundle = extract(tokenizer)
    assert 13 in bundle.excluded_token_ids


@pytest.mark.parametrize("state", [
    None,
    {"type": "ByteLevel", "add_prefix_space": False,
     "trim_offsets": True, "use_regex": True},
    {"type": "Sequence", "decoders": []},
])
def test_rejects_missing_or_mutated_native_decoder_before_piece_decode(state):
    tokenizer = TokenizersBackend()
    if state is None:
        tokenizer.decoder = object()
    else:
        import json
        decoder_type = type("ByteLevel", (), {
            "__module__": "tokenizers.decoders",
            "__getstate__": lambda self: json.dumps(state),
        })
        tokenizer.decoder = decoder_type()
    with pytest.raises(ValueError, match="NATIVE_DECODER"):
        extract_identity_bound_token_pieces_v1(
            tokenizer=tokenizer, identity=identity(),
            canonical_tokenizer_type=TokenizersBackend,
            canonical_decoder_type=ByteLevel,
            tokenizers_version=TOKENIZERS_VERSION,
            native_extension_path="/runtime/tokenizers/tokenizers.abi3.so",
            native_extension_sha256=TOKENIZERS_NATIVE_SHA256,
            python_wrapper_identity=TOKENIZERS_PYTHON_WRAPPER_IDENTITY)
    assert tokenizer.decode_calls == 0


@pytest.mark.parametrize("version,path,digest", [
    ("0.22.1", "/runtime/tokenizers/tokenizers.abi3.so", TOKENIZERS_NATIVE_SHA256),
    (TOKENIZERS_VERSION, "/tmp/substitute.so", TOKENIZERS_NATIVE_SHA256),
    (TOKENIZERS_VERSION, "/runtime/tokenizers/tokenizers.abi3.so", "0" * 64),
])
def test_rejects_native_distribution_substitution_before_decode(version, path, digest):
    tokenizer = TokenizersBackend()
    with pytest.raises(ValueError, match="NATIVE_DECODER_ARTIFACT_MISMATCH"):
        extract_identity_bound_token_pieces_v1(
            tokenizer=tokenizer, identity=identity(),
            canonical_tokenizer_type=TokenizersBackend,
            canonical_decoder_type=ByteLevel,
            tokenizers_version=version, native_extension_path=path,
            native_extension_sha256=digest,
            python_wrapper_identity=TOKENIZERS_PYTHON_WRAPPER_IDENTITY)
    assert tokenizer.decode_calls == 0


def test_rejects_python_wrapper_substitution_before_decode():
    tokenizer = TokenizersBackend()
    with pytest.raises(ValueError, match="TOKENIZERS_WRAPPER_MISMATCH"):
        extract_identity_bound_token_pieces_v1(
            tokenizer=tokenizer, identity=identity(),
            canonical_tokenizer_type=TokenizersBackend,
            canonical_decoder_type=ByteLevel,
            tokenizers_version=TOKENIZERS_VERSION,
            native_extension_path="/runtime/tokenizers/tokenizers.abi3.so",
            native_extension_sha256=TOKENIZERS_NATIVE_SHA256,
            python_wrapper_identity="0" * 64)
    assert tokenizer.decode_calls == 0


def test_module_is_launch_forbidden_and_has_no_runtime_imports():
    path = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imported.intersection({"transformers", "torch", "peft", "subprocess"})
    assert not any(isinstance(node, ast.If) and isinstance(node.test, ast.Compare) for node in tree.body)
