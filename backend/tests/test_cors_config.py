import importlib
import os
import unittest
from unittest.mock import patch


class CorsConfigurationTests(unittest.TestCase):
    def test_default_origins_include_production_frontend(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "sqlite://",
            },
            clear=False,
        ):
            os.environ.pop("ALLOWED_ORIGINS", None)

            from app.core import config

            reloaded = importlib.reload(config)

        self.assertIn(
            "https://construction-scheduler-eight.vercel.app",
            reloaded.ALLOWED_ORIGINS,
        )


if __name__ == "__main__":
    unittest.main()
