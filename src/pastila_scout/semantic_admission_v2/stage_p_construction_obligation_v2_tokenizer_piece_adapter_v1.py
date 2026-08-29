"""Identity-bound, injected-tokenizer piece extraction; never loads a tokenizer."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence


PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
TRANSFORMERS_VERSION = "5.15.0"
TOKENIZER_IMPLEMENTATION = "TokenizersBackend"
VOCABULARY_SIZE = 131_072
EOS_TOKEN_ID = 2
SPECIAL_TOKEN_IDS = frozenset((0, 1, 2, 11))


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


def extract_identity_bound_token_pieces_v1(
    *, tokenizer: InjectedTokenizerV1, identity: TokenizerRuntimeIdentityV1,
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
    if type(tokenizer).__name__ != TOKENIZER_IMPLEMENTATION:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_IMPLEMENTATION_MISMATCH")
    if len(tokenizer) != VOCABULARY_SIZE:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_VOCABULARY_MISMATCH")
    if tokenizer.eos_token_id != EOS_TOKEN_ID:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_EOS_MISMATCH")
    if frozenset(tokenizer.all_special_ids) != SPECIAL_TOKEN_IDS:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_SPECIAL_IDS_MISMATCH")

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
        if (type(initial) is not str or type(doubled) is not str
                or not doubled.startswith(initial)):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        continuation = doubled[len(initial):]
        if any(0xD800 <= ord(character) <= 0xDFFF
               for piece in (initial, continuation) for character in piece):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        initial_pieces[token_id] = initial
        continuation_pieces[token_id] = continuation
        if (not initial or not continuation) and token_id != EOS_TOKEN_ID:
            excluded.add(token_id)
    anchors = [token_id for token_id in range(VOCABULARY_SIZE)
               if token_id not in SPECIAL_TOKEN_IDS and initial_pieces[token_id]]
    if not anchors:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_CONTINUATION_ANCHOR_MISSING")
    anchor_id = anchors[0]
    anchor = initial_pieces[anchor_id]
    for token_id in range(VOCABULARY_SIZE):
        contextual = tokenizer.decode(
            [anchor_id, token_id], skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if (type(contextual) is not str or not contextual.startswith(anchor)
                or contextual[len(anchor):] != continuation_pieces[token_id]):
            raise ValueError(
                "CONSTRUCTION_OBLIGATION_V2_TOKENIZER_CONTINUATION_NOT_CONTEXT_FREE")
    return TokenPieceBundleV1(
        token_pieces=MappingProxyType(continuation_pieces),
        excluded_token_ids=frozenset(excluded),
        eos_token_id=EOS_TOKEN_ID,
        tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,
        projector_freeze_identity=PROJECTOR_FREEZE_IDENTITY,
        initial_token_pieces=MappingProxyType(initial_pieces),
    )


__all__ = (
    "DECODER_IDENTITY", "EOS_TOKEN_ID", "PROJECTOR_FREEZE_IDENTITY",
    "SPECIAL_TOKEN_IDS", "TOKENIZER_IDENTITY", "TRANSFORMERS_VERSION",
    "TOKENIZER_IMPLEMENTATION", "TokenizerRuntimeIdentityV1",
    "TokenPieceBundleV1", "VOCABULARY_SIZE",
    "extract_identity_bound_token_pieces_v1",
)
