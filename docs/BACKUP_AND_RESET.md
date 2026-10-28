# 备份与清空本地技能数据

> Closed Alpha 自助支持半页 · 配套 [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md)

## 备份（推荐）

SkillOS 工作区技能主要在仓库或数据目录下的 `skills/`（以及租户相关 SQLite，如 `skillhub.db`）。

**最小备份**：复制整个项目数据相关目录到安全位置，例如：

```bash
# 示例：备份技能目录与常见本地库（按你的实际路径调整）
mkdir -p ~/skillos-backup/2026-10-28
cp -r skills ~/skillos-backup/2026-10-28/
# 若存在本地 DB：
# cp skillhub.db ~/skillos-backup/2026-10-28/
```

Windows PowerShell：

```powershell
$stamp = Get-Date -Format "yyyy-MM-dd"
New-Item -ItemType Directory -Force -Path "$HOME\skillos-backup\$stamp" | Out-Null
Copy-Item -Recurse skills "$HOME\skillos-backup\$stamp\"
```

装到 Cursor / `.agents` / `.dsh` 的副本是**额外拷贝**；备份工作区 `skills/` 不等于备份 harness 目录。

## 清空 / 重置（谨慎）

1. **先备份**（上一节）。
2. 删除或移走不需要的技能目录：`skills/<技能名>/`（勿删系统参考技能，除非你清楚后果）。
3. 重启：`skillos --server-only`。
4. 可选：清空 harness 安装副本（`~/.cursor/skills/<slug>/` 等）——仅当你确定不再需要。

## 回滚软件版本

见 README「发布与回滚」：检出上一 tag（如 `v0.3.6` 的前一版）后 `pip install -e .` 再启动。

## 求助时请附带

- 卡在哪一步（登录 / Key / 列表 / 沉淀 / 安装）
- Trust Tier 是否理解
- 是否装进 Cursor + 报错原文
