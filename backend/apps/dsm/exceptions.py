# -*- coding: utf-8 -*-
"""DSM App 의 오류 계약.

**`200 + {"success": false}` 를 만들지 않는다** (W0-18 · `docs/contracts/api-error-and-auth.md`).
이 저장소는 권한 거부를 200 으로 내보내던 구조를 갖고 있었고, 그중 8개 라우트는
거부 사실이 아예 소멸해 **조용히 성공처럼 보였다.** 신규 App 은 그 전철을 밟지 않는다:
여기서 던지는 것들이 `api.py` 에서 실제 HTTP 상태로 번역된다.
"""
from __future__ import annotations


class DsmError(Exception):
    """DSM App 계열의 뿌리."""


class PermissionDeniedForSetting(DsmError):
    """F-12 설정 접근이 **차단됐다**.

    ★ `audit_id` 를 함께 나른다 — 차단됐다는 사실이 감사에 **남았다는 증거**다(AC-12).
      번호가 없으면 "막았다" 는 말은 응답에만 있고 기록에는 없을 수 있다.
    """

    def __init__(self, reason: str, *, audit_id: int) -> None:  # noqa: D107
        self.reason = reason
        self.audit_id = audit_id
        super().__init__(f"{reason} (감사 #{audit_id})")


class SettingNotAvailable(DsmError):
    """그 설정 영역은 **아직 다룰 수 없다** — 저장할 표가 없다.

    빈 목록이 아니라 예외인 것이 요점이다. 빈 목록을 돌려주면 화면은
    "설정이 없습니다" 를 그리고, 사용자는 **기능이 있는데 비어 있다**고 읽는다.
    없는 것과 비어 있는 것은 다르다 (D-284 · D-290).
    """
