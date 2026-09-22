from __future__ import annotations

import runpy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/test_sql_server.py"


class SqlServerHarnessTests(unittest.TestCase):
    def test_startup_failure_surfaces_output_and_redacts_generated_password(self) -> None:
        result = subprocess.CompletedProcess(
            ["docker", "run"],
            125,
            stdout="image pull detail\n",
            stderr="daemon failure with Test!harness-secret\n",
        )
        with (
            patch.object(sys, "argv", [str(SCRIPT), "--accept-eula"]),
            patch("subprocess.check_output", return_value="amd64\n"),
            patch("subprocess.run", return_value=result),
            patch("secrets.token_urlsafe", return_value="harness-secret"),
            self.assertRaises(RuntimeError) as raised,
        ):
            runpy.run_path(str(SCRIPT), run_name="__main__")
        message = str(raised.exception)
        self.assertIn("Docker run failed (exit 125)", message)
        self.assertIn("image pull detail", message)
        self.assertIn("daemon failure with [REDACTED]", message)
        self.assertNotIn("harness-secret", message)

    def test_startup_failure_uses_either_stream_or_silent_fallback(self) -> None:
        for stdout, stderr in (("pull detail", ""), ("", "daemon detail"), ("", "")):
            with self.subTest(stdout=stdout, stderr=stderr):
                result = subprocess.CompletedProcess(["docker", "run"], 125, stdout, stderr)
                with (
                    patch.object(sys, "argv", [str(SCRIPT), "--accept-eula"]),
                    patch("subprocess.check_output", return_value="amd64\n"),
                    patch("subprocess.run", return_value=result),
                    self.assertRaises(RuntimeError) as raised,
                ):
                    runpy.run_path(str(SCRIPT), run_name="__main__")
                self.assertIn(stdout or stderr or "No output captured.", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
