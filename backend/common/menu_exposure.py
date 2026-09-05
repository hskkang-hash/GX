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

표가 **둘**이 됐다 (2026-09-05 · P-50)
-------------------------------------
「무엇을」과 「누구에게서」가 한 쌍이 아니다. `/media-data` 는 두 판정 모두의
대상인데 **역할 집합이 다르다** — UX-21 은 U1·U2·U4, P-50 은 거기에 U5 까지.
그래서 표를 합치지 않고 **쌍의 목록**(`CUT_BUNDLES`)으로 둔다. 합치면 U5 가
`/device` 까지 잃고, 그것은 세종 P-40 이 남기라고 한 자리다.
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

#: U5 는 **이 묶음에서만** 유지한다. 관리자는 인수 화면으로도 장비를 등록해야 하고,
#: 그 화면은 **한국어 헤더 한 줄로 감싼다**(UX-21 닫는 조건).
#: ⚠ 2026-09-05 P-50 — 이 유지는 이제 **일곱 자리**다. `/media-data`(미디어 버킷)는
#:   장비를 등록하는 자리가 아니라 빈 버킷 브라우저이므로 아래 P-50 묶음이
#:   U5 에서도 끊는다. 「U5 는 다 남는다」로 읽으면 틀린다 — 묶음별로 다르다.
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


def is_live(row) -> bool:
    """네 칸 중 하나라도 켜져 있으면 그 연결은 **살아 있다**."""
    return any(getattr(row, f) for f in PERMIT_FIELDS)


def live_link_count(role_codes=None, paths=None, group_ids=None, bundles=None) -> int:
    """지금 **살아 있는** 연결의 수 — 네 칸 중 하나라도 켜져 있으면 산다.

    ★ 역할·경로를 **안 주면 묶음 표 전부**를 센다(UX-21 + P-50). 묶음마다 역할
      집합이 다르므로 한 벌의 역할·경로 곱으로는 셀 수 없다 — 그렇게 세면
      U5 의 `/device` 가 「안 끊긴 연결」로 잡혀서 `--check` 가 영영 빨강이다.
    """
    if role_codes is None and paths is None:
        return sum(1 for r, _ in all_target_role_menus(group_ids, bundles) if is_live(r))

    from django.db.models import Q

    q = Q()
    for f in PERMIT_FIELDS:
        q |= Q(**{f: True})
    return target_role_menus(role_codes, paths, group_ids).filter(q).count()


# ═══════════════════════════════════════════════════════════════════════════
# ③ P-50 — 레거시 화면 셋. **U5 에서도 끊는다** (2026-09-05 턴 E · 상용 점검 §8)
#
#    턴 C 는 U5 를 남겼다 — 「관리자는 인수 화면으로도 장비를 등록해야 한다」.
#    상용 점검이 반박했다: **관제 제품인데 인수 자산 화면이 그대로 보인다.**
#    셋은 장비 등록의 자리가 아니라 **대체된 화면**이거나 **고장난 화면**이다.
#
#      /surveillance-dashboard  레거시 감시 대시보드 — 스켈레톤 고착 · 전국 지도
#                               (PRD v2.6 §화면실사 25행 · DA-03 §0-1 의 그 증상)
#      /media-data              미디어 버킷 브라우저 — bucket · No preview available
#                               (같은 표 28행. UX-21 8자리에도 있으나 **U5 에 남아 있었다**)
#      /multi-stream-monitor    드론 다중 스트림 — 기체 3대 검은 타일 · 0 Participants
#                               (같은 표 26행. **UX-23 카메라 격자가 대체한다**)
#
#    ★ 넷째 자리 「Media Viewer」는 화면이 아니라 **묶음 마디**다. 그런데 dj-core 의
#      `list_menus` 는 묶음을 「자식이 남았으니 보인다」가 아니라 **제 행의
#      `permit_read` 로도** 보인다(`permitted ∪ 부모들`). 그리고 이 묶음의 자식은
#      다중 스트림 **하나뿐**이다 [실측 2026-09-05 · Menu 76 의 자식 1개].
#      자식만 끊으면 사이드바에 **아무 데도 못 가는 「Media Viewer」 한 줄**이 남는다 —
#      경로가 `Media Viewer` 라는 문자열이라 눌러도 라우트가 없다.
#      그래서 묶음도 함께 끊는다. **행은 그대로 있고 칸만 꺼진다**(되돌릴 수 있다).
# ═══════════════════════════════════════════════════════════════════════════

#: 레거시 감시 대시보드 — 스켈레톤 고착.
P50_LEGACY_DASHBOARD_PATHS = ("/surveillance-dashboard",)

#: 미디어 버킷 브라우저. UX-21 8자리와 **겹친다** — 겹치는 것이 이 판정의 요점이다.
#: UX-21 은 U1·U2·U4 에서만 끊었고, P-50 은 **U5 까지** 끊는다.
P50_MEDIA_BUCKET_PATHS = ("/media-data",)

#: 드론 다중 스트림과 그 묶음 마디. UX-23 카메라 격자(`/dsm/cameras/grid`)가 대체한다.
P50_DRONE_MULTISTREAM_PATHS = ("/multi-stream-monitor", "Media Viewer")

P50_LEGACY_PATHS = (
    P50_LEGACY_DASHBOARD_PATHS + P50_MEDIA_BUCKET_PATHS + P50_DRONE_MULTISTREAM_PATHS
)

#: **U5 를 포함한** 관제 역할 전부. 이것이 UX-21 과 P-50 을 가르는 유일한 차이다.
P50_ROLE_CODES = UX21_CONTROL_ROLE_CODES + tuple(K3_ROLE_SYSOPS)

#: 끊지 않는 역할. `superuser` 는 여기 안 적는다 — 전역 관리자 판정은
#: `common/tenant_roles.is_global_admin` 한 곳이 한다(D-212). 판정식을 두 벌 두면
#: 반드시 어긋난다. **그래서 superuser 에게는 이 셋이 그대로 보인다**(알고 남긴다).
P50_KEEP_ROLE_CODES = ()

# ═══════════════════════════════════════════════════════════════════════════
# ③-2 묶음 표 — 「무엇을 · 누구에게서」 쌍이 **둘**이 됐다
#
#    한 표에 합칠 수 없다. `/media-data` 는 두 묶음 모두에 있는데 역할 집합이
#    다르고, 합치면 U5 가 `/device` 까지 잃는다 — 세종 P-40 이 남기라 한 자리다.
#    그래서 표를 **쌍의 목록**으로 둔다. 끊기·되잇기가 같은 목록을 본다.
# ═══════════════════════════════════════════════════════════════════════════

CUT_BUNDLES = (
    {
        "id": "UX-21",
        "why": "인수 자산 8자리 — 드론·항공 4 · 영문 빈 CRUD 4 (세종 P-40)",
        "paths": UX21_MENU_PATHS,
        "roles": UX21_CONTROL_ROLE_CODES,
        "keep": UX21_KEEP_ROLE_CODES,
    },
    {
        "id": "P-50",
        "why": "레거시 화면 셋 — 감시 대시보드 · 미디어 버킷 · 드론 다중 스트림 "
               "(+묶음 마디). **U5 에서도 끊는다** (세종 P-50 · 상용 점검 §8)",
        "paths": P50_LEGACY_PATHS,
        "roles": P50_ROLE_CODES,
        "keep": P50_KEEP_ROLE_CODES,
    },
)

BUNDLE_IDS = tuple(b["id"] for b in CUT_BUNDLES)


def bundles_by_id(ids=None):
    """묶음을 이름으로 고른다. 없는 이름은 **조용히 넘기지 않는다.**"""
    if not ids:
        return CUT_BUNDLES
    want = list(ids)
    unknown = [i for i in want if i not in BUNDLE_IDS]
    if unknown:
        raise KeyError("모르는 묶음: %s (있는 것: %s)"
                       % (" ".join(unknown), " ".join(BUNDLE_IDS)))
    return tuple(b for b in CUT_BUNDLES if b["id"] in set(want))


def bundle_role_menus(bundle, group_ids=None):
    """묶음 하나의 대상 행."""
    return target_role_menus(bundle["roles"], bundle["paths"], group_ids)


def all_target_role_menus(group_ids=None, bundles=None):
    """묶음들을 합친 대상 행 — **한 행은 한 번만** 나온다(`/media-data` 가 겹친다).

    돌려주는 것은 `(행, 묶음 이름)` 쌍의 목록이다. 장부에 「어느 판정으로 끊었나」를
    적어야 다음 사람이 되돌릴 범위를 고를 수 있다.
    """
    seen, out = set(), []
    for b in (bundles or CUT_BUNDLES):
        for r in bundle_role_menus(b, group_ids):
            if r.pk in seen:
                continue
            seen.add(r.pk)
            out.append((r, b["id"]))
    return out


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
