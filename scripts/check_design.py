"""S4 판정 스크립트 (정적 검사).

사용: python scripts/check_design.py <실행폴더>
      python scripts/check_design.py --file <html> [--screen <약어>]   (tests용, 결과를 화면에 출력만)

HTML·CSS 텍스트에서 값을 직접 읽어 rules/rules.json과 비교한다.
실행폴더 모드에서는 04-verdict/violations.json 과 report.md 를 이 스크립트가 직접 쓴다.
종료 코드: 위반 0건이면 0, 1건 이상이면 1.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from _common import load_rules, load_run, read, run_dir, write

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
INLINE_STYLE = re.compile(r"<([a-zA-Z0-9-]+)[^>]*\sstyle\s*=\s*([\"'])(.*?)\2", re.S)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
HEX = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RGBA = re.compile(r"(rgba?|hsla?)\([^)]*\)", re.I)
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)")
PX = re.compile(r"^(-?\d+(?:\.\d+)?)px$")

SPACING_PROPS = {
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-inline", "margin-block-start", "margin-block-end",
    "margin-inline-start", "margin-inline-end",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-block", "padding-inline", "padding-block-start", "padding-block-end",
    "padding-inline-start", "padding-inline-end",
    "gap", "row-gap", "column-gap",
}
RADIUS_PROPS = {
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius",
}
KEYWORDS_OK = {"auto", "inherit", "initial", "unset", "0"}


def norm_hex(h):
    h = h.upper()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return "#" + h[:6]


def norm_rgba(s):
    return re.sub(r"\s+", "", s.lower())


def parse_declarations(block):
    decls = []
    for part in block.split(";"):
        if ":" not in part:
            continue
        prop, val = part.split(":", 1)
        prop, val = prop.strip().lower(), val.strip()
        val = re.sub(r"\s*!important\s*$", "", val, flags=re.I)
        if prop:
            decls.append((prop, val))
    return decls


def collect(html):
    """(selector, prop, value) 목록과 사용자 정의 변수 사전을 돌려준다."""
    items = []
    css = "\n".join(STYLE_BLOCK.findall(html))
    css = CSS_COMMENT.sub("", css)
    for sel, body in RULE.findall(css):
        sel = sel.strip()
        for prop, val in parse_declarations(body):
            items.append((sel, prop, val))
    for tag, _q, body in INLINE_STYLE.findall(html):
        for prop, val in parse_declarations(body):
            items.append((f"<{tag.lower()} style>", prop, val))
    variables = {p: v for _s, p, v in items if p.startswith("--")}
    return items, variables


def resolve(val, variables, depth=0):
    if depth > 5 or "var(" not in val:
        return val

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        return variables.get(name, (fallback or "").strip())

    return resolve(VAR.sub(sub, val), variables, depth + 1)


def visible_text(html):
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;", " ", t)
    return re.sub(r"\s+", " ", t)


def emoji_regex(ranges):
    parts = []
    for r in ranges:
        if "-" in r:
            a, b = r.split("-")
            parts.append(f"\\U{int(a, 16):08X}-\\U{int(b, 16):08X}")
        else:
            parts.append(f"\\U{int(r, 16):08X}")
    return re.compile("[" + "".join(parts) + "]")


def check_html(html, screen, rules):
    v = []

    def add(rule_id, value, allowed, where=""):
        v.append({"screen": screen, "rule": rule_id, "value": value,
                  "allowed": allowed, "where": where})

    items, variables = collect(html)
    hex_ok = {h.upper() for h in rules["colors_hex"]}
    rgba_ok = {norm_rgba(x) for x in rules["colors_rgba_allowed"]}
    named_bad = set(rules["colors_named_forbidden"])
    accent = rules["accent"]["hex"].upper()
    fam_ok = {f.lower() for f in rules["font_families"]}
    size_ok = set(rules["font_sizes_px"])
    space_ok = set(rules["spacing_px"])
    radius_ok = set(rules["radius_px"])
    ls_ok = set(rules["letter_spacing_allowed"])
    shadow_key = rules["shadow"]["allowed_only_when_selector_contains"]
    accent_uses = 0

    for sel, prop, raw in items:
        val = resolve(raw, variables)
        where = f"{sel} {{ {prop}: {raw} }}"

        # 색 (사용자 정의 변수 정의 자체도 검사)
        for h in HEX.findall(val):
            nh = norm_hex(h)
            if nh not in hex_ok:
                add("color", nh, "rules.colors_hex", where)
        for m in RGBA.finditer(val):
            if norm_rgba(m.group(0)) not in rgba_ok:
                add("color", m.group(0), "rules.colors_rgba_allowed", where)
        if prop in {"color", "background", "background-color", "border", "border-color", "fill", "stroke", "outline", "outline-color"}:
            for word in re.findall(r"[a-zA-Z]+", val):
                if word.lower() in named_bad:
                    add("color", word, "hex 토큰만 사용", where)

        if prop.startswith("--"):
            continue  # 변수 정의는 색만 검사하고, 나머지는 사용하는 곳에서 검사

        # 액센트
        if accent in {norm_hex(h) for h in HEX.findall(val)}:
            accent_uses += 1
            if rules["accent"]["forbid_on_button_background"] and prop in {"background", "background-color"} \
                    and re.search(r"button|btn|cta", sel, re.I):
                add("accent", "버튼 배경에 액센트", "액센트는 CTA에 쓰지 않음", where)

        # 서체
        if prop == "font-family":
            for fam in val.split(","):
                f = fam.strip().strip("'\"").lower()
                if f and f not in fam_ok:
                    add("font_family", fam.strip(), "rules.font_families", where)

        # 글자 크기
        if prop == "font-size":
            m = PX.match(val)
            if val not in KEYWORDS_OK and not (m and float(m.group(1)) in size_ok):
                add("font_size", val, "rules.font_sizes_px", where)

        # 간격
        if prop in SPACING_PROPS:
            for token in val.split():
                if token in KEYWORDS_OK:
                    continue
                m = PX.match(token)
                if not (m and float(m.group(1)) in space_ok):
                    add("spacing", token, "rules.spacing_px", where)

        # 라운드
        if prop in RADIUS_PROPS:
            for token in val.replace("/", " ").split():
                if token in KEYWORDS_OK:
                    continue
                m = PX.match(token)
                if not (m and float(m.group(1)) in radius_ok):
                    add("radius", token, "rules.radius_px", where)

        # 그림자
        if prop == "box-shadow" and val.lower() not in {"none", "0", "initial", "unset"}:
            if shadow_key not in sel.lower():
                add("shadow", val, "그림자 없음 (segmented 예외)", where)

        # 자간·대문자
        if prop == "letter-spacing" and val not in ls_ok:
            add("letter_spacing", val, "rules.letter_spacing_allowed", where)
        if prop == "text-transform" and val.lower() in rules["text_transform_forbidden"]:
            add("uppercase", val, "대문자 변환 금지", where)

    if accent_uses > rules["accent"]["max_per_screen"]:
        add("accent", f"{accent_uses}곳", f"화면당 {rules['accent']['max_per_screen']}곳 이하")

    # SVG 등 속성으로 들어간 색 (fill="#..." stroke="#...")
    for attr, h in re.findall(r"\s(fill|stroke|stop-color|color)\s*=\s*[\"']#([0-9a-fA-F]{3,8})[\"']", html):
        if norm_hex(h) not in hex_ok:
            add("color", norm_hex(h), "rules.colors_hex", f'{attr}="#{h}"')

    text = visible_text(html)

    # 이모지
    found = emoji_regex(rules["emoji_ranges"]).findall(text)
    if found:
        add("emoji", "".join(sorted(set(found))), "이모지 없음")

    # V1 서열화 금지
    for pat in rules["v1_rank_patterns"]:
        for m in re.finditer(pat, text):
            add("V1", m.group(0), "순위 표현 0건", text[max(0, m.start() - 12):m.end() + 12])
    for m in re.finditer(rules["v1_raw_achievement_pattern"], text):
        add("V1", m.group(0), "학업성취도 원자료 0건")

    # V2 기준 시점·출처
    if screen in rules["v2"]["applies_to"] or screen == "_test":
        if not re.search(rules["v2"]["date_pattern"], text):
            add("V2", "기준 날짜 없음", "\"기준 YYYY.MM.DD\" 1개 이상")
        if rules["v2"]["source_word"] not in text:
            add("V2", "출처 없음", "\"출처\" 1개 이상")

    return v


def write_report(rdir, violations, screens):
    lines = ["# 판정 결과 (S4)", "", f"- 대상 화면: {', '.join(screens)}",
             f"- 위반 합계: {len(violations)}건", ""]
    if violations:
        lines += ["| 화면 | 규칙 | 현재 값 | 허용 값 |", "|---|---|---|---|"]
        for x in violations:
            lines.append(f"| {x['screen']} | {x['rule']} | {x['value']} | {x['allowed']} |")
    else:
        lines.append("위반 없음. 사람 승인 단계로 넘어갈 수 있습니다.")
    write(rdir / "04-verdict" / "report.md", "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--screen", default="_test")
    args = ap.parse_args()
    rules = load_rules()

    if args.file:
        vs = check_html(read(args.file), args.screen, rules)
        print(json.dumps(vs, ensure_ascii=False, indent=2))
        sys.exit(1 if vs else 0)

    if not args.run:
        sys.exit("사용: python scripts/check_design.py <실행폴더>")
    rdir = run_dir(args.run)
    run = load_run(rdir)
    violations = []
    for s in run["screens"]:
        f = rdir / "03-drafts" / f"{s}.html"
        if not f.exists():
            violations.append({"screen": s, "rule": "missing", "value": f"{s}.html 없음",
                               "allowed": "화면마다 시안 1개", "where": ""})
            continue
        violations += check_html(read(f), s, rules)
    write(rdir / "04-verdict" / "violations.json", json.dumps(violations, ensure_ascii=False, indent=2))
    write_report(rdir, violations, run["screens"])
    print(f"[S4 판정] 위반 {len(violations)}건 → 04-verdict/violations.json")
    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
