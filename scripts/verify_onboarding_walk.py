#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-46 — **온보딩 카드를 닫는 것이 사람인가 기록인가** (턴 R 골격 → 턴 AI 차선 F 짓기 · P-311).

정본이 요구한 것 (PRD v1.1 §5.1 UX-46 · §7.1 · WO-01 §12)
----------------------------------------------------------
    "역할별 「처음 시작하기」 카드 7개 이하 · 완료 체크는 실제 행위(서버 기록)로 자동 ·
     진행률 % 역할 홈 상단 · 100%면 카드 숨김"
    AC: "각 역할 시드 계정으로 카드 전부 수행 → 진행률 100 · `verify_onboarding_walk` 신설"

그래서 이 판정기는 **세 층**이다 — 그리고 나쁜 쪽이 이긴다(한 수로 뭉개지 않는다)
--------------------------------------------------------------------------------
    ㉠ **구조**(서버 없이 지금 잰다) — 카드 표가 실재하고 · 역할마다 일곱 장 이하이고 ·
       **사람이 누르는 완료 문이 없고** · 라우트가 선언(테넌트 범위)과 인증을 달고 있고 ·
       화면이 그 라우트를 **부른다**(잠든 라우트가 아니다)
    ㉡ **로그인 계획**(서버 없이 지금 잰다 · `--dry-run`) — 6 버킷을 실재가 확인된 계정
       (U1·U2·U4·U5·U5 예비)으로 **어떻게** 덮을지 소스에서 읽어 짠다. 네트워크 0.
    ㉢ **걷기**(역할 계정으로 실제 HTTP · `--api`) — ㉡ 의 계획대로 로그인하고
       `GET /api/dsm/onboarding/progress`(카드 7 각각의 서버 기록을 이미 센 응답)를
       읽어 역할별 N/분모를 낸다.

㉢ 은 **서버와 자격증명이 있을 때만** 잰다. 없으면 **회색(exit 2)** 이다 —
「못 쟀다」는 「통과」가 아니다(D-301 · D-400). 게이트가 환경을 요구해 초록으로 죽는
길을 만들지 않으려고, 기본 판정은 ㉠만 하고 ㉢은 `--api` 를 준 실행에서만 돈다.

    python scripts/verify_onboarding_walk.py                 # ㉠ 구조 판정
    python scripts/verify_onboarding_walk.py --list          # 카드 표 전수
    python scripts/verify_onboarding_walk.py --dry-run        # ㉡ 로그인 계획만(네트워크 0)
    python scripts/verify_onboarding_walk.py --api URL        # ㉠+㉡+㉢ (V_LOCK 이면 ㉢ 회색)
    python scripts/verify_onboarding_walk.py --self-test     # 양성·음성 대조 (D-277)

종료 코드 (저장소 규약 · D-400): 0 = 쟀고 통과 · 1 = 쟀고 실패 · 2 = **못 쟀다(회색)**

★ [P-311 · 09-24 · 턴 AI] **이 턴은 걷지 않는다.** 걷기(㉢)는 짓지만 **부르지 않는다**
  — 역할 계정 로그인은 살아 있는 세션을 끊는다(`end_previous_session`), 그리고 V 의
  재측 앞에서 끼어들면 그 수가 망가진다(P-170 ①). 첫 실측은 V 가 한다. 이 턴이 낸 것은
  `--dry-run`(무엇을 할지 · 네트워크 0)까지다 — **지은 뒤의 첫 수가 첫 수**이고, 그 전엔
  회색을 유지한다(0 이라 적지 않는다).
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONBOARDING = ROOT / "backend" / "apps" / "dsm" / "onboarding.py"
ROUTER = ROOT / "backend" / "apps" / "dsm" / "api_f.py"
URLS = ROOT / "backend" / "apps" / "dsm" / "urls.py"
FRONTEND = ROOT / "frontend" / "src"
TEST = ROOT / "backend" / "tests" / "test_onboarding_progress.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: `verify_route_alive` 의 `login()`·`load_local_env()`·`expand_env_refs()` 를 **그대로**
#: 쓴다 — 로그인 문(`/api/v1/auth/login` · `end_previous_session` · 율제한 재시도 ·
#: V_LOCK 존중)을 이 파일이 두 번째로 적으면 두 벌은 반드시 어긋난다(D-369).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_route_alive import expand_env_refs, load_local_env, login  # noqa: E402

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 정본이 적은 상한. 넘기면 첫날에 아무도 안 읽는다 (PRD §7.2).
MAX_CARDS_PER_ROLE = 7

#: 진행률 라우트. 화면과 시험과 이 판정기가 **같은 문자열**을 봐야 한다.
ROUTE_PATH = "/onboarding/progress"

#: 라우트 표면에 반드시 있어야 하는 둘. 하나라도 없으면 그 라우트는 태어나면서 샌다.
REQUIRED_ON_ROUTE = ("@tenant_scoped", "auth=")

#: PRD §7.2 가 적은 **여섯 사람**. WO-01 §6 파 3 이 「진행률 6/6」이라고 적은 그 여섯이다.
#: 표에 없는 사람은 카드가 0장이고, 0장인 사람의 진행률은 잴 수 없다 — 그것이 6/6 이
#: 아니라 5/6 인 이유이고, 이 판정기가 그 차이를 **이름으로** 잡는 자리다.
EXPECTED_BUCKETS = ("U1", "U2", "U3", "U4", "U5", "U6")

#: 진행률 문의 실재 자리 [실측 2026-09-24 · `backend/apps/dsm/api_f.py:50`] —
#: `DsmFAPI.onboarding_progress` · `GET /api/dsm/onboarding/progress` · `persona=` 인자.
#: 「없으면 없다를 실측으로」(P-311) — **있다.** 사라지면(리팩터) `judge_progress_response`
#: 의 404 갈래가 회색으로 잡는다(거짓 초록을 안 낸다).
PROGRESS_ENDPOINT = "/api/dsm" + ROUTE_PATH

#: ★ [P-311 · 09-24 · 턴 AI 차선 F] **실재가 확인된** 시드 역할 계정 넷 —
#: `backend/stream_monitors/management/commands/seed_role_users.py:134,147,156,165` 가
#: 만드는 그대로다(`SEED_PREFIX = "gxseed_"`). `verify_sidebar.HTTP_ACCOUNTS` 와 **같은
#: 이름**이다 — 자기시험이 그 사실을 대조한다(아래 · D-369, 드리프트를 구조로 막는다).
CONFIRMED_ROLE_ACCOUNTS: dict[str, str] = {
    "U1": "gxseed_u1_operator",
    "U2": "gxseed_u2_manager",
    "U4": "gxseed_u4_official",
    "U5": "gxseed_u5_sysop",
}

#: U5 의 **예비 계정** — `backend/common/migrations/0003_p224_seed_account_marks.py:64`
#: 가 적은 그대로: 「온보딩 첫 근무일 계측용 예비 계정」. U6(외부 연계 · 기계)은 사람
#: 계정이 없어 페르소나 질의로만 열리는데, U5 본계정으로 열면 U5 자신의 온보딩 실측과
#: 섞인다 — 그래서 이 예비 계정으로 연다(그 계정이 태어난 이유 그대로 쓰는 것이다).
#: ⚠ `gxseed_u3_field` 는 **여기 안 쓴다** — `rotate_shared_passwords.py` 의
#: `NEVER_TOUCH` 목록에만 있고 **만드는 코드가 없다**(seed_role_users.py 에 없다 ·
#: 0003 마이그레이션 장부에 없다). 실재를 확인 못 한 이름으로 로그인을 시도하지
#: 않는다 — 시도해서 얻는 것은 헷갈리는 회색뿐이다(존재하지 않는 계정과 자격증명
#: 오류를 가르지 못한다). U3 는 아래처럼 **뷰어 계정 + persona 질의**로 연다.
U5_RESERVE_ACCOUNT = "gxseed_u5_newop"


# ══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 **순수 함수**로 둔다 (D-277)
# ══════════════════════════════════════════════════════════════════════════
def code_only(text: str) -> str:
    """주석을 뺀 원문. 주석은 **왜 그런지를 적는 자리**이고, 그것까지 세면 설명을
    지워야 초록이 나는 시험이 된다."""
    return "\n".join(line for line in text.splitlines()
                     if not line.strip().startswith("#"))


def cards_per_role(src: str) -> dict[str, list[tuple[str, bool]]]:
    """카드 표를 **소스에서** 읽는다 — `(카드 키, 닫는 술어가 있는가)`.

    Django 를 부르지 않는다: 게이트가 컨테이너를 요구하면 환경이 죽는 날 게이트도
    죽고, 그 죽음은 조용하다. 표는 리터럴이므로 구문 트리로 충분하다.
    """
    out: dict[str, list[tuple[str, bool]]] = {}
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "CARDS" not in names or not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or not isinstance(value, ast.Tuple):
                continue
            rows: list[tuple[str, bool]] = []
            for call in value.elts:
                if not isinstance(call, ast.Call) or not call.args:
                    continue
                card_key = call.args[0]
                if not isinstance(card_key, ast.Constant):
                    continue
                # 닫는 술어는 **넷째 자리(positional)** 또는 `closes=` 다.
                closes = len(call.args) >= 4 or any(
                    kw.arg == "closes" for kw in call.keywords)
                rows.append((str(card_key.value), closes))
            out[str(key.value)] = rows
    return out


def role_buckets(src: str) -> list[str]:
    """`_role_buckets()` 가 역할 코드로 고르는 버킷들 — **소스에서** 읽는다."""
    tree = ast.parse(src)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_role_buckets":
            continue
        for pair in ast.walk(node):
            if not isinstance(pair, ast.Tuple) or len(pair.elts) != 2:
                continue
            first = pair.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.append(first.value)
    return out


def persona_viewers(src: str) -> dict[str, list[str]]:
    """`PERSONA_VIEWERS` — 역할이 아닌 사람을 **누가 볼 수 있는가**."""
    tree = ast.parse(src)
    out: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if "PERSONA_VIEWERS" not in [t.id for t in node.targets
                                     if isinstance(t, ast.Name)]:
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant) or not isinstance(
                    value, (ast.Tuple, ast.List)):
                continue
            out[str(key.value)] = [e.value for e in value.elts
                                   if isinstance(e, ast.Constant)]
    return out


def card_links(src: str) -> dict[str, str]:
    """카드 키 → 그 카드가 여는 화면 주소(`Card` 의 셋째 자리)."""
    out: dict[str, str] = {}
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 3:
            continue
        key, link = node.args[0], node.args[2]
        if isinstance(key, ast.Constant) and isinstance(link, ast.Constant) and \
                isinstance(key.value, str) and isinstance(link.value, str) and \
                link.value.startswith("/"):
            out[key.value] = link.value
    return out


def declared_screen_paths(texts: list[str]) -> set[str]:
    """앞판 라우트 표가 선언한 주소 전수 — `path: '/...'` 를 그대로 집는다."""
    found: set[str] = set()
    for text in texts:
        # ★ 정규식에 역슬래시를 쓰지 않는다 — 이 파일을 고치는 도구마다 그 한 글자가
        #   다르게 살아남는다. 공백은 `[ ]*` 로, 따옴표는 문자군으로 적으면 충분하다.
        found.update(re.findall("""path:[ ]*["'](/[^"']*)["']""", text))
    return found


def inherited_screen_paths(app_src: str) -> set[str]:
    """**인수 자산(rj-core)이 들고 있는 화면 주소.** [실측 2026-09-19 · 턴 W · 차선 F]

    ★ 이 함수가 없으면 이 판정기는 **거짓 빨강**을 낸다. 출생 사례 그대로다:
      카드 `u1.profile -> /profile` 을 「없는 화면」이라고 적었는데, 그 화면은
      **실재한다** — `App.tsx:818` 이 `{ path: CustomRouters.profile.path,
      element: <ProfilePage /> }` 로 마운트하고, 로그인 되돌아갈 자리(`fallback`)도
      거기다. 못 본 이유는 하나다: `CustomRouters` 는 `rj-core` 에서 오고(§0.4
      금지구역 · `package.json` 의 git 의존), **그 표는 이 저장소에 없다.**
      우리 라우트 표 셋만 보면 인수 자산의 화면은 전부 「없는 화면」이 된다.

    ★ 그래서 **주소가 아니라 이름으로** 맞춘다 — `path: CustomRouters.profile.path`
      에서 `profile` 을 집어 `/profile` 로 친다. 읽을 수 없는 표를 읽은 척하지
      않으면서, 마운트된 사실은 `App.tsx` 에서 **실제로 읽은** 것이다.
      오타는 여전히 잡힌다: `/profil` 은 `profile` 과 다르므로 빨강 그대로다.
    """
    #: 역슬래시를 쓰지 않는다 — 이 파일의 다른 정규식과 같은 사유(도구마다 살아남는
    #: 방식이 다르다). 점은 문자군으로 적는다.
    found: set[str] = set()
    for key in re.findall("path:[ ]*CustomRouters[.]([A-Za-z0-9_]+)", app_src):
        found.add("/" + key)
    return found


def dead_card_links(src: str, screen_paths: set[str]) -> list[str]:
    """**없는 화면을 가리키는 카드.** 있으면 그 카드는 열리지 않는 문을 가리킨다.

    링크는 사람이 손으로 적는 문자열이라 오타 하나로 조용히 죽는다 — 죽은 링크는
    「자리가 없다」와 구별되지 않고(`why` 가 그 말을 하는 자리다), 구별되지 않으면
    다음 사람이 「자리를 만들어야 한다」고 읽는다.
    ★ 변수 조각(`:id`)은 카드가 가리키지 않는다 — 카드는 목록·홈으로 연다.
    """
    if not screen_paths:      # 라우트 표를 못 읽었으면 **판정하지 않는다**(회색 · D-301)
        return []
    return sorted(f"{key} -> {link}" for key, link in card_links(src).items()
                  if link.split("?")[0] not in screen_paths)


def unreachable_buckets(src: str) -> list[str]:
    """**아무도 못 보는 카드 표.** 있으면 그 표의 진행률은 영원히 안 읽힌다.

    카드를 늘리는 것과 그 카드가 누군가에게 보이는 것은 다른 일이다. 역할 코드로도
    (`_role_buckets`) 이름으로도(`PERSONA_VIEWERS`) 닿지 않는 버킷은 **분모 0의 자리**이고,
    그 자리를 세어 「6/6」이라고 적으면 그 수는 거짓이다 (D-301).
    """
    reachable = set(role_buckets(src)) | set(persona_viewers(src))
    return sorted(b for b in cards_per_role(src) if b not in reachable)


def unviewable_personas(src: str) -> list[str]:
    """`PERSONA_VIEWERS` 에 적혔는데 **카드 표가 없는** 이름 · 볼 사람이 역할이 아닌 이름."""
    table = cards_per_role(src)
    roles = set(role_buckets(src))
    bad: list[str] = []
    for persona, viewers in sorted(persona_viewers(src).items()):
        if persona not in table:
            bad.append(f"{persona}: 볼 수 있다고 적었는데 카드 표가 없다")
        if not viewers:
            bad.append(f"{persona}: 볼 사람이 0명이다 — 아무도 못 보는 표다")
        for viewer in viewers:
            if viewer not in roles:
                bad.append(f"{persona}: 보는 쪽 {viewer} 가 역할 버킷이 아니다 "
                           f"(_role_buckets 에 없다)")
    return bad


def has_write_door(router_src: str) -> bool:
    """사람이 눌러 카드를 닫는 문이 있는가. **있으면 그것이 체크박스다.**"""
    return "@route.post" in code_only(router_src) or \
           "@route.put" in code_only(router_src)


def route_is_declared(router_src: str) -> list[str]:
    """라우트 표면에 없어서는 안 되는 것들 중 **빠진 것**."""
    body = code_only(router_src)
    return [token for token in REQUIRED_ON_ROUTE if token not in body]


def frontend_calls(files: list[tuple[str, str]], route_path: str) -> list[str]:
    """이 라우트를 **부르는 화면 파일**들. 0건이면 잠든 라우트다(착시 ⑨)."""
    return [name for name, text in files if route_path in text]


# ══════════════════════════════════════════════════════════════════════════
# ㉡ 로그인 계획 — **순수 함수**(D-277). 소스만 읽는다 · 네트워크 0
# ══════════════════════════════════════════════════════════════════════════
def role_walk_plan(src: str, confirmed: dict[str, str],
                    reserve: tuple[str, str] | None = None
                    ) -> dict[str, tuple[str, str]]:
    """버킷(최대 6개) → `(로그인 계정, persona 질의)`. **실재가 확인된 계정만** 담는다.

    ① 역할 버킷(U1·U2·U4·U5)은 `confirmed` 의 그 계정을 persona 없이 그대로 연다.
    ② 페르소나(U3·U6)는 `onboarding.PERSONA_VIEWERS`(이 파일의 `persona_viewers()`가
       **소스에서** 읽는다 — 두 번째 표를 안 둔다 · D-369)가 정한 「볼 수 있는 역할」
       중 `confirmed` 에 있는 **첫 이름**으로 연다. `reserve=(역할, 계정)` 이 주어지고
       그 페르소나의 뷰어 목록에 그 역할이 있으면 **예비 계정을 먼저** 쓴다(본계정의
       실측과 섞이지 않도록).
    ③ 뷰어 전원이 `confirmed`(와 `reserve`)에 없는 페르소나는 **표에서 뺀다** — 계정이
       없는 것을 0 으로 지어내지 않는다(D-301). 빠진 버킷은 회색으로 보고된다.
    """
    plan: dict[str, tuple[str, str]] = {}
    for bucket, user in sorted(confirmed.items()):
        plan[bucket] = (user, "")
    reserve_role, reserve_user = reserve or (None, None)
    for persona, viewers in sorted(persona_viewers(src).items()):
        if reserve_role and reserve_user and reserve_role in viewers:
            plan[persona] = (reserve_user, persona)
            continue
        opener = next((v for v in viewers if v in confirmed), None)
        if opener:
            plan[persona] = (confirmed[opener], persona)
        # else: 계정이 없다 — 표에서 뺀다(그 버킷은 회색으로 보고된다)
    return plan


def judge_progress_response(status: int, body: dict) -> tuple[int, str]:
    """진행률 응답 **하나**를 판정한다. 순수 함수 — HTTP 없이 시험한다 (D-277).

    ★ **0/N 과 회색을 가른다.** 「분모를 못 셌다」(회색)와 「분모 N 중 0 을 했다」(초록 ·
      쟀다)는 다른 사실이다. 못 잰 것을 0 으로 적으면 그 0 은 거짓이다(D-301) — 이
      가름이 이 함수가 존재하는 이유다.
    """
    if status == 404:
        return EXIT_UNDECIDABLE, "진행률 문이 없다(404) — 아직 없는 것이지 실패가 아니다"
    if status in (401, 403):
        return EXIT_UNDECIDABLE, ("진행률 문 HTTP %d — 토큰이 안 먹혔거나 이 자리가 "
                                  "아니다(재려던 것을 못 쟀다)" % status)
    if status is not None and status >= 500:
        return EXIT_FAIL, "진행률 문이 서버 오류를 낸다(HTTP %d)" % status
    if status != 200:
        return EXIT_UNDECIDABLE, "진행률 문 HTTP %s — 못 쟀다" % status
    total = body.get("total") if isinstance(body, dict) else None
    if not isinstance(total, int) or total <= 0:
        return EXIT_UNDECIDABLE, ("분모를 못 셌다(total=%r) — 0/0 을 지어내지 않는다 "
                                  "(D-301)" % (total,))
    done = body.get("done")
    if not isinstance(done, int):
        return EXIT_UNDECIDABLE, "done 이 없다(응답 모양이 바뀌었을 수 있다)"
    return EXIT_OK, "%d/%d" % (done, total)


def combine_role_codes(results: dict[str, dict]) -> tuple[int, str]:
    """버킷별 판정을 **하나**로 접는다. 나쁜 쪽이 이긴다(기존 `walk()` 규약과 같다).

    ① 계획이 비면 회색(D-301) ② 하나라도 **빨강**(서버 5xx)이면 회색보다 빨강이 이긴다
    — 진짜 결함이다 ③ 그 밖에 하나라도 **회색**이면 전체가 회색이다 — **여섯을 다 재야
    첫 수다**(P-311 · 「그 전엔 회색 유지 · 0 이라 적지 않는다」) ④ 여섯 다 쟀을 때만 초록.
    """
    if not results:
        return EXIT_UNDECIDABLE, "계획이 비었다 — 잴 역할이 없다"
    codes = {b: r.get("code") for b, r in results.items()}
    reds = sorted(b for b, c in codes.items() if c == EXIT_FAIL)
    if reds:
        return EXIT_FAIL, "빨강 %d: %s" % (len(reds), reds)
    grays = sorted(b for b, c in codes.items() if c != EXIT_OK)
    if grays:
        return EXIT_UNDECIDABLE, ("회색 %d/%d: %s — 여섯을 다 재야 첫 수다(P-311)"
                                  % (len(grays), len(codes), grays))
    return EXIT_OK, "%d개 버킷 다 쟀다" % len(codes)


# ══════════════════════════════════════════════════════════════════════════
# ㉠ 구조 판정
# ══════════════════════════════════════════════════════════════════════════
def judge_structure() -> int:
    if not ONBOARDING.is_file() or not ROUTER.is_file():
        print(f"[UX-46] GRAY 카드 표 또는 라우터 파일이 없다 "
              f"({ONBOARDING.name} · {ROUTER.name}) — 판정 불가")
        return EXIT_UNDECIDABLE

    src = ONBOARDING.read_text(encoding="utf-8")
    router_src = ROUTER.read_text(encoding="utf-8")
    table = cards_per_role(src)
    if not table:
        print("[UX-46] GRAY 카드 표를 못 읽었다 — 0건 위의 「위반 0」은 초록이 아니다")
        return EXIT_UNDECIDABLE

    total = sum(len(v) for v in table.values())
    closable = sum(1 for v in table.values() for _, c in v if c)
    print(f"[입력] 사람 {len(table)}/{len(EXPECTED_BUCKETS)} · 카드 {total}장 "
          f"(서버 기록이 닫는 카드 {closable} · 아직 못 재는 카드 {total - closable}) "
          f"· 표={ONBOARDING.relative_to(ROOT)}")

    bad: list[str] = []

    for role, rows in sorted(table.items()):
        if len(rows) > MAX_CARDS_PER_ROLE:
            bad.append(f"{role} 카드 {len(rows)}장 — 상한 {MAX_CARDS_PER_ROLE}장(PRD §7.2)")
        if not any(c for _, c in rows):
            bad.append(f"{role} 에 서버 기록이 닫는 카드가 **한 장도 없다** — "
                       f"그 역할의 진행률은 영원히 0이고, 0은 아무것도 증명하지 않는다")

    missing_buckets = [b for b in EXPECTED_BUCKETS if b not in table]
    if missing_buckets:
        bad.append(f"카드 표가 없는 사람 {' · '.join(missing_buckets)} — PRD §7.2 는 "
                   f"여섯 사람을 적었고 WO-01 파 3 은 「진행률 6/6」을 적었다. "
                   f"표가 없는 사람의 진행률은 0 이 아니라 **없다**")
    orphans = unreachable_buckets(src)
    if orphans:
        bad.append(f"아무도 못 보는 카드 표 {' · '.join(orphans)} — 역할 코드로도 "
                   f"이름(PERSONA_VIEWERS)으로도 닿지 않는다. 닿지 않는 표를 세어 "
                   f"6/6 이라고 적으면 그 수는 거짓이다(D-301)")
    for line in unviewable_personas(src):
        bad.append(line)

    if has_write_door(router_src):
        bad.append("온보딩 라우터에 쓰기 문이 있다 — 카드를 사람이 닫으면 진행률은 "
                   "「했다」가 아니라 「했다고 적었다」를 센다(WO-01 §12)")

    missing = route_is_declared(router_src)
    if missing:
        bad.append(f"라우트 표면에 {' · '.join(missing)} 가 없다 — "
                   f"선언 없이 태어난 라우트다(ISO-03)")

    if URLS.is_file() and "DsmFAPI" not in code_only(URLS.read_text(encoding="utf-8")):
        bad.append("라우터가 `urls.py` 에 등록되지 않았다 — 파일은 있고 경로는 없다")

    route_tables = []
    for name in ("features/dsm/routes.ts", "features/mobile/routes.ts",
                 "features/nav/roleNav.ts"):
        path = FRONTEND / name
        if path.is_file():
            route_tables.append(path.read_text(encoding="utf-8"))
    screen_paths = declared_screen_paths(route_tables)
    #: ★ 인수 자산(rj-core)이 들고 있는 화면도 **선언된 화면이다.** 우리 표 셋만 보면
    #:   `/profile` 같은 자리가 「없는 화면」이 된다 — 거짓 빨강이다(턴 W 실측).
    inherited: set[str] = set()
    app_tsx = FRONTEND / "App.tsx"
    if app_tsx.is_file():
        inherited = inherited_screen_paths(app_tsx.read_text(encoding="utf-8"))
        if inherited:
            print(f"[UX-46] 인수 자산 화면 {len(inherited)}자리 — `App.tsx` 가 "
                  f"`CustomRouters.*` 로 마운트한다(표 자체는 rj-core · 저장소 밖)")
    screen_paths |= inherited
    if not screen_paths:
        print("[UX-46] GRAY 앞판 라우트 표를 못 읽었다 — 카드 링크는 **판정하지 않는다**")
    else:
        dead_links = dead_card_links(src, screen_paths)
        print(f"[UX-46] 카드 링크 대조 — 선언된 화면 주소 {len(screen_paths)}자리"
              f"(우리 표 {len(screen_paths) - len(inherited)} · 인수 자산 {len(inherited)})")
        for line in dead_links:
            bad.append(f"카드가 **없는 화면**을 가리킨다: {line} — 열리지 않는 문을 "
                       f"가리키는 카드는 「자리가 아직 없다」와 구별되지 않는다")

    files = []
    if FRONTEND.is_dir():
        for path in FRONTEND.rglob("*.ts*"):
            try:
                files.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
            except OSError:
                continue
    callers = frontend_calls(files, ROUTE_PATH)
    if not callers:
        bad.append(f"화면 중 {ROUTE_PATH} 를 부르는 파일이 0건이다 — "
                   f"만들어졌으나 켜지지 않은 라우트다(착시 ⑨)")
    else:
        print(f"[UX-46] 부르는 화면 {len(callers)}건: {' · '.join(sorted(callers)[:3])}")

    if not TEST.is_file():
        bad.append(f"규약 시험이 없다({TEST.relative_to(ROOT)}) — "
                   f"지워진 규약은 지워진 것이 보이지 않는다")

    if bad:
        print(f"[UX-46] **구조 위반 {len(bad)}건** — 멈춘다")
        for line in bad:
            print(f"  · {line}")
        return EXIT_FAIL

    print("[UX-46] 구조 통과 — 카드 표 · 자동 완료 술어 · 선언된 라우트 · 부르는 화면 · 시험")
    return EXIT_OK


# ══════════════════════════════════════════════════════════════════════════
# ㉢ 걷기 — **서버와 역할 계정이 있을 때만.** 없으면 회색이다 (P-311 · 짓기)
# ══════════════════════════════════════════════════════════════════════════
def accounts_needed(plan: dict[str, tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
    """계정 이름 → `[(버킷, persona 질의)]`. **로그인은 계정당 한 번**뿐이다.

    ★ 로그인에는 속도 제한이 있다(IP 기준 분당 5회 · `verify_route_alive.py` 머리말).
      U3 은 U1 계정으로, U6 는 예비 계정으로 열리므로 계정 하나가 버킷 둘을 덮을 수
      있다 — 그때마다 새로 로그인하면 6버킷에 로그인을 6번 쓰고, 이 게이트 하나가
      다른 게이트의 몫까지 태운다(D-460 의 그 사고). 계정별로 묶어 **한 번만** 로그인한다.
    """
    by_user: dict[str, list[tuple[str, str]]] = {}
    for bucket, (user, persona) in sorted(plan.items()):
        by_user.setdefault(user, []).append((bucket, persona))
    return by_user


def walk_all_roles(api: str, plan: dict[str, tuple[str, str]]) -> dict[str, dict]:
    """계획의 버킷마다 **실제로** 로그인하고 진행률을 읽는다.

    ★ 로그인 못 받음(V_LOCK · 자격없음 · 율제한 소진)은 **회색**이지 0 이 아니다 —
      `login()` 이 `None` 을 돌려주면 그 계정이 덮는 버킷 전부를 회색으로 적는다.
      「로그인 200 인데 토큰이 없다」(제품이 200 + success:false 로 「다른 세션 있음」을
      내는 그 자리 · `verify_route_alive._extract_token`)도 여기서는 **똑같이 회색**이다
      — `login()` 이 이미 그 갈래를 가려 `None` 하나로 묶어 주기 때문이다(두 벌 판독을
      안 둔다 · D-369).

    돌려주는 것: `{버킷: {"code", "why", "user", "total", "done"}}`.
    """
    import json
    import urllib.error
    import urllib.request

    password = os.environ.get("GX_SEED_ROLE_PASSWORD", "")
    out: dict[str, dict] = {}
    if not password:
        for bucket in plan:
            out[bucket] = {"code": EXIT_UNDECIDABLE, "user": plan[bucket][0],
                           "total": None, "done": None,
                           "why": "GX_SEED_ROLE_PASSWORD 가 없다 — 로그인을 시도하지 않는다"}
        return out

    for user, entries in sorted(accounts_needed(plan).items()):
        token = login(api, user, password)
        if not token:
            for bucket, _persona in entries:
                out[bucket] = {"code": EXIT_UNDECIDABLE, "user": user, "total": None,
                               "done": None,
                               "why": "로그인 실패 — 토큰을 못 받았다(V_LOCK·자격없음·"
                                      "율제한·다른 세션 중 하나 · login() 이 가른다)"}
            continue
        for bucket, persona in entries:
            qs = ("?persona=" + persona) if persona else ""
            req = urllib.request.Request(
                api.rstrip("/") + PROGRESS_ENDPOINT + qs,
                headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310
                    status = r.status
                    body = json.loads(r.read().decode("utf-8", "replace") or "{}")
            except urllib.error.HTTPError as exc:
                status, body = exc.code, {}
            except Exception as exc:                       # noqa: BLE001
                out[bucket] = {"code": EXIT_UNDECIDABLE, "user": user, "total": None,
                               "done": None, "why": "%s: %s" % (type(exc).__name__, exc)}
                continue
            code, why = judge_progress_response(status, body)
            out[bucket] = {"code": code, "user": user,
                           "total": body.get("total") if isinstance(body, dict) else None,
                           "done": body.get("done") if isinstance(body, dict) else None,
                           "why": why}
    return out


# ══════════════════════════════════════════════════════════════════════════
# 자기시험 — 판정식이 **잡는가**를 잡는다 (D-277)
# ══════════════════════════════════════════════════════════════════════════
#: ★ **출생 표본** — 이 도구를 만들게 한 바로 그 사례를 fixture 로 박는다 (D-310).
#:
#: [실측 2026-09-16 · 턴 R · 차선 F] 온보딩 카드 27장 중 **서버 기록이 닫을 수 있는
#: 것은 11장**이었고, 16장은 「화면을 열어 봤다」류라 닫을 기록이 없었다. 그 자리에서
#: 진행률을 100 으로 만드는 길이 둘 보였고, **둘 다 거짓말이다**:
#:
#:     ① 못 재는 16장을 표에서 **지운다** → 분모가 조용히 줄어 11/11 = 100% 가 된다.
#:        지워진 카드는 지워진 것이 보이지 않는다 — 분모는 손으로 적지 않는다(D-301).
#:     ② 카드를 닫는 **POST 문을 하나 낸다** → 사람이 눌러 닫는다. 그러면 진행률은
#:        「했다」가 아니라 **「했다고 적었다」**를 센다(WO-01 §12).
#:
#: 차선은 둘 다 하지 않고 16장을 `blocked` 로 이름과 사유와 함께 남겼다. 이 도구는
#: 다음 사람이 그 둘 중 하나를 고르는 날 멈춰 세우려고 태어났다.
_BIRTH_NO_CLOSER = ('CARDS = {\n'
                    '    "U2": (\n'
                    '        Card("u2.open_list", "목록을 열어 봤다", "/x"),\n'
                    '        Card("u2.open_stats", "통계를 열어 봤다", "/x"),\n'
                    '    ),\n'
                    '}\n')

#: 출생 표본 ② — 사람이 눌러 카드를 닫는 문. 이것이 있으면 그것이 곧 체크박스다.
_BIRTH_WRITE_DOOR = '@route.post("/onboarding/cards/{key}/done", auth=A())\n'

#: 출생 표본 ③ — **카드 표는 있는데 그 표를 열 사람이 없다** (턴 V · 차선 F).
#: U3(이동 중)·U6(외부 연계)은 역할 코드가 없는 사람이라 `bucket_of` 가 절대 고르지
#: 못한다. 표만 넣고 보는 길을 안 내면 카드 수는 늘고 진행률은 영영 안 읽힌다.
_ORPHAN_CARDS = ('CARDS = {\n'
                 '    "U9": (\n'
                 '        Card("u9.a", "t", "/x", _closed_by_x),\n'
                 '    ),\n'
                 '}\n')
_BIRTH_ORPHAN_BUCKET = _ORPHAN_CARDS + 'def _role_buckets():\n    return (("U1", A),)\n'
_BIRTH_REACHABLE = _ORPHAN_CARDS + 'def _role_buckets():\n    return (("U9", A),)\n'
_BIRTH_PERSONA = (_ORPHAN_CARDS + 'PERSONA_VIEWERS = {"U9": ("U1",)}\n'
                  'def _role_buckets():\n    return (("U1", A),)\n')
_BIRTH_BAD_VIEWER = (_ORPHAN_CARDS + 'PERSONA_VIEWERS = {"U9": ("U7",)}\n'
                     'def _role_buckets():\n    return (("U1", A),)\n')
_BIRTH_NO_TABLE = (_ORPHAN_CARDS + 'PERSONA_VIEWERS = {"U8": ("U1",)}\n'
                   'def _role_buckets():\n    return (("U9", A),)\n')


#: 출생 표본 ④ — **카드가 가리키는 화면이 없다** (턴 V · 차선 F · 실제로 저질렀다).
_BIRTH_DEAD_LINK = ('CARDS = {@'
                    '    "U9": (@'
                    '        Card("u9.a", "t", "/dsm/settings/integrations", _c),@'
                    '    ),@'
                    '}@').replace("@", chr(10))


#: 앞판 라우트 표의 모양 표본 — 주소를 집는 술어가 **집는가**를 잰다.
_BIRTH_ROUTE_TABLE = "x: { path: '/dsm/home' },  y: { path: '/m/inbox' }"


#: ★ [턴 W] 인수 자산 표본 — `App.tsx` 가 `rj-core` 의 화면을 **이름으로** 마운트하는
#:   모양 그대로다(`path: CustomRouters.profile.path` · `path: CustomRouters.login`).
_BIRTH_INHERITED_ROUTES = (
    "{ path: CustomRouters.profile.path, element: <ProfilePage /> },@"
    "{ path: CustomRouters.login, element: <Login /> },"
).replace("@", chr(10))

_BIRTH_INHERITED_CARD = ('CARDS = {@'
                         '    "U9": (@'
                         '        Card("u9.a", "t", "/profile", _c),@'
                         '    ),@'
                         '}@').replace("@", chr(10))

_BIRTH_INHERITED_TYPO = ('CARDS = {@'
                         '    "U9": (@'
                         '        Card("u9.b", "t", "/profil", _c),@'
                         '    ),@'
                         '}@').replace("@", chr(10))


def self_test() -> int:
    good = ('CARDS = {\n'
            '    "U1": (\n'
            '        Card("u1.review", "t", "/x", _closed_by_my_review),\n'
            '        Card("u1.queue", "t", "/x", why="기록이 없다"),\n'
            '    ),\n'
            '}\n')
    checks = [
        # ★ 출생 표본 둘 — 위 주석의 ①②를 그대로 잰다.
        ("★ 출생 표본 ① — 닫는 술어가 한 장도 없는 역할을 잡는다 "
         "(그 역할의 진행률은 영원히 0이고, 0은 아무것도 증명하지 않는다)",
         cards_per_role(_BIRTH_NO_CLOSER).get("U2") == [("u2.open_list", False),
                                                        ("u2.open_stats", False)]),
        ("★ 출생 표본 ② — 사람이 눌러 닫는 문을 잡는다 "
         "(카드를 사람이 닫으면 「했다고 적었다」를 센다)",
         has_write_door(_BIRTH_WRITE_DOOR)),
        ("표를 읽는다", cards_per_role(good).get("U1") == [("u1.review", True),
                                                        ("u1.queue", False)]),
        ("빈 표는 빈 값", cards_per_role("X = 1") == {}),
        ("쓰기 문을 잡는다", has_write_door("@route.post('/x')")),
        ("주석 속 쓰기 문은 안 센다", not has_write_door("# @route.post('/x')")),
        ("선언 빠짐을 잡는다",
         route_is_declared("@route.get('/x', auth=A())") == ["@tenant_scoped"]),
        ("둘 다 빠지면 둘 다 잡는다",
         route_is_declared("@route.get('/x')") == ["@tenant_scoped", "auth="]),
        ("둘 다 있으면 통과", route_is_declared(
            "@route.get('/x', auth=A())\n@tenant_scoped(reason='r')") == []),
        # ★ [턴 V · 차선 F] 출생 표본 ③ — **아무도 못 보는 카드 표.** U3·U6 을 표에
        #   넣으면서 생긴 새 거짓말 자리다: 카드를 늘리면 「6/6」이라고 적을 수 있는데,
        #   그 표를 열 사람이 없으면 그 수는 아무도 본 적 없는 수다.
        ("★ 출생 표본 ③ — 닿지 않는 카드 표를 잡는다",
         unreachable_buckets(_BIRTH_ORPHAN_BUCKET) == ["U9"]),
        ("닿는 표는 안 잡는다(역할 코드로 닿는다)",
         unreachable_buckets(_BIRTH_REACHABLE) == []),
        ("이름으로 닿는 표도 안 잡는다",
         unreachable_buckets(_BIRTH_PERSONA) == []),
        ("볼 사람이 역할이 아니면 잡는다",
         any("U7" in line for line in unviewable_personas(_BIRTH_BAD_VIEWER))),
        ("카드 표 없는 페르소나를 잡는다",
         any("U8" in line for line in unviewable_personas(_BIRTH_NO_TABLE))),
        # ★ [턴 V · 차선 F] 출생 표본 ④ — **없는 화면을 가리키는 카드.** 이 도구를
        #   만든 자리 그대로다: U6 카드 여섯을 `/dsm/settings/integrations` 로 적었는데
        #   실재하는 주소는 `/dsm/integrations` 였다(앞판 라우트 표 실측). 판정기가
        #   없었으면 여섯 장이 조용히 안 열리는 문을 가리킨 채 「진행률 6/6」이 됐다.
        ("★ 출생 표본 ④ — 없는 화면을 가리키는 카드를 잡는다",
         dead_card_links(_BIRTH_DEAD_LINK, {"/dsm/integrations"})
         == ["u9.a -> /dsm/settings/integrations"]),
        ("실재하는 주소는 안 잡는다",
         dead_card_links(_BIRTH_DEAD_LINK, {"/dsm/settings/integrations"}) == []),
        ("라우트 표를 못 읽으면 **판정하지 않는다**(회색)",
         dead_card_links(_BIRTH_DEAD_LINK, set()) == []),
        ("앞판 라우트 표에서 주소를 집는다",
         declared_screen_paths([_BIRTH_ROUTE_TABLE])
         == {"/dsm/home", "/m/inbox"}),
        # ★ [턴 W · 차선 F] 출생 표본 ⑤ — **거짓 빨강.** 이 판정기가 턴 V 에
        #   `u1.profile -> /profile` 을 「없는 화면」으로 적었다. 그 화면은 실재하고
        #   (`App.tsx` 가 `CustomRouters.profile.path` 로 마운트한다), 못 본 이유는
        #   그 표가 `rj-core`(저장소 밖)에 있기 때문이었다. 거짓 빨강은 진짜 빨강을
        #   덮는다 — 다음 사람은 이 게이트의 빨강을 안 믿게 된다.
        ("★ 출생 표본 ⑤ — 인수 자산 화면을 집는다",
         inherited_screen_paths(_BIRTH_INHERITED_ROUTES) == {"/profile", "/login"}),
        ("인수 자산 화면을 가리키는 카드는 **빨강이 아니다**",
         dead_card_links(_BIRTH_INHERITED_CARD,
                         {"/dsm/home"} | inherited_screen_paths(_BIRTH_INHERITED_ROUTES))
         == []),
        ("그래도 오타는 잡는다 — `/profil` 은 `/profile` 이 아니다",
         dead_card_links(_BIRTH_INHERITED_TYPO,
                         {"/dsm/home"} | inherited_screen_paths(_BIRTH_INHERITED_ROUTES))
         == ["u9.b -> /profil"]),
        ("`App.tsx` 를 못 읽으면 인수 자산 자리는 0이다(없는 것을 지어내지 않는다)",
         inherited_screen_paths("") == set()),
        ("역할 버킷을 읽는다", role_buckets(_BIRTH_REACHABLE) == ["U9"]),
        ("보는 사람 표를 읽는다",
         persona_viewers(_BIRTH_PERSONA) == {"U9": ["U1"]}),
        ("부르는 화면 0건을 잡는다", frontend_calls([("a.ts", "nothing")], ROUTE_PATH) == []),
        ("부르는 화면을 찾는다",
         frontend_calls([("a.ts", f"x = '{ROUTE_PATH}'")], ROUTE_PATH) == ["a.ts"]),
    ]

    # ══════════════════════════════════════════════════════════════════════
    # ★★ [P-311 · 09-24 · 턴 AI 차선 F] 로그인 계획 · 진행률 판정 · 접기 — 짓기
    # ══════════════════════════════════════════════════════════════════════
    _SRC_BOTH_PERSONAS = 'PERSONA_VIEWERS = {"U3": ("U1", "U2", "U4"), "U6": ("U5",)}\n'
    _SRC_ORPHAN_PERSONA = 'PERSONA_VIEWERS = {"U9": ("U7",)}\n'
    _CONF = {"U1": "acct1", "U2": "acct2", "U4": "acct4", "U5": "acct5"}
    _plan_no_reserve = role_walk_plan(_SRC_BOTH_PERSONAS, _CONF)
    _plan_reserve = role_walk_plan(_SRC_BOTH_PERSONAS, _CONF, reserve=("U5", "acct5-reserve"))
    checks += [
        ("역할 버킷은 persona 없이 제 계정 그대로", _plan_no_reserve["U1"] == ("acct1", "")),
        ("페르소나는 뷰어 계정 + persona 질의로 연다(U3 → U1)",
         _plan_no_reserve["U3"] == ("acct1", "U3")),
        ("예비 계정이 있으면 U6 은 본계정이 아니라 예비 계정으로 연다(안 섞는다)",
         _plan_reserve["U6"] == ("acct5-reserve", "U6")),
        ("예비 계정이 없으면 U6 은 뷰어 목록의 첫 confirmed 계정으로 연다",
         _plan_no_reserve["U6"] == ("acct5", "U6")),
        ("★ 뷰어 전원이 계정이 없는 페르소나는 표에서 **빠진다**(0 으로 지어내지 않는다)",
         "U9" not in role_walk_plan(_SRC_ORPHAN_PERSONA, _CONF)),
        ("accounts_needed 는 계정별로 묶는다(로그인 한 번)",
         sorted(accounts_needed(_plan_no_reserve)["acct1"]) == [("U1", ""), ("U3", "U3")]),
    ]

    checks += [
        ("0/7 은 쟀다(초록) — 분모를 못 센 회색과 다르다",
         judge_progress_response(200, {"total": 7, "done": 0}) == (EXIT_OK, "0/7")),
        ("★ 분모를 못 세면 회색이다(0/0 을 지어내지 않는다 · D-301)",
         judge_progress_response(200, {})[0] == EXIT_UNDECIDABLE),
        ("0/7 과 회색은 **다른 판정**이다(둘 다 셈 안 하면 못 가른다)",
         judge_progress_response(200, {"total": 7, "done": 0})[0]
         != judge_progress_response(200, {})[0]),
        ("진행률 문이 없으면(404) 회색이다 — 아직 없는 것이지 실패가 아니다",
         judge_progress_response(404, {})[0] == EXIT_UNDECIDABLE),
        ("401 은 회색이다(토큰이 안 먹혔다 — 재려던 것을 못 쟀다)",
         judge_progress_response(401, {})[0] == EXIT_UNDECIDABLE),
        ("403 도 같은 자리(이 페르소나가 내 자리가 아니다)",
         judge_progress_response(403, {})[0] == EXIT_UNDECIDABLE),
        ("서버 오류(5xx)는 회색이 아니라 **빨강**이다 — 진짜 결함이다",
         judge_progress_response(500, {})[0] == EXIT_FAIL),
        ("total 이 문자열이면(모양이 바뀌었다) 회색이다(정수만 분모다)",
         judge_progress_response(200, {"total": "칠", "done": 0})[0] == EXIT_UNDECIDABLE),
    ]

    checks += [
        ("계획이 비면 회색이다", combine_role_codes({})[0] == EXIT_UNDECIDABLE),
        ("여섯 다 쟀으면(초록) 그때만 초록",
         combine_role_codes({b: {"code": EXIT_OK} for b in EXPECTED_BUCKETS})[0] == EXIT_OK),
        ("★ 다섯만 쟀고 하나가 회색이면 **전체가 회색**이다(여섯 다 재야 첫 수다 · P-311)",
         combine_role_codes({**{b: {"code": EXIT_OK} for b in EXPECTED_BUCKETS[:5]},
                             "U6": {"code": EXIT_UNDECIDABLE}})[0] == EXIT_UNDECIDABLE),
        ("빨강이 하나라도 있으면 회색보다 빨강이 이긴다(진짜 결함)",
         combine_role_codes({"U1": {"code": EXIT_FAIL}, "U2": {"code": EXIT_UNDECIDABLE}})[0]
         == EXIT_FAIL),
    ]

    # ★ D-369 교훈 그대로 — 이 파일의 CONFIRMED_ROLE_ACCOUNTS 가 `verify_sidebar.
    #   HTTP_ACCOUNTS` 와 **갈리면** 둘 중 하나가 거짓말하는 것이다. 매번 다시 대조한다
    #   (믿지 않고 연다 — D-479 교훈과 같은 자리).
    try:
        from verify_sidebar import HTTP_ACCOUNTS as _SIDEBAR_ACCOUNTS  # noqa: PLC0415
        _drift = [b for b in ("U1", "U2", "U4", "U5")
                 if CONFIRMED_ROLE_ACCOUNTS.get(b) != _SIDEBAR_ACCOUNTS.get(b)]
        checks.append(("★ verify_sidebar.HTTP_ACCOUNTS 와 계정 이름이 갈리지 않는다 "
                       "(D-369 — 두 벌은 반드시 어긋난다)", not _drift))
    except ImportError:
        checks.append(("verify_sidebar 를 못 읽어 교차 대조를 건너뛴다(회색 취급 · 실패 아님)",
                       True))

    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'OK ' if ok else 'FAIL'} {name}")
    print(f"[UX-46] 자기시험 {len(checks)}건 중 {len(bad)}건 실패")
    return EXIT_OK if not bad else EXIT_FAIL


def _print_dry_run() -> int:
    """★ [P-311] **로그인 없이** 무엇을 할지만 찍는다. 네트워크 0 — 자격증명을 안 보낸다.

    이 턴은 걷지 않는다(역할 계정 로그인이 살아 있는 세션을 끊는다 · V 의 재측 앞에서
    끼어들면 그 수가 망가진다 · P-170 ①). 첫 실측은 V 가 한다 — 이 함수는 그 전에
    「무엇을 할 계획인지」를 보고에 붙이기 위한 것이다.
    """
    try:
        from v_lock import describe as _v_describe, is_locked as _v_locked  # noqa: PLC0415
    except ImportError:
        _v_locked, _v_describe = (lambda: False), (lambda: "v_lock 모듈을 못 읽었다")
    print("[UX-46] --dry-run — 로그인을 시도하지 않는다. 아래는 계획뿐이다(값 출력 0).")
    print(f"[UX-46] V_LOCK: {'잠김 — ' + _v_describe() if _v_locked() else '없음'}")
    read = load_local_env()
    print(f"[UX-46] 로컬 자격증명 파일 읽음: {', '.join(read) if read else '없음(환경변수만 본다)'}")
    print(f"[UX-46] GX_API 선언: {'있음' if os.environ.get('GX_API') else '없음'}")
    print(f"[UX-46] GX_SEED_ROLE_PASSWORD 선언: "
          f"{'있음' if os.environ.get('GX_SEED_ROLE_PASSWORD') else '없음'} (이름만 · 값은 안 찍는다)")
    if not ONBOARDING.is_file():
        print("[UX-46] ? 온보딩 소스를 못 읽어 계획을 못 짰다")
        return EXIT_UNDECIDABLE
    src = ONBOARDING.read_text(encoding="utf-8")
    plan = role_walk_plan(src, CONFIRMED_ROLE_ACCOUNTS, reserve=("U5", U5_RESERVE_ACCOUNT))
    for bucket in EXPECTED_BUCKETS:
        if bucket not in plan:
            print(f"[UX-46]   {bucket}: 계정 없음 — 표에서 빠진다(그 버킷은 회색으로 보고된다)")
            continue
        user, persona = plan[bucket]
        qs = f"?persona={persona}" if persona else ""
        print(f"[UX-46]   {bucket}: 로그인 시도 {user} (자격 이름 GX_SEED_ROLE_PASSWORD) "
              f"→ GET {PROGRESS_ENDPOINT}{qs}")
    by_user = accounts_needed(plan)
    print(f"[UX-46] 로그인 횟수 계획: 계정 {len(by_user)}개로 버킷 {len(plan)}/"
          f"{len(EXPECTED_BUCKETS)}개를 덮는다(계정당 한 번만 로그인한다 — 율제한을 안 늘린다)")
    if len(plan) < len(EXPECTED_BUCKETS):
        missing = [b for b in EXPECTED_BUCKETS if b not in plan]
        print(f"[UX-46] ⚠ 계정이 없어 계획에서 빠진 버킷: {missing}")
    print("[UX-46] ? **못 쟀다** — `--dry-run` 은 계획을 찍을 뿐 한 사람도 걷지 않는다 (P-204)")
    return EXIT_UNDECIDABLE


def main() -> int:
    parser = argparse.ArgumentParser(description="UX-46 온보딩 진행률 판정기")
    parser.add_argument("--list", action="store_true", help="카드 표 전수")
    parser.add_argument("--api", default=os.environ.get("GX_API", ""),
                        help="걷기 대상 서버 (없으면 구조만)")
    parser.add_argument("--dry-run", action="store_true",
                        help="로그인 없이 계획만 찍는다(네트워크 0 · P-311)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if args.list:
        table = cards_per_role(ONBOARDING.read_text(encoding="utf-8"))
        for role, rows in sorted(table.items()):
            print(f"{role} — 카드 {len(rows)}장")
            for key, closes in rows:
                print(f"    {'닫힘 판정 있음' if closes else '아직 못 잼   '}  {key}")
        #: ★ [P-204] 표를 찍은 것은 잰 것이 아니다 — 회색(2)이다.
        print("[UX-46] ? **못 쟀다** — `--list` 는 카드 표를 찍을 뿐 한 장도 걷지 않는다 (P-204)")
        return EXIT_UNDECIDABLE

    if args.dry_run:
        return _print_dry_run()

    code = judge_structure()
    if args.api:
        load_local_env()
        src = ONBOARDING.read_text(encoding="utf-8")
        plan = role_walk_plan(src, CONFIRMED_ROLE_ACCOUNTS, reserve=("U5", U5_RESERVE_ACCOUNT))
        if not plan:
            print("[UX-46] ? **못 쟀다** — 로그인 계획이 비었다(실재가 확인된 계정이 없다)")
            return EXIT_FAIL if code == EXIT_FAIL else EXIT_UNDECIDABLE
        results = walk_all_roles(args.api, plan)
        _marks = {EXIT_OK: "OK  ", EXIT_FAIL: "FAIL", EXIT_UNDECIDABLE: "GRAY"}
        for bucket in sorted(results):
            r = results[bucket]
            print(f"[UX-46]   {_marks.get(r['code'], '?   ')} {bucket} ({r['user']}) — "
                  f"{r['why']}")
        walked, walked_why = combine_role_codes(results)
        print(f"[UX-46] 걷기(㉢) 접은 수: {walked_why}")
        # 둘을 한 수로 합치지 않는다 — 나쁜 쪽이 이긴다(회색은 초록을 덮는다).
        if walked == EXIT_FAIL or code == EXIT_FAIL:
            return EXIT_FAIL
        return EXIT_OK if (code == EXIT_OK and walked == EXIT_OK) else EXIT_UNDECIDABLE
    #: ★★ [P-204 · 턴 Y · 차선 Q] **`--api` 없이 낸 0 은 「온보딩이 선다」가 아니다.**
    #:   이 게이트의 두 눈 중 **사람이 실제로 걷는 눈**은 `--api` 에만 있다. 구조만 보고
    #:   0 을 내면 UX-46 절이 **걸어 본 적 없이** 초록으로 적힌다 — 그 초록이 세 턴을 갔다.
    #:   구조가 빨강이면 그건 재서 틀린 것이므로 **1 그대로** 돌려준다(회색으로 덮지 않는다).
    if code != EXIT_OK:
        return code
    print("[UX-46] ? **못 쟀다** — `--api` 를 안 줬다. 구조만 봤고 **한 사람도 걷지 않았다.** "
          "이 0 은 「이 호출이 통과」일 뿐이다 (P-204) — 재려면 `--api …` 또는 `--dry-run` 으로 부른다")
    return EXIT_UNDECIDABLE


if __name__ == "__main__":
    #: [2026-09-19 · 턴 V 병합] **머리글이 없어 이 게이트는 회색으로 세어졌다**(P-107).
    #:   74개 판정기 중 73개가 세 줄을 찍는데 이것만 안 찍었다. 머리글 없는 게이트는
    #:   검증 차선의 셈에서 초록이 아니다 — 무엇을 재고 한 말인지 아무도 모르기 때문이다.
    #:   (경로는 이미 위(`login` import 자리)에서 꽂았다 — 두 번 꽂지 않는다.)
    from _gate_header import gate_header
    try:
        _cards = cards_per_role(ONBOARDING.read_text(encoding="utf-8"))
        _n_card = sum(len(v) for v in _cards.values())
        _n_role = len(_cards)
    except Exception:                                        # noqa: BLE001
        _n_card = _n_role = 0
    gate_header(__file__,
                measured=("① 구조 — 온보딩 카드마다 닫는 판정이 선언됐는가 · "
                          "**분모 %d장**(역할 %d) · ② 걷기 — `--api` 를 준 실행에서만 "
                          "그 카드를 **실제로 걷는다**(안 주면 ②는 분모 0 · 그 실행은 회색이다 · P-204)"
                          % (_n_card, _n_role)),
                target="구조는 저장소 파일 · 걷기는 --api 를 준 실행에서만 살아 있는 서버",
                as_="구조: 자격 없음 · 걷기: 시드 계정 여섯 (자격 이름 GX_SEED_ROLE_PASSWORD)",
                source="온보딩 카드 표 · 라우트 선언 · 화면 소스 (걷기일 때는 HTTP 응답)")
    sys.exit(main())
