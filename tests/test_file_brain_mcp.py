import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "file_brain_mcp.py"


def run_cmd(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def test_cli_indexes_and_searches_hyphenated_tokens(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "note.md").write_text("privacy-guard detects and redacts secrets", encoding="utf-8")

    index_dir = tmp_path / "index"
    index_result = run_cmd("--index-dir", str(index_dir), "index-dir", str(docs))
    assert json.loads(index_result.stdout)["success"] == 1

    search_result = run_cmd("--index-dir", str(index_dir), "search", "privacy guard")
    hits = json.loads(search_result.stdout)

    assert hits
    assert hits[0]["title"] == "note.md"
    assert "privacy-guard" in hits[0]["preview"]


def test_default_excludes_env_and_key_files(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "public.md").write_text("safe public document", encoding="utf-8")
    (docs / ".env").write_text("SECRET_TOKEN=abc", encoding="utf-8")
    (docs / "private.key").write_text("PRIVATE KEY", encoding="utf-8")

    index_dir = tmp_path / "index"
    run_cmd("--index-dir", str(index_dir), "index-dir", str(docs))
    listed = json.loads(run_cmd("--index-dir", str(index_dir), "list").stdout)
    sources = "\n".join(item["source"] for item in listed)

    assert "public.md" in sources
    assert ".env" not in sources
    assert "private.key" not in sources


def test_separator_form_reaches_mcp_mode_without_unknown_command() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--", "--mcp"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )

    assert "Unknown command" not in proc.stdout + proc.stderr
