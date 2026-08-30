# ByteLevel decoder admission

V1.2.1 token projection admits the frozen tokenizer only when its native decoder
is the Rust-backed `tokenizers.decoders.ByteLevel` type and its canonical state
is exactly `ByteLevel(add_prefix_space=true, trim_offsets=true, use_regex=true)`.

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
