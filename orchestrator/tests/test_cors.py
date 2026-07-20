import unittest

from fastapi.testclient import TestClient

from main import app


class CorsIntegrationTests(unittest.TestCase):
    def test_localhost_and_loopback_origins_are_allowed_for_preflight(self):
        with TestClient(app) as client:
            response = client.options(
                "/integrations/slack",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization",
                },
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:5173")


if __name__ == "__main__":
    unittest.main()
