# -*- coding: utf-8 -*-
"""제품 화면이 **사이드바에 서는 자리** — UX-25 집행 (세종 P-61).

왜 이 파일이 생겼나 — **빼는 일만 하고 있으면 더할 것이 없다는 사실이 안 보인다**
--------------------------------------------------------------------------------
UX-21·P-50 은 「관제하는 사람의 화면이 아닌 것」을 사이드바에서 **끊는** 일이었고
그 일은 잘 됐다(`menu_exposure.py` · 삭제 0 · 왕복 실측). 그런데 끊을수록 사이드바는
0 에 가까워졌다 — **더할 것이 애초에 없었기 때문이다.**

    [실측 2026-09-05 · 턴 E] `/dsm/*` · `/wall` · `/start` 로 시작하는 메뉴 행이
    dj-core `Menu` 표 131행 중 **하나도 없다.** 씨 뿌리는 코드도 저장소에 없었다.
    즉 관제요원이 우리 제품에 닿으려면 **URL 을 직접 쳐야 했다.**

    [실측 2026-09-05 · 턴 F 착수 전 · 실제 로그인 · GET /api/menu/menus]
      gxseed_u1_operator (U1 fire_user)          12행 — 제품 화면 **0장**
      gxseed_u2_manager  (U2 fire_admin)         14행 — 제품 화면 **0장**
      gxseed_u4_official (U4 view_only_-_anyang) 24행 — 제품 화면 **0장**

세종 P-61 이 연 것은 **코드가 아니라 데이터**다 (UX-21 의 P-40 과 같은 모양):

    메뉴 정본은 dj-core DB 다 — **코드가 아니라 시드(데이터)로 넣는다**(§0.4 무수정).
    이름은 한국어. 순서는 **하루에 누르는 횟수 순**.

그래서 이 파일은 **표**이고, 표를 DB 로 옮기는 것은 `ensure_product_menus()` 하나다.
`Menu` 모델도 dj-core 코드도 한 줄 안 고친다 — **행을 넣기만 한다.**

★ 왜 행에 소속(`group`)을 안 붙이나 — **붙일 수가 없다** (실측이 그렇게 말했다)
-------------------------------------------------------------------------------
처음 설계는 「테넌트마다 한 벌」이었다. 실측이 그것을 막았다:

  ① `RoleMenu` 는 `unique_together = ('menu', 'role')` 이다. 같은 (메뉴, 역할) 쌍의
     행은 **온 DB 에 하나뿐**이다 — 테넌트마다 연결을 따로 둘 수 없다.
  ② dj-core `list_menus` 는 메뉴를 **소속으로 가리지 않는다.**
     [실측 2026-09-05] 소속 4(ETRI-Group)의 U1 계정이 소속 6·7 의 메뉴 행
     (#128 · #130 · #101 · #104 · #96)을 **그대로 본다.**
     즉 테넌트마다 한 벌씩 심으면 **모든 테넌트의 사본이 모두에게 보인다** —
     테넌트 열 곳이면 「지금 처리할 것」이 사이드바에 열 줄 뜬다.

그래서 정본은 **소속 없는 한 벌**(`group=None`)이다. 지금 DB 의 131행 중 53행이
이미 그 모양이고(`Dashboard` · `Surveillance` · `사용자 관리` …), 그 53행은 모든
테넌트에서 보인다. 우리 행도 같은 자리에 선다.

★ 그러면 「테넌트가 생기면 함께 선다」는 무엇으로 닫히나
------------------------------------------------------
**구조로 닫힌다.** 소속 없는 한 벌이므로 새 테넌트는 만들어지는 순간 이미 그것을 본다.
그래도 신호를 하나 단다(`product_menu_signals.py`) — 이유는 둘이다:

  · 표가 늘었는데 아무도 시드를 다시 안 돌린 채 테넌트가 생기는 날이 온다.
    그날 새 테넌트는 **옛 표**를 본다. 신호는 그 자리를 멱등으로 메운다.
  · 새 테넌트가 **자기 역할을 새로 만들면**(이 DB 의 `role_role` 은 소속을 갖는다 —
    `fire_user` 는 소속 6, `surveillance_order` 는 소속 5) 그 역할에는 아직 연결이
    없다. `Role` 이 생길 때도 같은 함수를 부른다.

즉 신호는 「없으면 만든다」가 아니라 **「빠진 것을 메운다」**이고, 두 번 돌아도 행이
안 겹친다(멱등). 겹치지 않는 근거는 아래 `_find_row` 한 곳이다.

★ 표에 없는 것도 판정이다 (D-264 · D-301)
-----------------------------------------
P-61 이 적은 스물한 자리 중 **여덟 자리는 화면이 없다.** 없는 화면에 메뉴를 걸면
사이드바에 **눌러도 아무 데도 안 가는 줄**이 생긴다 — `menu_exposure.py` 가
「Media Viewer」에서 이미 만난 고장이고, 그 줄은 「메뉴가 있다」와 구별되지 않는다.
그래서 안 건 자리의 이름을 `P61_NO_SCREEN_YET` 에 적는다. **면제가 아니라 선언이다.**
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════
# ① 역할 묶음 — 코드는 `config/k3_roles.py` 한 곳에서 온다
#    ★ 여기에 역할 코드를 적지 않는다(D-212·D-369). 두 벌이 되면 반드시 어긋나고,
#      어긋나면 「역할에 없는 메뉴는 렌더하지 않는다」가 조용히 무너진다.
#    ★ 임포트를 **함수 안**에 둔 이유: 이 모듈은 판정기(`scripts/verify_sidebar.py`)가
#      Django 없이 호스트에서도 읽는다. `config` 패키지는 임포트만으로 celery 를 세운다.
# ═══════════════════════════════════════════════════════════════════════════

#: P-61 의 사람 넷. 표는 이 열쇠로만 말한다 — 역할 코드는 아래 함수가 푼다.
U1, U2, U4, U5 = "U1", "U2", "U4", "U5"

#: 사람 이름 — 보고와 판정기가 같은 말을 쓰기 위한 사전.
BUCKET_LABEL = {
    U1: "관제요원",
    U2: "관제팀장",
    U4: "재난안전과",
    U5: "관리자",
}


def role_codes_for(bucket: str) -> tuple:
    """묶음 하나의 역할 코드. **정본은 `config.k3_roles` 다.**"""
    from config.k3_roles import (  # noqa: PLC0415  (호스트 임포트를 막지 않기 위해 지연)
        K3_ROLE_EXECUTIVES,
        K3_ROLE_MANAGERS,
        K3_ROLE_OPERATORS,
        K3_ROLE_SYSOPS,
    )

    return {
        U1: tuple(K3_ROLE_OPERATORS),
        U2: tuple(K3_ROLE_MANAGERS),
        U4: tuple(K3_ROLE_EXECUTIVES),
        U5: tuple(K3_ROLE_SYSOPS),
    }[bucket]


# ═══════════════════════════════════════════════════════════════════════════
# ② 표 — **이것이 정본이다**
#
#    순서: 세종 P-61 「하루에 누르는 횟수 순」. 위에 있는 것이 더 자주 눌린다.
#    `ordering` 이 **음수**인 이유: dj-core 가 심어 둔 기존 뿌리 행들은 0 이상이고
#    (`Dashboard` 0 · `Surveillance` 3 · `Admin` 100), 정렬은 `order_by('ordering')`
#    하나다. 제품 화면은 인수 자산 위에 서야 하므로 음수 자리를 쓴다.
#    ⚠ 기존 행의 `ordering` 을 **고치지 않는다** — 남의 행을 만지면 되돌릴 수 없다.
#
#    `icon`: **이미 이 DB 에 쓰이고 있는 이름만** 골랐다. 앞판이 못 푸는 이름을 넣으면
#    아이콘 자리가 빈칸이 되고, 빈칸은 「아이콘이 없는 메뉴」와 구별되지 않는다.
#    [실측 2026-09-05] 쓰이는 이름 열아홉 개 중에서 고른 것이다.
# ═══════════════════════════════════════════════════════════════════════════

#: 한 줄의 모양: (경로, 한국어 이름, 아이콘, 이 줄을 보는 묶음들, 왜 이 자리인가)
PRODUCT_MENUS: tuple[dict, ...] = (
    {
        "path": "/dsm/queue",
        "name": "지금 처리할 것",
        "icon": "Bs1Square",
        "buckets": (U1, U2),
        "why": "W1 최상단. 관제요원이 하루에 가장 많이 누르는 자리다(UX-13 단일 초점 큐).",
    },
    {
        "path": "/dsm/events",
        "name": "무슨 일 있었나",
        "icon": "BsColumnsGap",
        "buckets": (U1, U2, U4),
        "why": "이벤트 목록. U4 는 이 화면 하나로 「지난 이레」를 본다.",
    },
    {
        "path": "/dsm/cameras/grid",
        "name": "카메라 격자",
        "icon": "BsCameraVideo",
        "buckets": (U1, U2),
        "why": "격자·자동 순회(UX-23). 큐 다음으로 오래 떠 있는 화면이다.",
    },
    {
        "path": "/handover",
        "name": "인계 메모",
        "icon": "BsPeople",
        "buckets": (U1, U2),
        "why": (
            "교대마다 한 번. ★ 인수 화면 `/handover` 를 **가리키기만 한다** — "
            "기존 행 #38 『Handover』(ko 인수인계)를 고치지 않는다. 그 행은 U4 가 이미 "
            "보고 있고, 남의 행을 고치면 되돌릴 수 없다."
        ),
    },
    {
        "path": "/start",
        "name": "처음이세요",
        "icon": "BsCompass",
        "buckets": (U1, U2),
        "why": "첫 근무일에 한 번(UX-03 온보딩). 자주 눌리지 않으므로 아래에 둔다.",
    },
    {
        "path": "/dsm/dashboard",
        "name": "관제 현황",
        "icon": "BsBarChartLine",
        "buckets": (U2,),
        "p61_gap": (
            "P-61 은 U2 자리에 **「요원별 현황」**을 적었다. 그 화면은 없다. 가장 가까운 "
            "것이 관제 대시보드(5상태의 분모·분자 · 연계 상태)이고, **그 이름으로** 건다. "
            "「요원별」이라 적으면 없는 것을 있다고 말하는 것이다."
        ),
        "why": "팀장이 아침·교대에 한 번씩 본다.",
    },
    {
        "path": "/dsm/drill",
        "name": "훈련 모드",
        "icon": "BsBinoculars",
        "buckets": (U2, U5),
        "why": "훈련 때만(UX-17). 달에 몇 번이다.",
    },
    {
        "path": "/dsm/privacy-requests",
        "name": "열람·삭제 청구",
        "icon": "BsSearch",
        "buckets": (U4,),
        "why": "청구가 들어올 때만(LAW-07). U4 의 자리다.",
    },
    {
        "path": "/dsm/cameras/import",
        "name": "카메라 일괄 등록",
        "icon": "BsBoxes",
        "buckets": (U5,),
        "why": "설치·증설 때만(UX-18).",
    },
    {
        "path": "/dsm/metering",
        "name": "이번 달 사용량",
        "icon": "BsDatabase",
        "buckets": (U5,),
        "why": "달에 한 번(OPS-16 계량).",
    },
    {
        "path": "/dsm/system",
        "name": "보존·백업 설정",
        "icon": "BsGear",
        "buckets": (U5,),
        "why": (
            "P-67 — 보존 일수·백업 목적지·일정에 **코드 기본값이 없다.** 선언하지 "
            "않은 항목은 이 화면에 빨강 「미선언」으로 뜨고, 그 상태에서는 파기도 "
            "백업도 돌지 않는다. 자주 눌리는 자리는 아니지만 **한 번도 안 보면 "
            "안 되는 자리**라 사이드바에 건다. "
            "★ 턴 F 에는 이 줄을 안 걸었다 — 그때는 화면이 없었기 때문이다"
            "(아래 P61_NO_SCREEN_YET 의 「백업·보존」). 화면이 생긴 턴에 옮겼다. "
            "⚠ 아이콘 `BsGear` 는 이 DB 에 아직 안 쓰인 이름이다 — 그래서 "
            "앞판이 **정말 푸는지 확인하고** 넣었다 [실측 2026-09-06 · "
            "node_modules/react-icons/bs 에 BsGear 실재 · ReactIcon 이 그 묶음을 "
            "통째로 편다]. 확인 없이 넣었으면 아이콘 자리가 빈칸이 되고, 빈칸은 "
            "「아이콘 없는 메뉴」와 구별되지 않는다."
        ),
    },
)

#: 첫 줄이 앉는 자리. 뒤로 갈수록 10 씩 커진다(= 아래로 내려간다).
ORDERING_BASE = -1000
ORDERING_STEP = 10

#: 뿌리 행이다 — 묶음 마디 아래 넣지 않는다. 넣으면 그 마디(예: 『Operator』)까지
#: 사이드바에 끌려 나오고, 그 마디는 우리 것이 아니다.
DEPTH = 0


def rows_for(bucket: str) -> tuple[dict, ...]:
    """묶음 하나가 **보는** 줄들. 순서는 표 순서(=하루에 누르는 횟수 순)."""
    return tuple(r for r in PRODUCT_MENUS if bucket in r["buckets"])


def expected_counts() -> dict:
    """묶음별 **기대 행 수**. 판정기가 실측과 맞대는 수다."""
    return {b: len(rows_for(b)) for b in (U1, U2, U4, U5)}


def ordering_of(row: dict) -> int:
    return ORDERING_BASE + PRODUCT_MENUS.index(row) * ORDERING_STEP


# ═══════════════════════════════════════════════════════════════════════════
# ③ **안 건 자리** — P-61 이 적었으나 화면이 없어서 못 건 여덟 (선언이다)
#
#    없는 화면에 메뉴를 걸면 「눌러도 아무 데도 안 가는 줄」이 생긴다.
#    `menu_exposure.py` 가 「Media Viewer」에서 만난 그 고장이다.
# ═══════════════════════════════════════════════════════════════════════════
P61_NO_SCREEN_YET = {
    "요원별 현황": "U2 — 화면 없음. `/dsm/dashboard`(관제 현황)로 **근사**해서 걸었다",
    "설정(임계값·알림 규칙·시험)": "U2 — 임계값·알림 규칙을 여는 우리 층 화면이 없다",
    "보고서(월간 1쪽·HWPX)": "U2·U4 — 월간 1쪽은 서버가 낸다. 그리는 화면이 없다",
    "이벤트 검색": "U4 — 목록의 거르개는 있으나 검색 화면이 따로 없다",
    "감사 기록": "U4 — 감사 기록을 보는 화면이 없다",
    "시스템(맥박·용량·생존)": "U5 — 운영 도구는 있으나 화면이 없다",
    "알림 규칙·채널": "U5 — 화면 없음(K2 규칙은 서버 자리다)",
    # ★ 「백업·보존」은 **이 표에서 나갔다** (2026-09-06 · 턴 G · P-67).
    #   `/dsm/system`(보존·백업 설정)이 그 자리를 채웠고, 위 PRODUCT_MENUS 에 섰다.
    #   ⚠ 여기 이름을 지운 것이 아니라 **자리를 옮긴 것**이다 — 지우기만 하면
    #     「P-61 이 적은 스물한 자리」의 셈이 조용히 하나 줄어든다.
}

#: 안 건 자리에서 **나간** 이름들 — 화면이 생겨 위 표로 옮겨 갔다.
#: 셈이 맞는지는 이 표를 함께 봐야 한다(선언은 지우는 것이 아니라 옮기는 것이다).
P61_SCREEN_ARRIVED = {
    "백업·보존": "→ `/dsm/system` 「보존·백업 설정」 (2026-09-06 턴 G · P-67)",
}

#: 사이드바에 **일부러 안 거는** 제품 화면. 없는 것이 아니라 **거기 두지 않기로 한 것**이다.
NOT_IN_SIDEBAR_BY_DECISION = {
    "/wall": "월 모드 — 대형 화면에는 마우스가 없다. `features/dsm/routes.ts` 가 그렇게 적어 두었다",
    "/dsm/cameras/address": "카메라 주소 채우기 — P-61 의 표에 없다. 표에 없는 것을 더하지 않는다",
    "/m/inbox": "이동 중 수신 — U3 의 자리이고 사이드바가 없는 화면이다",
}

#: 이미 DB 에 있어서 **새로 안 만드는** 자리. P-61 U5 의 「사용자·역할」·「기존 화면(래핑)」.
ALREADY_IN_DB = {
    "/users": "『User Management』(ko 사용자 관리) #3 — U5 가 이미 본다",
    "/roles": "『역할 관리』 #5 — 있다. UX-21 이 U1·U2·U4 에서만 끊었다",
}


# ═══════════════════════════════════════════════════════════════════════════
# ④ 표를 DB 로 — **행을 넣기만 한다**
# ═══════════════════════════════════════════════════════════════════════════
def _find_row(Menu, row: dict):
    """이 줄이 **이미 있는가.** 멱등의 근거는 여기 한 곳이다.

    열쇠는 (경로, 이름) 쌍이다. 경로만으로 찾으면 `/handover` 에서 **남의 행**
    (#38 『Handover』)을 우리 것으로 착각하고 그 행을 고쳐 버린다.

    ★ `_base_manager` 로 읽는다. `Menu.objects` 는 소속 거르개를 지나므로 요청 안에서
      돌 때(테넌트 생성 신호) **있는 행을 못 볼 수 있고**, 못 보면 같은 행을 또 만든다.
      「안 보인다」와 「없다」를 가르는 자리다(D-290).
    """
    return (
        Menu._base_manager.filter(
            path=row["path"], menu_name=row["name"], deleted__isnull=True)
        .order_by("id")
        .first()
    )


def _force_no_group(model, pk) -> None:
    """소속을 **비운다.**

    `BaseModel.save()` 는 요청이 있으면 만든 사람의 소속을 자동으로 채운다. 그것이
    맞는 모델이 대부분이지만 이 표는 아니다 — 소속이 붙는 순간 그 행은 「어느
    테넌트의 메뉴」가 되고, 위 머리말 ②의 이유로 그것은 **모두에게 보이는 사본**이 된다.
    그래서 저장 뒤에 한 번 비운다(`_base_manager` — 소속 거르개를 지나지 않는 문).
    """
    model._base_manager.filter(pk=pk).update(group=None)


def ensure_product_menus(*, dry_run: bool = False, log=None) -> dict:
    """표를 DB 에 세운다. **두 번 돌려도 행이 안 겹친다.**

    돌려주는 것은 「무엇을 했나」이지 「무엇이 보이나」가 아니다 — 보이는 것은
    판정기(`scripts/verify_sidebar.py`)가 **로그인해서** 잰다. 심은 쪽이 자기 일을
    세어 초록이라 말하는 것은 거짓 초록의 가장 흔한 모양이다(D-301).
    """
    from core.menu.models import Menu, RoleMenu  # dj-core — 읽고 **행만 넣는다**(§0.4)
    from core.role.models import Role

    say = log or (lambda *_a, **_k: None)
    result = {
        "menu_created": 0,
        "menu_updated": 0,
        "menu_unchanged": 0,
        "link_created": 0,
        "link_updated": 0,
        "link_unchanged": 0,
        "roles_missing": {},
        "rows": [],
    }

    for row in PRODUCT_MENUS:
        ordering = ordering_of(row)
        menu = _find_row(Menu, row)
        if menu is None:
            if dry_run:
                say("[dry-run] 새 행: %s → %s" % (row["name"], row["path"]))
                result["menu_created"] += 1
                continue
            menu = Menu.objects.create(
                menu_name=row["name"],
                path=row["path"],
                parent=None,
                depth=DEPTH,
                ordering=ordering,
                icon_name=row["icon"],
            )
            _force_no_group(Menu, menu.pk)
            result["menu_created"] += 1
            say("새 행 #%s %s → %s" % (menu.pk, row["name"], row["path"]))
        else:
            # 이미 있다. **자리와 아이콘만** 맞춘다 — 이름·경로는 열쇠라 안 건드린다.
            changed = []
            if menu.ordering != ordering:
                changed.append("자리 %s→%s" % (menu.ordering, ordering))
            if (menu.icon_name or "") != row["icon"]:
                changed.append("아이콘 %s→%s" % (menu.icon_name, row["icon"]))
            if menu.parent_id is not None:
                changed.append("뿌리로 올림")
            if changed and not dry_run:
                Menu._base_manager.filter(pk=menu.pk).update(
                    ordering=ordering, icon_name=row["icon"], parent=None,
                    depth=DEPTH, group=None,
                )
            if changed:
                result["menu_updated"] += 1
                say("고침 #%s %s — %s" % (menu.pk, row["name"], " · ".join(changed)))
            else:
                result["menu_unchanged"] += 1

        # ── 역할 연결 ────────────────────────────────────────────────────
        #    ★ 역할도 `_base_manager` 로 읽는다 — 이 DB 의 `role_role` 은 **소속을 갖고**
        #      (`fire_user` 는 소속 6), 소속 거르개를 지나면 다른 소속의 역할이 안 보인다.
        #      안 보이면 연결이 조용히 안 생기고, 사이드바는 그대로 비어 있다.
        for bucket in row["buckets"]:
            for code in role_codes_for(bucket):
                roles = list(Role._base_manager.filter(code=code, deleted__isnull=True))
                if not roles:
                    result["roles_missing"][code] = result["roles_missing"].get(code, 0) + 1
                    continue
                for role in roles:
                    link = RoleMenu._base_manager.filter(
                        menu=menu, role=role, deleted__isnull=True).first()
                    if link is None:
                        if dry_run:
                            result["link_created"] += 1
                            continue
                        link = RoleMenu.objects.create(
                            menu=menu, role=role,
                            permit_read=True, permit_create=False,
                            permit_update=False, permit_delete=False)
                        _force_no_group(RoleMenu, link.pk)
                        result["link_created"] += 1
                    elif not link.permit_read:
                        if not dry_run:
                            RoleMenu._base_manager.filter(pk=link.pk).update(permit_read=True)
                        result["link_updated"] += 1
                    else:
                        result["link_unchanged"] += 1

        result["rows"].append({
            "path": row["path"], "name": row["name"],
            "menu_id": getattr(menu, "pk", None),
            "ordering": ordering,
            "buckets": list(row["buckets"]),
        })

    return result
