# -*- coding: utf-8 -*-
"""앞단 관문 — **두 번째 방어선을 코드가 아닌 자리에 세운다** (OPS-13 · D-361).

원칙 하나
---------
    **단일 방어선은 방어선이 아니다.**
    미들웨어는 코드이고, 코드는 리팩터링 중에 순서가 바뀐다 — 앞단은 그때 남는다.

`common/access_gate.py` 는 §0.4 경로를 우리 층에서 막는다(D-348). 그 관문이 도는
자리는 `settings.MIDDLEWARE` 의 **순서**이고, 순서는 사람이 파일을 고치다가 바뀐다.
`GateIsOutsideTheCacheTest` 가 그 순서를 못박고 있지만, 못박는 것과 **막는 것**은
다르다 — 시험은 빨개질 뿐이고 그 사이에도 요청은 지나간다.

그래서 같은 규칙을 **앞단(nginx)** 에 한 벌 더 건다. 미들웨어가 목록에서 빠져도,
캐시 안쪽으로 들어가도, 앞단은 그대로 401 을 낸다.

★ 왜 nginx 설정을 **손으로 적지 않고 여기서 만드나** (D-369 · D-286)
---------------------------------------------------------------------
경로 목록을 두 벌 적으면 반드시 어긋난다. 어긋난 뒤에는 「어느 쪽이 정본인가」를
아무도 모르고, 대개 **앞단 쪽이 낡는다** — 새 경로를 막을 때 사람은 파이썬만 고친다.
그래서 앞단 설정은 `AUTHN_REQUIRED_PATHS` · `INBOUND_KEY_ALLOWED` 에서 **만들어 낸다.**

  ⚠ 그러면 「같은 뿌리를 쓰니 방어선이 하나 아닌가」— 아니다. 갈라지는 것은
    **사고의 모양**이다. 이 저장소가 실제로 겪은 사고는 ① 미들웨어가 캐시 안쪽으로
    들어간 것(2026-09-07)과 ② §0.4 라 라우트를 못 고친 것(2026-09-08)이다. 둘 다
    **목록은 멀쩡한데 집행이 사라진** 모양이고, 앞단은 그 둘 모두에서 살아남는다.
    반대로 `AUTHN_REQUIRED_PATHS` 에서 한 줄을 지우는 것은 사고가 아니라 **선언**이고,
    선언이 두 방어선을 함께 움직이는 것은 옳다.

무엇을 내는가 — 위치 블록뿐이다
-------------------------------
`server { }` 안에 그대로 끼워 넣을 수 있는 `location` 들을 낸다. `map` 을 쓰지 않는
이유는 `map` 이 `http` 수준에만 놓을 수 있어 **끼워 넣는 자리가 둘로 갈리기** 때문이다.

    python scripts/ops_front_line.py --render --out nginx/generated/gx-gate.conf
    python scripts/ops_front_line.py --check  nginx/generated/gx-gate.conf   # 드리프트

거절 본문은 **512바이트 미만**이다 — 미들웨어의 401 과 같은 규약(D-349 · 반출 0).
"""
from __future__ import annotations

import re

from common.access_gate import (
    AUTHN_REQUIRED_PATHS,
    AUTHN_REQUIRED_PREFIXES,
    INBOUND_KEY_ALLOWED,
    _normalize,
)

#: 생성물임을 첫 줄에 밝힌다. 사람이 손으로 고치면 `--check` 가 잡는다.
HEADER = (
    "# ═══════════════════════════════════════════════════════════════════════\n"
    "# GuardianX 앞단 관문 — **생성물이다. 손으로 고치지 마라.**\n"
    "#   만드는 곳: backend/common/front_line.py (정본은 common/access_gate.py 의 목록)\n"
    "#   다시 만들기: python scripts/ops_front_line.py --render\n"
    "#   드리프트 검사: python scripts/ops_front_line.py --check <이 파일>\n"
    "# 왜 있나: 단일 방어선은 방어선이 아니다 (OPS-13 · D-361). 미들웨어가\n"
    "#   목록에서 빠지거나 캐시 안쪽으로 들어가도 이 줄들은 남아 401 을 낸다.\n"
    "# ═══════════════════════════════════════════════════════════════════════\n"
)

#: 프록시 지시어 한 벌. 위치마다 베끼지 않는다 (D-369).
PROXY_INCLUDE = "include /etc/nginx/gx/gx-proxy.inc;"

#: 거절 본문. **상태는 HTTP 로 말한다** — 200 봉투에 담지 않는다 (D-349).
DENY_ANON = ('return 401 \'{"detail":"Unauthorized",'
             '"reason":"authentication required (front line)"}\';')
DENY_KEY = ('return 401 \'{"detail":"Unauthorized",'
            '"reason":"inbound key is not allowed on this route (front line)"}\';')

#: 자격증명을 **들고 왔는가** — 미들웨어 `_has_credentials` 와 같은 질문이다.
#: 유효한지는 보지 않는다(그건 인증의 일이다). 셋 중 하나라도 있으면 통과시킨다:
#: `Authorization` 헤더 · 들어오는 키 · 세션 쿠키. 쿠키를 빼면 앞단이 미들웨어보다
#: **더 엄해져** 정상 로그인 사용자가 막힌다 — 앞단이 사고를 내는 흔한 모양이다.
#: ⚠ nginx 의 `if` 는 **왼쪽에 변수 하나만** 받는다 — `if ("$a$b" = "")` 는
#:   `invalid condition` 으로 기동을 거부한다 [실측 2026-09-05 · `nginx -t`]. 그래서
#:   `set` 으로 한 변수에 접고 그 변수를 본다. ★ 앞단은 **기동을 거부하는 방식으로**
#:   틀림을 알렸다 — 조용히 통과시키지 않았다. 그것이 앞단을 방어선으로 쓸 수 있는 이유다.
CREDENTIAL_PROBE = "$gx_cred"
CREDENTIAL_FOLD = 'set $gx_cred "$http_authorization$http_x_api_key$cookie_sessionid";'


def _variants(path: str) -> tuple[str, str]:
    """`/p` 와 `/p/` 둘 다 낸다. 미들웨어가 `rstrip("/")` 로 같게 보는 것을
    앞단에서 한쪽만 막으면 **막은 것이 아니다**(`test_trailing_slash_does_not_open_a_hole`)."""
    bare = _normalize(path)
    return bare, bare + "/"


def gated_paths() -> tuple[str, ...]:
    """앞단이 익명에게 401 을 내야 하는 자리 전부(슬래시 변형 포함)."""
    out: list[str] = []
    for path in AUTHN_REQUIRED_PATHS:
        out.extend(_variants(path))
    return tuple(sorted(set(out)))


def gated_prefixes() -> tuple[str, ...]:
    """★ [P-83 · 2026-09-06] 앞단이 **접두로** 401 을 내야 하는 자리.

    경로 틀(inbound 키: `/api/apikey/keys/{user_id}`)은 이름으로 못 막는다 — 미들웨어가 접두로
    막았으니 앞단도 접두로 막아야 두 방어선이 **같은 자리**를 덮는다. 한쪽만 접두면
    「미들웨어를 빼도 앞단이 남는다」가 그 자리에서 거짓이 된다.
    """
    return tuple(sorted({p if p.endswith("/") else p + "/"
                         for p in AUTHN_REQUIRED_PREFIXES}))


def key_allowed() -> tuple[tuple[str, str], ...]:
    """들어오는 키가 닿아도 되는 (메서드, 경로). 나머지는 앞단에서 끊긴다."""
    return tuple(sorted((m.upper(), _normalize(p)) for m, p in INBOUND_KEY_ALLOWED))


def render_locations() -> str:
    """`server { }` 안에 넣을 위치 블록을 만든다."""
    parts: list[str] = [HEADER]

    parts.append("    # ── ① 익명 거절 (D-348) — §0.4 라 라우트를 못 고친 자리 ──\n")
    for path in gated_paths():
        parts.append(
            f"    location = {path} {{\n"
            f"        {CREDENTIAL_FOLD}\n"
            f"        if ({CREDENTIAL_PROBE} = \"\") {{ {DENY_ANON} }}\n"
            f"        {PROXY_INCLUDE}\n"
            f"    }}\n"
        )

    parts.append("\n    # ── ①-b 익명 거절 · 접두 (P-83) — 경로 틀은 이름으로 못 막는다 ──\n")
    for prefix in gated_prefixes():
        # `^~` 는 **정규식 위치보다 먼저** 잡는 접두 일치다. 붙이지 않으면 아래
        # `location /` 가 먼저 잡혀 이 블록이 죽는 배치가 생긴다.
        parts.append(
            f"    location ^~ {prefix} {{\n"
            f"        {CREDENTIAL_FOLD}\n"
            f"        if ({CREDENTIAL_PROBE} = \"\") {{ {DENY_ANON} }}\n"
            f"        {PROXY_INCLUDE}\n"
            f"    }}\n"
        )
        # ⚠ 접두의 **슬래시 없는 자기 자신**(`/api/apikey`)은 여기서 내지 않는다.
        #   `location = <경로>` 로 내면 `parse_gated_paths()` 가 그것을 「이름으로 선언한
        #   자리」로 되읽고, 선언 목록(`AUTHN_REQUIRED_PATHS`)과 갈려 자기시험이 빨개진다.
        #   그 자리는 라우트가 아니고(`/api/apikey` 는 아무것도 아니다) 미들웨어가
        #   여전히 덮는다 — 앞단이 덜 덮는 쪽이지 **더 덮어서 사고를 내는 쪽**이 아니다.

    parts.append("\n    # ── ② 들어오는 키 기본값 거절 (D-343 ③) — 선언한 자리에만 닿는다 ──\n")
    for method, path in key_allowed():
        parts.append(
            f"    location = {path} {{\n"
            f"        set $gx_key_denied \"\";\n"
            f"        if ($http_x_api_key != \"\") {{ set $gx_key_denied \"key\"; }}\n"
            f"        if ($request_method = {method}) {{ set $gx_key_denied \"\"; }}\n"
            f"        if ($gx_key_denied = \"key\") {{ {DENY_KEY} }}\n"
            f"        {PROXY_INCLUDE}\n"
            f"    }}\n"
        )

    parts.append(
        "\n    # ── ③ 나머지 전부 — 키를 들고 오면 여기서 끊긴다 (기본값 거절) ──\n"
        "    location / {\n"
        f"        if ($http_x_api_key != \"\") {{ {DENY_KEY} }}\n"
        f"        {PROXY_INCLUDE}\n"
        "    }\n"
    )
    conf = "".join(parts)
    _assert_round_trip(conf)
    return conf


def _assert_round_trip(conf: str) -> None:
    """★ [P-91 · 2026-09-07 턴 J · 차선 S] **생성기가 제 출력을 되읽는다.**

    왜 여기인가 — `parse_gated_prefixes` 가 **아무도 안 부르는 함수**였다.
    ------------------------------------------------------------------
    되읽기 셋(`parse_gated_paths`·`parse_key_allowed`·`parse_gated_prefixes`)은
    아래 §되읽기의 규율(「빈 집합끼리 일치로 초록이 나면 안 된다」)을 위해 태어났다.
    그런데 **접두 쪽만 부르는 데가 없었다**: `scripts/ops_front_line.py --check` 는
    `parse_gated_paths`·`parse_key_allowed` 둘만 견주고 `^~` 블록은 안 본다
    (`ops_front_line.py:122~140` [실측 2026-09-07]). 그래서 `verify_dormant` 가
    이 함수를 ㉠「호출 없음」으로 잡았다 — **옳은 관찰이다.** 접두 블록이
    통째로 빠져도 오늘의 드리프트 검사는 초록이었다.

    고르는 길은 둘이었다: ① 잠그고 사유를 적는다 ② 잇는다.
    `scripts/ops_*` 는 차선 S 소유 밖이라 `--check` 를 못 고치는데, 되읽기를
    **생성기 자신**에 걸면 소유 안에서 같은 것을 얻는다 — 그리고 더 낫다:
    `--check` 는 사람이 부를 때만 도는데, 이 자리는 **설정을 낼 때마다** 돈다.

    무엇을 막는가: 선언 목록(`AUTHN_REQUIRED_PATHS`·`AUTHN_REQUIRED_PREFIXES`·
    `INBOUND_KEY_ALLOWED`)과 **낸 설정**이 갈리면 여기서 예외로 선다.
    조용히 반쪽짜리 nginx 설정을 내보내지 않는다 — 앞단이 덜 덮으면 그것은
    「두 번째 방어선이 있다」는 착시다.

    ⚠ 되돌리기: 이 호출 한 줄을 뺀다. 그럴 조건 — 되읽기가 생성기보다 느슨해서
      **정상 설정을 거절하는** 일이 생기면(그때는 되읽기가 틀린 것이니 그쪽을 고친다).
    """
    bad: list[str] = []
    got_paths = parse_gated_paths(conf)
    if got_paths != set(gated_paths()):
        bad.append(f"익명 401 경로가 갈렸다: 선언에만 {sorted(set(gated_paths()) - got_paths)} · "
                   f"설정에만 {sorted(got_paths - set(gated_paths()))}")
    got_prefixes = parse_gated_prefixes(conf)
    if got_prefixes != set(gated_prefixes()):
        bad.append(f"익명 401 **접두**가 갈렸다: 선언에만 "
                   f"{sorted(set(gated_prefixes()) - got_prefixes)} · "
                   f"설정에만 {sorted(got_prefixes - set(gated_prefixes()))}")
    got_keys = parse_key_allowed(conf)
    if got_keys != set(key_allowed()):
        bad.append(f"키 허용이 갈렸다: 선언에만 {sorted(set(key_allowed()) - got_keys)} · "
                   f"설정에만 {sorted(got_keys - set(key_allowed()))}")
    if bad:
        raise AssertionError(
            "앞단 설정이 선언과 갈렸다 — 이 설정을 내보내면 앞단이 덜 덮는다:" + "\n  "
            + "\n  ".join(bad))


# ═══════════════════════════════════════════════════════════════════════════
# 되읽기 — **낸 것을 다시 읽어 대조한다**
#   생성기가 목록을 통째로 빠뜨려도 「빈 집합끼리 일치」로 초록이 나면 안 된다.
#   그래서 시험은 이 함수로 **설정 원문에서** 읽어 선언과 견준다.
# ═══════════════════════════════════════════════════════════════════════════
_LOCATION = re.compile(r"^\s*location\s*=\s*(\S+)\s*\{", re.MULTILINE)
_LOCATION_PREFIX = re.compile(r"^\s*location\s*\^~\s*(\S+)\s*\{", re.MULTILINE)


def parse_gated_prefixes(conf: str) -> set[str]:
    """설정 원문에서 **접두로** 익명 401 을 내는 위치를 읽는다 (P-83)."""
    out: set[str] = set()
    for match in _LOCATION_PREFIX.finditer(conf):
        body = _block_body(conf, match.end())
        if "authentication required" in body:
            out.add(match.group(1))
    return out


def parse_gated_paths(conf: str) -> set[str]:
    """설정 원문에서 **익명 401 을 내는** 위치를 읽는다."""
    out: set[str] = set()
    for match in _LOCATION.finditer(conf):
        body = _block_body(conf, match.end())
        if "authentication required" in body:
            out.add(match.group(1))
    return out


def parse_key_allowed(conf: str) -> set[tuple[str, str]]:
    """설정 원문에서 **키가 허용된** (메서드, 경로) 를 읽는다."""
    out: set[tuple[str, str]] = set()
    for match in _LOCATION.finditer(conf):
        body = _block_body(conf, match.end())
        method = re.search(r"if\s*\(\$request_method\s*=\s*(\w+)\)", body)
        if method and "gx_key_denied" in body:
            out.add((method.group(1).upper(), match.group(1)))
    return out


def _block_body(conf: str, start: int) -> str:
    """중괄호 짝을 세어 블록 본문을 떼어 낸다 (nginx `if` 가 중첩된다)."""
    depth, i = 1, start
    while i < len(conf) and depth:
        if conf[i] == "{":
            depth += 1
        elif conf[i] == "}":
            depth -= 1
        i += 1
    return conf[start:i]
