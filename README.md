# File Brain MCP / 文件大脑 MCP

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**English:** A local file system intelligent management tool with search, index, and Q&A capabilities. Built with MCP protocol support.

**中文:** 本地文件系统智能管理工具，提供搜索、索引和问答功能。支持 MCP 协议。

---

## Features / 功能特点

- **Search** - 快速搜索已索引的文件内容
- **Index** - 索引整个目录或单个文件
- **Q&A** - 基于索引内容回答问题
- **CLI & MCP** - 命令行和 MCP Server 双接口
- **Lightweight** - 零依赖，简单易用

## Supported File Types / 支持的文件类型

| Extension | Type |
|-----------|------|
| .py | Python |
| .js, .ts | JavaScript/TypeScript |
| .json, .yaml, .yml | Config files |
| .txt, .md | Text/Markdown |
| .html, .css, .xml | Web files |
| .sh, .bat, .ps1 | Scripts |
| .csv, .log | Data/Logs |
| .pdf, .docx, .xlsx, .pptx | Documents (basic) |

---

## Installation / 安装

```bash
# Clone / 克隆
git clone https://github.com/Mby159/file-brain-mcp.git
cd file-brain-mcp

# Install / 安装
pip install -e .

# Or / 或者
pip install .
```

### Install with MCP support / 安装 MCP 支持

```bash
pip install -e ".[mcp]"
```

---

## Usage / 使用方法

### CLI

```bash
# Index a directory / 索引目录
python file_brain_mcp.py index-dir ./src/

# Search / 搜索
python file_brain_mcp.py search "关键词"

# Ask questions / 问答
python file_brain_mcp.py ask "项目用了什么数据库？"

# List indexed files / 列出已索引文件
python file_brain_mcp.py list

# Show stats / 显示统计
python file_brain_mcp.py stats

# Clear index / 清空索引
python file_brain_mcp.py clear
```

### Python API

```python
from file_brain_mcp import SimpleSearchEngine, QaEngine

engine = SimpleSearchEngine()

# Index a directory / 索引目录
stats = engine.index_directory("./src")
print(f"Indexed: {stats}")

# Search / 搜索
results = engine.search("关键词")
for r in results:
    print(f"{r['title']}: {r['context'][:100]}")

# Ask / 问答
qa = QaEngine(engine)
answer = qa.ask("项目用了什么数据库？")
print(answer['answer'])
```

### MCP Server

```bash
# Start MCP server / 启动 MCP Server
python file_brain_mcp.py --mcp

# Configure in OpenCode or other MCP clients / 在 OpenCode 或其他 MCP 客户端中配置
```

#### MCP Configuration / MCP 配置

```json
{
  "mcpServers": {
    "file-brain": {
      "command": "python",
      "args": ["/path/to/file_brain_mcp.py", "--mcp"]
    }
  }
}
```

---

## Examples / 示例

### Index and Search / 索引和搜索

```python
from file_brain_mcp import SimpleSearchEngine

engine = SimpleSearchEngine()

# Index current project / 索引当前项目
stats = engine.index_directory(".", recursive=True)
print(stats)
# {'success': 72, 'failed': 0, 'skipped': 280}

# Search / 搜索
results = engine.search("config")
for r in results[:5]:
    print(f"[{r['title']}] {r['score']}")
    print(f"  {r['context'][:100]}")
    print()
```

### Q&A / 问答

```python
from file_brain_mcp import SimpleSearchEngine, QaEngine

engine = SimpleSearchEngine()
engine.index_directory("./src")

qa = QaEngine(engine)

# Ask about the project / 询问项目
answer = qa.ask("这个项目使用什么数据库？")
print(answer['answer'])
print()
print("Sources:", [s['title'] for s in answer['sources']])
```

---

## Workflow / 工作流程

```
1. index-dir   →  Index your project / 索引项目
       ↓
2. search/ask  →  Search or ask questions / 搜索或问答
       ↓
3. get results →  Get results / 获取结果
```

---

## License / 许可证

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing / 贡献

Issues and Pull Requests are welcome! / 欢迎提交 Issue 和 Pull Request！
