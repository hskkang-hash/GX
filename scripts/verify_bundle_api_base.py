#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-182 — **서버가 내는 번들 안에 API 주소가 박혀 있다** (2026-09-18 · 턴 V · 조율자).

무엇을 막는가 — **번들을 `.env` 없이 지어 측정 전부를 막았다** [실측 2026-09-18 · 턴 U]
---------------------------------------------------------------------------------
턴 U 에 조율자가 프런트를 다시 지으면서 `gx-fe-build` 의 `/app/.env` 를 빌드 자리로
같이 넣지 않았다. `vite` 는 **성공**했고(`exit 0`), 번들도 멀쩡히 섰다. 그런데
`import.meta.env.VITE_API_URL` 이 **빈 문자열**로 치환돼 `apiBase()` 가 `""` 를
돌려줬고, 로그인 POST 가 API 가 아니라 **SPA 제 원점**으로 갔다 → `501` →
V 의 측정이 **40분 동안 통째로** 막혔다.

★ 이 사고의 모양이 무섭다: **아무것도 빨갛지 않았다.** 빌더는 0, 번들 해시 게이트도
  초록(그 게이트는 「번들 = 이 커밋인가」만 묻는다), 화면도 떴다. 어긋난 곳은
  **번들 안에 있어야 할 리터럴이 없다**는 것 하나였고, 그것을 묻는 게이트가 없었다.

그래서 세 가지를 문다 (P-182)
-----------------------------
  ① **기대한 API 밑동이 번들에 있나.** `--expect`(기본: `GX_EXPECT_API_BASE`)로
     준 주소가 엔트리 JS 안에 **리터럴로** 있어야 한다. 없으면 빨강 —
     「`.env` 없이 지었다」의 지문이다. ⚠ 기대를 **안 주면 회색이다** — 초록이 아니다.
  ② **그 밑동이 SPA 제 원점과 다른가.** 같으면 빨강. 같은 순간 `""` 와 구별되지 않고,
     그 구별이 안 되는 자리가 정확히 턴 U 의 사고 자리다.
  ③ ★ **남의 주소를 밑동으로 세지 않는다.** 이 게이트가 처음 돌면서 드러난 약점이다 —
     살아 있는 번들에는 `http(s)://` 리터럴이 **55개** 있고 그중 대부분은
     `react.dev` · `redux.js.org` 같은 **의존성 안의 문서 주소**다. 「하나라도 있으면
     통과」로 짠으면 **사고 당일의 번들도 초록**이 된다.

  덤으로 게이트 자리에서는 ③ **SPA 정적 서버가 `/api/...` 에 404 를 내는가**를 함께
  문다. 턴 U 에 V 가 찾은 **거짓 초록의 씨**다 — 옛 서버는 파일이 없으면 무엇이든
  `index.html` 을 **200** 으로 돌려줬고, 상태코드로 「문이 살아 있다」를 세는 도구는
  그 200 을 그대로 먹었다. 지금 본문은 `scripts/gate_spa_server.py` 에 있다.

무엇을 재지 **않는가**
----------------------
· 번들이 어느 커밋인지 — 그것은 `verify_bundle_hash.py`(P-59)의 일이다. 두 게이트는
  서로의 빈자리를 메운다: 저쪽은 **신원**, 이쪽은 **배선**.
· `.env` 의 다른 값 — 이 파일은 `VITE_API_URL` **한 이름**만 본다. 그 파일에는 키와
  비밀번호가 같이 산다. ⚠ **값을 찍지 않는다** — API 밑동은 주소라 찍고, 나머지는
  이름조차 건드리지 않는다.

쓰는 법
-------
    python scripts/verify_bundle_api_base.py                     # 서는 SPA 를 문다
    python scripts/verify_bundle_api_base.py --dist /app/_fe_dist  # 파일을 문다(곁길)
    python scripts/verify_bundle_api_base.py --expect http://localhost:8000
    python scripts/verify_bundle_api_base.py --self-test

종료 코드: 0 성립 · 1 빨강 · 2 회색(잴 수 없었다 — SPA 가 안 선다 등)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

EXIT_OK, EXIT_RED, EXIT_GRAY = 0, 1, 2

DEFAULT_SPA = os.environ.get("GX_SPA_URL", "http://localhost:3002")
ENV_NAME = "VITE_API_URL"

#: 엔트리 `<script type="module" src="...">` — vite 가 내는 index.html 의 모양.
_ENTRY = re.compile(r'<script[^>]+type="module"[^>]+src="([^"]+)"')
#: 번들에 남은 밑동 리터럴. 포트까지 본다 — 호스트만 같고 포트가 다르면 다른 문이다.
_BASE = re.compile(r'https?://[A-Za-z0-9._-]+(?::\d+)?')

#: 밑동으로 세지 **않을** 주소들. 지도·스트리밍·CDN 은 API 가 아니다.
_NOT_API = (
    "dapi.kakao.com", "maps.googleapis.com", "fonts.googleapis.com",
    "fonts.gstatic.com", "www.w3.org", "schema.org", "unpkg.com",
    "cdn.jsdelivr.net", "github.com", "reactjs.org",
)


def _origin(url: str) -> str:
    m = re.match(r'(https?://[A-Za-z0-9._-]+(?::\d+)?)', url or "")
    return m.group(1) if m else ""


def entry_js_names(index_html: str) -> list[str]:
    """index.html 이 **모듈로** 부르는 스크립트만 돌려준다."""
    return [s for s in _ENTRY.findall(index_html or "")]


def api_bases(js_text: str) -> list[str]:
    """번들에 박힌 **API 가 될 만한** 밑동들 — 중복 없이, 나온 순서대로."""
    seen, out = set(), []
    for b in _BASE.findall(js_text or ""):
        if any(host in b for host in _NOT_API):
            continue
        if b in seen:
            continue
        seen.add(b)
        out.append(b)
    return out


def judge(bases: list[str], spa_origin: str, expect: str = "") -> list[str]:
    """★ 판정은 여기 한 군데에만 있다 — 자기시험이 무는 자리.

    ⚠ [2026-09-18 · 이 게이트가 처음 돌면서 스스로 드러낸 약점]
      처음엔 「밑동이 하나라도 있으면 통과」로 짰다. 실제 번들을 물어 보니 밑동이
      **55개** 나왔고 그중 대부분이 `react.dev` · `redux.js.org` · `bit.ly` 같은
      **의존성 안의 문서 주소**였다. 그 규칙대로라면 `.env` 없이 지은 번들도 —
      사고 당일의 그 번들도 — 남의 문서 주소 덕분에 **초록**이 된다.
      그래서 규칙을 뒤집는다: **기대한 밑동이 거기 있는가**만 묻는다. 기대를 모르면
      초록을 내지 않고 **회색**이다(`expect` 빈 문자열 → 문제 목록에 회색 표식).
    """
    problems: list[str] = []
    if not expect:
        problems.append(
            "GRAY:기대 밑동을 모른다 — `--expect` 또는 `GX_EXPECT_API_BASE` 로 "
            "`%s` 의 값을 줘라. 모르는 채로 초록을 내지 않는다." % ENV_NAME)
        return problems
    if _origin(expect) == spa_origin and spa_origin:
        problems.append(
            "기대 밑동이 **SPA 제 원점**(%s)과 같다 — 이 상태는 밑동이 빈 문자열인 것과 "
            "화면에서 구별되지 않는다. 로그인 POST 가 API 가 아니라 정적 서버로 간다."
            % spa_origin)
    if not any(_origin(b) == _origin(expect) for b in bases):
        problems.append(
            "기대한 밑동 `%s` 이 번들에 **없다** — `%s` 없이 지었다는 지문이다. "
            "`gx-fe-build` 에서 지을 때 `/app/.env` 를 빌드 자리로 같이 넣어라 "
            "(턴 U 조율자 오판 · D-493). 박힌 것 앞 5개: %s"
            % (expect, ENV_NAME, ", ".join(bases[:5]) or "(없음)"))
    return problems


def is_gray(problems: list[str]) -> bool:
    return any(p.startswith("GRAY:") for p in problems)


def _get(url: str, timeout: float = 10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:      # 404 도 **답**이다 — 회색이 아니다
        return e.code, ""
    except Exception as e:                    # 안 서 있다 → 회색
        return 0, str(e)


def probe_spa_api_404(spa: str) -> tuple[bool | None, str]:
    """③ 정적 서버가 `/api/...` 를 **제 것인 양** 받아 주지 않는가.

    ⚠ 탐침 경로에 **한글을 쓰지 않는다.** 처음엔 `.../절대없는자리` 로 짰고
      `urllib` 이 비-ASCII 를 못 실어 예외로 죽었다 — 그 예외가 「SPA 가 안 선다」로
      찍혀서, 멀쩡히 서 있는 서버를 **빨강**으로 만들었다. 못 잰 것은 회색이다.
    """
    code, _ = _get(spa.rstrip("/") + "/api/__gate_probe__/no-such-place")
    if code == 0:
        return None, "잴 수 없었다(응답 없음)"
    return code == 404, "GET /api/__gate_probe__/no-such-place -> %d" % code


def run_live(spa: str, expect: str) -> int:
    code, index = _get(spa.rstrip("/") + "/")
    if code != 200:
        print("[BUNDLE-API] 회색 — SPA 가 %s 에서 안 선다(%s)" % (spa, code or index[:80]))
        return EXIT_GRAY

    names = entry_js_names(index)
    if not names:
        print("[BUNDLE-API] 회색 — index.html 에 모듈 스크립트가 없다(빌드 산출물이 아닌 듯)")
        return EXIT_GRAY

    origin = _origin(spa)
    texts, read = [], []
    for n in names:
        url = n if n.startswith("http") else origin + "/" + n.lstrip("/")
        c, t = _get(url)
        if c == 200:
            texts.append(t)
            read.append(n)
    if not texts:
        print("[BUNDLE-API] 회색 — 엔트리 JS 를 하나도 못 읽었다: %s" % ", ".join(names))
        return EXIT_GRAY

    bases = api_bases("\n".join(texts))
    problems = judge(bases, origin, expect)

    ok404, note = probe_spa_api_404(spa)
    if ok404 is False:
        problems.append(
            "정적 서버가 `/api/...` 에 404 를 내지 않는다(%s) — 상태코드로 문을 세는 "
            "도구가 이 응답을 **살아 있는 문**으로 먹는다(턴 U · 거짓 초록의 씨). "
            "본문: scripts/gate_spa_server.py" % note)
    elif ok404 is None:
        problems.append("GRAY:`/api/*` 404 검사를 못 했다(%s)" % note)

    print("[BUNDLE-API] 엔트리 %d개 읽음: %s" % (len(read), ", ".join(read)))
    print("[BUNDLE-API] 기대 밑동: %s" % (expect or "(안 줌)"))
    print("[BUNDLE-API] 번들에 박힌 주소 리터럴 %d개 — 대부분은 의존성 안의 문서 주소다. "
          "판정은 **기대 밑동이 그 안에 있는가**로만 한다" % len(bases))
    print("[BUNDLE-API] SPA `/api/*` 404 검사: %s (%s)"
          % ({True: "초록", False: "빨강", None: "회색"}[ok404], note))

    if problems:
        for p in problems:
            print("[BUNDLE-API] %s — %s"
                  % ("회색" if p.startswith("GRAY:") else "빨강", p[5:] if p.startswith("GRAY:") else p))
        return EXIT_GRAY if is_gray(problems) and len(problems) == 1 else EXIT_RED
    print("[BUNDLE-API] 초록 — 서버가 내는 번들에 `%s`(%s)이 박혀 있고, 정적 서버는 "
          "`/api/*` 를 제 것인 양 받지 않는다" % (ENV_NAME, expect))
    return EXIT_OK


def run_dist(dist: Path, expect: str) -> int:
    """곁길 — **파일**을 문다. 서버가 내는 것이 아니므로 초록의 무게가 다르다."""
    index = dist / "index.html"
    if not index.exists():
        print("[BUNDLE-API] 회색 — %s 에 index.html 이 없다" % dist)
        return EXIT_GRAY
    names = entry_js_names(index.read_text(encoding="utf-8", errors="replace"))
    texts = []
    for n in names:
        p = dist / n.lstrip("/")
        if p.exists():
            texts.append(p.read_text(encoding="utf-8", errors="replace"))
    if not texts:
        print("[BUNDLE-API] 회색 — 엔트리 JS 파일을 못 찾았다: %s" % ", ".join(names))
        return EXIT_GRAY
    bases = api_bases("\n".join(texts))
    problems = judge(bases, "", expect)
    print("[BUNDLE-API] (곁길·파일) 박힌 밑동 %d개: %s"
          % (len(bases), ", ".join(bases[:6]) or "(없음)"))
    if problems:
        for p in problems:
            print("[BUNDLE-API] 빨강 — %s" % p)
        return EXIT_RED
    print("[BUNDLE-API] 초록(곁길) — 파일 안에 API 밑동이 있다. "
          "서버가 그것을 내는지는 `--spa` 로 따로 물어야 한다")
    return EXIT_OK


def self_test() -> int:
    """판정 규칙만 문다 — 서버도 파일도 필요 없다."""
    E, S = "http://localhost:8000", "http://localhost:3002"

    #: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 **바로 그 번들** [실측 2026-09-18 · 턴 U].
    #:   조율자가 `/app/.env` 없이 지은 번들에서 실제로 뽑힌 주소 리터럴의 앞머리다.
    #:   `VITE_API_URL` 이 빈 문자열로 치환됐으므로 `http://localhost:8000` 은 **없고**,
    #:   대신 의존성 안의 문서 주소만 남았다. 이 표본이 **빨강**으로 판정되지 않으면
    #:   이 게이트는 태어난 이유를 못 보는 것이다 — 그날 V 의 측정 40분이 여기서 막혔다.
    BIRTH_SAMPLE = ["http://jedwatson.github.io", "https://react.dev",
                    "http://localhost", "https://redux.js.org", "https://bit.ly"]
    birth = judge(BIRTH_SAMPLE, S, E)
    ok = bool(birth) and not is_gray(birth)
    print("  %s ★ 출생 표본 — `.env` 없이 지은 그 번들(턴 U)은 빨강이어야 한다"
          % ("O" if ok else "X"))
    bad_birth = 0 if ok else 1

    cases = [
        ("밑동 0개면 빨강", judge([], S, E), True),
        ("기대 밑동이 있으면 초록", judge([E, S], S, E), False),
        ("기대 밑동이 없으면 빨강", judge(["http://localhost:9999"], S, E), True),
        ("포트가 다르면 다른 문이다 — 8000 기대에 8001 은 빨강",
         judge(["http://localhost:8001"], S, E), True),
        ("기대가 SPA 제 원점이면 빨강(빈 문자열과 구별 불가)", judge([S], S, S), True),
        ("★ 남의 문서 주소가 잔뜩 있어도 기대가 없으면 빨강 — 처음 규칙이 놓친 자리",
         judge(["https://react.dev", "https://redux.js.org", "http://jedwatson.github.io"],
               S, E), True),
    ]
    bad = bad_birth
    gray = judge(["http://localhost:8000"], "http://localhost:3002", "")
    ok = is_gray(gray)
    bad += 0 if ok else 1
    print("  %s 기대 밑동을 안 주면 초록이 아니라 회색" % ("O" if ok else "X"))
    for name, problems, want_red in cases:
        got_red = bool(problems)
        ok = got_red == want_red
        bad += 0 if ok else 1
        print("  %s %s" % ("O" if ok else "X", name))

    # 뽑아내기 — 지도·폰트 주소를 API 로 세면 안 된다
    picked = api_bases('a="https://dapi.kakao.com/v2";b="http://localhost:8000/api"')
    ok = picked == ["http://localhost:8000"]
    bad += 0 if ok else 1
    print("  %s 지도·폰트 주소는 밑동으로 세지 않는다 (뽑힌 것: %s)"
          % ("O" if ok else "X", picked))

    # 엔트리 뽑기 — 모듈 스크립트만
    got = entry_js_names(
        '<script src="/legacy.js"></script>'
        '<script type="module" crossorigin src="/assets/index-a.js"></script>')
    ok = got == ["/assets/index-a.js"]
    bad += 0 if ok else 1
    print("  %s 모듈 스크립트만 엔트리로 본다 (뽑힌 것: %s)" % ("O" if ok else "X", got))

    print("[SELF-TEST] %s" % ("전부 통과" if bad == 0 else "%d개 어긋남" % bad))
    return EXIT_OK if bad == 0 else EXIT_RED


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spa", default=DEFAULT_SPA)
    ap.add_argument("--dist", default="")
    ap.add_argument("--expect", default=os.environ.get("GX_EXPECT_API_BASE", ""))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--container", default=os.environ.get("GX_ROUTE_CONTAINER", "gx-shell"),
                    help="호스트에서 SPA 가 안 보이면 여기 안에서 다시 돈다")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.dist:
        return run_dist(Path(a.dist), a.expect)

    #: ★ **호스트에서 SPA 가 안 보이는 것이 이 저장소의 기본값이다** [실측 2026-09-18].
    #:   `gx-shell` 은 3002·8000 을 게시하지 않는다(`docker port gx-shell` 이 비어 있다).
    #:   위임 없이 두면 이 게이트는 호스트에서 **영원히 회색**이고, 영원히 회색인 게이트는
    #:   곧 꺼진다(D-353). 위임은 복사하지 않고 `verify_route_alive` 의 것을 **빌린다**
    #:   — 두 벌은 반드시 어긋난다(D-369).
    if not os.environ.get("GX_ROUTE_IN_CONTAINER") and a.container:
        code, _ = _get(a.spa.rstrip("/") + "/", timeout=3.0)
        if code == 0:
            from verify_route_alive import delegate_to_container
            print("[BUNDLE-API] 컨테이너 위임: %s (호스트에서 SPA 가 안 보인다)" % a.container)
            sys.stdout.flush()
            return delegate_to_container(
                a.container, None, script="verify_bundle_api_base.py",
                extra_args=["--spa", a.spa] + (["--expect", a.expect] if a.expect else []),
                extra_env=["GX_SPA_URL", "GX_EXPECT_API_BASE"])

    return run_live(a.spa, a.expect)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header
    #: [턴 AD · 차선 Q · P-107 MEASURED 배선] 머리글은 `--self-test`(호스트 · SPA 안
    #: 봄)에서도 찍혀야 한다 — 그래서 분모는 라이브 번들의 밑동 리터럴 수(그때만 안다)가
    #: 아니라 이 판정기가 **밑동으로 안 셀** 것으로 선언해 둔 허용 목록(`_NOT_API` ·
    #: 이 파일의 핵심 약점을 메운 자리 · 위 docstring ③)의 갯수를 쓴다(D-301 ·
    #: 지금 셌다). 라이브 밑동 개수는 `[BUNDLE-API]` 줄에 그대로 찍힌다.
    gate_header(__file__,
                measured=("기대한 API 밑동이 번들에 있는가 · SPA `/api/*` 404 — "
                         "**분모 %d개**(밑동으로 안 세는 허용 목록 `_NOT_API` · "
                         "지도·CDN·문서 주소 · 지금 셌다)" % len(_NOT_API)),
                target="%s (서는 SPA 가 내는 번들)" % DEFAULT_SPA,
                as_="자격 없음 — 익명으로 정적 파일을 읽는다",
                source="살아 있는 SPA 의 index.html 과 엔트리 JS (HTTP)")
    raise SystemExit(main())
