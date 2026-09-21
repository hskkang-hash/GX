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
import re
from datetime import datetime

from ninja import Schema
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


class ReportRunIn(Schema):
    """「만들기」가 보내는 **본문(JSON)**. 질의 문자열로 받지 않는다 — 「특이사항」은 사람이
    쓴 글이고, 질의 문자열에 실린 글은 접근 로그·캐시·브라우저 이력에 그대로 남는다
    (턴 T 가 구독 비밀에서 본 그 자리 · P-166 과 같은 규약)."""

    kind: str
    event_id: int | None = None
    since: datetime | None = None
    until: datetime | None = None
    note: str = ""


@api_controller("", tags=["DSM — U2·U4 팀장·공무원 (WO-01 차선 U24)"])
class DsmU24API:
    """U24 차선의 새 라우트 — UX-35·UX-36·UX-39 (턴 Q 조율자 분할)."""

    # ═══════════════════════════════════════════════════════════════════
    # ★★ `stats/*` 에 **들어오는 키를 열지 않는다** — 턴 W · 차선 U24 의 답
    # ═══════════════════════════════════════════════════════════════════
    #
    # 두 턴째 떠다니던 질문이다: 「`stats/*` 에 `inbound_key=True` 를 줄 것인가.」
    # **이 턴의 답은 「열지 않는다」이고, 사유를 여기 적어 둔다** — 떠다니는 것보다 닫는
    # 편이 낫고, 닫은 이유가 적혀 있지 않으면 다음 턴에 또 떠다닌다.
    #
    # ① **분모가 틀렸다** [실측 2026-09-19 · 런타임 레지스트리 763자리]
    #    `stats/*` 는 여덟이 아니라 **아홉**이다 — GET 8 + **POST 1**
    #    (`/stats/thresholds/simulate`). 그 POST 는 `common/inbound_api_key` 규약 ③
    #    「읽기 전용부터」에 걸려 **애초에 열 대상이 아니다.** 「여덟을 연다」는 요청은
    #    실물과 안 맞았고, 안 맞는 요청을 그대로 집행하면 아홉째가 조용히 열린다.
    #
    # ② **선언 라우트는 하나가 아니라 둘이다** [같은 실측]
    #        GET /api/dsm/events         사유=F-05 외부 App 이벤트 조회
    #        GET /api/dsm/cameras/pulse  사유=UX-23 · 범위 `pulse:read` 를 **일부러 받은** 키만
    #    즉 「하나뿐이라 좁다」는 전제가 사실이 아니고, **여는 방법의 정본이 이미 있다** —
    #    데코레이터 한 줄이 아니라 **이름 붙은 범위**를 세우고 그 범위를 받은 키만 들인다.
    #
    # ③ 그래서 여는 일의 본체는 **`stats:read` 범위를 세우는 일**이고, 그 범위는 아직 없다
    #    [실측 턴 V · 차선 U56 — 「`stats`·`pulse` 미선언」]. 범위 없이 `inbound_key=True`
    #    만 달면 **기본 범위(`events:read`)만 가진 키가 통계에 전부 닿는다.**
    #    그 모양을 `inbound_api_key.py` 머리말이 계약 11조 자리에서 이름으로 금지했다 —
    #    「들어오는 키를 아직 안 만들었다」가 아니라 **「범위 없이 이미 열어 두었다」**.
    #
    # ④ **부르는 사람이 0이다.** `stats/*` 를 키로 부르는 외부 App 이 있다는 실측이 없다.
    #    필요를 못 본 채 여는 것은 D-300 부작위 규율의 반대다 — **기본값이 거절**이어야
    #    새 문이 조용히 표면을 넓히지 못한다.
    #
    # ★ **여는 조건**(다음 사람이 이 줄을 근거로 열 수 있게 적는다):
    #     ⓐ `stats:read` 범위가 서고  ⓑ 그 범위를 요구하는 외부 계약 절이 생기고
    #     ⓒ **키로 실제로 눌러 200 을 본 뒤** — 그때 **GET 8 개만** 연다.
    #        `POST /stats/thresholds/simulate` 는 규약 ③ 이 막는 자리다(열지 않는다).
    # ═══════════════════════════════════════════════════════════════════

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
            payload = audit.read_page(scope=scope, since=since, until=until,
                                      actor_id=actor_id, action=action,
                                      page=page, page_size=page_size)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        #: 턴 U — 해시 체인 두 칸을 붙인다(아래 `_with_chain_columns` 머리말).
        #: 턴 Y — 「대상」 칸을 붙인다. **수는 안 바뀐다**(아래 `_with_target_column` 머리말).
        return _with_target_column(_with_chain_columns(payload), scope=scope)

    @route.get("/audit/export.csv", auth=JwtOrInboundKey())
    @tenant_scoped(reason="감사 CSV — 남의 테넌트 감사 행이 파일로 나가면 격리 실패다")
    def audit_export_csv(self, request, since: datetime | None = None,
                         until: datetime | None = None, actor_id: int | None = None,
                         action: str | None = None, limit: int = 1000):
        """같은 필터의 감사 이력을 **파일 한 장**으로(턴 U · P-173 U24 ④).

        ★ 화면이 보는 쪽수와 **같은 함수**가 낸다 — 파일이 다른 질의를 타면 표와 파일이
          다른 사실을 말한다. 상한(`limit`)에 닿으면 **마지막 줄에 그렇게 적는다**.
        ★ `Cache-Control: no-store` — 파일은 사람이 보관하는 것이라, 60초 전 값이
          「지금 값」으로 남으면 안 된다(`/stats/export.csv` 와 같은 규약).
        """
        from apps.dsm import audit

        scope = _scope(request)
        denial = _audit_reader_denial(scope.actor)
        if denial:
            raise HttpError(403, denial)
        try:
            text = _audit_csv(scope=scope, since=since, until=until,
                              actor_id=actor_id, action=action, limit=limit,
                              reader=audit.read_page)
        except ValueError as exc:
            raise HttpError(400, str(exc))
        from django.http import HttpResponse

        resp = HttpResponse(text.encode("utf-8"), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="gx-audit.csv"'
        resp["Cache-Control"] = "no-store"
        return resp

    # ══════════════════════════════════════════════════════════════════════
    # 턴 U (P-173 U24) — 보고서 서식 3 · 실행 기록 · 파일 2(DOCX 정본 · PDF 병행)
    # ══════════════════════════════════════════════════════════════════════
    #
    # ★ 경로가 기존 `/reports/*` 를 삼키지 않는다 [실측 확인]: `api.py` 가 먼저 선
    #   자리는 `/reports/templates`(리터럴)와 `/reports/{int:template_id}.pdf`(정수
    #   변환기)뿐이다. `runs` 는 정수가 아니므로 그 변환기에 걸리지 않고, 우리 컨트롤러는
    #   그 뒤에 등록되므로 앞의 것을 가리지도 않는다(`urls.py` 규약 · 메모리 「라우트 삼킴」).
    # ★ 누가 보나 — 관제팀장(U2) · 지자체 담당관(U4) · 운영자(U5) · 관리자. 나머지는 403.
    #   남의 테넌트 실행 기록은 **404** 다(403 이 아니다 — 존재를 알리지 않는다).
    @route.get("/reports/runs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="보고서 실행 기록 — 남의 테넌트 실행이 보이면 격리 실패다")
    def report_runs(self, request, kind: str | None = None, limit: int = 50):
        """실행 목록 — 최신 순. 종류(`kind`)로 좁힐 수 있다."""
        from apps.dsm import monthly_report

        scope = _scope(request)
        denial = _report_reader_denial(scope.actor)
        if denial:
            raise HttpError(403, denial)
        try:
            payload = monthly_report.list_runs(scope=scope, kind=kind, limit=limit)
        except monthly_report.ReportRunError as exc:
            raise HttpError(400, str(exc))
        payload["kinds"] = [
            {"kind": k, "label": monthly_report.KIND_LABEL[k]} for k in monthly_report.KINDS]
        return payload

    @route.post("/reports/runs", auth=JwtOrInboundKey())
    @tenant_scoped(reason="보고서 만들기 — 남의 테넌트 자료로 종이를 만들면 격리 실패다")
    def report_run_create(self, request, payload: ReportRunIn):
        """「만들기」 — 서식 셋 중 하나를 조립하고 **실행 기록 한 행**을 남긴다.

        ★ 사람이 눌렀으므로 `trigger=manual` 이다. 자동본(`auto`)은 배치만 만든다 —
          사람이 누른 것을 자동이라고 적으면 PRD §7.4 의 수가 거짓이 된다.
        ★ 조립이 실패해도 **행은 남고**(`status=failed` + 사유) 200 이다. 실패를 404·500
          으로 뭉치면 「시도가 없었다」와 「해 봤는데 안 됐다」를 화면이 못 가른다.
        ★ 없는 사건 · 남의 사건은 404 이고 **행을 남기지 않는다**(행이 남으면 그 자체가
          남의 사건의 존재를 알린다).
        """
        from django.http import Http404

        from apps.dsm import monthly_report

        scope = _scope(request)
        denial = _report_reader_denial(scope.actor)
        if denial:
            raise HttpError(403, denial)
        try:
            run = monthly_report.create_report_run(
                scope=scope, kind=payload.kind, trigger=monthly_report.TRIGGER_MANUAL,
                event_id=payload.event_id, since=payload.since, until=payload.until,
                note=payload.note)
        except Http404:
            raise HttpError(404, "그런 사건이 없습니다.")
        except monthly_report.ReportRunError as exc:
            raise HttpError(400, str(exc))
        return monthly_report.run_row(run)

    @route.get("/reports/runs/{int:run_id}.docx", auth=JwtOrInboundKey())
    @tenant_scoped(reason="보고서 DOCX — 남의 테넌트 종이가 나가면 격리 실패다")
    def report_run_docx(self, request, run_id: int):
        """**정본**(결정 ⑤ · HWP 가 여는 DOCX). 내려받을 때 다시 그린다 — 저장된 파일이 없다."""
        return _report_file(request, run_id=run_id, fmt="docx")

    @route.get("/reports/runs/{int:run_id}.pdf", auth=JwtOrInboundKey())
    @tenant_scoped(reason="보고서 PDF — 남의 테넌트 종이가 나가면 격리 실패다")
    def report_run_pdf(self, request, run_id: int):
        """병행 — 같은 글자를 기존 K4 렌더러로 찍는다."""
        return _report_file(request, run_id=run_id, fmt="pdf")


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
    #: ★ 턴 U — 같은 질의를 상급 제출용 보고서도 쓴다. 두 벌을 두지 않는다(D-212 계열):
    #:   질의는 `monthly_report.live_upper_flags` 한 곳이고 여기는 그 이름을 부른다.
    from apps.dsm import monthly_report

    return monthly_report.live_upper_flags(group=group)


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


# ═══════════════════════════════════════════════════════════════════════════
# 턴 U — 뒷면 ①: 감사 해시 체인 두 칸 · CSV
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ `audit.read_page` 는 두 칸을 내지 않는다(그 파일은 이번 턴 U24 소유가 아니다 —
#   한 파일은 한 차선). 그래서 **라우트에서 칸을 더한다**: 저장된 값을 읽어 붙일 뿐,
#   해시를 여기서 **다시 계산하지 않는다.** 다시 계산하면 「저장된 값」과 「계산한 값」이
#   같은 이름으로 섞이고, 그 순간 검증이 자기 자신을 증명한다
#   (`common/audit_writer.AuditEntry` 머리말이 막는 그 모양).
# ★ 위조 여부를 판정하는 것은 여전히 `evidence_chain.verify_chain` 하나다. 이 칸이 말하는
#   것은 **이어짐**뿐이다: 이 행의 `prev_hash` 가 바로 앞 행의 `hash` 와 같은가.

#: 체인 상태 넷. 「모른다」를 지우지 않는다 — 모르는 것을 초록으로도 빨강으로도 적지 않는다.
CHAIN_LINKED = "linked"        # 앞 행의 hash 와 이어진다
CHAIN_BROKEN = "broken"        # 앞 행의 hash 와 다르다
CHAIN_UNCHAINED = "unchained"  # 체인이 서기 전(LAW-08 이전)에 쌓인 행 — 두 칸이 없다
CHAIN_UNKNOWN = "unknown"      # 앞 행을 이 화면에서 못 봤다(상한) — 회색이다

#: 한 쪽의 체인 상태를 가리려고 훑는 감사 행의 상한. 넘으면 그 쪽은 `unknown` 이다.
_CHAIN_SCAN_CAP = 3000
#: 앞 행을 찾을 때 되돌아보는 줄 수.
_CHAIN_BACK_CAP = 50
#: 화면이 적는 앞자리 수(12자)는 **화면의 몫**이다 — 서버는 전체 값을 낸다.
#: 자른 값을 서버가 내면 두 사람이 서로 다른 「해시」를 말하게 된다.


def _audit_rows_queryset():
    from django.apps import apps

    from common import evidence_chain

    return (apps.get_model("logger", "AuditLogs")._base_manager
            .filter(logger_name__startswith=evidence_chain.CHAIN_PREFIX))


def _chain_pair(payload) -> tuple[str, str]:
    from common import evidence_chain

    if not isinstance(payload, dict):
        return "", ""
    return (str(payload.get(evidence_chain.PREV_KEY) or ""),
            str(payload.get(evidence_chain.HASH_KEY) or ""))


def _with_chain_columns(payload: dict) -> dict:
    """쪽 하나에 `prev_hash` · `hash` · `chain` 세 칸을 더한다.

    ★ 이 쪽의 행들은 **테넌트로 걸러진 것**이라 서로 이웃이 아니다 — 그래서 「앞 행」은
      쪽 위의 행이 아니라 **체인 전체에서 바로 앞 행**이다. 그 앞 행을 못 보면
      `unknown` 이다(회색은 초록이 아니다).
    """
    items = list(payload.get("items") or ())
    if not items:
        payload["chain_states"] = {"linked": 0, "broken": 0, "unchained": 0, "unknown": 0}
        return payload

    from common import evidence_chain

    ids = [i["audit_id"] for i in items if i.get("audit_id") is not None]
    if not ids:
        return payload
    lo, hi = min(ids), max(ids)

    scanned = list(_audit_rows_queryset().filter(id__gte=lo, id__lte=hi)
                   .order_by("id").values("id", "data_after")[:_CHAIN_SCAN_CAP + 1])
    capped = len(scanned) > _CHAIN_SCAN_CAP
    scanned = scanned[:_CHAIN_SCAN_CAP]

    #: 이 쪽보다 앞에 있는 마지막 해시 — 없으면 체인의 첫 행 자리(GENESIS)다.
    anchor = evidence_chain.GENESIS
    anchor_known = True
    back = list(_audit_rows_queryset().filter(id__lt=lo).order_by("-id")
                .values("id", "data_after")[:_CHAIN_BACK_CAP + 1])
    if len(back) > _CHAIN_BACK_CAP:
        anchor_known = False
        back = back[:_CHAIN_BACK_CAP]
    for row in back:
        _, row_hash = _chain_pair(row.get("data_after"))
        if row_hash:
            anchor, anchor_known = row_hash, True
            break

    expected: dict[int, str] = {}
    running = anchor
    running_known = anchor_known
    for row in scanned:
        prev_hash, row_hash = _chain_pair(row.get("data_after"))
        expected[row["id"]] = running if running_known else ""
        if row_hash:
            running, running_known = row_hash, True
        elif prev_hash:
            #: 두 칸이 없는 행은 체인을 끊지 않는다(체인 이전 행) — 앞 해시를 그대로 잇는다.
            running_known = running_known

    stored = {row["id"]: _chain_pair(row.get("data_after")) for row in scanned}
    counts = {CHAIN_LINKED: 0, CHAIN_BROKEN: 0, CHAIN_UNCHAINED: 0, CHAIN_UNKNOWN: 0}
    for item in items:
        prev_hash, row_hash = stored.get(item.get("audit_id"), ("", ""))
        item["prev_hash"] = prev_hash
        item["hash"] = row_hash
        if capped or item.get("audit_id") not in stored:
            state = CHAIN_UNKNOWN
        elif not row_hash:
            state = CHAIN_UNCHAINED
        else:
            want = expected.get(item["audit_id"], "")
            state = (CHAIN_UNKNOWN if not want
                     else CHAIN_LINKED if prev_hash == want else CHAIN_BROKEN)
        item["chain"] = state
        counts[state] += 1
    payload["chain_states"] = counts
    payload["chain_scan_capped"] = capped
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 턴 Y — 뒷면 ③: 「대상」 칸 — **삭제된 사건을 「없음」이라고 적지 않는다** (P-208 U24 ①)
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇이 이 칸을 만들게 했나
# --------------------------
# 대표 결정으로 2026-09-19~20 에 씨앗 177행이 **지워졌다**(사건 16 + 발송 145 + 클립 16).
# 차선 S 가 그 뒤 체인을 재고 이렇게 적었다:
#
#     체인은 「이 행이 **안 고쳐졌다**」를 증명할 뿐
#     **「가리키는 대상이 아직 있다」는 증명하지 않는다.**
#
# 그 말이 옳다. 그리고 화면은 그 사실을 **한 자도 말하지 않고 있었다** — 감사 행의
# `action` 이 `upper_report:set:231073` 이라고 적혀 있어도, 그 231073 이 아직 있는지
# 지워졌는지 화면은 묻지 않았다. 묻지 않으면 사람은 **있는 것으로 읽는다.**
#
# ★★ **수는 한 건도 안 바뀐다.** `total`·`pages`·이 쪽의 행 수는 그대로다. 바뀌는 것은
#    **그 행이 가리키는 0 이 무엇인지 말하는 것**뿐이다. 이 저장소가 세 턴째 하는 일이다.
#
# ★ 갈래가 **셋**이다 — 둘로 적으면 또 거짓말이 된다
# ---------------------------------------------------
#     live                — 가리키는 사건이 아직 있다
#     deleted_by_decision — 없다 **그리고** 09-20 스냅샷에 그 id 가 있다
#                           → 「삭제된 사건 · 대표 결정 09-20 · 스냅샷 있음」
#     gone                — 없다 **그리고** 스냅샷에 없다
#                           → 「사라진 사건 · 기록된 결정 없음」  ← 회색이다. 초록이 아니다
#
#   둘로 줄여 「없으면 삭제된 것」이라고 적으면, **기록 없이 사라진 행**까지
#   「대표가 지웠다」는 근거로 읽힌다(D-280 — 모르는 칸을 그럴듯하게 채우면 그 값이
#   나중에 근거처럼 읽힌다). 우리가 증명할 수 있는 것은 **스냅샷에 적힌 id 뿐**이다.
#
# ★ 존재 여부는 **커널 문**으로 묻는다 — `services.event_detail`(남의 것이면 404).
#   여기서 표를 직접 묻지 않는다: 그러면 테넌트 좁히기가 두 벌이 되고, 남의 테넌트
#   사건의 **존재 여부가 샌다**(`get_event` 머리말 — 403 을 안 쓰는 그 이유 그대로).
#   그래서 남의 사건은 「없다」로 읽히고, 스냅샷에 없으므로 `gone` 이다 — 닫는 쪽이 기본값.

#: 대상 갈래 **넷**. 「모른다」를 지우지 않는다(체인 칸 `CHAIN_UNKNOWN` 과 같은 규율).
TARGET_LIVE = "live"
TARGET_DELETED_BY_DECISION = "deleted_by_decision"
#: ★★ [턴 AA · U24] 넷째가 늘었다 — **없는 번호를 가리킨 막힌 시도.**
#:   [실측 2026-09-21] `upper_report:set:999999999` 두 행. 결과 막힘 · HTTP 404 ·
#:   사유 「사건이 없거나 남의 테넌트다」. 999999999 는 **어느 스냅샷에도 없다.**
#:   이 두 행을 `gone`(사라진 사건 · 기록된 결정 없음)에 섞어 두면 화면이 「있던 사건이
#:   없어졌다」고 말하는 것이 되는데, 그 사건은 **처음부터 없었고 서버가 그때 막았다.**
#:   ⚠ 턴 Z 에 조율자가 이 두 행에 「삭제된 사건 · 대표 결정」을 적으라고 했고 거절했다.
#:     거절은 옳았지만 거절만으로는 행이 제 이름을 얻지 못한다 — 이 갈래가 그 이름이다.
TARGET_DENIED_ATTEMPT = "denied_attempt"
TARGET_GONE = "gone"
#: 다섯째는 **갈래가 아니라 「못 쟀다」**다 — 상한에 닿아 이 쪽에서 안 물어본 행.
#: 「모른다」를 지우지 않는다: 안 물어본 것을 `gone` 으로 적으면 **없어지지 않은 사건이
#: 사라진 것**이 되고, `live` 로 적으면 **없어진 사건이 살아 있는 것**이 된다.
TARGET_UNKNOWN = "unknown"

#: 쪽 하나에서 **커널 문을 두드리는 사건 수의 상한.**
#: [실측 2026-09-21 · 50행 한 쪽 · 서로 다른 사건 9] 질의 45 · 0.06초 — 사건 하나에
#: 약 다섯 질의다. 쪽 크기 상한은 200 이므로 상한이 없으면 한 쪽이 **질의 1,000**까지
#: 간다. 그래서 상한을 두고, **닿았다고 말한다**(`target_scan_capped` · 체인 칸의
#: `chain_scan_capped` 와 같은 규약 — 잘린 표본은 잘렸다고 말한다 · D-301).
TARGET_SCAN_MAX_EVENTS = 60

#: ★ 삭제를 집행한 **결정**과 그 **스냅샷**. 화면이 지어내는 말이 아니라 여기 적힌 사실이다.
DELETED_EVENT_DECISION = "대표 결정"
DELETED_EVENT_DECIDED_ON = "2026-09-20"
DELETED_EVENT_SNAPSHOT = "docs/agent/evidence/P-184/deleted_probe_snapshot_20260920.json"

#: ★★ 그날 지워진 **사건 id 열여섯** — 스냅샷 `events` 절의 pk 를 그대로 적는다.
#:   **수가 아니라 id 로** 적는 이유(D-285 ②): 「열여섯 건」이라고 적으면 한 건이 빠지고
#:   다른 한 건이 들어와도 수는 그대로라 아무도 모른다. 그리고 이 상수와 스냅샷 파일이
#:   갈리지 못하게 `tests/test_u24_audit_target.py` 가 **둘을 대 본다** — 파일을 요청마다
#:   읽지 않는 이유는 제품이 `docs/` 를 읽으면 안 되기 때문이다(컨테이너에 없을 수 있다).
DELETED_EVENT_IDS = frozenset({
    231073, 231074, 231075, 231076, 231077, 231078,
    268494, 268495, 268496, 268497,
    274947, 274948,
    285639, 285640, 285641, 285642,
})

#: ★★ [턴 AA · U24] **삭제는 두 번 있었다.** 대표 결정 2026-09-21 ②(「씨앗 삭제 그대로」)가
#:   사건 넷을 더 지웠고, 그 스냅샷이 따로 있다. 턴 Z 에 이 넷을 안 넣은 이유는
#:   **분모가 0** 이었기 때문이다 — 그때 화면은 `action` 한 모양만 읽었고 그 모양으로
#:   이 넷을 가리키는 행은 0 이었다. 이 턴에 `event_ref` 를 읽기 시작하면서 분모가
#:   **16 행**이 됐다 [실측 2026-09-21 · U4 테넌트]. 분모가 생겼으므로 이름을 준다.
#:   ⚠ 두 스냅샷을 **한 상수로 합치지 않는다.** 결정 날짜가 다르고, 합치면 09-21 에
#:     지워진 사건에 「대표 결정 2026-09-20」이 찍힌다 — 없던 날짜를 종이에 만드는 것이다.
DELETED_EVENT_DECIDED_ON_20260921 = "2026-09-21"
DELETED_EVENT_SNAPSHOT_20260921 = (
    "docs/agent/evidence/P-184/deleted_probe_snapshot_20260921.json")
DELETED_EVENT_IDS_20260921 = frozenset({295402, 295403, 295404, 295405})


def deleted_event_decision(event_id: int) -> tuple[str, str] | None:
    """이 사건 id 가 **어느 결정으로 지워졌나** — (결정 날짜, 스냅샷). 모르면 `None`.

    ★ 스냅샷에 적힌 id 만 답한다. 「없으면 지워진 것」으로 읽지 않는다 — 우리가 증명할
      수 있는 것은 스냅샷에 적힌 id 뿐이다(D-280).
    """
    if event_id in DELETED_EVENT_IDS:
        return DELETED_EVENT_DECIDED_ON, DELETED_EVENT_SNAPSHOT
    if event_id in DELETED_EVENT_IDS_20260921:
        return (DELETED_EVENT_DECIDED_ON_20260921,
                DELETED_EVENT_SNAPSHOT_20260921)
    return None

#: 감사 행이 사건을 가리키는 **유일한 모양** — `api_u24._upper_report_set/_clear` 가 적는다.
#: 다른 모양이 생기면 여기 늘린다. 억지로 숫자를 긁지 않는다: 아무 숫자나 사건 id 로
#: 읽으면 「설정 변경 write:inbound_api_key:rotate:7」의 7 이 사건 7 이 된다.
_TARGET_EVENT_ACTION = re.compile("^upper_report:(?:set|clear):([0-9]+)$")


def target_event_id(action: str) -> int | None:
    """감사 행의 `action` 이 가리키는 **사건 id**. 안 가리키면 `None`."""
    m = _TARGET_EVENT_ACTION.match((action or "").strip())
    return int(m.group(1)) if m else None


def row_event_id(item: dict) -> int | None:
    """감사 행 하나가 가리키는 사건 id — **축 둘을 한 답으로.**

    ★★ [턴 AA · U24] 왜 이 함수가 생겼나 — **화면이 180 행 앞에서 침묵했다.**
      [실측 2026-09-21 · U4 테넌트 2,194 행] 사건을 가리키는 행 **273** 중
      `action` 이 답하는 것은 **2** 뿐이고, 나머지 **271** 은 번호를 `action` 이 아니라
      `data_before`/`data_after` 페이로드에 든다. 그 271 을 화면이 한 자도 못 읽었다.

      · 축 ① `action` — `upper_report:set|clear:<id>` 한 모양. `api_u24` 가 적는다.
      · 축 ② `event_ref` — 페이로드의 사건 번호. `audit.read_page` 가 실어 준다
        (턴 Z · U56). 판정식은 `common/evidence_chain.event_ref_of` 하나이고
        `dangling_event_refs` 도 같은 함수를 부른다 — **화면이 세는 수와 체인이 세는
        수가 같은 자에서 나온다.**

    ★ 축 ①을 **먼저** 본다. 공짜이고(문자열 한 번) 이미 시험이 그 모양을 못 박아 뒀다
      (`TheActionShapeIsPinnedTest`). 축 ②는 **대체가 아니라 보완**이다 — ①이 답하면
      ①이 답이다.
    ⚠ 여기서 판정식을 새로 쓰지 않는다. 억지로 숫자를 긁으면 「설정 변경
      write:inbound_api_key:rotate:7」의 7 이 사건 7 이 된다.
    """
    by_action = target_event_id(item.get("action") or "")
    if by_action is not None:
        return by_action
    ref = item.get("event_ref")
    try:
        return int(ref) if ref is not None else None
    except (TypeError, ValueError):
        return None


def _resolve_event_target(event_id: int, *, scope: TenantScope) -> str:
    from django.http import Http404

    from apps.dsm import services

    try:
        services.event_detail(scope=scope, event_id=event_id)
    except Http404:
        return (TARGET_DELETED_BY_DECISION
                if deleted_event_decision(event_id) is not None else TARGET_GONE)
    return TARGET_LIVE


def _is_denied_attempt(item: dict) -> bool:
    """이 **행 자신**이 막혔는가 — 없는 번호를 가리킨 시도인가.

    ★ 추측이 아니라 **행에 적힌 사실**이다: 결과가 「막힘」이고 서버가 그때 404 를 냈다.
      즉 그 사건은 **그 시각에 이미 없었다** — 나중에 사라진 것이 아니다.
      [실측 2026-09-21] 이 모양의 행은 둘이고 둘 다 `upper_report:set:999999999` 다.
    ⚠ 결과만으로는 안 된다(막힘에는 권한 거절도 있다) · 404 만으로도 안 된다.
      **둘이 같이** 참일 때만 이 이름을 준다.
    """
    from apps.dsm import audit

    return (item.get("outcome") == audit.DENIED
            and item.get("status_http") == 404)


def _with_target_column(payload: dict, *, scope: TenantScope) -> dict:
    """쪽 하나에 `target` 칸과 **분모(`target_states`)** 를 더한다.

    ★ **분모를 같이 낸다.** `deleted_by_decision` 이 0 건인 쪽에서 「삭제된 사건을
      제대로 적는다」고 말하면 그것은 **분모 0 인 초록**이다. 네 갈래의 수를 같이 내서
      보는 사람이 「이 쪽에는 그런 행이 없었다」를 읽을 수 있게 한다(D-301).
    ★ 같은 사건 id 는 **한 번만 묻는다** — 쪽 하나에 같은 사건 행이 여럿 있을 수 있고,
      그때마다 커널 문을 두드리면 쪽 하나가 쪽 수만큼 질의를 낸다.
    """
    items = list(payload.get("items") or ())
    counts = {"none": 0, TARGET_LIVE: 0, TARGET_DELETED_BY_DECISION: 0,
              TARGET_DENIED_ATTEMPT: 0, TARGET_GONE: 0, TARGET_UNKNOWN: 0}
    seen: dict[int, str] = {}
    capped = False
    for item in items:
        #: ★ [턴 AA] `action` 한 모양이 아니라 **축 둘**을 본다 — 271 행이 여기서 말을 얻는다.
        event_id = row_event_id(item)
        if event_id is None:
            item["target"] = None
            counts["none"] += 1
            continue
        state = seen.get(event_id)
        if state is None:
            if len(seen) >= TARGET_SCAN_MAX_EVENTS:
                #: 상한에 닿았다 — **안 물어본다. 그리고 안 물어봤다고 적는다.**
                capped = True
                state = TARGET_UNKNOWN
            else:
                state = _resolve_event_target(event_id, scope=scope)
            seen[event_id] = state
        #: ★ 「없다」의 갈래를 하나 더 가른다. **행 자신이 그때 막혔으면** 그 사건은
        #:   나중에 사라진 것이 아니라 **처음부터 없었다.** 사건 단위 판정(`seen`)에
        #:   섞지 않는 이유가 이것이다 — 이것은 **행의 사실**이다.
        if state == TARGET_GONE and _is_denied_attempt(item):
            state = TARGET_DENIED_ATTEMPT
        decision = (deleted_event_decision(event_id)
                    if state == TARGET_DELETED_BY_DECISION else None)
        item["target"] = {
            "kind": "event",
            "event_id": event_id,
            "state": state,
            #: 이 행이 사건 번호를 **어디서** 얻었나. 화면은 안 그리지만 CSV 와 시험이
            #: 이 칸으로 「축 ②가 실제로 일하고 있는가」를 분모와 함께 읽는다.
            "via": "action" if target_event_id(item.get("action") or "") is not None
                   else "payload",
            #: 결정·스냅샷은 **삭제로 판정한 행에만** 적는다. 아무 행에나 붙이면
            #: 「대표가 지웠다」가 모든 행의 배경 소음이 된다.
            "decision": DELETED_EVENT_DECISION if decision else None,
            "decided_on": decision[0] if decision else None,
            "snapshot": decision[1] if decision else None,
        }
        counts[state] += 1
    payload["target_states"] = counts
    #: 닿았는가를 **언제나** 낸다(거짓일 때도). 칸이 있을 때만 나오면 화면은
    #: 「이 서버는 그 사실을 모른다」와 「안 닿았다」를 못 가른다.
    payload["target_scan_capped"] = capped
    return payload


#: CSV 의 칸 이름. 화면 표의 열과 **같은 순서**다 — 다르면 사람이 두 장을 대조할 수 없다.
_AUDIT_CSV_HEADER = ("audit_id", "at", "outcome", "action", "method", "actor_id",
                     "actor", "reason", "status_http", "channel", "prev_hash",
                     "hash", "chain", "target_event_id", "target_state")
#: CSV 한 장의 상한. 넘으면 **마지막 줄에 적는다**(잘린 표본은 잘렸다고 말한다 · D-301).
_AUDIT_CSV_CAP = 5000


def _csv_cell(row: dict, key: str):
    """CSV 한 칸. `target_*` 두 칸은 `target` dict 안에서 꺼낸다 — 파일과 화면이
    **같은 사실**을 말해야 하므로 화면에 생긴 열은 파일에도 선다."""
    if key in ("target_event_id", "target_state"):
        target = row.get("target")
        if not isinstance(target, dict):
            return ""
        return target.get("event_id" if key == "target_event_id" else "state") or ""
    value = row.get(key, "")
    return "" if value is None else value


def _audit_csv(*, scope, since, until, actor_id, action, limit: int, reader) -> str:
    """감사 CSV 한 장 — **화면과 같은 함수**(`audit.read_page`)가 낸 쪽들을 잇는다.

    다른 질의를 새로 짜지 않는 것이 요점이다: 파일이 표와 다른 사실을 말하면 둘 중
    어느 쪽이 맞는지 아무도 모른다.
    """
    import csv
    import io

    from apps.dsm import stats

    limit = max(1, min(int(limit or 1000), _AUDIT_CSV_CAP))
    page_size = 200
    rows: list[dict] = []
    page = 1
    total = 0
    while len(rows) < limit:
        payload = reader(scope=scope, since=since, until=until, actor_id=actor_id,
                         action=action, page=page, page_size=page_size)
        total = payload.get("total", 0)
        chunk = _with_target_column(_with_chain_columns(payload),
                                    scope=scope).get("items") or []
        if not chunk:
            break
        rows.extend(chunk)
        if page >= (payload.get("pages") or 1):
            break
        page += 1
    capped = len(rows) > limit or total > limit
    rows = rows[:limit]

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(_AUDIT_CSV_HEADER)
    for r in rows:
        writer.writerow([_csv_cell(r, k) for k in _AUDIT_CSV_HEADER])
    #: ★ 꼬리 줄의 길이를 **머리글에서 센다.** 턴 U 에는 빈 칸 열셋이 손으로 박혀 있었고,
    #:   그래서 열이 하나 늘 때마다 꼬리 줄만 조용히 짧아졌다 — 표 계산기에서 마지막
    #:   칸이 밀려 「잘림」이 엉뚱한 열에 선다.
    tail = ["# 전체", total, "이 파일", len(rows), "", "잘림" if capped else "전부"]
    writer.writerow(tail + [""] * (len(_AUDIT_CSV_HEADER) - len(tail)))
    return stats.CSV_BOM + buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# 턴 U — 뒷면 ②: 보고서 서식 3 · 파일 2
# ═══════════════════════════════════════════════════════════════════════════
def _report_reader_denial(user) -> str | None:
    """보고서를 만들고 내려받을 수 있는 사람 — **U2 · U4** + 테넌트·전역 관리자.

    ★ 판정식을 새로 쓰지 않는다 — 감사 읽기(`_audit_reader_denial`)와 같은 표
      (`config.k3_roles` · `common.tenant_roles` · `common.role_gate`)를 읽는다.
      U5(운영자)도 든다: 배치가 낸 자동본의 실패 사유를 볼 사람이 운영자이기 때문이다.
    """
    denial = _audit_reader_denial(user)
    if denial is None:
        return None
    return "보고서는 관제팀장 · 지자체 담당관 · 운영자만 만들고 내려받을 수 있습니다."


def _report_file(request, *, run_id: int, fmt: str):
    """`.docx` · `.pdf` 공통 뒷면 — 실행 기록에서 **지금 다시 그려** 파일로 낸다.

    상태를 뭉치지 않는다(`api.py::event_report_pdf` 와 같은 규약):
        401 인증 없음 · 403 볼 수 없는 역할 · 404 없는/남의 실행 기록(또는 그 사건) ·
        409 기록은 있는데 지금 만들 수 없다(실패 행 · 자료 없음 · 렌더 실패)
    """
    from urllib.parse import quote

    from django.http import Http404, HttpResponse

    from kernels.k4_report import InvalidReportInput, RenderFailed

    from apps.dsm import docx_export, monthly_report
    from apps.dsm.exceptions import IncidentReportUnavailable

    scope = _scope(request)
    denial = _report_reader_denial(scope.actor)
    if denial:
        raise HttpError(403, denial)
    try:
        run = monthly_report.get_run(scope=scope, run_id=run_id)
    except Http404:
        raise HttpError(404, "그런 보고서 실행 기록이 없습니다.")
    try:
        data = monthly_report.render_run(scope=scope, run=run, fmt=fmt)
    except Http404:
        raise HttpError(404, "그 사건을 읽을 수 없습니다 — 보고서를 만들 수 없습니다.")
    except (monthly_report.ReportRunError, IncidentReportUnavailable,
            docx_export.DocxRenderFailed, RenderFailed, InvalidReportInput) as exc:
        raise HttpError(409, f"지금은 보고서를 만들 수 없습니다 — {exc}")

    content_type, ext = monthly_report.FORMATS[fmt]
    name = f"{monthly_report.KIND_LABEL.get(run.kind, '보고서')}-{run_id}.{ext}"
    response = HttpResponse(data, content_type=content_type)
    #: 이름을 두 벌로 낸다 — `filename*` 이 없으면 한글 이름이 깨지고, `filename` 만
    #: 없으면 옛 브라우저가 이름을 못 읽는다(`event_report_pdf` 와 같은 자리).
    response["Content-Disposition"] = (
        f'attachment; filename="guardianx-report-{run_id}.{ext}"; '
        f"filename*=UTF-8''{quote(name)}")
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response["X-Content-Type-Options"] = "nosniff"
    return response
