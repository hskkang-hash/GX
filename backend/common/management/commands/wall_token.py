# -*- coding: utf-8 -*-
"""UX-24a — 월(wall) 표시 토큰의 **발급 · 회수**. 대장은 `docs/agent/authn_paths.md` §9-3.

★ 왜 HTTP 문이 아니라 관리 명령인가
-----------------------------------
발급 문을 네트워크에 내면 **그 문 자체가 새 공격면**이다. 월 토큰은 한 달에 몇 번 나가는
물건이고, 그런 것에 상시 열린 문을 주지 않는다(D-300 부작위 — 「안 열린 것」이 기본값).
그리고 이 절의 약속은 **쓰기 0** 이다. 발급을 HTTP 쓰기 문으로 만들면 그 약속이 첫 줄부터
깨진다.

    발급   python manage.py wall_token issue  --user <계정> [--note "관제실 A 대형화면"]
    회수   python manage.py wall_token revoke --jti <jti>
    전부   python manage.py wall_token revoke --all
    확인   python manage.py wall_token show   --token <토큰>

⚠ 토큰은 **한 번만 보인다.** 이 명령은 어디에도 저장하지 않는다 — 자체 완결(서명)이고,
  잃어버리면 새로 발급한다. 저장하지 않는 비밀은 새지 않는다.
"""
from __future__ import annotations

import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from common.wall_token import (
    WALL_SCREEN_PATH,
    WALL_TOKEN_HEADER,
    WALL_TOKEN_PATHS,
    WALL_TOKEN_TTL_SECONDS,
    issue,
    revoke,
    verify,
    wall_token_enabled,
)


class Command(BaseCommand):
    help = "UX-24a 월 표시 토큰 발급·회수 (읽기 전용 · 12시간 · /wall 하나)"

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("issue", "revoke", "show"))
        parser.add_argument("--user", help="발급 대상 계정(username). issue 에 필요하다")
        parser.add_argument("--note", default="", help="어느 화면인가 — 사람이 알아볼 한 줄")
        parser.add_argument("--jti", help="회수할 토큰의 jti")
        parser.add_argument("--all", action="store_true",
                            help="지금까지 나간 토큰 **전부** 회수 (WALL_TOKEN_EPOCH)")
        parser.add_argument("--token", help="show — 이 토큰이 무엇인지 읽는다")

    def handle(self, *args, **opts):
        if not wall_token_enabled():
            self.stderr.write("⚠ WALL_TOKEN_ENABLED=False — 이 문은 지금 통째로 닫혀 있다")
        action = opts["action"]
        if action == "issue":
            return self._issue(opts)
        if action == "revoke":
            return self._revoke(opts)
        return self._show(opts)

    # ── 발급 ────────────────────────────────────────────────────────────
    def _issue(self, opts):
        username = opts.get("user")
        if not username:
            raise CommandError("--user 가 필요하다 — 이 토큰은 **누구의 자격으로** 읽는가")
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"그런 계정이 없다: {username}")

        token, claims = issue(user.id, note=opts.get("note") or "")
        exp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(claims["exp"]))
        self.stdout.write("")
        self.stdout.write(f"  {WALL_TOKEN_HEADER}: {token}")
        self.stdout.write("")
        self.stdout.write(f"  대상 계정  {user.username} (id={user.id})")
        self.stdout.write(f"  jti        {claims['jti']}   ← 회수할 때 이 값을 쓴다")
        self.stdout.write(f"  만료       {exp}  ({WALL_TOKEN_TTL_SECONDS // 3600}시간)")
        self.stdout.write(f"  화면       {WALL_SCREEN_PATH}  (하나뿐이다)")
        self.stdout.write(f"  열리는 문  {', '.join(WALL_TOKEN_PATHS)}  ← **읽기만**")
        self.stdout.write("")
        self.stdout.write("  ⚠ 이 토큰은 다시 볼 수 없다. 저장하지 않는다 — 잃어버리면 다시 발급한다.")
        self.stdout.write("  ⚠ 이 토큰으로는 아무것도 쓸 수 없다. 쓰기 문은 전부 403 이다.")

    # ── 회수 ────────────────────────────────────────────────────────────
    def _revoke(self, opts):
        if opts.get("all"):
            now = int(time.time())
            self.stdout.write("")
            self.stdout.write("  **전부 회수**하려면 설정에 다음 한 줄을 넣고 서버를 다시 띄운다:")
            self.stdout.write("")
            self.stdout.write(f"      WALL_TOKEN_EPOCH = {now}")
            self.stdout.write("")
            self.stdout.write("  그 시각 **이전에 발급된 토큰 전부**가 즉시 죽는다.")
            self.stdout.write("  ★ 캐시가 아니라 설정값인 이유: 재기동해도 살아 있어야 하는 판정이다.")
            return
        jti = opts.get("jti")
        if not jti:
            raise CommandError("--jti 또는 --all 이 필요하다")
        revoke(jti)
        self.stdout.write(f"회수했다: jti={jti}")
        self.stdout.write("⚠ 회수 목록은 캐시다 — 재기동하면 빈다. 급한 회수는 --all 이 답이다.")

    # ── 확인 ────────────────────────────────────────────────────────────
    def _show(self, opts):
        token = opts.get("token")
        if not token:
            raise CommandError("--token 이 필요하다")
        claims, reason = verify(token)
        if claims is None:
            self.stdout.write(f"통하지 않는다: {reason}")
            return
        self.stdout.write(str(claims))
