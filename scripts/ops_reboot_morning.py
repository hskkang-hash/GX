#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-20 — **재부팅 아침의 증거 자리**. 수를 지어내지 않는다 (턴 AB · 차선 F).

    턴 AA 차선 Q: 「? 재부팅 아침 N/10 — **회색**. `docs/agent/evidence/OPS-20` 이
    **없다**(증거 0건 · 다섯 턴째)」 · 「그 셋은 **0 점이 아니라 회색**이고, PR 의
    하한·상한이 **30점 벌어진** 이유가 정확히 그것이다」

이 파일이 만드는 것은 **자리**다. 수가 아니다
----------------------------------------------
재부팅은 **대표 PC 의 손**이다(WO §7 「매일 아침 Docker `com.docker.service` 자동 시작
+ 재부팅 1회」). 차선은 그 손을 대신할 수 없다. 그러니 이 판정기가 할 수 있는 일은
둘뿐이고, 그 둘을 **갈라서** 적는다:

    ㉠ **준비** [오늘 실측]  재부팅이 오면 **스스로 설 수 있는 자리인가** —
                            컨테이너마다 `RestartPolicy` 가 무엇인가
    ㉡ **아침** [기록]      실제 재부팅 뒤 아침이 **몇 번 성공했는가** —
                            오늘은 **0건**이고, **0건은 0점이 아니라 회색**이다

㉠은 재부팅 없이도 참이 되는 사실이고, ㉡은 재부팅 없이는 **절대로** 참이 되지 않는다.
둘을 한 칸에 뭉치면 「정책은 섰다」가 「아침이 섰다」로 읽힌다 — 그것이 이 저장소가
내내 걷어낸 병(D-301 · 「고쳤다」와 「고친 것이 돌고 있다」)이다.

★★ **아침 한 건을 어떻게 세는가 — 지어낼 수 없게 만들었다**
------------------------------------------------------------
아침 한 건은 이 도구가 **판단**하지 않는다. `--record-morning` 을 받았을 때만 한 줄이
늘고, 그때도 **컨테이너가 이번 부팅에서 다시 선 것이 실측으로 보일 때만** 는다:
모든 컨테이너의 `StartedAt` 이 **직전 기록 시각보다 뒤**여야 한다. 그렇지 않으면
**거부한다**(exit 1). 「아침이었다」고 사람이 적는 것으로는 한 줄도 안 는다.

    PYTHONIOENCODING=utf-8 python scripts/ops_reboot_morning.py       # 자리를 세우고 잰다
    PYTHONIOENCODING=utf-8 python scripts/ops_reboot_morning.py --record-morning
    python scripts/ops_reboot_morning.py --self-test                  # 도커 없이

종료 코드: 0 잴 것을 다 쟀다 · 1 **준비가 안 됐다**(스스로 못 서는 컨테이너가 있다) ·
          2 **못 쟀다**(도커 없음). 아침 0건은 **1 이 아니라 0** 이다 —
          아직 안 온 아침을 실패로 세면 대표 손을 차선의 빨강으로 적는 것이 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "OPS-20" / "reboot_mornings.json"
TAG = "[OPS-20]"

#: 대장이 세는 아침의 수. **분모는 손으로 적지 않는다** — 여기 한 곳에만 있다.
MORNINGS_TARGET = 10

#: 스스로 다시 서는 정책. `no` 는 **재부팅 뒤 안 선다**.
SELF_STARTING = ("always", "unless-stopped", "on-failure")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []
    cons = facts.get("containers")
    if cons is None:
        return [("㉠ 준비", False, "**못 쟀다** — 도커에 닿지 못했다. 회색은 초록이 아니다"),
                ("㉡ 아침", False, "못 쟀다")]

    cannot = [c["name"] for c in cons
              if (c.get("restart_policy") or "no") not in SELF_STARTING]
    out.append(("㉠ 준비", not cannot,
                "컨테이너 %d개가 전부 스스로 다시 선다" % len(cons) if not cannot
                else "**재부팅 뒤 스스로 안 서는 컨테이너**: %s — 재시작 정책이 `no` 다. "
                     "이 빨강은 **다음에 그 컨테이너를 띄우는 사람**이 "
                     "`--restart unless-stopped` 로 지운다" % ", ".join(cannot)))

    mornings = facts.get("mornings")
    n = len(mornings or [])
    out.append(("㉡ 아침", n >= MORNINGS_TARGET,
                "아침 %d/%d" % (n, MORNINGS_TARGET) if n
                else "**아침 0건 — 회색이다. 0점이 아니다.** 재부팅은 대표 PC 의 손이고"
                     "(WO §7), 차선은 그 손을 대신할 수 없다. 자리는 섰다: %s"
                     % EVIDENCE.as_posix()))
    return out


def can_record(cons: list, last_recorded_at: str | None) -> tuple[bool, str]:
    """아침 한 줄을 늘려도 되는가. **사람의 말이 아니라 `StartedAt` 이 답한다.**"""
    if not cons:
        return False, "컨테이너를 못 읽었다 — 아침을 셀 근거가 없다"
    missing = [c["name"] for c in cons if not c.get("started_at")]
    if missing:
        return False, "시작 시각을 못 읽은 컨테이너: %s" % ", ".join(missing)
    if last_recorded_at is None:
        return True, "첫 기록 — 이번 부팅에서 선 컨테이너 %d개" % len(cons)
    newest_floor = min(c["started_at"] for c in cons)
    if newest_floor <= last_recorded_at:
        return False, ("**거부한다** — 컨테이너 중에 지난 기록(%s)보다 **먼저 선 것**이 "
                       "있다(가장 오래된 시작 %s). 재부팅이 없었는데 아침을 세는 것은 "
                       "수를 지어내는 것이다" % (last_recorded_at, newest_floor))
    return True, "컨테이너 %d개가 전부 지난 기록(%s) 뒤에 다시 섰다" % (
        len(cons), last_recorded_at)


def self_test() -> int:
    bad = []
    if [p for _, p, _ in judge({})] != [False, False]:
        bad.append("못 쟀는데 초록이 난다")

    good = {"containers": [{"name": "a", "restart_policy": "unless-stopped",
                            "started_at": "2026-09-21T10:00:00Z"}],
            "mornings": []}
    r = judge(good)
    if [p for _, p, _ in r] != [True, False]:
        bad.append("아침 0건인데 ㉡이 초록이다: %s" % [p for _, p, _ in r])
    if "0점이 아니" not in r[1][2]:
        bad.append("아침 0건을 0점으로 적는다")

    naked = dict(good, containers=[{"name": "a", "restart_policy": "no",
                                    "started_at": "2026-09-21T10:00:00Z"}])
    if judge(naked)[0][1]:
        bad.append("재시작 정책이 `no` 인데 ㉠이 초록이다")

    full = dict(good, mornings=[{"at": "x"}] * MORNINGS_TARGET)
    if not judge(full)[1][1]:
        bad.append("아침 %d건인데 ㉡이 빨갛다" % MORNINGS_TARGET)

    cons = [{"name": "a", "started_at": "2026-09-21T10:00:00Z"},
            {"name": "b", "started_at": "2026-09-21T10:00:05Z"}]
    if not can_record(cons, None)[0]:
        bad.append("첫 기록을 거부한다")
    if can_record(cons, "2026-09-21T10:00:03Z")[0]:
        bad.append("재부팅 없이 아침이 는다 — 수를 지어낸다")
    if not can_record(cons, "2026-09-21T09:00:00Z")[0]:
        bad.append("전부 다시 섰는데 기록을 거부한다")
    if can_record([], None)[0]:
        bad.append("컨테이너 0개인데 아침을 센다")

    if bad:
        print("%s 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):" % TAG)
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("%s 자기시험 통과 — 정상 2 · 음성 6" % TAG)
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 수집 — **도커에게 한 번만 묻는다** (차선 열하나가 같은 엔진을 쓴다)
# ═══════════════════════════════════════════════════════════════════════════
def containers() -> list | None:
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    fmt = ("{{.Name}}\t{{.State.Status}}\t{{.State.StartedAt}}"
           "\t{{.HostConfig.RestartPolicy.Name}}\t{{.RestartCount}}")
    try:
        ids = subprocess.run(["docker", "ps", "-aq"], capture_output=True,
                             timeout=120, env=env)
        if ids.returncode != 0:
            return None
        wanted = ids.stdout.decode("utf-8", "replace").split()
        if not wanted:
            return []
        p = subprocess.run(["docker", "inspect", "--format", fmt] + wanted,
                           capture_output=True, timeout=180, env=env)
        if p.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    out = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        out.append({"name": parts[0].lstrip("/"), "status": parts[1],
                    "started_at": parts[2], "restart_policy": parts[3] or "no",
                    "restart_count": parts[4]})
    return out


def load() -> dict:
    if EVIDENCE.is_file():
        try:
            return json.loads(EVIDENCE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    # ★ 자리를 세운다. **아침은 빈 목록이다 — 0 이 아니라 아직 없는 것이다.**
    return {"what": "OPS-20 재부팅 아침 — 대표 PC 재부팅 뒤 스스로 다 섰는가",
            "denominator": MORNINGS_TARGET,
            "denominator_note": "분모는 손으로 적지 않는다 — "
                                "`scripts/ops_reboot_morning.py::MORNINGS_TARGET`",
            "measured": False,
            "grey_note": "아침 0건은 **0점이 아니라 회색**이다. 재부팅은 대표 손이고"
                         "(WO §7), 차선은 그 손을 대신할 수 없다",
            "mornings": [], "readiness": None}


def main() -> int:
    ap = argparse.ArgumentParser(description="OPS-20 재부팅 아침 — 증거 자리")
    ap.add_argument("--record-morning", action="store_true",
                    help="이번 부팅을 아침 한 건으로 **기록한다**. "
                         "컨테이너가 전부 다시 선 것이 보일 때만 는다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    book = load()
    cons = containers()
    if cons is None:
        print("%s **판정 불가(exit 2)** — 도커에 닿지 못했다. 「0건」이 아니라 "
              "「못 쟀다」다" % TAG)
        return EXIT_UNDECIDABLE

    print("%s 컨테이너 %d개 — 재부팅이 오면 스스로 서는가 [실측 %s]"
          % (TAG, len(cons), time.strftime("%Y-%m-%d %H:%M:%S")))
    print()
    print("| 컨테이너 | 상태 | 재시작 정책 | 스스로 서나 | 이번 시작 |")
    print("|---|---|---|---|---|")
    for c in sorted(cons, key=lambda x: x["name"]):
        pol = c["restart_policy"]
        print("| %s | %s | `%s` | %s | %s |"
              % (c["name"], c["status"], pol,
                 "선다" if pol in SELF_STARTING else "**안 선다**",
                 c["started_at"][:19]))
    print()

    last = (book.get("mornings") or [{}])[-1].get("recorded_at") \
        if book.get("mornings") else None
    if args.record_morning:
        ok, why = can_record(cons, last)
        print("%s 아침 기록 — %s" % (TAG, why))
        if ok:
            book["mornings"].append({
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "containers": len(cons),
                "all_running": all(c["status"] == "running" for c in cons),
                "oldest_start": min(c["started_at"] for c in cons),
                "by": "scripts/ops_reboot_morning.py --record-morning"})
            book["measured"] = True
        else:
            print("%s **한 줄도 안 늘렸다.** 수를 지어내지 않는다" % TAG)

    book["readiness"] = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "containers": cons,
        "self_starting": [c["name"] for c in cons
                          if c["restart_policy"] in SELF_STARTING],
        "not_self_starting": [c["name"] for c in cons
                              if c["restart_policy"] not in SELF_STARTING]}

    rows = judge({"containers": cons, "mornings": book.get("mornings")})
    print("## 판정")
    print()
    for name, passed, why in rows:
        print("  %s %-8s %s" % ("OK  " if passed else "회색", name, why))
    print()

    try:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(json.dumps(book, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print("%s 자리: %s (아침 %d/%d)"
              % (TAG, EVIDENCE.as_posix(), len(book.get("mornings") or []),
                 MORNINGS_TARGET))
    except OSError as exc:
        print("%s ⚠ 자리를 못 적었다: %s" % (TAG, exc))
        return EXIT_UNDECIDABLE

    # ★ **아침 0건으로는 빨강을 내지 않는다.** 아직 안 온 아침을 실패로 세면
    #   대표 손을 차선의 빨강으로 적는 것이 되고, 그런 빨강은 아무도 못 지운다.
    return EXIT_OK if rows[0][1] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
