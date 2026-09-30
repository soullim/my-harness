"""문서·규칙 일관성 검사 (docs/harness-verify.md 4절).

사용: python scripts/doccheck.py
1) docs/*.md 와 CLAUDE.md 가 가리키는 경로(docs/…, rules/…, scripts/…, tests/…)가 모두 실제로 있는지
2) rules/rules.json 값이 docs/harness-gates.md 2절 표(색·글자 크기·간격·라운드)와 같은지
종료 코드: 어긋남 0건이면 0
"""
import re
import sys

from _common import ROOT, load_rules, read

problems = []

# 1) 경로 참조
PATH_RE = re.compile(r"(?<![\w/])((?:docs|rules|scripts|tests)/[\w.\-]+\.(?:md|json|py|html))")
sources = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "CLAUDE.md"]
checked = 0
for src in sources:
    if not src.exists():
        problems.append(f"{src.relative_to(ROOT).as_posix()} 없음")
        continue
    for ref in sorted(set(PATH_RE.findall(read(src)))):
        checked += 1
        if not (ROOT / ref).exists():
            problems.append(f"{src.relative_to(ROOT).as_posix()} → {ref} 없음")

# 2) rules.json ↔ harness-gates.md 표
rules = load_rules()
gates_md = read(ROOT / "docs" / "harness-gates.md")


def row(label):
    for line in gates_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == label:
            return cells[1]
    return None


def nums(text):
    return {float(x) for x in re.findall(r"\d+", text or "")}


pairs = [
    ("색", {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", row("색") or "")},
     {h.upper() for h in rules["colors_hex"]}),
    ("글자 크기", nums(row("글자 크기")), {float(x) for x in rules["font_sizes_px"]}),
    ("간격", nums(row("간격")), {float(x) for x in rules["spacing_px"]}),
    ("라운드", nums(row("라운드")), {float(x) for x in rules["radius_px"]}),
]
for label, doc_vals, json_vals in pairs:
    if doc_vals != json_vals:
        problems.append(f"{label}: 문서 {sorted(doc_vals)} ≠ rules.json {sorted(json_vals)}")

print(f"[경로 참조] {checked}개 확인")
print(f"[값 비교] 색·글자 크기·간격·라운드 4개 항목 확인")
if problems:
    print(f"[doccheck 실패] {len(problems)}건")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print("[doccheck 통과]")
sys.exit(0)
