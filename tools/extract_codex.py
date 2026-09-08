#!/usr/bin/env python3
"""从 Codex 会话记录里提取用户手打的消息。

只读 ~/.codex/sessions，不写任何文件，结果打印到标准输出（JSONL）。

用法：
  python3 extract_codex.py --list-projects
  python3 extract_codex.py --project /path/to/project --days 90
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SESSIONS = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"

# 工具自动注入的用户消息，不是人打的
INJECTED_PREFIXES = ("<recommended_plugins>", "<environment_context>", "<user_instructions>",
                     "<permissions", "<turn_aborted>", "<skill", "# AGENTS.md")


IDE_MARKER = "## My request for Codex:"


def strip_ide_context(text: str) -> str:
    """Codex IDE 插件会在用户正文前注入「# Context from my IDE setup」块，只保留正文。"""
    if text.lstrip().startswith("# Context from my IDE setup") and IDE_MARKER in text:
        return text.split(IDE_MARKER, 1)[1]
    return text


def is_handtyped(text: str) -> bool:
    """按 SKILL.md 阶段 5 的规则判断是否手打。"""
    t = text.strip()
    if not t or t.startswith(INJECTED_PREFIXES):
        return False
    if len(t) > 1500:
        return False
    if len(re.findall(r"^#{1,6}\s", t, flags=re.M)) >= 2:
        return False
    if re.match(r"^#{1,2}\s*任务", t):
        return False
    if t.count("```") >= 2 and len(t) > 400:
        return False
    lines = t.splitlines()
    if len(lines) >= 4 and sum("\t" in ln for ln in lines) > len(lines) / 2:
        return False  # 粘贴进来的日志或表格
    return True


def iter_sessions():
    for path in sorted(SESSIONS.rglob("rollout-*.jsonl")):
        cwd, date = None, None
        messages = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if rec.get("type") == "session_meta":
                        cwd = rec["payload"].get("cwd")
                        date = rec["payload"].get("timestamp", rec.get("timestamp"))
                    elif rec.get("type") == "event_msg" and rec["payload"].get("type") == "user_message":
                        messages.append((rec.get("timestamp"), rec["payload"].get("message", "")))
        except OSError:
            continue
        if cwd:
            yield cwd, date, messages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-projects", action="store_true", help="统计各工作目录的会话数")
    ap.add_argument("--project", help="只导出该路径（含子目录）下的会话")
    ap.add_argument("--days", type=int, default=90, help="只看最近 N 天，默认 90")
    args = ap.parse_args()

    if not SESSIONS.exists():
        sys.exit(f"找不到 {SESSIONS}")

    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    if args.list_projects:
        counter = Counter()
        for cwd, date, _ in iter_sessions():
            if date and datetime.fromisoformat(date.replace("Z", "+00:00")) < since:
                continue
            counter[cwd] += 1
        for cwd, n in counter.most_common():
            print(f"{n:5d}  {cwd}")
        return

    if not args.project:
        ap.error("请指定 --list-projects 或 --project")

    root = os.path.abspath(os.path.expanduser(args.project))
    total = kept = 0
    for cwd, date, messages in iter_sessions():
        if not (cwd == root or cwd.startswith(root + os.sep)):
            continue
        for ts, text in messages:
            if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")) < since:
                continue
            total += 1
            text = strip_ide_context(text)
            if not is_handtyped(text):
                continue
            kept += 1
            print(json.dumps({"date": (ts or "")[:10], "cwd": cwd, "text": text.strip()}, ensure_ascii=False))
    print(f"# 用户消息 {total} 条，手打 {kept} 条", file=sys.stderr)


if __name__ == "__main__":
    main()
