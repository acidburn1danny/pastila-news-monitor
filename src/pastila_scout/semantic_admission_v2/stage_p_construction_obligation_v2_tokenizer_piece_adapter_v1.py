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

    pieces: dict[int, str] = {}
    excluded = set(SPECIAL_TOKEN_IDS - {EOS_TOKEN_ID})
    for token_id in range(VOCABULARY_SIZE):
        piece = tokenizer.decode(
            [token_id], skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        if type(piece) is not str or any(
            0xD800 <= ord(character) <= 0xDFFF for character in piece
        ):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_TOKENIZER_DECODE_INVALID")
        pieces[token_id] = piece
        if not piece and token_id != EOS_TOKEN_ID:
            excluded.add(token_id)
    return TokenPieceBundleV1(
        token_pieces=MappingProxyType(pieces),
        excluded_token_ids=frozenset(excluded),
        eos_token_id=EOS_TOKEN_ID,
        tokenizer_identity=TOKENIZER_IDENTITY,
        decoder_identity=DECODER_IDENTITY,
        projector_freeze_identity=PROJECTOR_FREEZE_IDENTITY,
    )


__all__ = (
    "DECODER_IDENTITY", "EOS_TOKEN_ID", "PROJECTOR_FREEZE_IDENTITY",
    "SPECIAL_TOKEN_IDS", "TOKENIZER_IDENTITY", "TRANSFORMERS_VERSION",
    "TOKENIZER_IMPLEMENTATION", "TokenizerRuntimeIdentityV1",
    "TokenPieceBundleV1", "VOCABULARY_SIZE",
    "extract_identity_bound_token_pieces_v1",
)
