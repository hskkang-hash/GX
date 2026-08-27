# -*- coding: utf-8 -*-
"""K1 이벤트 커널 — 공개 면 (DA-04 §2 K1).

이벤트를 **만들고·모으고·찾고·판정하는** 한 벌. 이 App 의 심장이다.

이중 AC (DA-04 §1-2) — 충돌 시 **계약 AC 우선**
------------------------------------------------
    [F-04 계약] 동일 이벤트 5분 내 중복 **알림** 0건
    [F-05 계약] OpenAPI 제공 · p95 500ms
    [U1 상품]  증거 확보 클릭 수 ≤ 3 · 오탐률 수치화

★ 이 셋은 한 지점에서 충돌하고, DA-04 가 해법을 이미 적었다:

    중복 억제는 **기록 단계**(10초·이벤트)와 **알림 단계**(5분·K2)를 나눈다.
    **이벤트를 접으면 U1 의 오탐률 분모가 거짓이 되므로 이벤트는 남기고 알림만 접는다.**

그래서 `record_detection` 은 `created`(10초 창)와 `should_notify`(5분 창)를 **따로** 낸다.
둘을 하나로 합치고 싶어지는 순간이 곧 한쪽 AC 를 깨뜨리는 순간이다.

저장은 어디에 — 커널이 모델을 새로 만들지 않는다
-------------------------------------------------
`DetectionEvent` 는 이미 `stream_monitors` 앱에 있고(W2-1),
그 스키마는 `docs/contracts/detection-event.md` v1.0 으로 **고정**돼 있다(2026-08-13).
커널이 모델을 옮기면 마이그레이션이 생기고, 계약 고정의 뜻이 사라진다.
**커널이 가져가는 것은 로직이지 표가 아니다.**

테넌트 스코프 — C-3.1 을 커널에서 어떻게 지키나
-----------------------------------------------
C-3.1 은 "커널 공개 함수는 `@tenant_scoped()` 를 거치거나 PUBLIC 등재"라고 적었다.
**여기서는 데코레이터를 쓰지 않는다.** 이유가 있다:

    `tenant_scoped` 는 인자에서 `request` 를 찾고, 못 찾으면 **그냥 통과시킨다**
    (`common/tenant_scope._find_request` → `None` → 검사 생략).
    커널 서비스 함수에는 `request` 가 없다. 붙이면 **표식만 남고 아무것도 안 막는다** —
    데코레이터 466/466 부착을 완결로 착각했던 착시 ①(D-249)과 똑같은 모양이다.

대신 DA-04 가 정한 방식을 쓴다 — *"테넌트 스코프 강제 — 인자로 group 을 명시로 받는다."*
공개 면은 `actor` 를 **필수 인자**로 받고, 좁히기는 `common.tenant_filters` 의
**실제 문지기**(`get_scoped_or_404` · `assert_scoped` · `filter_by_group_field`)가 한다.
이 판정은 `common/tenant_tripwire.py` 가 라우트에 대해 쓰는 것과 **같은 문지기 목록**이다.

⚠ 이것은 C-3.1 문언과 다른 이행 방식이다. 임의로 정하지 않고
  `decisions_pending.yaml` 의 **P-K1-1** 로 적재했다 (D-213 — STOP 대신 적재하고 전진).
  판정이 나오면 그때 이 주석과 게이트를 함께 고친다.

`objects` 가 아니라 `_base_manager` 로 묻는 이유
-----------------------------------------------
`DetectionEvent.objects` 는 dj-core 의 테넌트 필터를 타고, 그 필터에는
`created_by__isnull=True` OR 절이 들어 있다(§0.4 — 고칠 수 없다).
문지기가 그 필터를 통해 물으면 **"내 것이 아닌데 통과"와 "없어서 통과"를 구별하지 못한다.**
소유 판정은 필터를 거치지 않은 사실 위에서 해야 한다 (W0-14c `assert_scoped` 와 같은 이유).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.tenant_filters import assert_scoped, filter_by_group_field, get_scoped_or_404
from kernels.k1_event.exceptions import InvalidEventInput, NotImplementedYet
from kernels.k1_event.schemas import EventView, RecordResult

#: **기록** 중복 억제 창. 같은 stream+type 이 이 안에 재발하면 `last_seen_at` 만 갱신한다.
#: DA-04 가 못박은 10초. 이 값을 늘리면 U1 의 오탐률 분모가 그만큼 줄어든다.
DEDUP_WINDOW = timedelta(seconds=10)

#: **알림** 중복 억제 창. F-04 의 "5분 내 중복 알림 0건"이 이것이다.
#: 이벤트를 접는 창이 **아니다** — 두 창을 같은 값으로 두지 말 것.
NOTIFY_WINDOW = timedelta(minutes=5)


def _model(name: str):
    return apps.get_model("stream_monitors", name)


def _owner_field(model) -> str:
    """이 모델이 테넌트에 닿는 필드 이름 — `groups`(M2M) 인가 `group`(FK) 인가.

    ★ 하드코딩하지 않는다. 저장소 소스의 `BaseModelWithGroup` 은 `groups` M2M 을 선언하지만
      **실행 중인 dj-core 는 `group` FK** 를 준다(실측). 어느 쪽이 정본인지는 P-LOCAL-4 가
      미결이고, 그 답이 나기 전에 한쪽을 코드에 박으면 다른 환경에서 조용히 깨진다.
      `common.tenant_filters._guess_group_lookup` 이 같은 판단을 이미 한다 —
      그래서 아래 문지기 호출들은 `group_lookup` 을 **넘기지 않는다.** 판단은 한 곳에서만 한다.
    """
    names = {f.name for f in model._meta.get_fields()}
    if "groups" in names:
        return "groups"
    if "group" in names:
        return "group"
    raise InvalidEventInput(
        f"{model.__name__} 에 테넌트 필드(groups/group)가 없다 — 소유를 정할 수 없다. "
        f"소유가 빈 행은 §0.4 의 created_by__isnull OR 절을 타고 모두에게 보인다"
    )


def _inherit_owner(event, stream) -> None:
    """이벤트의 소유를 **스트림에서 물려받는다.**

    이 두 줄이 빠지면 이벤트가 주인 없는 행이 되고, §0.4 의 OR 절을 타고 모든 테넌트에게
    보인다. W0-13 백필 25,296행이 되돌린 것이 정확히 그 상태다 — 다시 만들지 않는다.
    """
    field = _owner_field(type(event))
    if field == "groups":
        event.groups.set(stream.groups.all())
    else:
        setattr(event, "group", getattr(stream, "group", None))
        event.save(update_fields=["group"])


def _to_view(row) -> EventView:
    return EventView(
        event_id=row.pk,
        event_type=row.event_type,
        severity=row.severity,
        status=row.status,
        occurred_at=row.occurred_at,
        last_seen_at=row.last_seen_at,
        stream_monitor_id=row.stream_monitor_id,
        stream_monitor_name=row.stream_monitor.name if row.stream_monitor_id else "",
        confidence=row.confidence,
        bbox=row.bbox,
        snapshot_path=row.snapshot_path,
        clip_path=row.clip_path,
        lat=row.lat,
        lng=row.lng,
        reviewed_by_id=row.reviewed_by_id,
        reviewed_at=row.reviewed_at,
        reject_reason=row.reject_reason,
    )


def _validate(event_type: str, severity: str) -> None:
    Event = _model("DetectionEvent")
    if event_type not in Event.EventType.values:
        raise InvalidEventInput(
            f"event_type={event_type!r} 은 계약에 없다. "
            f"허용: {', '.join(Event.EventType.values)}. "
            f"열거값을 늘리려면 docs/contracts/detection-event.md 와 W2-3 색 규칙을 "
            f"**같은 커밋에서** 함께 고쳐라 (DA-01 OPEN-05)"
        )
    if severity not in Event.Severity.values:
        raise InvalidEventInput(
            f"severity={severity!r} 은 계약에 없다. 허용: {', '.join(Event.Severity.values)}. "
            f"ISA-101 — 빨강(critical)은 이 등급 전용이므로 새 등급을 만들지 않는다"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 1. record_detection — 만든다
# ═══════════════════════════════════════════════════════════════════════════
@transaction.atomic
def record_detection(
    *,
    stream_monitor_id: int,
    event_type: str,
    severity: str,
    occurred_at: datetime | None = None,
    snapshot_path: str = "",
    confidence: float | None = None,
    bbox: dict[str, Any] | None = None,
    track_id: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    alt: float | None = None,
    ai_model_id: int | None = None,
    mission_id: int | None = None,
) -> RecordResult:
    """검출 하나를 이벤트로 기록한다. **중복 억제 내장** (DA-04 K1).

    `actor` 를 받지 않는다 — 이 함수를 부르는 것은 **사람이 아니라 파이프라인**이다.
    테넌트는 요청자가 아니라 **스트림이 정한다**: 이벤트는 그 스트림을 가진 테넌트의 것이다.
    요청자에게서 group 을 받으면 파이프라인에 요청자가 없으므로 소유가 비게 되고,
    소유가 빈 행은 §0.4 의 `created_by__isnull` OR 절을 타고 **모두에게 보인다.**
    W0-13 백필 25,296행이 그 상태를 되돌린 일이었다 — 다시 만들지 않는다.
    """
    _validate(event_type, severity)
    Event = _model("DetectionEvent")
    Stream = _model("StreamMonitor")

    occurred_at = occurred_at or timezone.now()
    # 스트림은 `_base_manager` 로 찾는다 — 파이프라인에는 요청자가 없어 테넌트 필터가
    # 무엇을 기준으로 걸러야 할지 모른다. 소유는 아래에서 스트림의 group 으로 정한다.
    try:
        stream = Stream._base_manager.get(pk=stream_monitor_id)
    except Stream.DoesNotExist as exc:
        raise InvalidEventInput(f"stream_monitor_id={stream_monitor_id} 가 없다") from exc

    same = (
        Event._base_manager
        .filter(stream_monitor_id=stream_monitor_id, event_type=event_type,
                occurred_at__lte=occurred_at)
        .order_by("-occurred_at")
        .first()
    )

    # ── 기록 창(10초): 접을지 결정한다 ────────────────────────────────────
    folded = False
    if same is not None:
        last = same.last_seen_at or same.occurred_at
        if occurred_at - last <= DEDUP_WINDOW:
            same.last_seen_at = occurred_at
            # confidence 는 **더 높은 쪽**을 남긴다 — 접힌 관측 중 가장 확실한 것이
            # 증거로서 값이 있다. 마지막 값으로 덮으면 확신이 낮아질 수 있다.
            if confidence is not None and (same.confidence or 0) < confidence:
                same.confidence = confidence
            same.save(update_fields=["last_seen_at", "confidence"])
            folded = True
            event = same

    if not folded:
        event = Event._base_manager.create(
            stream_monitor_id=stream_monitor_id,
            ai_model_id=ai_model_id,
            event_type=event_type,
            severity=severity,
            occurred_at=occurred_at,
            confidence=confidence,
            bbox=bbox,
            track_id=track_id,
            lat=lat, lng=lng, alt=alt,
            snapshot_path=snapshot_path,
            mission_id=mission_id,
        )
        _inherit_owner(event, stream)

    # ── 알림 창(5분): 접는 것과 **무관하게** 따로 판정한다 ────────────────
    #   이 이벤트 자신은 세지 않는다. "5분 안에 이미 다른 이벤트가 있었는가"만 본다.
    prior_exists = (
        Event._base_manager
        .filter(stream_monitor_id=stream_monitor_id, event_type=event_type,
                occurred_at__lt=occurred_at,
                occurred_at__gte=occurred_at - NOTIFY_WINDOW)
        .exclude(pk=event.pk)
        .exists()
    )
    return RecordResult(
        event_id=event.pk,
        created=not folded,
        should_notify=not prior_exists,
        folded_into_existing=folded,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. query_events — 모은다 · 찾는다
# ═══════════════════════════════════════════════════════════════════════════
def query_events(
    *,
    actor,
    since: datetime | None = None,
    until: datetime | None = None,
    event_type: str | Iterable[str] | None = None,
    severity: str | Iterable[str] | None = None,
    status: str | Iterable[str] | None = None,
    stream_monitor_id: int | None = None,
    mission_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[EventView]:
    """이벤트를 찾는다. **테넌트 스코프 강제** · **필터는 전부 서버에서.**

    DA-04: *"3클릭이 되려면 조회 API 가 필터를 서버에서 처리해야 한다
    (클라이언트 필터는 클릭을 늘린다)."* — U1 의 3클릭이 이 함수 하나에 달려 있다.

    `select_related("stream_monitor")` 는 장식이 아니다. 없으면 `stream_monitor_name`
    한 줄이 행마다 쿼리를 낳고(N+1), 그것이 F-05 의 p95 500ms 를 깨는 가장 흔한 원인이다.
    """
    Event = _model("DetectionEvent")

    # ★ `_base_manager` 로 시작한다 — `objects` 는 §0.4 의 `created_by__isnull` OR 절을
    #   타서 주인 없는 행을 통과시킨다. 소유 판정은 필터를 거치지 않은 사실 위에서 한다.
    qs = Event._base_manager.select_related("stream_monitor")
    # 실제 좁히기. 문지기는 `common.tenant_filters` 가 한다 — 여기서 직접 group 을
    # 캐내지 않는다. 전역 여부는 `tenant_roles` 만 답한다 (D-212).
    qs = filter_by_group_field(qs, actor, field=_owner_field(Event))

    def _in(field: str, value):
        nonlocal qs
        if value is None:
            return
        if isinstance(value, str):
            qs = qs.filter(**{field: value})
        else:
            qs = qs.filter(**{f"{field}__in": list(value)})

    _in("event_type", event_type)
    _in("severity", severity)
    _in("status", status)
    if since is not None:
        qs = qs.filter(occurred_at__gte=since)
    if until is not None:
        qs = qs.filter(occurred_at__lte=until)
    if stream_monitor_id is not None:
        qs = qs.filter(stream_monitor_id=stream_monitor_id)
    if mission_id is not None:
        qs = qs.filter(mission_id=mission_id)

    # 소유가 M2M(`groups`)일 때 조인이 같은 행을 여러 번 낸다. distinct 없이 페이징하면
    # 페이지가 겹치고, 겹친 페이지는 화면에서 "같은 이벤트가 두 번" 으로 보인다.
    # FK 일 때는 불필요하지만 해롭지 않다 — 어느 쪽이 정본인지 미결이므로(P-LOCAL-4) 둔다.
    qs = qs.distinct().order_by("-occurred_at")
    return [_to_view(row) for row in qs[offset:offset + limit]]


# ═══════════════════════════════════════════════════════════════════════════
# 3. get_event — 남의 것이면 404
# ═══════════════════════════════════════════════════════════════════════════
def get_event(event_id: int, *, actor) -> EventView:
    """단건 조회. 남의 테넌트 것이면 **404** — `200 + 빈 응답` 을 만들지 않는다 (W0-18).

    403 이 아닌 이유: 403 은 "그 id 는 존재하지만 네 것이 아니다"를 알려 준다.
    **존재 여부가 새는 것도 누출이다.** 남의 것은 없는 것과 같아야 한다.
    """
    Event = _model("DetectionEvent")
    row = get_scoped_or_404(Event, event_id, actor)
    # `get_scoped_or_404` 는 `objects` 로 묻는다(§0.4 OR 절 포함). 소유가 빈 행이
    # 통과하는 것을 막기 위해 문지기를 한 번 더 세운다 — 우연에 기대지 않는다 (D-274).
    assert_scoped(Event, event_id, actor)
    if not row.stream_monitor_id:
        return _to_view(row)
    return _to_view(Event._base_manager.select_related("stream_monitor").get(pk=row.pk))


# ═══════════════════════════════════════════════════════════════════════════
# 4. review_event — 판정한다 (K6 오탐 통계의 입력)
# ═══════════════════════════════════════════════════════════════════════════
@transaction.atomic
def review_event(event_id: int, *, verdict: str, reason: str = "", actor) -> EventView:
    """`confirmed` / `rejected` 로 판정한다.

    ★ **기각은 삭제가 아니다.** 행을 지우면 U1 의 오탐률 분자가 함께 사라지고,
      "오탐률 수치화"라는 상품 AC 가 셀 수 있는 것을 잃는다. 상태만 바꾼다.
    """
    Event = _model("DetectionEvent")
    if verdict not in (Event.Status.CONFIRMED, Event.Status.REJECTED):
        raise InvalidEventInput(
            f"verdict={verdict!r} 은 판정값이 아니다. "
            f"허용: {Event.Status.CONFIRMED} · {Event.Status.REJECTED}. "
            f"종료는 close_event 가 한다"
        )
    # 쓰기 경로의 문지기는 **try 밖 첫 줄**에 둔다 (W0-14c) — 안에 두면 예외에 가려
    # "막힌 것"과 "찾고 나서 죽은 것"이 구별되지 않는다.
    assert_scoped(Event, event_id, actor)

    row = Event._base_manager.select_related("stream_monitor").get(pk=event_id)
    row.status = verdict
    row.reviewed_by = actor
    row.reviewed_at = timezone.now()
    row.reject_reason = reason or None
    row.save(update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason"])
    return _to_view(row)


# ═══════════════════════════════════════════════════════════════════════════
# 5. close_event — F-11 보고서 트리거 지점
# ═══════════════════════════════════════════════════════════════════════════
@transaction.atomic
def close_event(event_id: int, *, actor) -> EventView:
    """종료 처리. K4(보고서 엔진)가 여기를 트리거로 삼는다 (DA-04 K1 표)."""
    Event = _model("DetectionEvent")
    assert_scoped(Event, event_id, actor)

    row = Event._base_manager.select_related("stream_monitor").get(pk=event_id)
    row.status = Event.Status.CLOSED
    row.save(update_fields=["status"])
    return _to_view(row)


# ═══════════════════════════════════════════════════════════════════════════
# 6. subscribe — F-05 Webhook · **아직 없다**
# ═══════════════════════════════════════════════════════════════════════════
def subscribe(*, webhook_url: str, filters: dict | None = None, signing_key_ref: str = ""):
    """이벤트 Webhook 구독 (F-05).

    ★ **구현하지 않았다.** 이름만 세워 두는 이유는 DA-04 §2 K1 표가 정한 공개 면이
      6개이고, 그중 하나가 빠져 있다는 사실을 **표와 코드 양쪽에서 보이게** 하기 위해서다.
      `verify_kernel_map.py` 가 티켓 매핑에 대해 하는 일과 같은 계열이다.

    조용히 `None` 을 돌려주지 않는다. `detect_and_save` 가 정확히 그 모양이었다 —
    독스트링은 "저장한다"고 적혀 있고 본문은 비어 있어서, 부르는 쪽은 저장된 줄 알았다.
    **없는 것은 없다고 말한다.**

    선행 판정 필요:
      · 서명키를 어디에 두는가 (D-204 — 저장소 밖).
      · 재시도·지수 백오프 정책. 외부 호출이므로 타임아웃 필수 (W0-17 · C-3.3).
      · 구독 자체가 테넌트 자원이다 — 남의 테넌트 이벤트를 구독하지 못하게 막는 자리.
    """
    raise NotImplementedYet(
        "K1.subscribe(F-05 Webhook)은 아직 구현되지 않았다. "
        "서명키 보관·재시도 정책·구독의 테넌트 소유 판정이 선행이다 — "
        "W2-2 이후 별 티켓으로 연다. 지금은 이름만 서 있다"
    )
