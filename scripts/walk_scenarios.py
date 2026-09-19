#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**시나리오 걷기 W1~W6** — 사람처럼 지나간다 (2026-09-05 턴 C · W5·W6 는 2026-09-18 턴 V · 차선 Q).

무엇이 다른가 — **부하기와 촬영기 사이의 빈자리**
------------------------------------------------
    `perf_load.py`      문을 **두드린다**. API 가 몇 ms 인가. 화면은 안 연다.
    `capture_screens.py` 화면을 **찍는다**. 한 장 한 장이 떴는지 단언한다. 걷지는 않는다.
    이 도구            화면을 **걷는다**. 목록에서 필터를 누르고, 한 건을 열고,
                       그 사이에 **몇 번 눌렀고 몇 초 걸렸고 콘솔이 몇 번 울었는지** 센다.

★★ **걷기 아이디는 `W` 다** [P-181 · 2026-09-18 턴 V]. 종전에는 걷기 표의 열쇠가 `S1·S2·S3` 이라
  `perf_load.SCENARIOS` 의 열쇠와 **같은 이름 공간**을 썼다. 그래서 턴 V(파 3 턴 1)의 V 가
  걷기 S4·S5 를 걸려 했을 때 `S4` 는 이미 부하용 「섞기」의 임자였고 `S5` 는 어디에도 없었다 —
  V 는 **이름을 지어내지 않고 안 걸었다**. 옳다. 이제 두 이름 공간을 가른다:

      W1·W2·W3·W4   `perf_load.SCENARIOS` 의 S1·S2·S3·S4 에서 **이름을 빌린다**(BORROWED_FROM_PERF)
      W5·W6         **걷기 전용** — 부하 표에 대응하는 것이 없다(WALK_ONLY_NAMES)

  ★ 이름을 새로 짓지 않는다는 규율은 그대로다 — 빌린 넷의 **이름**은 여전히 `perf_load` 가 답한다.
    바뀐 것은 **열쇠**뿐이고, 그래서 「S4」를 물으면 부하 표 하나만 답한다(D-212).
  ★ 걷기 전용 둘의 이름은 세종 P-181 이 주었다(이 도구가 지은 것이 아니다).

★ **폭은 걸음마다 다르다** [P-181]. 종전에는 전부 390px 였다 — 현장(U1·U3)은 늘 모바일이므로
  그것이 맞았다. 그러나 **관제팀장(U2)과 시스템 관리자(U5)는 1440px 자리**다. 한 폭으로만 걸으면
  그 사람들의 화면에서 누를 수 없는 자리를 영영 못 본다. 그래서 `WALK_META` 가 걸음마다
  폭과 **누가 걷는가**를 적는다.
  ⚠ 사람이 바뀌면 **다시 로그인한다** — 이 환경은 계정당 세션 1개이고 IP 당 로그인 5회/분이다.
    그래서 사람이 바뀔 때마다 기다린다(`GAP_SECONDS`). 기다림을 뺀 시간이 표에 적히는 수다.

⚠ **클릭 수를 줄이는 것이 목적이 아니다.** 지금 몇 번인지 **재는 것**이 목적이다.
  첫 수는 기준선이지 합격선이 아니다 — PERF-04 에서 배운 그대로다(세종 P-34).
  그래서 클릭 수와 경과 시간은 **표에 적고 판정하지 않는다.** 판정하는 것은 셋뿐이다:
  ① 걸어지는가(각 걸음의 단언) ② 콘솔이 우는가 ③ 세션을 닫았는가.

⚠ **로그인 세션을 물고 있지 마라.** 이 환경은 **동시 접속 1개**다 — 다른 차선이
  화면을 만지는 중에 이 도구가 세션을 쥐고 있으면 그쪽이 튕긴다. 끝나면
  `POST /api/v1/auth/logout` 으로 닫는다. 닫지 못하면 그 사실을 **빨강으로** 적는다.

    docker exec -i gx-shell python /repo/scripts/walk_scenarios.py \
        --user gxprobe_e2e --password ****
    python scripts/walk_scenarios.py --self-test     # 판정 규칙만 (브라우저 없이)

종료 코드: 0 걸었고 통과 · 1 걸었고 실패 · 2 **못 걸었다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[WALK]"
ROOT = Path(__file__).resolve().parent.parent

#: **모바일 폭.** iPhone 12 급의 논리 해상도다. 이 수를 키우면 이 도구가 재는 것이
#: 달라진다 — 데스크톱에서 누를 수 있는 자리는 모바일의 증거가 아니다.
VIEWPORT = {"width": 390, "height": 844}
MOBILE = VIEWPORT
#: [P-181 · 턴 V] 관제팀장(U2)·시스템 관리자(U5)의 자리. 그 사람들은 현장이 아니라 책상이다.
DESKTOP = {"width": 1440, "height": 900}
#: 사람이 바뀔 때 기다리는 시간 — IP 당 로그인 5회/분 · 계정당 세션 1개 (P-157).
GAP_SECONDS = 61

# ═══════════════════════════════════════════════════════════════════════════
# P-154 잔여 · P-159 ③ — **대장은 줄지 않는다**: `walk.json` 을 덮어쓰지 않고 합쳐 쓴다 (턴 T · 차선 Q)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 종전에는 `UX-WALK/walk.json` 을 **이번 실행분 하나로 덮어썼다** — 같은 파일이 직전 걷기 하나만
#:   말했고, 지난 회는 손으로 이름을 바꿔 둔 사본(`walk_20260906_TG.json` …)에만 남았다. 그것은
#:   생성기가 대장을 이번 실행분만 남기고 다시 쓰는 턴 R 의 모양과 같다(D-473).
#:   이제 `capture_screens._rewrite_index` 와 **같은 방식**이다:
#:     · 이번 실행분은 **그대로** `UX-WALK/runs/walk_<stamp>.json` 에 (무엇이 이번 것인지 못 가리지 않게)
#:     · 대장 `walk.json` 은 `{"runs": [옛 것 …, 이번 것]}` — `ledger_merge.merge_records` 로 합치고
#:       `assert_not_shrunk` 로 **줄면 멈춘다**(예외 · 경고 아님).
#:   HEAD 의 `walk.json` 은 `runs` 없이 실행 하나가 통째다 — 그 판은 **실행 1건**으로 읽는다(옛 판을 버리지 않는다).
#: ★ 열쇠는 `when`(걷기 시각)이다 — 같은 시각을 다시 쓰면 그 판만 새 것이 되고, 다른 시각은 전부 남는다.
#:   기록 전체를 열쇠로 쓰면 같은 걷기를 두 번 저장했을 때 두 줄이 되므로, 여기서만 `when` 으로 좁힌다
#:   (걷기 하나는 시각 하나다 — 화면 대장의 「같은 라우트 다른 사람」 함정이 여기엔 없다).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger_merge import assert_not_shrunk, merge_records  # noqa: E402


def _by_when(r) -> str:
    return str(r.get("when", "")) if isinstance(r, dict) else str(r)


def ledger_runs(doc) -> list:
    """대장 문서 → 실행 목록. `runs` 가 있으면 그것, 없으면(HEAD 판) 문서 하나가 실행 하나다. 빈 문서는 0건."""
    if not isinstance(doc, dict) or not doc:
        return []
    if isinstance(doc.get("runs"), list):
        return list(doc["runs"])
    return [doc]


def merge_walk_ledger(old_doc, fresh: dict) -> dict:
    """옛 대장 + 이번 실행 → 새 대장. **줄면 예외.** 순수 함수 — 파일을 만지지 않는다(자기시험이 여기를 두드린다)."""
    old_runs = ledger_runs(old_doc)
    runs = merge_records(old_runs, [fresh], key=_by_when)
    assert_not_shrunk("walk.json runs", len(old_runs), len(runs))
    return {"ledger": "scripts/walk_scenarios.py", "latest_when": fresh.get("when"),
            "runs": runs}


def _read_json(p: Path):
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        #: 깨진 대장은 **합치지 못하면 쓰지 않는다** — 빈 것으로 읽어 덮어쓰면 그것이 곧 삭제다.
        raise RuntimeError(f"대장 {p} 를 읽지 못했다({type(exc).__name__}) — 합치지 못하면 쓰지 않는다") from exc


# ═══════════════════════════════════════════════════════════════════════════
# 이름 — **빌린 것**과 **걷기 전용**을 가른다 [P-181 · 2026-09-18 턴 V · 세종 P-181]
# ═══════════════════════════════════════════════════════════════════════════
#: 걷기 아이디 → 부하 표(`perf_load.SCENARIOS`)의 아이디. **이름은 저쪽이 답한다.**
BORROWED_FROM_PERF = {"W1": "S1", "W2": "S2", "W3": "S3", "W4": "S4"}

#: 걷기 전용 — 부하 표에 대응하는 것이 **없다**. 이름은 세종 P-181 이 주었다.
#: ⚠ 여기 이름을 `perf_load` 에 밀어 넣지 않는다: 저 표는 **동시 호출**의 표이고
#:   이 둘은 사람 하나의 걸음이다. 한 표에 두면 「S5 를 몇 ms 로 잡았나」에 답할 수 없다.
WALK_ONLY_NAMES = {
    "W5": "팀장 아침 인수 — 관제팀장이 교대에 들어와 밤사이를 인수한다 (U2 · 1440px)",
    "W6": "관리자 설치 다음 날 — 설치가 끝난 다음 날 관리자가 자리를 세운다 (U5 · 1440px)",
}


def _scenario_names() -> dict:
    """걷기 아이디마다 이름을 낸다 — 빌린 넷은 **`perf_load` 에서 가져온다.**

    ★ 못 가져오면 **판정 불가**다. 이름을 이 파일에 베껴 두면 그날부터 두 표가 되고,
      두 표는 반드시 어긋난다 (D-212 · D-369).
    ★ [P-181] 그리고 **이름 공간이 겹치면 멈춘다** — 걷기 전용 아이디가 부하 표에도
      있으면 「S5」가 둘을 가리키게 되고, 그 순간 다음 사람은 어느 표를 봐야 하는지 모른다.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from perf_load import SCENARIOS

    clash = sorted(set(WALK_ONLY_NAMES) & set(SCENARIOS))
    if clash:
        raise RuntimeError(
            "걷기 전용 이름이 perf_load.SCENARIOS 와 부딪힌다: %s — "
            "한 이름이 두 표를 가리키면 이름이 아니다 (D-212)" % clash)
    out = {}
    for wk, sk in BORROWED_FROM_PERF.items():
        if sk not in SCENARIOS:
            raise RuntimeError(
                "부하 표에 %s 가 없다 — %s 가 빌릴 이름이 사라졌다. "
                "여기서 새로 짓지 않는다" % (sk, wk))
        out[wk] = "%s (← perf_load.%s)" % (SCENARIOS[sk]["name"], sk)
    out.update(WALK_ONLY_NAMES)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 걸음 — **화면 경로만 여기 있다.** 이름은 perf_load 가 답한다
# ═══════════════════════════════════════════════════════════════════════════
#
# 걸음 하나는 셋 중 하나다:
#   {"go": 경로}              그 주소로 간다 (클릭이 아니다 — 주소창은 사람의 손이 아니다)
#   {"click": (역할, 이름)}    그 버튼·링크를 **누른다** (클릭 1회로 센다)
#   {"click_row": n}          표의 n번째 줄을 누른다 — 목록에서 한 건을 여는 손짓
# 그리고 걸음마다 `see` 가 있다: **그 걸음이 끝난 화면에만 있는 글자**.
# 공통 글자로 단언하면 안 움직여도 초록이 된다 — `capture_screens` 가 프리셋 넷에서
# 배운 함정이 그대로 여기에도 있다.
#
# ★ `see` 는 전부 **실제로 390px 에서 열어 본문을 읽고** 골랐다 [실측 2026-09-05 TC].
WALKS: dict[str, list] = {
    "W1": [
        {"go": "/dsm/events", "see": "이벤트 목록"},
        # 관제요원이 목록에서 가장 먼저 하는 일: **아직 아무도 안 본 것**만 남긴다.
        # ⚠ [실측 2026-09-05 턴 F] 이 `see` 는 **낡아 있었다**: 「미처리 — 대응 축이
        #   아직 「발생」인 것」. 그 문구는 UX-20 이 화면 밖으로 뺀 절 언어이고,
        #   이 걸음표는 **9-04 번들을 보고 적힌 것**이다. 번들을 새로 배치하자마자
        #   이 줄이 빨강을 냈고, 그 빨강은 화면의 결함이 아니라 **기대가 낡은 것**이었다.
        #   → 낡은 입력이 초록을 만드는 것과 같은 자리다(P-59). 정본은 화면 상수다:
        #     `frontend/src/features/dsm/pages/EventList.tsx` 의 프리셋 `headline`.
        {"click": ("button", "미처리"),
         "see": "미처리 — 아직 아무도 손대지 않은 것"},
        # 그리고 한 건을 연다. 여기까지가 「목록」 시나리오의 끝이다.
        {"click_row": 1, "see": "이벤트 상세"},
    ],
    "W2": [
        {"go": "/dsm/dashboard", "see": "관제 대시보드"},
        # 대시보드의 최근 이벤트에서 **전체 목록으로 건너가는 자리**. 이 한 번이
        # 안 되면 대시보드는 막다른 화면이 된다.
        #
        # ⚠ [실측 2026-09-05 TC] 이 자리는 **`href` 없는 `<a>`** 다. 그래서 접근성
        #   나무에서 `link` 가 아니고(이 화면의 link 는 **0개**다), 키보드 초점도
        #   새 탭 열기도 안 된다. 손가락으로는 눌리므로 **글자로** 누른다 —
        #   `get_by_role("link")` 로 걸으면 「없다」가 나오는데, 그 「없다」는
        #   자리가 없다는 뜻이 아니라 **역할이 없다**는 뜻이다. 둘을 섞지 않는다.
        {"click_text": "전체 목록", "see": "이벤트 목록"},
    ],
    "W3": [
        # ⚠ 같은 낡음 [실측 2026-09-05 턴 F] — 화면 머리는 「지금 처리할 것 — 가장
        #   급한 하나」다(`features/dsm/pages/FocusQueue.tsx` 의 `HEADLINE`).
        #   「지금 가장 급한 하나」는 어느 번들에도 없는 글자였다.
        {"go": "/dsm/queue", "see": "지금 처리할 것 — 가장 급한 하나"},
        # 단일 초점에서 **가장 급한 하나를 여는** 단추. 이것이 이 화면의 존재 이유다.
        {"click": ("button", "상세 열기"), "see": "이벤트 상세"},
    ],

    # ══════════════════════════════════════════════════════════════════════
    # W5 · W6 — **걷기 전용** [P-181 · 2026-09-18 턴 V · 차선 Q]
    #
    # ⚠⚠ **이 두 걸음표의 `see` 는 화면을 열어 본 것이 아니라 화면 상수에서 적었다.**
    #    차선은 브라우저를 재지 않는다 — 그래서 W1~W3 처럼 「390px 에서 열어 본문을
    #    읽고 골랐다」고 적을 수 없다. 대신 턴 F 가 가르쳐 준 그 자리(정본은 화면 상수다)로
    #    갔다: 아래 글자는 전부 **소스의 상수**이고 어디서 왔는지 줄마다 적었다
    #    [읽은 것 2026-09-18 · 차선 Q].
    #    → **첫 걷기가 빨강을 내면 그것이 화면의 결함이라고 먼저 믿지 마라.** 기대가
    #      낡았을 수 있다(P-59 의 그 자리). 첫 수는 기준선이지 합격선이 아니다.
    # ══════════════════════════════════════════════════════════════════════
    "W5": [
        # ① 밤사이를 먼저 본다 — 목록에 들어가 12시간 요약을 연다.
        #    「지난 12시간 보기」는 이 화면의 요약 단추다(`EventList.tsx` · U2#1 정본 문구).
        {"go": "/dsm/events", "see": "이벤트 목록"},
        {"click": ("button", "지난 12시간 보기"), "see": "지난 12시간 보기"},
        # ② 그 다음이 **미처리**다. 프리셋 머리글은 W1 이 쓰는 그 글자와 같다
        #    (`EventList.tsx` 프리셋 `headline` — 두 벌로 적지 않는다).
        {"go": "/dsm/events?preset=unhandled",
         "see": "미처리 — 아직 아무도 손대지 않은 것"},
        # ③ 사람을 본다 — 「요원별 현황」(`copy.ts::HEADLINE_COPY.teamStatus` · `TeamStatus.tsx`).
        {"go": "/dsm/team-status", "see": "요원별 현황"},
        # ④ 인수의 끝은 **종이**다 — 보고서 화면의 첫 카드 이름(`Reports.tsx` `FORMS[0].label`).
        {"go": "/dsm/reports", "see": "사건 보고서"},
    ],
    "W6": [
        # ① 카메라를 넣는다 — `CameraImport` 화면의 제목(U5#4 정본 문구와 같은 글자).
        {"go": "/dsm/cameras/import", "see": "카메라 일괄 등록"},
        # ② 주소를 채운다 — 「이 한 대 채우기」(`CameraAddress.tsx:297` · GX-COPY 턴 U 추가).
        {"go": "/dsm/cameras/address", "see": "이 한 대 채우기"},
        # ③ 사람을 만든다 — `copy.ts::HEADLINE_COPY.people` (`People.tsx` `HEADLINE`).
        {"go": "/dsm/people", "see": "사람·역할 — 계정 만들기 · 비활성화"},
        # ④ 알림이 누구에게 가는지 정한다 — `NotifySettings.tsx:56` `HEADLINE`.
        {"go": "/dsm/notify", "see": "알림 받는 사람·채널"},
        # ⑤ 마지막은 **자리를 세우는 칸**이다 — `SystemSettings.tsx:406` 카드 제목.
        #    ⚠ 단추(「재시작을 요청합니다」)는 **누르지 않는다**: 이 도구는 걸음을 재는 것이고,
        #      요청 행을 남기면 걷기가 제품의 표를 늘린다(되돌리는 문이 없다).
        {"go": "/dsm/system", "see": "재시작 요청 — 기록만 남습니다"},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# 걸음마다 — **누가 · 어느 폭으로** 걷는가 [P-181]
# ═══════════════════════════════════════════════════════════════════════════
#: `who` 는 자격의 **이름**이지 계정이 아니다. 실제 계정은 부르는 쪽이 준다
#: (이 도구는 계정을 만들지도 비밀번호를 소스에 두지도 않는다).
WALK_META: dict[str, dict] = {
    "W1": {"viewport": MOBILE, "who": "route", "why": "현장은 늘 모바일이다"},
    "W2": {"viewport": MOBILE, "who": "route", "why": "같음"},
    "W3": {"viewport": MOBILE, "who": "route", "why": "같음"},
    "W5": {"viewport": DESKTOP, "who": "u2",
           "why": "관제팀장의 자리는 관제실 책상이다 — 1440px"},
    "W6": {"viewport": DESKTOP, "who": "u5",
           "why": "시스템 관리자의 자리도 책상이다 — 1440px"},
}

#: **알려진 잡음.** 목록으로 두는 이유는 `capture_screens.KNOWN_BLANK` 와 같다 —
#: 못 고치는 것을 목록에서 지우면 「없다」와 「알고 있으나 남의 자리다」가 같아진다(D-264).
#:
#: ⚠ 이 목록은 **면제가 아니라 분류**다. 여기 걸리는 줄은 「알려진 잡음」으로 세고,
#:   **여기 안 걸리는 줄은 한 건이라도 빨강**이다. 반대로 만들면(=아는 것만 빨강)
#:   내일 새로 나는 오류가 조용히 통과한다.
#: ⚠ [실측 2026-09-05 TC] 넷 다 §0.4 금지구역(orders·partner)의 웹소켓이고, 이 환경에
#:   그 서버가 없어 404 로 떨어진 뒤 **재접속을 반복한다** — 그래서 건수가 걸은 시간에
#:   비례한다. 화면의 결함이 아니라 환경의 사실이다. 고치는 것은 이 차선의 몫이 아니다.
KNOWN_CONSOLE_NOISE = (
    ("/ws/partner-callbacks/", "§0.4 partner 웹소켓 — 이 환경에 서버가 없다(404) · 재접속 루프"),
    ("Partner callback WebSocket error", "위 404 가 남기는 두 번째 줄"),
    ("/ws/orders/notifications/", "§0.4 orders 웹소켓 — 같음"),
    ("New order notification WebSocket error", "위 404 가 남기는 두 번째 줄"),
    # ── 아래 셋은 **URL 이 붙기 전에는 분류할 수 없던 것들**이다 [실측 2026-09-05 턴 F].
    #    브라우저가 자원 적재 실패를 적는 줄에는 URL 이 없다 — 「Failed to load
    #    resource: … 404」 뿐이다. 그 줄만 보고 분류하려면 **모든 404 를 한꺼번에**
    #    면제해야 하고, 그것은 분류가 아니라 눈감기다. 그래서 `walk()` 가 브라우저의
    #    위치(URL)를 그 줄에 붙이고, 여기서 **자리로** 가른다.
    ("/Inter/Inter-VariableFont", "인수 자산 CSS 가 안 실린 글꼴을 부른다(404) — "
                                  "`url(../Inter/…ttf)`. 우리 CSS 는 `/fonts/Inter-Variable.ttf` "
                                  "를 부르고 그것은 200이다. 화면은 대체 글꼴로 그려진다"),
    ("/api/user-groups/gen-schema", "dj-core 사용자그룹 스키마(422) — §0.4 자산이고 "
                                    "상용점검 §3.1-5 에 이미 등재된 결함이다. "
                                    "**분류는 면제가 아니다** — 등재된 자리에서 고친다"),
    ("/ws/surveillance/profiles/", "감시 프로필 웹소켓 — `runserver` 는 WSGI 라 이 환경에 "
                                   "웹소켓 자체가 없다(404). 위 둘과 같은 사유 · 배치의 사실이 아니다"),
)


def classify_console(errors: dict) -> tuple:
    """콘솔 줄을 **알려진 잡음**과 **분류되지 않은 것**으로 가른다."""
    known, unknown = {}, {}
    for key, lines in (errors or {}).items():
        for line in lines:
            hit = next((why for tok, why in KNOWN_CONSOLE_NOISE if tok in line), None)
            bucket = known if hit else unknown
            bucket.setdefault(key, []).append(line)
    return known, unknown


#: W4(← S4 섞기)는 걷지 않는다 — **여러 자리를 동시에 두드리는 부하 시나리오**이고,
#: 사람의 손 하나로는 동시에 못 누른다. 이름을 빌린 표에 없는 것을 지어내지 않는다.
#: ⚠ **목록에서 지우지 않는다**(면제가 아니라 분류다 · D-264): 지우면 「걷지 않기로 한 것」과
#:   「잊은 것」이 같아진다. 그래서 `WALKS` 에는 없고 여기에는 있다.
NOT_WALKED = {"W4": "부하용 혼합 시나리오(← perf_load.S4) — "
                    "동시 호출이라 사람의 걸음으로 환산되지 않는다"}

#: 판정 줄의 이름. **수를 손으로 적지 않는다** — 걷기 표가 늘면 이 이름도 같이 는다.
WALKED_LABEL = "걷기 %d 시나리오를 다 걸었다" % len(WALKS)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(result: dict) -> list:
    """`(이름, 통과, 사유)`. **클릭 수와 시간은 판정하지 않는다** — 기준선이다.

    ★ `None` 은 **못 쟀다**이지 거짓이 아니다 (D-301).
    """
    out: list = []
    walks = result.get("walks")
    #: [P-181] 판정 이름에 **수를 손으로 적지 않는다** — 걷기 표가 늘면 이름도 같이 는다.
    #: 종전 이름은 「세 시나리오를 걸었다」였고, 표가 여섯이 된 날 그 이름이 거짓말을 한다.
    label = WALKED_LABEL
    #: 자격이 없어 **시도조차 못 한** 걷기. 「멈췄다」와 가른다 — 원인이 다르다.
    skipped = result.get("not_attempted") or {}

    if not walks:
        out.append((label, False, "**못 걸었다** — 결과가 없다"
                    + (f" · 자격이 없어 못 간 것: {skipped}" if skipped else "")))
    else:
        done = [k for k, w in walks.items() if w.get("completed")]
        ok = sorted(done) == sorted(WALKS)
        broke = {k: w.get("failed_at") for k, w in walks.items()
                 if not w.get("completed")}
        out.append((label, ok,
                    f"완주 {len(done)}/{len(WALKS)}"
                    + ("" if ok else
                       f" — 멈춘 자리: {broke}. **그 폭에서 누를 수 없는 자리**이거나 "
                       f"화면이 안 뜬 것이다"
                       + (f" · **자격이 없어 아예 못 간 것**: {skipped} "
                          f"(화면의 결함이 아니다 — 회색이고, 회색은 초록이 아니다)"
                          if skipped else ""))))

    errs = result.get("console_errors")
    if errs is None:
        out.append(("분류되지 않은 콘솔 오류 0건", False, "**못 쟀다**"))
    else:
        known, unknown = classify_console(errs)
        n_known = sum(len(v) for v in known.values())
        n_unknown = sum(len(v) for v in unknown.values())
        out.append(("분류되지 않은 콘솔 오류 0건", n_unknown == 0,
                    f"0건 (알려진 잡음 {n_known}건은 따로 센다)" if n_unknown == 0 else
                    f"{n_unknown}건 — {json.dumps(unknown, ensure_ascii=False)[:420]}"))

    closed = result.get("session_closed")
    if closed is None:
        out.append(("세션을 닫았다", False, "**못 쟀다** — 로그아웃을 부르지 못했다"))
    else:
        out.append(("세션을 닫았다", bool(closed),
                    "POST /api/v1/auth/logout 200" if closed else
                    "**세션이 열린 채다.** 이 환경은 동시 접속 1개다 — 물고 있으면 "
                    "다른 차선이 화면에서 튕긴다"))

    names = result.get("names_from_perf_load")
    out.append(("시나리오 이름을 빌려 왔다", bool(names),
                f"perf_load.SCENARIOS ← {names}" if names else
                "**이름을 못 가져왔다** — 여기서 새로 지으면 표가 둘이 된다 (D-212)"))
    return out


def self_test() -> int:
    """판정 규칙을 **브라우저 없이** 시험한다 (D-277 · D-350)."""
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    green = {
        "walks": {k: {"completed": True, "clicks": 1, "ms": 1000} for k in WALKS},
        "console_errors": {k: [] for k in WALKS},
        "session_closed": True,
        "names_from_perf_load": {"W1": "목록", "W2": "대시보드", "W3": "단일 초점"},
    }
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── **출생 표본** (D-310) — 이 도구가 없던 상태. 아무도 안 걸어 봤으므로
    #    걸음도 없고 수도 없다. 「0건 걸었다」가 초록이면 이 도구는 아무 일도 안 한다.
    if names(judge({"walks": {}, "console_errors": {}, "session_closed": True,
                    "names_from_perf_load": {}})).get(WALKED_LABEL):
        bad.append("**아무것도 안 걸었는데** 통과로 읽는다 — 0건은 통과가 아니다 (D-301)")

    # ── 음성 갈래 ──────────────────────────────────────────────────────────
    for key, value, expect_red in (
        ("walks", {**green["walks"], "W3": {"completed": False, "failed_at": 2}},
         WALKED_LABEL),
        ("console_errors", {"W1": ["TypeError: x is not a function"]},
         "분류되지 않은 콘솔 오류 0건"),
        ("session_closed", False, "세션을 닫았다"),
        ("names_from_perf_load", {}, "시나리오 이름을 빌려 왔다"),
    ):
        if names(judge(dict(green, **{key: value}))).get(expect_red):
            bad.append(f"{key}={str(value)[:40]!r} 인데 「{expect_red}」를 통과로 읽는다")

    # ── **못 쟀다 ≠ 거짓** ─────────────────────────────────────────────────
    # ★ **알려진 잡음만 있는 표본은 초록**이어야 한다 — 아니면 목록이 목록이 아니다.
    noise = dict(green, console_errors={"W1": [
        "console.error: WebSocket connection to 'ws://x/ws/partner-callbacks/' failed"]})
    if not names(judge(noise)).get("분류되지 않은 콘솔 오류 0건"):
        bad.append("알려진 잡음만 있는 표본을 빨강으로 읽는다 — 분류가 분류가 아니다")
    # ★ 그리고 **잡음에 섞인 새 오류는 빨강**이어야 한다. 이것이 뒤집히면 목록이 면제가 된다.
    mixed = dict(green, console_errors={"W1": [
        "console.error: WebSocket connection to 'ws://x/ws/orders/notifications/' failed",
        "console.error: 새로 난 오류"]})
    if names(judge(mixed)).get("분류되지 않은 콘솔 오류 0건"):
        bad.append("**잡음에 섞인 새 오류**를 통과로 읽는다 — 목록이 면제가 됐다")

    # ── ★ **URL 이 붙어야 분류된다** (턴 F) ────────────────────────────────
    #   자원 적재 실패 줄은 URL 없이는 남의 자리와 우리 고장을 못 가른다.
    #   ㉠ URL 이 붙으면 자리로 분류된다  ㉡ **URL 이 없으면 분류되지 않는다**(빨강).
    #   ㉡ 이 뒤집히면 이 목록은 「모든 404 면제」가 된다 — 그것은 분류가 아니다.
    res404 = "console.error: Failed to load resource: the server responded with a status of 404"
    with_url = dict(green, console_errors={"W1": [
        f"{res404} (File not found) ← http://localhost:3002/Inter/Inter-VariableFont_opsz,wght.ttf"]})
    if not names(judge(with_url)).get("분류되지 않은 콘솔 오류 0건"):
        bad.append("URL 이 붙은 **인수 자산 글꼴 404** 를 분류하지 못한다")
    if names(judge(dict(green, console_errors={"W1": [res404]}))).get(
            "분류되지 않은 콘솔 오류 0건"):
        bad.append("**URL 없는** 404 줄을 통과로 읽는다 — 그러면 모든 404 가 면제된다")

    for key, label in (("console_errors", "분류되지 않은 콘솔 오류 0건"),
                       ("session_closed", "세션을 닫았다")):
        hit = [r for r in judge(dict(green, **{key: None})) if r[0] == label][0]
        if hit[1] or "못 쟀다" not in hit[2]:
            bad.append(f"{key} 를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다")

    # ── 걸음표 자체를 시험한다 — 각 걸음에 **단언이 있는가** ───────────────
    for key, steps in WALKS.items():
        for i, step in enumerate(steps):
            if not step.get("see"):
                bad.append(f"{key} 의 {i+1}번째 걸음에 `see` 가 없다 — 단언 없는 걸음은 "
                           f"「눌렀다」만 남기고 「그래서 무엇이 떴는가」를 안 남긴다")

    # ── ★ [P-181 · 턴 V] **이름 공간이 갈려 있는가 · 걸음마다 임자가 있는가** ─────
    #   V 가 턴 V(파 3 턴 1)에 S4·S5 를 못 걸은 사유가 여기다 — `S4` 는 부하 표의 임자였고
    #   `S5` 는 어디에도 없었다. 그 자리를 규칙으로 못박는다.
    for key in WALKS:
        if key not in WALK_META:
            bad.append(f"{key} 에 `WALK_META` 가 없다 — **누가 어느 폭으로 걷는지**를 "
                       f"모르면 「그 폭에서 누를 수 없다」를 적을 수 없다")
        elif not WALK_META[key].get("viewport") or not WALK_META[key].get("who"):
            bad.append(f"{key} 의 `WALK_META` 에 폭이나 임자가 없다")
    for key in WALK_META:
        if key not in WALKS:
            bad.append(f"`WALK_META` 에 있는 {key} 가 걸음표에 없다 — 안 걷는 것은 "
                       f"`NOT_WALKED` 에 사유와 함께 둔다(지우면 「잊은 것」과 같아진다)")
    if set(NOT_WALKED) & set(WALKS):
        bad.append(f"안 걷기로 한 것이 걸음표에도 있다: {sorted(set(NOT_WALKED) & set(WALKS))}")
    try:
        got_names = _scenario_names()
    except Exception as exc:                                    # noqa: BLE001
        bad.append(f"이름을 못 가져왔다 — {type(exc).__name__}: {exc}")
        got_names = {}
    else:
        missing = sorted(set(WALKS) - set(got_names))
        if missing:
            bad.append(f"이름 없는 걷기: {missing} — 이름 없는 걸음은 표에 못 적는다")
        if set(WALK_ONLY_NAMES) & set(BORROWED_FROM_PERF):
            bad.append("걷기 전용 아이디가 **빌린 아이디**와 겹친다 — 한 열쇠가 둘을 가리킨다")
    #: ★ 음성 대조 — 이름 공간이 **겹치면 멈춘다**는 것을 실제로 확인한다.
    #:   이 규칙이 죽어 있으면 다음 사람이 `W5` 를 부하 표에 밀어 넣어도 아무도 안 막는다.
    _saved = dict(WALK_ONLY_NAMES)
    try:
        WALK_ONLY_NAMES.clear()
        WALK_ONLY_NAMES["S1"] = "부하 표와 부딪히는 이름 (시험용)"
        try:
            _scenario_names()
            bad.append("**부하 표와 부딪히는 이름**을 그냥 지나간다 — 이름이 이름이 아니게 된다")
        except RuntimeError:
            pass
    finally:
        WALK_ONLY_NAMES.clear()
        WALK_ONLY_NAMES.update(_saved)

    # ★ P-159 ③ — 대장 합치기 (파일 없이 · 순수 함수)
    head_style = {"when": "2026-09-05T14:51:34", "walks": {"S1": {}}}      # HEAD 판: runs 없이 실행 하나
    fresh = {"when": "2026-09-17T15:00:00", "walks": {"S1": {}}}
    m = merge_walk_ledger(head_style, fresh)
    if len(m["runs"]) != 2 or m["runs"][0]["when"] != head_style["when"] or m["latest_when"] != fresh["when"]:
        bad.append("HEAD 판(runs 없음) + 이번 1회 가 2회가 아니다 — 옛 판을 버렸다")
    m2 = merge_walk_ledger(m, dict(fresh, walks={"S2": {}}))
    if len(m2["runs"]) != 2 or m2["runs"][1]["walks"] != {"S2": {}}:
        bad.append("같은 `when` 을 다시 쓰면 그 판만 새 것이 돼야 하는데 그렇지 않다")
    if len(merge_walk_ledger({}, fresh)["runs"]) != 1:
        bad.append("빈 대장 + 이번 1회 가 1회가 아니다")
    try:
        from ledger_merge import LedgerShrank
        assert_not_shrunk("표본", 3, 1)
        bad.append("3 → 1 인데 멈추지 않았다 — 대장은 줄지 않는다")
    except LedgerShrank:
        pass

    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 초록 1 · 출생 표본 1 · 음성 4 · 판정 불가 2 · 걸음표 검사 · "
          f"대장 합치기 4 · **이름 공간 검사**(빌린 {len(BORROWED_FROM_PERF)} + 걷기 전용 "
          f"{len(WALK_ONLY_NAMES)} · 부딪히면 멈춘다) · 걷기 {len(WALKS)}개 전부 임자·폭이 있다")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — 브라우저를 열고 **사람처럼** 지나간다
# ═══════════════════════════════════════════════════════════════════════════
def _login(page, web: str, user: str, password: str) -> None:
    """로그인. **「다른 기기 접속」 확인 창을 사람처럼 처리한다.**

    ⚠ 이 환경은 동시 접속 1개다. 확인을 누르면 **앞의 세션이 끊긴다** — 그래서 이
      도구는 끝나면 반드시 로그아웃한다. 물고 있는 것이 남에게 주는 피해다.
    """
    page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(2_000)
    fields = page.locator("input")
    if fields.count() < 2:
        raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
    fields.nth(0).fill(user)
    fields.nth(1).fill(password)
    page.get_by_role("button", name="Log In").click()
    page.wait_for_timeout(3_000)
    confirm = page.get_by_role("button", name="Confirm")
    if confirm.count():
        # 「이 계정이 다른 기기에서 접속 중입니다」 — end_previous_session 과 같은 뜻이다.
        confirm.first.click()
        page.wait_for_timeout(9_000)
    else:
        page.wait_for_timeout(6_000)
    if page.url.rstrip("/").endswith("/login"):
        raise RuntimeError(
            f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
            f"본문: {page.inner_text('body')[:200]!r}")


def _one_walk(page, web: str, key: str, steps: list) -> dict:
    """한 시나리오를 걷는다. **각 걸음의 시간과 클릭 수를 따로 센다.**"""
    out = {"clicks": 0, "ms": 0, "steps": [], "completed": False, "failed_at": None}
    started_all = time.perf_counter()
    for i, step in enumerate(steps, start=1):
        started = time.perf_counter()
        what = ""
        #: **일부러 기다린 시간.** 이것을 빼지 않으면 「경과 18초」가 화면이 느린
        #: 것처럼 읽힌다 — 사실은 17초가 이 도구가 심은 대기다. 재는 사람이 심은
        #: 시간을 재는 대상의 시간으로 적는 것이 착시 ⑤다.
        settle = 0
        try:
            if "go" in step:
                what = f"주소 {step['go']}"
                page.goto(f"{web}{step['go']}", wait_until="networkidle", timeout=60_000)
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click" in step:
                role, name = step["click"]
                what = f"{role} 「{name}」 누름"
                target = page.get_by_role(role, name=name)
                if not target.count():
                    raise RuntimeError(
                        f"390px 화면에 {role} 「{name}」 가 없다 — **모바일에서 누를 수 "
                        f"없는 자리**이거나 이름이 바뀌었다")
                target.first.click()
                out["clicks"] += 1
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click_text" in step:
                what = f"글자 「{step['click_text']}」 누름"
                target = page.get_by_text(step["click_text"], exact=False)
                if not target.count():
                    raise RuntimeError(
                        f"390px 화면에 「{step['click_text']}」 가 없다")
                target.first.click()
                out["clicks"] += 1
                settle = 5_000
                page.wait_for_timeout(settle)
            elif "click_row" in step:
                n = step["click_row"]
                what = f"표 {n}번째 줄 누름"
                rows = page.get_by_role("row")
                # 0번째는 머리글이다. 사람이 누르는 것은 그 아래 첫 줄이다.
                if rows.count() <= n:
                    raise RuntimeError(f"표에 누를 줄이 없다 (줄 {rows.count()}개)")
                rows.nth(n).click()
                out["clicks"] += 1
                settle = 6_000
                page.wait_for_timeout(settle)
            body = page.inner_text("body")
            if step["see"] not in body:
                raise RuntimeError(
                    f"「{step['see']}」 가 화면에 없다 — 본문: {body[:200]!r}")
        except Exception as exc:                                # noqa: BLE001
            # ★ [실측 2026-09-05 TC] **로그인 화면으로 튕긴 것은 화면의 결함이 아니다.**
            #   이 환경은 동시 접속 1개다 — 걷는 도중 다른 차선이 로그인하면 이쪽 세션이
            #   그 자리에서 끝나고, 다음 걸음은 전부 로그인 화면을 본다.
            #   그것을 「이 자리를 못 누른다」로 적으면 **환경의 사실을 화면의 결함으로**
            #   기록하는 것이고, 그 기록은 다음 사람을 없는 버그로 하루 보내게 한다(D-322).
            if page.url.rstrip("/").endswith("/login"):
                out["session_lost"] = True
            out["failed_at"] = i
            ms = round((time.perf_counter() - started) * 1000)
            out["steps"].append({"n": i, "what": what, "ok": False, "ms": ms,
                                 "settle_ms": settle, "net_ms": max(ms - settle, 0),
                                 "why": f"{type(exc).__name__}: {exc}"[:300]})
            break
        ms = round((time.perf_counter() - started) * 1000)
        out["steps"].append({"n": i, "what": what, "ok": True, "ms": ms,
                             "settle_ms": settle, "net_ms": max(ms - settle, 0)})
    else:
        out["completed"] = True
    out["ms"] = round((time.perf_counter() - started_all) * 1000)
    #: **심은 대기를 뺀** 시간. 표에 적는 수는 이쪽이다.
    out["net_ms"] = sum(s.get("net_ms", 0) for s in out["steps"])
    return out


def _logout(page, api: str) -> bool:
    """**세션을 닫는다.** 브라우저가 가진 토큰으로 그대로 부른다 — 다시 로그인해서
    닫으면 그 사이에 세션이 하나 더 생기고, 그것이 정확히 이 절이 막으려는 일이다."""
    try:
        token = page.evaluate(
            "() => { try { const u = JSON.parse(localStorage.getItem('userInfo')"
            " || '{}'); return u.access_token || u.token || ''; } catch (e)"
            " { return ''; } }")
        if not token:
            return False
        got = page.evaluate(
            """async ([api, token]) => {
                const r = await fetch(api + '/api/v1/auth/logout', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json',
                              'Authorization': 'Bearer ' + token},
                    body: '{}'});
                return r.status;
            }""", [api, token])
        return int(got) in (200, 201, 204)
    except Exception:                                           # noqa: BLE001
        return False


def walk(*, web: str, api: str, user: str, password: str,
         accounts: dict | None = None, only=()) -> dict:
    """걷는다. [P-181 · 턴 V] **사람과 폭이 걸음마다 다르다.**

    `accounts` — `WALK_META[…]["who"]` → `(아이디, 비밀번호)`. 없는 임자의 걷기는
      **걷지 않고 `not_attempted` 에 사유와 함께 적는다** — 자격이 없어 못 간 것을
      「그 화면이 안 뜬다」로 적으면 다음 사람이 없는 버그로 하루를 보낸다(D-322).
    `only` — 이 아이디들만 걷는다(재측용). 비면 전부.
    """
    from playwright.sync_api import sync_playwright

    accounts = dict(accounts or {})
    accounts.setdefault("route", (user, password))
    keys = [k for k in WALKS if (not only or k in only)]
    #: 사람이 바뀔 때마다 로그인이 하나씩 는다 — **임자별로 묶어** 로그인 회수를 최소로 한다.
    groups: dict = {}
    for k in keys:
        groups.setdefault(WALK_META[k]["who"], []).append(k)

    result = {"viewport": VIEWPORT, "web": web, "api": api,
              "when": datetime.now().replace(microsecond=0).isoformat(),
              "names_from_perf_load": _scenario_names(),
              "walk_meta": {k: {"viewport": WALK_META[k]["viewport"],
                                "who": WALK_META[k]["who"]} for k in WALKS},
              "walks": {}, "console_errors": {}, "session_closed": None,
              "not_attempted": {k: "이번 실행이 고르지 않았다(--only)"
                                for k in WALKS if k not in keys},
              "not_walked": NOT_WALKED}

    current = {"key": "login"}
    errors: dict = {"login": []}
    #: 화면이 부른 **우리 API 중 실패한 것**. 콘솔 줄만 보면 「Network Error」까지만
    #: 보이고 **무엇이 왜 실패했는지**가 안 남는다 — 그 한 줄이 다음 사람의 하루다.
    api_failures: dict = {}

    def note(kind: str, text: str) -> None:
        errors.setdefault(current["key"], []).append(f"{kind}: {text}"[:300])

    def note_console(m) -> None:
        """`console.error` 한 줄. **자원 적재 실패에는 URL 을 붙인다.**

        ★ [실측 2026-09-05 턴 F] 브라우저가 적는 줄은 「Failed to load resource: the
          server responded with a status of 404 (File not found)」 **뿐**이다 —
          어느 자원인지가 없다. 그 줄로는 인수 자산의 글꼴 404 와 우리 화면의 고장을
          가를 수 없고, **가를 수 없는 줄은 분류할 수 없다.** 그래서 못 가른 채로
          「분류되지 않은 오류」에 쌓였고, 그 수는 아무에게도 자리를 알려 주지 않았다.
          브라우저는 그 자리를 `location.url` 로 함께 준다 — 붙여서 적는다.
        """
        if m.type != "error":
            return
        text = m.text
        try:
            url = (m.location or {}).get("url") or ""
        except Exception:                                       # noqa: BLE001
            url = ""
        if url and url not in text:
            text = f"{text} ← {url}"
        note("console.error", text)

    def note_response(r) -> None:
        try:
            if r.status >= 400 and "/api/" in r.url:
                api_failures.setdefault(current["key"], []).append(
                    f"{r.status} {r.request.method} {r.url}"[:200])
        except Exception:                                       # noqa: BLE001
            pass

    closed_all, logged_in = [], 0
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        for who, wkeys in groups.items():
            acct = accounts.get(who) or ()
            if len(acct) != 2 or not acct[0] or not acct[1]:
                #: **자격이 없으면 안 걷는다.** 지어낸 계정으로 걸으면 그 빨강은 화면의
                #: 빨강이 아니다. 못 간 것을 못 갔다고 적는다(D-301).
                for k in wkeys:
                    result["not_attempted"][k] = (
                        "임자 %r 의 자격이 없다 — 이 도구는 계정을 만들지 않는다 "
                        "(만들면 대장에 없는 계정이 생기고 비밀번호가 소스에 박힌다)" % who)
                continue
            #: 폭은 걸음마다다. 같은 임자라도 폭이 다르면 **다른 창**에서 걷는다 —
            #: 창 하나를 쓰면서 폭만 바꾸면 이미 그려진 화면이 그대로 남아 착시가 된다.
            for vp_key in sorted({tuple(sorted(WALK_META[k]["viewport"].items())) for k in wkeys}):
                vp = dict(vp_key)
                mine = [k for k in wkeys if WALK_META[k]["viewport"] == vp]
                if logged_in:
                    #: 사람이 바뀌었다 — IP 당 로그인 5회/분 · 계정당 세션 1개 (P-157).
                    print(f"{TAG} 사람을 바꾼다 — {GAP_SECONDS}초 기다림 "
                          f"(율제한 · 동시 접속 1개)")
                    time.sleep(GAP_SECONDS)
                context = browser.new_context(viewport=vp)
                page = context.new_page()
                # ★ **두 가지를 다 듣는다**: 잡히지 않은 예외(pageerror)와 `console.error`.
                #   전자만 들으면 화면이 스스로 삼킨 오류가 안 보인다.
                page.on("pageerror", lambda e: note("pageerror", str(e)))
                page.on("console", note_console)
                page.on("response", note_response)
                current["key"] = "login:%s" % who
                errors.setdefault(current["key"], [])
                try:
                    _login(page, web, acct[0], acct[1])
                    logged_in += 1
                    for key in mine:
                        current["key"] = key
                        errors.setdefault(key, [])
                        result["walks"][key] = _one_walk(page, web, key, WALKS[key])
                except Exception as exc:                        # noqa: BLE001
                    note("login", f"{type(exc).__name__}: {exc}")
                    for k in mine:
                        result["not_attempted"].setdefault(
                            k, "로그인하지 못했다(%s) — 화면의 결함이 아닐 수 있다" % who)
                finally:
                    #: **세션은 쓴 자리마다 닫는다.** 하나라도 못 닫으면 전체가 빨강이다.
                    closed_all.append(_logout(page, api))
                    context.close()
        browser.close()
    result["session_closed"] = (all(closed_all) if closed_all else None)
    result["logins"] = logged_in
    result["console_errors"] = errors
    result["api_failures"] = api_failures
    result["session_lost"] = any(w.get("session_lost")
                                 for w in result["walks"].values())
    return result


def _evidence_dir() -> Path:
    """증거 자리. 컨테이너는 저장소를 `/repo`, 문서를 `/docs` 로 **따로** 붙인다 —
    `capture_screens` 가 같은 함정을 이미 밟았다. 자리를 하나로 못 박지 않는다."""
    #: ★ [실측 2026-09-05 TC] `agent/evidence` 가 **있는지**만 보면 틀린다 —
    #:   컨테이너의 `/repo/docs` 는 마운트가 아니라 **빈 껍데기**이고, 거기에 쓰면
    #:   증거가 컨테이너 안에서 사라진다(호스트에서 안 보인다). 그래서 **정본 파일**이
    #:   있는 자리를 고른다: 「폴더가 있다」와 「그 폴더가 그 폴더다」는 다른 사실이다.
    marker = Path("agent") / "evidence" / "D-346" / "ga_readiness.yaml"
    for base in (Path("/docs"), ROOT / "docs"):
        if (base / marker).is_file():
            return base / "agent" / "evidence" / "UX-WALK"
    return ROOT / "docs" / "agent" / "evidence" / "UX-WALK"



# ═══════════════════════════════════════════════════════════════════════════
# [P-170 ① · 2026-09-18 턴 U · 차선 Q] **재는 동안 아무도 로그인하지 않는다**
#
#   턴 T 에 V 가 재는 동안 조율자의 게이트가 같은 역할 계정으로 로그인해 V 의 세션을
#   끊었다(계정당 세션 1개 → `end_previous_session` → 429 · D-487 ①). V 는 그 판을 버렸다.
#   이 도구는 **로그인을 한다** — 그러므로 LOCK 을 먼저 본다.
#
#   ★ **잠근 사람은 지나간다**: `GX_V_SESSION_ID` 가 LOCK 의 세션과 같으면 안 막는다.
#     그 밖의 사람에게는 **회색(exit 2)** 이다 — 회색은 초록이 아니다(D-301).
# ═══════════════════════════════════════════════════════════════════════════
def _v_lock_blocks(tag: str = TAG) -> bool:
    """V 단독 세션이 잠갔고 내가 그 사람이 아니면 True — 그때는 **재지 않는다**."""
    try:
        from v_lock import describe, is_locked
    except ImportError:                                   # 잠금 도구가 없으면 막지 않는다
        return False
    if not is_locked():
        return False
    print("%s ? **회색 — V 단독 중 · 재지 않음** (P-170 ① · docs/agent/evidence/V_LOCK)" % tag)
    print("%s   %s · 잠근 사람은 GX_V_SESSION_ID 를 주고 부른다" % (tag, describe()))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="시나리오 걷기 W1~W6 (W1~W3 390px · W5·W6 1440px)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", "http://localhost:3002"))
    ap.add_argument("--api", default=os.environ.get("GX_API", "http://localhost:8000"))
    ap.add_argument("--user", default=os.environ.get("GX_ROUTE_USER", ""))
    ap.add_argument("--password", default=os.environ.get("GX_ROUTE_PASSWORD", ""))
    #: [P-181] W5·W6 은 **다른 사람**이 걷는다. 비밀번호는 환경으로만 온다(소스에 두지 않는다).
    ap.add_argument("--u2-user", default=os.environ.get("GX_U2_USER", "gxseed_u2_manager"),
                    help="W5 「팀장 아침 인수」를 걷는 계정")
    ap.add_argument("--u5-user", default=os.environ.get("GX_U5_USER", "gxseed_u5_sysop"),
                    help="W6 「관리자 설치 다음 날」을 걷는 계정")
    ap.add_argument("--only", default="",
                    help="쉼표로 나눈 걷기 아이디만 (예: W5,W6) — 재측용")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL
    if _v_lock_blocks():
        return EXIT_UNDECIDABLE
    if not args.user or not args.password:
        print(f"{TAG} **판정 불가** — 계정이 없다. 이 도구는 계정을 만들지 않는다 "
              f"(만들면 대장에 없는 계정이 생기고 비밀번호가 소스에 박힌다)")
        return EXIT_UNDECIDABLE

    #: [P-181] 역할 계정의 비밀번호는 **환경 하나**에서 온다 — 씨앗 계정들이 쓰는 그 변수다.
    #: 없으면 W5·W6 은 **안 걷는다**(못 걸은 것으로 적힌다). 값은 어디에도 적지 않는다.
    seed_pw = os.environ.get("GX_SEED_ROLE_PASSWORD", "")
    accounts = {"route": (args.user, args.password),
                "u2": (args.u2_user, seed_pw),
                "u5": (args.u5_user, seed_pw)}
    only = tuple(x.strip() for x in args.only.split(",") if x.strip())
    unknown = [k for k in only if k not in WALKS]
    if unknown:
        print(f"{TAG} **판정 불가** — 모르는 걷기 아이디 {unknown}. "
              f"있는 것: {sorted(WALKS)} · 안 걷는 것: {sorted(NOT_WALKED)}")
        return EXIT_UNDECIDABLE
    if not seed_pw:
        print(f"{TAG} ⚠ GX_SEED_ROLE_PASSWORD 가 없다 — **W5·W6 은 안 걷는다**(못 걸은 것으로 적힌다). "
              f"자격이 없어 못 간 것을 화면의 결함으로 적지 않는다")

    try:
        result = walk(web=args.web, api=args.api, user=args.user,
                      password=args.password, accounts=accounts, only=only)
    except Exception as exc:                                    # noqa: BLE001
        print(f"{TAG} **판정 불가** — 걷지 못했다: {type(exc).__name__}: {exc}")
        print(f"{TAG} 화면(3002)·API(8000)·playwright 셋이 다 있어야 걷는다")
        return EXIT_UNDECIDABLE

    if result.get("session_lost"):
        print(f"{TAG} **판정 불가** — 걷는 도중 **세션을 빼앗겼다**(로그인 화면으로 튕겼다). "
              f"이 환경은 동시 접속 1개다: 다른 차선이 로그인하면 이쪽이 끝난다. "
              f"화면의 결함이 아니므로 빨강으로 적지 않는다 — **다시 걷는다.**")

    names = result["names_from_perf_load"]
    print(f"{TAG} [환경] {args.web} · {result['when']} · 로그인 {result.get('logins', '?')}회")
    if result.get("not_attempted"):
        print(f"{TAG} [못 걸었다 — 회색] {result['not_attempted']}")
    for key in WALKS:
        w = result["walks"].get(key, {})
        meta = WALK_META.get(key, {})
        vp = meta.get("viewport") or VIEWPORT
        print(f"{TAG} {key} {names.get(key, '?')} "
              f"[{meta.get('who', '?')} · {vp['width']}×{vp['height']}px]")
        print(f"{TAG}    클릭 {w.get('clicks', '?')}회 · "
              f"실걸음 {w.get('net_ms', '?')}ms (심은 대기 뺀 수) · "
              f"총 {w.get('ms', '?')}ms · "
              f"콘솔 오류 {len(result['console_errors'].get(key, []))}건 · "
              f"{'완주' if w.get('completed') else '멈춤(걸음 %s)' % w.get('failed_at')}")
        for s in w.get("steps", ()):
            print(f"{TAG}      {'  ' if s['ok'] else 'X '}{s['n']}. {s['what']} "
                  f"({s.get('net_ms', s['ms'])}ms + 대기 {s.get('settle_ms', 0)}ms)" + ("" if s["ok"] else f" — {s['why']}"))

    known, unknown = classify_console(result.get("console_errors") or {})
    n_known = sum(len(v) for v in known.values())
    if n_known:
        seen = {}
        for lines in known.values():
            for line in lines:
                why = next((w for tok, w in KNOWN_CONSOLE_NOISE if tok in line), "?")
                seen[why] = seen.get(why, 0) + 1
        print(f"{TAG} [알려진 잡음 {n_known}건] — 판정하지 않는다. 목록에 있으니 "
              f"「없다」와 「남의 자리다」가 섞이지 않는다:")
        for why, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            print(f"{TAG}      {n:3}건 · {why}")
    fails = result.get("api_failures") or {}
    if fails:
        print(f"{TAG} [화면이 부른 API 중 실패] — 판정하지 않는다. **다음 사람이 볼 "
              f"자리**로 적어 둔다:")
        for key, lines in fails.items():
            for line in sorted(set(lines))[:6]:
                print(f"{TAG}      {key} · {line}")

    # ★★ [P-181 · 턴 V] **못 간 것은 회색이다 — 빨강이 아니다.**
    #   자격이 없거나 `--only` 로 안 고른 걷기가 있으면 이 회차는 **덜 걸은 회차**이고,
    #   그것은 「걸었는데 막혔다」와 다르다(D-301 · 이 도구의 종료 코드 계약: 2 = 못 걸었다).
    #   ⚠ 그러나 **걸어 본 자리가 막혔으면 빨강이 이긴다** — 회색이 빨강을 덮지 않는다.
    skipped = result.get("not_attempted") or {}
    walked_red = any(not w.get("completed") for w in (result.get("walks") or {}).values())
    red = False
    for (name, ok, why) in judge(result):
        print(f"{TAG} {'  ' if ok else 'X '}{name:22} {why}")
        if ok:
            continue
        #: 「다 걸었다」가 **못 간 것 때문에만** 안 선 것이면 그것은 회색이지 빨강이 아니다.
        if name == WALKED_LABEL and skipped and not walked_red:
            continue
        red = True
    if result.get("session_lost"):
        rc = EXIT_UNDECIDABLE          # 세션을 빼앗긴 판은 버린다 — 다시 걷는다
    elif red:
        rc = EXIT_FAIL
    elif skipped:
        rc = EXIT_UNDECIDABLE          # 덜 걸은 회차 — **회색은 초록이 아니다**
    else:
        rc = EXIT_OK

    out = Path(args.json_out) if args.json_out else _evidence_dir() / "walk.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        #: ★ P-154 — 이번 실행분은 runs/ 에 그대로, 대장에는 옛 실행 + 이번 실행을 합쳐 쓴다.
        stamp = str(result.get("when") or datetime.now().isoformat()).replace(":", "").replace("-", "")
        run_copy = out.parent / "runs" / f"walk_{stamp}.json"
        run_copy.parent.mkdir(parents=True, exist_ok=True)
        run_copy.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        old_doc = _read_json(out)
        merged = merge_walk_ledger(old_doc, result)
        out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{TAG} [증거] 이번 실행 {run_copy}")
        print(f"{TAG} [대장] {out} — 옛 {len(ledger_runs(old_doc))}회 + 이번 1회 → {len(merged['runs'])}회 (줄지 않았다)")
    except (OSError, RuntimeError) as exc:
        print(f"{TAG} ⚠ 증거를 못 남겼다: {type(exc).__name__}: {exc}")

    print(f"{TAG} " + {
        EXIT_OK: f"통과 — 걷기 {len(WALKS)} 시나리오를 다 걸었고 콘솔은 조용했다. "
                 f"★ 클릭 수는 **기준선이지 합격선이 아니다**",
        EXIT_FAIL: "실패 — 위의 X 가 그 폭에서 막힌 자리다",
        EXIT_UNDECIDABLE: ("**회색** — 끝까지 못 걸었다"
                           + (f" (못 간 것 {sorted(skipped)})" if skipped else " (세션을 빼앗겼다)")
                           + ". 회색은 초록도 빨강도 아니다 (D-301)"),
    }[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
