"""Safe application-owned compatibility errors."""


class ProducerCompatibilityConfigurationError(Exception):
    """Report invalid inert composition configuration without retaining inputs."""

    def __init__(self) -> None:
        super().__init__("Producer compatibility configuration is invalid.")
        self.__cause__ = None
        self.__context__ = None
        self.__suppress_context__ = True


__all__ = ()
