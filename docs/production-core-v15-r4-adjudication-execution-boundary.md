# V15 R4 adjudication execution boundary

This signed boundary projects exactly the 1,986 structurally eligible R4 rows into
canonical candidate-blinded packets. The 414 `FAIL_CLOSED_INVALID_OUTPUT` rows are
excluded before packet construction. No real packet or receipt is materialized by
boundary issuance.

Each future custody manifest binds one registered role, the signed boundary, and
the complete packet inventory root. Each receipt signs the boundary, packet and
row identities, opaque candidate alias, output hash, registered role/person/key,
and the human verdict. Complete closure requires one valid Ed25519 receipt from
each distinct registered role for every packet. Missing, duplicate, replayed,
cross-row, cross-role, substituted-key, or invalid-signature receipts fail closed.
Promotion remains outside this boundary.
