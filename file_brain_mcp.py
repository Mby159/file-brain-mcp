#!/usr/bin/env python3
"""
File Brain MCP - Local File System Intelligent Management

Usage:
    # As CLI
    python file_brain_mcp.py index-dir ./docs/
    python file_brain_mcp.py search "关键词"
    python file_brain_mcp.py ask "文件在哪里？"

    # As MCP server
    python file_brain_mcp.py --mcp
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class SimpleSearchEngine:
    def __init__(self, index_dir: str = ".file_brain_index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        self.index_file = self.index_dir / "index.json"
        self.index: Dict[str, Dict] = {}
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index = json.load(f)

    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def _read_file(self, file_path: Path) -> Optional[str]:
        ext = file_path.suffix.lower()
        try:
            if ext in [
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
                ".csv",
                ".log",
                ".sh",
                ".bat",
                ".ps1",
            ]:
                return file_path.read_text(encoding="utf-8", errors="ignore")
            elif ext == ".pdf":
                return f"[PDF: {file_path.name}]"
            elif ext in [".docx", ".xlsx", ".pptx"]:
                return f"[Office: {file_path.name}]"
            else:
                return None
        except Exception:
            return None

    def index_file(self, file_path: Path) -> bool:
        content = self._read_file(file_path)
        if not content:
            return False

        source = str(file_path.absolute())
        self.index[source] = {
            "content": content,
            "file_type": file_path.suffix,
            "title": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime,
        }
        self._save_index()
        return True

    def index_directory(
        self,
        directory: Path,
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        stats = {"success": 0, "failed": 0, "skipped": 0}

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
                ".csv",
                ".log",
                ".sh",
                ".bat",
                ".ps1",
            ]

        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in extensions:
                stats["skipped"] += 1
                continue
            if self.index_file(file_path):
                stats["success"] += 1
            else:
                stats["failed"] += 1

        return stats

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        for source, data in self.index.items():
            content_lower = data["content"].lower()
            if query_lower in content_lower:
                lines = data["content"].split("\n")
                matches = [
                    i for i, line in enumerate(lines) if query_lower in line.lower()
                ]

                context = ""
                if matches:
                    idx = matches[0]
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 3)
                    context = "\n".join(lines[start:end])

                score = content_lower.count(query_lower)
                results.append(
                    {
                        "source": source,
                        "title": data["title"],
                        "file_type": data["file_type"],
                        "score": score,
                        "context": context[:500],
                        "preview": data["content"][:200],
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def list_sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "source": source,
                "title": data["title"],
                "file_type": data["file_type"],
                "size": data["size"],
            }
            for source, data in self.index.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        total_files = len(self.index)
        total_content = sum(len(d["content"]) for d in self.index.values())
        file_types = {}
        for d in self.index.values():
            ft = d["file_type"]
            file_types[ft] = file_types.get(ft, 0) + 1

        return {
            "total_files": total_files,
            "total_content_chars": total_content,
            "file_types": file_types,
        }

    def delete(self, source: str) -> bool:
        if source in self.index:
            del self.index[source]
            self._save_index()
            return True
        return False

    def clear(self) -> bool:
        self.index = {}
        self._save_index()
        return True


class QaEngine:
    def __init__(self, search_engine: SimpleSearchEngine):
        self.search_engine = search_engine

    def ask(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        results = self.search_engine.search(question, top_k=top_k)

        if not results:
            return {
                "answer": "No relevant content found.",
                "sources": [],
                "total_found": 0,
            }

        context = "\n\n".join(
            [f"[{r['title']}]\n{r['context']}" for r in results[:3] if r["context"]]
        )

        answer = (
            f"Found {len(results)} related results.\n\nMost relevant content from:\n"
        )
        for r in results[:3]:
            answer += f"- {r['title']} (score: {r['score']})\n"
            if r["context"]:
                answer += f"  Context: {r['context'][:200]}...\n"

        return {
            "answer": answer,
            "sources": [
                {"title": r["title"], "source": r["source"]} for r in results[:3]
            ],
            "total_found": len(results),
        }


async def run_mcp_server():
    if not HAS_MCP:
        print(
            "Error: MCP dependencies not installed. Run: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    server = Server("file-brain")
    engine = SimpleSearchEngine()
    qa = QaEngine(engine)

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="search",
                description="Search indexed files for content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "top_k": {
                            "type": "integer",
                            "description": "Max results",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="index_file",
                description="Index a single file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to index"}
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="index_directory",
                description="Index all files in a directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"},
                        "recursive": {
                            "type": "boolean",
                            "description": "Recursive search",
                            "default": True,
                        },
                        "extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File extensions to index",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="ask",
                description="Ask questions about indexed content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Question to ask",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Results to consider",
                            "default": 5,
                        },
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="list_indexed",
                description="List all indexed files",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_stats",
                description="Get indexing statistics",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search":
            results = engine.search(arguments["query"], arguments.get("top_k", 10))
            return [
                TextContent(
                    type="text", text=json.dumps(results, ensure_ascii=False, indent=2)
                )
            ]
        elif name == "index_file":
            success = engine.index_file(Path(arguments["path"]))
            stats = engine.get_stats()
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"success": success, "stats": stats}, indent=2),
                )
            ]
        elif name == "index_directory":
            stats = engine.index_directory(
                Path(arguments["path"]),
                arguments.get("recursive", True),
                arguments.get("extensions"),
            )
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
        elif name == "ask":
            result = qa.ask(arguments["question"], arguments.get("top_k", 5))
            return [
                TextContent(
                    type="text", text=json.dumps(result, ensure_ascii=False, indent=2)
                )
            ]
        elif name == "list_indexed":
            sources = engine.list_sources()
            return [
                TextContent(
                    type="text", text=json.dumps(sources, ensure_ascii=False, indent=2)
                )
            ]
        elif name == "get_stats":
            stats = engine.get_stats()
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
        raise ValueError(f"Unknown tool: {name}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    engine = SimpleSearchEngine()
    qa = QaEngine(engine)
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        print("\nAvailable commands: search, index, index-dir, ask, list, stats, clear")
        sys.exit(1)

    cmd = args[0]

    if cmd == "search":
        query = " ".join(args[1:]) if len(args) > 1 else input("Query: ")
        results = engine.search(query)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif cmd == "index":
        if len(args) < 2:
            print("Usage: file_brain_mcp.py index <file_path>")
            sys.exit(1)
        success = engine.index_file(Path(args[1]))
        print(f"Indexed: {success}")

    elif cmd == "index-dir":
        if len(args) < 2:
            print("Usage: file_brain_mcp.py index-dir <directory_path>")
            sys.exit(1)
        stats = engine.index_directory(Path(args[1]))
        print(json.dumps(stats, indent=2))

    elif cmd == "ask":
        question = " ".join(args[1:]) if len(args) > 1 else input("Question: ")
        result = qa.ask(question)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "list":
        sources = engine.list_sources()
        print(json.dumps(sources, ensure_ascii=False, indent=2))

    elif cmd == "stats":
        print(json.dumps(engine.get_stats(), indent=2))

    elif cmd == "clear":
        engine.clear()
        print("Index cleared")

    elif cmd == "--mcp":
        asyncio.run(run_mcp_server())

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
