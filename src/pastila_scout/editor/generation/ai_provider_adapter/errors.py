"""Provider-neutral failures normalized at the AI Provider Adapter boundary."""


class AIProviderAdapterError(RuntimeError):
    """Base class for safe infrastructure failures from an AI provider adapter."""


class AIProviderAuthenticationError(AIProviderAdapterError):
    pass


class AIProviderAuthorizationError(AIProviderAdapterError):
    pass


class AIProviderTimeoutError(AIProviderAdapterError):
    pass


class AIProviderRateLimitError(AIProviderAdapterError):
    pass


class AIProviderTransportError(AIProviderAdapterError):
    pass


class AIProviderMalformedResponseError(AIProviderAdapterError):
    pass


class AIProviderSchemaViolationError(AIProviderAdapterError):
    pass


class AIProviderUnavailableError(AIProviderAdapterError):
    pass


class AIProviderUnsupportedCapabilityError(AIProviderAdapterError):
    pass


class AIProviderInternalError(AIProviderAdapterError):
    pass
