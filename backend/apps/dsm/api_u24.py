# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **U24(관제팀장 · 재난안전과 공무원)** 라우터 모듈.
이 파일은 U24 차선만 고친다.

규약은 `api_u1.py` 머리말과 같다: 기존 라우트는 옮기지 않는다 · `DsmAPI`·`DsmLawAPI` 뒤에
붙으므로 기존 경로에 다른 메서드를 더하지 않는다(405 삼킴) · 새 경로는 ISO-03·SEC-04·계약
도달을 태어날 때 통과한다.

★ `from __future__ import annotations` 를 **일부러 쓰지 않는다** (`api.py` D-378 과 같은 사유).
  `@tenant_scoped` 로 감싸인 핸들러의 주석은 그 데코레이터 모듈의 `__globals__` 에서
  풀리고, 미래 임포트가 켜지면 거기 없는 이름(`datetime` 등)이 영원히 안 풀려 500 이 된다.
  파이썬 3.11 은 미래 임포트 없이도 `X | None` 을 그대로 평가하므로 뺄 이유만 있고
  얻을 것이 없다.

이 파일이 여는 셋 — UX-39(통계 요약) · UX-35(요원별) · UX-36(오탐률)
-------------------------------------------------------------------
집계 로직은 전부 `apps/dsm/stats.py` 에 있다. 여기는 그 결과를 HTTP 로 얇게 연다
(`api.py::events_summary` 가 `services`+`kernels.k6_feedback` 를 얇게 여는 것과 같은 모양).

경로 이름 — **가정 (조율자 검토 필요)**
----------------------------------------
정본(§5 UX-35·UX-36·UX-39·부속서A 업무플로우 9·10·12)에 적힌 이름은 서로 다른 접두어를
쓴다: UX-35 는 `GET /events/by-reviewer`, UX-36(부속서A #10)은 `GET /cameras/false-positive
?days=7`, UX-39 는 `GET /stats?by=...`. 그런데 WO-01 §5 성능 표와 §6 파1 실행지도는
이 셋을 **묶어서** `stats`·`by-reviewer`·`false-positive` 세 이름으로 부르고(같은 §5 줄:
"집계 `stats`·`by-reviewer`·`false-positive`는 …"), 상위 작업 지시(이 차선을 띄운 지시)도
못 찾을 때의 기본값으로 `/stats/summary`·`/stats/by-reviewer`·`/stats/false-positive` 를
명시했다. 그래서 **셋을 한 이름공간(`/stats/*`)에 새로 연다** — `/events/by-reviewer` ·
`/cameras/false-positive` 로 열지 않는다. 이유 셋:
  ① 정본의 그 두 경로는 이번 파 1 범위보다 넓은 기능(UX-36 의 임계값 슬라이더+시뮬레이션
     저장, UX-35 화면의 다른 위젯들)에 딸려 있을 수 있어, 좁은 집계 라우트를 그 이름으로
     선점하면 나중에 그 넓은 기능이 다른 모양을 요구할 때 이름을 다시 못 쓰게 된다.
  ② WO-01 §5·§6 이 이미 `stats`/`by-reviewer`/`false-positive` 세 낱말을 그 자체로 쓰고
     있어, 상위 지시가 뜻한 것이 `/stats/*` 이름공간일 가능성이 높다.
  ③ 반경 좁은 쪽 — 새 이름공간은 기존 라우트와 절대 안 부딪힌다(라우트 삼킴 위험 0).
등록 요청: 조율자가 부속서A #10 의 실제 지향 경로(`/cameras/false-positive`)와 다르다고
판단하면 이 세 경로의 이름을 바꿔 등록해도 이 파일의 로직(핸들러 본문)은 그대로 재사용된다.
"""
from datetime import datetime

from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped

from apps.dsm import stats
from kernels.k6_feedback.exceptions import InvalidMetricInput


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api.py::_scope` 와 같은 규약 —

    파일마다 새 인증 경로를 만들지 않는다. 이 한 줄은 `TenantScope.of` 를 감쌀
    뿐이고, 두 파일이 갈릴 자리가 아니다(공용부 `api.py` 는 조율자 소유라 이번
    턴에 그 파일을 손대지 않는다 — 대신 같은 세 줄을 여기 그대로 둔다).
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _split_multi(value: str | None) -> str | list[str] | None:
    """쉼표로 여럿 — `api.py::events` 와 같은 관용구(`event_type=a,b`).

    화면이 유형마다 따로 부르면 두 응답을 화면이 합치게 되고, 그 순간 각 응답의
    상한이 따로 걸린다. 커널은 처음부터 `str | Iterable` 을 받으므로 새로 만드는
    것이 아니라 이미 있는 것을 그대로 연다.
    """
    if value and "," in value:
        return [v.strip() for v in value.split(",") if v.strip()]
    return value


@api_controller("", tags=["DSM — U2·U4 팀장·공무원 (WO-01 차선 U24)"])
class DsmU24API:
    """U24 차선의 새 라우트 — UX-35·UX-36·UX-39 (턴 Q 조율자 분할)."""

    # ── UX-39 통계 요약 ──────────────────────────────────────────────────
    @route.get("/stats/summary", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-39 통계 — 남의 테넌트 건수가 섞이면 격리 실패다")
    def stats_summary(self, request, since: datetime | None = None,
                      until: datetime | None = None,
                      event_type: str | None = None, severity: str | None = None):
        """기간 내 건수 · 유형별 · 등급별 · 판정상태별 · 대응진행별 집계 (UX-39 부분집합).

        ★ AC-5 「합계 = 목록 수」— `total` 은 같은 `since`·`until`·`event_type`·
          `severity` 로 `GET /events` 를 부른 개수와 같다. 같은 함수
          (`services.recent_events`)를 그대로 부르기 때문에 집계 경로가 갈리지 않는다.

        ★ 캐시 60초(WO-01 §5 — 배치 테이블은 이번 턴 스키마 밖이라 안 만든다. 가정).
          기간을 안 주면 최근 30일, 366일을 넘는 기간은 400 이다(p95 800ms 보호).
        """
        try:
            return stats.stats_summary(
                scope=_scope(request), since=since, until=until,
                event_type=_split_multi(event_type), severity=_split_multi(severity))
        except stats.StatsInputError as exc:
            raise HttpError(400, str(exc))

    # ── UX-35 요원별 처리 현황 ───────────────────────────────────────────
    @route.get("/stats/by-reviewer", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-35 요원별 처리 현황 — 남의 테넌트 요원 실적이 보이면 "
                         "격리 실패다")
    def stats_by_reviewer(self, request, since: datetime | None = None,
                          until: datetime | None = None):
        """요원(판정자)별 판정 건수 · 종결 · 평균 대응 시간 · 오탐 판정 수 (UX-35).

        ★ AC-4 「요원 ≥ 2행」— 두 사람 이상이 판정한 기간을 주면 `reviewers` 가
          그만큼의 행을 낸다. 한 사람뿐인 테넌트/기간이면 행도 하나뿐이다 — 지어내지
          않는다.
        """
        try:
            return stats.stats_by_reviewer(
                scope=_scope(request), since=since, until=until)
        except stats.StatsInputError as exc:
            raise HttpError(400, str(exc))

    # ── UX-36 오탐률 ─────────────────────────────────────────────────────
    @route.get("/stats/false-positive", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-36 오탐률 — 남의 테넌트 판정 수치가 섞이면 격리 실패다")
    def stats_false_positive(self, request, since: datetime | None = None,
                             until: datetime | None = None,
                             event_type: str | None = None,
                             severity: str | None = None):
        """기간의 오탐률 — 분모·분자 포함 (UX-36). 나눗셈은 K6(`false_positive_rate`)
        가 한다 — 여기서도 `stats.py` 에서도 다시 세지 않는다(DA-04 K6 표 그대로).

        분모(`reviewed`)가 0 이면 `false_positive_rate` 는 **null** 이다 — 0.0 이 아니다.
        """
        try:
            return stats.stats_false_positive(
                scope=_scope(request), since=since, until=until,
                event_type=_split_multi(event_type), severity=_split_multi(severity))
        except (stats.StatsInputError, InvalidMetricInput) as exc:
            raise HttpError(400, str(exc))

    # ── UX-36 어느 카메라가 시끄러운가 (부속서A U2 #10) ────────────────────
    #
    # ★ 경로를 `/cameras/false-positive` 로 열지 않는다. 이 파일 머리말이 정한 그대로
    #   집계는 `/stats/*` 한 이름공간에 산다 — `api.py` 의 `/cameras/*` 밑으로 들어가면
    #   그 컨트롤러가 먼저 잡는 자리가 생기고, 그 어긋남은 **라우팅 침묵**으로 나타난다.
    @route.get("/stats/false-positive/by-camera", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-36 카메라별 오탐률 — 남의 테넌트 카메라 이름과 판정 "
                         "수치가 나가면 격리 실패다")
    def stats_false_positive_by_camera(self, request, days: int | None = 7,
                                       since: datetime | None = None,
                                       until: datetime | None = None,
                                       top_n: int = 3):
        """카메라별 오탐률 **내림차순 · 상위 N 강조** (부속서A U2 #10 완결 조건).

        ★ 나눗셈은 K6 이 한다 — `stats.py` 도 여기도 다시 세지 않는다.
        ★ 판정 0건인 카메라는 `false_positive_rate: null` 이고 **정렬 맨 뒤**다.
          「한 번도 판정 안 한 카메라」가 「오탐이 없는 카메라」로 보이면 안 된다.
        ★ `days` 와 `since`/`until` 을 함께 주면 `since`/`until` 이 이긴다 —
          명시한 창이 기본 창보다 세다.
        """
        try:
            return stats.false_positive_by_camera(
                scope=_scope(request), since=since, until=until,
                days=None if since is not None else days, top_n=top_n)
        except (stats.StatsInputError, InvalidMetricInput) as exc:
            raise HttpError(400, str(exc))

    # ── UX-36 임계값 시뮬 · 되돌려 읽기 (부속서A U2 #11 · BF-3 4~5단계) ─────
    #
    # ★ **쓰는 문을 새로 열지 않는다.** 임계값을 바꾸는 문은 F-12 의
    #   `POST /api/dsm/settings/thresholds` 하나이고 이미 서 있다(사유 필수 400 ·
    #   계약 고정 409 · 무권한 403 + 감사 번호). 같은 일을 하는 문이 둘이면
    #   문지기가 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212).
    @route.post("/stats/thresholds/simulate", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-36 임계값 시뮬 — 남의 테넌트 사건으로 셈하면 격리 실패다")
    def simulate_threshold(self, request, camera_id: int, confidence_min: float,
                           days: int = 7):
        """슬라이더가 부르는 자리 — 「최근 N일 기준 **시간당 몇 건**」.

        ★ **아무것도 바꾸지 않는다.** POST 인 이유는 정본(BF-3 4단계)이 그 모양으로
          적었고 슬라이더 값이 질의 문자열에 남으면 캐시·로그에 사람의 시행착오가
          쌓이기 때문이다 — 저장은 아래 「저장」 단추가 F-12 문으로 한다.
        ★ 확신도가 빈 사건은 「남는다」고 세지 않는다 — 가를 수 있는 행이 0 이면
          `measurable: false` 이고 `events_per_hour` 는 **null** 이다(0.0 이 아니다).
        ★ 「많다」의 문턱(시간당 6건)은 **서버가 낸다**(`noisy_per_hour`) — 화면이
          자기 문턱을 들면 두 곳이 갈린다.
        """
        try:
            return stats.simulate_threshold(
                scope=_scope(request), camera_id=camera_id,
                confidence_min=confidence_min, days=days)
        except stats.StatsInputError as exc:
            raise HttpError(400, str(exc))

    @route.get("/stats/camera-thresholds", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-36 임계값 목록 — 설정 면과 같은 무게로 좁힌다")
    def camera_threshold_keys(self, request):
        """카메라별로 고칠 수 있는 임계값의 **이름표만**. 값은 여기서 안 나간다.

        화면이 키 이름을 손으로 들지 않게 하는 자리다 — 표 ①이 늘거나 줄면
        이 목록이 함께 움직인다. 계약이 못박은 값은 목록에 없다(슬라이더로 옮길 수
        있는 것처럼 그려 놓고 저장에서 409 를 내는 것이 거짓말이기 때문이다).
        """
        return stats.camera_threshold_keys(scope=_scope(request))

    @route.get("/stats/camera-threshold", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-36 임계값 재조회 — 남의 카메라 기준선을 읽어 갈 수 없다")
    def camera_threshold(self, request, camera_id: int, key: str):
        """「저장 → **재조회**」의 재조회 (부속서A U2 #11 완결 조건).

        ★ 값이 없으면 `value: null` · `set: false` 다 — **0 이 아니다.**
        ★ 남의 카메라는 커널의 문지기(`assert_scoped`)가 끊는다. 여기서 문지기를
          다시 세우지 않는다 — 두 벌은 반드시 어긋난다.

        거절:
          400  표 ①에 없는 키 (오타는 새 임계값이 아니다)
          403  남의 카메라 · 404  없는 카메라
        """
        from django.core.exceptions import PermissionDenied
        from django.http import Http404

        from kernels.k5_trust import ThresholdNotDefined

        try:
            return stats.camera_threshold(
                scope=_scope(request), camera_id=camera_id, key=key)
        except ThresholdNotDefined as exc:
            raise HttpError(400, str(exc))
        except Http404 as exc:
            raise HttpError(404, str(exc) or "그런 카메라가 없습니다.")
        except PermissionDenied as exc:
            raise HttpError(403, str(exc))

    # ══════════════════════════════════════════════════════════════════════
    # 턴 T (P-164 U24) — 통계 축 5 · CSV · 상급 보고 체크 · 감사 읽기
    # ══════════════════════════════════════════════════════════════════════

    # ── UX-39 통계 화면 — 축 5 (카메라 · 유형 · 심각도 · 판정 · 시간대) ──────
    @route.get("/stats/axes", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-39 통계 축 — 남의 테넌트 건수가 섞이면 격리 실패다")
    def stats_axes(self, request, since: datetime | None = None,
                   until: datetime | None = None,
                   event_type: str | None = None, severity: str | None = None):
        """기간 내 사건을 축 다섯으로 접는다. `total` 은 같은 창의 `GET /events` 목록 수와
        같다(AC-5) — 화면이 둘을 나란히 적고 다르면 빨강으로 말한다.
        """
        try:
            return stats.stats_axes(
                scope=_scope(request), since=since, until=until,
                event_type=_split_multi(event_type), severity=_split_multi(severity))
        except stats.StatsInputError as exc:
            raise HttpError(400, str(exc))

    @route.get("/stats/export.csv", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-39 통계 CSV — 남의 테넌트 건수가 파일로 나가면 격리 실패다")
    def stats_export_csv(self, request, since: datetime | None = None,
                         until: datetime | None = None,
                         event_type: str | None = None, severity: str | None = None):
        """「표 내려받기」(GX-COPY 정본) — `stats_axes` 를 그대로 CSV 로. UTF-8 BOM ·
        `text/csv; charset=utf-8` · 파일 이름은 `Content-Disposition` 이 든다.
        ⚠ 이 라우트는 **응답 캐시를 타면 안 된다**(`Cache-Control: no-store`) — 파일은
          사람이 보고서에 붙이는 것이라 60초 전 값이 「지금 값」으로 남는다.
        """
        from django.http import HttpResponse

        try:
            text = stats.stats_axes_csv(
                scope=_scope(request), since=since, until=until,
                event_type=_split_multi(event_type), severity=_split_multi(severity))
        except stats.StatsInputError as exc:
            raise HttpError(400, str(exc))
        resp = HttpResponse(text.encode("utf-8"), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="gx-stats.csv"'
        resp["Cache-Control"] = "no-store"
        return resp

    # ── UX-47 상급 보고 체크 (모델 `DsmUpperReportFlag` — 실측: 이미 있다) ───────
    #
    # ★ 경로 `/events/{id}/upper-report` 는 모델 머리말이 적은 그 이름이다. `api.py` 의
    #   `/events/{int:event_id}` 밑에 변수 조각이 하나뿐이고 `upper-report` 는 정수가
    #   아니라 삼킴이 없다(`api_u1.py` 의 `/events/{id}/note` 와 같은 자리).
    # ★ 같은 리터럴 경로에 POST(체크)와 DELETE(해제)를 **함께** 선언한다 — 한 경로 =
    #   한 PathView 라 갈라 선언하면 뒤의 것이 405 다(메모리 「라우트 삼킴 함정」).
    # ★ 해제는 소프트 삭제다(모델 머리말) — 「체크했다가 풀었다」가 행으로 남는다.
    # ★ 감사는 **성공도 실패도** 남긴다(`audit.record_event_action`) — 감사에 못 남기면
    #   체크도 일어나지 않는다(`audit.py` 머리말 규약).
    @route.get("/events/upper-report/flags", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-47 상급 보고 표시 — 남의 테넌트 사건의 체크가 보이면 격리 실패다")
    def upper_report_flags(self, request, event_ids: str = ""):
        """목록 화면이 한 번에 묻는 자리 — `event_ids=1,2,3` → 체크된 것만 돌려준다.
        비어 있으면 **이 테넌트의 체크 전부**(상한 `_FLAG_CAP`)."""
        return _upper_report_flags(scope=_scope(request), event_ids=event_ids)

    @route.post("/events/{int:event_id}/upper-report", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-47 상급 보고 체크 — 남의 테넌트 사건에 체크를 남기면 격리 실패다")
    def upper_report_set(self, request, event_id: int,
                         reported_at: datetime | None = None, reason: str = ""):
        """체크. `reported_at` 을 안 주면 지금이다(전화로 03:10 에 보고하고 03:30 에
        체크하는 사람은 시각을 준다). 이미 체크돼 있으면 **그 행을 그대로** 낸다(멱등)."""
        return _upper_report_set(scope=_scope(request), event_id=event_id,
                                 reported_at=reported_at, reason=reason)

    @route.delete("/events/{int:event_id}/upper-report", auth=JwtOrInboundKey())
    @tenant_scoped(reason="UX-47 상급 보고 해제 — 남의 테넌트 사건의 체크를 풀면 격리 실패다")
    def upper_report_clear(self, request, event_id: int, reason: str = ""):
        """해제(소프트 삭제). 체크가 없으면 404 — 「풀 것이 없다」를 200 으로 덮지 않는다."""
        return _upper_report_clear(scope=_scope(request), event_id=event_id, reason=reason)

    # ── 감사 읽기 (P-164 U24 ③) — U2 · U4 · U5 만 ─────────────────────────────
    @route.get("/audit", auth=JwtOrInboundKey())
    @tenant_scoped(reason="감사 읽기 — 남의 테넌트 행위자의 감사 행이 보이면 격리 실패다")
    def audit_read(self, request, since: datetime | None = None,
                   until: datetime | None = None, actor_id: int | None = None,
                   action: str | None = None, page: int = 1, page_size: int = 50):
        """`audit.py` 가 남긴 것을 읽는다 — 필터 3(기간 · 행위자 · 행위 종류) + 쪽.

        ★ **누가 읽나**: U2(관제팀장 — `K3_ROLE_MANAGERS`) · U4(지자체 담당관 — 읽기 전용
          `view_only*`) · U5(운영자 — `K3_ROLE_SYSOPS` · 테넌트 관리자 · 전역 관리자).
          관제요원(U1)·현장(U3)은 403 — 남의 행위 이력은 팀장의 자리다.
          역할 표는 `config/k3_roles.py` **한 곳**을 읽는다(두 벌을 두지 않는다).
        ★ 테넌트 좁히기는 `audit.read_page` 가 한다 — 여기서 다시 하지 않는다.
        """
        from apps.dsm import audit

        scope = _scope(request)
        denial = _audit_reader_denial(scope.actor)
        if denial:
            raise HttpError(403, denial)
        try:
            return audit.read_page(scope=scope, since=since, until=until,
                                   actor_id=actor_id, action=action,
                                   page=page, page_size=page_size)
        except ValueError as exc:
            raise HttpError(400, str(exc))


# ═══════════════════════════════════════════════════════════════════════════
# 턴 T — 라우트 뒷면. 얇게 둔다: 모델은 `stream_monitors.DsmUpperReportFlag`(실측 · 있다),
# 감사는 `apps/dsm/audit.py`, 사건 문지기는 `services.event_detail`(남의 것은 404).
# ═══════════════════════════════════════════════════════════════════════════

#: ISO-03 목적 선언 — 이 파일에서만 쓴다.
_UPPER_REPORT_PURPOSE = "dsm.upper_report"
#: 한 번에 돌려주는 체크 수 상한(`stats._ROW_CAP` 과 같은 발상).
_FLAG_CAP = 2000


def _audit_reader_denial(user) -> str | None:
    """감사 읽기 권한 — 허용이면 `None`, 아니면 사유 한 줄. **판정식을 새로 쓰지 않는다**:
    전역·테넌트 관리자는 `common.tenant_roles`, 읽기 전용은 `common.role_gate`,
    팀장·운영자 역할 코드는 `config.k3_roles` 표를 그대로 읽는다."""
    from common.role_gate import is_read_only
    from common.tenant_roles import is_global_admin, is_tenant_admin
    from config.k3_roles import K3_ROLE_MANAGERS, K3_ROLE_SYSOPS

    if is_global_admin(user) or is_tenant_admin(user) or is_read_only(user):
        return None
    roles = getattr(user, "roles", None)
    codes = set(roles.values_list("code", flat=True)) if roles is not None else set()
    if codes & (set(K3_ROLE_MANAGERS) | set(K3_ROLE_SYSOPS)):
        return None
    return "감사 이력은 관제팀장 · 지자체 담당관 · 운영자만 볼 수 있습니다."


def _flag_model():
    from django.apps import apps

    return apps.get_model("stream_monitors", "DsmUpperReportFlag")


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


def _flag_row(row) -> dict:
    #: 시각은 ISO 문자열로 — 이 dict 가 그대로 감사 `data_before/after`(JSON 칸)에 들어간다.
    return {
        "event_id": row.event_id,
        "flagged": True,
        "reported_at": _iso(row.reported_at),
        "checked_at": _iso(getattr(row, "created_on", None)),
        "checked_by_id": getattr(row, "created_by_id", None),
    }


def _live_flags(group):
    #: `_base_manager` + `deleted__isnull` + `group` 명시 — `objects` 는 스레드에 남은
    #: 요청의 group 으로 좁히므로(메모리 「스레드에 남은 요청」) 여기서는 우연에 안 기댄다.
    return _flag_model()._base_manager.filter(group=group, deleted__isnull=True)


def _upper_report_flags(*, scope: TenantScope, event_ids: str) -> dict:
    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    group = get_user_group(actor)
    if group is None:
        return {"flags": {}, "total": 0, "capped": False}
    qs = _live_flags(group)
    if event_ids.strip():
        try:
            ids = [int(x) for x in event_ids.split(",") if x.strip()]
        except ValueError:
            raise HttpError(400, "event_ids 는 쉼표로 구분한 정수다")
        qs = qs.filter(event_id__in=ids)
    rows = list(qs.order_by("-id")[:_FLAG_CAP + 1])
    capped = len(rows) > _FLAG_CAP
    rows = rows[:_FLAG_CAP]
    return {"flags": {str(r.event_id): _flag_row(r) for r in rows},
            "total": len(rows), "capped": capped}


def _upper_report_set(*, scope: TenantScope, event_id: int,
                      reported_at: datetime | None, reason: str) -> dict:
    from django.http import Http404
    from django.utils import timezone

    from common.tenant_filters import get_user_group

    from apps.dsm import audit, services

    actor = scope.require_actor()
    action = f"upper_report:set:{event_id}"
    try:
        services.event_detail(scope=scope, event_id=event_id)
    except Http404:
        #: 남의 사건 · 없는 사건 — **실패도 감사에 남는다**(AC-12 규약). 존재 여부는
        #: 응답에 새지 않는다(404 하나).
        audit.record_event_action(scope=scope, action=action, outcome=audit.DENIED,
                                  reason="사건이 없거나 남의 테넌트다", api_name=action,
                                  api_method="POST", status_http=404)
        raise HttpError(404, "그런 사건이 없습니다.")
    group = get_user_group(actor)
    if group is None:
        raise HttpError(403, "소속 조직이 없어 체크를 남길 수 없습니다.")

    existing = _live_flags(group).filter(event_id=event_id).first()
    if existing is not None:
        entry = audit.record_event_action(
            scope=scope, action=action, outcome=audit.ALLOWED,
            reason=reason or "이미 체크됨 — 그대로", before=_flag_row(existing),
            after=_flag_row(existing), api_name=action, api_method="POST",
            status_http=200)
        return {**_flag_row(existing), "audit_id": entry.audit_id, "created": False}

    row = _flag_model().objects.create(
        event_id=event_id, reported_at=reported_at or timezone.now(),
        group=group, purpose_code=_UPPER_REPORT_PURPOSE)
    entry = audit.record_event_action(
        scope=scope, action=action, outcome=audit.ALLOWED,
        reason=reason or "상급 보고 체크", before=None, after=_flag_row(row),
        api_name=action, api_method="POST", status_http=200)
    return {**_flag_row(row), "audit_id": entry.audit_id, "created": True}


def _upper_report_clear(*, scope: TenantScope, event_id: int, reason: str) -> dict:
    from common.tenant_filters import get_user_group

    from apps.dsm import audit

    actor = scope.require_actor()
    action = f"upper_report:clear:{event_id}"
    group = get_user_group(actor)
    row = _live_flags(group).filter(event_id=event_id).first() if group else None
    if row is None:
        audit.record_event_action(scope=scope, action=action, outcome=audit.DENIED,
                                  reason="풀 체크가 없다", api_name=action,
                                  api_method="DELETE", status_http=404)
        raise HttpError(404, "이 사건에는 상급 보고 체크가 없습니다.")
    before = _flag_row(row)
    row.delete()  # safedelete — 소프트 삭제. 행은 남고 `deleted` 가 찍힌다.
    entry = audit.record_event_action(
        scope=scope, action=action, outcome=audit.ALLOWED,
        reason=reason or "상급 보고 체크 해제", before=before,
        after={"event_id": event_id, "flagged": False},
        api_name=action, api_method="DELETE", status_http=200)
    return {"event_id": event_id, "flagged": False, "audit_id": entry.audit_id}
