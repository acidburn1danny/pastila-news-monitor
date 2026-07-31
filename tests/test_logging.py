import logging

import pytest

from pastila_scout.logging_config import LOGGER_NAME, configure_logging


def test_normal_mode_logs_info_but_not_debug(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(verbose=False)
    logger = logging.getLogger(f"{LOGGER_NAME}.test")

    logger.debug("hidden diagnostic")
    logger.info("visible information")

    output = capsys.readouterr()
    assert "visible information" in output.err
    assert "hidden diagnostic" not in output.err
    assert output.out == ""


def test_verbose_mode_logs_debug(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(verbose=True)

    logging.getLogger(f"{LOGGER_NAME}.test").debug("visible diagnostic")

    output = capsys.readouterr()
    assert "DEBUG pastila_scout.test visible diagnostic" in output.err
    assert output.out == ""


def test_repeated_configuration_does_not_duplicate_handlers() -> None:
    configure_logging()
    configure_logging()
    application_logger = logging.getLogger(LOGGER_NAME)

    managed_handlers = [
        handler
        for handler in application_logger.handlers
        if getattr(handler, "_pastila_scout_console_handler", False)
    ]
    assert len(managed_handlers) == 1
