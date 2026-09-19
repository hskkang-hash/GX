#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-174 — **아침에 제품이 스스로 서는가** (2026-09-19 · 턴 V · 조율자).

무엇을 막는가 — **부팅 +198분에 아무것도 없었다** [실측 2026-09-18 · D-491]
---------------------------------------------------------------------------
09-18 아침, 기계가 켜진 지 3시간 18분 뒤에 도커가 없었다. **0/10**. 손으로 켜자
9/10 이 18초 만에 스스로 돌아왔다 — 정책은 옳았고 **그 위층이 비어 있었다.**

그런데 「위층」이 어디인지가 한 번에 안 보였다. 세 겹이다:

  ① 컨테이너 재시작 정책      `restart=unless-stopped` 인가 (없으면 엔진이 서도 안 온다)
  ② Docker Desktop 자동 시작  로그인할 때 뜨는가
  ③ **`com.docker.service`**  엔진 서비스가 `Automatic` 인가

★ **③ 이 뿌리였다** [실측 2026-09-18]. HKCU `Run` 키에는 `Docker Desktop.exe` 가
  **이미 있었는데도** 아침에 엔진이 없었다. 서비스가 `Manual` + `Stopped` 였기 때문이다.
  ① 만 보고 「다 unless-stopped 니 괜찮다」고 읽으면 **내일 아침도 0/10** 이다.

그래서 이 판정기는 **세 겹을 따로 센다** — 합치지 않는다. 고치는 방법이 다르기 때문이다
(①은 `docker update`, ②는 설정 파일, ③은 **관리자 권한**이 필요하다).

⚠ **이것은 아침을 대신 재지 않는다.** 여기 초록은 「내일 아침 서겠다」는 **약속의 모양**이고,
  실제 수는 부팅 뒤 `docs/agent/evidence/P-161/` 에 적히는 N/10 이다. 약속과 실측을
  한 칸에 적지 않는다(D-301).

⚠ 그리고 **남은 구멍 하나를 이 판정기가 소리 내어 말한다**: 컨테이너가 스스로 서도
  `gx-shell` 안의 게이트 서버 둘(runserver 8000 · SPA 3002)은 **손으로 띄운 프로세스**라
  돌아오지 않는다. 컨테이너 재시작 정책은 그 안의 프로세스를 모른다.

쓰는 법
-------
    python scripts/verify_autostart.py
    python scripts/verify_autostart.py --self-test

종료 코드: 0 세 겹 다 섰다 · 1 어긋난 겹이 있다 · 2 못 쟀다(도커 없음 등)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

EXIT_OK, EXIT_RED, EXIT_GRAY = 0, 1, 2

WANT_POLICY = "unless-stopped"
SERVICE = "com.docker.service"

#: 이 컨테이너들은 **아침에 서 있어야 한다.** 이름을 손으로 적는 이유: 그날 우연히 떠
#: 있던 것을 모수로 삼으면 「한 대가 통째로 빠진 아침」이 초록이 된다(D-301).
MUST_RUN = (
    "gx-gunicorn-e", "gx-celery-e", "gx-beat-e", "gx-nginx-e", "gx-shell",
    "postgres", "redis", "guardianx-source-minio-1", "guardianx-source-mailpit-1",
    "gx-fe-build",
)

#: ⚠ 컨테이너가 서도 **안에서 손으로 띄운 것**은 안 돌아온다. 이름을 적어 둔다 —
#:   적어 두지 않으면 「10/10」을 「다 됐다」로 읽는다.
HAND_STARTED_INSIDE = {
    "gx-shell": ("manage.py runserver 0.0.0.0:8000", "gate_spa_server.py (3002)"),
}


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, "%s: %s" % (type(exc).__name__, exc)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **함수로 떼어 둔다.** 자기시험이 무는 자리다 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge_policies(seen: dict[str, str]) -> list[str]:
    """① 컨테이너 재시작 정책. `seen` = {이름: 정책} · 없는 이름은 「안 돈다」."""
    bad = []
    for name in MUST_RUN:
        pol = seen.get(name)
        if pol is None:
            bad.append("%s 가 돌지 않는다 — 정책을 물을 대상이 없다" % name)
        elif pol != WANT_POLICY:
            bad.append("%s 의 재시작 정책이 `%s` 다 (원하는 것: `%s`) — "
                       "엔진이 서도 이 한 대는 안 온다" % (name, pol, WANT_POLICY))
    return bad


def judge_service(start_type: str | None) -> list[str]:
    """③ 엔진 서비스. `None` 은 **못 쟀다**이지 초록이 아니다."""
    if start_type is None:
        return ["GRAY:%s 의 StartType 을 못 읽었다" % SERVICE]
    if start_type.lower().startswith("auto"):
        return []
    return ["%s 의 StartType 이 `%s` 다 — **이것이 09-18 아침 0/10 의 뿌리다.** "
            "Run 키에 Docker Desktop 이 있어도 엔진 서비스가 수동이면 올라오지 않는다. "
            "관리자 한 줄: Set-Service %s -StartupType Automatic"
            % (SERVICE, start_type, SERVICE)]


def judge_desktop(auto_start: bool | None) -> list[str]:
    """② Docker Desktop 의 「로그인할 때 시작」."""
    if auto_start is None:
        return ["GRAY:Docker Desktop 의 AutoStart 설정을 못 읽었다"]
    if auto_start:
        return []
    return ["Docker Desktop 의 AutoStart 가 꺼져 있다 — 사람이 아이콘을 눌러야 엔진이 선다"]


def is_gray(problems: list[str]) -> bool:
    return bool(problems) and all(p.startswith("GRAY:") for p in problems)


# ═══════════════════════════════════════════════════════════════════════════
# 읽기 — 살아 있는 것에서 읽는다. 사진도 손 목록도 아니다
# ═══════════════════════════════════════════════════════════════════════════
def read_policies() -> dict[str, str] | None:
    rc, out = _run(["docker", "ps", "--format", "{{.Names}}"])
    if rc != 0:
        return None
    seen = {}
    for name in [ln.strip() for ln in out.splitlines() if ln.strip()]:
        rc2, pol = _run(["docker", "inspect", name, "--format",
                         "{{.HostConfig.RestartPolicy.Name}}"])
        if rc2 == 0:
            seen[name] = pol.strip()
    return seen


def read_service_start_type() -> str | None:
    if os.name != "nt":
        return None
    rc, out = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    "(Get-Service %s).StartType" % SERVICE])
    return out.strip() if rc == 0 and out.strip() else None


def read_desktop_autostart() -> bool | None:
    """⚠ 이 파일에는 설정만 읽는다. **다른 값은 건드리지도 찍지도 않는다.**"""
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return None
    p = Path(appdata) / "Docker" / "settings-store.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    v = data.get("AutoStart")
    return bool(v) if isinstance(v, bool) else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    if ap.parse_args().self_test:
        return self_test()

    seen = read_policies()
    if seen is None:
        print("[AUTOSTART] 회색 — `docker ps` 가 답하지 않는다. "
              "**엔진이 없는 것 자체가 아침의 답일 수 있다** — 부팅 뒤라면 그 수를 "
              "docs/agent/evidence/P-161/ 에 적어라")
        return EXIT_GRAY

    problems: list[str] = []
    p1 = judge_policies(seen)
    p2 = judge_desktop(read_desktop_autostart())
    p3 = judge_service(read_service_start_type())
    problems += p1 + p2 + p3

    print("[AUTOSTART] [입력] 돌고 있는 컨테이너 %d개 · 아침에 서야 하는 것 %d개"
          % (len(seen), len(MUST_RUN)))
    print("[AUTOSTART] ① 재시작 정책 `%s` : %d/%d"
          % (WANT_POLICY,
             sum(1 for n in MUST_RUN if seen.get(n) == WANT_POLICY), len(MUST_RUN)))
    print("[AUTOSTART] ② Docker Desktop AutoStart : %s" % ("어긋남" if p2 else "섰다"))
    print("[AUTOSTART] ③ %s StartType : %s" % (SERVICE, "어긋남" if p3 else "섰다"))
    for name, procs in HAND_STARTED_INSIDE.items():
        print("[AUTOSTART] ⚠ %s 는 서도 그 안의 손으로 띄운 것은 안 온다: %s"
              % (name, " · ".join(procs)))

    if problems:
        for p in problems:
            print("[AUTOSTART] %s — %s"
                  % ("회색" if p.startswith("GRAY:") else "빨강",
                     p[5:] if p.startswith("GRAY:") else p))
        return EXIT_GRAY if is_gray(problems) else EXIT_RED

    print("[AUTOSTART] 초록 — 세 겹 다 섰다. ⚠ 이것은 **약속의 모양**이고 수가 아니다. "
          "내일 아침 부팅 뒤의 N/10 이 증거다")
    return EXIT_OK


def self_test() -> int:
    """판정 규칙만 문다 — 도커도 윈도도 필요 없다."""
    ok_all = {n: WANT_POLICY for n in MUST_RUN}
    cases = [
        ("전부 unless-stopped 면 초록", judge_policies(ok_all), False),
        ("한 대가 `no` 면 빨강",
         judge_policies(dict(ok_all, **{"gx-shell": "no"})), True),
        ("한 대가 아예 안 돌면 빨강 (모수에서 빠지지 않는다)",
         judge_policies({k: v for k, v in ok_all.items() if k != "postgres"}), True),
        ("★ 서비스가 Manual 이면 빨강 — 09-18 의 뿌리", judge_service("Manual"), True),
        ("서비스가 Automatic 이면 초록", judge_service("Automatic"), False),
        ("Desktop AutoStart 가 False 면 빨강", judge_desktop(False), True),
        ("Desktop AutoStart 가 True 면 초록", judge_desktop(True), False),
    ]
    bad = 0
    for name, problems, want_red in cases:
        got = bool(problems) and not is_gray(problems)
        ok = got == want_red
        bad += 0 if ok else 1
        print("  %s %s" % ("O" if ok else "X", name))

    for name, problems in (("서비스를 못 읽으면 회색(초록 아님)", judge_service(None)),
                           ("Desktop 설정을 못 읽으면 회색", judge_desktop(None))):
        ok = is_gray(problems)
        bad += 0 if ok else 1
        print("  %s %s" % ("O" if ok else "X", name))

    #: ★ **출생 표본** (D-310) — 09-18 아침 그대로의 값이다 [실측]:
    #:   컨테이너 정책은 (gx-shell 을 고친 뒤 기준) 다 `unless-stopped` 인데
    #:   `com.docker.service` 는 `Manual` 이고 Docker Desktop 의 `AutoStart` 는 `False` 였다.
    #:   그날 부팅 +198분에 **0/10** 이었다. ①만 보고 초록을 내면 그 아침이 되풀이된다.
    #:   이 표본이 빨강이 아니면 이 게이트는 태어난 이유를 못 보는 것이다.
    BIRTH_SAMPLE = (ok_all, False, "Manual")
    b_pol, b_desk, b_svc = BIRTH_SAMPLE
    birth = judge_policies(b_pol) + judge_desktop(b_desk) + judge_service(b_svc)
    ok = bool(birth) and not is_gray(birth) and not judge_policies(b_pol)
    bad += 0 if ok else 1
    print("  %s ★ 출생 표본 (09-18 아침) — 정책이 10/10 이어도 "
          "서비스가 Manual 이면 초록이 아니다" % ("O" if ok else "X"))

    print("[SELF-TEST] %s" % ("전부 통과" if bad == 0 else "%d개 어긋남" % bad))
    return EXIT_OK if bad == 0 else EXIT_RED


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header
    gate_header(__file__,
                target="이 기계의 도커 엔진·컨테이너·서비스 (살아 있는 것)",
                as_="자격 없음 — 로컬 도커 소켓과 사용자 설정 파일을 읽는다",
                source="살아 있는 것을 **지금** 잰다 — docker ps/inspect · Get-Service · Docker Desktop 의 사용자 설정(읽는 그 순간의 값). 사진도 손 목록도 아니다")
    raise SystemExit(main())
