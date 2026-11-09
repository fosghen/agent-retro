"""Enforce the transcript extractor import graph declared by ADR 0004."""

import ast
import sys
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

ALLOWED = {
    "io": set(),
    "metadata": {"io"},
    "normalize": {"io"},
    "aggregate": {"io"},
    "conversation": {"io", "metadata"},
    "session": {"io", "metadata"},
    "tools": {"io"},
    "stream": {"aggregate", "conversation", "io", "session", "tools"},
    "subagents": {"aggregate", "io", "metadata", "normalize"},
    "result": {"aggregate", "io", "normalize", "session", "stream", "subagents", "tools"},
}


def _imports(path: Path) -> set[str]:
    modules = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def violations(root: Path) -> list[str]:
    """Return stable corrective diagnostics for extractor boundary violations."""
    problems = []
    edges: dict[str, set[str]] = {}
    for path in sorted(root.glob("transcript_*.py")):
        source = path.stem.removeprefix("transcript_")
        edges[source] = set()
        for module in sorted(_imports(path)):
            if module == "scripts.extract":
                problems.append(
                    f"transcript_{source} -> scripts.extract violates CLI boundary; "
                    "move shared behavior into agent_retro"
                )
            if not module.startswith("agent_retro.transcript_"):
                continue
            target = module.removeprefix("agent_retro.transcript_")
            edges[source].add(target)
            if target != source and target not in ALLOWED.get(source, set()):
                problems.append(
                    f"transcript_{source} -> transcript_{target} violates projection boundary; "
                    "depend toward io/metadata, not result"
                )
    try:
        tuple(TopologicalSorter(edges).static_order())
    except CycleError as error:
        cycle = error.args[1]
        names = " -> ".join(f"transcript_{name}" for name in cycle)
        problems.append(f"cycle: {names}; remove the upward import")
    return problems


def main() -> int:
    """Check the live package and print actionable diagnostics."""
    problems = violations(Path("src/agent_retro"))
    for problem in problems:
        print(problem, file=sys.stderr)  # noqa: T201
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
