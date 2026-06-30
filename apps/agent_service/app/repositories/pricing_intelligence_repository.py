from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun


def _to_agent_run_status(pipeline_status: str) -> str:
    """Translate detailed pipeline outcomes to the shared run lifecycle."""
    if pipeline_status == "PARTIAL_SUCCESS":
        return "SUCCESS"
    return pipeline_status


class PricingIntelligenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_run(
        self,
        *,
        product_id: UUID,
        seller_product_id: UUID | None,
        company_id: UUID | None,
        input_payload: dict,
        output_payload: dict,
        status: str,
    ) -> AgentRun:
        now = datetime.now(timezone.utc)
        run = AgentRun(
            product_id=product_id,
            seller_product_id=seller_product_id,
            company_id=company_id,
            run_type="PRICING_INTELLIGENCE",
            status=_to_agent_run_status(status),
            input_payload=input_payload,
            output_payload=output_payload,
            started_at=now,
            finished_at=now,
        )
        self.db.add(run)
        self.db.commit()
        return run

    def get_latest_run(
        self,
        *,
        product_id: UUID,
        seller_product_id: UUID | None = None,
    ) -> AgentRun | None:
        query = (
            self.db.query(AgentRun)
            .filter(AgentRun.run_type == "PRICING_INTELLIGENCE")
            .filter(AgentRun.product_id == product_id)
            .filter(AgentRun.output_payload.isnot(None))
        )
        if seller_product_id is not None:
            query = query.filter(AgentRun.seller_product_id == seller_product_id)

        return query.order_by(AgentRun.finished_at.desc()).first()
