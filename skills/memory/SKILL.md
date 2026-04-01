# Skill: memory

## 触发条件
每次对话开始时自动加载此 skill

## 自动行为
读取 `D:/opencode1/context.md` 获取 Leon 的上下文记忆

```python
from pathlib import Path
context = Path("D:/opencode1/context.md").read_text()
```

## 说明
此 skill 负责维护对话间的上下文连续性，确保 AI 记住：
- Leon 的个人信息
- 正在进行的项目
- 历史对话结论
