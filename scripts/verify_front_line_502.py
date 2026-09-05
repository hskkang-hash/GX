#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-13a — **502 가 언제 나는지**를 대조와 함께 잰다 (2026-09-05 · 턴 D · 차선 E).

    OPS-13a 앞단이 뒷단의 워커 재활용을 삼킨다 (502 3건 / 3,600 요청)

왜 이 판정기가 따로 있나 — **부하 표를 하나 더 만들지 않기 위해서다**
--------------------------------------------------------------------
부하는 `scripts/verify_perf_budget.py --measure` 가 낸다. 표가 둘이면 다음 사람이
어느 표를 봐야 하는지 모른다. 이 파일은 **부하를 걸지 않는다** — 그 부하가 남긴
자국 둘(앞단 접근로그 · 뒷단 재활용 로그)을 **맞대어 읽을** 뿐이다.

    ① 앞단 접근로그   `gx-nginx-e:/var/log/nginx/gx-front.access.log`
    ② 뒷단 재활용     `docker logs -t gx-gunicorn-e` 의 `Autorestarting worker`

★ **대조 없이 판정하지 않는다** (턴 C 가 배운 그대로)
------------------------------------------------------
「502 가 워커 재활용 옆에서 났다」는 문장은 **그 자체로는 아무 뜻이 없다.** 재활용이
2,700초에 130번 일어나면 창을 ±5초로만 넓혀도 **무엇이든** 재활용 옆에 놓인다 —
[실측 2026-09-05 · 턴 C] ±5초에서는 **정상 응답도 91%**가 재활용 옆이었다.

그래서 이 판정기는 **언제나 둘을 함께 낸다**:

    양성  502 응답이 재활용과 같은 초에 난 비율
    음성  **정상 200 응답**이 재활용과 같은 초에 난 비율   ← 이것이 없으면 표를 못 읽는다

그리고 **둘이 갈리지 않으면 초록도 빨강도 아니라 회색이다.** 갈리지 않는 창에서 낸
90% 는 「재활용 탓」이 아니라 「재활용이 잦다」는 말일 뿐이다.

무엇을 보는가 — 넷
------------------
  ① 표본        502 가 몇 건이고 대조(200)가 몇 건인가. 대조가 없으면 회색
  ② 설명        **모든 502 가 같은 초의 재활용으로 설명되는가.** 설명 안 되는 502 가
                하나라도 있으면 그것은 **다른 결함**이다 — 알려진 창에 묻으면 안 된다
  ③ 대조 분리   양성 비율 − 음성 비율 ≥ 문턱. 안 갈리면 **회색**(창이 아무것도 안 가른다)
  ④ 삼킴        앞단이 재시도로 **되살린** 건수가 0 이 아닌가. 0 이면 앞단의 재시도
                설정이 빠진 것이고, 그때 502 수는 「뒷단이 나쁘다」가 아니라 「앞단이
                일을 안 한다」다

    python scripts/verify_front_line_502.py --self-test
    python scripts/verify_front_line_502.py --since-line 27795 \\
        --evidence docs/agent/evidence/OPS-13a/coincidence.md

종료 코드: `0` 쟀고 통과 · `1` 쟀고 실패 · `2` **못 쟀다**(로그에 못 닿음 · 대조 없음).


★ 출생 표본 (D-310) — **이 도구를 만들게 한 바로 그 사례**
----------------------------------------------------------
턴 C 가 「502 는 워커 재활용과 같은 초에 90% 」라고 적고 이렇게 덧붙였다:

    ⚠ **대조가 없었으면 이 표를 못 읽는다** — ±5초로 넓히면 **정상 응답도 91%가 그 옆**이다.

즉 「502 옆에 재활용이 있다」만으로는 아무것도 증명되지 않는다. 재활용이 자주 나면
**무엇이든** 그 옆에 있다. 이 도구가 태어난 이유가 그것이고, 그래서 이 도구는
**502 와 정상 200 을 같은 창으로 함께 세지 않으면 판정을 내지 않는다.**

그 사례가 자기시험의 「겹침」 갈래에 fixture 로 박혀 있다 — 502 도 정상도 다 재활용
옆에 있는 로그를 먹이면 이 도구는 **초록을 내지 않고 회색(판정 불가)** 을 낸다.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

FRONT_CONTAINER = "gx-nginx-e"
BACK_CONTAINER = "gx-gunicorn-e"
ACCESS_PATH = "/var/log/nginx/gx-front.access.log"

#: 창 셋을 다 낸다. **가르는 것은 같은 초뿐**이라는 것을 표가 스스로 말하게 한다.
WINDOWS_SEC = (0, 1, 5)

#: 양성과 음성이 이만큼 갈려야 「같은 초」가 뜻을 갖는다. [실측 2026-09-05 · 턴 C]
#: 90% 대 21% = 69%p 였다. 30%p 는 그 절반보다 낮은 자리에 둔 문턱이다 —
#: 문턱을 실측값 가까이 두면 다음 판에서 조금만 흔들려도 색이 뒤집힌다.
SEPARATION_PP = 30.0

#: 음성 대조로 쓸 정상 응답의 최대 표본. 전수를 쓰면 3,700건 × 130 재활용의
#: 곱셈이 되어 느리다. **앞에서부터 고르게** 솎는다(뒤쪽만 쓰면 부하 후반만 본다).
CONTROL_SAMPLE = 400

_ACCESS = re.compile(
    r'^(?P<addr>\S+) \[(?P<t>\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}) (?P<tz>[+-]\d{4})\]'
    r' "(?P<req>[^"]*)" (?P<status>\d{3}) \S+ (?P<rt>\S+) "(?P<up>[^"]*)"')
_DOCKER_TS = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다.** 자기시험이 합성 표를 먹인다 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def coincidence(events: list[datetime], marks: list[datetime], window: int) -> int:
    """`events` 중 `marks` 와 `window` 초 안에 놓인 것의 수."""
    if not marks:
        return 0
    span = timedelta(seconds=window)
    return sum(1 for e in events if any(abs(e - m) <= span for m in marks))


def judge(facts: dict) -> list[tuple[str, str, str]]:
    """돌려주는 것: `(이름, "pass"|"fail"|"gray", 까닭)`.

    **회색을 초록으로 접지 않는다** — 못 가른 창에서 낸 수는 초록이 아니다(D-301).
    """
    out: list[tuple[str, str, str]] = []
    n502 = facts.get("n502")
    n200 = facts.get("n200")
    restarts = facts.get("n_restarts")
    if n502 is None or n200 is None or restarts is None:
        return [("① 표본", "gray", "**못 쟀다** — 로그에 닿지 못했다")]

    # ── ① 표본 ────────────────────────────────────────────────────────────
    if restarts == 0:
        out.append(("① 표본", "gray",
                    "재활용이 **0건**이다 — 맞댈 자국이 없다. `max_requests` 가 꺼졌거나 "
                    "부하가 워커 하나당 상한에 못 미쳤다"))
    elif n200 == 0:
        out.append(("① 표본", "gray",
                    "**음성 대조가 없다**(정상 200 이 0건) — 양성만으로는 표를 못 읽는다"))
    elif n502 == 0:
        out.append(("① 표본", "pass",
                    "이번 부하에서 502 **0건** — 맞댈 양성이 없다. "
                    "0 은 좋은 소식이되 **이 부하 이 순간의** 0 이다"))
    else:
        out.append(("① 표본", "pass",
                    "502 %d건 · 대조 200 %d건 · 재활용 %d건" % (n502, n200, restarts)))

    if n502 == 0:
        # 양성이 없으면 ②③은 판정할 것이 없다. **없는 것을 초록으로 적지 않는다.**
        out.append(("② 설명", "gray", "502 가 없어 설명할 대상이 없다"))
        out.append(("③ 대조 분리", "gray", "502 가 없어 갈릴 것이 없다"))
    else:
        same502 = facts["hit502"][0]
        unexplained = n502 - same502
        out.append(("② 설명", "pass" if unexplained == 0 else "fail",
                    "502 %d건 전부가 재활용과 **같은 초**에 났다" % n502
                    if unexplained == 0 else
                    "**같은 초의 재활용으로 설명되지 않는 502 가 %d건** — 알려진 창에 "
                    "묻지 마라. 이것은 다른 결함이다" % unexplained))

        pos = 100.0 * facts["hit502"][0] / n502
        neg = 100.0 * facts["hit200"][0] / n200 if n200 else 0.0
        gap = pos - neg
        out.append(("③ 대조 분리", "pass" if gap >= SEPARATION_PP else "gray",
                    "같은 초 — 502 %.0f%% 대 정상 %.0f%% (차 %.0f%%p ≥ %.0f%%p)"
                    % (pos, neg, gap, SEPARATION_PP) if gap >= SEPARATION_PP else
                    "같은 초 — 502 %.0f%% 대 정상 %.0f%% (차 %.0f%%p < %.0f%%p). "
                    "**갈리지 않는다** — 이 창은 아무것도 안 가른다. 회색이지 빨강이 아니다"
                    % (pos, neg, gap, SEPARATION_PP)))

    # ── ④ 삼킴 ────────────────────────────────────────────────────────────
    retried = facts.get("retried", 0)
    rescued = facts.get("rescued", 0)
    if retried == 0 and n502 == 0:
        # ★ **삼킬 것이 없었던 것과 삼키지 못한 것은 다르다.**
        #   [실측 2026-09-05 · 턴 D] `max_requests` 를 끄고 재니 재시도 0 · 502 0 이
        #   나왔는데, 첫 판은 그것을 「앞단이 아무것도 못 되살렸다」로 빨강을 찍었다.
        #   앞단은 멀쩡했다 — 뒷단이 한 번도 연결을 끊지 않았을 뿐이다. 판정기가
        #   **좋은 소식을 결함으로 읽은** 자리이고, 그런 빨강은 다음 사람을 엉뚱한
        #   파일로 보낸다.
        out.append(("④ 삼킴", "gray",
                    "삼킬 것이 **없었다** — 재시도 0건 · 502 0건. 뒷단이 이 부하 동안 "
                    "연결을 한 번도 끊지 않았다는 뜻이고, 앞단의 재시도 설정이 옳은지는 "
                    "**이 판으로는 못 잰다**"))
    else:
        out.append(("④ 삼킴", "pass" if rescued > 0 else "fail",
                    "앞단이 재시도 %d건 중 **%d건을 되살렸다**(손님은 200 을 봤다) · "
                    "새어 나간 502 %d건" % (retried, rescued, n502) if rescued > 0 else
                    "삼킬 것이 있었는데(재시도 %d · 502 %d) 되살린 건수가 **0**이다 — "
                    "`proxy_next_upstream` 이 빠졌거나 갈 peer 가 없다. 이 상태의 502 수는 "
                    "뒷단이 아니라 **앞단**의 수다" % (retried, n502)))
    return out


def verdict(rows: list[tuple[str, str, str]]) -> int:
    if any(v == "fail" for _, v, _ in rows):
        return EXIT_FAIL
    if any(v == "gray" for _, v, _ in rows):
        return EXIT_UNDECIDABLE
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════
def docker(*args: str, binary: bool = False, timeout: int = 300):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    p = subprocess.run(["docker", *args], capture_output=True, timeout=timeout, env=env)
    if binary:
        return p.returncode, p.stdout, p.stderr
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def read_access(container: str, path: str, since_line: int) -> list[str] | None:
    rc, out, _ = docker("exec", container, "sh", "-c",
                        "sed -n '%d,$p' %s" % (since_line + 1, path), binary=False)
    if rc != 0:
        return None
    return [l for l in out.splitlines() if l.strip()]


def read_restarts(container: str) -> list[datetime] | None:
    # ⚠ **stderr 를 함께 읽는다.** gunicorn 의 `Autorestarting` 은 **에러 로그**로 나가고,
    #   stdout 만 읽으면 재활용이 **0건으로 보인다** — 그러면 이 판정기는 「설명되지 않는
    #   502 가 8건」이라고 적는다. 즉 **판정기의 눈이 먼 것을 뒷단의 결함으로 적게 된다.**
    #   [실측 2026-09-05 · 턴 D] 첫 판이 정확히 그렇게 틀렸다.
    rc, out, errout = docker("logs", "-t", container)
    if rc != 0:
        return None
    out = out + "\n" + errout
    stamps = []
    for line in out.splitlines():
        if "Autorestarting" not in line:
            continue
        m = _DOCKER_TS.match(line)
        if m:
            # `docker logs -t` 의 앞머리는 **언제나 UTC** 다. 컨테이너 안의 시계
            # (여기서는 +0700)를 믿지 않는다 — 앞단은 +0000 으로 적는다.
            stamps.append(datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
                          .replace(tzinfo=timezone.utc))
    return stamps


def parse_access(lines: list[str]) -> dict:
    err, ok, retried, rescued = [], [], 0, 0
    for line in lines:
        m = _ACCESS.match(line)
        if not m:
            continue
        when = datetime.strptime(m.group("t") + m.group("tz"), "%d/%b/%Y:%H:%M:%S%z")
        status = m.group("status")
        multi = "," in m.group("up")
        if multi:
            retried += 1
        if status == "502":
            err.append(when)
        elif status.startswith("2"):
            ok.append(when)
            if multi:
                rescued += 1
    return {"err": err, "ok": ok, "retried": retried, "rescued": rescued}


def thin(items: list, cap: int) -> list:
    """고르게 솎는다 — 앞이나 뒤만 쓰면 부하의 한쪽만 보게 된다."""
    if len(items) <= cap:
        return items
    step = len(items) / float(cap)
    return [items[int(i * step)] for i in range(cap)]


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성·음성을 함께 둔다** (규약 7)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list[str] = []
    t0 = datetime(2026, 9, 5, 6, 0, 0, tzinfo=timezone.utc)

    def at(sec: int) -> datetime:
        return t0 + timedelta(seconds=sec)

    # ① 겹침 세기 — 양성(같은 초) · 음성(먼 자리)
    if coincidence([at(10)], [at(10)], 0) != 1:
        bad.append("같은 초를 못 셌다")
    if coincidence([at(10)], [at(13)], 0) != 0:
        bad.append("3초 떨어진 것을 같은 초로 셌다")
    if coincidence([at(10)], [at(13)], 5) != 1:
        bad.append("±5초 창을 못 셌다")
    if coincidence([at(10)], [], 5) != 0:
        bad.append("자국이 없는데 겹침을 셌다")

    # ② **양성 대조** — 턴 C 가 실제로 본 모양(502 90% · 정상 21%)은 초록이어야 한다
    good = {"n502": 20, "n200": 174, "n_restarts": 86,
            "hit502": {0: 18, 1: 20, 5: 20}, "hit200": {0: 37, 1: 92, 5: 158},
            "retried": 44, "rescued": 36}
    good["hit502"] = [18, 20, 20]
    good["hit200"] = [37, 92, 158]
    rows = good_rows = judge(good)
    if verdict(rows) != EXIT_FAIL:
        # 18/20 = 90% 이고 2건이 설명되지 않는다 → ②가 빨강이다. **그것이 옳다** —
        # 턴 C 의 표에도 설명 안 되는 502 가 둘 있었고, 그 둘은 아직 이름이 없다.
        bad.append("설명 안 되는 502 둘을 초록으로 봤다")

    # ③ **음성 대조** — 창이 안 갈리면 회색이어야 한다(초록이면 안 된다)
    flat = {"n502": 10, "n200": 100, "n_restarts": 200,
            "hit502": [10, 10, 10], "hit200": [95, 100, 100],
            "retried": 20, "rescued": 10}
    rows = judge(flat)
    if verdict(rows) != EXIT_UNDECIDABLE:
        bad.append("양성 100% · 음성 95% 인데 회색이 아니다 — 그 창은 아무것도 안 가른다")

    # ④ 전부 설명되고 잘 갈리면 초록
    clean = {"n502": 8, "n200": 400, "n_restarts": 131,
             "hit502": [8, 8, 8], "hit200": [40, 120, 380],
             "retried": 44, "rescued": 36}
    if verdict(judge(clean)) != EXIT_OK:
        bad.append("전부 설명되고 69%p 갈리는 표가 초록이 아니다")

    # ⑤ 앞단이 아무것도 못 되살렸으면 빨강 — 502 수를 뒷단 탓으로 읽지 않기 위해서다
    nofront = dict(clean, retried=0, rescued=0)
    if verdict(judge(nofront)) != EXIT_FAIL:
        bad.append("앞단이 0건을 되살렸는데 빨강이 아니다")

    # ⑥ 502 가 0건이면 **초록이 아니라** ②③이 회색이다 — 없는 것을 통과로 적지 않는다
    zero = dict(clean, n502=0, hit502=[0, 0, 0])
    if verdict(judge(zero)) != EXIT_UNDECIDABLE:
        bad.append("502 0건인데 ②③을 초록으로 적었다")

    # ⑥′ **삼킬 것이 없었으면 빨강이 아니라 회색이다** — 좋은 소식을 결함으로 읽지 않는다
    nothing = {"n502": 0, "n200": 400, "n_restarts": 0,
               "hit502": [0, 0, 0], "hit200": [0, 0, 0],
               "retried": 0, "rescued": 0}
    rows = judge(nothing)
    if any(v == "fail" for _, v, _ in rows):
        bad.append("재시도 0 · 502 0 인데 빨강을 찍었다 — 앞단은 멀쩡했다")

    # ⑥″ **음성 대조** — 삼킬 것이 있었는데 못 삼켰으면 그때는 빨강이다
    could_not = dict(nothing, n502=8, hit502=[8, 8, 8], n_restarts=100,
                     hit200=[40, 120, 380], retried=8, rescued=0)
    if verdict(judge(could_not)) != EXIT_FAIL:
        bad.append("재시도 8건이 하나도 못 되살아났는데 빨강이 아니다")

    # ⑦ 못 쟀으면 회색
    if verdict(judge({})) != EXIT_UNDECIDABLE:
        bad.append("못 쟀는데 회색이 아니다")

    # ⑧ 솎기는 **고르게** — 앞도 뒤도 남아야 한다
    sampled = thin(list(range(1000)), 10)
    if len(sampled) != 10 or sampled[0] != 0 or sampled[-1] < 800:
        bad.append("솎기가 한쪽으로 쏠린다")

    # ⑨ 접근로그 한 줄을 **되읽어** 판다 — 재시도(쉼표)와 상태를 함께
    line = ('172.18.0.4 [05/Sep/2026:06:19:06 +0000] "GET /x HTTP/1.1" 502 150 0.379 '
            '"172.18.0.6:8000, 172.18.0.6:8000, gx_app" 0.185, 0.194, 0.000')
    got = parse_access([line])
    if len(got["err"]) != 1 or got["retried"] != 1 or got["rescued"] != 0:
        bad.append("502 재시도 줄을 제대로 못 팠다: %s" % got)
    line200 = ('172.18.0.4 [05/Sep/2026:06:19:06 +0000] "GET /x HTTP/1.1" 200 900 0.2 '
               '"172.18.0.6:8000, 172.18.0.6:8000" 0.1, 0.1')
    got = parse_access([line200])
    if got["rescued"] != 1 or len(got["ok"]) != 1:
        bad.append("되살아난 200 을 못 셌다: %s" % got)

    if bad:
        print("[502] 자기시험 **실패** — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[502] 자기시험 통과 — 겹침 4 · 양성 1 · 음성 1 · 초록 1 · 앞단없음 1 · "
          "502없음 1 · 회색 1 · 솎기 1 · 되읽기 2")
    _ = good_rows
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="OPS-13a — 502 와 워커 재활용의 동시성")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--front", default=FRONT_CONTAINER)
    ap.add_argument("--back", default=BACK_CONTAINER)
    ap.add_argument("--access-path", default=ACCESS_PATH)
    ap.add_argument("--since-line", type=int, default=0,
                    help="이 줄 **다음**부터 읽는다. 부하 직전의 `wc -l` 을 넣어라")
    ap.add_argument("--evidence", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    rc = self_test()
    if rc != EXIT_OK:
        return rc

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    lines = read_access(args.front, args.access_path, args.since_line)
    restarts = read_restarts(args.back)
    if lines is None or restarts is None:
        print("[502] **판정 불가(exit 2)** — 로그에 닿지 못했다 "
              "(앞단 %s · 뒷단 %s)" % (args.front, args.back))
        return EXIT_UNDECIDABLE

    parsed = parse_access(lines)
    err, ok = parsed["err"], parsed["ok"]
    if err or ok:
        lo = min((err + ok))
        hi = max((err + ok))
        restarts = [r for r in restarts if lo - timedelta(seconds=10) <= r
                    <= hi + timedelta(seconds=10)]
    control = thin(ok, CONTROL_SAMPLE)

    facts = {
        "n502": len(err), "n200": len(control), "n_restarts": len(restarts),
        "hit502": [coincidence(err, restarts, w) for w in WINDOWS_SEC],
        "hit200": [coincidence(control, restarts, w) for w in WINDOWS_SEC],
        "retried": parsed["retried"], "rescued": parsed["rescued"],
    }

    say("## 502 는 언제 나는가 — **대조와 함께** [실측]")
    say()
    say("읽은 것: 앞단 접근로그 %d줄(%d번째 줄 다음부터) · 뒷단 재활용 %d건"
        % (len(lines), args.since_line, len(restarts)))
    say("표본: 502 **%d건** · 정상 200 %d건(대조로 %d건 솎음) · 재시도 %d건 · "
        "되살림 %d건" % (len(err), len(ok), len(control),
                        parsed["retried"], parsed["rescued"]))
    say()
    say("| 창 | 502 | 정상 200 (대조) |")
    say("|---|---|---|")
    for i, w in enumerate(WINDOWS_SEC):
        p = 100.0 * facts["hit502"][i] / len(err) if err else 0.0
        q = 100.0 * facts["hit200"][i] / len(control) if control else 0.0
        say("| %s | %d/%d = %.0f%% | %d/%d = %.0f%% |"
            % ("**±0초 (같은 초)**" if w == 0 else "±%d초" % w,
               facts["hit502"][i], len(err), p,
               facts["hit200"][i], len(control), q))
    say()
    say("★ **대조가 없으면 이 표를 못 읽는다.** 재활용이 잦으면 창을 넓히는 것만으로")
    say("  무엇이든 재활용 옆에 놓인다 — 위 표의 아래 줄들이 그 사실을 스스로 말한다.")
    say()

    rows = judge(facts)
    say("## 판정")
    say()
    mark = {"pass": "OK  ", "fail": "FAIL", "gray": "GRAY"}
    for name, v, why in rows:
        say("  %s %-12s %s" % (mark[v], name, why))
    rc = verdict(rows)
    say()
    say("판정 **%s** (exit %d)."
        % ({0: "통과", 1: "실패", 2: "못 쟀다"}[rc], rc))

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence) or ".", exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-13a — 502 와 워커 재활용의 동시성 (%s)\n\n"
                        % datetime.now(timezone.utc).isoformat(timespec="seconds"))
                f.write("**이 파일은 `scripts/verify_front_line_502.py` 가 실행하며 적었다.**\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
