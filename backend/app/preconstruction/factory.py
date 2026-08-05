from app.core.config import APP_ENV, PreconstructionAIConfig
from app.preconstruction.provider import (
    DeterministicFakePreconstructionAIProvider,
    DisabledPreconstructionAIProvider,
    PreconstructionAIProvider,
)


def build_preconstruction_provider(
    config: PreconstructionAIConfig,
    *,
    fake_mode: str = "success",
) -> PreconstructionAIProvider:
    if not config.enabled or config.provider == "disabled":
        return DisabledPreconstructionAIProvider()
    if config.provider == "fake_test":
        if APP_ENV == "production" or not config.fake_provider_allowed:
            raise RuntimeError(
                "The fake preconstruction provider is not allowed in this environment"
            )
        return DeterministicFakePreconstructionAIProvider(fake_mode)
    raise RuntimeError("Unsupported preconstruction AI provider")
