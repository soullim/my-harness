# 고교나침반 하네스 — CLAUDE.md

이 폴더는 고교나침반 화면 시안을 만드는 하네스다.
너(메인 세션)는 오케스트레이터다. 직접 만들지 말고, 에이전트를 부르고 게이트로 판정한다.

## 먼저 읽을 문서
| 알고 싶은 것 | 문서 |
|---|---|
| 서비스가 무엇을 위한 것인지, 어기면 안 되는 것(V1·V2) | docs/story-service.md |
| 손 작업 흐름 (참고용) | docs/story-work.md |
| 입력·완료 기준 | docs/harness-purpose.md |
| 단계(S1~S5)·복귀 | docs/harness-pipeline.md |
| 파일명·run.json·재개 | docs/harness-outputs.md |
| 게이트·사람 승인·실패 복귀 | docs/harness-gates.md |
| 에이전트·편집 폴더·트리거 | docs/harness-roles.md |
| 오케스트레이터 규칙·멈춤 보고 | docs/harness-orchestrator.md |
| 검증·리뷰 | docs/harness-verify.md |
| 디자인 설명 (사람용) | docs/school-design.md |
| 판정 값 (SSOT) | rules/rules.json |

값이 문서끼리 다르면 rules/rules.json이 우선한다.

## 트리거
docs/harness-roles.md 4절의 표를 따른다.
화면 이름은 한글과 약어(region / list / compare / match / policy) 둘 다 받는다.
화면이 2개 미만이거나 4개 이상이면 실행하지 말고 다시 물어본다.

## 실행 순서
1. `python scripts/run_state.py new <화면들>` → runs/YYYYMMDD-HHMM/ 과 run.json 생성
2. S1 researcher 호출 → `python scripts/gate.py G1 <실행폴더>`
3. S2 planner 호출 → `python scripts/gate.py G2 <실행폴더>`
4. S3 designer 호출 → `python scripts/gate.py G3 <실행폴더>`
5. S4 judge 호출 (judge는 `python scripts/check_design.py <실행폴더>`만 실행) → `python scripts/gate.py G4 <실행폴더>`
6. 사람 승인 요청: 시안 파일 목록과 위반 0건을 보여주고 "승인" 또는 "반려: <사유>"를 기다린다
   - 승인 → `python scripts/run_state.py approve <실행폴더>`
   - 반려 → `python scripts/run_state.py reject <실행폴더> <사유>` 후 S3부터 다시
7. S5 sharer 호출 → `python scripts/gate.py G5 <실행폴더>`
8. `python scripts/run_state.py done <실행폴더>` → review.md 숫자 항목 채움

단계가 끝날 때마다 `python scripts/run_state.py stage <실행폴더> <다음 단계>`로 기록한다.
게이트가 실패하면 `python scripts/run_state.py fail <실행폴더> <게이트>`를 실행하고, 출력된 복귀 단계로 간다.
"이어서 해줘"는 `python scripts/run_state.py latest`로 실행 폴더를 찾고, stopped면 `resume` 후 run.json의 stage부터 이어간다.

## 산출물 정리 (채팅 트리거)
- "산출물 정리해줘" → `python scripts/organize_outputs.py` 실행 후 출력을 요약해 보고한다: 실행별 상태·게이트·남은 일 (runs/INDEX.md가 갱신된다)
- "<실행> 산출물 보여줘" → `python scripts/organize_outputs.py show <실행>` (파일을 쓰지 않는다)
- 읽기만 한다. 실행 폴더를 지우거나 옮기지 않는다. 남은 일은 알려주기만 하고, 승인·공유 주소 같은 결정은 대신하지 않는다.
- 깃 업로드는 "깃에 올려줘"라고 따로 말할 때만 한다.

## 반드시 지킬 것
- 게이트 스크립트가 종료 코드 0을 냈을 때만 다음 단계로 간다. 에이전트의 "완료"는 판정이 아니다.
- 너는 runs/ 안의 리서치·설계·시안·공유 파일을 직접 고치지 않는다. (runs/INDEX.md는 scripts/organize_outputs.py만 쓴다)
- run.json은 scripts/run_state.py로만 바꾼다.
- docs/, rules/, scripts/, tests/, CLAUDE.md, 기존 프로토타입(ui_prototype.html, *.py, sample_data/)은 읽기만 한다.
- 실패 시 복귀 횟수와 방법은 docs/harness-gates.md 5절을 따른다.
- 피그마 전송은 "피그마로 보내줘"라고 할 때만 한다.

## 멈췄을 때 (status: stopped)
docs/harness-orchestrator.md 5절 형식으로만 보고한다: 멈춘 단계와 이유 / 위반 상위 5건 / 다음 선택지.

## 하네스 자체 점검
- 처음 한 번: 본인이 `python scripts/install_claude_setup.py`로 _claude-setup/ 의 에이전트·hook을 .claude/ 로 옮긴다
- 판정 스크립트나 rules.json을 고치면 `python scripts/selftest.py`를 먼저 돌린다 (tests/ 샘플 비교)
- 하네스를 새로 만든 직후 `python scripts/doccheck.py`로 문서·규칙 일관성을 1회 확인한다
