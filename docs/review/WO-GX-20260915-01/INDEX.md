# WO-GX-20260915-01 — 캡처 색인 (턴 W · V 단독)

- 만든 때: 2026-09-19 (턴 W · V). 이 디렉터리는 이번 턴에 처음 생겼다 — 턴 U·V 는 자리가 없어 회색이었다.
- 도구: `scripts/capture_screens.py --persona U4|U5` (gx-shell 안 실제 브라우저 · 역할 계정)
- 원본: `docs/agent/evidence/D-347/screens/SCREENS-1/<ROLE>/<route>.png` — 여기 것은 사본이다.

## 찍은 것 — 12장 (정상 상태 1종만)
| 화면코드 | 사람 | 역할 | 잰 때 |
|---|---|---|---|
| surveillance-dashboard · media-data · flight-log-analysis · report-template · notam · dsm_audit_read | U4 | view_only_-_anyang | 2026-09-19 19:36~19:37 |
| menu · configuration-management · profile · operation-settings · dsm_notify_recipients · dsm_integrations_api_keys | U5 | admin | 2026-09-19 19:38~19:39 |

## 못 찍은 것 — 사유를 적는다 (회색은 초록이 아니다)
- `/device` (U5) — 기다린 글자 `Add New Device` 가 화면에 없다. 같은 턴 온보딩 실측도 U4#11 `/device` 표 행 0 으로 **빨강**이다.
- `/roles` (U5) — 기다린 글자 `Add New Role` 이 화면에 없다. 같은 턴 온보딩 실측도 U5#2 `/roles` 표 행 0 으로 **빨강**이다.
- `/survey-profile` (U5) — 등재된 빈 화면(`KNOWN_BLANK`). 종전부터 못 찍는다.
  (이 셋의 **낡은 PNG 가 원본 자리에 남아 있으나** 이번 턴 것이 아니므로 여기 싣지 않았다.)

## AC-8 의 「5상태」는 **안 쟀다** — 도구가 없다
지시서 AC-8 은 화면마다 **5상태**(정상·빈·오류·로딩·권한)를 요구한다.
이 저장소에서 PNG 를 남기는 도구는 `capture_screens.py` 하나뿐이고, 그것은 **정상 상태 한 장**만 찍는다.
오류·빈·폼 상태를 **누르는** 도구(`walk_states.py`)는 있으나 **사진을 남기지 않는다**(판정 JSON 만 낸다).
그러므로 5상태 중 **1상태만 찍혔고 4상태는 못 찍었다** — 도구가 없어서다. 고치지 않았다(V 는 색만 낸다).
