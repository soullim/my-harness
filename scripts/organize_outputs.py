"""실행 산출물 정리. runs/ 안의 모든 실행을 훑어 현황을 요약하고 runs/INDEX.md 를 쓴다.

사용:
  python scripts/organize_outputs.py                 전체 요약 + runs/INDEX.md 갱신
  python scripts/organize_outputs.py show [<실행>]   한 실행만 화면에 출력 (파일을 쓰지 않음, 기본: 가장 최근 실행)

실행 폴더·run.json·산출물은 읽기만 한다. 지우거나 옮기지 않는다. 쓰는 파일은 runs/INDEX.md 하나뿐이다.
"""
import json
import re
import sys
from datetime import datetime

from _common import RUNS_DIR, load_rules, load_run, read, run_dir, write
from gate import GATES

STAGES = ["S1", "S2", "S3", "S4", "S5"]
GATE_IDS = ["G1", "G2", "G3", "G4", "G5"]


def run_folders():
    if not RUNS_DIR.exists():
        return []
    return sorted(p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "run.json").exists())


def stage_index(stage):
    return STAGES.index(stage) if stage in STAGES else 0


def gate_states(rdir, run, rules):
    """게이트별 (상태, 사유 목록). 아직 도달하지 않은 단계는 '대기'."""
    cur = stage_index(run.get("stage"))
    failed_before = {h.get("gate") for h in run.get("history", []) if h.get("event") == "fail"}
    out = {}
    for i, g in enumerate(GATE_IDS):
        try:
            errs = GATES[g](rdir, run, rules)
        except Exception as e:
            errs = [f"판정 중 오류: {e}"]
        if not errs:
            state = "통과"
        elif i > cur and g not in failed_before:
            state = "대기"
        else:
            state = "미통과"
        out[g] = (state, errs)
    return out


def violation_count(rdir):
    try:
        return len(json.loads(read(rdir / "04-verdict" / "violations.json")))
    except Exception:
        return None


def expected_files(run):
    rows = [("S1", "01-research/references.md")]
    rows += [("S2", f"02-spec/{s}.md") for s in run.get("screens", [])]
    rows += [("S3", f"03-drafts/{s}.html") for s in run.get("screens", [])]
    rows += [("S4", "04-verdict/violations.json"), ("S4", "04-verdict/report.md"),
             ("S5", "05-share/share-urls.txt"), ("완료", "review.md")]
    return rows


def todo(rdir, run, rules, gates):
    """사람이 다음에 할 일. 판단이 필요한 건 선택지로만 적는다."""
    status, stage = run.get("status"), run.get("stage")
    if status == "stopped":
        return ["멈춤 상태 — 위반 목록을 확인한 뒤 '이어서 해줘'(재시도 초기화) 또는 '반려: <사유>'로 결정"]
    if status == "done":
        review = rdir / "review.md"
        if review.exists() and re.search(r"-\s*(손 작업보다 좋았던 점 1개|아쉬운 점 1개):\s*$", read(review), re.M):
            return ["review.md '본인 작성' 칸 2줄이 비어 있음"]
        return []
    if stage in ("S1", "S2", "S3"):
        return [f"{stage}에서 멈춘 상태 — '이어서 해줘'로 재개"]
    if stage == "S4":
        if gates["G4"][0] == "통과" and not run.get("approved"):
            return ["사람 승인 대기 — '승인' 또는 '반려: <사유>'"]
        return ["S4 판정 진행 중 — '이어서 해줘'로 재개"]
    if stage == "S5":
        if not run.get("approved"):
            return ["사람 승인 대기 — '승인' 또는 '반려: <사유>'"]
        if not (rdir / "05-share" / "share-urls.txt").exists():
            if not rules.get("share", {}).get("base_url", "").strip():
                return ["공유 보류 — rules/rules.json 의 share.base_url 이 비어 있어 S5가 멈춤 (값을 채운 뒤 '이어서 해줘')"]
            return ["S5 공유 URL 목록 미작성 — '이어서 해줘'"]
    return []


def run_summary(rdir, rules):
    run = load_run(rdir)
    gates = gate_states(rdir, run, rules)
    return {"dir": rdir, "run": run, "gates": gates,
            "violations": violation_count(rdir), "todo": todo(rdir, run, rules, gates)}


def gate_brief(gates):
    ok = sum(1 for st, _ in gates.values() if st == "통과")
    bad = [g for g, (st, _) in gates.items() if st == "미통과"]
    return f"{ok}/5 통과" + (f" ({', '.join(bad)} 미통과)" if bad else "")


def section(info, rules):
    rdir, run, gates = info["dir"], info["run"], info["gates"]
    names = ", ".join(f"{rules['screens'].get(s, s)}({s})" for s in run.get("screens", []))
    failed = [h["gate"] for h in run.get("history", []) if h.get("event") == "fail"]
    viol = info["violations"]
    lines = [f"## {rdir.name}", "",
             f"- 화면: {names}",
             f"- 상태: {run.get('status')} · 단계 {run.get('stage')} · 승인 {'완료' if run.get('approved') else '대기'}",
             f"- 재시도: G4 {run.get('retry', 0)}회 · 반려 {run.get('reject', 0)}회 · 게이트 실패 기록 {', '.join(failed) if failed else '없음'}",
             "- 게이트: " + " · ".join(f"{g} {st}" for g, (st, _) in gates.items()),
             f"- 위반: {'기록 없음' if viol is None else f'{viol}건'}"]
    for g, (st, errs) in gates.items():
        if st == "미통과":
            lines.append(f"  - {g} 사유: {'; '.join(errs[:3])}")
    lines += ["", "| 단계 | 파일 | 상태 |", "|---|---|---|"]
    for stage, rel in expected_files(run):
        exists = (rdir / rel).exists()
        cell = f"[{rel}]({rdir.name}/{rel})" if exists else rel
        lines.append(f"| {stage} | {cell} | {'있음' if exists else '없음'} |")
    share = rdir / "05-share" / "share-urls.txt"
    if share.exists():
        lines += ["", "공유 URL:"] + [f"- {l}" for l in read(share).splitlines() if l.strip()]
    lines += ["", "남은 일:"] + ([f"- {t}" for t in info["todo"]] if info["todo"] else ["- 없음"])
    return lines


def build_index(infos, rules):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# 실행 산출물 목록", "",
             f"> scripts/organize_outputs.py 가 {stamp}에 작성. 직접 고치지 않는다 (다시 실행하면 덮어쓴다). 실행 {len(infos)}개.",
             "", "## 한눈에", "",
             "| 실행 | 화면 | 단계 | 상태 | 승인 | 게이트 | 위반 | 남은 일 |",
             "|---|---|---|---|---|---|---|---|"]
    for info in reversed(infos):
        run = info["run"]
        viol = info["violations"]
        first = info["todo"][0].split(" — ")[0] if info["todo"] else "없음"
        lines.append(f"| [{info['dir'].name}](#{info['dir'].name}) | {', '.join(run.get('screens', []))} | {run.get('stage')} "
                     f"| {run.get('status')} | {'완료' if run.get('approved') else '대기'} | {gate_brief(info['gates'])} "
                     f"| {'-' if viol is None else viol} | {first} |")
    for info in reversed(infos):
        lines += [""] + section(info, rules)
    return "\n".join(lines) + "\n"


def cmd_index():
    rules = load_rules()
    infos = [run_summary(p, rules) for p in run_folders()]
    if not infos:
        print("[안내] 실행 기록이 없습니다. '고교나침반 시안 만들어줘: <화면 2~3개>'로 먼저 실행하세요.")
        return
    text = build_index(infos, rules)
    write(RUNS_DIR / "INDEX.md", text)
    print(text)
    print(f"[완료] runs/INDEX.md 를 갱신했습니다. (실행 {len(infos)}개, 지우거나 옮긴 파일 0건)")


def cmd_show(args):
    rules = load_rules()
    rdir = run_dir(args[0]) if args else (run_folders() or [None])[-1]
    if rdir is None:
        sys.exit("[오류] 실행 기록이 없습니다.")
    print("\n".join(section(run_summary(rdir, rules), rules)))


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "index":
        cmd_index()
    elif sys.argv[1] == "show":
        cmd_show(sys.argv[2:])
    else:
        sys.exit(__doc__)
