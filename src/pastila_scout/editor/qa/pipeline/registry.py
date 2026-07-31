"""Explicit deterministic reviewer registry."""

from pastila_scout.editor.qa.models import ReviewScope, fingerprint
from pastila_scout.editor.qa.pipeline.models import RegisteredReviewerDescriptor


class ReviewerRegistryError(ValueError):
    pass


class ReviewerRegistry:
    def __init__(self, entries):
        normalized = []
        for value in entries:
            reviewer, descriptor = value if isinstance(value, tuple) else (value, None)
            descriptor = descriptor or RegisteredReviewerDescriptor(
                reviewer_id=reviewer.reviewer_id,
                reviewer_version=reviewer.reviewer_version,
                capabilities=reviewer.capabilities.values,
                supported_scopes=tuple(ReviewScope),
                implementation_key=f"{type(reviewer).__module__}.{type(reviewer).__qualname__}".lower().replace(
                    "_", "-"
                ),
            )
            if (
                descriptor.reviewer_id != reviewer.reviewer_id
                or descriptor.reviewer_version != reviewer.reviewer_version
                or descriptor.capabilities != reviewer.capabilities.values
            ):
                raise ReviewerRegistryError(
                    "reviewer descriptor disagrees with implementation"
                )
            if not callable(getattr(reviewer, "review", None)):
                raise ReviewerRegistryError(
                    "registered reviewer does not implement review"
                )
            normalized.append((descriptor, reviewer))
        normalized.sort(
            key=lambda item: (item[0].reviewer_id, item[0].reviewer_version)
        )
        if len({item[0].reviewer_id for item in normalized}) != len(normalized):
            raise ReviewerRegistryError("reviewer identities must be unique")
        self._entries = tuple(normalized)

    @classmethod
    def build(cls, reviewers):
        return cls(tuple(reviewers))

    @property
    def descriptors(self):
        return tuple(item[0] for item in self._entries)

    @property
    def registry_fingerprint(self):
        return fingerprint(self.descriptors)

    def resolve(self, reviewer_id, reviewer_version=None):
        for descriptor, reviewer in self._entries:
            if descriptor.reviewer_id == reviewer_id:
                if reviewer_version and descriptor.reviewer_version != reviewer_version:
                    raise ReviewerRegistryError("REVIEWER_VERSION_MISMATCH")
                return reviewer
        raise ReviewerRegistryError("REVIEWER_NOT_REGISTERED")

    def descriptor(self, reviewer_id):
        self.resolve(reviewer_id)
        return next(
            item for item in self.descriptors if item.reviewer_id == reviewer_id
        )
