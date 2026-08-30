# Batch 2 owner-side custodial public-key enrollment runbook V1

This runbook is bound to enrollment commit
be9bd9ca812468b46cc0c0924cb5db5392ae98d4 and request identity
c5439550d6a6d86a9a88893cbeb2f88712d6fdcc5fc7b05b08b981ef275c0e04.

It grants no operational authority.

## Frozen roles and challenges

Challenges are read from
docs/artifacts/humor-mechanics-batch2-custodial-key-enrollment-request-v1.json.
The exact signed bytes are the UTF-8 serialization of the complete challenge
object using sorted keys, no insignificant whitespace, and separators comma
and colon. Never sign a screen rendering or manually copied subset.

| Index | Role | JSON pointer | Challenge identity |
|---:|---|---|---|
| 0 | RIGHTS_CUSTODIAN | /requests/0/challenge | 47e7573a2378ed1a93481182aeefcc2f1feba42f2e9b774a6a5b08321e0c8db3 |
| 1 | ACQUISITION_CUSTODIAN | /requests/1/challenge | ee5d8224428a39481ddbfd1d03edcc91bbc096eee258dbbc1937eb5c5c98aff1 |
| 2 | FAMILY_CUSTODIAN | /requests/2/challenge | 9da4ee8cd04f151ef9b2af46f175a804786d9920a58efbe24e964bac68b6e798 |
| 3 | PARTITION_CUSTODIAN | /requests/3/challenge | 61a6f2084cc697104c473013f7f7303ae1e97c56795b02084ab230834da9344d |
| 4 | BLIND_ESCROW_CUSTODIAN | /requests/4/challenge | 492fa73d502c9e800fc30ded327d4a7072f2c8161f3162ccf70a6a43eecbbeef |
| 5 | CONTAMINATION_AUDITOR | /requests/5/challenge | 70c5b7fd8ebbfda3bd392bd550f90c13eb3f6dc2ea264ba9fbd225108a7aa4f7 |

Every challenge binds its role and principal to domain
PASTILA_BATCH2_OWNED_AUTHORITY_KEY_ENROLLMENT_V1, purpose
CUSTODIAL_PUBLIC_KEY_PROOF_OF_POSSESSION, appointment registry
e5b4ebb9fe29244a8d760337dcd66253264a42edd9b3540bb3fd5a44f91206d5,
signing readiness
89e61c2d7f2dcbfd51e41d907e3ef27041985dc6caad5d1267d6824530462e1a,
previous ledger head
8afc9aa54bf66d385d8e89d84f18884e06e6838acc9c1e3cc4127d1450442ad1,
and enrollment generation 1.

## Safe local procedure

OpenSSL 3.x is required. Ed25519 is preferred. ECDSA-P256 with SHA-256
remains allowed.

Create directories outside the repository:

~~~powershell
$keyRoot = Join-Path $env:USERPROFILE "Pastila-Owner-Secrets\Batch2-Custodians-v1"
$responseRoot = Join-Path $env:USERPROFILE "Pastila-Owner-Handoff\Batch2-Custodians-v1"
New-Item -ItemType Directory -Force -Path $keyRoot, $responseRoot
~~~

Do not use shell transcript logging. Inspect the public bindings:

~~~powershell
.\.venv\Scripts\python.exe scripts\owner_humor_batch2_custodial_key_enrollment_v1.py inspect
~~~

Generate and sign once per role:

~~~powershell
$roles = @("RIGHTS_CUSTODIAN","ACQUISITION_CUSTODIAN","FAMILY_CUSTODIAN","PARTITION_CUSTODIAN","BLIND_ESCROW_CUSTODIAN","CONTAMINATION_AUDITOR")
$ownerIdentity = "REPLACE_WITH_OWNER_SELECTED_IDENTITY"
foreach ($role in $roles) {
  .\.venv\Scripts\python.exe scripts\owner_humor_batch2_custodial_key_enrollment_v1.py prepare-role --role $role --algorithm ED25519 --key-dir $keyRoot --response-dir $responseRoot --owner-identity $ownerIdentity
}
~~~

For ECDSA-P256 replace ED25519 with ECDSA_P256_SHA256. The helper refuses
repository-local paths and existing output files. It generates one distinct
private key per role, signs only the frozen canonical challenge, immediately
verifies the signature, derives SHA256 over SPKI DER, and writes a public-only
response.

Protect the private directory using encrypted owner-controlled storage and
inspect Windows ACLs:

~~~powershell
icacls $keyRoot
git status --short
~~~

Git status must show no new PEM, DER, signature, response, key, or temporary
files.

## Public handoff

Return the six response JSON files, or a JSON array containing their six
objects. Each object supplies:

- enrollment_request_identity
- role
- principal_identity
- challenge_identity
- canonical_challenge_sha256
- algorithm
- public_key with format PEM_SPKI and value
- public_key_fingerprint with method SHA256_SPKI_DER and value
- proof_signature with encoding BASE64 and value
- owner_confirmation with owner identity, confirmation, role, principal,
  fingerprint, and statement
- private_key_included set to false

Never return private PEM files. Enrollment fails closed if any role, challenge,
principal, canonical hash, key fingerprint, signature, or owner confirmation
disagrees. Challenges are one-time and cannot be reused after registration.

## Owner safety checks

1. Six fingerprints and six private-key paths are all distinct.
2. Every response reports private_key_included false.
3. Every signature was locally verified.
4. Key and response roots are outside the repository.
5. Git status contains no generated secret or handoff file.
6. Private keys remain in owner-controlled encrypted storage.
7. Only the six public response objects are returned.
