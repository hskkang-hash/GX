# -*- coding: utf-8 -*-
"""P-339 · P-349 — **스모크 전용 계정 `gx-smoke`** (턴 AJ · 2026-09-25).

왜 따로 세우나 [실측 2026-09-24 · 턴 AI]
----------------------------------------
`scripts/smoke_live.py` 는 로그인 한 번을 잰다. 계정이 없어 **역할 계정 U4
(`gxseed_u4_official`)로 물러섰고**, 로그인은 `end_previous_session: true` 라 U4 로
재고 있는 사람(V 단독 · 대표 걷기)의 세션을 끊는다 — 「재는 동안 아무도 로그인하지
않는다」의 반대편이다. 스모크는 **제 계정**으로 들어가야 한다.

무엇을 세우나 (세종 P-339 ①)
----------------------------
    username   `gx-smoke`                 ← 저장소에 적는 것은 이 이름뿐
    역할       `view_only_-_anyang`        ← 읽기 전용(쓰기 문을 못 연다)
    소속       `--peer`(기본 gxprobe_e2e) 와 같은 검증 소속
    이메일     환경 `GX_SMOKE_EMAIL`       ← 대표가 정한 주소 · 저장소에 안 적는다
    비밀번호   환경 `GX_SMOKE_PASSWORD`    ← `.env.gates` 에만 · 기본값 없음(D-204)
    표식       곁표 `BillingMark(probe)`   ← 청구·수에서 빠진다(P-224 · 이름으로 안 거른다)
    사원번호   `GX-SMOKE`                  ← 제품이 읽는 칸에 남는 두 번째 표식

만드는 길은 `seed_role_users` 와 **같은 한 문**이다 — `POST /api/v1/user/create-user`
(진짜 HTTP · ORM 우회 없음). 소속·역할 판정도 그 명령의 것을 빌린다(두 벌로 쓰면 갈라진다).

★ [실측 2026-09-25] 그 문은 이제 **익명에게 닫혀 있다**(401 `authentication required`).
  `seed_role_users` 가 사람을 심던 09-04 에는 열려 있었다 — 닫힌 것이 옳다. 그래서 이
  명령은 **사람을 만들 권한이 있는 계정**(기본 `gxseed_u5_sysop` · 역할 `admin`)으로
  `/api/v1/auth/login` 을 거쳐 들어간다. 그 비밀번호도 이름으로만 받는다(`--admin-password-env`).

⚠ **이 계정은 경보를 받는 역할이다** — `view_only_-_anyang` 은 K2 critical 규칙이
  가리키는 역할이라, 실 SMTP 가 붙는 날 이 계정의 이메일로 경보 메일이 간다(지금은
  `smtp.invalid` · 창 2b 뒤에는 Mailpit — 둘 다 밖으로 안 나간다). 받지 않게 하려면
  그 전에 대표 결정이 필요하다(보고서 대표 손 줄).

되돌리기 = 비활성(`is_active=False`) 한 칸. 이 명령은 **지우지 않는다**.

    GX_SMOKE_PASSWORD=… GX_SMOKE_EMAIL=… python manage.py seed_smoke_user --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from stream_monitors.management.commands.seed_role_users import (
    SEED_NAME_PREFIX,
    Command as RoleSeed,
)

SMOKE_USERNAME = "gx-smoke"
SMOKE_ROLE = "view_only_-_anyang"
SMOKE_MARKER = "GX-SMOKE"
SMOKE_DISPLAY = "%s 스모크 전용(읽기)" % SEED_NAME_PREFIX
ENV_PASSWORD = "GX_SMOKE_PASSWORD"
ENV_EMAIL = "GX_SMOKE_EMAIL"


class Command(BaseCommand):
    help = "스모크 전용 계정 gx-smoke 를 실제 생성 경로로 세우고 probe 표식을 단다"

    def add_arguments(self, parser):
        parser.add_argument("--peer", default="gxprobe_e2e",
                            help="이 계정과 같은 소속에 세운다")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000",
                            help="떠 있는 서버 주소 — 여기로 진짜 HTTP 를 보낸다")
        parser.add_argument("--admin-user", default="gxseed_u5_sysop",
                            help="사람을 만들 권한이 있는 계정(이름)")
        parser.add_argument("--admin-password-env", default="GX_SEED_ROLE_PASSWORD",
                            help="그 계정 비밀번호가 든 **환경 이름**(값은 받지 않는다)")

    @staticmethod
    def _post(url, payload, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")
        except OSError as exc:
            raise CommandError("서버에 닿지 못했다: %s (%s)" % (url, exc))

    def _admin_token(self, base_url, user, env_name):
        password = os.environ.get(env_name)
        if not password:
            raise CommandError("환경 %s 가 비었다 — 만들 권한이 있는 계정으로 못 들어간다" % env_name)
        status, body = self._post(base_url.rstrip("/") + "/api/v1/auth/login",
                                  {"username": user, "password": password,
                                   "end_previous_session": True})
        try:
            parsed = json.loads(body)
            # 제품은 `{"user": {"access_token": …}}` 로 감싼다(verify_route_alive._extract_token).
            token = ((parsed.get("user") or parsed.get("data") or {}).get("access_token")
                     if isinstance(parsed, dict) else None)
        except ValueError:
            token = None
        if status != 200 or not token:
            raise CommandError("%s 로 로그인하지 못했다 (HTTP %s · 토큰 %s)"
                               % (user, status, "있음" if token else "없음"))
        return token

    def _readback(self, group):
        """`(user, 사유목록)` — 사유가 비면 온전하다. 지금 있는 것을 센다."""
        from django.apps import apps
        from django.contrib.auth import get_user_model

        user = get_user_model()._base_manager.filter(username=SMOKE_USERNAME).first()
        if user is None:
            return None, ["행이 없다"]
        bad = []
        codes = sorted(r.code for r in user.roles.all())
        if codes != [SMOKE_ROLE]:
            bad.append("역할이 %s (기대 %s)" % (codes or "없음", [SMOKE_ROLE]))
        if user.is_superuser or user.is_staff:
            bad.append("superuser/staff 다")
        prof = apps.get_model("user", "UserProfileLink").objects.filter(user=user).first()
        if prof is None:
            bad.append("프로필이 없다")
        else:
            if prof.group_id != group.pk:
                bad.append("소속이 %s (기대 %s)" % (prof.group_id, group.pk))
            if (prof.employee_id or "") != SMOKE_MARKER:
                bad.append("표식이 %r (기대 %r)" % (prof.employee_id, SMOKE_MARKER))
        return user, bad

    def handle(self, *args, **opts):
        seed = RoleSeed()
        seed.stdout, seed.stderr = self.stdout, self.stderr
        _peer, group = seed._group(opts["peer"])
        role = seed._role(SMOKE_ROLE)

        password = os.environ.get(ENV_PASSWORD)
        email = os.environ.get(ENV_EMAIL)
        if not password or not email:
            raise CommandError("%s · %s 둘 다 환경으로 준다 — 기본값은 없다(D-204)"
                               % (ENV_PASSWORD, ENV_EMAIL))
        if password.isalnum():
            raise CommandError("제품 규칙: 비밀번호에 특수문자가 1자 이상 있어야 한다")

        user, bad = self._readback(group)
        if user is not None and bad:
            raise CommandError("%s 행은 있는데 온전하지 않다: %s" % (SMOKE_USERNAME, ", ".join(bad)))
        if user is None:
            token = self._admin_token(opts["base_url"], opts["admin_user"],
                                      opts["admin_password_env"])
            status, body = self._post(opts["base_url"].rstrip("/") + "/api/v1/user/create-user", {
                "username": SMOKE_USERNAME,
                "email": email,
                "password": password,
                "first_name": SMOKE_DISPLAY,
                "last_name": "",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "otp_exempt": True,
                "roles": [role.pk],
                "employee_id": SMOKE_MARKER,
                "group_id": group.pk,
                "is_default": True,
            }, token)
            self.stdout.write("[SMOKE-SEED] POST create-user → %s" % status)
            if status not in (200, 201):
                # 본문에 값이 실리지 않는다(제품 응답은 사유 문장뿐) — 그래도 앞 200자만.
                raise CommandError("만들지 못했다 (HTTP %s): %s" % (status, body[:200]))
        else:
            self.stdout.write("[SMOKE-SEED] 이미 있다 — 다시 만들지 않는다")

        user, bad = self._readback(group)
        if user is None or bad:
            raise CommandError("세웠지만 온전하지 않다: %s" % ", ".join(bad))
        from common.billing_marks import mark_unbillable
        from common.probe_marker import PROBE_MARKER
        mark_unbillable(user, PROBE_MARKER.split("=", 1)[1],
                        reason="seed_smoke_user — 스모크 전용 계정(P-339) · 청구·수에서 뺀다")
        self.stdout.write("[SMOKE-SEED] %s · 역할 %s · 소속 %s · 표식 probe · 활성 %s"
                          % (SMOKE_USERNAME, SMOKE_ROLE, group.pk, user.is_active))
