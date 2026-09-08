# 工具适配说明

助手在阶段 0 读本文件对应的一节。标注「已核实」的是查过官方文档或在真实数据上验证过的；标注「待核实」的是公开资料里没找到、需要助手在用户机器上实地确认的。

## 对照表

| | Codex | DeepSeek Harness (dsh) | WorkBuddy | Claude Code |
|---|---|---|---|---|
| 会话记录位置 | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`（已核实） | `~/.dsh/` 下，每会话一个 `session.v*.jsonl.zstd`，默认 zstd 压缩（已核实位置，子目录结构待核实） | 官方未公开（待核实） | `~/.claude/projects/<路径编码>/*.jsonl`（已核实） |
| 会话里的项目路径 | `session_meta.payload.cwd`（已核实） | 会话头 `cwd` 字段（已核实有此字段） | 待核实 | 目录名即路径，`-` 替代 `/` |
| 用户消息怎么认 | `type=response_item` 且 `payload.role=user`；或 `event_msg` 的 `user_message`（已核实） | 事件 `user/message`（已核实） | 待核实 | `type=user` 且 `message.role=user` |
| 规矩文件 | `~/.codex/AGENTS.md` 全局；项目内从 Git 根往下到 cwd 逐级读 `AGENTS.md`，合并上限 32 KiB（已核实） | `~/.dsh/AGENTS.md` 全局；项目内从 Git 根往下到 cwd 逐级读 `AGENTS.md` / `CLAUDE.md`，再读 `.local.md` 覆盖（已核实） | 是否读 `AGENTS.md` 待核实 | `~/.claude/CLAUDE.md` 全局；项目内 `CLAUDE.md`，会向上找父目录 |
| 是否读 Git 根以上 | 否（已核实） | 否（已核实） | 待核实 | 是 |
| 个人技能目录 | `~/.codex/skills/` | `~/.agents/skills/` | `~/.workbuddy/skills/` | `~/.claude/skills/` |
| 项目技能目录 | `.codex/skills/` | `.agents/skills/` | `.workbuddy/skills/` | `.claude/skills/` |
| 定时任务 | 系统 cron 调 `codex exec` | 待核实 | 无（手动） | scheduled tasks |
| 需要兜底 | 否 | 否 | 是 | 否 |

## Codex

**读会话**：运行 `tools/extract_codex.py`：

```
python3 tools/extract_codex.py --list-projects            # 统计各工作目录的会话数
python3 tools/extract_codex.py --project <路径> --days 90  # 导出某项目最近 90 天的手打消息
```

脚本只读 `~/.codex/sessions`，输出 JSONL，每行含 `date`、`cwd`、`text`。已按 SKILL.md 阶段 5 的规则排除非手打消息与工具注入内容。

**接线**：Codex 从 Git 根往下读 `AGENTS.md`，不会读到岗位目录。项目 `AGENTS.md` 里必须显式写 `../业务知识/`。合并后总量上限 32 KiB，追加段要短。

**定时**：macOS/Linux 可用 cron：`30 8 * * 1 cd <项目> && codex exec "<每周提示词>"`。设之前问用户。

## DeepSeek Harness (dsh)

**读会话**：会话在 `~/.dsh/` 下，默认 zstd 压缩。助手先 `find ~/.dsh -name 'session*.jsonl*'` 确认实际路径与子目录结构，再决定解压方式（`zstd -d` 或 Python `zstandard` 库）。会话头带 `cwd`，事件流里 `user/message` 是用户消息。如果 dsh 配置了不压缩，直接读 JSONL。

**接线**：dsh 规则与 Codex 相同，从 Git 根往下读，同时认 `AGENTS.md` 和 `CLAUDE.md`。项目层显式引用上级。

**技能**：`~/.agents/skills/<skill>/SKILL.md`，frontmatter 至少含 `name`、`description`。放进去后目录会热刷新，不用重启。

## WorkBuddy

**读会话**：官方文档没有给出会话记录的磁盘路径。助手先看 `~/.workbuddy/` 和 `~/Library/Application Support/`（macOS）或 `%APPDATA%`（Windows）下有没有可读的会话文件；找到了按其格式处理，找不到就走兜底。

**兜底（会话末尾自记）**：在项目 `AGENTS.md` 追加段里启用「会话末尾自记」一节。每次会话结束前把用户手打的业务判断原话追加到项目内 `_候选/本项目候选.md`。每周蒸馏从这个文件读，而不是读会话记录。

**接线**：WorkBuddy 是否自动读取项目 `AGENTS.md` 未在公开资料里确认。助手实地测试：在项目 `AGENTS.md` 里写一句可验证的规矩（例如「回答开头加【已读规矩】」），新开会话看是否生效。不生效则把追加段内容装成项目技能（`.workbuddy/skills/`），或让用户在每次对话开头粘贴。

**技能**：`~/.workbuddy/skills/`，放入后重启生效；也可以把 `SKILL.md` 拖进对话框安装。

## Claude Code

**读会话**：`~/.claude/projects/` 下每个子目录对应一个项目路径，里面的 JSONL 每行一个事件，`type=user` 且 `message.role=user` 是用户消息。

**接线**：Claude Code 会向上找父目录的 `CLAUDE.md`，岗位目录放 `CLAUDE.md` 写一行 `@AGENTS.md` 即可自动读到。项目层仍建议显式引用，保证换工具时行为一致。

**定时**：可用 scheduled tasks 设每周一早上执行。

## 通用兜底

任何工具，只要读不到会话记录，都用「会话末尾自记」。它的代价是依赖助手每次收工时记一笔，可能漏；好处是完全不依赖工具内部格式，换工具不用改。
