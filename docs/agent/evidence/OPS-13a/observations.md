# OPS-13a — 관측 줄 (원인 미상 502 · 지어내지 않는다)

P-438(WO-20 §5 · 턴 AQ · 차선 Q). 원인을 모르는 502 한 번은 **관측 줄 하나**로만 적는다 —
시각 · 앞문 · 뒷단 칸을 채우고, 모르는 칸은 「미확인」으로 둔다. 다시 나면 그때 원인을 잰다
(`scripts/verify_front_line_502.py` · 이 폴더의 README §2 대조 방법).

| 시각(UTC) | 앞문(요청) | 뒷단 | 원인 | 재현 | 출처 |
|---|---|---|---|---|---|
| 2026-09-29T11:23:02Z | `gx-nginx-e:8500` · `GET /api/dsm/events?limit=1`(무인증 · 「누른 뒤」 U6#12 인증 실패 처리 — 기대 401) → **502** nginx 기본 오류 본문 | 미확인 — 그 순간의 `gx-gunicorn-e` 로그(`Worker exiting`·재기동)를 대조하지 않았다 | 미상 | 0(WO-20 §5 P-438) | `docs/agent/evidence/P-118/click_completes.json::observations["U6#12"]`(measured_at 2026-09-29T11:23:02Z) |
