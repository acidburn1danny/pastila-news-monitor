from types import SimpleNamespace

import pytest

from pastila_scout.contracts.scout_editor import EventAuthorityBundleV1
from pastila_scout.event_authority_v1 import build_event_authority_bundle


def _article(article_id: int, source_id: str, *, summary: str):
    return SimpleNamespace(
        id=article_id,
        source_id=source_id,
        source_name=f"Source {source_id}",
        url=f"https://example.test/{article_id}",
        title=f"Title {article_id}",
        summary=summary,
        published_at=None,
    )


def test_event_authority_preserves_canonical_first_and_source_attribution():
    bundle = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=2,
        articles=(
            _article(1, "secondary", summary="Secondary account."),
            _article(2, "canonical", summary="Canonical account."),
        ),
    )

    assert isinstance(bundle, EventAuthorityBundleV1)
    assert tuple(item.article_id for item in bundle.segments) == (2, 1)
    assert bundle.segments[0].canonical is True
    assert bundle.segments[1].canonical is False


def test_event_authority_requires_exactly_one_canonical_first_segment():
    canonical = build_event_authority_bundle(
        event_id=7,
        canonical_article_id=2,
        articles=(_article(2, "canonical", summary="Canonical account."),),
    ).segments[0]

    with pytest.raises(ValueError, match="exactly one canonical"):
        EventAuthorityBundleV1(
            authority_version="event-authority-bundle-v1",
            event_id=7,
            segments=(canonical, canonical),
        )
