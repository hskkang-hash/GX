# -*- coding: utf-8 -*-
"""K3 역할별 대시보드 프레임 — 공개 면 (DA-04 §2 K3).

"누가 보느냐에 따라 다른 화면"을 만드는 프레임. **위젯이 아니라 프레임이 커널이다.**

이중 AC (DA-04 §1-2) — 충돌 시 **계약 AC 우선**
------------------------------------------------
    [F-09 계약] 5상태(기본/로딩/빈/오류/권한없음) 100% · 클릭→영상 3초
    [U3 상품]  역할별 대시보드 **도달 클릭 ≤ 2**

★ DA-04 가 해법을 이미 적었다:

    프리셋이 **로그인 직후 기본 화면**을 결정하면 도달 클릭이 0~1 이 된다.
    즉 U3 의 ≤2 는 프리셋 라우팅으로 달성되고, F-09 의 5상태는 그 프레임이
    **상태를 위젯에 주입**하는 방식으로 한 번에 처리된다 —
    위젯마다 5상태를 손으로 짜지 않는다.

그래서 이 커널이 하는 일은 둘이다: **어느 화면인가**(프리셋)와
**각 칸이 어떤 상태인가**(주입). 위젯의 내용은 이 커널의 일이 아니다.

왜 모델을 새로 만들지 않았나
----------------------------
`Dashboard` · `DashboardPanel` 은 이미 있고 **둘 다 `BaseModelWithGroup`** 이다
(DA-04 §2 K3 — "격리 기반이 있다"). 커널이 가져가는 것은 로직이지 표가 아니다.

테넌트 스코프 — D-281
---------------------
공개 함수는 전부 `*, scope: TenantScope` 를 **키워드 전용 필수 인자**로 받고,
셋 다 읽기이므로 `require_actor()` 를 통과해야 한다. 대시보드를 시스템 스코프로
물으면 그것은 **전 테넌트의 화면**이고, 전 테넌트 화면은 격리의 부재다.

★ 그리고 화면 판정은 **격리를 대신하지 않는다.** `widget_permission` 이 `VISIBLE` 을
  줘도 그 위젯이 읽는 데이터는 여전히 `filter_by_group_field` 를 탄다.
  DA-03 §3-4: *"화면에서 감추는 것은 통제가 아니다."*
"""
from __future__ import annotations

from typing import Any, Callable, Iterable

from django.apps import apps

from common.tenant_filters import filter_by_group_field
from common.tenant_roles import is_global_admin, is_tenant_admin_role_code
from common.tenant_scope import TenantScope
from kernels.k3_dashboard.exceptions import InvalidLayoutInput
from kernels.k3_dashboard.presets import (
    FALLBACK_PRESET,
    SETTING_WIDGETS,
    Preset,
    Visibility,
    _role_preset_map,
    _widget_matrix,
)
from kernels.k3_dashboard.schemas import PanelView, PresetView, WidgetState


def _model(name: str):
    return apps.get_model("dashboard", name)


def _owner_field(model) -> str:
    """K1 과 **같은 판단**을 쓴다 — 판단은 한 곳에서만 한다 (D-212)."""
    from kernels.k1_event.services import _owner_field as k1_owner_field

    return k1_owner_field(model)


def _role_codes(actor: Any) -> tuple[str, ...]:
    """요청자의 역할 코드들.

    ⚠ `common.tenant_roles._role_codes` 와 같은 일을 한다. 그것은 비공개(`_`)라
      밖에서 부르지 않는 것이 규약이고, 여기서 복사하는 것도 D-212 위반이다.
      그래서 **전역 판정은 절대 여기서 하지 않는다** — `is_global_admin` 만 부른다.
      여기서 읽는 코드는 오직 **프리셋·가시성 조회의 열쇠**로만 쓰인다.
    """
    roles = getattr(actor, "roles", None)
    if roles is None:
        return ()
    try:
        return tuple(sorted(c for c in roles.values_list("code", flat=True) if c))
    except Exception:
        return ()


# ═══════════════════════════════════════════════════════════════════════════
# 1. get_preset — **선택을 요구하지 않는다** (U3 의 답)
# ═══════════════════════════════════════════════════════════════════════════
def get_preset(*, scope: TenantScope) -> PresetView:
    """로그인 직후 이 사람이 떨어질 화면 (DA-04 §2 K3).

    ★ 사용자가 고르게 하지 않는다. 고르게 하는 순간 클릭이 하나 늘고,
      그 하나가 U3(도달 클릭 ≤ 2)의 여유분 전부다.

    ★ **매핑을 못 찾은 것과 찾은 것을 가른다** (`matched`). 합치면 "설정을 안 했는데도
      잘 돌아간다"가 되고, 그 상태가 운영에 그대로 나간다 (D-290).

    ★ 못 찾으면 **가장 좁은 프리셋**으로 떨어진다. 넓은 쪽으로 떨어뜨리면 역할을 못
      알아본 사람이 기관장 화면을 본다 — 두 실패 중 눈에 띄는 쪽을 고른다 (4원칙 ①).
    """
    actor = scope.require_actor()
    codes = _role_codes(actor)
    mapping = _role_preset_map()

    # 여러 역할이 서로 다른 프리셋을 가리키면 **넓은 쪽**을 준다.
    # 좁은 쪽을 주면 관리자 역할을 겸한 사람이 관리자 화면을 못 본다 — 그것은
    # "안 보인다"로 즉시 신고되지만, 여기서 좁히면 U3 가 깨진다.
    matched = [mapping[c] for c in codes if c in mapping]
    # ★ 2026-09-17 (턴 T · F · SEC-22 · D-478) — `tenant_admin_<n>` 은 글자 일치가 아니라
    #   **패턴**으로 관리자 프리셋에 닿는다. 판정식은 `common.tenant_roles` 한 곳.
    matched += [Preset.MANAGER for c in codes if is_tenant_admin_role_code(c) and c not in mapping]
    if matched:
        preset = max(matched, key=lambda p: p.rank)
        return PresetView(
            preset=preset.value, matched=True, role_codes=codes,
            reason=f"역할 {[c for c in codes if c in mapping]} 매핑",
        )

    # 전역 관리자는 매핑이 없어도 넓게 본다 — 판정은 `tenant_roles` 한 곳이 한다(D-212).
    if is_global_admin(actor):
        return PresetView(
            preset=Preset.EXECUTIVE.value, matched=True, role_codes=codes,
            reason="전역 관리자 — tenant_roles.is_global_admin",
        )

    return PresetView(
        preset=FALLBACK_PRESET.value, matched=False, role_codes=codes,
        reason=(
            "역할 코드가 K3_ROLE_PRESET_MAP 에 없다 — 가장 좁은 프리셋으로 떨어졌다. "
            "매핑 확정은 W3-2(프리셋 정의)가 정본이고 P-K3-1 로 적재돼 있다"
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# 2. widget_permission — **서버가 다시 판정한다**
# ═══════════════════════════════════════════════════════════════════════════
def widget_permission(widget: str, *, scope: TenantScope) -> Visibility:
    """이 사람에게 이 위젯이 보이는가 · 편집되는가 (DA-03 §3-4 매트릭스).

    ★ DA-03 §3-4 불변 규칙 1: *"화면에서 감추는 것은 통제가 아니다."*
      화면이 탭을 안 그려도 API 는 열려 있을 수 있다. 그 API 가 이 함수를 부른다.

    ★ **편집은 설정 없이 절대 참이 되지 않는다.** 매트릭스가 비면 `VISIBLE` 까지다.
      읽기를 막지 않는 이유는 이 커널이 아직 편집 면을 열지 않았고, 읽기 격리는
      이미 `filter_by_group_field` 가 하기 때문이다 — 여기서 읽기까지 막으면
      "권한없음"이 "아직 설정 안 함"을 덮어 원인을 못 찾게 된다.
    """
    if widget not in SETTING_WIDGETS:
        raise InvalidLayoutInput(
            f"widget={widget!r} 은 DA-03 §3-4 가 이름 붙인 설정 항목이 아니다. "
            f"허용: {', '.join(SETTING_WIDGETS)}. "
            f"항목을 늘리려면 DA-03 §3-4 표와 `presets.SETTING_WIDGETS` 를 "
            f"**같은 커밋에서** 함께 고쳐라"
        )
    actor = scope.require_actor()
    if is_global_admin(actor):
        return Visibility.EDITABLE

    matrix = _widget_matrix()
    levels = [matrix[c][widget] for c in _role_codes(actor)
              if c in matrix and widget in matrix[c]]
    if not levels:
        # 설정이 비었다. **편집은 아니다.**
        return Visibility.VISIBLE
    return max(levels, key=lambda v: (v.can_read, v.can_write))


# ═══════════════════════════════════════════════════════════════════════════
# 3. resolve_layout — **상태를 위젯에 주입한다** (F-09 5상태의 자리)
# ═══════════════════════════════════════════════════════════════════════════
def resolve_layout(
    *,
    scope: TenantScope,
    preset: str | None = None,
    app: str | None = None,
    dashboard_code: str | None = None,
    panel_source: Callable[[Any], Any] | None = None,
) -> tuple[PanelView, ...]:
    """프리셋에 맞는 패널 목록. **각 칸의 상태를 프레임이 정한다.**

    상태 판정 순서 — 이 순서가 곧 F-09 의 정의다:

        ① 권한없음 (FORBIDDEN)  — `widget_permission` 이 HIDDEN
        ② 오류      (ERROR)     — 내용을 가져오다 실패했다
        ③ 빈        (EMPTY)     — 성공했는데 0건이다
        ④ 기본      (DATA)      — 그 밖

    ①이 먼저인 이유: 권한이 없는 칸은 **내용을 가져오지도 않는다.** 가져온 뒤에
    가리면 그 조회가 이미 남의 데이터를 만졌을 수 있다.
    ②와 ③을 가르는 이유는 DA-03 §2-5 규칙 1이다 — 대기와 신고는 다른 행동이다.

    `panel_source` 는 **시험이 오류·빈 갈래를 지나가게 하는 이음매**다.
    없으면 패널의 `panel_config` 를 그대로 쓴다. 운영 경로는 넘기지 않는다.
    """
    actor = scope.require_actor()
    if preset is not None:
        try:
            Preset(preset.upper())
        except ValueError:
            raise InvalidLayoutInput(
                f"preset={preset!r} 은 프리셋이 아니다. "
                f"허용: {', '.join(p.value for p in Preset)}. "
                f"재난용 프리셋을 따로 만들지 않는다 — U3 수렴이 깨진다 (DA-04 K3)"
            ) from None

    Dashboard = _model("Dashboard")
    Panel = _model("DashboardPanel")

    boards = filter_by_group_field(
        Dashboard._base_manager.all(), actor, field=_owner_field(Dashboard))
    if dashboard_code:
        boards = boards.filter(code=dashboard_code)
    boards = boards.distinct()

    # ★ 패널도 **따로 좁힌다.** 부모를 좁혔으니 자식은 안전하다고 보지 않는다 —
    #   D-272 가 그 가정을 깨뜨린 자리다(부모 경로가 열리면 자식이 통째로 나간다).
    panels = filter_by_group_field(
        Panel._base_manager.filter(dashboard__in=boards).select_related("dashboard"),
        actor, field=_owner_field(Panel),
    ).distinct().order_by("dashboard_id", "id")

    out: list[PanelView] = []
    for panel in panels:
        out.append(_to_view(panel, scope=scope, panel_source=panel_source))
    return tuple(out)


def _to_view(panel, *, scope: TenantScope,
             panel_source: Callable[[Any], Any] | None) -> PanelView:
    base = dict(panel_id=panel.pk, dashboard_id=panel.dashboard_id,
                title=panel.panel_title, panel_type=panel.panel_type)

    # ── ① 권한없음 — **내용을 가져오기 전에** 판정한다 ────────────────────
    widget = (panel.panel_config or {}).get("widget") if panel.panel_config else None
    if widget in SETTING_WIDGETS:
        if widget_permission(widget, scope=scope) is Visibility.HIDDEN:
            return PanelView(**base, state=WidgetState.FORBIDDEN,
                             reason=f"widget={widget} 가시성 hidden (DA-03 §3-4)")

    # ── ② 오류 — 값으로 받는다. 예외를 여기서 삼키지 않는다 ───────────────
    #    `panel_source` 가 예외를 던지면 그것은 **오류 상태**이지 500 이 아니다.
    #    대시보드 한 칸이 실패했다고 화면 전체가 서면 저하 운전이 아니다 (W0-17).
    try:
        content = panel_source(panel) if panel_source else panel.panel_config
    except Exception as exc:
        return PanelView(**base, state=WidgetState.ERROR,
                         reason=f"{type(exc).__name__}: {exc}"[:200])

    # ── ③ 빈 — 성공했는데 0건 ────────────────────────────────────────────
    if content is None or content == {} or content == []:
        return PanelView(**base, state=WidgetState.EMPTY,
                         reason="요청은 성공했고 데이터가 0건이다")

    # ── ④ 기본 ───────────────────────────────────────────────────────────
    if not isinstance(content, dict):
        content = {"value": content}
    return PanelView(**base, state=WidgetState.DATA, config=content)


#: F-09 검수용 — **이 프레임이 정의한 다섯**을 이름으로 낸다.
#:
#: 검수에서 "5상태 100%"를 물으면 세는 것이 아니라 **이 목록을 보여 준다.**
#: 위젯마다 다시 세면 그 수는 언제나 100% 가 나온다 (D-249 부착률 착시).
#: 함수가 아니라 상수인 이유: 부르는 데 스코프가 필요 없다는 사실을 모양으로 말한다.
FIVE_STATES: tuple[str, ...] = tuple(s.value for s in WidgetState)
