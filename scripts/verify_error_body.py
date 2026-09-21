#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-100 짝 게이트 — **5xx 본문이 내부를 싣고 나가는가** (2026-09-07 · 턴 L · 차선 Q).

    `verify_prod_settings` 는 「운영 프로필로 뜨면 닫혀 있는가」를 잰다.
    이 게이트는 그 앞의 질문을 잰다 — **지금 떠 있는 판이 오류를 낼 때
    본문에 무엇을 실어 보내는가.** 설정이 아니라 **나간 바이트**를 본다.

★ 출생 표본 (D-310) — BIRTH_SAMPLE
----------------------------------
P-100 은 「`GET /api/report-template` 권한 거절 → 500 + pydantic 역추적」 한 건으로
열렸다. 이 게이트를 세우고 **무인증 표본**을 떠 보니 그 한 건이 아니었다
[실측 2026-09-07 · `http://localhost:8000`]:

    GET /api/v1/health              (익명 · 머리글자 없음)      → 200        38 바이트
    GET /api/v1/health              Authorization: Bearer zzz   → **500  165,721 바이트**
    GET /api/cameras   (없는 경로)  Authorization: Bearer zzz   → **500  166,132 바이트**

  그 165KB 안에: `Traceback` 6 · `File "` 17 · `site-packages` 36 ·
  `/app/stream_monitors/media/images` · `INSTALLED_APPS` 전문 · 설정 표 전체
  (`Exception Location: /usr/local/lib/python3.11/site-packages/jwt…`).

  → **인증을 통과하지 못한 사람이 · 아무 라우트에나 · 망가진 토큰 한 줄로**
    장고 디버그 페이지를 받는다. **라우트가 없어도 받는다** — 그러므로 이것은
    한 라우트의 결함이 아니라 **URL 해석 앞단**의 결함이고, 그래서
    「그 라우트를 고쳤다」로는 닫히지 않는다.

이 표본이 아래 `self_test` 의 첫 갈래다. 여기서 초록이 나오면 이 파일은 도구가 아니다.

무엇을 재는가
-------------
  모수 : **살아 있는 라우터가 등록한 라우트 전수** (손 목록이 아니다 · P-99).
         컨테이너 안에서 `_iter_ninja_apis()` 로 뽑는다. 못 뽑으면 커밋된 사진으로
         물러서되 **그 사실을 적고 회색**을 낸다 — 낡은 사진 위의 초록은 눈이 먼
         초록이다(P-93).
  결   : **무인증 두 결.** 둘 다 「자격이 없는 사람」이 지금 당장 보낼 수 있는 것이다.
           ① `anon`      머리글자 없음
           ② `bad_token` `Authorization: Bearer <쓰레기>`   ← 출생 표본이 나온 결
  술어 : 상태 **5xx** 인 응답의 본문에 다음이 **한 번도** 나오지 않는다 —
           `Traceback` · `pydantic` · `File "` · **내부 파일 경로**
  색   : 빨강 = 5xx 본문에 표지 1건 이상
         회색 = 못 쟀다(컨테이너·라우터·요청 실패) **또는 5xx 를 한 번도 못 봤다**
                — 5xx 가 0건이면 술어는 「공백 참」이지 초록이 아니다(D-301)
         초록 = 5xx 를 **실제로 보았고** 그 본문 전부가 깨끗했다

★ **면제 칸이 없다** (D-327). 「이 라우트는 원래 그렇다」를 적는 자리를 만들지 않는다.
★ **쓰기 라우트에 쓰기를 보내지 않는다.** POST/PUT/PATCH/DELETE 자리에는 `OPTIONS`
  를 보내고 「대체」로 표시한다 — 그 메서드 자체는 **못 잰 것**이다. 무인증으로 남의
  자료를 바꾸는 것은 이 게이트의 일이 아니다(그 자리는 `verify_write_auth`).
  경로 매개변수는 **없는 id**(`999999999`)로 채운다 — 실재 id 로 두드리지 않는다.

    python scripts/verify_error_body.py               # 판정 (컨테이너에 위임)
    python scripts/verify_error_body.py --self-test   # 판정 규칙만 (요청 없이)
    python scripts/verify_error_body.py --list        # 유출 행 전부
    python scripts/verify_error_body.py --limit 40    # 표본을 줄여서 빨리
    python scripts/verify_error_body.py --json PATH   # 관측 저장

종료 코드: 0 초록 · 1 빨강(유출) · 2 회색(못 쟀다)
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[ERRBODY]"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent

#: 술어의 네 표지 — **P-100 이 적은 그대로**. 여기서 늘리지도 줄이지도 않는다.
#:   HTML 로 나오면 따옴표가 `&quot;` · `&#x27;` 로 바뀌므로 그 모양들을 함께 본다.
MARKERS: dict[str, str] = {
    "Traceback": r"Traceback",
    "pydantic": r"pydantic",
    "File \"": r"File (?:\"|&quot;|&#x27;|')",
    "내부경로": (r"(?:/app/|/repo/|/usr/local/lib/python|/usr/lib/python"
                r"|site-packages|[A-Za-z]:\\\\?(?:Users|GuardianX))"),
}

#: 5xx 가 아닌 본문의 유출은 **참고로만** 적는다 — P-100 의 술어는 5xx 다.
#:   참고를 판정에 섞으면 그것은 게이트를 내 맘대로 넓힌 것이다.
GATED_STATUS_MIN = 500

DEFAULT_API = "http://localhost:8000"
DEFAULT_CONTAINER = "gx-shell"

#: 무인증 두 결. 값은 Authorization 머리글자(또는 None).
LEGS: dict = {
    "anon": None,
    "bad_token": "Bearer gx-error-body-probe-not-a-real-token",
}

#: 쓰기 메서드에는 이것을 대신 보낸다. 안전한 쪽 · 되돌릴 것이 없는 쪽.
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
SUBSTITUTE = "OPTIONS"


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 순수 함수. **이 함수 하나가 정본이다** (D-212).
#        탐침(컨테이너 안)은 이 함수의 **원문을 그대로 실어 간다** — 사본을 만들지 않는다.
# ═══════════════════════════════════════════════════════════════════════════

def scan_body(text, markers):
    """본문에서 표지를 찾아 [(이름, 첫 조각)] 로 돌려준다."""
    hits = []
    for name, pattern in markers.items():
        m = re.search(pattern, text)
        if m:
            i = max(0, m.start() - 40)
            hits.append([name, text[i:m.end() + 80].replace("\n", " ")])
    return hits


def fill_path(path: str) -> str:
    """경로 매개변수를 **없는 id** 로 채운다. 실재 id 로 쓰기 경로를 두드리지 않는다."""
    def one(m):
        name = m.group(1)
        if "uuid" in name or name.endswith("uid"):
            return "00000000-0000-0000-0000-000000000000"
        return "999999999"
    return re.sub(r"\{([^}]*)\}", one, path)


def sample_plan(routes: list, legs: dict) -> list:
    """모수 → 표본. 쓰기 메서드는 `OPTIONS` 로 **대체**하고 그렇게 표시한다."""
    plan = []
    for r in routes:
        method = (r.get("method") or "GET").upper()
        sent = SUBSTITUTE if method in WRITE_METHODS else method
        for leg in legs:
            plan.append({"method": method, "sent_method": sent,
                         "substituted": sent != method,
                         "path": r.get("path", ""),
                         "url_path": fill_path(r.get("path", "")),
                         "leg": leg})
    return plan


def judge(rows: list, meta: dict):
    """관측 → (색, 빨강 사유, 회색 사유, 셈). **면제 칸 없음** (D-327)."""
    red = []
    gray = []

    n = len(rows)
    errored = [r for r in rows if r.get("status") is None]
    fivexx = [r for r in rows
              if isinstance(r.get("status"), int) and r["status"] >= GATED_STATUS_MIN]
    leaks = [r for r in fivexx if r.get("markers")]
    other_leaks = [r for r in rows
                   if r.get("markers") and not (isinstance(r.get("status"), int)
                                                and r["status"] >= GATED_STATUS_MIN)]

    counts = {
        "sampled": n,
        "unreached": len(errored),
        "five_xx": len(fivexx),
        "leaking_5xx": len(leaks),
        "leaking_other": len(other_leaks),
        "substituted": sum(1 for r in rows if r.get("substituted")),
        "routes": meta.get("routes", 0),
        "source": meta.get("source", ""),
    }

    if n == 0:
        gray.append("표본이 0건이다 — 아무것도 재지 않았다")
        return "회색", red, gray, counts

    if meta.get("source") != "live-router":
        gray.append("모수를 **살아 있는 라우터에서 못 뽑았다**(출처=%r) — 게이트의 분모는 "
                    "손으로 적지 않는다(P-99). 이 표본의 라우트 수를 믿지 말 것"
                    % meta.get("source"))

    if errored:
        gray.append("응답을 못 받은 자리 %d건(연결·시간초과) — 그 자리는 **모른다**이지 "
                    "「깨끗하다」가 아니다" % len(errored))

    for r in leaks:
        red.append("%s %s [%s] → %d · 표지 %s"
                   % (r.get("method"), r.get("path"), r.get("leg"), r["status"],
                      "·".join(str(m[0]) for m in r["markers"])))

    if red:
        return "빨강", red, gray, counts

    if not fivexx:
        gray.append("이 표본이 **5xx 를 한 번도 못 봤다** — 술어가 시험되지 않았다"
                    "(공백 참). 5xx 0건은 초록이 아니다(D-301)")
        return "회색", red, gray, counts

    if gray:
        return "회색", red, gray, counts
    return "초록", red, gray, counts


# ═══════════════════════════════════════════════════════════════════════════
# 탐침 — 컨테이너 안에서 돈다. `scan_body` 의 **원문을 실어 간다**(사본 금지)
# ═══════════════════════════════════════════════════════════════════════════

PROBE_TEMPLATE = r'''# -*- coding: utf-8 -*-
import json, os, re, sys, urllib.request, urllib.error

MARKERS = json.loads(os.environ["GX_EB_MARKERS"])
LEGS = json.loads(os.environ["GX_EB_LEGS"])
API = os.environ.get("GX_EB_API", "http://localhost:8000")
PLAN = json.loads(sys.stdin.read())
MAXBYTES = 600000

%(scan_src)s


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)

out = []
for item in PLAN:
    url = API + item["url_path"]
    hdrs = {"Accept": "*/*"}
    authn_header = LEGS.get(item["leg"])
    if authn_header:
        hdrs["Authorization"] = authn_header
    req = urllib.request.Request(url, method=item["sent_method"], headers=hdrs)
    row = dict(item)
    try:
        r = opener.open(req, timeout=15)
        body, status = r.read(MAXBYTES), r.status
    except urllib.error.HTTPError as e:
        body, status = e.read(MAXBYTES), e.code
    except Exception as e:
        row.update(status=None, length=0, markers=[], error=repr(e)[:160])
        out.append(row)
        continue
    text = body.decode("utf-8", "replace")
    row.update(status=status, length=len(body), error=None,
               markers=scan_body(text, MARKERS))
    out.append(row)

sys.stdout.write("GXERRBODY " + json.dumps(out, ensure_ascii=False) + "\n")
'''

ROUTES_TEMPLATE = r'''# -*- coding: utf-8 -*-
import json, os, sys
sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from common.tenant_scope import _iter_ninja_apis, _join
rows = []
for mount, api in _iter_ninja_apis():
    for prefix, router in getattr(api, "_routers", []) or []:
        for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
            for op in getattr(path_view, "operations", []) or []:
                path = _join(mount, prefix, op_path)
                for m in getattr(op, "methods", []) or []:
                    rows.append({"method": m, "path": path})
sys.stdout.write("GXROUTES " + json.dumps({"routes": rows}, ensure_ascii=False) + "\n")
'''


def _probe_source() -> str:
    return PROBE_TEMPLATE % {"scan_src": inspect.getsource(scan_body)}


def _extract(out: str, tag: str):
    for line in (out or "").splitlines():
        if line.startswith(tag + " "):
            return json.loads(line[len(tag) + 1:])
    return None


def _put_script(container: str, remote: str, src: str) -> str:
    put = subprocess.run(["docker", "exec", "-i", container, "sh", "-c", "cat > " + remote],
                         input=src.encode("utf-8"),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if put.returncode != 0:
        return (put.stderr or b"").decode("utf-8", "replace")[-300:] or "docker exec 실패"
    return ""


def _run_script(container: str, remote: str, env: dict, stdin: str, timeout: int):
    cmd = ["docker", "exec", "-i"]
    for k, v in env.items():
        cmd += ["-e", "%s=%s" % (k, v)]
    cmd += [container, "python", remote]
    try:
        proc = subprocess.run(cmd, input=stdin.encode("utf-8"), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return "", "docker 를 못 불렀다: %r" % (exc,)
    return (proc.stdout.decode("utf-8", "replace"),
            (proc.stderr or b"").decode("utf-8", "replace")[-600:])


def collect_routes(container: str):
    """모수 — **살아 있는 라우터**에서 뽑는다. 못 뽑으면 사진으로 물러서되 그렇게 적는다."""
    remote = "/tmp/gx_verify_error_body_routes.py"
    err = _put_script(container, remote, ROUTES_TEMPLATE)
    if not err:
        out, err = _run_script(container, remote, {"PYTHONIOENCODING": "utf-8"}, "", 600)
        got = _extract(out, "GXROUTES")
        if got and got.get("routes"):
            return got["routes"], "live-router", ""
    snap = ROOT / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"
    if snap.is_file():
        data = json.loads(snap.read_text(encoding="utf-8"))
        return ([{"method": r["method"], "path": r["path"]} for r in data.get("routes", [])],
                "snapshot:%s" % snap.name, err)
    return [], "none", err


def run_probe(container: str, api: str, plan: list, timeout: int = 3600):
    remote = "/tmp/gx_verify_error_body_probe.py"
    err = _put_script(container, remote, _probe_source())
    if err:
        return [], "탐침을 컨테이너에 못 넣었다: %s" % err
    out, err = _run_script(container, remote,
                           {"PYTHONIOENCODING": "utf-8",
                            "GX_EB_API": api,
                            "GX_EB_MARKERS": json.dumps(MARKERS, ensure_ascii=False),
                            "GX_EB_LEGS": json.dumps(LEGS, ensure_ascii=False)},
                           json.dumps(plan, ensure_ascii=False), timeout)
    got = _extract(out, "GXERRBODY")
    if got is None:
        return [], err or "탐침이 답을 안 냈다"
    return got, ""


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 출생 표본이 첫 갈래다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

BIRTH_SAMPLE = (
    "<!DOCTYPE html><html><head><title>DecodeError at /api/v1/health</title></head>"
    "<body><h1>DecodeError at /api/v1/health</h1>"
    "<th>Exception Location:</th>"
    "<td>/usr/local/lib/python3.11/site-packages/jwt/api_jws.py</td>"
    "<h2>Traceback <span>Switch to copy-and-paste view</span></h2>"
    "<li>File &quot;/app/common/middleware.py&quot;, line 42, in __call__</li>"
    "<td>IMG_DIR</td><td>&#x27;/app/stream_monitors/media/images&#x27;</td></body></html>"
)

CLEAN_SAMPLE = '{"success": false, "status_code": 500, "message": "서버 오류"}'


def self_test(verbose: bool = True) -> int:
    cases = []

    def ok(name, cond):
        cases.append((name, bool(cond)))

    # ── ★ 출생 표본 — 165KB 디버그 페이지는 표지로 잡힌다 ─────────────────────
    hits = dict((h[0], h[1]) for h in scan_body(BIRTH_SAMPLE, MARKERS))
    ok("★ 출생 표본 · `Traceback` 을 잡는다", "Traceback" in hits)
    ok("★ 출생 표본 · `File \"`(HTML 이스케이프 포함)를 잡는다", "File \"" in hits)
    ok("★ 출생 표본 · 내부 경로(/app/ · site-packages)를 잡는다", "내부경로" in hits)
    color, red, _, _ = judge(
        [{"method": "GET", "path": "/api/v1/health", "leg": "bad_token",
          "status": 500, "markers": [[k, v] for k, v in hits.items()]}],
        {"routes": 1, "source": "live-router"})
    ok("★ 출생 표본 · 판정이 **빨강**이다", color == "빨강")
    ok("★ 출생 표본 · 빨강 사유에 경로와 결이 적힌다",
       any("/api/v1/health" in x and "bad_token" in x for x in red))

    # ── pydantic 표지 (P-100 이 열린 그 문장) ────────────────────────────────
    ok("`pydantic` 표지를 잡는다",
       any(h[0] == "pydantic"
           for h in scan_body("pydantic_core._pydantic_core.ValidationError", MARKERS)))

    # ── 음성 ① — 깨끗한 5xx 본문은 초록 ──────────────────────────────────────
    ok("음성 · 봉투만 있는 500 본문은 표지 0", not scan_body(CLEAN_SAMPLE, MARKERS))
    c1, _, _, cnt1 = judge(
        [{"method": "GET", "path": "/a", "leg": "anon", "status": 500, "markers": []},
         {"method": "GET", "path": "/a", "leg": "bad_token", "status": 401, "markers": []}],
        {"routes": 1, "source": "live-router"})
    ok("음성 · 깨끗한 5xx 를 보면 초록", c1 == "초록" and cnt1["five_xx"] == 1)

    # ── 음성 ② — 5xx 를 한 번도 못 보면 **회색**(공백 참을 초록으로 안 낸다) ──
    c2, _, g2, _ = judge([{"method": "GET", "path": "/a", "leg": "anon",
                           "status": 401, "markers": []}],
                         {"routes": 1, "source": "live-router"})
    ok("음성 · 5xx 0건이면 회색이지 초록이 아니다",
       c2 == "회색" and any("공백 참" in x for x in g2))

    # ── 음성 ③ — 모수가 살아 있는 라우터가 아니면 회색 (P-99) ────────────────
    c3, _, g3, _ = judge([{"method": "GET", "path": "/a", "leg": "anon",
                           "status": 500, "markers": []}],
                         {"routes": 1, "source": "snapshot:route_inventory.json"})
    ok("음성 · 사진으로 뽑은 분모면 회색",
       c3 == "회색" and any("손으로 적지 않는다" in x for x in g3))

    # ── 음성 ④ — 응답을 못 받은 자리는 「깨끗하다」가 아니다 ──────────────────
    c4, _, g4, _ = judge([{"method": "GET", "path": "/a", "leg": "anon",
                           "status": None, "markers": []},
                          {"method": "GET", "path": "/b", "leg": "anon",
                           "status": 500, "markers": []}],
                         {"routes": 2, "source": "live-router"})
    ok("음성 · 못 받은 응답 1건이면 회색", c4 == "회색" and any("모른다" in x for x in g4))

    # ── 음성 ⑤ — 5xx 아닌 유출은 빨강을 만들지 않는다(참고로만) ──────────────
    c5, r5, _, cnt5 = judge([{"method": "GET", "path": "/a", "leg": "anon",
                              "status": 404, "markers": [["Traceback", "..."]]},
                             {"method": "GET", "path": "/b", "leg": "anon",
                              "status": 500, "markers": []}],
                            {"routes": 2, "source": "live-router"})
    ok("음성 · 404 본문의 유출은 참고이지 빨강이 아니다",
       c5 == "초록" and not r5 and cnt5["leaking_other"] == 1)

    # ── 표본 계획 — 쓰기에 쓰기를 보내지 않는다 · 없는 id 로 채운다 ──────────
    plan = sample_plan([{"method": "DELETE", "path": "/api/x/{id}"},
                        {"method": "GET", "path": "/api/y"}], LEGS)
    ok("쓰기 라우트에 OPTIONS 를 대신 보낸다",
       all(p["sent_method"] == "OPTIONS" and p["substituted"]
           for p in plan if p["method"] == "DELETE"))
    ok("경로 매개변수를 **없는 id** 로 채운다",
       all(p["url_path"] == "/api/x/999999999" for p in plan if p["method"] == "DELETE"))
    ok("결이 둘이므로 표본은 라우트의 두 배", len(plan) == 4)
    ok("uuid 자리는 0-uuid 로 채운다",
       fill_path("/api/z/{device_uuid}") == "/api/z/00000000-0000-0000-0000-000000000000")

    # ── 탐침이 술어의 **사본**을 만들지 않는다 ───────────────────────────────
    ok("탐침이 `scan_body` 원문을 그대로 실어 간다", "def scan_body" in _probe_source())

    fails = [n for n, g in cases if not g]
    if verbose or fails:
        for name, good in cases:
            if verbose or not good:
                print("  %-4s %s" % ("OK" if good else "FAIL", name))
    if fails:
        print("%s 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)" % (TAG, len(fails)))
        return EXIT_FAIL
    print("%s 자기시험 %d건 통과 — ★ 출생 표본 6 · 음성 대조 6" % (TAG, len(cases)))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# P-221 · 턴 AA — **오류 본문 사전** (2026-09-21 · 차선 Q)
#
# 위의 술어는 **서버가 새는 것**을 잰다(5xx 본문의 `Traceback`). 세종이 이 턴에
# 지목한 것은 그 반대편이다 — **서버가 안 새는데 화면이 우리 사정을 적어 둔 자리.**
#
#     「서버가 404 를 냈습니다」   정직하다. 그러나 **고객 말이 아니다.**
#     「나에게 온 것만 못 골라 줍니다」   우리 사정을 사과로 내민 것이다.
#     「장애 신고 창구 미등록」   ★ **우리 회색을 고객 발치에 적어 둔 것**이다(세종 관찰).
#                                 창구 번호가 오면 그때 뜬다. 오기 전에는 그 줄이 없어야 한다.
#
# ★★ **두 벌을 두지 않는다** (D-369). 그 사전의 구현은 `verify_ui_copy` 에 있고,
#   여기서는 그것을 **부른다**. 여기에 정규식을 한 벌 더 두면 둘은 반드시 어긋나고,
#   어긋나면 한쪽이 조용히 아무것도 안 본다 — 이 저장소가 거듭 만난 실패 모양이다.
#   그래서 이 갈래가 하는 일은 셋이다: **부르고 · 오류 무리만 골라내고 · 색을 낸다.**
# ═══════════════════════════════════════════════════════════════════════════

#: 이 갈래가 보는 무리. `verify_ui_copy.HANGUL_ONLY_PATTERNS` 의 **이름**이다 —
#: 정규식이 아니라 이름을 적는 것이 요점이다(저쪽이 고쳐지면 여기가 따라간다).
COPY_GROUPS = ("상태 코드 숫자", "우리 사정", "빈 값 표시", "영문 오류 원문")


def copy_scan():
    """화면 소스에서 **오류 본문 사전**에 걸린 자리를 되돌린다.

    `(걸린 자리, 본 파일 수, 못 부른 사유)` — 못 부르면 **회색**이다. 0건이 아니다.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import verify_ui_copy as copy_gate
    except Exception as exc:                                    # noqa: BLE001
        return [], 0, "`verify_ui_copy` 를 못 불렀다: %s" % exc
    missing = [g for g in COPY_GROUPS
               if g not in {n for n, _ in copy_gate.HANGUL_ONLY_PATTERNS}]
    if missing:
        #: ★ 저쪽의 이름이 바뀌었는데 여기가 안 따라간 자리. **조용히 0건이 되는**
        #:   자리이고, 그래서 색을 내지 않고 사유를 낸다.
        return [], 0, ("`verify_ui_copy` 에 무리 %s 가 없다 — 이름이 갈렸다. "
                       "두 파일을 **같은 커밋에서** 고친다" % " · ".join(missing))
    #: ⚠ [실측 2026-09-21 · 턴 AB] `verify_ui_copy.scan()` 이 다섯 번째 값
    #:   (**선언으로 건너뛴 조각 수**)을 내게 되면서 이 줄이 `ValueError` 로 죽었다.
    #:   ★ **죽은 것이 옳다** — 조용히 네 개만 받았으면 이 게이트가 다른 표를 읽은
    #:     줄도 모르고 초록을 냈을 것이다(손으로 적은 분모가 거짓 초록을 내는 것과
    #:     같은 모양 · P-204). 그래서 개수를 고정하지 않고 **앞 넷만** 집는다.
    _got = copy_gate.scan()
    seen, findings, _cov, _tot = _got[0], _got[1], _got[2], _got[3]
    rows = [f for f in findings if f[2] in COPY_GROUPS]
    return rows, seen, ""


def copy_main(list_all: bool = False) -> int:
    """오류 본문 사전 — **고객 화면에 우리 사정이 적혀 있는가.**"""
    rows, seen, why = copy_scan()
    if why:
        print("%s ? **못 쟀다** — %s" % (TAG, why))
        return EXIT_UNDECIDABLE
    if not seen:
        #: 분모 0인 초록은 초록이 아니다 (D-301). 파일을 하나도 못 열었으면 회색.
        print("%s ? **못 쟀다** — 화면 파일을 한 개도 못 열었다. 분모 0인 초록은 "
              "초록이 아니다 (D-301)" % TAG)
        return EXIT_UNDECIDABLE
    print("%s [입력] 화면 파일 **%d개** × 오류 본문 무리 **%d종**(%s) — 걸린 자리 %d건"
          % (TAG, seen, len(COPY_GROUPS), " · ".join(COPY_GROUPS), len(rows)))
    if rows and list_all:
        for rel, line, name, snip in rows:
            print("%s   X %s:%d  [%s]  %s" % (TAG, rel, line, name, snip[:110]))
    if rows:
        by = {}
        for _r, _l, name, _s in rows:
            by[name] = by.get(name, 0) + 1
        print("%s X **빨강** — 고객 화면에 우리 사정이 %d자리 있다 (%s). "
              "**정직한 회색을 고객 말로** — 원인과 다음 손을 같은 줄에. "
              "★ 실제 값(창구 번호·주소)이 없는 문구는 **비표시**다"
              % (TAG, len(rows), " · ".join("%s %d" % kv for kv in sorted(by.items()))))
        if not list_all:
            print("%s   (자리 전부: `python scripts/verify_error_body.py --copy --list`)"
                  % TAG)
        return EXIT_FAIL
    print("%s O 화면 파일 %d개에 오류 본문 사전 위반 **0건** — 분모가 실재한다" % (TAG, seen))
    return EXIT_OK


def copy_self_test(verbose: bool = True) -> int:
    """★ **출생 표본**. 새 게이트에는 자기시험을 반드시 붙인다.

    턴 Z 에 `verify_classification` 이 **자기시험이 아예 없어서** 칸 이름을
    동사로 읽는 오독이 오래 살았다. 그 값을 치르고 배운 것이 이 함수다.
    """
    cases = []

    def ok(name, cond):
        cases.append((name, bool(cond)))

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import verify_ui_copy as g
    except Exception as exc:                                    # noqa: BLE001
        print("%s 자기시험 **회색** — `verify_ui_copy` 를 못 불렀다: %s" % (TAG, exc))
        return EXIT_UNDECIDABLE

    names = {n for n, _ in g.HANGUL_ONLY_PATTERNS}
    ok("★ 네 무리의 **이름**이 저쪽에 실재한다 (갈리면 조용히 0건이 된다)",
       all(x in names for x in COPY_GROUPS))
    # ── 양성 — 세종이 이름으로 지목한 셋 ──────────────────────────────────
    ok("★ 출생 표본 · 「서버가 404」를 잡는다",
       "상태 코드 숫자" in g.scan_line_aa("서버가 404 를 냈습니다"))
    ok("★ 출생 표본 · 「못 골라 줍니다」를 잡는다",
       "우리 사정" in g.scan_line_aa("나에게 온 것만 못 골라 줍니다"))
    ok("★★ 출생 표본 · 「장애 신고 창구 미등록」을 잡는다 — **실제 값이 없는 문구는 비표시**",
       "빈 값 표시" in g.scan_line_aa("장애 신고 창구 미등록"))
    ok("★ 출생 표본 · 한글 문장에 섞인 영문 원문을 잡는다",
       "영문 오류 원문" in g.scan_line_aa("알림을 보내지 못했습니다 (Network Error)"))
    # ── 음성 — 고쳐 쓴 말과 **코드**는 잡히면 안 된다 ──────────────────────
    ok("★ 음성 · 원인과 다음 손이 같은 줄에 있으면 안 잡는다",
       not g.scan_line_aa("사진을 불러오지 못했습니다. 잠시 뒤 다시 시도해 보십시오."))
    ok("★ 음성 · 창구 번호가 **실제로 있으면** 안 잡는다",
       not g.scan_line_aa("장애 신고 창구 02-000-0000 으로 연락해 주십시오."))
    ok("★ 음성 · 장비 수·건수의 숫자를 상태 코드로 읽지 않는다",
       "상태 코드 숫자" not in g.scan_line_aa("카메라 404 대가 붙어 있습니다"))
    ok("★ 음성 · **방어선을 결함으로 읽지 않는다**(버리려고 적어 둔 영문 목록)",
       not g.scan_line_aa("'Network Error',"))
    ok("★ 음성 · 한글 없는 코드는 화면이 아니다",
       not g.scan_line_aa("if (err.code === 404) return null;"))

    bad = [n for n, good in cases if not good]
    if verbose or bad:
        for name, good in cases:
            if verbose or not good:
                print("%s   %-4s %s" % (TAG, "OK" if good else "FAIL", name))
    if bad:
        print("%s 오류 본문 사전 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)"
              % (TAG, len(bad)))
        return EXIT_FAIL
    print("%s 오류 본문 사전 자기시험 %d건 통과 — 양성 5(출생 표본) · 음성 5"
          % (TAG, len(cases)))
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="5xx 본문이 내부를 싣고 나가는가 (P-100)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true", help="유출 행 전부")
    ap.add_argument("--limit", type=int, default=0, help="라우트 표본 상한(0=전수)")
    ap.add_argument("--api", default=os.environ.get("GX_API", DEFAULT_API))
    ap.add_argument("--container",
                    default=os.environ.get("GX_SHELL_CONTAINER", DEFAULT_CONTAINER))
    ap.add_argument("--json", default="", help="관측을 저장할 경로")
    ap.add_argument("--copy", action="store_true",
                    help="★ **오류 본문 사전** — 고객 화면에 우리 사정이 적혔는가 (P-221)")
    args = ap.parse_args()

    if args.copy:
        #: 두 갈래는 **다른 것을 잰다.** 서버가 새는가(기본) ↔ 화면이 우리 사정을
        #: 적어 두는가(`--copy`). 한 색으로 뭉치면 어느 쪽이 빨간지 모른다.
        rc = copy_self_test(verbose=False)
        if rc != EXIT_OK:
            print("%s 오류 본문 사전 자기시험이 초록이 아니다 — 판정을 신뢰할 수 없다" % TAG)
            return rc
        return copy_main(list_all=args.list)

    if args.self_test:
        rc = copy_self_test()
        if rc != EXIT_OK:
            return rc
        return self_test()

    if self_test(verbose=False) != EXIT_OK:
        print("%s 자기시험이 빨강이다 — 판정을 신뢰할 수 없다" % TAG)
        return EXIT_FAIL

    routes, source, err = collect_routes(args.container)
    if not routes:
        print("%s ? **못 쟀다** — 라우트를 하나도 못 뽑았다. %s" % (TAG, err[:300]))
        return EXIT_UNDECIDABLE
    if args.limit:
        routes = routes[:args.limit]

    plan = sample_plan(routes, LEGS)
    print("%s [입력] 모수 라우트 **%d건**(출처 %s) × 무인증 결 **%d**(%s) = 표본 **%d건** · "
          "대상 %s · 쓰기 %d건은 `OPTIONS` 대체(그 메서드 자체는 못 잰 것)"
          % (TAG, len(routes), source, len(LEGS), " · ".join(LEGS), len(plan), args.api,
             sum(1 for p in plan if p["substituted"])))
    print("%s [술어] 5xx 본문에 %s 가 **0회** — 면제 칸 없음(D-327)"
          % (TAG, " · ".join("`%s`" % k for k in MARKERS)))

    rows, perr = run_probe(args.container, args.api, plan)
    if not rows:
        print("%s ? **못 쟀다** — 탐침이 답을 안 냈다: %s" % (TAG, perr[:400]))
        return EXIT_UNDECIDABLE

    color, red, gray, counts = judge(rows, {"routes": len(routes), "source": source})

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"api": args.api, "source": source, "counts": counts, "color": color,
             "markers": MARKERS, "legs": list(LEGS), "rows": rows},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("%s 관측 저장: %s" % (TAG, args.json))

    print("%s 표본 %d · 응답 못 받음 %d · **5xx %d** · 그중 유출 **%d** · "
          "5xx 아닌 본문의 유출 %d(참고)"
          % (TAG, counts["sampled"], counts["unreached"], counts["five_xx"],
             counts["leaking_5xx"], counts["leaking_other"]))

    shown = red if args.list else red[:12]
    for line in shown:
        print("%s X %s" % (TAG, line))
    if len(red) > len(shown):
        print("%s   ... 그리고 %d건 더 (`--list`)" % (TAG, len(red) - len(shown)))
    for g in gray:
        print("%s ? %s" % (TAG, g))

    if color == "빨강":
        first = next((r for r in rows
                      if isinstance(r.get("status"), int) and r["status"] >= 500
                      and r.get("markers")), None)
        if first:
            print("%s   첫 조각: %s" % (TAG, str(first["markers"][0][1])[:200]))
        print("%s **빨강(exit 1)** — 자격 없는 사람에게 5xx 본문이 내부를 실어 보낸다. "
              "이 하나가 열려 있으면 다른 500 도 다 말한다 (P-100)" % TAG)
        return EXIT_FAIL
    if color == "회색":
        print("%s **회색(exit 2)** — 회색은 초록이 아니다 (D-301)" % TAG)
        return EXIT_UNDECIDABLE
    print("%s **초록(exit 0)** — 5xx %d건을 실제로 보았고 본문에 표지 0"
          % (TAG, counts["five_xx"]))
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    #: ★ 두 갈래는 **다른 것을 재고, 그래서 분모가 다르다.** 한 줄로 뭉치면
    #:   그 머리글은 둘 중 어느 쪽도 말하지 않은 것이 된다(거짓 분모의 한 모양).
    if "--copy" in sys.argv:
        _rows, _seen, _why = copy_scan()
        gate_header(
            __file__,
            measured=("**오류 본문 사전** — 고객 화면에 우리 사정이 적혔는가. "
                      "화면 파일 **분모 %d개**(지금 셌다) × 무리 %d종(%s). "
                      "★ 실제 값이 없는 문구는 **비표시**다 — 「장애 신고 창구 미등록」은 "
                      "우리 회색을 고객 발치에 적어 둔 것이다"
                      % (_seen, len(COPY_GROUPS), " · ".join(COPY_GROUPS))),
            target="이 저장소의 화면 소스 (frontend/src) — 서버가 아니다",
            as_="(자격증명 없음 — 소스를 읽는다)",
            source="화면 소스 전수(주석은 걷어낸다) · 사전의 구현은 "
                   "`verify_ui_copy` 에 있고 여기서는 그것을 **부른다**(D-369)",
        )
        raise SystemExit(main())
    gate_header(
        __file__,
        #: ⚠ 분모는 **살아 있는 라우터가 등록한 라우트 전수**이고 머리글 시점에는
        #:   아직 모른다(컨테이너를 불러야 안다). 그래서 여기서는 **무엇을 분모로
        #:   삼는지**와 결의 수를 말하고, 실제 수는 `[입력]` 줄이 낸다 —
        #:   못 뽑으면 그 실행은 **회색(exit 2)** 이고 초록이 아니다.
        measured=("5xx 본문이 내부를 싣고 나가는가 — 모수는 **살아 있는 라우터가 등록한 "
                  "라우트 전수**(손 목록이 아니다 · P-99) × 무인증 **분모 %d결**"
                  "(익명 · 망가진 토큰). 라우트를 하나도 못 뽑으면 **회색**이고, "
                  "5xx 를 한 번도 못 보면 그 술어는 공백 참이지 초록이 아니다 (D-301)"
                  % len(LEGS)),
        target=os.environ.get("GX_API", "http://localhost:8000") + " (gx-shell 안 · 호스트에 포트가 없다)",
        as_="익명 · 그리고 `Authorization: Bearer <쓰레기>` — **자격이 없는 쪽이 재는 대상이다**(출생 표본: 그 머리글자 하나로 705/705 라우트가 165KB 디버그 전문을 냈다)",
        source="살아 있는 서버 응답 (HTTP) — 사진도 손 목록도 아니다",
    )
    raise SystemExit(main())
