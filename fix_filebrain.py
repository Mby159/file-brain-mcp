import pathlib
import fnmatch

p = pathlib.Path("D:/opencode1/file_brain_mcp.py")
c = p.read_text(encoding="utf-8")

# Add gitignore support
old_code = """    def index_directory(
        self,
        directory: Path,
        recursive: bool = True,
        extensions: List[str] = None,
        incremental: bool = True,
    ) -> Dict[str, int]:
        stats = {"success": 0, "failed": 0, "skipped": 0, "updated": 0}

        if extensions is None:
            extensions = [
                ".txt",
                ".md",
                ".py",
                ".js",
                ".ts",
                ".json",
                ".yaml",
                ".yml",
                ".html",
                ".css",
                ".xml",
            ]

        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in extensions:
                stats["skipped"] += 1
                continue"""

new_code = """    def _load_gitignore(self, directory: Path) -> set:
        gitignore_path = directory / ".gitignore"
        patterns = set()
        if gitignore_path.exists():
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)
        default_ignore = {".git", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache"}
        patterns.update(default_ignore)
        return patterns

    def _should_ignore(self, path: Path, patterns: set, is_recursive: bool) -> bool:
        rel_path = path.name
        for pattern in patterns:
            if pattern.startswith("**/"):
                if fnmatch.fnmatch(rel_path, pattern[3:]) or fnmatch.fnmatch(str(path), pattern):
                    return True
            elif "/" in pattern or (is_recursive and "**" in pattern):
                if fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(str(path).replace("\\\\", "/"), pattern):
                    return True
            else:
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, f"*/{pattern}") or fnmatch.fnmatch(rel_path, f"**/{pattern}"):
                    return True
        return False

    def index_directory(
        self,
        directory: Path,
        recursive: bool = True,
        extensions: List[str] = None,
        incremental: bool = True,
        use_gitignore: bool = True,
    ) -> Dict[str, int]:
        stats = {"success": 0, "failed": 0, "skipped": 0, "updated": 0}

        if extensions is None:
            extensions = [
                ".txt",
                ".md",
                ".py",
                ".js",
                ".ts",
                ".json",
                ".yaml",
                ".yml",
                ".html",
                ".css",
                ".xml",
            ]

        ignore_patterns = self._load_gitignore(directory) if use_gitignore else set()
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path, ignore_patterns, recursive):
                stats["skipped"] += 1
                continue
            if file_path.suffix.lower() not in extensions:
                stats["skipped"] += 1
                continue"""

c = c.replace(old_code, new_code)
p.write_text(c, encoding="utf-8")
print("file_brain_mcp.py updated with gitignore support")
