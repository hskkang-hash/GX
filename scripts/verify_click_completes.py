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
from probe_marks import PROBE_TAG  # noqa: E402

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
def F(key, title, actor, screen, control, call, state, text, confirm=None, note="",
      fill=None, img_check=False):
    """한 흐름.

    `fill` — 누르기 **전에** 채워야 하는 글상자의 `placeholder` (P-132).
      왜 필요한가: 제품이 **일부러** 빈 글상자에서 단추를 잠그는 자리가 있다
      (「회신 보내기」는 글이 비면 `disabled` 다 — `MobileEventDetail.tsx:481`).
      채우지 않고 눌러 「안 눌린다」를 적으면 **제품의 규율을 고장으로 파는 것**이다.
      ★ 이것은 면제가 아니다 — 채운 뒤에도 ②③④ 는 그대로 다 서야 한다.

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
        "state": state, "text": text, "note": note, "fill": fill,
        "img_check": img_check,
    }


def btn(name):
    return {"kind": "button", "name": name}


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
      {"kind": "route_change", "from": "/login"}, ["가장 급한 하나"]),
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
      note="사유 필수 · 확인창을 지나는 길 · 종결된 사건에서만 그려진다"),
    F("U2#4", "심각 이벤트 상황 판단", "u2", "/dsm/events/{event}", goto(),
      ("GET", r"/api/dsm/events/\d+$"),
      srv_reflect("/api/dsm/events/{event}", "severity"), ["심각", "critical", "대응"]),
    #: ★ [P-132] `GET /api/dsm/reports/templates` 는 **서 있다**(`api.py:750`). 그러나
    #:  그 문을 부르는 화면이 저장소에 **없다** — `/report-template` 은 인수 자산의
    #:  운송장 서식 화면이고 부르는 문은 `/api/report-template/`(`services/API.ts:819`)다.
    #:  즉 「그려졌다 ≠ 동작한다」가 아니라 **아직 안 그려졌다**. 그 사실을 빨강으로
    #:  적으면 남의 화면을 우리 결함으로 파는 것이 된다.
    F("U2#6", "상황보고서 생성", "u2", None, None, None, None, [],
      note="정본 없음 — 서버 문(GET /api/dsm/reports/templates · api.py:750)은 서 있으나 "
           "그것을 부르는 화면이 없다. /report-template 은 인수 자산의 운송장 서식이다"),
    F("U2#9", "요원별 처리 현황", "u2", None, None, None, None, [],
      note="정본: 집계 면 없다 — 사람별로 세는 자리가 없다"),
    F("U2#16", "알림 규칙 확인", "u2", None, None, None, None, [],
      note="정본: 조회 라우트·화면 없다 · 규칙 0건"),
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
      srv_change("/api/dsm/deliveries?event_id={event}&limit=500", "total"), ["발송", "알림"]),
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
      srv_change("/api/dsm/events/{event}", "response_state"), ["접수", "조치", "종결"]),
    #: ★ [P-132] 단추 이름은 **「회신 보내기」**다 (`MobileEventDetail.tsx:484`).
    #:  그리고 이 단추는 글상자가 비면 `disabled` 다(같은 파일 481행) —
    #:  그래서 **글을 먼저 채운다**(`fill` 은 아래 드라이버가 한다).
    #:  바뀌는 칸은 `response_state` 가 아니라 **회신 건수**다:
    #:  `GET /api/dsm/events/{id}/field-replies` 가 그 목록을 낸다(`api.ts:51`).
    F("U3#9", "현장 상황 한 줄 보고", "u3", "/m/events/{event}", btn("회신 보내기"),
      ("POST", r"/api/dsm/events/\d+/field-reply"),
      srv_change("/api/dsm/events/{event}/field-replies", "replies"), ["회신", "현장"],
      fill="현장에서 본 것을 한 줄로 적습니다."),
    F("U3#14", "해당 카메라 모바일 실시간", "u3", None, None, None, None, [],
      note="정본: 없음 — 구간 티켓은 계약 11조 잠김"),
    F("U3#16", "근무 외 알림 차단", "u3", None, None, None, None, [],
      note="정본: 없음 — 알림 채널 결정 대기"),
    F("U3#19", "내가 처리한 이벤트 목록", "u3", "/m/inbox", goto(),
      ("GET", r"/api/dsm/deliveries"),
      srv_reflect("/api/dsm/deliveries?limit=20&mine=true", "deliveries"),
      ["내가", "발송", "이력", "처리"]),

    # ── U4 · 재난안전과 담당 공무원 ──────────────────────────────────────
    F("U4#1", "주간 상황 요약", "u4", None, None, None, None, [],
      note="정본: 라우트는 hours=168 을 받지만 **누를 자리가 없다**"),
    #: ★ [P-132] `/report-template` 은 **인수 자산의 운송장 서식 화면**이고 부르는 문은
    #:  `/api/report-template/`(`services/API.ts:819`) 다 — `/api/dsm/reports` 가 아니다.
    #:  그리고 `POST /api/dsm/reports` 라는 문은 **저장소에 없다**
    #:  [실측 `backend/apps/dsm/api.py` 의 `@route.post` 전부 — 보고서 생성 문 0개].
    #:  U4 의 「보고서」 줄이 사이드바에 안 걸린 사유도 같다
    #:  (`features/nav/roleNav.ts:143` 「그리는 화면이 라우터에 없다」).
    F("U4#5", "월간 보고서 자동 생성", "u4", None, None, None, None, [],
      note="정본 없음 — 월간 보고서를 만드는 문도(POST /api/dsm/reports 없음) "
           "그리는 화면도 없다 (roleNav.ts:143 P61_NO_SCREEN_YET 「보고서」)"),
    #: ★ [P-132] 서버가 내는 종이는 **하나**다 — `GET /api/dsm/events/{id}/report.pdf`
    #:  (`backend/apps/dsm/api.py:802` UX-30 사건 보고서 1쪽). 그런데 그 주소를 부르는
    #:  화면이 저장소에 **없다**(frontend 전체에 `report.pdf` 참조 0건).
    #:  종전 기대식이 가리키던 `/api/dsm/reports/{template_id}.pdf` 는 **운송장 서식**이다
    #:  (같은 파일 766행 · 그 표 19행은 전부 택배다 — 800행 주석).
    F("U4#7", "보고서 다운로드", "u4", None, None, None, None, [],
      note="정본 없음 — 서버 문은 GET /api/dsm/events/{id}/report.pdf 하나인데 "
           "그것을 누르는 화면이 라우터에 없다 (api.py:802 · 프런트 참조 0건)"),
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
    F("U4#15", "상급기관 제출 자료", "u4", None, None, None, None, [],
      note="정본: 없음 — 상급기관 서식 T4"),
    F("U4#16", "감사 대응 이력", "u4", None, None, None, None, [],
      note="정본: 감사는 쌓이는데 **볼 자리가 없다**"),

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
      note="정본 없음 — 단추는 있으나(App.tsx:728 「사용자 추가」) 그것은 서식 화면으로 "
           "가는 링크다. 계정 생성은 다음 화면의 서식을 채워야 끝난다 · "
           "그 문은 프리플라이트 401 로 끊겨 있다(P-125 A절 · 보안 차선)"),
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
      note="정본 없음 — 자리는 /dsm/cameras/import(routes.ts:23 · roleNav.ts:132)이나 "
           "「표 먼저, 그 다음 적용」이 세 걸음이고 매번 새 시험 자료가 필요하다. "
           "한 번 누름으로 재는 정본이 없다"),
    #: ★ [P-132] 「저장」이라는 단추는 없다 — `CameraAddress.tsx:177·185` 의
    #:  **「표 먼저 보기」 · 「채우기」** 둘뿐이고, 둘 다 이름·주소를 채우기 전에는
    #:  `disabled` 다(`ready`, 같은 파일 88행). 「채우기」는 표를 본 뒤에만 열린다(182행).
    #:  U5#4 와 같은 사유로 **한 번 누름의 정본이 없다.**
    F("U5#5", "카메라 설치 주소 입력", "u5", None, None, None, None, [],
      note="정본 없음 — 단추는 「표 먼저 보기」·「채우기」(CameraAddress.tsx:177·185)이고 "
           "둘 다 입력 전에는 잠겨 있다. 「표 먼저, 그 다음 채움」이 두 걸음이다"),
    #: ★ [턴 T · U56] 설정 화면(`/dsm/notify`)이 턴 S 에 섰고, 「끄기/켜기」 한 번 누름이
    #:  턴 T 에 생겼다(NotifySettings.tsx · `data-gx=notify-rule-saved`). 옛 note 「화면·라우트
    #:  없다」는 턴 S 이후 옛말이었다 — 정본 없음을 그대로 두면 영원히 회색이다.
    #:  ⚠ 심각 등급 행은 서버가 409 로 막는다(심각 0명 금지) — 정보/경고 행의 단추를 누른다.
    F("U5#9", "알림 규칙 설정", "u5", "/dsm/notify", btn("^(끄기|켜기)$"),
      ("POST", r"/api/dsm/settings/notify-rules/save"),
      srv_reflect("/api/dsm/settings/notify-rules/list", "rules"), ["저장했습니다", "규칙 #"]),
    F("U5#10", "알림 채널 설정", "u5", None, None, None, None, [],
      note="정본: 없음 — 알림 채널 결정 대기(대표)"),
    F("U5#14", "시스템 상태 확인", "u5", "/dsm/system", goto(),
      ("GET", r"/api/dsm/(dashboard/link-state|ops/)"),
      srv_reflect("/api/dsm/dashboard/link-state", "status"), ["상태", "시스템", "연계"]),
    F("U5#15", "저장 용량 확인", "u5", "/dsm/system", goto(),
      ("GET", r"/api/dsm/ops/"),
      srv_reflect("/api/dsm/dashboard/link-state", "status"), ["용량", "저장", "GB"],
      note="정본: 신호는 ops_monitor 안에만 있다 — 읽는 라우트가 없다"),

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
      note="정본: 없음 — 스키마 버전"),
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


def _cell_state(o):
    s = o.get("state") or {}
    kind = s.get("kind")
    if not kind:
        return None, "상태 규격이 없다"
    if s.get("error"):
        return None, "다시 읽지 못했다: %s" % s["error"]
    if kind == "server_change":
        before, after = s.get("before"), s.get("after")
        if before == after:
            return False, "다시 읽었는데 `%s` 가 그대로다 (%r)" % (s.get("field"), before)
        return True, "`%s` %r → %r" % (s.get("field"), before, after)
    if kind == "server_reflect":
        after = s.get("after")
        if after in (None, "", [], {}, 0):
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


def self_test() -> int:
    ok = True

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

    print("%s 자기시험 %s" % (TAG, "통과" if ok else "**실패**"))
    return EXIT_OK if ok else EXIT_FAIL


# ──────────────────────────────────────────────────────────────────────────
# 실측 — gx-shell 안에서 **실제로 누른다**
# ──────────────────────────────────────────────────────────────────────────
DRIVER = r'''# -*- coding: utf-8 -*-
"""P-118 실측 드라이버 — gx-shell 안에서 돈다. **누르고, 나간 것을 세고, 다시 읽는다.**"""
import json, os, re, sys, threading, time
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
            note(key, control={"found": False, "why": "정본이 「없음」이라 적은 자리 — " + (f["note"] or "")})
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
                try:
                    box = page.get_by_placeholder(f["fill"])
                    if box.count():
                        box.first.fill("P-118 게이트 측정 (자동) — 현장 이상 없음")
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
                    st["on_screen"] = bool(a) and (str(a) in hay or any(
                        w.lower() in hay.lower() for w in ["행", "건", "개"]) and len(hay) > 400)

        note(key, control={"found": True, "clicked": True,
                           "name": f["control"].get("name", "화면 열기")},
             calls=got, state=st, text_after=(text_after or "")[:6000],
             **({"img": img_obs} if img_obs is not None else {}))

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


def measure(container="gx-shell", api="http://gx-nginx-e:8500", spa="http://localhost:3002",
            keep_event_ids=()):
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
    put = subprocess.run(["docker", "exec", "-i", container, "sh", "-c",
                          "cat > /tmp/p118_driver.py"], input=DRIVER.encode("utf-8"),
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
    OBSERVED.write_text(_redact_credentials(got.stdout.decode("utf-8", "replace")),
                        encoding="utf-8")
    print("%s 실측 기록 → %s" % (TAG, OBSERVED.relative_to(ROOT)))
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
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.measure:
        rc = self_test()
        if rc != EXIT_OK:
            print("%s 자기시험이 깨졌다 — 재지 않는다" % TAG)
            return rc
        return measure(args.container, args.api, args.spa, keep_event_ids=args.keep_event)
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
