# -*- coding: utf-8 -*-
"""라우트 하나가 **누구 관할인가** — SEC-04 의 모수를 가르는 술어 한 벌.

왜 이 파일이 따로 있나 (D-369)
------------------------------
「관문 없는 라우트」의 수는 오래 **틀린 수**였다. 09-09 에 55건이라 적었는데, 그 55 에는
우리가 고칠 수 있는 자리와 **못 고치는 자리**(dj-core · §0.4 금지구역)가 섞여 있었다.
표적이 무엇인지 모른 채로 수만 있었다.

09-24 에 관할로 가르고 나서야 표적이 보였다 — **우리 층 28건.**
그 뒤로 이 술어를 두 곳이 쓴다:

    scripts/probe_authn_gap_ownership.py   인벤토리를 관할별로 세는 계측기
    backend/tests/test_authn_gap_closed.py 우리 층이 **다시 열리지 않는지** 보는 부작위 시험

두 벌을 두면 반드시 어긋난다. 어긋나면 계측기는 0을 내고 시험은 통과하는데
**실제로는 열려 있는** 상태가 만들어진다 — 이 저장소가 여러 번 만난 모양이다.
그래서 술어는 여기 한 벌뿐이고, 두 도구가 이것을 부른다.

★ **순수 함수다.** Django 도 파일 시스템도 필요 없다 — 문자열 하나를 받아 관할을 낸다.
  그래서 자기시험이 합성 경로를 그대로 먹일 수 있다.

★ 왜 `backend/` 가 아니라 `scripts/` 에 사는가 [실측 2026-09-26]
  처음에는 `backend/common/route_ownership.py` 에 두었다. 그러자 **잠자는 기능 게이트가
  잡았다** — 제품 코드 어디에서도 이 함수를 부르지 않는다. 옳은 빨강이다:
  이것은 제품이 하는 일이 아니라 **재는 일**이고, 재는 것은 재는 층에 산다.
  그래서 옮겼다. 시험은 아래 `scripts` 경로를 잇는 한 줄로 이것을 부른다 —
  **잇는 쪽이 시험이라는 사실이 여기서는 옳다.** 이 함수는 제품 경로가 아니다.
"""
from __future__ import annotations

#: §0.4 금지구역 (D-207). **경로로** 확인한다 — 이름이 비슷한 것만으로 붙이지 않는다.
FORBIDDEN_APPS = ("delivery", "orders", "terminals")

OURS = "우리 층"
OUTSIDE = "저장소 밖"
FORBIDDEN = "§0.4 금지구역"
UNRESOLVED = "모듈 해석 실패"


def classify_path(file_path: str) -> str:
    """핸들러 소스 파일 경로 하나 → 관할.

    ★ `UNRESOLVED` 는 **0이 아니라 「못 본 것」이다**(D-301). 이 값이 0보다 크면
      그만큼은 재지 못한 것이고, 재지 못한 것은 초록이 아니다.
    """
    if not file_path:
        return UNRESOLVED
    p = file_path.replace("\\", "/")
    if "site-packages" in p:
        return OUTSIDE
    if any(f"/{zone}/" in p for zone in FORBIDDEN_APPS):
        return FORBIDDEN
    if "/app/" in p or "/backend/" in p:
        return OURS
    return UNRESOLVED
