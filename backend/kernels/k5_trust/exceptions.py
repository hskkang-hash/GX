# -*- coding: utf-8 -*-
"""K5 신뢰 커널의 거부들 — **없는 것은 없다고 말한다** (D-284).

빈 값·None·False 로 돌려주지 않는 이유는 하나다. 부르는 쪽이 그것을
"그런 설정은 0 이다" 로 읽고, 그 오독이 조용히 판정의 근거가 되기 때문이다.
"""
from __future__ import annotations


class K5Error(Exception):
    """K5 가 내는 거부의 뿌리."""


class ThresholdNotDefined(K5Error):
    """표에 없는 임계값 키를 물었다.

    정의에 없는 키를 허용하면 오타 하나가 **새 임계값**이 되고, 그 값은 아무도
    검토한 적 없이 판정에 들어간다.
    """


class ThresholdNotSet(K5Error):
    """정의는 있는데 **값이 아직 없다** — 「0 이다」가 아니다 (D-290).

    F-02 의 지점별 수위 기준선이 이 자리다. 기본값을 지어내면 그 숫자가 곧
    계약 AC 의 판정 근거가 된다(D-280). 그래서 지어내지 않고 멈춘다.
    """


class ThresholdIsContractFixed(K5Error):
    """계약이 못박은 임계값을 설정으로 덮으려 했다.

    F-04 「5분 내 중복 알림 0건」 · F-10 「30초 내 발송」은 **우리 취향이 아니라 계약**이다.
    표에 두는 이유는 값이 한 곳에 보이게 하기 위해서이지 고치라고 둔 것이 아니다.
    설정 한 줄로 계약을 어길 수 있으면 그 계약은 코드에서 사라진 것이다.
    """


class ScopeNotAvailable(K5Error):
    """아직 열지 않은 적용 범위에 값을 넣으려 했다 (D-325: 지금은 전역 기본만)."""


class CredentialNotDeclared(K5Error):
    """선언에 없는 자격증명 이름을 물었다.

    이름을 자유롭게 받으면 표가 **이 환경에 있는 것의 목록**이 아니라
    누군가 물어본 것의 목록이 된다.
    """


class CredentialNotUsable(K5Error):
    """`typed` 미만이거나 `capability` 가 빈 키를 기능 코드가 쓰려 했다 (D-328).

    juso 사건이 이 자리다. **「있다」와 「무엇인지 안다」는 다른 사실**이고,
    그 사이의 하루가 우리에게 값을 물렸다.
    """
