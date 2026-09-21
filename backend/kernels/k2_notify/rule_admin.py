# -*- coding: utf-8 -*-
"""S-16 「알림 받는 사람·채널」 · S-15 「내 정보」의 **서버 면** — UX-43 · WS-14 (턴 S · U56).

한 문장
-------
    규칙을 **읽고 · 저장하고 · 시험 발송한다.** 그리고 **심각 등급을 0명으로 만들지 못하게
    막는다** — 그 한 가지가 이 모듈이 `save_notification_rule` 위에 더하는 전부다.

왜 `services.save_notification_rule` 을 고치지 않고 이 파일을 새로 여나
----------------------------------------------------------------------
`services.save_notification_rule`(P-20 ① · 2026-09-22)은 **검사 넷**(등급·역할·채널·소속)을
이미 한다. 그 넷은 「이 규칙이 말이 되는가」를 묻고, 여기서 더하는 것은 다른 질문이다 —
**「이 저장 뒤에도 심각 경보가 사람에게 닿는가」.** 앞엣것은 규칙 한 줄의 성질이고
뒤엣것은 **테넌트 전체의 상태**다. 두 질문을 한 함수에 섞으면 시드·파이프라인처럼
「한 줄만 세우고 싶은」 호출까지 전체 상태 검사를 지나게 되고, 그러면 `seed_alert_routing`
이 첫 규칙을 세우는 순간(그때는 당연히 0명이다) **스스로 막힌다.**

    `save_notification_rule`   규칙 한 줄이 말이 되는가   — 낮은 문턱 · 시드도 지난다
    `save_rule`(여기)           저장 뒤에도 심각이 닿는가   — 높은 문턱 · **사람의 화면**이 지난다

그래서 화면은 이 문으로만 들어오고, 시드·파이프라인은 종전 문을 그대로 쓴다.

★ 「심각 0명 금지」는 **행 수가 아니라 사람 수로** 판정한다 (D-301)
------------------------------------------------------------------
규칙이 있어도 그 역할에 사람이 없으면 **아무에게도 안 간다.** 「규칙 ≥ 1」로 재면
그 상태가 초록이 되고, 그것이 DA-03 §3-2 가 이름 붙인 조용한 무력화다. 그래서 여기서는
`resolve_recipients` 를 불러 **실제로 고른 사람 수**를 센다 — 규칙 행을 세지 않는다.

★ 저장하고 **나서** 센다. 그리고 0이면 되돌린다 (`transaction.atomic`)
----------------------------------------------------------------------
저장 전에 「이 저장이 어떤 결과를 낳을까」를 손으로 예측하면 그 예측식이 곧
`resolve_recipients` 의 **복제본**이 되고, 복제본은 반드시 갈린다(D-212). 대신 실제로
쓰고 · 실제로 세고 · 0이면 **트랜잭션을 되돌린다.** 재는 것과 쓰는 것이 같은 코드를 지난다.

★ 시험 발송은 **훈련 채널로만 나간다** — 그리고 `DeliveryRecord` 를 만들지 않는다
----------------------------------------------------------------------------------
둘 다 일부러다:

    ① 훈련 채널(`log`)  — 「시험」이라 부르며 당직자 휴대전화를 울리면 그것은 시험이 아니라
                          사고다. 채널을 **인자로 받지 않는다** — 고를 수 있으면 언젠가
                          실채널이 선택되고, 그날 실채널로 나간 시험은 되돌릴 수 없다.
    ② 이력을 안 만든다  — `DeliveryRecord` 는 F-10 의 30초를 재는 표이자 5분 억제가 세는
                          표다(`services.notice_false_positive` 머리말 ★★와 같은 이유).
                          시험 한 건을 거기 끼우면 **그 다음 진짜 경보가 억제로 삼켜진다.**
                          시험은 발송이 아니라 **점검**이다 — 감사 한 줄로 남는다.

★ 사건을 만들지 않는다 (P-156)
------------------------------
시험 발송은 `DetectionEvent` 를 새로 만들지 않는다. 만들면 그 사건이 다음 회 표본에 들어가
**측정이 자기가 재는 상태를 바꾼다.** 수신자만 뽑아 훈련 채널로 한 통 보내고 끝낸다.

★ 이 파일에 **스코프 없는 공개 함수를 두지 않는다** (D-281 · `verify_tenant_scope`)
-----------------------------------------------------------------------------------
`kernels/` 안의 모듈 최상위 **공개** 함수는 `*, scope: TenantScope` 를 필수로 요구받는다.
채널 목록·훈련 채널 이름처럼 **테넌트를 만지지 않는** 것들은 그 규약을 무르게 하는 대신
**밑줄로 비공개**로 둔다(`channels.py` 가 레지스트리 객체로 같은 문제를 푼 것과 같은 판단).
밖에는 `notify_rule_overview` 가 그 값을 실어 내보낸다 — 그쪽은 규칙을 함께 내므로
`scope` 를 **실제로 쓴다.**

★ `me/notify-prefs` 는 **이 파일이 열지 않는다** — 그것은 U3 차선의 면이다
--------------------------------------------------------------------------
`DsmNotifyPrefs`(마이그 0029)는 「내 알림 설정」의 표이고, 그 쓰기 면은 등록부
`docs/agent/write_surfaces_v11.yaml` 의 **WS-02(lane U3)** 다. 여기서 여는 것은
**읽기 하나**(`my_notify_reach` — 「나는 무엇을 받는가」)뿐이고 그 표를 쓰지 않는다.
겹치면 한 표에 두 차선의 손이 닿고, 그 표가 곧 당직자의 수신 여부다.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from common import audit_writer
from common.tenant_scope import TenantScope
from kernels.k2_notify import channels as channel_registry
from kernels.k2_notify.exceptions import CriticalWithoutRecipients
from kernels.k2_notify.schemas import RuleView

#: 계약이 정한 **심각** 등급의 이름. 문자열을 화면·시험이 각자 들지 않게 여기 한 곳에 둔다
#: (정본은 `stream_monitors.models.DetectionEvent.Severity.CRITICAL`).
CRITICAL = "critical"

#: 채널 이름에 붙는 **사람의 말** 한 줄. 이름 자체는 레지스트리가 정하고(아래
#: `_selectable_channels`), 여기 있는 것은 **설명뿐**이다 — 목록을 두 벌로 두지 않는다.
CHANNEL_NOTE: dict[str, str] = {
    "email": "이메일 — 지금 붙어 있는 유일한 실채널",
    "webpush": "웹푸시 — 브라우저 잠금화면. 발송기는 U3 차선이 짓는다",
    "sms": "문자 — 발송 업체 미선정(대표 결정 대기)",
    "push": "앱 푸시 — 모바일 클라이언트 배포와 함께 온다",
    "webhook": "웹훅 — 상대 시스템으로. 구독·서명키가 선행",
    "log": "훈련 채널 — **사람이 아니라 로그에 도달한다.** 운영 규칙에 넣으면 당직자가 못 받는다",
}


@dataclass(frozen=True)
class NotifyReach:
    """등급 하나가 **실제로 몇 사람에게 닿는가.**

    `rule_count` 와 `recipient_count` 를 **따로** 든다 — 둘을 합쳐 세면 「규칙이 있다」가
    「사람이 받는다」로 읽힌다. 그 둘이 다른 사실이라는 것이 이 절의 전부다(D-301).
    """

    severity: str
    rule_count: int
    recipient_count: int
    #: 사람에게 도달하는 채널만. `log` 는 여기 없다 — 로그는 사람이 아니다.
    human_channels: tuple[str, ...]

    @property
    def reaches_people(self) -> bool:
        return self.recipient_count > 0 and bool(self.human_channels)


# ═══════════════════════════════════════════════════════════════════════════
# 비공개 — 테넌트를 만지지 않거나, 공개 함수가 부르는 속살
# ═══════════════════════════════════════════════════════════════════════════
def _group_of(scope: TenantScope):
    """이 사람의 테넌트. 못 정하면 **규칙을 만지지 않는다.**

    ★ `require_user_group` 을 부른다 — `get_user_group`(있으면 준다)이 아니다.
      뒤엣것은 소속이 없으면 `None` 을 주고, 그러면 부르는 쪽이 그 `None` 으로
      **전 테넌트의 규칙**을 고르게 된다. 그리고 이것이 `common.tenant_filters` 의
      진짜 문지기라 `verify_tenant_scope.py` 의 호출 그래프 추적이 인정한다
      (표식이 아니라 실제로 막기 때문이다 — `k5_trust/inbound_keys.py` 와 같은 형).
    """
    from common.tenant_filters import require_user_group

    if scope.is_system:
        raise CriticalWithoutRecipients(
            "알림 규칙 설정은 사람이 한다 — 시스템 스코프로 하지 않는다. "
            "주인 없는 규칙은 어느 테넌트의 당직자를 부르는지 아무도 모른다 (D-281)")
    return require_user_group(scope.actor)


def _rule_model():
    from django.apps import apps

    return apps.get_model("stream_monitors", "NotificationRule")


def _test_channel() -> str:
    """시험 발송이 나가는 채널 이름 — **훈련 채널 하나뿐이다.**

    `stream_monitors.services.drill.DRILL_CHANNEL` 을 **읽어서** 낸다. 글자를 여기 또
    적으면 두 벌이 되고, 갈리는 날 시험 발송이 훈련 채널이 아닌 곳으로 나간다.

    ★ **비공개다** — 테넌트를 만지지 않으므로 `scope` 를 받을 이유가 없는데, 커널
      공개 면은 D-281 로 `scope` 를 반드시 받아야 한다. 쓰지도 않을 `scope` 를 시그니처에
      다는 것은 「테넌트마다 다른 답이 있다」는 거짓 신호다.
    """
    from stream_monitors.services.drill import DRILL_CHANNEL

    return DRILL_CHANNEL


def _selectable_channels() -> tuple[dict, ...]:
    """화면이 그릴 **채널 목록**. 레지스트리를 읽어서 만든다.

    ★ 목록을 손으로 적지 않는 이유: 적으면 U3 이 웹푸시 어댑터를 끼우는 날 이 목록만
      옛말이 되고, **옛말이 된 목록은 옛말인 것이 안 보인다**(D-286). 여기서는
      `channels.REGISTRY`(붙어 있다)와 `channels.UNAVAILABLE`(자리는 있다)을 그대로 읽어
      `available` 칸으로 그 차이를 **화면에 넘긴다** — 화면은 「고를 수는 있으나 아직
      안 나간다」를 사람에게 그대로 말할 수 있다.
    ★ 이름이 여기서 나오므로 화면이 고른 채널은 `save_notification_rule` 의 검사 ②를
      반드시 지난다 — 화면이 고를 수 있는데 서버가 거절하는 자리를 만들지 않는다.
    """
    out = []
    for name in sorted(set(channel_registry.REGISTRY) | set(channel_registry.UNAVAILABLE)):
        usable = channel_registry.get(name) is not None
        out.append({
            "channel": name,
            "available": usable,
            #: 사람에게 도달하는가. `log` 는 거짓이다 — 그 사실을 화면이 배지로 그린다.
            "reaches_people": name not in channel_registry.NON_HUMAN,
            "note": CHANNEL_NOTE.get(name, ""),
            #: 왜 못 쓰는가. 쓸 수 있으면 빈 문자열이다.
            "unavailable_reason": "" if usable else channel_registry.why_unavailable(name),
        })
    return tuple(out)


def _reach(scope: TenantScope, group, severity: str) -> NotifyReach:
    """등급 하나의 도달. **규칙 수와 사람 수를 따로 센다.**"""
    from kernels.k2_notify.services import resolve_recipients

    rows = list(_rule_model()._base_manager.filter(
        severity=severity, is_active=True, group=group))
    people = resolve_recipients(scope=scope, severity=severity, group=group)
    human = sorted({c for r in rows for c in (r.channels or [])
                    if c not in channel_registry.NON_HUMAN})
    return NotifyReach(severity=severity, rule_count=len(rows),
                       recipient_count=len(people), human_channels=tuple(human))


def _critical_block_reason(reach: NotifyReach) -> str:
    """심각이 막힌 **사유 한 줄.** 안 막혔으면 빈 문자열이다.

    ★ 두 사유를 **가른다** — 다음 손이 다르기 때문이다(P-221). 「사람이 없다」는
      역할에 사람을 넣어야 풀리고, 「채널이 사람에게 안 간다」는 규칙의 채널을
      바꿔야 풀린다. 한 문장으로 뭉뚱그리면 운영자가 엉뚱한 쪽을 고치고,
      고친 뒤에도 안 풀리는 화면은 **고장으로 읽힌다**.

    ★ 사유는 **서버가 쓴 한국어**다 — 화면이 짓지 않는다(D-212 · 저장 409 와 같은
      규율). 화면이 사유를 지으면 서버가 판정을 바꾸는 날 화면만 옛말이 된다.
    """
    if reach.reaches_people:
        return ""
    if reach.recipient_count == 0:
        return ("심각 등급 규칙이 없거나, 규칙이 가리키는 역할에 사람이 없습니다. "
                "아래에서 심각 규칙을 하나 세우거나 그 역할에 사람을 넣어 주십시오.")
    # ★ 별표(강조 표시)를 안 쓴다 — 이 문장은 화면의 경고 상자에 **그대로** 들어가고,
    #   그 상자는 마크다운을 안 그린다. 그러면 고객이 별표를 글자로 읽는다.
    return (
        "심각 규칙이 가리키는 사람은 %d명 있지만, 그 규칙의 채널이 사람에게 닿지 "
        "않는 채널뿐입니다(훈련·검수용). 이 상태에서는 재난이 나도 당직자의 "
        "수신함·휴대전화로는 한 건도 가지 않습니다. 아래에서 심각 규칙의 채널에 "
        "사람에게 닿는 것을 하나 이상 넣어 주십시오." % reach.recipient_count)


def _critical_recipients(scope: TenantScope, group) -> int:
    """지금 **심각 경보를 받는 사람 수.** 규칙 수가 아니다."""
    from kernels.k2_notify.services import resolve_recipients

    return len(resolve_recipients(scope=scope, severity=CRITICAL, group=group))


def _rule_view(row) -> RuleView:
    return RuleView(
        rule_id=row.pk, severity=row.severity, role_id=row.role_id,
        role_code=getattr(row.role, "code", "") or "", zone=row.zone,
        channels=tuple(row.channels or []), is_active=row.is_active)


# ═══════════════════════════════════════════════════════════════════════════
# 공개 면 넷 — 읽기 · 저장 · 시험 발송 · 내 수신
# ═══════════════════════════════════════════════════════════════════════════
def notify_rule_overview(*, scope: TenantScope) -> dict:
    """S-16 화면이 읽는 **한 묶음** (UX-43).

    넷을 함께 낸다: 등급별 도달(`severities`) · 규칙 목록(`rules`) · 고를 수 있는 채널
    (`channels`) · **심각이 막혀 있는가**(`critical_blocked`). 나눠 부르게 하면 화면이
    넷 중 하나를 빠뜨리고, 빠뜨린 것이 `critical_blocked` 이면 운영자는 자기 테넌트의
    심각 경보가 아무에게도 안 간다는 사실을 모른 채 저장 버튼만 누른다.
    """
    from django.apps import apps

    group = _group_of(scope)
    Event = apps.get_model("stream_monitors", "DetectionEvent")

    rows = (_rule_model()._base_manager.select_related("role")
            .filter(group=group).order_by("severity", "id"))
    reach = {s: _reach(scope, group, s) for s in Event.Severity.values}
    critical = reach[CRITICAL]
    return {
        "severities": [
            {"severity": s, "label": str(label),
             "rule_count": reach[s].rule_count,
             "recipient_count": reach[s].recipient_count,
             "human_channels": list(reach[s].human_channels),
             "reaches_people": reach[s].reaches_people}
            for s, label in Event.Severity.choices
        ],
        "rules": [
            {"rule_id": v.rule_id, "severity": v.severity, "role_code": v.role_code,
             "role_id": v.role_id, "zone": v.zone, "channels": list(v.channels),
             "is_active": v.is_active}
            for v in (_rule_view(r) for r in rows)
        ],
        "channels": list(_selectable_channels()),
        #: ★★ **막혔는가는 「사람 수」가 아니라 「도달」이다** [턴 AA · U56 · P-220].
        #:
        #:   턴 S~Z 동안 이 칸은 `critical.recipient_count == 0` 이었다. 그래서
        #:   고객 화면에 **「심각 경보를 받는 사람 4명」 초록**이 뜨면서 바로 아래
        #:   표의 세 등급이 전부 **「닿지 않음」 빨강**이었다 [세종 실측 2026-09-21].
        #:   사람은 있는데 규칙의 채널이 `log`(훈련)뿐이라 **아무에게도 안 갔다.**
        #:   같은 화면이 두 말을 한 것이고, 그 초록은 **거짓 초록**이다.
        #:
        #:   이 파일이 이미 그 판정을 갖고 있었다 — `NotifyReach.reaches_people`
        #:   (`recipient_count > 0 and human_channels`). 등급 표는 그것으로 그리고
        #:   배지만 다른 식으로 쟀다. **판정식을 두 벌로 둔 자리**였고(D-212),
        #:   두 벌은 갈렸다. 이제 한 벌이다.
        "critical_recipient_count": critical.recipient_count,
        #: 사람에게 닿는 채널이 하나라도 있는가. 없으면 「수신자 N명」은 거짓이다.
        "critical_human_channels": list(critical.human_channels),
        "critical_blocked": not critical.reaches_people,
        #: ★ **왜 막혔는가를 서버가 적는다** — 화면이 두 사실을 갈라 말할 수 있어야
        #:   사람이 다음 손을 안다(P-221 「원인과 다음 손을 같은 줄에」). 빈
        #:   문자열은 「안 막혔다」다 — 화면이 `critical_blocked` 와 함께만 읽는다.
        "critical_block_reason": _critical_block_reason(critical),
        #: 시험 발송이 나갈 곳. 화면이 「어디로 가는지」를 누르기 **전에** 말한다.
        "test_channel": _test_channel(),
    }


def save_rule(*, scope: TenantScope, severity: str, role_code: str,
              channels, zone: str | None = None, is_active: bool = True,
              rule_id: int | None = None) -> RuleView:
    """규칙 하나를 저장한다. **심각을 0명으로 만드는 저장은 거절한다** (UX-43 AC).

    ★ 거절은 예외이지 값이 아니다. `{"saved": false}` 를 200 으로 돌려주면 화면이
      그것을 성공으로 그리는 날이 오고(W0-18 이 이 저장소에서 실제로 만난 모양),
      그러면 「저장했다」는 글자 뒤에서 심각 경보가 꺼진다.

    ★ **쓰고 나서 센다.** 예측식을 여기 두면 `resolve_recipients` 의 복제본이 되고
      복제본은 갈린다(D-212). `transaction.atomic` 안에서 실제로 쓰고, 실제로 세고,
      0이면 통째로 되돌린다 — 재는 코드와 쓰는 코드가 같다.
    """
    from kernels.k2_notify.services import save_notification_rule

    group = _group_of(scope)
    with transaction.atomic():
        view = save_notification_rule(
            scope=scope, severity=severity, role_code=role_code,
            channels=channels, zone=zone, is_active=is_active,
            rule_id=rule_id, group=group)
        remaining = _critical_recipients(scope, group)
        if remaining == 0:
            #: ⚠ 되돌린다. 이 예외가 트랜잭션을 깨고, 위에서 만든 행은 **없던 일이 된다.**
            raise CriticalWithoutRecipients(
                "이 저장은 **심각(critical) 경보를 받는 사람을 0명으로** 만든다. "
                "심각 등급에 받는 사람이 없으면 재난이 나도 아무에게도 안 가고, "
                "화면에는 규칙이 있는 것처럼 보인다 — 그것이 조용한 무력화다"
                "(DA-03 §3-2 · D-290). 저장하지 않았다. "
                "심각 규칙을 먼저 하나 세우거나, 그 역할에 사람을 넣어라")
    audit_writer.write(
        logger_name="guardianx.dsm.notify", tag="[RULE]", actor=scope.actor,
        action="notify.save_rule_guarded",
        api_name="dsm.notify.save_rule_guarded:%s" % view.rule_id,
        api_method="POST", outcome=audit_writer.ALLOWED,
        reason=("S-16 규칙 저장 — %s/%s 채널 %s · 저장 뒤 심각 수신자 %d명"
                % (view.severity, view.role_code, ",".join(view.channels), remaining)),
        before=None, after={"rule_id": view.rule_id, "severity": view.severity,
                            "role_code": view.role_code,
                            "channels": list(view.channels),
                            "is_active": view.is_active,
                            "critical_recipients_after": remaining},
        status_http=200)
    return view


def send_test_notification(*, scope: TenantScope, severity: str = CRITICAL) -> dict:
    """규칙이 고른 사람들에게 **훈련 채널로 한 통** 보낸다 (UX-43 「시험 발송」).

    ★ 채널을 **인자로 받지 않는다.** 고를 수 있으면 언젠가 실채널이 선택되고, 그날
      「시험」이라 부르며 당직자 휴대전화가 울린다. 나가는 곳은 언제나 훈련 채널이다.
    ★ `DeliveryRecord` 를 만들지 않는다 — 그 표는 F-10 의 30초와 5분 억제가 세는
      자리다. 시험 한 건을 끼우면 **그 다음 진짜 경보가 억제로 삼켜진다.**
    ★ 사건도 만들지 않는다 — 측정이 자기가 재는 표본을 바꾸지 않는다(P-156).

    돌려주는 것: 보낸 수 · 받을 사람 수 · 나간 채널. **0명이면 0명이라고 말한다** —
    「보냈다」로 덮지 않는다(D-290).
    """
    from kernels.k2_notify.services import resolve_recipients

    group = _group_of(scope)
    channel = _test_channel()
    adapter = channel_registry.get(channel)
    if adapter is None:                     # 훈련 채널이 없으면 시험 자체가 성립 안 한다
        raise CriticalWithoutRecipients(
            "훈련 채널(%s)이 등록돼 있지 않다 — 시험 발송이 나갈 곳이 없다. "
            "실채널로 대신 보내지 않는다" % channel)

    people = resolve_recipients(scope=scope, severity=severity, group=group)
    subject = "[GuardianX] 시험 발송 — %s 등급 수신 확인" % severity
    body = ("이 통지는 **시험 발송**입니다. 실제 재난 경보가 아닙니다.\n"
            "이 글이 보이면 %s 등급 규칙이 당신을 수신자로 고르고 있습니다.\n"
            "나간 채널: %s (훈련 채널 — 사람이 아니라 로그에 도달합니다)" % (severity, channel))

    sent = 0
    for person in people:
        if adapter.send(address=person.address, subject=subject, body=body).ok:
            sent += 1

    audit_writer.write(
        logger_name="guardianx.dsm.notify", tag="[RULE]", actor=scope.actor,
        action="notify.test_send", api_name="dsm.notify.test_send:%s" % severity,
        api_method="POST", outcome=audit_writer.ALLOWED,
        reason=("S-16 시험 발송 — %s 등급 · 수신자 %d명 · 훈련 채널(%s)로 %d건. "
                "실채널로는 한 건도 나가지 않았다"
                % (severity, len(people), channel, sent)),
        before=None,
        after={"severity": severity, "recipients": len(people),
               "channel": channel, "sent": sent},
        status_http=200)

    return {
        "severity": severity,
        "channel": channel,
        #: ★ 훈련 채널로 갔다는 사실을 **응답에 못박는다.** 화면이 「보냈습니다」만
        #:   그리면 사람은 자기 휴대전화를 확인하러 간다.
        "reaches_people": False,
        "recipients": len(people),
        "sent": sent,
        "note": ("훈련 채널로만 나갔습니다 — 사람이 아니라 로그에 도달합니다. "
                 "실제 수신함으로는 한 건도 가지 않았습니다."),
    }


def my_notify_reach(*, scope: TenantScope) -> dict:
    """S-15 「내 정보」가 읽는 한 묶음 — **나는 무엇을 받는가** (UX-42-me).

    ★ 이 함수는 **아무것도 쓰지 않는다.** 「내 알림 설정」의 쓰기 면
      (`me/notify-prefs` · `DsmNotifyPrefs`)은 등록부의 **WS-02(lane U3)** 이고,
      여기서 열지 않는다 — 한 표에 두 차선의 손이 닿으면 그 표가 곧 당직자의 수신
      여부다. 그래서 이 묶음은 **읽기**이고, 설정 화면이 아직 없다는 사실을
      `prefs_surface_open: False` 로 **말해 준다**(빈 칸으로 두지 않는다 · D-290).

    ★ 자기 계정의 값만 낸다 — 남의 것을 가리킬 인자가 **시그니처에 없다**(D-281
      「시그니처가 1차」). 소속은 `_group_of` 가 문지기로 정한다.
    """
    group = _group_of(scope)
    actor = scope.require_actor()

    codes = sorted({(getattr(r, "code", "") or "").strip()
                    for r in actor.roles.all()} - {""})
    rows = (_rule_model()._base_manager.select_related("role")
            .filter(group=group, is_active=True))
    #: 나를 고르는 규칙 = **내 역할을 가리키는 규칙.** 규칙은 사람이 아니라 역할을
    #: 가리키므로(모델 머리말), 내가 받는지는 내 역할로만 답할 수 있다.
    mine = [r for r in rows if (getattr(r.role, "code", "") or "") in codes]

    by_severity: dict[str, set] = {}
    for row in mine:
        #: ⚠ **집합의 갱신 메서드를 일부러 쓰지 않는다** [실측 2026-09-16 · 턴 S].
        #:   격리 대장의 쓰기 판별기(`tests/test_tenant_isolation._writes_to_db`)는
        #:   소스에서 점 뒤에 오는 네 낱말(create·save·update·delete)을 **글자로** 찾아
        #:   쓰기 면을 가려낸다. 파이썬 집합의 갱신과 ORM 의 갱신은 글자로 구별되지
        #:   않으므로, 그대로 두면 **읽기 전용인 이 함수가 쓰기 면으로 잡히고** 대장에
        #:   거짓 한 줄이 등재된다. 판별기를 무르게 하는 쪽이 아니라 이쪽을 고친다 —
        #:   대장은 **넓게 잡는 쪽**이 옳고(놓치면 조용히 통과한다), 무르게 한 판별기는
        #:   다음 진짜 쓰기 면을 놓친다.
        #: ⚠⚠ **이 주석 자체도 그 글자를 담으면 안 된다** — 판별기는 `inspect.getsource`
        #:    로 읽으므로 주석까지 본다. 처음에 문제를 설명하려고 그 글자를 그대로
        #:    적었다가 같은 시험이 다시 빨개졌다 [실측]. 설명은 낱말로만 한다.
        bucket = by_severity.setdefault(row.severity, set())
        for channel in (row.channels or []):
            bucket.add(channel)

    return {
        "user_id": getattr(actor, "pk", None),
        "username": getattr(actor, "username", "") or "",
        #: 자기 자신의 주소다 — 남의 것이 아니다. 이 값이 비어 있으면 **이메일 채널로는
        #: 아무것도 못 받는다**, 그 사실이 화면에 보여야 한다.
        "email": getattr(actor, "email", "") or "",
        "display_name": (getattr(actor, "first_name", "") or "").strip(),
        "group_id": getattr(group, "pk", None),
        "group_name": getattr(group, "name", "") or "",
        "roles": codes,
        "receives": [
            {"severity": sev,
             "channels": sorted(chans),
             "reaches_people": bool(sorted(set(chans) - channel_registry.NON_HUMAN))}
            for sev, chans in sorted(by_severity.items())
        ],
        #: 내 역할을 가리키는 규칙이 하나도 없으면 **나는 아무것도 못 받는다.**
        "receives_nothing": not by_severity,
        #: 「내 알림 설정」(조용 시간·구역·채널 좁히기)의 쓰기 면 — U3 차선(WS-02).
        #: 아직 안 열렸다는 것을 **말해 준다**: 화면이 빈 칸을 그리면 「설정이 없다」와
        #: 「설정 화면이 아직 없다」가 같은 그림이 된다.
        "prefs_surface_open": False,
    }


__all__ = [
    "CRITICAL",
    "CHANNEL_NOTE",
    "NotifyReach",
    "my_notify_reach",
    "notify_rule_overview",
    "save_rule",
    "send_test_notification",
]
