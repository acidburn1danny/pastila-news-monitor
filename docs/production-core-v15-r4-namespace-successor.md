# V15 R4 executable namespace successor

The published R3 commit `cb2f05909fc833ad4a1643b35753feda59017393`
is immutable. Its one authorized route invocation failed before atomic claim.
The R3 projection compiles the V3 mechanics a second time after the V15 adapter
has bound V13 snapshots and V15 runtime inputs. That compilation restores V9
snapshot names, V3 prompt hashes, the V3 runner and launcher, and the V3
directory lock. The V14 terminal validator rejected the first mismatch before
`attempt.json` was created. R3 output remains empty and unconsumed.

R4 keeps the frozen 200 requests, V13 qualification generation and schedule,
2,400 rows, 12 checkpoints, candidate weights, validator contract, V15 driver
snapshot, resource limits, and R2/V14 historical evidence unchanged. It uses a
new native ext4 output at `/root/pf9-v15-r4-preconsumption-output`.

The R4 projection compiles the unchanged R3 corrected mechanics, then restores
the exact V14/V15 globals used by the live `main`: snapshot set, prompt paths
and hashes, runner, 16-argument launcher, object authority helper, Linux path
mapping, exclusive directory flock, durable no-clobber atomic writer, CUDA
snapshot, and driver helper. It checks those values and the inherited
generation, qualification, rootfs, Unicode, validator, and execution-authority
bindings before any claim. The signed authority binds the complete source map,
the effective namespace claim, R3 publication and signature, and empty R4
output. Under the exclusive lock, the consuming route repeats the signed audit,
receipt, and live namespace checks immediately before atomic `attempt.json`.

The signed R4 supervisor starts that exact route as a single systemd service
with `Restart=no` and `KillMode=control-group`. Its durable state and heartbeat
live outside qualification output. It observes accepted checkpoint receipts,
rejects regression and parallel ownership, propagates termination to the whole
worker cgroup, and seals the already-authorized terminal-failure schema if an
unexpected post-claim process exit bypasses the route's own exception closure.
It never starts a second service for an existing state and never treats its
monitor files as qualification evidence.

This local signed boundary does not grant candidate execution or attempt
consumption. Publication requires a separate checkpoint commit and push. A
future attempt requires its own owner authorization and a fresh executable
pre-consumption preflight. No retry of the consumed R2 attempt is permitted.
The publication gate accepts only a linear descendant chain from the exact R3
commit and requires the cumulative `R3..HEAD` file set and every published blob
to equal the signed R4 closure. Merge ancestry and unrelated follow-up files are
rejected.
