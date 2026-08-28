# -*- coding: utf-8 -*-
"""K4 보고서 엔진 — 공개 면 (DA-04 §2 K4).

템플릿에 값을 꽂아 PDF 를 만드는 한 벌.

이중 AC (DA-04 §1-2) — 충돌 시 **계약 AC 우선**
------------------------------------------------
    [F-11 계약] 템플릿 변수(**이벤트 · 조치 · 캡처**) 치환 및 PDF 출력
    [U2 상품]  보고서 생성 시간 **≤ 10분**

★ DA-04 가 해법을 이미 적었다:

    10분은 **사람의 작업 시간**이지 렌더 시간이 아니다. 줄이는 것은
    `build_context` 의 **자동 취합 범위**다 — 사람이 손으로 옮겨 적는 항목이 0 이면
    10분이 된다. 즉 **U2 의 KPI 가 F-11 의 치환 변수 목록을 결정한다.**

그래서 이 커널의 무게는 `render` 가 아니라 `build_context` 에 있다.
`ReportContext.manual_fields` 가 비어 있지 않으면 U2 는 아직 달성되지 않았고,
그 사실이 숫자로 보인다.

★ **조치 이력은 K2 를 그대로 읽는다** — 여기가 재사용의 증거다
--------------------------------------------------------------
DA-04 §2 K2: *"발송 기록이 곧 보고서의 '조치 이력' 행이다 — K4 가 이 레코드를
그대로 읽는다. **알림용·보고서용 두 벌로 적재하지 않는다.**"*

두 벌이면 알림과 보고서가 다른 말을 하고, 그 둘이 같은 회의에 올라가면 아무도 어느
쪽을 믿을지 모른다. 그리고 D-287 이 말한 재사용의 증거가 바로 이것이다 —
*"진짜 재사용은 K2·K3·K4 가 K1 을 소비하는 것으로 증명된다."*

DA-01 OPEN-03 정정 (2026-08-30 · D-210 실측 우선)
--------------------------------------------------
OPEN-03 은 *"`ReportTemplate` 은 `BaseModel` 상속 — **group 격리 없음**"* 이라 적었다.
**실행 중인 dj-core 실측은 다르다:**

  · `core.base.BaseModel` 이 **이미** `group = FK(user.UserGroup)` 와
    `objects = CustomManagerGroup()` 을 갖는다 (base.py:2073 · 2082).
  · `BaseModelWithGroup` 은 그 파일에서 **"DEPRECATED — BaseModel 을 직접 쓰라"** 로
    표시돼 있고, 필드를 하나도 더 정의하지 않는다 (base.py:2382).

즉 `ReportTemplate` 의 격리 수준은 `BaseModelWithGroup` 모델과 **같다.**
DB 실측도 그렇다: `report_template` 에 `group_id` 열이 **이미 있고**,
살아 있는 13행은 **전부 group 과 created_by 가 채워져 있다**
(group NULL 4행은 전부 soft-deleted 인 씨앗·시험 잔여물).

→ **기저 클래스 변경도, 마이그레이션도, 백필도 필요 없다.**
  증거: `docs/agent/evidence/W2-K4/open03_premise.md`
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.tenant_filters import assert_scoped, filter_by_group_field
from common.tenant_scope import TenantScope
from kernels.k4_report import renderers as renderer_registry
from kernels.k4_report.exceptions import (
    InvalidReportInput,
    NotImplementedYet,
    RenderFailed,
)
from kernels.k4_report.schemas import (
    REQUIRED_VARIABLES,
    ActionRow,
    CaptureRow,
    ReportContext,
    TemplateView,
)

#: 기간을 안 주면 보는 창. 보고서는 보통 "최근"을 묻는다.
DEFAULT_PERIOD = timedelta(days=30)


def _template_model():
    return apps.get_model("report_template", "ReportTemplate")


def _owner_field(model) -> str:
    """K1 과 **같은 판단**을 쓴다 — 판단은 한 곳에서만 한다 (D-212)."""
    from kernels.k1_event.services import _owner_field as k1_owner_field

    return k1_owner_field(model)


# ═══════════════════════════════════════════════════════════════════════════
# 1. list_templates — 테넌트 스코프 강제
# ═══════════════════════════════════════════════════════════════════════════
def list_templates(*, scope: TenantScope,
                   enabled_only: bool = True) -> tuple[TemplateView, ...]:
    """이 테넌트가 쓸 수 있는 템플릿 (DA-04 §2 K4).

    ★ `_base_manager` 로 시작하고 문지기로 좁힌다 — `objects` 는 §0.4 의
      `created_by__isnull` OR 절을 타서 주인 없는 행을 통과시킨다.
      템플릿에는 고객사 로고·문구가 들어간다. 남의 템플릿이 보이는 것은 그 자체로 누출이다.
    """
    Template = _template_model()
    actor = scope.require_actor()

    qs = Template._base_manager.all()
    qs = filter_by_group_field(qs, actor, field=_owner_field(Template))
    if enabled_only:
        qs = qs.filter(is_enabled=True)
    qs = qs.distinct().order_by("-is_default", "id")
    return tuple(
        TemplateView(
            template_id=row.pk, name=row.name,
            is_default=bool(row.is_default), is_enabled=bool(row.is_enabled),
            usage_count=int(row.usage_count or 0),
        )
        for row in qs
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. build_context — **U2 의 10분이 여기서 결정된다**
# ═══════════════════════════════════════════════════════════════════════════
def build_context(
    *,
    scope: TenantScope,
    event_id: int | None = None,
    mission_id: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> ReportContext:
    """치환 컨텍스트를 **자동으로** 모은다 (F-11 세 변수 · U2 10분).

    셋 다 다른 커널에서 온다. 여기서 새로 만들지 않는다:

        이벤트 → K1 `query_events` / `get_event`
        조치   → **K2 `list_deliveries`**  ← 두 벌로 적재하지 않는다 (DA-04 K2)
        캡처   → 그 이벤트가 이미 들고 있는 `snapshot_path` · `clip_path`

    ★ 출처 하나가 실패해도 **예외로 끊지 않는다.** 대신 `sources_failed` 에 이름을
      남긴다 — 그래야 "조치가 없었다"와 "조치를 못 가져왔다"가 갈린다(D-290).
      빈 목록으로 뭉개면 발송 조회가 실패한 보고서가 **"조치 없음"으로 인쇄되어**
      고객에게 나가고, 그 종이는 되돌릴 수 없다.
    """
    from kernels.k1_event import get_event, query_events

    actor = scope.require_actor()
    until = until or timezone.now()
    since = since or (until - DEFAULT_PERIOD)
    if since > until:
        raise InvalidReportInput(f"기간이 뒤집혔다 — since={since} > until={until}")

    failed: list[str] = []

    # ── 이벤트 ────────────────────────────────────────────────────────────
    events: tuple[Any, ...] = ()
    try:
        if event_id is not None:
            events = (get_event(event_id, scope=scope),)
        else:
            events = tuple(query_events(scope=scope, since=since, until=until,
                                        mission_id=mission_id, limit=500))
    except Exception as exc:
        # 남의 것을 물어 404 가 난 경우는 **실패가 아니라 거부**다 — 그대로 올린다.
        if type(exc).__name__ == "Http404":
            raise
        failed.append(f"events: {type(exc).__name__}")

    # ── 조치 — K2 를 그대로 읽는다 ────────────────────────────────────────
    actions: tuple[ActionRow, ...] = ()
    try:
        from kernels.k2_notify import list_deliveries

        rows = list_deliveries(scope=scope, since=since, until=until,
                               event_id=event_id, limit=500)
        actions = tuple(
            ActionRow(
                delivery_id=d.delivery_id, event_id=d.event_id, channel=d.channel,
                recipient_address=d.recipient_address, occurred_at=d.occurred_at,
                sent_at=d.sent_at, succeeded=d.succeeded,
                failure_reason=d.failure_reason,
            )
            for d in rows
        )
    except Exception as exc:
        failed.append(f"actions: {type(exc).__name__}")

    # ── 캡처 — 이벤트가 이미 들고 있다. 따로 저장하지 않는다 ──────────────
    captures = tuple(
        CaptureRow(event_id=e.event_id, snapshot_path=e.snapshot_path,
                   clip_path=e.clip_path)
        for e in events if getattr(e, "snapshot_path", "")
    )

    # ── 손으로 채울 칸 — U2 의 10분이 이 수에 달려 있다 ───────────────────
    #    지금은 **0** 이다. 늘어나는 순간 U2 가 깨지고, 그 사실이 여기서 보인다.
    manual: tuple[str, ...] = ()

    return ReportContext(
        since=since, until=until,
        events=events, actions=actions, captures=captures,
        manual_fields=manual, sources_failed=tuple(failed),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. render — 템플릿 + 컨텍스트 → PDF
# ═══════════════════════════════════════════════════════════════════════════
@transaction.atomic
def render(
    *,
    scope: TenantScope,
    template_id: int,
    context: ReportContext,
    renderer: str | None = None,
    allow_incomplete: bool = False,
) -> bytes:
    """PDF 바이트. **빈 PDF 를 성공으로 돌려주지 않는다** (D-284).

    ★ 기본값은 **불완전한 컨텍스트로 인쇄하지 않는 것**이다.
      출처가 실패했는데 그대로 찍으면 "조치 없음" 보고서가 고객에게 나가고,
      종이는 되돌릴 수 없다. 그래도 찍어야 한다면 `allow_incomplete=True` 를
      **명시적으로** 넘긴다 — 그때는 실패한 출처가 보고서 본문에도 실린다
      (`as_template_vars()["sources_failed"]`).

    ★ 남의 템플릿으로는 찍지 못한다. 문지기가 **try 밖 첫 줄**에 있다 (W0-14c).
    """
    Template = _template_model()
    actor = scope.require_actor()
    assert_scoped(Template, template_id, actor)

    missing = context.missing_variables
    if missing:
        raise InvalidReportInput(
            f"F-11 이 요구한 치환 변수가 컨텍스트에 없다: {missing}. "
            f"필수 3종: {', '.join(REQUIRED_VARIABLES)}")
    if not context.is_complete and not allow_incomplete:
        raise InvalidReportInput(
            f"불완전한 컨텍스트로 보고서를 만들지 않는다 — "
            f"실패한 출처 {list(context.sources_failed)} · "
            f"손으로 채울 칸 {list(context.manual_fields)}. "
            f"그래도 찍어야 하면 allow_incomplete=True 를 명시하라 (D-290)")

    row = Template._base_manager.get(pk=template_id)
    html = _fill(row.template or "", context)

    engine = renderer_registry.get(renderer)
    if engine is None:
        raise InvalidReportInput(
            f"renderer={renderer!r} 가 등록되지 않았다. "
            f"등록된 것: {', '.join(sorted(renderer_registry.REGISTRY))}")

    outcome = engine.render(html=html)
    if not outcome.ok:
        raise RenderFailed(
            f"보고서 렌더 실패 (template_id={template_id}, engine={engine.name}): "
            f"{outcome.reason}")
    # ★ 어댑터가 성공이라 해도 **빈 바이트는 성공이 아니다** (D-284).
    #   기본 어댑터는 스스로 0바이트를 거르지만, 나중에 끼울 엔진은 그러지 않는다 —
    #   그리고 0바이트 PDF 는 열리기는 하고 내용이 없다. 받는 사람은 "보고서가 비었다"로
    #   읽고 시스템은 "생성했다"로 센다. 판정을 어댑터에 맡기지 않는다.
    #   실측: `_EmptyPdfRenderer` 시험이 이 줄이 없을 때 통과했다.
    if not outcome.pdf:
        raise RenderFailed(
            f"엔진 {engine.name} 이 0바이트를 냈다 — 빈 PDF 는 성공이 아니다 "
            f"(template_id={template_id})")

    # 사용 횟수는 **성공했을 때만** 올린다. 실패까지 세면 U2 의 분모가 부푼다.
    Template._base_manager.filter(pk=template_id).update(
        usage_count=(row.usage_count or 0) + 1)
    return outcome.pdf


#: 불완전 보고서에 반드시 찍히는 표시. **템플릿이 무엇이든 남는다.**
INCOMPLETE_BANNER = "[GuardianX] 이 보고서는 불완전합니다"


def _fill(template_html: str, context: ReportContext) -> str:
    """치환. **엔진의 템플릿 문법을 커널이 다시 만들지 않는다.**

    지금은 `{{ name }}` 형태를 문자열로 바꾸는 최소 치환이다 — 저장소의 렌더 경로가
    Jinja2 와 Django 템플릿을 **둘 다** 쓰고 있어(`report_template/utils.py:428·432),
    어느 쪽이 정본인지가 미결이기 때문이다. 추정으로 한쪽을 고르지 않는다 (D-280).
    문법 확정은 **P-K4-1 로 적재**했다.
    """
    out = template_html
    for key, value in context.as_template_vars().items():
        out = out.replace("{{ " + key + " }}", str(value))
        out = out.replace("{{" + key + "}}", str(value))

    # ★ 불완전 사실은 **템플릿이 자리를 안 만들어도** 남는다.
    #   `{{ sources_failed }}` 를 안 쓴 템플릿으로 찍으면 그 사실이 조용히 사라지고,
    #   받는 사람은 완전한 줄 안다. 종이는 되돌릴 수 없다 (D-290).
    #   실측: 이 줄이 없을 때 시험이 잡았다 — 본문에 아무 표시도 없었다.
    if not context.is_complete:
        notice = (
            f"<div data-gx-incomplete=\"1\"><strong>{INCOMPLETE_BANNER}</strong>"
            f"<br>가져오지 못한 출처: {', '.join(context.sources_failed) or '없음'}"
            f"<br>손으로 채워야 하는 칸: {', '.join(context.manual_fields) or '없음'}"
            f"</div>"
        )
        out = notice + out
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 4. render_period — **아직 없다** (기간 보고서는 K7 컨텍스트가 선행)
# ═══════════════════════════════════════════════════════════════════════════
def render_period(*, scope: TenantScope, template_id: int,
                  since: datetime, until: datetime):
    """기간 단위 종합 보고서 (F-11 확장 · W3-3).

    ★ **구현하지 않았다.** `build_context` + `render` 를 붙이면 모양은 나오지만,
      기간 보고서가 요구하는 **집계**(구역별·등급별·추이)의 정의가 없다. 지금 만들면
      그 집계식이 곧 계약이 되고, K6 이 이미 세운 집계 경로와 **두 벌**이 된다 —
      DA-04 가 K6 에서 금지한 바로 그 모양이다.

    선행: K6 `kpi_series`(P-K6-3) 와 기간 집계 정의. 그 전까지는 던진다.
    """
    scope.require_actor()
    raise NotImplementedYet(
        "K4.render_period(기간 종합 보고서)는 아직 구현되지 않았다. "
        "기간 집계의 정의가 선행이고, 지금 만들면 K6 의 집계 경로와 두 벌이 된다 "
        "(DA-04 §2 K6 — 집계 경로를 하나로). P-K6-3 과 함께 연다")
