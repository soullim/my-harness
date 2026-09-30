"""run.json 상태 관리 스크립트. run.json은 이 스크립트로만 바꾼다.

사용:
  python scripts/run_state.py new <화면...>          새 실행 폴더 + run.json (예: new "학교 비교" "일반고 목록" / new compare list)
  python scripts/run_state.py latest                 가장 최근 실행 폴더 출력
  python scripts/run_state.py show <실행>            run.json 출력
  python scripts/run_state.py stage <실행> <S1~S5>   현재 단계 기록
  python scripts/run_state.py fail <실행> <G1~G5>    게이트 실패 기록 → 복귀 단계 또는 stopped
  python scripts/run_state.py approve <실행>         사람 승인 → S5
  python scripts/run_state.py reject <실행> <사유>   사람 반려 → S3 (reject-notes.md에 사유 기록)
  python scripts/run_state.py resume <실행>          stopped 해제 (본인 확인), 재시도 횟수 초기화
  python scripts/run_state.py done <실행>            완료 처리 + review.md 숫자 항목 작성
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from _common import RUNS_DIR, load_rules, load_run, normalize_screens, read, run_dir, write

STAGE_OF_GATE = {"G1": "S1", "G2": "S2", "G3": "S3", "G4": "S4", "G5": "S5"}
SUBDIRS = ["01-research", "02-spec", "03-drafts", "04-verdict", "05-share"]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def save(rdir, run):
    write(Path(rdir) / "run.json", json.dumps(run, ensure_ascii=False, indent=2))


def log(run, event, **kw):
    run.setdefault("history", []).append({"at": now(), "event": event, **kw})


def cmd_new(args):
    rules = load_rules()
    screens, bad = normalize_screens(args, rules)
    if screens is None:
        sys.exit(f"[오류] 알 수 없는 화면: {bad}  (가능: {', '.join(f'{k}={v}' for k, v in rules['screens'].items())})")
    lo, hi = rules["screen_count"]["min"], rules["screen_count"]["max"]
    if not lo <= len(screens) <= hi:
        sys.exit(f"[오류] 화면은 {lo}~{hi}개여야 합니다. 받은 개수: {len(screens)}")
    name = datetime.now().strftime("%Y%m%d-%H%M")
    rdir = RUNS_DIR / name
    n = 2
    while rdir.exists():
        rdir = RUNS_DIR / f"{name}-{n}"
        n += 1
    for d in SUBDIRS:
        (rdir / d).mkdir(parents=True, exist_ok=True)
    run = {"screens": screens, "stage": "S1", "retry": 0, "reject": 0,
           "gate_retry": {"G1": 0, "G2": 0, "G3": 0}, "status": "running",
           "approved": False, "history": []}
    log(run, "new", screens=screens)
    save(rdir, run)
    print(rdir.relative_to(RUNS_DIR.parent).as_posix())


def cmd_latest(_):
    runs = sorted(p for p in RUNS_DIR.glob("*") if (p / "run.json").exists()) if RUNS_DIR.exists() else []
    if not runs:
        sys.exit("[오류] 실행 기록이 없습니다.")
    print(runs[-1].relative_to(RUNS_DIR.parent).as_posix())


def cmd_show(args):
    print(json.dumps(load_run(run_dir(args[0])), ensure_ascii=False, indent=2))


def cmd_stage(args):
    rdir = run_dir(args[0])
    run = load_run(rdir)
    stage = args[1].upper()
    if stage not in {"S1", "S2", "S3", "S4", "S5"}:
        sys.exit("[오류] 단계는 S1~S5")
    if stage == "S5" and not run.get("approved"):
        sys.exit("[중단] 사람 승인 전에는 S5로 갈 수 없습니다. 'approve'를 먼저 기록하세요.")
    run["stage"] = stage
    log(run, "stage", stage=stage)
    save(rdir, run)
    print(f"[상태] stage = {stage}")


def violation_count(rdir):
    f = Path(rdir) / "04-verdict" / "violations.json"
    try:
        return len(json.loads(read(f)))
    except Exception:
        return None


def cmd_fail(args):
    rules = load_rules()
    rdir = run_dir(args[0])
    run = load_run(rdir)
    gate = args[1].upper()
    lim = rules["retry"]
    if gate in {"G1", "G2", "G3"}:
        run["gate_retry"][gate] = run["gate_retry"].get(gate, 0) + 1
        log(run, "fail", gate=gate, count=run["gate_retry"][gate])
        if run["gate_retry"][gate] > lim["g1_g3_max"]:
            run["status"] = "stopped"
            msg = f"[멈춤] {gate} 재실행 {lim['g1_g3_max']}회를 넘었습니다."
        else:
            run["stage"] = STAGE_OF_GATE[gate]
            msg = f"[복귀] {gate} 실패 → {run['stage']} 재실행 ({run['gate_retry'][gate]}/{lim['g1_g3_max']})"
    elif gate == "G4":
        run["retry"] += 1
        log(run, "fail", gate=gate, count=run["retry"], violations=violation_count(rdir))
        if run["retry"] > lim["g4_max"]:
            run["status"] = "stopped"
            msg = f"[멈춤] G4 재시도 {lim['g4_max']}회를 넘었습니다. 위반 목록을 보고하세요."
        else:
            run["stage"] = "S3"
            msg = f"[복귀] G4 실패 → S3 ({run['retry']}/{lim['g4_max']})"
    elif gate == "G5":
        log(run, "fail", gate=gate)
        run["stage"] = "S5"
        msg = "[복귀] G5 실패 → S5 재실행"
    else:
        sys.exit("[오류] 게이트는 G1~G5")
    save(rdir, run)
    print(msg)
    sys.exit(2 if run["status"] == "stopped" else 0)


def cmd_approve(args):
    rdir = run_dir(args[0])
    run = load_run(rdir)
    if violation_count(rdir) != 0:
        sys.exit("[중단] G4 위반이 0건이 아니면 승인할 수 없습니다.")
    run["approved"] = True
    run["stage"] = "S5"
    log(run, "approve")
    save(rdir, run)
    print("[승인] → S5 공유")


def cmd_reject(args):
    rules = load_rules()
    rdir = run_dir(args[0])
    reason = " ".join(args[1:]).strip() or "(사유 없음)"
    run = load_run(rdir)
    run["reject"] += 1
    run["approved"] = False
    log(run, "reject", reason=reason, count=run["reject"])
    notes = Path(rdir) / "reject-notes.md"
    prev = read(notes) if notes.exists() else "# 반려 사유 (designer 입력)\n"
    write(notes, prev + f"\n## {run['reject']}차 반려 ({now()})\n{reason}\n")
    # 반려 후에는 다시 판정해야 승인할 수 있도록 이전 판정 결과를 보관 이름으로 옮긴다
    vf = Path(rdir) / "04-verdict" / "violations.json"
    if vf.exists():
        vf.replace(vf.with_name(f"violations-before-reject-{run['reject']}.json"))
    if run["reject"] > rules["retry"]["reject_max"]:
        run["status"] = "stopped"
        msg = f"[멈춤] 반려 {rules['retry']['reject_max']}회를 넘었습니다."
    else:
        run["stage"] = "S3"
        msg = f"[반려] → S3 ({run['reject']}/{rules['retry']['reject_max']}), 사유는 reject-notes.md"
    save(rdir, run)
    print(msg)


def cmd_resume(args):
    rdir = run_dir(args[0])
    run = load_run(rdir)
    if run["status"] == "stopped":
        run["status"] = "running"
        run["retry"] = 0
        run["gate_retry"] = {"G1": 0, "G2": 0, "G3": 0}
        log(run, "resume", note="본인 확인으로 재시도 횟수 초기화")
        save(rdir, run)
        print(f"[재개] 재시도 횟수를 초기화했습니다. stage = {run['stage']}")
    else:
        print(f"[재개] status = {run['status']}, stage = {run['stage']}")


def cmd_done(args):
    rdir = run_dir(args[0])
    run = load_run(rdir)
    run["status"] = "done"
    log(run, "done")
    save(rdir, run)
    hist = run["history"]
    failed = [h["gate"] for h in hist if h["event"] == "fail"]
    trend = [str(h["violations"]) for h in hist if h.get("gate") == "G4" and h.get("violations") is not None]
    trend.append(str(violation_count(rdir)))
    review = [
        "# 실행 리뷰", "",
        "## 숫자 (스크립트 작성)",
        f"- 화면: {', '.join(run['screens'])}",
        f"- 걸린 게이트: {', '.join(failed) if failed else '없음'}",
        f"- G4 재시도 횟수: {sum(1 for g in failed if g == 'G4')}",
        f"- 반려 횟수: {run['reject']}",
        f"- 위반 건수 추이: {' → '.join(trend)}",
        "",
        "## 본인 작성",
        "- 손 작업보다 좋았던 점 1개: ",
        "- 아쉬운 점 1개: ",
    ]
    write(Path(rdir) / "review.md", "\n".join(review) + "\n")
    print("[완료] review.md 작성 — 본인 작성 칸 2줄을 채워주세요.")


COMMANDS = {"new": cmd_new, "latest": cmd_latest, "show": cmd_show, "stage": cmd_stage,
            "fail": cmd_fail, "approve": cmd_approve, "reject": cmd_reject,
            "resume": cmd_resume, "done": cmd_done}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
