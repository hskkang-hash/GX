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
        Card("u2.threshold", "시끄러운 카메라 임계값 시험", "/dsm/home",
             why="카메라별 오탐률을 내주는 자리가 아직 없습니다."),
        Card("u2.report", "사건 보고서 한 쪽 만들기", "/dsm/events", _closed_by_report_run),
        Card("u2.drill", "훈련 모드 위치 확인", "/dsm/drill", _closed_by_drill),
    ),
    "U4": (
        Card("u4.week", "지난 7일 요약 보기", "/dsm/home",
             why="요약을 본 사실이 서버에 남지 않습니다."),
        Card("u4.stats", "기간별 통계 한 번 보기", "/dsm/home",
             why="집계를 본 사실이 서버에 남지 않습니다."),
        Card("u4.search", "사건 한 건 찾아보기", "/dsm/events",
             why="검색한 사실이 서버에 남지 않습니다."),
        Card("u4.report", "이번 달 우리 센터 확인", "/dsm/home", _closed_by_report_run),
        Card("u4.audit", "처리 기록 조회", "/dsm/home",
             why="감사 기록을 여는 화면이 아직 없습니다."),
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
        Card("u5.channel", "알림 채널 시험 발송", "/dsm/system",
             why="채널 설정을 여는 화면이 아직 없습니다."),
        Card("u5.backup", "백업 회수증 확인", "/dsm/system",
             why="백업 선언을 내주는 자리가 아직 없습니다."),
    ),
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


def progress(*, scope: TenantScope) -> dict:
    """진행률 한 장. 화면 상단의 띠가 이 값을 그린다.

    ★ 분모(`total`)는 **이 파일의 표를 센 수**다. 표에 적지 않는다 — 세어서 낸다.
    ★ 못 재는 카드는 `blocked` 로 따로 나간다. 분모에서 빼는 것이 아니라 **다른 칸**이다:
      진행률은 「잴 수 있는 것 중 얼마나」이고, `blocked` 는 「아직 못 재는 것」이다.
      둘을 한 수로 접으면 어느 쪽이 남았는지 아무도 못 본다.
    """
    actor = scope.require_actor()
    bucket = bucket_of(actor)
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
    }
