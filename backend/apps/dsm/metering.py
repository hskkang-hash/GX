# -*- coding: utf-8 -*-
"""OPS-16 — **이번 달 사용량** (계량 · 2026-09-05 · 차선 E).

왜 이 파일이 「상용」의 뿌리인가
-------------------------------
[실측 2026-09-05] 이 저장소에는 **계량 자리가 0건**이었다. 가격표를 쓸 수는 있어도
**청구할 수는 없었다** — 청구서에 적을 수가 어디에도 없었기 때문이다. 이 파일이
그 다섯 수를 센다:

    카메라 대수 · 쓰는 사람 수 · 이벤트 수 · 보낸 알림 수 · 저장 용량

★ **수는 세는 것이지 만드는 것이 아니다**
-----------------------------------------
이 파일은 **읽기 전용**이다. 행을 만들지도 고치지도 지우지도 않는다.
계량이 이벤트를 하나라도 새로 만들면 **그 수로 청구하게 된다** — 우리가 만든 사실에
값을 매기는 것이고, 그것은 계량이 아니라 발행이다. 그래서 여기에는 `create` ·
`update` · `delete` 가 한 번도 나오지 않는다.

★ **소프트 삭제가 청구서에 올라온다** — 이 파일이 지키는 첫째
--------------------------------------------------------------
[실측 2026-09-05 · retention.py §3 머리말] dj-core 는 `objects` 를
`CustomManagerGroup(models.Manager)` 로 덮어썼다. safedelete 의 매니저가 아니다.
그래서 **소프트 삭제된 행이 평범한 조회에 그대로 보인다.** 아무 생각 없이
`StreamMonitor.objects.filter(group=...)` 를 세면 **지운 카메라가 청구서에 오른다** —
고객은 지웠다고 알고 있고, 우리는 돈을 받는다. 그것이 이 절에서 가장 나쁜 결함이다.

    그래서 이 파일의 모든 셈은 `_alive()` 를 지난다. `deleted` 칸이 있는 표는
    **반드시** 그 칸이 빈 행만 센다.

★ **테넌트 격리** — 둘째
------------------------
모든 셈은 `group` 으로 좁힌다. 좁힐 수 없는 표는 **세지 않는다**(`None` 이고
「0」이 아니다 · D-301). 남의 테넌트 수가 섞인 청구서는 틀린 청구서가 아니라
**개인정보 유출**이다 — 남의 카메라 대수는 남의 사업 규모다.

★ 못 재는 칸은 **비워 둔다** — 셋째
-----------------------------------
`None` 은 0이 아니다. 저장 용량을 못 셌으면 「0바이트 썼다」가 아니라
**「못 쟀다」**다. 0으로 적으면 그 달 청구서의 저장 용량 칸이 조용히 0원이 된다.

낱말
----
화면의 말은 `docs/design/GX-COPY_v1.md` §5 「2026-09-05 턴 E 추가」가 정본이다 —
「계량」·「미터링」은 기계의 말이라 화면에 쓰지 않는다. 이 파일은 그 낱말을
`LABELS` 로 한 벌만 갖는다(두 벌이면 화면과 CSV 가 다른 말을 한다).
"""
import csv
import io
import logging
from datetime import datetime

from django.apps import apps
from django.utils import timezone

from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope

log = logging.getLogger("guardianx.ops16.metering")

#: 화면·CSV 가 함께 쓰는 낱말. **GX-COPY §5 그대로다** — 여기서 새 말을 만들지 않는다.
TITLE = "이번 달 사용량"
LABELS = {
    "cameras": "카메라 대수",
    "users": "쓰는 사람 수",
    "events": "이벤트 수",
    "notifications": "보낸 알림 수",
    "storage": "저장 용량",
}

#: 다섯 칸의 순서. 화면과 CSV 가 같은 순서로 읽는다.
ORDER = ("cameras", "users", "events", "notifications", "storage")

#: 한 번에 낼 수 있는 달 수의 상한. 상한이 없으면 한 화면이 표 전체를 훑는다.
MAX_MONTHS = 24


# ═══════════════════════════════════════════════════════════════════════════
# 1. 달의 경계 — **한 곳에서만 정한다**
# ═══════════════════════════════════════════════════════════════════════════
def month_bounds(month: str = ""):
    """`YYYY-MM` → (시작, 끝). 끝은 **다음 달 1일 0시**(반열린 구간)다.

    반열린으로 두는 이유: 「이번 달 마지막 날 23:59:59」로 닫으면 그 1초 사이의
    이벤트가 어느 달에도 안 들어간다. 그 한 건이 다음 달 청구서에서도 안 보이면
    그것은 **셈에서 사라진 사실**이다.
    """
    now = timezone.localtime()
    if month:
        try:
            year, mon = (int(x) for x in str(month).split("-")[:2])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"달은 YYYY-MM 으로 줍니다 (받은 값: {month!r})") from exc
    else:
        year, mon = now.year, now.month
    if not (1 <= mon <= 12) or not (2000 <= year <= 2999):
        raise ValueError(f"달의 범위를 벗어났습니다: {month!r}")

    tz = timezone.get_current_timezone()
    start = datetime(year, mon, 1, tzinfo=tz)
    end = (datetime(year + 1, 1, 1, tzinfo=tz) if mon == 12
           else datetime(year, mon + 1, 1, tzinfo=tz))
    return start, end


def month_label(month: str = "") -> str:
    start, _ = month_bounds(month)
    return start.strftime("%Y-%m")


def recent_months(count: int = 6) -> list:
    """최근 N 개월의 `YYYY-MM`. **미래는 없다** — 안 지난 달은 셀 것이 없다."""
    count = max(1, min(int(count), MAX_MONTHS))
    now = timezone.localtime()
    out, year, mon = [], now.year, now.month
    for _ in range(count):
        out.append(f"{year:04d}-{mon:02d}")
        mon -= 1
        if mon == 0:
            year, mon = year - 1, 12
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 2. 세는 손 — **읽기만 한다**
# ═══════════════════════════════════════════════════════════════════════════
def _alive(model, **filters):
    """행을 세는 **유일한 문.** 소프트 삭제된 행을 뺀다.

    ★ 이 함수가 이 파일의 존재 이유의 절반이다 (머리말 첫째). `deleted` 칸이 없는
      표는 그냥 세고, 있는 표는 **반드시** 그 칸이 빈 행만 센다.
    """
    qs = model._base_manager.filter(**filters)
    names = {f.name for f in model._meta.get_fields()}
    if "deleted" in names:
        qs = qs.filter(deleted__isnull=True)
    return qs


def _cameras(group, start, end):
    """**카메라 대수** — 그 달 끝 시점에 등록되어 있던 카메라.

    「그 달에 새로 등록한 수」가 아니다. 카메라는 달마다 새로 사는 물건이 아니고,
    청구는 **그 달에 우리가 지켜 준 대수**에 붙는다.
    """
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    return _alive(Stream, group=group, created_on__lt=end).count()


def _users(group, start, end):
    """**쓰는 사람 수** — 그 테넌트의 **살아 있는 로그인 계정**.

    ★ 정의를 응답에 싣는다(`definitions`). 「그 달에 로그인한 사람」으로 세면
      `last_login` 이 **마지막 한 번만** 남는 칸이라 지난 달을 다시 세면 수가
      달라진다 — 다시 재면 달라지는 수로 청구서를 쓸 수 없다.
    """
    CoreUser = apps.get_model("user", "CoreUser")
    #: ★ `distinct()` — 소속은 **역참조를 타고** 붙는다. 한 사람에게 소속 행이 둘이면
    #:   조인이 그 사람을 두 번 낸다. 청구서에서 **한 사람을 두 번 세는 것**은
    #:   0을 1로 세는 것보다 발견이 늦다: 수가 그럴듯하기 때문이다.
    return _alive(CoreUser, userprofilelink__group=group, is_active=True,
                  date_joined__lt=end).distinct().count()


def _events(group, start, end):
    """**이벤트 수** — 그 달에 **일어난** 이벤트(`occurred_at` 기준).

    적재 시각이 아니라 발생 시각으로 센다. 늦게 들어온 이벤트가 다음 달 청구서로
    넘어가면 그 달의 수가 두 번 달라진다.
    """
    Event = apps.get_model("stream_monitors", "DetectionEvent")
    return _alive(Event, group=group, occurred_at__gte=start,
                  occurred_at__lt=end).count()


def _notifications(group, start, end):
    """**보낸 알림 수** — 실제로 **보낸 것만**(`succeeded=True` · `sent_at` 기준).

    ★ 실패한 발송은 여기 안 들어간다. 실패까지 세면 **못 보낸 알림에 돈을 받는다.**
      실패 건수는 따로 `notifications_failed` 로 낸다 — 「0」과 「안 셌다」를
      가르는 것과 같은 이유로, 실패를 안 보이게 두지도 않는다.
    """
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    return _alive(Delivery, group=group, succeeded=True, sent_at__gte=start,
                  sent_at__lt=end).count()


def _notifications_failed(group, start, end):
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    return _alive(Delivery, group=group, succeeded=False,
                  occurred_at__gte=start, occurred_at__lt=end).count()


def _storage(group, start, end) -> dict:
    """**저장 용량** — 그 달 끝 시점에 이 테넌트가 저장소에 갖고 있던 바이트.

    ★ 어디서 세나 — **객체저장소를 훑지 않는다.** `core.file_management.UserMediaFile`
      에 `file_size` 와 `group` 이 있고, MinIO 에 올릴 때 그 행이 함께 쓰인다
      [실측 stream_monitors/utils/minio_client.py:253]. 그 장부를 센다.

      버킷을 직접 훑는 길도 있지만(=`ops_monitor.py` 가 그렇게 한다) 두 가지가
      막는다: ㉠ 객체 이름 앞머리는 `group.code` 인데 **테넌트 몫만 재려면 전 객체를
      나열**해야 하고, 화면 한 장이 저장소 전체를 훑게 된다. ㉡ 이 환경의 저장소는
      `minio.invalid` 라 아예 못 닿는다. 청구서의 수가 저장소의 생사에 매달리면
      **저장소가 죽은 달은 청구를 못 한다.**

    ★ **크기를 모르는 파일은 「0바이트」가 아니다.** `file_size` 가 비어 있는 행을
      `unsized` 로 따로 센다. 그 수가 0이 아니면 이 칸은 **하한**이고, 응답이
      그렇게 말한다 — 하한을 총량처럼 청구하면 그것은 우리에게 유리한 반올림이다.
    """
    try:
        Media = apps.get_model("file_management", "UserMediaFile")
    except LookupError as exc:                                  # noqa: BLE001
        #: 장부가 없으면 **못 쟀다**이지 0바이트가 아니다 (D-301).
        return {"bytes": None, "files": None, "unsized": None,
                "why": f"미디어 장부를 찾지 못했다: {exc}"[:200]}

    from django.db.models import Count, Sum

    qs = _alive(Media, group=group, created_on__lt=end)
    agg = qs.aggregate(total=Sum("file_size"), files=Count("id"))
    unsized = qs.filter(file_size__isnull=True).count()
    return {
        "bytes": int(agg["total"] or 0),
        "files": int(agg["files"] or 0),
        "unsized": unsized,
        "why": ("크기가 안 적힌 파일이 %d개다 — 이 수는 **하한**이다" % unsized
                if unsized else ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. 표 한 벌
# ═══════════════════════════════════════════════════════════════════════════
def _tenant_of(scope: TenantScope):
    """이 요청자의 테넌트. **없으면 던진다** — 아무 테넌트나 고르지 않는다(W0-12)."""
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        raise LookupError(
            "요청자에게 소속이 없어 사용량을 셀 수 없습니다. 소속 없이 센 수는 "
            "누구의 사용량인지 답할 수 없습니다.")
    return group


def usage(*, scope: TenantScope, month: str = "") -> dict:
    """**이번 달 사용량** 한 벌. 읽기 전용이고 테넌트 안에서만 센다."""
    group = _tenant_of(scope)
    start, end = month_bounds(month)
    now = timezone.now()
    storage = _storage(group, start, end)

    cells = [
        {"key": "cameras", "label": LABELS["cameras"], "unit": "대",
         "value": _cameras(group, start, end)},
        {"key": "users", "label": LABELS["users"], "unit": "명",
         "value": _users(group, start, end)},
        {"key": "events", "label": LABELS["events"], "unit": "건",
         "value": _events(group, start, end)},
        {"key": "notifications", "label": LABELS["notifications"], "unit": "건",
         "value": _notifications(group, start, end)},
        {"key": "storage", "label": LABELS["storage"], "unit": "바이트",
         "value": storage["bytes"], "why": storage["why"]},
    ]
    for cell in cells:
        #: ★ 「못 쟀다」와 「0」을 화면이 가를 수 있게 **상태를 싣는다**(DA-03 §2-5).
        cell["state"] = "unknown" if cell["value"] is None else "ok"

    return {
        "title": TITLE,
        "measured_at": now.isoformat(timespec="seconds"),
        "month": month_label(month),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "tenant": getattr(group, "name", "") or getattr(group, "code", ""),
        "tenant_id": group.pk,
        "cells": cells,
        "notifications_failed": _notifications_failed(group, start, end),
        "storage_files": storage["files"],
        "storage_unsized": storage["unsized"],
        "read_only": True,
        "months": recent_months(6),
        #: ★ 청구서의 수는 **정의와 함께** 나가야 한다. 정의가 없으면 고객이
        #:   같은 수를 다시 셀 수 없고, 다시 못 세는 수는 다툼이 된다.
        "definitions": {
            "cameras": "그 달 끝 시점에 등록되어 있던 카메라 (지운 카메라는 빼고 센다)",
            "users": "그 테넌트의 살아 있는 로그인 계정 (비활성·지운 계정은 뺀다)",
            "events": "그 달에 발생한 탐지 이벤트 (occurred_at 기준)",
            "notifications": "그 달에 실제로 보낸 알림 (실패는 빼고 센다)",
            "storage": "그 달 끝 시점 보유 바이트 (미디어 장부 file_size 합계)",
        },
    }


def usage_series(*, scope: TenantScope, months: int = 6) -> dict:
    """최근 몇 달을 한 번에. 화면이 「지난 달과 견주기」를 할 수 있게 한다."""
    return {
        "title": TITLE,
        "rows": [usage(scope=scope, month=m)
                 for m in recent_months(months)],
    }


def usage_csv(*, scope: TenantScope, months: int = 6) -> str:
    """**표 내려받기** (GX-COPY §5). 「CSV 내보내기」라고 부르지 않는다.

    ★ 못 잰 칸은 **빈 칸으로 나간다.** 0으로 적으면 표계산기가 그것을 0으로 더하고,
      그 순간 「못 쟀다」가 「안 썼다」가 된다.
    """
    series = usage_series(scope=scope, months=months)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["달"] + [LABELS[k] for k in ORDER])
    for row in series["rows"]:
        by_key = {c["key"]: c for c in row["cells"]}
        writer.writerow(
            [row["month"]]
            + ["" if by_key[k]["value"] is None else by_key[k]["value"]
               for k in ORDER])
    return buf.getvalue()
