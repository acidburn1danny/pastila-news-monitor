# V15 R2 terminal forensics and local R3 repair boundary

## Immutable R2 conclusion

The published R2 HEAD is `2a45477249da4105e5c563dc090457ca05190a85`.
Its consumed attempt at `/root/pf9-v15-preconsumption-output/attempt.json` has
identity `30747ad2a52d1d64a0ad29933eb51385a2cebd9a6efecfcc77993140c5542bdd`,
SHA-256 `189f0905ca0973cf7fc78c2fbf7af308a95f1caa90957a0ce19e875a0fa30efe`,
and inner preflight identity
`e2f7c54e30f4bda75e8c95b1558f5f59c52245c0cfbfd64b00f5a1abf3d0029c`.
The attempt is terminal historical evidence. No R2 file is changed or completed
after the fact.

The first batch reached 200 raw outputs and 200 observations. Its batch and
heartbeat SHA-256 values are respectively
`43b0579c2cd4aad44bcde1b413b0da5758a58aae5db9b4953eb4a2070cb41ebe`
and `f7c17afcdf3b0351c145bf641154c1b11f78840c8dec8cd570b9eb8a24d2e763`.
There are zero case receipts and zero accepted checkpoints. Neither
`completion.json` nor `terminal-failure.json` exists. A read-only inventory of
the 806 R2 files had SHA-256
`ccb42322be83de8a1dbfa846dd8ae9b7fce34c44082caac30a774d9516864d9d`
over compact JSON of sorted `(relative path, file SHA-256)` pairs.

The causal mismatch is reproducible without inference. Each published V2
request-manifest row carries `candidate_visible_request`, but has no top-level
`authority_spans`. The prompt's `INPUT` JSON does carry the ordered spans.
The R2 execution mechanics pass the manifest row to `validate_response_v2`.
That validator indexes `case["authority_spans"]`, which raises `KeyError` for
the published row. The observed R2 process traceback ended at that lookup
with exit code 1. The R2 pre-consumption validation checked manifest identity,
prompt hash, schedule cardinality, and row bindings. It never probed the
actual validator input shape. The mechanics write `terminal-failure.json` only
on explicit error branches; the uncaught `KeyError` escaped those branches.

The owner of the mismatch is the R2 execution request-to-validator adapter and
its pre-consumption contract check. The owner of the missing terminal artifact
is the post-claim exception-closure path. Neither fault is attributable to a
candidate output, a GPU failure, or an unaccepted checkpoint. The first
candidate execution occurred; no second execution or retry is authorized.

## Separate R3 repair boundary

The R3 source projection leaves the frozen V13 request manifest, qualification
generation, schedule, candidate objects, prompt bytes, resource caps, and V14
evidence unchanged. Before claim, it parses all 200 exact prompt `INPUT`
objects, checks their bytes and their matching manifest fields, and probes
the actual semantic validator with a synthetic abstention. A missing or
malformed `authority_spans` field fails before an attempt can be created. The
post-inference path passes the parsed case to the validator. Invalid candidate
bytes remain individual failed cases under the already-published V14/V15
two-exception catch; a contract `KeyError` stays fatal.

The projected mechanics put attempt creation and all later work inside one
post-claim exception closure. If `attempt.json` exists and there is neither
completion nor terminal evidence, the closure inventories current files,
builds and validates the existing terminal-failure schema, then publishes
`terminal-failure.json` atomically without replacement. It re-raises the
original failure. Existing terminal evidence is never overwritten. A failure
before claim produces no terminal artifact. If the evidence cannot be
validated, the route fails closed rather than fabricating a terminal state.

The separate R3 authority binds these repaired bytes, the immutable R2
publication and consumed-evidence inventory, the frozen V15 authority and
qualification identities, and the distinct native ext4 output
`/root/pf9-v15-r3-preconsumption-output`. Its detached Ed25519 signature
authenticates a new binding. R2's signed authority and consumed output remain
historical inputs only and cannot authorize the R3 route.

The R3 consuming route requires a fresh R3 receipt that verifies an exact
successor commit whose sole parent is the published R2 checkpoint, exact
published blobs and signed artifacts, source/runtime closure, the 200-case
validator contract, the frozen V15 CUDA snapshot, and empty output. Under the
exclusive output flock, it repeats the signed audit and receipt check
immediately before the existing durable no-clobber `attempt.json` write.
The route additionally requires explicit owner attempt authorization. Until
the R3 sources and artifacts are committed and published, the publication
gate rejects it. Signing does not grant an attempt, adjudication, promotion,
commit, or publication.
