# VNext R2 Reference Dependency Closure v1

This checkpoint records the minimal content-addressed R2 component closure and
the clean-room startup boundary. Active runtime resolution is restricted to a
restored VNext closure, a VNext-managed Python package environment, and declared
host Python/CUDA/GPU dependencies.

Component operational independence and global VNext migration are separate
gates. Global migration remains blocked until every production stage passes
startup and acceptance tests with legacy unavailable and a zero legacy
dependency count.
