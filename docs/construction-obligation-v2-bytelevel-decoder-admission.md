# ByteLevel decoder admission

V1.2.1 token projection admits the frozen tokenizer only when its native decoder
is the Rust-backed `tokenizers.decoders.ByteLevel` type and its canonical state
is exactly `ByteLevel(add_prefix_space=true, trim_offsets=true, use_regex=true)`.
Admission also requires `tokenizers==0.22.2`, the canonical manylinux x86-64
wheel identity `369cc9fc…2c67`, import origin
`tokenizers/tokenizers.abi3.so`, and native-extension SHA-256
`c116fcf1…1ccc`. The decoder-mechanism seal covers all four identities.
The installed `METADATA`, `WHEEL`, package initializer, and decoder initializer
are also hashed into wrapper identity `a465a7f8…5b45`; runtime derives this
identity from the imported distribution before accepting its class objects.
The canonical wheel `RECORD` is sealed as `d12cab93…e421`. Runtime admission
requires every canonical row, unchanged, using order-independent row-set seal
`2623b4cc…f27c`; it permits only closed pip extras (`INSTALLER` and empty-hash
CPython 3.12 bytecode rows). All imported tokenizers artifacts and dist-info
must share one distribution root. The Transformers entrypoint is independently
bound to wheel `d7f00773…b107`, canonical `RECORD` `18faf105…b936`, row-set
seal `435bcb53…01fc`, and `tokenization_utils_tokenizers.py` SHA-256
`bf921a16…8de8`. Its installed manifest permits only the corresponding closed
pip extras (`INSTALLER`, `REQUESTED`, console script, and empty-hash CPython
3.12 bytecode rows).

The ByteLevel decoder converts each vocabulary token's byte-alphabet symbols to
bytes, concatenates those bytes, and performs one lossy UTF-8 decode. Therefore,
decoded Unicode token pieces are concatenative only when each admitted token's
own byte sequence is valid UTF-8. Extraction excludes empty pieces, special
tokens other than terminal EOS, surrogate-containing pieces, and every token
whose isolated or doubled decode contains U+FFFD. On that admitted subset, each
token contributes a complete UTF-8 sequence, so concatenating token bytes and
then decoding is equivalent to concatenating the precomputed Unicode pieces.

This proof is intentionally narrower than accepting arbitrary decoder objects.
Configuration mutation, decoder-type substitution, malformed serialization,
and non-compositional byte fragments fail before the generation callback is
constructed. The initial and continuation indexes remain separate and their
phase remains part of the projector cache domain.
