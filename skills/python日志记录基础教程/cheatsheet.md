# 速查表: Python日志记录基础教程

# Python logging 速查表

## 1. 核心规则：工具选择矩阵

```python
# 根据任务选择正确工具
print()           # 普通输出、临时调试
warnings.warn()   # 可避免的警告（如弃用提示）
logging           # 运行时事件跟踪、状态监控、故障排查
raise Exception   # 应中断程序的错误
```

## 2. 日志级别速查（从低到高）

| 级别 | 数值 | 使用场景 |
|------|------|----------|
| DEBUG | 10 | 诊断信息，开发调试 |
| INFO | 20 | 程序正常运行事件 |
| WARNING | 30 | 意外但程序仍能运行 |
| ERROR | 40 | 功能无法执行，但程序不崩溃 |
| CRITICAL | 50 | 程序可能无法继续运行 |

> **默认过滤级别：WARNING**（只有 ≥ WARNING 的事件会被跟踪）

## 3. 决策流程

```
遇到需要记录的事件？
├─ 是否应中断程序？
│   ├─ 是 → 抛出异常 (raise)
│   └─ 否 → 继续
├─ 是否只是临时输出？
│   ├─ 是 → print()
│   └─ 否 → 继续
├─ 是否是可避免的警告？
│   ├─ 是 → warnings.warn()
│   └─ 否 → 使用 logging
└─ 选择日志级别：
    ├─ 开发调试信息 → DEBUG
    ├─ 正常事件 → INFO
    ├─ 意外但可继续 → WARNING
    ├─ 功能失败 → ERROR
    └─ 程序濒临崩溃 → CRITICAL
```

## 4. 正确实践：显式创建 Logger

```python
# ✅ 正确做法
import logging
logger = logging.getLogger(__name__)  # 显式创建
logger.setLevel(logging.DEBUG)

# ❌ 避免：使用默认根日志记录器
logging.warning("消息")  # 无法灵活配置
```

## 5. 常见陷阱

- ❌ 用 `print()` 做日志 → 无法分级、格式化、持久化
- ❌ 用 `logging.warning()` 代替异常 → 应中断的错误不中断
- ❌ 依赖默认根日志记录器 → 难以控制输出行为
- ❌ 不设置日志级别 → 默认只显示 WARNING 及以上

## 6. 一句话总结

> **对于生产级程序，用 `logging.getLogger(__name__)` 创建独立 Logger，按严重程度分级记录事件，并配置输出到文件，而不是用 `print()`。**