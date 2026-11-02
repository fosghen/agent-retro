import io
import unittest
from contextlib import redirect_stdout

from agent_retro.cli import main


class CliTests(unittest.TestCase):
    def test_help_exits_successfully(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("Local-first retrospectives", output.getvalue())


if __name__ == "__main__":
    unittest.main()
