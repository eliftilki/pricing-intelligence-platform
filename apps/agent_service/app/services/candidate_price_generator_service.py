from app.schemas.candidate_price_schema import (
    CandidatePriceContext,
    CandidatePriceGenerateResponse,
    CandidateStrategy,
)
from app.services.candidate_strategy_selector import CandidateStrategySelector
from app.services.candidate_strategies.adaptive_dense_strategy import AdaptiveDenseStrategy
from app.services.candidate_strategies.basic_range_strategy import BasicRangeStrategy
from app.services.candidate_strategies.tier_based_strategy import TierBasedStrategy


class CandidatePriceGeneratorService:
    def __init__(self):
        self.selector = CandidateStrategySelector()

        self.strategies = {
            CandidateStrategy.BASIC_COMPETITOR_RANGE: BasicRangeStrategy(),
            CandidateStrategy.TIER_BASED_COMPETITOR_WINDOW: TierBasedStrategy(),
            CandidateStrategy.ADAPTIVE_DENSE_MARKET_WINDOW: AdaptiveDenseStrategy(),
        }

    def generate(
        self,
        context: CandidatePriceContext,
        strategy: CandidateStrategy = CandidateStrategy.AUTO,
    ) -> CandidatePriceGenerateResponse:
        selected_strategy = strategy

        if strategy == CandidateStrategy.AUTO:
            selected_strategy = self.selector.select(context)

        generator = self.strategies[selected_strategy]

        return generator.generate(context)