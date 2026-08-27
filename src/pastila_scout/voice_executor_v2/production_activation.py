"""Owner-approved bounded initial production activation policy."""

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

from .models import (
    ZERO_IDENTITY,
    ProductionActivationEntryV1,
    VoiceProductionActivationPolicyV1,
)


def _finalize(policy: VoiceProductionActivationPolicyV1):
    return policy.model_copy(
        update={
            "policy_identity": canonical_identity(
                policy.model_copy(update={"policy_identity": ZERO_IDENTITY})
            )
        }
    )


BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1 = _finalize(
    VoiceProductionActivationPolicyV1(
        entries=(
            ProductionActivationEntryV1(
                expression_identity="ro-expression-v1:65f9b0c32e8e886b8d0f",
                surface_identity="SURFACE_BOUNDED_POOL_02_V1",
                eligibility_spec_identity="sha256:97bddb7efbb365baaf4081af79abb46c86f9ff62cf5d1b28822cf8907be31e6c",
                relationship_scope_identity="sha256:ae64b3627a890c18310a833e71708884c4860b5a7315c24602a93cdf54e61724",
            ),
            ProductionActivationEntryV1(
                expression_identity="ro-expression-v1:1068794b4bf34c8914dc",
                surface_identity="SURFACE_BOUNDED_POOL_01_V1",
                eligibility_spec_identity="sha256:8806b8cc207b65ed5113d5dbcef7a05a44ccbced85477c8b3ca511053c54653a",
                relationship_scope_identity="sha256:b72337f4b103cafd564e726aea27636d63bf971e8fb395beb3df68f2c0097f2d",
            ),
            ProductionActivationEntryV1(
                expression_identity="ro-expression-v1:0e6562965022d3dd391f",
                surface_identity="SURFACE_BOUNDED_POOL_03_V1",
                eligibility_spec_identity="sha256:c1297fb7c0d66d921182ffc47a706c9c2b51777aa9300b3423eb6a5a42ca59d5",
                relationship_scope_identity="sha256:ab43191ab144ee258e1e4a3f5eae8d321263659f564838b5cbbd35f71d643c4c",
            ),
        )
    )
)


__all__ = ["BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1"]
