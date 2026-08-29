# -*- coding: utf-8 -*-
"""구역 판정 — **카메라 묶음과 폴리곤, 둘 다 돈다** (D-299 · D-365).

한 문장
-------
    "그 관측이 이 구역 안인가" 를 두 방식으로 답한다. 답할 수 없는 상태는
    **답하는 척하지 않고 멈춘다.**

무엇이 있고 무엇이 없나 (D-300 부작위 시험 대상)
------------------------------------------------
    있다  · `same_zone`           — 두 카메라가 한 구역에 있는가 (camera_group)
          · `zones_for_camera`    — 그 카메라가 속한 활성 구역들
          · `combine_in_zone`     — F-03 결합 판정. **등급 상향값을 돌려준다**
          · `contains` · `point_in_zone` — 폴리곤 판정 (**2026-09-10 열렸다** · D-365)
          · `InvalidPolygon`      — 그린 것이 잘못됐을 때. 조용한 False 가 아니다
          · `save_zone` · `list_zones` — 구역 편집 면 (**2026-09-10 열렸다** · D-366)

    없다  · 구멍(내부 고리) · MultiPolygon · 좌표계 변환 · GIS 의존
          · 고도(3차원) 판정 — 계약 F-03 이 부르지 않는다
          · `DetectionEvent.severity` 를 덮어쓰는 쓰기 — 아래 `combine_in_zone` 참조

★ 안 그린 것과 잘못 그린 것을 가른다 (D-365)
--------------------------------------------
    `geometry_status != 'ready'`  → `NotImplementedError`  **아직 안 그렸다**
    도형이 폴리곤이 아니다        → `InvalidPolygon`        **잘못 그렸다**
한 예외로 뭉치면 운영자는 "언젠가 되겠지" 와 "내가 지금 고쳐야 한다" 를 구별하지 못한다.

왜 `ZONE_POLYGON_READY` 인가 — SDN 에서 쓴 `KERNEL_READY` 패턴을 그대로 재사용한다
----------------------------------------------------------------------------------
`adapters/sdn/__init__.py` 가 세운 규약이 정확히 이 문제를 푼다:

    · 잠긴 기능은 **상수로 잠근다.**
    · 사유(`..._NOT_READY_REASON`)가 비면 **게이트가 exit 1.**
    · 상수를 True 로 올리는 순간 **그 기능의 계약 AC 시험이 의무가 된다.**

★ 그 규약이 이번에 **값을 냈다.** 상수를 올리자 `verify_zone_polygon.py` 가
  `test_f03_polygon_contract_ac` 를 요구했고, 구현만 올리고 시험을 안 낼 길이 없었다.
  선언된 미완성은 "언젠가 하겠다"는 문서가 아니라 **해소될 때 값을 받는 장치**다.

★ 반대 방향도 잠근다 — **데이터가 상수를 앞지르는 것**
`geometry_status='ready'` 인 Zone 이 하나라도 있는데 상수가 False 면, 화면·판정은
폴리곤을 쓴다고 믿는데 코드는 미구현인 상태다. 그 어긋남을 `scripts/verify_zone_polygon.py`
(정적)와 `backend/tests/test_zone_judgment.py`(DB)가 양쪽에서 잡는다.

E2E-2 해금
----------
`tests/e2e/e2e_contract.KERNEL_PACKAGES["ZONE"]` 이 이 모듈을 가리킨다. `KERNEL_READY`
가 True 이므로 E2E-2 의 3단계가 **열린다** — 그 단계가 재는 것은 카메라 묶음 결합이고,
폴리곤 판정은 별개의 시험이 잰다. 두 잠금이 다른 것을 잠갔고, 이제 둘 다 열렸다.
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

#: ★ 폴리곤 판정의 잠금. **2026-09-10 올렸다** (D-365 · 지시 D-360 ②).
#:
#:   올린 조건 둘을 함께 채웠다:
#:     ① `_point_in_polygon` 이 실재한다 — 아래 순수 함수
#:     ② F-03 폴리곤 계약 AC 시험이 실재한다 —
#:        `backend/tests/test_zone_judgment.py::test_f03_polygon_contract_ac`
#:   둘 중 하나만 올리면 `scripts/verify_zone_polygon.py` 가 exit 1 한다.
#:   ★ 올리는 순간 그 시험이 **의무**가 된다 — 그것이 이 상수 규약의 요점이다(D-299).
ZONE_POLYGON_READY: bool = True

#: ★ `ZONE_POLYGON_READY=False` 일 때 **반드시 채워져 있어야 한다.** 비면 게이트가 exit 1.
#:   지금은 True 이므로 사유가 쓰이지 않는다. **지우지 않는다** — 되돌리는 날
#:   사유 없이 되돌릴 수 있게 되면 그 되돌림이 조용해진다(D-264).
ZONE_POLYGON_NOT_READY_REASON: str = (
    "폴리곤 판정을 구현하지 않았다. 좌표 표현(GeoJSON 인지 좌표쌍 배열인지)과 좌표계"
    "(WGS84 인지 TM 인지)가 아직 정해지지 않았고, 지금 한쪽을 골라 넣으면 그 선택이 곧 "
    "F-03 의 계약이 된다(D-280). 계약 F-03 AC 는 '지정 위험구역(폴리곤) 내 사람·차량 "
    "진입' 이므로 최종적으로는 폴리곤이 필요하며, 그때까지 이 자리는 비운 채 "
    "kind='camera_group' 으로 같은 질문에 답한다(D-299). "
    "해소는 F-03 설계(좌표 표현·좌표계·구역 편집 화면) 확정이지 이 파일의 수정이 아니다."
)

# ═══════════════════════════════════════════════════════════════════════════
# ★ 좌표 표현·좌표계 — **여기서 한 번 고른다. 이 선택이 곧 F-03 의 계약이다** (D-365)
# ═══════════════════════════════════════════════════════════════════════════
#
# D-280 이 미뤄 둔 그 선택을 이번 턴에 한다(지시 D-360 ②). 미룬 이유가 사라져서가
# 아니라 **미루는 값보다 갚을 절의 값이 커져서**다. 그러므로 고른 것을 고른 자리에
# 적는다 — 흩어 두면 다음 사람이 다른 것을 고르고, 두 선택이 한 필드를 쓴다.
#
#   표현    GeoJSON Polygon 의 **부분집합** (RFC 7946)
#           {"type": "Polygon", "coordinates": [[[경도, 위도], ...]]}
#           · 바깥 고리 **하나만** 받는다. 구멍(내부 고리)은 받지 않는다 —
#             계약 F-03 이 부르는 것은 "지정 위험구역" 하나이고, 구멍이 필요한 현장을
#             아직 못 봤다. 안 본 것을 지금 만들면 그 구멍이 곧 계약이 된다(D-280).
#           · 왜 GeoJSON 인가: 구역을 그리는 쪽(지도 화면·QGIS·에스비 SDN 좌표)이
#             전부 이 모양으로 낸다. 우리 고유 표현을 만들면 **변환기가 하나 생기고**,
#             변환기는 조용히 좌표를 뒤집는다.
#
#   좌표계  **WGS84** (위경도, 도 단위). GeoJSON 이 규격으로 못박은 것이 이것이다.
#           · 국내 TM(중부원점 등)을 쓰지 않는 이유: 카메라·드론이 내는 좌표가 위경도이고,
#             TM 으로 받으면 우리가 투영을 해야 한다. 투영은 GIS 의존을 부른다.
#           · **평면으로 판정한다.** 구역 하나가 수 km 규모이므로 이 축척에서 측지선과
#             직선의 차이는 판정을 뒤집지 않는다. 대륙 규모 구역은 이 함수의 범위 밖이고,
#             그 요구가 오면 그때 다시 고른다 — 지금 미리 만들지 않는다.
#
#   ★ 순서   `[경도, 위도]` — GeoJSON 순서다. **`[위도, 경도]` 가 아니다.**
#            이 한 줄이 이 모듈에서 가장 자주 틀릴 자리이므로 이름으로 못박는다.
LON, LAT = 0, 1

#: 좌표계 이름. 문자열로 **한 곳에만** 둔다 — 화면·API·보고서가 이것을 인용한다.
ZONE_CRS: str = "WGS84"

#: 경계 위의 점은 **안에 있다**. 「밖」이 아니라 「안」으로 정한 이유:
#: 위험구역 판정에서 경계에 선 사람을 밖으로 세면 **놓친다.** 재난안전에서
#: 두 오류는 값이 다르다 — 헛경보는 사람이 지우고, 놓친 것은 아무도 모른다.
BOUNDARY_IS_INSIDE: bool = True

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
# 폴리곤 — **순수 함수 셋.** DB 도 Django 도 모른다 (D-365)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 순수 함수인가: 판정이 모델에 붙어 있으면 경계 사례를 시험하려고 매번 행을 만들어야
# 하고, 그러면 **경계를 적게 시험하게 된다.** 꼭짓점·변·오목·자기교차는 DB 없이 잰다.


class InvalidPolygon(ValueError):
    """폴리곤이 폴리곤이 아니다. **판정하지 않고 멈춘다.**

    조용히 False 를 돌려주면 「밖이다」와 「이 도형은 판정할 수 없다」가 같은 값이 되고,
    잘못 그려진 구역이 **영원히 아무도 안 잡히는 구역**이 된다 (D-284 · D-290).
    """


def _ring(geometry) -> list[tuple[float, float]]:
    """GeoJSON Polygon 에서 **바깥 고리**를 꺼낸다. 아니면 `InvalidPolygon`.

    받는 모양을 넓게 잡지 않는다 — "이것도 받아 주자" 가 쌓이면 무엇이 계약인지
    아무도 못 읽고, 읽을 수 없는 계약은 지킬 수도 없다.
    """
    if not isinstance(geometry, dict):
        raise InvalidPolygon(
            f"폴리곤은 GeoJSON 객체여야 한다 — 받은 것은 {type(geometry).__name__} 다. "
            f'모양: {{"type": "Polygon", "coordinates": [[[경도, 위도], ...]]}}')
    if geometry.get("type") != "Polygon":
        raise InvalidPolygon(
            f"type 이 {geometry.get('type')!r} 다 — 이 판정기가 아는 것은 'Polygon' 하나다. "
            f"MultiPolygon·구멍(내부 고리)은 아직 범위가 아니다(D-365)")

    rings = geometry.get("coordinates")
    if not isinstance(rings, (list, tuple)) or not rings:
        raise InvalidPolygon("coordinates 가 비었다 — 고리 없는 폴리곤은 도형이 아니다")
    if len(rings) > 1:
        # 구멍을 조용히 무시하면 **구멍 안이 구역 안으로 판정된다.** 무시하지 않는다.
        raise InvalidPolygon(
            f"고리가 {len(rings)}개다 — 구멍(내부 고리)은 받지 않는다. 무시하고 바깥만 "
            f"쓰면 구멍 안이 '구역 안'으로 판정되고, 그 오판은 화면에 안 보인다(D-365)")

    raw = rings[0]
    if not isinstance(raw, (list, tuple)):
        raise InvalidPolygon("고리가 좌표 배열이 아니다")

    points: list[tuple[float, float]] = []
    for i, pair in enumerate(raw):
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            raise InvalidPolygon(f"{i}번 좌표가 [경도, 위도] 쌍이 아니다: {pair!r}")
        try:
            lon, lat = float(pair[LON]), float(pair[LAT])
        except (TypeError, ValueError) as exc:
            raise InvalidPolygon(f"{i}번 좌표가 수가 아니다: {pair!r}") from exc
        # ★ 범위를 여기서 본다. 위경도가 뒤집혀 들어오는 것이 이 모듈에서 가장 흔한
        #   사고이고, 대부분 위도 127 같은 값으로 드러난다 — 그때 잡아야 잡힌다.
        if not (-180.0 <= lon <= 180.0):
            raise InvalidPolygon(
                f"{i}번 경도가 {lon} 다 — 범위 밖이다. [경도, 위도] 순서인지 확인하라 "
                f"({ZONE_CRS} · GeoJSON 순서는 위경도가 아니라 **경위도**다)")
        if not (-90.0 <= lat <= 90.0):
            raise InvalidPolygon(
                f"{i}번 위도가 {lat} 다 — 범위 밖이다. [경도, 위도] 순서인지 확인하라 "
                f"({ZONE_CRS} · GeoJSON 순서는 위경도가 아니라 **경위도**다)")
        points.append((lon, lat))

    # 닫는 점(첫 점과 같은 마지막 점)은 GeoJSON 규격이 요구하지만 판정에는 군더더기다.
    # 있으면 떼고, 없다고 거절하지 않는다 — 화면이 안 닫고 보내는 일이 흔하다.
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]

    if len(points) < 3:
        raise InvalidPolygon(
            f"서로 다른 꼭짓점이 {len(points)}개다 — 셋이 안 되면 넓이가 없고, "
            f"넓이 없는 도형에는 '안'이 없다")
    return points


def _on_segment(px: float, py: float, ax: float, ay: float,
                bx: float, by: float) -> bool:
    """점이 선분 AB **위**에 있는가. 꼭짓점 위도 여기에 걸린다(A 또는 B 와 같은 점).

    외적이 0(일직선)이고 **선분의 상자 안**이어야 한다. 상자를 안 보면 AB 를 무한히
    늘린 직선 위의 점까지 「변 위」가 된다.
    """
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > _EPS:
        return False
    return (min(ax, bx) - _EPS <= px <= max(ax, bx) + _EPS
            and min(ay, by) - _EPS <= py <= max(ay, by) + _EPS)


#: 부동소수 비교의 허용치. 위경도 **도** 단위이므로 1e-12도 ≈ 0.1μm — 좌표 잡음보다
#: 훨씬 작다. 0 으로 비교하면 같은 점을 다르다고 하고, 크게 잡으면 다른 점을 같다고 한다.
_EPS: float = 1e-12


def _segments_properly_cross(a, b, c, d) -> bool:
    """선분 AB 와 CD 가 **가로지르는가.** 끝점을 공유하는 것은 교차가 아니다.

    자기교차 판정에 쓴다. 이웃한 두 변은 언제나 꼭짓점 하나를 공유하므로 그것을
    교차로 세면 **모든 폴리곤이 자기교차**가 된다.
    """
    def side(p, q, r) -> float:
        return (q[LON] - p[LON]) * (r[LAT] - p[LAT]) - (q[LAT] - p[LAT]) * (r[LON] - p[LON])

    d1, d2 = side(a, b, c), side(a, b, d)
    d3, d4 = side(c, d, a), side(c, d, b)
    if ((d1 > _EPS and d2 < -_EPS) or (d1 < -_EPS and d2 > _EPS)) and \
       ((d3 > _EPS and d4 < -_EPS) or (d3 < -_EPS and d4 > _EPS)):
        return True
    # 일직선으로 겹쳐 지나가는 경우 — 끝점 공유가 아닌 겹침도 자기교차다.
    for p, (s, t) in ((c, (a, b)), (d, (a, b)), (a, (c, d)), (b, (c, d))):
        if p in (s, t):
            continue
        if _on_segment(p[LON], p[LAT], s[LON], s[LAT], t[LON], t[LAT]):
            return True
    return False


def _reject_self_intersection(points: list[tuple[float, float]]) -> None:
    """자기교차하면 멈춘다. **판정하지 않는다.**

    ★ 왜 거절하는가 — 자기교차 폴리곤에는 「안」이 **하나로 정해지지 않는다.**
      홀짝 규칙과 감김수 규칙이 서로 다른 답을 내고, 어느 쪽을 골라도 그 선택은
      화면이 그린 모양과 다르다. 그러면 운영자가 그린 구역과 시스템이 판정하는
      구역이 갈리고, **갈렸다는 사실이 아무 데도 안 남는다.**
      그래서 답을 고르는 대신 그리는 쪽에 되돌린다 (D-284).
    """
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue                       # 자기 자신·이웃 변은 건너뛴다
            c, d = points[j], points[(j + 1) % n]
            if _segments_properly_cross(a, b, c, d):
                raise InvalidPolygon(
                    f"폴리곤이 자기교차한다 ({i}–{i + 1}번 변과 {j}–{j + 1}번 변). "
                    f"자기교차 도형에는 '안'이 하나로 정해지지 않는다 — 규칙마다 답이 "
                    f"달라지므로 판정하지 않고 되돌린다. 구역을 다시 그려야 한다(D-365)")


def _point_in_polygon(lon: float, lat: float,
                      points: list[tuple[float, float]]) -> bool:
    """★ 판정 본체 — **광선 투사**(ray casting, 홀짝 규칙).

    경계(변 위·꼭짓점 위)를 **먼저** 본다. 광선 투사는 경계에서 부정확하고,
    그 부정확함이 「경계에 선 사람을 놓치는」 모양으로 나타난다 —
    재난안전에서 가장 비싼 오류다(`BOUNDARY_IS_INSIDE` 참조).

    GIS 의존이 없다. 계약에 GIS 요구가 없고, 의존 하나가 배포 하나를 어렵게 한다.
    """
    n = len(points)
    for i in range(n):
        ax, ay = points[i]
        bx, by = points[(i + 1) % n]
        if _on_segment(lon, lat, ax, ay, bx, by):
            return BOUNDARY_IS_INSIDE

    inside = False
    for i in range(n):
        ax, ay = points[i]
        bx, by = points[(i + 1) % n]
        # 위쪽 끝점만 세는 반열림 규칙 — 꼭짓점을 지나는 광선을 두 번 세지 않는다.
        if (ay > lat) != (by > lat):
            x_at = ax + (lat - ay) * (bx - ax) / (by - ay)
            if lon < x_at:
                inside = not inside
    return inside


def point_in_zone(zone, *, lat: float, lng: float) -> bool:
    """구역(폴리곤)이 그 좌표를 품는가. **공개 면** — 화면·규칙엔진이 이것을 부른다.

    `contains(zone, lat=, lng=)` 와 같은 판정이며, 이름이 둘인 이유는 하나다:
    `contains` 는 종류를 가리지 않는 문이고 이것은 폴리곤 전용 문이다. 좌표만 있는
    호출자가 카메라 묶음 구역을 넘기면 `contains` 는 `ValueError` 를 내는데,
    그 오류 메시지가 「좌표로 물었는데 왜 카메라를 요구하나」로 읽힌다.
    """
    return contains(zone, lat=lat, lng=lng)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — 못 하는 것은 정직하게 던진다 (D-284)
# ═══════════════════════════════════════════════════════════════════════════
def contains(zone, *, camera_id: int | None = None,
             lat: float | None = None, lng: float | None = None) -> bool:
    """이 구역이 그 관측을 품는가.

    카메라 묶음이면 **묶음에 그 카메라가 있는가** 하나로 답한다.
    폴리곤이면 **좌표로** 답한다 (D-365 — 2026-09-10 열렸다).

    답할 수 없는 상태는 여전히 조용하지 않다:
      · `geometry_status != 'ready'`  → `NotImplementedError` (아직 그릴 것이 안 그려졌다)
      · 도형이 폴리곤이 아니다        → `InvalidPolygon` (그린 것이 잘못됐다)
    둘은 **다른 사실**이고, 한 예외로 뭉치면 "안 그렸다"와 "잘못 그렸다"가 같아진다.
    """
    Zone = _zone_model()
    if zone.kind == Zone.Kind.CAMERA_GROUP:
        if camera_id is None:
            raise ValueError(
                "camera_group 구역 판정에는 camera_id 가 필요하다 — 좌표만으로는 "
                "이 종류의 구역이 답할 수 있는 질문이 아니다")
        return zone.cameras.filter(pk=camera_id).exists()

    if not ZONE_POLYGON_READY:
        raise NotImplementedError(
            f"폴리곤 판정 미구현 — 계약 F-03 AC 대상. {ZONE_POLYGON_NOT_READY_REASON}")
    if zone.geometry_status != Zone.GeometryStatus.READY:
        raise NotImplementedError(
            f"구역 '{zone.name}' 의 geometry_status 가 "
            f"{zone.geometry_status!r} 다 — 판정 코드는 섰으나 **이 구역의 도형이 아직 "
            f"안 서 있다.** 계약 F-03 AC 대상이며, 도형을 넣고 'ready' 로 올려야 판정한다")
    if lat is None or lng is None:
        raise ValueError(
            "폴리곤 구역 판정에는 lat·lng 가 필요하다 — 카메라 번호만으로는 "
            "이 종류의 구역이 답할 수 있는 질문이 아니다")

    points = _ring(zone.geometry)
    _reject_self_intersection(points)
    return _point_in_polygon(float(lng), float(lat), points)


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


# ═══════════════════════════════════════════════════════════════════════════
# 구역을 **만드는** 면 — F-12 「구역」 절 (D-366)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 직전까지 이 면은 **일부러 없었다.** `test_zone_editing_surface_was_not_built` 가
#   그것을 지켰고, 그 시험은 이렇게 적혀 있었다:
#
#       "구역 편집 함수가 공개 면에 생겼습니다 — 쓰기 면이 늘면
#        test_tenant_isolation.py 의 WRITE_PROBES 도 함께 늘어야 합니다 (D-290)."
#
#   이번에 그 면을 만들면서 **그 조건을 먼저 지켰다** — `WRITE_PROBES` 에 구역 쓰기
#   probe 를 넣고, 대장 검사가 이 모듈까지 훑도록 넓혔다. 시험이 건 조건을 지키고
#   면을 여는 것과, 면을 열고 시험을 지우는 것은 **다른 일**이다.
#
# 계층: 여기는 L3 Platform 이다. 구역은 재난안전 전용 개념이 아니므로(산업안전·시설물
# App 도 쓴다) 판정과 같은 자리에 둔다. App(L4)은 이 함수를 **부르기만** 한다.


def _writable_group(scope: TenantScope):
    """이 사람이 **어느 테넌트에 쓸 수 있는가.** 못 정하면 쓰지 않는다.

    ★ 시스템 스코프로는 구역을 못 만든다 — 파이프라인에는 요청자가 없고, 주인 없이
      만들어진 구역은 §0.4 의 `created_by__isnull` OR 절을 타고 **모두에게 보인다**
      (`_own`/`k1_event._inherit_owner` 와 같은 판단 · D-281).
    """
    from django.core.exceptions import PermissionDenied

    from common.tenant_filters import get_user_group

    if scope.is_system:
        raise PermissionDenied(
            "구역 쓰기는 사람이 한다 — 시스템 스코프로는 만들지 않는다. 주인 없는 "
            "구역은 §0.4 의 OR 절을 타고 모든 테넌트에 보인다 (D-281)")
    group = get_user_group(scope.actor)
    if group is None:
        raise PermissionDenied(
            "소속이 없는 계정은 구역을 만들 수 없다 — 어느 테넌트의 구역인지 "
            "정할 수 없기 때문이다. 전체로 두면 소속 없음이 전권이 된다")
    return group


def save_zone(*, scope: TenantScope, name: str, kind: str,
              zone_id: int | None = None, geometry=None,
              camera_ids: list[int] | None = None, is_active: bool = True):
    """구역 하나를 만들거나 고친다. **F-12 「구역」이 실제로 설정되는 자리.**

    ★ 폴리곤이면 **저장 전에 판정해 본다.** 못 판정할 도형은 저장하지 않는다 —
      저장해 두고 부를 때 터지면, 화면에는 '가동'인 구역이 판정에서만 사라진다.
      그 상태는 아무도 신고하지 않는다(`test_every_ready_zone_can_actually_be_judged`).

    ★ `geometry_status` 를 **부르는 쪽이 정하지 않는다.** 도형이 서면 `ready`,
      없으면 `not_implemented` 다 — 손으로 정하게 두면 도형 없는 `ready` 가 생긴다.
    """
    from django.db import transaction

    Zone = _zone_model()
    group = _writable_group(scope)

    if kind not in (Zone.Kind.CAMERA_GROUP, Zone.Kind.POLYGON):
        raise ValueError(
            f"kind={kind!r} 은 구역 종류가 아니다. "
            f"허용: {Zone.Kind.CAMERA_GROUP}, {Zone.Kind.POLYGON}")
    if not (name or "").strip():
        raise ValueError("이름 없는 구역은 만들지 않는다 — 화면에서 고를 수 없다")

    status = Zone.GeometryStatus.NOT_IMPLEMENTED
    if kind == Zone.Kind.POLYGON:
        if geometry is None:
            raise ValueError(
                "폴리곤 구역에는 도형이 필요하다 — 도형 없는 폴리곤 구역은 아무 진입도 "
                "판정하지 못하면서 화면에는 구역으로 보인다(D-365)")
        points = _ring(geometry)                 # 잘못 그렸으면 여기서 InvalidPolygon
        _reject_self_intersection(points)
        status = Zone.GeometryStatus.READY

    with transaction.atomic():
        if zone_id is None:
            zone = Zone.objects.create(name=name.strip(), kind=kind,
                                       geometry=geometry, geometry_status=status,
                                       is_active=is_active)
            _assign_group(zone, group)
        else:
            # ★ 남의 구역은 **없는 것으로** 답한다 (D-269) — 403 은 존재를 알린다.
            from common.tenant_filters import get_scoped_or_404

            zone = get_scoped_or_404(Zone, zone_id, scope.actor)
            zone.name = name.strip()
            zone.kind = kind
            zone.geometry = geometry
            zone.geometry_status = status
            zone.is_active = is_active
            zone.save(update_fields=["name", "kind", "geometry",
                                     "geometry_status", "is_active"])
        if camera_ids is not None:
            zone.cameras.set(_own_cameras(camera_ids, scope))
    return zone


def _assign_group(zone, group) -> None:
    """소유를 박는다. 필드 이름을 하드코딩하지 않는다 — 실행 중인 dj-core 는
    `group` FK 를 준다(D-292 실측)."""
    names = {f.name for f in type(zone)._meta.get_fields()}
    if "groups" in names:
        zone.groups.set([group])
    elif "group" in names:
        zone.group = group
        zone.save(update_fields=["group"])


def _own_cameras(camera_ids: list[int], scope: TenantScope) -> list:
    """**내 테넌트의 카메라만** 붙인다. 남의 카메라 번호는 조용히 빠지지 않고 멈춘다.

    조용히 빼면 운영자는 붙었다고 믿고 그 카메라의 진입은 영영 이 구역으로 안 온다 —
    빠진 것이 화면에 안 보이는 종류의 고장이다 (D-284).
    """
    from django.core.exceptions import PermissionDenied

    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    # `_scoped` 를 쓴다 — 구역 조회가 쓰는 그 좁히기다. 다른 방식을 쓰면 읽기와 쓰기가
    # 서로 다른 테넌트 판정을 갖게 되고, 둘이 갈리는 날 아무도 모른다 (D-212).
    mine = list(_scoped(StreamMonitor.objects.filter(pk__in=camera_ids), scope))
    missing = sorted(set(camera_ids) - {c.pk for c in mine})
    if missing:
        raise PermissionDenied(
            f"내 테넌트의 카메라가 아닌 번호가 있다: {missing}. 조용히 빼지 않는다 — "
            f"뺐다는 사실이 화면에 안 보이면 그 카메라의 진입은 영영 이 구역으로 안 온다")
    return mine


def list_zones(*, scope: TenantScope) -> list[dict]:
    """설정 화면이 읽는 구역 목록. **판정 가능 여부를 함께 낸다.**

    `judgeable` 이 없으면 화면은 도형이 깨진 구역과 멀쩡한 구역을 구별하지 못한다.
    """
    Zone = _zone_model()
    rows = []
    for zone in _scoped(Zone.objects.all(), scope):
        judgeable, why = True, ""
        if zone.kind == Zone.Kind.POLYGON:
            try:
                _reject_self_intersection(_ring(zone.geometry))
            except InvalidPolygon as exc:
                judgeable, why = False, str(exc)
        rows.append({
            "zone_id": zone.pk,
            "name": zone.name,
            "kind": zone.kind,
            "geometry_status": zone.geometry_status,
            "is_active": zone.is_active,
            "camera_count": zone.cameras.count(),
            "crs": ZONE_CRS if zone.kind == Zone.Kind.POLYGON else "",
            "judgeable": judgeable,
            #: 못 판정하면 **사유가 함께 나간다.** 빈 값이면 화면이 "구역이 없다"로 읽는다.
            "reason": why,
        })
    return rows


def is_polygon_ready() -> bool:
    """폴리곤 판정이 **잴 수 있는 상태인가.** 선언과 데이터를 함께 보지 않는다 —
    데이터 쪽 대조는 DB 가 필요하므로 `tests/test_zone_judgment.py` 가 한다."""
    return ZONE_POLYGON_READY


__all__ = [
    "KERNEL_READY",
    "ZONE_POLYGON_READY",
    "ZONE_POLYGON_NOT_READY_REASON",
    "ZONE_CRS",
    "BOUNDARY_IS_INSIDE",
    "InvalidPolygon",
    "point_in_zone",
    "ESCALATED_SEVERITY",
    "ZoneCombination",
    "contains",
    "zones_for_camera",
    "same_zone",
    "combine_in_zone",
    "save_zone",
    "list_zones",
    "is_polygon_ready",
]
