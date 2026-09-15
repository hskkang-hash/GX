# U6 발송 — 알림을 보내도 발송 수가 그대로다 (턴 Q · 차선 U56)

**판정** 가설 A(수신자 0명·NoRecipients) 기각 · 실제 원인은 F-04 5분 중복 억제
(`kernels/k2_notify/services.py::suppress`) — **결함이 아니라 계약**. 클라이언트 해석
(P-129)은 F 차선이 가른다 — 이 문서는 **서버가 실제로 무엇을 했는지**만 적는다.

## 1. 실측 (2026-09-15 · gx-shell · 개발 DB · 이름/개수만)

group 4(ETRI-Group) 활성 알림 규칙 **9건**, 전부 실제 구성원이 있다:

```
critical  fire_user(2명) operator(12명) fire_admin(1명) view_only_-_anyang(1명)
warning   fire_user(2명) operator(12명) fire_admin(1명)
info      fire_user(2명) operator(12명)
```

→ **가설 A(규칙 0건)는 이 테넌트에서 거짓이다.**

최근 이벤트(예: id 4798~4801, 같은 스트림·`event_type=fire`)를 조사하면 서로
`SUPPRESS_WINDOW`(5분) 안에 몰려 있고, 각 이벤트 앞에 **이미 성공한 발송**이
있다(`prior_success_in_window` 12~42건). `kernels/k2_notify/services.py::suppress()`
(469행)는

```python
Delivery._base_manager.filter(
    succeeded=True,
    event__stream_monitor_id=event.stream_monitor_id,
    event__event_type=event.event_type,
    occurred_at__lt=event.occurred_at,
    occurred_at__gte=event.occurred_at - SUPPRESS_WINDOW,
).exists()
```

를 묻는다 — **이벤트 자신의 `occurred_at` 기준**이라 같은 event_id 를 몇 번을 다시
두드려도 판정이 안 바뀐다. `send()`(500행)는 `suppress()` 가 참이면 **행을 만들지
않고 빈 튜플을 돌려준다**(524~528행) — API 는 200 · `{"total": 0, "deliveries": []}`.

## 2. 이 차선이 재현한 것 (`test_u56_notify_repeat_count.py`, 3 passed)

1. **가설 A 기각** — `resolve_recipients(scope=.., severity="critical")` 가 빈 값이
   아님을 직접 확인(설정 문 `setting_overview` 를 거치지 않는다 — 그건 다른 질문).
2. **가설 B 재현** — 같은 스트림·같은 `event_type`(`fire`) 이벤트 둘을 5분 창 안에
   만들고 순서대로 `/notify` 를 두드리면: 첫째는 200·`total>0`·`/deliveries` N+1,
   **둘째는 200·`total=0`** — `/deliveries` 가 늘지 않는다. 이것이 "발송 수가
   그대로"였던 자리의 서버 쪽 실측이다.
3. **대조** — 같은 창 안이라도 **다른 종류**(`flood`)는 억제되지 않고 N+1 로 는다 —
   억제가 "발송 자체가 죽었다"가 아니라 "같은 경보를 두 번 안 보낸다"임을 보인다.

## 3. F 차선에 넘기는 것

서버는 **200 + `total=0`** 을 정직하게 낸다 — 실패(4xx/5xx)가 아니다. 화면이 이
`total=0` 을 "눌러도 안 된다"로 읽는지, "이미 보냈습니다"류로 읽는지는 이 차선이
가르지 않는다(P-129, adapter 대조표는 F 차선 소관). 다만 게이트가 **같은 event_id**
를 반복해 두드리는 습관을 갖고 있다면(예: "판정이 안 된 것 중 첫째"를 매번 고르는
방식), 그 습관 자체가 **매번 같은 억제**를 재현하고 있을 가능성이 높다 —
새 이벤트를 고르거나 5분을 넘겨 두드리면 다른 결과가 나올 것이다.
