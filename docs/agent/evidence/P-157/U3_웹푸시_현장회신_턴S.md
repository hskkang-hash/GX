# P-157 · 차선 U3 — 웹푸시 구독·발송 · M3 시트 · M4 골격 (턴 S)

- 작성: 2026-09-16 · 차선 **U3(현장대원 축 · 모바일)** · 턴 S
- 근거 지시: `docs/agent/RESUME_NEXT.md` §3 U3 행 · `docs/workorders/WO-GX-20260915-01.md` §5
- 선등록: `docs/agent/write_surfaces_v11.yaml` WS-02(`me/notify-prefs`) · WS-08(`push-subscriptions`)

## 1. 이번 턴에 낸 라우트 — **경로 문자열 전수**

조율자가 진입면 명부(`backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE`)에
등재할 때 **글자까지 이 표와 맞춘다.** 전부 `backend/apps/dsm/api_u3.py` 에서 태어났고,
문지기는 전건 `@tenant_scoped` + `JwtOrInboundKey()` 기본값(들어오는 키 거절)이다.

| # | method | path | 선등록 | 쓰기? |
| --- | --- | --- | --- | --- |
| 1 | `GET` | `/api/dsm/push-subscriptions/vapid-key` | WS-08 | 읽기 |
| 2 | `POST` | `/api/dsm/push-subscriptions/test-send` | **표 밖** | 쓰기(감사 1줄) |
| 3 | `POST` | `/api/dsm/push-subscriptions` | WS-08 | ★쓰기 |
| 4 | `GET` | `/api/dsm/push-subscriptions` | WS-08 | 읽기 |
| 5 | `DELETE` | `/api/dsm/push-subscriptions/{int:subscription_id}` | WS-08 | ★쓰기 |
| 6 | `GET` | `/api/dsm/me/notify-prefs` | WS-02 | 읽기 |
| 7 | `PUT` | `/api/dsm/me/notify-prefs` | WS-02 | ★쓰기 |

- **②는 선등록표 밖에서 태어난 면이다.** 조율자가 턴 S 선등록에서 바로 이 자리를
  「예상하지 못할 자리 — U3 의 웹푸시 **발송** 쪽」으로 지목했고, 그 예상이 맞았다.
  지우지 않고 적는다(표 밖 면이 조용히 태어나는 것을 막는 것이 그 표의 값이다).
  ⚠ ②는 **문만 섰고 이번 턴에 한 통도 보내지 않는다** — §3 을 보라.
- `POST /api/dsm/events/{int:event_id}/field-reply` 는 **새 문이 아니다** — `kind` 칸이
  하나 늘었을 뿐이고 경로·메서드·문지기는 그대로다. 진입면 명부는 안 바뀐다.
- 라우트 삼킴: 리터럴 둘(`vapid-key`·`test-send`)을 `{int:subscription_id}` **위**에
  세웠다. `/me/…` 는 새 접두라 `/settings/{domain}` 와 무관하다.

## 2. VAPID — 값은 저장소에 없다

| 이름 | 어디에 | 지금 상태 [실측 2026-09-16] |
| --- | --- | --- |
| `GX_VAPID_PUBLIC_KEY` | 환경변수만 | **없음** |
| `GX_VAPID_PRIVATE_KEY` | 환경변수만 | **없음** |
| `GX_VAPID_SUBJECT` | 환경변수만 | **없음** |

- 코드에는 **이름만** 있다. `notify_prefs.vapid_status()` 는 값을 한 글자도 내지 않고
  `configured` · `missing_env` · 공개키 **지문 12자**까지만 낸다(조율자 지시).
- 값이 나가는 칸은 라우트 ①의 `public_key` 하나이고, 그것은 **정의상 공개**다
  (브라우저 `applicationServerKey`). 그 값만으로는 아무것도 못 보낸다 — 발송에는
  비밀키 서명이 필요하고, 비밀키를 읽는 곳은 발송 어댑터 한 곳뿐이다.
- 게이트 `verify_no_secret_echo` **통과(exit 0)** — 대상 5건 · 새어 나온 자리 0건.

## 3. 잠금화면 도달 캡처 — **없다. 사유를 적는다**

지시서가 요구한 「훈련 채널로 보내 잠금화면 도달 캡처 1장」을 **내지 못했다.**
「못 했다」를 회색으로 적지 않고 막은 것 넷을 그대로 적는다 [전부 실측]:

1. **발송기가 이 환경에 없다.** `gx-shell` 에 `pywebpush` · `py_vapid` · `http_ece` ·
   `ecdsa` 전부 미설치(`cryptography` 와 `jwt` 만 있다). 웹푸시 본문은 RFC 8291
   암호화가 필요해 이 넷 없이는 **한 통도 못 나간다.**
2. **VAPID 키가 없다**(§2). 키는 대표·조율자가 저장소 **밖** `.env` 로 주는 값이고,
   차선이 만들 자격이 아니다.
3. **받을 기기가 없다.** 캡처는 휴대전화 잠금화면 사진이고, 이 세션에는 기기가 없다.
4. `scripts/capture_screens.py` 는 **금지**다(턴 R 에 대장 셋을 덮었다).

### 그리고 다섯째 — **커널 공개 면에 발송 문이 없다** [이번 턴에 알게 된 것]

App 이 어댑터를 부르려던 자리가 **계층 위반**이었다(§5-③). 게이트가 세 번 막았고
세 번 다 옳았다. 그래서 `POST …/test-send` 는 이번 턴에 **한 통도 보내지 않는다** —
기기마다 「왜 못 보내는가」를 사유로 돌려준다(`KERNEL_SENDER_MISSING`).

★ **그렇다고 웹푸시가 죽은 것이 아니다.** 어댑터 `WebPushChannel` 은 K2 채널
등록부에 **이름으로 서 있고**(`REGISTRY["webpush"]`), 알림 규칙이 고른 수신자의
채널이 `webpush` 면 커널의 정상 발송 경로(`_send_one` → 등록부)가 그것을 그대로 쓴다.
문이 없는 것은 **「내 기기로 지금 한 통」이라는 App 쪽 편의**뿐이다.

### 조율자에게 청하는 한 줄

`kernels/k2_notify/__init__.py` 는 이번 턴 **U56 차선이 고치는 파일**이라 손대지 않았다.
병합에서 공개 면에 이 이름 하나를 달아 주기를 청한다 — 달리면 `notify_prefs.py` 의
`send_test_push` 가 **그날 바로** 쓴다(자리는 주석으로 표시해 두었다):

```
send_webpush(*, scope, subscription: dict, title: str, body: str) -> SendOutcome
    # 구현은 이미 있다: kernels/k2_notify/channels.py::WebPushChannel.send
    # subscription = {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}  (RFC 8291)
```

### 캡처를 내려면 — 네 걸음(대표·조율자)

1. 위 공개 면 한 줄.
2. VAPID 한 쌍을 저장소 **밖** `.env` 에 §2 의 세 이름으로 넣는다.
3. `gx-shell` 이미지에 `pywebpush` 를 넣는다(컨테이너 의존성이라 차선이 못 바꾼다).
4. 휴대전화에서 `/m/settings` → 「알림 받기」 → 「시험 알림 보내기 (훈련)」 →
   **잠금화면 사진 1장**을 `docs/agent/evidence/P-157/` 아래 손으로 둔다.

## 4. 시험 결과 [실측 2026-09-16 · `DB_TEST_NAME=test_gx_u3`]

| 파일 | 수 |
| --- | --- |
| `test_u3_field_reply_kind.py` (신규) · `test_u3_push_and_prefs.py` (신규) | **37 passed** |
| 커널 공개 면 5종 + `test_write_probe_registry_covers_kernel_writes` | **118 passed** |
| 전 단위 시험(`tests` · e2e 제외) | **1,463 passed · 4 skipped** |

전 단위 시험의 빨강 8건 중 **6건이 내 계층 위반 하나**였다(§5-③ — 커널 공개 면
시험 다섯과 격리 쓰기 대장 시험이 전부 `verify_layers` 를 부른다). 고친 뒤 118 passed.
**남은 빨강은 `test_f05_event_api` 둘뿐**이고, 그것은 새 라우트가 진입면 명부에 아직
없어서다 — 등재는 조율자의 일이다(차선이 그 표를 고치면 두 차선이 한 파일을 고치게 된다).
그 시험이 「새로 생긴 것」으로 센 16건 중 **내 것은 §1 의 7건**이고, 나머지 9건
(`/api/dsm/me` · `stats/*` · `settings/notify-rules/*` · `queue/field-signals`)은
다른 차선 것이다 — 내가 등재하지도, 고치지도 않았다.

재는 것 중 값이 큰 셋:

- **자격이 응답에 안 실린다** — 구독 응답·목록을 통째로 직렬화해 엔드포인트·키
  문자열을 찾아본다. 나가는 것은 지문 12자와 기기 이름뿐이다.
- **같은 기관 동료도 내 기기를 못 보고 못 끈다** — 테넌트가 갈라 주지 않는 자리라
  함수가 가른다. 남이 끄려 하면 404(403 이면 「그 번호는 있다」가 샌다).
- **시험 발송이 `DeliveryRecord` 행을 만들지 않는다** — 만들면 F-10 지연 통계가
  경보 아닌 것을 세고 5분 억제가 **다음 진짜 경보를 삼킨다**.

## 5. 게이트 — 넷이 내 결함을 잡았고, 넷 다 기준선을 안 올리고 고쳤다

| 게이트 | 결과 |
| --- | --- |
| `verify_layers.py` | **통과(exit 0)** — 계층 위반 0건 (③) |
| `verify_dormant.py` | **통과(exit 0)** — 새로 잠든 것 0건 (①) |
| `verify_homonyms.py` | **통과(exit 0)** — 161건 = 기준선 161건 (②) |
| `ui-copy` | **통과** — 새로 생긴 대장 언어 0건 (④) |
| `verify_no_secret_echo.py` · `ui-secrets` · `forbidden-zone` | 통과 |
| `tsc --noEmit -p tsconfig.app.json` (컨테이너) | 내 파일 오류 **0건** (⑤) |

① **잠든 코드 셋** — 조율자가 `save_notify_prefs`·`send_test_push`·`vapid_status` 를
지목했는데, 확인해 보니 **이미 라우트에 이어져 있었다**(§1 ⑦·②·①). 조율자의 실행이
내 `api_u3.py` 편집보다 앞선 것이다. `--freeze` 는 쓰지 않았다.

② **동음이의 `auth` 셋** — 조율자는 「웹푸시 규격 이름일 테니 정당하면 기준선에
올려라」고 했는데 **코드를 보니 아니었다**: 걸린 셋은 전부 **내가 지은 파이썬 인자**이고,
규격 이름(`keys.auth`)은 JSON 칸 문자열로만 있어 게이트가 보지도 않는다. 그래서
기준선을 올리는 대신 인자를 `auth_secret` 으로 **고쳤다** — 161건으로 돌아왔고
`docs/agent/evidence/D-337/homonym_baseline.txt` 는 **한 글자도 안 건드렸다**.

③ **계층 위반 한 줄** — App 이 커널 비공개 모듈(`k2_notify.channels`)을 열었다.
**세 번 고쳐 세 번 다 막혔고, 그 과정이 곧 판정이다**:

| 시도 | 모양 | 게이트 |
| --- | --- | --- |
| ① | `from kernels.k2_notify import channels` | 금지① 비공개 모듈 |
| ② | `from kernels import k2_notify` | 금지② 패키지 통째 |
| ③ | `from kernels.k2_notify import send_webpush` | 금지① — 그 이름이 `__all__` 에 없어 **비공개 모듈로 읽힌다** |

③이 말하는 것은 분명하다 — **없는 공개 이름은 부를 수 없다.** 그래서 부르지 않고
없다고 말한다(§3). `verify_layers.py` 도 예외 목록도 고치지 않았다.

④ **ui-copy 빨강 1건** — `MobileSettings.tsx` 의 사용자 본문에 마크다운 강조
(`**한쪽만**`)를 썼다. React 는 그 별표를 **그대로 그린다.** 별표를 뺐다.

⑤ **타입 여덟 — 그리고 내 첫 측정이 거짓 초록이었다.** 호스트에서 `npx tsc` 를 돌려
「오류 0」을 봤는데 **본 파일 수를 안 셌다.** 조율자가 준 방법(컨테이너 `/tmp/gxf` ·
`-p tsconfig.app.json` · `--listFiles`)으로 다시 재니 **833개 파일**을 보았고, 그때
`MobileEventDetail.tsx` 의 `by_kind` 오류 여덟이 나왔다. 서버가 실제로 그 칸을 내는지
먼저 확인하고(낸다 — `api.py::field_replies` · 시험이 그 값을 단언한다) **타입에 칸을
더했다**(`FieldReplyPage`). 지금 내 파일 오류 0건.
