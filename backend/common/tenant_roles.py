"""전역 관리 역할 vs 테넌트 운영 역할 — **정의 한 곳** (W0-16 · D-243 · D-247).

왜 이 모듈이 W0-14 보다 먼저인가
    W0-14(뷰 레벨 테넌트 스코프)는 "이 요청자가 테넌트 경계를 넘어도 되는가"를
    물어야 한다. 그런데 지금 그 질문의 답은 `common/tenant_filters.is_superuser()`
    가 내리고 있고, 그 판정은 **dj-core 의 역할 우회를 그대로 복제**한다
    (`core/base.py:308` == `tenant_filters.py:72`).

    즉 뷰를 아무리 고쳐도 판정 기준이 같으면 결과가 같다. **기준을 먼저 갈라야 한다.**
    그것이 이 모듈이고, D-247 이 실행 순서를 뒤집은 이유다.

실측이 말하는 것 (evidence/W0-16/superuser_accounts.md)
    · 레거시 `superuser` **역할** 보유 13계정 — 전원 활성, 전원 `is_superuser=false`
    · 그중 **7계정이 고객 테넌트(Anyang) 안에 있다**
    · 이 역할은 ORM 필터(base.py:308)와 권한검사(permission.py:475)를 통째로 통과시킨다
      — 둘 다 §0.4 라 고칠 수 없다. 그래서 **역할을 갈라내고 회수**한다.

정의 (설정은 `config/settings.py` 한 곳 · D-212)
    전역 관리자 = 다음 중 하나
        ① DB 플래그 `is_superuser=True`                    (현재 실계정 0명)
        ② `TENANT_GLOBAL_ADMIN_ROLE_CODES` 의 역할 보유    (GAION 운영자 전용)
        ③ 레거시 `superuser` 역할 보유 **AND**
           `TENANT_TRUST_LEGACY_SUPERUSER = True`          ← 전환기에만 참
    테넌트 운영자 = `<TENANT_ADMIN_ROLE_PREFIX>_<group_id>` 역할을 보유하고
                    그 역할의 `group_id` 가 **요청자의 소속 group 과 같다**

③ 을 끄는 것이 회수의 실질이다. 순서는 evidence/W0-16/revocation_runbook.md:
    대체역할 부여 → ③ False → 검증 → 역할 회수 → `is_default` 내리기

⚠ 이 판정식을 다른 파일에 복사하지 말 것 (D-212). 복사본 하나가 우회 지점 하나다.
  W0-14 는 `tenant_filters` 를 통해 이 모듈만 부른다.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

#: 레거시 전역 역할 코드. dj-core 가 하드코딩으로 아는 유일한 값이다 (base.py:308).
LEGACY_GLOBAL_ROLE_CODE = "superuser"


def global_admin_role_codes() -> frozenset[str]:
    """전역으로 인정하는 역할 코드 집합. 전환 플래그를 여기서 반영한다."""
    codes = set(getattr(settings, "TENANT_GLOBAL_ADMIN_ROLE_CODES", []) or [])
    if trusts_legacy_superuser():
        codes.add(LEGACY_GLOBAL_ROLE_CODE)
    return frozenset(codes)


def trusts_legacy_superuser() -> bool:
    """레거시 `superuser` 역할을 아직 전역으로 인정하는가 (기본 True · 무중단)."""
    return bool(getattr(settings, "TENANT_TRUST_LEGACY_SUPERUSER", True))


def tenant_admin_role_code(group_id: Any) -> str:
    """테넌트 운영 역할의 코드 규약 — `<prefix>_<group_id>`."""
    prefix = getattr(settings, "TENANT_ADMIN_ROLE_PREFIX", "tenant_admin")
    return f"{prefix}_{group_id}"


def _role_codes(user: Any) -> set[str]:
    roles = getattr(user, "roles", None)
    if not roles:
        return set()
    return {code for code in roles.values_list("code", flat=True) if code}


def is_global_admin(user: Any) -> bool:
    """테넌트 경계를 넘어도 되는가. **이 질문의 답은 여기서만 낸다.**"""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return bool(_role_codes(user) & global_admin_role_codes())


def global_admin_reason(user: Any) -> str | None:
    """왜 전역으로 판정됐는가 — 로그·감사용. 전역이 아니면 None.

    회수 작업 중에는 "아직 레거시로 통과하고 있는 계정"을 세어야 한다.
    그 계수를 사람이 눈으로 세지 않게 하려고 사유를 문자열로 돌려준다.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False):
        return "db-flag"
    codes = _role_codes(user)
    explicit = codes & set(getattr(settings, "TENANT_GLOBAL_ADMIN_ROLE_CODES", []) or [])
    if explicit:
        return "role:" + ",".join(sorted(explicit))
    if LEGACY_GLOBAL_ROLE_CODE in codes and trusts_legacy_superuser():
        return "legacy-superuser"
    return None


def is_tenant_admin(user: Any) -> bool:
    """자기 테넌트를 관리하는 역할인가 (경계는 넘지 못한다).

    역할 코드가 맞아도 **그 역할의 group 이 요청자의 group 과 다르면 거짓**이다.
    코드 문자열만 보고 통과시키면 다른 테넌트의 admin 역할을 얻어 붙이는 경로가 열린다.

    ★ P-146 · SEC-22 — `config/k3_roles.py::K3_ROLES_WITH_TENANT_SETTINGS_ACCESS`
      (지금 값은 `admin` 하나)도 **자기 소속 안에서만** 이 판정을 받는다. 계정마다
      `tenant_admin_<group_id>` 역할을 따로 만들어 붙이지 않는다 — 그 붙이기는
      게이트의 증거이지 제품의 증거가 아니었다(evidence/P-141). 매핑은 저 표
      **한 곳**에 적혀 있고(표를 두 벌 두지 않는다 · D-212), 여기서는 **읽기만** 한다.
      판정식은 여전히 이 함수 하나다 — 늘어난 것은 "어떤 역할 코드를 인정하는가"
      뿐이고, "테넌트 경계를 넘는가"는 그대로 이 함수가 정한다.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    from common.tenant_filters import get_user_group  # 순환 import 회피 — 호출 시점에만

    group = get_user_group(user)
    if group is None:
        return False
    codes = _role_codes(user)
    if tenant_admin_role_code(group.id) in codes:
        return True
    from config.k3_roles import (  # noqa: PLC0415  (표를 두 벌 두지 않기 위해 지연 임포트)
        K3_ROLES_WITH_TENANT_SETTINGS_ACCESS,
    )

    return bool(codes & set(K3_ROLES_WITH_TENANT_SETTINGS_ACCESS))
