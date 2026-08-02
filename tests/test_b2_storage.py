import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botocore.exceptions import ClientError

import matchcast_settings
from storage import b2 as storage_b2
from backend.routers import storage as storage_router


class B2StorageTests(unittest.TestCase):
    def test_placeholder_b2_credentials_are_not_considered_configured(self):
        with patch.object(matchcast_settings, "B2_APPLICATION_KEY_ID", "your-b2-key-id-here"), \
             patch.object(matchcast_settings, "B2_APPLICATION_KEY", "your-b2-application-key-here"):
            self.assertFalse(matchcast_settings.b2_configured())

    def test_b2_configured_reloads_values_from_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("B2_APPLICATION_KEY_ID=real-id\nB2_APPLICATION_KEY=real-key\n", encoding="utf-8")

            with patch.object(matchcast_settings, "REPO_ROOT", Path(tmp_dir)):
                os.environ.pop("B2_APPLICATION_KEY_ID", None)
                os.environ.pop("B2_APPLICATION_KEY", None)
                self.assertTrue(matchcast_settings.b2_configured())

    def test_upload_file_wraps_b2_client_error(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("hello")
            temp_path = handle.name

        try:
            class FakeS3Client:
                def upload_file(self, *args, **kwargs):
                    raise ClientError(
                        {"Error": {"Code": "InvalidAccessKeyId", "Message": "Malformed Access Key Id"}},
                        "PutObject",
                    )

            with patch.object(storage_b2, "_get_s3_client", return_value=FakeS3Client()):
                with self.assertRaises(RuntimeError) as ctx:
                    storage_b2.upload_file(temp_path, "match-123", "test.txt")

            message = str(ctx.exception)
            self.assertIn("InvalidAccessKeyId", message)
            self.assertIn("Malformed Access Key Id", message)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_upload_status_marks_partial_results_as_failed(self):
        with patch.object(storage_router, "upload_match_assets", return_value={
            "status": "partial",
            "asset_count": 0,
            "total_size_bytes": 0,
            "errors": ["bad credentials"],
        }):
            storage_router._run_upload("match-123", "", "")

        job = storage_router._storage_jobs["match-123"]
        self.assertEqual(job.phase, "failed")
        self.assertEqual(job.asset_count, 0)
        self.assertIn("bad credentials", job.errors[0])


if __name__ == "__main__":
    unittest.main()
