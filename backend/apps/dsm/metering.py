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

    그래서 청구의 모든 셈은 **`deleted` 칸이 빈 행만** 센다. 그 규칙은 이제 이
    파일이 아니라 `common/billing_marks.exclude_soft_deleted` 한 곳에 산다 —
    2026-09-21 까지 여기 `_alive()` 로도 한 벌 살아 있었고, 두 벌이던 동안
    어느 쪽이 정본인지 아무도 안 물었다.

★ **셈이 커널로 갔다** — P-206 (2026-09-20 · 차선 U56 · D-508)
--------------------------------------------------------------
[실측 2026-09-20 · 차선 U1 이 찾아 넘겼다] 이 파일의 `_events` ·
`_notifications` · `_notifications_failed` 가 `apps.get_model` 로 표를 **직접**
셌다. 커널을 안 지나니 **게이트가 심은 씨앗(P-193 `data_source=probe`)도
훈련(P-201 `data_source=drill`)도 그 셈에 들어 있었다** — 우리가 심은 가짜 사건에
고객이 돈을 내고 있었다.

    이제 그 셋은 `kernels.k1_event.count_events` ·
    `kernels.k2_notify.count_deliveries` 가 센다 — 다만 **이 파일이 커널을 직접
    부르지는 않는다**: 「K1 의 App 소비자는 하나뿐」이라 `apps/dsm/services.py` 의
    `count_billable_events` · `count_billable_deliveries` 를 지난다(아래 import 주석).
    청구에서 빼는 표식은 `common/billing_marks.py` 한 곳이 안다.

★ **왜 시험 범위가 절반인가.** 구멍이 살아 있던 진짜 이유는 코드가 아니라
  **아무도 안 보고 있었다**는 것이다 — `tests/test_dsm_app.py::AppStaysThinTest`
  는 `apps/dsm/{services,api}.py` 만 봤고 **이 파일은 안 봤다.** 이제 본다.

★ **남은 셋도 커널로 갔다 — 빚 0** (P-178 U56 ② · 2026-09-21 · 턴 Z)
-------------------------------------------------------------------
턴 Y 까지 이 파일에는 직접 세는 자리가 셋 남아 있었다(`_cameras` · `_users` ·
`_storage`, 그리고 그 셋이 함께 쓰던 `_alive`). 그때 적은 사유는 *"카메라·계정·
미디어 장부를 세는 커널 함수가 저장소에 없다"* 였고, **그것이 틀렸다** —
`kernels.k6_feedback.usage_snapshot` 이 DA-04 §2 K6 표에 **이름으로** 서 있었고
(`W4-1`), 그 자리가 `NotImplementedYet` 이었을 뿐이다. 빚 문서가 가리키던
「갚는 날: 계량 커널 면(W4-1)」이 바로 그 이름이다.

    이제 셋은 `count_billable_ledgers` 한 문을 지난다. 이 파일에 `apps.get_model` ·
    `_base_manager` · `.objects.filter(` 는 **0개**이고,
    `AppStaysThinTest.METERING_ORM_DEBT` 는 **빈 집합**이다.

★ **씨앗이 청구에서 빠졌다 — P-224** (2026-09-21 · 턴 AB · 차선 B)
------------------------------------------------------------------
턴 Z 까지 카메라·계정·미디어 표에는 표식 칸이 없어서 `exclude_unbillable` 을 걸 자리가
없었다. 그래서 **우리가 심은 카메라·계정에 고객이 돈을 내고 있었다**
[실측 2026-09-21 11:37 · ETRI-Group 카메라 15 중 11 · 계정 30 중 11].

    이제 카메라는 제 칸(`data_source`)으로, 계정·API 키는 곁표
    (`common.BillingMark`)로 갈린다. 이 파일은 **한 줄도 그 판단을 안 한다** —
    갈래를 고르는 일은 전부 `common/billing_marks.exclude_unbillable` 안에서 끝난다.

⚠ **저장(미디어)은 여전히 「못 쟀다」다.** 곁표는 섰지만 *무엇을 표시할지*의 근거가
  없다 — 미디어 행은 표식도 이름도 만든이도 씨앗을 안 가른다. **0으로 안 덮는다**
  (D-301). 그 사실은 응답의 `exclusions.not_applied` 로 화면까지 나간다.

★ **운영·감사 면은 한 줄도 안 뺀다** (D-497 · P-224 ③). 이 파일이 세는 수만 줄고,
  관제 화면·사건 목록·감사 로그는 씨앗을 **그대로 본다.** 씨앗이 화면에서 사라지면
  운영자가 실물을 못 보고, **못 보는 것은 못 고친다.** 그 불변을 `tests/
  test_b_billing_marks.py` 의 「계량 전/후 불변」 시험 셋이 붙들고 있다.

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
from pathlib import Path

from django.utils import timezone

from common.tenant_filters import get_user_group
from common.tenant_scope import TenantScope
#: ★ P-206 — **청구서의 수는 커널이 센다.** 앱은 부르고 표에 옮겨 적을 뿐이다.
#:   `tests/test_dsm_app.py::AppStaysThinTest` 가 이 파일을 본다(그 시험 범위에
#:   이 파일이 든 것이 P-206 의 절반이다 — 안 보고 있어서 구멍이 살아 있었다).
#:
#: ⚠ **커널을 직접 부르지 않는다 — `services.py` 를 지난다.** 「K1 의 App 소비자는
#:   하나뿐」이 F-05 「진입면 하나」의 집행이고(`test_f05_event_api.py::
#:   EntrySurfaceIsOneTest`), 그 하나가 `apps/dsm/services.py` 다. 1차판은 여기서
#:   `from kernels.k1_event import count_events` 를 썼고 **그 시험이 멈춰 세웠다**
#:   [실측 2026-09-20 · 턴 Y]. 옳은 지적이다: 진입면이 둘이면 다음 소비자는
#:   아무 데서나 들어온다.
from apps.dsm.services import (count_billable_deliveries,
                               count_billable_events, count_billable_ledgers)

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

#: ★ P-224 ⑤ — **「이번 달 사용량」이 제 입으로 무엇을 뺐는지 말한다.**
#:   수만 줄고 아무 말이 없으면 고객은 지난 달과 다른 수를 보고 우리를 의심한다.
#:   뺀 것을 적는 것이 「정직한 청구서」의 절반이다.
EXCLUDED_NOTE = ("우리가 심은 행(시험·검수 씨앗·훈련)은 이 수에서 뺐습니다. "
                 "훈련은 몇 건이든 0원입니다.")

#: 씨앗 거름이 **걸리는** 칸. 걸리는 것과 안 걸리는 것을 가려 적는다 —
#: 「전부 뺐다」고 뭉뚱그리면 저장 용량의 못 잰 칸이 뺀 것처럼 읽힌다.
EXCLUSIONS_APPLY_TO = ("cameras", "users", "events", "notifications")

#: 못 건 칸과 **그 이유**. 0으로 덮지 않는다 (D-301).
EXCLUSIONS_NOT_APPLIED = {
    "storage": ("미디어 장부에는 표식이 없습니다 — 씨앗 몫을 **못 쟀습니다**. "
                "0이 아니라 모르는 것입니다."),
}

#: 가격표. **값은 비어 있다** (§4-5 · P-223). 자리는 세우고 수는 안 짓는다.
#: ⚠ `metering/` 디렉터리에 `__init__.py` 를 **두지 마라** — 그 순간 정규 패키지가
#:   되어 이 모듈(`metering.py`)을 가린다. 자료만 사는 자리다
#:   (`tests/test_b_billing_marks.py` 가 그 사실을 붙든다).
PRICE_TABLE_PATH = Path(__file__).with_suffix("") / "price_table.yaml"

#: 단가가 없는 줄의 상태·문구. **0원과 다른 말이다.**
UNPRICED = "unpriced"
UNPRICED_LABEL = "단가 미확정"

#: 사용량 칸 → 가격표 키. 여기 없는 칸은 청구서 줄이 안 된다(저장 용량은 단가
#: 체계 자체가 §4-5 에 없다 — 없는 것을 있는 척 회색으로 내지 않는다).
PRICE_KEYS = {
    "cameras": "camera_month",
    "users": "seat_month",
}


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
def _cameras(scope, start, end):
    """**카메라 대수** — 그 달 끝 시점에 등록되어 있던 카메라.

    「그 달에 새로 등록한 수」가 아니다. 카메라는 달마다 새로 사는 물건이 아니고,
    청구는 **그 달에 우리가 지켜 준 대수**에 붙는다.

    ★ 턴 Z — **이제 안 센다. 커널이 센다**(`K6.usage_snapshot`). 전에는
      `apps.get_model` 으로 표를 직접 셌고, 그래서 소프트 삭제 규칙(`_alive`)이
      **앱에 한 벌 · `billing_marks` 에 한 벌** 두 벌로 살아 있었다.
    """
    return _ledgers(scope, end)["cameras"]


def _users(scope, start, end):
    """**쓰는 사람 수** — 그 테넌트의 **살아 있는 로그인 계정**.

    ★ 정의를 응답에 싣는다(`definitions`). 「그 달에 로그인한 사람」으로 세면
      `last_login` 이 **마지막 한 번만** 남는 칸이라 지난 달을 다시 세면 수가
      달라진다 — 다시 재면 달라지는 수로 청구서를 쓸 수 없다.

    ★ 턴 Z — 커널이 센다(`K6.usage_snapshot`). 한 사람을 두 번 세지 않는
      `distinct()` 도 그 안에 있다.
    """
    return _ledgers(scope, end)["users"]


def _events(scope, start, end):
    """**이벤트 수** — 그 달에 **일어난** 이벤트(`occurred_at` 기준).

    적재 시각이 아니라 발생 시각으로 센다. 늦게 들어온 이벤트가 다음 달 청구서로
    넘어가면 그 달의 수가 두 번 달라진다.

    ★ P-206 (2026-09-20) — **이 함수는 이제 안 센다. 커널이 센다.**
      전에는 `apps.get_model(…)` 으로 표를 직접 셌고, 그래서 게이트가 심은 씨앗
      (`data_source=probe`)이 **청구서에 올랐다**. 표식을 아는 자리는 커널이고,
      앱이 제 손으로 세는 한 그 구멍은 다시 난다 (D-508).
    """
    return count_billable_events(scope=scope, since=start, until=end)


def _notifications(scope, start, end):
    """**보낸 알림 수** — 실제로 **보낸 것만**(`succeeded=True` · `sent_at` 기준).

    ★ 실패한 발송은 여기 안 들어간다. 실패까지 세면 **못 보낸 알림에 돈을 받는다.**
      실패 건수는 따로 `notifications_failed` 로 낸다 — 「0」과 「안 셌다」를
      가르는 것과 같은 이유로, 실패를 안 보이게 두지도 않는다.
    """
    return count_billable_deliveries(scope=scope, since=start, until=end,
                                     time_field="sent_at", succeeded=True)


def _notifications_failed(scope, start, end):
    """실패한 발송 수. **칸이 다르다** — 실패 행의 `sent_at` 은 `None` 이라
    그 칸으로 거르면 이 수가 **언제나 0**이 된다 (models.py `DeliveryRecord`).
    """
    return count_billable_deliveries(scope=scope, since=start, until=end,
                                     time_field="occurred_at", succeeded=False)


def _storage(scope, start, end) -> dict:
    """**저장 용량** — 그 달 끝 시점에 이 테넌트가 저장소에 갖고 있던 바이트.

    ★ 턴 Z — **이제 안 센다. 커널이 센다**(`K6.usage_snapshot`). 「어디서 세는가」
      (미디어 장부 · 버킷을 안 훑는 이유)와 「못 잰 칸은 `None` 이다」는 그대로이고,
      그 설명은 이제 커널 쪽 `_billable_storage` 머리말에 산다 — **설명은 셈 옆에
      둔다.** 셈만 옮기고 설명을 여기 두면 다음 사람이 여기를 고친다.
    """
    return _ledgers(scope, end)["storage"]


def _ledgers(scope, end) -> dict:
    """장부 셋을 **한 번에** 받아 온다 (`apps/dsm/services.count_billable_ledgers`).

    ★ **한 달에 한 번만 두드린다.** 위 셋이 각자 커널을 부르면 달 하나에 세 번,
      최근 6달 표에 18번이다. 같은 시점의 잔량 셋은 **한 질문**이다.
    """
    return count_billable_ledgers(scope=scope, until=end)


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
    storage = _storage(scope, start, end)

    cells = [
        {"key": "cameras", "label": LABELS["cameras"], "unit": "대",
         "value": _cameras(scope, start, end)},
        {"key": "users", "label": LABELS["users"], "unit": "명",
         "value": _users(scope, start, end)},
        {"key": "events", "label": LABELS["events"], "unit": "건",
         "value": _events(scope, start, end)},
        {"key": "notifications", "label": LABELS["notifications"], "unit": "건",
         "value": _notifications(scope, start, end)},
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
        "notifications_failed": _notifications_failed(scope, start, end),
        "storage_files": storage["files"],
        "storage_unsized": storage["unsized"],
        "read_only": True,
        "months": recent_months(6),
        #: ★ P-224 ⑤ — **뺀 것을 적는다.** 「전부 뺐다」고 뭉뚱그리지 않는다:
        #:   걸린 칸과 못 건 칸을 **가려서** 싣는다. 저장 용량의 씨앗 몫은
        #:   0이 아니라 **모르는 것**이고, 그 둘이 한 칸에 섞이면 고객이 못 가른다.
        "exclusions": {
            "note": EXCLUDED_NOTE,
            "applies_to": list(EXCLUSIONS_APPLY_TO),
            "not_applied": dict(EXCLUSIONS_NOT_APPLIED),
            "drill_is_free": True,
        },
        #: ★ 청구서의 수는 **정의와 함께** 나가야 한다. 정의가 없으면 고객이
        #:   같은 수를 다시 셀 수 없고, 다시 못 세는 수는 다툼이 된다.
        "definitions": {
            "cameras": "그 달 끝 시점에 등록되어 있던 카메라 "
                       "(지운 카메라·우리가 심은 카메라는 빼고 센다)",
            "users": "그 테넌트의 살아 있는 로그인 계정 "
                     "(비활성·지운 계정·우리가 만든 시험 계정은 뺀다)",
            "events": "그 달에 발생한 탐지 이벤트 (occurred_at 기준 · 시험·훈련 제외)",
            "notifications": "그 달에 실제로 보낸 알림 "
                             "(실패·시험·훈련은 빼고 센다)",
            "storage": "그 달 끝 시점 보유 바이트 (미디어 장부 file_size 합계 · "
                       "씨앗 몫은 표식이 없어 못 갈랐다)",
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


# ═══════════════════════════════════════════════════════════════════════════
# 4. 가격표와 청구서 초안 — **값이 없으면 회색으로 낸다** (§4-5 · P-223 · P-224 ⑤)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 여기에 있나
# --------------
# 계량은 「얼마나 썼나」를 세고, 청구서는 「얼마인가」를 낸다. 두 질문은 다르지만
# **같은 정의 위에 서야** 한다 — 사용량 화면의 수와 청구서 초안의 수가 다른 정의로
# 세어지면 고객은 두 종이를 들고 우리에게 묻고, 우리는 답할 수 없다. 그래서 초안은
# `usage()` 가 낸 그 수를 **그대로** 쓴다(다시 세지 않는다).
#
# ★ **지어내지 않되 개발을 막지 않는다** (P-223). 단가 넷은 09-28 대표 확인 전까지
#   정본이 아니다. 그래서 가격표 파일은 **자리만 있고 값이 비어 있고**, 비면 그 줄이
#   회색(`unpriced`)으로 나간다. 회색은 0원이 아니다 — 0원은 **정했다**는 뜻이다.
def _parse_flat_yaml(text: str) -> dict:
    """`키: 값` **한 겹만** 읽는다. YAML 전체를 읽지 않는다.

    왜 라이브러리를 안 쓰나 — [실측 2026-09-21] 이 환경에 PyYAML 이 **없다.**
    청구서 한 장 때문에 의존성을 늘리면 그 순간 이 파일은 컨테이너를 다시 짓기
    전에는 못 읽히고, **못 읽히는 가격표는 없는 가격표**다.

    ★ **빈 값과 0을 가른다.** 빈 칸·`null` 은 `None`(아직 안 정했다)이고
      `0` 은 0(0원이라고 정했다)이다. 둘을 같게 읽으면 확정된 「훈련 0원」이
      「미확정」으로 나가거나, 그 반대가 된다.
    """
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        #: 줄 끝 주석. 값에 공백+우물정이 없는 것이 이 파일의 규약이다(머리말).
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if value in ("", "null", "~"):
            out[key] = None
            continue
        try:
            out[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            out[key] = float(value)
            continue
        except ValueError:
            pass
        out[key] = value.strip("'\"")
    return out


def load_price_table(path=None) -> dict:
    """가격표 한 벌. **없거나 비어도 던지지 않는다** — 회색으로 낼 수 있어야 한다.

    돌려주는 것에는 `_missing` 이 함께 온다: 값이 안 정해진 키들의 목록이다.
    화면·보고가 「무엇이 회색인가」를 **셈 없이** 읽게 하려는 것이고, 그 목록이
    비는 날이 가격표가 정본이 되는 날이다.
    """
    path = Path(path) if path else PRICE_TABLE_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:                                      # noqa: BLE001
        log.warning("가격표를 못 읽었다(%s): %s — 청구서 초안은 전부 회색이다",
                    path, exc)
        return {"_missing": sorted(set(PRICE_KEYS.values()) | {"drill_month"}),
                "_why": f"가격표 파일을 못 읽었다: {exc}"[:200]}
    table = _parse_flat_yaml(text)
    table["_missing"] = sorted(k for k, v in table.items()
                               if not k.startswith("_") and v is None)
    return table


def invoice_draft(*, scope: TenantScope, month: str = "") -> dict:
    """**청구서 초안.** 수는 `usage()` 에서, 단가는 가격표에서 온다.

    ★ **초안이다.** 이 함수는 행을 만들지 않는다(계량과 같은 규율) — 청구서를
      *발행*하는 자리가 생기는 날 그 자리가 이 초안을 받아 적는다. 세는 함수가
      발행까지 하면 우리가 만든 사실에 우리가 값을 매기게 된다.

    ★ **훈련 줄은 회색이 아니다** (P-224 ⑤). 훈련 건수는 이 셈이 세지 않는다 —
      훈련은 청구에서 빠지므로 애초에 셈을 안 지난다. 그런데도 이 줄의 **금액은
      확정**이다: 0원이 단가이니 건수가 몇이든 0원이다. *못 잰 채로도 답이 나오는
      유일한 줄*이고, 그래서 이 줄만은 회색으로 안 낸다.
    """
    used = usage(scope=scope, month=month)
    prices = load_price_table()
    by_key = {c["key"]: c for c in used["cells"]}

    lines = []
    for key, price_key in PRICE_KEYS.items():
        cell = by_key[key]
        unit = prices.get(price_key)
        qty = cell["value"]
        line = {
            "key": key,
            "label": cell["label"],
            "unit": cell["unit"],
            "quantity": qty,
            "unit_price": unit,
            "price_key": price_key,
        }
        if unit is None:
            line["state"] = UNPRICED
            line["amount"] = None
            line["why"] = (f"{UNPRICED_LABEL} — 가격표의 {price_key} 가 비어 "
                           f"있습니다 (대표 확인 전까지 정본이 아닙니다)")
        elif qty is None:
            line["state"] = "unknown"
            line["amount"] = None
            line["why"] = "사용량을 못 쟀습니다 — 0이 아니라 모르는 것입니다"
        else:
            line["state"] = "ok"
            line["amount"] = qty * unit
            line["why"] = ""
        lines.append(line)

    #: ★ **훈련 = 0원 줄.** 건수를 못 세어도 금액이 확정인 유일한 줄(머리말 ★).
    drill_unit = prices.get("drill_month")
    lines.append({
        "key": "drill",
        "label": "훈련",
        "unit": "건",
        "quantity": None,
        "unit_price": drill_unit,
        "price_key": "drill_month",
        "state": "ok" if drill_unit == 0 else UNPRICED,
        "amount": 0 if drill_unit == 0 else None,
        "why": ("훈련은 몇 건이든 0원입니다 — 건수는 이 셈이 세지 않습니다"
                if drill_unit == 0 else
                f"{UNPRICED_LABEL} — 가격표의 drill_month 가 비어 있습니다"),
    })

    priced = [ln for ln in lines if ln["state"] == "ok"]
    unpriced = [ln["key"] for ln in lines if ln["state"] != "ok"]
    return {
        "title": "청구서 초안",
        "month": used["month"],
        "tenant": used["tenant"],
        "tenant_id": used["tenant_id"],
        "currency": prices.get("currency") or "",
        "price_table_confirmed_on": prices.get("confirmed_on"),
        "lines": lines,
        #: ★ **부분합을 총액이라 부르지 않는다.** 회색 줄이 하나라도 있으면 이 수는
        #:   총액이 아니라 **잰 줄의 합**이고, 응답이 그렇게 말한다.
        "subtotal": sum(ln["amount"] for ln in priced),
        "is_total": not unpriced,
        "unpriced_lines": unpriced,
        "state": "ok" if not unpriced else UNPRICED,
        "why": ("" if not unpriced else
                f"{UNPRICED_LABEL}인 줄이 있습니다: {', '.join(unpriced)} — "
                f"가격표(§4-5)가 대표 확인 전입니다. 이 초안은 청구서가 아닙니다."),
        "exclusions": used["exclusions"],
        "read_only": True,
    }
