# -*- coding: utf-8 -*-
"""K3 공개 면이 주고받는 모양 — **모델을 밖으로 내보내지 않는다** (DA-04 §1-4).

이 파일의 중심은 `WidgetState` 다. F-09 의 검수 기준이 *"5상태 100%"* 이고,
DA-03 §0 이 그 뜻을 고정했다:

    5상태는 **재난 등급이 아니라 화면 상태**다 (기본/로딩/빈/오류/권한없음).
    검수 기준은 **모든 위젯이 다섯 상태를 전부 정의·구현했는가**를 묻는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WidgetState(str, Enum):
    """F-09 의 5상태 (DA-03 §0 표 그대로).

    ★ **셋을 절대 합치지 않는다** — `EMPTY` · `ERROR` · `FORBIDDEN`.
      DA-03 §2-5 규칙 1: *"'빈'과 '오류'를 같은 문구로 쓰지 않는다. 데이터가 없는 것과
      못 가져온 것은 다른 사실이고, 관제요원의 다음 행동이 다르다 — 전자는 대기,
      후자는 신고."*
      D-290 이 서버 쪽에서 말한 것("없는 것과 실패한 것을 같은 값으로 표현하지 않는다")과
      **같은 문장**이다. 이 커널은 그것을 화면 쪽에서 지킨다.
    """

    DATA = "data"            # 기본 — 정상 데이터 있음
    LOADING = "loading"      # 로딩 — 요청 진행 중. **서버는 이 값을 내지 않는다** (아래 ★)
    EMPTY = "empty"          # 빈 — 요청 성공 · 데이터 0건
    ERROR = "error"          # 오류 — 요청 실패
    FORBIDDEN = "forbidden"  # 권한없음 — 403. 기본은 **미렌더**다


#: ★ 서버가 낼 수 없는 상태. `LOADING` 은 **클라이언트의 시간**이지 서버의 사실이 아니다.
#:
#: 열거에 다섯을 다 두는 이유는 F-09 가 "5상태 정의"를 요구하기 때문이고,
#: 그중 하나를 서버가 못 낸다는 사실은 **시험으로 못박는다**
#: (`FiveStateTest.test_server_never_emits_loading`).
#: 못박지 않으면 언젠가 `LOADING` 을 응답에 넣게 되고, 그 순간 화면은 영원히 스피너다 —
#: DA-03 §0-1 이 실측한 "로딩 상태가 오류 상태를 삼킨다"가 그것이다.
SERVER_EMITTED_STATES: frozenset[WidgetState] = frozenset(
    {WidgetState.DATA, WidgetState.EMPTY, WidgetState.ERROR, WidgetState.FORBIDDEN}
)


@dataclass(frozen=True)
class PanelView:
    """패널 한 장. App·화면이 보는 위젯의 전부다.

    ★ `state` 를 **프레임이 채운다.** DA-04 §2 K3:
      *"그 프레임이 **상태를 위젯에 주입**하는 방식으로 한 번에 처리된다 —
      위젯마다 5상태를 손으로 짜지 않는다."*
      위젯이 스스로 상태를 정하면 위젯 수만큼 다섯 갈래를 다시 짜게 되고,
      그중 하나는 반드시 빠진다. 빠진 갈래가 곧 F-09 의 미충족이다.
    """

    panel_id: int
    dashboard_id: int
    title: str
    panel_type: str
    state: WidgetState
    #: 정상일 때의 내용. `state` 가 `DATA` 가 아니면 **비어 있다** —
    #: 오류인데 옛 데이터를 함께 주면 화면이 그것을 그린다.
    config: dict[str, Any] | None = None
    #: 왜 이 상태인가. `EMPTY`·`ERROR`·`FORBIDDEN` 에서 채운다.
    #: 사람이 읽을 문구는 화면이 i18n 으로 정한다 — 여기 있는 것은 **사유**다.
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state is WidgetState.LOADING:
            raise ValueError(
                "PanelView 에 LOADING 을 담을 수 없다 — 로딩은 클라이언트의 시간이지 "
                "서버의 사실이 아니다. 서버가 LOADING 을 내면 화면은 영원히 스피너다 "
                "(DA-03 §0-1)."
            )
        if self.state is not WidgetState.DATA and self.config:
            raise ValueError(
                f"state={self.state.value} 인데 config 가 채워져 있다. "
                "오류·빈·권한없음에 내용을 함께 주면 화면이 그것을 그린다 — "
                "'빈'과 '오류'를 가르는 이유가 사라진다 (DA-03 §2-5)."
            )


@dataclass(frozen=True)
class PresetView:
    """`get_preset` 의 결과.

    ★ `matched` 가 요점이다. 매핑이 없어 기본값으로 떨어진 것과, 역할을 알아보고
      그 프리셋을 준 것은 **다른 사실**이다. 하나로 합치면 "설정을 안 했는데도
      잘 돌아간다"가 되고, 그 상태가 운영에 그대로 나간다 (D-290).
    """

    preset: str
    #: 역할에서 **실제로 매핑을 찾았는가.** 거짓이면 `FALLBACK_PRESET` 로 떨어진 것이다.
    matched: bool
    #: 판정에 쓰인 역할 코드들 — 감사에서 "왜 이 화면인가"에 답하는 값이다.
    role_codes: tuple[str, ...] = field(default_factory=tuple)
    #: 왜 이 프리셋인가.
    reason: str = ""

    @property
    def clicks_to_reach(self) -> int:
        """[U3] **도달 클릭 수.**

        프리셋이 로그인 직후 화면을 정하므로 **0** 이다. 매핑이 없어 떨어진 경우에도
        화면은 나오므로 0 이지만, 그때 `matched` 가 거짓이라는 사실이 함께 보고된다.
        사용자가 프리셋을 고르게 하는 순간 이 값이 1 이 되고, 그 하나가 U3 의 여유분이다.
        """
        return 0
