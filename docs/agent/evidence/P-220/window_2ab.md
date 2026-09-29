# 창 2a · 2b 집행 — 증거 자리 (P-220 · 턴 AN 2026-09-29 · 조율자)

이 파일은 기록을 **가리킨다**. 수와 걸음은 원본 기록에 있다(두 벌을 두지 않는다).

| 창 | 집행 | 원본 기록 | 닫은 것 |
|---|---|---|---|
| 2a | 2026-09-22 (턴 AC) | `docs/agent/runbook/창2a_실행기록_20260922.md` | 그 기록의 표 |
| 2b (웹푸시 새 쌍) | 2026-09-23 (턴 AE · `709a5aa`) | `docs/agent/runbook/창2b_20260923_웹푸시새쌍.md` | VAPID 3 두 통 실림 |
| 2b (SMTP·서명키·K2·시험 DB) | **2026-09-29 11:20~11:40** (턴 AN · P-391 · 대표 「창 2b 열어라 — 두 통 재생성」) | `docs/agent/runbook/창2b_집행기록_20260929.md` | 두 통 재생성 · `WEBHOOK_SIGNING_KEYS` 이름 셋 · SMTP 여섯(Mailpit) · K2 세 줄 + `DEFAULT_FROM_EMAIL` · `verify_prod_settings` 7/7 · 비번 한 바퀴 1 · K2 훈련 1통 · 시험 DB 21 삭제 |

**남은 것**
- 실기기 웹푸시 도달 1 — 대표 크롬 손(`/m/settings`). 아직 없음.
- `gx-portfwd` 삭제 — 보류. 호스트 8000 을 쓰는 게이트를 옮긴 뒤에 지운다(집행 기록 §portfwd).
- 실 SMTP — 금고 `smtp.env` 가 없다. Mailpit 한 바퀴까지만.
