\---

name: core-context

description: File-Brain 项目家族核心上下文，包括 file-brain-mcp 和 privacy-guard

\---



你正在为以下项目家族开发和维护代码：



核心项目：

\- File-Brain：本地智能文件管理系统，支持多格式解析、向量搜索、知识图谱、实时监控和智能组织。

\- SplitMind：隐私优先的多智能体任务编排系统，负责任务拆分、敏感信息处理和可信结果聚合。



当前子模块：

\- file-brain-mcp：File-Brain 的 MCP 实现，提供本地文件系统的智能管理功能，包括关键词搜索、语义向量搜索、增量索引、中文分词（jieba）、AI Q\&A，以及 MCP Server 模式。

\- privacy-guard：敏感信息防护模块，负责检测（手机号、身份证、银行卡、邮箱、微信/QQ、IP 等）、脱敏（mask/redact）、恢复、自定义规则、风险等级分类，支持批量处理和 MCP Server 模式。



开发原则（必须严格遵守）：

\- 强隐私优先：所有涉及用户数据的操作都要经过 privacy-guard 处理，避免不必要的数据泄露。

\- 模块化与可集成：file-brain-mcp 和 privacy-guard 要方便集成到 File-Brain 和 SplitMind 中（支持 MCP 协议）。

\- 代码风格：Python，带完整类型提示，清晰注释，错误处理完善。

\- 中文支持良好（尤其文件路径、搜索、分词）。

\- 尽量保持本地执行，减少对外部服务的依赖。



当用户提出需求时，先参考这些背景，再进行规划和编码。

