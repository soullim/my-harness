"""G1~G5 게이트 판정. 파일을 고치지 않고 통과/실패만 알린다.

사용: python scripts/gate.py <G1~G5> <실행폴더>
종료 코드: 통과 0, 실패 1
"""
import json
import re
import sys

from _common import load_rules, load_run, read, run_dir

LINK = re.compile(r"https?://\S+")


def sections(md):
    """'## 제목' 단위로 나눈 {제목: 본문}"""
    out, cur = {}, None
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def find_section(secs, abbr, ko):
    for title, body in secs.items():
        t = title.replace(" ", "")
        if abbr in title or ko.replace(" ", "") in t:
            return body
    return None


def g1(rdir, run, rules):
    errs = []
    f = rdir / "01-research" / "references.md"
    if not f.exists():
        return ["01-research/references.md 없음"]
    secs = sections(read(f))
    need = rules["gates"]["G1"]["min_refs_per_screen"]
    for s in run["screens"]:
        body = find_section(secs, s, rules["screens"][s])
        if body is None:
            errs.append(f"'## {s}' 섹션 없음")
            continue
        n = len({m.group(0) for m in LINK.finditer(body)})
        if n < need:
            errs.append(f"{s}: 레퍼런스 링크 {n}개 (최소 {need}개)")
    return errs


def g2(rdir, run, rules):
    errs = []
    need = rules["gates"]["G2"]["required_headings"]
    for s in run["screens"]:
        f = rdir / "02-spec" / f"{s}.md"
        if not f.exists():
            errs.append(f"02-spec/{s}.md 없음")
            continue
        heads = [re.sub(r"^#+\s*", "", l).strip() for l in read(f).splitlines() if l.startswith("#")]
        for h in need:
            if not any(h.replace(" ", "") in x.replace(" ", "") for x in heads):
                errs.append(f"{s}.md: 제목 '{h}' 없음")
    return errs


def g3(rdir, run, rules):
    errs = []
    cfg = rules["gates"]["G3"]
    w, h = rules["frame"]["width_px"], rules["frame"]["height_px"]
    for s in run["screens"]:
        f = rdir / "03-drafts" / f"{s}.html"
        if not f.exists():
            errs.append(f"03-drafts/{s}.html 없음")
            continue
        html = read(f)
        blocks = len(re.findall(r"<style[\s>]", html, re.I))
        if blocks > cfg["max_style_blocks"] or blocks == 0:
            errs.append(f"{s}.html: <style> {blocks}개 (정확히 {cfg['max_style_blocks']}개)")
        if not cfg["inline_style_allowed"] and re.search(r"<[^>]+\sstyle\s*=", html, re.I):
            errs.append(f"{s}.html: style=\"…\" 속성 사용 (스타일은 <style> 안에만)")
        for link in re.findall(r"<link[^>]+rel=[\"']?stylesheet[^>]*>", html, re.I):
            if cfg["allowed_stylesheet_link_contains"] not in link.lower():
                errs.append(f"{s}.html: 허용되지 않은 외부 스타일시트 {link[:60]}")
        css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))
        if not re.search(rf"(?<![\w-])width\s*:\s*{w}px", css):
            errs.append(f"{s}.html: 프레임 width: {w}px 없음")
        if not re.search(rf"(?<![\w-])(min-)?height\s*:\s*{h}px", css):
            errs.append(f"{s}.html: 프레임 height/min-height: {h}px 없음")
    return errs


def g4(rdir, run, rules):
    f = rdir / "04-verdict" / "violations.json"
    if not f.exists():
        return ["04-verdict/violations.json 없음 — check_design.py를 먼저 실행"]
    vs = json.loads(read(f))
    return [f"{v['screen']} · {v['rule']} · {v['value']}" for v in vs]


def g5(rdir, run, rules):
    errs = []
    if not run.get("approved"):
        errs.append("사람 승인 기록 없음")
    f = rdir / "05-share" / "share-urls.txt"
    if not f.exists():
        return errs + ["05-share/share-urls.txt 없음"]
    lines = [l for l in read(f).splitlines() if l.strip()]
    if len(lines) != len(run["screens"]):
        errs.append(f"URL 줄 수 {len(lines)} ≠ 시안 수 {len(run['screens'])}")
    pat = re.compile(rules["gates"]["G5"]["line_pattern"])
    for l in lines:
        if not pat.match(l.strip()):
            errs.append(f"형식 오류: {l}")
    return errs


GATES = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5}

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1].upper() not in GATES:
        sys.exit(__doc__)
    gate = sys.argv[1].upper()
    rdir = run_dir(sys.argv[2])
    errs = GATES[gate](rdir, load_run(rdir), load_rules())
    if errs:
        print(f"[{gate} 실패] {len(errs)}건")
        for e in errs[:20]:
            print(f"  - {e}")
        sys.exit(1)
    print(f"[{gate} 통과]")
    sys.exit(0)
