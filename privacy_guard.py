#!/usr/bin/env python3
import json
import re
import sys
import os
import pathlib
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CustomRule:
    name: str
    pattern: str
    risk_level: str
    replace_with: str = "[REDACTED]"


class PrivacyGuard:
    def __init__(self):
        self._patterns = self._init_patterns()
        self._counter: Dict[str, int] = {}
        self._last_mapping: Dict[str, str] = {}
        self._custom_rules: List[CustomRule] = []
        self._config_file = str(
            pathlib.Path(__file__).parent / ".privacy_guard_config.json"
        )
        self._load_config()

    def _luhn_check(self, card_number: str) -> bool:
        digits = [int(d) for d in card_number if d.isdigit()]
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    def _init_patterns(self) -> Dict[str, re.Pattern]:
        return {
            "phone": re.compile(r"(?<![\d\-])(?:\+?86[-\s]?)?(1[3-9]\d{9})(?![\d\-])"),
            "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
            "id_card_cn": re.compile(
                r"(?<![\dXx])\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![\dXx])"
            ),
            "bank_card": re.compile(r"(?<![a-zA-Z0-9])(\d{12,19})(?![a-zA-Z0-9])"),
            "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
            "ipv4": re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            ),
            "ipv6": re.compile(
                r"(?<![:\w])([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}(?![:\w])"
            ),
            "url": re.compile(
                r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
            ),
            "address_cn": re.compile(
                r"(?:[^\w](?:省|市|区|县|路|街|道|号|弄|栋|楼|室|村|镇|乡)[^\n,，]{5,30})|(?:[\u4e00-\u9fa5]{2,6}(?:省|市|区|县))"
            ),
            "wechat": re.compile(
                r"(?<![a-zA-Z0-9])(?:微信号|微信[:：\s]*)[a-zA-Z][a-zA-Z0-9_-]{5,19}(?![a-zA-Z0-9])"
            ),
            "qq": re.compile(
                r"(?<![a-zA-Z0-9])(?:QQ|qq)[:：\s]*(\d{5,11})(?![a-zA-Z0-9])"
            ),
            "license_plate": re.compile(
                r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]"
            ),
            "amount": re.compile(
                r"(?:[￥¥$]\s*[\d,]+(?:\.\d{2})?)|(?:[\d,]+(?:\.\d{2})?\s*(?:元|美元|USD|CNY|RMB))"
            ),
            "china_passport": re.compile(r"E\d{8,9}", re.IGNORECASE),
            "china_credit_code": re.compile(r"\b[0-9A-Z]{18}\b"),
            "jwt_token": re.compile(
                r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
            ),
        }

    def _get_risk_level(self, info_type: str) -> str:
        risk_map = {
            "id_card_cn": RiskLevel.CRITICAL,
            "ssn": RiskLevel.CRITICAL,
            "bank_card": RiskLevel.HIGH,
            "wechat": RiskLevel.HIGH,
            "jwt_token": RiskLevel.HIGH,
            "china_passport": RiskLevel.HIGH,
            "china_credit_code": RiskLevel.HIGH,
            "phone": RiskLevel.MEDIUM,
            "email": RiskLevel.MEDIUM,
            "qq": RiskLevel.MEDIUM,
            "address_cn": RiskLevel.MEDIUM,
            "license_plate": RiskLevel.MEDIUM,
            "ipv4": RiskLevel.LOW,
            "ipv6": RiskLevel.LOW,
            "amount": RiskLevel.LOW,
            "url": RiskLevel.LOW,
        }
        return risk_map.get(info_type, RiskLevel.MEDIUM).value

    def _generate_placeholder(self, info_type: str) -> str:
        self._counter[info_type] = self._counter.get(info_type, 0) + 1
        return f"[REDACTED_{info_type.upper()}_{self._counter[info_type]}]"

    def _load_config(self):
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self._custom_rules = [
                        CustomRule(**r) for r in config.get("custom_rules", [])
                    ]
            except Exception:
                pass

    def _save_config(self):
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(
                {"custom_rules": [asdict(r) for r in self._custom_rules]},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def add_custom_rule(
        self,
        name: str,
        pattern: str,
        risk_level: str = "medium",
        replace_with: str = "[REDACTED]",
    ) -> bool:
        try:
            re.compile(pattern)
            self._custom_rules.append(
                CustomRule(
                    name=name,
                    pattern=pattern,
                    risk_level=risk_level,
                    replace_with=replace_with,
                )
            )
            self._save_config()
            return True
        except re.error:
            return False

    def remove_custom_rule(self, name: str) -> bool:
        for i, rule in enumerate(self._custom_rules):
            if rule.name == name:
                del self._custom_rules[i]
                self._save_config()
                return True
        return False

    def list_custom_rules(self) -> List[Dict[str, str]]:
        return [asdict(r) for r in self._custom_rules]

    def _validate_credit_code(self, code: str) -> bool:
        if len(code) != 18:
            return False
        weight = [3, 7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = "0123456789ABCDEFGHJKLMNPQRTUWXY"
        try:
            check_sum = sum(
                (int(c, 36) if c.isdigit() else check_codes.index(c)) * w
                for c, w in zip(code[:17], weight)
            )
            return code[17] == check_codes[check_sum % 31]
        except (ValueError, IndexError):
            return False

    def _detect_in_text(self, text: str) -> List[Dict[str, Any]]:
        detected = []
        for info_type, pattern in self._patterns.items():
            for match in pattern.finditer(text):
                value = match.group()
                if info_type == "bank_card":
                    digits = re.sub(r"\D", "", value)
                    if (
                        len(digits) < 12
                        or len(digits) > 19
                        or not self._luhn_check(digits)
                    ):
                        continue
                if info_type == "china_credit_code" and not self._validate_credit_code(
                    value
                ):
                    continue
                detected.append(
                    {
                        "info_type": info_type,
                        "original_value": value,
                        "placeholder": self._generate_placeholder(info_type),
                        "risk_level": self._get_risk_level(info_type),
                    }
                )
        for rule in self._custom_rules:
            try:
                for match in re.compile(rule.pattern).finditer(text):
                    detected.append(
                        {
                            "info_type": f"custom:{rule.name}",
                            "original_value": match.group(),
                            "placeholder": self._generate_placeholder(rule.name),
                            "risk_level": rule.risk_level,
                            "_replace_with": rule.replace_with,
                        }
                    )
            except re.error:
                continue
        return detected

    def detect(self, text: str) -> List[Dict[str, Any]]:
        self._counter = {}
        return self._detect_in_text(text)

    def batch_detect(self, texts: List[str]) -> List[List[Dict[str, Any]]]:
        self._counter = {}
        return [self._detect_in_text(text) for text in texts]

    def batch_detect_from_file(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            results = [
                {
                    "line": i + 1,
                    "content": line.strip()[:100],
                    "detected": self._detect_in_text(line.strip()),
                }
                for i, line in enumerate(lines)
                if self._detect_in_text(line.strip())
            ]
            return {
                "file": file_path,
                "total_lines": len(lines),
                "lines_with_sensitive": len(results),
                "results": results,
            }
        except Exception as e:
            return {"error": str(e)}

    def redact(self, text: str, strategy: str = "placeholder") -> Dict[str, Any]:
        self._counter = {}
        self._last_mapping = {}
        detected = self._detect_in_text(text)
        if not detected:
            return {"text": text, "mapping": {}, "detected_count": 0}
        redacted_text = text
        for item in sorted(
            detected, key=lambda x: text.find(x["original_value"]), reverse=True
        ):
            placeholder = item["placeholder"]
            original = item["original_value"]
            if strategy == "mask":
                placeholder = self._mask_value(original)
            elif strategy == "remove":
                placeholder = "[REDACTED]"
            elif item.get("_replace_with"):
                suffix = item["placeholder"].split("_")[-1].rstrip("]")
                placeholder = f"{item['_replace_with']}_{suffix}"
            redacted_text = redacted_text.replace(original, placeholder)
            self._last_mapping[placeholder] = original
        return {
            "text": redacted_text,
            "mapping": self._last_mapping,
            "detected_count": len(detected),
        }

    def batch_redact(
        self, texts: List[str], strategy: str = "placeholder"
    ) -> List[Dict[str, Any]]:
        return [self.redact(text, strategy) for text in texts]

    def redact_file(
        self, input_path: str, output_path: str, strategy: str = "placeholder"
    ) -> Dict[str, Any]:
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
            result = self.redact(content, strategy)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["text"])
            return {
                "success": True,
                "input": input_path,
                "output": output_path,
                "detected_count": result["detected_count"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _mask_value(self, value: str) -> str:
        if len(value) <= 4:
            return "*" * len(value)
        elif len(value) <= 8:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        return value[:3] + "*" * (len(value) - 6) + value[-3:]

    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        restored = text
        for placeholder, original in sorted(
            mapping.items(), key=lambda x: len(x[0]), reverse=True
        ):
            restored = restored.replace(placeholder, original)
        return restored

    def export_config_example(self) -> str:
        example = {
            "custom_rules": [
                {
                    "name": "order_id",
                    "pattern": r"[A-Z]{3}\d{10,}",
                    "risk_level": "medium",
                    "replace_with": "[ORDER]",
                }
            ]
        }
        return json.dumps(example, indent=2, ensure_ascii=False)


async def run_mcp_server():
    if not HAS_MCP:
        print("Error: MCP not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)
    server = Server("privacy-guard")
    guard = PrivacyGuard()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="detect",
                description="Detect sensitive information",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            ),
            Tool(
                name="batch_detect",
                description="Detect in multiple texts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "texts": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["texts"],
                },
            ),
            Tool(
                name="batch_detect_file",
                description="Detect in a file",
                inputSchema={
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="redact",
                description="Redact sensitive information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "strategy": {
                            "type": "string",
                            "enum": ["placeholder", "mask", "remove"],
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="batch_redact",
                description="Redact multiple texts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "texts": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["texts"],
                },
            ),
            Tool(
                name="redact_file",
                description="Redact a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "input_path": {"type": "string"},
                        "output_path": {"type": "string"},
                    },
                    "required": ["input_path", "output_path"],
                },
            ),
            Tool(
                name="add_rule",
                description="Add custom rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "pattern": {"type": "string"},
                        "risk_level": {"type": "string"},
                    },
                    "required": ["name", "pattern"],
                },
            ),
            Tool(
                name="list_rules",
                description="List custom rules",
                inputSchema={"type": "object"},
            ),
            Tool(
                name="restore",
                description="Restore redacted text",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "mapping": {"type": "object"},
                    },
                    "required": ["text", "mapping"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "detect":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.detect(arguments["text"]), ensure_ascii=False, indent=2
                    ),
                )
            ]
        elif name == "batch_detect":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.batch_detect(arguments["texts"]),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]
        elif name == "batch_detect_file":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.batch_detect_from_file(arguments["file_path"]),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]
        elif name == "redact":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.redact(
                            arguments["text"], arguments.get("strategy", "placeholder")
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]
        elif name == "batch_redact":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.batch_redact(
                            arguments["texts"], arguments.get("strategy", "placeholder")
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]
        elif name == "redact_file":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.redact_file(
                            arguments["input_path"], arguments["output_path"]
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            ]
        elif name == "add_rule":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": guard.add_custom_rule(
                                arguments["name"],
                                arguments["pattern"],
                                arguments.get("risk_level", "medium"),
                            )
                        },
                        indent=2,
                    ),
                )
            ]
        elif name == "list_rules":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        guard.list_custom_rules(), ensure_ascii=False, indent=2
                    ),
                )
            ]
        elif name == "restore":
            return [
                TextContent(
                    type="text",
                    text=guard.restore(arguments["text"], arguments["mapping"]),
                )
            ]
        raise ValueError(f"Unknown tool: {name}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    guard = PrivacyGuard()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        print(
            "\nCommands: detect, batch-detect, redact, batch-redact, redact-file, add-rule, list-rules, restore, --mcp"
        )
        print("\nConfig example (JSON):")
        print(guard.export_config_example())
        sys.exit(1)
    cmd = args[0]
    if cmd == "detect":
        text = " ".join(args[1:]) if len(args) > 1 else input("Text: ")
        print(json.dumps(guard.detect(text), ensure_ascii=False, indent=2))
    elif cmd == "batch-detect":
        text = (
            " ".join(args[1:]) if len(args) > 1 else input("Texts (comma separated): ")
        )
        print(
            json.dumps(
                guard.batch_detect([t.strip() for t in text.split(",")]),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif cmd == "redact":
        text = " ".join(args[1:]) if len(args) > 1 else input("Text: ")
        print(json.dumps(guard.redact(text), ensure_ascii=False, indent=2))
    elif cmd == "batch-redact":
        text = (
            " ".join(args[1:]) if len(args) > 1 else input("Texts (comma separated): ")
        )
        print(
            json.dumps(
                guard.batch_redact([t.strip() for t in text.split(",")]),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif cmd == "redact-file":
        input_path, output_path = (
            (args[1], args[2])
            if len(args) > 2
            else (input("Input: "), input("Output: "))
        )
        print(json.dumps(guard.redact_file(input_path, output_path), indent=2))
    elif cmd == "add-rule":
        name, pattern = (
            (args[1], args[2])
            if len(args) > 2
            else (input("Name: "), input("Pattern (e.g. r'\\d{10,}'): "))
        )
        print(f"Added: {guard.add_custom_rule(name, pattern)}")
    elif cmd == "list-rules":
        print(json.dumps(guard.list_custom_rules(), ensure_ascii=False, indent=2))
    elif cmd == "restore":
        text, mapping = (
            (args[1], json.loads(args[2]))
            if len(args) > 2
            else (input("Text: "), json.loads(input("Mapping: ")))
        )
        print(guard.restore(text, mapping))
    elif cmd == "--mcp":
        import asyncio

        asyncio.run(run_mcp_server())
    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
