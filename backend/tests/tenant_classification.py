# -*- coding: utf-8 -*-
"""테넌트 분류 등록부 — 소유가 없는 행을 **선언된 상태**로 만든다 (W0-13 · D-261).

왜 이 파일이 있나
------------------
W0-13 백필은 `group IS NULL` 30,200행을 셋으로 갈랐다(D-261). 그중 둘은 **채우지 않는다**:

  · **공용 마스터** — 채우면 다른 테넌트 화면에서 국가·시간대·상태값이 **사라진다**
  · **미사용(참조 0)** — 채우면 소유자를 **추측**하게 된다

문제는 둘 다 백필 후에도 `group IS NULL` 로 남는다는 것이다. 즉 **"공용이라서 비었다"와
"아직 안 정했다"가 DB 에서 구별되지 않는다.** 그 상태를 방치하면 미분류가 면제로 위장하고,
시험은 초록이 되고 노출은 그대로 남는다 — `PUBLIC_ROUTES` 도피로와 같은 모양이다.

★ 그래서 **여기에 선언하고, 격리 시험이 그 선언을 지킨다.**
  D-261 이 요구한 것이 이것이다 — "보류로 두지 말고 상태를 명시하라".

  · `SHARED_MASTERS`     기대값 = **전 테넌트가 조회 가능**해야 한다
  · `TENANT_UNASSIGNED`  기대값 = **전역 관리자 외 어떤 테넌트에도 비노출**이어야 한다

  **PUBLIC 은 검사 면제가 아니라 "공용임을 시험으로 증명한 것"이어야 한다** (D-261 c).

왜 컬럼(`is_system`)을 만들지 않았나
------------------------------------
그것이 D-209 ② 가 말한 정공법이지만 **스키마 변경 + 데이터 마이그레이션**이라 파괴적이고,
WP-2 EXIT 를 늦춘다. EXIT 는 WP-DA2 착수 조건이므로 전체 일정이 밀린다(P-DA-3 판정과 같은 논리).
지금은 **선언 + 시험**으로 같은 보장을 만들고, 컬럼 도입은 별건으로 둔다.
선언과 실제가 갈리면 시험이 실패한다 — 그것이 이 파일이 종이 조각이 되지 않는 이유다.

⚠ 이 파일에 모델을 **추가하는 것은 면제를 늘리는 일**이다. 근거 한 줄을 반드시 적는다.
  근거 없는 등재는 `NO_ROUTE` 와 같은 이유로 시험이 거부한다.
"""
from __future__ import annotations

#: 공용 마스터 — `group IS NULL` 이 **정상**이고, 전 테넌트가 봐야 한다.
#:
#: 근거: `docs/agent/evidence/W0-13/backfill_dryrun.md` §3-2 (약 2,000행 실측).
#: 이들은 `created_by`/`group` 열을 dj-core 베이스 모델에서 **물려받았을 뿐**이고
#: 내용은 전 테넌트 공용이다.
SHARED_MASTERS: dict[str, str] = {
    "user.Timezone":
        "IANA 시간대 목록(598행). 테넌트마다 다른 시간대 집합을 갖지 않는다",
    "user.Country":
        "국가 코드 목록(238행). 국제 표준이라 테넌트별로 갈리지 않는다",
    "user.CurrencyFormat":
        "통화 표기 규칙(31행). 통화는 테넌트 소유가 아니다",
    "advanced_table.GridSetting":
        "표 컬럼 기본 정의(928행). 화면 구성 마스터이며 업무 데이터가 아니다",
    "menu.UserMenu":
        "메뉴 트리 정의(60행). 무엇이 보이는가는 역할이 정하지 메뉴 행이 정하지 않는다",
    "menu.Tab":
        "탭 정의(27행). 같은 이유",
    "devices.FrameType":
        "기체 프레임 종류(24행). 장비 분류 마스터",
    "devices.Protocol":
        "통신 프로토콜 종류(17행). 장비 분류 마스터",
    "devices.FrameClass":
        "기체 등급(14행). 장비 분류 마스터",
    "orders.OrderItemType":
        "주문 품목 유형(15행). 코드 테이블",
    "delivery.DeliveryStatus":
        "배송 상태 코드(14행). 상태 열거값이라 테넌트별로 다르면 오히려 결함이다",
    "configuration.AdminConfig":
        "전역 관리 설정(11행). 정의상 전역이다",
}

#: 소유를 **정하지 않기로 선언한** 행이 있는 모델.
#: 백필 후에도 `group IS NULL` 로 남되, 그것은 "공용"이 아니라 **"주인 없음"** 이다.
#:
#: 근거: `backfill_dryrun.md` §3-1 — 역참조 8경로 전수 실측.
#: `terminals.Terminal` 3,399 중 단일소유 1,809 는 백필하고(D-261 b),
#: **참조가 0인 1,590 은 채우지 않는다** — 채우면 추측이 된다.
TENANT_UNASSIGNED: dict[str, str] = {
    "terminals.Terminal":
        "참조 0인 미사용 행. 역참조 8경로 전수 실측에서 다중 소유 0건 · 미사용 1,590행. "
        "숨겨도 업무에 영향이 없고, 채우면 소유자를 추측하게 된다 (D-261 b)",
}

#: 증가금지 래칫 — 선언된 '주인 없음' 행 수의 상한.
#: 이 수가 **늘면** 새로 만들어진 행이 주인 없이 쌓이고 있다는 뜻이다.
#: 줄어드는 것은 환영이다(누군가 소유를 정했다는 뜻).
#:
#: ⚠ 값은 **백필 적용 후 실측으로** 확정한다. 지금 값은 dry-run 예측치이고,
#:   적용 후 실측이 다르면 **그 차이가 곧 조사 대상**이다 — 조용히 맞추지 말 것.
UNASSIGNED_BASELINE: dict[str, int] = {
    "terminals.Terminal": 1590,
}

#: 이 등록부가 다루지 않는 것 — 별도 판단이 필요하다고 **명시**해 둔다.
#: 조용히 빠뜨리면 "안 봤다"와 "봐서 괜찮았다"가 구별되지 않는다.
DEFERRED: dict[str, str] = {
    "user.CoreUser":
        "소유 테넌트는 UserProfileLink.group 이 이미 말한다. created_by 문제와 별개다 — "
        "W0-16 역할 분리와 함께 본다 (backfill_dryrun.md §3-3)",
    "advanced_table.GridSettingUser":
        "사용자별 표 설정(3,230행). 마스터인지 사용자 데이터인지 갈린다 — 사람 판단 필요",
    "menu.RoleMenu":
        "역할↔메뉴 매핑(923행). 일부만 공용일 수 있다 (§3-3)",
    "menu.RoleTab":
        "역할↔탭 매핑(375행). 같은 이유",
    "file_management.UserMediaFile":
        "사용자 업로드 파일(1,077행). 업무 데이터일 가능성이 높다 — 공용으로 선언하면 안 된다",
}


def all_declared() -> set[str]:
    """선언된 전체 — 중복 선언은 결함이므로 시험이 잡는다."""
    return set(SHARED_MASTERS) | set(TENANT_UNASSIGNED) | set(DEFERRED)


def conflicts() -> set[str]:
    """두 곳 이상에 선언된 모델. 공용이면서 주인 없음일 수는 없다."""
    return (
        (set(SHARED_MASTERS) & set(TENANT_UNASSIGNED))
        | (set(SHARED_MASTERS) & set(DEFERRED))
        | (set(TENANT_UNASSIGNED) & set(DEFERRED))
    )
