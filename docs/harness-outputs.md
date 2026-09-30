# 고교나침반 하네스 — 산출물 (harness-outputs.md)

> 기준 문서: docs/harness-pipeline.md (S1~S5 단계)

## 1. 실행 폴더
- 실행할 때마다 새 폴더 `runs/YYYYMMDD-HHMM/`를 만든다
- 이전 실행 결과는 덮어쓰지 않는다

## 2. 화면 약어 (파일명·URL용)
| 화면 | 약어 |
|---|---|
| 지역 선택 | region |
| 일반고 목록 | list |
| 학교 비교 | compare |
| 조건 매칭 | match |
| 정책 업데이트 | policy |

## 3. 단계별 파일
| 단계 | 파일 | 완료 판정 |
|---|---|---|
| 공통 | run.json | 입력 화면·현재 단계·재시도 횟수 필드가 있음 |
| S1 | 01-research/references.md | 파일 존재 + 선택한 화면마다 섹션 1개 |
| S2 | 02-spec/<약어>.md | 선택한 화면 수만큼 파일 존재 |
| S3 | 03-drafts/<약어>.html | 선택한 화면 수만큼 파일 존재 |
| S4 | 04-verdict/violations.json | 파일 존재 (위반 0건이면 빈 목록 `[]`) |
| S4 | 04-verdict/report.md | 사람용 요약 (판정에는 쓰지 않음) |
| S5 | 05-share/share-urls.txt | 줄 수 = 시안 수, 형식 `시안 A — <URL>` |

### run.json 필드
| 필드 | 예시 |
|---|---|
| screens | ["compare", "list"] |
| stage | "S3" |
| retry | 1 (S4 실패로 S3에 돌아간 횟수, 최대 2) |
| status | "running" / "done" / "stopped" |

## 4. 규칙 SSOT
- 스크립트 판정 규칙은 `rules/rules.json` 한 파일에만 적는다
- 들어가는 값: 허용 색 hex, 폰트, 글자 크기, 간격, 라운드, 프레임 390×844, V1 금지어, V2 표기 패턴, 재시도 최대 2회
- docs/school-design.md는 사람이 읽는 설명 문서로 둔다
- 두 파일 값이 다르면 rules.json이 우선한다
- rules.json 세부 값은 R5 게이트에서 확정한다

## 5. 재개
- run.json의 stage부터 다시 시작한다
- 단계 출력 파일이 완료 판정을 통과하면 그 단계는 건너뛴다
- status가 "stopped"(재시도 초과)면 재개하기 전에 사람이 확인한다
