#!/usr/bin/env python3
"""Dependency-free smoke test for the manage-ckg CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "ckg.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(ROOT),
        check=True,
        text=True,
        capture_output=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="manage-ckg-") as tmp:
        bundle = Path(tmp) / "sample"
        run("init", str(bundle))
        run("build", str(bundle))
        result = run("validate", str(bundle))
        report = json.loads(result.stdout)
        assert report["status"] == "pass", report
        assert report["concepts"] == 2, report
        assert report["edges"] == 1, report
        assert (bundle / "build" / "graph_index.json").exists()
        assert (bundle / "visualizations" / "sample.html").exists()
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
