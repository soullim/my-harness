"""_claude-setup/ 의 에이전트 정의와 hook 설정을 .claude/ 로 복사한다. 본인이 1회 실행한다.

사용: python scripts/install_claude_setup.py
이미 .claude/settings.json 이 있으면 덮어쓰지 않고 멈춘다 (--force 로 덮어쓰기).
"""
import shutil
import sys

from _common import ROOT

src = ROOT / "_claude-setup"
dst = ROOT / ".claude"
force = "--force" in sys.argv

if (dst / "settings.json").exists() and not force:
    sys.exit("[중단] .claude/settings.json 이 이미 있습니다. 내용을 확인한 뒤 --force 로 다시 실행하세요.")

(dst / "agents").mkdir(parents=True, exist_ok=True)
for f in (src / "agents").glob("*.md"):
    shutil.copy2(f, dst / "agents" / f.name)
    print(f"[복사] .claude/agents/{f.name}")
shutil.copy2(src / "settings.json", dst / "settings.json")
print("[복사] .claude/settings.json")
print("[완료] Claude Code를 이 폴더에서 다시 열면 에이전트 5종과 편집 폴더 hook이 적용됩니다.")
