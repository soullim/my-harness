# 고교나침반 하네스 — 오케스트레이터 (harness-orchestrator.md)

> 오케스트레이터 = CLAUDE.md를 읽고 움직이는 메인 Claude Code 세션
> 기준 문서: docs/harness-roles.md (에이전트·트리거), docs/harness-gates.md (게이트), docs/harness-outputs.md (run.json)

## 1. 하는 일
- 자연어 트리거 해석 (docs/harness-roles.md 4절)
- 실행 폴더 `runs/YYYYMMDD-HHMM/` 만들기
- 단계별 에이전트 호출 (researcher → planner → designer → judge → sharer)
- 단계마다 게이트 스크립트 실행
- 사람 승인 요청 (G4 통과 후, S5 전)

## 2. 하지 않는 일
- 리서치·설계·시안·공유 파일을 직접 고치지 않는다 (오케스트레이터 편집 파일 0건)
- run.json을 직접 고치지 않고 상태 스크립트로만 갱신한다 [추가]
- 규칙 값을 바꾸지 않는다 (rules.json은 본인만 수정)

## 3. 단계 전환 조건
- 게이트 스크립트가 통과(종료 코드 0)를 냈을 때만 다음 단계로 간다
- 에이전트의 "완료했다"는 말만으로는 넘어가지 않는다
- 실패하면 docs/harness-gates.md 5절의 복귀 규칙을 따른다

## 4. CLAUDE.md 작성 원칙
- 규칙 값은 복사하지 않고 docs/ 파일과 rules/rules.json 경로만 가리킨다
- 분량 150줄 이내 [추가]

## 5. 멈춤(stopped) 보고 형식 [추가]
1. 멈춘 단계와 이유
2. 위반 목록 상위 5건: 화면 / 규칙 / 현재 값 / 허용 값
3. 다음 선택지
   - "이어서 해줘" → 본인 확인으로 보고 재시도 횟수를 초기화한 뒤 재개
   - "반려: <사유>" → 사유를 입력으로 S3 복귀
   - 규칙 직접 수정 → rules.json을 고친 뒤 "판정만 다시 해줘"
