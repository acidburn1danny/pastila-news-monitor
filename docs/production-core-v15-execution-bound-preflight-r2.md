# V15 execution-bound source-closure successor r2

The published checkpoint `c060df236c416dd9ef7d62c987205973da7767a9`
and its authority remain historical evidence. Its preflight passed, but its
consuming route stopped before attempt claim because the signed source map
omitted eight keys required by `execute_production_core_candidate_qualification_v15.py`.
The real V15 output remains empty and no attempt was consumed.

The r2 authority inherits the verified source maps of the signed V15 attempt
boundary and the published execution-bound preflight. It adds exactly seven
r2 sources. The consuming executor's `source_keys` tuple is extracted from
the pinned Python source with `ast.literal_eval`; all its keys must be present
in the resulting map. Duplicate inherited names must have identical digests.
The map must equal this exact union, and every referenced local file is hashed
again. This closes the eight missing direct keys and preserves the already
signed transitive runner, helper, checkpoint, semantic, schema, and shell
sources without adding unrelated paths.

The dependency order is acyclic: the two published predecessor signatures and
their source maps -> seven r2 source hashes -> r2 authority -> r2 binding ->
Ed25519 signature -> runtime receipt. The r2 identities and future publication
commit do not occur in the hashed r2 sources. The initial r2 checkpoint
`46fa435afc93831104bb68e03599fcba9fd3c718` remains local historical
evidence. Its corrective successor must have that checkpoint as its sole parent
and change exactly four r2 sources and four signed r2 artifacts. All 42 sources,
including the unchanged r2 sources, must match signed hashes and published
blobs. The live remote commit, tree, exact changed-file set and every published
blob are checked before a receipt can be issued.

The receipt is runtime observation, never qualification evidence. The r2
consuming route self-issues a new receipt, rechecks the signed authority and
live state while holding the exclusive output lock, then uses the unchanged
atomic no-clobber attempt mechanism. The frozen 2,400-row qualification,
16-argument V15 shell, V13 secret, ext4 CUDA snapshot, V14 terminal evidence,
and no-restart semantics are unchanged. No real preflight or attempt is
authorized by this local repair.
