# -*- coding: utf-8 -*-
"""표 ① 임계값 커널 — **한 번 만들어 네 절을 갚는 표 둘 중 첫째** (D-325).

무엇이 여기 있고 무엇이 DB 에 있나
----------------------------------
    여기(코드)  정의 — 항목 · 기본값 · 단위 · 적용 범위 · 왜 이 값인가 · 계약 근거
    DB          그 정의를 **덮어쓴 값**과 **변경 이력** (`ThresholdSetting` · `ThresholdChange`)

나눈 이유: 정의는 개발이 정하고(커밋으로 바뀐다), 값은 운영이 정한다(화면으로 바뀐다).
한 표에 두면 운영이 정의를 지울 수 있고, 지워진 정의는 코드가 부를 때 터진다.

★ 계약이 못박은 값은 **덮을 수 없다** (`contract_fixed`)
--------------------------------------------------------
F-04 「동일 이벤트 5분 내 중복 알림 0건」 · F-10 「30초 내 발송」은 취향이 아니라 계약이다.
표에 두는 이유는 값이 한 곳에 보이게 하기 위해서이지 고치라고 둔 것이 아니다.
**설정 한 줄로 계약을 어길 수 있으면 그 계약은 코드에서 사라진 것이다.**
이 구별이 없으면 "임계값을 설정 가능하게 만들었다" 가 곧 "계약 AC 를 설정 가능하게
만들었다" 가 된다 — 표가 갚으려던 절을 표가 부수는 모양이다.

★ 값이 아직 없는 항목은 **기본값을 지어내지 않는다** (D-280 · D-284)
--------------------------------------------------------------------
`waterlevel.baseline` 이 그 자리다. F-02 가 요구하는 것은 **지점별** 기준선이고,
전역 기본을 지금 하나 적어 두면 그 숫자가 곧 F-02 의 AC 판정 근거가 된다.
그래서 `default=None` 으로 두고, 값이 없으면 `ThresholdNotSet` 으로 멈춘다.
Zone 의 `geometry_status='not_implemented'` 와 같은 대칭이다(D-299).

★ 이 표가 전수(610건)를 다 옮기는 표가 아니다
---------------------------------------------
2026-09-06 착수 전 실측(D-301): 하드코딩 임계값 **610건 / backend 비시험 549파일**,
계약 기능 면 **127건**. 610 은 **분모**이지 이사 목록이 아니다.
표가 갖는 것은 **계약 AC 가 이름을 대는 값**과 **운영이 바꿔야 하는 값**뿐이다.
나머지는 코드에 있는 것이 맞다 — 표에 넣으면 아무도 안 보는 행이 늘고, 늘어난 행은
표를 못 읽게 만든다. 새로 태어나는 매직 넘버는 `scripts/verify_threshold_table.py`
래칫이 잡는다(D-311).
"""
from __future__ import annotations

from dataclasses import dataclass

#: 적용 범위. **좁은 것이 이긴다** — camera → tenant → global.
SCOPE_GLOBAL = "global"
SCOPE_TENANT = "tenant"
SCOPE_CAMERA = "camera"
SCOPE_LEVELS = (SCOPE_GLOBAL, SCOPE_TENANT, SCOPE_CAMERA)


@dataclass(frozen=True)
class ThresholdDef:
    """임계값 하나의 **정의**. 값이 아니라 값이 무엇인지에 대한 진술이다."""

    key: str
    title: str
    unit: str
    #: `None` = **기본값이 아직 없다.** 「0 이다」가 아니다 (D-290).
    default: float | None
    #: 어느 층까지 덮어쓸 수 있는가. `global` 만이면 전역 하나뿐이다.
    applies_to: str
    #: 계약이 못박은 값인가. 참이면 **어떤 층에서도 덮을 수 없다.**
    contract_fixed: bool
    #: 어느 계약 절이 이 값을 이름으로 대는가. 없으면 빈 문자열.
    clause: str
    #: 왜 이 값인가. 비울 수 없다 — 사유 없는 임계값은 다음 사람에게 마법의 숫자다.
    why: str
    #: 코드 어디가 이 값을 읽는가. **표와 코드가 갈리는 것을 막는 유일한 끈**이다.
    used_by: tuple[str, ...]


#: ★ 표 ① — 첫 등재. **계약 AC 가 이름을 대는 값 + 운영이 바꿔야 하는 값**만 올린다.
#:
#: 여기 없는 임계값이 코드에 많다(실측 610). 그것들이 여기 없는 것은 누락이 아니라
#: 판정이다 — 계약도 운영도 그 값을 부르지 않기 때문이다. 부르게 되는 날 올린다.
THRESHOLDS: dict[str, ThresholdDef] = {
    "event.dedup_window": ThresholdDef(
        key="event.dedup_window",
        title="기록 단계 중복 억제창",
        unit="seconds",
        default=10,
        applies_to=SCOPE_TENANT,
        contract_fixed=False,
        clause="",
        why="같은 프레임에서 연달아 나는 탐지를 한 이벤트로 접는다. **계약이 부른 값이 "
            "아니라 우리 판단**이므로 현장에 따라 달라질 수 있다. F-04 의 5분과 다른 값이고, "
            "둘을 한 칸에 두면 기록과 알림이 같은 규칙이 된다(K1 이 나눈 이유).",
        used_by=("kernels/k1_event/services.py:DEDUP_WINDOW",),
    ),
    "notify.suppress_window": ThresholdDef(
        key="notify.suppress_window",
        title="알림 중복 억제창",
        unit="minutes",
        default=5,
        applies_to=SCOPE_GLOBAL,
        contract_fixed=True,
        clause="F-04 「동일 이벤트에 대해 5분 내 중복 알림 0건」",
        why="**계약 인용값이다.** 표에 두는 이유는 값이 한 곳에 보이게 하기 위해서이고, "
            "고치라고 둔 것이 아니다. 늘리면 계약 위반이고 줄이면 시험이 재는 것이 달라진다.",
        used_by=("kernels/k2_notify/schemas.py:SUPPRESS_WINDOW",
                 "kernels/k1_event/services.py:NOTIFY_WINDOW"),
    ),
    "notify.max_latency": ThresholdDef(
        key="notify.max_latency",
        title="알림 발송 상한",
        unit="seconds",
        default=30,
        applies_to=SCOPE_GLOBAL,
        contract_fixed=True,
        clause="F-10 「심각 등급 이벤트 발생 후 30초 내에 … 발송 기록을 남긴다」",
        why="**계약 인용값이다.** F-02 의 「30초 내 이벤트 생성」과 숫자가 같지만 재는 "
            "구간이 다르다 — 같아 보이는 두 값을 한 칸에 두지 않는다(D-290).",
        used_by=("kernels/k2_notify/schemas.py:F10_MAX_LATENCY",),
    ),
    "notify.email_timeout": ThresholdDef(
        key="notify.email_timeout",
        title="메일 채널 타임아웃",
        unit="seconds",
        default=10,
        applies_to=SCOPE_TENANT,
        contract_fixed=False,
        clause="",
        why="저하 운전의 값이다 — 메일 서버가 느려도 **화재 판정은 살아야 한다**(K5 규약 ④). "
            "고객 메일 서버 사정에 따라 달라지므로 테넌트까지 연다.",
        used_by=("kernels/k2_notify/channels.py:FALLBACK_EMAIL_TIMEOUT",),
    ),
    "waterlevel.baseline": ThresholdDef(
        key="waterlevel.baseline",
        title="지점별 수위 기준선",
        unit="cm",
        #: ★ **없다.** 지어내면 그 숫자가 곧 F-02 의 AC 판정 근거가 된다 (D-280).
        default=None,
        applies_to=SCOPE_CAMERA,
        contract_fixed=False,
        clause="F-02 「수위선 초과 신호로부터 30초 내에 이벤트를 생성한다 (지점별 기준선 설정)」",
        why="계약이 **지점별**이라고 못박았다. 하천 지점마다 범람 수위가 다르므로 전역 "
            "기본이라는 것이 성립하지 않는다 — 그래서 기본값을 두지 않고, 값이 없으면 "
            "`ThresholdNotSet` 으로 멈춘다. 「기본값 0」은 「기준선이 0cm」로 읽히고 "
            "그러면 모든 신호가 초과가 된다.",
        used_by=(),
    ),
}


def _definition(key: str):
    """정의 하나. 없으면 `ThresholdNotDefined` — 오타가 새 임계값이 되지 않게."""
    from kernels.k5_trust.exceptions import ThresholdNotDefined

    try:
        return THRESHOLDS[key]
    except KeyError:
        raise ThresholdNotDefined(
            f"임계값 키 {key!r} 는 표 ①에 없다. 있는 키: {', '.join(sorted(THRESHOLDS))}. "
            f"새 임계값은 여기 정의를 먼저 올린다 — 정의 없는 값은 아무도 검토한 적이 없다"
        ) from None
