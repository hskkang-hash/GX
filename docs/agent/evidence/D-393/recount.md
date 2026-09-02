# ㉮ 「켜야 할 것」을 켜기 전에 **다시 셌다** — 셋은 처음부터 켜져 있었다 (D-393~D-395)

**실행 2026-09-14** · 도구 `scripts/verify_dormant.py` · `scripts/classify_dormant.py`
**모수 정정** ㉠ 314 → **311** · ㉮ 41 → **38** · 우리 관할 198 → **195** [실측]

---

## 1. 왜 다시 셌나 — 켜기 전에 판정기를 의심했다 (D-350)

D-388 이 낸 **㉮ 41건**은 「켤 순서는 세종이 정한다」로 넘어와 있었다.
켜기 전에 목록의 **맨 위 세 건**을 열어 봤다:

```
backend/config/celery.py::init_worker_process
backend/config/celery.py::close_db_connections_before_task
backend/config/celery.py::close_db_connections_after_task
```

셋 다 이렇게 서 있었다 [실측]:

```python
@worker_process_init.connect
def init_worker_process(**kwargs): ...
@task_prerun.connect
def close_db_connections_before_task(**kwargs): ...
@task_postrun.connect
def close_db_connections_after_task(**kwargs): ...
```

**켜라고 낸 것이 이미 켜져 있었다.**

---

## 2. 구멍의 정확한 자리 [실측]

`verify_dormant.ENTRY_DECORATORS` 는 **이름 집합**이다. `_dec_names` 가
`@worker_process_init.connect` 에서 내는 이름은 `{"connect", "worker_process_init"}` 이고
**둘 다 그 집합에 없다.** `@receiver` 는 이름이라 잡히고, `@sig.connect` 는 **모양**이라 안 잡혔다.

★ **gunicorn `server-hook` 오답(D-388 ③)과 같은 모양이다** — 프레임워크가 부르는 자리를
「아무도 안 부른다」로 읽는다. 그때는 **파일 이름**으로 메웠고, 이번에는 **배선 형태**로 잡는다.
파일 이름으로 메우는 방식은 `celery.py` 에서 다시 뚫렸을 것이다 — 그 파일에는
배선된 함수와 배선 안 된 함수가 **함께** 있기 때문이다.

저장소 전수 [실측]: `@<x>.connect` 로 배선된 함수는 **정확히 3건**이고, **셋 다 ㉮ 에 있었다.**

---

## 3. 고친 것

```
scripts/verify_dormant.py
  · _wired_by_signal()  신설 — 데코레이터의 **점 뒤**가 `connect`/`connect_via` 면 배선이다
    ★ ENTRY_DECORATORS 에 "connect" 를 넣지 않은 이유: 그러면 `@connect` 라는 **이름의**
      데코레이터까지 함께 모수에서 빠진다. 모수에서 빼는 일은 **좁게** 한다 (D-301)
  · 자기시험 출생 표본 ③ — 양성 1 · 음성 2 (`@sig.connect` · `@sig.connect(sender=…)`)
    ★ 같은 파일에 `signal_not_wired` 를 두어 **파일째 면제가 아님**을 시험이 본다
  · 래칫 보고를 **둘로 갈랐다** (아래 §4)

backend/tests/test_dormant_wiring.py
  · 저장소 **실물**을 표본으로 박았다 (D-310) — 합성 fixture 는 규칙이 있는지를 보고,
    이 시험은 그 규칙이 **오늘 이 저장소의 그 세 함수에** 걸리는지를 본다
```

---

## 4. ★★ 「켜졌다」와 「자고 있지 않았다」는 다른 말이다 (D-393)

래칫(D-311)은 기준선에서 빠진 것을 **「켜졌다」** 한 마디로 적고 있었다. 그러면
**판정기 정정이 진척으로 둔갑한다.** 목록에서 빠지는 길은 둘이고 둘은 전혀 다른 일이다:

```
① 켜졌다          모수에는 그대로 있는데 **운영이 이제 그것을 부른다.** 진척이다
② 자고 있지 않았다  **모수에서 빠졌다.** 판정기가 틀렸던 것이지 우리가 한 일이 없다
```

D-385 가 정한 것 — **「켰다」는 「돌았다」의 증거가 있어야 한다.** ②에는 그 증거가 없다.
게이트가 이제 둘을 따로 출력한다. 이번 실행 [실측]:

```
[DORMANT] ★ 기준선에서 빠진 3건 — **켜졌다 0건 · 자고 있지 않았다 3건**
[DORMANT]   정정: A backend/config/celery.py::close_db_connections_after_task  (**모수에서 빠졌다**)
[DORMANT]   정정: A backend/config/celery.py::close_db_connections_before_task (**모수에서 빠졌다**)
[DORMANT]   정정: A backend/config/celery.py::init_worker_process              (**모수에서 빠졌다**)
```

**이번 턴에 켠 것은 0건이다.** 그렇게 적는다.

---

## 5. ㉮ 38건 중 **둘을 열어 봤다** — 하나는 켜면 안 되는 것이었다 (D-394)

### ㉮ 가 「자산 목록」이 아님을 보인 사례 ①

```
backend/common/base_model.py::process_request   (class RequestMiddleware)
```

[실측] ① `RequestMiddleware` 는 `MIDDLEWARE` 에 **없다** (backend 전체 참조 0건)
       ② 이 미들웨어가 쓰는 `_request_local` 을 **읽는 코드가 저장소에 없다** —
          쓰기 1자리(자기 자신)뿐이다
       ③ 실제로 쓰이는 것은 `core.middleware.refresh_token.get_current_request()` 이고,
          그 미들웨어(`core.middleware.refresh_token.TokenRefreshMiddleware`)는
          `backend/config/settings.py:128` 에 **등록돼 있다**

→ **이것은 켜야 할 것이 아니라 대체된 것이다.** 켰다면 매 요청마다 스레드 로컬에
  request 를 붙잡아 두고 **읽는 이는 아무도 없다.** ㉮ 가 아니라 ㉯ 성격이다.
★ D-388 이 「㉮ 목록을 켜라」가 아니라 「켤 순서를 세종이 정한다」로 둔 것이 옳았다.

### ㉮ 가 진짜인 사례 ② — 그리고 **당직자에게 보이는 결함**이다 (D-378)

```
backend/surveillance/signals.py::video_analysis_post_save
```

[실측] **두 겹으로 꺼져 있다:**
       ① `# @receiver(post_save, sender=VideoAnalysis)` — 데코레이터가 **주석**이다
       ② `surveillance/apps.py` 의 `SurveillanceConfig` 에 `ready()` 가 없다 —
          **signals 모듈을 아무도 import 하지 않는다.** 주석을 풀어도 안 돈다

그리고 그 아래가 진짜 크기다 [실측]:
`SurveillanceDashboardService.broadcast_detection_message` 를 부르는 **운영 코드는 이 한 자리뿐**이다.
(1487줄 정의 · 1507줄은 **docstring 안의 예시**다 — 코드가 아니다)

→ **새 탐지가 저장돼도 관제 화면으로 가는 WebSocket 알림이 한 번도 발화하지 않는다.**
  당직자에게는 「새 이벤트가 안 뜬다」로 보인다 — 착시 ⑨의 교과서적 사례다.

⚠ **그러나 이번 턴에 켜지 않았다.** 사유를 적는다(D-322 · 부재 주장도 주장이다):
   `post_save` 마다 브로드캐스트를 쏘는 것은 **D-369 가 다룬 그 폭주 경로**다.
   재난 때 초당 수십 건이 들어오면 이 시그널이 그대로 채널 레이어를 때린다.
   켜려면 **큐잉·같은 (모델,pk) 접기**를 함께 얹어야 한다 — 그것은 켜기가 아니라 설계다.
   상용 절 **UX-08 「미착수」**로 등재했고, 켤지·어떻게 켤지는 세종의 판정이다.

---

## 6. ★ ㉰정상 `method` 91건의 한계를 [실측]으로 적는다 (D-395)

위 §5 ②가 드러낸 것 하나 더: `broadcast_detection_message` 는 **㉰정상**으로 분류된다.
규칙 `method` 가 「그 클래스가 자기 파일 밖에서 쓰이는가」만 보기 때문이다.
`SurveillanceDashboardService` 는 밖에서 쓰인다 — 그래서 **그 안의 죽은 메서드도 정상이 된다.**

```
㉰정상 132건 = dynamic 1 · method 91 · server-hook 9 · test-file 31
                       ↑ 이 91건은 「살아 있는 클래스 안에 있다」는 뜻이지
                         「그 메서드가 불린다」는 뜻이 아니다
```

★ 이번에는 **규칙을 고치지 않는다.** 고치면 91건이 한꺼번에 다른 칸으로 쏟아지고,
  그 이동은 이번 턴에 검증할 수 없다. **한계를 적어 두는 것**이 지금 할 수 있는 정직이다
  (D-290 3값 · D-301). 다음에 이 91건을 볼 때의 출발점이 이 문단이다.

---

## 7. 검증 [실측 2026-09-14]

```
단위          542 passed · 1 skipped · exit 0   (직전 541 + 새 시험 1)
게이트 9종     전부 exit 0
verify_dormant --self-test   양성 7갈래 · 음성 8갈래 (출생 표본 셋)
§0.4 수정      0줄
지운 코드      0줄  — ㉯ 5건은 여전히 한 건도 지우지 않았다 (D-388)
이번 턴에 켠 것 **0건** — 정정 3건이 있을 뿐이다
```
