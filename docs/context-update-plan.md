# context.md 更新实施计划

## 1. 目标
在 `D:\opencode1\context.md` 文件的第102行后（即 `(检测 & 脱敏)` 之后）添加以下内容：
- 隐私代理服务器使用指南（6个部分）
- 外部AI系统集成说明（5个部分）

## 2. 当前状态
查看文件第95-110行内容：

```
95: - 配置 OpenCode 使用隐私代理 (opencode.json)
96: - 测试验证隐私处理功能正常工作
97: 
98: **架构**
99: 用户 → OpenCode → 隐私代理服务器 (localhost:8080) → AI API
100:                         ↓
101:                    Privacy Guard
102:                    (检测 & 脱敏)
103: 
104: ### 2026-03-31 URL 误报修复
105: - SVG xmlns URL 被误判为敏感 URL
106: - 添加 url_false_positives 白名单
107: - 已推送 commit `f737c95`
108: 
109: ## 重要提示
110: - context.md 使用 UTF-8 编码保存，避免乱码
```

## 3. 要添加的内容

### 3.1 隐私代理服务器使用指南
1. **安装**
   - 依赖安装：`pip install aiohttp>=3.8.0 pydantic>=2.0.0 python-dotenv>=1.0.0`
   - 项目结构：`src/privacy-proxy/` 目录包含完整代码

2. **配置**
   - 配置文件：`src/privacy-proxy/config.json` 和 `config.example.json`
   - 主要配置项：`proxy.host`, `proxy.port`, `proxy.openai_base_url`, `proxy.openai_api_key`, `privacy.enabled`

3. **启动**
   - 命令：`python src/privacy-proxy/main.py --config src/privacy-proxy/config.json`
   - 参数：`--host`, `--port`, `--openai-api-key`, `--openai-base-url`, `--no-privacy`, `--debug`

4. **测试**
   - 健康检查：`curl http://localhost:8080/health`
   - 隐私测试：发送包含敏感信息的请求到 `/process` 或 `/detect` 端点

5. **OpenCode 配置**
   - 在 `opencode.json` 中配置 `privacy-proxy` 提供商：
     ```json
     {
       "providers": {
         "privacy-proxy": {
           "npm": "@ai-sdk/openai-compatible",
           "name": "Privacy Proxy",
           "options": {
             "baseURL": "http://localhost:8080/v1",
             "apiKey": "proxy-secret-key"
           }
         }
       }
     }
     ```

6. **常见问题**
   - 端口冲突：修改 `config.json` 中的 `proxy.port`
   - 目标API连接失败：检查 `proxy.openai_base_url` 和网络连接
   - 隐私规则误匹配：调整 `privacy.custom_rules` 或 `privacy.excluded_types`

### 3.2 外部AI系统集成说明
1. **集成原理**
   - 隐私代理作为中间层，拦截用户输入
   - 使用 privacy-guard 检测和脱敏
   - 将处理后的内容转发到外部AI API

2. **集成方式**
   - **代理模式**：所有请求通过隐私代理
   - **直连模式**：仅对指定API启用隐私代理
   - **混合模式**：根据内容敏感度动态选择

3. **支持系统**
   - OpenAI API (api.openai.com)
   - Anthropic Claude API
   - Azure OpenAI Service
   - 本地部署的 LLM (Ollama, LM Studio)

4. **配置示例**
   ```json
   {
     "ai_systems": [
       {
         "name": "OpenAI",
         "base_url": "https://api.openai.com/v1",
         "api_key": "sk-...",
         "privacy_enabled": true
       },
       {
         "name": "Claude",
         "base_url": "https://api.anthropic.com/v1",
         "api_key": "sk-...",
         "privacy_enabled": true
       }
     ]
   }
   ```

5. **多代理架构**
   - 负载均衡：多个隐私代理实例
   - 优先级路由：根据内容类型选择代理
   - 故障转移：备用隐私代理
   - 端点列表：`/health`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`, `/process`, `/detect`

## 4. 实施步骤

### 4.1 准备工作
1. 备份原文件：`cp context.md context.md.backup`
2. 确认插入位置：第102行后

### 4.2 使用 edit 工具插入内容
```python
# 步骤1：准备要插入的文本
new_content = """
### 隐私代理服务器使用指南
#### 安装
- 安装依赖：`pip install aiohttp>=3.8.0 pydantic>=2.0.0 python-dotenv>=1.0.0`
- 项目结构：`src/privacy-proxy/` 目录包含完整代码

#### 配置
- 配置文件：`src/privacy-proxy/config.json` 和 `config.example.json`
- 主要配置项：
  - `proxy.host`: 代理服务主机 (默认 127.0.0.1)
  - `proxy.port`: 代理服务端口 (默认 8080)
  - `proxy.openai_base_url`: 目标AI API地址
  - `proxy.openai_api_key`: OpenAI API密钥
  - `privacy.enabled`: 是否启用隐私处理

#### 启动
- 命令：`python src/privacy-proxy/main.py --config src/privacy-proxy/config.json`
- 参数：`--host`, `--port`, `--openai-api-key`, `--openai-base-url`, `--no-privacy`, `--debug`

#### 测试
- 健康检查：`curl http://localhost:8080/health`
- 隐私测试：发送包含敏感信息的请求到 `/process` 或 `/detect` 端点

#### OpenCode 配置
- 在 `opencode.json` 中配置 `privacy-proxy` 提供商：
  ```json
  {
    "providers": {
      "privacy-proxy": {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Privacy Proxy",
        "options": {
          "baseURL": "http://localhost:8080/v1",
          "apiKey": "proxy-secret-key"
        }
      }
    }
  }
  ```
- 重启 OpenCode 使配置生效

#### 常见问题
- **端口冲突**：修改 `config.json` 中的 `proxy.port`
- **目标API连接失败**：检查 `proxy.openai_base_url` 和网络连接
- **隐私规则误匹配**：调整 `privacy.custom_rules` 或 `privacy.excluded_types`

### 外部AI系统集成说明
#### 集成原理
隐私代理作为中间层，拦截所有用户输入和AI响应，使用 privacy-guard 进行检测和脱敏，确保敏感信息不会泄露给外部AI服务。

#### 集成方式
1. **代理模式**：所有AI请求通过隐私代理
2. **直连模式**：仅对指定API启用隐私代理
3. **混合模式**：根据内容敏感度动态选择是否使用代理

#### 支持系统
- **OpenAI API**：完全支持，包括 GPT-4, GPT-3.5
- **Anthropic Claude API**：支持 Claude 3 系列
- **Azure OpenAI Service**：支持企业级部署
- **本地LLM**：Ollama, LM Studio, Text Generation WebUI

#### 端点列表
- `/health` - 健康检查
- `/v1/chat/completions` - OpenAI兼容聊天
- `/v1/embeddings` - OpenAI兼容嵌入
- `/v1/models` - OpenAI兼容模型列表
- `/process` - 隐私处理测试
- `/detect` - 敏感信息检测

#### 多代理架构
- **负载均衡**：多个隐私代理实例分担流量
- **优先级路由**：根据内容类型选择最优代理
- **故障转移**：主代理故障时自动切换到备用代理
- **监控**：集成 Prometheus 监控代理性能
"""

# 步骤2：使用 edit 工具在第102行后插入
# 注意：实际操作时需要读取文件，然后使用 edit 工具
```

### 4.3 实际编辑操作
1. 读取文件，确认第102行内容为 `(检测 & 脱敏)`
2. 使用 edit 工具，在第102行后插入新内容
3. 确保新内容与上下文格式一致（使用 ### 和 #### 标题）

## 5. 验证要点
1. **内容完整性**：所有要求的6+5=11个部分都已添加，包括端点列表（`/health`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`, `/process`, `/detect`）
2. **格式正确**：
   - Markdown 标题层级正确（### 和 ####）
   - 代码块使用 ``` 标记
   - 列表使用 - 或 1. 格式
3. **编码正确**：UTF-8 编码，无乱码
4. **上下文连贯**：新内容与原有内容自然衔接
5. **链接有效**：文件路径和配置引用正确，特别是 `src/privacy-proxy/config.json` 和 `opencode.json` 中的配置

## 6. 回滚计划
如果更新失败或需要恢复：
1. **立即回滚**：
   ```bash
   cp context.md.backup context.md
   ```
2. **手动恢复**：
   - 删除从 `### 隐私代理服务器使用指南` 到文件末尾的所有内容
   - 确保文件结束于第112行 `索引目录：`D:/opencode1/indexes``
3. **验证回滚**：检查文件行数、编码和内容是否正确

## 7. 风险与缓解
- **风险**：编辑过程中破坏原有结构
  - **缓解**：先备份，小范围测试编辑
- **风险**：编码问题导致乱码
  - **缓解**：使用 UTF-8 编码保存，验证中文显示正常
- **风险**：插入位置错误
  - **缓解**：先读取文件，确认行号后再编辑

## 8. 时间估算
- 准备工作：2分钟
- 编辑操作：5分钟
- 验证测试：3分钟
- **总计**：约10分钟

---

**计划制定时间**：2026-04-01
**计划执行者**：opencode
**最后验证**：完成后运行 `cat context.md | wc -l` 确认行数增加