from __future__ import annotations

import importlib
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "out",
}

TOKEN_PATTERNS = [
    re.compile(r"apify_api_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]
ASSIGNMENT_PATTERN = re.compile(r"APIFY_TOKEN\s*=\s*[A-Za-z0-9]")


def _tracked_text_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in {
            ".py",
            ".toml",
            ".md",
            ".yml",
            ".yaml",
            ".json",
            ".txt",
            ".example",
            "",
        }:
            if path.name == ".env":
                continue
            files.append(path)
    return files


def test_no_token_shaped_strings_or_assignments() -> None:
    for path in _tracked_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in TOKEN_PATTERNS:
            assert not pattern.search(text), f"Token-shaped string in {path}"
        for line in text.splitlines():
            if "APIFY_TOKEN" not in line:
                continue
            assert not ASSIGNMENT_PATTERN.search(line), f"Token assignment in {path}: {line}"


def test_only_apify_client_module_imports_apify_client() -> None:
    package = REPO_ROOT / "src" / "prospectforge"
    for path in package.rglob("*.py"):
        if path.name == "apify_client.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "import apify_client" not in text
        assert "from apify_client" not in text


def test_package_imports_without_secret_env(monkeypatch) -> None:
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert "APIFY_TOKEN" not in os.environ
    module = importlib.import_module("prospectforge")
    importlib.reload(module)
    assert module.__version__
