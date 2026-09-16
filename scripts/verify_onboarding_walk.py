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
    print(f"[입력] 역할 {len(table)} · 카드 {total}장 "
          f"(서버 기록이 닫는 카드 {closable} · 아직 못 재는 카드 {total - closable}) "
          f"· 표={ONBOARDING.relative_to(ROOT)}")

    bad: list[str] = []

    for role, rows in sorted(table.items()):
        if len(rows) > MAX_CARDS_PER_ROLE:
            bad.append(f"{role} 카드 {len(rows)}장 — 상한 {MAX_CARDS_PER_ROLE}장(PRD §7.2)")
        if not any(c for _, c in rows):
            bad.append(f"{role} 에 서버 기록이 닫는 카드가 **한 장도 없다** — "
                       f"그 역할의 진행률은 영원히 0이고, 0은 아무것도 증명하지 않는다")

    if has_write_door(router_src):
        bad.append("온보딩 라우터에 쓰기 문이 있다 — 카드를 사람이 닫으면 진행률은 "
                   "「했다」가 아니라 「했다고 적었다」를 센다(WO-01 §12)")

    missing = route_is_declared(router_src)
    if missing:
        bad.append(f"라우트 표면에 {' · '.join(missing)} 가 없다 — "
                   f"선언 없이 태어난 라우트다(ISO-03)")

    if URLS.is_file() and "DsmFAPI" not in code_only(URLS.read_text(encoding="utf-8")):
        bad.append("라우터가 `urls.py` 에 등록되지 않았다 — 파일은 있고 경로는 없다")

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
        return EXIT_OK

    code = judge_structure()
    if args.api:
        walked = walk(args.api, args.user, args.password)
        # 둘을 한 수로 합치지 않는다 — 나쁜 쪽이 이긴다(회색은 초록을 덮는다).
        if walked == EXIT_FAIL or code == EXIT_FAIL:
            return EXIT_FAIL
        return EXIT_OK if (code == EXIT_OK and walked == EXIT_OK) else EXIT_UNDECIDABLE
    return code


if __name__ == "__main__":
    sys.exit(main())
