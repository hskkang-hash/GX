# -*- coding: utf-8 -*-
"""K1 오류 계약.

DA-04 §2 K1 **오류 계약**: *"거부는 HTTP 4xx 로 낸다. `200 + {"success":false}` 를
새로 만들지 않는다."*

W0-18 이 그 부류 8건을 제거했다 — 권한 거부가 200 안에 숨어 **조용히 사라지던** 코드다.
커널이 그것을 다시 만들지 않게 여기서 형을 고정한다.

  · 남의 테넌트 것 → `Http404` (`common.tenant_filters` 가 던진다).
    **403 이 아니다** — 403 은 "그 id 는 있는데 네 것이 아니다"를 알려 준다.
    존재 여부가 새는 것도 누출이다. 남의 것은 **없는 것과 같아야** 한다.
  · 입력이 계약을 벗어남 → `InvalidEventInput` (4xx 로 번역된다).
  · 아직 안 만든 공개 면 → `NotImplementedYet`.
"""
from __future__ import annotations


class K1Error(Exception):
    """K1 이 내는 모든 오류의 뿌리. App 은 이것 하나만 알면 된다."""


class InvalidEventInput(K1Error):
    """계약(`docs/contracts/detection-event.md`)을 벗어난 입력. HTTP 400 으로 번역한다."""


class NotImplementedYet(K1Error):
    """공개 면에 **이름은 있는데 구현이 없는** 것.

    ★ 조용히 `None` 이나 빈 목록을 돌려주지 않는다. 그렇게 하면 부르는 쪽이
      "동작했는데 결과가 없다"로 읽고, 그 오해는 한참 뒤에 발견된다 —
      `detect_and_save` 가 정확히 그 모양이었다(독스트링은 저장한다고 적혀 있고 본문은 비어 있다).
      **없는 것은 없다고 말한다.**
    """


# ═══════════════════════════════════════════════════════════════════════════
# 대응 진행 축 (D-399) — **거절은 4xx 로 나간다**
#
#   커널이 던지고 App 이 번역한다. 커널은 HTTP 를 모른다 — 상태코드를 여기 적으면
#   그 순간 커널이 웹 계층을 알게 되고, 다음 소비자(배치·gRPC)가 그 값을 못 쓴다.
#
#   셋을 따로 두는 이유: 셋은 **부르는 쪽이 할 일이 다르다.**
#     Forbidden     → 그 전이는 없다. 다시 보내도 같다        (409)
#     NeedsReason   → 사유를 채워 다시 보내면 된다             (400)
#     NeedsManager  → 이 사람은 못 한다. 팀장이 해야 한다      (403)
#   하나로 묶어 400 만 내면 화면이 「무엇을 고쳐 다시 보낼지」를 모른다 (D-290).
# ═══════════════════════════════════════════════════════════════════════════
class ResponseTransitionError(K1Error):
    """대응 진행 전이가 **거절됐다**. 어디서 어디로 가려 했는지를 나른다."""

    def __init__(self, *, frm: str, to: str, why: str) -> None:  # noqa: D107
        self.frm = frm
        self.to = to
        self.why = why
        super().__init__(f"{frm} → {to} 를 거절했다: {why}")


class ResponseTransitionForbidden(ResponseTransitionError):
    """그 전이 자체가 없다 — 다시 보내도 결과가 같다. **409.**"""


class ResponseTransitionNeedsReason(ResponseTransitionError):
    """되돌림에는 사유가 필수다 — 채워 다시 보내면 된다. **400.**"""

    def __init__(self, *, frm: str, to: str) -> None:  # noqa: D107
        super().__init__(frm=frm, to=to,
                         why="되돌림에는 사유가 필수다. 무엇에서 무엇으로는 표가 알고 "
                             "**왜** 는 여기서만 들어온다")


class ResponseTransitionNeedsManager(ResponseTransitionError):
    """되돌림은 관제팀장(U2)만 한다 — 이 사람으로는 안 된다. **403.**"""

    def __init__(self, *, frm: str, to: str) -> None:  # noqa: D107
        super().__init__(frm=frm, to=to,
                         why="되돌림은 관제팀장(K3 MANAGER 이상)만 한다")
