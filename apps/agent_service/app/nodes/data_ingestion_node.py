from app.schemas.data_ingestion_schema import (
    DataIngestionRunRequest,
    DataIngestionSearchAndRunRequest,
)
from app.services.data_ingestion_client import (
    DataIngestionClientError,
    data_ingestion_client,
)


SUCCESS_STATUSES = {"COMPLETED", "PARTIAL"}


async def data_ingestion_node(state: dict) -> dict:
    if not state.get("refresh_market_data", False):
        return {
            "ingestion_result": {
                "status": "SKIPPED",
                "message": "Data ingestion was skipped; existing marketplace data will be used.",
                "scrape_counts": {},
            }
        }

    product_id = state.get("product_id")
    if not product_id:
        return {
            "status": "FAILED",
            "error_code": "PRODUCT_ID_REQUIRED_FOR_INGESTION",
            "message": "product_id is missing. Data ingestion cannot run.",
        }

    marketplaces = state.get("ingestion_marketplaces") or [
        "TRENDYOL",
        "HEPSIBURADA",
        "AMAZON",
    ]
    query = state.get("ingestion_query")
    company_id = state.get("ingestion_company_id")

    if bool(query) != bool(company_id):
        return {
            "status": "FAILED",
            "error_code": "INVALID_DATA_INGESTION_OPTIONS",
            "message": (
                "ingestion_query and ingestion_company_id must be provided together."
            ),
        }

    if query and company_id:
        request = DataIngestionSearchAndRunRequest(
            product_id=product_id,
            company_id=company_id,
            query=query,
            marketplaces=marketplaces,
        )
    else:
        request = DataIngestionRunRequest(
            product_id=product_id,
            marketplaces=marketplaces,
        )

    try:
        response = await data_ingestion_client.run_ingestion(request)
    except DataIngestionClientError as exc:
        return {
            "status": "FAILED",
            "error_code": exc.code,
            "message": str(exc),
            "ingestion_result": {
                "status": "FAILED",
                "message": str(exc),
                "scrape_counts": {},
            },
        }

    result = response.model_dump(mode="json")
    status = response.status.upper()
    updates: dict = {
        "ingestion_job_id": response.job_id,
        "ingestion_result": result,
    }

    if status not in SUCCESS_STATUSES:
        updates.update(
            {
                "status": "FAILED",
                "error_code": "DATA_INGESTION_FAILED",
                "message": response.message,
            }
        )
        return updates

    if status == "PARTIAL":
        updates["warnings"] = [
            f"DATA_INGESTION_PARTIAL: {response.message}"
        ]

    return updates
