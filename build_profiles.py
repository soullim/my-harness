"""
NEIS 학교기본정보 + 학교알리미 공시자료(CSV)를 병합해
서비스용 "학교 프로필" 통합 스키마를 만들고 5축 성향 지표를 계산한다.

학교알리미 공시자료 확보 방법 (Open API 계약이 문서마다 달라 자동화 대신 이 경로를 권장):
  1) https://www.data.go.kr 에서 "학교알리미 공시정보" 데이터셋 검색
  2) 학사년도 / 시도 / 학교급을 선택해 "학생현황", "교원현황",
     "학급당 학생수", "졸업생의 진로현황", "학교폭력 발생현황 등"
     항목별 CSV를 내려받아 disclosure_raw/ 폴더에 저장
  3) 아래 REQUIRED_COLUMNS에 맞춰 CSV를 하나로 정리(또는 각 파일을 학교코드 기준 merge)

이 스크립트는 병합된 CSV(disclosure_raw/merged.csv)를 입력으로 받는다.
CSV가 없으면 sample_data/sample_schools.json 을 그대로 사용해
프로토타입 화면이 항상 돌아가도록 한다.
"""

import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DISCLOSURE_CSV = os.path.join(BASE_DIR, "disclosure_raw", "merged.csv")
SAMPLE_JSON = os.path.join(BASE_DIR, "sample_data", "sample_schools.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "sample_data", "school_profiles.json")

REQUIRED_COLUMNS = [
    "school_code",        # SD_SCHUL_CODE (NEIS와 조인 키)
    "students_total",     # 학생현황 - 전체 학생수
    "classes_total",      # 학급현황 - 전체 학급수
    "teachers_total",     # 교원현황 - 전체 교원수
    "elective_subjects",  # 선택과목 개설 수 (고교학점제 관련 공시)
    "transfer_out_rate",  # 전출률(%)
    "special_hs_feed_rate",   # 배정 중학교 특목고/자사고 진학 비율(%) - 진로진학 공시 연계
    "facility_budget_index",  # 시설·재정 관련 지표(자체 정규화 값, 0~100)
]


def normalize(value, lo, hi, invert=False):
    """min-max 정규화(0~100). invert=True면 값이 낮을수록 좋은 지표(예: 전출률)."""
    v = max(lo, min(hi, value))
    score = (v - lo) / (hi - lo) * 100 if hi > lo else 50
    return round(100 - score if invert else score, 1)


def compute_composite_axes(row: dict) -> dict:
    """공시 원자료 -> 화면에 쓰는 5축 성향 지표로 변환.

    실제 서비스에서는 이 가중치/구간을 지역 전체 분포(백분위)로 재계산해야 하며,
    여기서는 프로토타입 검증용으로 고정 구간을 사용한다.
    """
    class_size = row["students_total"] / max(row["classes_total"], 1)
    teacher_ratio = row["students_total"] / max(row["teachers_total"], 1)

    return {
        "focus_intensity": normalize(row["special_hs_feed_rate"], 0, 60),
        "class_room_margin": normalize(class_size, 20, 35, invert=True),
        "track_diversity": normalize(row["elective_subjects"], 10, 60),
        "environment_investment": normalize(row["facility_budget_index"], 0, 100),
        "cohort_stability": normalize(row["transfer_out_rate"], 0, 8, invert=True),
        "_debug_class_size": round(class_size, 1),
        "_debug_teacher_ratio": round(teacher_ratio, 1),
    }


def load_disclosure_rows() -> dict:
    if not os.path.exists(DISCLOSURE_CSV):
        print(f"[안내] {DISCLOSURE_CSV} 가 없어 공시자료 병합 단계를 건너뜁니다.",
              file=sys.stderr)
        return {}

    rows = {}
    with open(DISCLOSURE_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV에 필수 컬럼이 없습니다: {missing}")
        for r in reader:
            code = r["school_code"]
            rows[code] = {k: float(r[k]) if k != "school_code" else r[k]
                          for k in REQUIRED_COLUMNS}
    return rows


def merge_with_neis(neis_schools: list[dict], disclosure: dict) -> list[dict]:
    profiles = []
    for school in neis_schools:
        code = school["school_code"]
        disc = disclosure.get(code)
        profile = dict(school)
        if disc:
            profile["axes"] = compute_composite_axes(disc)
            profile["source"] = "neis+disclosure"
        else:
            profile["axes"] = None
            profile["source"] = "neis-only (공시자료 미병합)"
        profiles.append(profile)
    return profiles


if __name__ == "__main__":
    disclosure = load_disclosure_rows()

    if not disclosure:
        print(f"[안내] 데모용으로 {SAMPLE_JSON} 을 그대로 출력합니다.")
        with open(SAMPLE_JSON, encoding="utf-8") as f:
            print(f.read())
        sys.exit(0)

    from fetch_neis import fetch_school_info  # 실제 키가 있을 때만 사용

    region = sys.argv[1] if len(sys.argv) > 1 else "서울특별시"
    neis_schools = fetch_school_info(region)
    profiles = merge_with_neis(neis_schools, disclosure)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    print(f"[완료] {len(profiles)}개 학교 프로필을 {OUTPUT_JSON} 에 저장했습니다.")
