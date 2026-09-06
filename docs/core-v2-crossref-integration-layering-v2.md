# Core V2 Crossref integration layering

`crossref_integration_core_v2` is the specimen-neutral admission mechanism for
future, separately authorized work. It does not designate a capture, provider
execution, state instance, record limit, or milestone as active authority.

The mechanism accepts an immutable `CrossrefAdmissionProfileV2`, immutable
state, and canonical normalized bytes. The profile layer supplies the
normalized schema and maximum record count. The specimen supplies its own raw
capture identity, while the normalized identity is derived from the supplied
bytes. Accepted records retain both identities.

Historical Phase 3 and Phase 6 implementations and evidence remain unchanged.
They truthfully prove admission of their designated specimens, but they are not
the reusable integration mechanism for a future capture. No historical module
or qualification is rewritten or implicitly selected by this design.

The reusable module has no transport, filesystem, scheduling, publication,
provider-execution, qualification, commit, tree, phase, or runtime-path
authority. Selecting it in a future orchestration remains a separate owner and
qualification action.
