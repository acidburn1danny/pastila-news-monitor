# V13 executable launcher and pre-consumption gate

The published V13 authority remains unchanged. This successor launcher boundary
signs the exact launcher, executor adapter, preflight, validator projection,
runner, shell, and supporting source bytes. It binds the published V13 commit
`b67b31e2e9931ecde05c2a9de5018a5e7bca7834` and authority
`2aaa50283451d5338b15d256becccb1ac7e557f12a677126051a036c368d2804`.
The detached Ed25519 binding grants no candidate execution or attempt
consumption by itself.

Run the launcher only with `--preflight-only` in this phase. Supply the native
ext4 recovery root, private V13 secret root, owner-held backup root, Unicode
authority root, and an existing empty owner-only ext4 output directory. The
backup volume must first be mounted in the same WSL session. The gate verifies
the signed source boundary, V13 authority, secret and exact backup, schedule,
Unicode objects, GPU and namespace capabilities, output emptiness, and all
recovered runtime objects. The independent adversarial auditor additionally
runs the executor's own `--preflight-only` path and validates its receipt with
the V13 attempt validator. Neither path writes `attempt.json`.

The three Unicode 16 objects were restored to
`/root/pf9-v13-unicode-authority/objects/sha256/` from the official Unicode
16.0.0 auxiliary files and UAX #29 revision 45 after their bytes matched the
published SHA-256 identities. These objects are runtime inputs, not Git files.
The recovered V12 runtime intentionally shares one rootfs tar across A and B;
the V13 validator permits that exact sharing while requiring distinct physical
model and adapter materializations.

The V13 executor adapter reuses byte-pinned V3 mechanics without inheriting V3,
V10, or V11 authority identities. Two invalid historical `except` clauses are
repaired only in the V13 projections. The executor's candidate path exists for
a future, separately authorized attempt; it was not invoked or tested by
consuming an attempt in this phase. Any preflight must be rerun immediately
before a future consumption decision because output state and host capacity can
change.
