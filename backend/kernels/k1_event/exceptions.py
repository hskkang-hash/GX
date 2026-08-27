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
