# P-427 — DSM-U6-01 외부 이벤트 문의 인증 = 들어오는 키 + HMAC (턴 AP · 조율자 E)

| 항목 | 턴 AO(N4) | **턴 AP** |
|---|---|---|
| 인증 | JWT(사람 세션) | **들어오는 키** — JWT 로 온 요청은 핸들러 첫 줄 401 |
| 키 범위 | (규칙 없음 — 읽기 기본 키로도 들어올 수 있었다) | **`events:ingest`**(새 범위 · 기본 아님 · `key_scopes.PATH_SCOPES`) — 읽기 키 403 |
| 서명키 | 새 이름 `EXTERNAL_EVENT_SIGNING_KEYS`(새 자격 체계) | **웹훅 서명키 `agency` 재사용**(창 2b 에 실림 · 새 자격 0) — settings 블록 삭제 |
| 재생 | `webhook_contract` 시각 창 300초 | 같음(시험 1 추가) |
| D-335 ③ 래칫 | 쓰기 0 | **결정 번호 붙은 예외 1**. 짝 셋을 손으로 모두 열었다: 라우트 `inbound_key=True` · `access_gate.INBOUND_KEY_ALLOWED` · 시험 `DECIDED_INBOUND_WRITES` |

**시험**: `tests/test_dsm_u36_an.py::U6_01_ExternalEventsTest` 11(성공 3 · 키 없음 401 · JWT 401 · 서명 틀림 401 · 재생 401 · 읽기 키 403 · 스키마 없음 401 · 남의 테넌트 카메라 404 · 증거 표) + `test_f05_inbound_api_key` · `test_u3_pulse_inbound_key` · `test_access_gate` → **73 passed**.

**N4 가 적은 반론(보존)**
- 들어오는 이벤트의 서명키는 「상대가 이미 쥔 값」이라 우리가 만든 발신용 웹훅 키와 방향이 반대다.
- 세종 판정이 재사용이라 따랐다.
- 기관마다 키를 따로 두는 것은 다음 결정(새 자격 체계)이다.
