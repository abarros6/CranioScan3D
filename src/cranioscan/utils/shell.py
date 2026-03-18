"""Subprocess runner with logging, timeout, and error handling.

All external tool invocations (COLMAP, OpenMVS) go through run_command()
so they get consistent logging, timeout enforcement, and error reporting.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_command(
    cmd: list[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    description: str = "",
) -> str:
    """Run a subprocess command with logging and error handling.

    Streams stdout/stderr to the debug log. On failure, logs the full
    command and return code, then raises RuntimeError.

    Args:
        cmd: Command and arguments as a list of strings.
        cwd: Working directory for the subprocess. Defaults to current dir.
        timeout: Timeout in seconds. None = no timeout.
        description: Human-readable description for log messages.

    Returns:
        Combined stdout + stderr output as a string.

    Raises:
        RuntimeError: If the subprocess exits with a non-zero return code.
        subprocess.TimeoutExpired: If the command exceeds the timeout.
    """
    label = description or cmd[0]
    logger.debug("Running [%s]: %s", label, " ".join(str(c) for c in cmd))
    if cwd:
        logger.debug("  cwd: %s", cwd)

    # Propagate DYLD_LIBRARY_PATH so OpenMVS binaries can find Homebrew libs (libjxl etc.)
    env = os.environ.copy()
    dyld = os.environ.get("DYLD_LIBRARY_PATH", "")
    homebrew_lib = "/opt/homebrew/lib"
    if homebrew_lib not in dyld:
        env["DYLD_LIBRARY_PATH"] = f"{homebrew_lib}:{dyld}".rstrip(":")

    try:
        result = subprocess.run(
            [str(c) for c in cmd],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"[{label}] Binary not found: {cmd[0]}. "
            "Is it installed and in PATH? See scripts/setup_mac.sh."
        ) from exc

    output = (result.stdout or "") + (result.stderr or "")
    for line in output.splitlines():
        logger.debug("[%s] %s", label, line)

    if result.returncode != 0:
        raise RuntimeError(
            f"[{label}] Failed with return code {result.returncode}.\n"
            f"Command: {' '.join(str(c) for c in cmd)}\n"
            f"Output:\n{output[-2000:]}"  # Last 2000 chars to avoid flooding
        )

    logger.info("[%s] completed successfully", label)
    return output
