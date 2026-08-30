"""Identity-bound, injected-tokenizer piece extraction; never loads a tokenizer."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Callable
import csv
import hashlib
import io
import json
from typing import Mapping, Protocol, Sequence


PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
TRANSFORMERS_VERSION = "5.15.0"
TOKENIZER_IMPLEMENTATION = "TokenizersBackend"
TOKENIZER_IMPLEMENTATION_MODULE = "transformers.tokenization_utils_tokenizers"
VOCABULARY_SIZE = 131_072
EOS_TOKEN_ID = 2
SPECIAL_TOKEN_IDS = frozenset((0, 1, 2, 11))
DECODER_CONFIGURATION = {
    "add_prefix_space": True, "trim_offsets": True,
    "type": "ByteLevel", "use_regex": True,
}
DECODER_CONFIGURATION_SHA256 = "1d64d97add535d9ad91561aabea254849cf7f2ea4b924cc61c17152f1dd6e672"
TOKENIZERS_VERSION = "0.22.2"
TOKENIZERS_WHEEL_SHA256 = "369cc9fc8cc10cb24143873a0d95438bb8ee257bb80c71989e3ee290e8d72c67"
TOKENIZERS_NATIVE_SHA256 = "c116fcf1e80d461ce0a35c332974f25949e8359416f50b3d53371810d2ce1ccc"
TOKENIZERS_PYTHON_WRAPPER_IDENTITY = "a465a7f8617d1d4ece64f1d833f98597c398efb8183b4e8b85fe92a52fe15b45"
TOKENIZERS_RECORD_SHA256 = "d12cab93031dc452a44cf753277eef6405d645d9adc48b6b59e4432fa721e421"
TOKENIZERS_RECORD_ROWSET_IDENTITY = "2623b4cc71db0d39977a2901e6d28a24d6e819f4f4b63f35d2cce93339e3f27c"
TRANSFORMERS_WHEEL_SHA256 = "d7f007736f67749ae9490c4f8cb5d30b452ae2d68c8675e50ba8d63ea7feb107"
TRANSFORMERS_RECORD_SHA256 = "18faf1053b2e169cfd9eb8eca1ccc35ebaf3bb0ce4f6c9dc137e010ab269b936"
TRANSFORMERS_RECORD_ROWSET_IDENTITY = "435bcb53c4f0dbf3527c7b4e435cc23c093f34493f3b8f42876daef1702b01fc"
TRANSFORMERS_WRAPPER_SHA256 = "bf921a160f483c7a32973952ed82a08c7d8982f769726bd220933aae2df98de8"
DECODER_MECHANISM_IDENTITY = "75f65490cd9f498d08b831bee612d0285c54351bc71ee2d87892e8ab89a65c95"
DECODER_MECHANISM_FIELDS = {
    "decoder_configuration_sha256": DECODER_CONFIGURATION_SHA256,
    "native_extension_sha256": TOKENIZERS_NATIVE_SHA256,
    "tokenizers_version": TOKENIZERS_VERSION,
    "wheel_sha256": TOKENIZERS_WHEEL_SHA256,
    "python_wrapper_identity": TOKENIZERS_PYTHON_WRAPPER_IDENTITY,
    "tokenizers_record_sha256": TOKENIZERS_RECORD_SHA256,
    "tokenizers_record_rowset_identity": TOKENIZERS_RECORD_ROWSET_IDENTITY,
    "transformers_record_sha256": TRANSFORMERS_RECORD_SHA256,
    "transformers_record_rowset_identity": TRANSFORMERS_RECORD_ROWSET_IDENTITY,
    "transformers_wheel_sha256": TRANSFORMERS_WHEEL_SHA256,
    "transformers_wrapper_sha256": TRANSFORMERS_WRAPPER_SHA256,
}
DERIVED_DECODER_MECHANISM_IDENTITY = hashlib.sha256(json.dumps(
    DECODER_MECHANISM_FIELDS, sort_keys=True,
    separators=(",", ":")).encode()).hexdigest()


class InjectedTokenizerV1(Protocol):
    eos_token_id: int
    all_special_ids: Sequence[int]

    def __len__(self) -> int: ...
    def decode(self, token_ids: Sequence[int], *, skip_special_tokens: bool,
               clean_up_tokenization_spaces: bool) -> str: ...


@dataclass(frozen=True)
class TokenizerRuntimeIdentityV1:
    tokenizer_identity: str
    decoder_identity: str
    transformers_version: str
    tokenizer_implementation: str
    vocabulary_size: int
    eos_token_id: int
    special_token_ids: tuple[int, ...]
    projector_freeze_identity: str


@dataclass(frozen=True)
class TokenPieceBundleV1:
    token_pieces: Mapping[int, str]
    excluded_token_ids: frozenset[int]
    eos_token_id: int
    tokenizer_identity: str
    decoder_identity: str
    projector_freeze_identity: str
    initial_token_pieces: Mapping[int, str] | None = None
    decode_token_ids: Callable[[Sequence[int]], str] | None = None
    decoder_mechanism_identity: str | None = None


def _validate_native_decoder(tokenizer: InjectedTokenizerV1) -> None:
    decoder = getattr(tokenizer, "decoder", None)
    decoder_type = type(decoder)
    if (decoder_type.__name__ != "ByteLevel"
            or decoder_type.__module__ != "tokenizers.decoders"):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_TYPE_MISMATCH")
    state_method = getattr(decoder, "__getstate__", None)
    if not callable(state_method):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_MISSING")
    try:
        state = state_method()
        if isinstance(state, bytes):
            state = state.decode("utf-8")
        value = json.loads(state) if isinstance(state, str) else state
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")
    except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_INVALID") from exc
    if (value != DECODER_CONFIGURATION
            or hashlib.sha256(canonical).hexdigest()
            != DECODER_CONFIGURATION_SHA256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_IDENTITY_MISMATCH")


def _validate_installed_record(
    raw: bytes, *, package: str, version: str, expected_rowset_identity: str,
) -> None:
    """Admit canonical wheel rows plus only closed, non-runtime pip extras."""
    try:
        text = raw.decode("utf-8", errors="strict")
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except (UnicodeError, csv.Error) as exc:
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_DISTRIBUTION_RECORD_INVALID") from exc
    if not rows or any(len(row) != 3 for row in rows):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DISTRIBUTION_RECORD_INVALID")
    observed: set[tuple[str, str, str]] = set()
    canonical: list[tuple[str, str, str]] = []
    dist_info = f"{package}-{version}.dist-info"
    for raw_row in rows:
        row = tuple(raw_row)
        if row in observed:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DISTRIBUTION_RECORD_INVALID")
        observed.add(row)
        path, digest, size = row
        bytecode_extra = (
            path.startswith(package + "/")
            and "/__pycache__/" in path
            and path.endswith(".cpython-312.pyc")
            and digest == "" and size == ""
        )
        installer_extra = (
            path == dist_info + "/INSTALLER"
            and digest.startswith("sha256=") and size.isdecimal()
        )
        requested_extra = (
            path == dist_info + "/REQUESTED"
            and digest == "sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU"
            and size == "0"
        )
        console_extra = (
            package == "transformers" and path == "../../../bin/transformers"
            and digest.startswith("sha256=") and size.isdecimal()
        )
        if bytecode_extra or installer_extra or requested_extra or console_extra:
            continue
        canonical.append(row)
    identity = hashlib.sha256(json.dumps(
        sorted(canonical), ensure_ascii=True,
        separators=(",", ":")).encode()).hexdigest()
    if identity != expected_rowset_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DISTRIBUTION_RECORD_ROWSET_MISMATCH")


def extract_identity_bound_token_pieces_v1(
    *, tokenizer: InjectedTokenizerV1, identity: TokenizerRuntimeIdentityV1,
    canonical_tokenizer_type: type, canonical_decoder_type: type,
    tokenizers_version: str, native_extension_path: str,
    native_extension_sha256: str, python_wrapper_identity: str,
    tokenizers_record_bytes: bytes, common_distribution_root: bool,
    transformers_wrapper_path: str, transformers_wrapper_sha256: str,
    transformers_record_bytes: bytes, transformers_common_root: bool,
) -> TokenPieceBundleV1:
    """Validate the entire frozen identity tuple before performing any decode."""
    expected = TokenizerRuntimeIdentityV1(
        tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,
        transformers_version=TRANSFORMERS_VERSION,
        tokenizer_implementation=TOKENIZER_IMPLEMENTATION,
        vocabulary_size=VOCABULARY_SIZE,
        eos_token_id=EOS_TOKEN_ID,
        special_token_ids=tuple(sorted(SPECIAL_TOKEN_IDS)),
        projector_freeze_identity=PROJECTOR_FREEZE_IDENTITY,
    )
    if type(identity) is not TokenizerRuntimeIdentityV1 or identity != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_IDENTITY_MISMATCH")
    if DERIVED_DECODER_MECHANISM_IDENTITY != DECODER_MECHANISM_IDENTITY:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_DECODER_MECHANISM_SEAL_INVALID")
    if (type(tokenizer) is not canonical_tokenizer_type
            or canonical_tokenizer_type.__name__ != TOKENIZER_IMPLEMENTATION
            or canonical_tokenizer_type.__module__ != TOKENIZER_IMPLEMENTATION_MODULE):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_IMPLEMENTATION_MISMATCH")
    if (type(tokenizer.decoder) is not canonical_decoder_type
            or canonical_decoder_type.__name__ != "ByteLevel"
            or canonical_decoder_type.__module__ != "tokenizers.decoders"):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_TYPE_MISMATCH")
    if (tokenizers_version != TOKENIZERS_VERSION
            or not native_extension_path.replace("\\", "/").endswith(
                "/tokenizers/tokenizers.abi3.so")
            or native_extension_sha256 != TOKENIZERS_NATIVE_SHA256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NATIVE_DECODER_ARTIFACT_MISMATCH")
    if python_wrapper_identity != TOKENIZERS_PYTHON_WRAPPER_IDENTITY:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZERS_WRAPPER_MISMATCH")
    if common_distribution_root is not True:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZERS_RECORD_MISMATCH")
    _validate_installed_record(
        tokenizers_record_bytes, package="tokenizers", version=TOKENIZERS_VERSION,
        expected_rowset_identity=TOKENIZERS_RECORD_ROWSET_IDENTITY)
    if (not transformers_wrapper_path.replace("\\", "/").endswith(
            "/transformers/tokenization_utils_tokenizers.py")
            or transformers_wrapper_sha256 != TRANSFORMERS_WRAPPER_SHA256
            or transformers_common_root is not True):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TRANSFORMERS_WRAPPER_MISMATCH")
    _validate_installed_record(
        transformers_record_bytes, package="transformers", version=TRANSFORMERS_VERSION,
        expected_rowset_identity=TRANSFORMERS_RECORD_ROWSET_IDENTITY)
    if len(tokenizer) != VOCABULARY_SIZE:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_VOCABULARY_MISMATCH")
    if tokenizer.eos_token_id != EOS_TOKEN_ID:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_EOS_MISMATCH")
    if frozenset(tokenizer.all_special_ids) != SPECIAL_TOKEN_IDS:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_SPECIAL_IDS_MISMATCH")
    _validate_native_decoder(tokenizer)

    initial_pieces: dict[int, str] = {}
    continuation_pieces: dict[int, str] = {}
    excluded = set(SPECIAL_TOKEN_IDS - {EOS_TOKEN_ID})
    for token_id in range(VOCABULARY_SIZE):
        initial = tokenizer.decode(
            [token_id], skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        doubled = tokenizer.decode(
            [token_id, token_id], skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if type(initial) is not str or type(doubled) is not str:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        # ByteLevel vocabularies include raw UTF-8 byte fragments.  Decoding one
        # such token can yield U+FFFD while decoding two fragments can form a
        # different valid sequence, so compositional prefix subtraction is not
        # defined for that token.  It is not a global decoder failure: exclude
        # the token from both tries and retain an empty continuation sentinel.
        compositional = doubled.startswith(initial)
        continuation = doubled[len(initial):] if compositional else ""
        if any(0xD800 <= ord(character) <= 0xDFFF
               for piece in (initial, continuation) for character in piece):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        initial_pieces[token_id] = initial
        continuation_pieces[token_id] = continuation
        if (not compositional or not initial or not continuation or "\ufffd" in initial
                or "\ufffd" in continuation) and token_id != EOS_TOKEN_ID:
            excluded.add(token_id)
    def decode_token_ids(token_ids: Sequence[int]) -> str:
        result = tokenizer.decode(
            token_ids, skip_special_tokens=True,
            clean_up_tokenization_spaces=False)
        if type(result) is not str or any(
                0xD800 <= ord(character) <= 0xDFFF for character in result):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        return result
    return TokenPieceBundleV1(
        token_pieces=MappingProxyType(continuation_pieces),
        excluded_token_ids=frozenset(excluded),
        eos_token_id=EOS_TOKEN_ID,
        tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,
        projector_freeze_identity=PROJECTOR_FREEZE_IDENTITY,
        initial_token_pieces=MappingProxyType(initial_pieces),
        decode_token_ids=decode_token_ids,
        decoder_mechanism_identity=DECODER_MECHANISM_IDENTITY,
    )


__all__ = (
    "DECODER_IDENTITY", "EOS_TOKEN_ID", "PROJECTOR_FREEZE_IDENTITY",
    "SPECIAL_TOKEN_IDS", "TOKENIZER_IDENTITY", "TRANSFORMERS_VERSION",
    "TOKENIZER_IMPLEMENTATION", "DECODER_MECHANISM_IDENTITY", "TokenizerRuntimeIdentityV1",
    "TokenPieceBundleV1", "VOCABULARY_SIZE",
    "extract_identity_bound_token_pieces_v1",
)
