# Milestone 9 proof-boundary reset

Status: accepted

## Root cause

The V2.3 deployment boundary made a single Git commit serve simultaneously as
the authority for RFC-3161 request construction, request transport, response
verification, workflow scheduling, and workflow execution.  Those phases have
different capabilities and different evidence lifetimes.  In particular, the
request verifier needs no network, transport needs network, and activation must
not perform transport at all.

This produced a self-invalidating governance loop: correcting any executable
check changed the freeze commit; that changed the schedule preimage and query;
that invalidated the timestamp receipt, qualification, and activation workflow;
and the replacement closure exposed the next runtime mismatch.

The repeated blockers were therefore manifestations of three architectural
defects:

1. phase and capability conflation;
2. treating a mutable implementation commit as both specification and evidence;
3. requiring pre-response authority to contain post-response evidence.

## Replacement architecture

Milestone 9 uses five monotonic phases.  Evidence may flow only forward.

| Phase | Network | Input | Output |
| --- | --- | --- | --- |
| Freeze | prohibited | reviewed deployment specification | immutable release digest |
| Pre-request validation | prohibited | frozen schedule and query byte snapshot | validation record |
| RFC-3161 transport | DigiCert endpoint only | the validated query snapshot | response bytes and HTTP record |
| Post-response verification | prohibited | frozen inputs and response | committed proof record |
| Attestation-only activation | GitHub OIDC/Fulcio/Rekor only | committed proof record | initiation and final Sigstore attestations |

The RFC-3161 verifier runs in the digest-pinned OCI runtime with networking
disabled.  The transport process never enters that runtime and performs no
verification; it may send exactly the already validated query snapshot and
record the response.  Consequently no host-side `chroot`/`unshare` executable
is part of the cryptographic authority.  The OCI launcher is an execution
substrate, while the pinned image, verifier, inputs, and recorded results are
the evidence authority.

Activation does not generate or submit RFC-3161 requests.  It verifies the
committed proof offline before requesting Sigstore attestations.  Publisher and
registry metadata paths remain absent from attestation-only activation.

## Stable governance

- Schedule selection:
  `FIRST_UTC_HOUR_AT_LEAST_12_HOURS_AFTER_REPLACEMENT_FREEZE`
- Scheduler delay allowance: 24 hours
- Artifact retention: 30 days
- Manual or redrawn scheduled execution: prohibited
- Attestation registry push: false
- Publisher and registry metadata acquisition: prohibited in Milestone 9

Changing implementation code within a phase requires new qualification for
that phase.  It does not retroactively change evidence from an earlier phase.
A new RFC-3161 request is required only when the frozen release digest or query
bytes change.

## Milestone completion and successor

Milestone 9 is complete when the inactive workflow and release bundle have a
committed offline proof, and one scheduled activation produces verified public
initiation and final Sigstore attestations.

Milestone 10 is **authorized production metadata capture**.  It must introduce
publisher/registry access as a new, separately reviewed capability and bind its
captured dataset to the Milestone 9 initiation evidence.  It must not expand
the Milestone 9 attestation-only workflow in place.
