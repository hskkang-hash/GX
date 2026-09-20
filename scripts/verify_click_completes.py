#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-118 강제 도구 — **누른 뒤를 보지 않은 초록은 초록이 아니다.**

    「그려졌다 ≠ 동작한다」

★★ 이 도구가 태어난 사유 [2026-09-08 · CR-USER · 턴 N~O]
------------------------------------------------------------
제품의 **핵심 동작**인 「실제로 판정」이 여러 턴 동안 **0.5 「구현」**으로 채점됐다.
근거는 「상세 화면에 판정 칸이 그려졌다」였다. 사람이 그것을 실제로 눌렀더니:

    네트워크 요청 **0** · 확인창 **0** · 토스트 **0** · 오류 **0** · 판정 그대로 「미판정」

원인은 한 줄이었다. `react 19` + `antd 5` 는 `@ant-design/v5-patch-for-react-19` 를
필요로 하고, 그것은 `frontend/package.json:25` 에 **선언돼 있었으며 아무도 import 하지
않았다**. 그래서 제품의 모든 `Modal.confirm` 과 `message.*` 가 **한 번도 뜨지 않았다**.

    의존성은 설치됐고 배선은 안 됐다. **코드는 배포됐고 실행만 안 됐다.**

왜 게이트가 못 잡았나 — 그것이 이 파일의 전부다:

    `scripts/capture_screens.py` 는 **화면을 열어 찍는다.**
    확인창은 **누른 뒤에** 뜬다. 그러므로 촬영 경로에 **없었다.**
    이 저장소의 어떤 게이트도 **누른 뒤**를 보지 않았다.

그래서 이 게이트는 48 흐름마다 **네 칸**을 잰다. 넷이 다 서야 초록이다:

    ① 누르는 것        그 자리에 **누를 것이 실재하는가** (이름·선택자)
    ② 기대 호출        누른 뒤 **그 요청이 실제로 나갔는가** (메서드+경로)
    ③ 기대 상태 변화   **새 GET 으로 다시 읽어** 값이 정말 바뀌었는가
    ④ 기대 화면 문구   그 뒤 **화면이 그 말을 하는가**

색의 규칙 — **회색과 빨강을 섞지 않는다**
-------------------------------------------
    회색  누를 자리를 **못 찾았다.** 재지 못한 것이다. 초록이 아니다 (exit 2)
          → **이름을 반드시 적는다.** 못 잰 자리를 익명으로 두면 다음 사람이 못 찾는다
    빨강  ㉠ 눌렀는데 **아무것도 나가지 않았다**   ← 2026-09-08 의 그 모양
          ㉡ 요청은 나갔는데 **값이 안 바뀌었다**   ← 이 턴 결함의 **가족**
          ㉢ 값은 바뀌었는데 **화면이 침묵한다**   ← 성공을 실패로 읽고 다시 누른다
          ㉣ 관문이 **거절했다**(401·403)          ← 빨강이되 **사유를 따로 적는다**
    초록  넷이 다 섰다

★ **면제 칸이 없다** (D-327). 이 파일 어디에도 「알려진 정상」 목록이 없다.
  판정기(`judge`)는 **관측만** 받는다 — 흐름 이름을 보고 봐주는 길이 없다.
  `_no_exception_slot()` 이 **자기 소스를 훑어** 그런 이름이 생기면 자기시험을 깬다.

★ **빨강을 회색으로 내리지 않는다.** 누를 자리가 있었고 눌렀는데 안 되면 그것은
  「못 쟀다」가 아니라 **「안 된다」**다. 그 둘을 한 칸에 넣으면 이 도구가 태어난
  사유가 그대로 지워진다.

    python scripts/verify_click_completes.py --self-test   # 판정 규칙만 (브라우저 없이)
    python scripts/verify_click_completes.py --measure     # gx-shell 안에서 **실제로 누른다**
    python scripts/verify_click_completes.py               # 증거를 읽어 판정 · N/48
    python scripts/verify_click_completes.py --list        # 흐름별 네 칸
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

#: ★ [P-156 · 턴 T · 차선 Q] probe 표식 규약 — 씨앗 카메라 표를 **한 곳**(`probe_marks.py`)에서 가져온다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_marks import PROBE_TAG, load_seed  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "P-118"
OBSERVED = EVIDENCE / "click_completes.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[P-118]"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

GREEN, RED, GREY = "green", "red", "grey"

#: 증거가 이보다 오래되면 **재지 않은 것**으로 본다 (D-301). 화면은 매 턴 바뀐다.
MAX_AGE_HOURS = 12

#: 「누른 뒤」를 재는 창. 확인창 → 요청 → 응답 → 토스트까지가 이 안에 들어와야 한다.
CLICK_WINDOW_MS = 4500


# ──────────────────────────────────────────────────────────────────────────
# 48 흐름 — 여섯 사람 × 여덟 일. 정본은 docs/agent/onboarding_48.md 다.
#
# 각 행이 드는 것이 **네 칸**이다. 「선언된 자리가 없다」(control=None)는
# 이 표의 판단이 아니라 정본이 「없음 · 화면 없음」이라 적어 둔 자리를 그대로 옮긴 것이고,
# 그 행은 **관측에서 회색**으로 떨어진다 — 판정기가 이름을 보고 봐주는 것이 아니다.
# ──────────────────────────────────────────────────────────────────────────
#: [P-190 · 턴 W] 정정 주석의 머리표. 이 글자가 든 `note` 는 **「없다」는 낱말을 나르되
#: 주장하지 않는다** — 종전 주장이 틀렸음을 적는 자리이기 때문이다(`_NOTE_IS_CORRECTION`).
P190 = "[P-190 정정 · 턴 W] "


def F(key, title, actor, screen, control, call, state, text, confirm=None, note="",
      fill=None, fill_text=None, img_check=False, revert=None):
    """한 흐름.

    `revert` — [★ 턴 U · 차선 Q · 조율자 실측 2026-09-17 21:0x] **상태를 바꾸는 클릭은
      판정 뒤 같은 문으로 되돌린다.** 턴 T 의 `click_completes` 가 U5#9 「끄기/켜기」를
      눌러 `NotificationRule` pk 9(critical · fire_user)를 **끈 채로 남겼고**, 그래서
      다음 게이트(`verify_seed_roles` K2 수신자)가 「닿는 사람 0명」으로 빨강이 됐다.
      게이트가 제품의 상태를 남기면 **다음 게이트가 제품 대신 우리를 잰다.**

      규약: `revert_toggle()` 을 단 흐름은, 판정에 쓸 상태를 **다 읽은 뒤에** 같은 단추를
      한 번 더 눌러 원래 값으로 돌린다. 되돌린 사실(눌렀나 · 되돌아갔나)은 관측에
      `revert` 로 남고 보고에 셈으로 나온다.

      ★ 되돌리기는 **판정을 바꾸지 않는다.** 판정은 되돌리기 전에 이미 끝난 관측으로
        내려진다 — 되돌림이 실패해도 그 행의 빨강/초록은 그대로이고, 실패는 따로
        「되돌리지 못한 자리」로 적힌다(빨강을 회색으로 바꾸지 않는다).

    `fill` — 누르기 **전에** 채워야 하는 글상자의 `placeholder` (P-132).
      왜 필요한가: 제품이 **일부러** 빈 글상자에서 단추를 잠그는 자리가 있다
      (「회신 보내기」는 글이 비면 `disabled` 다 — `MobileEventDetail.tsx:481`).
      채우지 않고 눌러 「안 눌린다」를 적으면 **제품의 규율을 고장으로 파는 것**이다.
      ★ 이것은 면제가 아니다 — 채운 뒤에도 ②③④ 는 그대로 다 서야 한다.

    `fill_text` — [P-179 · 턴 V] 그 칸에 **무엇을 적을 것인가**. 안 주면 종전대로 기본 한 줄을
      적는다. `{event}` 는 **이번 회 씨앗 사건 번호**로 치환된다 — 「사건 보고서」의 사건번호 칸처럼
      숫자만 받는 칸이 있기 때문이다(기본 한 줄을 적으면 그 칸이 `118` 만 남기고 서버가 404 를 낸다).

    `img_check` — [P-148] 이 행의 술어 ④「화면이 말한다」를 **글자 대신 그림**으로 잰다.
      사진은 낱말로 못 잰다 — 「스냅샷」이라는 표제는 실패 화면에도 뜬다(성공·실패가 같은
      글자를 쓴다). 그래서 셋을 본다: `img[data-gx=snapshot]` 1개 · `naturalWidth>0` ·
      응답 200 image/jpeg. 셋이 다 서야 초록이고, 「불러오지 못했습니다」는 실제
      4xx/5xx 일 때만 나와야 한다 — 이 셋이 서 있는데 그 문구가 함께 뜨면 그 자체가
      모순이라 빨강이다 (`_cell_img` 마지막 검사).
    """
    return {
        "key": key, "title": title, "actor": actor, "screen": screen,
        "control": control, "confirm": confirm, "call": call,
        "state": state, "text": text, "note": note,
        "fill": fill, "fill_text": fill_text,
        "img_check": img_check, "revert": revert,
    }


def btn(name):
    return {"kind": "button", "name": name}


def revert_toggle():
    """**같은 문으로 되돌린다** — 판정 뒤 같은 단추를 한 번 더 누른다 (턴 U · 절 4).

    껐다 켜는 한 쌍의 단추(「끄기/켜기」처럼)는 **같은 단추를 다시 누르면 원래 값**이다.
    한쪽으로만 가는 전이(접수 → 조치 → 종결)나 **새로 만드는 문**(키 발급 · 구독)은
    같은 단추로 돌아오지 않는다 — 그런 자리에는 이것을 달지 않는다(달면 두 번 만든다).
    """
    return {"kind": "same_control"}


def no_revert(why: str):
    """**되돌리지 않는다 — 그리고 그 사유를 적는다** (턴 U · 절 4).

    한쪽으로만 가는 전이(접수 → 조치 → 종결)와 새로 만드는 문(회신 · 키 발급)은 같은
    단추로 돌아오지 않는다. 그런 자리를 「되돌림 선언 없음」으로 두면 **잊은 것**과
    구별되지 않으므로(D-301 의 0건 규칙과 같다) 선언은 하되 사유를 적는다.
    """
    return {"kind": "none", "why": why}


def changes_state(flow) -> bool:
    """이 흐름의 클릭이 **상태를 바꾸는가** — 단추를 눌러 쓰기 문을 부르면 그렇다.

    ★ 단추 **이름**으로 가르지 않는다. 「접수하기|조치 시작|종결하기」도 이름이 갈래로
      적혀 있지만 그것은 뒤집는 단추가 아니라 **한쪽으로만 가는 전이**다 — 다시 누르면
      원래로 오는 게 아니라 한 걸음 더 간다. 이름이 아니라 **문의 메서드**를 본다.
    """
    ctrl, call = flow.get("control"), flow.get("call")
    if not ctrl or ctrl.get("kind") != "button" or not call:
        return False
    return str(call[0]).upper() in ("POST", "PUT", "PATCH", "DELETE")


def goto():
    return {"kind": "goto"}


def api():
    return {"kind": "api"}


def srv_change(get, field):
    """쓰기 흐름 — **새 GET 으로 다시 읽어** 값이 before 와 달라야 한다."""
    return {"kind": "server_change", "get": get, "field": field}


def srv_reflect(get, field):
    """읽기 흐름 — 새 GET 이 낸 값이 **화면에 실제로 보여야** 한다.

    읽기 자리에서 「그려졌다 ≠ 동작한다」는 이 모양이다: 화면은 떴는데 서버 값이
    아니라 **빈 표**를 그린다(2026-09-08 `U5-USERS-ROLES-EMPTY` 가 그 자리다).
    """
    return {"kind": "server_reflect", "get": get, "field": field}


FLOWS = (
    # ── U1 · 관제요원 ────────────────────────────────────────────────────
    #: ★ [P-141 · 턴 Q] 첫 화면이 역할 홈이 됐다(`features/nav/roleHome.ts` · P-131 사양).
    #:  관제요원의 홈은 `/dsm/queue` 이고 그 화면의 정본 제목은 `FocusQueue.tsx:108`
    #:  `HEADLINE` 「지금 처리할 것 — 가장 급한 하나」다. 기대식은 그 뒤 반쪽만 쓴다 —
    #:  앞 반쪽 「지금 처리할 것」은 **사이드바 줄 이름**(`roleNav.ts:83`)이라 `/profile`
    #:  에 떨어져도 화면에 뜬다. 그 글자를 기대하면 종전 빨강이 거짓 초록으로 바뀐다.
    #:  종전 기대식(「관제·대시보드·이벤트·GuardianX」)은 역할 홈이 없던 시절의 짐작이었다.
    F("U1#1", "교대 시작 — 로그인", "u1", "/login", btn("로그인"),
      ("POST", r"/api/v1/auth/login$"),
      {"kind": "route_change", "from": "/login"}, ["가장 급한 하나"],
      revert=no_revert("로그인은 제품의 상태가 아니라 **세션**이다. 되돌림(로그아웃)을 하면 "
                       "뒤의 일곱 행이 그 세션으로 걷지 못한다 — 되돌리는 것이 측정을 끊는다")),
    #: ★ [P-132 · 2026-09-11] `preset` 은 **화면에 한 번도 안 뜨는 값**이다 —
    #:  `ControlDashboard.tsx:158` 이 `PRESET_LABEL` 로 「관제요원 화면」이라 부른다.
    #:  화면이 서버 값을 **그대로 적는** 자리는 `panel_total` 하나다:
    #:  `ControlDashboard.tsx:183` 「화면 {panel_total}칸이 정상적으로 그려졌습니다.」
    F("U1#2", "전체 상황판 한눈에", "u1", "/dsm/dashboard", goto(),
      ("GET", r"/api/dsm/dashboard/frame"),
      srv_reflect("/api/dsm/dashboard/frame", "panel_total"),
      ["상황", "대시보드", "칸이 정상적으로"]),
    #: ★ [P-132] `counts` 는 **사전이다.** `dig()` 가 그 자리에서 내는 3 은 칸 수가
    #:  아니라 **열쇠의 개수**(alive·total·never_seen)였다 — 어떤 카메라 수와도 무관한
    #:  계측 착시다. 화면이 적는 수는 `counts.total` 이고 그 자리는
    #:  `CameraGrid.tsx:130` 「전체 {counts.total}대」다.
    F("U1#3", "죽은 카메라 확인", "u1", "/dsm/cameras/grid", goto(),
      ("GET", r"/api/dsm/cameras/pulse"),
      srv_reflect("/api/dsm/cameras/pulse", "total"), ["카메라", "응답 없음", "전체"]),
    #: ★ [P-132] **정본 없음 — 재는 잣대가 없다.** 이 화면은 인수 자산이고
    #:  [실측 2026-09-10] 부르는 문은 `GET /api/stream-monitors/stream-monitors` 이며
    #:  화면은 카메라 **이름 타일**만 그린다(GD-150Q · H40 · NBP-DR-P2). 서버 값이
    #:  화면에 **수로도 글자로도** 드러나는 칸이 없어 ③「다시 읽어 화면에 있는가」의
    #:  잣대가 정본으로 정해진 적이 없다. 종전 이 행은 `/api/dsm/cameras/pulse` 의
    #:  `counts`(=사전 길이 3)를 보고 빨강이었다 — **재지 못한 것을 안 된다고 판 것**이다.
    F("U1#4", "실시간 스트림 열기", "u1", None, None, None, None, [],
      note="정본 없음 — 인수 스트림 화면에 서버 값이 드러나는 칸이 없다 "
           "(실측: GET /api/stream-monitors/stream-monitors · 화면은 이름 타일뿐)"),
    F("U1#8", "이벤트 목록 확인", "u1", "/dsm/events", goto(),
      ("GET", r"/api/dsm/events(\?|$)"),
      srv_reflect("/api/dsm/events?limit=20", "events"), ["이벤트", "발생"]),
    F("U1#9", "이벤트 상세 열기", "u1", "/dsm/events/{event}", goto(),
      ("GET", r"/api/dsm/events/\d+$"),
      srv_reflect("/api/dsm/events/{event}", "event_id"), ["이벤트", "상세", "발생"]),
    #: ★★ **이 턴의 그 자리.** 0.5 「그려졌다」로 채점되던 행이 여기서 다시 재진다.
    F("U1#11", "진위 판단 — 진짜인가 오탐인가", "u1", "/dsm/events/{event}",
      btn("실제로 판정"), ("POST", r"/api/dsm/events/\d+/review"),
      srv_change("/api/dsm/events/{event}", "verdict"),
      ["판정", "실제", "확정"], confirm=btn("확인"),
      revert=no_revert("판정은 **감사 기록이 남는 한쪽 전이**다. 되돌리면 감사에 거짓 왕복이 "
                       "남는다(대장은 줄지 않는다). 대상은 이번 회 씨앗 사건이라 다음 회에 "
                       "안 남는다 — 씨앗은 회마다 새로 심는다(P-156)"),
      note="확인창(Modal.confirm)을 지나는 길. 2026-09-08 에 요청 0건이었다"),
    #: ★ [P-132] 이 화면이 **실제로 그리는 수**는 이벤트 5건이 아니라 교대 초안의
    #:  「미처리: N건」이고, 그 수는 `ShiftHandoverPanel.tsx:79` 가
    #:  `GET /api/dsm/events/summary?hours=24`(같은 파일 42행 `SHIFT_HOURS = 24`) 로
    #:  받아 `draftText()`(68행)에서 적는다.
    F("U1#19", "교대 인계 메모", "u1", "/handover", goto(),
      ("GET", r"/api/.*(handover|shift)"),
      srv_reflect("/api/dsm/events/summary?hours=24", "unhandled"),
      ["인계", "메모", "교대"]),

    # ── U2 · 관제팀장/상황실장 ───────────────────────────────────────────
    F("U2#1", "밤사이 요약 보기", "u2", "/dsm/events", goto(),
      ("GET", r"/api/dsm/events/summary"),
      srv_reflect("/api/dsm/events/summary?hours=12", "unhandled"),
      ["요약", "미처리", "오탐"]),
    F("U2#2", "미처리 이벤트 확인", "u2", "/dsm/events?preset=unhandled", goto(),
      ("GET", r"/api/dsm/events\?.*response_state"),
      srv_reflect("/api/dsm/events?limit=50&response_state=occurred", "events"),
      ["미처리", "이벤트"]),
    #: ★ [P-132] 「되돌리기」는 **판정 문을 부르지 않는다.** 그 단추는
    #:  `EventDetail.tsx:508` 의 처리-단계 전이(`advance()`)이고 부르는 문은
    #:  `/response` 다 — 바뀌는 칸은 `verdict` 가 아니라 `response_state` 다.
    #:  확인창의 이름도 「확인」이 아니라 `EventDetail.tsx:256` 의 **「되돌리기」**다.
    #:  ⚠ 이 단추는 `response_state == 'closed'` 일 때만 그려진다(같은 파일 505행) —
    #:    그렇지 않은 사건에서는 **누를 자리가 없어 회색**이 맞다.
    F("U2#3", "이벤트 등급 재판정", "u2", "/dsm/events/{event}",
      btn("되돌리기 \\(사유 필수\\)"),
      ("POST", r"/api/dsm/events/\d+/response"),
      srv_change("/api/dsm/events/{event}", "response_state"),
      ["되돌", "사유"], confirm=btn("되돌리기"),
      revert=no_revert("이 단추 **자체가 되돌림 문**이다. 한 번 더 누르면 원래로 오는 것이 "
                       "아니라 또 되돌린다(사유가 또 하나 남는다) — 대상은 이번 회 씨앗 사건이다"),
      note="사유 필수 · 확인창을 지나는 길 · 종결된 사건에서만 그려진다"),
    F("U2#4", "심각 이벤트 상황 판단", "u2", "/dsm/events/{event}", goto(),
      ("GET", r"/api/dsm/events/\d+$"),
      srv_reflect("/api/dsm/events/{event}", "severity"), ["심각", "critical", "대응"]),
    #: ★ [P-132] `GET /api/dsm/reports/templates` 는 **서 있다**(`api.py:750`). 그러나
    #:  그 문을 부르는 화면이 저장소에 **없다** — `/report-template` 은 인수 자산의
    #:  운송장 서식 화면이고 부르는 문은 `/api/report-template/`(`services/API.ts:819`)다.
    #:  즉 「그려졌다 ≠ 동작한다」가 아니라 **아직 안 그려졌다**. 그 사실을 빨강으로
    #:  적으면 남의 화면을 우리 결함으로 파는 것이 된다.
    #: ★★ [P-179 · 2026-09-18 턴 V · 차선 Q] **위 문단은 턴 U 이전 사실이다 — 정정한다.**
    #:  턴 V(파 3 턴 1)의 실측이 「정본이 낡았다」고 적은 넷 중 하나다
    #:  (`docs/workorders/WO-GX-20260915-01_report_wave3_turn1.md` §4 · 그 표의 문안 그대로).
    #:  턴 U 에 **그 화면이 섰다**: `/dsm/reports`(`features/dsm/pages/Reports.tsx` ·
    #:  `dsm/routes.u24.ts:53` · `App.tsx:724`)의 카드 셋 중 **첫째가 「사건 보고서」**이고
    #:  그 카드의 「만들기」가 `POST /api/dsm/reports/runs`(`api_u24.py:408`)를 부른다.
    #:  ⚠ `/report-template` 이 인수 자산의 운송장 서식이라는 사실은 **안 바뀌었다** — 바뀐 것은
    #:    「그것 말고는 아무 데도 없다」는 쪽이다.
    #:  ⚠ 「사건 보고서」 카드는 **사건번호 칸이 비면 단추가 잠긴다**(`Reports.tsx` `disabled=
    #:    {f.needsEvent && !eventId}` · 그 칸은 숫자만 받는다) — 그래서 `fill` 로 이번 회
    #:    씨앗 사건 번호를 먼저 적는다(`fill_text` 의 `{event}` 치환 · 이 턴에 드라이버를 같이 늘렸다).
    F("U2#6", "상황보고서 생성", "u2", "/dsm/reports", btn("만들기"),
      ("POST", r"/api/dsm/reports/runs"),
      srv_change("/api/dsm/reports/runs?kind=incident&limit=200", "total"),
      ["만들었습니다", "사건 보고서"],
      fill="사건번호", fill_text="{event}",
      revert=no_revert("**새 실행 기록을 만드는 문**이다 — 같은 단추를 한 번 더 누르면 원래로 "
                       "오는 것이 아니라 행이 하나 더 생긴다(`trigger=manual` · 실행 목록에 남는다). "
                       "행을 지우는 문은 제품에 없다"),
      note="[P-179 정정] 종전 정본 「그 문을 부르는 화면이 없다」는 **턴 U 이전 사실**이다"),
    F("U2#9", "요원별 처리 현황", "u2", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `/dsm/team-status` · `GET /api/dsm/stats/by-reviewer` 200 · "
           "제목 `요원별 현황` 을 적어 두었다(턴 T 에 채운 9행). 종전 주석 「집계 면 "
           "자체가 만들어지지 않았다」는 그 전 사실이다. **이 도구가 안 누를 뿐**이고, "
           "안 누르는 사유는 한 번 누름으로 끝나는 단추가 아니라 화면 도달이라 "
           "네 칸(①~④) 중 ②가 안 선다는 것이다 — 회색이지 「정본이 비었다」가 아니다"),
    F("U2#16", "알림 규칙 확인", "u2", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `/dsm/notify` · `GET /api/dsm/settings/notify-rules/list` 200 · "
           "제목 `알림 받는 사람·채널` 을 적어 두었다. 종전 주석 「조회 라우트도 화면도 "
           "만들어지지 않았다」는 턴 S 이전 사실이다. 이 도구는 **같은 화면의 쓰기 쪽만** "
           "누른다(U5#9) — 읽기 확인은 U5#9 의 재조회가 겸하므로 이 행은 안 누른다"),
    F("U2#19", "장애 판단 — 시스템인가 현장인가", "u2",
      "/dsm/events?preset=system", goto(),
      ("GET", r"/api/dsm/events\?.*event_type"),
      srv_reflect("/api/dsm/events?limit=50&event_type=camera_down,storage_high", "events"),
      ["시스템", "카메라", "장애"]),

    # ── U3 · 이동 중 수신 모드 (390px) ───────────────────────────────────
    #: ★ [P-132] 화면에 「발송」이라는 단추는 **없다.** UX-20 이 「규칙대로 발송」을
    #:  **「알림 보내기」**로 바꿨고(`EventDetail.tsx:279-287`), 종전 기대식의 「발송」은
    #:  본문 아무 데나 걸리는 글자를 잡아 눌러 **호출 0건을 제품의 빨강으로 팔았다**.
    #: ★ [P-141 · 턴 Q · 차선 Q 3종 분류: 기대식 오류] 종전 재조회 `deliveries?limit=1` 의
    #:  `total` 은 **돌려준 행 수**(`api.py:700` `len(rows)`)라 1 을 넘을 수 없다 — 발송 행이
    #:  실제로 늘어도(턴 P 관측 06:53:16~17) 1 → 1 로 「그대로」였다. 이 사건의 이력만
    #:  거르고 상한을 넉넉히 둬야 N → N+k 가 보인다. 중복 억제(F-04 5분)로 0 통이면 여전히
    #:  빨강이고, 그때 화면은 「새로 보낸 알림이 없습니다」라고 말한다(`EventDetail.tsx`).
    F("U3#1", "알림 수신", "u3", "/dsm/events/{event}", btn("알림 보내기"),
      ("POST", r"/api/dsm/events/\d+/notify"),
      srv_change("/api/dsm/deliveries?event_id={event}&limit=500", "total"), ["발송", "알림"],
      revert=no_revert("보낸 알림은 **안 보낸 것으로 못 만든다**. 발송 기록을 지우는 것은 대장을 줄이는 일이다 — 대상은 이번 회 씨앗 사건이다")),
    F("U3#2", "위치 확인 — 어디로 가나", "u3", "/m/events/{event}", goto(),
      ("GET", r"/api/dsm/events/\d+$"),
      srv_reflect("/api/dsm/events/{event}", "address"), ["어디로", "주소", "위치"]),
    #: ★ [P-148 · 턴 R] **사진 술어를 켠다.** 「사진」·「스냅샷」은 실패 화면(표제)에도
    #:  뜨는 낱말이라 종전 문구 검사는 성공·실패를 못 가른다 — 그래서 이 행은 판정
    #:  술어가 없어 빨강이었다. `img_check=True` 가 ④를 글자 대신 그림으로 재게 한다
    #:  (`img[data-gx=snapshot]` 1개 · `naturalWidth>0` · 응답 200 image/jpeg).
    F("U3#3", "상황 사진 1장 보기", "u3", "/m/events/{event}", goto(),
      ("GET", r"/api/dsm/events/\d+/snapshot"),
      srv_reflect("/api/dsm/events/{event}", "snapshot_path"), ["사진", "스냅샷"],
      img_check=True),
    #: ★ [P-132] 「도착」이라는 단추도 **없다.** 다음 단계 단추의 이름은 서버가 주는
    #:  `allowed_next` 를 `advanceLabel()` 이 옮긴 셋뿐이다
    #:  (`severity.ts:143-145` 접수하기 · 조치 시작 · 종결하기 ·
    #:   `MobileEventDetail.tsx:449-460` 이 그 셋을 그린다).
    #:  종전 기대식의 「도착」은 [실측] 현장 회신 **본문**(「현장 도착, 연기 없음…」)을
    #:  잡아 눌렀다 — 글자를 누르고 호출 0건을 빨강으로 적은 자리다.
    F("U3#7", "현장 도착 보고", "u3", "/m/events/{event}",
      btn("접수하기|조치 시작|종결하기"),
      ("POST", r"/api/dsm/events/\d+/response"),
      srv_change("/api/dsm/events/{event}", "response_state"), ["접수", "조치", "종결"],
      revert=no_revert("접수 → 조치 → 종결은 **한쪽으로만 가는 전이**다. 같은 단추를 다시 누르면 원래로 오는 것이 아니라 한 걸음 더 간다 — 대상은 이번 회 씨앗 사건이다")),
    #: ★ [P-132] 단추 이름은 **「회신 보내기」**다 (`MobileEventDetail.tsx:484`).
    #:  그리고 이 단추는 글상자가 비면 `disabled` 다(같은 파일 481행) —
    #:  그래서 **글을 먼저 채운다**(`fill` 은 아래 드라이버가 한다).
    #:  바뀌는 칸은 `response_state` 가 아니라 **회신 건수**다:
    #:  `GET /api/dsm/events/{id}/field-replies` 가 그 목록을 낸다(`api.ts:51`).
    F("U3#9", "현장 상황 한 줄 보고", "u3", "/m/events/{event}", btn("회신 보내기"),
      ("POST", r"/api/dsm/events/\d+/field-reply"),
      srv_change("/api/dsm/events/{event}/field-replies", "replies"), ["회신", "현장"],
      fill="현장에서 본 것을 한 줄로 적습니다.",
      revert=no_revert("회신은 **덧붙이는 것**이고 지우는 문이 없다(있어도 쓰지 않는다 — 대장은 줄지 않는다). 대상은 이번 회 씨앗 사건이다")),
    F("U3#14", "해당 카메라 모바일 실시간", "u3", None, None, None, None, [],
      note="정본: 없음 — 구간 티켓은 계약 11조 잠김"),
    F("U3#16", "근무 외 알림 차단", "u3", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `/m/settings` · `PUT /api/dsm/me/notify-prefs` 200 → 재조회에 "
           "차단 시간대 반영 + 시험 발송이 실제 `deliveries` 행을 남기는 것(P-160 ③)을 "
           "적어 두었다 [조율자 실측 2026-09-18 · M4 실자료가 섰다]. 종전 주석 "
           "「채널 결정 대기」는 그 전 사실이다. 이 도구가 안 누르는 사유는 **시간대 "
           "입력이 두 걸음**(저장 → 재조회)이라 한 번 누름 창(4.5초)에 안 들어온다는 것이다"),
    F("U3#19", "내가 처리한 이벤트 목록", "u3", "/m/inbox", goto(),
      ("GET", r"/api/dsm/deliveries"),
      srv_reflect("/api/dsm/deliveries?limit=20&mine=true", "deliveries"),
      ["내가", "발송", "이력", "처리"]),

    # ── U4 · 재난안전과 담당 공무원 ──────────────────────────────────────
    F("U4#1", "주간 상황 요약", "u4", None, None, None, None, [],
      note=P190 + "온보딩 정본은 단추 `7일`(`EventList.tsx:223` `PERIODS.d7`)과 "
           "`GET /api/dsm/events?since=…` 200 을 적어 두었다(턴 U 추가). 종전 주석 "
           "「프리셋 넷에 7일이 빠져 있다」는 턴 T 이전 사실이다. 이 도구가 안 누르는 "
           "사유는 이 행을 U4(읽기 전용) 축으로 잡아 두었는데 목록 필터는 사람 축이 "
           "U1·U2 라, **누구로 누를지 정본이 아직 한 사람을 고르지 않았다**는 것이다"),
    #: ★ [P-132] `/report-template` 은 **인수 자산의 운송장 서식 화면**이고 부르는 문은
    #:  `/api/report-template/`(`services/API.ts:819`) 다 — `/api/dsm/reports` 가 아니다.
    #:  그리고 `POST /api/dsm/reports` 라는 문은 **저장소에 없다**
    #:  [실측 `backend/apps/dsm/api.py` 의 `@route.post` 전부 — 보고서 생성 문 0개].
    #:  U4 의 「보고서」 줄이 사이드바에 안 걸린 사유도 같다
    #:  (`features/nav/roleNav.ts:143` 「그리는 화면이 라우터에 없다」).
    #: ★★ [P-179 · 2026-09-18 턴 V · 차선 Q] **위 문단은 턴 U 이전 사실이다 — 정정한다.**
    #:  문도 화면도 **있다**: `POST /api/dsm/reports/runs`(`api_u24.py:408`) · 화면 `/dsm/reports`
    #:  (`Reports.tsx` 「이번 달 우리 센터」 카드 · `App.tsx:724`). 종전 문장이 「없다」고 적은
    #:  `POST /api/dsm/reports` 는 지금도 없지만, 그 주소가 아니었을 뿐이다.
    #:  ⚠ **그런데도 이 행은 선언된 회색으로 남긴다 — 사람이 눌러 끝나는 자리가 아니다.**
    #:    ① 이 행의 이름이 「**자동** 생성」이고, 자동본(`trigger=auto`)은 매월 1일 배치
    #:      `apps.dsm.monthly_report.run_monthly_all` 이 만든다. 화면의 「만들기」는 언제나
    #:      `trigger=manual` 이다(`api_u24.py` 머리말) — 그것을 눌러 초록을 적으면
    #:      **사람이 누른 것을 자동이라고 적는 것**이고 PRD §7.4 의 수가 거짓이 된다.
    #:    ② U4 는 읽기 전용 역할(`view_only_*`)이라 그 단추가 **403 이고 그것이 옳다**
    #:      (플랫폼 문지기 `read_only_role` · 턴 U V 실측 — 화면이 사람 말로 그것을 말한다).
    #:      여기에 단추를 선언하면 판정기는 「관문이 거절했다(403)」로 **빨강**을 적는다 —
    #:      제품이 옳게 막은 자리를 결함으로 파는 것이다.
    #:    ③ 사람이 눌러 끝나는 자리는 **U2#6**(만들기)과 **U4#7**(내려받기)이 잰다. 자동 행이
    #:      실제로 있는지는 U4#7 의 상태 재읽기(`?kind=monthly`)가 같은 회차에 증명한다.
    #:  → 정본 경로·문·화면은 적되 **●가 될 수 없는 행**으로 선언한다(U4#9 와 같은 모양).
    F("U4#5", "월간 보고서 자동 생성", "u4", None, None, None, None, [],
      note="[P-179 정정] 문도 화면도 **있다** — POST /api/dsm/reports/runs (api_u24.py:408) · "
           "/dsm/reports (Reports.tsx 「이번 달 우리 센터」). 그러나 **자동본은 사람이 누르지 않는다** — "
           "매월 1일 배치 monthly_report.run_monthly_all 이 trigger=auto 로 만들고, 화면의 「만들기」는 "
           "언제나 trigger=manual 이다. 게다가 읽기 전용 U4 의 그 단추는 403 이 옳다. "
           "이 행은 ●가 될 수 없다 — 사람이 눌러 끝나는 자리는 U2#6 · U4#7 이 잰다"),
    #: ★ [P-132] 서버가 내는 종이는 **하나**다 — `GET /api/dsm/events/{id}/report.pdf`
    #:  (`backend/apps/dsm/api.py:802` UX-30 사건 보고서 1쪽). 그런데 그 주소를 부르는
    #:  화면이 저장소에 **없다**(frontend 전체에 `report.pdf` 참조 0건).
    #:  종전 기대식이 가리키던 `/api/dsm/reports/{template_id}.pdf` 는 **운송장 서식**이다
    #:  (같은 파일 766행 · 그 표 19행은 전부 택배다 — 800행 주석).
    #: ★★ [P-179 · 2026-09-18 턴 V · 차선 Q] **위 문단은 턴 U 이전 사실이다 — 정정한다.**
    #:  서버가 내는 종이는 이제 **하나가 아니다**: `GET /api/dsm/reports/runs/{run_id}.docx`
    #:  (**정본** · 결정 ⑤ · HWP 가 연다 · `api_u24.py:439`)와 `.pdf`(병행 · `:445`)가 있고,
    #:  **`Reports.tsx` 가 그 둘을 부른다**(`features/dsm/api.ts:860,862`). 「프런트 참조 0건」은 끝났다.
    #:  ⚠ 누르는 자리가 **둘**이다: 만든 직후 상태 카드의 「DOCX 내려받기」(`Reports.tsx:207`)와
    #:    실행 목록 표 「파일」 열의 **「DOCX」**(`:296`). 읽기 전용 U4 는 만들 수 없으므로(403)
    #:    그 사람에게 서는 자리는 **표의 것**이다 — 그래서 `^DOCX$` 로 표의 단추를 정확히 집는다
    #:    (`DOCX 내려받기` 까지 같이 집히면 없는 자리를 눌렀다고 적히게 된다).
    #:  ⚠ 내려받기는 파일 응답이라 서버 상태가 안 바뀐다. 그래서 상태 칸은 **자동본이 있는가**를
    #:    다시 읽는다(`?kind=monthly`) — 그 수(`total`)는 화면이 「전체/실행 기록」에 그대로 적는다.
    #:    「받았다」의 증거는 술어 ④ 다: `Reports.tsx:130` 이 **받은 바이트 수**를 상태 칸에 적는다
    #:    (사라지는 토스트가 아니다 · 0바이트는 성공이 아니다).
    F("U4#7", "보고서 다운로드", "u4", "/dsm/reports", btn("^DOCX$"),
      ("GET", r"/api/dsm/reports/runs/\d+\.docx"),
      srv_reflect("/api/dsm/reports/runs?kind=monthly&limit=1", "total"),
      ["내려받았습니다", "바이트"],
      revert=no_revert("내려받기는 **읽기**다 — 서버에 남기는 것이 없다(파일은 누를 때마다 "
                       "실행 기록에서 다시 그린다 · 저장된 파일이 없다)"),
      note="[P-179 정정] 종전 정본 「서버 문은 report.pdf 하나 · 프런트 참조 0건」은 "
           "**턴 U 이전 사실**이다"),
    #: ★ [P-132] 「조회」라는 단추는 **없다.** P-120 이 기간을 `Segmented` 로 세웠고
    #:  그 칸의 이름은 `EventList.tsx:221` 의 **「7일」**이다(`period=d7` → `since`·`until`
    #:  두 끝을 그대로 보낸다 — 같은 파일 254-260행).
    F("U4#8", "특정 사건 이력 조회", "u4", "/dsm/events", btn("^7일$"),
      ("GET", r"/api/dsm/events\?.*(since|hours)"),
      srv_reflect("/api/dsm/events?limit=20", "events"), ["기간", "이벤트", "보고 있는 기간"]),
    #: ★ [P-132] 이 화면에 「영상」 **단추는 없다.** 있는 것은 표의 이름칸
    #:  `EventDetail.tsx:345` 「영상 구간」이고, 종전 기대식은 그 **글자**를 눌러
    #:  호출 0건을 빨강으로 적었다. 정본이 이미 「이 행은 ●가 될 수 없다」고 적어 둔
    #:  자리이므로(계약 11조 설계 잠금 · 영구) **선언된 회색**으로 옮긴다.
    F("U4#9", "증빙 영상 확인", "u4", None, None, None, None, [],
      note="정본: 추출은 계약 11조 설계 잠금(영구) — 이 행은 ●가 될 수 없다 · "
           "화면에 단추가 없다(EventDetail.tsx:345 는 표의 이름칸 「영상 구간」이다)"),
    #: ★ [P-132] `/device` 는 **드론·로봇 장비 등록** 화면이다(`App.tsx:769` 제목 그대로).
    #:  카메라 수를 **분모와 함께** 적는 자리는 `CameraAddress.tsx:134` 「카메라 {total}대」이고
    #:  그 수의 출처가 이미 이 행이 쓰던 `/api/dsm/cameras/address-gap` 이다.
    F("U4#11", "카메라 설치 현황", "u4", "/dsm/cameras/address", goto(),
      ("GET", r"/api/dsm/cameras/address-gap"),
      srv_reflect("/api/dsm/cameras/address-gap", "total"),
      ["카메라", "주소 있음", "주소 없음"]),
    #: ★★ [P-190 · 턴 W] **이 행은 U4 로 ● 가 될 수 없다 — U2 축에서 잰다.**
    #:  [실측 2026-09-19 · 차선 U24 · `tests/test_u24_law07_authz.py::U4CannotBeGreenOnUpperReportTest`]
    #:  U4 의 역할 코드는 글자 그대로 `view_only_-_anyang` 이고, 읽기 전용 관문
    #:  (`common/role_gate` P-119 / SEC-20)이 **쓰기 메서드 전부**를 막는다. 그래서
    #:  `POST /api/dsm/events/{id}/upper-report` 는 U4 로 **언제나 403** 이고, 그 403 은
    #:  **제품이 옳게 막은 자리**다 — 고칠 흠이 아니다. 같은 문을 U2(`fire_admin`)로 누르면
    #:  관문을 지나 핸들러가 돈다.
    #:  ⚠ **U4 계정으로 이 행을 다시 재지 않는다.** 다시 재면 또 403 이 나오고, 그 403 을
    #:   빨강으로 세면 제품이 옳게 한 일에 벌점을 주는 것이다(P-159 가 그렇게 쟀다).
    #:  ⚠ 읽기 전용에 열어 준 쓰기는 **열람 청구 면 둘**뿐이다(P-185 · 접수·회신).
    #:   `upper-report` 는 거기 없다 — 이 행을 초록으로 만들려고 관문을 넓히지 않는다.
    #:  그래서 이 도구는 이 행을 **안 누른다**: 이 파일의 U4 자리는 `gxseed_u4_official`
    #:  한 사람이고, 그 사람으로 누르면 언제나 403 이다. U2 축 측정은 온보딩 정본
    #:  (`onboarding_48.md` U4 15 · 턴 W 정정)이 든다.
    F("U4#15", "상급기관 제출 자료", "u4", None, None, None, None, [],
      note=P190 + "온보딩 정본은 [서버 기록] `POST /api/dsm/events/{id}/upper-report` 200"
           "(**U2** `gxseed_u2_manager`) → 재조회에서 그 행의 표시가 서버 값으로 `보고함` "
           "+ [화면 상태] `보고 표시`/`보고함` 두 말이 같은 화면에 동시에 있지 않을 것을 "
           "적어 두었다. 문과 문구는 **있다.** 이 도구가 안 누르는 사유는 이 파일의 U4 "
           "자리가 읽기 전용 계정이라 **언제나 403** 이고, 그 403 은 제품이 옳게 막은 "
           "자리이기 때문이다 — U2 축 측정은 온보딩 정본이 든다"),
    #: ★★ [P-179 · 2026-09-18 턴 V · 차선 Q] **「볼 자리가 없다」는 턴 U 이전 사실이다 — 정정한다.**
    #:  자리가 **섰다**: `/dsm/audit`(`features/dsm/pages/AuditLog.tsx` · `dsm/routes.u24.ts:41`)이
    #:  `GET /api/dsm/audit`(`api_u24.py:321`)를 읽는다. 읽는 사람은 U2·U4·U5 이고 U1·U3 은 403 이다
    #:  (`config/k3_roles.py` 한 곳 · U4 는 읽기 전용이지만 **읽기는 그 사람의 자리**다).
    #:  턴 V(파 3 턴 1)의 캡처가 이 화면을 200 으로 기록했다.
    #:  ⚠ 상태 칸은 화면이 적는 그 수를 그대로 다시 읽는다 — `AuditLog.tsx` 가
    #:    「전체 {total}건 · {page}/{pages}쪽」을 그리므로 `total` 이 **화면에 실재하는 수**다.
    #:  ⚠ 기대 문구에 「N.N초 · 60초 안」을 쓰지 않는다 — 그것은 `{n.toFixed(1)}` 틀 문장이라
    #:    글자가 매회 다르다(사전의 `${n}` 규약). 대신 그 칸의 **고정 글자**(「첫 응답」)를 쓴다.
    F("U4#16", "감사 대응 이력", "u4", "/dsm/audit", goto(),
      ("GET", r"/api/dsm/audit(\?|$)"),
      srv_reflect("/api/dsm/audit?page_size=1", "total"),
      ["감사 기록", "첫 응답", "표 내려받기"],
      note="[P-179 정정] 종전 정본 「감사는 쌓이는데 볼 자리가 없다」는 **턴 U 이전 사실**이다"),

    # ── U5 · 시스템 관리자 ───────────────────────────────────────────────
    #: ★ [P-132] `/users` 에 「추가」는 없다. 단추 이름은 `App.tsx:728` 의
    #:  **「사용자 추가」**이고, 그것을 누르면 `POST` 가 아니라 `/users/add-user`
    #:  **화면으로 간다**(`ListRealityNote.tsx:98-102` 의 `<Link>`). 계정은 그 다음
    #:  화면의 서식을 다 채워야 생긴다 — **한 번 누름으로 재는 정본이 없다.**
    #:  ⚠ 그 서식의 문은 지금 프리플라이트에서 끊긴다
    #:    [실측 턴 O · `docs/agent/evidence/P-125/users_roles_0행과_프리플라이트401.md`
    #:     A절 — `OPTIONS /api/v1/user/create-user` → 401 · `front_line.py:81`].
    #:    그 자리는 **보안 차선**이 들고 있다.
    F("U5#1", "사용자 계정 생성", "u5", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `/dsm/people` · `POST /api/dsm/settings/people/create` 200 → "
           "사용자 수 +1 을 적어 두었다(⚠ `/settings/people` 이 아니다 — `/settings/{domain}` 이 "
           "삼켜 405 를 낸다). 문은 **있다.** 이 도구가 안 누르는 사유는 둘이다: "
           "① 화면의 단추(App.tsx:728 「사용자 추가」)는 서식 화면으로 가는 링크라 "
           "한 번 누름으로 안 끝난다 · ② 그 문이 프리플라이트 401 로 끊겨 있다"
           "(P-125 A절 · 보안 차선). 둘 다 회색 사유이고 「정본이 비었다」가 아니다"),
    #: ★ [P-132] 이 행의 상태 규격이 **다른 화면**을 읽고 있었다
    #:  (`/api/dsm/dashboard/frame` 의 `preset` — 역할 화면과 아무 상관이 없다).
    #:  `/roles` 가 실제로 세는 문은 `App.tsx:754` 의 `countUrl="/api/roles/"` 이고,
    #:  그 수를 화면에 적는 자리가 `ListRealityNote.tsx:136`
    #:  「서버에는 역할 {n}개가 있습니다.」다(읽는 칸 이름은 `count` — 같은 파일 69행).
    F("U5#2", "역할 부여·변경", "u5", "/roles", goto(),
      ("GET", r"/api/roles"),
      srv_reflect("/api/roles/?page_size=1&current_page=1", "count"),
      ["역할", "서버에는"]),
    #: ★ [P-132] 카메라를 등록하는 자리는 `/device`(드론·로봇)가 아니라
    #:  **`/dsm/cameras/import`** 다 — `routes.ts:23` 이 그 경로를 정하고
    #:  `roleNav.ts:132` 가 그 줄을 U5 사이드바에 「카메라 등록」이라 세운다.
    #:  그런데 그 화면은 **일부러 세 걸음**이다(`CameraImport.tsx:186·199·204`
    #:  예시 채우기 → ② 표 먼저 보기(dry-run) → ③ 이 표대로 적용). 「표를 본 뒤에만
    #:  쓴다」가 그 화면의 규약이고, **한 번 누름**으로는 그 규약을 지나갈 수 없다.
    #:  게다가 같은 표를 두 번 적용하면 `unchanged` 라 총수가 안 변한다 — 잴 때마다
    #:  **새 시험 자료**가 있어야 하는데 그 정본이 없다(사건과 같은 문제다).
    F("U5#4", "카메라 등록", "u5", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `/dsm/cameras/import` · `POST /api/dsm/cameras/import` 200"
           "(dry-run 뒤 실행) → 카메라 수 +N 과 문구 `카메라 일괄 등록`·`표 먼저 보기` 를 "
           "적어 두었다. 문과 문구는 **있다.** 이 도구가 안 누르는 사유는 "
           "「표 먼저, 그 다음 적용」이 **세 걸음**이고 매번 새 시험 자료가 필요해 "
           "한 번 누름 창에 안 들어온다는 것이다 — 그리고 누르면 제품에 카메라가 남는다"),
    #: ★ [P-132] 「저장」이라는 단추는 없다 — `CameraAddress.tsx:177·185` 의
    #:  **「표 먼저 보기」 · 「채우기」** 둘뿐이고, 둘 다 이름·주소를 채우기 전에는
    #:  `disabled` 다(`ready`, 같은 파일 88행). 「채우기」는 표를 본 뒤에만 열린다(182행).
    #:  U5#4 와 같은 사유로 **한 번 누름의 정본이 없다.**
    F("U5#5", "카메라 설치 주소 입력", "u5", None, None, None, None, [],
      note=P190 + "온보딩 정본은 `POST /api/dsm/cameras/{id}/address` 200(`api_u56.py:506`) → "
           "`GET /api/dsm/cameras/address-gap` 반영과 문구 `이 한 대 채우기`"
           "(`CameraAddress.tsx:297`)를 적어 두었다. 문과 문구는 **있다.** 이 도구가 "
           "안 누르는 사유는 단추 둘(`표 먼저 보기`·`채우기`)이 **입력 전에는 잠겨 있고** "
           "「표 먼저, 그 다음 채움」이 두 걸음이라는 것이다(P-132 — 제품의 규율을 "
           "고장으로 팔지 않는다)"),
    #: ★ [턴 T · U56] 설정 화면(`/dsm/notify`)이 턴 S 에 섰고, 「끄기/켜기」 한 번 누름이
    #:  턴 T 에 생겼다(NotifySettings.tsx · `data-gx=notify-rule-saved`). 옛 note 「화면·라우트
    #:  없다」는 턴 S 이후 옛말이었다 — 정본 없음을 그대로 두면 영원히 회색이다.
    #:  ⚠ 심각 등급 행은 서버가 409 로 막는다(심각 0명 금지) — 정보/경고 행의 단추를 누른다.
    #: ★★ [턴 U · 차선 Q · 절 4] **되돌린다.** 턴 T 의 이 한 번 누름이 `NotificationRule`
    #:  pk 9(critical · fire_user)를 끈 채로 남겼고, `verify_seed_roles` 의 K2 수신자가
    #:  「닿는 사람 0명」으로 빨강이 됐다 [조율자 실측 2026-09-17 21:0x]. 잰 자리는
    #:  제품이 아니라 **우리가 남긴 상태**였다. 판정 뒤 같은 단추를 한 번 더 누른다.
    F("U5#9", "알림 규칙 설정", "u5", "/dsm/notify", btn("^(끄기|켜기)$"),
      ("POST", r"/api/dsm/settings/notify-rules/save"),
      srv_reflect("/api/dsm/settings/notify-rules/list", "rules"), ["저장했습니다", "규칙 #"],
      revert=revert_toggle()),
    F("U5#10", "알림 채널 설정", "u5", None, None, None, None, [],
      note=P190 + "온보딩 정본은 규칙 저장 200 → `channel` 값 `email`/`webpush` 가 "
           "`…/list` 에 남는 것을 적어 두었다. ⚠ 다만 채널 **이름** 자체(`이메일`·`웹푸시`)는 "
           "아직 사전 밖이고, 문자 채널은 대표 결정 대기다 — 그래서 정본은 제목으로 "
           "자리를 단언하고 채널 값은 서버 기록으로 잰다. 이 도구가 안 누르는 사유는 "
           "U5#9 이 같은 화면의 같은 단추를 이미 누르고 **되돌리기까지** 하기 때문이다 "
           "— 같은 상태를 두 번 흔들지 않는다"),
    F("U5#14", "시스템 상태 확인", "u5", "/dsm/system", goto(),
      ("GET", r"/api/dsm/(dashboard/link-state|ops/)"),
      srv_reflect("/api/dsm/dashboard/link-state", "status"), ["상태", "시스템", "연계"]),
    F("U5#15", "저장 용량 확인", "u5", "/dsm/system", goto(),
      ("GET", r"/api/dsm/ops/"),
      srv_reflect("/api/dsm/dashboard/link-state", "status"), ["용량", "저장", "GB"],
      note=P190 + "**종전 주석은 이제 거짓이다.** 「신호는 ops_monitor 안에만 있다 · "
           "읽는 문이 서 있지 않다」는 턴 V 이전 사실이었다. 차선 U56 이 이 턴에 "
           "`GET /api/dsm/ops/backup/declaration` 을 세우고 **눌러서 200 을 봤다**"
           "(익명 401 · 역할 0 403 · POST 405 · 화면에서 404 **0/11**). 온보딩 정본도 "
           "`GET /api/dsm/system/storage` 200(`api_u56.py:647` · `ops_tasks.py:1126` "
           "`storage_declaration()` 하나가 판정)을 적어 두었다. 이 행의 기대 호출은 "
           "그래서 `/api/dsm/ops/` 로 남긴다 — 화면(`/dsm/system`)이 그 아래를 부른다"),

    # ── U6 · 외부 연계 시스템(기계) ──────────────────────────────────────
    # 사람이 아니다. **면이 곧 API** 이므로 「누르는 것」은 HTTP 호출 자체다.
    F("U6#1", "API 키로 인증", "u6", None, api(),
      ("POST", r"/api/dsm/settings/api-keys"),
      srv_change("/api/dsm/settings/api_keys", "inbound"), ["key", "api_key"],
      note="읽는 자리는 `/settings/{domain}` 이고 domain 은 `api_keys` 다 (하이픈 아니다). "
           "★ [D-470 · 턴 R] 보는 칸이 `total` 이었는데 **그 응답에 그런 칸은 없다** — "
           "`services.setting_overview(domain='api_keys')` 가 내는 것은 "
           "outbound · inbound · inbound_api_type · inbound_capability · api_keys 다섯이다. "
           "없는 칸은 앞뒤가 늘 None 이라 `server_change` 가 「그대로다」로 읽었고, "
           "그래서 **제품이 고쳐진 뒤에도 빨강이었다**(POST 200 실측 · P-146 배선 확인). "
           "키를 발급하면 늘어나는 것은 들어오는 키 목록이므로 `inbound` 를 본다."),
    F("U6#2", "이벤트 목록 조회", "u6", None, api(),
      ("GET", r"/api/dsm/events(\?|$)"),
      srv_reflect("/api/dsm/events?limit=5", "events"), ["events", "total"]),
    F("U6#3", "이벤트 상세 조회", "u6", None, api(),
      ("GET", r"/api/dsm/events/\d+$"),
      srv_reflect("/api/dsm/events/{event}", "event_id"), ["event_id"]),
    F("U6#4", "이벤트 발생 웹훅 수신", "u6", None, api(),
      ("POST", r"/api/dsm/webhook-subscriptions"),
      srv_change("/api/dsm/webhook-subscriptions", "total"), ["subscription", "webhook"]),
    #: ★ [P-132] 기계에는 화면이 없고 **응답 본문이 곧 화면**이다. 그 본문이 쓰는 칸은
    #:  `from` · `to` · `audit_id` 이고(`api.py:445` 전이 응답) `response_state` 라는
    #:  낱말은 거기 **한 번도 안 나온다** — 값은 바뀌었는데 화면이 침묵한다고 적히던 자리다.
    F("U6#9", "이벤트 상태 갱신", "u6", None, api(),
      ("POST", r"/api/dsm/events/\d+/response"),
      srv_change("/api/dsm/events/{event}", "response_state"),
      ["audit_id", "\"to\""]),
    F("U6#12", "인증 실패 처리", "u6", None, api(),
      ("GET", r"/api/dsm/events(\?|$)"),
      {"kind": "status_is", "get": "/api/dsm/events?limit=1", "field": "401"},
      ["401", "unauthor", "인증"],
      note="자격 없이 부른다 — **진짜 4xx** 가 와야 한다. 200 봉투는 빨강"),
    F("U6#14", "스키마 버전 확인", "u6", None, None, None, None, [],
      note=P190 + "온보딩 정본은 **아무 응답에나 헤더 `X-GX-Schema` 1개**와 "
           "`backend/tests/test_u56_schema_header.py` 가 그것을 잠그는 것을 적어 두었다"
           "(턴 W · U56 축). 종전 주석 「스키마 버전」 한 낱말은 정본이 비었다는 뜻으로 "
           "읽혔다. 이 도구가 안 누르는 사유는 이 행의 술어가 **본문이 아니라 헤더**라 "
           "지금 네 칸(②기대 호출·③상태·④문구)이 헤더를 볼 자리가 없다는 것이다"),
    F("U6#15", "연계 헬스체크", "u6", None, api(),
      ("GET", r"/api/dsm/dashboard/link-state"),
      srv_reflect("/api/dsm/dashboard/link-state", "status"), ["status", "waiting", "ok"]),
)

FLOW_BY_KEY = dict((f["key"], f) for f in FLOWS)
PERSONAS = ("U1", "U2", "U3", "U4", "U5", "U6")


# ──────────────────────────────────────────────────────────────────────────
# 판정기 — **관측만 받는다.** 흐름 이름을 보고 봐주는 길이 없다 (D-327).
# ──────────────────────────────────────────────────────────────────────────
def _cell_control(o):
    c = o.get("control") or {}
    if not c.get("found"):
        return False, c.get("why") or "누를 자리를 못 찾았다"
    if not c.get("clicked"):
        return False, c.get("why") or "찾았는데 눌러 보지 못했다"
    return True, ""


def _cell_call(flow, o):
    want = flow.get("call")
    if not want:
        return False, "기대 호출이 선언되지 않았다"
    method, pat = want
    rx = re.compile(pat)
    for c in o.get("calls") or []:
        if (c.get("method") or "").upper() != method:
            continue
        url = c.get("url") or ""
        path = url.split("?")[0] if pat.endswith("$") else url
        if rx.search(path) or rx.search(url):
            return True, c
    return False, None


def server_gave_value(after) -> bool:
    """서버가 그 칸에 **무언가를 냈는가.** ★ **`0` 은 값이다.**

    ⚠ [실측 2026-09-20 · 턴 X] 이 판정기는 `after in (None, "", [], {}, 0)` 으로 물었고,
      그래서 **서버가 정직하게 낸 `0` 을 「아무것도 안 냈다」로 읽었다.**
      그 한 줄이 `U1#19`·`U2#1`·`U2#2` 세 행을 빨강으로 만들었다 — 그런데 화면은
      **「미처리 0건」이라고 옳게 그리고 있었고** 관측 본문에 그 글자가 있었다.
      즉 **제품이 아니라 판정기가 틀렸다.**

    ★ 이 저장소가 세 턴째 같은 말을 하고 있다 — 「분모 0인 초록은 초록이 아니다」 ·
      「0은 원인이 아니라 질문이다」. 그 말의 뒷면이 이것이다: **0을 「없음」으로 접으면
      「0건이라고 옳게 말한 화면」과 「아무 말도 안 한 화면」이 같은 칸에 들어간다.**

    가르는 선: **없는 것**(`None` · 빈 문자열 · 빈 목록 · 빈 표)과 **0인 것**은 다르다.
      `bool` 은 값으로 센다 — `False` 도 서버가 낸 답이다.
    """
    if after is None:
        return False
    if isinstance(after, (int, float, bool)):
        return True                      # ← 0 · 0.0 · False 는 **낸 값**이다
    if isinstance(after, str):
        return after.strip() != ""
    if isinstance(after, (list, dict, tuple, set)):
        return len(after) > 0
    return True


def _cell_state(o):
    s = o.get("state") or {}
    kind = s.get("kind")
    if not kind:
        return None, "상태 규격이 없다"
    if s.get("error"):
        return None, "다시 읽지 못했다: %s" % s["error"]
    if kind == "server_change":
        before, after = s.get("before"), s.get("after")
        #: ★★ **「없음 → 값」은 「변했다」가 아니다 — 「변했는지 모른다」다.**
        #:   [실측 2026-09-20 · 턴 X · V 가 자진 신고] `U3#1` 이 `total` **None → 12** 로
        #:   **초록**이었다. 이 술어는 「누른 뒤 값이 **변했는가**」인데, `before` 가 `None` 이면
        #:   **처음 읽기가 실패한 것**과 **원래 없던 것**이 같은 글자다. 둘 다 「눌러서 변했다」의
        #:   증거가 못 된다 — 누르기 전에 무엇이었는지를 모르기 때문이다.
        #:   ★ 이것은 같은 턴에 고친 병(「`0` 을 **없음**으로 접었다」)의 **거울상**이다:
        #:     이번엔 **「없음을 값으로 폈다」**. 한 판정기 안에 두 방향이 같이 있었다.
        #:   ⇒ **회색**이다(빨강이 아니다 — 「안 변했다」고 말할 근거도 없다).
        #:     회색은 초록이 아니므로 이 자리는 더 이상 점수를 벌지 않는다.
        #: ⚠ **첫 판은 너무 넓었다** [V 가 비용을 청구했다 · 같은 턴에 정정].
        #:   `before is None` 을 전부 회색으로 했더니 `U1#11`(`verdict` **None → 'confirmed'**)
        #:   이 초록에서 회색으로 떨어졌다. 그런데 `verdict` 의 `None` 은 **읽기 실패가 아니라
        #:   「아직 판정 안 함」이라는 뜻 있는 값**이고, **읽기 실패는 이미 위의 `error` 갈래가
        #:   잡는다.** 아마도 참인 초록 하나를 잃은 것이다.
        #: ★ 가르는 선: **세는 수**와 **갈래값**은 다르다.
        #:   · `total` 처럼 **수**가 없었다가 12 가 된 것 → 「눌러서 **늘었다**」의 증거가 못 된다.
        #:     누르기 전의 수를 모르면 **얼마나 늘었는지**를 말할 수 없다. → 회색.
        #:   · `verdict` 처럼 **갈래**가 null → 'confirmed' 인 것 → **그 자체가 전이**다. → 초록.
        if before is None and isinstance(after, (int, float)) \
                and not isinstance(after, bool):
            return None, ("누르기 **전** `%s` 의 수를 모른다(`None`) — 「없음 → %r」은 "
                          "**늘었다의 증거가 아니다**. 세는 수는 앞을 알아야 뒤를 잰다"
                          % (s.get("field"), after))
        if before == after:
            return False, "다시 읽었는데 `%s` 가 그대로다 (%r)" % (s.get("field"), before)
        return True, "`%s` %r → %r" % (s.get("field"), before, after)
    if kind == "server_reflect":
        after = s.get("after")
        if not server_gave_value(after):
            return False, "서버가 `%s` 에 아무것도 안 냈다" % s.get("field")
        if not s.get("on_screen"):
            return False, "서버는 `%s`=%r 를 내는데 **화면에 없다**" % (s.get("field"), after)
        return True, "`%s`=%r 가 화면에 있다" % (s.get("field"), after)
    if kind == "route_change":
        if (s.get("after") or "") == (s.get("before") or ""):
            return False, "주소가 그대로다 (%s)" % s.get("after")
        return True, "%s → %s" % (s.get("before"), s.get("after"))
    if kind == "status_is":
        want, got = str(s.get("field")), str(s.get("after"))
        if want != got:
            return False, "상태코드 %s 를 기대했는데 %s 였다" % (want, got)
        return True, "상태코드 %s" % got
    return None, "모르는 상태 규격 %r" % kind


def _cell_text(flow, o):
    want = flow.get("text") or []
    if not want:
        return None, "기대 문구가 없다"
    seen = o.get("text_after") or ""
    hit = [w for w in want if w.lower() in seen.lower()]
    if hit:
        return True, "「%s」" % hit[0]
    return False, "기대한 말(%s) 중 아무것도 화면에 없다" % " · ".join(want)


def _cell_img(o):
    """P-148 사진 술어 — 술어 ④「화면이 말한다」를 **글자 대신 그림**으로 잰다.

    「사진」·「스냅샷」이라는 표제는 실패 화면에도 뜨는 낱말이라 `_cell_text` 로는
    성공·실패를 못 가른다. 그래서 셋을 본다 — 셋이 다 서야 초록이다:
        ① `img[data-gx=snapshot]` 가 **1개** 있다 (0 = 안 그렸다 · 2+ = 중복 태그)
        ② 그 이미지의 `naturalWidth > 0` 이다 (태그는 있는데 그림이 안 채워진 것과 가른다)
        ③ 그 이미지가 받은 응답이 `200 image/jpeg` 다 (다른 상태·형식은 성공이 아니다)
    ★ 반증 한 줄 — 셋이 다 섰는데 화면이 그래도 「불러오지 못했습니다」라고 말하면
      그 자체가 모순이다(그 문구는 실제 4xx/5xx 일 때만 나와야 한다). 그 모순을 초록으로
      내보내지 않는다.
    """
    img = o.get("img") or {}
    n = img.get("count")
    if n != 1:
        return False, "img[data-gx=snapshot] 가 %r개다 (1개여야 한다)" % n
    if not img.get("natural_width"):
        return False, "naturalWidth 가 0이다 — 태그는 있는데 그림이 안 채워졌다"
    resp = img.get("response") or {}
    status, ctype = resp.get("status"), resp.get("content_type") or ""
    if status != 200 or "image/jpeg" not in ctype:
        return False, ("사진 응답이 200 image/jpeg 가 아니다 (status=%r content-type=%r)"
                        % (status, resp.get("content_type")))
    if "불러오지 못했습니다" in (o.get("text_after") or ""):
        return False, "셋이 다 섰는데 화면이 그래도 「불러오지 못했습니다」라고 말한다 — 모순"
    return True, "img 1개 · naturalWidth=%s · 200 image/jpeg" % img.get("natural_width")


def judge_one(flow, o):
    """한 흐름 → (색, 한 줄, 네 칸). **관측이 없으면 회색이다 — 0 이 아니라 회색.**"""
    cells = {"control": None, "call": None, "state": None, "text": None}
    if not o:
        return GREY, "재지 않았다 — 관측이 없다", cells

    ok_c, why_c = _cell_control(o)
    cells["control"] = ok_c
    if not ok_c:
        # ★ 회색이다. **빨강이 아니다.** 누를 것이 없으면 「안 된다」를 못 쟀다.
        return GREY, why_c, cells

    fired, call = _cell_call(flow, o)
    cells["call"] = fired
    if not flow.get("call"):
        # ★ [P-132] 표가 「누를 자리 없음」이라 적은 행인데 관측은 눌렀다고 말한다 —
        #   **증거가 표보다 낡았다.** 그것은 빨강이 아니라 회색이다(못 잰 것이다).
        #   종전에는 이 자리에서 판정기가 통째로 죽었다(`flow["call"][0]` · TypeError).
        return GREY, "표에 없는 자리를 관측이 눌렀다 — 증거가 표보다 낡았다 (다시 재라)", cells
    if not fired:
        # ★★ 2026-09-08 의 그 모양 — 눌렀는데 **아무것도 나가지 않았다**
        n = len(o.get("calls") or [])
        return RED, ("눌렀는데 `%s %s` 가 나가지 않았다 (그 사이 나간 호출 %d건)"
                     % (flow["call"][0], flow["call"][1], n)), cells

    status = call.get("status") if isinstance(call, dict) else None
    if status in (401, 403) and (o.get("state") or {}).get("kind") != "status_is":
        return RED, "관문이 거절했다 — %s (권한)" % status, cells

    ok_s, why_s = _cell_state(o)
    cells["state"] = ok_s
    if ok_s is None:
        return GREY, "상태를 다시 읽지 못했다 — %s" % why_s, cells
    if not ok_s:
        # ★★ **이 턴 결함의 가족** — 요청은 나갔는데 값이 안 바뀌었다
        return RED, "요청은 나갔는데 %s" % why_s, cells

    if flow.get("img_check"):
        # [P-148] 이 행은 글자가 아니라 그림으로 「화면이 말한다」를 잰다.
        ok_t, why_t = _cell_img(o)
    else:
        ok_t, why_t = _cell_text(flow, o)
    cells["text"] = ok_t
    if ok_t is None:
        return GREY, "기대 문구가 선언되지 않았다", cells
    if not ok_t:
        # 성공했는데 화면이 침묵한다 → 사용자는 실패로 읽고 다시 누른다
        return RED, "값은 바뀌었는데 화면이 말하지 않는다 — %s" % why_t, cells

    return GREEN, "%s · %s · %s" % (why_s, why_t, "눌렀고 나갔다"), cells


def judge(observations):
    """48행 전부에 대해 (key, 색, 한 줄, 칸). **분모는 언제나 48 이다.**"""
    rows = []
    for flow in FLOWS:
        o = (observations or {}).get(flow["key"])
        color, why, cells = judge_one(flow, o)
        rows.append((flow["key"], color, why, cells, flow))
    return rows


def score(rows):
    g = sum(1 for _, c, _, _, _ in rows if c == GREEN)
    r = sum(1 for _, c, _, _, _ in rows if c == RED)
    y = sum(1 for _, c, _, _, _ in rows if c == GREY)
    return g, r, y


# ──────────────────────────────────────────────────────────────────────────
# 자기시험 — 양성 대조 · 변이 · **출생 표본** · 관측 0건 · 면제 칸 없음
# ──────────────────────────────────────────────────────────────────────────
def sample_url(pat):
    """기대 호출 정규식 → **그 식이 실제로 받아들이는 URL 한 개.**

    양성 대조의 재료이자, 식 자체의 오타를 잡는 자다 — 만들어 낸 URL 이 자기 식에
    안 걸리면 그 식은 **살아 있는 브라우저의 URL 도 못 걸린다**(자기시험 ①-b).
    """
    s = pat
    s = s.replace(r"\d+", "1")
    for _ in range(8):                       # 안쪽 괄호부터 하나씩 편다
        m = re.search(r"\(([^()]*)\)\??", s)
        if not m:
            break
        s = s[:m.start()] + m.group(1).split("|")[0] + s[m.end():]
    s = s.replace(".*", "").replace("$", "").replace("^", "")
    return s.replace(r"\.", ".").replace(r"\?", "?")


def _good(flow):
    """넷이 다 선 관측 하나. 양성 대조의 재료다."""
    st = dict(flow["state"] or {})
    k = st.get("kind")
    if k == "server_change":
        st.update(before="occurred", after="acknowledged")
    elif k == "server_reflect":
        st.update(after="42", on_screen=True)
    elif k == "route_change":
        st.update({"before": "/login", "after": "/dsm/dashboard"})
    elif k == "status_is":
        st.update(after=st.get("field"))
    method, pat = flow["call"]
    sample = "http://localhost:8000" + sample_url(pat)
    out = {
        "control": {"found": True, "clicked": True, "name": "x"},
        "calls": [{"method": method, "url": sample, "status": 200}],
        "state": st,
        "text_after": " ".join(flow["text"]) if flow["text"] else "",
    }
    if flow.get("img_check"):
        # [P-148] 셋이 다 선 사진 관측 — 양성 대조의 재료.
        out["img"] = {"count": 1, "natural_width": 640,
                      "response": {"status": 200, "content_type": "image/jpeg"}}
    return out


def _all_good():
    return dict((f["key"], _good(f)) for f in FLOWS if f["control"] and f["call"])


#: ★★ **출생 표본** — 2026-09-08 CR-USER 가 손으로 잰 그 세 줄.
#:  전부 **빨강**이어야 한다. 그날의 채점표는 이 자리에 **0.5 「그려졌다」**를 줬다.
def BIRTH_SAMPLE():
    dead = {
        "U1#11": ("실제로 판정", "/dsm/events/4813", "verdict", None),
        "U2#3": ("되돌리기", "/dsm/events/4808", "verdict", "confirmed"),
        "U3#9": ("회신", "/m/events/4804", "response_state", "in_progress"),
    }
    out = {}
    for key, (label, where, field, val) in dead.items():
        out[key] = {
            "control": {"found": True, "clicked": True, "name": label, "where": where,
                        "dom": "disabled=false, pointer-events=auto, opacity=1"},
            "calls": [],                      # ← **0건.** 그것이 그날의 사실이다
            "state": dict(FLOW_BY_KEY[key]["state"], before=val, after=val),
            "text_after": "미판정",           # 확인창 0 · 토스트 0
        }
    return out


def _no_exception_slot():
    """★ D-327 — **면제 칸이 자라지 않게 한다.**

    누군가 「알려진 정상」 목록을 이 파일에 들이면 그 순간 이 게이트는 손으로 쓴
    초록을 내기 시작한다. 그래서 **자기 소스를 훑는다.**
    """
    src = Path(__file__).read_text(encoding="utf-8")
    banned = ("KNOWN_GOOD", "EXPECTED_GREY", "WAIVER", "ALLOWLIST", "EXEMPT",
              "SKIP_FLOWS", "IGNORE_FLOWS", "면제 목록")
    hits = [b for b in banned if re.search(r"^\s*%s\s*=" % b, src, re.M)]
    # 판정기가 흐름 이름을 보고 갈라지는가 — `judge_one` 안에 키 문자열이 있으면 안 된다
    body = src.split("def judge_one(")[1].split("\ndef ")[0]
    keyed = [k for k in FLOW_BY_KEY if '"%s"' % k in body or "'%s'" % k in body]
    return hits, keyed


#: ★★ [P-190 · 턴 W · 차선 Q] **두 도구가 같은 행에 다른 정본을 들면 빨강이다.**
#:
#: 이 저장소에는 48행을 드는 도구가 **둘**이다 — 이 파일(FC · 「누른 뒤」)과
#: `measure_onboarding_t.py`(온보딩 · 「문구 + 셋째 술어」). 둘은 **다른 것을 재도 된다.**
#: 재는 축이 다른 것은 흠이 아니다. 흠은 **같은 행에 대해 서로 다른 사실을 말하는 것**이다.
#:
#: [실물 표본 2026-09-19 · 턴 W · U56 실측] `U5#15 저장 용량 확인`
#:   이 파일의 주석: 「신호는 ops_monitor 안에만 있다 — 읽는 라우트가 없다」
#:   온보딩 정본:    `GET /api/dsm/system/storage` **200** (`api_u56.py:647`)
#:   U56 이 이 턴에 그 문을 세우고 **눌러서 200 을 봤다.** 두 정본 중 하나는 거짓이고,
#:   어느 쪽이 거짓인지는 **아무 도구도 묻지 않았다.**
#:
#: 그래서 술어 하나를 세운다:
#:   **이 파일이 어떤 행을 「정본 없음」이라 적었는데, 온보딩 정본이 그 행에
#:   잴 것(`[API 호출]`·`[서버 기록]`·`[화면 상태]`)을 적어 두었으면 빨강.**
#: 그 반대(이 파일은 정본이 있다는데 온보딩 정본은 없다)도 같은 빨강이다.
#:
#: ⚠ **「이 도구가 그 자리를 안 누른다」는 빨강이 아니다.** 그것은 도구의 한계이고
#:   회색이다. 다투는 것은 **사실**이지 능력이 아니다 — 둘을 섞으면 이 술어가 소음이 된다.
#: ⚠ 정본 문서를 못 읽으면 **회색**이다(빨강이 아니다). 문서가 없다고 두 정본이
#:   갈렸다고 말할 수는 없다.
CANON_DOC = ROOT / "docs" / "agent" / "onboarding_48.md"
CANON_MARK = "## ★ 2026-09-17 턴 T · P-159 ①"

#: 온보딩 정본의 셋째 술어 칸이 **잴 것을 적었다**고 볼 표식.
_CANON_MEASURES = re.compile(r"\[(API 호출|서버 기록|화면 상태|실측)")
#: ★ 정본이 **제 입으로 「못 잰다」**고 적은 칸. 술어를 적어 두고도 「이 행은 회색」이라
#:   덧붙인 자리가 있다(U1#4 의 「문구 정본이 없으므로 이 행은 회색」 · U3#14 의 「(회색 ·
#:   잠금 — 재지 않는다)」). 그런 칸을 「잴 것이 있다」로 읽으면 **정본이 회색이라 적은 행을
#:   이 술어가 빨강으로 몰게 된다** — 그것은 다툼이 아니라 같은 말이다.
#: ⚠ 「U4 로 ● 가 될 수 없다」는 여기 넣지 않는다. 그것은 **축을 옮기라는 말**이지
#:   못 잰다는 말이 아니다(U4#15 · U24 턴 W 실측 — U2 축에서 잰다).
#: ⚠ 「재지 않는다」 한 낱말만으로는 회색이 아니다 — U24 의 U4#15 정정 문안이
#:   「**U4 계정으로** 이 행을 다시 재지 않는다」고 적으면서 같은 칸에 U2 축 술어를
#:   못 박았다. 낱말이 아니라 **회색 선언**을 본다.
_CANON_SAYS_GREY = re.compile(r"이 행은 회색|\(회색")
#: 이 파일의 `note` 가 그 행에 **정본이 없다**고 말하는 모양.
_NOTE_SAYS_NONE = re.compile(
    r"정본 없음|정본: 없음|라우트가 없다|화면이 없다|문도 아직 없다|"
    r"누를 자리가 없다|집계 면 없다|세는 자리가 없다|조회 라우트·화면 없다")
#: ★ 「종전 정본은 틀렸다」고 **정정하는 주석**은 「없다」는 낱말을 나르지만 주장이 아니다.
#:   정정문을 빨강으로 세면 정정한 사람이 벌을 받는다 — 그러면 아무도 정정을 안 적는다.
_NOTE_IS_CORRECTION = re.compile(r"정정\]|이전 사실|종전 정본")


def canon_cells(path=None) -> dict:
    """온보딩 정본에서 행 → 표 칸들. 못 읽으면 빈 칸(회색)이다 — 지어내지 않는다."""
    p = Path(path) if path else CANON_DOC
    try:
        doc = p.read_text(encoding="utf-8")      # P-189 — errors 없음
    except OSError:
        return {}
    if CANON_MARK not in doc:
        return {}
    who, cells = None, {}
    for line in doc.split(CANON_MARK)[1].splitlines():
        m = re.match(r"#{3,4} (U\d)", line)
        if m:
            who = m.group(1)
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 4 and re.fullmatch(r"(U\d )?\d+", c[0]):
            key = c[0] if " " in c[0] else "%s %s" % (who, c[0])
            cells[key.replace(" ", "#")] = c        # 뒤에 오는 표가 앞을 덮는다(최신 정정이 이긴다)
    return cells


def canon_disagreements(path=None):
    """(행, 이 파일이 말하는 것, 온보딩 정본이 말하는 것) — 갈린 행만."""
    cells = canon_cells(path)
    if not cells:
        return None
    out = []
    for f in FLOWS:
        c = cells.get(f["key"])
        if not c:
            continue
        last, note = c[-1], (f.get("note") or "")
        #: **양쪽이 다 적극적으로 말할 때만** 다툼이다. 한쪽의 침묵은 주장이 아니다.
        canon_none = "정본 없음" in last
        canon_has = (bool(_CANON_MEASURES.search(last)) and not canon_none
                     and not _CANON_SAYS_GREY.search(last))
        fc_none = (bool(_NOTE_SAYS_NONE.search(note))
                   and not _NOTE_IS_CORRECTION.search(note))
        #: 이 파일이 「문이 있다」고 **적극적으로** 말하는 모양 = 기대 호출을 못 박은 것.
        #: ⚠ `control` 이 선언된 것만으로는 주장이 아니다 — 못 찾으면 **이름을 적고 회색**을
        #:   내려고 일부러 적어 둔 자리가 있다(U2#3 「되돌리기 (사유 필수)」).
        fc_has = bool(f.get("call")) and not fc_none
        if fc_none and canon_has:
            out.append((f["key"], "「정본 없음」 — %s" % note[:90],
                        "잴 것이 적혀 있다 — %s" % last[:90]))
        elif fc_has and canon_none:
            out.append((f["key"], "기대 호출 `%s %s` 를 못 박았다" % f["call"],
                        "「정본 없음」 — %s" % last[:90]))
    return out


def canon_compare_census(path=None):
    """**무엇을 실제로 대 봤는가.** 분모를 손으로 적지 않는다 (D-327 · 턴 X 2차 회귀).

    「갈린 행 0」은 두 길로 난다 — ① 정말 둘이 같다 ② **갈릴 수 있는 행이 하나도 없다.**
    턴 W 에 술어를 좁히고(`_CANON_SAYS_GREY` · `_NOTE_IS_CORRECTION`) 정본 11행을
    정정한 뒤, 턴 X 실측은 **②**였다: `canon_none` **0행**(정정으로 사라졌다) ·
    `fc_none` 2행은 둘 다 정본이 제 입으로 「회색」이라 적은 행이라 다툼이 못 된다
    → **갈릴 수 있는 행 0.** 그런데 출력은 「48행에 같은 정본」이라 적고 있었다.
    48 은 **대 본 수가 아니라 표의 행 수**다 — 그 글자가 거짓말이었다.

    그래서 센다. 갈릴 수 있는 행이 0이면 살아 있는 데이터로는 이 술어가 **빨개질 수
    없다**; 그때 이 술어를 살려 두는 것은 `_p190_canon_cases()` 의 **출생 표본**뿐이고,
    출력이 그렇게 말해야 한다. 말하지 않으면 술어가 죽은 날에도 초록이 나온다.
    """
    cells = canon_cells(path)
    if not cells:
        return None
    n = dict(rows=0, canon_has=0, canon_none=0, canon_grey=0,
             fc_has=0, fc_none=0, both_say=0, capable=0)
    for f in FLOWS:
        c = cells.get(f["key"])
        if not c:
            continue
        last, note = c[-1], (f.get("note") or "")
        n["rows"] += 1
        canon_none = "정본 없음" in last
        canon_grey = bool(_CANON_SAYS_GREY.search(last)) and not canon_none
        canon_has = (bool(_CANON_MEASURES.search(last)) and not canon_none
                     and not canon_grey)
        fc_none = (bool(_NOTE_SAYS_NONE.search(note))
                   and not _NOTE_IS_CORRECTION.search(note))
        fc_has = bool(f.get("call")) and not fc_none
        n["canon_has"] += canon_has
        n["canon_none"] += canon_none
        n["canon_grey"] += canon_grey
        n["fc_has"] += fc_has
        n["fc_none"] += fc_none
        n["both_say"] += bool((canon_has or canon_none) and (fc_has or fc_none))
        #: 갈릴 **수 있는** 행 = 다툼 두 갈래 중 하나가 성립할 수 있는 자리
        n["capable"] += bool((fc_none and canon_has) or (fc_has and canon_none))
    return n


def self_test() -> int:
    ok = True

    # ── ★ 출생 표본 — **`0` 은 값이다** (턴 X · D-507) ─────────────────────
    #   [실측 2026-09-20] 차선 Q 가 찾았다: 이 판정기가 `after in (None,"",[],{},0)` 으로
    #   물어서, 서버가 정직하게 낸 **`0` 을 「아무것도 안 냈다」로 읽었다.**
    #   그 한 줄이 `U1#19`·`U2#1`·`U2#2` 세 행을 빨강으로 만들었는데, 화면은
    #   **「미처리 0건」이라 옳게 그리고 있었다**(관측 본문에 그 글자가 있었다).
    #   ⚠ **음성 대조를 같이 둔다** — 이 고침이 「전부 값이다」로 미끄러지면
    #     정말로 아무것도 안 낸 칸까지 초록이 되고, 그게 이 판정기의 죽음이다.
    _VALUE_SAMPLE = [
        (0, True, "★ 서버가 낸 **0** — 「미처리 0건」은 답이지 침묵이 아니다"),
        (0.0, True, "0.0 도 같다"),
        (False, True, "`False` 도 서버가 낸 답이다"),
        (4, True, "평범한 값"),
        ("0", True, "문자열 0"),
        ("서울시 강남구", True, "글자"),
        ([1], True, "비지 않은 목록"),
        (None, False, "**없다** — 칸 자체가 안 왔다"),
        ("", False, "빈 문자열"),
        ("   ", False, "공백뿐"),
        ([], False, "빈 목록"),
        ({}, False, "빈 표"),
    ]
    zbad = [(v, why) for v, want, why in _VALUE_SAMPLE
            if server_gave_value(v) is not want]
    if zbad:
        ok = False
        print("%s X ★ 출생 표본(0은 값이다)이 깨졌다: %s" % (TAG, zbad[:4]))
    else:
        print("%s O ★ **출생 표본 %d — 「0 은 값이다」**(양성 %d · 음성 %d · "
              "`0`·`0.0`·`False` 가 값이고 `None`·빈 것은 아니다)"
              % (TAG, len(_VALUE_SAMPLE),
                 sum(1 for _, w, _ in _VALUE_SAMPLE if w),
                 sum(1 for _, w, _ in _VALUE_SAMPLE if not w)))

    # ── ★ 출생 표본 — **「없음 → 값」은 변했다가 아니다** (턴 X · V 가 자진 신고) ──
    #   [실측 2026-09-20] `U3#1` 이 `total` **None → 12** 로 **초록**이었다.
    #   같은 턴에 고친 병(「`0` 을 없음으로 접었다」)의 **거울상** — 「없음을 값으로 폈다」.
    #   ⚠ 음성 대조를 같이 둔다: 진짜 변화는 **여전히 초록**이고, 안 변한 것은 **여전히 빨강**이다.
    _CHANGE_SAMPLE = [
        ({"kind": "server_change", "field": "total", "before": None, "after": 12},
         None, "★ **세는 수가 없음 → 12** — 앞을 모르니 늘었다고 못 한다 · 회색"),
        ({"kind": "server_change", "field": "verdict", "before": None,
          "after": "confirmed"},
         True, "★ **갈래값이 null → 'confirmed'** — 그 자체가 전이다 · 초록 "
               "(V 가 비용을 청구해 같은 턴에 되찾은 자리)"),
        ({"kind": "server_change", "field": "x", "before": None, "after": True},
         True, "null → True — bool 은 갈래값이다 · 초록"),
        ({"kind": "server_change", "field": "total", "before": 4, "after": 8},
         True, "4 → 8 — 진짜 변화 · 초록"),
        ({"kind": "server_change", "field": "total", "before": 0, "after": 1},
         True, "**0 → 1** — 0 은 읽은 값이다 · 초록"),
        ({"kind": "server_change", "field": "total", "before": 13, "after": 13},
         False, "13 → 13 — 안 변했다 · 빨강"),
        ({"kind": "server_change", "field": "total", "before": 0, "after": 0},
         False, "0 → 0 — 안 변했다 · 빨강"),
    ]
    cbad = [why for st, want, why in _CHANGE_SAMPLE
            if _cell_state({"state": st})[0] is not want]
    if cbad:
        ok = False
        print("%s X ★ 출생 표본(없음 → 값)이 깨졌다: %s" % (TAG, cbad[:3]))
    else:
        print("%s O ★ **출생 표본 %d — 「없음 → 값」은 회색**(변했는지 모른다) · "
              "진짜 변화는 초록 · 안 변한 것은 빨강 · **`0` 은 읽은 값이다**"
              % (TAG, len(_CHANGE_SAMPLE)))

    # ── ★ 출생 표본 — **드라이버는 딴 프로세스다** (턴 X · 조율자가 여기서 부쉈다) ──
    #   [실측 2026-09-20] 조율자가 `server_gave_value(a)` 를 `DRIVER` 문자열 **안**에 써 넣었다.
    #   그 문자열은 `/tmp/p118_driver.py` 로 따로 도는 프로세스라 바깥 모듈의 이름이 없고,
    #   **`NameError` 로 48행 중 39행이 회색**이 됐다. 그런데 **이 자기시험은 초록이었다** —
    #   자기시험은 바깥 모듈만 돌기 때문이다. **측정할 때만 죽는 결함**이었다.
    #   ⇒ 이제 자기시험이 **심은 뒤의 드라이버 원문**을 읽어, 부르는데 정의가 없는 이름을 잡는다.
    try:
        import ast
        import builtins
        import inspect as _inspect
        _src = DRIVER.replace(_DRIVER_SLOT,
                              _inspect.getsource(server_gave_value))
        _tree = ast.parse(_src)
        _known = set(dir(builtins))
        for _n in ast.walk(_tree):
            if isinstance(_n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                _known.add(_n.name)
            elif isinstance(_n, ast.Name) and isinstance(_n.ctx, ast.Store):
                _known.add(_n.id)
            elif isinstance(_n, (ast.Import, ast.ImportFrom)):
                for _a in _n.names:
                    _known.add((_a.asname or _a.name).split(".")[0])
            elif isinstance(_n, ast.arg):
                _known.add(_n.arg)
        _called = {_n.func.id for _n in ast.walk(_tree)
                   if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Name)}
        _orphan = sorted(_called - _known)
        if _orphan:
            ok = False
            print("%s X ★ **드라이버가 제 안에 없는 이름을 부른다**: %s — "
                  "`DRIVER` 는 딴 프로세스다. 바깥 모듈의 함수를 그냥 쓰면 "
                  "자기시험은 초록인 채 **측정만 죽는다** (턴 X)" % (TAG, _orphan[:6]))
        else:
            print("%s O ★ **출생 표본 — 드라이버가 부르는 이름 %d개가 전부 제 안에 있다** "
                  "(공용 술어는 원문을 심어 넣는다 · 한 벌을 더 만들지 않는다)"
                  % (TAG, len(_called)))
    except Exception as _e:                                  # noqa: BLE001
        ok = False
        print("%s X 드라이버 이름 검사를 못 돌렸다: %r" % (TAG, _e))

    # ① 양성 대조 — 넷이 다 선 관측은 초록이다
    rows = judge(_all_good())
    good_keys = set(_all_good())
    bad = [k for k, c, w, _, _ in rows if k in good_keys and c != GREEN]
    if bad:
        ok = False
        print("%s X 넷이 다 선 관측을 초록으로 못 읽는다: %s" % (TAG, bad[:6]))
    else:
        print("%s O 양성 대조 %d/%d 초록 (네 칸이 다 선 관측)" % (TAG, len(good_keys), len(good_keys)))

    # ①-b 기대 호출 식이 **자기가 만든 URL 을 스스로 받는가** — 식의 오타를 잡는다
    broken = [f["key"] for f in FLOWS if f["call"]
              and not re.compile(f["call"][1]).search(sample_url(f["call"][1]))]
    if broken:
        ok = False
        print("%s X 스스로 받지 못하는 기대 호출 식: %s" % (TAG, broken))
    else:
        n = sum(1 for f in FLOWS if f["call"])
        print("%s O 기대 호출 식 %d개가 **자기 URL 을 스스로 받는다**" % (TAG, n))

    # ② 변이 — **판정 하나마다 하나씩.** 그 칸만 빨개지거나 회색이어야 한다
    K = "U1#11"
    mutants = {}

    m = _all_good(); m[K] = dict(m[K], calls=[])
    mutants["눌렀는데 아무것도 안 나갔다"] = (m, RED)

    m = _all_good()
    m[K] = dict(m[K], state=dict(m[K]["state"], before="x", after="x"))
    mutants["요청은 나갔는데 값이 그대로다"] = (m, RED)

    m = _all_good(); m[K] = dict(m[K], text_after="")
    mutants["바뀌었는데 화면이 침묵한다"] = (m, RED)

    m = _all_good()
    m[K] = dict(m[K], control={"found": False, "why": "단추가 없다"})
    mutants["누를 자리가 없다 → 회색"] = (m, GREY)

    m = _all_good()
    m[K] = dict(m[K], calls=[{"method": "POST", "status": 403,
                              "url": "http://localhost:8000/api/dsm/events/4808/review"}])
    mutants["관문이 거절했다(403) → 빨강"] = (m, RED)

    m = _all_good()
    m[K] = dict(m[K], calls=[{"method": "POST", "status": 200,
                              "url": "http://localhost:8000/api/dsm/events/4808/notify"}])
    mutants["다른 경로가 나갔다"] = (m, RED)

    m = _all_good()
    m[K] = dict(m[K], calls=[{"method": "GET", "status": 200,
                              "url": "http://localhost:8000/api/dsm/events/4808/review"}])
    mutants["메서드가 다르다"] = (m, RED)

    m = _all_good()
    m["U1#8"] = dict(m["U1#8"], state=dict(m["U1#8"]["state"], on_screen=False))
    mutants["서버는 냈는데 화면이 안 그린다"] = (m, RED)

    m = _all_good()
    m[K] = dict(m[K], control={"found": True, "clicked": False, "why": "눌리지 않았다"})
    mutants["찾았는데 못 눌렀다 → 회색"] = (m, GREY)

    caught = 0
    for label, (obs, want) in mutants.items():
        key = "U1#8" if "화면이 안 그린다" in label else K
        got = dict((k, c) for k, c, _, _, _ in judge(obs))[key]
        if got == want:
            caught += 1
        else:
            ok = False
            print("%s X 변이 「%s」를 못 잡는다 — %s 를 기대했는데 %s" % (TAG, label, want, got))
    print("%s O 변이 %d/%d 를 잡는다 (음성 대조 · 규칙)" % (TAG, caught, len(mutants)))

    # ③ ★★ 출생 표본 — 2026-09-08 의 죽은 단추 셋. **셋 다 빨강**이어야 한다
    born = judge(BIRTH_SAMPLE())
    bkeys = set(BIRTH_SAMPLE())
    wrong = [(k, c) for k, c, _, _, _ in born if k in bkeys and c != RED]
    if wrong:
        ok = False
        print("%s X 출생 표본을 빨강으로 못 읽는다: %s — **이 도구가 태어난 사유가 안 재진다**"
              % (TAG, wrong))
    else:
        print("%s O 출생 표본 %d/%d 빨강 — 「그려졌다」로 0.5 를 받던 단추 셋을 "
              "**0 으로** 읽는다 (실제로 판정 · 되돌리기 · 현장 회신)" % (TAG, len(bkeys), len(bkeys)))

    # ④ 관측 0건은 **초록이 아니다** (D-301) — 48 이 전부 회색이고 점수는 0/48
    z = judge({})
    g, r, y = score(z)
    if g or y != len(FLOWS):
        ok = False
        print("%s X 관측 0건을 초록으로 읽는다 (초록 %d · 회색 %d)" % (TAG, g, y))
    else:
        print("%s O 관측 0건 → 0/48 · 회색 48 (**못 잰 것이 통과가 되지 않는다**)" % TAG)

    # ⑤ ★ 면제 칸이 없다 (D-327)
    hits, keyed = _no_exception_slot()
    if hits or keyed:
        ok = False
        print("%s X 면제 칸이 생겼다 — 상수 %s · 판정기가 이름을 본다 %s" % (TAG, hits, keyed))
    else:
        print("%s O 면제 칸 없음 — 판정기는 **관측만** 받는다 (D-327)" % TAG)

    # ⑥ 분모는 48 이다. 손으로 줄지 않는다
    if len(FLOWS) != 48 or len(FLOW_BY_KEY) != 48:
        ok = False
        print("%s X 분모가 48 이 아니다 — %d행 · 고유키 %d개" % (TAG, len(FLOWS), len(FLOW_BY_KEY)))
    else:
        per = dict((p, sum(1 for f in FLOWS if f["key"].startswith(p + "#"))) for p in PERSONAS)
        if sorted(per.values()) != [8] * 6:
            ok = False
            print("%s X 여섯 사람 × 여덟이 아니다 — %s" % (TAG, per))
        else:
            print("%s O 분모 48 = 여섯 사람 × 여덟 (%s)" % (TAG, per))

    # ⑦ ★ [턴 U · 절 4] **상태를 바꾸는 클릭은 전부 되돌림을 선언한다** — 손 grep 대신
    #   시험이 센다. 다음에 쓰기 흐름을 하나 더 넣는 사람이 이 주석을 못 읽어도 잡힌다.
    writers = [f["key"] for f in FLOWS if changes_state(f)]
    missing = [f["key"] for f in FLOWS if changes_state(f) and not f.get("revert")]
    if missing:
        ok = False
        print("%s X 상태를 바꾸는 클릭인데 되돌림 선언이 없다: %s — 게이트가 남긴 상태는 "
              "다음 게이트의 거짓 빨강이다 (턴 T · U5#9 → verify_seed_roles K2 0명)"
              % (TAG, missing))
    elif not writers:
        ok = False
        print("%s X 상태를 바꾸는 클릭이 한 자리도 없다 — 이 시험의 분모가 0이다" % TAG)
    else:
        back = [f["key"] for f in FLOWS
                if changes_state(f) and (f["revert"] or {}).get("kind") == "same_control"]
        print("%s O 상태를 바꾸는 클릭 %d자리가 모두 되돌림을 선언한다 — 같은 문으로 "
              "되돌리는 자리 %d(%s) · 사유를 적고 안 되돌리는 자리 %d"
              % (TAG, len(writers), len(back), " · ".join(back) or "—",
                 len(writers) - len(back)))
        blank = [k for k in writers
                 if (FLOW_BY_KEY[k]["revert"] or {}).get("kind") == "none"
                 and not (FLOW_BY_KEY[k]["revert"] or {}).get("why")]
        if blank:
            ok = False
            print("%s X 사유 없는 「안 되돌림」: %s — 사유 없는 선언은 잊은 것과 "
                  "구별되지 않는다 (D-301)" % (TAG, blank))

    # ⑦-b 되돌리기는 **판정을 바꾸지 않는다** — 관측에 revert 가 있든 없든 같은 답
    base = _all_good()
    K2 = "U5#9"
    if K2 in base:
        m = _all_good()
        m[K2] = dict(m[K2], revert={"kind": "same_control", "clicked": True,
                                    "restored": False, "why": "안 돌아왔다"})
        a = dict((k, c) for k, c, _w, _s, _t in judge(base))
        b = dict((k, c) for k, c, _w, _s, _t in judge(m))
        if a != b:
            ok = False
            print("%s X 되돌림 관측이 판정을 바꿨다 — 판정은 되돌리기 **전**의 관측이다" % TAG)
        else:
            print("%s O 되돌림 관측은 판정을 바꾸지 않는다 (실패해도 그 행의 색은 그대로)" % TAG)

    # ⑦-c ★★ [P-189 · 2차] **증거 되읽기 — 가리기를 손상으로 읽지 않는다.**
    #     출생 표본이 이 술어에 박혀 있다: 내가 만든 **거짓 회색**이다.
    rt_ok, rt_bad = _p189_roundtrip_cases()
    if rt_bad:
        ok = False
        print("%s X [P-189] 되읽기 검사가 틀렸다 %d건:" % (TAG, len(rt_bad)))
        for line in rt_bad:
            print("      %s" % line)
    else:
        print("%s O [P-189] 되읽기 %d갈래 — ★ 출생 표본: **가리기가 일어난 판을 "
              "초록으로 읽는다**(종전 판은 여기서 언제나 회색이었다) · "
              "손상은 여전히 빨강 · 가리기가 수를 바꾸면 빨강" % (TAG, rt_ok))

    # ⑧ ★★ [P-190] **두 도구 한 행 한 정본.** 같은 행에 다른 사실을 말하면 빨강이다.
    #    출생 표본이 이 술어에 박혀 있다 — 아래 `_p190_birth_sample()` 이 그 모양이다.
    b_bad, b_good = _p190_birth_sample()
    if not b_bad or b_good:
        ok = False
        print("%s X [P-190] 출생 표본을 못 잡는다 — 갈린 표본 %r · 같은 표본 %r"
              % (TAG, b_bad, b_good))
    else:
        print("%s O [P-190] 출생 표본 — U5#15「읽는 라우트가 없다」 vs 정본 "
              "`GET /api/dsm/system/storage` 200 을 **갈림**으로 읽는다" % TAG)

    dis = canon_disagreements()
    if dis is None:
        print("%s ? [P-190] 온보딩 정본(%s)을 못 읽었다 — **회색**이다. 문서가 없다고 "
              "두 정본이 갈렸다고 말하지 않는다" % (TAG, CANON_DOC.name))
    elif dis:
        ok = False
        print("%s X [P-190] **두 도구가 같은 행에 다른 정본을 든다 %d행** — 하나는 거짓이다:"
              % (TAG, len(dis)))
        for key, mine, theirs in dis:
            print("      %-7s 이 파일: %s" % (key, mine))
            print("      %-7s 온보딩 정본: %s" % ("", theirs))
    else:
        #: ★ [턴 X 2차 회귀] **분모를 손으로 적지 않는다.** 종전 문구의 「48행」은
        #:   대 본 수가 아니라 표의 행 수였다 — 갈릴 수 있는 행이 0이어도 그대로 찍혔다.
        n = canon_compare_census() or {}
        print("%s O [P-190] 두 도구가 갈린 행 **0** — 읽은 행 %d · 양쪽이 다 말한 행 %d "
              "(정본: 잰다 %d · 「정본 없음」 %d · 제 입으로 회색 %d / 이 파일: 문 있다 %d · "
              "「정본 없음」 %d)"
              % (TAG, n.get("rows", 0), n.get("both_say", 0), n.get("canon_has", 0),
                 n.get("canon_none", 0), n.get("canon_grey", 0), n.get("fc_has", 0),
                 n.get("fc_none", 0)))
        if not n.get("capable", 0):
            print("%s ⚠ [P-190] **갈릴 수 있는 행 0** — 살아 있는 정본으로는 이 술어가 "
                  "빨개질 수 없다. 지금 이 줄을 초록으로 만드는 것은 정본이 아니라 "
                  "위의 **출생 표본**이다. 「갈린 행 0」을 「둘이 같다」로 읽지 마라 — "
                  "「댈 것이 없다」와 글자가 같다 (턴 W 정정 11행이 `canon_none` 을 "
                  "0으로 만들어 두 갈래 중 하나가 구조적으로 죽었다)" % TAG)
        else:
            print("%s   갈릴 수 있었던 행 %d — 그중 갈린 행 0" % (TAG, n["capable"]))

    print("%s 자기시험 %s" % (TAG, "통과" if ok else "**실패**"))
    return EXIT_OK if ok else EXIT_FAIL


def _p189_roundtrip_cases():
    """★ **출생 표본** (P-189 2차) — `evidence_roundtrip` 의 네 갈래.

    [실측 2026-09-19 · 턴 W · V] 종전 판은 「가리기 **전** 원문 == 쓴 파일」을 견줬고,
    증거에 `appkey=` 가 **18곳** 있어 그 비교가 **언제나** 어긋났다 —
    `--measure` 가 증거가 멀쩡한데도 매번 **회색**으로 끝났다. 아래 첫 갈래가 그 판이다.
    ⚠ 이 갈래가 빨강이면 고친 것이 아니라 **되돌아간 것**이고,
      셋째·넷째 갈래가 초록이면 고친 것이 아니라 **끈 것**이다.
    """
    def doc(phrase2="전체 상황판 · 대시보드 · 칸이 정상적으로 그려졌습니다", extra_url=True):
        calls = [{"method": "GET",
                  "url": "http://localhost:8000/api/dsm/dashboard/frame", "status": 200}]
        if extra_url:
            #: 실제 증거에 18곳 있는 그 모양 — 지도를 그리려고 부른 공개 클라이언트 키
            calls.append({"method": "GET",
                          "url": "http://dapi.kakao.com/v2/maps/sdk.js"
                                 "?appkey=0123456789abcdef&libraries=services", "status": 200})
        return {"observations": {"U1#2": {
            "control": {"found": True, "clicked": True, "name": "화면 열기"},
            "calls": calls,
            "state": {"kind": "server_reflect", "field": "panel_total",
                      "after": 2, "on_screen": True},
            "text_after": phrase2}}}

    bad, n = [], 0
    raw = json.dumps(doc(), ensure_ascii=False, indent=2)
    written = _redact_credentials(raw)

    # ① ★ 출생 표본 — **가리기가 실제로 일어난 판.** 종전 판은 여기서 언제나 회색이었다.
    n += 1
    if _CRED_IN_URL.search(raw) is None:
        bad.append("표본에 가릴 자격이 없다 — 이 갈래가 아무것도 재지 않는다")
    okv, lines, facts = evidence_roundtrip(raw, written, written)
    if not okv:
        bad.append("★ **가리기가 일어난 판을 회색으로 읽는다** — 내가 만든 그 거짓 회색이 "
                   "돌아왔다: %s" % (lines[-1] if lines else "?"))
    elif facts.get("가린 자리", 0) < 1:
        bad.append("가린 자리를 0곳으로 센다 — 가리기 칸이 분모 없이 초록이 된다")

    # ② 가릴 것이 없는 판도 초록 (가리기는 있을 수도 없을 수도 있다)
    n += 1
    raw0 = json.dumps(doc(extra_url=False), ensure_ascii=False, indent=2)
    okv, _l, f0 = evidence_roundtrip(raw0, raw0, raw0)
    if not okv or f0.get("가린 자리") != 0:
        bad.append("가릴 것이 없는 판을 초록으로 못 읽거나 가린 자리를 0으로 안 적는다")

    # ③ **손상은 여전히 빨강** — 다시 읽은 것이 쓴 것과 다르다
    n += 1
    hurt = written.replace('"panel_total"', '"panel_totaI"', 1)
    okv, lines, _f = evidence_roundtrip(raw, written, hurt)
    if okv:
        bad.append("★ 쓴 것과 **다시 읽은 것이 다른데** 초록으로 읽는다 — 검사를 껐다")

    # ④ **가리기가 수를 바꾸면 빨강** — 자격 값이 아니라 한글을 지운 판
    n += 1
    eaten = json.dumps(doc(phrase2="???"), ensure_ascii=False, indent=2)
    okv, lines, f4 = evidence_roundtrip(raw, eaten, eaten)
    if okv:
        bad.append("★ **가리기가 수를 바꿨는데** 초록으로 읽는다 — 가리기 칸이 꺼졌다")
    elif f4.get("수(가리기 전)") == f4.get("수(가린 뒤)"):
        bad.append("가리기 전후의 수가 같다고 적으면서 빨강을 냈다 — 사유가 사유가 아니다")

    # ⑤ 출생 표본의 **그 병**(cp949 왕복)이 수를 바꾸는 것은 여전히 잡힌다
    n += 1
    broken = raw.encode("cp949", "replace").decode("utf-8", "replace")
    okv, _l, f5 = evidence_roundtrip(raw, broken, broken)
    if okv:
        bad.append("★ cp949 로 깨진 판을 초록으로 읽는다 — 이 도구가 태어난 그 병이다")
    return n, bad


def _p190_birth_sample():
    """★ **출생 표본** (D-310 · P-190) — 이 술어를 만들게 한 **바로 그 두 줄**.

    [실측 2026-09-19 · 턴 W · 차선 U56] `U5#15 저장 용량 확인` 에 대해
      · 이 파일의 주석:  「신호는 ops_monitor 안에만 있다 — 읽는 라우트가 없다」
      · 온보딩 정본:     `GET /api/dsm/system/storage` **200** (`api_u56.py:647`)
    U56 이 그 문을 세우고 **눌러서 200 을 봤다**(익명 401 · 역할 없음 403 · POST 405 ·
    화면 404 0/11). 두 정본 중 하나는 거짓인데, 그 거짓을 묻는 자리가 **없었다.**

    돌려주는 것: (갈린 표본이 갈림으로 읽히는가, 같은 표본이 갈림으로 잘못 읽히는가).
    """
    none_note = "정본: 신호는 ops_monitor 안에만 있다 — 읽는 라우트가 없다"
    canon_has = ("[API 호출] `GET /api/dsm/system/storage` 200"
                 "(`api_u56.py:647`) + [화면 상태] `저장 용량` 카드")
    def split(note, last):
        none_ = "정본 없음" in last
        has = (bool(_CANON_MEASURES.search(last)) and not none_
               and not _CANON_SAYS_GREY.search(last))
        says_none = (bool(_NOTE_SAYS_NONE.search(note))
                     and not _NOTE_IS_CORRECTION.search(note))
        return says_none and has
    return (split(none_note, canon_has),                     # 갈림 → True 여야 한다
            split("정본: 이 자리는 아직 없다 — 읽는 라우트가 없다", "**정본 없음**"))


# ──────────────────────────────────────────────────────────────────────────
# 실측 — gx-shell 안에서 **실제로 누른다**
# ──────────────────────────────────────────────────────────────────────────
#: 드라이버에 공용 술어를 심는 자리. **이 이름을 드라이버 머리말에 글자로 적지 마라** —
#:   치환이 머리말을 먼저 먹는다(턴 X 실측).
_DRIVER_SLOT = "# __SHARED_" + "HELPERS__"

DRIVER = r'''# -*- coding: utf-8 -*-
"""P-118 실측 드라이버 — gx-shell 안에서 돈다. **누르고, 나간 것을 세고, 다시 읽는다.**

⚠ **이 파일은 딴 프로세스다.** 바깥 모듈(`verify_click_completes.py`)의 이름은 여기 없다.
  같이 써야 하는 술어는 아래 표시된 자리에 **원문 그대로 심어** 넣는다
  (`measure()` 가 `inspect.getsource` 로 심는다). **손으로 한 벌 더 적지 마라** —
  두 벌을 두면 어긋나고, 어긋난 쪽이 조용히 이긴다.

⚠ 그 표시 이름을 이 머리말에 **글자로 적지 마라** — 치환이 머리말을 먼저 먹는다.
  [실측 2026-09-20 · 턴 X] 조율자가 적었고, 머리말이 먹혀 파일이 구문 오류가 됐다.
"""
import json, os, re, sys, threading, time

# __SHARED_HELPERS__
import urllib.request as U
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SPEC = json.loads(sys.stdin.read())
API = SPEC["api"]              # http://gx-nginx-e:8500
SPA = SPEC["spa"]              # http://localhost:3002
OUT = SPEC["out"]
HOP = {"connection", "keep-alive", "transfer-encoding", "content-encoding",
       "content-length", "te", "trailer", "upgrade", "proxy-authorization"}


class Proxy(BaseHTTPRequestHandler):
    """번들이 http://localhost:8000 을 부른다. 그 포트를 실제 gunicorn 에 잇는다.

    ★ 2026-09-08 의 계측 결함을 되풀이하지 않는다 — 그때 프록시가
      Content-Encoding 을 지운 채 gzip 바이트를 넘겨 로그인 응답이 깨졌고,
      그 구간의 「비밀번호가 올바르지 않습니다」는 **제품 결함이 아니라 계측 결함**이었다.
      그래서 위로 갈 때 `Accept-Encoding: identity` 를 박아 압축 자체를 없앤다.
    """
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _pass(self, method):
        body = None
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            body = self.rfile.read(n)
        h = dict((k, v) for k, v in self.headers.items() if k.lower() not in HOP)
        h["Accept-Encoding"] = "identity"
        h.pop("Host", None)
        req = U.Request(API + self.path, data=body, headers=h, method=method)
        try:
            r = U.urlopen(req, timeout=40)
            code, hdrs, data = r.status, r.headers, r.read()
        except U.HTTPError as e:
            code, hdrs, data = e.code, e.headers, e.read()
        except Exception as e:
            self.send_response(502); self.send_header("Content-Length", "0"); self.end_headers()
            return
        self.send_response(code)
        for k, v in (hdrs.items() if hdrs else []):
            if k.lower() in HOP:
                continue
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_GET(self): self._pass("GET")
    def do_POST(self): self._pass("POST")
    def do_PUT(self): self._pass("PUT")
    def do_PATCH(self): self._pass("PATCH")
    def do_DELETE(self): self._pass("DELETE")

    def do_OPTIONS(self): self._pass("OPTIONS")


#: ★ 8000 을 뺏지 않는다. 다른 차선이 거기에 **개발용 runserver** 를 세워 두는데,
#:   그 판은 MinIO 자리표 자격이라 사진 경로가 503 이다 — 그 503 을 제품 결함으로
#:   적으면 **계측 결함을 빨강으로 파는 것**이 된다. 그래서 빈 포트를 잡고,
#:   브라우저가 부르는 localhost:8000 을 그 포트로 **돌려세운다**(아래 route).
srv = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

TOKENS = {}


def login_api(user, pw):
    d = json.dumps({"username": user, "password": pw, "end_previous_session": True}).encode()
    r = U.Request(API + "/api/v1/auth/login", data=d, headers={"Content-Type": "application/json"})
    return json.loads(U.urlopen(r, timeout=30).read())["user"]["access_token"]


#: ★ [P-132] 관리자 자격은 **필요한 순간에 한 번만** 얻는다. 미리 얻어 두면
#:  `end_previous_session` 이 그 계정으로 화면을 걷던 사람의 세션을 죽인다
#:  (동시 접속 1 — 그 끊김이 다음 사람의 회색이 된다).
_ADMIN = [None, False]


def admin_token():
    if _ADMIN[1]:
        return _ADMIN[0]
    _ADMIN[1] = True
    acc = SPEC.get("admin_account") or []
    if len(acc) == 2:
        try:
            _ADMIN[0] = login_api(acc[0], acc[1])
        except U.HTTPError as e:
            # ★ [실측 2026-09-17 · 턴 T · V] SEC-21 율제한(IP 당 로그인 5회/분)이 이번 턴 생겼다.
            #   U5·U6 의 화면 로그인(각 2회) + 표본 고르기 1회 뒤의 여섯째 로그인이 **429** 를 받아
            #   U6#1 이 「관리자 자격으로 들어가지 못했다」 회색이 됐다 — 제품이 아니라 이 도구의 박자다.
            #   429 면 61초 기다려 **한 번만** 다시 얻는다. 다른 오류는 그대로 None(회색).
            _ADMIN[0] = None
            if e.code == 429:
                print("[P-118] 관리자 로그인 429(율제한) — 61초 뒤 한 번 다시", file=sys.stderr)
                time.sleep(61)
                try:
                    _ADMIN[0] = login_api(acc[0], acc[1])
                except Exception:
                    _ADMIN[0] = None
        except Exception:
            _ADMIN[0] = None
    return _ADMIN[0]


def _get1(path, tok):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    try:
        r = U.urlopen(U.Request(API + path, headers=h), timeout=30)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except U.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def get(path, tok=None):
    """다시 읽기. **한 번 더 준다** — 401·502 한 방으로 회색을 내면,
    앱이 토큰을 막 갈아 끼운 순간이나 게이트웨이가 한 번 튄 것이
    「제품을 못 쟀다」로 적힌다. 두 번 다 아니면 그때는 정말 못 잰 것이다."""
    code, js = _get1(path, tok)
    if js is None and code in (401, 502, 503, None):
        time.sleep(1.5)
        code, js = _get1(path, tok)
    return code, js


def call(method, path, tok=None, body=None):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    if body is not None:
        h["Content-Type"] = "application/json"
        body = json.dumps(body).encode()
    try:
        r = U.urlopen(U.Request(API + path, data=body, headers=h, method=method), timeout=30)
        return r.status, r.read().decode("utf-8", "replace")[:400]
    except U.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:
        return None, str(e)[:200]


def dig(obj, field):
    if obj is None:
        return None
    if isinstance(obj, dict):
        if field in obj:
            v = obj[field]
            return len(v) if isinstance(v, (list, dict)) else v
        for v in obj.values():
            if isinstance(v, dict):
                r = dig(v, field)
                if r is not None:
                    return r
    return None


results = {}
NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

from playwright.sync_api import sync_playwright

pw = sync_playwright().start()
browser = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])


def note(key, **kw):
    kw["measured_at"] = NOW()
    results[key] = kw


def settle_login(page, ms=25000):
    """**로그인이 끝나기를 기다린다 — 정해진 시간을 자고 일어나지 않는다.**

    턴 O 08:32 에 이 자리가 4.5초 낮잠이었다. 그 순간 화면은 「로그인 중입니다…」
    였고 게이트는 「주소가 그대로다」를 **빨강으로** 적었다 — 제품이 아니라
    **계측이 늦은 것**이었다. 기다리는 것과 없는 것은 다르다.
    """
    end = time.time() + ms / 1000.0
    while time.time() < end:
        if "/login" not in page.url:
            page.wait_for_timeout(2500)
            return True
        try:
            b = page.get_by_role("button", name=re.compile("Confirm|확인"))
            if b.count() and b.first.is_visible():
                b.first.click()
        except Exception:
            pass
        page.wait_for_timeout(1000)
    return "/login" not in page.url


def find_control(page, ctrl):
    """이름으로 누를 것을 찾는다. **못 찾으면 회색이다 — 지어내지 않는다.**"""
    name = ctrl["name"]
    for loc in (page.get_by_role("button", name=re.compile(name)),
                page.get_by_text(re.compile(name), exact=False)):
        try:
            n = loc.count()
        except Exception:
            continue
        for i in range(min(n, 6)):
            el = loc.nth(i)
            try:
                if el.is_visible():
                    return el
            except Exception:
                continue
    return None


def walk(persona, account, viewport, flows, event_id):
    tok = None
    ctx = browser.new_context(viewport=viewport, locale="ko-KR")
    # 번들에 박힌 localhost:8000 을 **우리 프록시**로 돌려세운다 → 진짜 MinIO 자격의 gunicorn
    ctx.route(re.compile(r"^https?://localhost:8000/"),
              lambda route: route.continue_(
                  url=route.request.url.replace("localhost:8000", "127.0.0.1:%d" % PORT)))
    page = ctx.new_page()
    calls = []
    #: ★ **앱이 쓰는 그 자격으로 다시 읽는다.** 게이트가 따로 로그인하면
    #:   `end_previous_session` 이 브라우저의 세션을 죽여(동시 접속 1) 다시 읽기가
    #:   401 이 되고, 그러면 **제품이 아니라 계측이 회색을 만든다** [실측 08:24 · U1 7행].
    #:   그래서 브라우저가 실제로 보낸 Authorization 을 주워서 그것으로 다시 읽는다.
    seen_auth = [None]

    def on_req(r):
        calls.append({"method": r.method, "url": r.url, "status": None})
        try:
            a = (r.headers or {}).get("authorization") or ""
        except Exception:
            a = ""
        if a.lower().startswith("bearer "):
            seen_auth[0] = a.split(" ", 1)[1]

    page.on("request", on_req)

    def on_resp(r):
        for c in reversed(calls):
            if c["url"] == r.url and c["status"] is None:
                c["status"] = r.status
                break
    page.on("response", on_resp)

    #: [P-148] 사진 술어 전용 — **`calls` 와 따로** 잡는다. 상세 화면은 먼저 이벤트를
    #:   읽고 그 응답이 온 **뒤에야** 사진을 잇달아 부른다(순차 연쇄). goto 행은 본문을
    #:   붙잡는 순간 `calls` 를 비우므로(`del calls[:]`, 아래) 늦게 오는 사진 응답은
    #:   그 순간 이후 갈 곳이 없다 — 그래서 흐름 전체에 걸쳐 **따로** 살아남는 자리를 둔다.
    img_resp = {}

    def on_img_resp(r):
        try:
            if re.search(r"/snapshot(\?|$)", r.url):
                img_resp["status"] = r.status
                img_resp["content_type"] = r.headers.get("content-type")
        except Exception:
            pass
    page.on("response", on_img_resp)

    relogin = [0]                    # 다시 들어간 횟수 — 로그인은 IP 당 5/분이다

    def ui_login():
        """**화면으로** 들어간다. 여기가 서면 그 사람의 여덟 자리를 잴 수 있다."""
        page.goto(SPA + "/login", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2200)
        page.fill("input[name=username]", account[0])
        page.fill("input[name=password]", account[1])
        page.click("button.login-button")
        return settle_login(page)

    # U1 은 자기 #1 행이 로그인 그 자체다 — 거기서 잰다. 나머지는 **준비로** 들어간다.
    does_own_login = any(f["key"] == "U1#1" for f in flows)
    if account and persona != "U6" and not does_own_login:
        try:
            if not ui_login():
                # ★★ [P-132] **못 들어간 이유를 적는다.** 종전에는 「/login 에 머문다」
                #   한 줄뿐이었고 화면 글자도 응답 코드도 안 남았다 — 그래서 U2 여덟 줄이
                #   **원인 없는 회색**으로 한 턴을 통째로 건너뛰었다. 화면이 이미 사유를
                #   적고 있는데(다섯 갈래 · `loginCopy.ts`) 그것을 줍지 않은 것은
                #   제품이 아니라 **계측의 침묵**이다.
                try:
                    said = page.inner_text("body")[:1500]
                except Exception:
                    said = ""
                seen = [(c.get("method"), c.get("url"), c.get("status"))
                        for c in calls if "/auth/login" in (c.get("url") or "")]
                for f in flows:
                    note(f["key"], control={
                        "found": False,
                        "why": "그 사람으로 **화면에 들어가지 못했다** (%s · /login 에 머문다)"
                               % account[0],
                        "login_said": said,
                        "login_calls": seen,
                        "url": page.url})
                ctx.close(); return
        except Exception as e:
            for f in flows:
                note(f["key"], control={"found": False,
                                        "why": "로그인이 끊겼다: %s" % type(e).__name__})
            ctx.close(); return

    if persona == "U6":
        tok = login_api(account[0], account[1])

    for f in flows:
        del calls[:]                 # ★ 흐름마다 **새로 센다** — 앞 화면의 호출이 섞이지 않는다
        img_resp.clear()             # [P-148] 사진 술어도 흐름마다 새로 센다
        tok = seen_auth[0] or tok    # 앱이 쓰는 자격을 그대로 쓴다
        key = f["key"]
        # ★ [P-162 · 턴 T · U3#3] 흐름마다 **다른 표본**을 쓸 수 있다 — 사진 술어는 `snapshot_path`
        #   가 비어 있지 않은 사건이어야 한다(참조 없는 씨앗은 GET 이 안 나가는 것이 옳다 —
        #   턴 S 빨강은 표본 선택이었다). `SPEC["event_by_flow"]` 에 있으면 그 사건, 없으면 공용.
        flow_event = (SPEC.get("event_by_flow") or {}).get(key, event_id)
        screen = (f["screen"] or "").replace("{event}", str(flow_event))
        st = dict(f["state"] or {})
        gp = (st.get("get") or "").replace("{event}", str(flow_event))

        # ── 누르기 전 상태 (새 GET) ──
        before = None
        if gp and st.get("kind") in ("server_change", "server_reflect"):
            code, js = get(gp, tok)
            before = dig(js, st.get("field")) if js is not None else None

        # ── U6: 사람이 아니다. 「누르는 것」이 곧 HTTP 호출이다 ──
        if (f["control"] or {}).get("kind") == "api":
            method, pat = f["call"]
            path = SPEC["api_paths"].get(key, "")
            path = path.replace("{event}", str(event_id))
            if "{next}" in path:
                c0, ev0 = get("/api/dsm/events/%s" % event_id, tok)
                nxt = ((ev0 or {}).get("allowed_next") or [""])[0]
                if not nxt:
                    note(key, control={"found": False,
                                       "why": "제품이 다음 단계를 하나도 내주지 않았다 "
                                              "(allowed_next 비었다) — 밀어 넣지 않는다"})
                    continue
                path = path.replace("{next}", nxt)
            if not path:
                note(key, control={"found": False, "why": "기계 흐름의 호출 경로가 선언되지 않았다"})
                continue
            anon = (key == "U6#12")
            # ★ [P-132] **누가 누르는가도 기대식이다.** 설정 문(키 발급)은 관리자만
            #   지난다 — 기계 자격으로 두드려 받은 403 은 제품의 결함이 아니라 **내
            #   자격의 결함**이다. 그 행만 관리자 자격을 쓴다(아래 `admin_account`).
            who = SPEC.get("api_actor", {}).get(key)
            use = tok
            if who == "admin" and not anon:
                use = admin_token()
                if use is None:
                    note(key, control={"found": False,
                                       "why": "관리자 자격으로 들어가지 못했다 — "
                                              "이 문은 관리자만 지난다(재지 못했다)"})
                    continue
            code, body = call(method, path, None if anon else use,
                              SPEC["api_bodies"].get(key))
            got = [{"method": method, "url": API + path, "status": code}]
            if st.get("kind") == "status_is":
                st["after"] = str(code)
            elif gp:
                c2, js2 = get(gp, None if anon else use)
                st["before"], st["after"] = before, dig(js2, st.get("field"))
                st["on_screen"] = True   # 기계에는 화면이 없다 — 응답 본문이 곧 화면이다
            note(key, control={"found": True, "clicked": True, "name": "HTTP " + method},
                 calls=got, state=st, text_after=str(body))
            continue

        if not f["control"]:
            # ★ [P-190 · 턴 W] 종전 문구는 「정본이 「없음」이라 적은 자리」였다. 그 말은
            #   **거짓일 수 있다** — 온보딩 정본에는 술어가 적혀 있는데 이 도구만 안 누르는
            #   자리가 있기 때문이다(U5#15 이 그 모양이었다). 회색 사유는 **이 도구가 누를
            #   자리를 선언하지 않았다**이고, 정본이 없다는 말과 같지 않다.
            note(key, control={"found": False,
                               "why": "이 도구가 누를 자리를 선언하지 않았다 — " + (f["note"] or "")})
            continue

        # ── 화면으로 간다 ──
        try:
            page.goto(SPA + screen, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            note(key, control={"found": False, "why": "화면을 열지 못했다: %s" % type(e).__name__})
            continue
        page.wait_for_timeout(2500)

        # ★ 로그인 화면으로 튕겼으면 **그 사람의 자리를 본 적이 없다.** 회색이다.
        #   이 빗장이 없으면 로그인 화면의 「호출 0건」이 제품의 빨강으로 팔린다.
        if "/login" in page.url and key != "U1#1":
            # ★ **한 번은 다시 들어가 본다.** 동시 접속 1이라 다른 차선이 같은 계정으로
            #   들어오면 걷는 중에 세션이 끊긴다 — 그 끊김을 그 사람의 자리가 없는 것으로
            #   적으면 **남의 로그인이 우리 점수가 된다.** 두 번째도 튕기면 그때는 회색이다.
            back = False
            if account and persona != "U6" and relogin[0] < 3:
                relogin[0] += 1
                try:
                    back = ui_login()
                except Exception:
                    back = False
                if back:
                    try:
                        # ★★ [P-132] **여기서 비우고 다시 연다.** 종전에는 다시 연
                        #   **뒤에** 비웠고, 그래서 다시 연 화면이 낸 호출이 통째로
                        #   지워졌다 — 그 행은 「눌렀는데 아무것도 안 나갔다」(빨강)로
                        #   적혔다. [실측 2026-09-10 · U1#3 · U3#19] 둘 다 화면에는
                        #   서버 값이 그려져 있는데(「응답 없음 4대 (전체 4대)」·
                        #   「발송 기록 50건」) 기록된 호출은 0건이었다. 남의 로그인이
                        #   우리 빨강이 되던 자리다.
                        del calls[:]
                        page.goto(SPA + screen, wait_until="domcontentloaded", timeout=45000)
                        page.wait_for_timeout(2500)
                    except Exception:
                        back = False
            if "/login" in page.url or not back:
                note(key, control={
                    "found": False,
                    "why": "로그인 화면으로 튕겼다 (%s · 다시 들어가기 %s) — 그 사람의 자리를 못 봤다"
                           % (screen, "했다" if relogin[0] else "안 했다")},
                     calls=list(calls))
                continue

        if key.endswith("#1") and key.startswith("U1"):
            # 로그인은 **화면으로** 한다 — 이 행이 재는 것이 그것이다
            before_url = page.url
            del calls[:]
            try:
                page.fill("input[name=username]", account[0])
                page.fill("input[name=password]", account[1])
                page.click("button.login-button")
            except Exception as e:
                note(key, control={"found": False, "why": "로그인 자리를 못 찾았다: %s" % type(e).__name__})
                continue
            settle_login(page)
            note(key, control={"found": True, "clicked": True, "name": "로그인"},
                 calls=list(calls),
                 state={"kind": "route_change", "before": before_url, "after": page.url},
                 text_after=(page.inner_text("body")[:4000] if page.url else ""))
            continue

        body_before = ""
        try:
            body_before = page.inner_text("body")
        except Exception:
            pass

        img_obs = None
        if f["control"]["kind"] == "goto":
            # 「누르는 것」 = 그 화면을 여는 것. **비어 있으면 누를 자리가 없다**
            if len(body_before.strip()) < 40:
                note(key, control={"found": False, "why": "화면이 비어 있다 (본문 %d자)"
                                   % len(body_before.strip())},
                     calls=list(calls))
                continue
            if f.get("img_check"):
                # [P-148] **더 기다린다.** 사진은 이벤트 GET 이 끝난 뒤에야 잇달아 불려서
                #   위 2.5초 낮잠만으로는 그림이 안 채워진 채로 잡힐 수 있다. 그림이
                #   채워지거나(성공) 오류 문구가 뜨거나(실패) 둘 중 하나가 설 때까지
                #   기다린다 — 그래도 안 서면 그때는 있는 그대로 잰다.
                try:
                    page.wait_for_function(
                        "() => { var i = document.querySelector('img[data-gx=\"snapshot\"]'); "
                        "return (i && i.complete && i.naturalWidth > 0) || "
                        "document.body.innerText.indexOf('불러오지 못했습니다') >= 0 || "
                        "document.body.innerText.indexOf('저장소에 연결할 수 없습니다') >= 0; }",
                        timeout=8000)
                except Exception:
                    pass
                try:
                    body_before = page.inner_text("body")
                except Exception:
                    pass
                try:
                    ev = page.evaluate(
                        "() => { var els = document.querySelectorAll('img[data-gx=\"snapshot\"]'); "
                        "if (els.length !== 1) return {count: els.length}; "
                        "var el = els[0]; return {count: 1, natural_width: el.naturalWidth}; }")
                except Exception:
                    ev = {"count": 0}
                img_obs = dict(ev or {"count": 0})
                img_obs["response"] = dict(img_resp)
            got = list(calls); del calls[:]
            text_after = body_before
        else:
            # ★ [P-132] 잠긴 단추를 **깨우는 글상자.** 제품이 일부러 잠근 자리
            #   (「회신 보내기」는 글이 비면 disabled)를 채우지 않고 눌러 「안 눌린다」를
            #   적으면 제품의 규율을 고장으로 파는 것이다. 채운 뒤에도 ②③④ 는 다 서야 한다.
            if f.get("fill"):
                # ★ [P-179 · 턴 V] 무엇을 적을지는 흐름이 정한다(`fill_text`). 숫자만 받는
                #   칸(「사건 보고서」의 사건번호)에 기본 한 줄을 적으면 화면이 숫자만 남기고
                #   서버가 404 를 낸다 — 제품이 아니라 계측이 빨강을 만드는 자리다.
                what = str(f.get("fill_text") or "P-118 게이트 측정 (자동) — 현장 이상 없음")
                what = what.replace("{event}", str(event_id))
                try:
                    box = page.get_by_placeholder(f["fill"])
                    if box.count():
                        box.first.fill(what)
                        page.wait_for_timeout(400)
                except Exception:
                    pass

            el = find_control(page, f["control"])
            if el is None:
                note(key, control={"found": False,
                                   "why": "「%s」를 화면에서 못 찾았다 (%s)"
                                          % (f["control"]["name"], screen)},
                     calls=list(calls))
                continue
            del calls[:]
            try:
                el.click(timeout=8000)
            except Exception as e:
                note(key, control={"found": True, "clicked": False,
                                   "why": "「%s」가 눌리지 않는다: %s"
                                          % (f["control"]["name"], type(e).__name__)})
                continue
            page.wait_for_timeout(1200)
            # 확인창을 지나는 길 — **여기가 2026-09-08 에 죽어 있던 층이다**
            if f.get("confirm"):
                try:
                    ta = page.locator("textarea")
                    if ta.count():
                        ta.first.fill("P-118 게이트 측정 (자동)")
                except Exception:
                    pass
                try:
                    ok = page.locator(".ant-modal-confirm-btns button, [role=dialog] button")
                    if ok.count():
                        for i in range(ok.count()):
                            t = (ok.nth(i).inner_text() or "").strip()
                            # ★ [P-132] 확인창의 단추 이름은 **화면마다 다르다.**
                            #   되돌림 확인창의 이름은 「되돌리기」다(EventDetail.tsx:256).
                            #   「확인」만 찾으면 그 확인창을 못 지나고, 못 지난 것이
                            #   「요청이 안 나갔다」로 적힌다.
                            if re.search("확인|OK|Confirm|판정|예|되돌리기|보내기|적용", t):
                                ok.nth(i).click(); break
                except Exception:
                    pass
            page.wait_for_timeout(SPEC["window_ms"])
            got = list(calls)
            try:
                text_after = page.inner_text("body")
            except Exception:
                text_after = ""

        # ── 누른 뒤 상태 (**새 GET 으로 다시 읽는다**) ──
        if st.get("kind") in ("server_change", "server_reflect") and gp:
            code, js = get(gp, tok)
            st["before"] = before
            st["after"] = dig(js, st.get("field"))
            if js is None:
                st["error"] = "다시 읽기 HTTP %s" % code
            if st["kind"] == "server_reflect":
                a = st.get("after")
                hay = (text_after or "")
                if f.get("img_check"):
                    # [P-148] 사진 경로 문자열은 화면에 글자로 안 뜬다(접힌 「참조 보기」
                    #   안에만 있다) — 실제로 그려졌는지는 술어 ④(img 판정)가 잰다.
                    #   여기서는 서버가 그 값 자체를 냈는지만 본다(데이터 존재).
                    st["on_screen"] = bool(a)
                else:
                    #: ★ **여기도 `0` 이 값이다** [턴 X]. `bool(a)` 로 물으면 서버가 낸 `0` 이
                    #:   화면에 「0건」으로 **글자까지 떠 있어도** 「화면에 없다」가 된다.
                    #:   무엇을 재는 칸인지 보면 분명하다 — 이 줄은 **「서버가 낸 값이 화면에
                    #:   반사됐는가」**를 재지 「그 값이 0보다 큰가」를 재지 않는다.
                    st["on_screen"] = server_gave_value(a) and (str(a) in hay or any(
                        w.lower() in hay.lower() for w in ["행", "건", "개"]) and len(hay) > 400)

        # ── ★ [턴 U · 절 4] **되돌리기 — 판정에 쓸 것을 다 읽은 뒤에** ──────────
        #   게이트가 제품의 상태를 남기면 다음 게이트가 제품 대신 우리를 잰다
        #   (턴 T · U5#9 → `verify_seed_roles` K2 수신자 0명).
        rev = None
        if ((f.get("revert") or {}).get("kind") == "same_control"
                and f["control"] and f["control"].get("kind") == "button"):
            rev = {"kind": f["revert"]["kind"], "clicked": False, "restored": None}
            try:
                el2 = find_control(page, f["control"])
                if el2 is None:
                    rev["why"] = "되돌릴 단추를 다시 못 찾았다 — 상태가 남는다"
                else:
                    el2.click(timeout=8000)
                    page.wait_for_timeout(SPEC["window_ms"])
                    rev["clicked"] = True
                    if gp:
                        _c, _j = get(gp, tok)
                        rev["after"] = dig(_j, st.get("field"))
                        #: 「원래대로」 = 누르기 **전에** 읽은 값과 같다.
                        rev["restored"] = (rev["after"] == before)
                        if not rev["restored"]:
                            rev["why"] = ("되돌렸는데 값이 처음과 다르다 (%r → %r)"
                                          % (before, rev["after"]))
            except Exception as exc:                    # noqa: BLE001
                rev["why"] = "되돌리기가 터졌다: %s" % type(exc).__name__

        note(key, control={"found": True, "clicked": True,
                           "name": f["control"].get("name", "화면 열기")},
             calls=got, state=st, text_after=(text_after or "")[:6000],
             **({"img": img_obs} if img_obs is not None else {}),
             **({"revert": rev} if rev is not None else {}))

    ctx.close()


# 이벤트 하나 고르기 — **판정이 안 된 것**이라야 U1#11 이 잴 것이 있다
tok0 = login_api(SPEC["pick_user"], SPEC["pick_pw"])
code, ev = get("/api/dsm/events?limit=50", tok0)
# ★ [P-156 · 턴 T · 차선 Q] **지난 회의 probe 씨앗은 표본에서 뺀다.** 목록 문은 `track_id` 를
#   안 내므로(api.py:244) 씨앗 카메라 이름(`probe_tag` 로 시작)으로 가른다 — 씨앗은 전부 그 카메라에
#   심긴다. 이번 회에 심은 것(`keep_event_ids`)만 남긴다. 규약과 순수 함수는 `scripts/probe_marks.py`
#   (`is_probe` · `exclude`) — 이 줄은 그 필터의 HTTP 판이다. 둘이 갈리면 그쪽이 정본이다.
_ptag = SPEC.get("probe_tag") or ""
_keep = set(int(x) for x in (SPEC.get("keep_event_ids") or []))
_all = list((ev or {}).get("events", []))
_rows = [e for e in _all
         if not (_ptag and str(e.get("stream_monitor_name") or "").startswith(_ptag)
                 and int(e.get("event_id") or 0) not in _keep)]
print("[P-118] 표본 %d건 중 probe 제외 %d건 (남긴 이번 씨앗 %d)"
      % (len(_all), len(_all) - len(_rows), len(_keep)), file=sys.stderr)
unv = [e["event_id"] for e in _rows if not e.get("verdict")]
EVENT = unv[0] if unv else (_rows or [{}])[0].get("event_id")
# ★ [P-162 · 턴 T] U3#3 표본 — `snapshot_path` 가 비어 있지 않은 사건. 없으면 공용 표본을 쓰고
#   그 사실을 적는다(그때 U3#3 빨강은 「참조 없는 표본」이지 제품이 아니다 — 3종 분류 데이터 상태).
_snap = [e["event_id"] for e in _rows if e.get("snapshot_path")]
SPEC.setdefault("event_by_flow", {})
if _snap and "U3#3" not in SPEC["event_by_flow"]:
    SPEC["event_by_flow"]["U3#3"] = _snap[0]
print("[P-118] U3#3 표본: %s (snapshot_path 있는 사건 %d건)"
      % (SPEC["event_by_flow"].get("U3#3", "공용 — 참조 있는 사건 없음"), len(_snap)), file=sys.stderr)

for persona in SPEC["order"]:
    p = SPEC["personas"][persona]
    flows = [f for f in SPEC["flows"] if f["key"].startswith(persona + "#")]
    try:
        walk(persona, p.get("account"), p["viewport"], flows, EVENT)
    except Exception as e:
        for f in flows:
            if f["key"] not in results:
                note(f["key"], control={"found": False,
                                        "why": "그 사람의 걷기가 끊겼다: %s %s"
                                               % (type(e).__name__, str(e)[:120])})

browser.close(); pw.stop(); srv.shutdown()
open(OUT, "w", encoding="utf-8").write(json.dumps(
    {"measured_at": NOW(), "event_id": EVENT, "event_by_flow": SPEC.get("event_by_flow") or {},
     "api": API, "spa": SPA,
     "observations": results}, ensure_ascii=False, indent=2))
print("WROTE %s · %d행" % (OUT, len(results)))
'''

#: 기계(U6) 흐름이 실제로 두드릴 경로. **사람 흐름에는 쓰이지 않는다.**
#: ★ 이 문들은 인자를 **질의문자열로** 받는다 (`api.py:977` `issue_api_key(name=…)` ·
#:  `api.py:613` `create_webhook_subscription(endpoint_url=…, signing_key_ref=…)`).
#:  본문 JSON 으로 두드리면 **422** 가 오고, 그 422 를 「값이 안 바뀌었다」로 적으면
#:  **내 요청이 틀린 것을 제품의 빨강으로 파는 것**이 된다 [실측 08:24 · U6#1·#4].
#: ★ [P-132] **누가 누르는가도 기대식이다.**
#:  `POST /api/dsm/settings/api-keys` 는 설정 문이라 관리자만 지난다
#:  (`api.py:986` `PermissionDeniedForSetting` → 403). 게이트는 그 문을 `gxprobe_q`
#:  (역할 `user`)로 두드리고 403 을 받아 **제품의 빨강**으로 적었다 — 제품은 옳게
#:  거절한 것이고 **틀린 것은 내 자격**이었다. 키를 **발급**하는 것은 사람(관리자)이고
#:  기계는 그 키를 **쓰는** 쪽이다(같은 파일 974행: 들어오는 키로 키를 못 만든다).
#:  그래서 이 한 행만 관리자 자격으로 두드린다.
API_ACTOR = {"U6#1": "admin"}

API_PATHS = {
    "U6#1": "/api/dsm/settings/api-keys?name=p118-gate",
    "U6#2": "/api/dsm/events?limit=5",
    "U6#3": "/api/dsm/events/{event}",
    #: ★ [P-132] `http://` 로 두드려 400 을 받고 있었다 — 「평문으로 보내면 서명이
    #:  위조는 막아도 **내용을 읽히는 것**은 막지 못합니다」. 제품이 옳고 **요청이
    #:  틀렸다.** 그 400 을 「값이 안 바뀌었다」로 적으면 내 오타를 제품의 빨강으로 판다.
    #: ★ [P-141 · 턴 Q · 차선 Q 3종 분류: 기대식 오류] `https://localhost:9` 는 **422** 였다 —
    #:  `webhook_outbox.py:173-175` 가 「우리 서버 자신을 가리키는 주소」를 막는다. 제품이
    #:  옳고 요청이 틀렸다(서명키 검사는 그 뒤라 닿지도 못했다). `.invalid` 는 RFC 6761 이
    #:  **절대 풀리지 않는다**고 정한 이름이다 — 등록 검사(이름 · IP 리터럴)는 통과하고,
    #:  나중에 발송이 떠도 밖의 실제 호스트를 두드리지 않는다.
    "U6#4": ("/api/dsm/webhook-subscriptions?endpoint_url=https://p118-gate.invalid/p118"
             "&signing_key_ref=p118-gate&event_types=fire"),
    #: 다음 단계는 **제품이 말해 주는 것**을 쓴다(`allowed_next`). 아무 값이나 밀어
    #:  넣으면 409「앞으로만 간다」가 오고 그것은 제품이 옳은 자리다.
    "U6#9": "/api/dsm/events/{event}/response?to_state={next}&reason=P-118",
    "U6#12": "/api/dsm/events?limit=1",
    "U6#15": "/api/dsm/dashboard/link-state",
}
API_BODIES = {}



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


def measure(container="gx-shell", api="http://gx-nginx-e:8500", spa="http://localhost:3002",
            keep_event_ids=(), seed_file=None):
    if _v_lock_blocks():
        return EXIT_UNDECIDABLE
    #: ★★ [P-170 ② · 턴 U · 차선 Q] **씨앗 id 는 손으로 옮기지 않는다.**
    #:   `capture_screens` 가 심고 `runs/<stamp>/seed.json` 에 적은 것을 여기서 읽는다.
    #:   `--keep-event` 를 손으로 준 것이 있으면 그것과 **합친다**(손이 이긴다는 뜻이 아니라,
    #:   둘 다 이번 회의 씨앗이라는 뜻이다). 파일이 없으면 빈 벌이고, 빈 벌이면 종전처럼
    #:   손으로 준 것만 쓴다 — **지어내지 않는다**.
    seed = load_seed(seed_file)
    keep = list(dict.fromkeys(list(keep_event_ids or []) + list(seed["event_ids"])))
    if seed["source"]:
        print("%s [씨앗] %s — 회차 %s · 사건 %s · 표식 %s"
              % (TAG, seed["source"], seed["run"] or "?", seed["event_ids"] or "없음",
                 seed["probe_mark"] or "없음"))
    else:
        print("%s [씨앗] 명세 없음 — %s" % (TAG, seed["why"]))
    keep_event_ids = keep
    pw_role = os.environ.get("GX_SEED_ROLE_PASSWORD") or ""
    pw_probe = os.environ.get("GX_PROBE_PASSWORD") or ""
    if not pw_role or not pw_probe:
        print("%s 자격이 없다 — `set -a; . ./.env.gates; set +a` 뒤에 다시 부른다" % TAG)
        return EXIT_UNDECIDABLE

    personas = {
        "U1": {"account": ["gxseed_u1_operator", pw_role], "viewport": {"width": 1440, "height": 900}},
        "U2": {"account": ["gxseed_u2_manager", pw_role], "viewport": {"width": 1440, "height": 900}},
        "U3": {"account": ["gxseed_u1_operator", pw_role], "viewport": {"width": 390, "height": 844}},
        "U4": {"account": ["gxseed_u4_official", pw_role], "viewport": {"width": 1440, "height": 900}},
        "U5": {"account": ["gxseed_u5_sysop", pw_role], "viewport": {"width": 1440, "height": 900}},
        "U6": {"account": ["gxprobe_q", pw_probe], "viewport": {"width": 1440, "height": 900}},
    }
    spec = {
        "api": api, "spa": spa, "out": "/tmp/p118_click_completes.json",
        "window_ms": CLICK_WINDOW_MS, "order": list(PERSONAS), "personas": personas,
        "flows": [dict(f) for f in FLOWS],
        "api_paths": API_PATHS, "api_bodies": API_BODIES,
        "api_actor": API_ACTOR,
        # ★ [P-132] 설정 문 한 행이 쓰는 관리자 자격. U5 의 걷기가 끝난 **뒤에만**
        #   쓰인다(사람 순서가 U1…U6 이고 U6 이 마지막이다).
        "admin_account": ["gxseed_u5_sysop", pw_role],
        "pick_user": "gxprobe_q", "pick_pw": pw_probe,
        # ★ [P-156] probe 표식 — 지난 회 씨앗 제외 · 이번 회 씨앗 유지 (`scripts/probe_marks.py`)
        "probe_tag": PROBE_TAG, "keep_event_ids": list(keep_event_ids or []),
    }
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    # 드라이버 소스는 **파일로** 넣고, SPEC 은 **stdin 으로** 넣는다 — 두 번에 나눈다
    #
    # ⚠⚠ **`DRIVER` 는 딴 프로세스다** [실측 2026-09-20 · 턴 X · 조율자가 여기서 부쉈다].
    #   이 문자열은 `/tmp/p118_driver.py` 로 써서 **gx-shell 안에서 따로 돈다** —
    #   바깥 모듈의 이름은 **거기에 없다.** 조율자가 `server_gave_value(a)` 를 이 안에
    #   써 넣었고, 모듈 최상위의 정의는 그 프로세스에 안 따라가서 **`NameError` 로
    #   48행 중 39행이 회색**이 됐다. 그리고 `--self-test` 는 **초록인 채**였다 —
    #   자기시험은 바깥 모듈만 돌기 때문이다. **측정할 때만 죽는 결함**이다.
    #   ★ 그래서 **한 벌을 더 만들지 않는다.** 정의는 모듈에 하나 두고, 그 **원문을
    #     그대로 심는다**(`inspect.getsource`). 두 벌을 두면 어긋나고, 어긋난 쪽이
    #     조용히 이긴다 — 이 저장소가 이 턴에 세 번 배운 것이다.
    import inspect
    #: ★ 표시는 **정확히 한 번** 나와야 한다. 두 번 나오면 첫 자리(머리말)가 먹히고
    #:   파일이 구문 오류가 된다 — 조율자가 턴 X 에 실제로 그렇게 부쉈다.
    if DRIVER.count(_DRIVER_SLOT) != 1:
        print("%s 드라이버 심는 자리가 %d 곳이다 — **정확히 하나**여야 한다 (턴 X)"
              % (TAG, DRIVER.count(_DRIVER_SLOT)))
        return EXIT_UNDECIDABLE
    shared_src = inspect.getsource(server_gave_value)
    driver_src = DRIVER.replace(_DRIVER_SLOT, shared_src)
    if "def server_gave_value" not in driver_src:
        print("%s 드라이버에 공용 술어를 못 심었다 — `# __SHARED_HELPERS__` 자리가 "
              "사라졌다. 심지 않고 재면 측정만 죽는다 (턴 X)" % TAG)
        return EXIT_UNDECIDABLE
    put = subprocess.run(["docker", "exec", "-i", container, "sh", "-c",
                          "cat > /tmp/p118_driver.py"], input=driver_src.encode("utf-8"),
                         env=env, capture_output=True)
    if put.returncode != 0:
        print("%s 드라이버를 넣지 못했다: %s" % (TAG, put.stderr.decode("utf-8", "replace")[:300]))
        return EXIT_UNDECIDABLE
    p = subprocess.run(["docker", "exec", "-i", container, "python", "/tmp/p118_driver.py"],
                       input=json.dumps(spec).encode("utf-8"), capture_output=True, env=env)
    sys.stderr.write(p.stderr.decode("utf-8", "replace")[-4000:])
    print(p.stdout.decode("utf-8", "replace")[-2000:])
    if p.returncode != 0:
        print("%s 드라이버가 끊겼다 (rc=%d) — **못 잰 것은 회색이다**" % (TAG, p.returncode))
    got = subprocess.run(["docker", "exec", container, "cat", "/tmp/p118_click_completes.json"],
                         capture_output=True, env=env)
    if got.returncode != 0:
        print("%s 증거를 꺼내지 못했다" % TAG)
        return EXIT_UNDECIDABLE
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    # ★ [SEC-05 · 턴 R] **저장소에 남는 순간에만** 가린다 — 컨테이너 안 드라이버는
    #   원본 URL 로 상태코드를 맞춰야 하기 때문이다(`on_resp` 는 `c["url"] == r.url`).
    #   요청을 잡는 자리에서 가리면 응답이 짝을 못 찾아 **모든 상태코드가 None** 이 되고,
    #   판정기는 401·403 을 그것으로 가르므로 여정 전체가 무너진다.
    # ★★ [P-189 · 턴 W · 차선 Q] **증거를 쓰는 자리에 utf-8 을 못 박는다 — errors 를 두지 않는다.**
    #
    #   여기가 이 저장소에서 증거 원문이 **처음 문자가 되는 자리**다. 종전에는
    #   `decode("utf-8", "replace")` 였다. 그 한 낱말이 무엇을 하느냐 —
    #   컨테이너가 utf-8 이 아닌 바이트를 한 개라도 흘리면 그 자리를 U+FFFD 로
    #   **조용히 바꿔 놓고 계속 간다.** 그렇게 쓰인 파일은 여전히 **JSON 으로 파싱되고**
    #   판정기도 **초록을 내며 수를 말한다** — 다만 그 수가 틀렸다.
    #
    #   [실측 2026-09-19 · 턴 W] 지금 증거(29/48)의 한글만 cp949 왕복으로 깨뜨려
    #   같은 판정기에 먹였더니 **8/48** 이 나왔다(초록 21개가 빨강으로 내려앉는다).
    #   깨진 것은 파싱 오류를 내지 않는다 — 네 칸 중 ④ 화면 문구가 안 맞을 뿐이다.
    #   그러므로 **소리 없이 틀린 수**가 보고서에 실린다. 그것이 P-189 다.
    #
    #   그래서 여기서는 무르게 읽지 않는다. 깨진 바이트를 만나면 **쓰지 않고 회색**이다 —
    #   「깨진 증거를 남기는 것」보다 「증거가 없는 것」이 정직하다.
    try:
        _text = got.stdout.decode("utf-8")           # errors 없음 — 무르게 읽지 않는다
    except UnicodeDecodeError as exc:
        print("%s 증거가 utf-8 이 아니다 (%s) — **쓰지 않는다.** 깨진 증거는 "
              "파싱은 되고 수만 틀린다(P-189). 컨테이너 쪽 출력 인코딩을 먼저 본다"
              % (TAG, exc))
        return EXIT_UNDECIDABLE
    _redacted = _redact_credentials(_text)
    OBSERVED.write_text(_redacted, encoding="utf-8", newline="\n")
    # 쓴 즉시 **다시 읽어** 같은 것이 나오는지 본다 (P-189 · 「썼다」가 아니라 「다시 읽으니 같더라」)
    _back = OBSERVED.read_text(encoding="utf-8")
    _ok, _lines, _facts = evidence_roundtrip(_text, _redacted, _back)
    for _ln in _lines:
        print("%s   %s" % (TAG, _ln))
    if not _ok:
        print("%s 증거를 믿을 수 없다 (P-189) — **회색이다.** 위 줄이 어느 칸인지 말한다" % TAG)
        return EXIT_UNDECIDABLE
    print("%s 실측 기록 → %s (쓰고 다시 읽어 같음을 확인 · P-189)"
          % (TAG, OBSERVED.relative_to(ROOT)))
    return EXIT_OK


# ──────────────────────────────────────────────────────────────────────────
#: ★ [SEC-05 · 턴 R] 증거는 **자격을 나르지 않는다.**
#:
#: [실측 2026-09-16] 브라우저가 지도를 그리려고 부른
#: `dapi.kakao.com/v2/maps/sdk.js?appkey=…` 가 그대로 증거에 적혔고,
#: `verify_secret_scan` 이 「저장소가 나른다」로 멈춰 세웠다. 그 키는 번들에 구워져
#: 나가는 공개용 클라이언트 키라 **유출은 아니지만**, 이 파일은 우리가 **커밋하는**
#: 파일이다 — 저장소가 그것을 나르기 시작하면 다음에 진짜로 새는 값과 구별되지 않는다.
#:
#: 허용 목록(`.gitleaksignore`)에 넣어 스캐너를 무르게 하는 길은 쓰지 않았다 —
#: 그 길은 **다음에 진짜로 새는 값을 가린다**(같은 턴에 `P-151/iso_guard.py` 에서도
#: 같은 판단을 했다: 스캐너는 뜻이 아니라 모양을 본다).
#:
#: ⚠ 범위를 **좁게** 잡는다. 우리 라우트의 질의(`event_id`·`limit`·`name`·`preset`)는
#:   `_cell_call` 이 정규식으로 맞추는 자리라 건드리면 멀쩡한 초록이 빨강이 된다.
#:   그래서 **자격 이름이 붙은 값만** 가린다.
#: ⚠ 문자 클래스에 역슬래시를 넣지 않는다 — 값은 JSON 문자열 안에 있어 `&` 아니면
#:   `"` 에서 끝난다. 역슬래시를 넣으면 이 줄을 셸로 옮겨 적는 날 조용히 깨진다
#:   (실측: 같은 패턴을 heredoc 으로 넣다 두 번 깨졌다).
_CRED_IN_URL = re.compile(
    r'([?&](?:appkey|api_?key|token|secret|password|access_key|signature)=)([^&"]+)',
    re.I)


def _redact_credentials(text: str) -> str:
    """증거 원문에서 자격이 실린 질의 값을 가린다. **이름과 자리는 남긴다** —
    무엇이 불렸는지는 증거이고, 그 값만 증거가 아니다."""
    return _CRED_IN_URL.sub(lambda m: m.group(1) + "REDACTED-자격은-증거에-적지-않는다",
                            text)


def evidence_roundtrip(raw: str, written: str, read_back: str):
    """P-189 — 증거를 쓰고 **다시 읽어** 같은지 본다. 칸을 **둘로 나눈다.**

        ① **되읽기**   쓴 것 == 다시 읽은 것          ← 인코딩·줄바꿈 손상을 잡는다
        ② **가리기**   가리기 전후의 **수가 같은가**  ← 가리기는 정당한 변형이다

    ★★ **[턴 W · 2차 · V 실측] 이 함수가 태어난 사유 — 내가 만든 거짓 회색.**
      처음 넣은 판은 ①을 「**가리기 전 원문** == 쓴 파일」로 견줬다. 그런데 증거에는
      카카오 지도 `appkey=` 가 **18곳** 있어 `_redact_credentials` 가 **언제나** 작동한다.
      그래서 그 비교는 **언제나 어긋났고**, `--measure` 는 증거가 멀쩡한데도 **매번 회색**
      으로 끝났다. V 가 컨테이너 원본과 저장소 사본을 `appkey` 만 맞춰 대 보니
      **135,139 → 134,977 바이트 · 차이는 가린 문자열뿐**이었다. 증거는 유효했고
      **게이트가 아니라고 말한 것**이다.

      ⚠ **거짓 초록만 위험한 것이 아니다. 거짓 회색도 위험하다.** 회색은 조용하고,
        몇 턴 지나면 「FC 는 원래 회색이야」가 된다 — 그러면 내가 막으려던 바로 그 일이
        **게이트 뒤에 숨어서** 벌어진다.

      ⚠ 고치면서 **약하게 만들지 않는다.** 가리기를 검사에서 그냥 빼면 「가리기가 수를
        바꿔도 아무도 안 본다」가 된다. 그래서 그 칸을 **②로 따로** 세웠다 — 가린 자리
        수를 적고, **가리기 전후의 판정 수가 같은지**를 본다(자리 수만 세는 것보다 강하다).

    돌려주는 것: `(성립했나, 적을 줄들, 셈)`.
    """
    facts: dict = {}
    try:
        w, b = json.loads(written), json.loads(read_back)
    except ValueError as exc:
        return False, ["① 되읽기: 쓴 것이나 다시 읽은 것이 JSON 이 아니다 — %s" % exc], facts
    if w != b:
        return False, ["① 되읽기: **쓴 것과 다시 읽은 것이 다르다** — "
                       "인코딩이나 줄바꿈이 손상됐다. 이 증거로 잰 수는 수가 아니다"], facts
    lines = ["① 되읽기: 쓴 것과 다시 읽은 것이 **같다**"]

    n = len(_CRED_IN_URL.findall(raw))
    facts["가린 자리"] = n
    try:
        r = json.loads(raw)
    except ValueError as exc:
        return False, lines + ["② 가리기: 가리기 전 원문이 JSON 이 아니다 — %s" % exc], facts
    s_raw = score(judge(r.get("observations") or {}))
    s_new = score(judge(w.get("observations") or {}))
    facts["수(가리기 전)"], facts["수(가린 뒤)"] = s_raw, s_new
    if s_raw != s_new:
        return False, lines + [
            "② 가리기: **가리기가 수를 바꿨다** %s → %s — 가리기는 자격 **값만** 지워야 "
            "한다. 수가 움직였다면 지운 것이 값이 아니다" % (s_raw, s_new)], facts
    lines.append("② 가리기: 자격 **%d곳**을 가렸고 **수는 그대로다** %s "
                 "(가리기는 정당한 변형이지 손상이 아니다)" % (n, s_raw))
    return True, lines, facts


def load():
    if not OBSERVED.exists():
        return None, "증거가 없다 (%s)" % OBSERVED.relative_to(ROOT)
    doc = json.loads(OBSERVED.read_text(encoding="utf-8"))
    when = doc.get("measured_at") or ""
    try:
        t = datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
    except ValueError:
        return doc, "실측 시각을 못 읽었다 (%r)" % when
    if age > MAX_AGE_HOURS:
        return doc, "증거가 %.1f시간 낡았다 (한도 %d시간) — 화면은 매 턴 바뀐다" % (age, MAX_AGE_HOURS)
    return doc, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true", help="판정 규칙만 (브라우저 없이)")
    ap.add_argument("--measure", action="store_true", help="gx-shell 안에서 실제로 누른다")
    ap.add_argument("--list", action="store_true", help="흐름별 네 칸")
    ap.add_argument("--container", default="gx-shell")
    ap.add_argument("--api", default="http://gx-nginx-e:8500")
    ap.add_argument("--spa", default="http://localhost:3002")
    ap.add_argument("--keep-event", type=int, action="append", default=[],
                    help="[P-156] 이번 회에 심은 probe 씨앗 id — 표본에서 빼지 않는다 (여러 번 가능)")
    ap.add_argument("--seed-file", default=None,
                    help="[P-170 ②] capture_screens 가 쓴 씨앗 명세 "
                         "(기본: docs/agent/evidence/P-157/runs/ 의 최신 seed.json)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.measure:
        rc = self_test()
        if rc != EXIT_OK:
            print("%s 자기시험이 깨졌다 — 재지 않는다" % TAG)
            return rc
        return measure(args.container, args.api, args.spa,
                       keep_event_ids=args.keep_event, seed_file=args.seed_file)
    if args.list:
        for f in FLOWS:
            print("%-7s %-26s | 누르는 것 %-14s | 기대 호출 %-8s %-42s | 상태 %-15s | 문구 %s"
                  % (f["key"], f["title"][:26],
                     (f["control"] or {}).get("name", (f["control"] or {}).get("kind", "—")),
                     (f["call"] or ("—", "—"))[0], (f["call"] or ("—", "—"))[1],
                     (f["state"] or {}).get("kind", "—"), " · ".join(f["text"]) or "—"))
        return EXIT_OK

    rc = self_test()
    if rc != EXIT_OK:
        return rc
    print("")

    doc, stale = load()
    obs = (doc or {}).get("observations") or {}
    if stale:
        print("%s ⚠ %s" % (TAG, stale))
    rows = judge(obs if not stale else {})
    g, r, y = score(rows)

    # ★ 모수와 술어를 **먼저** 적는다. 안 적으면 행마다 판정이 달라지고,
    #   무엇을 보고 한 말인지 모르는 초록은 초록이 아니다 (D-301).
    print("%s [입력] %d건 — 온보딩 48행(여섯 사람 × 여덟, docs/agent/onboarding_48.md)" % (TAG, len(FLOWS)))
    print("%s        술어: ① 누를 것이 **실재하는가** · ② 누른 뒤 그 요청이 **나갔는가** · "
          "③ **새 GET 으로 다시 읽어** 값이 변했는가 · ④ 그 뒤 화면이 **그 말을 하는가** "
          "— 넷이 다 서야 초록. 하나라도 못 재면 회색, 재서 안 되면 빨강" % TAG)
    print("%s **%d/48** — 초록 %d · 빨강 %d · 회색 %d   [실측 %s · TARGET=%s]"
          % (TAG, g, g, r, y, (doc or {}).get("measured_at", "없음"),
             (doc or {}).get("spa", "—")))
    print("%s 사람별: %s" % (TAG, " · ".join(
        "%s %d/8" % (p, sum(1 for k, c, _, _, _ in rows
                            if c == GREEN and k.startswith(p + "#"))) for p in PERSONAS)))
    print("")
    mark = {GREEN: "O", RED: "X", GREY: "?"}
    for key, color, why, cells, flow in rows:
        c4 = "".join("O" if cells[n] else ("?" if cells[n] is None else "X")
                     for n in ("control", "call", "state", "text"))
        print("  %s %-7s %-4s %-26s %s" % (mark[color], key, c4, flow["title"][:26], why))

    # ★ [턴 U · 절 4] **되돌림 셈** — 게이트가 남긴 상태는 다음 게이트의 거짓 빨강이다
    want_rev = [f["key"] for f in FLOWS
                if (f.get("revert") or {}).get("kind") == "same_control"]
    if want_rev:
        done, failed, notrun = [], [], []
        for k in want_rev:
            rv = (obs.get(k) or {}).get("revert")
            if not rv or not rv.get("clicked"):
                (notrun if not rv else failed).append(
                    (k, (rv or {}).get("why", "이번 판에 그 행을 못 눌렀다")))
            elif rv.get("restored") is False:
                failed.append((k, rv.get("why", "값이 처음과 다르다")))
            else:
                done.append(k)
        print("")
        print("%s [되돌림] 선언 %d자리 — 되돌림 %d · 못 되돌림 %d · 안 눌림 %d "
              "(상태를 바꾸는 클릭은 판정 뒤 같은 문으로 되돌린다)"
              % (TAG, len(want_rev), len(done), len(failed), len(notrun)))
        for k, w in failed:
            print("%s   ★ %s 를 되돌리지 못했다 — %s. **지금 남은 상태를 손으로 되돌린다**"
                  % (TAG, k, w))

    reds = [(k, w) for k, c, w, _, _ in rows if c == RED]
    family = [(k, w) for k, w in reds if w.startswith("요청은 나갔는데")]
    dead = [(k, w) for k, w in reds if w.startswith("눌렀는데")]
    print("")
    if dead:
        print("%s ★ **눌렀는데 아무것도 나가지 않는다** %d건 — 2026-09-08 의 그 모양:" % (TAG, len(dead)))
        for k, w in dead:
            print("      %-7s %s" % (k, w))
    if family:
        print("%s ★★ **요청은 나갔는데 값이 안 바뀐다** %d건 — 이 결함의 가족:" % (TAG, len(family)))
        for k, w in family:
            print("      %-7s %s" % (k, w))
    greys = [(k, w) for k, c, w, _, _ in rows if c == GREY]
    if greys:
        print("%s 회색 %d건 — **못 쟀다. 초록이 아니다.** 이름을 적는다:" % (TAG, len(greys)))
        for k, w in greys:
            print("      %-7s %s" % (k, w))

    print("")
    if r:
        print("%s 빨강 %d — **누른 뒤가 안 끝난다.** 그려진 것으로 점수를 주지 않는다" % (TAG, r))
        return EXIT_FAIL
    if y:
        print("%s 회색 %d — **못 쟀다.** 못 잰 것은 통과가 아니다" % (TAG, y))
        return EXIT_UNDECIDABLE
    print("%s 48/48 — 누른 것이 전부 끝까지 갔다" % TAG)
    return EXIT_OK


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE (stderr 로 나간다)

    _m = "--measure" in sys.argv
    gate_header(
        __file__,
        target=("gx-shell 안 SPA http://localhost:3002 (/app/_fe_dist) 를 **실제 브라우저로 누른다** · "
                "API 는 gx-nginx-e:8500 (실 MinIO 자격) — 번들이 부르는 localhost:8000 을 그리로 잇는다"
                if _m else
                "실측 증거 docs/agent/evidence/P-118/click_completes.json 을 읽어 판정한다"),
        as_=("여섯 사람의 계정으로 **각각 로그인해서** 누른다: gxseed_u1_operator · "
             "gxseed_u2_manager · gxseed_u4_official · gxseed_u5_sysop · gxprobe_q "
             "(비밀번호는 저장소 밖 .env.gates 의 GX_SEED_ROLE_PASSWORD · GX_PROBE_PASSWORD)"
             if _m else "(자격증명 없음 — 증거 파일을 읽는다)"),
        source=("살아 있는 브라우저가 낸 네트워크 기록 + **누른 뒤 새로 부른 GET** 의 응답 "
                "— 소스에 적힌 글자가 아니다" if _m else None) or "",
    )
    raise SystemExit(main())
