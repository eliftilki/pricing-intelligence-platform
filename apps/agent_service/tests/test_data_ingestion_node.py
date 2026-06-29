import asyncio
import unittest
from uuid import uuid4

from app.nodes import data_ingestion_node as node_module
from app.graph.pricing_pipeline_graph import _route_after_data_ingestion
from app.schemas.data_ingestion_schema import (
    DataIngestionRunResponse,
    DataIngestionSearchAndRunRequest,
)
from app.services.data_ingestion_client import DataIngestionClientError


class FakeDataIngestionClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    async def run_ingestion(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


class DataIngestionNodeTests(unittest.TestCase):
    def setUp(self):
        self.original_client = node_module.data_ingestion_client

    def tearDown(self):
        node_module.data_ingestion_client = self.original_client

    def test_ingestion_runs_automatically_without_refresh_flag(self):
        fake_client = FakeDataIngestionClient(
            response=DataIngestionRunResponse(
                job_id=uuid4(),
                status="COMPLETED",
                message="Cached data is ready.",
                scrape_counts={"TRENDYOL": 4},
            )
        )
        node_module.data_ingestion_client = fake_client

        result = asyncio.run(
            node_module.data_ingestion_node({"product_id": uuid4()})
        )

        self.assertEqual(result["ingestion_result"]["status"], "COMPLETED")
        self.assertEqual(len(fake_client.requests), 1)
        self.assertNotIn("status", result)

    def test_completed_ingestion_continues_without_failure_status(self):
        job_id = uuid4()
        fake_client = FakeDataIngestionClient(
            response=DataIngestionRunResponse(
                job_id=job_id,
                status="COMPLETED",
                message="Fresh data is ready.",
                scrape_counts={"TRENDYOL": 5},
            )
        )
        node_module.data_ingestion_client = fake_client

        result = asyncio.run(
            node_module.data_ingestion_node(
                {
                    "product_id": uuid4(),
                    "ingestion_marketplaces": ["TRENDYOL"],
                }
            )
        )

        self.assertEqual(result["ingestion_job_id"], job_id)
        self.assertEqual(result["ingestion_result"]["status"], "COMPLETED")
        self.assertNotIn("status", result)

    def test_partial_ingestion_continues_with_warning(self):
        fake_client = FakeDataIngestionClient(
            response=DataIngestionRunResponse(
                job_id=uuid4(),
                status="PARTIAL",
                message="One marketplace failed.",
                scrape_counts={"TRENDYOL": 5, "AMAZON": 0},
            )
        )
        node_module.data_ingestion_client = fake_client

        result = asyncio.run(
            node_module.data_ingestion_node(
                {"product_id": uuid4()}
            )
        )

        self.assertNotIn("status", result)
        self.assertIn("DATA_INGESTION_PARTIAL", result["warnings"][0])

    def test_failed_ingestion_stops_pipeline(self):
        fake_client = FakeDataIngestionClient(
            response=DataIngestionRunResponse(
                job_id=uuid4(),
                status="FAILED",
                message="No marketplace could be scraped.",
                scrape_counts={},
            )
        )
        node_module.data_ingestion_client = fake_client

        result = asyncio.run(
            node_module.data_ingestion_node(
                {"product_id": uuid4()}
            )
        )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error_code"], "DATA_INGESTION_FAILED")

    def test_client_error_stops_pipeline_with_specific_error_code(self):
        fake_client = FakeDataIngestionClient(
            error=DataIngestionClientError(
                "DATA_INGESTION_TIMEOUT",
                "Data ingestion service request timed out.",
            )
        )
        node_module.data_ingestion_client = fake_client

        result = asyncio.run(
            node_module.data_ingestion_node(
                {"product_id": uuid4()}
            )
        )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error_code"], "DATA_INGESTION_TIMEOUT")

    def test_query_and_company_use_search_and_run_request(self):
        fake_client = FakeDataIngestionClient(
            response=DataIngestionRunResponse(
                job_id=uuid4(),
                status="COMPLETED",
                message="Search and scrape completed.",
                scrape_counts={"HEPSIBURADA": 3},
            )
        )
        node_module.data_ingestion_client = fake_client

        asyncio.run(
            node_module.data_ingestion_node(
                {
                    "product_id": uuid4(),
                    "ingestion_marketplaces": ["HEPSIBURADA"],
                    "ingestion_query": "Logitech G305",
                    "ingestion_company_id": uuid4(),
                }
            )
        )

        self.assertIsInstance(
            fake_client.requests[0],
            DataIngestionSearchAndRunRequest,
        )

    def test_route_fans_out_after_success_and_stops_after_failure(self):
        self.assertEqual(
            _route_after_data_ingestion({}),
            ["competitor_intelligence", "event_agent"],
        )
        self.assertEqual(
            _route_after_data_ingestion({"status": "FAILED"}),
            ["end"],
        )


if __name__ == "__main__":
    unittest.main()
