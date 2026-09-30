"""하네스 스크립트 공통 도구. 직접 실행하지 않는다."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "rules" / "rules.json"
RUNS_DIR = ROOT / "runs"

try:  # Windows 콘솔에서도 한글이 깨지지 않게
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_rules():
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_dir(arg):
    p = Path(arg)
    if not p.is_absolute():
        p = (ROOT / p) if (ROOT / p).exists() else (RUNS_DIR / arg)
    if not (p / "run.json").exists():
        sys.exit(f"[오류] 실행 폴더를 찾을 수 없습니다: {arg}")
    return p


def load_run(rdir):
    return json.loads(read(Path(rdir) / "run.json"))


def normalize_screens(names, rules):
    """한글 이름·약어를 모두 받아 약어 목록으로 바꾼다."""
    ko_to_abbr = {ko.replace(" ", ""): ab for ab, ko in rules["screens"].items()}
    def match(token):
        t = token.strip()
        if t in rules["screens"]:
            return t
        return ko_to_abbr.get(t.replace(" ", ""))

    out = []
    for raw in names:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            hit = match(part)
            if hit:
                out.append(hit)
                continue
            # "compare list"처럼 공백으로 이어 쓴 약어
            words = part.split()
            hits = [match(w) for w in words]
            if words and all(hits):
                out.extend(hits)
            else:
                return None, part
    # 순서 유지하며 중복 제거
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq, None
