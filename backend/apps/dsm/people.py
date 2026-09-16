# -*- coding: utf-8 -*-
"""U56 차선 — **사람 만들기·비활성화 골격** (턴 Q P-141 ④ · 시간이 남으면 하는 절).

이 파일이 하는 일 · 안 하는 일
--------------------------------
    한다   dj-core 의 **실제 생성·비활성화 경로**(`core.api.v1.user.create_user` ·
           `core.api.v1.user.deactivate_user`)를 Django 시험 클라이언트로 두드린다.
           `seed_role_users.py` 가 실제 HTTP(urllib)로 하는 것과 **같은 이유**다 —
           ORM 으로 직접 만들면 중복 검사·기본 역할·`UserSettings`·
           `ensure_complete_profile` 같은 자리들이 한 번도 안 돈다(그 파일 머리말 참고).
    안 한다  **새 인증 경로를 만들지 않는다** (§ 공통 규칙 4). 비활성화된 계정이
           막히는 것은 dj-core 의 기존 로그인 경로(`CustomJWTAuth`/토큰 발급)가
           `is_active=False` 를 보고 거절하기 때문이고, 이 파일은 그 사실을 **재는**
           함수만 두지 비활성 계정을 따로 판정하는 두 번째 문을 만들지 않는다.

★ 왜 `django.test.Client` 인가 — **실제 라우팅을 그대로 타면서 소켓이 없다**
------------------------------------------------------------------------------
운영에서 이 모듈을 부르는 자리(관리 화면의 "계정 만들기")는 이미 같은 프로세스
안에 있다. `urllib` 로 자기 자신에게 진짜 소켓 HTTP 를 여는 것은 순환 호출이 되고,
ORM 을 직접 만지는 것은 위에서 적은 이유로 「실제 경로」가 아니게 된다.
`django.test.Client` 는 URL 라우팅·미들웨어·뷰를 **소켓 없이 그대로** 태우는
Django 표준 도구이고, 이 저장소의 시험들이 이미 그 경로로 같은 문(`create-user`)을
검증하고 있다(`tests/test_dsm_app.py` 류의 `Client` 사용과 같은 도구).

§0.4 — dj-core 의 `core.api.v1.user` 는 **부르기만** 한다. 고치지 않는다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

#: dj-core 의 `create_user` 뷰 선언 자체엔 `auth=` 가 없다(문서만 "관리자 전용"이라
#: 적혀 있고 코드엔 검사가 없다) — 그러나 이 경로는 `common/access_gate.py` 의
#: `AUTHN_REQUIRED_PATHS` 에 올라 있어 **자격증명이 없으면 우리 층에서 401 로
#: 끊긴다**(D-348 · P-83, 2026-09-06). `create_person()` 이 `actor_bearer_header` 를
#: 요구하는 이유가 이것이다 — 5/분 속도제한(`@ratelimit`)은 그 다음 층의 방어다.
CREATE_USER_PATH = "/api/v1/user/create-user"
DEACTIVATE_USER_PATH = "/api/v1/user/deactivate-user"


class PersonOpError(Exception):
    """사람 만들기·비활성화가 dj-core 문에서 거절됐다. **본문을 그대로 들고 있는다** —
    삼키면 "무엇이 틀렸는지" 가 사라진다."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"dj-core 문이 {status_code} 를 냈다: {body[:200]}")


@dataclass(frozen=True)
class CreatedPerson:
    """만든 결과 — **값(비밀번호)을 담지 않는다.** 부르는 쪽이 이미 값을 쥐고 있다."""

    user_id: int
    username: str


def create_person(*, actor_bearer_header: dict, username: str, email: str,
                  password: str, group_id: int, role_ids: list[int],
                  display_name: str = "", employee_id: str | None = None,
                  is_active: bool = True) -> CreatedPerson:
    """dj-core 의 **실제 생성 경로**로 사람 하나를 만든다.

    ★ `actor_bearer_header` 가 필수다 — **익명으로 부르지 않는다.**
      [실측 2026-09-15 · 이 파일을 쓰다가 걸렸다] `common/access_gate.py` 의
      `AUTHN_REQUIRED_PATHS` 가 `/api/v1/user/create-user` 를 **이미 막고 있다**
      (D-348 · P-83, 2026-09-06 — dj-core 핸들러 자체엔 권한 검사가 한 줄도 없어서
      우리 층에서 길목을 막았다). `seed_role_users.py` 머리말의 "떠 있는 서버에
      익명으로 HTTP 를 보낸다"는 그 관문이 서기 **전** 문서다 — 지금은 자격증명이
      **없으면** 401 이다. 이 관문(`_has_credentials`)은 **있음**만 보고 유효성은
      안 본다(그것은 인증의 일 · D-212 판정 복제 금지) — 그래서 어떤 로그인 사용자의
      Bearer 든 이 문을 지나게 하되, **누가 만들 수 있는가의 판정은 여기서 하지
      않는다**(그 판정은 dj-core 의 것이고, 지금 이 핸들러엔 그 판정이 없다는 사실을
      숨기지 않는다 — 새 인증 경로를 만들지 않는다).
    ★ 비밀번호는 반환값에 담지 않는다(D-204) — 부르는 쪽이 이미 알고 있다.
    ★ `role_ids` 를 비우면 dj-core 가 **기본 역할('user')을 스스로 채운다**
      (`create_user` 974~984행) — 여기서 따로 채우지 않는다. 두 곳이 같은 기본값을
      들면 하나가 바뀔 때 어긋난다(D-212).
    """
    from django.test import Client

    payload = {
        "username": username, "email": email, "password": password,
        "first_name": display_name, "last_name": "",
        "is_active": is_active, "is_staff": False, "is_superuser": False,
        "otp_exempt": True,
        "roles": role_ids or None,
        "employee_id": employee_id,
        "group_id": group_id, "is_default": True,
    }
    client = Client(raise_request_exception=False)
    resp = client.post(CREATE_USER_PATH, data=json.dumps(payload),
                       content_type="application/json", **actor_bearer_header)
    if resp.status_code not in (200, 201):
        raise PersonOpError(resp.status_code,
                            (resp.content or b"").decode("utf-8", "replace"))
    body: dict[str, Any] = json.loads(resp.content.decode("utf-8"))
    user_data = (body.get("data") or {}).get("user") or body.get("user") or {}
    user_id = user_data.get("id")
    if user_id is None:
        raise PersonOpError(resp.status_code,
                            "응답에 user.id 가 없다 — dj-core 응답 모양이 바뀌었을 수 있다: "
                            + (resp.content or b"")[:200].decode("utf-8", "replace"))
    return CreatedPerson(user_id=int(user_id), username=username)


def deactivate_person(*, actor_bearer_header: dict, user_id: int) -> None:
    """dj-core 의 **실제 비활성화 경로**로 계정을 끈다.

    ★ `actor_bearer_header` 는 이미 인증된 관리자의 `{"HTTP_AUTHORIZATION": "Bearer …"}`
      다 — 이 함수는 **누가 끌 수 있는지를 판정하지 않는다.** dj-core 의
      `deactivate_user` 가 `CustomJWTAuth()` 로 그 자리를 이미 지킨다(§0.4 — 고치지
      않는다). 판정을 여기서 다시 하면 두 벌이 되고, 두 벌은 반드시 어긋난다(D-212).
    ★ 행을 지우지 않는다 — dj-core 자체가 `is_active=False` 로만 끈다. 그것이 이
      제품 전체의 규약(SEC-05·SEC-07)과 같은 모양이다.
    """
    from django.test import Client

    client = Client(raise_request_exception=False)
    resp = client.post(
        f"{DEACTIVATE_USER_PATH}?user_id={user_id}",
        **actor_bearer_header)
    if resp.status_code != 200:
        raise PersonOpError(resp.status_code,
                            (resp.content or b"").decode("utf-8", "replace"))
