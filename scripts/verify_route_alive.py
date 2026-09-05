#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""화면이 쓰는 라우트를 **실제 HTTP 로 때린다** — 단위 시험이 못 보는 층 (D-386).

    "캡처 첫 시도에서 `/api/dsm/events` 가 **500** 이었다.
     **단위 시험 530건이 전부 초록인 채로** 그 라우트는 운영에서 죽어 있었다."

단위 시험은 **함수를 부른다.** 브라우저는 **라우트를 때린다.** 그 사이에 URL 배선·
스키마 해석·직렬화·권한·미들웨어 순서가 다 들어 있고, 단위 시험은 그 전부를 건너뛴다.
그래서 이 판정기가 있다 — **단위가 전부 초록이어도 독립적으로 빨개질 수 있어야 한다.**
그것이 존재 이유다(D-386).

무엇을 때리나 — **우리가 정하지 않는다**
----------------------------------------
`scripts/capture_screens.py` 가 화면을 지나며 **브라우저가 실제로 부른 API** 를 적어 둔
`docs/agent/evidence/D-386/screen_routes.json` 을 읽는다. 목록을 손으로 적으면 화면이
새 API 를 부르기 시작한 날 이 판정기만 옛말을 하게 된다.

    python scripts/verify_route_alive.py --user gxprobe_e2e --password ****
    python scripts/verify_route_alive.py --self-test      # 판정 규칙 대조 (D-277 · D-310)

★ D-310 자기표본: **500 을 내던 그 라우트**(`/api/dsm/events`)를 자기시험에 박았다.
  목록에서 그 라우트가 사라지면 자기시험이 먼저 실패한다 — 눈이 감기는 것을 눈이 본다.

종료 코드
    0 전부 살아 있다 · 1 죽은 라우트가 있다 · 2 **판정 불가**(서버 미기동·자격증명 없음)
★ 2 는 실패가 아니고 **통과는 더더욱 아니다.** 때려 보지 못한 것을 초록으로 적지 않는다(D-301).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 증거가 어디에 있나. 컨테이너는 저장소가 `/repo`, 문서가 `/docs` 로 **따로** 붙는다 —
#: `/repo/docs` 는 없다. 한 자리로 못 박으면 컨테이너에서 「목록이 없다」로 죽는다 [실측].
def _routes_file() -> Path:
    tail = Path("agent") / "evidence" / "D-386" / "screen_routes.json"
    for base in (ROOT / "docs", Path("/docs")):
        if (base / tail).is_file():
            return base / tail
    return ROOT / "docs" / tail


#: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 사례는 합성이 아니다:
#:   [실측 2026-09-12] 화면을 처음 띄운 순간 `GET /api/dsm/events` 가 **500** 이었다
#:   (pydantic `QueryParams is not fully defined` — 미래 임포트 + @tenant_scoped).
#:   **단위 시험 530건이 전부 초록인 채로** 그 라우트는 운영에서 죽어 있었다.
#:   아래 자기시험이 그 사례 그대로를 판정한다 — 합성 상태 코드가 아니라 그날의 세 값으로.
BIRTH_SAMPLE = ("GET", "/api/dsm/events", 500)

#: ★ 자기표본 (D-310). 이 라우트가 목록에 없으면 **판정기부터 의심한다** — 이번 국면에서
#:   실제로 500 을 내던 자리이고, 화면을 띄우기 전에는 아무도 몰랐다.
SELF_SAMPLE = "/api/dsm/events"

#: 값이 든 경로(`/api/dsm/events/4674`)는 그 순간의 씨앗을 가리킨다. 씨앗은 캡처가 끝나며
#: 지워지므로(D-347 ④) 지금 때리면 404 가 정상이다 — **때리지 않고, 몇 건인지 말한다**(D-301).
_HAS_ID = re.compile(r"/\d+(?:/|$)")


def judge(status: int) -> tuple[bool, str]:
    """상태 코드 하나를 판정한다. **규칙을 함수로 떼어 둔 이유는 시험하기 위해서다.**

    · 2xx      살아 있다
    · 401/403  **살아 있다.** 문지기가 선 것은 라우트가 죽은 것이 아니다(F-09 는 그것을 원한다)
    · 5xx      죽었다 — 이번 국면이 잡으려는 바로 그것
    · 그 밖    죽었다(404 포함) — 화면이 부르는데 없는 자리다
    """
    if 200 <= status < 300:
        return True, "산다"
    if status in (401, 403):
        return True, "문지기가 섰다(살아 있다)"
    if status >= 500:
        return False, "**서버 오류** — 화면이 부르는 자리가 죽었다"
    return False, "없거나 못 받는다"


def load_routes(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs: set[tuple[str, str]] = set()
    skipped: list[str] = []
    for _screen, calls in data.get("screens", {}).items():
        for c in calls:
            if c.get("method", "GET").upper() != "GET":
                continue
            p = c["path"]
            #: id 판정은 **경로 부분만** 본다 — `?page_size=10000` 의 숫자는 씨앗이 아니다
            if _HAS_ID.search(p.split("?", 1)[0]):
                skipped.append(p)
                continue
            pairs.add((c.get("method", "GET").upper(), p))
    return sorted(pairs), sorted(set(skipped))


#: ★ **로그인 경로는 우리가 정하지 않는다 — 제품이 정한다** [실측 2026-09-17].
#:   앞판은 `/api/token/pair` 를 **첫째로** 시도했고 그것이 231자 JWT 를 내주었다.
#:   그런데 dj-core `core/auth.py:38` 은 `user.token`(저장된 세션 토큰)이 없으면
#:   **"Token expired"** 로 그 JWT 를 거절한다 — `token/pair` 는 세션을 세우지 않는다.
#:   결과: **로그인 성공이라 적어 놓고 26건 중 24건이 401**, 그 401 을 규칙대로
#:   「문지기가 섰다(살아 있다)」로 읽어 **exit 0**. 죽어 있던 `/api/media-data(/)` 두 자리는
#:   그 401 에 가려 보이지 않았다. 이 파일 첫머리가 「가장 나쁜 실패」라 적어 둔 바로 그것이다.
#:   `/api/v1/auth/login` 이 세션을 세우는 진짜 문이다 — **먼저 시도한다.**
LOGIN_PATHS = ("/api/v1/auth/login", "/api/token/pair")


def _extract_token(data: object) -> str | None:
    """응답에서 접근 토큰을 찾는다. 제품은 `{"user": {"access_token": ...}}` 로 감싼다."""
    if not isinstance(data, dict):
        return None
    #: ★ **HTTP 200 인데 `success: false`** — 조용한 성공을 토큰으로 읽지 않는다.
    #:   제품은 「다른 곳에 활성 세션이 있다」를 **200 + success:false** 로 낸다 [실측].
    if data.get("success") is False:
        return None
    for scope in (data, data.get("user"), data.get("data")):
        if not isinstance(scope, dict):
            continue
        for key in ("access_token", "access", "token"):
            tok = scope.get(key)
            if isinstance(tok, dict):
                tok = tok.get("access") or tok.get("token")
            if isinstance(tok, str) and len(tok) > 40:
                return tok
    return None


def login(api: str, user: str, password: str) -> str | None:
    """제품의 로그인으로 토큰을 받는다. **못 받으면 못 받았다고 말한다** — 익명으로 때려
    401 만 잔뜩 보고 「전부 살아 있다」로 적는 것이 이 판정기의 가장 나쁜 실패다.

    ★ 여기서 토큰을 받은 것은 **아직 증거가 아니다.** 받은 토큰이 실제로 문을 여는지는
      `token_changed_anything()` 이 익명 대조로 판정한다 — 이 함수는 그것을 대신하지 않는다.
    """
    for path in LOGIN_PATHS:
        #: `end_previous_session` — 제품은 동시 접속 1개다. 이 칸이 없으면 앞선 세션
        #: 때문에 **200 + success:false** 가 돌아온다(토큰 없음) [실측].
        payload = {"username": user, "password": password, "end_previous_session": True}
        body = json.dumps(payload).encode()
        req = urllib.request.Request(api + path, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (404, 405):
                continue
            print(f"[ALIVE] 로그인 {path} → HTTP {e.code}")
            continue
        except Exception as exc:                       # noqa: BLE001
            print(f"[ALIVE] 로그인 {path} → {type(exc).__name__} {exc}")
            continue
        tok = _extract_token(data)
        if tok:
            print(f"[ALIVE] 로그인 성공: {path}")
            return tok
        if isinstance(data, dict) and data.get("success") is False:
            print(f"[ALIVE] 로그인 {path} → 200 인데 success=false: "
                  f"{str(data.get('message'))[:120]}")
    return None


def hit(api: str, method: str, path: str, token: str | None,
        *, with_body: bool = False) -> int | tuple[int, bytes]:
    """문 하나를 두드린다. `with_body` 면 `(상태, 본문)` 을 함께 돌려준다.

    ★ 본문 갈래는 `verify_contract_route_reach` 가 쓴다 — 그 판정기는 목록 응답에서
      **씨앗 id 를 거둬** 매개변수 경로를 때린다(없는 id 로 때리면 404 가 「없는 문」인지
      「없는 행」인지 못 가른다). 그쪽에 두 번째 `hit` 을 두지 않는 이유는 하나다:
      **두 벌은 반드시 어긋난다**(D-369). 이 함수 안에는 2026-09-17 의 교훈
      (익명 대조 · 401 판독)이 얽혀 있고, 복사본은 그 교훈을 한쪽에만 남긴다.
    """
    req = urllib.request.Request(api + path, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return (r.status, r.read()) if with_body else r.status
    except urllib.error.HTTPError as e:
        return (e.code, e.read()) if with_body else e.code
    except Exception as exc:                           # noqa: BLE001
        print(f"[ALIVE] {path} — 응답을 못 받았다: {type(exc).__name__} {exc}")
        return (0, b"") if with_body else 0


#: ★ **출생 표본 ②** (D-310) — [실측 2026-09-17] 「로그인 성공」을 찍고도
#:   26건 중 **24건이 401** 이었고, 규칙이 401 을 「살아 있다」로 읽어 **exit 0** 이 나갔다.
#:   토큰은 받았으나 **아무 문도 열지 못한 토큰**이었다. 그 아래 `/api/media-data(/)` 두 자리는
#:   실제로 **500** 이었는데 401 에 덮여 있었다.
#:   그래서 이 도구는 이제 **토큰이 무엇을 바꿨는지**를 센다 — 0건이면 판정 불가다.
BIRTH_SAMPLE_TOKEN_DEAF = (26, 24)   # (때린 라우트, 401 이던 라우트) — 그날의 두 수


def token_changed_anything(api: str, pairs: list[tuple[str, str]],
                           token: str, tok_status: dict[tuple[str, str], int]) -> tuple[bool, int]:
    """**토큰을 넣은 것과 안 넣은 것의 결과가 같으면, 그 토큰은 없는 것과 같다.**

    이것이 「로그인 성공」이라는 진술을 **증거로** 바꾸는 유일한 자리다. 로그인 응답이
    200 이고 JWT 모양의 문자열이 들어 있다는 사실은 그 토큰이 **먹힌다**는 뜻이 아니다 —
    2026-09-17 에 정확히 그 착시로 초록이 나갔다(위 출생 표본 ②).

    양성 대조를 손으로 정하지 않는 것이 요점이다. 「이 라우트는 인증되면 200 이어야 한다」를
    적어 두면 그 목록이 곧 옛말이 된다. 대신 **같은 목록을 익명으로 한 번 더 때려**
    두 결과를 견준다. 한 건도 안 바뀌면 우리는 한 번도 들어가지 못한 것이다.

    반환: (바꿨는가, 바뀐 건수)
    """
    changed = 0
    for method, path in pairs:
        anon = hit(api, method, path, None)
        if anon != tok_status.get((method, path)):
            changed += 1
    return changed > 0, changed


def self_test() -> int:
    """판정 규칙과 자기표본을 함께 본다 (D-277 · D-310)."""
    bad = []
    for status, expect in ((200, True), (204, True), (401, True), (403, True),
                           (500, False), (502, False), (404, False), (0, False)):
        ok, _ = judge(status)
        if ok != expect:
            bad.append(f"judge({status}) = {ok} (기대 {expect})")
    # ★ 출생 표본 — 그날의 세 값(GET · /api/dsm/events · 500)을 그대로 판정한다
    _m, _p, _s = BIRTH_SAMPLE
    if judge(_s)[0]:
        bad.append(f"출생 표본 {_m} {_p} {_s} 를 「살아 있다」로 읽는다 — "
                   f"이 도구가 태어난 바로 그 사례를 놓친다 (D-310)")
    # ── 출생 표본 ② — **토큰을 받고도 아무 문도 못 연 날** (D-310 · 2026-09-17) ──
    #   그날 26건 중 24건이 401 이었고 규칙은 그것을 「살아 있다」로 읽었다. 규칙은 옳다 —
    #   틀린 것은 **들어가지 못한 채로 그 규칙을 쓴 것**이다. 그래서 둘을 함께 시험한다.
    _n, _gated = BIRTH_SAMPLE_TOKEN_DEAF
    if not judge(401)[0]:
        bad.append("judge(401) 이 「죽었다」가 되었다 — 문지기가 선 것은 죽은 것이 아니다")
    #: 그날의 상황을 그대로 만든다: 익명과 토큰이 **모든 라우트에서 같은 답**을 냈다.
    _pairs = [("GET", f"/probe/{i}") for i in range(_n)]
    _same = {k: 401 for k in _pairs}
    _saved_hit = globals()["hit"]
    try:
        globals()["hit"] = lambda api, m, p, t: 401       # 익명도 똑같이 401
        _worked, _changed = token_changed_anything("http://x", _pairs, "tok", _same)
    finally:
        globals()["hit"] = _saved_hit
    if _worked or _changed != 0:
        bad.append(f"출생 표본 ② — 익명과 결과가 같은데 「토큰이 먹혔다」로 읽는다 "
                   f"(바뀐 건수 {_changed}) — 2026-09-17 의 거짓 초록이 그대로 산다")
    #: 음성 갈래 — 토큰이 **한 건이라도** 바꾸면 통과여야 한다. 「전부 2 로」가 되면 안 된다.
    _saved_hit = globals()["hit"]
    try:
        globals()["hit"] = lambda api, m, p, t: 401
        _one = dict(_same); _one[_pairs[0]] = 200
        _worked2, _changed2 = token_changed_anything("http://x", _pairs, "tok", _one)
    finally:
        globals()["hit"] = _saved_hit
    if not _worked2 or _changed2 != 1:
        bad.append(f"토큰이 1건을 바꿨는데 못 알아본다 (바뀐 건수 {_changed2}) — "
                   f"판정 불가가 모든 것을 삼킨다")

    # ── 로그인 응답 판독 — 양성·음성 (D-277) ─────────────────────────────────
    if LOGIN_PATHS[0] != "/api/v1/auth/login":
        bad.append(f"로그인 첫 경로가 {LOGIN_PATHS[0]} 다 — /api/token/pair 를 먼저 물으면 "
                   f"세션 없는 JWT 를 받아 전부 401 이 된다 [실측 2026-09-17]")
    if _extract_token({"user": {"access_token": "a" * 200}, "success": True}) is None:
        bad.append("제품 응답 모양 {user:{access_token}} 에서 토큰을 못 찾는다")
    if _extract_token({"success": False, "status": 200,
                       "message": "active session"}) is not None:
        bad.append("**200 인데 success:false** 를 토큰으로 읽는다 — 조용한 성공을 성공으로 셌다")
    if _extract_token({"user": {"access_token": "short"}}) is not None:
        bad.append("토큰 자리에 든 짧은 문자열을 토큰으로 읽는다")

    src = _routes_file()
    if not src.is_file():
        bad.append(f"라우트 목록이 없다: {src} — 무엇을 때릴지 모르는 채로 통과할 수 없다")
    else:
        pairs, _ = load_routes(src)
        #: 질의문자열은 그대로 두고 때리므로(위 사유) 자기표본은 **경로로** 맞춘다
        if not any(p.split("?", 1)[0] == SELF_SAMPLE for _, p in pairs):
            bad.append(f"자기표본 {SELF_SAMPLE} 이 목록에 없다 — 500 을 내던 그 자리다 (D-310)")
    if bad:
        print("[ALIVE] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print(f"    {b}")
        return EXIT_FAIL
    print(f"[ALIVE] 자기시험 통과 — 판정 규칙 8종 + 출생 표본 {BIRTH_SAMPLE[1]} 500 "
          f"+ 출생 표본 ② 토큰 먹통 {BIRTH_SAMPLE_TOKEN_DEAF[1]}/{BIRTH_SAMPLE_TOKEN_DEAF[0]} 401 "
          f"+ 로그인 판독 양성1·음성2 + 자기표본 {SELF_SAMPLE}")
    return EXIT_OK


#: ★ P-12 ① — **자격증명이 없어 못 잰 것은 회색이다. 회색은 색이 아니라 빚이다.**
#:   게이트가 스스로 로그인할 수 있어야 그 빚이 갚아진다. 값은 **저장소 밖**에 산다 —
#:   여기서 읽는 파일은 전부 `.gitignore` 가 잡는 자리이고, 저장소에는 **이름만** 남는다
#:   (`docs/agent/ENV_EXAMPLE_게이트자격증명.txt` · D-204).
#:   ⚠ 이미 환경에 있는 값을 **덮지 않는다** — CI 가 준 값이 파일에 지는 일이 없어야 한다.
LOCAL_ENV_FILES = (".env.gates", ".env.local", ".env")
LOCAL_ENV_KEYS = ("GX_API", "GX_ROUTE_USER", "GX_ROUTE_PASSWORD", "GX_ROUTE_CONTAINER",
                  # UX-25 — 시드 역할 계정(U1·U2·U4) 공용 비밀번호.
                  # `verify_sidebar.py` 가 **역할별로 로그인해서** 사이드바를 잰다.
                  # 읽는 자리를 따로 만들지 않는다(같은 D-369 사유).
                  "GX_SEED_ROLE_PASSWORD",
                  # P-5 — 같은 로컬 파일에서 저장소 자격증명도 읽는다.
                  # 읽는 자리를 둘로 만들면 둘이 어긋난다(D-369).
                  "MINIO_ENDPOINT", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD",
                  "MINIO_BUCKET_NAME")


def load_local_env() -> list[str]:
    """로컬(gitignored) env 파일에서 `GX_*` 이름만 읽어 환경에 채운다. 읽은 파일을 돌려준다."""
    read: list[str] = []
    for name in LOCAL_ENV_FILES:
        f = ROOT / name
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        took = False
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k not in LOCAL_ENV_KEYS or os.environ.get(k):
                continue
            os.environ[k] = v.strip().strip('"').strip("'")
            took = True
        if took:
            read.append(name)
    return read


#: ★ 서버가 **호스트에서 안 보이는** 환경이 이 저장소의 기본값이다 [실측 2026-09-17]:
#:   `gx-shell` 은 8000 을 게시하지 않아 172.18.0.4:8000 은 호스트에서 시간 초과다.
#:   컨테이너 안에서는 200 이다. 게이트가 호스트에서 도는 한, 위임 없이는 **영원히 회색**이다.
#:   그래서 이름이 주어지면 **자신을 컨테이너 안에서 다시 돌린다** — 한 벌의 코드가 두 곳에서
#:   같은 판정을 한다(두 벌은 반드시 어긋난다 · D-369).
#:   ⚠ 비밀번호를 명령줄에 싣지 않는다. `docker exec -e NAME`(값 없이)은 **제 환경에서**
#:     값을 가져가므로 프로세스 목록에 남지 않는다.
def delegate_to_container(container: str, json_path: str | None,
                         script: str = "verify_route_alive.py") -> int:
    import subprocess
    #: `script` — 이 위임은 판정기 하나만의 것이 아니다. `verify_minio.py` 도 같은 문으로
    #:   들어간다. 위임을 복사하지 않고 **이름만 받는다** (두 벌은 반드시 어긋난다 · D-369).
    inner = ["python", "/repo/scripts/" + script]
    if json_path:
        #: 컨테이너는 문서를 `/docs` 로 붙인다 — 호스트의 `docs/…` 를 그 자리로 옮긴다.
        norm = json_path.replace("\\", "/")
        inner += ["--json", "/docs/" + norm[len("docs/"):] if norm.startswith("docs/") else norm]
    cmd = ["docker", "exec",
           "-e", "GX_ROUTE_IN_CONTAINER=1",
           "-e", "GX_API", "-e", "GX_ROUTE_USER", "-e", "GX_ROUTE_PASSWORD",
           # ★ 값 없이 이름만 넘긴다 — 프로세스 목록에 비밀번호가 안 남는다.
           #   이 이름이 부모 환경에 없으면 docker 는 그냥 안 넘긴다(무해).
           "-e", "GX_SEED_ROLE_PASSWORD",
           "-e", "MINIO_ENDPOINT", "-e", "MINIO_ROOT_USER",
           "-e", "MINIO_ROOT_PASSWORD", "-e", "MINIO_BUCKET_NAME",
           container] + inner
    print(f"[ALIVE] 컨테이너 위임: {container} (호스트에서 서버가 안 보인다 · "
          f"GX_ROUTE_CONTAINER)")
    # ★ [실측 2026-09-18] **비우지 않으면 우리 줄이 맨 뒤로 간다.** 자식은 파이프에
    #   바로 쓰고 우리 출력은 버퍼에 남았다가 종료 때 흘러나온다. 그래서 게이트가
    #   `tail -1` 로 집은 「판정문」이 실제로는 **이 안내 문구**였다 —
    #   초록이 무엇을 재고 한 말인지 모르게 되는 자리다(D-301). 순서는 사실의 일부다.
    sys.stdout.flush()
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print("[ALIVE] docker 명령을 찾지 못했다 — **판정 불가**")
        return EXIT_UNDECIDABLE


def main() -> int:
    #: argparse 의 default 가 os.environ 을 읽으므로 **파서를 만들기 전에** 채워야 한다.
    _env_files = load_local_env()
    ap = argparse.ArgumentParser(description="화면이 쓰는 라우트가 살아 있나 (D-386)")
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
        return delegate_to_container(container, args.json)

    src = _routes_file()
    pairs, skipped = load_routes(src)
    print(f"[ALIVE] [입력] {len(pairs)}건 — 화면이 실제로 부른 GET 라우트 "
          f"(값이 든 경로 {len(skipped)}건은 씨앗이 지워져 때리지 않는다)")

    try:
        urllib.request.urlopen(args.api + "/api/docs", timeout=10)
    except urllib.error.HTTPError:
        pass
    except Exception as exc:                           # noqa: BLE001
        print(f"[ALIVE] API 에 닿지 못했다 ({args.api}): {type(exc).__name__} {exc}")
        print("[ALIVE] **판정 불가** — 때려 보지 못한 것을 초록으로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE
    if _env_files:
        print(f"[ALIVE] 로컬 자격증명 파일 읽음: {', '.join(_env_files)} (저장소엔 이름만 · D-204)")
    if not (args.user and args.password):
        print("[ALIVE] 자격증명이 없다 (--user/--password 또는 GX_ROUTE_USER/PASSWORD "
              f"또는 {' / '.join(LOCAL_ENV_FILES)})")
        print("[ALIVE] **판정 불가** — 익명으로 때려 401 만 보고 통과로 적지 않는다 (D-301)")
        return EXIT_UNDECIDABLE
    token = login(args.api, args.user, args.password)
    if not token:
        print("[ALIVE] 토큰을 못 받았다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    dead, rows = [], []
    tok_status: dict[tuple[str, str], int] = {}
    for method, path in pairs:
        status = hit(args.api, method, path, token)
        tok_status[(method, path)] = status
        ok, why = judge(status)
        rows.append({"method": method, "path": path, "status": status, "alive": ok})
        mark = "  " if ok else "✗ "
        print(f"[ALIVE] {mark}{status:3} {method:4} {path:52} {why}")
        if not ok:
            dead.append((method, path, status))

    # ── ★ 토큰이 실제로 문을 열었는가 — 익명 대조 (출생 표본 ②) ──────────────
    #   여기를 통과하지 못하면 아래의 어떤 판정도 믿을 수 없다. 401 을 「문지기가 섰다」로
    #   읽는 규칙은 **우리가 들어갈 수 있을 때만** 옳다. 못 들어간 채로 401 을 세면
    #   죽은 라우트가 그 뒤에 숨는다 — 그것이 2026-09-17 에 일어난 일이다.
    worked, changed = token_changed_anything(args.api, pairs, token, tok_status)
    gated = sum(1 for st in tok_status.values() if st in (401, 403))
    print(f"[ALIVE] 토큰 대조 — 익명과 다른 응답 {changed}/{len(pairs)}건 · "
          f"토큰을 들고도 401/403 인 자리 {gated}건")
    if not worked:
        print("[ALIVE] 토큰이 **아무것도 바꾸지 않았다** — 익명으로 때린 것과 결과가 같다.")
        print("[ALIVE] **판정 불가** — 들어가지 못한 채 본 401 을 "
              "「살아 있다」로 적지 않는다 (D-301 · 출생 표본 ②)")
        return EXIT_UNDECIDABLE

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"api": args.api, "checked": len(pairs),
                                   "skipped_with_id": skipped, "rows": rows,
                                   "dead": len(dead)}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"[ALIVE] 증거 기록: {out}")

    if dead:
        print(f"[ALIVE] **죽은 라우트 {len(dead)}건** — 화면이 부르는데 응답이 없다:")
        for m, p, s in dead:
            print(f"          {s} {m} {p}")
        return EXIT_FAIL
    print(f"[ALIVE] 통과 — {len(pairs)}건 전부 살아 있다 (실제 HTTP 로 때렸다)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
