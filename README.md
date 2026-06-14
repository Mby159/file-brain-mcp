# File Brain MCP

本地文件系统智能管理 MCP/CLI：索引、搜索、问答。

## 功能

- 关键词搜索
- 中文/英文 token 搜索
- 向量搜索（可选，需要 `numpy`）
- 中文分词（可选，需要 `jieba`）
- 增量索引
- `.gitignore` + 默认隐私/缓存排除
- MCP Server

## 安装

最小 CLI：

```bash
python src/file_brain_mcp.py --help
```

可选能力：

```bash
pip install mcp jieba numpy
```

说明：

- 不装 `numpy` 也能使用普通搜索和问答。
- 不装 `jieba` 也能用内置中英文 token 搜索。
- 只有运行 MCP server 时才需要 `mcp`。

## CLI 使用

建议使用专用索引目录，避免污染项目根目录：

```bash
python src/file_brain_mcp.py --index-dir .file_brain_index index-dir ./docs
python src/file_brain_mcp.py --index-dir .file_brain_index search "关键词"
python src/file_brain_mcp.py --index-dir .file_brain_index vector-search "语义查询"
python src/file_brain_mcp.py --index-dir .file_brain_index ask "问题"
python src/file_brain_mcp.py --index-dir .file_brain_index reindex ./docs
python src/file_brain_mcp.py --index-dir .file_brain_index list
python src/file_brain_mcp.py --index-dir .file_brain_index stats
```

排除额外路径/模式：

```bash
python src/file_brain_mcp.py --index-dir .file_brain_index --exclude "private/**" index-dir ./docs
```

输出格式：

```bash
python src/file_brain_mcp.py --index-dir .file_brain_index --format table search "privacy"
```

## MCP Server

```bash
python src/file_brain_mcp.py --index-dir .file_brain_index --mcp
```

兼容某些启动器传入的分隔符形式：

```bash
python src/file_brain_mcp.py -- --mcp
```

## 默认排除

索引目录会读取目标目录下的 `.gitignore`，并额外排除常见缓存/环境/密钥路径：

```text
.git
__pycache__
node_modules
.pytest_cache
.mypy_cache
.ruff_cache
.venv
venv
dist
build
.env
*.env
*.key
*.pem
secrets
secrets/**
```

这只是本地索引的安全默认值；如果要索引敏感目录，需要显式调整代码或放宽排除规则。

## 开发自检

```bash
python -m py_compile src/file_brain_mcp.py
rm -rf .test_idx
python src/file_brain_mcp.py --index-dir .test_idx index-dir skills
python src/file_brain_mcp.py --index-dir .test_idx search privacy
python src/file_brain_mcp.py --index-dir .test_idx ask "privacy guard 做什么"
python src/file_brain_mcp.py -- --mcp
```
