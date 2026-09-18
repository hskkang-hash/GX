# -*- coding: utf-8 -*-
"""보고서 **실행 기록**과 그 값 모으기 — 서식 3 의 뒷면 (턴 U · P-173 U24).

이 파일이 하는 일 셋
--------------------
① **값을 모은다** — 월간본의 집계는 `apps/dsm/stats.py` 의 **공개 함수를 그대로 부른다**
   (`stats_summary` · `stats_axes`). 손 SQL 을 여기서 쓰지 않는다: 화면의 수와 종이의
   수가 갈리는 가장 흔한 길이 「같은 것을 두 번 센 것」이기 때문이다(AC-5 규약).
② **실행 기록을 남긴다** — `stream_monitors.DsmReportRun` 한 행. 무엇을(`kind`) ·
   사람이 불렀나 자동인가(`trigger`) · 끝났나(`status`) · 못 끝났으면 왜
   (`failure_reason`). ⚠ 이 표의 칸은 **U56 소유**다(이번 턴 `models.py` 는 U56 만
   고친다) — 있는 칸을 그대로 쓴다. 칸이 더 필요하면 등록 요청이고, 이번 턴에는 없다.
③ **다시 만든다** — 산출물은 저장하지 않는다. `.docx`·`.pdf` 를 부를 때마다 이 행에서
   **다시 그린다**(모델 머리말 그대로: 「특이사항」을 고치면 재생성된다). 파일을 저장하면
   특이사항을 고친 뒤에도 옛 파일이 내려가고, 그 종이가 결재에 올라간다.

서식은 여기 없다
----------------
종이의 모양은 `apps/dsm/incident_report.py` 한 곳이다(택배 칸 금지 목록 · 등급 낱말 ·
「기록 없음」 규약 · 시간대 고지가 거기 있다). 이 파일은 값을 모아 그 함수에 넘긴다.

배치(매월 1일)는 **등록하지 않는다 — 함수만 둔다**
--------------------------------------------------
celery beat 등재는 `config/**` 이고 그 파일은 조율자 소유다(WO-01 §4.2). 여기서는
배치가 부를 **한 함수**(`run_monthly_all`)를 두고, 등재 줄은 보고의 「등록 요청」에 적는다.
이번 턴은 그 함수를 **수동 1회**로 돌려 자동본 한 행을 실제로 만든다(trigger=auto —
사람이 시각을 골랐을 뿐 내용은 사람 손 없이 나왔다).
"""
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

#: ISO-03 목적 선언 — 이 표에 쓰는 행의 목적. 빈 문자열은 DB 가 거절한다(TenantModel).
PURPOSE_CODE = "dsm.report_run"

#: 종류 셋 — 모델 `DsmReportRun.Kind` 와 **같은 문자열**. 여기서 새 낱말을 만들지 않는다.
KIND_INCIDENT = "incident"
KIND_MONTHLY = "monthly"
KIND_UPPER = "upper"
KINDS = (KIND_INCIDENT, KIND_MONTHLY, KIND_UPPER)

TRIGGER_AUTO = "auto"
TRIGGER_MANUAL = "manual"
TRIGGERS = (TRIGGER_AUTO, TRIGGER_MANUAL)

STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

#: 화면(`Reports.tsx`)이 카드에 적는 이름. 서식 제목과 같은 글자다.
KIND_LABEL = {
    KIND_INCIDENT: "사건 보고서",
    KIND_MONTHLY: "이번 달 우리 센터",
    KIND_UPPER: "상급기관 제출용",
}
#: 실행 목록의 「자동/사람」 칸. PRD §7.4 가 묻는 그 수다.
TRIGGER_LABEL = {TRIGGER_AUTO: "자동", TRIGGER_MANUAL: "사람"}
STATUS_LABEL = {STATUS_SUCCEEDED: "생성됨", STATUS_FAILED: "생성 실패"}

#: 한 번에 돌려주는 실행 기록 수 상한.
RUN_CAP = 200
#: 상급 제출용이 한 번에 읽는 체크 수 상한.
UPPER_FLAG_CAP = 200


class ReportRunError(Exception):
    """실행 기록을 만들 수 없다 — 입력이 틀렸거나 자격이 없다(400/403 으로 번역된다)."""


# ═══════════════════════════════════════════════════════════════════════════
# 표 · 창
# ═══════════════════════════════════════════════════════════════════════════
def run_model():
    from django.apps import apps

    return apps.get_model("stream_monitors", "DsmReportRun")


def flag_model():
    from django.apps import apps

    return apps.get_model("stream_monitors", "DsmUpperReportFlag")


def live_runs(*, group):
    """살아 있는 실행 기록. `_base_manager` + `group` 명시 — 스레드에 남은 요청의 group 에
    기대지 않는다(메모리 「스레드에 남은 요청이 거짓 초록을 만든다」)."""
    return run_model()._base_manager.filter(group=group, deleted__isnull=True)


def live_upper_flags(*, group):
    """살아 있는 상급 보고 체크. `api_u24._live_flags` 가 이 함수를 부른다 —
    같은 질의를 두 벌 두지 않는다(D-212 계열)."""
    return flag_model()._base_manager.filter(group=group, deleted__isnull=True)


def month_window(when: datetime | None = None) -> tuple[datetime, datetime]:
    """`when` 이 든 달의 **달력 한 달**(시작 00:00 ~ 다음 달 시작). 현지 시각 기준.

    ★ 「이번 달」은 아직 안 끝났다 — 끝을 미래로 두면 종이가 오지 않은 날을 집계한 것처럼
      읽힌다. 그래서 `monthly_window` 가 끝을 **지금**으로 자른다. 이 함수는 달의 경계만
      낸다(배치가 지난달을 부를 때 그대로 쓴다).
    """
    from django.utils import timezone

    now = when or timezone.now()
    local = timezone.localtime(now)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    #: 다음 달 1일 — 28일을 더하면 어느 달이든 다음 달 안이고, 거기서 다시 1일로 내린다.
    nxt = (start + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0,
                                               microsecond=0)
    return start, nxt


def monthly_window(when: datetime | None = None) -> tuple[datetime, datetime]:
    """집계에 실제로 쓰는 창 — 달의 시작부터 **지금과 달의 끝 중 이른 쪽**까지."""
    from django.utils import timezone

    start, end = month_window(when)
    now = timezone.localtime(when or timezone.now())
    return start, min(end, now)


# ═══════════════════════════════════════════════════════════════════════════
# 실행 기록 한 행
# ═══════════════════════════════════════════════════════════════════════════
def _create_run(*, group, kind: str, trigger: str, status: str,
                period_start=None, period_end=None, event_id=None,
                note: str = "", failure_reason: str = "", actor=None):
    if kind not in KINDS:
        raise ReportRunError(f"kind={kind!r} 는 서식 이름이 아니다. 셋뿐이다: {', '.join(KINDS)}")
    if trigger not in TRIGGERS:
        raise ReportRunError(f"trigger={trigger!r} 는 없다. 둘뿐이다: {', '.join(TRIGGERS)}")
    if status == STATUS_FAILED and not failure_reason:
        #: DB 의 CHECK 가 먼저 막지만, 여기서 먼저 말해 준다 — 사유 없는 실패는
        #: 「없었다」와 「못 했다」를 가르지 못한다.
        raise ReportRunError("실패한 실행에는 사유가 반드시 있다")
    Model = run_model()
    fields = {f.name for f in Model._meta.get_fields() if hasattr(f, "attname")}
    kwargs = dict(group=group, purpose_code=PURPOSE_CODE, kind=kind, trigger=trigger,
                  status=status, period_start=period_start, period_end=period_end,
                  event_id=event_id, note=note or "", failure_reason=failure_reason or "")
    if actor is not None and "created_by" in fields:
        kwargs["created_by_id"] = getattr(actor, "pk", None)
    return Model._base_manager.create(**kwargs)


def run_row(run) -> dict:
    """실행 기록 한 행의 **화면 표현**. 시각은 ISO 문자열 — 화면이 자기 시계로 다시 적는다."""
    def _iso(v):
        return v.isoformat() if v is not None else None

    return {
        "run_id": run.pk,
        "kind": run.kind,
        "kind_label": KIND_LABEL.get(run.kind, run.kind),
        "trigger": run.trigger,
        "trigger_label": TRIGGER_LABEL.get(run.trigger, run.trigger),
        "status": run.status,
        "status_label": STATUS_LABEL.get(run.status, run.status),
        "event_id": run.event_id,
        "period_start": _iso(run.period_start),
        "period_end": _iso(run.period_end),
        "note": run.note or "",
        "failure_reason": run.failure_reason or "",
        "created_at": _iso(getattr(run, "created_on", None)),
    }


def list_runs(*, scope, kind: str | None = None, limit: int = 50) -> dict:
    """이 테넌트의 실행 기록 목록 — 최신 순. 남의 테넌트 행은 여기 오지 않는다."""
    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        #: 소속 없는 계정은 닫는 쪽이 기본값 — 0행이고, 0행이라고 말한다.
        return {"runs": [], "total": 0, "capped": False}
    if kind is not None and kind not in KINDS:
        raise ReportRunError(f"kind={kind!r} 는 서식 이름이 아니다")
    limit = max(1, min(int(limit or 50), RUN_CAP))
    qs = live_runs(group=group)
    if kind:
        qs = qs.filter(kind=kind)
    rows = list(qs.order_by("-id")[:limit + 1])
    capped = len(rows) > limit
    rows = rows[:limit]
    return {"runs": [run_row(r) for r in rows], "total": len(rows), "capped": capped}


def get_run(*, scope, run_id: int):
    """실행 기록 하나. **남의 테넌트는 404** — 403 이 아니다(존재도 알리지 않는다)."""
    from django.http import Http404

    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    group = get_user_group(actor)
    row = live_runs(group=group).filter(pk=run_id).first() if group is not None else None
    if row is None:
        raise Http404("그런 보고서 실행 기록이 없습니다.")
    return row


# ═══════════════════════════════════════════════════════════════════════════
# 값 모으기 — 서식 셋의 입력
# ═══════════════════════════════════════════════════════════════════════════
def monthly_payload(*, scope, since, until) -> tuple[dict, dict]:
    """월간본이 그릴 두 사전 — **`stats.py` 공개 함수 그대로**. 여기서 다시 세지 않는다."""
    from apps.dsm import stats

    summary = stats.stats_summary(scope=scope, since=since, until=until)
    axes = stats.stats_axes(scope=scope, since=since, until=until)
    return summary, axes


def upper_rows(*, scope, since, until) -> tuple[list[dict], int]:
    """상급 제출용의 사건 줄 — **사람이 체크한 것만**(`DsmUpperReportFlag`).

    Returns:
        (줄들, 못 읽은 수). 체크는 있는데 사건을 못 읽으면(파기·접근 불가) 그 수를 센다 —
        조용히 빼면 종이가 「대상이 적었다」로 읽힌다(D-290).
    """
    from django.http import Http404

    from common.tenant_filters import get_user_group

    from apps.dsm import services

    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return [], 0
    qs = live_upper_flags(group=group)
    if since is not None:
        qs = qs.filter(reported_at__gte=since)
    if until is not None:
        qs = qs.filter(reported_at__lte=until)
    rows: list[dict] = []
    missing = 0
    for flag in qs.order_by("-reported_at")[:UPPER_FLAG_CAP]:
        try:
            view = services.event_detail(scope=scope, event_id=flag.event_id)
        except Http404:
            missing += 1
            continue
        rows.append({
            "event_id": flag.event_id,
            "occurred_at": getattr(view, "occurred_at", None),
            "severity": getattr(view, "severity", None),
            "event_type": getattr(view, "event_type", None),
            "camera": getattr(view, "stream_monitor_name", None),
            "verdict": getattr(view, "verdict", None),
            "reported_at": flag.reported_at,
        })
    return rows, missing


def html_for_run(*, scope, run) -> str:
    """실행 기록 하나를 **지금 다시 그린다.** 저장된 파일이 없다는 것이 요점이다.

    Raises:
        Http404: 사건 보고서인데 그 사건을 못 읽는다(파기·남의 테넌트).
        IncidentReportUnavailable: 자료를 못 가져왔다.
        ReportRunError: 이 실행 기록은 애초에 실패한 행이다 — 실패를 종이로 내지 않는다.
    """
    from apps.dsm import incident_report as form

    actor = scope.require_actor()
    if run.status == STATUS_FAILED:
        raise ReportRunError(
            f"이 실행은 실패로 기록돼 있습니다 — {run.failure_reason or '(사유 미기재)'}")

    if run.kind == KIND_INCIDENT:
        if run.event_id is None:
            raise ReportRunError("사건 보고서인데 사건이 비어 있습니다.")
        return form.build_incident_html(scope=scope, event_id=run.event_id)

    since, until = run.period_start, run.period_end
    if since is None or until is None:
        raise ReportRunError("집계 구간이 비어 있어 다시 그릴 수 없습니다.")

    if run.kind == KIND_MONTHLY:
        summary, axes = monthly_payload(scope=scope, since=since, until=until)
        return form.build_monthly_html(
            tenant=form.tenant_name(actor), issued_by=form.person_label(actor),
            since=since, until=until, summary=summary, axes=axes,
            note=run.note or "", trigger=run.trigger)

    rows, missing = upper_rows(scope=scope, since=since, until=until)
    return form.build_upper_html(
        tenant=form.tenant_name(actor), issued_by=form.person_label(actor),
        since=since, until=until, rows=rows, note=run.note or "", missing=missing)


#: 파일 두 벌. **정본은 DOCX 다**(결정 ⑤ · HWP 가 여는 서식) · PDF 는 병행이다.
FORMATS = {
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "docx"),
    "pdf": ("application/pdf", "pdf"),
}


def render_run(*, scope, run, fmt: str) -> bytes:
    """실행 기록 하나 → 파일 바이트. DOCX 는 `docx_export`, PDF 는 **기존 K4 렌더러**.

    ★ 엔진을 두 곳에서 부르지 않는다 — PDF 는 `kernels.k4_report.render_html` 하나이고
      그 함수가 `report_template` 엔진을 부르는 유일한 자리다(K4 `renderers.py` 머리말).
    """
    if fmt not in FORMATS:
        raise ReportRunError(f"fmt={fmt!r} 는 없다. 둘뿐이다: docx · pdf")
    html = html_for_run(scope=scope, run=run)
    if fmt == "docx":
        from apps.dsm import docx_export

        return docx_export.render(run, html=html)
    from kernels.k4_report import render_html

    return render_html(scope=scope, html=html)


# ═══════════════════════════════════════════════════════════════════════════
# 만들기 — 사람이 부르는 셋 + 배치
# ═══════════════════════════════════════════════════════════════════════════
def create_report_run(*, scope, kind: str, trigger: str = TRIGGER_MANUAL,
                      event_id: int | None = None, since=None, until=None,
                      note: str = ""):
    """서식 셋 중 하나를 **만들고 실행 기록 한 행을 남긴다.**

    ★ 「만들었다」는 **글자를 실제로 조립했다**는 뜻이다. 조립해 보지 않고 행부터 남기면
      내려받을 때 처음 실패하고, 그때는 실행 목록이 이미 초록이다(조용한 성공 · D-284).
      조립이 실패하면 **실패 행을 남긴다** — 사유와 함께. 행을 안 남기면 「시도가 없었다」와
      「해 봤는데 안 됐다」를 가를 수 없다.
    """
    from django.http import Http404

    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        raise ReportRunError("소속 조직이 없어 보고서를 만들 수 없습니다.")
    if kind not in KINDS:
        raise ReportRunError(f"kind={kind!r} 는 서식 이름이 아니다. 셋뿐이다: {', '.join(KINDS)}")

    if kind == KIND_INCIDENT:
        if event_id is None:
            raise ReportRunError("사건 보고서에는 사건번호가 필요합니다.")
        since = until = None
    elif since is None or until is None:
        since, until = monthly_window()

    #: 먼저 행을 만들지 않는다 — 조립을 해 보고, 그 결과로 행의 `status` 를 정한다.
    stub = _Stub(kind=kind, trigger=trigger, event_id=event_id,
                 period_start=since, period_end=until, note=note,
                 status=STATUS_SUCCEEDED, failure_reason="")
    try:
        html_for_run(scope=scope, run=stub)
    except Http404:
        #: 없는 사건 · 남의 사건 — 실행 기록을 남기지 않는다(남의 사건에 우리 표의 행이
        #: 생기면 그 자체가 존재를 알린다). 라우트가 404 로 번역한다.
        raise
    except Exception as exc:                       # 자료 없음 · 집계 실패 · 서식 오류
        reason = f"{type(exc).__name__}: {exc}"[:250]
        run = _create_run(group=group, kind=kind, trigger=trigger,
                          status=STATUS_FAILED, period_start=since, period_end=until,
                          event_id=event_id, note=note, failure_reason=reason,
                          actor=actor)
        log.warning("[U24-REPORT] 실행 실패 run=%s kind=%s reason=%s", run.pk, kind, reason)
        return run

    run = _create_run(group=group, kind=kind, trigger=trigger, status=STATUS_SUCCEEDED,
                      period_start=since, period_end=until, event_id=event_id,
                      note=note, actor=actor)
    log.info("[U24-REPORT] 실행 기록 run=%s kind=%s trigger=%s", run.pk, kind, trigger)
    return run


class _Stub:
    """행을 만들기 **전에** 같은 모양으로 조립해 보는 임시 값. DB 에 안 간다."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.pk = None


def _batch_actor(group):
    """배치가 **누구의 자격으로** 집계하는가.

    ⚠ 가정 · 등록 요청 — 집계 함수(`stats.py` → K1 `query_events`)는 `scope.require_actor()`
      를 요구한다(시스템 스코프로는 테넌트를 좁힐 수 없다 · D-281). 배치에는 사람이 없으므로
      **그 조직의 관리자 계정 하나**를 자격으로 쓴다(pk 가 가장 작은 계정 — 결과가 흔들리지
      않게). 「사람이 요청했다」가 되는 것이 아니다: `trigger=auto` 가 그 사실을 남긴다.
      조율자께: 전용 배치 계정(예 `gxbatch_report`)을 두면 이 함수는 그 계정을 찾는 한 줄이
      된다. 계정 생성은 이번 턴 U24 소유 밖이라 하지 않았다.
    """
    from django.contrib.auth import get_user_model

    from common.tenant_roles import is_tenant_admin

    CoreUser = get_user_model()
    users = list(CoreUser._base_manager.filter(userprofilelink__group=group)
                 .order_by("pk")[:50])
    for user in users:
        if is_tenant_admin(user):
            return user
    return users[0] if users else None


def run_monthly(*, group, when: datetime | None = None, trigger: str = TRIGGER_AUTO,
                note: str = "", actor=None):
    """**배치의 한 조직 몫** — 「이번 달 우리 센터」 자동본 한 행.

    Args:
        group: 조직(테넌트) 하나.
        when: 이 시각이 든 달을 집계한다. 기본은 지금(= 이번 달).
        trigger: 기본 `auto` — 배치가 부르는 자리이기 때문이다.
        actor: 집계 자격. 없으면 `_batch_actor` 가 그 조직에서 찾는다.

    Returns:
        `DsmReportRun` 한 행. 자격을 못 찾으면 **실패 행**이다(사유와 함께) — 조용히
        건너뛰지 않는다. 건너뛴 조직은 다음 달에도 조용하고, 아무도 못 알아챈다.
    """
    from common.tenant_scope import TenantScope

    since, until = monthly_window(when)
    actor = actor or _batch_actor(group)
    if actor is None:
        return _create_run(group=group, kind=KIND_MONTHLY, trigger=trigger,
                           status=STATUS_FAILED, period_start=since, period_end=until,
                           note=note,
                           failure_reason="이 조직에 집계를 대행할 계정이 없습니다 "
                                          "(배치 자격 미지정)")
    return create_report_run(scope=TenantScope.of(actor), kind=KIND_MONTHLY,
                             trigger=trigger, since=since, until=until, note=note)


def run_monthly_all(*, when: datetime | None = None, trigger: str = TRIGGER_AUTO) -> list:
    """**배치 진입점** — 매월 1일 03:00 에 조직마다 한 행(부속서 A 243행).

    등재는 여기서 하지 않는다(`config/**` 은 조율자 소유) — 보고의 「등록 요청」에 줄을 적는다.
    ★ 한 조직이 실패해도 **다음 조직을 계속한다** — 한 조직의 자료 문제로 전 조직의
      자동본이 사라지면, 다음 달에 아무도 그 사실을 모른다.
    """
    from django.apps import apps

    Group = apps.get_model("user", "UserGroup")
    runs = []
    for group in Group._base_manager.all().order_by("pk"):
        try:
            runs.append(run_monthly(group=group, when=when, trigger=trigger))
        except Exception as exc:                            # pragma: no cover - 방어
            log.warning("[U24-REPORT] 월간 배치 조직 실패 group=%s err=%s", group.pk, exc)
    log.info("[U24-REPORT] 월간 배치 끝 — 조직 %s · 행 %s", len(runs), len(runs))
    return runs
