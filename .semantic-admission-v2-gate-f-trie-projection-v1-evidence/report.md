# Gate-F optimized trie projection V1

The optimized evaluation-only projector builds a trie over the exact 131,072-token vocabulary and traverses shared decoded-character prefixes through the frozen Gate-F DFA. Allowed-token sets are cached by immutable grammar state with semantically irrelevant string history normalized; character count remains distinct near the hard output bound.

The original full-prefix projector remains the correctness oracle. Exhaustive comparisons at root, decision, reason-code, free-string, and confidence states found zero missing and zero extra token IDs. Additional distinct string histories—ASCII, spaces and Unicode, embedded backticks, and escaped newline text—also matched the oracle exactly while reusing the normalized cache.

The optimized projector is isolated from the previously frozen correctness-oracle module, whose bound source and test hashes remain byte-exact. The 221,961-node trie builds in 0.403172 seconds. Non-string cold projections take 0.010642–0.013682 seconds. The mandatory free-string prewarm takes 0.687749 seconds within its two-second budget. Cached projection remains below one millisecond in the final separated-module preflight. All defined correctness and performance gates pass.

The known tokenizer-regex warning remains preserved under the frozen tokenizer configuration. No tokenizer setting, model runner, prompt, parser, production import path, or runtime behavior was changed. No model/provider call occurred, and no inference or Run 3 authority was issued.

The optimized projector is ready for a separately authorized evaluation-only runner integration and zero-inference lifecycle preflight. It is not yet authorized for a model call.
