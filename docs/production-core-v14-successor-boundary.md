# V14 successor runner and overnight supervisor boundary

The V13 attempt `28358c61c869659b4af1774eecd5f462bf2e209b0cf19503025438deb367a67e`
is consumed terminal evidence. Its terminal-failure identity is
`8aa8b23f9cec02aaa8157bd4773e6666e4f16ac4987135791655d0c63650ce7d`.
The V14 builder reads and validates both files and the partial artifact inventory;
it never changes or resumes that attempt.

The V14 runner accepts exactly qualification generation
`65d5b2502c0ff3a30367cceccda2a2e5c772844cb70500445a186deebf1d4567`
and qualification
`309facaf268c79cdf3e6c635bec47c46c68121b7b5eb543f07c801048386da13`.
The V14 shell carries both identities through the isolated child environment.
The runner rejects historical or substituted identities before importing model
libraries. The signed V14 authority binds these source bytes, the published V13
source commit/tree, V13 authority, ext4 recovery resolution, unchanged secret
commitment/schedule, and terminal evidence. It grants neither candidate execution
nor another attempt.

The V14 overnight supervisor has a synthetic smoke protocol and a separate
production connector. The smoke plan explicitly requires
`candidate_execution=false` and `attempt_consumption=false`; it cannot launch
the qualification executor. Heartbeat and state live in a separate owner-only
runtime directory and declare `qualification_evidence=false`. State and
checkpoint ordinals are sealed and checked on restart. Smoke tasks run as
systemd transient services with `KillMode=control-group`; a file lock excludes
parallel supervisors. Systemd owns an active worker if the supervisor is killed,
and a restarted supervisor reattaches without replaying accepted tasks. SIGTERM
stops the active unit and records a terminal state. A task advances only after
its exact marker and successful unit exit are observed.

The production connector is included in the separately signed V14 launcher
boundary. It requires a fresh executable `PASS + 0 BLOCKERS` preflight and an
explicit owner authorization flag before starting the V14 launcher in a
systemd service. It never retries a stopped or completed unit. While active it
validates the V14 attempt identity and the existing V6 checkpoint chain against
the unchanged V13 schedule and secret, reports accepted rows and checkpoints,
and stops on terminal failure or invalid evidence. It validates completion
against the frozen evidence contract. Its heartbeat and state are observations,
not qualification evidence. The synthetic smoke exercises the same durable
state, systemd ownership, signal, and restart mechanisms, without creating an
attempt. The production connector has not been invoked because another
candidate execution and attempt consumption are not authorized.

The V14 executor/launcher projection binds the new runner and shell and
preserves the V13 generation and qualification identities. Its signed boundary
and executable `--preflight-only` paths use a **new, empty** native ext4 output
root. Before any future attempt, rerun the full preflight immediately before
consumption. This document and the synthetic smoke do not authorize a new
attempt, adjudication, or promotion.
