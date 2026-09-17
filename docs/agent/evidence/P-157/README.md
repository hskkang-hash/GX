# P-157 — 실행분(`runs/`)과 대장의 관계 · 규약 (턴 T · 차선 Q · P-159 ③)

**대장은 줄지 않는다(P-154).** 생성기는 자기가 만든 것만 알기 때문에 대장을 통째로 쓰게 두지 않는다 —
**이번 실행분은 `runs/` 에 그대로, 대장에는 옛 항목 + 이번 항목**을 쓴다. 합치기와 「줄면 멈춤」은
`scripts/ledger_merge.py`(`merge_records` · `assert_not_shrunk`) 한 곳이고, 게이트 `scripts/verify_ledger_monotonic.py` 가
HEAD 와 대조한다.

| 생성기 | 이번 실행분(그대로) | 대장(합쳐 씀) | 열쇠 |
|---|---|---|---|
| `scripts/capture_screens.py` | `P-157/runs/<RUN_STAMP>/INDEX_entries.json` · `run_log.json` · `screen_routes.json` | `D-347/screens/INDEX.yaml` · `D-347/screens/run_log.json` · `D-386/screen_routes.json` | PNG 파일 경로(역할 폴더 포함) · 단계 번호 · 화면 자리 |
| `scripts/walk_scenarios.py` (턴 T 부터) | `UX-WALK/runs/walk_<stamp>.json` | `UX-WALK/walk.json` = `{"ledger", "latest_when", "runs": […]}` | `when`(걷기 시각) |

- `walk.json` 의 HEAD 판(2026-09-05 · `runs` 없이 실행 하나가 통째)은 **실행 1회**로 읽는다 — 버리지 않는다.
- PNG 는 **「대체」 규칙**이다(`capture_screens.replace_plan` · 턴 T): 같은 파일명이면 새 것으로 대체 · 이번에 안 찍은 파일명은 남긴다 ·
  **지우지 않는다.** 종전의 「첫 페르소나에서 `SCREENS-1` 을 비운다」는 대장이 합쳐 쓰이는 지금은 틀린 처방이라 뗐다.
  유령이 걱정되면 지우지 말고 대조한다(`verify_screens.py`).
- `runs/` 안의 파일은 **손대지 않는다.** 실행분은 실행분이다 — 고치면 대장과 갈린다.
- 등록 요청(조율자 · `verify_ledger_monotonic.LEDGERS`): `("walk.json", "docs/agent/evidence/UX-WALK/walk.json", count_walk, "회")` —
  세는 법은 `runs` 가 있으면 `len(runs)`, 없으면 1. 등록 전까지 이 대장은 게이트 밖이다(회색).
