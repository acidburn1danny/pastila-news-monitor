import httpx
import pytest

from pastila_scout.http_client import (
    USER_AGENT,
    HTTPClient,
    HTTPResponseError,
    HTTPTimeoutError,
)
from pastila_scout.logging_config import configure_logging


def install_transport(
    monkeypatch: pytest.MonkeyPatch,
    handler: httpx.MockTransport,
) -> dict[str, object]:
    real_client = httpx.Client
    options: dict[str, object] = {}

    def client_factory(**kwargs: object) -> httpx.Client:
        options.update(kwargs)
        return real_client(transport=handler, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)
    return options


def test_successful_response_returns_bytes_and_configures_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"feed")
    )
    options = install_transport(monkeypatch, transport)

    with HTTPClient(timeout=7.5) as client:
        content = client.fetch("https://example.com/feed")

    assert content == b"feed"
    assert options["timeout"] == 7.5
    assert options["follow_redirects"] is True
    assert options["headers"] == {"User-Agent": USER_AGENT}


def test_redirect_response_is_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/feed":
            return httpx.Response(302, headers={"Location": "/world.xml"})
        return httpx.Response(200, content=b"world feed")

    install_transport(monkeypatch, httpx.MockTransport(handler))

    with HTTPClient() as client:
        content = client.fetch("https://example.com/feed")

    assert content == b"world feed"


def test_timeout_is_translated(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    install_transport(monkeypatch, httpx.MockTransport(timeout))

    with HTTPClient() as client, pytest.raises(HTTPTimeoutError, match="timed out"):
        client.fetch("https://example.com/feed")


def test_status_error_is_translated_and_logged(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    install_transport(monkeypatch, transport)
    configure_logging()

    with HTTPClient() as client, pytest.raises(HTTPResponseError, match="503"):
        client.fetch("https://example.com/feed")

    assert "HTTP response error" in capsys.readouterr().err
