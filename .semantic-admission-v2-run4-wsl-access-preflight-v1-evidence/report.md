# Semantic Admission V2 — Run 4 WSL access preflight

## Outcome

The corrected unrestricted zero-inference preflight passed. WSL service access was available, both exact runner paths were readable, the ordinary runner compiled, and the constrained runner completed tokenizer loading, trie construction, and prefix prewarming.

No model was loaded and no inference, model call, or provider call occurred. Run 4 remains unauthorized.

## Verified boundaries

- Source Run 3 remains frozen under `d567adaddd889063ae48d65d647c8676b6a4ea87f9f9cc047ed80888af12ee07`.
- WSL distribution: `Ubuntu-24.04`.
- Constrained runner SHA-256: `17a1669d5ec145bfc2ef746890e4d6534670e94b069a3a7d6307bb8127bd2ac9`.
- Ordinary runner SHA-256: `51c7ff37731c5f4a9cacda7ee3a9d1966e51bb80098ce2ea6503a34345ee06a9`.
- Constrained trie: 221,961 nodes; canonical streams terminal; root fence impossible; terminal-only EOS verified.
- Model loading, generation, model calls, and provider calls: zero.

## Preserved harness failure

The first authorized attempt completed the service, path-readability, and ordinary compile checks, then stopped because the harness required its not-yet-created temporary lifecycle output to exist during path conversion. That attempt is preserved. The converter was corrected only for output paths, and the full preflight then passed. Neither attempt loaded a model or performed inference.

## Readiness warning

The local Transformers tokenizer emitted a warning that this Mistral tokenizer is being loaded with an incorrect regex pattern and recommends `fix_mistral_regex=True`. The existing frozen constrained runner does not set that option. This did not prevent trie construction or the structural prefix checks, but it may change tokenization and therefore can affect constrained-decoding behavior. The warning must not be silently dismissed or remediated inside the frozen Run 4 contract.

## Recommendation

Before authorizing Run 4 inference, perform a bounded design/read-only impact check of the tokenizer-regex warning against the frozen constrained-decoding identities and prior successful one-call probe. Decide explicitly whether the existing frozen tokenizer behavior remains the Run 4 contract or whether a separately versioned remediation and new preflight are required. Do not modify or execute Run 4 implicitly.
