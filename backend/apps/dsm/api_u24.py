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
