#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""계약 라우트 **도달** 판정 — 세 번째 눈 (D-410 · 지시서 2026-09-19 판정 3).

    "POST /api/dsm/settings/{api-keys,thresholds,zones,grade-rules} 넷이
     전부 **405 (Allow: GET)** 였다. 로직은 있었고 시험도 있었다.
     틀린 것은 「구현되었다」가 아니라 **「외부 App 이 쓸 수 있다」**는 함의였다."

왜 세 번째 눈인가 — **두 눈의 사각이 정확히 겹쳤다**
----------------------------------------------------
    · 단위 시험(`verify_contract_ac`)  → **서비스 함수**를 부른다.  배선을 안 본다
    · `verify_route_alive`             → **화면이 부른 GET** 만 때린다. 쓰기 면을 안 본다

두 도구 다 제 할 일을 했다. 아무도 안 보는 자리가 **그 사이**에 있었을 뿐이다.
그 자리를 이 판정기가 본다: **선언된 계약 진입면의 (method, path) 마다 실제 HTTP 로
한 번씩 문을 두드린다.** U6(외부 App)은 HTTP 로만 들어온다 — 함수는 문이 아니다(착시 ⑨).

무엇을 때리나 — **우리가 손으로 적지 않는다**
--------------------------------------------
`backend/tests/test_f05_event_api.py` 의 **`EVENT_ENTRY_SURFACE`** 를 읽는다. 그것이
「재난안전 App 의 HTTP 표면 전부」로 이미 선언된 등재부이고, 새 라우트가 생기면 그
등재부에 손으로 줄을 더해야만 시험이 통과한다. 목록을 여기 또 적으면 **두 벌이 되고,
두 벌은 반드시 어긋난다**(D-369).

    python scripts/verify_contract_route_reach.py
    python scripts/verify_contract_route_reach.py --self-test

판정 규칙 — **405 는 언제나 실패다**
------------------------------------
    2xx                    도달 (문이 열렸다)
    400 · 409 · 422 · 501  도달 — **검증이 돌았다는 뜻이다.** 문 안쪽에서 난 소리다
    401 · 403              도달 — 문지기가 섰다. ⚠ 도달이지 **기능의 증거가 아니다**(착시 ⑪)
    405                    **실패** — 문은 있는데 그 메서드를 안 받는다. 이 판정기의 출생 사유
    404 (매개변수 없는 경로) **실패** — 선언된 라우트가 없다
    404 (매개변수 있는 경로) **한 번 더 묻는다** — 아래 「404 를 가르는 자」
    5xx                    실패
    닿지 못함              **판정 불가** (exit 2)

404 를 가르는 자 — **「없는 문」과 「없는 행」은 같은 404 다**
------------------------------------------------------------
그 둘을 상태 코드로는 못 가른다. 그래서 **아무도 안 받는 메서드**(`PROPFIND`)로 한 번
더 두드린다 [실측 2026-09-19]: 라우트가 있으면 django-ninja 가 **405**, 없으면 Django 가
**404** 다. 씨앗도 필요 없고 **아무것도 쓰지 않는다** — 그 메서드를 받는 핸들러가 없으니까.

씨앗은 **제품이 준다** — 목록 응답(`GET /events`)에서 `event_id` 를 거둬 읽기 경로에
쓴다. DB 에 심지 않는다. ⚠ **쓰기 경로에는 실재 id 를 쓰지 않는다**: 진짜 id 로
`POST /events/{id}/notify` 를 두드리면 판정기가 진짜로 발송하고, F-04 5분 중복 억제가
걸려 **그 다음 진짜 경보가 조용해진다.**

종료 코드: 0 전부 도달 · 1 못 닿는 라우트가 있다 · 2 판정 불가(서버·자격증명·못 잼)
★ 2 는 실패가 아니고 **통과는 더더욱 아니다.** 두드려 보지 못한 문을 초록으로 적지 않는다(D-301).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

#: ★ **한 벌의 코드가 두 곳에서 같은 판정을 한다** (D-369). 로그인·컨테이너 위임·
#:   자격증명 읽기는 `verify_route_alive` 가 이미 피 흘리며 고친 자리다 — 2026-09-17 의
#:   거짓 초록(`token/pair` 를 먼저 물어 26 중 24가 401)이 그 안에 박혀 있다.
#:   복사하면 그 교훈이 한쪽에만 남는다.
from verify_route_alive import (          # noqa: E402
    LOCAL_ENV_FILES,
    delegate_to_container,
    hit,
    load_local_env,
    login,
)

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

SURFACE_FILE = ROOT / "backend" / "tests" / "test_f05_event_api.py"
SURFACE_NAME = "EVENT_ENTRY_SURFACE"

#: ★ **출생 표본** (D-310) — 합성이 아니다. [실측 2026-09-18] 이 넷이 그날 전부 405 였고,
#:   `verify_contract_ac` 는 초록이었으며 `verify_route_alive` 는 이 넷을 **때리지도 않았다**.
#:   자기시험이 이 네 줄을 「도달」로 읽으면 이 도구는 도구가 아니다.
BIRTH_SAMPLE = (
    ("POST", "/api/dsm/settings/api-keys", 405),
    ("POST", "/api/dsm/settings/thresholds", 405),
    ("POST", "/api/dsm/settings/zones", 405),
    ("POST", "/api/dsm/settings/grade-rules", 405),
)

#: 매개변수 자리. **있을 법하지 않은 값**을 넣는다 — 진짜 행을 건드리지 않기 위해서다.
#:   쓰기 라우트를 두드리면서 남의 데이터를 바꾸면 판정기가 사고가 된다(D-209 의 정신).
ABSENT_ID = "987654321"
#: 문자열 매개변수. `{domain}` 에 실재 이름을 넣으면 리터럴 경로와 겹쳐 **다른 문**을
#:   두드리게 된다 — 그러면 `{domain}` 자신은 한 번도 안 재고 초록이 난다.
ABSENT_WORD = "reach-probe"

_PARAM = re.compile(r"\{([a-z]+:)?([A-Za-z_][A-Za-z0-9_]*)\}")


def has_param(path: str) -> bool:
    return bool(_PARAM.search(path))


def param_names(path: str) -> list[str]:
    return [m.group(2) for m in _PARAM.finditer(path)]


def concretize(path: str, seeds: "dict[str, object] | None" = None) -> str:
    """`/events/{int:event_id}` → `/events/4712`(씨앗이 있으면) 또는 `/events/987654321`.

    ★ **씨앗은 제품이 준다.** 목록 라우트(`GET /events`)의 응답에서 `event_id` 를
      거둬 쓴다 — 우리가 DB 에 무엇을 심지 않는다(심으면 판정기가 쓰기 면이 된다).
      씨앗이 없으면 없는 값으로 두드리고, 그 404 는 **못 잼**으로 적는다.
    """
    def sub(m: "re.Match[str]") -> str:
        name = m.group(2)
        if seeds and name in seeds:
            return str(seeds[name])
        conv = (m.group(1) or "").rstrip(":")
        return ABSENT_ID if conv == "int" else ABSENT_WORD
    return _PARAM.sub(sub, path)


def harvest_seeds(body: bytes, wanted: "set[str]") -> "dict[str, int]":
    """200 응답 본문에서 **원하는 이름의 첫 정수값**을 줍는다.

    이름으로 줍는 이유: 목록 응답의 모양(`{"events": [...]}` · `{"data": [...]}` ·
    `{"templates": [...]}`)이 라우트마다 다르다. 모양을 적어 두면 그 목록이 곧
    옛말이 된다 — 대신 **매개변수 이름과 같은 키**를 재귀로 찾는다.
    `{int:event_id}` 를 채울 값은 응답 어딘가의 `event_id` 다.
    """
    found: dict[str, int] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in wanted and k not in found and isinstance(v, int) \
                        and not isinstance(v, bool) and v > 0:
                    found[k] = v
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    try:
        walk(json.loads(body.decode("utf-8", "replace")))
    except (ValueError, AttributeError):
        pass
    return found


#: ★ **404 를 가르는 자** — 「없는 문」과 「없는 행」은 HTTP 상태로는 똑같이 404 다.
#:   그런데 **모르는 메서드로 한 번 더 두드리면 갈린다** [실측 2026-09-19]:
#:       라우트가 있다  → django-ninja `PathView` 가 **405** 를 낸다
#:       라우트가 없다  → Django 가 **404** 를 낸다
#:   씨앗도 필요 없고 아무것도 쓰지 않는다 — 이 메서드를 받는 핸들러는 없기 때문이다.
#:   그래서 「씨앗이 없어 못 잰다」던 자리들이 잴 수 있는 자리가 됐다.
NONSENSE_METHOD = "PROPFIND"


def route_exists(api: str, path: str) -> "bool | None":
    """그 경로에 **문이 달려 있는가.** 아무도 안 받는 메서드로 두드려 본다.

    405 → 있다 · 404 → 없다 · 그 밖 → 모른다(None). 쓰기가 일어나지 않는다.
    """
    st = hit(api, NONSENSE_METHOD, path, None)
    if st == 405:
        return True
    if st == 404:
        return False
    return None


def judge(status: int, parameterized: bool) -> tuple[str, str]:
    """(판정, 사유). 판정은 `reach` / `fail` / `unmeasured` 셋 중 하나.

    **규칙을 함수로 떼어 둔 이유는 시험하기 위해서다** — 그리고 이 규칙의 핵심은
    한 줄이다: **405 는 언제나 실패다.** 405 는 「문은 있는데 이 메서드는 안 받는다」
    이고, 계약이 선언한 메서드를 안 받는 문은 계약에게 **없는 문**이다.
    """
    if 200 <= status < 300:
        return "reach", "산다"
    if status == 405:
        return "fail", "**405 — 문은 있는데 그 메서드를 안 받는다** (배선이 삼켰다 · 착시 ⑨)"
    if status == 404:
        if parameterized:
            # 「없는 문」과 「없는 행」을 HTTP 로 가를 수 없다. 모르는 것을 색칠하지 않는다.
            return "unmeasured", "404 — 씨앗이 없다. **못 잼**(없는 문인지 없는 행인지 못 가른다)"
        return "fail", "404 — 선언된 라우트가 없다"
    if status in (401, 403):
        # ⚠ 착시 ⑪. 도달은 맞다. **기능의 증거는 아니다** — 그래서 따로 센다.
        return "reach", "문지기가 섰다(도달 — 기능의 증거는 아니다 · ⑪)"
    if status in (400, 409, 415, 422, 501):
        return "reach", "검증이 돌았다(문 안쪽에서 난 소리 — 도달)"
    if status >= 500:
        return "fail", "**서버 오류** — 문 뒤가 죽었다"
    if status == 0:
        return "unmeasured", "응답을 못 받았다 — **못 잼**"
    return "fail", "뜻을 모르는 응답 " + str(status)


def load_surface(path: Path) -> list[tuple[str, str]]:
    """`EVENT_ENTRY_SURFACE` 를 **AST 로** 읽는다.

    import 하지 않는 이유: 그 파일은 Django 시험 모듈이고, 판정기가 Django 를
    요구하면 **환경에 따라 사라진다.** 사라진 게이트는 사라진 것이 보이지 않는다.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            continue
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if SURFACE_NAME not in names or node.value is None:
            continue
        call = node.value
        if isinstance(call, ast.Call):          # frozenset({...})
            call = call.args[0] if call.args else None
        if not isinstance(call, ast.Set):
            continue
        out: list[tuple[str, str]] = []
        for el in call.elts:
            if isinstance(el, ast.Tuple) and len(el.elts) == 2:
                m, p = el.elts
                if isinstance(m, ast.Constant) and isinstance(p, ast.Constant):
                    out.append((m.value, p.value))
        return sorted(set(out))
    raise LookupError(SURFACE_NAME + " 을 " + str(path) + " 에서 찾지 못했다")


def self_test() -> int:
    """판정 규칙과 **출생 표본**을 함께 본다 (D-277 · D-310)."""
    bad: list[str] = []

    for status, param, expect in (
        (200, False, "reach"), (204, False, "reach"),
        (400, False, "reach"), (403, False, "reach"), (422, False, "reach"),
        (501, False, "reach"), (409, False, "reach"),
        (405, False, "fail"), (405, True, "fail"),
        (404, False, "fail"), (404, True, "unmeasured"),
        (500, False, "fail"), (502, True, "fail"), (0, False, "unmeasured"),
    ):
        got, _ = judge(status, param)
        if got != expect:
            bad.append("judge(%s, param=%s) = %s (기대 %s)" % (status, param, got, expect))

    # ★ 출생 표본 — 2026-09-18 의 그 네 줄을 **그대로** 판정한다
    for m, p, st in BIRTH_SAMPLE:
        verdict, _ = judge(st, has_param(p))
        if verdict != "fail":
            bad.append("출생 표본 %s %s %s 를 「%s」로 읽는다 — 이 도구가 태어난 "
                       "바로 그 사례를 놓친다 (D-310)" % (m, p, st, verdict))

    # 매개변수 치환 — **실재 이름을 넣으면 다른 문을 두드린다**
    if concretize("/api/dsm/events/{int:event_id}") != "/api/dsm/events/" + ABSENT_ID:
        bad.append("int 매개변수 치환이 틀렸다")
    if concretize("/api/dsm/settings/{domain}") != "/api/dsm/settings/" + ABSENT_WORD:
        bad.append("문자열 매개변수 치환이 틀렸다")
    if ABSENT_WORD in ("thresholds", "zones", "recipients", "widgets",
                       "api_keys", "grade_rules"):
        bad.append("%s 가 실재 설정 영역이다 — {domain} 대신 리터럴 문을 두드리게 되고, "
                   "{domain} 자신은 한 번도 안 재고 초록이 난다" % ABSENT_WORD)
    if concretize("/api/dsm/reports/{int:template_id}.pdf") != \
            "/api/dsm/reports/" + ABSENT_ID + ".pdf":
        bad.append("접미사가 붙은 매개변수 치환이 틀렸다")

    # ── 씨앗 수확 — 모양이 아니라 **이름**으로 줍는가 ─────────────────────
    body = b'{"total": 2, "events": [{"event_id": 4712, "severity": "fire"}]}'
    got = harvest_seeds(body, {"event_id", "template_id"})
    if got.get("event_id") != 4712:
        bad.append("목록 응답에서 event_id 를 못 줍는다 (%r) — 씨앗 없이 때리면 "
                   "404 가 「없는 문」인지 「없는 행」인지 못 가른다" % got)
    if harvest_seeds(b'{"ok": true, "count": 3}', {"event_id"}):
        bad.append("원하지 않은 이름을 씨앗으로 줍는다 — 아무 숫자나 id 로 쓴다")
    if harvest_seeds(b'{"event_id": true}', {"event_id"}):
        bad.append("bool 을 정수 id 로 줍는다")
    if harvest_seeds(b"not json at all", {"event_id"}):
        bad.append("JSON 이 아닌 본문에서 씨앗을 지어낸다")
    if concretize("/api/dsm/events/{int:event_id}", {"event_id": 4712}) != \
            "/api/dsm/events/4712":
        bad.append("씨앗이 있는데 없는 id 로 때린다")

    # ── 404 를 가르는 자 — **모르는 메서드는 아무도 받지 않는다** ──────────
    if NONSENSE_METHOD in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        bad.append("404 판별에 쓰는 메서드가 제품이 받는 메서드다 — "
                   "판별하려다 **진짜로 부른다**")

    # 등재부를 실제로 읽는가 — **읽지 못하면 무엇을 재는지 모르는 채로 도는 것이다**
    surface: list[tuple[str, str]] = []
    try:
        surface = load_surface(SURFACE_FILE)
    except Exception as exc:                              # noqa: BLE001
        bad.append("%s 을 못 읽는다: %s %s" % (SURFACE_NAME, type(exc).__name__, exc))
    for m, p, _st in BIRTH_SAMPLE:
        if (m, p) not in surface:
            bad.append("자기표본 %s %s 이 %s 에 없다 — 405 였던 바로 그 자리다. "
                       "등재부에서 빠지면 이 눈이 감긴다 (D-310)" % (m, p, SURFACE_NAME))

    if bad:
        print("[REACH] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[REACH] 자기시험 통과 — 판정 규칙 14종 + 출생 표본 405 넷 + 치환 4 "
          "+ 씨앗 수확 5 + 404 판별자 1 + 등재부 %d건 실독" % len(surface))
    return EXIT_OK


def main() -> int:
    _env_files = load_local_env()
    ap = argparse.ArgumentParser(
        description="계약 진입면의 (method, path) 마다 실제 HTTP 로 도달을 잰다 (D-410)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER"))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD"))
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    container = os.environ.get("GX_ROUTE_CONTAINER", "").strip()
    if container and not os.environ.get("GX_ROUTE_IN_CONTAINER"):
        os.environ.setdefault("GX_API", "http://localhost:8000")
        if args.user:
            os.environ["GX_ROUTE_USER"] = args.user
        if args.password:
            os.environ["GX_ROUTE_PASSWORD"] = args.password
        return delegate_to_container(container, args.json,
                                     script="verify_contract_route_reach.py")

    surface = load_surface(SURFACE_FILE)
    n_param = sum(1 for _m, p in surface if has_param(p))
    print("[REACH] [입력] %d건 — 선언된 계약 진입면 (%s · 매개변수 있는 경로 %d건은 "
          "제품이 준 씨앗으로, 쓰기 경로는 없는 id 로 두드린다)"
          % (len(surface), SURFACE_NAME, n_param))
    if not surface:
        print("[REACH] 등재부가 비었다 — **판정 불가** (잴 것이 없는 것과 못 읽은 것은 다르다)")
        return EXIT_UNDECIDABLE

    if _env_files:
        print("[REACH] 로컬 자격증명 파일 읽음: %s (저장소엔 이름만 · D-204)"
              % ", ".join(_env_files))
    if not (args.user and args.password):
        print("[REACH] 자격증명이 없다 (--user/--password 또는 %s)"
              % " / ".join(LOCAL_ENV_FILES))
        print("[REACH] **판정 불가** — 익명으로 두드려 401 만 보고 통과로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE
    token = login(args.api, args.user, args.password)
    if not token:
        print("[REACH] 토큰을 못 받았다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    # ★ **순서가 판정의 일부다.** 매개변수 없는 라우트를 먼저 두드려 그 응답에서
    #   씨앗을 거두고, 그 씨앗으로 매개변수 경로를 때린다. 거꾸로 하면 없는 id 로
    #   두드려 404 를 받고, 그 404 는 「없는 문」인지 「없는 행」인지 못 가른다 —
    #   그러면 잴 수 있었던 자리가 영영 회색으로 남는다.
    plain = [(m, p) for m, p in surface if not has_param(p)]
    parameterized = [(m, p) for m, p in surface if has_param(p)]
    wanted: set[str] = set()
    for _m, p in parameterized:
        wanted.update(param_names(p))

    rows: list[dict] = []
    failed: list[tuple[str, str, int]] = []
    unmeasured: list[tuple[str, str, int]] = []
    gated = 0
    seeds: dict[str, object] = {}
    tok_status: dict[tuple[str, str], int] = {}

    #: ★ 씨앗을 **읽기에만** 쓴다. 실재하는 id 로 `POST /events/{id}/notify` 를
    #:   두드리면 판정기가 **진짜로 발송한다** — 행이 남고 F-04 5분 중복 억제가
    #:   걸려 그 다음 진짜 경보가 조용해진다. 판정기가 제품 상태를 바꾸면 그것은
    #:   판정기가 아니라 사고다(D-209 의 정신). 쓰기 경로는 없는 id 로 두드리고,
    #:   그 404 는 위 `route_exists` 가 가른다.
    READ_ONLY = {"GET", "HEAD", "OPTIONS"}

    def knock(method: str, path: str, collect: bool) -> None:
        nonlocal gated
        target = concretize(path, seeds if method in READ_ONLY else None)
        if collect:
            status, body = hit(args.api, method, target, token, with_body=True)
            if 200 <= status < 300:
                for k, v in harvest_seeds(body, wanted).items():
                    seeds.setdefault(k, v)
        else:
            status = hit(args.api, method, target, token)
        tok_status[(method, target)] = status
        verdict, why = judge(status, has_param(path))
        # ★ 회색을 색으로 바꾸는 자리 — 404 는 두 번 묻고 나서야 판정한다.
        if verdict == "unmeasured" and status == 404:
            exists = route_exists(args.api, target)
            if exists is True:
                verdict, why = "reach", ("404 — 문은 있고 **그 행이 없을 뿐**이다 "
                                         "(%s 로 두드리니 405 · 도달)" % NONSENSE_METHOD)
            elif exists is False:
                verdict, why = "fail", ("404 — **문이 없다** (%s 로 두드려도 404 · "
                                        "선언된 라우트가 배선에 없다)" % NONSENSE_METHOD)
        if status in (401, 403):
            gated += 1
        mark = {"reach": "  ", "fail": "X ", "unmeasured": "? "}[verdict]
        seeded = "" if not has_param(path) else (
            "  [씨앗]" if any(n in seeds for n in param_names(path))
            and method in READ_ONLY else "  [씨앗 없음]")
        print("[REACH] %s%3d %-6s %-52s %s%s" % (mark, status, method, path, why, seeded))
        rows.append({"method": method, "path": path, "probe": target,
                     "status": status, "verdict": verdict})
        if verdict == "fail":
            failed.append((method, path, status))
        elif verdict == "unmeasured":
            unmeasured.append((method, path, status))

    for method, path in plain:
        knock(method, path, collect=(method == "GET"))
    if seeds:
        print("[REACH] [씨앗] 제품이 준 목록에서 거뒀다: %s (DB 에 심지 않았다)"
              % ", ".join("%s=%s" % kv for kv in sorted(seeds.items())))
    else:
        print("[REACH] [씨앗] 목록이 비어 거둘 것이 없었다 — 매개변수 경로는 **못 잼**이 된다")
    for method, path in parameterized:
        knock(method, path, collect=False)

    # ── 증거로 (착시 ⑪ · 2026-09-17 의 뿌리) ───────────────────────────────
    #   「로그인 성공」은 진술이다. **토큰이 무엇을 바꿨는지**가 증거다.
    #   한 건도 안 바뀌면 우리는 한 번도 들어가지 못한 것이고, 그 상태에서 401·403 을
    #   「도달」로 읽으면 그것이 바로 2026-09-17 의 거짓 초록이다.
    changed = 0
    for (method, target), st in tok_status.items():
        if hit(args.api, method, target, None) != st:
            changed += 1
    print("[REACH] [대조] 익명으로 한 번 더 두드렸다 — 토큰이 바꾼 라우트 %d건 "
          "/ 문지기가 선 라우트 %d건" % (changed, gated))
    if changed == 0:
        print("[REACH] 토큰이 **아무 문도 바꾸지 못했다** — 들어가지 못한 채로 "
              "401/403 을 「도달」로 읽을 뻔했다 (착시 ⑪ · 2026-09-17)")
        print("[REACH] **판정 불가**")
        return EXIT_UNDECIDABLE

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"surface": SURFACE_NAME, "counted": len(surface), "rows": rows,
             "failed": len(failed), "unmeasured": len(unmeasured),
             "token_changed": changed, "gated": gated},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("[REACH] 기록: %s" % out)

    print("\n[REACH] 잰 라우트 %d · 도달 %d · 못 닿음 %d · 못 잼 %d"
          % (len(surface), len(surface) - len(failed) - len(unmeasured),
             len(failed), len(unmeasured)))
    if failed:
        for m, p, st in failed:
            print("[REACH] X %s %s -> %d" % (m, p, st))
        print("[REACH] **계약이 선언한 문 중 열리지 않는 것이 있다** — "
              "함수가 있어도 U6 은 못 쓴다 (착시 ⑨)")
        return EXIT_FAIL
    if unmeasured:
        for m, p, st in unmeasured:
            print("[REACH] ? %s %s -> %d" % (m, p, st))
        print("[REACH] **판정 불가** — 씨앗이 없어 못 잰 자리가 있다 (P-12 · D-301)")
        return EXIT_UNDECIDABLE
    print("[REACH] 계약 진입면 전부 도달")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
