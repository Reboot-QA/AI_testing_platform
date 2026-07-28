#!/usr/bin/env python3
"""中文安全的 glab Issue 读写（本机控制台为 GBK，正文禁走命令行参数）。

背景：glab 1.108.0 没有 --description-file / --message-file，只有 -d/-m 参数。
Windows 上参数要经控制台码页（GBK）才交给进程，长中文正文会被双重编码写坏
（Issue #15、#21 曾整篇报废）。本脚本改走 `glab api --input <UTF-8 JSON 文件>`，
文件字节原样进 HTTP body，不经任何码页转换，并强制读回校验。

用法（正文一律先写成 UTF-8 的 .md 草稿，落 scratchpad，不进仓库）：
    python .claude/scripts/glab_cn.py create  --body-file draft.md [--title "..."]
    python .claude/scripts/glab_cn.py update  <IID> --body-file draft.md
    python .claude/scripts/glab_cn.py comment <IID> --body-file draft.md
    python .claude/scripts/glab_cn.py check   <IID>

create 默认取草稿首个 `# ` 标题作为 Issue 标题（避免中文标题走参数）；
显式 --title 仅建议用于纯 ASCII 前缀场景。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# UTF-8 被按 GBK 解读后的高频残片，用于判定正文是否写坏
MOJIBAKE_MARKERS = ("锛", "鎺", "瀵", "鏂", "鐨", "鍏", "閫")
MOJIBAKE_THRESHOLD = 20


def _glab_api(path: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    cmd = ["glab", "api", path, "--method", method]
    tmp = None
    if payload is not None:
        # 关键：正文落 UTF-8 文件后用 --input，绝不拼进命令行参数
        tmp = Path(tempfile.mkstemp(suffix=".json")[1])
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--input", str(tmp)]
    try:
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0:
            sys.exit(f"glab api 失败：{proc.stdout.decode('utf-8', 'replace')[:500]}")
        return json.loads(proc.stdout.decode("utf-8"))
    finally:
        if tmp is not None:
            # Windows 上 glab 偶发仍占用 --input 文件，忽略 WinError 32
            try:
                tmp.unlink(missing_ok=True)
            except PermissionError:
                pass


def _mojibake_count(text: str) -> int:
    return sum(text.count(m) for m in MOJIBAKE_MARKERS)


def _verify(iid: int, expected: str | None = None) -> bool:
    """读回校验：无乱码残片，且（如给了原文）与原文逐字符一致。"""
    desc = _glab_api(f"projects/:fullpath/issues/{iid}")["description"] or ""
    markers = _mojibake_count(desc)
    ok = markers <= MOJIBAKE_THRESHOLD
    print(f"#{iid} 读回 {len(desc)} 字符，乱码残片 {markers} -> {'CLEAN' if ok else 'CORRUPT'}")
    if expected is not None:
        match = desc.strip() == expected.strip()
        print(f"与草稿比对：{'EXACT MATCH' if match else 'DIFF（内容不一致，请复查）'}")
        ok = ok and match
    return ok


def _read_body(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _title_from(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    sys.exit("草稿里没有 `# 标题` 行，且未显式指定 --title")


def main() -> None:
    ap = argparse.ArgumentParser(description="中文安全的 glab Issue 读写")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="建 Issue")
    c.add_argument("--body-file", required=True)
    c.add_argument("--title", default=None, help="省略则取草稿首个 `# ` 标题")

    u = sub.add_parser("update", help="改 Issue 描述")
    u.add_argument("iid", type=int)
    u.add_argument("--body-file", required=True)

    m = sub.add_parser("comment", help="追加 Issue 评论（交接物）")
    m.add_argument("iid", type=int)
    m.add_argument("--body-file", required=True)

    k = sub.add_parser("check", help="只读校验现有 Issue 编码")
    k.add_argument("iid", type=int)

    s = sub.add_parser("show", help="把 Issue 描述+评论导成 UTF-8 文件（GBK 终端直接打印会假乱码）")
    s.add_argument("iid", type=int)
    s.add_argument("--out", required=True, help="输出路径，随后用 Read 工具查看")

    args = ap.parse_args()

    if args.cmd == "check":
        sys.exit(0 if _verify(args.iid) else 1)

    if args.cmd == "show":
        issue = _glab_api(f"projects/:fullpath/issues/{args.iid}")
        notes = _glab_api(f"projects/:fullpath/issues/{args.iid}/notes")
        parts = [
            f"# Issue #{issue['iid']}: {issue['title']}",
            f"state: {issue['state']}  |  {issue['web_url']}",
            "\n---\n## 描述（契约，以此为准）\n",
            issue.get("description") or "(空)",
        ]
        # notes 接口按时间倒序返回，转为正序更贴合「最后一条交接评论」的语义
        for n in reversed(notes):
            if n.get("system"):
                continue
            parts.append(f"\n---\n## 评论 · {n['author']['username']} · {n['created_at']}\n")
            parts.append(n.get("body") or "")
        Path(args.out).write_text("\n".join(parts), encoding="utf-8")
        print(f"已导出 #{args.iid}（描述 + {len(notes)} 条评论）到 {args.out}，请用 Read 工具查看")
        sys.exit(0)

    body = _read_body(args.body_file)

    if args.cmd == "create":
        title = args.title or _title_from(body)
        issue = _glab_api("projects/:fullpath/issues", "POST", {"title": title, "description": body})
        iid = issue["iid"]
        print(f"已建 Issue #{iid}：{issue['web_url']}")
        sys.exit(0 if _verify(iid, body) else 1)

    if args.cmd == "update":
        _glab_api(f"projects/:fullpath/issues/{args.iid}", "PUT", {"description": body})
        print(f"已更新 #{args.iid} 描述")
        sys.exit(0 if _verify(args.iid, body) else 1)

    if args.cmd == "comment":
        note = _glab_api(f"projects/:fullpath/issues/{args.iid}/notes", "POST", {"body": body})
        got = note.get("body", "")
        markers = _mojibake_count(got)
        ok = markers <= MOJIBAKE_THRESHOLD and got.strip() == body.strip()
        print(f"已在 #{args.iid} 追加评论 note:{note['id']} -> {'CLEAN' if ok else 'CORRUPT/DIFF'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
