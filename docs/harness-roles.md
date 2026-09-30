# 고교나침반 하네스 — 역할 (harness-roles.md)

> 기준 문서: docs/harness-pipeline.md (S1~S5), docs/harness-outputs.md (파일명), docs/harness-gates.md (게이트)

## 1. 에이전트

| 에이전트 | 단계 | 편집 가능한 폴더 (1개) | 쓰는 도구 |
|---|---|---|---|
| researcher | S1 리서치 | runs/<실행>/01-research/ | uibowl, 파일 쓰기 |
| planner | S2 설계 | runs/<실행>/02-spec/ | 파일 쓰기 |
| designer | S3 시안 | runs/<실행>/03-drafts/ | 파일 쓰기 |
| sharer | S5 공유 | runs/<실행>/05-share/ | 파일 쓰기 |
| judge | S4 판정 | 없음 (읽기 전용) | 판정 스크립트 실행만 |

- 에이전트는 자기 편집 폴더 밖에 파일을 쓰지 않는다
- 판정: 편집 폴더 밖에 쓴 파일 0건. 폴더 밖 쓰기는 설정(hook)이 막는다 [추가]

## 2. 모두 읽기 전용인 곳
- docs/, rules/, scripts/, CLAUDE.md
- 기존 프로토타입: ui_prototype.html, fetch_neis.py, build_profiles.py, sample_data/
- 규칙 값 변경은 본인이 rules/rules.json을 직접 고친다

## 3. 판정자 (judge)
- 파일 수정 도구 없음, 판정 스크립트 실행만 허용
- 04-verdict/violations.json과 report.md는 스크립트가 직접 쓴다
- judge는 결과를 읽고 통과/실패만 오케스트레이터에 알린다

## 4. 자연어 트리거

| 이렇게 말하면 | 동작 |
|---|---|
| "고교나침반 시안 만들어줘: <화면 2~3개>" | 새 실행 폴더를 만들고 S1부터 시작 |
| "이어서 해줘" | 가장 최근 실행의 run.json 단계부터 재개 |
| "판정만 다시 해줘" | S4만 다시 실행 |
| "승인" | 사람 승인 지점에서 S5 진행 |
| "반려: <사유>" | 사유를 입력으로 S3 복귀 |
| "피그마로 보내줘" | 통과한 시안을 피그마로 전송 (선택 단계) |

- 화면 이름은 한글 이름과 약어(region / list / compare / match / policy) 둘 다 받는다 [추가]
