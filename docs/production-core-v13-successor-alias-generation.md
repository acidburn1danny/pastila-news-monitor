# V13 successor alias generation

The V2 candidate alias secret was lost. Its historical commitment
`ee86684da529d0b1a75c172d5ed2c3ec65f21da5f350d53cb7dda500f4449dca`
and all V12 source, recovery, and authority artifacts remain unchanged.

V13 uses one new private 256-bit nonce and a new private alias mapping. The
primary secret is an owner-only file on native WSL ext4 at
`/root/pf9-v13-private/candidate-alias-secret-v13.json`; an exact backup is on
the owner-held `SCOUT_BACKUP` volume under
`pastila-v13-secret-recovery/candidate-alias-secret-v13.json`. Neither copy is
part of Git. The public commitment is the SHA-256 of the canonical secret
bytes. The schedule uses the V2 HMAC-SHA256 ordering formula and the original
200 request case IDs to produce 2400 new positions. Neither the nonce nor the
candidate-to-alias mapping is disclosed by the public artifacts.

The V10 request manifest, candidate object manifest, input envelope receipts,
corpus, qualification rows, model weights, adapters, tokenizers, and rootfs are
reused byte-for-byte. The new generation and qualification identities reflect
only the changed secret-dependent schedule, commitment, status/lineage, and
generator source binding. The V13 execution authority binds those identities
to the published source anchor `ea428931f95a65131ed7def90e9c17f488bd714b`,
its tree `0e5038566f6b1cb9a3b725cccf00b2fe403c7aaa`, the V12 runner identity,
the successful ext4 resolution, and the independently audited V12 runtime
authority. The failed Windows/drvfs replay is not a source or runtime input.

The V13 authority is a signed **zero-attempt boundary**. It does not authorize
candidate execution or attempt consumption. An executable V13 launcher and a
fresh pre-consumption preflight must be reviewed and authorized separately
before running candidates. Historical V10/V11 execution identities must not
be used as V13 attempt authority.
