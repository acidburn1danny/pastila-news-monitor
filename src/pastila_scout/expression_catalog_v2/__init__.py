"""Additive, inactive Voice V2 expression catalog overlay."""

from .eligibility import (
    ALL_SCOPE_SPECS_V1,
    BOUNDED_POOL_SCOPE_SPECS_V1,
    EVIDENCE_ONLY_EXPRESSION_ID,
    FIRST_TWELVE_SCOPE_SPECS_V1,
    SCOPE_SPECS_V1,
    ExpressionEligibilityIntegrityError,
    evaluate_expression_eligibility_v1,
    expression_repetition_identity,
    finalize_expression_selection_receipt,
    finalize_relation_binding_identity,
)
from .eligibility_models import (
    CommentaryRelationBinding,
    CommentaryRelationBindingV1,
    CommentaryRelationBindingV2,
    CommentaryRelationshipV1,
    ExpressionEligibilityStatusV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
    MultiRoleAtomReuseAuthorizationV2,
    RelationAtomRoleV1,
)
from .models import (
    AdjudicationStatusV2,
    ExpressionCatalogOverlayV2,
    RenderabilityStatusV2,
)
from .persistence import (
    ExpressionCatalogV2IntegrityError,
    UnknownExpressionCatalogV2VersionError,
    load_expression_catalog_overlay_v2,
    validate_overlay_v2,
)
from .relationship_persistence import (
    CommentaryRelationBindingStoreV2,
    UnknownCommentaryRelationBindingVersionError,
)
from .selection_persistence import (
    ExpressionSelectionReceiptStoreV1,
    UnknownExpressionSelectionReceiptVersionError,
)

_PROOF_RENDERING_EXPORTS = {
    "IntegratedExpressionProofArtifactV1",
    "IntegratedExpressionProofStoreV1",
    "MultiRoleAtomReuseAuthorizationV2",
    "finalize_integrated_expression_artifact_v1",
    "integrate_expression_selection_v1",
    "render_integrated_expression_v1",
}


def __getattr__(name: str):
    if name in _PROOF_RENDERING_EXPORTS:
        from . import rendering

        return getattr(rendering, name)
    raise AttributeError(name)


__all__ = [
    "ALL_SCOPE_SPECS_V1",
    "BOUNDED_POOL_SCOPE_SPECS_V1",
    "EVIDENCE_ONLY_EXPRESSION_ID",
    "FIRST_TWELVE_SCOPE_SPECS_V1",
    "SCOPE_SPECS_V1",
    "AdjudicationStatusV2",
    "CommentaryRelationBinding",
    "CommentaryRelationBindingStoreV2",
    "CommentaryRelationBindingV1",
    "CommentaryRelationBindingV2",
    "CommentaryRelationshipV1",
    "ExpressionCatalogOverlayV2",
    "ExpressionCatalogV2IntegrityError",
    "ExpressionEligibilityIntegrityError",
    "ExpressionEligibilityStatusV1",
    "ExpressionOwnerSelectionReceiptV1",
    "ExpressionSelectionKindV1",
    "ExpressionSelectionReceiptStoreV1",
    "IntegratedExpressionProofArtifactV1",
    "IntegratedExpressionProofStoreV1",
    "MultiRoleAtomReuseAuthorizationV2",
    "RelationAtomRoleV1",
    "RenderabilityStatusV2",
    "UnknownCommentaryRelationBindingVersionError",
    "UnknownExpressionCatalogV2VersionError",
    "UnknownExpressionSelectionReceiptVersionError",
    "evaluate_expression_eligibility_v1",
    "expression_repetition_identity",
    "finalize_expression_selection_receipt",
    "finalize_integrated_expression_artifact_v1",
    "finalize_relation_binding_identity",
    "integrate_expression_selection_v1",
    "load_expression_catalog_overlay_v2",
    "render_integrated_expression_v1",
    "validate_overlay_v2",
]
