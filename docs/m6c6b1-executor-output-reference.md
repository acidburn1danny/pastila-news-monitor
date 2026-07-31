# M6C.6B.1 executor output-reference compatibility

M6C.6B.1 adds the immutable, capability-neutral
`CorrectiveActionOutputReference` without changing dispatch ownership or legacy
executor semantics.

Executor result version 1 remains the canonical representation when no output
reference is present. Its fingerprint payload is unchanged. A successful result
that carries an output reference uses result version 2, and its fingerprint also
includes the reference fingerprint. Failed results cannot carry outputs, version
1 cannot carry an output, and version 2 requires one. Unknown versions fail
closed.

The generic reference contains only an output type, capability, capability-owned
output fingerprint, capability-result fingerprint, and its own deterministic
fingerprint. It contains no output content and does not transfer ownership of
capability-specific validation to the dispatcher.
