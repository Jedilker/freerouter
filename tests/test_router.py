import hashlib
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import (
    app,
    RouterRequest,
    choose_model,
    get_user_analytics,
    require_api_key,
    route_llm,
)


class FakeResult:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class FakeQuery:
    def __init__(self, table_name, client):
        self.table_name = table_name
        self.client = client
        self.fields = None
        self.filters = {}
        self.payload = None
        self.is_head = False

    def select(self, fields, **kwargs):
        self.fields = fields
        self.is_head = kwargs.get("head", False)
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def limit(self, _limit):
        return self

    def order(self, _field, **_kwargs):
        return self

    def insert(self, payload):
        self.payload = payload
        self.client.inserted.append((self.table_name, payload))
        return self

    def execute(self):
        self.client.queries.append((self.table_name, self.filters.copy()))
        if self.payload is not None:
            return FakeResult()
        if self.fields == "user_id":
            return FakeResult([{"user_id": "user-123"}])
        if self.is_head:
            return FakeResult(count=2)
        return FakeResult(
            [
                {"target_model": "test/budget", "latency_ms": 2.0},
                {"target_model": "test/quality", "latency_ms": 4.0},
            ]
        )


class FakeSupabase:
    def __init__(self):
        self.inserted = []
        self.queries = []

    def table(self, table_name):
        return FakeQuery(table_name, self)


class ModelRoutingTests(unittest.TestCase):
    def setUp(self):
        self.model_settings = patch.dict(
            os.environ,
            {
                "ROUTER_BUDGET_MODEL": "test/budget",
                "ROUTER_QUALITY_MODEL": "test/quality",
            },
        )
        self.model_settings.start()
        self.addCleanup(self.model_settings.stop)

    def test_simple_prompt_uses_budget_model(self) -> None:
        model, reason = choose_model("What is an HTTP status code?")

        self.assertEqual(model, "test/budget")
        self.assertEqual(reason, "simple_request")

    def test_complex_prompt_uses_quality_model(self) -> None:
        model, reason = choose_model(
            "Compare the security trade-offs of a distributed architecture."
        )

        self.assertEqual(model, "test/quality")
        self.assertEqual(reason, "complexity_rules")

    def test_code_prompt_uses_quality_model(self) -> None:
        model, reason = choose_model("Review this code:\n```python\nprint('hello')\n```")

        self.assertEqual(model, "test/quality")
        self.assertEqual(reason, "complexity_rules")

    def test_turkish_complex_prompt_uses_quality_model(self) -> None:
        model, reason = choose_model(
            "Dağıtık mimaride güvenlik ve ölçeklenebilirlik için detaylı analiz yap."
        )

        self.assertEqual(model, "test/quality")
        self.assertEqual(reason, "complexity_rules")

    def test_model_configuration_is_required(self) -> None:
        with patch.dict(
            os.environ,
            {"ROUTER_BUDGET_MODEL": "", "ROUTER_QUALITY_MODEL": ""},
        ):
            with self.assertRaises(HTTPException) as error:
                choose_model("A simple question")

        self.assertEqual(error.exception.status_code, 503)

    def test_api_key_lookup_uses_hash(self) -> None:
        fake = FakeSupabase()
        with patch("main.get_supabase", return_value=fake):
            user = require_api_key("sk_live_example-secret")

        self.assertEqual(user, {"user_id": "user-123"})
        self.assertEqual(
            fake.queries[0][1]["key_hash"],
            hashlib.sha256(b"sk_live_example-secret").hexdigest(),
        )

    def test_route_log_is_user_scoped_and_does_not_store_prompt(self) -> None:
        fake = FakeSupabase()
        prompt = "Explain this request without persisting its text."
        with patch("main.get_supabase", return_value=fake):
            response = route_llm(
                RouterRequest(prompt=prompt),
                {"user_id": "user-456"},
            )

        self.assertEqual(response["target_model"], "test/budget")
        log = fake.inserted[0][1]
        self.assertEqual(log["user_id"], "user-456")
        self.assertNotIn("prompt", log)

    def test_analytics_query_is_user_scoped(self) -> None:
        fake = FakeSupabase()
        with patch("main.get_supabase", return_value=fake):
            response = get_user_analytics({"user_id": "user-789"})

        self.assertEqual(response["summary"]["total_requests"], 2)
        self.assertEqual(response["sampled_requests"], 2)
        self.assertEqual(response["chart_data"]["datasets"], [1, 1])
        self.assertTrue(
            all(filters.get("user_id") == "user-789" for _, filters in fake.queries)
        )

    def test_api_key_requires_expected_prefix(self) -> None:
        with self.assertRaises(HTTPException) as error:
            require_api_key("not-a-router-key")

        self.assertEqual(error.exception.status_code, 401)


class ApiSmokeTests(unittest.TestCase):
    def test_health_and_dashboard_are_available_without_backend_credentials(self) -> None:
        with TestClient(app) as client:
            health = client.get("/health")
            dashboard = client.get("/")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("FreeRouter Dashboard", dashboard.text)


if __name__ == "__main__":
    unittest.main()
