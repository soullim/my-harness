"""
NEIS 교육정보 개방포털(open.neis.go.kr) 학교기본정보 Open API 수집 스크립트.

사전 준비:
  1) https://open.neis.go.kr 에서 소셜 로그인 후 [인증키 신청] -> 무료 발급
  2) 환경변수로 키를 넘기거나, 아래 NEIS_API_KEY 상수에 직접 입력
  3) pip install requests

확인된 사실: 이 API는 KEY 없이도 호출은 되지만 pSize와 무관하게 응답이
5행으로 고정되는 것으로 보인다(트라이얼 제한 추정, 2026-09-16 확인). 구 단위로
학교를 훑으려면(예: 서울 300여개 고교 중 은평구만 추리기) 결국 정식 인증키가
필요하다. 인증키 없이 급하게 몇 개 학교만 확인할 땐 SCHUL_NM에 학교명을
정확히 넣어 1건씩 조회하면 5행 제한 안에서 전체 필드를 받을 수 있다.

주의:
  - 필드명(ATPT_OFCDC_SC_CODE 등)은 2026-09 기준 공개 문서를 참고해 작성했다.
    실제 호출 전 open.neis.go.kr의 "학교기본정보" 명세 페이지에서
    최신 필드 목록을 반드시 대조할 것 (교육부가 공시 항목을 개편하는 경우가 있음).
  - 이 스크립트는 "일반고" 필터링 + 특정 지역(LCTN_SC_NM) 조회 예시다.
    실제 서비스에서는 지역 코드 테이블을 별도로 관리해 시군구 단위까지 좁혀야 한다.
"""

import os
import sys
import json
import requests

NEIS_API_KEY = os.environ.get("NEIS_API_KEY", "")
BASE_URL = "https://open.neis.go.kr/hub/schoolInfo"


def fetch_school_info(region_name: str, school_kind: str = "고등학교",
                       hs_type: str = "일반고", page_size: int = 100) -> list[dict]:
    """지역명 + 학교종류 + 고교유형으로 학교 기본정보를 가져온다.

    region_name: 시도명 (예: '서울특별시', '경기도')
    school_kind: SCHUL_KND_SC_NM (초등학교/중학교/고등학교)
    hs_type:     HS_SC_NM (일반고/특수목적고/특성화고/자율고) - 고교만 해당
    """
    if not NEIS_API_KEY:
        raise RuntimeError(
            "NEIS_API_KEY가 설정되지 않았습니다. "
            "환경변수로 발급받은 인증키를 지정하세요. "
            "예) PowerShell: $env:NEIS_API_KEY='발급받은키'"
        )

    params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": page_size,
        "LCTN_SC_NM": region_name,
        "SCHUL_KND_SC_NM": school_kind,
    }
    if school_kind == "고등학교" and hs_type:
        params["HS_SC_NM"] = hs_type

    resp = requests.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if "schoolInfo" not in data:
        # 결과 없음 또는 에러 코드 반환 (예: INFO-200 조회된 데이터가 없습니다)
        result = data.get("RESULT", {})
        print(f"[NEIS] 조회 결과 없음: {result}", file=sys.stderr)
        return []

    rows = data["schoolInfo"][1]["row"]
    return [
        {
            "school_code": r.get("SD_SCHUL_CODE"),
            "name": r.get("SCHUL_NM"),
            "office_of_edu": r.get("ATPT_OFCDC_SC_NM"),
            "region": r.get("LCTN_SC_NM"),
            "establishment": r.get("FOND_SC_NM"),      # 공립/사립/국립
            "coed": r.get("COEDU_SC_NM"),               # 남녀공학 구분
            "hs_type": r.get("HS_SC_NM"),                # 일반고/특목고/특성화고/자율고
            "day_night": r.get("DGHT_SC_NM"),
            "address": r.get("ORG_RDNMA"),
            "homepage": r.get("HMPG_ADRES"),
            "tel": r.get("ORG_TELNO"),
            "founded": r.get("FOND_YMD"),
        }
        for r in rows
    ]


if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else "서울특별시"
    schools = fetch_school_info(region)
    print(json.dumps(schools, ensure_ascii=False, indent=2))
