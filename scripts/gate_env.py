# -*- coding: utf-8 -*-
"""P-70 — **게이트가 환경의 사실과 제품의 사실을 스스로 가른다** (2026-09-06 · 턴 G · 차선 S).

무엇을 막는가 — **게이트 여섯이 유령 파일 953개를 훑고 있었다**
---------------------------------------------------------------
[실측 2026-09-05 · 턴 F · `docs/agent/evidence/P-55/window_20260905_2247.md`]
`gx-shell` 의 `/repo/frontend` 는 마운트가 아니라 **사본**이었다. 그 사본에는
파일이 **1,956개** 있었고 호스트 저장소의 실제 프런트는 **1,003개**였다.
**953개가 저장소에 없는 유령**이었고, 컨테이너 안에서 도는 게이트 여섯
(`verify_ui_secrets` · `verify_ui_copy` · `verify_wall_keys` · `verify_post_arg_style` ·
`scan_frontend_success_contract` · `verify_bundle_hash`)이 그것을 훑고 있었다.

그때 나온 색은 **제품의 색이 아니었다.** 환경이 어긋나 있었고, 게이트는 그 사실을
말할 낱말이 없어서 제품의 결함처럼 보이는 색을 냈다. 이 파일이 그 낱말이다.

    제품의 사실 : 빨강(exit 1) — 코드가 규칙을 어겼다
    환경의 사실 : **회색(exit 2) + 사유 = 환경 이름** — 잴 자리가 없었다

★ **회색은 초록이 아니다** (D-301). 그러나 **빨강도 아니다** — 둘을 섞으면
  「환경을 세우면 사라지는 빨강」이 쌓이고, 그런 빨강을 몇 번 본 사람은 게이트를 끈다
  (D-353). 꺼진 게이트는 아무것도 안 지킨다.

무엇을 재는가 — 넷
------------------
  ``minio``    MinIO 도달 — 컨테이너가 떠 있는가 · 9000 이 health 를 내는가
  ``smtp``     SMTP 수신함(mailpit) 도달 — 발송→도착을 기계로 볼 수 있는가
  ``mount``    **마운트 일치** — 호스트가 세는 파일 수 = 컨테이너가 보는 파일 수
               (유령 953의 뿌리. 컨테이너가 아예 없으면 위임 경로도 없으므로 해당 없음)
  ``session``  세션 점유자 — **동시 접속 1**(UX-24 · §0.4 자료구조)이라 누가 쥐고
               있으면 게이트가 로그인하는 순간 남의 화면이 죽는다. 쥔 사람을 이름으로 말한다

쓰는 법
-------
    python scripts/gate_env.py --self-test
    python scripts/gate_env.py                          # 넷 다 재서 표로
    python scripts/gate_env.py --require mount minio    # 필요한 것만 판정
    python scripts/gate_env.py --require mount --json docs/agent/evidence/P-70/env.json

종료 코드: **0 필요한 환경이 다 있다 · 2 빠진 환경이 있다(회색)**.
이 파일은 **1(빨강)을 내지 않는다** — 환경은 제품이 아니다.

★ 공통 코드는 여기 한 곳에 둔다. 열두 게이트에 복붙하면 열두 벌이 서로 달라지고,
  달라진 판정식 복사본 하나가 D-212 였다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EXIT_OK, EXIT_GRAY = 0, 2
OK, MISSING, NA = "ok", "missing", "na"
TAG = "[ENV]"
ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 캐시 수명(초). 열두 게이트가 각자 재면 열두 번 도는데, 그 사이 환경이 바뀌는 일은
#: 드물다. 다만 **잰 시각을 늘 함께 낸다** — 오래된 사실을 새 사실처럼 읽지 않게.
CACHE_TTL = 180
CACHE_PATH = Path(os.environ.get("GX_ENV_CACHE") or
                  (Path(os.environ.get("TEMP") or "/tmp") / "gx_gate_env.json"))

MINIO_CONTAINER = os.environ.get("GX_MINIO_CONTAINER", "guardianx-source-minio-1")
MINIO_HEALTH = os.environ.get("GX_MINIO_HEALTH", "http://localhost:9000/minio/health/live")
#: mailpit 은 차선 E 가 세우는 중이다(P-68). 없으면 **없다**고 회색으로 말한다 —
#: 「없는 것」과 「봤는데 비었다」는 다른 사실이다.
SMTP_API = os.environ.get("GX_SMTP_API", "http://localhost:8025/api/v1/messages?limit=1")
#: 인증 문의 주소. ⚠ `.env.gates` 의 `GX_API` 는 **컨테이너 안에서 본 주소**
#: (`http://localhost:8000` = gx-shell 의 runserver)라서 호스트에서는 닿지 않는다.
#: 그래서 후보를 순서대로 두드리고 **닿는 첫 자리**를 쓴다 — 닿지 않는 주소 하나로
#: 「세션을 못 쟀다」를 내면 그것은 환경의 사실이 아니라 **주소를 틀린 것**이다.
API_BASES = [b for b in (os.environ.get("GX_API_PUBLIC"),
                         os.environ.get("GX_API"),
                         "http://localhost:8500",
                         "http://localhost:8000") if b]
#: **차선 이름 다섯** 중 탐침 계정(P-70). 차선마다 다른 사람이라야 동시 접속 1의
#: 세션 빼앗김이 원천에서 없어진다 — `GX_LANE=s` → `gxprobe_s`.
LANE = (os.environ.get("GX_LANE") or "").strip().lower()
PROBE_USER = (os.environ.get("GX_PROBE_USER")
              or (f"gxprobe_{LANE}" if LANE else "")).strip()
PROBE_PASSWORD = os.environ.get("GX_PROBE_PASSWORD", "")

#: **마운트 일치**를 재는 짝. (이름, 호스트 상대경로, 컨테이너, 컨테이너 경로)
#: 유령 953 이 나온 자리(`gx-shell:/repo/frontend`)가 첫 줄에 있다.
MOUNT_PAIRS = (
    ("frontend", "frontend", "gx-shell", "/repo/frontend"),
    ("backend", "backend", "gx-shell", "/app"),
    ("scripts", "scripts", "gx-shell", "/repo/scripts"),
    ("docs", "docs", "gx-shell", "/docs"),
)

#: ⚠ **`gx-fe-build` 는 일부러 뺐다.** 그 컨테이너의 `/app` 은 마운트가 아니라 사본이고
#: (`docker inspect` 의 `Mounts` 가 비어 있다 [실측 2026-09-06]), `scripts/deploy.sh` 가
#: **빌드할 때마다 `docker cp` 로 소스를 새로 넣는다** — 사본인 것이 설계다.
#: 여기 넣으면 이 게이트는 영원히 회색이 되고, 영원한 회색은 아무도 안 읽는다.
#: 드릴로 그 사본을 재 보고 싶으면 `GX_MOUNT_EXTRA` 로 한 줄 얹는다:
#:     GX_MOUNT_EXTRA="febuild:frontend:gx-fe-build:/app"
_extra = (os.environ.get("GX_MOUNT_EXTRA") or "").strip()
if _extra:
    for _spec in _extra.split(","):
        _p = _spec.split(":")
        if len(_p) == 4:
            MOUNT_PAIRS = MOUNT_PAIRS + (tuple(x.strip() for x in _p),)

#: 세는 규칙 — **두 쪽이 같은 규칙으로 세야 비교가 성립한다.**
PRUNE_DIRS = ("node_modules", "dist", "dist_deploy", "__pycache__", ".git",
              ".venv", ".pytest_cache", ".mypy_cache")
PRUNE_PREFIX = ("_fe_dist",)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수다** (D-277). 자기시험이 합성 사실을 먹인다
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list:
    """`facts` → `[(환경이름, 판정, 사유)]`.

    판정 셋만 쓴다: `ok`(있다) · `missing`(**빠졌다 = 회색 사유**) · `na`(해당 없음).
    `na` 는 「잴 자리가 설계상 없다」이지 「못 쟀다」가 아니다 — 둘을 섞으면
    갚아야 할 빚의 수가 부풀어 보인다(P-12 ③④).
    """
    out: list = []

    # ── minio ────────────────────────────────────────────────────────────
    m = facts.get("minio") or {}
    if m.get("http_ok"):
        out.append(("minio", OK,
                    f"{m.get('container') or '컨테이너 이름 모름'} 떠 있고 "
                    f"{m.get('url')} → {m.get('status')}"))
    elif m.get("running") is False:
        out.append(("minio", MISSING,
                    f"컨테이너 `{m.get('container')}` 가 떠 있지 않다 — "
                    f"객체 저장소를 쓰는 판정은 잴 자리가 없다"))
    else:
        out.append(("minio", MISSING,
                    f"{m.get('url')} 에 닿지 않는다 ({m.get('error') or '사유 미상'})"))

    # ── smtp ─────────────────────────────────────────────────────────────
    s = facts.get("smtp") or {}
    if s.get("http_ok"):
        out.append(("smtp", OK, f"수신함 {s.get('url')} → {s.get('status')}"))
    else:
        out.append(("smtp", MISSING,
                    f"SMTP 수신함(mailpit)이 **없다** — {s.get('url')} "
                    f"({s.get('error') or '사유 미상'}). 차선 E 가 세우는 중이다(P-68)"))

    # ── mount ────────────────────────────────────────────────────────────
    rows = facts.get("mount") or []
    if not rows:
        out.append(("mount", MISSING, "마운트 짝을 하나도 재지 못했다"))
    else:
        bad = [r for r in rows if r.get("state") == "mismatch"]
        na_rows = [r for r in rows if r.get("state") == "no-container"]
        unread = [r for r in rows if r.get("state") == "unreadable"]
        okrows = [r for r in rows if r.get("state") == "match"]
        if bad:
            detail = " · ".join(
                f"{r['name']}: 호스트 {r['host']} vs 컨테이너 {r['container_n']} "
                f"(**유령 {r['container_n'] - r['host']:+d}**)" for r in bad)
            out.append(("mount", MISSING,
                        f"**컨테이너가 저장소를 보고 있지 않다** — {detail}. "
                        f"사본을 훑는 게이트의 색은 제품의 색이 아니다 (유령 953 · P-55)"))
        elif unread:
            out.append(("mount", MISSING,
                        "컨테이너 쪽 파일 수를 못 셌다: " +
                        " · ".join(f"{r['name']}({r.get('error')})" for r in unread)))
        elif not okrows and na_rows:
            out.append(("mount", NA,
                        "컨테이너가 떠 있지 않다 — **위임 경로가 없으므로** 게이트는 "
                        "호스트 저장소만 본다. 유령이 생길 자리가 아니다"))
        else:
            detail = " · ".join(f"{r['name']} {r['host']}" for r in okrows)
            tail = f" (해당 없음 {len(na_rows)})" if na_rows else ""
            out.append(("mount", OK, f"호스트 = 컨테이너 — {detail}{tail}"))

    # ── session ──────────────────────────────────────────────────────────
    ss = facts.get("session") or {}
    if ss.get("no_credentials"):
        out.append(("session", MISSING,
                    "탐침 계정이 없다 — `GX_PROBE_USER`/`GX_PROBE_PASSWORD` "
                    "(뿌리 `.env.gates`). 남의 계정으로 로그인하면 **남의 화면이 죽는다**"))
    elif ss.get("unreachable"):
        out.append(("session", MISSING,
                    f"인증 문에 닿지 않는다 — {ss.get('url')} "
                    f"({ss.get('error') or '사유 미상'})"))
    elif ss.get("refused") is not None:
        out.append(("session", MISSING,
                    f"인증 문에는 **닿았는데** 탐침 계정 `{ss.get('holder')}` 이 "
                    f"거절당했다 (HTTP {ss.get('refused')}) — 서버가 없는 것과 "
                    f"자격증명이 틀린 것은 세울 것이 다르다"))
    elif ss.get("existing_session"):
        # ★ **점유자가 누구인가로 갈린다** (P-70 「차선 탐침 계정」).
        #   차선 전용 계정(`gxprobe_<차선>`)이 쥐고 있다면 그 창은 **이 차선의 앞선
        #   창**이다 — 끊어도 남의 화면이 아니다. 동시 접속 1을 차선 이름으로
        #   원천 해소한다는 것이 정확히 이 뜻이다.
        #   반대로 공용 계정이면 점유자가 **남일 수 있다** — 그때 로그인하는 것은
        #   남의 화면을 죽이는 일이고, 그것은 재기 전에 멈춰야 할 환경의 사실이다.
        if ss.get("dedicated"):
            out.append(("session", OK,
                        f"점유자 `{ss.get('holder')}` = **이 차선 전용 계정**"
                        f"(차선 {ss.get('lane')}) — 앞선 창은 우리 것이다. "
                        f"동시 접속 1(UX-24 · §0.4)을 차선 이름으로 가른 자리"))
        else:
            out.append(("session", MISSING,
                        f"**세션 점유자가 있다: `{ss.get('holder') or '?'}`** — 그런데 "
                        f"이 계정은 차선 전용(`gxprobe_<차선>`)이 아니다. 동시 접속 1"
                        f"(UX-24 · §0.4 자료구조)이라 지금 로그인하면 **남의 화면이 "
                        f"죽는다.** 차선 탐침 계정(`GX_LANE`/`GX_PROBE_USER`)을 쓴다"))
    elif ss.get("logged_in"):
        out.append(("session", OK,
                    f"`{ss.get('holder')}` 자리가 비어 있었다 — 이 차선이 쥐었다"))
    else:
        out.append(("session", MISSING,
                    f"로그인이 성공도 거절도 아니다: {ss.get('message') or '?'}"))
    return out


def exit_code(rows: list, require: list) -> int:
    """**필요하다고 선언한 것만** 판정에 든다. 나머지는 표에만 적힌다."""
    need = set(require)
    for (name, verdict, _why) in rows:
        if name in need and verdict == MISSING:
            return EXIT_GRAY
    return EXIT_OK


def missing_names(rows: list, require: list) -> list:
    need = set(require)
    return [n for (n, v, _w) in rows if n in need and v == MISSING]


# ═══════════════════════════════════════════════════════════════════════════
# 재기 — 여기부터는 바깥을 만진다
# ═══════════════════════════════════════════════════════════════════════════
def _http(url: str, timeout: int = 6) -> tuple:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return True, r.status, None
    except urllib.error.HTTPError as exc:      # 200이 아니어도 **닿기는 했다**
        return (200 <= exc.code < 500), exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, OSError) as exc:
        return False, None, f"{type(exc).__name__}"


def _docker(args: list, timeout: int = 25) -> tuple:
    try:
        p = subprocess.run(["docker"] + args, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "docker 명령이 없다"
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, "", f"{type(exc).__name__}"


def container_running(name: str) -> bool | None:
    rc, out, _err = _docker(["inspect", "-f", "{{.State.Running}}", name], timeout=15)
    if rc == 127:
        return None                     # 도커 자체가 없다 — 「안 떠 있다」와 다르다
    return rc == 0 and out.strip() == "true"


def probe_minio() -> dict:
    running = container_running(MINIO_CONTAINER)
    ok, status, err = _http(MINIO_HEALTH)
    return {"container": MINIO_CONTAINER, "running": running,
            "url": MINIO_HEALTH, "http_ok": ok, "status": status, "error": err}


def probe_smtp() -> dict:
    ok, status, err = _http(SMTP_API)
    return {"url": SMTP_API, "http_ok": ok, "status": status, "error": err}


def count_host(rel: str) -> int | None:
    base = ROOT / rel
    if not base.is_dir():
        return None
    n = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in PRUNE_DIRS
                       and not any(d.startswith(p) for p in PRUNE_PREFIX)]
        n += len(filenames)
    return n


def _find_cmd(path: str) -> str:
    names = " -o ".join(f"-name '{d}'" for d in PRUNE_DIRS)
    names += " " + " ".join(f"-o -name '{p}*'" for p in PRUNE_PREFIX)
    return f"find {path} \\( {names} \\) -prune -o -type f -print | wc -l"


def probe_mount() -> list:
    rows: list = []
    for (name, rel, container, cpath) in MOUNT_PAIRS:
        host_n = count_host(rel)
        row = {"name": name, "host_path": rel, "container": container,
               "container_path": cpath, "host": host_n, "container_n": None}
        if host_n is None:
            row["state"] = "unreadable"
            row["error"] = f"호스트에 {rel} 이 없다"
            rows.append(row)
            continue
        running = container_running(container)
        if running is None:
            row["state"] = "no-container"
            row["error"] = "docker 없음"
            rows.append(row)
            continue
        if not running:
            row["state"] = "no-container"
            row["error"] = f"{container} 가 떠 있지 않다"
            rows.append(row)
            continue
        rc, out, err = _docker(["exec", container, "sh", "-c", _find_cmd(cpath)])
        digits = "".join(ch for ch in out if ch.isdigit())
        if rc != 0 or not digits:
            row["state"] = "unreadable"
            row["error"] = (err or out or "출력 없음")[:80]
        else:
            row["container_n"] = int(digits)
            row["state"] = "match" if row["container_n"] == host_n else "mismatch"
        rows.append(row)
    return rows


def probe_session() -> dict:
    """**앞선 세션을 끊지 않고** 점유 여부만 묻는다.

    ★ `end_previous_session: false` 가 이 탐침의 핵심이다. `true` 로 물으면
      묻는 행위 자체가 남의 화면을 죽인다 — 재는 것이 대상을 바꾸면 그것은 측정이 아니다.
      `false` 면 앞선 세션이 있을 때 서버가 **200 · success:false** 로 알려 주고
      토큰을 아예 안 준다(`core/api/v1/auth.py:630`).
    """
    urls = list(dict.fromkeys(b.rstrip("/") + "/api/v1/auth/login"
                              for b in API_BASES))
    if not PROBE_USER or not PROBE_PASSWORD:
        return {"url": urls[0], "no_credentials": True,
                "holder": PROBE_USER or None}
    body = json.dumps({"username": PROBE_USER, "password": PROBE_PASSWORD,
                       "end_previous_session": False}).encode()
    url, data, err, refused = urls[0], None, None, None
    for cand in urls:
        req = urllib.request.Request(cand, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            url = cand
            break
        except urllib.error.HTTPError as exc:
            # ★ **닿았다.** 거절은 도달의 증거다 — 「서버가 없다」와 「자격증명이
            #   틀렸다」를 같은 칸에 넣으면 세울 것을 못 찾는다.
            refused, url = exc.code, cand
            break
        except (urllib.error.URLError, OSError, ValueError) as exc:
            err = f"{type(exc).__name__} @ {cand}"
    if refused is not None:
        return {"url": url, "refused": refused, "holder": PROBE_USER,
                "lane": LANE or None}
    if data is None:
        return {"url": " · ".join(urls), "unreachable": True, "error": err,
                "holder": PROBE_USER}
    # ⚠ 이름을 `auth` 로 두지 않는다 (D-337 동음이의) — 「인증(누구인가)」과
    #   「인가(무엇을 할 수 있나)」가 같은 낱말로 읽힌다. 여기서 보는 것은 **인증 쪽**이다.
    authn_status = data.get("auth_status") or {}
    return {"url": url, "holder": PROBE_USER, "lane": LANE or None,
            "dedicated": bool(LANE) and PROBE_USER == f"gxprobe_{LANE}",
            "existing_session": bool(authn_status.get("existing_session")),
            "logged_in": bool(data.get("success")),
            "message": data.get("message")}


def config_fingerprint() -> str:
    """**무엇을 잰 설정인가.** 캐시가 이것을 함께 들고 있지 않으면 설정을 바꿔 다시
    부른 사람이 **앞 설정으로 잰 답**을 받는다 — 재지 않은 것을 잰 것으로 읽는 자리다."""
    return json.dumps([MOUNT_PAIRS, MINIO_CONTAINER, MINIO_HEALTH, SMTP_API,
                       API_BASES, PROBE_USER, LANE], ensure_ascii=False,
                      sort_keys=True)


def measure() -> dict:
    return {"measured_at": time.time(), "config": config_fingerprint(),
            "minio": probe_minio(), "smtp": probe_smtp(),
            "mount": probe_mount(), "session": probe_session()}


def measure_cached(no_cache: bool = False) -> tuple:
    """`(facts, 몇 초 전에 잰 것인가)`. 캐시를 써도 **나이를 늘 함께 낸다**."""
    if not no_cache and CACHE_PATH.exists():
        try:
            facts = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            age = time.time() - float(facts.get("measured_at") or 0)
            if 0 <= age <= CACHE_TTL and \
                    facts.get("config") == config_fingerprint():
                return facts, age
        except (OSError, ValueError, TypeError):
            pass
    facts = measure()
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(facts, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    except OSError:
        pass
    return facts, 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성과 음성을 함께** (D-277 · D-350)
# ═══════════════════════════════════════════════════════════════════════════
def self_test(quiet: bool = False) -> int:
    bad: list = []

    def v(facts):
        return {n: verdict for (n, verdict, _w) in judge(facts)}

    good = {
        "minio": {"container": "c", "running": True, "url": "u", "http_ok": True,
                  "status": 200},
        "smtp": {"url": "u", "http_ok": True, "status": 200},
        "mount": [{"name": "frontend", "state": "match", "host": 1003,
                   "container_n": 1003}],
        "session": {"holder": "gxprobe_s", "existing_session": False,
                    "logged_in": True},
    }
    g = v(good)
    if set(g.values()) != {OK}:
        bad.append(f"환경이 다 갖춰졌는데 초록이 아니다: {g}")
    if exit_code(judge(good), ["minio", "smtp", "mount", "session"]) != EXIT_OK:
        bad.append("전부 ok 인데 종료 코드가 0이 아니다")

    # ── ★★ **출생 표본** (D-310) — 이 파일을 만들게 한 바로 그 사례 ──────────
    #   [실측 2026-09-05 · P-55] `gx-shell:/repo/frontend` 가 사본이었고 그 안에
    #   파일이 1,956개, 호스트에는 1,003개였다. **953개가 유령**이었고 게이트 여섯이
    #   그것을 훑으며 색을 내고 있었다. 그 색은 제품의 색이 아니었다.
    born = dict(good, mount=[{"name": "frontend", "state": "mismatch",
                              "host": 1003, "container_n": 1956}])
    rows = judge(born)
    if v(born).get("mount") != MISSING:
        bad.append("**출생 표본** — 호스트 1,003 vs 컨테이너 1,956 인데 회색이 아니다. "
                   "게이트 여섯이 유령 953개를 훑던 자리가 여기다")
    if exit_code(rows, ["mount"]) != EXIT_GRAY:
        bad.append("마운트가 어긋났는데 종료 코드가 2(회색)가 아니다")
    if exit_code(rows, ["minio"]) != EXIT_OK:
        bad.append("**요구하지 않은 환경**이 빠졌는데 회색이다 — 게이트마다 필요한 "
                   "환경이 다르고, 남의 환경으로 회색이 되면 그 게이트는 곧 꺼진다")
    why = dict((n, w) for (n, _v, w) in rows)["mount"]
    if "953" not in why and "+953" not in why:
        bad.append(f"유령 수를 사유에 안 적는다: {why!r} — 회색의 사유는 **환경 이름과 "
                   f"그 크기**여야 한다")

    # ── 세션 점유자 — **차선 이름이 가른다** (P-70) ──────────────────────
    shared = dict(good, session={"holder": "gxprobe_e2e", "existing_session": True,
                                 "lane": "s", "dedicated": False,
                                 "logged_in": False, "message": "active session"})
    if v(shared).get("session") != MISSING:
        bad.append("**공용 계정**을 남이 쥐고 있는데 초록이다 — 그대로 로그인하면 "
                   "남의 화면이 죽는다(동시 접속 1)")
    if "gxprobe_e2e" not in dict((n, w) for (n, _v, w) in judge(shared))["session"]:
        bad.append("점유자 이름을 말하지 않는다 — 「누가 잡고 있는가」가 이 탐침의 답이다")
    mine = dict(good, session={"holder": "gxprobe_s", "existing_session": True,
                               "lane": "s", "dedicated": True,
                               "logged_in": False, "message": "active session"})
    if v(mine).get("session") != OK:
        bad.append("**차선 전용 계정**이 쥔 앞선 창까지 회색으로 낸다 — 그러면 차선 "
                   "이름을 다섯으로 나눈 이유가 없어지고, 게이트는 늘 회색이 된다")

    nocred = dict(good, session={"no_credentials": True})
    if v(nocred).get("session") != MISSING:
        bad.append("탐침 자격증명이 없는데 초록이다")
    ref = dict(good, session={"holder": "gxprobe_s", "refused": 401})
    if v(ref).get("session") != MISSING:
        bad.append("탐침 계정이 401 로 거절당했는데 초록이다")
    if "401" not in dict((n, w) for (n, _v, w) in judge(ref))["session"]:
        bad.append("거절을 「닿지 않는다」와 같은 말로 적는다 — 서버가 없는 것과 "
                   "자격증명이 틀린 것은 **세울 것이 다르다**")

    # ── **해당 없음 ≠ 못 잼** (P-12 ③④) ────────────────────────────────
    nocont = dict(good, mount=[{"name": "frontend", "state": "no-container",
                                "host": 1003}])
    if v(nocont).get("mount") != NA:
        bad.append("컨테이너가 없어 **위임 경로 자체가 없는데** 회색이다 — 잴 자리가 "
                   "설계상 없는 것과 못 잰 것은 다른 사실이다")
    if exit_code(judge(nocont), ["mount"]) != EXIT_OK:
        bad.append("해당 없음인데 종료 코드가 0이 아니다")

    unread = dict(good, mount=[{"name": "frontend", "state": "unreadable",
                                "host": 1003, "error": "permission denied"}])
    if v(unread).get("mount") != MISSING:
        bad.append("컨테이너 쪽 수를 **못 셌는데** 초록이다 — 못 센 것은 일치가 아니다")

    # ── minio · smtp 음성 ───────────────────────────────────────────────
    if v(dict(good, minio={"container": "c", "running": False,
                           "url": "u"})).get("minio") != MISSING:
        bad.append("MinIO 컨테이너가 안 떠 있는데 초록이다")
    if v(dict(good, smtp={"url": "u", "http_ok": False,
                          "error": "URLError"})).get("smtp") != MISSING:
        bad.append("SMTP 수신함이 없는데 초록이다")

    # ── 세는 규칙이 두 쪽에서 같은가 — 이름 목록이 비면 비교가 무의미해진다 ──
    if not PRUNE_DIRS or "node_modules" not in PRUNE_DIRS:
        bad.append("호스트·컨테이너가 같은 규칙으로 세지 않는다 — node_modules 를 "
                   "한쪽만 세면 늘 어긋난다")
    if "node_modules" not in _find_cmd("/x") or "_fe_dist*" not in _find_cmd("/x"):
        bad.append("컨테이너 쪽 find 가 호스트와 같은 것을 걸러내지 않는다")
    # ── 캐시가 **설정을 함께 들고 있는가** ───────────────────────────────
    #   [실측 2026-09-06] 첫 판은 안 들고 있었다. `GX_MOUNT_EXTRA` 로 짝을 하나 얹고
    #   다시 불렀더니 **앞 설정으로 잰 답**이 그대로 나왔고, 얹은 짝은 재지도 않은 채
    #   초록이었다 — 캐시가 「재지 않은 것」을 「쟀다」로 바꾼 자리다.
    if MOUNT_PAIRS and str(MOUNT_PAIRS[0][0]) not in config_fingerprint():
        bad.append("캐시 지문이 마운트 짝을 안 담는다 — 짝을 바꿔도 앞 답이 나온다")

    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return 1
    if not quiet:
        print(f"{TAG} 자기시험 통과 — **출생 표본 1**(유령 953 · P-55) · 양성 1 · "
              f"음성 9 · 해당없음 1 · 요구범위 1 · 세는규칙 2")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="P-70 게이트 환경 전처리")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--require", nargs="*", default=[],
                    help="이 게이트가 필요로 하는 환경 이름 (없으면 표만 낸다)")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--quiet", action="store_true",
                    help="빠진 것만 말한다 (게이트가 부를 때)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test(quiet=args.quiet) != EXIT_OK:
        return EXIT_GRAY          # 판정기가 눈이 멀었으면 **환경을 안다고 말하지 않는다**

    unknown = [r for r in args.require
               if r not in ("minio", "smtp", "mount", "session")]
    if unknown:
        print(f"{TAG} 알 수 없는 환경 이름: {unknown}")
        return EXIT_GRAY

    facts, age = measure_cached(args.no_cache)
    rows = judge(facts)
    mark = {OK: "  ", MISSING: "? ", NA: "- "}
    need = set(args.require)
    for (name, verdict, why) in rows:
        if args.quiet and (name not in need or verdict != MISSING):
            continue
        star = "*" if name in need else " "
        print(f"{TAG} {mark[verdict]}{star}{name:8} {why}")

    miss = missing_names(rows, args.require)
    rc = exit_code(rows, args.require)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"require": args.require, "age_sec": round(age, 1), "facts": facts,
             "rows": [{"name": n, "verdict": v, "why": w} for (n, v, w) in rows],
             "missing": miss, "exit": rc}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"{TAG} 기록 → {args.json}")

    if args.require:
        if miss:
            print(f"{TAG} **환경 미비: {','.join(miss)}** — 회색(exit 2). "
                  f"제품의 빨강이 아니다 (P-70) · {age:.0f}초 전에 잰 것")
        elif not args.quiet:
            print(f"{TAG} 필요한 환경 {len(args.require)}가지 다 있다 "
                  f"({age:.0f}초 전에 잰 것)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
