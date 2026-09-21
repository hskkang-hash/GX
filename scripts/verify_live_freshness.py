#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**게이트가 때리는 서버가 지금 코드를 물고 있는가** — P-82 (2026-09-06 · 턴 I).

무엇을 막는가 — **낡은 판정: 잰 사실이 그 뒤의 행동을 덮는다**
--------------------------------------------------------------
[실측 2026-09-06 · 턴 H] 게이트 12종이 이틀 동안 초록이었다. 그 초록은
**2026-09-05 14:41 의 코드**에 대한 것이었다. 조율자가 턴 G 에 「최신이다」를
한 번 재고, 그 뒤 병합·배치하고 **재기동하지 않았다.** 같은 요청에 두 서버가
다른 답을 냈다(8000→422 · 8010→401). 아무도 그 차이를 보지 않았다.

    이것이 이 저장소가 만난 **낡음의 넷째 얼굴**이다.
      ① 낡은 인벤토리(D-427) ② 낡은 증거(P-59) ③ 낡은 프로세스(D-451)
      ④ **낡은 판정** — 잰 것은 진짜였고, 그 뒤의 행동이 그것을 덮었다

앞의 셋은 전부 도구가 잡게 만들었다. 넷째만 사람이 기억해야 했다.
**사람이 기억해야 하는 규칙은 지켜지는 동안에만 값이 있다.** 이 파일이 그 자리다.

무엇을 재는가 — 셋
------------------
  ``대상 서버``   `GX_API` 가 가리키는 그 서버. 게이트가 실제로 때리는 자리다.
  ``기동 시각``   그 서버 프로세스가 **언제 떴는가** (`/proc/<pid>/stat` · 클럭틱)
  ``커밋``        그 프로세스의 환경에 실린 `GX_COMMIT` (있으면)

판정 — **다르면 빨강 · 오래되면 회색**
--------------------------------------
  빨강(1) ``LIVE_COMMIT_MISMATCH``   커밋을 알고 있는데 HEAD 와 **다르다**.
                                     이것은 사실이지 환경이 아니다.
  회색(2) ``LIVE_OLDER_THAN_SOURCE`` 기동 시각이 **소스보다 오래됐다.**
                                     지금 코드를 문다고 **증명할 수 없다** —
                                     증명 못 한 것은 초록이 아니다(D-301).
  회색(2) ``LIVE_NO_PROCESS``        그 포트를 문 프로세스를 못 찾았다.
  회색(2) ``LIVE_NO_CONTAINER``      위임할 컨테이너 이름이 없거나 docker 가 없다.
  초록(0)                            기동이 소스보다 **뒤**이고, 커밋이 같거나 모른다.

★ **소스 시각은 HEAD 커밋 시각이 아니다.** HEAD 가 `docs/**` 만 고친 커밋이면
  서버는 낡지 않았다. 그래서 재는 것은 **서버가 실제로 실행하는 나무**(`backend/`)의
  ㉠ 마지막 커밋 시각과 ㉡ 작업본 파일 mtime 중 **큰 쪽**이다.
  ㉡ 을 빼면 커밋 안 된 수정이 도는 서버를 초록으로 읽는다.

★ **회색은 초록이 아니다. 그러나 빨강도 아니다** (P-70). 못 잰 것을 빨강으로
  내면 「환경을 세우면 사라지는 빨강」이 쌓이고, 그런 빨강을 본 사람은 게이트를 끈다.

★★ **[P-116 · 2026-09-10 · 턴 O] 한 서버만 재면 낡음의 대부분을 못 본다.**

    [실측 2026-09-08] 백업 주기가 **24시간 두 번** 동안 꺼진 것처럼 보였다.
    설정은 내내 `True` 였다. 낡은 것은 설정이 아니라 **`gx-celery-e` 작업자 프로세스**다 —
    2026-09-05 에 떠서 씨앗 이전 코드를 메모리에 물고 있었다.

    그 프로세스는 `GX_API` 가 가리키는 서버가 **아니다.** 위쪽 판정기는 그것을
    **구조적으로 볼 수 없었다** — 없는 눈은 감은 눈보다 나쁘다. 안 보이니까
    「전부 최신이다」가 계속 초록으로 나왔다.

    그래서 자리를 **다섯**으로 늘렸다. 각자 **자기 소스**에 대해 잰다:

      `gx-gunicorn-e` · `gx-celery-e` · `gx-beat-e` → `backend/**.py`
      `gx-nginx-e`                                  → `nginx/**.conf`·`.inc`
      `gx-shell` 안의 `runserver`                    → `backend/**.py`

    ⚠ 나무를 안 갈라 놓으면 판정이 거짓말한다 — `gx-nginx-e` 를 `backend/` 로 재면
      앞단 설정을 고쳐도 초록이고, gunicorn 을 `nginx/` 로 재면 코드를 고쳐도 초록이다.

쓰는 법
-------
    python scripts/verify_live_freshness.py --self-test
    python scripts/verify_live_freshness.py                 # GX_API 한 자리만 (P-82)
    python scripts/verify_live_freshness.py --all           # **다섯 자리** (P-116)
    python scripts/verify_live_freshness.py --all --json docs/agent/evidence/P-116/fresh.json
    python scripts/verify_live_freshness.py --prove-stale   # 음성 대조 (아래)

★ `--prove-stale` 이 왜 따로 있나 — **자기시험은 상수를 못 잡는다.**
  `decide()` 표를 먹이는 자기시험은 판정 *식*이 맞는지만 본다. 실제로 재는 경로가
  「늘 초록」인 상수여도 그 시험은 통과한다. `--prove-stale` 은 **살아 있는 다섯 자리를
  그대로 재고** 비교 대상 시각만 「지금」으로 민다 — 다섯이 **모두 회색**으로 뒤집혀야 한다.
  하나라도 초록이면 그 초록은 측정이 아니다.

종료 코드: 0 신선 · 1 다르다(빨강) · 2 판정 불가(회색) · `--all` 은 **가장 나쁜 것**
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_route_alive import (  # noqa: E402  — **같은 눈으로 읽는다** (D-369)
    expand_env_refs,
)

ROOT = Path(__file__).resolve().parent.parent
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 서버가 실제로 실행하는 나무. 여기가 바뀌면 서버는 다시 떠야 한다.
SOURCE_TREE = "backend"

LOCAL_ENV_FILES = (".env.gates", ".env.local", ".env")
LOCAL_ENV_KEYS = ("GX_API", "GX_ROUTE_CONTAINER")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def load_local_env() -> list[str]:
    """저장소 밖(gitignored) 파일에서 이름 둘만 읽는다. 이미 있는 값은 **덮지 않는다**."""
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
        seen: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            #: ★ [D-457] `${NAME}` 참조를 셸과 같은 뜻으로 펼친다 — 안 펼치면
            #:   리터럴이 값으로 나가 판정기가 회색이 된다 (verify_route_alive 참조).
            #:   ⚠ 거르기 **앞에서** 담는다 — 가리키는 이름이 `LOCAL_ENV_KEYS` 밖일 수 있다.
            raw = expand_env_refs(v.strip().strip('"').strip("'"), seen)
            seen[k] = raw
            if k not in LOCAL_ENV_KEYS or os.environ.get(k):
                continue
            os.environ[k] = raw
            took = True
        if took:
            read.append(name)
    return read


def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def head_commit() -> str:
    rc, out = _run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"])
    return out.strip() if rc == 0 else ""


def source_time() -> tuple[int, str]:
    """서버가 실행하는 나무의 **가장 최근 시각** — 커밋과 작업본 중 큰 쪽.

    돌려주는 둘째 값은 **그 시각이 어디서 왔는가**다. 수만 내면 다음 사람이
    「왜 회색인가」를 다시 알아내야 한다(D-301 이 반복해 말한 자리).
    """
    best, why = 0, "없음"
    rc, out = _run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct", "--", SOURCE_TREE])
    if rc == 0 and out.strip().isdigit():
        best, why = int(out.strip()), SOURCE_TREE + "/ 마지막 커밋"
    rc, out = _run(["git", "-C", str(ROOT), "ls-files", SOURCE_TREE])
    if rc == 0:
        for rel in out.splitlines():
            rel = rel.strip()
            if not rel.endswith(".py"):
                continue
            try:
                m = int((ROOT / rel).stat().st_mtime)
            except OSError:
                continue
            if m > best:
                best, why = m, "작업본 " + rel
    return best, why


def port_of(api: str) -> str:
    m = re.search(r":(\d+)", api)
    return m.group(1) if m else "8000"


# ══════════════════════════════════════════════════════════════════════════════
# P-116 — **한 서버가 아니라 모든 프로세스**
# ══════════════════════════════════════════════════════════════════════════════
#: [실측 2026-09-08 · P-116] 백업 주기가 24시간 두 번 동안 꺼진 것처럼 보였다.
#: 설정은 내내 `True` 였다. 낡은 것은 **설정이 아니라 작업자 프로세스**였다 —
#: 2026-09-05 에 떠서 씨앗 이전 코드를 메모리에 물고 있었다. 그 프로세스는
#: `GX_API` 가 가리키는 서버가 **아니다.** 서버 하나만 재는 판정기는 그것을 못 본다.
#:
#: ★ 그래서 재는 자리는 다섯이다. **각자 자기 소스**에 대해 잰다 —
#:   `gx-nginx-e` 를 `backend/` 로 재면 nginx 설정을 고쳐도 초록이고,
#:   gunicorn 을 `nginx/` 로 재면 코드를 고쳐도 초록이다.
PROCESSES = (
    {
        "key": "gx-gunicorn-e",
        "container": "gx-gunicorn-e",
        "match": "gunicorn",
        "role": "API (nginx `upstream gx_app` 의 peer)",
        "sources": (("backend", ".py"),),
    },
    {
        "key": "gx-celery-e",
        "container": "gx-celery-e",
        "match": "celery -A config worker",
        "role": "작업자 — **예약 백업이 실제로 도는 자리** (P-116 출생 표본)",
        "sources": (("backend", ".py"),),
    },
    {
        "key": "gx-beat-e",
        "container": "gx-beat-e",
        "match": "celery -A config beat",
        "role": "스케줄러 — 백업 주기를 쏘는 자리",
        "sources": (("backend", ".py"),),
    },
    {
        "key": "gx-nginx-e",
        "container": "gx-nginx-e",
        "match": "nginx: master process",
        "role": "앞단 (`-c /etc/nginx/gx/gx-front.conf`)",
        "sources": (("nginx", ".conf"), ("nginx", ".inc")),
    },
    {
        "key": "gx-shell:runserver",
        "container": "gx-shell",
        "match": "manage.py runserver",
        "role": "게이트가 때리는 개발 서버 (`GX_API`)",
        "sources": (("backend", ".py"),),
    },
)

#: ★ **`nginx:alpine` 에는 파이썬이 없다** [실측 2026-09-10 · 턴 O].
#:   `python -c` 로 캐는 위쪽 `PROBE_SRC` 는 앞단을 영원히 회색으로 만든다 —
#:   「도구가 없어서 못 잰다」는 **못 잰 것이지 초록이 아니다**. 그래서 이 조각은
#:   busybox `sh` + `awk` 만 쓴다. 백엔드 이미지와 `nginx:alpine` 둘 다에서 돈다.
SH_PROBE = r"""
TOK="$1"
now=$(date +%s)
up=$(awk '{print $1}' /proc/uptime)
tck=$(getconf CLK_TCK 2>/dev/null)
[ -n "$tck" ] || tck=100
best=""; bestpid=""; bestcl=""
for p in /proc/[0-9]*; do
  [ -r "$p/cmdline" ] || continue
  cl=$(tr '\0' ' ' < "$p/cmdline" 2>/dev/null)
  [ -n "$cl" ] || continue
  case "$cl" in *"$TOK"*) ;; *) continue ;; esac
  # 자기 자신(docker exec 가 띄운 sh -c 래퍼)은 TOK 를 인자로 달고 있다. 반드시 뺀다.
  case "$cl" in "sh -c "*|"/bin/sh -c "*|"bash -c "*) continue ;; esac
  stt=$(awk '{ i=index($0,") "); s=substr($0,i+2); split(s,f," "); print f[20] }' "$p/stat" 2>/dev/null)
  [ -n "$stt" ] || continue
  # ★ 맞는 것이 여럿이면 **가장 먼저 뜬 것**(마스터)을 고른다. 일꾼은 죽으면 다시
  #   태어나므로 일꾼의 기동 시각은 코드를 언제 읽었는지를 말하지 않는다.
  if [ -z "$best" ] || [ "$stt" -lt "$best" ]; then
    best=$stt; bestpid=${p#/proc/}; bestcl=$cl
  fi
done
if [ -z "$best" ]; then echo "GXFRESH found=0"; exit 0; fi
boot=$(awk -v n="$now" -v u="$up" -v s="$best" -v t="$tck" 'BEGIN{printf "%d", n-(u-s/t)}')
echo "GXFRESH found=1"
echo "GXFRESH pid=$bestpid"
echo "GXFRESH boot_epoch=$boot"
echo "GXFRESH cmdline=$(echo "$bestcl" | cut -c1-160)"
if [ -r "/proc/$bestpid/environ" ]; then
  tr '\0' '\n' < "/proc/$bestpid/environ" 2>/dev/null | grep -E '^(GX_COMMIT|DJANGO_SETTINGS_MODULE)=' | sed 's/^/GXFRESH env_/'
fi
"""


def probe_sh(container: str, token: str) -> dict:
    """컨테이너 안에서 `token` 을 문 **가장 먼저 뜬** 프로세스의 기동 시각을 캔다.

    파이썬을 쓰지 않는다 — 앞단(`nginx:alpine`)에 파이썬이 없기 때문이다.
    """
    rc, out = _run(["docker", "exec", container, "sh", "-c", SH_PROBE, "gxfresh", token])
    got: dict = {"found": False, "env": {}}
    saw = False
    for ln in out.splitlines():
        ln = ln.strip()
        if not ln.startswith("GXFRESH "):
            continue
        saw = True
        k, _, v = ln[len("GXFRESH "):].partition("=")
        if k == "found":
            got["found"] = (v == "1")
        elif k in ("pid", "boot_epoch"):
            got[k] = int(v) if v.lstrip("-").isdigit() else 0
        elif k == "cmdline":
            got["cmdline"] = v
        elif k.startswith("env_"):
            got["env"][k[4:]] = v
    if not saw:
        return {"found": False, "env": {}, "error": "LIVE_NO_CONTAINER",
                "detail": out.strip().replace("\n", " ")[:200]}
    if not got["found"]:
        got["error"] = "LIVE_NO_PROCESS"
    return got


#: `git ls-files` 는 나무당 한 번만 부른다 (다섯 자리가 같은 나무를 공유한다).
_LS_CACHE: dict[str, list[str]] = {}


def _ls_tree(tree: str) -> list[str]:
    if tree not in _LS_CACHE:
        rc, out = _run(["git", "-C", str(ROOT), "ls-files", tree])
        _LS_CACHE[tree] = out.splitlines() if rc == 0 else []
    return _LS_CACHE[tree]


def source_time_for(sources: tuple) -> tuple[int, str]:
    """**그 프로세스가 실제로 실행하는 것들**의 가장 최근 시각 — 커밋과 작업본 중 큰 쪽.

    `source_time()` 과 같은 규칙이되 나무가 여럿이고 확장자가 자리마다 다르다.
    """
    best, why = 0, "없음"
    for tree, ext in sources:
        rc, out = _run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct", "--", tree])
        if rc == 0 and out.strip().isdigit() and int(out.strip()) > best:
            best, why = int(out.strip()), tree + "/ 마지막 커밋"
        for rel in _ls_tree(tree):
            rel = rel.strip()
            if not rel.endswith(ext):
                continue
            try:
                m = int((ROOT / rel).stat().st_mtime)
            except OSError:
                continue
            if m > best:
                best, why = m, "작업본 " + rel
    return best, why


#: 컨테이너 안에서 도는 조각. **`/proc` 만 읽는다** — `curl` 도 `ps -o lstart` 도
#: 없는 컨테이너가 이 저장소의 기본값이다. 도구가 있을 것이라 가정하지 않는다.
PROBE_SRC = r"""
import os, sys, json, time
port = sys.argv[1]
hit = None
for pid in os.listdir("/proc"):
    if not pid.isdigit():
        continue
    try:
        cl = open("/proc/" + pid + "/cmdline", "rb").read().decode("utf-8", "replace")
    except OSError:
        continue
    cl = cl.replace("\x00", " ").strip()
    if "manage.py runserver" not in cl or (":" + port) not in cl:
        continue
    if cl.startswith("sh ") or cl.startswith("/bin/sh"):
        continue        # sh -c 로 감싼 부모가 아니라 실제 파이썬 프로세스를 고른다
    hit = (pid, cl)
    break
if hit is None:
    print(json.dumps({"found": False}))
    sys.exit(0)
pid, cl = hit
st = open("/proc/" + pid + "/stat").read()
fields = st[st.rindex(")") + 2:].split()   # 이름에 공백이 있을 수 있어 마지막 ')' 뒤부터
starttime = int(fields[19]) / float(os.sysconf("SC_CLK_TCK"))
uptime = float(open("/proc/uptime").read().split()[0])
env = {}
try:
    raw = open("/proc/" + pid + "/environ", "rb").read().decode("utf-8", "replace")
    for kv in raw.split("\x00"):
        if "=" in kv:
            k, _, v = kv.partition("=")
            if k in ("GX_COMMIT", "DJANGO_SETTINGS_MODULE", "MINIO_ENDPOINT"):
                env[k] = v
except OSError:
    pass
print(json.dumps({"found": True, "pid": pid, "cmdline": cl[:200],
                  "boot_epoch": int(time.time() - (uptime - starttime)), "env": env}))
"""


def probe(container: str, port: str) -> dict:
    """컨테이너 안에서 그 포트를 문 프로세스의 **기동 시각과 커밋**을 캔다."""
    rc, out = _run(["docker", "exec", container, "python", "-c", PROBE_SRC, port])
    line = ""
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.startswith("{"):
            line = ln
    if not line:
        return {"found": False, "error": "LIVE_NO_CONTAINER",
                "detail": out.strip().replace("\n", " ")[:200]}
    try:
        return json.loads(line)
    except ValueError:
        return {"found": False, "error": "LIVE_NO_CONTAINER", "detail": line[:200]}


#: 판정표 — **한 자리에 적고 한 자리에서 읽는다.** 복사본 둘은 반드시 어긋난다(D-369).
#:   (커밋 아는가, 커밋 같은가, 기동이 소스보다 뒤인가) → (종료코드, 사유 이름)
def decide(commit_known: bool, commit_same: bool, boot_after_source: bool) -> tuple[int, str]:
    if commit_known and not commit_same:
        return EXIT_FAIL, "LIVE_COMMIT_MISMATCH"
    if not boot_after_source:
        return EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE"
    return EXIT_OK, "FRESH"


#: ★ **출생 표본** (BIRTH_SAMPLE · D-310) — 이 도구를 만들게 한 **바로 그 사례**다.
#:   [실측 2026-09-06 · 턴 H] 8000 이 문 프로세스는 **2026-09-05 14:41** 에 떴고,
#:   `backend/` 는 그 뒤 턴 G·H 로 여러 번 바뀌었다. `GX_COMMIT` 은 없이 떴다 —
#:   그래서 커밋으로는 아무것도 못 가리고 **시각만이 증거**였다. 아무도 안 봤다.
#:   이 표본이 회색이 아니게 되는 날, 이 도구는 눈이 먼 것이다.
BIRTH_SAMPLE = {
    "boot_epoch": 1757043660,     # 2026-09-05 14:41 — 8000 이 문 프로세스의 기동
    "source_epoch": 1757164800,   # 2026-09-06 — 그 뒤 backend/ 가 바뀐 시각
    "live_commit": "",            # GX_COMMIT 없이 떴다 → 커밋으로는 못 가린다
    "expect": (EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE"),
}


#: ★ **출생 표본 둘** (P-116 · 2026-09-08) — 이 확장을 만들게 한 **바로 그 사례**다.
#:   백업 주기가 24시간 두 번 동안 꺼진 것처럼 보였다. 설정은 내내 `True` 였다.
#:   낡은 것은 **`gx-celery-e` 작업자 프로세스**다 — 2026-09-05 에 떠서 씨앗 이전
#:   코드를 물고 있었다. 위쪽 `BIRTH_SAMPLE` 은 `GX_API` 서버만 재므로 이것을
#:   **구조적으로 볼 수 없었다.** 자리를 다섯으로 늘린 이유가 정확히 이 한 줄이다.
#:   이 표본이 초록이 되는 날, 이 확장은 눈이 먼 것이다.
BIRTH_SAMPLE_WORKER = {
    "key": "gx-celery-e",
    "boot_epoch": 1788586860,     # 2026-09-05 14:41 — 작업자가 뜬 시각
    "source_epoch": 1788825600,   # 2026-09-08 09:00 — 그 뒤 backend/ 가 바뀐 시각(씨앗)
    "live_commit": "",            # GX_COMMIT 없이 떴다 → 시각만이 증거다
    "expect": (EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE"),
}


SELF_CASES = (
    ((True,  False, True),  (EXIT_FAIL, "LIVE_COMMIT_MISMATCH")),
    ((True,  False, False), (EXIT_FAIL, "LIVE_COMMIT_MISMATCH")),   # 빨강이 회색을 이긴다
    ((True,  True,  False), (EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE")),
    ((False, False, False), (EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE")),
    ((True,  True,  True),  (EXIT_OK, "FRESH")),
    ((False, False, True),  (EXIT_OK, "FRESH")),                    # 모르면 시각으로만
)


def self_test() -> int:
    bad = [c for c, want in SELF_CASES if decide(*c) != want]
    if bad:
        print("[FRESH] 자기시험 **실패** — 판정표가 어긋난다: " + str(bad))
        return EXIT_FAIL
    #: 출생 표본을 **판정표에 그대로 태운다.** 표본을 주석에만 적으면 그것은 기록이지
    #:   시험이 아니고, 판정식이 흔들려도 아무도 모른다(D-310 이 만들어진 이유).
    b = BIRTH_SAMPLE
    got = decide(bool(b["live_commit"]), False, b["boot_epoch"] >= b["source_epoch"])
    if got != b["expect"]:
        print("[FRESH] 자기시험 **실패** — **출생 표본**(턴 H · 8000 이 2026-09-05 14:41 "
              "코드를 물고 있던 그 사례)이 " + str(got) + " 로 판정된다. 기대는 " +
              str(b["expect"]) + " — 이 도구는 자기가 태어난 이유를 못 잡는다")
        return EXIT_FAIL
    #: 둘째 출생 표본 — **낡은 작업자**. 판정기가 낡은 것을 실제로 잡는지 여기서 본다.
    w = BIRTH_SAMPLE_WORKER
    got = decide(bool(w["live_commit"]), False, w["boot_epoch"] >= w["source_epoch"])
    if got != w["expect"]:
        print("[FRESH] 자기시험 **실패** — **출생 표본 2**(P-116 · gx-celery-e 가 "
              "2026-09-05 코드를 물고 백업 주기를 이틀 죽인 그 사례)이 " + str(got) +
              " 로 판정된다. 기대는 " + str(w["expect"]) + " — 이 확장은 자기가 "
              "태어난 이유를 못 잡는다")
        return EXIT_FAIL
    #: 그리고 **반대쪽**도 본다. 낡은 것만 잡고 새 것도 잡으면 그것은 판정기가 아니라
    #:   상수다(D-301). 같은 표본을 소스보다 **뒤에** 뜬 것으로 바꾸면 초록이어야 한다.
    fresh_got = decide(False, False, (w["source_epoch"] + 60) >= w["source_epoch"])
    if fresh_got != (EXIT_OK, "FRESH"):
        print("[FRESH] 자기시험 **실패** — 같은 표본을 소스보다 뒤에 띄웠는데도 " +
              str(fresh_got) + " 다. 판정기가 아니라 상수다")
        return EXIT_FAIL
    print("[FRESH] 자기시험 통과 — 판정 규칙 " + str(len(SELF_CASES)) +
          "종 + **출생 표본 2**: ① 턴 H 의 8000(기동 2026-09-05 14:41 · 소스 09-06 "
          "→ 회색) ② P-116 의 gx-celery-e(기동 2026-09-05 · 소스 09-08 → 회색, "
          "같은 표본을 소스 뒤로 옮기면 초록) · 빨강이 회색을 이긴다")
    return EXIT_OK


def fmt(epoch: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch)) if epoch else "모름"


def run_all(json_path: str = "") -> int:
    """다섯 자리를 **각자 자기 소스**에 대해 재고 한 표로 낸다 (P-116).

    돌려주는 값은 **가장 나쁜 것**이다 — 넷이 초록이고 하나가 회색이면 회색이다.
    한 자리라도 못 재면 「전부 최신이다」는 말은 그 순간 거짓이 된다.
    """
    head = head_commit()
    rows, worst = [], EXIT_OK
    for spec in PROCESSES:
        src_epoch, src_why = source_time_for(spec["sources"])
        info = probe_sh(spec["container"], spec["match"])
        if not info.get("found"):
            why = info.get("error", "LIVE_NO_PROCESS")
            rows.append({"key": spec["key"], "role": spec["role"], "boot": 0,
                         "boot_str": "모름", "verdict": why, "exit": EXIT_UNDECIDABLE,
                         "source_epoch": src_epoch, "source_why": src_why,
                         "live_commit": "", "pid": 0, "delta_min": 0,
                         "detail": info.get("detail", "")})
            worst = max(worst, EXIT_UNDECIDABLE)
            continue
        boot = int(info["boot_epoch"])
        live_commit = info.get("env", {}).get("GX_COMMIT", "")
        commit_known = bool(live_commit and head)
        commit_same = bool(commit_known and (live_commit.startswith(head[:7])
                                             or head.startswith(live_commit[:7])))
        rc, why = decide(commit_known, commit_same, boot >= src_epoch)
        rows.append({"key": spec["key"], "role": spec["role"], "boot": boot,
                     "boot_str": fmt(boot), "verdict": why, "exit": rc,
                     "source_epoch": src_epoch, "source_why": src_why,
                     "live_commit": live_commit, "pid": info.get("pid", 0),
                     "delta_min": (boot - src_epoch) // 60, "detail": ""})
        #: 빨강이 회색을 이긴다 — 회색(2)보다 빨강(1)이 나쁘다. max() 로는 못 고른다.
        worst = EXIT_FAIL if (rc == EXIT_FAIL or worst == EXIT_FAIL) else max(worst, rc)

    mark = {EXIT_OK: "초록", EXIT_FAIL: "**빨강**", EXIT_UNDECIDABLE: "**회색**"}
    print("[FRESH] ══ 다섯 자리 · 각자 자기 소스에 대해 (P-116) · HEAD " +
          (head or "모름") + " ══")
    print("[FRESH] " + "자리".ljust(20) + " " + "판정".ljust(8) + " " +
          "기동".ljust(20) + " 소스대비  사유")
    for r in rows:
        d = ("+" + str(r["delta_min"]) if r["delta_min"] >= 0 else str(r["delta_min"])) + "분"
        print("[FRESH] " + r["key"].ljust(20) + " " + mark[r["exit"]].ljust(8) + " " +
              r["boot_str"].ljust(20) + " " + d.ljust(9) + " " + r["verdict"])
        print("[FRESH]   └ " + r["role"] + " · 소스 " + fmt(r["source_epoch"]) +
              " (" + r["source_why"] + ")" +
              (" · " + r["detail"] if r["detail"] else ""))
    if worst == EXIT_OK:
        print("[FRESH] 통과 — 다섯 자리가 **모두** 자기 소스보다 뒤에 떴다")
    else:
        bad = [r["key"] + "(" + r["verdict"] + ")" for r in rows if r["exit"] != EXIT_OK]
        print("[FRESH] " + mark[worst] + " — " + ", ".join(bad) +
              ". **한 자리라도 못 재면 「전부 최신」은 거짓이다** (D-301)")

    if json_path:
        out = Path(json_path)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "head_commit": head, "worst_exit": worst,
            "measured_at": fmt(int(time.time())), "processes": rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[FRESH] 증거: " + json_path)
    return worst


def prove_stale() -> int:
    """**살아 있는 다섯 자리로 음성 대조를 한다** — 판정기가 상수가 아님을 보인다.

    자기시험(`decide()` 표)은 판정 *식*이 맞는지만 본다. 그것은 실제로 재는 경로가
    **초록을 늘 뱉는 상수**여도 통과한다 [실측 2026-09-10 · 턴 O 에 실제로 의심한 자리].
    그래서 여기서는 **똑같은 살아 있는 측정**을 그대로 쓰되 소스 시각만 「지금」으로
    옮긴다. 기동은 전부 그보다 앞이므로 다섯이 **모두 회색**이어야 한다.
    하나라도 초록이면 그 자리의 초록은 측정이 아니라 상수다.

    ★ `backend/**` 를 건드리지 않는다 — 파일을 만지는 대신 **비교 대상 시각만** 민다.
    """
    now = int(time.time())
    print("[FRESH] ══ 음성 대조 — 소스 시각을 「지금」(" + fmt(now) +
          ") 으로 밀면 다섯이 **모두 회색**이어야 한다 ══")
    bad, seen = [], 0
    for spec in PROCESSES:
        info = probe_sh(spec["container"], spec["match"])
        if not info.get("found"):
            print("[FRESH]   " + spec["key"].ljust(20) + " 건너뜀 — " +
                  info.get("error", "LIVE_NO_PROCESS") + " (잴 프로세스가 없다)")
            continue
        seen += 1
        boot = int(info["boot_epoch"])
        rc, why = decide(False, False, boot >= now)
        ok = (rc, why) == (EXIT_UNDECIDABLE, "LIVE_OLDER_THAN_SOURCE")
        print("[FRESH]   " + spec["key"].ljust(20) + ("회색 " if ok else "**초록** ") +
              "기동 " + fmt(boot) + " → " + why + ("" if ok else "  ← 상수 의심"))
        if not ok:
            bad.append(spec["key"])
    if seen == 0:
        print("[FRESH] **회색** — 잴 프로세스가 하나도 없어 음성 대조를 못 했다")
        return EXIT_UNDECIDABLE
    if bad:
        print("[FRESH] **빨강** — " + ", ".join(bad) + " 가 낡은데도 초록이다. "
              "이 판정기의 초록은 측정이 아니다")
        return EXIT_FAIL
    print("[FRESH] 음성 대조 통과 — 살아 있는 " + str(seen) +
          "자리가 **모두** 회색으로 뒤집혔다. 초록은 상수가 아니라 측정이다")
    return EXIT_OK


def main() -> int:
    load_local_env()
    ap = argparse.ArgumentParser(description="게이트가 때리는 서버가 지금 코드를 무는가 (P-82/P-116)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="다섯 프로세스를 각자 자기 소스에 대해 잰다 (P-116)")
    ap.add_argument("--prove-stale", action="store_true",
                    help="음성 대조 — 소스를 「지금」으로 밀어 다섯이 회색으로 뒤집히는지 본다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL
    if args.prove_stale:
        return prove_stale()
    if args.all:
        return run_all(args.json or "")

    api, port = args.api, port_of(args.api)
    cont = os.environ.get("GX_ROUTE_CONTAINER", "").strip()
    head = head_commit()
    src_epoch, src_why = source_time()

    if not cont:
        print("[FRESH] 대상 서버 " + api + " · 기동 모름 · 커밋 모름")
        print("[FRESH] **판정 불가(회색)** — `LIVE_NO_CONTAINER`: "
              "`GX_ROUTE_CONTAINER` 가 없어 프로세스를 볼 자리가 없다 (.env.gates)")
        return EXIT_UNDECIDABLE

    info = probe(cont, port)
    if not info.get("found"):
        why = info.get("error", "LIVE_NO_PROCESS")
        print("[FRESH] 대상 서버 " + api + " · 기동 모름 · 커밋 모름")
        print("[FRESH] **판정 불가(회색)** — `" + why + "`: " + cont +
              " 안에서 :" + port + " 를 문 runserver 를 찾지 못했다. " +
              info.get("detail", ""))
        return EXIT_UNDECIDABLE

    boot = int(info["boot_epoch"])
    live_commit = info.get("env", {}).get("GX_COMMIT", "")
    commit_known = bool(live_commit and head)
    commit_same = bool(commit_known and (live_commit.startswith(head[:7])
                                         or head.startswith(live_commit[:7])))
    boot_after = boot >= src_epoch

    #: ★ 첫 줄은 **언제나 같은 세 가지**다 — 대상 서버 · 기동 시각 · 커밋 (P-82).
    print("[FRESH] 대상 서버 " + api + " · 기동 " + fmt(boot) + " · 커밋 " +
          (live_commit or "모름(GX_COMMIT 없이 떴다)"))
    print("[FRESH] [입력] 저장소 HEAD " + (head or "모름") + " · 소스 최신 " +
          fmt(src_epoch) + " (" + src_why + ") · 컨테이너 " + cont +
          " · pid " + str(info["pid"]) + " · 설정 " +
          info.get("env", {}).get("DJANGO_SETTINGS_MODULE", "모름"))

    rc, why = decide(commit_known, commit_same, boot_after)
    delta = boot - src_epoch
    if rc == EXIT_FAIL:
        print("[FRESH] **빨강** — `" + why + "`: 서버가 문 커밋 " + live_commit +
              " ≠ HEAD " + head + ". 이 서버를 때린 판정은 전부 **그 커밋에 대한 판정**이다")
    elif rc == EXIT_UNDECIDABLE:
        print("[FRESH] **판정 불가(회색)** — `" + why + "`: 기동이 소스보다 " +
              str(abs(delta) // 60) + "분 오래됐다 (" + src_why +
              "). 지금 코드를 문다고 **증명할 수 없다** — 회색은 초록이 아니다(D-301)")
    else:
        print("[FRESH] 통과 — 기동이 소스보다 " + str(delta // 60) + "분 뒤다" +
              (" · 커밋 " + live_commit + " = HEAD" if commit_known
               else " · 커밋은 모르지만 시각이 받친다"))

    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "api": api, "port": port, "container": cont, "pid": info["pid"],
            "boot_epoch": boot, "boot": fmt(boot),
            "live_commit": live_commit, "head_commit": head,
            "source_epoch": src_epoch, "source": fmt(src_epoch), "source_why": src_why,
            "verdict": why, "exit": rc,
            "measured_at": fmt(int(time.time())),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[FRESH] 증거: " + args.json)
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("서는 것이 **지금 커밋인가** — **분모 %d개**(`PROCESSES` 가 "
                  "못박은 프로세스: %s · 지금 셌다). 프로세스마다 기동 시각과 "
                  "그 소스의 마지막 수정을 댄다 — 소스가 더 새로우면 "
                  "**서는 것은 지금 코드가 아니다**"
                  % (len(PROCESSES),
                     " · ".join(_p["key"] for _p in PROCESSES))),
        target=os.environ.get("GX_API", "http://localhost:8000") + " (gx-shell 안 · 호스트에 포트가 없다)",
        as_="익명 — 기동 시각·커밋만 묻는다 (자격 없이 답하는 자리다)",
        source="살아 있는 서버가 스스로 낸 기동 시각·커밋 (HTTP)",
    )
    sys.exit(main())
