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

쓰는 법
-------
    python scripts/verify_live_freshness.py --self-test
    python scripts/verify_live_freshness.py                 # GX_API 를 잰다
    python scripts/verify_live_freshness.py --api http://localhost:8000
    python scripts/verify_live_freshness.py --json docs/agent/evidence/P-82/fresh.json

종료 코드: 0 신선 · 1 다르다(빨강) · 2 판정 불가(회색)
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
    print("[FRESH] 자기시험 통과 — 판정 규칙 " + str(len(SELF_CASES)) +
          "종 + **출생 표본** (턴 H 의 8000: 기동 2026-09-05 14:41 · 소스 09-06 · "
          "GX_COMMIT 없음 → 회색) · 빨강이 회색을 이긴다")
    return EXIT_OK


def fmt(epoch: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch)) if epoch else "모름"


def main() -> int:
    load_local_env()
    ap = argparse.ArgumentParser(description="게이트가 때리는 서버가 지금 코드를 무는가 (P-82)")
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

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
    sys.exit(main())
