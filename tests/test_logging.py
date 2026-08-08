import logging

import pytest

from pastila_scout import __version__
from pastila_scout.logging_config import LOG_FORMAT, LOGGER_NAME, configure_logging


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
    assert (
        f"DEBUG pastila_scout.test version={__version__} visible diagnostic"
        in output.err
    )
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


def test_logging_projects_exact_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert f"version={__version__}" in LOG_FORMAT
    configure_logging()
    logging.getLogger(f"{LOGGER_NAME}.version").info("projection")
    output = capsys.readouterr()
    assert f"version={__version__} projection" in output.err
    assert output.out == ""
