# SEC-16 — 웹훅 서명·재시도 규약 (HMAC · 스키마 버전 헤더 · 지수 백오프 5회)

- 차선 **S(보안·연계)** · 턴 B · 2026-09-05
- 정본: `ga_readiness.yaml` `SEC-16` (미착수 · PRD v2.5 · 손 안)
- 닫는 조건(정본 그대로): **서명 불일치 거절 · 5회 뒤 포기 기록 · 스키마 버전 헤더 부재 거절**

---

## 1. 전제 실측 — 문은 아직 없다 [실측 2026-09-05]

| 물음 | 실측 |
|---|---|
| 나가는 웹훅 | **0개.** 문은 UX-19(CAP 1.2)가 낸다 |
| 구독 모델(`Subscription`) | **0건.** 저장소 전체에 클래스가 없다 |
| 구독 등록 라우트 | **없다.** F-05 진입면 33건(`test_f05_event_api.EVENT_ENTRY_SURFACE`)에 구독 경로 0 |
| `kernels/k1_event/services.py` `subscribe()` | 이름만 · `NotImplementedYet`. 선행 셋을 스스로 적어 뒀다: ① 서명키 보관 ② **재시도·지수 백오프** ③ 구독의 테넌트 소유 |
| `X-GX-Schema` 헤더 | 코드에 **0건**. PRD v2.5 §6 한 줄에만 있었다 |
| 지수 백오프 구현 | 저장소 전체에 **0건**. 있는 것은 Celery `max_retries=3` 과 손으로 쓴 `for attempt in range(...)` 뿐 |
| 포기 행이 앉을 칸 | **이미 있다** — `DeliveryRecord.retry_count/succeeded/failure_reason/sent_at` |

**그래서 이번 턴은 문이 아니라 규약을 지었다.** 규약이 나중에 오면 규약은
「이미 보내고 있는 모양」의 다른 이름이 되고, 그것은 규약이 아니라 기록이다.

---

## 2. 지은 것

### `backend/common/webhook_contract.py` — 규약 (라우트 없음 · Django 없음)

| 이름 | 무엇 |
|---|---|
| `SCHEMA_HEADER = "X-GX-Schema"` · `SCHEMA_VERSION = "1"` | PRD v2.5 §6 이 정한 이름 그대로 |
| `sign()` / `outbound_headers()` | HMAC-SHA256. 값 모양 `sha256=<16진>` |
| `verify() -> (통과?, 사유)` | 거절 사유를 **이름으로** 돌려준다(9갈래) |
| `RetryPolicy` | 5회 · 1·2·4·8·16초 · 상한 60초 · `RETRYABLE_STATUS` |
| `giveup_record()` | **포기했다는 사실을 행으로** 만든다 (저장은 안 한다 — 문의 몫) |

**서명이 덮는 것**: `타임스탬프 + 개행 + 스키마판 + 개행 + 본문`.
본문만 덮으면 같은 요청을 **다시 보내는 것**(재생)을 못 막는다. 타임스탬프 창은 5분이다.

**함정 넷을 파일 안에 적어 뒀다** — ① 새 인증 경로 금지(라우트 0) ② 본문만 서명 금지
③ `==` 로 서명 비교 금지 ④ 무한 재시도 금지.

### `backend/tests/test_s_webhook_contract.py` — 시험 **32건 통과** [실측]

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
  python -m pytest tests/test_s_webhook_contract.py -q --nomigrations -p no:randomly
→ 32 passed
```

닫는 조건 셋을 이름으로 재는 시험:

- ① `test_a_wrong_secret_is_rejected` · `test_a_tampered_body_is_rejected` ·
  `test_no_secret_on_our_side_is_a_rejection_not_a_pass`
  (「키가 아직 없어서 통과시켰다」가 정확히 사고가 나는 자리)
- ② `test_a_dead_receiver_is_hit_exactly_five_times`(503 을 20번 줘도 **5번**) ·
  `test_giving_up_leaves_a_row` · `test_a_client_error_is_not_retried`
- ③ `test_a_missing_schema_header_is_rejected` ·
  `test_the_schema_is_judged_before_the_signature`
  (판을 서명보다 **먼저** 본다 — 서명부터 보면 「모르는 판인데 서명은 맞다」는
  통과 아닌 통과가 생긴다)
- 재생: `test_a_recorded_request_replayed_later_is_rejected` ·
  `test_moving_the_timestamp_alone_breaks_the_signature`
- 함정: `test_the_module_declares_no_routes`(P-37 · 세종 §4-4)

**양성 대조를 먼저 뒀다** — `ValidWebhookPassesTest`. 전부 거절하는 검증기는
규약이 아니라 고장이다.

### `scripts/verify_webhook_contract.py` — 판정기 (PRD v2.5 §6 이 이름을 정했다)

호스트에서 돈다. 보는 것 다섯: ① 규약 실재(상수 값·함수) ② 닫는 조건마다 시험 존재
③ 상수시간 비교 ④ 규약이 문을 내지 않았는가 ⑤ **래칫** — 규약을 안 쓰는 새 발송자 0.

```
$ python scripts/verify_webhook_contract.py
[WEBHOOK-CONTRACT] [입력] backend 파이썬 645개 읽음 · 발송자 후보 2건 (기준선 2건)
                          · 규약 검사 9항목 · 시험 등재 5건
[WEBHOOK-CONTRACT] PASS 규약 실재 · 닫는 조건 셋 전부 시험 있음 · 상수시간 비교 ·
                        새 인증 경로 0 · 규약 밖 새 발송자 0
EXIT=0
$ python scripts/verify_webhook_contract.py --self-test
[WEBHOOK-CONTRACT] 자기시험 24건 중 0건 실패
```

---

## 3. **심어 보고 잡았다** — 저장소에 실제로 심고 잰 것 셋 [실측]

| 심은 결함 | 판정기 |
|---|---|
| `hmac.compare_digest` → `given != expected` | **FAIL** ×2 (compare_digest 부재 · `==/!=` 1곳 225행) |
| `MAX_ATTEMPTS = 5` → `9` | **FAIL** 「정본은 5 — 여기서 조용히 늘리지 않는다」 |
| 새 파일 `requests.post(webhook_url, ...)` | **FAIL** 「규약을 쓰지 않는 **새** 발송자 1건」 |

셋 다 심은 뒤 되돌렸고, 되돌린 뒤 다시 PASS 다 [실측].

### ★ 이 턴에 판정기 자신이 두 번 틀렸다 — 그것이 값이다

**틀림 ①: 판정기가 자기 문서를 잡았다.**
낱말 검색이라 규약 모듈의 「`sig == expected` 를 쓰지 마라」는 **설명 한 줄**과
시험 파일의 「skip·xfail 하지 말 것」이라는 **금지 문구**가 위반으로 셌다.
금지를 적은 글이 금지 위반이 되면 다음 사람은 **설명을 지워서** 초록을 만든다.
→ `strip_noncode()` 로 주석·문자열을 지운 뒤 판정한다.

**틀림 ②: 그 고침이 진짜 발송자를 지웠다.**
토큰을 공백으로 이어 붙였더니 `requests . post` 가 되어 술어가 눈이 멀었고,
실재하는 발송자 **2건이 0건**으로 셌다. 그리고 0건은 초록으로 보였다.
→ 이름·숫자끼리만 공백으로 가른다. 자기시험 2건을 그 자리에 박았다.

**틀림 ③(가장 나쁜 것): 낱말 검색이 심은 결함을 놓쳤다.**
`compare_digest` → `!=` 로 바꿔 심었는데 판정기가 **PASS** 를 냈다 —
`compare_digest` 라는 낱말이 **독스트링에 남아 있었기** 때문이다.
규약을 설명하는 문장이 규약을 지켰다는 증거로 셌다.
→ 판정을 **AST(코드의 구조)** 로 옮겼다: `verify()` 안에 `compare_digest` 호출이
있는가 · `==`/`!=` 비교가 있는가 · 상수 값이 정본과 같은가.

> 심어 보지 않았으면 셋 다 초록이었을 것이다.

---

## 4. 함정 — 새 인증 경로를 만들지 않았다 (세종 §4-4 · P-37)

- 규약 모듈에 **라우트가 0개**다. `test_the_module_declares_no_routes` 가 소스를 읽어
  `@route.` · `@api_controller` · `@router.` · `urlpatterns` 부재를 못박고,
  판정기도 AST 로 같은 것을 본다.
- **무계정 링크를 만들지 않았다.** 서명키는 구독에 매이고, 구독은 로그인한 계정이
  등록한다(F-05). URL 하나가 계정이 되는 길을 내지 않았다.
- **익명 콜백을 만들지 않았다**(P-37). 인바운드는 기존 `JwtOrInboundKey` 규약 위다 —
  이 턴에 `INBOUND_KEY_ALLOWED` 를 **한 줄도 넓히지 않았다**.

---

## 5. **닫히지 않았다** — 무엇이 남았나

정본의 SEC-16 닫는 조건 셋은 **규약 층에서** 전부 강제된다(시험 32 · 판정기 24).
그러나 **실제로 나가는 웹훅이 0개**라 「나가는 것이 서명돼 있다」는 아직 못 잰다.

남은 것 셋, 이름으로:

1. **문** — `POST` 구독 등록 라우트 + `kernels.k1_event.subscribe()` 구현 (UX-19)
2. **서명키 보관처** — 구독의 `signing_key_ref` 가 어디를 가리키는가 (D-204 · 저장소 밖)
3. **포기 행의 실제 저장** — `DeliveryRecord`(칸은 이미 있다)에 쓰는 자리

문이 서면 판정기의 래칫(⑤)이 그 자리에서 규약 사용을 강제한다 —
규약을 안 쓰는 발송자가 태어나면 **exit 1** 이다(위 §3 에서 심어 보고 확인).

## 6. 만든 파일

- `backend/common/webhook_contract.py` (신규)
- `backend/tests/test_s_webhook_contract.py` (신규 · 32건)
- `scripts/verify_webhook_contract.py` (신규 · 자기시험 24건)
- `docs/agent/evidence/SEC-16/webhook_senders_baseline.txt` (신규 · 래칫 기준선 2건, 사유 기재)
