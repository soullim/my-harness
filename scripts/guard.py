"""PreToolUse hook: 편집 폴더 밖 쓰기를 막는다.

Write / Edit / MultiEdit / NotebookEdit 도구가 쓰려는 경로가
runs/<실행>/01-research | 02-spec | 03-drafts | 05-share 안이 아니면 막는다 (종료 코드 2).
hook 입력에 에이전트 이름이 들어 있으면 그 에이전트의 폴더 1개만 허용한다.
04-verdict/ 와 run.json 은 스크립트만 쓰므로 도구 쓰기를 전부 막는다.
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = {"researcher": "01-research", "planner": "02-spec",
             "designer": "03-drafts", "sharer": "05-share"}
ALLOWED = re.compile(r"^runs/[^/]+/(01-research|02-spec|03-drafts|05-share)/[^/].*")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if not path:
        return 0
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        rel = p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        print(f"[차단] 하네스 폴더 밖 쓰기: {path}", file=sys.stderr)
        return 2

    m = ALLOWED.match(rel)
    if not m:
        print(f"[차단] 편집 폴더 밖 쓰기: {rel}  (허용: runs/<실행>/01-research|02-spec|03-drafts|05-share/)", file=sys.stderr)
        return 2

    agent = ""
    for key in ("agent_type", "subagent_type", "agent_name", "agent"):
        if isinstance(data.get(key), str):
            agent = data[key].lower()
            break
    if agent in AGENT_DIR and m.group(1) != AGENT_DIR[agent]:
        print(f"[차단] {agent}의 편집 폴더는 {AGENT_DIR[agent]}/ 입니다: {rel}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
