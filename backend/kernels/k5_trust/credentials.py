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
    # ═══════════════════════════════════════════════════════════════════════
    # ★ **들어오는** 키가 이 표에 처음 들어온다 (D-382)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 표 ②는 여태 **나가는 키**(우리가 남을 부를 때)의 표였다. 이 한 건은 방향이
    # 반대다 — **AI 분석 서버가 우리를 부른다.** 그래서 이름에 `INBOUND_` 를 박는다:
    # D-337(동음이의 대장)이 잡은 혼동이 「API Key」라는 한 단어가 두 방향을 가리킨
    # 것이었고, 방향을 **이름으로** 말하지 않으면 그 혼동이 표 안으로 들어온다.
    #
    # ★ 왜 이 줄이 지금 생겼나 — **막은 것에는 여는 절차가 함께 있어야 한다** (D-382)
    # ------------------------------------------------------------------------
    #   D-370 에서 익명이 쓰던 네 자리를 막았고, 그중 둘(`/api/media-data/detect-callback`,
    #   `/api/media-data/upload-detection`)은 **AI 서비스가 인증 없이 부르던 콜백**이다.
    #   막은 것은 옳았다 — 인증 없는 쓰기 콜백을 열어 두는 쪽이 더 나쁘다.
    #
    #   그러나 **막기만 하고 여는 절차가 없으면 다음 배포에서 조용히 깨진다.**
    #   차단은 절반이고, 나머지 절반은 복구 경로다. 이 줄이 그 나머지 절반이다:
    #     · 이 키가 무엇인지 (`api_type`) · 이 키로 무엇을 할 수 있는지 (`capability`)
    #     · 지금 이 환경에 있는지 (5값 상태 — `probe()` 가 다시 판정한다)
    #     · 그리고 **`present` 미만이면 배포하지 않는다** (`scripts/verify_deploy_ready.py`)
    #
    # ⚠ 이 키는 **테넌트별 DB 행이 아니다.** 테넌트별 발급·폐기는
    #   `kernels/k5_trust/inbound_keys.py` 의 몫이고 그것은 표 ②에 들어갈 수 없다(D-337).
    #   여기 있는 것은 **환경변수 하나로 오는 서비스 간 자격증명**이라 표 ②의 술어
    #   (「이 환경의 환경변수에 있는가」)가 그대로 성립한다.
    "INBOUND_AI_CALLBACK_KEY": CredentialDef(
        name="INBOUND_AI_CALLBACK_KEY",
        env_var="INBOUND_AI_CALLBACK_KEY",
        api_type="GuardianX 들어오는 서비스 키 (AI 분석 서버 → 우리)",
        capability=(
            "AI 분석 서버가 `/api/media-data/detect-callback` 과 "
            "`/api/media-data/upload-detection` 두 자리를 부를 때 자신을 증명한다. "
            "**쓰기 콜백이다** — 검출 결과를 저장한다. "
            "★ 재난 검출 **본선은 이 경로가 아니다** [실측 D-370]: 본선은 gRPC "
            "(`stream_monitors/services/grpc_dual_stream_service.py` → K1)이므로 "
            "이 키가 없어도 **F-02·F-10 계약 경로는 살아 있다.** 죽는 것은 미디어 분석 "
            "콜백이고, 그것이 이 절이 CONTRACT 가 아니라 DEV 인 이유다."
        ),
        intended_use=(
            "D-370 이 두 콜백에 `CustomJWTAuth` 를 붙이면서 AI 서버 쪽이 깨진다. "
            "배포 전에 이 키를 양쪽에 심어야 한다 — 대장 `AI_CALLBACK_NEEDS_CREDENTIAL`. "
            "★ [실측 2026-09-12] 지금 이 환경에 **없다**(`absent`). 그것이 사실이고, "
            "`verify_deploy_ready.py` 가 배포를 막는 자리가 여기다."
        ),
        is_secret=True,
        #: ★ **아직 받지 않았다.** `absent` 라고 적는 것이 이 표의 요점이다 —
        #:   「받을 예정」을 `present` 로 적으면 표가 계획서가 되고, 계획서는 배포를 막지 못한다.
        declared_status=ABSENT,
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
