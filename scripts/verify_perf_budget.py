#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PERF-04 — **응답시간 예산과 그 회귀 감시** (차선 Q · 2026-09-05).

예산은 **이미 정해졌다.** 이 파일은 정하지 않고 **집행**한다 (세종 위임 판정 P-34):

    ┌──────────────────────────────────┬────────────┐
    │ 면                               │ p95 예산   │
    ├──────────────────────────────────┼────────────┤
    │ 계약 F-05 진입면 (NFR-05-1)      │   500 ms   │  ← 계약이 이름을 댄 유일한 수
    │ 화면 API                         │   800 ms   │
    │ 스냅샷·미디어                    │ 1,000 ms   │
    │ 상태·가용성 (캐시 금지 · P-19)   │   300 ms   │
    ├──────────────────────────────────┴────────────┤
    │ 회귀 감시: 기준선 대비 **+20% 초과 시 빨강**  │
    └───────────────────────────────────────────────┘

★★ 이 게이트의 초록을 어떻게 읽어야 하는가 — **반드시 함께 읽는다** ★★
------------------------------------------------------------------------
지금 이 수는 `runserver`(개발 서버)로 잰 **기준선**이다. **합격선은 gunicorn+nginx
에서 다시 잰다**(OPS-13 뒤). 그때까지 이 게이트의 초록은 「예산을 지켰다」가 아니라
**「기준선이 예산 안에 있다」**이다. 기준선을 합격선으로 읽으면 그것이 착시 ⑤(환경)다.
그래서 이 문장은 주석이 아니라 **출력에 박혀 있다**(`BASELINE_CAVEAT`) — 안 박으면
다음 사람이 이 수를 운영의 수로 옮겨 적는다.

★ 왜 모든 호출에 `?bust=` 를 붙이는가 — **캐시 적중 시간은 성능이 아니다**
--------------------------------------------------------------------------
`UniversalCacheMiddleware` 는 캐시가 적중하면 저장된 본문을 **언제나 200** 으로
되살린다(D-412 [실측]: MinIO 를 내린 채 같은 순간에 두 번 물어 0.01s/200 과
6.68s/500 을 함께 봤다). 성능을 재는 자리에서 이것은 치명적이다 — 10ms 를 적고
「빠르다」고 말하지만 잰 것은 **우리 코드가 아니라 Redis** 다. 그래서 이 측정기는
호출마다 다른 질의문자열을 붙여 캐시를 비낀다. 비끼지 못한 측정은 **회색**이지
초록이 아니다.

무엇을 보는가 — 넷
------------------
  ① **구조** (서버 없이 돈다) 캐시 금지 면의 경로가 `BYPASS_PATTERNS` 에 있는가 (P-19)
  ② **예산**  면마다 p95 ≤ 예산 · 오류 0건
  ③ **회귀**  면마다 p95 ≤ 기준선 × 1.20 — ★ 흩어진 폭이 그 문턱을 **걸치면 회색**이다
              (예산 갈래에 건 규칙을 여기에도 건다: 다시 재면 통과하고 또 재면
               실패하는 수를 빨강으로 적으면, 그 빨강은 그날의 스케줄러를 가리킨다)
  ④ **비낌**  측정이 캐시를 비껴서 이뤄졌는가

    python scripts/verify_perf_budget.py --self-test        # 판정 규칙만 (서버 없이)
    python scripts/verify_perf_budget.py                    # 증거를 읽고 판정 (호스트)
    docker exec -e GX_API=http://127.0.0.1:8400 -e GX_ROUTE_USER=… -e GX_ROUTE_PASSWORD=… \\
        gx-shell python /repo/scripts/verify_perf_budget.py --measure \\
        --out /docs/agent/evidence/PERF-04/budget.json

★ 모드 둘 — **대상이 무엇이냐가 절대 예산의 색을 정한다** (세종 P-34)
---------------------------------------------------------------------
    기준선 모드   대상이 `runserver` 다. 절대 예산 초과는 **빨강이 아니라 기록**(`!`)
                  이고 종료 코드를 물들이지 않는다. 「그때까지 회색 아님 — 기준선으로
                  초록」이 그 뜻이다. 넘은 자리는 `pending_acceptance` 에 **이름으로**
                  남아 OPS-13 을 닫는 사람 앞에 선다
    합격선 모드   대상이 `runserver` 가 아니다(gunicorn·nginx). 절대 예산도 **빨강**

모드는 응답의 `Server:` 헤더로 **저절로** 갈린다(`mode_for`) — 사람이 기억해야 켜지는
규칙은 바쁜 날 깨진다(D-286). `--acceptance` 는 손수 켜는 곁길이지 본줄기가 아니다.

★ 왜 기준선 모드가 빨강을 안 내는가 — **태어나면서부터 빨간 게이트는 죽는다**
-----------------------------------------------------------------------------
`runserver` 는 한 프로세스이고 이 컨테이너에는 서버가 여럿 서 있다. 그 위에서 낸
빨강은 코드가 아니라 그날의 스케줄러를 가리키고, 그런 빨강이 몇 번 나면 다음 사람이
게이트를 우회한다. **우회당한 게이트는 죽는다.** 그래서 색을 빼되 **사실은 남긴다** —
`pending_acceptance` 가 그 못이고, 이 정정이 면제로 굳지 않게 하는 것이 그 목록의 일이다.

종료 코드: **0 통과 · 1 빨강(회귀 · 오류 · 구조 · 합격선 모드의 예산) · 2 못 쟀다(회색)**.
★ 회색은 초록이 아니다. 「안 쟀다」와 「재서 통과했다」를 같은 수로 적는 순간
  이 게이트는 아무것도 재지 않는 게이트가 된다 (D-301).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
CACHE_SRC = ROOT / "backend" / "common" / "universal_optimization.py"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
PASS, FAIL, GRAY = "pass", "fail", "gray"
#: ★ **제4의 표시** — 「기준선에서 예산을 넘었다」. 초록도 회색도 빨강도 아니다.
#:   세종 위임 판정 P-34 가 「그때까지 회색 아님 — 기준선으로 초록」이라 했으므로
#:   이 표시는 **종료 코드를 물들이지 않는다**(`exit_code` 가 무시한다). 그러나
#:   눈에는 띄어야 한다: 이 자리는 OPS-13 뒤 합격선에서 **빨강이 될 자리**이고,
#:   `budget.json` 의 `pending_acceptance` 에 이름으로 남는다.
#:   ⚠ 이 표시가 **면제로 굳지 않게** 하는 것이 `pending_acceptance` 의 일이다.
OVER = "over"

#: 판정 모드 둘.
#:   `baseline`   대상이 `runserver` 다 → 절대 예산 초과는 **기록**(OVER)이지 빨강이 아니다
#:   `acceptance` 대상이 `runserver` 가 아니다 → 절대 예산도 **빨강**이다
MODE_BASELINE, MODE_ACCEPTANCE = "baseline", "acceptance"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


#: ★ **출력에 박는다.** 이 게이트가 내는 수는 `runserver` 의 수이고, 합격선은
#:   gunicorn+nginx 에서 다시 잰다(OPS-13 뒤). 안 적으면 다음 사람이 기준선을
#:   합격선으로 오독한다 — 그 오독이 정확히 착시 ⑤(환경)다.
BASELINE_CAVEAT = (
    "★ 이 수는 `runserver`(개발 서버)로 잰 **기준선**이다. **합격선은 gunicorn+nginx "
    "에서 다시 잰다**(OPS-13 뒤). 그때까지 이 초록은 「예산을 지켰다」가 아니라 "
    "**「기준선이 예산 안에 있다」**이다 — 기준선을 합격선으로 옮겨 적으면 착시 ⑤(환경)다."
)

#: 회귀 감시의 문턱. 기준선 대비 이만큼을 **넘으면** 빨강 (세종 위임 판정 P-34).
REGRESSION_TOLERANCE = 0.20

# ═══════════════════════════════════════════════════════════════════════════
# ★ 세종 판정 P-53 — **응답시간과 오류율은 다른 칸이다**
# ═══════════════════════════════════════════════════════════════════════════
#   [실측 2026-09-05 · 턴 D] 3,722 요청 중 502 가 8건(0.21%) 났고 p95 는 네 면
#   전부 예산 안이었다(F05 217ms ≤ 500ms …). 그런데 이 게이트는 **예산 칸에**
#   빨강을 적었다 — 「오류가 있으면 예산과 무관하게 빨강」이었기 때문이다.
#   그 빨강을 보고 다음 사람은 **응답시간이 예산을 넘었다고 읽는다.** 실제로 넘은
#   것은 가용성이고, 고칠 자리도(워커 재활용 · OPS-13a) 전혀 다른 자리다.
#   **한 칸에 두 고장을 적으면 어느 쪽이 빨간지 아무도 모른다.**
#: 오류율 예산 — SLA 가용성 **99.9%** 의 월 단위 환산(30일 43,200분 중 43.2분).
#: 이 수는 여기서 정한 것이 아니다 — 세종 판정 P-53 · LAW-05 SLA 초안에서 옮겨 적었다.
ERROR_BUDGET = 0.001

#: 표본의 이만큼이 오류면 **응답시간을 판정하지 않는다.**
#: 502 는 **빠르다** — 앞단(nginx)이 뒤를 못 잡고 즉시 끊으므로 그 표본은 20ms 대다.
#: 오류가 표본의 다수를 차지하면 p95 는 「우리 코드가 얼마나 빠른가」가 아니라
#: 「얼마나 빨리 실패하는가」다. 소수(0.1% 대)면 가운데 값이 흔들리지 않으므로
#: 응답시간을 그대로 판정하고, 그 사실은 사유에 적는다.
LATENCY_POISON = 0.05

#: **3/n 규칙**(rule of three) — 오류 0건을 본 표본 n 에서 참 오류율의 95% 상한은 3/n.
#: 그래서 0.1% 를 **확인**하려면 최소 3,000건이 필요하다. n 이 그보다 작을 때의
#: 「0건」은 「0.1% 안이다」가 아니라 **못 쟀다**(회색)이다 — 40건에서 오류 0건을
#: 보고 가용성 99.9% 를 초록으로 적는 것이 정확히 이 게이트가 막아야 할 거짓 초록이다.
ERROR_MIN_N = math.ceil(3 / ERROR_BUDGET)


@dataclass(frozen=True)
class Face:
    """예산이 걸린 면 하나. **예산은 여기서 정하지 않는다** — 옮겨 적을 뿐이다."""
    title: str
    budget_ms: float
    source: str
    calls: tuple[str, ...]
    #: 이 면이 **캐시되면 안 되는** 자리인가 (P-19). 참이면 구조 검사 ①이 걸린다.
    cache_forbidden: bool = False


#: ★ 예산 표 — 세종 위임 판정 P-34. 여기 수를 고치는 것은 **예산을 다시 정하는 일**이고,
#:   그것은 이 차선의 몫이 아니다. 고쳐야 하면 판정을 먼저 바꾸고 그 다음 여기를 바꾼다.
FACES: dict[str, Face] = {
    "F05": Face(
        title="계약 F-05 진입면 (NFR-05-1)",
        budget_ms=500.0,
        source="계약 F-05 「OpenAPI 제공 · p95 500ms」 (kernels/k1_event/services.py 머리말)",
        # ★ **한 자리다.** `inbound_key=True` 를 선언한 라우트는 저장소 전체에서
        #   `GET /api/dsm/events` 하나뿐이다(`backend/apps/dsm/api.py:163`) —
        #   F-05 「진입면 하나」의 실제 집행이 그 선언이다. 다른 자리를 여기 넣으면
        #   계약이 부르지 않은 면에 계약의 수를 씌우는 것이 된다.
        calls=("/api/dsm/events?limit=50",),
    ),
    "SCREEN": Face(
        title="화면 API",
        budget_ms=800.0,
        source="세종 위임 판정 P-34",
        calls=("/api/dsm/events/summary",
               "/api/dsm/dashboard/frame",
               "/api/dsm/events/queue",
               "/api/dsm/events/response-times"),
    ),
    "MEDIA": Face(
        title="스냅샷·미디어",
        budget_ms=1000.0,
        source="세종 위임 판정 P-34",
        # 바깥 저장소(MinIO)를 타는 자리. 예산이 가장 헐거운 이유가 그것이다.
        calls=("/api/media-data/",),
    ),
    "STATUS": Face(
        title="상태·가용성 (캐시 금지 · P-19)",
        budget_ms=300.0,
        source="세종 위임 판정 P-34 · 캐시 금지는 P-19 · D-413",
        calls=("/api/dsm/dashboard/link-state",),
        cache_forbidden=True,
    ),
}

#: 측정 조건 — **동시성은 PERF-01 과 같다** (동시 10 · 워밍업 1라운드 버림).
#:
#: ★ 왜 조건을 여기 박는가: **조건 없는 p95 는 판정할 수 없다.** [실측 2026-09-05]
#:   같은 코드·같은 서버에서 상태·가용성 면은 **동시 4에서 122ms · 동시 10에서 445ms**
#:   였다. 300ms 예산은 앞의 수로는 초록이고 뒤의 수로는 빨강이다 — 조건을 안 적으면
#:   이 게이트의 색은 판정이 아니라 **누가 어떤 인자로 돌렸는가**가 된다.
#: ★ 왜 하필 동시 10인가: PERF-01 이 그 조건으로 쟀고(`load.json`), 예산이 정해질 때
#:   눈앞에 있던 수가 **그 조건의 수**다. 회귀를 견주려면 두 수가 같은 조건이어야 한다.
DEFAULT_CONCURRENCY = 10
#: 라운드 수는 **부하가 아니라 표본 수**다. 동시성은 PERF-01 과 같게 두고
#: 표본만 늘린다 — [실측 2026-09-05] 5라운드(n=50)에서 같은 서버·같은 코드의
#: F05 p95 가 465ms 와 579ms 로 흔들렸다(+25%). 그 흔들림이 회귀 문턱(20%)보다
#: 크면 이 게이트는 **성능이 아니라 잡음을 잰다.**
DEFAULT_ROUNDS = 10
#: 같은 벌을 몇 번 재는가. **1은 안 된다** — 한 번 잰 p95 는 그날의
#: 스케줄러를 함께 담고 있고, 그 수로 20% 문턱을 판정하면 거짓 경보가 난다.
DEFAULT_REPEAT = 3
WARMUP_ROUNDS = 1

DEFAULT_EVIDENCE_PARTS = ("agent", "evidence", "PERF-04", "budget.json")

# ═══════════════════════════════════════════════════════════════════════════
# 주입한 5xx 는 SLA 의 5xx 가 아니다 — **그러나 빼기가 손잡이가 되면 안 된다**
# (P-79 · 2026-09-06 · 턴 H · 차선 Q)
# ═══════════════════════════════════════════════════════════════════════════
#: 계량이 자기 요청에 다는 표. 앞단 로그에서 **계량 트래픽을 이름으로** 가려낼 수 있게 한다.
#: 이름 없는 트래픽에는 나중에 아무 사유나 붙는다 — 그것이 P-71 의 「환경」이었다.
PROBE_HEADER = "X-GX-Probe"
PROBE_VALUE = "perf-budget"

#: 일부러 고장 내는 요청에 다는 표. **이 표가 붙은 요청의 5xx 만** SLA 분모에서 뺀다.
INJECT_HEADER = "X-GX-Fault-Inject"

#: ★ **이 게이트가 일부러 고장 내는 호출.** 비어 있다 — 이 계량은 주입하지 않는다.
#:   비어 있다는 사실 자체가 「뺄 것이 없다」의 근거이고, 증거에 `subtracted: 0` 으로
#:   적힌다. 여기에 무엇이든 들어오면 그 요청의 5xx 는 분모에서 빠지고 **뺀 건수와
#:   사유가 함께 적힌다.**
#:
#:   ⚠ **빼기는 「빨강을 없애는 손잡이」가 아니다.** 표가 없는 5xx 는 502 든 500 이든
#:     빠지지 않는다 — 사용자에게는 같은 고장이다. 자기시험 갈래가 그것을 지킨다.
INJECTED_CALLS: frozenset = frozenset()


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다** (D-277). 자기시험이 합성 수치를 먹인다
# ═══════════════════════════════════════════════════════════════════════════
def mode_for(server_header: str | None) -> str:
    """대상 서버가 무엇인가로 **모드를 저절로 고른다** (D-286).

    ★ 사람이 기억해야 켜지는 규칙은 바쁜 날 깨진다. 그래서 `--acceptance` 는
      손수 켜는 곁길이고, **본줄기는 이 함수**다. 판별은 응답의 `Server:` 헤더로
      한다 — 추측이 아니라 **서버가 스스로 말하는 이름**이다:

          `WSGIServer/0.2 CPython/3.11`  Django 개발 서버 → 기준선 모드
          `gunicorn/21.2.0` · `nginx`    운영 앞단        → 합격선 모드

    ★ 못 읽으면 **합격선**이다. 조율자 지시 그대로 「대상이 `runserver` 가 아니면
      합격선」이고, 이쪽으로 틀리는 것이 안전하다: 모르는 서버를 기준선으로 접으면
      진짜 운영이 조용히 면제를 받는다.
    """
    if server_header and "wsgiserver" in server_header.lower():
        return MODE_BASELINE
    return MODE_ACCEPTANCE


def judge_face(key: str, face: Face, sample: dict | None, baseline: dict | None,
               *, tolerance: float = REGRESSION_TOLERANCE,
               mode: str = MODE_BASELINE) -> list:
    """면 하나를 판정한다. `(이름, 판정, 사유)` — 판정은 `pass`·`fail`·`gray`.

    ★ **`gray` 는 `pass` 가 아니다** (D-301). 못 쟀다는 사실을 초록으로 접으면
      서버가 없는 날 이 게이트는 회색이 아니라 **초록으로 죽는다.**
    """
    out: list = []
    label = f"{key} {face.title}"

    if sample is None or not sample.get("n"):
        out.append((f"{label} · 예산 {face.budget_ms:.0f}ms", GRAY,
                    "**못 쟀다** — 이 면의 표본이 없다. 0건은 「빠르다」가 아니다"))
        out.append((f"{label} · 회귀 +{tolerance:.0%}", GRAY, "**못 쟀다** — 표본이 없다"))
        return out

    n_total = int(sample.get("n") or 0)
    errors = int(sample.get("errors", 0))
    err_rate = (errors / n_total) if n_total else 0.0
    p95 = float(sample.get("p95_ms", 0.0))

    # ★ **오류는 이 칸에서 판정하지 않는다** (세종 P-53). 여기는 응답시간 칸이고,
    #   오류율은 `judge_availability` 가 **자기 칸에서** 빨강을 낸다. 둘 다 종료
    #   코드에 든다 — 갈라 적는 것이지 면제하는 것이 아니다.
    #   다만 오류가 표본을 **먹어 버리면** 이 칸의 수는 성능이 아니다:
    if err_rate > LATENCY_POISON:
        out.append((f"{label} · 예산 {face.budget_ms:.0f}ms", GRAY,
                    f"**판정 불가** — 표본의 {err_rate:.1%}({errors}/{n_total})가 "
                    f"오류다. 502 는 앞단이 뒤를 못 잡고 즉시 끊으므로 **빠르다** — "
                    f"이 p95 는 「우리 코드가 얼마나 빠른가」가 아니라 「얼마나 빨리 "
                    f"실패하는가」다. 오류율은 가용성 칸이 따로 판정한다 (P-53)"))
    elif not sample.get("cache_bust", False):
        # 캐시를 비끼지 못한 수는 **성능이 아니다.** 초록으로 적지 않는다.
        out.append((f"{label} · 예산 {face.budget_ms:.0f}ms", GRAY,
                    f"p95 {p95:.0f}ms — 그러나 **캐시를 비끼지 않고 잰 수**다. "
                    f"적중한 응답은 언제나 200 이고 10ms 대다(D-412). "
                    f"이 수는 우리 코드가 아니라 Redis 를 잰 것일 수 있다"))
    else:
        # ★ **흩어진 폭이 예산을 걸치면 판정하지 않는다.** 회귀에서 잡음을 재지
        #   않기로 한 것과 같은 규칙이다 — 다시 재면 통과하고 또 재면 실패하는
        #   수를 빨강으로 적으면, 그 빨강은 코드가 아니라 그날의 스케줄러를 가리킨다.
        #   전 벌이 예산을 넘었을 때만 빨강이고, 전 벌이 안에 들었을 때만 초록이다.
        lo, hi = sample.get("p95_min"), sample.get("p95_max")
        if lo is not None and hi is not None and float(lo) <= face.budget_ms < float(hi):
            out.append((f"{label} · 예산 {face.budget_ms:.0f}ms", GRAY,
                        f"**판정 불가** — {sample.get('repeats')}벌의 p95 가 "
                        f"{float(lo):.0f}–{float(hi):.0f}ms 로 예산 "
                        f"{face.budget_ms:.0f}ms 를 **걸친다.** 넘은 벌도 있고 든 벌도 "
                        f"있다 — 이 환경에서는 이 면을 판정할 수 없다 (OPS-13 뒤 "
                        f"gunicorn+nginx 에서 다시 잰다)"))
        else:
            ok = p95 <= face.budget_ms
            band = "" if lo is None else f" · {sample.get('repeats')}벌 {float(lo):.0f}–{float(hi):.0f}ms"
            head = (f"p95(가운데) {p95:.0f}ms {'≤' if ok else '>'} "
                    f"{face.budget_ms:.0f}ms (n={sample.get('n')} · "
                    f"오류 {errors}{band})")
            if errors:
                # ★ 초록이지만 **조건부 초록**이다. 이 줄이 없으면 다음 사람이
                #   「오류가 있는데도 초록이 났다」를 면제로 읽는다.
                head += (f" · ⚠ 표본에 오류 {errors}건({err_rate:.2%})이 섞였다 — "
                         f"이 칸은 **응답시간만** 판정한다. 오류율은 아래 "
                         f"「[전체] 가용성」 칸이 낸다 (P-53)")
            if ok:
                verdict, tail = PASS, ""
            elif mode == MODE_BASELINE:
                # ★ 세종 위임 판정 P-34 — 「합격선은 gunicorn+nginx 에서 다시 잰다
                #   (그때까지 회색 아님 — 기준선으로 초록)」. 그래서 **빨강이 아니라
                #   기록**이다. 태어나면서부터 빨간 게이트는 다음 사람이 우회하고,
                #   우회당한 게이트는 죽는다 — 회색 규칙을 세운 것과 같은 걱정이다.
                verdict, tail = OVER, (" — **전 벌이 예산을 넘었다.** 기준선 모드라 "
                                       "빨강이 아니라 **기록**이다. 합격선(OPS-13 뒤 "
                                       "gunicorn+nginx)에서는 이 자리가 빨강이다")
            else:
                verdict, tail = FAIL, " — **전 벌이 예산을 넘었다** (합격선 모드)"
            out.append((f"{label} · 예산 {face.budget_ms:.0f}ms", verdict, head + tail))

    base_p95 = None if baseline is None else baseline.get("p95_ms")
    if base_p95 is None:
        out.append((f"{label} · 회귀 +{tolerance:.0%}", GRAY,
                    "**못 쟀다** — 기준선이 없다. 첫 측정이 기준선이 된다"))
    elif (baseline.get("concurrency") is not None
          and sample.get("concurrency") is not None
          and baseline["concurrency"] != sample["concurrency"]):
        # ★ 동시성이 다른 두 p95 를 견주면 **다른 것 둘을 견주는 것**이다.
        #   동시 4의 130ms 와 동시 10의 400ms 는 3배 차이지만 회귀가 아니다 —
        #   그것을 빨강으로 적으면 다음 사람이 이 게이트를 끄게 된다 (착시 ⑤).
        out.append((f"{label} · 회귀 +{tolerance:.0%}", GRAY,
                    f"**못 쟀다** — 동시성이 다르다 (기준선 동시 "
                    f"{baseline['concurrency']} · 이번 동시 {sample['concurrency']}). "
                    f"동시성이 다른 두 p95 는 같은 것이 아니다"))
    elif (sample.get("noise") is not None
          and float(sample["noise"]) > tolerance):
        # ★ **못 가르는 것을 갈랐다고 적지 않는다.** 같은 조건에서 다시 잰 p95 가
        #   문턱보다 넓게 흩어지면, 이 환경에서 「+20% 나빠졌다」와 「그날 느렸다」는
        #   구별되지 않는다. 그 상태의 빨강은 거짓 경보이고, 거짓 경보가 몇 번
        #   나면 다음 사람이 이 게이트를 끈다 — 회귀 감시가 사라지는 길이 그것이다.
        out.append((f"{label} · 회귀 +{tolerance:.0%}", GRAY,
                    f"**판정 불가** — 측정 잡음 {float(sample['noise']):.0%} 가 문턱 "
                    f"{tolerance:.0%} 보다 크다 (p95 {sample.get('p95_min')}–"
                    f"{sample.get('p95_max')}ms · {sample.get('repeats')}벌). "
                    f"`runserver` 는 한 프로세스라 꼬리가 스케줄러를 탄다 — "
                    f"회귀 감시는 gunicorn+nginx 뒤에 뜻이 선다 (OPS-13)"))
    else:
        ceiling = float(base_p95) * (1.0 + tolerance)
        lo, hi = sample.get("p95_min"), sample.get("p95_max")
        src = baseline.get("source", "이 파일")
        if lo is not None and hi is not None and float(lo) <= ceiling < float(hi):
            # ★ **예산 갈래에 건 규칙을 회귀에도 건다.** 폭이 문턱을 걸치면
            #   511ms 인 벌은 통과이고 543ms 인 벌은 실패다 — 다시 재면 통과하고
            #   또 재면 실패하는 수를 빨강으로 적으면, 그 빨강은 코드가 아니라
            #   그날의 스케줄러를 가리킨다.
            #   ⚠ 이 검사는 위의 `noise > tolerance` 와 **다른 것을 잰다.**
            #     잡음 6%(문턱 20%보다 작다)여도 폭이 문턱을 걸칠 수 있다 —
            #     잡음은 「폭이 얼마나 넓은가」이고 이것은 「폭이 어디에 놓였는가」다.
            out.append((f"{label} · 회귀 +{tolerance:.0%}", GRAY,
                        f"**판정 불가** — {sample.get('repeats')}벌의 p95 가 "
                        f"{float(lo):.0f}–{float(hi):.0f}ms 로 회귀 문턱 "
                        f"{ceiling:.0f}ms(기준선 {float(base_p95):.0f}ms × "
                        f"{1 + tolerance:.2f})를 **걸친다.** 넘은 벌도 있고 든 벌도 "
                        f"있다 · 기준선 출처 {src}"))
        else:
            ok = p95 <= ceiling
            band = "" if lo is None else f" · {sample.get('repeats')}벌 {float(lo):.0f}–{float(hi):.0f}ms"
            out.append((f"{label} · 회귀 +{tolerance:.0%}", PASS if ok else FAIL,
                        f"p95 {p95:.0f}ms {'≤' if ok else '>'} 기준선 "
                        f"{float(base_p95):.0f}ms × {1 + tolerance:.2f} = {ceiling:.0f}ms"
                        f"{band} · 기준선 출처 {src}"))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 가용성 — **응답시간과 다른 칸** (세종 판정 P-53)
# ═══════════════════════════════════════════════════════════════════════════
def _bucket(status: int) -> str:
    """상태 하나를 갈래로. **0(도달 못 함)은 5xx 쪽**이다 — 사용자에게는 같은 고장이다."""
    if status <= 0 or 500 <= status < 600:
        return "5xx"
    if 400 <= status < 500:
        return "4xx"
    return "other"


def _split_errors(sample: dict) -> tuple[int, int, bool]:
    """`(5xx, 4xx, 추정했는가)`.

    ★ 낡은 증거(`errors_5xx` 가 없는 `budget.json`)에서도 판정할 수 있어야 한다 —
      그러지 않으면 이 갈래는 다시 재기 전까지 회색이고, 회색인 채로 잊힌다.
      그때는 `error_detail` 의 상태 코드로 갈래를 **추정**하고, 추정했다는 사실을
      사유에 적는다. `error_detail` 은 **중복을 지운 목록**이라 건수는 못 준다 —
      건수는 `errors` 에서 오고 갈래만 여기서 온다.
    """
    total = int(sample.get("errors", 0) or 0)
    if "errors_5xx" in sample:
        five = int(sample.get("errors_5xx") or 0)
        four = int(sample.get("errors_4xx") or 0)
        # 갈래 합이 총합에 못 미치면(3xx 등) 나머지는 5xx 쪽으로 센다 — 모르는 고장을
        # 「없는 고장」으로 접지 않는다.
        return five + max(0, total - five - four), four, False
    if not total:
        return 0, 0, False
    codes = [int(m.group(1))
             for line in (sample.get("error_detail") or [])
             if (m := re.search(r"->\s*(\d{1,3})", str(line)))]
    kinds = {_bucket(c) for c in codes}
    if kinds == {"4xx"}:
        return 0, total, True
    return total, 0, True


def judge_availability(faces: dict | None, *, budget: float = ERROR_BUDGET) -> list:
    """측정 **전체**의 오류율을 판정한다. `(이름, 판정, 사유)`.

    ★ 왜 면별이 아니라 전체인가 — SLA 가용성은 **서비스 한 대의 수**이고, 면별
      n=900 에서는 오류 1건이 곧 0.11% 라 **0.1% 예산이 태어나면서부터 빨갛다.**
      가르지 못하는 것을 갈랐다고 적으면 그 빨강은 다음 사람이 끈다(이 파일이
      회귀 갈래에서 이미 배운 규칙이다). 면별 수는 **사유에 적어** 어느 면이
      울었는지 보이게 한다 — 판정은 하나, 근거는 넷.

    ★ 4xx 는 **다른 고장**이다. 우리가 두드리는 자리는 전부 유효한 주소이고 토큰도
      있다. 그래서 4xx 에는 예산이 없다 — 계약이 어긋난 것이고 0건이어야 한다.
    """
    name5 = f"[전체] 가용성 · 5xx ≤ {budget:.1%}"
    name4 = "[전체] 계약 · 4xx 0건"
    out: list = []
    if not faces:
        out.append((name5, GRAY, "**못 쟀다** — 표본이 없다. 0건은 「안정적」이 아니다"))
        out.append((name4, GRAY, "**못 쟀다** — 표본이 없다"))
        return out

    n = sum(int(f.get("n") or 0) for f in faces.values())
    five = four = 0
    #: ★ [P-79] **주입한 5xx 는 SLA 의 5xx 가 아니다** — 일부러 만든 고장이기 때문이다.
    #:   그러나 뺀 건수와 사유를 **함께** 적지 않으면 이 빼기는 「빨강을 없애는 손잡이」가
    #:   된다. 그래서 0건이어도 적는다 — 0 이라고 적힌 줄이 「뺄 것이 없었다」의 증거다.
    injected = 0
    codes: dict = {}
    guessed = False
    per: list[str] = []
    for key in sorted(faces):
        f = faces[key] or {}
        a, b, g = _split_errors(f)
        five += a
        four += b
        injected += int(f.get("errors_5xx_injected") or 0)
        for code, cnt in (f.get("errors_5xx_by_status") or {}).items():
            codes[str(code)] = codes.get(str(code), 0) + int(cnt)
        guessed = guessed or g
        fn = int(f.get("n") or 0)
        per.append(f"{key} {a + b}/{fn}" + (f"={(a + b) / fn:.2%}" if fn else ""))
    detail = " · ".join(per)
    tail = " · ⚠ 갈래를 `error_detail` 로 **추정**했다(낡은 증거)" if guessed else ""
    #: 주입분을 **분자에서도 분모에서도** 뺀다 — 보내지 않았어야 할 요청이므로.
    five = max(0, five - injected)
    n = max(0, n - injected)
    ledger = (f" · 주입 제외 **{injected}건**"
              + (f"(표 `{INJECT_HEADER}` 가 붙은 요청)" if injected
                 else "(뺀 것이 없다 — 이 계량은 주입하지 않는다)"))
    if codes:
        ledger += " · 5xx 코드별 " + " ".join(f"{c}×{v}" for c, v in sorted(codes.items()))
    #: 회색 갈래에서도 보이게 `detail` 에 붙인다 — 못 잰 자리에서도 「무엇을 뺐는가」는
    #: 말해야 한다. 안 보이는 빼기가 손잡이가 된다.
    detail += ledger

    if not n:
        out.append((name5, GRAY, "**못 쟀다** — 표본 0건"))
    elif five == 0 and n < ERROR_MIN_N:
        out.append((name5, GRAY,
                    f"**못 쟀다** — 5xx 0건이지만 표본 {n:,}건은 {budget:.1%} 를 "
                    f"**증명하지 않는다.** 3/n 규칙으로 이 표본이 말할 수 있는 상한은 "
                    f"{3 / n:.2%} 다 — {budget:.1%} 를 확인하려면 최소 "
                    f"{ERROR_MIN_N:,}건이 필요하다. 면별 {detail}"))
    else:
        rate = five / n
        ok = rate <= budget
        out.append((name5, PASS if ok else FAIL,
                    f"5xx {five}/{n:,} = **{rate:.3%}** "
                    f"{'≤' if ok else '>'} {budget:.1%} "
                    f"(SLA 가용성 99.9% 월 환산 · 세종 P-53) · 면별 {detail}"
                    + tail
                    + ("" if ok else " — **응답시간이 아니라 가용성이 빨갛다.** "
                                     "고칠 자리는 예산 표가 아니라 앞단·워커다")))

    if four:
        out.append((name4, FAIL,
                    f"4xx {four}/{n:,} — 우리가 두드린 자리는 전부 **유효한 주소**이고 "
                    f"토큰도 있다. 4xx 는 느림도 가용성도 아니라 **계약이 어긋난 "
                    f"것**이다 · 면별 {detail}" + tail))
    elif n:
        out.append((name4, PASS, f"4xx 0/{n:,}"))
    else:
        out.append((name4, GRAY, "**못 쟀다** — 표본 0건"))
    return out


def evidence_path(*parts: str) -> Path:
    """증거 파일의 자리. ★ **자리를 하나로 박지 않는다** — 컨테이너는 `/repo`(=scripts)
    와 `/docs` 를 **따로** 마운트해 `/repo/docs` 가 없다 [실측 2026-09-05].
    호스트에서는 `<저장소>/docs` 다. 저장소가 이미 아는 함정이다
    (`verify_alarm_budget._refuse_if_shared_master` 가 같은 이유로 두 자리를 본다)."""
    #: `/docs` 를 먼저 본다 — 컨테이너에서 그 자리가 **진짜 마운트**다.
    #: 호스트(Windows)에는 `/docs` 가 없으므로 자연히 저장소의 `docs` 가 뽑힌다.
    bases = (Path("/docs"), ROOT / "docs")
    for base in bases:                       # ① 파일이 실제로 있는 자리
        cand = base.joinpath(*parts)
        if cand.is_file():
            return cand
    for base in bases:                       # ② 없으면 **마운트된 자리**에 쓴다
        if base.is_dir():                    #    없는 자리에 쓰면 컨테이너 안에만 남고
            return base.joinpath(*parts)     #    호스트의 게이트는 그 파일을 못 본다
    return ROOT.joinpath("docs", *parts)


#: PERF-01 이 남긴 증거. **기준선은 여기서 온다** — 이 게이트가 자기 측정을
#: 자기 기준선으로 삼으면 회귀 감시는 언제나 초록이고, 아무것도 감시하지 않는다.
PERF01_PARTS = ("agent", "evidence", "PERF-01", "load.json")


def baseline_from_perf01(path: Path | None = None) -> dict:
    """PERF-01 의 per_call p95 를 **면별 기준선**으로 접는다.

    한 면의 기준선은 그 면이 부르는 자리들 중 **가장 느린 것**이다 — 평균을 쓰면
    느린 한 자리가 빠른 자리에 묻히고, 예산은 언제나 가장 느린 자리에서 깨진다.
    PERF-01 에 없는 면(스냅샷·미디어)은 **없다고 적는다** — 지어내지 않는다.
    """
    doc = load_evidence(path or evidence_path(*PERF01_PARTS))
    if not doc:
        return {}
    seen: dict[str, float] = {}
    concurrency = doc.get("concurrency")
    for scenario in doc.get("scenarios", []):
        for call, stat in (scenario.get("per_call") or {}).items():
            p95 = stat.get("p95_ms")
            if p95 is not None:
                seen[call] = max(seen.get(call, 0.0), float(p95))
    out: dict = {}
    for key, face in FACES.items():
        hits = {c: seen[c] for c in face.calls if c in seen}
        if not hits:
            continue
        slowest = max(hits, key=hits.get)
        out[key] = {
            "p95_ms": hits[slowest],
            "concurrency": concurrency,
            "source": f"PERF-01 load.json · 가장 느린 자리 {slowest}",
            "covered_calls": sorted(hits),
        }
    return out


def judge_cache_frame(face_key: str, face: Face, patterns: list[str] | None) -> tuple:
    """① **구조** — 캐시 금지 면이 정말 우회 목록에 있는가 (P-19 · 서버 없이 돈다).

    이 검사가 없으면 「300ms 예산 통과」가 **캐시 적중 10ms** 로 채워질 수 있고,
    그 초록은 상태를 묻는 질문에 **과거의 답**을 준 것을 통과로 적는 일이다.
    """
    label = f"{face_key} 캐시 금지 (P-19)"
    if not face.cache_forbidden:
        return (label, PASS, "이 면은 캐시 금지 면이 아니다 — 검사하지 않는다")
    if patterns is None:
        return (label, GRAY, "**못 쟀다** — `BYPASS_PATTERNS` 를 못 읽었다 (D-301)")
    missing = []
    for path in face.calls:
        bare = path.split("?", 1)[0].lower()
        if not any(p.lower() in bare for p in patterns):
            missing.append(path)
    if missing:
        return (label, FAIL,
                f"{missing} 가 `BYPASS_PATTERNS` 에 안 걸린다 — 이 자리는 캐시된다. "
                f"상태를 묻는 질문에 과거의 답을 주면 그 답은 틀린 것이 아니라 "
                f"**질문에 답한 것이 아니다** (P-19)")
    return (label, PASS, f"{len(face.calls)}자리 전부 `BYPASS_PATTERNS` 에 걸린다")


def exit_code(rows: list) -> int:
    """판정 셋을 종료 코드 셋으로 옮긴다. **빨강 > 회색 > 초록** 순으로 이긴다.

    ★ 회색이 하나라도 있으면 초록이 아니다. 그러나 **빨강이 회색을 이긴다** —
      「재서 넘었다」가 「못 쟀다」보다 급한 사실이기 때문이다.
    """
    #: ★ `OVER` 는 여기 없다 — **기준선 초과는 종료 코드를 물들이지 않는다**
    #:   (세종 P-34). 대신 `pending_acceptance` 로 남아 OPS-13 을 닫는 사람 앞에 선다.
    verdicts = {v for (_n, v, _w) in rows}
    if FAIL in verdicts:
        return EXIT_FAIL
    if GRAY in verdicts:
        return EXIT_UNDECIDABLE
    return EXIT_OK


def percentile(values: list[float], pct: float) -> float:
    """p50·p95. ★ **한 벌만 둔다** — PERF-01 의 것을 그대로 쓴다 (D-369)."""
    from perf_load import percentile as _p                # noqa: PLC0415

    return _p(values, pct)


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성 대조가 있다** (D-277 · D-289)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list = []

    def verdicts(rows):
        return {n: v for (n, v, _w) in rows}

    face = FACES["F05"]
    green = {"n": 40, "errors": 0, "p95_ms": 410.0, "cache_bust": True}
    base = {"p95_ms": 400.0}

    got = verdicts(judge_face("F05", face, green, base))
    if set(got.values()) != {PASS}:
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── 예산 초과 ────────────────────────────────────────────────────────
    #   ★ 모드가 갈린 뒤로 「예산 초과」의 색은 둘이다: 기준선에서는 기록(OVER),
    #     합격선에서는 빨강(FAIL). **어느 쪽도 초록은 아니다** — 그것이 요점이다.
    over = verdicts(judge_face("F05", face, dict(green, p95_ms=501.0), {"p95_ms": 500.0}))
    if over.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != OVER:
        bad.append("p95 501ms 가 예산 500ms 를 넘었는데 기준선 모드에서 **기록조차** "
                   "남기지 않는다")
    over_acc = verdicts(judge_face("F05", face, dict(green, p95_ms=501.0),
                                   {"p95_ms": 500.0}, mode=MODE_ACCEPTANCE))
    if over_acc.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != FAIL:
        bad.append("p95 501ms 가 예산 500ms 를 넘었는데 합격선 모드에서 빨강이 아니다")

    # ── 회귀: 예산 안인데 기준선 대비 +20% 를 넘는다 ──────────────────────
    #   이 갈래가 이 게이트의 핵심이다. 「예산 안이면 됐지」로 접으면 성능은
    #   예산 문턱까지 **조용히** 나빠지고, 나빠진 날을 아무도 못 짚는다.
    creep = verdicts(judge_face("F05", face, dict(green, p95_ms=490.0), {"p95_ms": 400.0}))
    if creep.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != FAIL:
        bad.append("예산 안(490ms)이지만 기준선 400ms 의 +22.5% 인데 회귀를 못 잡는다 — "
                   "이 갈래를 놓치면 성능은 예산 문턱까지 조용히 나빠진다")
    if creep.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != PASS:
        bad.append("회귀 갈래가 예산 갈래를 오염시킨다 — 두 수는 따로 판정한다")
    edge = verdicts(judge_face("F05", face, dict(green, p95_ms=480.0), {"p95_ms": 400.0}))
    if edge.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != PASS:
        bad.append("정확히 +20%(480ms)를 **초과가 아닌데** 빨강으로 읽는다 — "
                   "판정은 「초과 시 빨강」이다")

    # ── 흩어진 폭이 예산을 **걸치면** 판정하지 않는다 ─────────────────────
    straddle = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=517.0, p95_min=498.0, p95_max=564.0, repeats=3),
        {"p95_ms": 500.0}))
    if straddle.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != GRAY:
        bad.append("3벌이 498–564ms 로 예산 500ms 를 **걸치는데** 단정한다 — "
                   "다시 재면 통과하고 또 재면 실패하는 수는 판정이 아니다")
    allover = verdicts(judge_face(
        "STATUS", FACES["STATUS"],
        dict(green, p95_ms=352.8, p95_min=350.0, p95_max=410.0, repeats=3),
        {"p95_ms": 416.8}))
    if allover.get("STATUS 상태·가용성 (캐시 금지 · P-19) · 예산 300ms") != OVER:
        bad.append("3벌 **전부**(350–410ms)가 300ms 예산을 넘었는데 기준선 모드에서 "
                   "기록조차 안 남긴다 — 걸침 규칙이 진짜 초과까지 삼켰다")
    allover_acc = verdicts(judge_face(
        "STATUS", FACES["STATUS"],
        dict(green, p95_ms=352.8, p95_min=350.0, p95_max=410.0, repeats=3),
        {"p95_ms": 416.8}, mode=MODE_ACCEPTANCE))
    if allover_acc.get("STATUS 상태·가용성 (캐시 금지 · P-19) · 예산 300ms") != FAIL:
        bad.append("3벌 전부가 300ms 예산을 넘었는데 **합격선 모드에서도** 빨강이 아니다")
    allunder = verdicts(judge_face(
        "SCREEN", FACES["SCREEN"],
        dict(green, p95_ms=480.6, p95_min=394.0, p95_max=543.0, repeats=3),
        {"p95_ms": 590.2}))
    if allunder.get("SCREEN 화면 API · 예산 800ms") != PASS:
        bad.append("3벌 전부가 800ms 예산 안(394–543ms)인데 초록이 아니다")

    # ── ★ 정정 ① — **회귀 문턱을 걸치면 회귀도 회색이다** ─────────────────
    #   출생 표본: [실측 2026-09-05] F05 3벌 511–543ms · 기준선 429.8ms.
    #   문턱은 429.8 × 1.20 = 515.8ms 이고 **폭이 그 문턱을 걸친다** — 511 인 벌은
    #   통과, 543 인 벌은 실패다. 잡음은 6.2% 로 문턱 20% 보다 **작다**: 두 검사는
    #   다른 것을 잰다(잡음=폭이 얼마나 넓은가 · 걸침=폭이 어디에 놓였는가).
    reg_straddle = dict(green, p95_ms=518.9, p95_min=511.0, p95_max=543.0,
                        noise=0.062, repeats=3)
    rs = verdicts(judge_face("F05", face, reg_straddle, {"p95_ms": 429.8}))
    if rs.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != GRAY:
        bad.append("3벌이 511–543ms 로 회귀 문턱 516ms 를 **걸치는데** 빨강으로 "
                   "단정한다 — 잡음(6%)이 문턱(20%)보다 작다는 것은 폭이 문턱을 "
                   "안 걸친다는 뜻이 아니다. 예산 갈래에 건 규칙이 회귀 갈래에만 없다")
    # 걸침 규칙이 **진짜 회귀까지 삼키면** 안 된다 — 폭이 문턱 위에 온전히 있으면 빨강
    reg_over = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=620.0, p95_min=600.0, p95_max=650.0,
                          noise=0.08, repeats=3), {"p95_ms": 429.8}))
    if reg_over.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != FAIL:
        bad.append("3벌 **전부**(600–650ms)가 회귀 문턱 516ms 위인데 빨강이 아니다 — "
                   "걸침 규칙이 진짜 회귀까지 삼켰다")
    reg_under = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=440.0, p95_min=430.0, p95_max=450.0,
                          noise=0.05, repeats=3), {"p95_ms": 429.8}))
    if reg_under.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != PASS:
        bad.append("3벌 전부가 문턱 516ms 아래(430–450ms)인데 초록이 아니다")

    # ── ★ 정정 ② — **모드가 판정을 가른다** (세종 P-34) ───────────────────
    over_sample = dict(green, p95_ms=518.9, p95_min=511.0, p95_max=543.0, repeats=3)
    base_mode = verdicts(judge_face("F05", face, over_sample, {"p95_ms": 500.0},
                                    mode=MODE_BASELINE))
    if base_mode.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != OVER:
        bad.append("**기준선 모드**에서 절대 예산 초과를 빨강으로 낸다 — 세종 P-34 는 "
                   "「그때까지 회색 아님 — 기준선으로 초록」이라 했고, 태어나면서부터 "
                   "빨간 게이트는 다음 사람이 우회한다")
    acc_mode = verdicts(judge_face("F05", face, over_sample, {"p95_ms": 500.0},
                                   mode=MODE_ACCEPTANCE))
    if acc_mode.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != FAIL:
        bad.append("**합격선 모드**에서 예산 초과가 빨강이 아니다 — 그러면 모드를 "
                   "가른 뜻이 없고, 이 정정은 그냥 면제가 된다")
    # 모드는 예산 갈래**만** 가른다. 회귀는 두 모드에서 같아야 한다.
    if (base_mode.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%")
            != acc_mode.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%")):
        bad.append("모드가 **회귀 갈래까지** 가른다 — 회귀는 상대값이라 서버 종류와 "
                   "무관하다. 모드가 가르는 것은 절대 예산뿐이다")

    # ── 모드 판별은 **서버가 스스로 말하는 이름**으로 한다 (D-286) ────────
    for header, want, why in (
        ("WSGIServer/0.2 CPython/3.11.14", MODE_BASELINE, "Django 개발 서버"),
        ("gunicorn/21.2.0", MODE_ACCEPTANCE, "운영 앞단"),
        ("nginx", MODE_ACCEPTANCE, "운영 앞단"),
        (None, MODE_ACCEPTANCE, "못 읽었다 — 모르는 서버를 기준선으로 접으면 "
                                "진짜 운영이 조용히 면제를 받는다"),
    ):
        if mode_for(header) != want:
            bad.append(f"Server: {header!r} 를 {mode_for(header)} 로 읽는다 "
                       f"({want} 이어야 한다 — {why})")

    # ── `OVER` 는 **종료 코드를 물들이지 않는다** ─────────────────────────
    if exit_code([("a", PASS, ""), ("b", OVER, "")]) != EXIT_OK:
        bad.append("기준선 초과가 종료 코드를 빨강으로 물들인다 — 세종 P-34 와 어긋난다")
    if exit_code([("a", OVER, ""), ("b", GRAY, "")]) != EXIT_UNDECIDABLE:
        bad.append("기준선 초과가 회색을 덮는다")
    if exit_code([("a", OVER, ""), ("b", FAIL, "")]) != EXIT_FAIL:
        bad.append("기준선 초과가 빨강을 덮는다")

    # ── ★ 세종 판정 P-53 — **응답시간 칸과 오류율 칸을 가른다** ──────────
    #
    # ★★ **출생 표본** (D-310) — 이 갈래를 만들게 한 바로 그 사례다.
    #    [실측 2026-09-05 · 턴 D · `budget.json`] gx-nginx-e 앞단에서 3,600 표본
    #    (보고된 총 요청 3,722)을 냈고 **502 가 8건**이었다. 네 면의 p95 는 전부
    #    예산 안이었다(F05 217ms ≤ 500ms · SCREEN 225 ≤ 800 · MEDIA 179 ≤ 1000 ·
    #    STATUS 181 ≤ 300). 그런데 이 게이트는 **예산 칸에 빨강**을 적었다 —
    #    「오류가 있으면 예산과 무관하게 빨강」이었기 때문이다.
    #    사람은 그 빨강을 「응답시간이 예산을 넘었다」로 읽었고(PERF-04),
    #    실제로 넘은 것은 **가용성**(OPS-13a · 워커 재활용)이었다.
    #    **한 칸에 두 고장을 적으면 어느 쪽이 빨간지 아무도 모른다.**
    birth_perf = dict(green, n=900, errors=2, errors_5xx=2, errors_4xx=0,
                      p95_ms=217.3, p95_min=168.0, p95_max=274.5,
                      noise=0.49, repeats=3, concurrency=10)
    born = verdicts(judge_face("F05", face, birth_perf,
                               {"p95_ms": 417.1, "concurrency": 10}))
    if born.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != PASS:
        bad.append("**출생 표본**(턴 D · 502 2건 · p95 217ms ≤ 500ms)의 **응답시간 "
                   "칸**이 초록이 아니다 — 오류가 예산 칸을 물들이면 PERF-04 와 "
                   "OPS-13a 를 가릴 수 없다 (세종 P-53)")
    avail = verdicts(judge_availability({"F05": birth_perf}))
    if avail.get("[전체] 가용성 · 5xx ≤ 0.1%") != FAIL:
        bad.append("**출생 표본**의 5xx 2/900 = 0.22% 가 0.1% 예산을 넘었는데 "
                   "가용성 칸이 빨강이 아니다 — 갈라 적는 것은 면제가 아니다")

    # 둘은 **함께 종료 코드에 든다.** 응답시간만 초록이면 통과가 되는 게이트는
    # 오류율 예산을 적어 두고도 아무것도 막지 않는다.
    if exit_code([("응답시간", PASS, ""), ("가용성", FAIL, "")]) != EXIT_FAIL:
        bad.append("오류율 빨강이 종료 코드에 들지 않는다 — 갈랐더니 사라졌다")

    # 오류율 예산 안이면 **초록**이다 (0.1% 는 0건이 아니다).
    inside = verdicts(judge_availability(
        {"F05": {"n": 4000, "errors": 3, "errors_5xx": 3, "errors_4xx": 0}}))
    if inside.get("[전체] 가용성 · 5xx ≤ 0.1%") != PASS:
        bad.append("5xx 3/4,000 = 0.075% 는 예산 안인데 빨강이다 — 예산을 「0건」으로 "
                   "읽으면 그 게이트는 영원히 빨갛고, 영원히 빨간 게이트는 죽는다")

    # **3/n 규칙** — 작은 표본의 「0건」은 0.1% 를 증명하지 않는다.
    tiny = verdicts(judge_availability({"F05": {"n": 40, "errors": 0,
                                                "errors_5xx": 0, "errors_4xx": 0}}))
    if tiny.get("[전체] 가용성 · 5xx ≤ 0.1%") != GRAY:
        bad.append("40건에서 오류 0건을 보고 가용성 99.9% 를 **초록**으로 적는다 — "
                   "3/n 규칙으로 이 표본이 말할 수 있는 상한은 7.5% 다")
    big = verdicts(judge_availability({"F05": {"n": 4000, "errors": 0,
                                               "errors_5xx": 0, "errors_4xx": 0}}))
    if big.get("[전체] 가용성 · 5xx ≤ 0.1%") != PASS:
        bad.append("4,000건 오류 0건이 초록이 아니다 — 3/n 규칙을 넘겼는데도 회색이면 "
                   "이 갈래는 영원히 회색이다")

    # ── ★ [P-79 · 2026-09-06] **주입한 5xx 는 SLA 의 5xx 가 아니다.** 그러나
    #    빼기가 「빨강을 없애는 손잡이」가 되면 안 된다. 갈래 셋으로 잠근다.
    #
    #    출생 표본: 턴 G 의 0.139%(5/3,600)는 **전부 502**였고 주입은 한 건도 없었다.
    #    같은 시각 다른 차선이 돌린 오류 주입은 브라우저 안에서 끝나(walk_states —
    #    Playwright 요청 가로채기) **서버에 닿지 않았다.** 뺄 것이 없었다는 뜻이고,
    #    그 사실은 「뺐다」는 말이 아니라 **0 이라고 적힌 줄**이 증명해야 한다.
    inj = verdicts(judge_availability(
        {"F05": {"n": 4000, "errors": 8, "errors_5xx": 8, "errors_4xx": 0,
                 "errors_5xx_injected": 8,
                 "errors_5xx_by_status": {"503": 8}}}))
    if inj.get("[전체] 가용성 · 5xx ≤ 0.1%") != PASS:
        bad.append("주입 표가 붙은 5xx 8건을 SLA 분자에서 빼지 않았다 — "
                   "일부러 만든 고장은 가용성의 고장이 아니다")
    if "주입 제외 **8건**" not in " ".join(w for _n, _v, w in judge_availability(
            {"F05": {"n": 4000, "errors": 8, "errors_5xx": 8, "errors_4xx": 0,
                     "errors_5xx_injected": 8,
                     "errors_5xx_by_status": {"503": 8}}})):
        bad.append("뺀 건수를 사유에 안 적었다 — **적히지 않는 빼기가 손잡이가 된다**")

    #    ⚠ 표가 없는 5xx 는 **502 든 500 이든 빠지지 않는다.** 사용자에게는 같은 고장이다.
    notinj = verdicts(judge_availability(
        {"F05": {"n": 3600, "errors": 5, "errors_5xx": 5, "errors_4xx": 0,
                 "errors_5xx_injected": 0,
                 "errors_5xx_by_status": {"502": 5}}}))
    if notinj.get("[전체] 가용성 · 5xx ≤ 0.1%") != FAIL:
        bad.append("★ **출생 표본**(턴 G · 502 5/3,600 = 0.139%)이 빨강이 아니다 — "
                   "주입이 아닌 502 를 빼면 그 빼기는 빨강을 없애는 손잡이다")

    #    뺄 것이 없어도 **0 이라고 적는다** — 0 이라고 적힌 줄이 「뺄 것이 없었다」의 증거다.
    if "주입 제외 **0건**(뺀 것이 없다" not in " ".join(w for _n, _v, w in
            judge_availability({"F05": {"n": 3600, "errors": 5, "errors_5xx": 5,
                                        "errors_4xx": 0, "errors_5xx_injected": 0,
                                        "errors_5xx_by_status": {"502": 5}}})):
        bad.append("주입 0건을 적지 않는다 — 안 적힌 0 은 「안 쟀다」와 구분되지 않는다")

    # **4xx 는 다른 고장이다.** 유효한 주소에 유효한 토큰으로 두드린 자리다.
    contract = verdicts(judge_availability(
        {"F05": {"n": 4000, "errors": 1, "errors_5xx": 0, "errors_4xx": 1}}))
    if contract.get("[전체] 계약 · 4xx 0건") != FAIL:
        bad.append("4xx 1건이 초록이다 — 4xx 에는 예산이 없다(계약이 어긋난 것)")
    if contract.get("[전체] 가용성 · 5xx ≤ 0.1%") != PASS:
        bad.append("4xx 가 **가용성 칸까지** 물들인다 — 두 칸을 가른 뜻이 없다")

    # 낡은 증거(갈래 없음)에서도 **판정한다** — 회색인 채로 잊히지 않게.
    legacy = verdicts(judge_availability(
        {"F05": {"n": 900, "errors": 2,
                 "error_detail": ["/api/dsm/events?limit=50 -> 502"]}}))
    if legacy.get("[전체] 가용성 · 5xx ≤ 0.1%") != FAIL:
        bad.append("`errors_5xx` 가 없는 낡은 증거를 판정하지 못한다 — 그 회색은 "
                   "다시 잴 때까지 아무도 안 본다")

    # 표본이 없으면 **회색**이다 (D-301).
    if verdicts(judge_availability(None)).get("[전체] 가용성 · 5xx ≤ 0.1%") != GRAY:
        bad.append("표본이 없는데 가용성이 회색이 아니다")

    # ── 오류가 표본을 먹으면 **응답시간을 판정하지 않는다** ───────────────
    #   502 는 앞단이 즉시 끊으므로 빠르다. 반이 502 인 표본의 p95 1ms 를
    #   「빠르다」로 읽으면, 서버가 죽을수록 이 게이트가 초록이 된다.
    poisoned = verdicts(judge_face(
        "F05", face, dict(green, n=100, errors=50, errors_5xx=50, p95_ms=1.0), base))
    if poisoned.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != GRAY:
        bad.append("표본의 50%가 502 인데 「1ms 라 빠르다」를 **초록**으로 읽는다 — "
                   "서버가 죽을수록 초록이 되는 게이트다")

    # ── ★ 출생 표본 (D-310) — **캐시 적중을 성능으로 적는 것** ────────────
    #   [실측 2026-09-19 · D-412] MinIO 를 내린 채 같은 순간에 두 번 물었다:
    #       GET /api/media-data/         → 200 · 0.01s  (캐시)
    #       GET /api/media-data/?bust=…  → 500 · 6.68s  (실제)
    #   왼쪽 수를 예산 판정에 넣으면 저장소가 죽은 채로 **1,000ms 예산 통과**가 난다.
    birth = verdicts(judge_face("MEDIA", FACES["MEDIA"],
                                {"n": 40, "errors": 0, "p95_ms": 10.0,
                                 "cache_bust": False},
                                {"p95_ms": 600.0}))
    if birth.get("MEDIA 스냅샷·미디어 · 예산 1000ms") == PASS:
        bad.append("**출생 표본**(캐시 적중 10ms · 비낌 없음)을 예산 통과로 읽는다 — "
                   "그 수는 우리 코드가 아니라 Redis 를 잰 것이다 (D-412)")

    # ── 못 쟀다 ≠ 통과 ──────────────────────────────────────────────────
    none_rows = judge_face("F05", face, None, base)
    if {v for (_n, v, _w) in none_rows} != {GRAY}:
        bad.append("표본이 **없는데** 회색이 아니다 (D-301)")
    zero_rows = judge_face("F05", face, {"n": 0, "errors": 0, "p95_ms": 0.0,
                                         "cache_bust": True}, base)
    if {v for (_n, v, _w) in zero_rows} != {GRAY}:
        bad.append("표본 0건을 「0ms 라 빠르다」로 읽는다 — 0건은 빠른 것이 아니다")
    nobase = verdicts(judge_face("F05", face, green, None))
    if nobase.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != GRAY:
        bad.append("기준선이 없는데 회귀를 초록으로 읽는다")

    # ── 동시성이 다른 두 p95 는 **같은 것이 아니다** (착시 ⑤) ─────────────
    skew = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=130.0, concurrency=4),
        {"p95_ms": 417.1, "concurrency": 10}))
    if skew.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != GRAY:
        bad.append("동시 4의 130ms 를 동시 10의 417ms 기준선에 견주고 **초록**을 낸다 — "
                   "그 초록은 「빨라졌다」가 아니라 다른 것 둘을 견준 것이다")
    same = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=600.0, concurrency=10),
        {"p95_ms": 417.1, "concurrency": 10}))
    if same.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != FAIL:
        bad.append("동시성이 같은데(둘 다 10) 417ms → 600ms 회귀를 못 잡는다")

    # ── 잡음이 문턱보다 넓으면 **회귀를 판정하지 않는다** ─────────────────
    #   흩어진 폭이 예산보다 **온전히 위**인 표본을 쓴다 — 예산 갈래는 빨강이고
    #   회귀 갈래만 회색이어야 한다. 두 갈래는 서로를 흐리지 않는다.
    noisy = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=600.0, noise=0.28, p95_min=560.0,
                          p95_max=720.0, repeats=3),
        {"p95_ms": 417.1}))
    if noisy.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != GRAY:
        bad.append("같은 조건 재측정이 560–720ms(잡음 28%)로 흩어지는데 회귀를 "
                   "**빨강으로 단정한다** — 그 빨강은 성능이 아니라 그날의 스케줄러다")
    if noisy.get("F05 계약 F-05 진입면 (NFR-05-1) · 예산 500ms") != OVER:
        bad.append("잡음 갈래가 **예산 갈래까지** 흐린다 — 전 벌이 예산 위에 있으면 "
                   "잡음과 무관하게 (기준선 모드에서는) 기록이 남아야 한다")
    quiet = verdicts(judge_face(
        "F05", face, dict(green, p95_ms=600.0, noise=0.05, p95_min=590.0,
                          p95_max=620.0, repeats=3),
        {"p95_ms": 417.1}))
    if quiet.get("F05 계약 F-05 진입면 (NFR-05-1) · 회귀 +20%") != FAIL:
        bad.append("잡음 5%(문턱보다 좁다)인데 417→600ms 회귀를 못 잡는다 — "
                   "잡음 갈래가 회귀 감시를 통째로 삼켰다")

    # ── 종료 코드 셋이 **갈라져 있는가** ─────────────────────────────────
    for rows, want, why in (
        ([("a", PASS, "")], EXIT_OK, "전부 초록"),
        ([("a", PASS, ""), ("b", GRAY, "")], EXIT_UNDECIDABLE, "회색이 섞이면 회색"),
        ([("a", GRAY, ""), ("b", FAIL, "")], EXIT_FAIL, "빨강이 회색을 이긴다"),
        ([("a", FAIL, "")], EXIT_FAIL, "전부 빨강"),
    ):
        if exit_code(rows) != want:
            bad.append(f"종료 코드가 갈리지 않는다 ({why}): {exit_code(rows)} ≠ {want}")

    # ── 구조 검사 ────────────────────────────────────────────────────────
    if judge_cache_frame("STATUS", FACES["STATUS"], ["dsm/"])[1] != PASS:
        bad.append("`dsm/` 우회가 있는데 STATUS 면을 빨강으로 읽는다")
    if judge_cache_frame("STATUS", FACES["STATUS"], ["orders/"])[1] != FAIL:
        bad.append("캐시 금지 면이 우회 목록에 **없는데** 빨강이 아니다 — "
                   "그러면 300ms 예산이 캐시 적중으로 채워질 수 있다")
    if judge_cache_frame("STATUS", FACES["STATUS"], None)[1] != GRAY:
        bad.append("우회 목록을 **못 읽었는데** 회색이 아니다 (D-301)")

    # ── 예산 표가 위임 판정과 어긋나지 않는가 (옮겨 적기 사고 방지) ───────
    want_budgets = {"F05": 500.0, "SCREEN": 800.0, "MEDIA": 1000.0, "STATUS": 300.0}
    got_budgets = {k: v.budget_ms for k, v in FACES.items()}
    if got_budgets != want_budgets:
        bad.append(f"예산 표가 위임 판정 P-34 와 다르다: {got_budgets} ≠ {want_budgets}")
    if abs(REGRESSION_TOLERANCE - 0.20) > 1e-9:
        bad.append("회귀 문턱이 20% 가 아니다")

    # ── 단서가 출력에 **실제로** 실리는가 ────────────────────────────────
    for token in ("기준선", "gunicorn", "OPS-13"):
        if token not in BASELINE_CAVEAT:
            bad.append(f"단서에서 「{token}」 가 사라졌다 — 이 문장이 없으면 다음 사람이 "
                       f"기준선을 합격선으로 읽는다")

    if bad:
        print("[PERF-BUDGET] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[PERF-BUDGET] 자기시험 통과 — 초록 1 · 예산초과 2(모드별) · **회귀 1** · "
          "**P-53 응답시간/오류율 가르기 10**(출생 표본 턴 D 502 8건 포함) · "
          "출생 표본 1(캐시 적중) · 회색 3 · 동시성 대조 2 · 잡음 대조 3 · 걸침 대조 3 · **회귀 걸침 3** · **모드 7** · 종료코드 7 · 구조 3 · 표 대조 2")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 구조 — 서버 없이 읽는다
# ═══════════════════════════════════════════════════════════════════════════
def bypass_patterns() -> list[str] | None:
    """`BYPASS_PATTERNS` 의 실제 원소. ★ **한 벌만 둔다** — D-413 이 이미 판 자리를
    다시 파지 않는다(`verify_cache_frame`). 두 벌은 반드시 어긋난다 (D-369)."""
    try:
        from verify_cache_frame import _bypass_patterns, _read   # noqa: PLC0415

        return _bypass_patterns(_read(CACHE_SRC))
    except Exception:                                    # noqa: BLE001
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **호출마다 캐시를 비낀다**
# ═══════════════════════════════════════════════════════════════════════════
def _bust(path: str) -> str:
    """질의문자열 하나로 캐시를 비낀다. **매 호출 다른 값**이어야 한다."""
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}bust={time.time_ns()}"


def measure(api: str, token: str, *, concurrency: int, rounds: int,
            repeat: int = 1) -> dict:
    """면마다 문을 두드려 p50·p95 를 낸다. 오류는 세고 **덮지 않는다.**

    ★ **한 번 재고 끝내지 않는다** — 같은 벌을 `repeat` 번 재고 **가운데 p95** 를 쓴다.
      [실측 2026-09-05] `runserver` 에서 같은 코드·같은 조건의 F05 p95 가 한 번은
      414ms, 다음 번은 528ms 였다(+28%). 한 번 잰 수로 회귀(문턱 20%)를 판정하면
      이 게이트가 잡는 것은 성능이 아니라 **그날의 스케줄러**다. 흩어진 폭은
      `p95_min`·`p95_max`·`noise` 로 남기고, 그 폭이 문턱보다 크면 회귀 판정은
      **회색**이 된다(`judge_face`) — 못 가르는 것을 갈랐다고 적지 않는다.
    """
    from verify_route_alive import hit                    # noqa: PLC0415

    def one(path: str):
        #: ★ [P-79] 계량 요청에 이름을 단다. 주입하는 호출이면 주입 표까지 단다 —
        #:   그래야 나중에 「이 5xx 는 누가 만든 것인가」를 사유가 아니라 **표**로 답한다.
        headers = {PROBE_HEADER: PROBE_VALUE}
        if path in INJECTED_CALLS:
            headers[INJECT_HEADER] = "1"
        started = time.perf_counter()
        status = hit(api, "GET", _bust(path), token, headers=headers)
        return path, status, (time.perf_counter() - started) * 1000.0

    passes: list[dict] = []
    for attempt in range(max(1, repeat)):
        passes.append(_one_pass(one, concurrency=concurrency, rounds=rounds))
        print(f"[PERF-BUDGET]   {attempt + 1}차: " + " · ".join(
            f"{k} p95 {v['p95_ms']:.0f}ms" for k, v in passes[-1].items()))
    return _fold(passes, concurrency=concurrency)


def _one_pass(one, *, concurrency: int, rounds: int) -> dict:
    """한 벌을 한 번 잰다."""
    faces: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for key, face in FACES.items():
            samples: list[float] = []
            per_call: dict[str, list[float]] = {}
            errors: list[str] = []
            #: ★ **갈래를 재는 순간에 센다** (P-53). `error_detail` 은 중복을 지운
            #:   목록이라 나중에 세면 건수를 잃는다 — 502 여덟 건이 한 줄로 접힌다.
            by_kind = {"5xx": 0, "4xx": 0, "other": 0}
            #: ★ [P-79] **주입한 5xx** 와 상태 코드별 건수. 앞의 것은 SLA 분모에서
            #:   빼고(뺀 건수를 적는다), 뒤의 것은 502(앞단)와 500(응용)을 **보이게만**
            #:   한다 — 보이는 것과 빼는 것은 다른 일이다.
            injected5 = 0
            by_status: dict = {}
            for round_no in range(rounds + WARMUP_ROUNDS):
                batch = [face.calls[i % len(face.calls)] for i in range(concurrency)]
                for path, status, elapsed in pool.map(one, batch):
                    if round_no < WARMUP_ROUNDS:
                        continue        # 워밍업은 버린다 — 다른 것을 재고 있다
                    if not (200 <= status < 300):
                        errors.append(f"{path} -> {status}")
                        by_kind[_bucket(status)] += 1
                        by_status[str(status)] = by_status.get(str(status), 0) + 1
                        if _bucket(status) == "5xx" and path in INJECTED_CALLS:
                            injected5 += 1
                    samples.append(elapsed)
                    per_call.setdefault(path, []).append(elapsed)
            faces[key] = {
                "title": face.title,
                "budget_ms": face.budget_ms,
                "concurrency": concurrency,
                "n": len(samples),
                "errors": len(errors),
                #: 갈래를 나눠 둔다 — 「느린 것」과 「틀린 것」을 가르고(P-53),
                #: 틀린 것 안에서 다시 **가용성(5xx)** 과 **계약(4xx)** 을 가른다.
                "errors_5xx": by_kind["5xx"],
                "errors_4xx": by_kind["4xx"],
                #: ★ [P-79] 주입 표가 붙은 요청의 5xx. **이것만** 분모에서 뺀다
                "errors_5xx_injected": injected5,
                "errors_5xx_by_status": dict(sorted(by_status.items())),
                "error_detail": sorted(set(errors))[:6],
                "cache_bust": True,      # 위 `_bust` 가 매 호출 다른 값을 붙였다
                "p50_ms": round(percentile(samples, 50), 1) if samples else 0.0,
                "p95_ms": round(percentile(samples, 95), 1) if samples else 0.0,
                "max_ms": round(max(samples), 1) if samples else 0.0,
                "mean_ms": round(statistics.fmean(samples), 1) if samples else 0.0,
                "per_call": {p: {"n": len(v),
                                 "p50_ms": round(percentile(v, 50), 1),
                                 "p95_ms": round(percentile(v, 95), 1)}
                             for p, v in sorted(per_call.items())},
            }
    return faces


def _fold(passes: list[dict], *, concurrency: int) -> dict:
    """여러 벌을 **가운데 값**으로 접는다. 평균이 아니다 — 한 번의 튐이 평균을 끈다."""
    out: dict = {}
    for key, face in FACES.items():
        p95s = [p[key]["p95_ms"] for p in passes]
        p50s = [p[key]["p50_ms"] for p in passes]
        median = statistics.median(p95s)
        errors = sum(p[key]["errors"] for p in passes)
        five = sum(p[key].get("errors_5xx", 0) for p in passes)
        four = sum(p[key].get("errors_4xx", 0) for p in passes)
        inj = sum(p[key].get("errors_5xx_injected", 0) for p in passes)
        by_status: dict = {}
        for p in passes:
            for code, cnt in (p[key].get("errors_5xx_by_status") or {}).items():
                by_status[code] = by_status.get(code, 0) + cnt
        detail = sorted({d for p in passes for d in p[key]["error_detail"]})[:6]
        out[key] = {
            "title": face.title,
            "budget_ms": face.budget_ms,
            "concurrency": concurrency,
            "repeats": len(passes),
            "n": sum(p[key]["n"] for p in passes),
            "errors": errors,
            "errors_5xx": five,
            "errors_4xx": four,
            "errors_5xx_injected": inj,
            "errors_5xx_by_status": dict(sorted(by_status.items())),
            "error_detail": detail,
            "cache_bust": True,          # 매 호출 다른 `?bust=` 를 붙였다
            "p50_ms": round(statistics.median(p50s), 1),
            "p95_ms": round(median, 1),
            "p95_each": [round(v, 1) for v in p95s],
            "p95_min": round(min(p95s), 1),
            "p95_max": round(max(p95s), 1),
            #: 흩어진 폭을 가운데 값으로 나눈 것. 이 수가 회귀 문턱보다 크면
            #: 이 환경에서 회귀는 **판정할 수 없다** (측정 잡음이 신호보다 크다).
            "noise": round((max(p95s) - min(p95s)) / median, 3) if median else None,
            "per_call": passes[-1][key]["per_call"],
        }
        print(f"[PERF-BUDGET]   {key:6} {face.title[:28]:30} n={out[key]['n']:<4} "
              f"p95(가운데) {out[key]['p95_ms']:7.1f}ms "
              f"[{out[key]['p95_min']:.0f}–{out[key]['p95_max']:.0f}] "
              f"· 잡음 {out[key]['noise']:.0%} · 오류 {errors}"
              f" (5xx {five} · 4xx {four})")
    return out


def server_header(api: str, token: str | None) -> str | None:
    """대상의 `Server:` 헤더. **모드는 이 한 줄이 정한다** (`mode_for`).

    `verify_route_alive.hit` 은 상태만 돌려주므로 여기서 직접 연다 — 베끼는 것이
    아니라 **다른 것을 묻는 것**이다(그쪽은 「문이 열리는가」, 이쪽은 「누가 문지기인가」).
    """
    import urllib.request                                   # noqa: PLC0415

    req = urllib.request.Request(api + _bust("/api/dsm/events?limit=1"), method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.headers.get("Server")
    except Exception as exc:                                # noqa: BLE001
        got = getattr(exc, "headers", None)
        return got.get("Server") if got is not None else None


def _environment() -> dict:
    """환경 한 벌. `perf_measure.environment()` 을 그대로 쓴다 (D-369)."""
    try:
        from perf_measure import environment                # noqa: PLC0415

        return environment()
    except Exception as exc:                                # noqa: BLE001
        return {"읽지 못함": f"{type(exc).__name__}: {exc}"}


def _co_resident() -> dict:
    """★ **같은 컨테이너에 다른 서버가 몇 개 서 있는가** [실측 2026-09-05].

    이 저장소는 차선마다 다른 포트로 `runserver` 를 띄운다(8000·8300·8400…). 셋이
    한 컨테이너의 CPU 를 나눠 쓰면 **내 p95 는 남의 부하를 함께 잰다** — 같은 코드로
    10분 사이에 414ms 와 608ms 를 본 이유가 그것이다. 재는 사람이 이 수를 못 보면
    그 흔들림을 코드의 회귀로 읽는다. 그래서 수와 **함께** 적는다.
    """
    out: dict = {"runserver_processes": None, "loadavg": None}
    try:
        procs = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(
                    bytes([0]), b" ").decode("utf-8", "replace")
            except OSError:
                continue
            if "runserver" in cmd:
                procs.append(cmd.strip()[:120])
        out["runserver_processes"] = sorted(set(procs))
    except Exception:                                       # noqa: BLE001
        pass
    try:
        out["loadavg"] = Path("/proc/loadavg").read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return out


def load_evidence(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="PERF-04 응답시간 예산과 회귀 감시")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--measure", action="store_true",
                    help="실제로 문을 두드려 잰다 (컨테이너 안에서 · GX_API 필요)")
    ap.add_argument("--set-baseline", action="store_true",
                    help="이번 측정을 **기준선으로 박는다**. 기준선이 없을 때는 저절로 박힌다")
    ap.add_argument("--evidence", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    ap.add_argument("--repeat", type=int, default=DEFAULT_REPEAT,
                    help="같은 벌을 몇 번 재고 **가운데 p95** 를 쓸 것인가")
    ap.add_argument("--acceptance", action="store_true",
                    help="합격선 모드를 **손수** 켠다. 본줄기는 자동 전환이다 — "
                         "대상이 runserver 가 아니면 저절로 합격선이다 (D-286)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    doc_path = Path(args.out or args.evidence
                    or evidence_path(*DEFAULT_EVIDENCE_PARTS))
    doc = load_evidence(doc_path) or {}

    if args.measure:
        api = os.environ.get("GX_API", "").rstrip("/")
        user = os.environ.get("GX_ROUTE_USER", "")
        password = os.environ.get("GX_ROUTE_PASSWORD", "")
        if not (api and user and password):
            print("[PERF-BUDGET] **판정 불가** — 자격증명이 없다 "
                  "(GX_API · GX_ROUTE_USER · GX_ROUTE_PASSWORD)")
            return EXIT_UNDECIDABLE
        from verify_route_alive import login              # noqa: PLC0415

        token = login(api, user, password)
        if not token:
            print(f"[PERF-BUDGET] **판정 불가** — 로그인 실패. {api} 가 서 있는가 "
                  f"(동시 접속 1개다)")
            return EXIT_UNDECIDABLE
        header = server_header(api, token)
        mode = MODE_ACCEPTANCE if args.acceptance else mode_for(header)
        print(f"[PERF-BUDGET] [입력] {api} · 면 {len(FACES)}종 · 동시 {args.concurrency} · "
              f"{args.rounds}라운드 (워밍업 {WARMUP_ROUNDS}라운드 버림) · **호출마다 ?bust=**")
        print(f"[PERF-BUDGET] [모드] {mode} ← Server: {header!r}"
              + ("  (--acceptance 로 손수 켰다)" if args.acceptance else "  (저절로 골랐다)"))
        latest = measure(api, token, concurrency=args.concurrency,
                         rounds=args.rounds, repeat=args.repeat)
        doc["latest"] = {
            "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "api": api,
            # ★ **환경 없는 성능 수치는 착시 ⑤다.** 한 벌만 둔다 — PERF-03 의 것을
            #   그대로 쓴다 (D-369).
            "environment": _environment(),
            "co_resident": _co_resident(),
            "server_header": header,
            "mode": mode,
            "server": ("runserver (개발 서버) — 합격선은 gunicorn+nginx 에서 다시 잰다"
                       if mode == MODE_BASELINE else
                       "runserver 가 아니다 — **합격선 모드**로 판정한다"),
            "concurrency": args.concurrency,
            "rounds": args.rounds,
            "repeat": args.repeat,
            "faces": latest,
        }
        # ── 기준선 — **PERF-01 이 남긴 수가 먼저다** ──────────────────────
        #   자기 측정을 자기 기준선으로 삼으면 회귀 감시는 언제나 초록이고,
        #   그 초록은 아무것도 감시하지 않는다. PERF-01 에 없는 면만 이번 수로 채운다.
        if args.set_baseline or "baseline" not in doc:
            from_perf01 = baseline_from_perf01()
            faces_base: dict = {}
            for key in FACES:
                if key in from_perf01:
                    faces_base[key] = from_perf01[key]
                else:
                    faces_base[key] = {
                        "p95_ms": latest[key]["p95_ms"],
                        "concurrency": args.concurrency,
                        "source": "이번 측정 — PERF-01 에 이 면이 없다(첫 수)",
                    }
            doc["baseline"] = {
                "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "server": "runserver (개발 서버)",
                "note": ("면별 기준선의 출처는 각 항목의 `source` 다. PERF-01 에서 온 "
                         "수는 그 파일이 잰 동시성의 수이고, 동시성이 다르면 이 게이트는 "
                         "회귀를 **회색**으로 낸다 — 다른 것 둘을 견주지 않기 위해서다."),
                "faces": faces_base,
            }
            for key, val in faces_base.items():
                print(f"[PERF-BUDGET] 기준선 {key:6} p95 {val['p95_ms']:7.1f}ms "
                      f"(동시 {val['concurrency']}) ← {val['source']}")
        doc["budget_table"] = {k: {"title": f.title, "budget_ms": f.budget_ms,
                                   "source": f.source, "calls": list(f.calls)}
                               for k, f in FACES.items()}
        doc["regression_tolerance"] = REGRESSION_TOLERANCE
        doc["error_budget"] = ERROR_BUDGET
        # ★ **한 벌로 판정하지 마라** (세종 P-53 · 턴 D 가 배운 것). 같은 설정이
        #   턴 D 에 8건을 내고 턴 E 에 3건을 냈다 — 502 건수는 그 순간의 기계
        #   상태(loadavg)가 좌우한다. 그래서 **매 측정의 오류율을 쌓아 둔다.**
        #   판정은 여전히 이번 벌로 하되, 이력이 예산을 걸치면 아래에서 경고한다.
        _n = sum(int(f.get("n") or 0) for f in latest.values())
        _five = sum(_split_errors(f)[0] for f in latest.values())
        doc.setdefault("availability_history", []).append({
            "measured_at": doc["latest"]["measured_at"],
            "n": _n, "errors_5xx": _five,
            "rate": round(_five / _n, 5) if _n else None,
            "loadavg": (doc["latest"].get("co_resident") or {}).get("loadavg"),
            "mode": mode, "rounds": args.rounds, "repeat": args.repeat,
            "concurrency": args.concurrency,
        })
        doc["availability_history"] = doc["availability_history"][-10:]
        doc["error_budget_source"] = ("SLA 가용성 99.9% 의 월 단위 환산 — 세종 판정 "
                                      "P-53 · LAW-05 SLA 초안. 이 게이트가 정한 수가 "
                                      "아니라 옮겨 적은 수다")
        doc["caveat"] = BASELINE_CAVEAT
        doc["mode"] = mode
        # `pending_acceptance` 는 판정을 돌려야 나온다 — 아래에서 채우고 다시 쓴다.
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        print(f"[PERF-BUDGET] 기록 → {doc_path}")
        wrote_evidence = True
    else:
        wrote_evidence = False

    patterns = bypass_patterns()
    rows: list = []
    for key, face in FACES.items():
        rows.append(judge_cache_frame(key, face, patterns))

    latest_faces = (doc.get("latest") or {}).get("faces") or {}
    base_faces = (doc.get("baseline") or {}).get("faces") or {}
    if not latest_faces:
        print(f"[PERF-BUDGET] 증거가 없다: {doc_path} — **회색이지 초록이 아니다.** "
              f"컨테이너 안에서 `--measure` 로 잰다 (D-301)")
    # ★ 모드는 **증거에 적힌 서버**가 정한다 — 호스트에서 증거만 읽고 판정할 때도
    #   같은 모드가 나와야 한다. `--acceptance` 는 손수 켜는 곁길이다 (D-286).
    mode = (MODE_ACCEPTANCE if args.acceptance
            else (doc.get("latest") or {}).get("mode")
            or mode_for((doc.get("latest") or {}).get("server_header")))
    for key, face in FACES.items():
        rows.extend(judge_face(key, face, latest_faces.get(key), base_faces.get(key),
                               mode=mode))
    # ★ **오류율은 자기 칸에서 판정한다** (세종 P-53). 응답시간 칸이 초록이어도
    #   이 칸이 빨가면 종료 코드는 빨강이다 — 갈라 적는 것이지 면제가 아니다.
    rows.extend(judge_availability(latest_faces))

    mark = {PASS: "  ", FAIL: "X ", GRAY: "? ", OVER: "! "}
    for (name, verdict, why) in rows:
        print(f"[PERF-BUDGET] {mark[verdict]}{name:52} {why}")

    # ── 기준선 초과는 **이름으로** 남긴다. 면제로 굳지 않게 하는 못이다 ──
    pending = [{"face": key, "title": face.title, "budget_ms": face.budget_ms,
                "p95_ms": (latest_faces.get(key) or {}).get("p95_ms"),
                "p95_min": (latest_faces.get(key) or {}).get("p95_min"),
                "p95_max": (latest_faces.get(key) or {}).get("p95_max"),
                "why": "기준선(runserver)에서 예산을 넘었다 — OPS-13 뒤 "
                       "gunicorn+nginx 에서 다시 재야 하고, 그때는 빨강이다"}
               for key, face in FACES.items()
               if any(v == OVER and n.startswith(f"{key} ") for (n, v, _w) in rows)]

    if wrote_evidence:
        doc["pending_acceptance"] = pending
        doc_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    rc = exit_code(rows)
    # ★ 단서는 **기준선 모드일 때만** 참이다. 합격선(nginx·gunicorn)에서 잰 수에
    #   「이 수는 runserver 로 잰 기준선이다」를 붙이면 그 줄이 곧 거짓이 되고,
    #   거짓 단서는 다음 사람이 진짜 단서까지 안 읽게 만든다.
    if mode == MODE_BASELINE:
        print("[PERF-BUDGET] " + BASELINE_CAVEAT)
    else:
        print("[PERF-BUDGET] ★ 이 수는 **합격선 모드**로 잰 것이다 — 대상이 "
              f"runserver 가 아니다(Server: {(doc.get('latest') or {}).get('server_header')!r}). "
              "절대 예산도 빨강이고, 위 단서(기준선)는 이 수에 붙지 않는다")
    if mode == MODE_BASELINE:
        co = ((doc.get("latest") or {}).get("co_resident") or {})
        #: 껍데기(`sh -c … runserver …`)는 세지 않는다 — 서버 하나가 둘로 세어지면
        #: 잡음의 출처를 과장하게 되고, 과장된 수는 다음 사람이 안 믿는다.
        procs = [c for c in (co.get("runserver_processes") or [])
                 if "manage.py runserver" in c and not c.lstrip().startswith("sh ")]
        if procs:
            print(f"[PERF-BUDGET] [환경] 같은 컨테이너에 runserver {len(procs)}대가 서 "
                  f"있다 — **내 p95 는 남의 부하를 함께 잰다**(loadavg "
                  f"{co.get('loadavg')}). 잡음의 출처가 여기다")
    hist = [h for h in (doc.get("availability_history") or [])
            if h.get("rate") is not None]
    if len(hist) >= 2:
        rates = [h["rate"] for h in hist[-5:]]
        if min(rates) <= ERROR_BUDGET < max(rates):
            # ★ **이 자리는 색이 없다 — 사실만 적는다.** 판정을 뒤집지 않는 이유는
            #   하나다: 뒤집을 규칙을 여기서 지어내면 그것은 게이트가 아니라 내 의견이
            #   된다. 세종에게 필요한 것은 「몇 벌을 재고 어떻게 접을 것인가」라는
            #   **판정**이고, 이 줄은 그 판정을 청하는 근거다.
            print(f"[PERF-BUDGET] ★★ **한 벌로 판정하지 마라** — 최근 "
                  f"{len(rates)}벌의 5xx 비율이 "
                  + " · ".join(f"{r:.3%}" for r in rates)
                  + f" 로 예산 {ERROR_BUDGET:.1%} 를 **걸친다.** 어느 벌을 쓰느냐로 "
                    f"색이 갈린다 — 이 게이트의 색은 지금 코드가 아니라 "
                    f"**그 순간의 기계 상태**를 함께 담고 있다 "
                  + " · ".join(f"loadavg {h.get('loadavg')}" for h in hist[-5:]))
    if pending:
        names = " · ".join(f"{q['face']}({q['p95_ms']:.0f}ms>{q['budget_ms']:.0f}ms)"
                           for q in pending)
        print(f"[PERF-BUDGET] ★★ **이 초록은 합격선이 아니다** — 넘은 자리 "
              f"{len(pending)}곳: {names}. 이 자리들은 OPS-13 뒤 gunicorn+nginx "
              f"에서 다시 재야 하고, **그때는 빨강이다.** "
              f"budget.json 의 `pending_acceptance` 에 이름으로 남겼다")
    if (doc.get("latest") or {}).get("measured_at"):
        print(f"[PERF-BUDGET] 잰 때 {doc['latest']['measured_at']} · "
              f"기준선 {(doc.get('baseline') or {}).get('measured_at')}")
    print("[PERF-BUDGET] " + {
        EXIT_OK: (f"통과 ({mode}) — 회귀 갈래가 전부 문턱 안이다"
                  + (f" · 다만 예산을 넘은 자리 {len(pending)}곳이 "
                     f"`pending_acceptance` 에 남아 있다" if pending else
                     " · 예산을 넘은 자리도 없다")),
        EXIT_FAIL: ("실패 — 위의 X 가 그 자리다. **X 가 어느 칸인지 보라**(세종 P-53): "
                    "「· 예산 …ms」는 **응답시간**(PERF-04) · 「· 회귀 +20%」는 회귀 · "
                    "「[전체] 가용성」은 **오류율**(OPS-13a 앞단·워커)이다. 셋은 다른 "
                    "고장이고 고칠 자리도 다르다"),
        EXIT_UNDECIDABLE: "**회색(exit 2)** — 못 쟀다. 위의 ? 가 그 자리다. "
                          "회색은 초록이 아니다 (D-301)",
    }[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
