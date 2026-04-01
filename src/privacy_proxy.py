#!/usr/bin/env python3
"""
隐私代理 MCP 服务器 - 自动处理用户输入中的敏感信息
拦截所有用户输入，进行检测和脱敏，然后返回脱敏后的内容

注意：这是一个概念验证，展示了如何实现"用户输入 → 检测 → 脱敏 → AI收到脱敏后的内容"
由于 OpenCode 目前不支持 API 级别的输入拦截，这需要与 OpenCode 集成。

工作原理：
1. 接收用户输入文本
2. 调用 privacy-guard 检测敏感信息
3. 自动脱敏高风险信息
4. 返回脱敏后的安全文本

使用方式：
作为 MCP 服务器运行：
    python privacy_proxy.py --mcp

或作为独立工具：
    python privacy_proxy.py redact "用户输入文本"
"""

import json
import sys
import asyncio
from pathlib import Path

# 添加 privacy-guard 到路径
privacy_guard_path = Path(__file__).parent / "privacy-guard"
sys.path.insert(0, str(privacy_guard_path))


def safe_print(text):
    """安全打印，处理 Windows 编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        # 使用 sys.stdout.buffer 直接写入字节
        import io

        if isinstance(text, str):
            # 替换无法编码的字符为问号
            safe_text = text.encode("gbk", errors="replace").decode("gbk")
            print(safe_text)
        else:
            print(text)


try:
    from privacy_guard import PrivacyGuard

    HAS_PRIVACY_GUARD = True
except ImportError:
    HAS_PRIVACY_GUARD = False
    print("Error: privacy_guard not found", file=sys.stderr)

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class PrivacyProxy:
    """隐私代理 - 自动处理用户输入"""

    def __init__(self):
        if not HAS_PRIVACY_GUARD:
            raise ImportError("privacy_guard module not available")
        self.guard = PrivacyGuard()

    def process_user_input(self, text: str, auto_redact: bool = True) -> dict:
        """
        处理用户输入

        Args:
            text: 用户输入文本
            auto_redact: 是否自动脱敏高风险信息

        Returns:
            处理结果
        """
        # 1. 检测敏感信息
        detection = self.guard.detect(text)

        # 2. 分析风险
        high_risk = [d for d in detection if d["risk_level"] in ["high", "critical"]]
        any_sensitive = len(detection) > 0

        # 3. 如果有敏感信息且启用自动脱敏
        if any_sensitive and auto_redact:
            redacted = self.guard.redact(text, strategy="placeholder")
            return {
                "original": text,
                "redacted": redacted["text"],
                "detection": detection,
                "high_risk_count": len(high_risk),
                "auto_redacted": True,
                "mapping": redacted["mapping"],
            }
        else:
            return {
                "original": text,
                "redacted": text,  # 保持原样
                "detection": detection,
                "high_risk_count": len(high_risk),
                "auto_redacted": False,
                "mapping": {},
            }

    def safe_user_input(self, text: str) -> str:
        """返回安全的用户输入（自动脱敏）"""
        result = self.process_user_input(text, auto_redact=True)
        return result["redacted"]

    def get_risk_report(self, text: str) -> str:
        """获取风险报告"""
        result = self.process_user_input(text, auto_redact=False)
        report = []

        if result["detection"]:
            detection = result["detection"]
            report.append(f"⚠️ Found {len(detection)} sensitive items:")
            for item in detection:
                report.append(
                    f"  - {item['info_type']}: {item['original_value'][:20]}... (risk: {item['risk_level']})"
                )

        if result["auto_redacted"]:
            report.append("✅ Auto-redacted")

        return "\n".join(report) if report else "✅ No sensitive info found"


async def run_mcp_server():
    """运行 MCP 服务器"""
    if not HAS_MCP:
        print("Error: MCP dependencies not installed", file=sys.stderr)
        sys.exit(1)

    server = Server("privacy-proxy")
    proxy = PrivacyProxy()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="safe_input",
                description="安全处理用户输入，自动检测和脱敏敏感信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "用户输入文本"}
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="analyze_input",
                description="分析用户输入中的敏感信息风险",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "用户输入文本"}
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="batch_safe",
                description="批量安全处理多个用户输入",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "texts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "用户输入文本列表",
                        }
                    },
                    "required": ["texts"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "safe_input":
            text = arguments["text"]
            safe_text = proxy.safe_user_input(text)
            detection = proxy.guard.detect(text)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "safe_text": safe_text,
                            "original": text,
                            "has_sensitive_info": len(detection) > 0,
                            "detection_count": len(detection),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]

        elif name == "analyze_input":
            text = arguments["text"]
            report = proxy.get_risk_report(text)
            detection = proxy.guard.detect(text)

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "report": report,
                            "detection": detection,
                            "risk_level": "high"
                            if any(
                                d["risk_level"] in ["high", "critical"]
                                for d in detection
                            )
                            else "low",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]

        elif name == "batch_safe":
            texts = arguments["texts"]
            results = []

            for text in texts:
                safe_text = proxy.safe_user_input(text)
                detection = proxy.guard.detect(text)
                results.append(
                    {
                        "original": text,
                        "safe_text": safe_text,
                        "has_sensitive_info": len(detection) > 0,
                    }
                )

            return [
                TextContent(
                    type="text", text=json.dumps(results, ensure_ascii=False, indent=2)
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    """命令行入口"""
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        asyncio.run(run_mcp_server())
    elif len(sys.argv) > 2 and sys.argv[1] == "redact":
        # 命令行脱敏模式
        text = " ".join(sys.argv[2:])
        proxy = PrivacyProxy()
        safe_text = proxy.safe_user_input(text)
        print(safe_text)
    elif len(sys.argv) > 2 and sys.argv[1] == "analyze":
        # 命令行分析模式
        text = " ".join(sys.argv[2:])
        proxy = PrivacyProxy()
        report = proxy.get_risk_report(text)
        safe_print(report)
    else:
        print(__doc__)
        print("\nUsage:")
        print("  As MCP server: python privacy_proxy.py --mcp")
        print("  As CLI tool:   python privacy_proxy.py redact 'user input'")
        print("  Analyze:       python privacy_proxy.py analyze 'user input'")
        sys.exit(1)


if __name__ == "__main__":
    main()
