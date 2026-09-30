# 차선 Q · 턴 AQ 진행 (P-440 — 끊기면 이어받는 차선이 읽는다)

## ① P-431 증거 표 분리 2단계 — 끝남
- 공용 읽개 `scripts/_retro_table.py`(판정기 아님 · 읽기만 · 자기시험 출생 표본).
- `scripts/verify_spec_title_parts.py` — 표는 `<id>.retro.md` 에서만 · json 표 무시 · 게이트 1행 「사람 표 diff 0」(정적 + 런타임) · 자기시험 짝 · 「깨끗함」 칸 수 버그(늘 0) 고침.
- 판정기 9(조율자 판정으로 이 턴 Q 소유 · `_load_evidence` 끝 overlay 한 줄): ap_n4 · dsm_u36 · dsm_u4 · fws_f3 · fws_f3b · fws_f4 · ops · u5_an · fws_f6 — 이주 전후 PASS/FAIL 수 같음.
- `backend/common/evidence_guard.py` — `.retro.md` 는 이름을 대도 못 쓴다.
- 쓰개 시험 — json 에 title_parts·retro 안 씀.
- 걷기 `scripts/strip_spec_human_keys.py --apply` 적용: 101 걷음 · 보류 0. 재실행 가능(멱등 · LF 유지).
- `TITLE_PARTS_RULE.md` §4-1 파일 둘 규칙.

## ② P-433 — 끝남 (`--c-from-ledger`·`--onboarding-md`·`c_rows_from_markdown` 삭제 · 시험 갱신 · argparse 오류 시험)
## ③ P-437 — 고침(탐침 포함 목록에서 U1#11 표본) · U5#5 원인 1줄 · P-438 `OPS-13a/observations.md`
## ④ P-439 — conftest autouse `clear_thread_request` + 시험
## 끝 — 좁은 시험 31파일 256 통과 · 4 skip(옛 docs 마운트) · 0 실패 · 보고함
