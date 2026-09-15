# U6#4 · SEC-16 — 웹훅 서명키 목록이 비어 있다 (턴 Q · 차선 U56)

**판정** 환경의 결함 · 코드는 옳다 — 이 차선은 `.env*` 를 만지지 못한다(등록 요청으로 남긴다).

## 1. 실측 (2026-09-15 · gx-shell · 개발 DB · 이름만, 값 없음)

```python
settings.WEBHOOK_SIGNING_KEYS  →  {} (키 0개)
```

환경변수 `WEBHOOK_SIGNING_KEYS` 가 이 환경에 **아예 없다**
(`backend/config/settings.py:1283` `_parse_webhook_signing_keys(os.environ.get(...))`).

## 2. 코드 경로가 하는 일 (`backend/common/webhook_outbox.py`)

`register()`(202행)는 `signing_secret(ref)` 가 빈 문자열이면 `UnknownSigningKey`(422)로
**등록 자체를 거절한다** — "등록은 됐는데 못 보내는 구독"을 만들지 않기 위한 설계
(202~220행). 즉 이 환경에서는 **어떤 서명키 이름으로도 구독이 절대 만들어지지 않는다** —
구독이 0건이니 목록도 0건이고, 그래서 "서명키 목록이 비어 있다"로 보인다.

`test_s_webhook_outbox.py` 는 이미 `WEBHOOK_SIGNING_KEYS` 를 채운 채로 43개 시험을
통과시킨다(서비스 층, 2026-09-15 재실행 확인) — **모듈 자체엔 결함이 없다.**

## 3. 이 차선이 새로 잰 것 — API 라우트까지 (`test_u56_webhook_signing_key.py`, 2 passed)

- `override_settings(WEBHOOK_SIGNING_KEYS={})`(지금 이 환경과 같은 모양) →
  등록 **422**, 목록 `total=0` — 거절과 저장이 따로 놀지 않는다.
- `override_settings(WEBHOOK_SIGNING_KEYS={이름: 값})` → 등록 **200**, 응답의
  `signing_key_ref` 에 그 이름이 그대로 실리고, 곧바로 목록에서도 구독 1건·같은 이름
  확인(**구독 1 → 서명키 1**). 응답 어디에도 값 자체는 없다(SEC-16 이 막으려는 유출 없음).

## 4. 등록 요청

이 환경(`gx-shell`)의 `.env`/`.env.gates` 에 `WEBHOOK_SIGNING_KEYS="<이름>=<값>"`
최소 1건을 채워야 U6#4 여정이 실제로 닫힌다. 게이트 주석이 이미 이름 하나
(`p118-gate`)를 기대하고 있다(`scripts/verify_click_completes.py` API_PATHS 의
`signing_key_ref=p118-gate`) — 그 이름으로 채우면 기존 게이트 스크립트도 함께 선다.
값은 이 차선이 보지도 만지지도 않았다(§ 공통 규칙 4·5).
