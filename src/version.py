"""
Version of the backend: the git commit of its code (hash and date). It comes from NOCUMENT_COMMIT and
NOCUMENT_COMMIT_DATE when set (the Docker image is built without .git and receives them as build arguments, see the
Dockerfile), otherwise from git in the project folder (local runs and the development container).
"""
import os
from pathlib import Path
import subprocess

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent


def backend_version() -> dict:
    """{"commit": full hash, "date": commit date in ISO 8601}; null fields if unknown (no variables and no git)."""
    commit = os.getenv("NOCUMENT_COMMIT", "").strip()
    date = os.getenv("NOCUMENT_COMMIT_DATE", "").strip()
    if not commit:
        try:
            result = subprocess.run(
                # safe.directory: in a container the mounted project belongs to another user, which git refuses.
                ["git", "-c", "safe.directory=*", "-C", str(PROJECT_DIRECTORY), "log", "-1", "--format=%H%n%cI"],
                capture_output=True, text=True, timeout=5, check=True,
            )
            commit, date = (result.stdout.strip().splitlines() + ["", ""])[:2]
        except (OSError, subprocess.SubprocessError):
            commit, date = "", ""
    return {"commit": commit or None, "date": date or None}
