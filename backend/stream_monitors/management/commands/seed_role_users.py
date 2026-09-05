# -*- coding: utf-8 -*-
"""역할을 가진 **사람**을 실제 생성 경로로 심는다 — U1 · U2 · U4 (P-9 · D-401 계열).

왜 이 명령이 생겼나 — **화면이 없는 것이 아니라 사람이 없었다**
--------------------------------------------------------------------
온보딩 48행은 U2(관제팀장) 75% · U3(이동 중) 50% 를 적어 두었지만, 그 판정을
화면으로 확인하려면 **그 역할을 가진 계정으로 로그인**해야 한다. 착수 전에 쟀다:

    [실측 2026-09-04 · database_guardianx · 소속 4 ETRI-Group]
      gxprobe_e2e            역할 0개          ← 탐침 계정에 역할이 없다
      fire_admin (U2)        그 소속에 0명
      view_only_-_anyang(U4) 그 소속에 0명
      operator   (U1)        12명
      critical 수신자 12명   — **전원 operator**. U2·U4 자리는 규칙만 서 있고 사람이 없다

    [실측 2026-09-24 · 같은 소속 · U2·U4 를 심은 뒤]
      fire_admin (U2)        1명   ← 2026-09-04 시드가 메웠다
      view_only_-_anyang(U4) 1명   ← 같음
      operator   (U1)        12명
      fire_user  (U1)        **0명**  ← 규칙 `critical/fire_user` 는 서 있는데 사람이 없다
      critical 수신자 14명

    ★ `fire_user` 가 남아 있던 이유는 「U1 은 이미 12명 있다」고 읽었기 때문이다.
      그러나 K2 규칙은 **역할 코드**를 가리키고, `operator` 와 `fire_user` 는 다른 코드다.
      「U1 자리에 사람이 있다」와 「이 규칙이 고르는 사람이 있다」는 다른 사실이다 —
      OPS-10 발송처 표가 `fire_user/log 0명`을 critical 로 찍어서야 갈렸다(D-301).

즉 K2 규칙 넷(`fire_user`·`operator`·`fire_admin`·`view_only_-_anyang`)은 이미 서 있고,
그중 **둘은 아무에게도 도달하지 않는다.** 「규칙이 있다」와 「받을 사람이 있다」가
다른 사실이라는 것을 `seed_dsm_events._report_recipients` 가 이미 적어 두었다(D-301).
이 명령이 메우는 것은 그 둘째 자리다.

★ **시드는 규칙을 흉내 내지 않는다** (P-20 ④ · P-9)
---------------------------------------------------
사람 하나를 만드는 데는 여러 갈래가 있다. 이 명령이 **쓰지 않는** 갈래부터 적는다:

    ✗ `CoreUser.objects.create(...)` · `_base_manager.create(...)`
    ✗ `user.roles.add(role)` 로 역할을 직접 붙이기
    ✗ `UserProfileLink.objects.create(...)` 로 소속을 직접 붙이기

셋 다 **모형**이다. 그렇게 만든 사람은 제품이 사람을 만들 때 지나는 자리를 한 번도
안 지난다 — 중복 username·중복 email 검사, 기본 역할 대체 규칙, `UserSettings` 생성,
`ensure_complete_profile`, 알림 채널 구독. 그 자리들의 결함은 모형 위에서 절대
드러나지 않는다. 화면을 띄우는 것이 가장 강한 시험인 이유(D-386)가 그대로 뒤집힌다.

그래서 이 명령은 **한 자리만** 두드린다:

    POST {base_url}/api/v1/user/create-user      (core/api/v1/user.py :: create_user)

**진짜 HTTP 다.** 떠 있는 서버가 없으면 이 명령은 심지 않고 멈춘다(exit≠0) —
서버 없이 ORM 으로 흘러내리는 우회로를 두지 않는다. 우회로가 있으면 언젠가 그 길로
가고, 그때 「실제 경로로 심었다」는 문장은 거짓이 된다.

★ 표식 — **시드로 세운 사람임이 행 안에 남는다** (P-9 · `data_source=seed`)
---------------------------------------------------------------------------
표는 셋이고, 셋 다 **제품이 읽는 칸**에 들어간다. 지울 때의 유일한 근거이고,
검수 화면의 「데이터 출처: 시드」 표기도 이 표에서 나온다:

    ① username 접두   `gxseed_`
    ② 사원번호        `employee_id = "GX-SEED-ROLE-<역할키>"`  ← 판정기가 보는 칸
                      (칸에 UNIQUE 제약이 있어 사람마다 갈린다 — 아래 `SEED_MARKER`)
    ③ 표시 이름       `[시드] …`                        ← 화면에 그대로 보인다

시드로 찍은 화면은 **실제 화면이지만 실제 사람은 아니다.** 고객이 그것을 구분할 수
있어야 한다.

★ 비밀번호는 저장소에 없다 (D-204 · P-12 ①)
--------------------------------------------
`--password` 또는 환경변수 `GX_SEED_ROLE_PASSWORD` 로만 받는다. 기본값을 두지 않는다 —
기본값을 두면 그 값이 곧 저장소에 적힌 비밀번호다. 제품 규칙상 **특수문자 1자 이상**.

사용법
------
    # 서버를 먼저 띄운다 (차선 E3 는 8500)
    docker exec -d -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        sh -c 'cd /app && python manage.py runserver 0.0.0.0:8500 --noreload'

    python manage.py seed_role_users --peer gxprobe_e2e --report
    GX_SEED_ROLE_PASSWORD='…' python manage.py seed_role_users \
        --peer gxprobe_e2e --base-url http://127.0.0.1:8500
    python manage.py seed_role_users --peer gxprobe_e2e --purge

★ `--purge` 는 ORM 으로 지운다 — 그리고 **그 사실을 숨기지 않는다.**
  지우는 문(`DELETE /api/v1/user/delete-user/{id}`)은 관리자 토큰을 요구하고, 이 환경에
  그 자격은 없다. **지우기는 이 명령이 세우려는 사실(「실제 경로로 생겼는가」)이 아니므로**
  우회를 허용하되, 표식 셋을 **전부** 만족하는 행만 지운다. 하나라도 어긋나면 멈춘다.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

# ═══════════════════════════════════════════════════════════════════════════
# 표식 — 이 셋이 「시드로 세운 사람」의 유일한 근거다
# ═══════════════════════════════════════════════════════════════════════════
#: 사원번호 칸에 남는 표의 **접두**. `UserProfileLink.employee_id` 는 32자다 — 넘지 않는다.
#:
#: ★ 접두인 이유 [실측 2026-09-04 · 첫 실행이 이것으로 깨졌다]:
#:   `user_profile_link.employee_id` 에 **UNIQUE 제약**이 걸려 있다. 두 사람에게 같은
#:   표를 달면 둘째가 `duplicate key value violates unique constraint
#:   "user_profile_link_employee_id_key"` 로 죽고, 화면에는 그냥 `400 Failed to create
#:   user.` 만 온다 — **사유가 응답에 안 실린다.** 그래서 표는 `GX-SEED-ROLE-U2` 처럼
#:   사람마다 갈리고, 판정은 접두로 한다.
#:   ⚠ 이 사실은 **실제 경로로 심었기 때문에** 드러났다. ORM 으로 직접 만들었어도 같은
#:     제약에 걸렸겠지만, 「제품이 사람을 만들 때 이 400 을 낸다」는 사실은 안 나왔다.
SEED_MARKER = "GX-SEED-ROLE"

#: username 접두. 목록 화면에서 눈으로도 갈린다.
SEED_PREFIX = "gxseed_"

#: 표시 이름 접두. **화면에 그대로 보이는 자리**다.
SEED_NAME_PREFIX = "[시드]"

#: 이메일 도메인. `.invalid` 는 RFC 2606 이 「절대 존재하지 않는다」고 못 박은 TLD 다 —
#: 실수로 메일이 나가도 도달할 곳이 없다. 탐침 계정(`@example.invalid`)과 같은 규약.
SEED_EMAIL_DOMAIN = "seed.invalid"


# ═══════════════════════════════════════════════════════════════════════════
# 심을 사람 셋 — **역할 코드는 실측 목록에서 고른다**(config/k3_roles.py 머리말)
# ═══════════════════════════════════════════════════════════════════════════
#: 지시서가 요구한 것은 「U1(`fire_user`)·U2·U4 역할 사람 **각 1명**」이다. 더 심지 않는다 —
#: 수를 늘리면 「몇 명이 옳은가」를 시드가 정하게 되고, 그것은 지시서가 정하지 않은 수다.
#:
#: ⚠ `role_code` 를 바꿀 때는 `config.k3_roles.K3_ROLE_PRESET_MAP` 을 함께 봐야 한다.
#:   그 표가 역할 → 프리셋을 정하고, 프리셋이 곧 「이 사람이 보는 화면」이다.
SEED_PEOPLE = (
    {
        "key": "U1",
        "username": SEED_PREFIX + "u1_operator",
        "role_code": "fire_user",
        "expect_preset": "OPERATOR",
        "display": "%s U1 관제요원(화재)" % SEED_NAME_PREFIX,
        "why": "화면 앞에 앉아 이벤트를 처리하는 사람. K3 OPERATOR 프리셋. "
               "★ 이 자리는 **경보가 갈 곳**이다 — K2 규칙 `critical/fire_user` 는 "
               "2026-09-04 부터 서 있었는데 그 역할에 사람이 0명이었다(실측 2026-09-24). "
               "규칙이 있고 사람이 0명이면 경보는 아무 데도 안 간다(D-301)",
    },
    {
        "key": "U2",
        "username": SEED_PREFIX + "u2_manager",
        "role_code": "fire_admin",
        "expect_preset": "MANAGER",
        "display": "%s U2 관제팀장/상황실장" % SEED_NAME_PREFIX,
        "why": "규칙·임계값·수신자를 정하는 사람. K3 MANAGER 프리셋(위젯 편집 4종)",
    },
    {
        "key": "U4",
        "username": SEED_PREFIX + "u4_official",
        "role_code": "view_only_-_anyang",
        "expect_preset": "EXECUTIVE",
        "display": "%s U4 재난안전과 담당 공무원" % SEED_NAME_PREFIX,
        "why": "열람 전용. K3 EXECUTIVE 프리셋 — 편집 위젯 0종이 정상이다",
    },
)

#: 만드는 문. **하나뿐이다.**
CREATE_PATH = "/api/v1/user/create-user"

#: 기본 주소. 차선 E3 의 포트(P-18 차선 격리). 다른 차선의 8000/8300/8400 을 치지 않는다.
DEFAULT_BASE_URL = "http://127.0.0.1:8500"


def _refuse_if_shared_master() -> None:
    """지우기 전에 **공용 마스터인지 묻는다** (D-270 ③).

    이 커맨드는 시드 사람을 만들고, `--purge` 로 지운다. 지우는 것은 되돌릴 수 없다 —
    사용자 표가 **공용 마스터**라면 그 행은 우리 테넌트의 것이 아니고, 지우는 순간
    남의 것을 지운 것이 된다.

    등록부(`tests/tenant_classification.py`)가 그 분류의 **유일한 출처**다 —
    판정식을 복사하지 않는다(D-212). **못 읽으면 지우지 않는다**:
    「검사 못함」과 「대상 아님」은 다른 사실이다(D-301).
    """
    try:
        from tests.tenant_classification import SHARED_MASTERS
    except ImportError as exc:                     # pragma: no cover - 환경 문제
        raise CommandError(
            "분류 등록부(tests/tenant_classification.py)를 읽지 못했다: %s — "
            "공용 마스터인지 확인하지 못한 채로 지우지 않는다 (D-270 ③ · D-301)" % exc)
    for label in ("user.CoreUser", "user.UserProfileLink"):
        if label in SHARED_MASTERS:
            raise CommandError(
                "%s 이 분류 등록부에서 **공용 마스터**다. 시드 사람을 공용 표에서 "
                "지우면 남의 것을 지운 것이 된다" % label)


class Command(BaseCommand):
    help = "U1·U2·U4 역할을 가진 사람을 **실제 생성 경로(HTTP)** 로 심는다"

    def add_arguments(self, parser):
        parser.add_argument("--peer", default="gxprobe_e2e",
                            help="이 계정과 **같은 소속**에 심는다 (기본: gxprobe_e2e)")
        parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                            help="떠 있는 서버 주소. 여기로 진짜 HTTP 를 보낸다")
        parser.add_argument("--password", default=None,
                            help="심을 계정의 비밀번호. 없으면 GX_SEED_ROLE_PASSWORD 를 읽는다")
        parser.add_argument("--purge", action="store_true", help="심은 사람을 지운다")
        parser.add_argument("--report", action="store_true", help="세기만 한다")

    # ── 소속 ─────────────────────────────────────────────────────────────
    def _group(self, username):
        """소속은 **제품이 읽는 방식 그대로** 읽는다 (`common.tenant_filters.get_user_group`).

        두 벌로 읽으면 화면이 보는 소속과 시드가 심긴 소속이 갈라진다 — 화면은 「0건」을
        그리고, 그것은 격리가 제대로 걸린 결과인데 결함처럼 보인다(D-369).
        """
        from django.contrib.auth import get_user_model

        from common.tenant_filters import get_user_group

        user = get_user_model()._base_manager.filter(username=username).first()
        if user is None:
            raise CommandError("계정이 없다: %s" % username)
        group = get_user_group(user)
        if group is None:
            raise CommandError(
                "%s 에 소속이 없다 — 같은 소속에 심을 수가 없다. "
                "격리를 끄지 않는다(D-105)" % username)
        return user, group

    # ── 역할 ─────────────────────────────────────────────────────────────
    def _role(self, code):
        """역할 코드 → 역할 행. **없으면 만들지 않는다.**

        ★ 여기서 `Role.objects.create(code=…)` 로 없는 역할을 지어내면, 그 순간
          이 명령은 **권한 체계를 발명한다.** 역할은 이 제품의 계약이고 시드의 것이
          아니다 — 없으면 그 사실을 말하고 멈춘다(D-301: 없음과 못 만듦을 가른다).
        """
        from django.apps import apps

        Role = apps.get_model("role", "Role")
        role = Role.objects.filter(code=code).first()
        if role is None:
            have = ", ".join(sorted(Role.objects.values_list("code", flat=True)))
            raise CommandError(
                "역할 코드 %r 가 이 DB 에 없다. 시드는 역할을 만들지 않는다 — "
                "있는 것: %s" % (code, have))
        return role

    # ── 실제 생성 경로 ────────────────────────────────────────────────────
    def _post_create(self, base_url, payload):
        """`POST /api/v1/user/create-user` **하나만** 부른다.

        ★ 실패를 삼키지 않는다. 4xx 본문을 그대로 올린다 — 「만들었다고 했는데 없다」가
          가장 나쁜 결과이고, 그것은 실패를 조용히 넘겼을 때만 생긴다.
        """
        url = base_url.rstrip("/") + CREATE_PATH
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")
        except OSError as exc:
            raise CommandError(
                "서버에 닿지 못했다: %s (%s)\n"
                "  이 명령은 **실제 HTTP 경로로만** 심는다. ORM 우회로는 없다 — "
                "runserver 를 먼저 띄워라:\n"
                "  docker exec -d -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \\\n"
                "      sh -c 'cd /app && python manage.py runserver 0.0.0.0:8500 --noreload'"
                % (url, exc))

    # ── 표식 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _marker(spec):
        """이 사람의 사원번호 칸에 들어갈 표. **UNIQUE 제약이 있어 사람마다 갈린다.**"""
        return "%s-%s" % (SEED_MARKER, spec["key"])

    # ── 되읽기 — **만들었다와 있다는 다른 사실이다** ───────────────────────
    def _readback(self, spec, group):
        """지금 DB 에 무엇이 있는지 센다. 방금 한 일을 세지 않는다.

        돌려주는 것: `(user, 사유목록)` — 사유가 비면 온전하다.
        """
        from django.apps import apps
        from django.contrib.auth import get_user_model

        Profile = apps.get_model("user", "UserProfileLink")
        user = get_user_model()._base_manager.filter(
            username=spec["username"]).first()
        if user is None:
            return None, ["행이 없다"]

        bad = []
        codes = sorted(r.code for r in user.roles.all())
        if codes != [spec["role_code"]]:
            bad.append("역할이 %s (기대 %s)" % (codes or "없음", [spec["role_code"]]))
        if not user.is_active:
            bad.append("비활성 — 수신자 목록에 안 잡힌다")
        if user.is_superuser or user.is_staff:
            bad.append("superuser/staff 다 — 시드 사람에게 줄 것이 아니다")

        prof = Profile.objects.filter(user=user).first()
        if prof is None:
            bad.append("프로필이 없다 — 소속이 없으면 어느 화면에도 안 보인다")
        else:
            if prof.group_id != group.pk:
                bad.append("소속이 %s (기대 %s)" % (prof.group_id, group.pk))
            want_mark = self._marker(spec)
            if (prof.employee_id or "") != want_mark:
                bad.append("표식이 %r (기대 %r)" % (prof.employee_id, want_mark))
            if not (prof.name or "").startswith(SEED_NAME_PREFIX):
                bad.append("표시 이름에 %s 가 없다" % SEED_NAME_PREFIX)
        return user, bad

    def _preset_of(self, user):
        """이 사람이 로그인 직후 떨어질 화면. **K3 커널에게 묻는다** — 표를 복사하지 않는다.

        `config.k3_roles.K3_ROLE_PRESET_MAP` 을 여기서 다시 읽으면 판정식이 두 벌이 되고,
        두 벌은 반드시 어긋난다(D-369). 커널이 답하는 그 값이 곧 화면이다.
        """
        try:
            from common.tenant_scope import TenantScope
            from kernels.k3_dashboard.services import get_preset
        except ImportError as exc:                       # noqa: BLE001
            return None, "K3 를 읽지 못했다: %s" % exc
        try:
            view = get_preset(scope=TenantScope.of(user))
        except Exception as exc:                         # noqa: BLE001
            return None, "%s: %s" % (type(exc).__name__, exc)
        return getattr(view, "preset", None), (
            "matched=%s" % getattr(view, "matched", "?"))

    # ── 보고 ─────────────────────────────────────────────────────────────
    def _report(self, group, peer):
        """이 소속의 **역할별 사람 수**와 **critical 수신자**를 센다.

        ★ 둘을 함께 세는 이유: 「사람이 늘었다」와 「알림이 도달한다」는 다른 사실이다.
          역할에 사람을 넣어도 그 역할을 가리키는 규칙이 없으면 수신자는 안 는다.
        """
        from django.apps import apps
        from django.contrib.auth import get_user_model

        User = get_user_model()
        Role = apps.get_model("role", "Role")
        wanted = [s["role_code"] for s in SEED_PEOPLE]

        self.stdout.write("[SEED] 소속 %s(%s) · 기준 계정 %s"
                          % (group.pk, getattr(group, "name", "?"), peer.username))
        self.stdout.write("[SEED] ── 역할별 사람 수 (활성 · 이 소속) ──")
        for code in sorted(set(wanted) | {"operator", "fire_user"}):
            if Role.objects.filter(code=code).first() is None:
                self.stdout.write("[SEED]   %-24s 역할 자체가 없다" % code)
                continue
            n = User.objects.filter(roles__code=code,
                                    userprofilelink__group=group,
                                    is_active=True).distinct().count()
            mark = " ←" if code in wanted else ""
            self.stdout.write("[SEED]   %-24s %d명%s" % (code, n, mark))

        seeded = User._base_manager.filter(
            username__startswith=SEED_PREFIX,
            userprofilelink__employee_id__startswith=SEED_MARKER).distinct()
        self.stdout.write("[SEED] ── 시드로 세운 사람 %d명 ──" % seeded.count())
        for u in seeded.order_by("username"):
            codes = ",".join(sorted(r.code for r in u.roles.all())) or "없음"
            preset, note = self._preset_of(u)
            self.stdout.write("[SEED]   %-22s 역할=%-20s 프리셋=%s (%s)"
                              % (u.username, codes, preset, note))

        # 수신자 — K2 에게 묻는다. 시드가 세지 않는다.
        try:
            from common.tenant_scope import TenantScope
            from kernels.k2_notify import resolve_recipients

            people = resolve_recipients(scope=TenantScope.of(peer),
                                        severity="critical", group=group)
            by = {}
            for r in people:
                by[r.role_code] = by.get(r.role_code, 0) + 1
            self.stdout.write("[SEED] [실측] critical 수신자 %d명 — 역할별 %s"
                              % (len(people), by or "0명"))
        except Exception as exc:                          # noqa: BLE001
            self.stdout.write("[SEED] ⚠ 수신자를 **못 쟀다** (%s: %s) — 0명이 아니다"
                              % (type(exc).__name__, exc))

    # ── 지우기 ───────────────────────────────────────────────────────────
    def _purge(self):
        """표식 셋을 **전부** 만족하는 행만 지운다. 하나라도 어긋나면 멈춘다."""
        from django.apps import apps
        from django.contrib.auth import get_user_model

        Profile = apps.get_model("user", "UserProfileLink")
        User = get_user_model()
        names = [s["username"] for s in SEED_PEOPLE]
        gone = 0
        for name in names:
            user = User._base_manager.filter(username=name).first()
            if user is None:
                continue
            prof = Profile.objects.filter(user=user).first()
            if prof is None or not (prof.employee_id or "").startswith(SEED_MARKER):
                raise CommandError(
                    "%s 에 시드 표식(%s)이 없다 — **지우지 않는다.** 같은 이름의 "
                    "다른 사람일 수 있다" % (name, SEED_MARKER))
            if user.is_superuser or user.is_staff:
                raise CommandError("%s 가 superuser/staff 다 — 지우지 않는다" % name)
            _refuse_if_shared_master()
            user.delete()
            gone += 1
            self.stdout.write("[SEED] 지웠다: %s" % name)
        self.stdout.write("[SEED] 지운 사람 %d명" % gone)

    # ── 본체 ─────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        peer, group = self._group(opts["peer"])

        if opts["purge"]:
            self._purge()
            self._report(group, peer)
            return
        if opts["report"]:
            self._report(group, peer)
            return

        password = opts["password"] or os.environ.get("GX_SEED_ROLE_PASSWORD")
        if not password:
            raise CommandError(
                "비밀번호가 없다. `--password` 또는 환경변수 GX_SEED_ROLE_PASSWORD 로 준다. "
                "기본값을 두지 않는다 — 기본값은 곧 저장소에 적힌 비밀번호다(D-204)")
        if password.isalnum():
            raise CommandError("제품 규칙: 비밀번호에 특수문자가 1자 이상 있어야 한다")

        base_url = opts["base_url"]
        self.stdout.write("[SEED] ── 착수 전 ──")
        self._report(group, peer)

        made, kept = 0, 0
        for spec in SEED_PEOPLE:
            role = self._role(spec["role_code"])
            existing, bad = self._readback(spec, group)
            if existing is not None and not bad:
                kept += 1
                self.stdout.write("[SEED] 이미 있다: %s — 다시 만들지 않는다"
                                  % spec["username"])
                continue
            if existing is not None:
                # ★ [실측 2026-09-04] 여기서 「이미 있으니 넘어간다」로 지나가면 안 된다.
                #   `create-user` 는 **한 트랜잭션이 아니다.** `CoreUser` 를 먼저 만들고
                #   그 뒤에 `UserProfileLink`·역할·설정을 붙이는데, 뒤에서 죽으면
                #   앞의 행이 남는다 — 소속도 역할도 없는 **반쪽 사람**이다. 그런데
                #   응답은 `400 Failed to create user.` 이므로 부른 쪽은 "안 생겼다"고 읽는다.
                #   그 상태로 다시 부르면 이번엔 `Username already exists` 가 나고,
                #   반쪽 사람은 영원히 거기 남는다. 이 명령은 그 자리에서 멈춘다.
                raise CommandError(
                    "%s 행은 있는데 **온전하지 않다**: %s — "
                    "`create-user` 는 원자적이지 않다. 프로필 생성에서 죽으면 "
                    "CoreUser 행만 남고 응답은 400 이다. 그 반쪽 행을 먼저 치워야 한다."
                    % (spec["username"], ", ".join(bad)))

            payload = {
                "username": spec["username"],
                "email": "%s@%s" % (spec["username"], SEED_EMAIL_DOMAIN),
                "password": password,
                "first_name": spec["display"],
                "last_name": "",
                "is_active": True,          # 비활성이면 수신자 목록에 안 잡힌다
                "is_staff": False,
                "is_superuser": False,
                "otp_exempt": True,         # 검수 환경에 OTP 수신 수단이 없다
                "roles": [role.pk],
                "employee_id": self._marker(spec),
                "group_id": group.pk,
                "is_default": True,
            }
            status, body = self._post_create(base_url, payload)
            self.stdout.write("[SEED] POST %s%s → %s"
                              % (base_url.rstrip("/"), CREATE_PATH, status))
            if status not in (200, 201):
                raise CommandError(
                    "%s 를 만들지 못했다 (HTTP %s): %s" % (spec["username"], status, body))
            made += 1

        # ── 되읽기 판정 ──────────────────────────────────────────────────
        self.stdout.write("[SEED] ── 되읽기 (방금 한 일이 아니라 **지금 있는 것**) ──")
        broken = []
        for spec in SEED_PEOPLE:
            user, bad = self._readback(spec, group)
            preset, note = (None, "행이 없다") if user is None else self._preset_of(user)
            if preset != spec["expect_preset"]:
                bad = list(bad) + ["프리셋이 %s (기대 %s · %s)"
                                   % (preset, spec["expect_preset"], note)]
            if bad:
                broken.append((spec["username"], bad))
            self.stdout.write(
                "[SEED]   %-3s %-22s 역할=%-20s 프리셋=%-10s %s"
                % (spec["key"], spec["username"], spec["role_code"],
                   preset, "OK" if not bad else "✗ " + " · ".join(bad)))

        self.stdout.write("[SEED] ── 착수 후 ──")
        self._report(group, peer)
        self.stdout.write("[SEED] 새로 만든 사람 %d명 · 이미 있던 사람 %d명" % (made, kept))
        if broken:
            raise CommandError(
                "심었지만 **온전하지 않다**: %s"
                % "; ".join("%s(%s)" % (n, ", ".join(b)) for n, b in broken))
