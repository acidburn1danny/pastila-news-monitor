# V15 execution-bound pre-consumption layer

This successor layer closes the publication gap in the original V15 preflight.
It grants no attempt or candidate execution. The dependency graph is acyclic:

1. Published base checkpoint `f1cf2967705d29e53fb2e5eccc7459aecc2b43fc`
   fixes the original V15 attempt boundary, executor, validator, shell and
   historical preflight.
2. New source files contain no new authority, binding, signature, or future
   publication commit identity. Their bytes are hashed into the new authority.
3. The new authority binds the base boundary, new source hashes, V13 secret
   commitment, qualification, snapshot, output identity, and attempt semantics.
   A detached Ed25519 signature covers its binding.
4. At runtime the executable preflight verifies the signed authority and
   published source blobs, then verifies the live remote commit and tree contain
   the exact signed sources and artifacts. The observed commit/tree are sealed
   into a short-lived receipt. A future commit cannot be embedded in its own
   source-derived authority, so publication is checked from actual Git objects
   and recorded in the receipt; a mutable ref alone is never trusted.
   The published successor commit must have the exact base commit as its sole
   parent and contain exactly the seven new sources and four signed artifacts.
5. The receipt identity is SHA-256 of compact, sorted-key UTF-8 JSON over every
   field except `receipt_identity`. It includes the signed authority/binding/
   signature, base and current published commits/trees, source identities,
   legacy receipt, V13 commitment, qualification, runtime, snapshot, V14
   evidence, output path/device/inode, process ID and issue/expiry nanoseconds.

The consuming route generates its own fresh receipt in the same process; it
does not accept a caller-supplied receipt. It verifies receipt identity,
publication, source hashes, secret hash, output identity/emptiness and expiry.
The comparative mechanics then acquires an exclusive output-directory flock.
Immediately before the no-clobber atomic `attempt.json` publication, while
that lock is held, the route repeats the signed authority/runtime audit and
receipt checks. These checks reject old receipts, old checkpoint authority,
source drift, remote movement, secret/snapshot changes and stale output.
The output argument must equal its canonical absolute path, so the locked
`attempt.json` path cannot evade the final guarded atomic-write comparison.
`attempt.json` publication consumes the one attempt. The first V15 shell
subprocess follows it. Any later invocation sees nonempty output and fails
closed; the receipt never authorizes retry, redraw or accepted-row replay.

The receipt is runtime observation, never qualification evidence. Local tests
use fixtures only. Publishing this authority, running its executable preflight,
and authorizing a candidate attempt remain separate owner actions.
