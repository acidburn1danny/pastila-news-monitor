# VNext ACTIVE Runtime Cache Policy & Managed Inventory Semantics Repair v1

PASS + 0 BLOCKERS. One canonical runtime-bytes policy is consumed by builder, ACTIVE preflight, and standalone auditor. Managed authority, regenerable cache, mutable SQLite state, and forbidden paths now receive the same classification.

Allowed Python cache and SQLite WAL/SHM do not enter managed inventory or authority identity. Unauthorized bytes, ambiguous paths, traversal, symlinks, managed drift, and policy drift fail closed.

Identities: product lock `b8fe4dd7c7d1e9482388a7435e4655b9c9ef0436adaf1d224befac0530949514`; SHA-256 `de5fe4388f065123bcfc7c7c0f829ecba9b24340819e59b8c58d3762e1d896e7`; graph `f98a47aa61c5391abe7bda7efe79a9cbaeae326f47b7c89be5a188517c11bed3`; audit `fe9b36b57528de3806be73ef16c6458c4a29efc246af779adaf84b9e7b78f29c`.