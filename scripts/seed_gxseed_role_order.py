# -*- coding: utf-8 -*-
"""P-261 — 표 밖 역할 `order` 를 **잴 수 있는 시드 계정 하나**를 만든다 (차선 U56 · 턴 AE).

왜 이 스크립트가 필요한가
-------------------------
표 밖 역할(`order` 등) 8명을 `fire_user` 로 재배정했더니(P-238) 영어 사이드바가
121→0 이 됐다. 그런데 그 0 은 **ORM 으로 센 수**이고 아무도 눌러 보지 않았다.
눌러 보려 했더니 그 계정들은 **실사용자**라 비밀번호가 우리에게 없다.

세종 판정(P-261): **실사용자 비밀번호는 만지지 않는다** → 시드 계정 하나로 경로를 잰다.
이 스크립트가 심는 사람은 `gxseed_role_order` 하나뿐이다.

★★ 순서가 생명이다 — **`mark_unbillable` 을 먼저, 역할(`order`)은 그 다음**
--------------------------------------------------------------------------
계정을 실제 생성 경로(HTTP `POST /api/v1/user/create-user`)로 만들 때 `roles` 를
**일부러 비워 둔다**(`[]`). 그 직후,

    1. `common.billing_marks.mark_unbillable(user, SEED_SOURCE, …)` 를 **먼저** 부른다
    2. 그 다음에야 `user.roles.add(order_role)` 로 `order` 역할을 준다

반대로 하면(역할을 먼저 주면) 역할이 실린 채로 표식이 없는 창이 생기고, 그 창에서
청구 셈(`kernels.k6_feedback.services.usage_snapshot`)이 지나가면 이 씨앗이 고객
계정과 똑같이 청구에 든다 — 이 저장소는 "씨앗 청구 0"을 어제(2026-09-22) 벌었고
(`backend/tests/test_b_billing_marks.py` · P-224), 순서를 뒤집으면 그 값이 깨진다.

★ 이 스크립트는 **실제 생성 경로**를 쓴다(`seed_role_users.py` 와 같은 규율 — P-9).
  `CoreUser.objects.create(...)` 로 모형을 만들지 않는다. ORM 직접 생성은 제품이
  사람을 만들 때 지나는 자리(중복 검사·`UserSettings`·`ensure_complete_profile`·
  알림 채널 구독)를 전부 건너뛰고, 그 결함은 모형 위에서 절대 드러나지 않는다.

★ 테넌트는 **`UserProfileLink.group`** 이 정본이다 — `Role.group` 은 역할이 **정의된
  스코프**이지 사람의 테넌트가 아니다(U56 이 턴 AD 에 이 자리에서 헷갈릴 뻔했다 ·
  `reassign_role_p254.py::_tenant` 머리말과 같은 규율). GX 계열은 `ETRI-Group`
  (id 는 DB 에서 이름으로 찾는다 — 여기 하드코딩하지 않는다).

★ 살아 있는 계정 조건은 **`is_active=True AND deleted IS NULL`** 둘 다다(P-258).

★ 비밀번호는 **환경 이름으로만** 받는다(`GX_SEED_ROLE_PASSWORD`). 기본값을 두지
  않는다 — 기본값을 두면 그 값이 곧 저장소에 적힌 비밀번호다(D-204 · P-12 ①).
  값을 출력·로그·커밋하지 않는다 — 길이와 sha256 앞 12자까지만 본다.

★ **되돌리는 길이 같은 파일에 있다**(`--revert`). 계정 자체는 지우지 않는다
  (삭제는 대표 결정 — 계정·카메라·행을 지우지 마라). `--revert` 는 `order` 역할만
  M2M 에서 뗀다. **되돌리기는 대표 결정이므로 이 스크립트는 길만 두고, 부르지 않는다.**

★ **`create-user` 는 이제 익명이 못 지난다** [실측 2026-09-23 · 이 턴]. `common/
  access_gate.py::AUTHN_REQUIRED_PATHS` 가 D-343 §5 로 이 자리를 올렸다(익명 401 ·
  reason="authentication_required") — `seed_role_users.py` 머리말이 전제한
  "익명 HTTP" 시절 글은 이제 안 맞는다. 그래서 이 스크립트는 **먼저 로그인해서**
  진짜 토큰을 받고(`GX_ROUTE_USER`/`GX_ROUTE_PASSWORD` — 스크립트 전용 게이트
  계정, `verify_authn_paths.py` 와 같은 계정), 그 토큰을 `Authorization: Bearer`
  로 싣는다. 관문은 헤더가 **있기만 하면** 지나가지만(`_has_credentials` — 값 검증은
  안 함) 가짜 헤더로 속이지 않고 실제 로그인을 거친다.

부르는 자리 — **gx-shell 안**(HTTP 는 로컬 runserver:8000 을 두드리고, 그 외엔 ORM 을
직접 본다 · MinIO 는 안 건드린다):

    저장소 뿌리에서 (호스트):
        set -a; . ./.env.gates; set +a
        MSYS_NO_PATHCONV=1 docker exec -e GX_SEED_ROLE_PASSWORD \\
          -e DJANGO_SETTINGS_MODULE=config.settings \\
          -e PYTHONPATH=/app -e PYTHONIOENCODING=utf-8 \\
          -w /app gx-shell python /repo/scripts/seed_gxseed_role_order.py --apply

    재 보기만(기본):
        docker exec ... gx-shell python /repo/scripts/seed_gxseed_role_order.py

    되돌리기(대표 결정 — role 만 뗀다, 계정은 안 지운다):
        docker exec ... gx-shell python /repo/scripts/seed_gxseed_role_order.py --revert --apply

종료 코드: 0 = 쟀고(재 보기) 또는 옳게 됐다 · 0이 아님 = 못 했다/틀렸다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

import django

django.setup()

from django.apps import apps                      # noqa: E402
from django.contrib.auth import get_user_model     # noqa: E402

USERNAME = "gxseed_role_order"
EMAIL = "gxseed_role_order@seed.invalid"
ROLE_CODE = "order"
GROUP_NAME = "ETRI-Group"          # GX 계열 테넌트 (UserProfileLink.group 정본)
EMPLOYEE_MARKER = "GX-SEED-ROLE-ORDER"
DISPLAY_NAME = "[시드] U56 표밖역할(order) 측정용"
CREATE_PATH = "/api/v1/user/create-user"
LOGIN_PATH = "/api/v1/auth/login"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

#: [실측 2026-09-23 · 이 턴] `create-user` 가 D-343 §5 로 `AUTHN_REQUIRED_PATHS`
#: 에 올라 **익명 401** 이 됐다(`common/access_gate.py`) — `seed_role_users.py` 가
#: 전제한 "진짜 HTTP·무인증" 시절 글이었다. 이 관문은 **자격증명이 들어왔는지만**
#: 보고 유효성은 안 본다(`_has_credentials`) — 그래도 진짜 로그인으로 얻은 토큰만
#: 쓴다(가짜 헤더로 관문을 속이지 않는다).
#:
#: ★ [실측] `GX_ROUTE_USER`(=`gxseed_u4_official`)로는 **403 `read_only_role`**
#:   이 난다 — 그 계정의 역할(`view_only_-_anyang`)이 읽기 전용 관문(P-119)에
#:   걸린다. `create-user` 는 쓰기이므로 **관리자 권한을 가진 기존 시드 계정**이
#:   필요하다 — `gxseed_u5_sysop`(U5 · role=`admin` · `seed_role_users.py` 가
#:   같은 `GX_SEED_ROLE_PASSWORD` 로 이미 심어 둔 사람 · 브라우저로 아무도 안 든다).
#:   새 비밀 이름을 만들지 않는다 — 이미 있는 `GX_SEED_ROLE_PASSWORD` 하나로 로그인도
#:   하고 새 계정 비밀번호도 정한다(둘 다 "시드 역할 비밀번호"라는 같은 뜻이다).
AUTH_USERNAME = "gxseed_u5_sysop"
AUTH_PASSWORD_ENV = "GX_SEED_ROLE_PASSWORD"

#: 청구 셈을 잴 때 쓰는 관측자(actor) — GX(ETRI-Group) 소속의 **살아 있는 기존 계정**.
#: 이 계정으로 아무것도 안 바꾼다 — `TenantScope.of(actor)` 가 소속을 읽는 용도뿐이다.
MEASURE_ACTOR_USERNAME = "order_chungnam"


def _log(msg: str) -> None:
    print("[U56/P-261] %s" % msg)


def _group_id() -> int:
    from django.apps import apps as django_apps

    UPL = None
    for m in django_apps.get_models():
        if m.__name__ == "UserProfileLink":
            UPL = m
            break
    if UPL is None:
        raise SystemExit("[U56/P-261] ★ UserProfileLink 모델을 못 찾았다 — 멈춘다")
    Group = UPL._meta.get_field("group").related_model
    g = Group.objects.filter(name=GROUP_NAME).first()
    if g is None:
        raise SystemExit(
            "[U56/P-261] ★ 테넌트 %r 를 못 찾았다 — GX 계열이 없으면 멈춘다" % GROUP_NAME)
    return g.id


def _fresh_user():
    """**같은 인스턴스로 확인하지 않는다** — 매번 새로 읽는다(제가 쓴 것을 기억하지
    않게 하려고). `_base_manager` — 소프트삭제 매니저를 지나 있는 그대로 본다."""
    User = get_user_model()
    return User._base_manager.filter(username=USERNAME).first()


def _roles(u) -> list:
    return sorted(r.code for r in u.roles.all())


def _tenant_name(u) -> str:
    from django.apps import apps as django_apps

    for m in django_apps.get_models():
        if m.__name__ != "UserProfileLink":
            continue
        row = m.objects.filter(user_id=u.id).first()
        if row is None:
            return "(UserProfileLink 에 이 사람의 행이 없다)"
        grp = getattr(row, "group", None)
        return getattr(grp, "name", None) or str(grp)
    return "(UserProfileLink 모델을 못 찾았다)"


def _billing_users_count() -> dict:
    """청구 셈 — GX(ETRI-Group) 테넌트의 「계정 수」 (`usage_snapshot()['users']`).

    ★ 이것이 이 스크립트의 진짜 닫는 조건이다: 계정을 만들기 전후로 이 수가
      **안 늘어야** 한다. 못 재면(관측자가 없으면) `None` 과 사유를 돌려준다 —
      0으로 덮지 않는다(D-301).
    """
    User = get_user_model()
    actor = User._base_manager.filter(
        username=MEASURE_ACTOR_USERNAME, is_active=True, deleted__isnull=True
    ).first()
    if actor is None:
        return {"users": None, "why": "관측자 %r 를 못 찾았다 — 못 쟀다" % MEASURE_ACTOR_USERNAME}
    from common.tenant_scope import TenantScope
    from kernels.k6_feedback.services import usage_snapshot

    snap = usage_snapshot(scope=TenantScope.of(actor))
    return {"users": snap["users"], "why": "actor=%s 로 관측" % MEASURE_ACTOR_USERNAME}


def _login_token(base_url: str) -> str:
    """게이트 계정으로 로그인해 `access_token` 을 얻는다.

    ★ **가짜 헤더로 관문을 속이지 않는다.** `access_gate.AUTHN_REQUIRED_PATHS` 는
      `Authorization` 헤더가 **있기만** 하면 지나가지만(값 검증은 안 함), 이 스크립트는
      진짜 로그인으로 얻은 토큰만 싣는다 — 그 틈을 알고 있다는 사실과 그것을 이용하지
      않는다는 사실을 둘 다 남긴다.
    ★ `end_previous_session: True` — 이 계정(`gxseed_u5_sysop`)은 U5 시드 계정이다
      (`seed_role_users.py` 가 심었다 · 브라우저로 아무도 안 든다). 실사람의 화면을
      끊지 않는다.
    """
    user = AUTH_USERNAME
    password = os.environ.get(AUTH_PASSWORD_ENV)
    if not password:
        raise SystemExit(
            "[U56/P-261] ★ 게이트 로그인 비밀번호가 없다 — %s 를 환경변수로 준다"
            % AUTH_PASSWORD_ENV)
    url = base_url.rstrip("/") + LOGIN_PATH
    body = json.dumps({"username": user, "password": password,
                       "end_previous_session": True}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            "[U56/P-261] ★ 게이트 로그인 실패 (HTTP %s): %s"
            % (exc.code, exc.read().decode("utf-8", "replace")))
    except OSError as exc:
        raise SystemExit("[U56/P-261] ★ 로그인 서버에 닿지 못했다: %s (%s)" % (url, exc))
    token = (payload.get("user") or {}).get("access_token")
    if not token:
        raise SystemExit(
            "[U56/P-261] ★ 로그인 응답에 access_token 이 없다 — auth_status=%s"
            % payload.get("auth_status"))
    return token


def _post_create(base_url: str, payload: dict, token: str):
    url = base_url.rstrip("/") + CREATE_PATH
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer %s" % token})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except OSError as exc:
        raise SystemExit(
            "[U56/P-261] ★ 서버에 닿지 못했다: %s (%s) — runserver 가 gx-shell 안 %s "
            "에 떠 있어야 한다" % (url, exc, base_url))


def _do_create(base_url: str) -> None:
    password = os.environ.get("GX_SEED_ROLE_PASSWORD")
    if not password:
        raise SystemExit(
            "[U56/P-261] ★ 비밀번호가 없다 — 환경변수 GX_SEED_ROLE_PASSWORD 로 준다 "
            "(값을 argv 에 넘기지 않는다 · D-204)")

    group_id = _group_id()
    payload = {
        "username": USERNAME,
        "email": EMAIL,
        "password": password,
        "first_name": DISPLAY_NAME,
        "last_name": "",
        "is_active": True,
        "is_staff": False,
        "is_superuser": False,
        "otp_exempt": True,
        # ★★ 일부러 비운다 — 역할은 이 창(HTTP 호출) 안에서 안 준다.
        #    mark_unbillable 이 먼저 서야 `order` 가 뒤에 올 수 있다.
        "roles": [],
        "employee_id": EMPLOYEE_MARKER,
        "group_id": group_id,
        "is_default": True,
    }
    token = _login_token(base_url)
    status, body = _post_create(base_url, payload, token)
    _log("POST %s%s → %s" % (base_url.rstrip("/"), CREATE_PATH, status))
    if status not in (200, 201):
        raise SystemExit("[U56/P-261] ★ 계정을 만들지 못했다 (HTTP %s): %s" % (status, body))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 실행한다 (없으면 재 보기만)")
    ap.add_argument("--revert", action="store_true",
                    help="되돌린다 — order 역할만 뗀다. 계정은 안 지운다. **대표 결정이다**")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help="create-user 를 두드릴 떠 있는 서버 주소 (기본: gx-shell 안 runserver:8000)")
    args = ap.parse_args()

    # ── 되돌리기 ─────────────────────────────────────────────────────────
    if args.revert:
        u = _fresh_user()
        if u is None:
            _log("계정이 없다 — 되돌릴 것이 없다")
            return 0
        before = {"roles": _roles(u)}
        _log("되돌리기 전 · " + json.dumps(before, ensure_ascii=False))
        if not args.apply:
            _log("재 보기만 했다 — 되돌리려면 --revert --apply")
            return 0
        Role = apps.get_model("role", "Role")
        order_role = Role.objects.filter(code=ROLE_CODE).first()
        if order_role is not None:
            u.roles.remove(order_role)
        fresh = _fresh_user()
        after = {"roles": _roles(fresh)}
        _log("되돌리기 후 · " + json.dumps(after, ensure_ascii=False))
        ok = ROLE_CODE not in after["roles"]
        _log("%s · 계정은 그대로 있다(삭제 0)" % ("되돌렸다" if ok else "★ 안 떨어졌다"))
        return 0 if ok else 1

    # ── 만들기 ───────────────────────────────────────────────────────────
    before_billing = _billing_users_count()
    _log("청구 셈(전) · " + json.dumps(before_billing, ensure_ascii=False))

    existing = _fresh_user()
    created_this_run = False
    if existing is None:
        _log("계정이 아직 없다 — 만든다: %s" % USERNAME)
        if not args.apply:
            _log("재 보기만 했다 — 만들려면 --apply "
                 "(GX_SEED_ROLE_PASSWORD 필요 · 삭제 0 · 실사용자 비밀번호 0건 건드림)")
            return 0
        _do_create(args.base_url)
        created_this_run = True
    else:
        _log("계정이 이미 있다 — 다시 만들지 않는다(멱등): %s" % USERNAME)
        if not args.apply:
            _log("재 보기만 했다 — 표식·역할 상태만 확인하려면 --apply")
            return 0

    u = _fresh_user()
    if u is None:
        raise SystemExit("[U56/P-261] ★ 만들었다는데 되읽어지지 않는다 — 멈춘다")

    if not u.is_active or getattr(u, "deleted", None) is not None:
        raise SystemExit(
            "[U56/P-261] ★ 살아 있는 계정이 아니다(is_active=%s · deleted=%s) — 멈춘다"
            % (u.is_active, getattr(u, "deleted", None)))

    # ── ★★ 순서: mark_unbillable 먼저 ────────────────────────────────────
    from common.billing_marks import SEED_SOURCE, mark_unbillable, marked_unbillable_ids

    mark_unbillable(
        u, SEED_SOURCE,
        reason="U56 P-261 gxseed_role_order — 표 밖 역할(order) 측정 전용 시드. "
               "청구 제외(순서: mark 가 role 보다 먼저)")
    _log("mark_unbillable 완료(role 부여 전)")

    # ── 그 다음에야 역할을 준다 ──────────────────────────────────────────
    Role = apps.get_model("role", "Role")
    order_role = Role.objects.filter(code=ROLE_CODE).first()
    if order_role is None:
        raise SystemExit("[U56/P-261] ★ 역할 코드 %r 가 이 DB 에 없다 — 멈춘다" % ROLE_CODE)
    u.roles.add(order_role)
    _log("role=%s 부여 완료(mark 뒤)" % ROLE_CODE)

    # ── 독립 재조회로 확인 (같은 인스턴스로 확인하지 않는다) ──────────────
    fresh = _fresh_user()
    User = get_user_model()
    marked_ids = marked_unbillable_ids(User)
    after = {
        "id": fresh.id, "username": fresh.username, "roles": _roles(fresh),
        "is_active": fresh.is_active, "deleted": str(getattr(fresh, "deleted", None)),
        "tenant": _tenant_name(fresh),
        "unbillable_marked": fresh.id in marked_ids,
    }
    _log("확인(독립 재조회) · " + json.dumps(after, ensure_ascii=False))

    after_billing = _billing_users_count()
    _log("청구 셈(후) · " + json.dumps(after_billing, ensure_ascii=False))

    ok = (
        after["roles"] == [ROLE_CODE]
        and after["is_active"] and after["deleted"] == "None"
        and after["unbillable_marked"]
        and after["tenant"] == GROUP_NAME
    )
    billing_ok = (
        before_billing["users"] is None or after_billing["users"] is None
        or after_billing["users"] <= before_billing["users"]
    )
    if not billing_ok:
        _log("★★ 청구가 늘었다 — 이 계정은 시드가 아니다: 전=%s 후=%s"
             % (before_billing["users"], after_billing["users"]))
    _log("결과 · 계정 상태 %s · 청구 0증가 %s · 새로 만듦=%s"
         % ("OK" if ok else "★FAIL", "OK" if billing_ok else "★FAIL", created_this_run))
    return 0 if (ok and billing_ok) else 2


if __name__ == "__main__":
    sys.exit(main())
