# -*- coding: utf-8 -*-
"""구역 판정 — **카메라 묶음은 지금 돌고, 폴리곤은 선언된 미완성이다** (D-299).

한 문장
-------
    "같은 구역인가" 를 지금 답할 수 있는 방식으로 답하고, **답할 수 없는 방식은
    답하는 척하지 않는다.**

무엇이 있고 무엇이 없나 (D-300 부작위 시험 대상)
------------------------------------------------
    있다  · `same_zone`           — 두 카메라가 한 구역에 있는가 (camera_group)
          · `zones_for_camera`    — 그 카메라가 속한 활성 구역들
          · `combine_in_zone`     — F-03 결합 판정. **등급 상향값을 돌려준다**
          · `ZONE_POLYGON_READY`  — 폴리곤 판정의 잠금 상수

    없다  · 폴리곤 판정 알고리즘(point-in-polygon) · 좌표계 변환 · GIS 의존
          · 구역 편집 API·화면 — 구역을 **만드는** 면은 이번 범위가 아니다
          · `DetectionEvent.severity` 를 덮어쓰는 쓰기 — 아래 `combine_in_zone` 참조

왜 `ZONE_POLYGON_READY` 인가 — SDN 에서 쓴 `KERNEL_READY` 패턴을 그대로 재사용한다
----------------------------------------------------------------------------------
`adapters/sdn/__init__.py` 가 세운 규약이 정확히 이 문제를 푼다:

    · 잠긴 기능은 **상수로 잠근다.**
    · 사유(`..._NOT_READY_REASON`)가 비면 **게이트가 exit 1.**
    · 상수를 True 로 올리는 순간 **그 기능의 계약 AC 시험이 의무가 된다.**

그래서 폴리곤은 "언젠가 하겠다"는 문서가 아니라 **선언된 미완성**이다. 올리면 시험이
따라오고, 안 올리면 사유가 남는다. 어느 방향으로도 조용할 수 없다.

★ 반대 방향도 잠근다 — **데이터가 상수를 앞지르는 것**
`geometry_status='ready'` 인 Zone 이 하나라도 있는데 상수가 False 면, 화면·판정은
폴리곤을 쓴다고 믿는데 코드는 미구현인 상태다. 그 어긋남을 `scripts/verify_zone_polygon.py`
(정적)와 `backend/tests/test_zone_judgment.py`(DB)가 양쪽에서 잡는다.

E2E-2 해금
----------
`tests/e2e/e2e_contract.KERNEL_PACKAGES["ZONE"]` 이 이 모듈을 가리킨다. `KERNEL_READY`
가 True 이므로 E2E-2 의 3단계가 **열린다** — 열리는 것은 카메라 묶음 판정 하나이고,
폴리곤은 위 상수로 여전히 잠겨 있다. 두 잠금이 다른 것을 잠근다.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.apps import apps

from common.tenant_scope import TenantScope

#: ★ 이 모듈이 **잴 수 있는 상태인가** — E2E 등재부(`kernel_present`)가 이것을 본다.
#:   카메라 묶음 판정은 실재하므로 True 다. 폴리곤은 아래 별도 상수로 잠근다 —
#:   둘을 한 상수에 두면 "구역이 된다"와 "폴리곤이 된다"가 한 칸에 섞이고,
#:   그러면 카메라 묶음이 초록일 때 폴리곤까지 초록으로 읽힌다 (E2E-1 8·9단계와 같은 이유).
KERNEL_READY: bool = True

#: ★ 폴리곤 판정의 잠금. **False 인 동안 폴리곤 Zone 을 부르면 멈춘다.**
#:
#:   올리는 조건은 둘이다:
#:     ① `_point_in_polygon` 이 실재할 것 (지금은 없다)
#:     ② F-03 폴리곤 계약 AC 시험이 실재할 것 —
#:        `backend/tests/test_zone_judgment.py::test_f03_polygon_contract_ac`
#:   ②가 없는데 올리면 `scripts/verify_zone_polygon.py` 가 exit 1 한다.
#:   추측이 계약이 되는 것이 아니라, **선언된 미완성**이 된다.
ZONE_POLYGON_READY: bool = False

#: ★ `ZONE_POLYGON_READY=False` 일 때 **반드시 채워져 있어야 한다.** 비면 게이트가 exit 1.
#:   "안 됐다" 를 사유 없이 적는 것은 D-264(모르면 멈춘다)가 금지한 모양이다.
ZONE_POLYGON_NOT_READY_REASON: str = (
    "폴리곤 판정을 구현하지 않았다. 좌표 표현(GeoJSON 인지 좌표쌍 배열인지)과 좌표계"
    "(WGS84 인지 TM 인지)가 아직 정해지지 않았고, 지금 한쪽을 골라 넣으면 그 선택이 곧 "
    "F-03 의 계약이 된다(D-280). 계약 F-03 AC 는 '지정 위험구역(폴리곤) 내 사람·차량 "
    "진입' 이므로 최종적으로는 폴리곤이 필요하며, 그때까지 이 자리는 비운 채 "
    "kind='camera_group' 으로 같은 질문에 답한다(D-299). "
    "해소는 F-03 설계(좌표 표현·좌표계·구역 편집 화면) 확정이지 이 파일의 수정이 아니다."
)

#: F-03 결합의 상향 등급. **계약이 정한 값이 아니라 이 규칙의 값이다.**
#: 계약 [별첨1] 은 "등급 상향" 이라고만 적었고 목표 등급을 숫자로 적지 않았다.
#: 그래서 여기 한 곳에만 두고 이름을 붙인다 — 여러 곳에 흩으면 그 값이 조용히 갈린다.
ESCALATED_SEVERITY: str = "critical"


def _zone_model():
    return apps.get_model("stream_monitors", "Zone")


def _scoped(qs, scope: TenantScope):
    """스코프로 좁힌다. 시스템 스코프는 좁히지 않되 **사유를 이미 낸 상태**다 (D-281).

    사람이 부른 경우에만 group 으로 거른다 — 파이프라인에는 요청자가 없어
    무엇을 기준으로 걸러야 할지 모르기 때문이다. `k1_event.services` 와 같은 판단이다.
    """
    if scope.is_system:
        return qs
    from common.tenant_filters import (_guess_group_lookup, get_user_group,
                                       is_global_admin)

    if is_global_admin(scope.actor):
        return qs
    group = get_user_group(scope.actor)
    if group is None:
        # 소속이 없는 사람에게는 **아무 구역도 없다.** 전체를 돌려주면 그 순간
        # 소속 없음이 전권이 된다 — §0.4 의 created_by__isnull OR 절과 같은 함정이다.
        return qs.none()
    return qs.filter(**{_guess_group_lookup(qs.model): group})


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — 미구현을 정직하게 던진다 (D-284)
# ═══════════════════════════════════════════════════════════════════════════
def contains(zone, *, camera_id: int | None = None,
             lat: float | None = None, lng: float | None = None) -> bool:
    """이 구역이 그 관측을 품는가.

    카메라 묶음이면 **묶음에 그 카메라가 있는가** 하나로 답한다. 폴리곤이면 답하지
    않고 멈춘다 — 조용히 False 를 돌려주면 "구역 밖이다" 와 "판정 못 한다" 가 같은
    값이 되고, 그러면 미구현이 정상 판정으로 위장한다 (D-284 · D-290).
    """
    Zone = _zone_model()
    if zone.kind == Zone.Kind.CAMERA_GROUP:
        if camera_id is None:
            raise ValueError(
                "camera_group 구역 판정에는 camera_id 가 필요하다 — 좌표만으로는 "
                "이 종류의 구역이 답할 수 있는 질문이 아니다")
        return zone.cameras.filter(pk=camera_id).exists()

    if zone.geometry_status != Zone.GeometryStatus.READY or not ZONE_POLYGON_READY:
        raise NotImplementedError(
            f"폴리곤 판정 미구현 — 계약 F-03 AC 대상. {ZONE_POLYGON_NOT_READY_REASON}")
    # 여기 아래는 ZONE_POLYGON_READY 를 True 로 올리는 사람이 채운다.
    # 지금 자리만 만들어 두고 알고리즘을 적지 않는 이유는 위 사유 그대로다 (D-280).
    raise NotImplementedError(
        "ZONE_POLYGON_READY 가 True 인데 point-in-polygon 구현이 없다 — "
        "상수만 올리고 구현을 안 올린 상태다")


def zones_for_camera(camera_id: int, *, scope: TenantScope) -> list:
    """그 카메라가 속한 **활성 카메라묶음 구역**들. 순서는 모델 기본 정렬이다."""
    Zone = _zone_model()
    qs = _zone_model().objects.filter(
        kind=Zone.Kind.CAMERA_GROUP, is_active=True, cameras__pk=camera_id)
    return list(_scoped(qs, scope).distinct())


def same_zone(camera_a: int, camera_b: int, *, scope: TenantScope):
    """두 카메라가 **한 구역에 함께** 있는가. 있으면 그 구역, 없으면 `None`.

    같은 카메라를 두 번 물으면 `None` 이다 — F-03 이 묻는 것은 *서로 다른* 관측 둘이
    같은 구역에서 났는가이고, 자기 자신과의 결합은 그 질문이 아니다.
    """
    if camera_a == camera_b:
        return None
    a = {z.pk: z for z in zones_for_camera(camera_a, scope=scope)}
    for zone in zones_for_camera(camera_b, scope=scope):
        if zone.pk in a:
            return a[zone.pk]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# F-03 결합 — **값을 돌려주고, 저장된 등급을 덮지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class ZoneCombination:
    """같은 구역에서 난 관측 둘이 하나로 읽혀야 한다는 판정.

    ★ 왜 값인가 — **저장된 `severity` 를 덮어쓰지 않는다.**
      덮어쓰려면 K1 공개 면에 일곱 번째 함수가 필요하고, DA-04 §2 는 K1 의 공개 면을
      여섯으로 고정했다. 계약이 정한 면을 이 규칙 하나 때문에 조용히 넓히지 않는다.
      그리고 관측이 실제로 난 등급(`warning`)은 오탐률·이력의 사실이므로, 결합 판정이
      그 사실을 덮으면 나중에 "무엇이 실제로 났는가" 를 아무도 못 읽는다 (D-293 과 같은 계열).

      결합의 결과는 **누가 받는가**로 나타난다 — `resolve_recipients(severity=...)` 에
      이 값을 넣으면 수신자가 실제로 갈린다. 그것이 F-03 이 요구하는 효과다.
    """

    #: 결합의 근거가 된 구역
    zone_id: int
    zone_name: str
    #: 결합된 두 관측
    event_ids: tuple[int, int]
    #: 상향된 등급. 이 값으로 수신자를 다시 고른다.
    severity: str
    #: 무엇과 무엇이 만났는가 — 알림 본문·감사 기록에 그대로 쓴다
    reason: str


def combine_in_zone(*, scope: TenantScope, primary, secondary) -> ZoneCombination | None:
    """F-03 — **같은 구역에서 난 두 관측을 결합하고 등급을 올린다.**

    `primary` · `secondary` 는 K1 의 `EventView` 다. 모델이 아니라 커널의 값을 받는다 —
    모델을 받으면 이 함수를 부르는 쪽이 커널 내부를 알아야 하고, 그 순간 DA-04 §1-4 가
    끊어 둔 경계가 무너진다.

    결합되지 않으면 `None` 이다. **거짓 결합을 만들지 않는다** — 구역이 없으면 없는 것이다.
    """
    zone = same_zone(primary.stream_monitor_id, secondary.stream_monitor_id, scope=scope)
    if zone is None:
        return None
    return ZoneCombination(
        zone_id=zone.pk,
        zone_name=zone.name,
        event_ids=(primary.event_id, secondary.event_id),
        severity=ESCALATED_SEVERITY,
        reason=(f"구역 '{zone.name}' 에서 {primary.event_type} 관측과 "
                f"{secondary.event_type} 관측이 함께 났다 — F-03 결합"),
    )


def is_polygon_ready() -> bool:
    """폴리곤 판정이 **잴 수 있는 상태인가.** 선언과 데이터를 함께 보지 않는다 —
    데이터 쪽 대조는 DB 가 필요하므로 `tests/test_zone_judgment.py` 가 한다."""
    return ZONE_POLYGON_READY


__all__ = [
    "KERNEL_READY",
    "ZONE_POLYGON_READY",
    "ZONE_POLYGON_NOT_READY_REASON",
    "ESCALATED_SEVERITY",
    "ZoneCombination",
    "contains",
    "zones_for_camera",
    "same_zone",
    "combine_in_zone",
    "is_polygon_ready",
]
