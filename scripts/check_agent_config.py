"""Run the pinned, offline agent-configuration quality gate."""

import subprocess  # nosec B404

COMMAND = ["agnix", "--strict", "--target", "codex", "."]


def main() -> None:
    """Validate repository agent configuration for Codex."""
    # The executable and every argument are fixed repository policy.
    subprocess.run(COMMAND, check=True)  # noqa: S603  # nosec B603


if __name__ == "__main__":
    main()
