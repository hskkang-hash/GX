# -*- coding: utf-8 -*-
"""표 ② 자격증명 저장처 — **값이 아니라 「있는가」의 사실** (D-325 · D-328).

왜 이 표가 필요했나
-------------------
키가 `.env` 에 흩어져 있고, 외부 API 가 늘면 관리가 무너진다. 그리고 juso 사건이
보여 준 것 — **「발급됐다」와 「이 환경에 있다」를 구분할 자리가 없었다**(D-323).

그 다음 날 더 아픈 것이 나왔다. 우리는 「키가 있는가/없는가」만 물었고
**「어떤 키인가」는 묻지 않았다.** 받은 것은 **도로명주소 팝업 API** 키 —
브라우저에 주소검색 창을 띄우는 UI 위젯이고, 서버끼리 쓰는 조회 API 조차 아니다.
그 하루가 `present`(파일에 있다)와 `typed`(무슨 API 인지 안다) 사이다(D-328).

    absent → present → typed → verified → rotated

★ 값은 여기에도 DB 에도 없다 (D-204 · D-319)
--------------------------------------------
`CredentialRecord` 에 값 칸이 **없다.** "마스킹해서 저장" 은 저장이다. 칸이 있으면
언젠가 채워지고, 채워진 값은 덤프·백업·화면·로그로 흘러나간다.
이 모듈이 환경변수를 읽는 유일한 목적은 **「있는가」를 판정하기 위해서**이고,
읽은 값은 함수 밖으로 나가지 않는다. 조회는 언제나 마스킹된 사실만 돌려준다.

★ 이 표가 서면 잠금 대장이 손으로 적는 칸을 잃는다
--------------------------------------------------
`blockers.yaml` 의 `verified_at`/`verified_by`(D-323)가 **진술이 아니라 조회 결과**가 된다.
"완료했다"는 말이 아니라 **확인 행위**가 잠금을 내린다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

#: 상태 5값 — **`present` 와 `typed` 사이가 juso 사건이다** (D-328).
ABSENT = "absent"
PRESENT = "present"
TYPED = "typed"
VERIFIED = "verified"
ROTATED = "rotated"

#: 순서가 있는 값이다. 「typed 이상인가」를 물을 수 있어야 게이트가 선다.
STATUS_ORDER = (ABSENT, PRESENT, TYPED, VERIFIED, ROTATED)

#: 기능 코드가 읽어도 되는 최소 상태. **`typed` 미만은 무엇인지 모르는 키**다.
MIN_USABLE = TYPED


@dataclass(frozen=True)
class CredentialDef:
    """자격증명 하나의 **선언**. 값이 아니라 값에 대한 사실이다."""

    name: str
    #: 값이 실려 오는 환경변수 이름. **값 자체는 어디에도 적지 않는다**(D-319).
    env_var: str
    #: ★ 발급처가 부르는 그 이름 그대로 (D-328). 우리 말로 바꾸면 신청 화면과 대조할 수 없다.
    api_type: str
    #: ★ 이 키로 **할 수 있는 일**. 비면 기능 코드가 읽을 수 없다(게이트 exit 1).
    capability: str
    #: 이 키를 쓰기로 한 자리. 아직 없으면 빈 문자열 — 「쓸 데가 아직 없다」도 사실이다.
    intended_use: str
    #: 비밀인가. 팝업 API 키처럼 **애초에 브라우저에 노출되는 공개 클라이언트 키**가 있다(D-331).
    is_secret: bool
    #: 마지막으로 우리가 아는 상태. 실제 상태는 `probe()` 가 이 환경에서 다시 판정한다.
    declared_status: str


#: ★ 표 ② — 첫 등재 3건 (D-325 ④ · 2026-09-06).
CREDENTIALS: dict[str, CredentialDef] = {
    "JUSO_POPUP_KEY_1": CredentialDef(
        name="JUSO_POPUP_KEY_1",
        env_var="JUSO_POPUP_KEY_1",
        api_type="도로명주소 팝업 API",
        capability=(
            "브라우저에 주소검색 팝업 창을 띄운다. **서버 조회 불가** — 좌표→주소"
            "(역지오코딩)도, 주소→좌표도 이 키로는 되지 않는다(D-329). "
            "공개 클라이언트 키이므로 페이지 소스에 노출되는 것이 정상이고, "
            "**유일한 방어선은 발급 시 등록한 URL 제한**이다(D-331)."
        ),
        intended_use=(
            "카메라 등록·수정 화면에서 `StreamMonitor.install_address` 입력 팝업(D-331). "
            "손으로 치면 오타가 나고, 오타 난 주소는 알림에 그대로 나가 사람을 엉뚱한 곳으로 보낸다. "
            "★ 우선순위 낮음 — 지금 막고 있는 것이 아니다."
        ),
        is_secret=False,
        declared_status=TYPED,
    ),
    "JUSO_POPUP_KEY_2": CredentialDef(
        name="JUSO_POPUP_KEY_2",
        env_var="JUSO_POPUP_KEY_2",
        api_type="도로명주소 팝업 API",
        capability=(
            "JUSO_POPUP_KEY_1 과 **같은 유형**이다 [실측·대표 승인 화면 2건]. "
            "두 건을 다르게 쓰려던 계획은 유형이 같다는 사실로 무의미해졌다 — "
            "한 건은 예비다."
        ),
        intended_use="예비. 1번과 같은 자리에 쓴다.",
        is_secret=False,
        declared_status=TYPED,
    ),
    "DATA_GO_KR_KEY_DECODED": CredentialDef(
        name="DATA_GO_KR_KEY_DECODED",
        env_var="DATA_GO_KR_KEY_DECODED",
        api_type="공공데이터포털 일반 인증키 (Decoding)",
        capability=(
            "포털에서 승인된 서비스를 **서버에서** 호출한다 [실측 2026-09-04 · "
            "활용신청 현황 18건 전건 승인]. 기상특보·단기/중기예보·특일정보·학교위치가 "
            "이 키 하나로 열린다. **비밀 키다** — 노출되면 우리 할당량이 남에게 쓰인다."
        ),
        intended_use=(
            "기상특보(FX-1)·특일정보. 학교위치는 D-333 재검토로 `not_required` 로 내렸다 — "
            "고객이 특정 지자체이고 카메라가 D-330 으로 자기 주소를 갖는다."
        ),
        is_secret=True,
        declared_status=PRESENT,
    ),
}


def _definition(name: str) -> CredentialDef:
    """선언 하나. 없으면 `CredentialNotDeclared`.

    이름을 자유롭게 받으면 표가 **이 환경에 있는 것의 목록**이 아니라
    누군가 물어본 것의 목록이 된다.
    """
    from kernels.k5_trust.exceptions import CredentialNotDeclared

    try:
        return CREDENTIALS[name]
    except KeyError:
        raise CredentialNotDeclared(
            f"자격증명 {name!r} 은 표 ②에 선언되지 않았다. "
            f"선언된 것: {', '.join(sorted(CREDENTIALS))}. "
            f"새 외부 자원은 선언을 먼저 올린다 — 그때 D-333 의 "
            f"「우리가 이미 아는 것으로 되는가」를 함께 적게 된다"
        ) from None


def _mask(value: str) -> str:
    """조회는 **언제나 마스킹**이다 (D-325 표 ②).

    앞 2·뒤 2 만 남긴다. 짧은 값은 길이도 흘리지 않는다 —
    "4자리 키" 라는 사실 자체가 공격면이다.
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * 8
    return f"{value[:2]}{'*' * 6}{value[-2:]}"


def _observe(name: str) -> str:
    """**이 환경에서** 이 키가 어느 상태인가 (D-316 · D-323).

    문서·계정 화면이 아니라 **여기**를 본다. 값은 돌려주지 않는다 — 상태만 돌려준다.
    선언이 `typed` 이상이어도 환경에 값이 없으면 `absent` 다:
    **발급 완료 ≠ 전달 완료 ≠ 환경 존재.**
    """
    spec = _definition(name)
    raw = os.environ.get(spec.env_var, "")
    if not raw.strip():
        return ABSENT
    # 값이 있다. 그러면 선언이 아는 만큼까지 올라간다 — 그 이상은 확인 행위가 올린다.
    return spec.declared_status if spec.declared_status != ABSENT else PRESENT


def _at_least(status: str, floor: str) -> bool:
    """`status` 가 `floor` 이상인가. `rotated` 는 `verified` 와 같은 급으로 본다."""
    order = {s: i for i, s in enumerate(STATUS_ORDER)}
    if status == ROTATED:
        status = VERIFIED
    return order.get(status, -1) >= order.get(floor, 99)
