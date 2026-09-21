# -*- coding: utf-8 -*-
"""UX-46 온보딩 진행률 — **카드의 완료는 서버 기록이 닫는다** (WO-01 §12 · PRD §7.1·§7.2).

이 파일이 하는 일과 안 하는 일
------------------------------
    한다   역할별 카드 표(PRD §7.2)를 한 곳에 둔다 · 카드마다 **어느 서버 기록이 닫는가**를
           술어로 적는다 · 그 술어가 참이면 `DsmOnboardingProgress` 행을 남긴다(근거 포함) ·
           행을 세어 진행률을 낸다
    안 한다 사람이 누르는 「완료」 문을 열지 않는다 · 목록·집계를 새로 짜지 않는다
           (전부 `apps/dsm/services.py` 와 커널의 공개 면을 그대로 부른다) ·
           **분모를 손으로 적지 않는다** — 분모는 이 파일의 표를 센 수다

왜 「사람이 체크」가 없나
------------------------
체크는 **행위의 증거가 아니라 주장**이다. 주장으로 닫힌 카드는 「했다」와 「했다고 적었다」를
구별하지 못하고, 그 둘이 같아지는 순간 진행률 100 은 아무것도 증명하지 않는다.
그래서 모델이 `source_ref`(닫은 기록의 이름) 없이는 행을 못 만들게 되어 있고
(`DsmOnboardingProgress` CHECK), 이 파일은 그 근거를 **실제 기록에서** 찾아 적는다.

왜 읽는 자리에서 행을 만드나 — **되짚을 수 있는 쪽**
----------------------------------------------------
진행률을 묻는 요청이 오면 ① 서버 기록을 보고 ② 닫힌 것을 행으로 남긴 뒤 ③ 행을 센다.
①만 하고 행을 안 남기면 「언제 닫혔나」가 영영 없다(카드는 오늘의 사실로만 산다).
②는 **멱등**이다 — 같은 카드에 살아 있는 행은 하나뿐이고(UniqueConstraint),
사용자 입력을 한 글자도 받지 않는다. 그래서 이 쓰기는 자원을 늘리지 않는다.

★ **못 재는 카드를 표에서 지우지 않는다.** 서버 기록이 없는 카드(「격자를 열어 봤다」처럼
  읽기만 하는 행위)는 `BLOCKED` 에 **이름과 사유와 함께** 남는다. 지우면 분모가 조용히
  줄어 진행률이 올라가고, 그 수는 거짓이다 (D-301 · 「빨강을 회색으로 바꾸지 않는다」).
"""
# ★ `from __future__ import annotations` 를 쓰지 않는다 — 이 모듈을 부르는 라우트가
#   `@tenant_scoped` 로 감싸여 있고, 그 데코레이터의 `__globals__` 에서 주석이 풀린다
#   (`api.py` D-378 머리말과 같은 자리).
from datetime import datetime
from typing import Any, Callable, NamedTuple, Optional

from django.apps import apps
from django.utils import timezone

from common.tenant_filters import filter_by_group_field, get_user_group
from common.tenant_scope import TenantScope

#: 이 표가 만드는 행의 목적 코드. 이 파일에서만 쓴다 (`field.py::dsm.field_photo` 와 같은 규약).
PURPOSE_CODE = "dsm.onboarding"

#: 진행률이 닫혔다고 보는 수. 100 이 아니면 그 고객은 온보딩 중이다 (PRD §7.4).
COMPLETE_PERCENT = 100


class Card(NamedTuple):
    """카드 한 장. `closes` 가 **없으면 못 재는 카드**다 — 지우지 않고 사유와 함께 남긴다."""

    key: str
    title: str
    #: 화면에서 이 카드가 여는 자리. 없으면 여는 자리가 아직 없다는 뜻이다.
    link: str
    #: 이 카드를 닫는 서버 기록을 찾는 술어. `(scope) -> source_ref | None`.
    closes: Optional[Callable[[TenantScope], Optional[str]]] = None
    #: 술어가 없는 이유. 못 재는 카드에만 적는다.
    why: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# 값 꺼내기 — 서비스가 dict 를 주든 객체를 주든 **모양을 가정하지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
def _field(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _model(label: str):
    return apps.get_model("stream_monitors", label)


def _tenant_rows(model, actor):
    """이 테넌트의 살아 있는 행. **`_base_manager` 로 시작한다.**

    `objects` 는 dj-core 의 스레드 지역 요청을 보고 좁히고, HTTP 를 한 번 때린 뒤에는
    그 자리가 비어 **「없다」가 「못 봤다」와 같아진다** (D-253 · 시험 오염의 그 자리).
    좁히기는 `filter_by_group_field` 한 곳이 한다.
    """
    qs = model._base_manager.filter(deleted__isnull=True)
    return filter_by_group_field(qs, actor)


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — **기존 공개 면만 부른다.** 새 질의를 짜지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def _closed_by_my_review(scope: TenantScope) -> Optional[str]:
    """내가 판정한 사건이 있는가 (PRD §7.2 U1 ②의 `review 1`)."""
    from apps.dsm import services

    actor = scope.require_actor()
    rows = services.recent_events(scope=scope, reviewed_by_id=actor.pk, limit=1)
    return f"event#{rows[0].event_id}" if rows else None


def _closed_by_response(scope: TenantScope) -> Optional[str]:
    """접수 이후로 넘어간 사건이 있는가 (U1 ③의 `response 1`).

    ★ 「누가 접수했나」로 좁히지 않는다 — 대응 전이의 행위자는 행이 아니라 감사에 있다
      (D-399 가 판정 축과 대응 축을 가른 그 이유). 그래서 이 카드의 근거는 **사건**이다.
    """
    from apps.dsm import services

    rows = services.recent_events(
        scope=scope, response_state=["acknowledged", "in_progress", "closed"], limit=1)
    return f"event#{rows[0].event_id}" if rows else None


def _closed_by_handover(scope: TenantScope) -> Optional[str]:
    """인계 메모가 한 건이라도 있는가 (U1 ⑤의 `handover 1`)."""
    actor = scope.require_actor()
    row = _tenant_rows(_model("DsmHandover"), actor).order_by("-id").first()
    return f"handover#{row.pk}" if row else None


def _closed_by_report_run(scope: TenantScope) -> Optional[str]:
    """보고서가 한 번이라도 나왔는가 (U2 ⑥ · U4 ④의 `report 1`)."""
    actor = scope.require_actor()
    row = _tenant_rows(_model("DsmReportRun"), actor).order_by("-id").first()
    return f"report_run#{row.pk}" if row else None


def _closed_by_drill(scope: TenantScope) -> Optional[str]:
    """훈련 모드를 켜거나 끈 기록이 있는가 (U2 ⑦ · U5 ⑦의 `drill 1`)."""
    from apps.dsm import services

    state = services.drill_state(scope=scope)
    last = str(_field(state, "last_action", "") or "").strip()
    return f"drill:{last}" if last else None


def _closed_by_people(scope: TenantScope) -> Optional[str]:
    """우리 조직에 사람이 여섯 이상인가 (U5 ①의 `users >= 6`)."""
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return None
    CoreUser = apps.get_model("user", "CoreUser")
    link_field = CoreUser._meta.get_field("userprofilelink")
    link_model = link_field.related_model
    owner = link_field.remote_field.name
    count = link_model._base_manager.filter(group=group).values(owner).distinct().count()
    return f"people:{count}" if count >= PEOPLE_MINIMUM else None


#: PRD §7.2 U5 ①이 적은 수. 표에 적힌 수이지 이 파일이 정한 수가 아니다.
PEOPLE_MINIMUM = 6


def _closed_by_address_gap(scope: TenantScope) -> Optional[str]:
    """카메라 설치 주소가 **한 대도 안 빈** 상태인가 (U5 ②의 `address-gap 0`)."""
    from apps.dsm import services

    gap = services.camera_address_gap(scope=scope)
    total = _field(gap, "total", 0) or 0
    missing = _field(gap, "without_address", None)
    if missing is None or total <= 0:
        # 카메라가 0대면 「전부 주소가 있다」가 아니라 **잴 수 없다**이다 (D-301).
        return None
    return f"address_gap:0/{total}" if int(missing) == 0 else None


def _closed_by_critical_recipients(scope: TenantScope) -> Optional[str]:
    """심각 등급을 받는 사람이 하나라도 있는가 (U5 ③의 `rule >= 1`)."""
    from kernels.k2_notify import resolve_recipients
    from kernels.k2_notify.exceptions import InvalidNotifyInput

    try:
        people = resolve_recipients(scope=scope, severity="critical")
    except InvalidNotifyInput:
        return None
    if not people:
        return None
    rule_id = getattr(people[0], "rule_id", None)
    return f"notify_rule#{rule_id}" if rule_id else f"notify_recipients:{len(people)}"


def _closed_by_retention(scope: TenantScope) -> Optional[str]:
    """영상 보관 기간을 **선언했는가** (U5 ⑤의 `retention 선언`)."""
    from apps.dsm import retention

    actor = scope.require_actor()
    group = get_user_group(actor)
    days = retention.declared_retention_days(getattr(group, "pk", None))
    return f"retention:{int(days)}d" if days is not None else None


def _closed_by_threshold_change(scope: TenantScope) -> Optional[str]:
    """**내가** 임계값을 한 번이라도 바꿨는가 (U2 ⑤의 `thresholds 시험 1` · 턴 U).

    근거는 K5 표 ① 의 변경 이력 `ThresholdChange`(무엇에서 무엇으로 · 누가 · 왜)다.
    ★ 테넌트가 아니라 **행위자**로 좁힌다 — 전역 층(`group=null`)의 변경은 테넌트 칸이
      비어 있어 `_tenant_rows` 로는 못 보고, 이 카드가 묻는 것은 「이 사람이 시험해 봤나」다.
      남의 테넌트 사람의 변경은 `changed_by` 가 다르므로 내 카드를 닫지 못한다.
    """
    actor = scope.require_actor()
    row = (_model("ThresholdChange")._base_manager
           .filter(deleted__isnull=True, changed_by=actor).order_by("-id").first())
    return f"threshold_change#{row.pk}" if row else None


#: 시험 발송을 남기는 감사 채널 둘과 그 행위 이름. **값의 정본은 각 모듈이다** —
#: 여기서는 이름만 모은다(두 벌이 되지 않게 모듈 상수를 그대로 읽는다).
def _test_send_audit_channels():
    from apps.dsm import notify_prefs

    return (
        # (logger_name, api_name 앞머리) — `kernels/k2_notify/rule_admin.py::test_send`
        ("guardianx.dsm.notify", "dsm.notify.test_send"),
        # `apps/dsm/notify_prefs.py::test_send`(웹푸시 · api_name = 행위 이름 그대로)
        (notify_prefs.LOGGER_NAME, notify_prefs.ACTION_TEST_SEND),
    )


def _closed_by_test_send(scope: TenantScope) -> Optional[str]:
    """**내가** 알림 채널 시험 발송을 한 번이라도 눌렀는가 (U5 ④의 `채널 시험 발송` · 턴 U).

    근거는 감사 표(`logger.AuditLogs`)의 시험 발송 행이다 — 이메일 훈련 채널(K2 `test_send`)
    이든 웹푸시(`notify_prefs.test_send`)든 **둘 다 감사에 남고**, 둘 중 하나면 닫는다.
    ★ 행위자(`user_id`)로 좁힌다 — 감사 표에는 테넌트 칸이 없다(`audit.read_page` 와 같은
      사실). 남의 테넌트 사람이 누른 시험 발송은 `user_id` 가 다르므로 내 카드를 못 닫는다.
    """
    from common import audit_writer

    actor = scope.require_actor()
    Model = audit_writer._model()
    for logger_name, prefix in _test_send_audit_channels():
        row = (Model._base_manager
               .filter(logger_name=logger_name, user_id=actor.pk,
                       api_name__startswith=prefix)
               .order_by("-id").first())
        if row is not None:
            return f"audit#{row.pk}"
    return None


#: 현장 회신이 남는 감사 채널 `(logger_name, api_name)`. **값의 정본은 커널**이고
#: (`kernels/k1_event/field_reply.py` 의 `LOGGER_NAME` · `ACTION`) 여기 적힌 것은 사본이다.
#:
#: ★ 왜 상수를 가져오지 않고 적어 두는가 — **App 은 커널의 공개 면만 만진다**
#:   (DA-04 §1-4 · D-278). `kernels.k1_event.field_reply` 는 서브모듈이라 App 이 가져오면
#:   계층 검사가 멈추고, 그 다음 걸음이 커널 로직이 App 으로 새는 길이다. 실제로 이 줄을
#:   import 로 짰다가 시험 다섯이 한꺼번에 빨개졌고, **그 빨강이 옳다.**
#: ★ 그래서 남는 위험은 하나다: 커널이 이름을 바꾸면 이 사본이 조용히 낡는다. 그 위험은
#:   시험이 든다 — `tests/test_onboarding_progress.py::OnboardingU3CardsTest::
#:   test_the_channel_name_is_the_same_string_the_kernel_writes` 가 커널 상수와 대 본다.
#:   시험은 App 이 아니므로 커널을 그대로 읽을 수 있다. (같은 파일의 K2 시험 발송 채널
#:   `"guardianx.dsm.notify"` 이 이미 같은 규약으로 적혀 있다.)
FIELD_REPLY_CHANNEL = ("guardianx.dsm.field_reply", "field_reply")


# ── U3 「이동 중」 · U6 「외부 연계」 술어 (턴 V · 차선 F) ────────────────────
#
# ★ 이 여섯은 **전부 이미 있는 기록**을 읽는다. 새 표도 새 질의도 만들지 않았다 —
#   온보딩 카드를 위해 기록을 새로 만들면 그 기록은 카드 말고는 아무도 안 쓰고,
#   아무도 안 쓰는 기록은 다음 턴에 죽은 필드가 된다(D-304).
def _closed_by_field_report(scope: TenantScope) -> Optional[str]:
    """**내가** 현장에서 한 줄을 보냈거나 사진을 올렸는가 (U3 ③ · PRD `field-reply 1`).

    PRD §7.2 U3 ③ 은 「도착·사진·한 줄」 한 장이고, 닫는 기록으로 `field-reply 1` 을
    적었다. 그래서 **한 줄이 먼저**이고, 사진은 같은 카드의 다른 손이다 — 둘 중
    하나면 닫는다(`_closed_by_test_send` 가 채널 둘을 한 장으로 본 것과 같은 모양).
    ★ 한 줄은 표가 아니라 **감사**에 산다(`kernels/k1_event/field_reply.py` 머리말) —
      감사 표에는 테넌트 칸이 없으므로 `user_id` 로 좁힌다. 남의 테넌트 사람의 회신은
      `user_id` 가 달라 내 카드를 못 닫는다(`_closed_by_test_send` 와 같은 사실).
    """
    from common import audit_writer

    logger_name, action = FIELD_REPLY_CHANNEL
    actor = scope.require_actor()
    row = (audit_writer._model()._base_manager
           .filter(logger_name=logger_name, api_name=action, user_id=actor.pk)
           .order_by("-id").first())
    if row is not None:
        return f"audit#{row.pk}"
    photo = (_tenant_rows(_model("DsmFieldPhoto"), actor)
             .filter(created_by=actor).order_by("-id").first())
    return f"field_photo#{photo.pk}" if photo else None


def _closed_by_notify_prefs(scope: TenantScope) -> Optional[str]:
    """**내** 알림 설정 행이 있는가 (U3 ④ · PRD `notify-prefs 저장`).

    ★ 행이 **있는 것**이 곧 「저장했다」다 — 이 표는 계정당 살아 있는 행 하나이고,
      쓰는 문(`PUT /api/dsm/me/notify-prefs`)을 지나야 태어난다. 값이 비어 있어도
      「비우기로 정했다」는 사람이 한 판정이다(`DsmNotifyPrefs` 머리말).
    """
    actor = scope.require_actor()
    row = (_tenant_rows(_model("DsmNotifyPrefs"), actor)
           .filter(user=actor).order_by("-id").first())
    return f"notify_prefs#{row.pk}" if row else None


def _closed_by_inbound_key(scope: TenantScope) -> Optional[str]:
    """연계용 키가 우리 테넌트에 하나라도 있는가 (U6 ① · PRD §7.2 U6 의 「키 1」).

    ★ **들어오는 키**(`inbound_api_key` — 남이 우리를 부를 때 쓰는 키)다. 나가는 키와
      같은 낱말로 적지 않는다(D-337 동음이의) — 방향이 다르면 다른 것이다.

    ★ 키 표는 §0.4(dj-core `apikey_account`)다. 직접 뒤지지 않고 **커널의 공개 면**
      (`k5_trust.list_keys`)을 부른다 — 그 함수가 이미 테넌트로 좁힌다(D-212).
    ★ 값은 읽지 않는다. 근거로 나가는 것은 **id 뿐**이다(D-204).
    """
    from kernels.k5_trust import list_keys

    try:
        keys = list(list_keys(scope=scope))
    except Exception:  # noqa: BLE001 — 못 읽은 것은 「닫히지 않은 것」이다
        return None
    return f"inbound_key#{keys[0].key_id}" if keys else None


def _closed_by_webhook_subscription(scope: TenantScope) -> Optional[str]:
    """나가는 웹훅 구독이 한 건이라도 있는가 (U6 ④ · PRD `subscription 1`)."""
    actor = scope.require_actor()
    row = _tenant_rows(_model("WebhookSubscription"), actor).order_by("-id").first()
    return f"webhook#{row.pk}" if row else None


def _closed_by_webhook_delivery(scope: TenantScope) -> Optional[str]:
    """그 구독에 **도달한 적이 있는가** (U6 ⑤ · PRD `delivery 200 1`).

    ★ 「구독을 만들었다」와 「받았다」는 다른 사실이다. 구독 행만 보고 이 카드를 닫으면
      한 번도 안 닿은 연계가 초록이 된다. `last_delivered_at` 이 **비어 있으면
      「한 번도 도달한 적 없다」**이고(모델 머리말), 그것이 이 카드의 답이다.
    """
    actor = scope.require_actor()
    row = (_tenant_rows(_model("WebhookSubscription"), actor)
           .filter(last_delivered_at__isnull=False).order_by("-id").first())
    return f"webhook_delivered#{row.pk}" if row else None


# ═══════════════════════════════════════════════════════════════════════════
# 카드 표 — PRD §7.2 그대로. 역할마다 일곱 장을 넘지 않는다
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 못 재는 카드는 `closes=None` + `why` 로 남는다. 「화면을 열어 봤다」는 서버에 기록이
#   없고, 기록 없이 닫으면 그것은 체크다. 그 자리가 생기는 턴(방문 기록·감사 열람)에
#   술어를 달면 이 표만 고치면 된다.
CARDS = {
    "U1": (
        Card("u1.queue", "지금 처리할 것 열기", "/dsm/queue",
             why="화면을 열어 본 사실이 서버에 남지 않습니다."),
        Card("u1.review", "사건 한 건 판정하기", "/dsm/queue", _closed_by_my_review),
        Card("u1.response", "접수하고 대응 시계 보기", "/dsm/queue", _closed_by_response),
        Card("u1.grid", "카메라 격자 순회 켜기", "/dsm/cameras/grid",
             why="순회를 켠 사실이 서버에 남지 않습니다."),
        Card("u1.handover", "인계 메모 한 건 남기기", "/handover", _closed_by_handover),
        Card("u1.sound", "알림 소리 켜기", "/dsm/queue",
             why="소리 설정은 이 브라우저에만 남습니다."),
        Card("u1.profile", "내 정보 확인", "/profile",
             why="내 정보를 본 사실이 서버에 남지 않습니다."),
    ),
    "U2": (
        Card("u2.summary", "지난 12시간 요약 보기", "/dsm/home",
             why="요약을 본 사실이 서버에 남지 않습니다."),
        Card("u2.unhandled", "미처리만 모아 보기", "/dsm/events?preset=unhandled",
             why="목록을 본 사실이 서버에 남지 않습니다."),
        Card("u2.regrade", "사건 한 건 재판정", "/dsm/events",
             why="등급을 바꾼 기록을 사건별로 되짚는 자리가 아직 없습니다."),
        Card("u2.by_reviewer", "요원별 처리 현황 열기", "/dsm/home",
             why="집계를 본 사실이 서버에 남지 않습니다."),
        # ★ 턴 U — BLOCKED 에서 옮김. 「카메라별 오탐률을 내주는 자리」는 아직 없지만,
        #   PRD §7.2 가 적은 닫는 기록은 `thresholds 시험 1` 이고 그 기록(K5 변경 이력)은 있다.
        Card("u2.threshold", "시끄러운 카메라 임계값 시험", "/dsm/home",
             _closed_by_threshold_change),
        Card("u2.report", "사건 보고서 한 쪽 만들기", "/dsm/events", _closed_by_report_run),
        Card("u2.drill", "훈련 모드 위치 확인", "/dsm/drill", _closed_by_drill),
    ),
    # ★ [턴 V · 차선 F] U3 은 **역할이 아니라 상태**다 — `onboarding_48.md` 가 「U1·U2·U4의
    #   이동 상태」라고 적은 그 사람이고, 그래서 아래 `PERSONA_VIEWERS` 가 누가 이 표를
    #   볼 수 있는지 가른다. 카드 넷은 PRD §7.2 U3 행 그대로(①~④)다.
    "U3": (
        Card("u3.login", "문자·푸시 링크로 열기", "/m/inbox",
             why="문자·푸시 링크로 들어왔다는 사실이 서버에 남지 않습니다 — "
                 "로그인 기록은 어느 링크를 눌러 왔는지를 가르지 않습니다."),
        Card("u3.response", "이동 중에 접수하기", "/m/inbox", _closed_by_response),
        Card("u3.field", "도착 보고 · 현장 한 줄", "/m/inbox", _closed_by_field_report),
        Card("u3.prefs", "근무 외 시간·담당 구역 설정", "/m/settings",
             _closed_by_notify_prefs),
    ),
    "U4": (
        Card("u4.week", "지난 7일 요약 보기", "/dsm/home",
             why="요약을 본 사실이 서버에 남지 않습니다."),
        Card("u4.stats", "기간별 통계 한 번 보기", "/dsm/home",
             why="집계를 본 사실이 서버에 남지 않습니다."),
        Card("u4.search", "사건 한 건 찾아보기", "/dsm/events",
             why="검색한 사실이 서버에 남지 않습니다."),
        Card("u4.report", "이번 달 우리 센터 확인", "/dsm/home", _closed_by_report_run),
        # ★ [턴 V · 차선 F] PRD §7.2 U4 ⑤ 가 적은 카드다. 턴 U 가 「PRD 38 · 코드 27」로
        #   센 차이 열한 장 중 **이 한 장이 U4 의 몫**이었다 — 빠진 것은 표에 없어서
        #   빠진 것이지 없어서 빠진 것이 아니었다. HWPX 서식은 아직 없으므로
        #   `blocked` 로 들어온다(분모에는 안 들어간다 · 진행률은 안 움직인다).
        Card("u4.hwpx", "상급기관 서식(HWPX) 내려받기", "/dsm/reports",
             why="HWPX 서식이 아직 없습니다 — 지금 나오는 것은 DOCX·PDF 둘입니다. "
                 "서식이 서는 턴에 술어를 답니다."),
        # ★ 턴 U — 화면(`AuditLog.tsx`)은 이번 턴(U24)에 서는 중이지만, 조회는
        #   읽기라 그 자체로는 서버 기록을 남기지 않습니다 — 화면이 서는 것과
        #   이 카드가 닫히는 것은 다른 일입니다. 조회 행위가 남기는 기록(예: 감사
        #   열람 자체의 감사)이 정해지면 술어를 답니다.
        Card("u4.audit", "처리 기록 조회", "/dsm/home",
             why="감사 기록 조회 화면이 이번 턴(U24)에 서는 중입니다 — 조회는 읽기라 "
                 "그 자체로는 서버 기록을 남기지 않습니다. 남길 기록이 정해지면 술어를 답니다."),
        Card("u4.privacy", "열람·삭제 청구 화면 확인", "/dsm/privacy-requests",
             why="화면을 열어 본 사실이 서버에 남지 않습니다."),
    ),
    "U5": (
        Card("u5.people", "사람 여섯 명 등록하고 역할 주기", "/users", _closed_by_people),
        Card("u5.cameras", "카메라 등록하고 주소 채우기", "/dsm/cameras/import",
             _closed_by_address_gap),
        Card("u5.recipients", "심각 등급 받는 사람 세우기", "/dsm/system",
             _closed_by_critical_recipients),
        Card("u5.retention", "영상 보관 기간 선언", "/dsm/system", _closed_by_retention),
        Card("u5.drill", "훈련 모드 한 번 켜 보기", "/dsm/drill", _closed_by_drill),
        # ★ 턴 U — BLOCKED 에서 옮김. 시험 발송은 K2 `test_send`(이메일 훈련 채널) 와
        #   `notify_prefs.test_send`(웹푸시 · 턴 T 실측 `deliveries #481`) 둘 다 감사에 남는다.
        Card("u5.channel", "알림 채널 시험 발송", "/dsm/system", _closed_by_test_send),
        Card("u5.backup", "백업 회수증 확인", "/dsm/system",
             why="백업 회수증을 내주는 자리가 이번 턴(U56) 에 서는 중입니다 — "
                 "그 화면이 남기는 기록이 정해지면 술어를 답니다."),
    ),
    # ★ [턴 V · 차선 F] U6 은 **기계**다 — `onboarding_48.md` 가 「외부 연계 시스템(기계)」
    #   라고 적었고 사람 계정이 없다. 그래서 이 표를 보는 사람은 연계를 **세우는 사람**
    #   (U5)이고, 카드 여섯은 전부 그 사람이 남기는 기록으로 닫힌다. 진행률 라우트는
    #   키를 받지 않으므로(`JwtOrInboundKey()` 기본값) 기계 스스로는 이 표를 못 읽는다 —
    #   그것이 사고가 아니라 설계다: 기계에게 「처음 시작하기」 카드는 소용이 없다.
    "U6": (
        Card("u6.key", "연계용 키 발급", "/dsm/integrations",
             _closed_by_inbound_key),
        Card("u6.health", "health 200 확인", "/dsm/integrations",
             why="`GET /api/dsm/health` 는 익명으로 열려 있고 감사에 남지 않습니다 — "
                 "누가 눌렀는지 서버가 모릅니다."),
        Card("u6.events", "키로 이벤트 목록 조회", "/dsm/integrations",
             why="키로 읽은 사실을 남기는 자리가 아직 없습니다 — 키 표는 §0.4(dj-core)라 "
                 "우리가 마지막 사용 시각을 더할 수 없습니다."),
        Card("u6.subscription", "웹훅 구독 등록(필터)", "/dsm/integrations",
             _closed_by_webhook_subscription),
        Card("u6.delivery", "서명 검증 통과 — 한 번 도달", "/dsm/integrations",
             _closed_by_webhook_delivery),
        Card("u6.update", "외부에서 상태 갱신 1", "/dsm/integrations",
             _closed_by_response),
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
# 「처음이세요」 첫 카드 셋 × 6 역할 = 18 (WO-04 §4-4 · 턴 AB · 차선 K)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ **두 벌을 만들지 않는다.** 이 표는 새 카드 체계가 아니라 위 `CARDS` 를 읽는
#   **한 겹 얇은 창**이다. 역할 홈에 처음 들어온 사람에게 일곱 장을 한꺼번에 들이밀면
#   아무도 안 읽으므로, 그중 **세 기둥**(골든타임 30 · 정직 관제 · 훈련 모드)만 먼저
#   보여 준다. 문안은 WO-04 §4-4 가 정본이고 여기 적힌 것은 그 표를 옮긴 것이다.
#
# ★ 같은 사실을 두 번 판정하지 않는다 — 규약 셋:
#     ① `same_as` 가 있으면 **판정은 그 카드 하나다.** 새 술어도, 새 행도 없다.
#        그 카드가 `CARDS` 에서 못 재는 카드면 이 카드도 **같은 사유로** 못 잰다.
#        (턴 AA 에 U56 이 잰 병 — 「같은 파일에 옳은 판정이 이미 있었는데 배지만
#        다른 것을 읽고 있었다」 — 가 나는 자리가 바로 여기다.)
#     ② `closes` 를 쓸 때는 **이미 있는 술어 함수를 그대로** 쓴다. 같은 뜻의 술어를
#        새로 짜면 두 술어가 언젠가 어긋나고, 어긋난 뒤에는 어느 쪽이 참인지 모른다.
#     ③ 이 표는 **진행률을 내지 않는다.** `progress()` 의 `total`·`done`·`percent` 는
#        예나 지금이나 `CARDS` 만 센다 — 진행률이 두 벌이 되면 둘 다 못 믿는다.
#
# ★ 못 재는 카드는 지우지 않는다(D-301). 여섯 역할 × 세 기둥 = **열여덟 장이 언제나
#   열여덟 장**이고, 그중 서버 기록이 없는 것은 이름과 사유와 함께 나간다. 지우면
#   「셋 중 둘」이 조용히 「둘 중 둘」이 되어 100 % 가 되고, 그 수는 거짓이다.

#: 세 기둥. 순서가 곧 화면의 순서다 (WO-04 §4-4 표의 열 순서 그대로).
KICK_PILLARS = (
    ("golden30", "골든타임 30"),
    ("honest", "정직 관제"),
    ("drill", "훈련 모드"),
)


class KickCard(NamedTuple):
    """첫 진입 카드 한 장. **셋 중 정확히 하나만** 채운다 — `same_as`·`closes`·`why`."""

    key: str
    #: `KICK_PILLARS` 의 코드. 어느 기둥의 카드인가.
    pillar: str
    #: WO-04 §4-4 의 문안 **정본**. 화면이 그리는 글자가 이것이다.
    prompt: str
    #: §4-4 의 「닫는 기록」 칸을 그대로 옮긴 것. **지시서가 무엇을 약속했는지**가
    #: 남아 있어야, 실제로 닫는 기록과 어긋날 때 그 어긋남이 보인다.
    promised_record: str = ""
    #: 같은 역할 `CARDS` 의 카드 키. 있으면 **판정은 그 카드 하나다**.
    same_as: str = ""
    #: `same_as` 가 없을 때만. **이미 있는 술어를 그대로 쓴다.**
    closes: Optional[Callable[[TenantScope], Optional[str]]] = None
    #: 술어도 짝지을 카드도 없는 이유. 못 재는 카드에만 적는다.
    why: str = ""


# ── 훈련 기둥의 술어 ────────────────────────────────────────────────────────
#
# ★ 이 다섯은 **새 표도 새 기록도 만들지 않는다.** 훈련 한 판의 창(켠 시각~끈 시각)은
#   이미 `stream_monitors/services/drill.py` 가 감사에서 읽어 `drill_report` 로 내주고,
#   「그 창 안에서 무슨 일이 있었나」는 사건 목록·발송 대장·보고서 실행 기록이 이미
#   안다. 온보딩 카드를 위해 기록을 새로 만들면 그 기록은 카드 말고는 아무도 안 쓰고,
#   아무도 안 쓰는 기록은 다음 턴에 죽은 필드가 된다(D-304).
# ★ 훈련 발송은 대장에서 **안 빠진다**(P-201 · `list_deliveries` 주석) — 빠지는 것은
#   청구뿐이다. 그래서 훈련 창 안의 발송을 이 술어들이 볼 수 있다.
def _drill_window(scope: TenantScope):
    """마지막(또는 진행 중인) 훈련 한 판의 창 `(시작, 끝|None)`. 없으면 `None`.

    ★ 창을 여기서 다시 계산하지 않는다 — `services.drill_report` 가 이미 감사에서
      켠 기록·끈 기록을 집어 창을 낸다. 두 곳이 창을 계산하면 두 창이 어긋나고,
      어긋난 창에서는 「훈련 중이었다」가 자리마다 다른 말이 된다(D-212).
    """
    from apps.dsm import services

    try:
        report = services.drill_report(scope=scope)
    except Exception:  # noqa: BLE001 — 못 읽은 것은 「닫히지 않은 것」이다
        return None
    if not _field(report, "measurable", False):
        return None
    started = _field(report, "started_at")
    if started is None:
        return None
    return started, _field(report, "ended_at")


def _closed_by_drill_event_closed(scope: TenantScope) -> Optional[str]:
    """훈련 사건 하나를 **종결까지** 끌고 갔는가 (U1 ③ · §4-4 「drill 사건 생성·종결 1」).

    ★ 「만들었다」로 닫지 않는다. 생성만으로 닫으면 훈련은 「사건이 떴다」에서 끝나고,
      이 카드가 가르치려는 것(미처리 → 접수 → 조치 중 → 종결)이 한 칸도 안 돈다.
    """
    window = _drill_window(scope)
    if window is None:
        return None
    from apps.dsm import services

    started, ended = window
    rows = services.recent_events(scope=scope, since=started, until=ended,
                                  response_state=["closed"], limit=1)
    return "event#%s" % rows[0].event_id if rows else None


def _drill_report_run(scope: TenantScope, kind: str) -> Optional[str]:
    """훈련 창 안에서 난 **사건**으로 만든 보고서 실행 기록 (U2 ③ · U4 ③).

    ★ 보고서 행에는 훈련 칸이 없다. 그러나 **사건에는 있다** — 훈련이란 이 저장소에서
      「훈련 창 안에 발생한 것」이고(`drill.is_drill_event_for_stream`), 그 정의를
      여기서 바꾸지 않는다. 그래서 「훈련 보고서」 = 창 안 사건을 대상으로 한 보고서다.
    ★ `status='succeeded'` 로 좁힌다 — 실패한 실행은 **나온 적 없는 보고서**다.
    """
    window = _drill_window(scope)
    if window is None:
        return None
    started, ended = window
    actor = scope.require_actor()
    rows = _tenant_rows(_model("DsmReportRun"), actor).filter(
        kind=kind, status="succeeded", event__isnull=False,
        event__occurred_at__gte=started)
    if ended is not None:
        rows = rows.filter(event__occurred_at__lte=ended)
    row = rows.order_by("-id").first()
    return "report_run#%s" % row.pk if row else None


def _closed_by_drill_incident_report(scope: TenantScope) -> Optional[str]:
    """훈련 사건 보고서 한 쪽이 나왔는가 (U2 ③ · §4-4 「DOCX 1」)."""
    return _drill_report_run(scope, "incident")


def _closed_by_drill_upper_report(scope: TenantScope) -> Optional[str]:
    """훈련 사건 상황보고서(별지 1호 · 상급기관)가 나왔는가 (U4 ③ · §4-4 「DOCX 1」)."""
    return _drill_report_run(scope, "upper")


def _closed_by_drill_delivery(scope: TenantScope) -> Optional[str]:
    """**내가** 훈련 알림을 받았는가 (U3 ③ · §4-4 「drill 수신 1」).

    ★ `mine=True` 로 서버가 거른다 — 「내게 온 것」을 화면이 거르면 페이지 밖 발송이
      **없는 것**이 된다(`delivery_history` 머리말 · P-13).
    ★ `succeeded=True` 다. 실패한 발송은 **안 받은 것**이고, 실패를 받은 것으로 세면
      알림이 한 번도 안 닿은 사람에게도 이 카드가 초록이 된다.
    """
    window = _drill_window(scope)
    if window is None:
        return None
    from apps.dsm import services

    started, ended = window
    rows = services.delivery_history(scope=scope, mine=True, since=started,
                                     until=ended, succeeded=True, limit=1)
    return "delivery#%s" % rows[0].delivery_id if rows else None


def _closed_by_drill_webhook_delivery(scope: TenantScope) -> Optional[str]:
    """훈련 사건이 **웹훅으로** 나갔는가 (U6 ③ · §4-4 「drill 수신 1」).

    ★ U3 ③ 과 같은 창·같은 대장을 읽되 채널이 다르다 — 사람에게 간 것과 기계에게
      간 것은 다른 사실이고, 한 술어로 접으면 웹훅이 한 번도 안 나간 연계가 초록이 된다.
    """
    window = _drill_window(scope)
    if window is None:
        return None
    from apps.dsm import services

    started, ended = window
    webhook = _model("DeliveryRecord").Channel.WEBHOOK
    rows = services.delivery_history(scope=scope, since=started, until=ended,
                                     succeeded=True, limit=100)
    for row in rows:
        if str(getattr(row, "channel", "")) == str(webhook):
            return "delivery#%s" % row.delivery_id
    return None


#: 첫 카드 셋 × 6 역할 = **18**. 문안 정본은 WO-04 §4-4.
KICK_CARDS = {
    "U1": (
        KickCard("u1.response", "golden30",
                 "대응 시계가 도는 사건 하나를 접수해 보세요",
                 "접수 기록 1", same_as="u1.response"),
        KickCard("u1.kick.honest", "honest",
                 "이 사진은 시드입니다 — 판정 근거를 열어 보세요",
                 "판정 패널 열람 기록 1",
                 why="판정 근거(사진·사유)를 연 사실이 서버에 남지 않습니다 — "
                     "`GET /api/dsm/events/{id}/snapshot` 은 워터마크를 찍어 바이트만 "
                     "내보내고 감사에 줄을 남기지 않습니다. 「판정했다」로 바꿔 닫지 "
                     "않습니다: 이 카드가 묻는 것은 누르기 전에 **열어 봤는가**이고, "
                     "판정으로 닫으면 그 물음이 사라집니다."),
        KickCard("u1.kick.drill", "drill",
                 "훈련 사건 하나를 만들어 종결까지",
                 "drill 사건 생성·종결 1", closes=_closed_by_drill_event_closed),
    ),
    "U2": (
        KickCard("u2.by_reviewer", "golden30",
                 "팀 대응 시계 p95 를 확인하세요",
                 "TeamStatus 열람 1", same_as="u2.by_reviewer"),
        KickCard("u2.regrade", "honest",
                 "등급을 다시 매겨 보세요(기록이 남습니다)",
                 "재판정 1", same_as="u2.regrade"),
        KickCard("u2.kick.drill", "drill",
                 "훈련 사건 보고서를 내 보세요 — 첫 줄에 「훈련」",
                 "DOCX 1", closes=_closed_by_drill_incident_report),
    ),
    "U3": (
        KickCard("u3.response", "golden30",
                 "내게 온 사건에 현장 도착을 눌러 보세요",
                 "response 1", same_as="u3.response"),
        KickCard("u3.kick.honest", "honest",
                 "알림이 사람에게 닿았는지 확인하세요",
                 "도달 카드 열람 1",
                 why="발송 대장을 **연** 사실이 서버에 남지 않습니다 — 대장에는 "
                     "「무엇이 언제 누구에게 갔나」가 있지만 「누가 그것을 봤나」는 "
                     "없습니다. 도달 자체(`DeliveryRecord`)로 바꿔 닫지 않습니다: "
                     "알림이 닿은 것과 사람이 닿았는지 확인한 것은 다른 사실이고, "
                     "둘을 접으면 이 기둥(정직 관제)이 묻는 것이 사라집니다."),
        KickCard("u3.kick.drill", "drill",
                 "훈련 알림을 받아 보세요",
                 "drill 수신 1", closes=_closed_by_drill_delivery),
    ),
    "U4": (
        KickCard("u4.report", "golden30",
                 "이번 주 골든타임 한 장을 열어 보세요",
                 "월간 자동본 열람 1", same_as="u4.report"),
        KickCard("u4.search", "honest",
                 "사건 이력을 사건번호로 찾아 보세요",
                 "검색 1", same_as="u4.search"),
        KickCard("u4.kick.drill", "drill",
                 "훈련 사건 상황보고서(별지 1호)를 내려 보세요",
                 "DOCX 1", closes=_closed_by_drill_upper_report),
    ),
    "U5": (
        #: ★ U5 의 골든타임 카드는 `CARDS["U5"]` 에 짝이 없다 — 임계값 카드는 U2 표에
        #:   있다. 그래서 **술어를 그대로 재사용**한다: 행 키만 이 표의 것이고, 판정하는
        #:   함수는 `u2.threshold` 와 한 몸이다. 같은 뜻의 술어를 새로 짜지 않는다.
        KickCard("u5.kick.golden30", "golden30",
                 "임계값을 우리 기관 값으로 바꿔 보세요",
                 "변경 기록 1", closes=_closed_by_threshold_change),
        KickCard("u5.recipients", "honest",
                 "알림 채널을 사람에게 닿는 것으로 바꿔 보세요",
                 "규칙 저장 1", same_as="u5.recipients"),
        KickCard("u5.kick.drill", "drill",
                 "훈련 구역 하나를 켜 보세요",
                 "OPS-15 구역 1",
                 why="「훈련 구역」이라는 것이 서버에 없습니다 — `Zone.Kind` 는 "
                     "카메라 묶음·폴리곤 둘뿐이고(D-299), 켠 구역이 훈련용인지 "
                     "서버가 모릅니다. 아무 활성 구역으로 바꿔 닫지 않습니다: "
                     "그러면 훈련과 상관없는 구역 하나가 훈련 카드를 닫습니다. "
                     "구역에 훈련 표식이 서는 턴에 술어를 답니다."),
    ),
    "U6": (
        KickCard("u6.events", "golden30",
                 "API 키로 사건 하나를 읽어 보세요",
                 "200 1", same_as="u6.events"),
        KickCard("u6.subscription", "honest",
                 "웹훅 구독을 등록하고 서명 검증을 확인하세요",
                 "구독 1", same_as="u6.subscription"),
        KickCard("u6.kick.drill", "drill",
                 "훈련 사건이 웹훅으로 오는지 보세요",
                 "drill 수신 1", closes=_closed_by_drill_webhook_delivery),
    ),
}


def kick_integrity() -> list:
    """이 표가 **스스로 어긋났는지**를 말한다. 시험·판정기가 이것을 읽는다.

    돌려주는 것은 어긋남의 목록이다 — 비어 있으면 성한 것이다. 예외를 던지지 않는
    이유: 표 하나가 어긋났다고 진행률 화면이 통째로 빌 일은 아니고, 어긋남은
    **보이게** 해야 고쳐진다.
    """
    problems = []
    pillars = tuple(code for code, _ in KICK_PILLARS)
    if set(KICK_CARDS) != set(CARDS):
        problems.append("kick 표의 역할이 CARDS 의 역할과 다릅니다: %s vs %s"
                        % (sorted(KICK_CARDS), sorted(CARDS)))
    for role, cards in sorted(KICK_CARDS.items()):
        if len(cards) != len(pillars):
            problems.append("%s 의 첫 카드가 %d 장입니다 — 기둥은 %d 입니다."
                            % (role, len(cards), len(pillars)))
        if tuple(c.pillar for c in cards) != pillars:
            problems.append("%s 의 기둥 순서가 §4-4 표와 다릅니다: %s"
                            % (role, [c.pillar for c in cards]))
        keys = {c.key for c in CARDS.get(role, ())}
        for card in cards:
            filled = [bool(card.same_as), card.closes is not None,
                      bool(card.why.strip())]
            if sum(1 for f in filled if f) != 1:
                problems.append("%s/%s 는 same_as·closes·why 중 정확히 하나여야 "
                                "합니다." % (role, card.key))
            if card.same_as:
                if card.same_as != card.key:
                    problems.append("%s/%s 의 키가 짝지은 카드와 다릅니다 — 키가 "
                                    "다르면 행이 둘이 되고 판정이 두 벌이 됩니다."
                                    % (role, card.key))
                if card.same_as not in keys:
                    problems.append("%s/%s 가 이 역할에 없는 카드(%s)를 가리킵니다."
                                    % (role, card.key, card.same_as))
            if not card.prompt.strip():
                problems.append("%s/%s 에 문안이 없습니다." % (role, card.key))
    return problems


def kick(*, scope: TenantScope, bucket: Optional[str], measured, blocked,
         now: Optional[datetime] = None) -> dict:
    """「처음이세요」 첫 카드 셋. **진행률을 내지 않는다.**

    `measured`·`blocked` 는 `progress()` 가 이미 낸 `CARDS` 의 판정이다. 그것을
    **다시 재지 않고 그대로 읽는다** — 같은 카드를 두 번 재면 두 번째가 첫 번째와
    다를 수 있고, 그 순간 화면의 배지와 목록이 다른 말을 한다(턴 AA · U56).
    """
    cards = KICK_CARDS.get(bucket or "", ())
    by_key = {c["key"]: c for c in measured}
    holes = {c["key"]: c for c in blocked}
    at = now or timezone.now()

    shown, unmeasurable = [], []
    for card in cards:
        row = {"key": card.key, "pillar": card.pillar, "prompt": card.prompt,
               "promised_record": card.promised_record}
        if card.same_as:
            twin = by_key.get(card.same_as)
            if twin is None:
                hole = holes.get(card.same_as)
                unmeasurable.append(dict(
                    row, link=hole["link"] if hole else "",
                    why=(hole["why"] if hole else
                         "짝지은 카드 %s 가 이 역할의 표에 없습니다." % card.same_as)))
                continue
            shown.append(dict(row, link=twin["link"], done=twin["done"],
                              source_ref=twin["source_ref"],
                              completed_at=twin["completed_at"],
                              closed_by="CARDS:%s" % card.same_as))
            continue
        if card.closes is None:
            unmeasurable.append(dict(row, link="", why=card.why))
            continue
        try:
            ref = card.closes(scope)
        except Exception:  # noqa: BLE001 — 근거를 못 읽은 것은 닫히지 않은 것이다
            ref = None
        stored = None
        if ref:
            stored = record_card(scope=scope, card_key=card.key, source_ref=ref,
                                 completed_at=at)
        shown.append(dict(row, link="", done=stored is not None,
                          source_ref=getattr(stored, "source_ref", "") if stored else "",
                          completed_at=(getattr(stored, "completed_at", None)
                                        if stored else None),
                          closed_by="predicate:%s" % card.closes.__name__))
    return {
        "pillars": [{"code": code, "label": label} for code, label in KICK_PILLARS],
        "cards": shown,
        #: 못 재는 첫 카드. **지우지 않는다** — 셋 중 둘이 조용히 둘 중 둘이 되면
        #: 「첫 카드 다 했다」가 거짓이 된다(D-301).
        "blocked": unmeasurable,
        "total": len(shown) + len(unmeasurable),
        "done": sum(1 for c in shown if c["done"]),
        "blocked_total": len(unmeasurable),
    }


#: 역할 코드 → 사람. **`config/k3_roles.py` 의 묶음을 그대로 쓴다** — 새 표를 만들지 않는다
#: (앞판 `features/nav/roleNav.ts` 가 같은 말을 하고, 두 벌이 되면 반드시 어긋난다).
def _role_buckets():
    from config.k3_roles import (
        K3_ROLE_EXECUTIVES, K3_ROLE_MANAGERS, K3_ROLE_OPERATORS, K3_ROLE_SYSOPS,
    )

    # 넓은 쪽부터. 한 계정이 여러 역할을 가지면 **더 넓은 자리**를 준다(앞판과 같은 순서).
    return (
        ("U5", K3_ROLE_SYSOPS),
        ("U2", K3_ROLE_MANAGERS),
        ("U4", K3_ROLE_EXECUTIVES),
        ("U1", K3_ROLE_OPERATORS),
    )


#: 역할이 아닌 페르소나 둘 — **누가 이 표를 볼 수 있는가** (턴 V · 차선 F).
#:
#: `bucket_of` 는 역할 코드로 사람을 가른다. 그런데 U3·U6 은 역할이 아니다:
#:   · **U3 은 상태다** — `onboarding_48.md` 가 「U1·U2·U4의 이동 상태」라고 적었다.
#:     같은 사람이 자리에 앉아 있으면 U1·U2·U4 이고 움직이면 U3 이다. 그래서 U3 표는
#:     그 셋이 본다 — 닫는 기록도 **그 사람 자신의 기록**이다.
#:   · **U6 은 기계다** — 사람 계정이 없다. 그 연계를 세우는 사람은 U5 이고, 카드
#:     여섯(키·구독·도달·상태 갱신)은 전부 U5 가 남기는 기록으로 닫힌다.
#:
#: ★ 이 표를 **비워 두고 카드만 늘리지 않는다.** 아무도 못 보는 버킷은 분모가 0인
#:   진행률이고, 0 위의 100 은 아무것도 증명하지 않는다(D-301). `verify_onboarding_walk`
#:   가 「닿을 수 없는 버킷」을 빨강으로 잡는다 — 이 표와 `_role_buckets()` 를 함께 읽는다.
PERSONA_VIEWERS = {
    "U3": ("U1", "U2", "U4"),
    "U6": ("U5",),
}


class PersonaError(Exception):
    """페르소나를 줄 수 없다. `code` 는 `unknown`(모르는 이름) 또는 `not_yours`."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def resolve_bucket(role_bucket: Optional[str],
                   persona: str = "") -> tuple[Optional[str], str]:
    """어느 표를 보여 줄까. **순수 함수다** — 판정기가 Django 없이 이것을 시험한다.

    돌려주는 것: `(버킷, 사유코드)`. 사유코드는 `""`(준다) · `unknown` · `not_yours`.
    ★ 페르소나를 안 주면 제 역할 표다(지금까지의 동작 그대로 · 화면은 안 바뀐다).
    """
    want = (persona or "").strip().upper()
    if not want:
        return role_bucket, ""
    if want not in CARDS:
        return None, "unknown"
    if want in PERSONA_VIEWERS:
        return (want, "") if role_bucket in PERSONA_VIEWERS[want] else (None, "not_yours")
    #: 역할 버킷을 이름으로 달라고 한 경우 — **제 것이면** 준다. 남의 역할 표는 안 준다:
    #: 남의 카드 목록은 그 자체로 남의 조직이 무엇까지 세웠는지를 말한다.
    return (want, "") if want == role_bucket else (None, "not_yours")


def bucket_of(actor) -> Optional[str]:
    """이 사람은 누구인가. **모르면 `None`** — 모르는 것을 아는 척하지 않는다."""
    try:
        codes = {str(c or "").strip().lower()
                 for c in actor.roles.values_list("code", flat=True)}
    except Exception:  # noqa: BLE001 — 역할 관계를 못 읽으면 「모른다」다
        return None
    for bucket, role_codes in _role_buckets():
        if codes & {c.lower() for c in role_codes}:
            return bucket
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 자동 완료 훅 — **근거가 있을 때만 행이 태어난다**
# ═══════════════════════════════════════════════════════════════════════════
def record_card(*, scope: TenantScope, card_key: str, source_ref: str,
                completed_at: Optional[datetime] = None):
    """카드 한 장을 닫는다. **`source_ref` 없이는 닫지 않는다.**

    이 함수가 온보딩 카드를 닫는 **유일한 자리**다. 사람이 부르는 문(HTTP)에서는
    닿지 않는다 — 닿게 만들면 그것이 곧 체크박스다.
    """
    if not (source_ref or "").strip():
        raise ValueError(
            f"card_key={card_key!r} 를 근거 없이 닫으려 했습니다. 근거 없는 완료는 "
            f"「체크했다」와 구별되지 않습니다 (WO-01 §12).")
    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return None
    model = _model("DsmOnboardingProgress")
    existing = _tenant_rows(model, actor).filter(user=actor, card_key=card_key).first()
    if existing is not None:
        return existing
    return model.objects.create(
        user=actor,
        card_key=card_key,
        completed_at=completed_at or timezone.now(),
        source_ref=source_ref.strip()[:128],
        group=group,
        purpose_code=PURPOSE_CODE,
    )


def progress(*, scope: TenantScope, persona: str = "") -> dict:
    """진행률 한 장. 화면 상단의 띠가 이 값을 그린다.

    ★ 분모(`total`)는 **이 파일의 표를 센 수**다. 표에 적지 않는다 — 세어서 낸다.
    ★ 못 재는 카드는 `blocked` 로 따로 나간다. 분모에서 빼는 것이 아니라 **다른 칸**이다:
      진행률은 「잴 수 있는 것 중 얼마나」이고, `blocked` 는 「아직 못 재는 것」이다.
      둘을 한 수로 접으면 어느 쪽이 남았는지 아무도 못 본다.
    """
    actor = scope.require_actor()
    role_bucket = bucket_of(actor)
    bucket, why = resolve_bucket(role_bucket, persona)
    if why == "unknown":
        raise PersonaError("unknown", "그런 사람 유형이 없습니다 — 있는 것은 %s 입니다."
                           % " · ".join(sorted(CARDS)))
    if why == "not_yours":
        raise PersonaError(
            "not_yours",
            "이 유형의 카드는 당신의 자리가 아닙니다 — 「이동 중」(U3)은 관제요원·"
            "관리자·담당 공무원의 다른 모드이고, 「외부 연계」(U6)는 그 연계를 "
            "세우는 시스템 관리자의 자리입니다.")
    now = timezone.now()
    cards = CARDS.get(bucket or "", ())

    model = _model("DsmOnboardingProgress")
    rows = {r.card_key: r for r in _tenant_rows(model, actor).filter(user=actor)}

    measurable, blocked = [], []
    for card in cards:
        if card.closes is None:
            blocked.append({"key": card.key, "title": card.title,
                            "link": card.link, "why": card.why})
            continue
        row = rows.get(card.key)
        if row is None:
            try:
                ref = card.closes(scope)
            except Exception:  # noqa: BLE001
                # 근거를 못 읽은 것은 **닫히지 않은 것**이지 실패가 아니다. 카드 하나가
                # 진행률 전체를 못 내게 만들면 화면이 통째로 빈다.
                ref = None
            if ref:
                row = record_card(scope=scope, card_key=card.key, source_ref=ref,
                                  completed_at=now)
        measurable.append({
            "key": card.key,
            "title": card.title,
            "link": card.link,
            "done": row is not None,
            #: 무엇이 이 카드를 닫았는가. **관리자·감사 자리의 값이다.**
            "source_ref": getattr(row, "source_ref", "") if row else "",
            "completed_at": getattr(row, "completed_at", None) if row else None,
        })

    total = len(measurable)
    done = sum(1 for c in measurable if c["done"])
    return {
        "role": bucket,
        #: 이 표를 **요청한 사람**의 역할. `role` 과 다르면 다른 모드를 보고 있는 것이다
        #: (U1 이 「이동 중」을 볼 때 `role="U3"` · `viewer_role="U1"`).
        "viewer_role": role_bucket,
        "persona": (persona or "").strip().upper() or None,
        #: 역할을 못 읽으면 카드가 0장이다. 0/0 을 100% 로 적지 않는다.
        "role_known": bucket is not None,
        "measured_at": now,
        "total": total,
        "done": done,
        #: 분모가 0이면 **`null` 이다 — 0 도 100 도 아니다** (D-301 · 오탐률과 같은 규약).
        "percent": (round(done * 100 / total) if total else None),
        "measurable": total > 0,
        "complete": total > 0 and done == total,
        "cards": measurable,
        "blocked": blocked,
        "blocked_total": len(blocked),
        #: 「처음이세요」 첫 카드 셋 (WO-04 §4-4 · 턴 AB). **위 수에 손대지 않는다** —
        #: `total`·`done`·`percent` 는 예나 지금이나 `CARDS` 만 센 수다. 이 칸은
        #: 같은 판정에서 **세 장만 골라 보여 주는 창**이지 두 번째 진행률이 아니다.
        "kick": kick(scope=scope, bucket=bucket, measured=measurable,
                     blocked=blocked, now=now),
    }
