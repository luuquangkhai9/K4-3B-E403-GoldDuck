"""Resolve data/config independently of the caller's working directory."""
from pathlib import Path

from dotenv import load_dotenv

CODE_ROOT = Path(__file__).resolve().parents[1]


def runtime_root(code_root=CODE_ROOT):
    """Prefer codebase config; reuse an existing checkout's root data and .env."""
    code_root = Path(code_root)
    parent = code_root.parent
    if not (code_root / ".env").is_file() and code_root.name == "codebase":
        if (parent / ".env").is_file() or (parent / "data/index/slides.json").is_file():
            return parent
    return code_root


def load_environment(code_root=CODE_ROOT):
    root = runtime_root(code_root)
    load_dotenv(root / ".env")
    return root
