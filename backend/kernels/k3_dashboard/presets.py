# -*- coding: utf-8 -*-
"""프리셋과 가시성 — **판정표를 한 곳에 둔다** (DA-03 §3-4 · D-212).

이 파일이 답하는 것은 둘이다:

    ① 이 사람은 **어느 화면으로 떨어지는가** (프리셋)
    ② 이 사람에게 **이 위젯이 보이는가** (가시성)

둘 다 화면이 아니라 **서버가** 답한다. DA-03 §3-4 불변 규칙 1:

    **화면에서 감추는 것은 통제가 아니다.** 이 표는 UI 규칙이고, 같은 내용을
    **서버가 다시 판정**한다. 서버 판정은 `common/tenant_roles.py` 한 곳만 부른다 —
    판정식을 화면 코드로 복사하지 않는다(D-212).

왜 프리셋이 U3 의 답인가
------------------------
DA-04 §2 K3: *"프리셋이 **로그인 직후 기본 화면**을 결정하면 도달 클릭이 0~1 이 된다.
즉 U3 의 ≤2 는 프리셋 라우팅으로 달성된다."*

그러므로 `get_preset` 은 **선택을 요구하지 않아야** 한다. 사용자가 프리셋을 고르게 하는
순간 클릭이 하나 늘고, 그 하나가 U3 의 여유분 전부다.

★ 역할 코드 ↔ 프리셋 매핑은 **추정하지 않았다** (D-280)
-------------------------------------------------------
DA-03 은 역할을 **다섯 종류의 사람**으로 적었다(관제요원 · 재난관제 관리자 ·
기관장/부서장 · 운영자 · 외부 APP 개발자). 그런데 **이 저장소의 `role.Role.code` 에
그 다섯이 어떤 문자열로 들어 있는지는 정해진 바가 없다** — 실측으로도 찾지 못했다.

그래서 코드에 문자열을 박지 않고 **설정에서 읽는다.** 설정이 비면 매핑은 비고,
비면 **가장 낮은 프리셋으로 떨어진다**(4원칙 ① 더 안전한 쪽). 그 상태를
`get_preset` 이 `matched=False` 로 **말해 준다** — 조용히 기본값을 주지 않는다.

매핑 확정은 **P-K3-1 로 적재**했다. W3-2(프리셋 정의)가 정본이다.
"""
from __future__ import annotations

from enum import Enum

from django.conf import settings


class Preset(str, Enum):
    """DA-04 §2 K3 이 정한 셋. **넷째를 만들지 않는다.**

    재난용 프리셋을 따로 만들면 U3 수렴이 깨진다 (DA-04 K3 · DA-03 D3-2).
    """

    OPERATOR = "OPERATOR"      # 관제요원 — 오늘의 임무·미처리 이벤트
    MANAGER = "MANAGER"        # 재난관제 관리자 — 4카드 + 추이 + 히트맵
    EXECUTIVE = "EXECUTIVE"    # 기관장/부서장 — 숫자 4~6 + 지도 1장

    @property
    def rank(self) -> int:
        """권한의 높낮이가 아니라 **범위의 넓이**다. 낮을수록 좁다.

        떨어질 때는 항상 **낮은 쪽**으로 떨어진다 — 모르면 좁게 보여 준다.
        """
        return {"OPERATOR": 0, "MANAGER": 1, "EXECUTIVE": 2}[self.value]


#: 매핑이 없을 때 떨어지는 자리. **가장 좁은 것**이다 (4원칙 ①).
#:
#: 넓은 쪽으로 떨어뜨리면 역할을 못 알아본 사람이 기관장 화면을 본다.
#: 좁은 쪽으로 떨어뜨리면 못 보는 것이 생기고, 그것은 **눈에 띄어 신고된다.**
#: 두 실패 중 눈에 띄는 쪽을 고른다.
FALLBACK_PRESET = Preset.OPERATOR


def _role_preset_map() -> dict[str, Preset]:
    """역할 코드 → 프리셋. **설정 한 곳에서 읽는다** (D-212).

    ★ 밑줄로 시작하는 이유는 커널 규약이다 — `kernels/` 안의 모듈 최상위 **공개** 함수는
      `*, scope: TenantScope` 를 요구받는다(D-281). 이 함수는 설정을 읽을 뿐 테넌트
      데이터를 만지지 않으므로 공개 면이 아니고, 그 사실을 **이름으로** 말한다.
      규약에 면제를 내는 대신 모양을 맞춘다 — `k2_notify/channels.py` 와 같은 처리다.

    `settings.K3_ROLE_PRESET_MAP = {"disaster_admin": "MANAGER", …}`

    비어 있는 것이 기본값이다 — 실측으로 확인되지 않은 매핑을 코드에 박지 않는다.
    """
    raw = getattr(settings, "K3_ROLE_PRESET_MAP", None) or {}
    out: dict[str, Preset] = {}
    for code, name in raw.items():
        try:
            out[str(code)] = Preset(str(name).upper())
        except ValueError:
            # 설정에 없는 프리셋 이름이 들어오면 **조용히 버리지 않는다** —
            # 버리면 "매핑했는데 안 먹는" 상태가 되고 아무도 이유를 모른다.
            raise ValueError(
                f"K3_ROLE_PRESET_MAP[{code!r}] = {name!r} 은 프리셋이 아니다. "
                f"허용: {', '.join(p.value for p in Preset)}"
            ) from None
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 가시성 — DA-03 §3-4 매트릭스의 **서버측 정본**
# ═══════════════════════════════════════════════════════════════════════════
#
# `–` = 미렌더(=여기서는 등재하지 않음) · `V` = 볼 수 있다 · `E` = 편집할 수 있다.
#
# ★ 이 표는 **프리셋이 아니라 역할**을 기준으로 한다. 프리셋은 "어느 화면으로
#   떨어지는가"이고 가시성은 "무엇을 만질 수 있는가"다 — 둘을 한 축으로 합치면
#   화면을 바꾸는 것이 곧 권한을 바꾸는 일이 된다.
#
# ⚠ 역할 코드가 미정이므로(P-K3-1) 이 표의 **키도 설정에서 온다.**
#   설정이 비면 위젯은 전부 `FORBIDDEN` 이 아니라 **`VISIBLE`(읽기)** 로 떨어진다:
#   이 커널은 아직 편집 면을 열지 않았고, 읽기 격리는 이미 `filter_by_group_field` 가 한다.
#   **편집(E) 판정은 설정 없이는 절대 참이 되지 않는다** — 그것이 이 기본값의 요점이다.


class Visibility(str, Enum):
    """DA-03 §3-4 의 세 값. **`–` 는 `HIDDEN` 이다** — 빈 값이 아니다."""

    HIDDEN = "hidden"      # 탭·위젯 자체가 렌더되지 않는다
    VISIBLE = "visible"    # V — 볼 수 있다
    EDITABLE = "editable"  # E — 편집할 수 있다

    @property
    def can_read(self) -> bool:
        return self is not Visibility.HIDDEN

    @property
    def can_write(self) -> bool:
        return self is Visibility.EDITABLE


#: DA-03 §3-4 가 이름 붙인 설정 항목 8종. **이름으로 잠근다** (D-285 ②).
#: 늘리려면 이 집합과 DA-03 §3-4 표를 **같은 커밋에서** 고친다.
SETTING_WIDGETS: tuple[str, ...] = (
    "danger_zone",       # 위험구역
    "threshold",         # 임계값
    "severity_rule",     # 등급 규칙 (F-04)
    "recipient_group",   # 수신자 그룹 (K2)
    "sdn_link",          # SDN 연계
    "role_management",   # 역할 관리
    "api_key",           # API Key 발급
    "audit_log",         # 감사로그
)


def _widget_matrix() -> dict[str, dict[str, Visibility]]:
    """역할 코드 → 위젯 → 가시성. **설정에서 읽는다.** (밑줄 이유는 위와 같다.)

    `settings.K3_WIDGET_MATRIX = {"disaster_admin": {"threshold": "editable", …}}`

    비면 빈 표다. 빈 표에서 편집은 **아무에게도** 허용되지 않는다 (아래 `_default`).
    """
    raw = getattr(settings, "K3_WIDGET_MATRIX", None) or {}
    out: dict[str, dict[str, Visibility]] = {}
    for code, widgets in raw.items():
        row: dict[str, Visibility] = {}
        for widget, level in (widgets or {}).items():
            try:
                row[str(widget)] = Visibility(str(level).lower())
            except ValueError:
                raise ValueError(
                    f"K3_WIDGET_MATRIX[{code!r}][{widget!r}] = {level!r} 은 "
                    f"가시성이 아니다. 허용: {', '.join(v.value for v in Visibility)}"
                ) from None
        out[str(code)] = row
    return out
