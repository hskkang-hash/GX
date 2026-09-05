# -*- coding: utf-8 -*-
"""역할↔메뉴 **연결**의 자리 — UX-21 집행 (P-40 승인).

왜 이 파일이 생겼나
-------------------
UX-21 은 「관제 역할 메뉴에 드론·항공·영문 CRUD 0개」다. 턴 B 에 그것이
막혔던 이유는 **등재의 정본이 우리 코드가 아니었기** 때문이다 —
사이드바는 서버가 준 목록으로 그리고, 그 목록은 dj-core 의
`core.menu.models.Menu` 행에서 나온다(§0.4 · 우리가 코드를 못 고친다).

P-40 이 연 것은 **코드가 아니라 데이터**다:

    끊는 것은 「역할 ↔ 메뉴 연결」(`core.menu.models.RoleMenu`)뿐이다.
    **메뉴 행도 라우트도 지우지 않는다.**

그래서 이 일은 삭제가 아니라 **되돌릴 수 있는 데이터 작업**이고,
관리 명령 두 벌(끊기 · 되잇기)로 만든다. 시드처럼 다시 돌릴 수 있다.

무엇을 끊나 — 이 표가 정본이다
------------------------------
아래 두 상수가 「무엇을」과 「누구에게서」다. 표를 코드에 두는 이유는
**되돌리는 쪽이 같은 표를 봐야** 하기 때문이다(두 벌이 되면 반드시 어긋난다).

어떻게 되돌리나
---------------
끊을 때 **바꾸기 전의 네 칸을 장부에 적는다**(`menu_unlink_ledger.json`).
되잇기는 그 장부를 그대로 되돌려 쓴다 — 「원래 꺼져 있던 것」을 켜지 않는다.
표만 보고 되돌리면 **끊기 전부터 꺼져 있던 연결까지 켜 버린다.**
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

# ═══════════════════════════════════════════════════════════════════════════
# ① 무엇을 — 관제하는 사람의 화면이 아닌 인수 자산 8자리
#    [실측 2026-09-25 · 24장 중 9장 · PRD v2.6 §화면실사]
# ═══════════════════════════════════════════════════════════════════════════

#: 드론·항공 계열 — 재난 관제가 아니라 드론 운용의 화면이다.
UX21_DRONE_AVIATION_PATHS = (
    "/device",                # 드론 기체 등록 (Add New Device · Image · Color)
    "/notam",                 # 항공 고시보 (SNOWTAM)
    "/flight-log-analysis",   # 비행로그 분석 (Drone State Prediction)
    "/survey-profile",        # 조사 프로파일 (Add New Profile)
)

#: 영문 빈 CRUD 4장 — PRD v2.6 §화면실사 28행. 사용자의 언어가 아니다.
UX21_ENGLISH_CRUD_PATHS = (
    "/roles",                 # Add New Role
    "/menu",                  # Menu Management
    "/report-template",       # Usage Count
    "/media-data",            # bucket · No preview available.
)

UX21_MENU_PATHS = UX21_DRONE_AVIATION_PATHS + UX21_ENGLISH_CRUD_PATHS

# ═══════════════════════════════════════════════════════════════════════════
# ② 누구에게서 — U1·U2·U4 (관제하는 사람). U5 는 **유지**한다
#    역할 코드는 `backend/config/k3_roles.py` 의 실측 매핑을 그대로 쓴다 —
#    같은 매핑을 두 벌 적으면 반드시 어긋난다(D-212).
# ═══════════════════════════════════════════════════════════════════════════

from config.k3_roles import (  # noqa: E402  (표를 두 벌 두지 않기 위해 여기서 읽는다)
    K3_ROLE_OPERATORS,   # U1 관제요원
    K3_ROLE_MANAGERS,    # U2 관제팀장
    K3_ROLE_EXECUTIVES,  # U4 재난안전과 공무원 (열람 전용)
    K3_ROLE_SYSOPS,      # U5 시스템 관리자 — **끊지 않는다**
)

UX21_CONTROL_ROLE_CODES = tuple(K3_ROLE_OPERATORS) + tuple(K3_ROLE_MANAGERS) + tuple(K3_ROLE_EXECUTIVES)

#: U5 는 유지한다. 관리자는 인수 화면으로도 장비를 등록해야 하고,
#: 그 화면은 **한국어 헤더 한 줄로 감싼다**(UX-21 닫는 조건).
UX21_KEEP_ROLE_CODES = tuple(K3_ROLE_SYSOPS)

#: 끊는 것은 네 칸 전부다. `permit_read` 만 끄면 사이드바에서는 사라지는데
#: 「만들 수 있음」이 남는다 — **반만 끊긴 연결**은 다음 사람이 못 읽는다.
PERMIT_FIELDS = ("permit_read", "permit_create", "permit_update", "permit_delete")

#: 장부. `settings.BASE_DIR` 는 `backend/` 이므로 그 부모가 저장소 뿌리다
#: (컨테이너에서는 `/app` 의 부모 `/` 이고 `/docs` 마운트와 맞는다).
LEDGER_RELPATH = Path("docs") / "agent" / "evidence" / "UX-21" / "menu_unlink_ledger.json"


def default_ledger_path() -> Path:
    return Path(settings.BASE_DIR).parent / LEDGER_RELPATH


def target_role_menus(role_codes=None, paths=None, group_ids=None):
    """끊기·되잇기 두 명령이 **같은 눈**으로 보는 대상 집합.

    ★ `group_ids` 를 주면 **그 테넌트만** 본다. 안 주면 테넌트를 안 가린다 —
      그것은 기본값이 아니라 **부르는 쪽이 골라야 하는 것**이다(명령이 강제한다).
      [실측 2026-09-05] 이 표의 969행 중 926행이 테넌트를 갖는다(4·5·6·7).
      즉 **공용 마스터가 아니다** — 안 가리고 쓰면 남의 테넌트까지 친다.
    """
    from core.menu.models import RoleMenu  # dj-core — 읽기만 한다(§0.4)

    qs = RoleMenu.objects.filter(
        role__code__in=list(role_codes or UX21_CONTROL_ROLE_CODES),
        menu__path__in=list(paths or UX21_MENU_PATHS),
    ).select_related("role", "menu")
    if group_ids is not None:
        qs = qs.filter(group_id__in=list(group_ids))
    return qs


def live_link_count(role_codes=None, paths=None, group_ids=None) -> int:
    """지금 **살아 있는** 연결의 수 — 네 칸 중 하나라도 켜져 있으면 산다."""
    from django.db.models import Q

    q = Q()
    for f in PERMIT_FIELDS:
        q |= Q(**{f: True})
    return target_role_menus(role_codes, paths, group_ids).filter(q).count()


# ═══════════════════════════════════════════════════════════════════════════
# ③ **이 표는 누구 것인가** — 분류 등록부에 묻는다 (D-270 ③ · D-212)
# ═══════════════════════════════════════════════════════════════════════════
#: 우리가 쓰는 표. 등록부(`backend/tests/tenant_classification.py`)가 분류의
#: **유일한 출처**다 — 여기에 판정식을 복사하지 않는다.
WRITE_TARGET = "menu.RoleMenu"

#: 착수 시점에 등록부가 말한 분류. **기대를 코드에 적어 둔다** —
#: 나중에 누가 이 표를 `SHARED_MASTERS` 나 `TENANT_UNASSIGNED` 로 옮기면
#: 이 명령의 전제가 깨진 것이고, 그때 **조용히 도는 것이 가장 나쁘다.**
EXPECTED_CLASSIFICATION = "DEFERRED"


def _load_registry():
    """분류 등록부 모듈. **못 읽으면 통과시키지 않는다** — 「검사 못함」≠「대상 아님」.

    ★ 이름으로 못 찾으면 **파일로 찾는다.** 컨테이너는 `/repo` 와 `/app`(=backend)을
      따로 마운트해 `tests` 가 이름 공간에 없다 — 저장소가 이미 아는 함정이다.
    """
    try:
        from tests import tenant_classification as mod
        return mod
    except ImportError:
        pass
    import importlib.util
    from pathlib import Path as _P

    here = _P(__file__).resolve().parent.parent          # backend/
    for cand in (here / "tests" / "tenant_classification.py",
                 _P("/app") / "tests" / "tenant_classification.py"):
        if not cand.is_file():
            continue
        spec = importlib.util.spec_from_file_location("_tenant_classification", cand)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def classification_of(label: str = WRITE_TARGET):
    """`(분류 이름, 등록부가 적은 사유)`. 못 읽으면 `(None, 사유)`."""
    mod = _load_registry()
    if mod is None:
        return None, "분류 등록부를 못 읽었다"
    for name in ("SHARED_MASTERS", "TENANT_UNASSIGNED", "DEFERRED"):
        table = getattr(mod, name, {})
        if label in table:
            return name, table[label]
    return None, "등록부에 선언이 없다"


def assert_classification_unchanged(label: str = WRITE_TARGET,
                                    expected: str = EXPECTED_CLASSIFICATION):
    """분류가 착수 때와 같은지 본다. 다르면 **사유 문자열**을 돌려준다(=멈출 이유)."""
    got, why = classification_of(label)
    if got is None:
        return None, why, f"{label} 의 분류를 확인할 수 없다 — 확인 못 한 채로 쓰지 않는다"
    if got != expected:
        return got, why, (
            f"{label} 의 분류가 {expected} → **{got}** 으로 바뀌었다. "
            f"이 명령은 그 표가 아직 테넌트 소유로 확정되지 않았다는 전제 위에 서 있다 — "
            f"전제가 바뀌었으므로 멈춘다. 사람이 다시 판정해야 한다."
        )
    return got, why, None
