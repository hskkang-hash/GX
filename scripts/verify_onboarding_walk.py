#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-46 — **온보딩 카드를 닫는 것이 사람인가 기록인가** (턴 R · 차선 F · 골격).

정본이 요구한 것 (PRD v1.1 §5.1 UX-46 · §7.1 · WO-01 §12)
----------------------------------------------------------
    "역할별 「처음 시작하기」 카드 7개 이하 · 완료 체크는 실제 행위(서버 기록)로 자동 ·
     진행률 % 역할 홈 상단 · 100%면 카드 숨김"
    AC: "각 역할 시드 계정으로 카드 전부 수행 → 진행률 100 · `verify_onboarding_walk` 신설"

그래서 이 판정기는 **두 층**이다 — 그리고 둘을 한 수로 합치지 않는다
--------------------------------------------------------------------
    ㉠ **구조**(서버 없이 지금 잰다) — 카드 표가 실재하고 · 역할마다 일곱 장 이하이고 ·
       **사람이 누르는 완료 문이 없고** · 라우트가 선언(테넌트 범위)과 인증을 달고 있고 ·
       화면이 그 라우트를 **부른다**(잠든 라우트가 아니다)
    ㉡ **걷기**(역할 계정으로 실제 HTTP) — 시드 계정 여섯으로 진행률을 받아 100 을 본다

㉡ 은 **서버와 자격증명이 있을 때만** 잰다. 없으면 **회색(exit 2)** 이다 —
「못 쟀다」는 「통과」가 아니다(D-301 · D-400). 게이트가 환경을 요구해 초록으로 죽는
길을 만들지 않으려고, 기본 판정은 ㉠만 하고 ㉡은 `--api` 를 준 실행에서만 돈다.

    python scripts/verify_onboarding_walk.py                 # ㉠ 구조 판정
    python scripts/verify_onboarding_walk.py --list          # 카드 표 전수
    python scripts/verify_onboarding_walk.py --api URL --user U --password P   # ㉠+㉡
    python scripts/verify_onboarding_walk.py --self-test     # 양성·음성 대조 (D-277)

종료 코드 (저장소 규약 · D-400): 0 = 쟀고 통과 · 1 = 쟀고 실패 · 2 = **못 쟀다(회색)**

★ 이 파일은 **골격이다.** ㉡ 의 걷기는 자리와 판정식만 서 있고, 역할 계정 여섯의
  자격은 이 저장소에 없다(`.env.gates` 규약). 조율자가 계정을 주는 턴에 `walk()` 의
  `TODO` 두 줄(로그인 · 카드별 행위 재현)이 채워진다 — 그때까지 ㉡ 은 **회색**이고,
  회색을 초록으로 적지 않는 것이 이 파일의 절반이다.
"""
from __future__ import annotations

import argparse
import ast
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
# ㉡ 걷기 — **서버와 역할 계정이 있을 때만.** 없으면 회색이다
# ══════════════════════════════════════════════════════════════════════════
def walk(api: str, user: str, password: str) -> int:
    """역할 계정으로 진행률을 받아 100 을 본다. **골격이다.**

    지금 서 있는 것: 자리와 판정식(진행률 100 · 분모 0이면 회색 · 못 재는 카드 목록).
    아직 없는 것: 역할 계정 여섯의 자격(`.env.gates` 규약 — 저장소에 값이 없다)과
    카드별 행위 재현(판정 1 · 인계 1 · 보고서 1 …)을 이 판정기가 대신 누르는 부분.

    ★ 그 둘이 없으면 **회색을 낸다.** 「로그인은 됐고 진행률은 0이었다」를 초록으로
      적으면, 그 초록은 제품이 아니라 이 판정기의 게으름을 증명한다.
    """
    import json
    import urllib.error
    import urllib.request

    if not (api and user and password):
        print("[UX-46] GRAY 걷기에 필요한 셋(--api · --user · --password)이 없다 — 판정 불가")
        return EXIT_UNDECIDABLE

    # TODO(조율자 계정 배포 뒤): ① `/api/v1/auth/login`(end_previous_session=true)로 토큰
    #   ② 카드별 행위를 실제로 눌러 서버 기록을 만든다. 지금은 **읽기 한 번**만 한다.
    try:
        req = urllib.request.Request(
            f"{api.rstrip('/')}/api/dsm{ROUTE_PATH}",
            headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8") or "{}")
            code = resp.status
    except urllib.error.HTTPError as exc:
        code, body = exc.code, {}
    except Exception as exc:  # noqa: BLE001
        print(f"[UX-46] GRAY 서버에 닿지 못했다({type(exc).__name__}) — 판정 불가")
        return EXIT_UNDECIDABLE

    if code == 401:
        print("[UX-46] GRAY 익명으로는 진행률을 못 읽는다(401 · 정상) — "
              "역할 계정 로그인이 아직 이 판정기에 없다. 걷기는 **회색**이다")
        return EXIT_UNDECIDABLE

    percent = body.get("percent")
    if percent is None:
        print(f"[UX-46] GRAY 진행률이 없다(카드 0장 · 역할 모름) — 응답 {code}")
        return EXIT_UNDECIDABLE
    if percent < 100:
        print(f"[UX-46] 진행률 {percent} — 100 이 아니다 "
              f"({body.get('done')}/{body.get('total')})")
        return EXIT_FAIL
    print(f"[UX-46] 진행률 100 ({body.get('done')}/{body.get('total')})")
    return EXIT_OK


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
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'OK ' if ok else 'FAIL'} {name}")
    print(f"[UX-46] 자기시험 {len(checks)}건 중 {len(bad)}건 실패")
    return EXIT_OK if not bad else EXIT_FAIL


def main() -> int:
    parser = argparse.ArgumentParser(description="UX-46 온보딩 진행률 판정기 (골격)")
    parser.add_argument("--list", action="store_true", help="카드 표 전수")
    parser.add_argument("--api", default="", help="걷기 대상 서버 (없으면 구조만)")
    parser.add_argument("--user", default="")
    parser.add_argument("--password", default="")
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

    code = judge_structure()
    if args.api:
        walked = walk(args.api, args.user, args.password)
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
          "이 0 은 「이 호출이 통과」일 뿐이다 (P-204) — 재려면 `--api …` 로 부른다")
    return EXIT_UNDECIDABLE


if __name__ == "__main__":
    #: [2026-09-19 · 턴 V 병합] **머리글이 없어 이 게이트는 회색으로 세어졌다**(P-107).
    #:   74개 판정기 중 73개가 세 줄을 찍는데 이것만 안 찍었다. 머리글 없는 게이트는
    #:   검증 차선의 셈에서 초록이 아니다 — 무엇을 재고 한 말인지 아무도 모르기 때문이다.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
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
