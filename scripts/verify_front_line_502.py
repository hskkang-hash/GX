#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-13a — **502 가 언제 나는지**를 대조와 함께 잰다 (2026-09-05 · 턴 D · 차선 E).

    OPS-13a 앞단이 뒷단의 워커 재활용을 삼킨다 (502 3건 / 3,600 요청)

왜 이 판정기가 따로 있나 — **부하 표를 하나 더 만들지 않기 위해서다**
--------------------------------------------------------------------
부하는 `scripts/verify_perf_budget.py --measure` 가 낸다. 표가 둘이면 다음 사람이
어느 표를 봐야 하는지 모른다. 이 파일은 **부하를 걸지 않는다** — 그 부하가 남긴
자국 둘(앞단 접근로그 · 뒷단 재활용 로그)을 **맞대어 읽을** 뿐이다.

★ **[2026-09-07 · 턴 J · P-92] 「설명되지 않는 502 7건」의 정체는 결함이 아니라 이 판정기였다.**

    두 자리가 틀려 있었다. 둘 다 **판정기 쪽**이다.

      ㉠ **자국이 예고였다.** `Autorestarting worker after current request.` 는 선언이고,
         손님의 연결을 실제로 끊는 것은 그 0.13~0.25초 뒤의 **`Worker exiting (pid: N)`** 이다.
      ㉡ **창이 요청의 끝 한 점이었다.** 접근로그의 시각은 요청이 **끝난** 순간이고 초 단위인데,
         재활용은 요청이 **도는 동안** 일어난다. 끝 한 점만 보면 짧은 요청은 언제나 무죄가 된다.

    고친 뒤 같은 표본에서 **13/13 이 설명되고**, 음성 대조는 **18.8%** 에 머문다(차 81%p).
    ⚠ **자를 바꿔 빨강을 초록으로 만든 것이 아니다** — 바꾼 자에도 **음성 대조를 그대로 댔고**,
      종전 자의 수(±0초 · 미설명 7건)를 표와 판정문에서 **지우지 않았다.** 대조 없이 창만
      넓혔다면 그것은 예외 칸이다(D-327).

    그리고 502 13건에 **남은 결함 하나에는 이름이 생겼다** — 판정기가 아니라 앞단에 있다:
    **OPS-13b · 앞단의 재시도가 두 번에서 멈춘다**(`upstream gx_app` 에 같은 서버가 두 줄이고
    `proxy_next_upstream_tries` 선언이 없다 → 끊긴 연결을 연달아 둘 뽑으면 세 번째 기회가 없다).
    **회색** — 고쳐서 502 가 주는지는 재지 않았다. 증거: `docs/agent/evidence/OPS-13a/미설명7_20260907_TJ.md`

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
import json
import os
import re
import subprocess
import sys
import time
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
#: ★ [실측 2026-09-07 · 턴 J] **초로 자르면 자국을 흘린다.** `docker logs -t` 는
#:   마이크로초까지 적는데 위 정규식은 초까지만 받는다. 같은 초에 여러 번 난 재활용이
#:   하나로 뭉개졌고, 그래서 `Autorestarting` 164줄이 판정기 안에서는 더 적게 보였다.
_DOCKER_TS_US = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{1,9})')


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다.** 자기시험이 합성 표를 먹인다 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def coincidence(events: list[datetime], marks: list[datetime], window: int) -> int:
    """`events` 중 `marks` 와 `window` 초 안에 놓인 것의 수."""
    if not marks:
        return 0
    span = timedelta(seconds=window)
    return sum(1 for e in events if any(abs(e - m) <= span for m in marks))


def span_coincidence(events: list[tuple[datetime, float]],
                    marks: list[datetime]) -> int:
    """`events` 중 **요청이 살아 있던 구간** 안에 `marks` 를 가진 것의 수.

    ★ **왜 점이 아니라 구간인가** [실측 2026-09-07 · 턴 J · P-92]
      접근로그의 시각은 요청이 **끝난** 순간이고 **초 단위**다. 워커 재활용은 요청이
      **도는 동안** 일어난다. 끝 한 점만 보면 `rt=0.234` 인 요청은 0.234초 전의 자국을
      통째로 놓친다 — 그리고 짧은 요청일수록 **언제나 무죄**가 된다.

      구간 = `[끝 - request_time, 끝 + 1초)`.
      뒤를 1초 늘린 것은 실제 끝이 `[t, t+1)` 어딘가라 그렇다(초 단위 기록).

    ⚠ 이 함수는 창을 **넓힌다**. 넓힌 창은 그 자체로는 아무것도 증명하지 않는다 —
      **반드시 음성 대조(정상 200)에 같은 자를 대고 갈리는지 보아야 한다**(③).
    """
    if not marks:
        return 0
    n = 0
    for when, rt in events:
        lo = when - timedelta(seconds=max(rt, 0.0))
        hi = when + timedelta(seconds=1)
        if any(lo <= m < hi for m in marks):
            n += 1
    return n


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
        old_unexplained = n502 - same502

        # ★ [2026-09-07 · 턴 J · P-92] **자국과 창을 둘 다 고쳤다.**
        #   `hit502_span` 이 있으면 그것으로 잰다 — 없으면(합성 표·옛 호출) 종전대로.
        #     자국: `Autorestarting`(예고) → **`Worker exiting`**(연결이 실제로 끊기는 순간)
        #     창  : 요청의 **끝 한 점** → 요청이 **살아 있던 구간**
        #   왜 이것이 「예외 칸 열기」가 아닌가: 종전 수를 **지우지 않고 같은 줄에 남긴다**.
        #   그리고 ③의 음성 대조를 **같은 자로 다시 잰다** — 자를 바꾸면서 대조를 안 바꾸면
        #   그것이 거짓 초록이다.
        has_span = facts.get("hit502_span") is not None
        if has_span:
            hit = facts["hit502_span"]
            unexplained = n502 - hit
            why_ok = ("502 %d건 **전부**가 `Worker exiting` 을 요청 구간 안에 갖는다 "
                      "(종전 자 ±0초·`Autorestarting` 로는 미설명 %d건이었다 — "
                      "그 %d건은 다른 결함이 아니라 **판정기의 눈**이었다)"
                      % (n502, old_unexplained, old_unexplained))
            why_bad = ("**요청 구간 안의 `Worker exiting` 으로도 설명되지 않는 502 가 %d건** "
                       "— 알려진 창에 묻지 마라. 이것은 다른 결함이다" % unexplained)
        else:
            unexplained = old_unexplained
            why_ok = "502 %d건 전부가 재활용과 **같은 초**에 났다" % n502
            why_bad = ("**같은 초의 재활용으로 설명되지 않는 502 가 %d건** — 알려진 창에 "
                       "묻지 마라. 이것은 다른 결함이다" % unexplained)
        out.append(("② 설명", "pass" if unexplained == 0 else "fail",
                    why_ok if unexplained == 0 else why_bad))

        if has_span:
            pos = 100.0 * facts["hit502_span"] / n502
            neg = 100.0 * facts["hit200_span"] / n200 if n200 else 0.0
            label = "요청 구간 · `Worker exiting`"
        else:
            pos = 100.0 * facts["hit502"][0] / n502
            neg = 100.0 * facts["hit200"][0] / n200 if n200 else 0.0
            label = "같은 초"
        gap = pos - neg
        out.append(("③ 대조 분리", "pass" if gap >= SEPARATION_PP else "gray",
                    "%s — 502 %.0f%% 대 정상 %.0f%% (차 %.0f%%p ≥ %.0f%%p)"
                    % (label, pos, neg, gap, SEPARATION_PP) if gap >= SEPARATION_PP else
                    "%s — 502 %.0f%% 대 정상 %.0f%% (차 %.0f%%p < %.0f%%p). "
                    "**갈리지 않는다** — 이 창은 아무것도 안 가른다. 회색이지 빨강이 아니다"
                    % (label, pos, neg, gap, SEPARATION_PP)))

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


# P-84 — **5xx 는 두 줄로 적는다** (세종 판정 · 2026-09-06 · 턴 I)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 무엇이 이 절을 만들었나 [실측 2026-09-06 · 턴 H → 턴 I 정정]
#:
#:   턴 H 의 5xx 0.139%(502 5건/3,600)는 **개발 기계에서 난 수**다. 같은 순간
#:   그 기계에는 차선들의 runserver 여섯 대가 돌고 있었고 loadavg 는 3.57 이었다.
#:   그 수를 SLA 로 적으면 「제품이 0.139% 로 실패한다」로 읽힌다 — 아니다.
#:   **우리 개발 기계가 그만큼 붐볐다**는 말이다.
#:
#:   그렇다고 그 수를 지우지 않는다(P-84). 지우면 「개발 기계에서 502 가 난다」는
#:   사실도 함께 사라진다. 그래서 **두 줄로 적는다**:
#:
#:       ① 개발 기계 수     참고. runserver 몇 대 · loadavg 얼마를 **같은 줄에** 적는다
#:       ② 운영형 인스턴스   `gx-gunicorn-e` / `gx-nginx-e`. **SLA 정본은 이것뿐이다**
#:
#:   ②를 못 재면 **「SLA 미측정 · 사유: 운영형 인스턴스 없음」**(회색)이다 —
#:   ①의 수를 SLA 칸에 옮겨 적는 길은 없다.
#:
#:   ⚠ 「오류 주입을 SLA 에서 뺀다」는 **철회됐다**(P-84). 주입은 Playwright 가로채기라
#:     서버에 닿은 적이 없다 — 앞단 로그에 그 요청이 없다. 뺄 건수는 0 이고,
#:     여기서도 아무것도 빼지 않는다. 빼기는 손잡이가 되고, 손잡이는 당겨진다.

#: 가용성 예산. 정본은 `verify_perf_budget` 의 예산표이고 여기서 **베끼지 않는다** —
#: `sla_budget()` 이 그 파일에서 읽어 온다. 이 상수는 그 파일을 못 읽을 때의 바닥이다.
SLA_BUDGET_FALLBACK = 0.001

#: ① 개발 기계 — P-82 로 배치 대상이 된 runserver. ② 운영형 — 앞단 nginx.
DEV_API_DEFAULT = "http://127.0.0.1:8010"
PROD_API_DEFAULT = "http://gx-nginx-e:8500"
SLA_ROUNDS = 200
SLA_CONCURRENCY = 10


def _scripts_dir_on_path() -> None:
    d = os.path.dirname(os.path.abspath(__file__))
    if d not in sys.path:
        sys.path.insert(0, d)


def sla_budget() -> float:
    """가용성 예산. **정본은 예산표 한 자리다** — 여기 수를 베끼지 않는다(D-369)."""
    _scripts_dir_on_path()
    try:
        from verify_perf_budget import ERROR_BUDGET            # noqa: PLC0415

        return float(ERROR_BUDGET)
    except Exception:                                          # noqa: BLE001
        return SLA_BUDGET_FALLBACK


def sla_calls() -> tuple:
    """때릴 문들. **정본은 `verify_perf_budget.FACES`** — 두 벌을 두지 않는다(D-369)."""
    _scripts_dir_on_path()
    from verify_perf_budget import FACES                       # noqa: PLC0415

    return tuple(c for face in FACES.values() for c in face.calls)


def co_resident() -> dict:
    """이 기계에 **누가 같이 살고 있는가.** ①의 수는 이것 없이는 읽을 수 없다."""
    _scripts_dir_on_path()
    try:
        from verify_perf_budget import _co_resident            # noqa: PLC0415

        return _co_resident()
    except Exception:                                          # noqa: BLE001
        return {"runserver_processes": None, "loadavg": None}


def sample_5xx(api: str, token: str, calls, *, rounds: int = SLA_ROUNDS,
               concurrency: int = SLA_CONCURRENCY) -> dict:
    """한 대상에 요청을 던지고 **5xx 를 센다.** 못 닿으면 `unreachable` 에 사유.

    ★ 0(도달 못 함)은 5xx 쪽으로 센다 — 손님에게는 같은 고장이다.
    """
    import concurrent.futures
    import urllib.error
    import urllib.request

    plan = [calls[i % len(calls)] for i in range(rounds * len(calls))]

    def one(path: str) -> int:
        sep = "&" if "?" in path else "?"
        url = api + path + sep + "_gxts=" + str(time.time_ns())
        req = urllib.request.Request(url)
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("X-GX-Probe", "sla-5xx")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return int(r.status)
        except urllib.error.HTTPError as e:
            return int(e.code)
        except Exception:                                       # noqa: BLE001
            return 0

    codes: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        for code in pool.map(one, plan):
            codes[code] = codes.get(code, 0) + 1
    n = sum(codes.values())
    five = sum(v for c, v in codes.items() if c == 0 or 500 <= c <= 599)
    return {"api": api, "n": n, "n5xx": five,
            "by_status": {str(c): v for c, v in sorted(codes.items())},
            "unreachable": None}


def judge_sla(dev, prod, co: dict, budget: float) -> tuple:
    """두 줄을 만든다. **판정은 ②만 한다.**"""
    lines: list = []
    need = int(round(1.0 / budget)) if budget else 0

    # ── ① 개발 기계 수 — 참고 ─────────────────────────────────────────────
    procs = [c for c in (co.get("runserver_processes") or []) if "runserver" in c]
    where = "runserver %d대 · loadavg %s" % (len(procs), co.get("loadavg") or "못 읽음")
    if dev is None or dev.get("unreachable"):
        lines.append("[5XX] 1) **개발 기계 수** — 못 쟀다 (%s) · %s"
                     % ((dev or {}).get("unreachable") or "대상 없음", where))
    else:
        rate = 100.0 * dev["n5xx"] / dev["n"] if dev["n"] else 0.0
        lines.append("[5XX] 1) **개발 기계 수 (참고)** %s — 5xx %d/%d = %.3f%% · %s"
                     % (dev["api"], dev["n5xx"], dev["n"], rate, where))
        lines.append("[5XX]    ^ **이 수는 SLA 가 아니다.** 같은 기계에서 차선들의 "
                     "runserver 가 함께 돈다 — 재는 것은 제품이 아니라 이 기계의 붐빔이다")

    # ── ② 운영형 인스턴스 — SLA 정본 ──────────────────────────────────────
    if prod is None or prod.get("unreachable"):
        why = (prod or {}).get("unreachable") or "gx-gunicorn-e / gx-nginx-e 에 못 닿았다"
        lines.append("[5XX] 2) **SLA 미측정 · 사유: 운영형 인스턴스 없음** (%s)" % why)
        lines.append("[5XX] **회색(exit 2)** — 1)의 수를 SLA 칸에 옮겨 적는 길은 없다")
        return EXIT_UNDECIDABLE, lines

    rate = prod["n5xx"] / prod["n"] if prod["n"] else 0.0
    codes = " ".join("%s x%d" % (c, v) for c, v in prod["by_status"].items())
    lines.append("[5XX] 2) **운영형 인스턴스 (SLA 정본)** %s — 5xx %d/%d = %.3f%% "
                 "(예산 %.1f%%) · 코드별 %s"
                 % (prod["api"], prod["n5xx"], prod["n"], 100.0 * rate,
                    100.0 * budget, codes or "없음"))
    if prod["n"] == 0:
        lines.append("[5XX] **못 쟀다(exit 2)** — 표본이 0건이다")
        return EXIT_UNDECIDABLE, lines
    if prod["n5xx"] == 0 and prod["n"] < need:
        lines.append("[5XX] **못 쟀다(exit 2)** — 5xx 0건이지만 표본 %d건은 예산 %.1f%% 를 "
                     "판정할 수 없다(최소 %d건). 0 은 「예산 안」이 아니라 「아직 모른다」다"
                     % (prod["n"], 100.0 * budget, need))
        return EXIT_UNDECIDABLE, lines
    if rate > budget:
        lines.append("[5XX] **빨강(exit 1)** — 운영형 인스턴스의 5xx 가 예산을 넘었다. "
                     "**아무것도 빼지 않았다**(주입 분리는 P-84 로 철회 · 뺄 건수 0)")
        return EXIT_FAIL, lines
    lines.append("[5XX] **초록(exit 0)** — 운영형 인스턴스의 5xx 가 예산 안이다")
    return EXIT_OK, lines


def sla_self_test() -> list:
    """P-84 의 규칙 셋을 표본으로 박는다. 실패 사유 목록을 돌려준다."""
    bad: list = []
    co = {"runserver_processes": ["python manage.py runserver 0.0.0.0:8000"], "loadavg": "3.57"}

    # ① 운영형이 없으면 **회색**이다 — 개발 기계 수가 SLA 칸으로 넘어오지 않는다
    rc, lines = judge_sla({"api": "d", "n": 3600, "n5xx": 5, "by_status": {"502": 5}},
                          None, co, 0.001)
    text = "\n".join(lines)
    if rc != EXIT_UNDECIDABLE:
        bad.append("운영형 인스턴스가 없는데 회색이 아니다")
    if "SLA 미측정" not in text or "운영형 인스턴스 없음" not in text:
        bad.append("운영형이 없을 때의 사유 문구가 없다")
    if "0.139" in text.replace("0.139%", "0.139"):
        pass
    if "SLA 정본" in text:
        bad.append("SLA 정본 줄이 없는데 있는 것처럼 적었다")

    # ② 개발 기계 수 줄에는 runserver 대수와 loadavg 가 **같은 줄에** 있어야 한다
    if "runserver 1대" not in text or "loadavg 3.57" not in text:
        bad.append("개발 기계 수 줄에 runserver 대수·loadavg 가 없다 — "
                   "그 둘이 없으면 그 수는 읽을 수 없다")

    # ③ 표본이 예산을 판정할 수 없으면 5xx 0건도 **회색**이다
    rc, lines = judge_sla(None, {"api": "p", "n": 400, "n5xx": 0, "by_status": {"200": 400}},
                          co, 0.001)
    if rc != EXIT_UNDECIDABLE:
        bad.append("표본 400건에 예산 0.1% 를 판정했다 — 0 은 「아직 모른다」다")

    # ④ 예산을 넘으면 빨강. **아무것도 빼지 않는다**
    rc, lines = judge_sla(None, {"api": "p", "n": 3600, "n5xx": 5, "by_status": {"502": 5}},
                          co, 0.001)
    if rc != EXIT_FAIL:
        bad.append("5xx 5/3,600 = 0.139% 가 예산 0.1% 를 넘었는데 빨강이 아니다")
    if "빼지 않았다" not in "\n".join(lines):
        bad.append("주입 분리 철회(뺀 건수 0)를 말하지 않는다")

    # ⑤ 예산 안이면 초록
    rc, _ = judge_sla(None, {"api": "p", "n": 3600, "n5xx": 2, "by_status": {"502": 2}},
                      co, 0.001)
    if rc != EXIT_OK:
        bad.append("5xx 2/3,600 = 0.056% 는 예산 안인데 초록이 아니다")
    return bad


def run_sla(args) -> int:
    """1)2)를 **차례로** 잰다. 동시에 안 재는 이유: 탐침 계정은 동시 접속 1개다 —
    둘을 겹쳐 로그인하면 앞의 토큰이 죽고, 죽은 토큰으로 잰 401 은 5xx 가 아니라서
    **오류율이 0 으로 보인다.** 그것이 이 판정기가 낼 수 있는 가장 나쁜 거짓 초록이다."""
    _scripts_dir_on_path()
    from verify_route_alive import login                        # noqa: PLC0415

    bad = sla_self_test()
    for b in bad:
        print("[5XX] 자기시험 FAIL %s" % b)
    if bad:
        print("[5XX] 자기시험 %d건 실패 — 판정기를 먼저 의심한다 (D-350)" % len(bad))
        return EXIT_FAIL
    print("[5XX] 자기시험 통과 — P-84 갈래 5")

    budget = sla_budget()
    calls = sla_calls()
    co = co_resident()
    user, pw = args.user, args.password
    if not pw:
        print("[5XX] **못 쟀다(exit 2)** — 탐침 비밀번호가 없다 "
              "(저장소 밖 `.env.gates` 의 `GX_PROBE_PASSWORD`)")
        return EXIT_UNDECIDABLE

    out = {}
    for name, api in (("dev", args.dev_api), ("prod", args.prod_api)):
        if not api:
            out[name] = {"unreachable": "대상을 안 줬다"}
            continue
        token = login(api, user, pw)
        if not token:
            out[name] = {"unreachable": "%s 에 로그인하지 못했다" % api, "api": api}
            continue
        out[name] = sample_5xx(api, token, calls, rounds=args.rounds)

    rc, lines = judge_sla(out.get("dev"), out.get("prod"), co, budget)
    print("[5XX] [입력] 문 %d종 · 라운드 %d · 동시 %d · 계정 %s · 예산 %.1f%%"
          % (len(calls), args.rounds, SLA_CONCURRENCY, user, 100.0 * budget))
    for ln in lines:
        print(ln)

    if args.evidence:
        payload = {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "budget": budget, "co_resident": co,
                   "dev_reference": out.get("dev"), "prod_sla": out.get("prod"),
                   "verdict_exit": rc, "lines": lines,
                   "note": ("P-84 — 5xx 는 두 줄. SLA 정본은 2)(운영형 인스턴스)뿐이다. "
                            "주입 분리는 철회됐다(뺀 건수 0)")}
        try:
            os.makedirs(os.path.dirname(args.evidence) or ".", exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            print("[5XX] 증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("[5XX] 증거를 못 적었다: %s" % exc)
    return rc


# ═══════════════════════════════════════════════════════════════════════════

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
    """앞단 접근로그를 읽는다 — **파일이면 파일에서, 표준출력이면 도커에서.**

    ★ [실측 2026-09-06 · 턴 I · 조율자] **이 판정기는 두 턴 동안 회색이었고, 그 회색의
      원인은 우리가 고친 다른 것이었다.** OPS-07(로그 상한)을 갚으려고 앞단 설정을
      `access_log /dev/stdout gx;` 로 바꿨다 — 컨테이너 **안의 파일**에는 도커의
      `--log-opt` 도 logrotate 도 안 닿아 무한히 쌓이기 때문이다. 옳은 조치였다.
      그런데 이 판정기는 여전히 `/var/log/nginx/gx-front.access.log` 를 열고 있었고,
      없는 파일이니 **「못 쟀다」**를 냈다. 그 회색이 SLA 정본(P-84 ②)을 가리고 있었다.

      **한쪽을 고치면 다른 쪽이 눈이 먼다** — 이 저장소가 반복해 만난 모양이고,
      여기서는 「로그를 어디에 적는가」와 「로그를 어디서 읽는가」가 두 자리에 따로 있었다.
      그래서 **둘 다 본다**: 파일이 있으면 파일, 없으면 `docker logs`.
      ⚠ 회색을 초록으로 바꾼 것이 아니다 — **읽을 자리를 하나 더 안 것**이고,
        둘 다 없으면 여전히 회색이다.
    """
    rc, out, _ = docker("exec", container, "sh", "-c",
                        "sed -n '%d,$p' %s" % (since_line + 1, path), binary=False)
    if rc == 0:
        lines = [l for l in out.splitlines() if l.strip()]
        if lines:
            return lines
    #: 표준출력으로 나가는 형상 — `docker logs` 가 그 자리다. 앞머리 타임스탬프는
    #: 붙이지 않는다(`-t` 없이 읽는다): 아래 `parse_access` 는 접근로그 **원문**을 판다.
    rc, out, errout = docker("logs", container)
    if rc != 0:
        return None
    joined = out + chr(10) + errout
    lines = [l for l in joined.splitlines() if l.strip()]
    return lines[since_line:] if lines else None


def read_marks(container: str) -> tuple[list[datetime], list[datetime]] | None:
    """뒷단의 자국 **둘**을 마이크로초까지 읽는다.

    ㉠ `Autorestarting worker after current request.` — **예고**다. 워커는 이 줄을 적고도
       「지금 처리 중인 요청을 마치고」 나간다.
    ㉡ `Worker exiting (pid: N)` — **손님의 연결이 실제로 끊기는 순간**이다.

    ★ [실측 2026-09-07 · 턴 J] 둘 사이는 0.13~0.25초 벌어진다. 판정기가 ㉠만 보던 동안
      그 틈에 빠진 502 가 **7건**이었고, 판정기는 그것을 「설명되지 않는 다른 결함」으로
      적었다. **자국이 예고였던 것이지 결함이 둘이었던 것이 아니다.**
    """
    rc, out, errout = docker("logs", "-t", container)
    if rc != 0:
        return None
    out = out + chr(10) + errout
    ann: list[datetime] = []
    exits: list[datetime] = []
    for line in out.splitlines():
        is_ann = "Autorestarting" in line
        is_exit = ("Worker exiting (pid" in line) and ("cleaning" not in line)
        if not (is_ann or is_exit):
            continue
        m = _DOCKER_TS_US.match(line)
        if m:
            # `docker logs -t` 의 앞머리는 **언제나 UTC** 다(컨테이너 안 시계를 믿지 않는다).
            when = (datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
                    .replace(tzinfo=timezone.utc)
                    + timedelta(microseconds=int((m.group(2) + "000000")[:6])))
        else:
            m = _DOCKER_TS.match(line)
            if not m:
                continue
            when = (datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
                    .replace(tzinfo=timezone.utc))
        (ann if is_ann else exits).append(when)
    return ann, exits


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
    """★ [2026-09-07 · 턴 J] **`$request_time` 을 버리지 않는다.**
    종전 판은 시각만 들고 나왔고, 그래서 「요청이 얼마나 오래 살아 있었는가」를
    판정기가 알 수 없었다. `err`·`ok` 는 이제 `(끝난 시각, request_time)` 짝이다."""
    err, ok, retried, rescued = [], [], 0, 0
    for line in lines:
        m = _ACCESS.match(line)
        if not m:
            continue
        when = datetime.strptime(m.group("t") + m.group("tz"), "%d/%b/%Y:%H:%M:%S%z")
        try:
            rt = float(m.group("rt"))
        except (TypeError, ValueError):
            rt = 0.0
        status = m.group("status")
        multi = "," in m.group("up")
        if multi:
            retried += 1
        if status == "502":
            err.append((when, rt))
        elif status.startswith("2"):
            ok.append((when, rt))
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

    # ①′ **구간 겹침** — 턴 J 가 고친 자. 양성·음성을 함께 둔다 (P-92)
    #   요청이 10.00 에 끝나고 rt=0.30 이면 구간은 [09.70, 11.00) 이다.
    if span_coincidence([(at(10), 0.30)], [at(10) - timedelta(milliseconds=200)]) != 1:
        bad.append("요청이 도는 동안 난 자국을 못 셌다 — 이것이 미설명 7건의 정체였다")
    if span_coincidence([(at(10), 0.30)], [at(10) - timedelta(milliseconds=400)]) != 0:
        bad.append("구간 **밖**(0.4초 전)의 자국을 안에 있다고 셌다")
    if span_coincidence([(at(10), 0.30)], [at(10) + timedelta(milliseconds=900)]) != 1:
        bad.append("끝 초 안(+0.9초)의 자국을 못 셌다 — 접근로그 시각은 초 단위다")
    if span_coincidence([(at(10), 0.30)], [at(12)]) != 0:
        bad.append("2초 뒤의 자국을 구간 안으로 셌다")
    if span_coincidence([(at(10), 0.30)], []) != 0:
        bad.append("자국이 없는데 구간 겹침을 셌다")
    if span_coincidence([], [at(10)]) != 0:
        bad.append("요청이 없는데 구간 겹침을 셌다")

    # ①″ **자를 바꿔도 대조가 안 갈리면 회색이다** — 자만 바꾸고 초록을 얻지 않는다
    span_flat = {"n502": 10, "n200": 100, "n_restarts": 50,
                 "hit502": [3, 5, 9], "hit200": [10, 40, 90],
                 "hit502_span": 10, "hit200_span": 96,
                 "retried": 20, "rescued": 10}
    if verdict(judge(span_flat)) != EXIT_UNDECIDABLE:
        bad.append("구간으로 100% 대 96% 인데 회색이 아니다 — 넓힌 창은 그 자체로 무죄가 아니다")

    # ①‴ **구간으로 전부 설명되고 잘 갈리면 초록** — 턴 J 가 실제로 본 모양
    span_ok = {"n502": 13, "n200": 400, "n_restarts": 61,
               "hit502": [6, 13, 13], "hit200": [70, 162, 310],
               "hit502_span": 13, "hit200_span": 75,
               "retried": 138, "rescued": 125}
    if verdict(judge(span_ok)) != EXIT_OK:
        bad.append("구간 13/13 · 음성 18.8% (차 81%p) 인데 초록이 아니다")
    #   그리고 **종전 자의 미설명 7건이 판정문에 남아 있어야 한다**
    if not any("7건" in why for _, _, why in judge(span_ok)):
        bad.append("자를 바꾸면서 종전 수(미설명 7건)를 지웠다 — 지우면 무엇이 바뀌었는지 사라진다")
    #   구간으로도 설명이 안 되면 그때는 여전히 빨강이다
    span_bad = dict(span_ok, hit502_span=9)
    if verdict(judge(span_bad)) != EXIT_FAIL:
        bad.append("구간으로도 4건이 설명 안 되는데 빨강이 아니다")

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
    # ⑨′ **`$request_time` 을 같이 들고 나왔는가** — 이것이 없으면 구간을 못 그린다
    if not got["err"] or abs(got["err"][0][1] - 0.379) > 1e-9:
        bad.append("접근로그의 request_time 을 흘렸다 — 구간을 그릴 수 없다: %s" % got)
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
    print("[502] 자기시험 통과 — 겹침 4 · **구간겹침 6** · 양성 1 · 음성 1 · 초록 1 · "
          "앞단없음 1 · 502없음 1 · 회색 2 · **구간초록 2** · 솎기 1 · 되읽기 3")
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
    #: P-84 — 5xx 를 **두 줄로** 잰다. 이 갈래는 로그를 안 읽고 직접 때린다.
    ap.add_argument("--sla-5xx", action="store_true",
                    help="P-84 — 1) 개발 기계 수(참고) 2) 운영형 인스턴스 수(SLA 정본)")
    ap.add_argument("--dev-api", default=DEV_API_DEFAULT)
    ap.add_argument("--prod-api", default=PROD_API_DEFAULT)
    ap.add_argument("--rounds", type=int, default=SLA_ROUNDS)
    ap.add_argument("--user", default=os.environ.get("GX_PROBE_USER", "gxprobe_q"))
    ap.add_argument("--password", default=os.environ.get("GX_PROBE_PASSWORD", ""))
    args = ap.parse_args()

    if args.sla_5xx:
        return run_sla(args)
    if args.self_test:
        rc_sla = sla_self_test()
        for b in rc_sla:
            print("[5XX] 자기시험 FAIL %s" % b)
        if rc_sla:
            return EXIT_FAIL
        return self_test()
    rc = self_test()
    if rc != EXIT_OK:
        return rc

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    lines = read_access(args.front, args.access_path, args.since_line)
    marks = read_marks(args.back)
    restarts, exits = (marks if marks else (None, None))
    if lines is None or restarts is None:
        print("[502] **판정 불가(exit 2)** — 로그에 닿지 못했다 "
              "(앞단 %s · 뒷단 %s)" % (args.front, args.back))
        return EXIT_UNDECIDABLE

    parsed = parse_access(lines)
    err, ok = parsed["err"], parsed["ok"]
    err_t = [e[0] for e in err]
    ok_t = [o[0] for o in ok]
    if err_t or ok_t:
        lo = min(err_t + ok_t)
        hi = max(err_t + ok_t)
        keep = lambda xs: [r for r in xs if lo - timedelta(seconds=10) <= r
                           <= hi + timedelta(seconds=10)]
        restarts = keep(restarts)
        exits = keep(exits)
    control = thin(ok, CONTROL_SAMPLE)
    control_t = [c[0] for c in control]
    restarts_sec = [r.replace(microsecond=0) for r in restarts]

    facts = {
        "n502": len(err), "n200": len(control), "n_restarts": len(restarts),
        "n_exits": len(exits),
        # 종전 자는 **종전 그대로** 재서 나란히 보인다. 뒷단 자국을 µs 까지 읽게 되면서
        # `±0초`(=같은 초)의 뜻이 「같은 마이크로초」로 바뀌어 버리므로, 이 세 줄에서만
        # 초로 도로 자른다. **자를 바꾼 자리를 스스로 적는 것**이 이 판정기의 규약이다.
        "hit502": [coincidence(err_t, restarts_sec, w) for w in WINDOWS_SEC],
        "hit200": [coincidence(control_t, restarts_sec, w) for w in WINDOWS_SEC],
        # ★ 옳은 자국(연결이 실제로 끊기는 순간) × 옳은 창(요청이 살아 있던 구간)
        "hit502_span": span_coincidence(err, exits),
        "hit200_span": span_coincidence(control, exits),
        "retried": parsed["retried"], "rescued": parsed["rescued"],
    }

    say("## 502 는 언제 나는가 — **대조와 함께** [실측]")
    say()
    say("읽은 것: 앞단 접근로그 %d줄(%d번째 줄 다음부터) · 뒷단 자국 둘 — "
        "예고(`Autorestarting`) %d건 · **종료(`Worker exiting`) %d건**"
        % (len(lines), args.since_line, len(restarts), len(exits)))
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
    say("| **요청 구간 × `Worker exiting`** | %d/%d = %.0f%% | %d/%d = %.0f%% |"
        % (facts["hit502_span"], len(err),
           100.0 * facts["hit502_span"] / len(err) if err else 0.0,
           facts["hit200_span"], len(control),
           100.0 * facts["hit200_span"] / len(control) if control else 0.0))
    say()
    say("★ 마지막 줄이 판정에 쓰는 자다. 위 세 줄은 **종전 자**이고 지우지 않는다 —")
    say("  지우면 「무엇을 바꿔서 설명이 되었는가」가 사라진다(P-92 · 턴 J).")
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
