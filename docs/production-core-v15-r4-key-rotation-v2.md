# V15 R4 adjudicator key rotation V2

This successor preserves the published R4 attempt, packets, custody exports, and
the historical V1 registry. Registry V2 supersedes registry V1 only for future
human receipts. Two independently signed proof-of-possession challenges bind the
new public keys to the same registered people and roles.

The bridge treats every V1 packet and custody identity as immutable input. A V2
receipt additionally signs the rotation-authority identity, historical packet
registry identity, and successor registry identity. Consequently neither a V1
receipt nor a receipt signed by an old key can satisfy V2 closure.

The successor CLI uses the existing candidate-blinded custody roots and new,
role-separated receipt roots ending in `-v2`. Private keys remain external
required arguments. The client neither discovers nor generates keys. It creates
no receipt until the complete signed authority, registry, packet inventory,
role, public key, and output path pass fail-closed validation.

No receipt, adjudication decision, semantic verdict, or promotion is issued by
this boundary.
