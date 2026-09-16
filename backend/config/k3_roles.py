# -*- coding: utf-8 -*-
"""K3 역할별 프레임의 **배선** — 역할 코드 ↔ 프리셋 ↔ 위젯 가시성 (P-K3-1 해소).

★ 이 파일이 왜 생겼나 — **프레임은 이미 있었고, 비어 있었다** (D-333 ④ · D-369)
--------------------------------------------------------------------------------
지시 D-371 ①은 「K3 역할별 프레임」을 이번 턴 표적으로 올렸다. 착수 전에 실측했다:

    backend/kernels/k3_dashboard/  — **2026-09 이전에 이미 서 있었다.**
        presets.py   프리셋 3종 · 가시성 3값 · 설정 위젯 8종
        services.py  get_preset · widget_permission · resolve_layout · 5상태 주입
        tests/test_k3_dashboard_kernel.py 도 함께 있었다

즉 **만들 것이 아니라 배선할 것**이었다. `presets.py` 는 매핑을 코드에 박지 않고
설정에서 읽게 해 두었고(D-280 — 실측되지 않은 매핑을 박지 않는다),
**그 설정이 어디에도 없었다.** 그래서 실제 동작은 이랬다:

    모든 사용자 → `matched=False` → 가장 좁은 프리셋(OPERATOR)
    모든 위젯   → 매트릭스가 비어서 `VISIBLE` (편집은 아무에게도 안 열림)

프레임이 있는데 배선이 없으면 **역할별 화면이 아니라 한 가지 화면**이다.
⑦사용성이 두 턴 동안 0%p 였던 자리 하나가 여기다.

역할 코드를 **실측했다** (D-280 · D-210)
----------------------------------------
`presets.py` 는 「이 저장소의 `role.Role.code` 에 그 다섯이 어떤 문자열로 들어 있는지는
정해진 바가 없다 — 실측으로도 찾지 못했다」고 적어 두었다. 이번에 DB 를 물었다:

    [실측 2026-09-11 · role.Role · 전수 15종]
      operator · order · delivery_admin · surveillance_operation · surveillance_order
      fire_admin · fire_user · drone_robot_admin · drone_robot_user
      view_only_-_anyang · delivery_order · delivery_operation
      admin · user · superuser

DA-03 §3-4 는 역할을 **다섯 종류의 사람**으로 적었다. 그 다섯과 위 열다섯을 잇는 것이
이 파일이고, **그 이음은 인용이 아니라 판정이다** — 아래 주석마다 근거를 적는다.

★ 매핑하지 않은 것도 판정이다 (D-264 · D-301)
---------------------------------------------
배송·물류 역할(`order` · `delivery_*` · `drone_robot_*`)과 `user` 는 **일부러 비웠다.**
그들은 이 제품(재난안전 모니터링)의 역할이 아니다. 비우면 `get_preset` 이
`matched=False` 로 **말해 준다** — 조용히 기본값을 주지 않는다.
「매핑을 깜빡했다」와 「매핑하지 않기로 했다」가 코드에서 갈려야 하므로,
비운 것들의 이름을 `K3_UNMAPPED_BY_DECISION` 에 적는다. 면제가 아니라 선언이다.

★ `superuser` 도 비어 있다 — 그러나 다른 이유다
-----------------------------------------------
전역 관리자 판정은 `common/tenant_roles.is_global_admin` 한 곳이 한다(D-212).
여기에 `superuser` 를 적으면 **판정식이 두 벌**이 되고, 두 벌은 반드시 어긋난다(D-369).
`get_preset` 과 `widget_permission` 은 이미 그 함수를 부른다.
"""

# ═══════════════════════════════════════════════════════════════════════════
# 역할 코드 묶음 — DA-03 §3-4 의 「다섯 종류의 사람」에 대응시킨다
# ═══════════════════════════════════════════════════════════════════════════

#: 관제요원 — 화면 앞에 앉아 이벤트를 처리하는 사람.
#: `fire_user`(화재 사용자) · `surveillance_operation`(감시 운용) · `operator`.
K3_ROLE_OPERATORS = ("fire_user", "surveillance_operation", "operator")

#: 재난관제 관리자 — 규칙·임계값·수신자를 **정하는** 사람.
#: `fire_admin` 은 이름이 그대로이고, `surveillance_order` 는 감시 임무를 **지시**하는
#: 자리라 운용자보다 넓다.
K3_ROLE_MANAGERS = ("fire_admin", "surveillance_order")

#: 기관장/부서장 — **보기만** 한다. 숫자와 지도.
#: `view_only_-_anyang` 은 이름이 곧 그 뜻이다(안양시 열람 전용).
K3_ROLE_EXECUTIVES = ("view_only_-_anyang",)

#: 운영자 — 시스템을 운영한다. SDN 연계·역할·API Key 가 이 사람의 자리다.
#: ★ 프리셋은 EXECUTIVE 가 아니라 **MANAGER** 다. 운영자가 보는 것은 기관장의
#:   요약이 아니라 관리 화면이고, 프리셋은 「권한의 높낮이가 아니라 범위의 넓이」다.
K3_ROLE_SYSOPS = ("admin",)

#: **일부러 비운 것.** 위 머리말의 이유. 늘 때마다 사람이 이 목록을 고쳐야 한다.
K3_UNMAPPED_BY_DECISION = {
    "order": "배송 주문 역할 — 이 제품(재난안전)의 역할이 아니다",
    "delivery_admin": "배송 관리 역할 — 위와 같다",
    "delivery_order": "배송 주문 역할 — 위와 같다",
    "delivery_operation": "배송 운용 역할 — 위와 같다",
    "drone_robot_admin": "드론·로봇 관리 역할 — 위와 같다",
    "drone_robot_user": "드론·로봇 사용 역할 — 위와 같다",
    "user": "기본 역할 — 아무 뜻이 없다. 여기 매핑하면 「역할이 없는 사람」이 "
            "화면을 얻고, 그러면 매핑이 매핑이 아니게 된다",
    "superuser": "전역 관리자 — 판정은 tenant_roles.is_global_admin 한 곳이 한다 (D-212)",
}

K3_ROLE_PRESET_MAP = {
    **{code: "OPERATOR" for code in K3_ROLE_OPERATORS},
    **{code: "MANAGER" for code in K3_ROLE_MANAGERS},
    **{code: "EXECUTIVE" for code in K3_ROLE_EXECUTIVES},
    **{code: "MANAGER" for code in K3_ROLE_SYSOPS},
}


# ═══════════════════════════════════════════════════════════════════════════
# P-146 · SEC-22 — 이 역할 코드는 **자기 테넌트 안에서** 설정 문(F-12)을 지난다
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 여기 있나 — 계정이 아니라 **역할**에 붙인다 (턴 R 세종 판정 P-146)
# --------------------------------------------------------------------------
# 턴 Q 는 탐침 계정 `gxprobe_q` 한 명에게 `tenant_admin_<group_id>` 역할을
# **손으로 만들어 붙였다**(evidence/P-141/u56_sec22_role_grant.md). 그것은
# 「이 계정으로 두드리면 지나간다」는 게이트의 증거이지, 「이 역할을 가진 사람은
# 지나가야 한다」는 제품의 증거가 아니다. U5 시드 계정(`gxseed_u5_sysop`)이 바로
# 그 간극을 드러냈다 — `admin` 역할의 K3 위젯(`_SYSOP_WIDGETS["api_key"]`)은
# 이미 "편집 가능"으로 그려지는데, 실제 판정식(`tenant_roles.is_tenant_admin`)은
# `tenant_admin_<group_id>` 라는 **별도 역할**을 요구했다 — 화면과 판정이 어긋난
# 그 자리다.
#
# ★ 여기 적는 것은 **매핑 한 줄**이지 판정식이 아니다 (D-212)
# --------------------------------------------------------------------------
# `common/tenant_roles.py::is_tenant_admin` 이 판정하는 **유일한 곳**이고, 여기서
# 판정을 다시 하지 않는다. 이 튜플은 그 판정이 "어떤 역할 코드를 추가로 인정하는가"
# 를 말하는 **표**일 뿐이다 — `K3_ROLE_SYSOPS` 를 다시 적지 않고 **그대로 별칭**한다
# (표를 두 벌 두지 않는다). 이름을 따로 둔 이유는 이 표의 뜻이 "K3 화면이 운영자를
# 어떻게 보여줄까"(UI 프리셋)와 "누가 설정을 쓸 수 있나"(보안 판정)라는 **다른 질문**
# 이기 때문이다 — 지금은 같은 답(`admin` 하나)이지만, 언젠가 갈릴 수 있는 두 질문을
# 같은 상수로 가리키면 다음 사람이 "이걸 고치면 뭐가 바뀌나"를 못 읽는다.
#
# ★ 경계는 그대로다 — **전역이 아니라 테넌트다**
# --------------------------------------------------------------------------
# `is_tenant_admin` 은 이 표에 있어도 **자기 소속(group)이 없으면 여전히 거짓**이다
# (남의 테넌트 설정은 여전히 못 만진다). 전역 관리자(`is_global_admin`)의 판정식은
# 손대지 않는다 — 범위를 넓히는 방향이 아니라 **그 역할이 원래 가져야 할 만큼만** 준다.
K3_ROLES_WITH_TENANT_SETTINGS_ACCESS = K3_ROLE_SYSOPS


# ═══════════════════════════════════════════════════════════════════════════
# 위젯 가시성 — **DA-03 §3-4 표를 그대로 옮긴다.** 고쳐 옮기지 않는다
# ═══════════════════════════════════════════════════════════════════════════
#
#   | 설정 항목    | 관제요원 | 재난관제 관리자 | 기관장/부서장 | 운영자 |
#   |--------------|---------|----------------|--------------|-------|
#   | 위험구역     |    V    |       E        |      V       |   V   |
#   | 임계값       |    –    |       E        |      –       |   V   |
#   | 등급 규칙    |    V    |       E        |      V       |   –   |
#   | 수신자 그룹  |    –    |       E        |      V       |   –   |
#   | SDN 연계     |    –    |       V        |      –       |   E   |
#   | 역할 관리    |    –    |       V        |      –       |   E   |
#   | API Key 발급 |    –    |       –        |      –       |   E   |
#   | 감사로그     |    –    |       V        |      V       |   V   |
#
# ★ `–` 를 **적지 않고 비워 두면 안 된다.** `widget_permission` 은 매트릭스에 값이
#   없으면 `VISIBLE` 로 떨어진다(설정 전 상태와 구별하려고 그렇게 설계돼 있다).
#   그러므로 `–` 는 반드시 `"hidden"` 이라고 **적어야** 숨는다.
#   비워 두면 「숨기기로 했다」가 「아직 설정 안 했다」와 같아진다 (D-290).

# ★ 아래 표의 `api_key` 는 **DA-03 §3-4 의 위젯 이름**이지 자격증명이 아니다.
#   `verify_homonyms.py` 가 「수식어 없는 api_key」를 잡는 것은 옳고, 이 자리는
#   그 잡힘을 **기준선에 올려 통과시킨다**(D-311 래칫). 이름을 못 바꾸는 이유:
#   이 문자열은 `kernels/k3_dashboard/presets.py::SETTING_WIDGETS` 와 DA-03 §3-4
#   표를 잇는 열쇠다. 여기서만 바꾸면 **문서와 코드를 잇는 끈이 끊긴다**.
#   방향이 궁금하면 답은 하나다 — 이 위젯이 여는 것은 **들어오는 키의 발급 화면**이고,
#   그 발급기는 `kernels/k5_trust/inbound_keys.py` 다.

_V, _E, _H = "visible", "editable", "hidden"

_OPERATOR_WIDGETS = {
    "danger_zone": _V, "threshold": _H, "severity_rule": _V, "recipient_group": _H,
    "sdn_link": _H, "role_management": _H, "api_key": _H, "audit_log": _H,
}
_MANAGER_WIDGETS = {
    "danger_zone": _E, "threshold": _E, "severity_rule": _E, "recipient_group": _E,
    "sdn_link": _V, "role_management": _V, "api_key": _H, "audit_log": _V,
}
_EXECUTIVE_WIDGETS = {
    "danger_zone": _V, "threshold": _H, "severity_rule": _V, "recipient_group": _V,
    "sdn_link": _H, "role_management": _H, "api_key": _H, "audit_log": _V,
}
_SYSOP_WIDGETS = {
    "danger_zone": _V, "threshold": _V, "severity_rule": _H, "recipient_group": _H,
    "sdn_link": _E, "role_management": _E, "api_key": _E, "audit_log": _V,
}

K3_WIDGET_MATRIX = {
    **{code: dict(_OPERATOR_WIDGETS) for code in K3_ROLE_OPERATORS},
    **{code: dict(_MANAGER_WIDGETS) for code in K3_ROLE_MANAGERS},
    **{code: dict(_EXECUTIVE_WIDGETS) for code in K3_ROLE_EXECUTIVES},
    **{code: dict(_SYSOP_WIDGETS) for code in K3_ROLE_SYSOPS},
}
