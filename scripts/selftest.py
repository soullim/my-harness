"""판정 스크립트 자체 검증 (docs/harness-verify.md 1절).

사용: python scripts/selftest.py
- tests/fail-sample.html: 심어둔 위반 규칙 종류 = 잡힌 규칙 종류, V1·V2는 반드시 잡혀야 함
- tests/pass-sample.html: 위반 0건
종료 코드: 모두 통과 0, 하나라도 실패 1
"""
import json
import sys

from _common import ROOT, load_rules, read
from check_design import check_html

rules = load_rules()
exp = json.loads(read(ROOT / "tests" / "expected.json"))
ok = True

fail_v = check_html(read(ROOT / "tests" / "fail-sample.html"), "_test", rules)
found = {v["rule"] for v in fail_v}
want = set(exp["fail_sample_rules"])
missing, extra = want - found, found - want
print(f"[위반 샘플] 잡은 규칙 {len(found)}종 / 심은 규칙 {len(want)}종")
if missing:
    ok = False
    print(f"  - 못 잡은 규칙: {', '.join(sorted(missing))}")
if extra:
    ok = False
    print(f"  - 심지 않았는데 잡힌 규칙: {', '.join(sorted(extra))}")
for must in ("V1", "V2"):
    if must not in found:
        ok = False
        print(f"  - 필수 규칙 {must}를 잡지 못함")

pass_v = check_html(read(ROOT / "tests" / "pass-sample.html"), "_test", rules)
print(f"[통과 샘플] 위반 {len(pass_v)}건 (기대 {exp['pass_sample_violations']}건)")
if len(pass_v) != exp["pass_sample_violations"]:
    ok = False
    for v in pass_v:
        print(f"  - {v['rule']} · {v['value']} · {v.get('where', '')}")

print("[selftest 통과]" if ok else "[selftest 실패]")
sys.exit(0 if ok else 1)
