#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**순회 한 바퀴.** 서 있는 판정기를 한 번에 돌고 그 자리를 적는다 (2026-09-04 · 차선 E3).

    "순회 1바퀴 로그"  — RESUME_NEXT 2026-09-04 §E3 첫 증거

왜 순회가 따로 있어야 하나
--------------------------
판정기는 여럿이고 각각 자기 자리만 본다. 그런데 운영자가 아침에 묻는 질문은 하나다:
**「지금 어디가 빨간가.」** 그 질문에 답하려면 누군가 한 바퀴를 돌아야 하고, 돌지 않으면
초록인 자리만 눈에 띈다 — 아무도 안 돌리는 판정기는 **회색인 채로 잊힌다**(D-311 계열).

★ 세 색을 **가른다** — 이 순회의 요점이 그것이다
------------------------------------------------
    0  초록   쟀고 통과
    1  빨강   쟀고 실패            ← 고칠 자리가 있다
    2  **회색** 못 쟀다            ← **초록이 아니다.** 자격증명·환경이 없어 판정 자체를 못 했다

회색을 초록 옆에 놓으면 「대부분 초록」으로 보이고, 그 착시가 D-341 이 적은 그 자리다.
그래서 이 순회는 **회색을 따로 세고**, 회색이 하나라도 있으면 순회 자체가 회색이다.

★ 「부분」은 상태가 아니다
--------------------------
이 순회는 「몇 %」를 만들지 않는다. 빨강 1 · 회색 0 은 「거의 초록」이 아니라 **빨강**이다.

    python scripts/ops_patrol.py --evidence docs/agent/evidence/OPS-PATROL/round.md
    python scripts/ops_patrol.py --self-test

종료 코드: 0 전부 초록 · 1 빨강이 있다 · 2 **회색이 있다**(빨강보다 먼저 본다)
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 컨테이너 안에서 돌아야 하는 것들 — dj-core 가 거기에만 있다.
IN_CONTAINER = "gx-shell"

#: 한 바퀴의 자리들. **여기 없는 판정기는 순회가 안 돈다** — 새로 세우면 여기 적는다.
#:
#: ⚠ 「무겁고 부수효과가 있는 것」은 순회에 넣지 않는다. 되돌리기 훈련(OPS-08)은 DB 를
#:   만들었다 지우고 6분이 걸리며, 백업(OPS-12)은 볼륨에 파일을 쌓는다. 아침마다 도는
#:   순회가 그런 일을 하면 **순회 자체가 사고의 원인**이 된다. 그 둘은 사람이 부른다.
STOPS = (
    ("감시 3종 (liveness·lag·fill)", "container",
     ["python", "/repo/scripts/ops_monitor.py", "--check"]),
    ("시드 역할 사람 U2·U4", "container",
     ["python", "/repo/scripts/verify_seed_roles.py"]),
    ("경보 발송처 표 (OPS-10)", "container",
     ["python", "/repo/scripts/ops_alert_routing.py"]),
    ("로그 수집기·보존 (OPS-07)", "host",
     [sys.executable, "scripts/ops_log_collectors.py"]),
)

COLOR = {0: "초록", 1: "**빨강**", 2: "**회색**"}


def judge(results: list[tuple[str, int, str]]) -> tuple[int, str]:
    """순회 한 바퀴의 색. **회색을 빨강보다 먼저 본다.**

    회색이 있으면 「빨강이 몇 개인지」를 아직 모른다 — 못 잰 자리 뒤에 무엇이 있는지
    모르는 채로 「빨강 1개」라고 말하면 그 수가 거짓이 된다.
    """
    grey = [n for n, rc, _ in results if rc == 2]
    red = [n for n, rc, _ in results if rc == 1]
    if grey:
        return EXIT_UNDECIDABLE, "회색 %d · 빨강 %d — **회색이 있으므로 이 순회는 회색이다**" % (
            len(grey), len(red))
    if red:
        return EXIT_FAIL, "빨강 %d — %s" % (len(red), ", ".join(red))
    return EXIT_OK, "%d자리 전부 초록" % len(results)


def self_test() -> int:
    ok = True
    ok &= judge([("a", 0, ""), ("b", 0, "")])[0] == EXIT_OK
    ok &= judge([("a", 0, ""), ("b", 1, "")])[0] == EXIT_FAIL
    ok &= judge([("a", 1, ""), ("b", 2, "")])[0] == EXIT_UNDECIDABLE
    ok &= judge([])[0] == EXIT_OK
    # 회색 하나가 빨강 셋보다 **먼저** 온다
    ok &= judge([("a", 1, ""), ("b", 1, ""), ("c", 1, ""), ("d", 2, "")])[0] == EXIT_UNDECIDABLE
    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


#: 저장소 뿌리의 `.env`(gitignored). **값은 저장소에 없다**(D-204) — 이름만 안다.
#: 이것을 안 넘기면 컨테이너에 구워진 값(minio.invalid)이 쓰이고, 감시 3종은
#: 「객체저장이 죽었다」고 운다. 그것은 저장소의 사실이 아니라 **순회가 주소를 안 준
#: 사실**이다 — 늑대를 부르는 순회는 아무도 안 본다.
LOCAL_ENV_FILE = ".env"
MINIO_KEYS = ("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD")


def minio_env():
    """`.env` 에서 MinIO 자격증명을 빌려 온다. 없으면 **없다고 말한다.**"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, LOCAL_ENV_FILE)
    got = {}
    try:
        with io.open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() in MINIO_KEYS:
                    got[k.strip()] = v.strip()
    except OSError:
        return [], ("저장소 뿌리에 `%s` 가 없다 — MinIO 주소를 못 넘긴다. "
                    "객체저장 경보는 **환경의 사실**로 읽어야 한다" % LOCAL_ENV_FILE)
    if len(got) < len(MINIO_KEYS):
        return [], "`%s` 에 %s 가 다 있지 않다" % (LOCAL_ENV_FILE, ", ".join(MINIO_KEYS))
    return (["-e", "MINIO_ENDPOINT=minio:9000",
             "-e", "MINIO_ACCESS_KEY=%s" % got["MINIO_ROOT_USER"],
             "-e", "MINIO_SECRET_KEY=%s" % got["MINIO_ROOT_PASSWORD"]],
            "`%s` 에서 MinIO 자격증명을 넘겼다 (값은 적지 않는다)" % LOCAL_ENV_FILE)


def run_stop(where, argv, extra_env=None):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    if where == "container":
        cmd = ["docker", "exec", "-w", "/app", "-e", "PYTHONPATH=/app",
               "-e", "DJANGO_SETTINGS_MODULE=config.settings",
               *(extra_env or []), IN_CONTAINER, *argv]
    else:
        cmd = argv
    try:
        # ★ `text=True` 를 쓰지 않는다. 윈도우에서는 로케일(cp949)로 풀어 **한글이 깨진다** —
        #   깨진 글자는 판정을 못 읽게 만들고, 못 읽는 증거는 증거가 아니다 [실측 2026-09-04].
        p = subprocess.run(cmd, capture_output=True, timeout=900, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 2, "부르지 못했다: %s: %s" % (type(exc).__name__, exc)
    body = (p.stdout + b"\n" + p.stderr).decode("utf-8", "replace")
    # ★ 무엇을 남길지가 순회의 값을 정한다. **빨간 줄을 버리면 초록만 남는다** —
    #   첫 판이 ALARM·UNKNOWN 을 안 남겨서 「전부 OK 인데 경보 2개」가 찍혔다 [실측].
    keep = [l for l in body.splitlines()
            if l.strip().startswith(("OK", "FAIL", "ALARM", "UNKNOWN", "판정",
                                     "[verify", "[OPS", "①", "②", "③", "④"))
            or "판정 불가" in l]
    return p.returncode, "\n".join(keep[-16:]) or (body.strip().splitlines() or [""])[-1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    started = time.time()
    say("순회 시작 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    extra, note = minio_env()
    say()
    say("- 환경: %s" % note)
    say()
    results: list[tuple[str, int, str]] = []
    for name, where, argv in STOPS:
        t0 = time.time()
        rc, tail = run_stop(where, argv, extra)
        results.append((name, rc, tail))
        say("### %s" % name)
        say()
        say("- 도는 자리: `%s` · 명령: `%s`"
            % (where, " ".join(argv[-2:] if where == "container" else argv[1:])))
        say("- 종료 코드 **%d** → %s · %.1f초" % (rc, COLOR.get(rc, "알 수 없음(%d)" % rc),
                                                time.time() - t0))
        say()
        say("```")
        for l in tail.splitlines():
            say(l)
        say("```")
        say()

    verdict, why = judge(results)
    say("## 한 바퀴의 결론")
    say()
    say("| 자리 | 색 | 종료 코드 |")
    say("|---|---|---|")
    for name, rc, _ in results:
        say("| %s | %s | %d |" % (name, COLOR.get(rc, "?"), rc))
    say()
    say("한 바퀴의 색: %s — %s" % (COLOR.get(verdict, "?"), why))
    say()
    say("걸린 시간 %.0f초. 순회에 **넣지 않은 것**: 되돌리기 훈련(OPS-08 · 6분 · DB 를"
        % (time.time() - started))
    say("만들었다 지운다) · 볼륨 백업(OPS-12 · 볼륨에 파일을 쌓는다). 아침마다 도는 순회가")
    say("그런 일을 하면 **순회 자체가 사고의 원인**이 된다 — 그 둘은 사람이 부른다.")

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# 순회 1바퀴 (%s)\n\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_patrol.py` 가 실행하며 적었다.**\n"
                        "종료 코드는 각 판정기가 실제로 낸 값이다 — 회색(2)은 초록이 아니다.\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return verdict


if __name__ == "__main__":
    raise SystemExit(main())
