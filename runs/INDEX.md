# 실행 산출물 목록

> scripts/organize_outputs.py 가 2026-10-07 13:08에 작성. 직접 고치지 않는다 (다시 실행하면 덮어쓴다). 실행 1개.

## 한눈에

| 실행 | 화면 | 단계 | 상태 | 승인 | 게이트 | 위반 | 남은 일 |
|---|---|---|---|---|---|---|---|
| [20260930-1616](#20260930-1616) | compare, list | S5 | running | 완료 | 4/5 통과 (G5 미통과) | 0 | 공유 보류 |

## 20260930-1616

- 화면: 학교 비교(compare), 일반고 목록(list)
- 상태: running · 단계 S5 · 승인 완료
- 재시도: G4 0회 · 반려 0회 · 게이트 실패 기록 G5
- 게이트: G1 통과 · G2 통과 · G3 통과 · G4 통과 · G5 미통과
- 위반: 0건
  - G5 사유: 05-share/share-urls.txt 없음

| 단계 | 파일 | 상태 |
|---|---|---|
| S1 | [01-research/references.md](20260930-1616/01-research/references.md) | 있음 |
| S2 | [02-spec/compare.md](20260930-1616/02-spec/compare.md) | 있음 |
| S2 | [02-spec/list.md](20260930-1616/02-spec/list.md) | 있음 |
| S3 | [03-drafts/compare.html](20260930-1616/03-drafts/compare.html) | 있음 |
| S3 | [03-drafts/list.html](20260930-1616/03-drafts/list.html) | 있음 |
| S4 | [04-verdict/violations.json](20260930-1616/04-verdict/violations.json) | 있음 |
| S4 | [04-verdict/report.md](20260930-1616/04-verdict/report.md) | 있음 |
| S5 | 05-share/share-urls.txt | 없음 |
| 완료 | review.md | 없음 |

남은 일:
- 공유 보류 — rules/rules.json 의 share.base_url 이 비어 있어 S5가 멈춤 (값을 채운 뒤 '이어서 해줘')
