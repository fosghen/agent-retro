"""Create and verify locks for one canonical Agent Retro checkout."""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 -- fixed git inspection commands, no shell
from pathlib import Path

LOCK_PATH = Path(".local/state/agent-retro/install-lock.json")


class LockError(RuntimeError):
    """The install lock or its source checkout cannot be verified."""


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(  # noqa: S603  # nosec B603
        ["git", "-C", str(root), *arguments],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = "canonical source is not a readable git checkout"
        raise LockError(message)
    return result.stdout


def snapshot(root: Path) -> dict[str, str]:
    """Describe the selected revision and all of its tracked file contents."""
    root = root.resolve()
    revision = _git(root, "rev-parse", "HEAD").strip()
    digest = hashlib.sha256()
    for relative in _git(root, "ls-files", "-z").split("\0"):
        if not relative:
            continue
        path = root / relative
        if not path.is_file():
            raise LockError(f"tracked file is missing: {relative}")  # noqa: EM102, TRY003
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return {"source": str(root), "revision": revision, "content_hash": digest.hexdigest()}


def read(home: Path) -> dict[str, str]:
    """Read a complete lock or fail closed."""
    try:
        value = json.loads((home / LOCK_PATH).read_text())
        result = {name: value[name] for name in ("source", "revision", "content_hash")}
        if not all(isinstance(field, str) and field for field in result.values()):
            raise ValueError  # noqa: TRY301
    except (OSError, ValueError, KeyError, TypeError) as error:
        message = "install lock is missing or invalid"
        raise LockError(message) from error
    return result


def write(home: Path, value: dict[str, str]) -> None:
    """Atomically persist the verified canonical source snapshot."""
    path = home / LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True) + "\n")
    temporary.replace(path)
