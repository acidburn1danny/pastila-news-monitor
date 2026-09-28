# VNext VOICE Candidates Dependency Closure v1

This dependency-only closure physically materializes the two exact, previously inventoried text-only candidate snapshots beneath the single VNext product root. The historical content-addressed store is migration input only and is not a runtime dependency.

Every source file is checked against its exact revision inventory, byte size, Git blob identity and any published SHA-256. Every copied file receives a complete SHA-256 in the VNext lock. Publication is atomic after full copy. The closure rejects symlinks, hardlinks, source inode reuse and direct legacy path bytes.

The clean relocation proof copies only the completed VNext candidate closure to an ephemeral root and executes dependency-only verification from that root. It does not load a model, tokenize input, generate output, run inference, download bytes, create an optimizer or train.
