#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-106 — **영역 ① 기능 완결성에 게이트를 준다** (2026-09-07 · 턴 M · 차선 Q).

왜 이 게이트가 생겼나 — **가중 20%가 아무 색도 안 내고 있었다**
----------------------------------------------------------------
[실측 2026-09-07 · 턴 L]
`docs/agent/evidence/D-346/ga_readiness.yaml` 의 여덟 영역 중 **①만 `gate:` 가 0개**다.
그래서 `verify_ga_readiness.py` 의 여덟째 눈(P-85 · **대장 상태 = 게이트 색**)이
①을 **통째로 건너뛴다.** 82.2 라는 수의 **20%가 아무에게도 안 물어본 수**였다.

    ① 기능 완결성  가중 20%  절 32/39 = 82%  →  16.41   ← 이 16.41 을 아무도 안 쟀다

무엇을 재는가 — **사슬 다섯이 이어져야 한 절이 초록이다**
---------------------------------------------------------
    절  ↔  화면  ↔  라우트  ↔  **역할 계정의 200**  ↔  data_source

  ① **절**          계약 절 대장(D-309)의 39절. 분모를 손으로 적지 않는다.
  ② **화면**        그 절이 사람에게 닿는 자리. `D-347/screens/INDEX.yaml` 의 32장.
  ③ **라우트**      그 화면이 실제로 부른 API. 인덱스의 `calls` 가 적는다.
  ④ **역할 계정**   ★★ 이 자리가 턴 L 의 사고다. `walk_scenarios.py` 와
                    `verify_screens.py` 가 **역할이 0개인 `gxprobe_e2e`** 로 걸으면서
                    「걷기 3/3 · 콘솔 0」을 냈다. 그것은 「됐다」가 아니라
                    **「거기까지 못 갔다」**였다. 그래서 여기서는 `viewed_by` 가
                    **역할을 든 계정**이어야 하고, 상태는 **200** 이어야 한다.
  ⑤ **data_source** `모의` 로 찍은 화면은 제품이 낸 답이 아니다. 초록이 될 수 없다.

색 넷 — **못 이은 것은 초록이 아니고, 빨강도 아니다**
----------------------------------------------------
    초록   다섯 고리가 다 이어졌다
    빨강   사슬이 있는데 **끊겼다** — 200 이 아니다 · 역할 0 이다 · 모의다
    회색   사슬을 **못 만들었다** — 그 절에 화면이 없다 (D-301: 못 잰 것은 통과가 아니다)
    잠김   계약이 조건부로 잠가 둔 절 (SDN 명세 · 구간 추출). 판정 대상이 아니다

★ **회색이 나오면 수가 내려간다. 그것이 이 게이트의 산출이다.**
  세종 판정(턴 M): 「상용 /100 이 내려가도 좋다. 나오는 대로 보고하라.」
  올리려고 사슬을 느슨하게 하는 순간 이 파일은 도구가 아니라 장식이다.

★ 출생 표본 (D-310) — 셋 다 실측이고 합성이 아니다
--------------------------------------------------
  ㉠ **역할 0 으로 걸은 초록** — 턴 L 의 `walk 3/3`. `viewed_by` 에 역할이 없으면 빨강.
  ㉡ **모의로 찍은 화면** — `login_locked.png` 는 서버의 잠금 본문을 **주입**해 찍었다.
     그 장으로 「잠금이 된다」를 초록으로 적으면 제품이 아니라 주입기를 잰 것이다.
  ㉢ **404 인데 화면은 떴다** — `/m/events/99554` 의 `GET …/clip` 은 **404** 다
     (구간 추출 잠김). 화면이 떴다는 것과 그 절이 닿았다는 것은 다른 사실이다.

    python scripts/verify_feature_reach.py            # 판정
    python scripts/verify_feature_reach.py --list     # 절별 사슬
    python scripts/verify_feature_reach.py --json     # 영역 ① 이 쓸 셈 (기계용)
    python scripts/verify_feature_reach.py --self-test

exit 0 끊긴 사슬이 없다 · 1 **빨강이 있다** · 2 못 쟀다(증거 파일이 없다)
호스트에서 돈다 — Django 가 필요 없다. `via: gate` 인 절은 그 게이트를 **부른다**(D-210).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:                                       # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

CONTRACT = ROOT / "docs" / "agent" / "evidence" / "D-309" / "contract_ac_ledger.yaml"
INDEX = ROOT / "docs" / "agent" / "evidence" / "D-347" / "screens" / "INDEX.yaml"
SCREEN_ROUTES = ROOT / "docs" / "agent" / "evidence" / "D-386" / "screen_routes.json"
OUT_JSON = ROOT / "docs" / "agent" / "evidence" / "P-106" / "feature_reach.json"

#: ★ P-149 — **row_map 을 입력으로 읽는다.**
#:   그 전까지 사슬 선언은 이 파일 안(REACH_MAP)에만 있었다. 그래서 증거를 아무리 쌓아도
#:   수가 움직이지 않았고, P-142 가 그 사실을 스스로 적어 두었다:
#:     「판정기는 row_map 을 읽지 않는다 … 곧 이 파일로 수가 움직이는 길은 없다」
#:   두 벌을 읽는다 — 하나는 **절 단위**(회색 25 를 절마다 두드린 것 · P-142),
#:   하나는 **페인 18행**(행 → 화면·라우트·시험·역할 계정 캡처 · P-106).
#:
#:   ⚠ **이 파일들은 초록을 만들지 못한다.** 행이 「이었다」(`linked: true`)고 적어도
#:     그것은 **가설**이고, 캡처·라우트·시험 세 짝을 이 판정기가 다시 확인한다.
#:     하나라도 없으면 회색이다. 손으로 절을 초록으로 만드는 길은 여기에도 없다.
ROW_MAP_CLAUSE = ROOT / "docs" / "agent" / "evidence" / "P-142" / "row_map.json"
ROW_MAP_PAIN = ROOT / "docs" / "agent" / "evidence" / "P-106" / "row_map.json"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[REACH]"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

GREEN, RED, GREY, LOCKED = "초록", "빨강", "회색", "잠김"

#: `data_source` 앞머리. **모의는 제품의 답이 아니다.**
SOURCE_MEASURED = ("실측", "시드")
SOURCE_FAKE = "모의"

#: `viewed_by` 가 역할을 들지 않은 자리들. 턴 L 의 사고가 정확히 이 모양이었다.
NO_ROLE_MARKS = ("아직 누구도 아니다", "역할 0", "NO_ROLE", "gxprobe_e2e")


# ═══════════════════════════════════════════════════════════════════════════
# 사슬 선언 — **이 표는 초록을 만들지 못한다. 가설만 적는다.**
#
#   여기 적은 화면·라우트가 인덱스에 없거나, 200 이 아니거나, 역할 0 이 봤거나,
#   모의였다면 그 절은 **빨강**이 된다. 즉 잘못 적으면 수가 **내려간다** —
#   손으로 적은 목록이 초록을 만드는 길이 없다(턴 L 의 분모 30 이 그 길이었다).
#
#   적지 못한 절은 **회색**이고, 회색마다 「왜 못 이었나」를 적는다 (D-301).
# ═══════════════════════════════════════════════════════════════════════════
REACH_MAP: dict[str, dict] = {
    # ── 화면으로 닿는 절 ────────────────────────────────────────────────
    "F-01-c2": {
        "screen": "/dsm/events", "api": "/api/dsm/events", "expect": 200,
        "why": "저장된 이벤트가 목록 화면에 실제로 실려 나온다 — 역할 fire_user 가 200 으로 봤다",
    },
    "F-09-c2": {
        "screen": "/dsm/events/{id}", "api": "/api/dsm/events/{id}", "expect": 200,
        "why": "이벤트 클릭 → 상세. 그 클릭이 실제로 부른 라우트가 200 이다",
    },
    "F-10-c3": {
        "screen": "/dsm/events/{id}", "api": "/api/dsm/deliveries", "expect": 200,
        "why": "발송 기록이 이벤트 상세에서 실제로 조회된다 (deliveries?event_id=…)",
    },
    "F-14-c1": {
        "screen": "/dsm/events/{id}", "api": "/api/dsm/events/{id}/timeline",
        "expect": 200, "file_hint": "verdict_panel",
        "why": "사람의 판정이 남는 자리(판정 패널·타임라인)를 역할 계정이 200 으로 봤다",
    },

    # ── 화면이 아니라 **다른 게이트**로 닿는 절 ─────────────────────────
    #   U6(외부 App)은 화면이 없다 — HTTP 로만 들어온다. 그 절의 도달을 화면에서
    #   찾으면 영원히 회색이 된다. 그래서 그 절을 재는 게이트를 **부른다**(D-210).
    "F-05-c1": {"gate": "scripts/verify_contract_route_reach.py",
                "why": "외부 App 의 진입면은 화면이 아니라 라우트다 — 그 게이트가 문을 두드린다"},
    "F-05-c2": {"gate": "scripts/verify_contract_route_reach.py",
                "why": "이벤트 OpenAPI 진입면 — 위와 같은 게이트가 잰다"},
    "F-05-c3": {"gate": "scripts/verify_contract_route_reach.py",
                "why": "API Key 발급·폐기도 그 진입면 위에 있다"},
}

#: 사슬을 **못 만든** 절. 회색에는 반드시 사유가 붙는다 — 0건에 사유를 요구하는
#: 그 규칙 그대로다(D-301). 사유 없는 회색은 「잊은 것」과 구별되지 않는다.
GREY_WHY: dict[str, str] = {
    "F-01-c1": "AI 라벨 → 이벤트 변환은 화면에 나타나지 않는다. 단위 시험만 있고, 사람이 그 절을 보는 자리가 없다",
    "F-02-c1": "수위선 초과 신호를 보여 주는 화면이 32장 안에 없다",
    "F-02-c2": "30초 이내라는 **시간**은 화면 한 장으로 재지지 않는다 — 시간 게이트가 따로 있어야 한다",
    "F-02-c3": "지점별 기준선(임계값) 설정 화면을 찍지 못했다 — `/operation-settings` 는 설정 API 를 한 건도 부르지 않았다 [실측]",
    "F-03-c1": "사람·차량 결합 판정을 보여 주는 화면이 없다",
    "F-03-c2": "등급 상향의 결과를 화면에서 확인한 장이 없다",
    "F-03-c3": "위험구역(폴리곤) 편집 화면을 찍지 못했다",
    "F-04-c1": "「동일 이벤트」 판정은 화면에 드러나지 않는다",
    "F-04-c2": "5분 내 중복 0건은 **시간에 걸친 사실**이다 — 한 장의 화면이 답할 수 없다",
    "F-09-c1": "재난 대시보드의 5상태 중 **기본 상태 한 장**만 찍혔다. 로딩·빈·오류·권한없음 네 상태의 화면이 없다 (로그인 화면의 다섯 장은 다른 화면의 상태다)",
    "F-10-c1": "등급별 수신그룹 설정 화면이 없다",
    "F-10-c2": "30초 이내 — 시간이라 화면으로 안 재진다",
    "F-11-c1": "상황 보고서 템플릿 변수 3종을 보여 주는 화면이 없다. `/report-template` 이 부른 것은 레거시 print-format(모델 DeliveryOperation)이고 계약이 말하는 상황 보고서와 이어지지 않는다 [실측]",
    "F-11-c2": "손입력 0 은 위와 같은 이유로 못 이었다",
    "F-11-c3": "치환 결과를 보여 주는 화면이 없다",
    "F-12-c1": "무권한 차단은 **403 으로** 재야 하고 실제로 `/surveillance-dashboard` 에서 view_only 계정이 403 을 7건 받았다 [실측]. 그러나 그 라우트는 계약이 말하는 **관리자 설정**이 아니다 — 다른 자리의 403 을 이 절의 증거로 쓰지 않는다",
    "F-12-c2": "성공·실패 감사로그를 보여 주는 화면이 없다",
    "F-12-c3": "수신자 관리 화면이 없다",
    "F-12-c4": "위젯 관리 화면이 없다",
    "F-12-c5": "구역 관리 화면이 없다",
    "F-12-c6": "임계값 관리 화면이 없다",
    "F-12-c7": "등급규칙 관리 화면이 없다",
    "F-12-c8": "API 키 관리 화면이 없다 (진입면은 F-05 가 라우트로 잰다)",
    "F-13-c1": "「비행 명령을 전송하지 않는다」는 **하지 않음**이다. 화면에서 안 한 것을 보는 방법이 없다 — 부작위 게이트가 따로 있어야 한다",
    "F-14-c2": "월간 오탐률 산출 결과를 보여 주는 화면이 없다",
}


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수다** (D-277). 관측만 먹는다
# ═══════════════════════════════════════════════════════════════════════════
def role_of(entry: dict) -> tuple[str, str]:
    """이 장을 **누가** 봤는가. (역할, 못 쓰는 사유) — 사유가 있으면 그 장은 증거가 못 된다."""
    role = (entry.get("user_role") or "").strip()
    viewed = (entry.get("viewed_by") or "").strip()
    if not role:
        return "", "역할 칸이 비었다 — 누가 봤는지 모르는 장은 증거가 아니다"
    for mark in NO_ROLE_MARKS:
        if mark in viewed:
            return role, ("이 장을 본 쪽에 **역할이 없다**(«%s») — 「됐다」가 아니라 "
                          "「거기까지 못 갔다」다 (출생 표본 ㉠)" % mark[:24])
    return role, ""


#: ★ [턴 S · 조율자] **사건 번호는 사슬의 일부가 아니다.** 이 표는 사건 상세를 `/dsm/events/99554`
#:   로 — 턴 L 의 씨앗 번호 그대로 — 못박고 있었다. 씨앗은 매 회 실제 경로로 새로 만든다(P-156)
#:   는 규약과 정면으로 어긋난다: 이번 턴 새 씨앗(204342)의 화면이 정확히 같은 셋
#:   (`events/{id}` 200 · `deliveries` 200 · `timeline` 200)을 불렀는데 세 절이 회색이 됐다 —
#:   제품 사슬은 그대로였고 **판정기가 지난 씨앗의 번호를 들고 있었다**(D-470 계열).
#:   숫자만으로 된 경로 조각을 `{id}` 로 접어 견준다. 그 밖의 글자는 그대로 정확히 맞아야 한다.
def _slot(path: str) -> str:
    """`/dsm/events/204342` → `/dsm/events/{id}`. 숫자만인 조각만 접는다."""
    head, q, query = str(path).partition("?")
    parts = ["{id}" if seg.isdigit() else seg for seg in head.split("/")]
    return "/".join(parts) + (q + query if q else "")


def call_status(calls, api: str):
    """그 화면이 부른 것 중 `api` 로 시작하는 첫 호출의 상태. 없으면 `None`."""
    for c in calls or []:
        parts = str(c).split()
        if len(parts) < 3:
            continue
        path, status = parts[1], parts[-1]
        if _slot(path).startswith(_slot(api)):
            try:
                return int(status)
            except ValueError:
                return None
    return None


def _role_of_viewed(viewed) -> str:
    """«U1 · gxseed_u1_operator · fire_user · 1440px» → 역할 이름."""
    if isinstance(viewed, (list, tuple)):
        viewed = viewed[0] if viewed else ""
    parts = [p.strip() for p in str(viewed).split("·")]
    for p in parts[2:]:
        if p and not p.endswith("px"):
            return p
    return ""


def _first(v):
    return (v[0] if v else "") if isinstance(v, (list, tuple)) else (v or "")


def load_row_map(path) -> dict:
    """row_map 한 벌을 읽는다. 없거나 깨졌으면 **빈 벌** — 없는 것은 없는 것이다."""
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def row_map_links(doc: dict) -> tuple[dict, dict]:
    """**절 단위** row_map → (사슬 선언, 회색 사유).

    `linked: true` 이고 화면·라우트를 **둘 다** 적은 행만 선언이 된다. 그 선언은
    REACH_MAP 의 한 줄과 똑같은 지위다 — **가설**이고, 초록은 증거가 만든다.
    `linked: false` 인 행은 「무엇이 없어서 못 이었나」를 회색 사유로 준다
    (사유 없는 회색은 여전히 빨강이다 · D-301).
    """
    links: dict[str, dict] = {}
    grey: dict[str, str] = {}
    for r in doc.get("rows") or []:
        cid = (r.get("id") or "").strip()
        if not cid:
            continue
        if r.get("linked") and r.get("screen") and r.get("api"):
            links[cid] = {"screen": r["screen"], "api": r["api"],
                          "expect": r.get("expect", 200),
                          "file_hint": r.get("file_hint", ""),
                          "why": r.get("why") or r.get("checked") or "row_map 이 이은 절"}
        elif r.get("linked") and r.get("gate"):
            links[cid] = {"gate": r["gate"],
                          "why": r.get("why") or r.get("checked") or "row_map 이 게이트에 맡긴 절"}
        else:
            blocker = (r.get("blocker") or "").strip()
            checked = (r.get("checked") or "").strip()
            if blocker or checked:
                grey[cid] = ("row_map: %s%s"
                             % (blocker + " — " if blocker else "", checked))[:400]
    return links, grey


def row_map_screens(doc: dict, known_files: set) -> list:
    """row_map 이 든 **화면 증거** → 화면 인덱스에 **없는 장만** 더한다.

    ★ [실측 2026-09-16 · 턴 R] P-106 의 12행이 든 장은 **전부 INDEX 에 이미 있다.**
      그래서 이 함수가 더하는 장은 **0** 이다. 그 0 이 이 턴의 사실이다 — row_map 을
      입력으로 넣어도 수가 안 움직이는 이유가 「판정기가 안 읽어서」가 아니라
      **「그 파일이 새 증거를 안 들고 있어서」**라는 것. 앞으로 INDEX 밖의 장을 든
      행이 오면 그 장이 여기서 산다.
    """
    out = []
    for r in doc.get("rows") or []:
        calls = r.get("calls") or []
        for s in (r.get("screens") or []) + (r.get("screens_seen") or []):
            name = str(s).replace("\\", "/").split("/")[-1]
            if any(name in str(f) for f in known_files):
                continue
            out.append({"route": r.get("route") or "", "file": s,
                        "user_role": _role_of_viewed(r.get("viewed_by")),
                        "viewed_by": _first(r.get("viewed_by")),
                        "data_source": _first(r.get("data_source")),
                        "calls": calls})
    return out


def proof_map(clauses: list) -> dict:
    """절 → **시험 다리가 서는가.** 대장의 `proof` 파일이 실제로 있어야 True.

    세 짝(캡처 · 라우트 · **시험**) 중 셋째다. 대장 규칙 ②는 「구현 주장은 시험이
    하지 사람이 하지 않는다」였고, 이 자리가 그것을 다시 확인한다. 시험 없는 절은
    화면이 아무리 예뻐도 초록이 될 수 없다.
    """
    out = {}
    for cid, c in clauses:
        proofs = c.get("proof") or []
        out[cid] = any((ROOT / str(p).split("::")[0]).is_file() for p in proofs)
    return out


def judge_clause(cid: str, clause: dict, *, screens: list, gate_rc: dict,
                 links: dict | None = None,
                 rowmap_grey: dict | None = None) -> tuple[str, str]:
    """절 하나 → **(색, 사유)**. 이 함수만이 색을 만든다."""
    links = links or {}
    rowmap_grey = rowmap_grey or {}
    if (clause.get("state") or "").strip() == "잠김":
        return LOCKED, "계약이 조건부로 잠근 절 (%s) — 판정 대상이 아니다" % (
            clause.get("unlock_id") or "?")

    #: ★ P-149 — row_map 이 적은 선언을 **먼저** 본다. 코드 안의 REACH_MAP 은 그 다음이다.
    link = links.get(cid) or REACH_MAP.get(cid)
    if not link:
        #: 회색 사유도 row_map 이 적은 것을 먼저 쓴다 — 절을 실제로 두드린 쪽의 말이다.
        why = rowmap_grey.get(cid) or GREY_WHY.get(cid)
        if not why:
            # ★ 사유 없는 회색은 만들지 않는다 — 그 자체가 빨강이다 (D-301)
            return RED, ("사슬도 없고 **왜 못 이었는지도 안 적혔다** — "
                         "회색에는 사유가 붙어야 한다 (D-301)")
        return GREY, why

    # ── 다른 게이트에 맡긴 절 ──────────────────────────────────────────
    if link.get("gate"):
        rc = gate_rc.get(link["gate"])
        if rc is None:
            return GREY, "게이트 «%s» 를 못 불렀다 — %s" % (link["gate"], link["why"])
        if rc == 0:
            return GREEN, "게이트 «%s» 초록 — %s" % (link["gate"], link["why"])
        if rc == 2:
            return GREY, "게이트 «%s» 가 **회색(exit 2)** 이다 — 못 잰 것은 통과가 아니다" % link["gate"]
        return RED, "게이트 «%s» 가 **빨강(exit %s)** 이다" % (link["gate"], rc)

    # ── 화면으로 닿는 절 — 고리 다섯을 하나씩 ──────────────────────────
    want_screen, want_api = link["screen"], link["api"]
    expect = link.get("expect", 200)
    hint = link.get("file_hint", "")

    cands = [e for e in screens if _slot(e.get("route") or "") == _slot(want_screen)]
    if hint:
        narrowed = [e for e in cands if hint in (e.get("file") or "")]
        cands = narrowed or cands
    if not cands:
        return GREY, "선언한 화면 «%s» 이 인덱스에 없다 — 사슬의 둘째 고리가 없다" % want_screen

    problems = []
    for e in cands:
        role, why_role = role_of(e)
        if why_role:
            problems.append("%s: %s" % (e.get("file", "?"), why_role))
            continue
        ds = (e.get("data_source") or "")
        if ds.startswith(SOURCE_FAKE):
            problems.append("%s: data_source 가 **모의**다 — 제품이 낸 답이 아니다 "
                            "(출생 표본 ㉡)" % e.get("file", "?"))
            continue
        if not any(ds.startswith(s) for s in SOURCE_MEASURED):
            problems.append("%s: data_source «%s» 가 실측도 시드도 아니다"
                            % (e.get("file", "?"), ds[:20]))
            continue
        status = call_status(e.get("calls"), want_api)
        if status is None:
            problems.append("%s: 그 화면이 «%s» 를 **부르지 않았다** — 셋째 고리가 없다"
                            % (e.get("file", "?"), want_api))
            continue
        if status != expect:
            problems.append("%s: «%s» 가 **%d** 다(기대 %d) — 화면이 떴다는 것과 그 절이 "
                            "닿았다는 것은 다른 사실이다 (출생 표본 ㉢)"
                            % (e.get("file", "?"), want_api, status, expect))
            continue
        return GREEN, ("%s ← 화면 %s · %s %d · 역할 %s · %s | %s"
                       % (link["why"], want_screen, want_api, status, role,
                          ds[:12], e.get("file", "?")))
    return RED, " / ".join(problems[:3])


def judge(observations: dict) -> list:
    """관측 → **[(절 id, 색, 사유)]**. 절 하나에 한 줄.

    ★ P-149 — 세 짝을 여기서 다 본다: 캡처·라우트(judge_clause) + **시험**(proof_ok).
      셋이 다 서야 초록이고, 하나라도 없으면 **회색**이다. 회색은 초록이 아니다.
    """
    clauses = observations.get("clauses") or []
    screens = observations.get("screens") or []
    gate_rc = observations.get("gate_rc") or {}
    links = observations.get("links") or {}
    rowmap_grey = observations.get("rowmap_grey") or {}
    proof_ok = observations.get("proof_ok") or {}
    if not clauses:
        return []
    out = []
    for cid, c in clauses:
        color, why = judge_clause(cid, c, screens=screens, gate_rc=gate_rc,
                                  links=links, rowmap_grey=rowmap_grey)
        if color == GREEN and not proof_ok.get(cid):
            #: 캡처·라우트는 이었는데 **시험이 없다** — 셋째 다리가 빠진 자리.
            color, why = GREY, ("캡처·라우트는 이어졌는데 **시험 다리가 없다** — 대장의 "
                                "`proof` 가 비었거나 그 파일이 저장소에 없다. 세 짝 중 "
                                "하나가 빠지면 회색이다 (P-149)")
        out.append((cid, color, why))
    return out


def tally(rows: list) -> dict:
    out = {GREEN: 0, RED: 0, GREY: 0, LOCKED: 0}
    for _, color, _ in rows:
        out[color] = out.get(color, 0) + 1
    return out


def area_one(rows: list) -> dict:
    """영역 ① 이 쓸 셈. **분모는 절 전부**다 — 못 잰 것을 분모에서 빼지 않는다."""
    t = tally(rows)
    n = len(rows)
    done = t.get(GREEN, 0)
    return {"n": n, "구현": done, "빨강": t.get(RED, 0), "미측정": t.get(GREY, 0),
            "잠김": t.get(LOCKED, 0),
            "ratio": (done / n) if n else 0.0,
            "weighted": 20.0 * ((done / n) if n else 0.0)}


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-310)
# ═══════════════════════════════════════════════════════════════════════════
def _screen(route, role, viewed, ds, calls, file="x.png"):
    return {"route": route, "user_role": role, "viewed_by": viewed,
            "data_source": ds, "calls": calls, "file": file}


def _good_observations() -> dict:
    return {
        "clauses": [
            ("F-01-c2", {"state": "구현"}),
            ("F-05-c1", {"state": "구현"}),
            ("F-06-c1", {"state": "잠김", "unlock_id": "SDN_API_SPEC"}),
            ("F-03-c1", {"state": "구현"}),
        ],
        "screens": [
            _screen("/dsm/events", "fire_user", "U1 · gxseed_u1_operator · fire_user",
                    "시드", ["GET /api/dsm/events?limit=50 200"], "SCREENS-1/fire_user/e.png"),
        ],
        "gate_rc": {"scripts/verify_contract_route_reach.py": 0},
        #: 세 짝의 셋째. 이 벌에서는 네 절 다 시험이 선다고 두고, 변이가 그것을 끊는다.
        "proof_ok": {"F-01-c2": True, "F-05-c1": True, "F-06-c1": True, "F-03-c1": True},
    }


#: ★ **출생 표본** — 셋 다 실측이다(턴 L · 2026-09-07). 셋 다 **초록이면 안 된다.**
def BIRTH_SAMPLE() -> dict:
    return {
        "clauses": [("F-01-c2", {"state": "구현"}),
                    ("F-09-c2", {"state": "구현"}),
                    ("F-10-c3", {"state": "구현"})],
        "screens": [
            # ㉠ 역할 0 계정으로 걸었다 — 턴 L 의 `walk 3/3 · 콘솔 0`
            _screen("/dsm/events", "", "(로그인 전 · 아직 누구도 아니다) — gxprobe_e2e",
                    "시드", ["GET /api/dsm/events 200"], "walk/e2e.png"),
            # ㉡ 모의로 찍었다 — 서버의 본문을 주입한 장
            _screen("/dsm/events/99554", "fire_user", "U1 · gxseed_u1_operator · fire_user",
                    "모의 (500 을 주입했다)", ["GET /api/dsm/events/99554 200"], "mock.png"),
            # ㉢ 화면은 떴는데 그 라우트는 404 였다
            _screen("/dsm/events/99554", "fire_user", "U1 · gxseed_u1_operator · fire_user",
                    "시드", ["GET /api/dsm/deliveries 404"], "clip404.png"),
        ],
        "gate_rc": {},
        #: ★ 시험은 셋 다 선다 — 그래야 이 표본이 **사슬 때문에** 안 초록인 것이 보인다.
        "proof_ok": {"F-01-c2": True, "F-09-c2": True, "F-10-c3": True},
    }


def self_test() -> int:
    ok = True
    # ★ 출생 표본 (턴 S) — 씨앗 번호가 바뀌어도 사슬은 같은 사슬이다 · 숫자 아닌 조각은 안 접는다
    assert _slot("/dsm/events/204342") == "/dsm/events/{id}" == _slot("/dsm/events/99554")
    assert _slot("/api/dsm/events/7/timeline") == "/api/dsm/events/{id}/timeline"
    assert _slot("/dsm/events?preset=unhandled") == "/dsm/events?preset=unhandled"
    assert _slot("/api/dsm/settings/zones") == "/api/dsm/settings/zones"   # 글자는 그대로
    assert call_status(["GET /api/dsm/events/204342 200"], "/api/dsm/events/{id}") == 200
    assert call_status(["GET /api/dsm/events/204342/timeline 200"], "/api/dsm/events/{id}") == 200
    assert call_status(["GET /api/dsm/eventsX/1 200"], "/api/dsm/events/{id}") is None
    print("%s O 씨앗 번호를 접어 견준다 (204342 == 99554 == {id} · 글자 조각은 그대로)" % TAG)

    def say(good, label):
        nonlocal ok
        if good:
            print("%s O %s" % (TAG, label))
        else:
            ok = False
            print("%s X %s" % (TAG, label))

    rows = judge(_good_observations())
    colors = dict((cid, c) for cid, c, _ in rows)
    say(colors.get("F-01-c2") == GREEN, "이어진 사슬은 초록 (양성 대조)")
    say(colors.get("F-05-c1") == GREEN, "다른 게이트가 초록이면 그 절도 초록")
    say(colors.get("F-06-c1") == LOCKED, "잠김 절은 판정 대상이 아니다")
    say(colors.get("F-03-c1") == GREY, "사슬 없는 절은 **회색** (초록이 아니다)")

    # 변이 — 고리 하나씩 끊어 본다. **그 절만** 빨개져야 한다
    mutants = {}
    m = _good_observations(); m["screens"][0]["calls"] = ["GET /api/dsm/events 403"]
    mutants["상태가 200 이 아니다"] = m
    m = _good_observations(); m["screens"][0]["data_source"] = "모의 (주입했다)"
    mutants["모의로 찍은 화면"] = m
    m = _good_observations()
    m["screens"][0]["viewed_by"] = "(로그인 전 · 아직 누구도 아니다) — gxprobe_e2e"
    mutants["역할 0 계정이 봤다"] = m
    m = _good_observations(); m["screens"][0]["calls"] = ["GET /api/menu/menus 200"]
    mutants["그 라우트를 아예 안 불렀다"] = m
    m = _good_observations(); m["gate_rc"]["scripts/verify_contract_route_reach.py"] = 1
    mutants["맡긴 게이트가 빨강"] = m

    caught = 0
    for label, obs in mutants.items():
        colors = dict((cid, c) for cid, c, _ in judge(obs))
        target = "F-05-c1" if "게이트" in label else "F-01-c2"
        if colors.get(target) == RED:
            caught += 1
        else:
            ok = False
            print("%s X 변이 「%s」를 못 잡는다 (%s → %s)" % (TAG, label, target, colors.get(target)))
    print("%s O 변이 %d/%d 를 잡는다 (음성 대조 · 규칙)" % (TAG, caught, len(mutants)))

    # 맡긴 게이트가 **회색**이면 그 절도 회색이다 — 회색은 초록이 아니다
    m = _good_observations(); m["gate_rc"]["scripts/verify_contract_route_reach.py"] = 2
    say(dict((c, k) for c, k, _ in judge(m)).get("F-05-c1") == GREY,
        "맡긴 게이트가 회색이면 그 절도 회색")

    # ★ 출생 표본 — 셋 다 **초록이 아니어야** 한다
    born = judge(BIRTH_SAMPLE())
    greens = [cid for cid, c, _ in born if c == GREEN]
    say(not greens, "출생 표본 3/3 이 초록이 아니다 (역할0 · 모의 · 404)")
    if greens:
        print("%s   초록으로 샌 절: %s" % (TAG, greens))

    # 관측 0건은 초록이 아니다 (D-301)
    say(not judge({}), "관측 0건은 판정 0줄 — 「전부 통과」를 말하지 않는다")
    say(area_one([])["ratio"] == 0.0, "절 0개의 비율은 0 이다 (빈 분모가 100%가 되지 않는다)")

    # 사유 없는 회색은 만들 수 없다
    stray = judge({"clauses": [("F-99-c9", {"state": "구현"})], "screens": [], "gate_rc": {}})
    say(stray and stray[0][1] == RED, "사슬도 사유도 없는 절은 **빨강** (조용한 회색을 안 만든다)")

    # 선언한 사슬이 실재 파일과 어긋나면 잡히는가 — 표가 초록을 만들 수 없다
    m = _good_observations(); m["screens"] = []
    say(dict((c, k) for c, k, _ in judge(m)).get("F-01-c2") == GREY,
        "선언한 화면이 인덱스에 없으면 회색 (표가 초록을 만들지 못한다)")

    # ── ★ P-149 — 세 짝의 셋째(시험) · row_map 을 입력으로 읽는 갈래 ──────────
    m = _good_observations(); m["proof_ok"]["F-01-c2"] = False
    say(dict((c, k) for c, k, _ in judge(m)).get("F-01-c2") == GREY,
        "★ 캡처·라우트가 이어져도 **시험이 없으면 초록이 아니다** (세 짝)")

    m = _good_observations(); m["proof_ok"] = {}
    say(not [c for c, k, _ in judge(m) if k == GREEN],
        "★ 시험 벌이 통째로 비면 초록 0 (모르는 것을 초록으로 세지 않는다)")

    # ★★ **row_map 이 초록을 만들지 못한다** — 이 판정의 심장이다
    m = _good_observations()
    m["links"] = {"F-03-c1": {"screen": "/없는/화면", "api": "/api/dsm/x",
                              "why": "row_map 이 「이었다」고 적었다"}}
    m["proof_ok"]["F-03-c1"] = True
    say(dict((c, k) for c, k, _ in judge(m)).get("F-03-c1") == GREY,
        "★★ row_map 이 `linked:true` 라 적어도 **캡처가 없으면 회색** (파일이 초록을 못 만든다)")

    # row_map 이 선언한 사슬도 증거가 서면 초록이 된다 (양성 대조 — 길이 막히지 않았다)
    m = _good_observations()
    m["links"] = {"F-03-c1": {"screen": "/dsm/events", "api": "/api/dsm/events",
                              "why": "row_map 이 이은 절"}}
    m["proof_ok"]["F-03-c1"] = True
    say(dict((c, k) for c, k, _ in judge(m)).get("F-03-c1") == GREEN,
        "row_map 이 선언하고 **증거가 서면** 초록 (입력이 실제로 판정에 닿는다)")

    # row_map 이 적은 회색 사유를 판정기가 쓴다
    m = _good_observations(); m["rowmap_grey"] = {"F-03-c1": "row_map 이 적은 막힌 자리"}
    got = dict((c, (k, w)) for c, k, w in judge(m)).get("F-03-c1", ("", ""))
    say(got[0] == GREY and "row_map" in got[1],
        "row_map 이 적은 회색 사유를 판정기가 쓴다 (절을 두드린 쪽의 말)")

    # 파서 — 「이었다」가 아닌 행은 선언이 되지 않는다
    links, grey = row_map_links({"rows": [
        {"id": "F-12-c3", "linked": False, "blocker": "화면 없음", "checked": "부르는 화면 0"},
        {"id": "F-99-c1", "linked": True, "screen": "/s", "api": "/api/x", "why": "이었다"},
        {"id": "F-98-c1", "linked": True},
    ]})
    say(set(links) == {"F-99-c1"} and "F-12-c3" in grey,
        "row_map 파서 — `linked:true` + 화면·라우트가 다 있는 행만 선언이 된다")

    # INDEX 에 이미 있는 장은 **더하지 않는다** (같은 장을 두 번 세지 않는다)
    doc = {"rows": [{"screens": ["SCREENS-1/fire_user/a.png"], "calls": ["GET /api/x 200"],
                     "viewed_by": ["U1 · gxseed_u1_operator · fire_user · 1440px"],
                     "data_source": ["시드"]}]}
    say(not row_map_screens(doc, {"SCREENS-1/fire_user/a.png"}),
        "row_map 의 장이 INDEX 에 이미 있으면 안 더한다 (한 장을 두 번 세지 않는다)")
    say(len(row_map_screens(doc, set())) == 1
        and row_map_screens(doc, set())[0]["user_role"] == "fire_user",
        "row_map 의 장이 INDEX 밖이면 더하고, 역할을 `viewed_by` 에서 읽는다")
    return EXIT_OK if ok else EXIT_FAIL


# ═══════════════════════════════════════════════════════════════════════════
# 관측
# ═══════════════════════════════════════════════════════════════════════════
class Undecidable(Exception):
    """못 쟀다 — 회색(exit 2)."""


def read_clauses() -> list:
    if yaml is None:
        raise Undecidable("PyYAML 이 없다 — 계약 절 대장을 못 읽는다")
    if not CONTRACT.is_file():
        raise Undecidable("계약 절 대장이 없다: %s" % CONTRACT)
    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    out = []
    for feat in data.get("features") or []:
        fid = feat.get("id")
        for i, c in enumerate(feat.get("clauses") or [], 1):
            out.append(("%s-c%d" % (fid, i), c))
    return out


def read_screens() -> list:
    if yaml is None:
        raise Undecidable("PyYAML 이 없다 — 화면 인덱스를 못 읽는다")
    if not INDEX.is_file():
        raise Undecidable("화면 인덱스가 없다: %s" % INDEX)
    data = yaml.safe_load(INDEX.read_text(encoding="utf-8")) or {}
    return list(data.get("screens") or [])


def call_gates(gates, timeout: int = 900) -> dict:
    """맡긴 게이트를 **실제로 부른다** (D-210). 못 부르면 `None` = 회색."""
    out = {}
    for g in sorted(gates):
        path = ROOT / g
        if not path.is_file():
            out[g] = None
            continue
        try:
            proc = subprocess.run([sys.executable or "python", str(path)],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, cwd=str(ROOT))
            out[g] = proc.returncode
        except (OSError, subprocess.SubprocessError):
            out[g] = None
    return out


def observe(run_gates: bool = True) -> dict:
    clauses = read_clauses()
    screens = read_screens()
    known = {e.get("file") or "" for e in screens}

    #: ★ P-149 — row_map 두 벌을 **입력으로** 읽는다.
    cdoc = load_row_map(ROW_MAP_CLAUSE)      # 절 단위 (P-142)
    pdoc = load_row_map(ROW_MAP_PAIN)        # 페인 18행 (P-106)
    links, rowmap_grey = row_map_links(cdoc)
    extra = row_map_screens(pdoc, known) + row_map_screens(cdoc, known | {
        e.get("file") or "" for e in row_map_screens(pdoc, known)})

    wanted = {v["gate"] for v in list(REACH_MAP.values()) + list(links.values())
              if v.get("gate")}
    return {"clauses": clauses, "screens": screens + extra,
            "links": links, "rowmap_grey": rowmap_grey,
            "proof_ok": proof_map(clauses),
            "row_map": {"clause_rows": len(cdoc.get("rows") or []),
                        "pain_rows": len(pdoc.get("rows") or []),
                        "links": len(links), "grey": len(rowmap_grey),
                        "extra_screens": len(extra)},
            "gate_rc": call_gates(wanted) if run_gates else {}}


def main() -> int:
    ap = argparse.ArgumentParser(description="영역 ① 기능 완결성의 게이트 (P-106)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true", help="절별 사슬")
    ap.add_argument("--json", action="store_true", help="영역 ① 이 쓸 셈만 (기계용)")
    ap.add_argument("--no-gates", action="store_true",
                    help="맡긴 게이트를 부르지 않는다 (그 절은 회색이 된다)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # ★ `--json` 은 **기계가 읽는 자리**다. stdout 에는 JSON 말고 아무것도 안 나간다 —
    #   2026-09-07 에 머리글이 stdout 으로 나가 `deploy.sh` 의 JSON 을 깨뜨렸고,
    #   그 게이트는 회색이 되어 배치를 되돌렸다. 같은 실수를 자기시험 줄로 반복하지 않는다.
    _saved = sys.stdout
    if args.json:
        sys.stdout = sys.stderr
    try:
        rc = self_test()
    finally:
        sys.stdout = _saved
    if rc != EXIT_OK:
        print("%s 자기시험이 빨강이다 — 판정을 신뢰할 수 없다" % TAG, file=sys.stderr)
        return rc

    try:
        obs = observe(run_gates=not args.no_gates)
    except Undecidable as exc:
        print("%s ? **못 쟀다** — %s" % (TAG, exc))
        return EXIT_UNDECIDABLE

    rows = judge(obs)
    t = tally(rows)
    a = area_one(rows)
    where = sys.stderr if args.json else sys.stdout
    rm = obs.get("row_map") or {}
    print("%s [입력] 계약 절 %d개 · 화면 %d장 · 맡긴 게이트 %d벌 · 시험 다리 %d/%d절"
          % (TAG, len(obs["clauses"]), len(obs["screens"]), len(obs["gate_rc"]),
             sum(1 for v in (obs.get("proof_ok") or {}).values() if v),
             len(obs["clauses"])), file=where)
    print("%s [입력] row_map 2벌 — 절 단위 %d행(선언 %d · 회색 사유 %d) · 페인 %d행 "
          "· **INDEX 밖의 새 장 %d**"
          % (TAG, rm.get("clause_rows", 0), rm.get("links", 0), rm.get("grey", 0),
             rm.get("pain_rows", 0), rm.get("extra_screens", 0)), file=where)
    if not rm.get("links"):
        print("%s [입력]   ↳ `linked:true` 인 행이 **0** 이다 — row_map 은 읽혔고, "
              "그 파일이 「이을 절이 없다」고 적고 있다. 판정기가 안 읽어서가 아니다"
              % TAG, file=where)

    if args.json:
        payload = dict(a, rows=[{"id": c, "color": k, "why": w} for c, k, w in rows])
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return EXIT_OK

    for cid, color, why in rows:
        if args.list or color != GREY:
            print("  %s %-9s %s" % ({GREEN: "O", RED: "X", GREY: "?", LOCKED: "L"}[color],
                                    cid, why[:150]))
    if not args.list and t.get(GREY):
        print("  ? 회색 %d절 — `--list` 로 사유를 전부 본다" % t[GREY])

    print("%s 색: 초록 %d · 빨강 %d · **회색 %d** · 잠김 %d  (절 %d)"
          % (TAG, t.get(GREEN, 0), t.get(RED, 0), t.get(GREY, 0), t.get(LOCKED, 0), len(rows)))
    print("%s ★ 영역 ① = 구현 %d / 절 %d = %.1f%% → 가중 **%.2f** (가중치 20%%)"
          % (TAG, a["구현"], a["n"], a["ratio"] * 100, a["weighted"]))
    print("%s   회색 %d절은 **못 잰 것**이다 — 통과가 아니다. 그래서 수가 내려간다 (D-301)"
          % (TAG, a["미측정"]))

    try:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(
            dict(a, rows=[{"id": c, "color": k, "why": w} for c, k, w in rows]),
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("%s   셈을 적어 두었다: %s" % (TAG, OUT_JSON.relative_to(ROOT)))
    except OSError as exc:
        print("%s   셈을 못 적었다: %s" % (TAG, exc))

    if t.get(RED):
        print("%s 빨강 %d절 — **사슬이 있는데 끊겼다**" % (TAG, t[RED]))
        return EXIT_FAIL
    print("%s 끊긴 사슬은 없다 (회색은 끊긴 것이 아니라 **못 이은 것**이다)" % TAG)
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import file_stamp, gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="계약 절 39개 ↔ 화면 32장 ↔ 그 화면이 부른 라우트 (영역 ① · 가중 20%)",
        as_="이 게이트 자신은 자격 없이 증거를 읽는다. 화면을 **본** 쪽은 역할 계정이다 "
            "— U1 gxseed_u1_operator/fire_user · U2 gxseed_u2_manager/fire_admin · "
            "U4 gxseed_u4_official/view_only_-_anyang · U5 gxseed_u5_sysop/admin · "
            "자격 이름 GX_SEED_ROLE_PASSWORD. **역할 0 계정(gxprobe_e2e)이 본 장은 "
            "초록이 될 수 없다**",
        source=file_stamp(CONTRACT) + " + " + file_stamp(INDEX) + " + " + file_stamp(SCREEN_ROUTES),
        reason="32장 중 6장은 U5 sysop(admin)으로 찍었다 — 관리자 화면은 관리자만 볼 수 "
               "있기 때문이다. 나머지 26장은 역할 계정이고, 이 게이트가 초록을 내는 "
               "네 절은 전부 fire_user 가 본 장이다",
    )
    raise SystemExit(main())
