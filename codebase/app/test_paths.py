import tempfile
from pathlib import Path
import unittest

from app.paths import runtime_root


class PathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.code = self.root / "codebase"
        self.code.mkdir()

    def test_fresh_checkout_uses_codebase(self):
        self.assertEqual(runtime_root(self.code), self.code)

    def test_existing_root_env_is_reused(self):
        (self.root / ".env").touch()
        self.assertEqual(runtime_root(self.code), self.root)

    def test_codebase_env_takes_precedence(self):
        (self.root / ".env").touch()
        (self.code / ".env").touch()
        self.assertEqual(runtime_root(self.code), self.code)

    def test_existing_root_index_is_reused_without_env(self):
        directory = self.root / "data/index"
        directory.mkdir(parents=True)
        (directory / "slides.json").touch()
        self.assertEqual(runtime_root(self.code), self.root)
