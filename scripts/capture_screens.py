#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""화면 캡처 **실행체** — 브라우저가 실제로 지나간 화면만 남긴다 (D-347 · D-384 ②).

두 턴 동안 스크린샷이 **0장**이었고, 0장인 것이 정직한 상태였다. 사유는 둘이었다:

    ① 브라우저를 여는 구동체가 없다 (playwright·selenium 어느 것도 requirements 에 없음)
    ② 프런트 의존 설치본이 저장소와 어긋나 빌드가 서지 않는다 (FRONTEND_DEPS_DRIFT · D-376)

[실측 2026-09-12] ②가 풀렸다 — **빌드가 1회 성공했다**(`vite build` 66초 · exit 0).
D-381 이 문턱을 낮춘 그대로다: **타입오류 3229건이 있어도 번들은 만들어진다.**
타입검사와 번들링은 다른 일이고, 스크린샷에 필요한 것은 후자다.

이 실행체가 하는 일 — 그리고 하지 않는 일
------------------------------------------
    한다   : 로그인 화면부터 **사람이 하는 그대로** 지나가며, 각 화면이 **떴는지 단언**하고
             그 순간에 찍는다. 단언이 깨지면 **찍지 않고 실패한다.**
    안 한다: 화면을 따로 띄워 예쁘게 만들어 찍는 일. 그것이 D-347 ①이 금지한 것이고,
             고객이 보는 자리에서는 착시가 아니라 **거짓말**이다 (D-284).

    ★ 단언이 캡처보다 먼저다. 「파일이 생겼다」는 성공이 아니다 — 로그인 화면으로
      튕긴 뒤 찍은 PNG 도 파일은 생긴다. 그래서 **화면마다 그 화면에만 있는 글자**를
      찾고, 못 찾으면 그 자리에서 멈춘다.

    ★ 씨앗은 **시험 데이터뿐**이다 (D-347 ④). 실제 영상 프레임·개인정보는 넣지 않는다.
      만든 것에는 전부 `PROBE_TAG` 가 붙고, 끝나면 지운다.

무엇이 필요한가 (없으면 **판정 불가로 멈춘다** · exit 2)
--------------------------------------------------------
    · API      기본 http://localhost:8000   (`--api`)
    · 화면     기본 http://localhost:3002   (`--web`) — `vite build` 산출물을 SPA 로 서빙
    · 계정     `--user` / `--password`

    python scripts/capture_screens.py --user gxseed_u1_operator --password ****            --persona all                            # U1→U2→U3→U4→U5 를 차례로
    python scripts/capture_screens.py --dry-run     # 씨앗·정리 없이 도달만 본다

★★ [P-98 · 2026-09-07] **한 벌은 다섯 사람의 벌이다.** 그 전까지 33장은 전부 한 계정
   (`gxprobe_e2e`)이 찍었고, 그 계정의 역할 목록은 **비어 있었다** — 33장이 「제품이
   된다」가 아니라 「역할 없는 사람에게 무엇이 보이는가」를 찍고 있었던 것이다.
   화면마다 `persona` 가 붙었고, 인덱스의 `viewed_by` 가 그것을 말한다.
   역할이 0개인 계정으로는 **찍지 않는다**(판정 불가 · exit 2).

⚠ 계정은 **이 실행체가 만들지 않는다.** 사람이 만든 계정을 받아 쓴다 — 스크립트가
  계정을 만들면 그 계정의 존재를 아무도 대장에서 못 찾고, 비밀번호가 소스에 박힌다.
  이 저장소의 개발 환경에는 `gxprobe_e2e` 를 손으로 만들어 두었고, 그 계정은
  **개발 DB 에만** 있다. 운영에 같은 계정을 만들지 말 것.

산출: `docs/agent/evidence/D-347/screens/SCREENS-1/<ROLE>/<route>.png`
      + `run_log.json` (단계 시각). `scripts/verify_screens.py` 가 이 둘을 ±5분으로 대조한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 이 실행체가 만든 씨앗에만 붙는 표. **지울 때의 유일한 근거**다.
#: ★ [P-156 · 턴 T · 차선 Q] 값은 `scripts/probe_marks.py` 가 **하나로** 든다 — 여기와 판정기가
#:   다른 표를 들면 「제외 필터」가 아무것도 못 거른다. 두 벌로 두지 않는다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_marks import PROBE_TAG, mark_string as _probe_mark_string, mark as _probe_mark  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# 누가 봤나 — **역할 없는 계정으로 찍은 33장은 인수 증거가 아니었다** (P-98)
# ═══════════════════════════════════════════════════════════════════════════
# [실측 2026-09-07] 앞선 33장은 전부 `gxprobe_e2e` 로 찍혔고, 그 계정의 역할 목록은
# **비어 있다**(`user.roles` = []). 그 벌은 「제품이 돈다」를 보여 준 것이 아니라
# **「역할 없는 사람에게 무엇이 보이는가」**를 보여 준 것이다 — 뜻이 있는 측정이지만
# 인수 증거는 아니다. 그 벌은 `docs/agent/evidence/P-98/denied/` 로 옮겨 두었다.
#
# ★ 그리고 **왜 아무도 못 봤나**가 이 파일 안에 있었다: `read_role()` 이 `user.role`
#   (단수 · 이 제품에 **존재하지 않는 필드**)을 읽었다. 없는 필드는 `None` 이고,
#   `None` 은 `NO_ROLE` 로 적혔다. 역할이 **있는** 계정도 똑같이 `NO_ROLE` 로 적힌다 —
#   즉 이 칸은 「역할이 없다」가 아니라 **「읽는 곳을 틀렸다」**를 말하고 있었다.
#   제품이 실제로 들고 있는 자리는 `user.roles` (M2M) 다.
#
# ★ 페르소나는 **계정이 아니라 자리**다. U3 은 새 계정이 아니라 **U1 이 390px 에서**
#   보는 화면이다 — 폭이 다르면 사람이 보는 화면이 다르고, 그것이 U3 의 전부다.
PERSONAS = {
    "U1": {"username": "gxseed_u1_operator", "role": "fire_user",
           "label": "관제요원", "note": "상황실에서 이벤트를 받는 사람"},
    "U2": {"username": "gxseed_u2_manager", "role": "fire_admin",
           "label": "팀장", "note": "훈련·일괄등록·온보딩을 여는 사람"},
    "U3": {"username": "gxseed_u1_operator", "role": "fire_user",
           "label": "관제요원(이동 중)", "note": "U1 과 **같은 계정** · 390px"},
    "U4": {"username": "gxseed_u4_official", "role": "view_only_-_anyang",
           "label": "재난안전과", "note": "읽기 전용으로 상황을 보는 사람"},
    "U5": {"username": "gxseed_u5_sysop", "role": "admin",
           "label": "관리자", "note": "장비·역할·메뉴·설정을 만지는 사람"},
}

#: 시나리오 코드. E2E-1·2·3 은 업무 시나리오 등재부(`e2e_contract.py`)의 것이므로
#: 쓰지 않는다 — 이것은 **화면 캡처 실행**이고, 이름이 그 사실을 말해야 한다.
SCENARIO = "SCREENS-1"

#: 데스크톱과 휴대전화 두 크기. 「M1~M3 는 잰 적이 없다」를 끝내는 자리다.
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
#: 390×844 — U3 시나리오가 적은 폭이다. 480 로 좁아지는 모바일 껍데기가 이 안에 든다.
MOBILE_VIEWPORT = {"width": 390, "height": 844}

ROOT = Path(__file__).resolve().parent.parent

#: 증거를 어디에 남기나. 컨테이너에서는 저장소가 `/repo` 로, 문서 트리가 `/docs` 로
#: **따로** 마운트된다 — `/repo/docs` 는 없다. 그래서 자리를 하나로 못 박지 않는다.
#: ★ 1차판은 `ROOT/docs` 로 못 박았고, 컨테이너에서 **PNG 는 남는데 인덱스는 못 고치는**
#:   반쪽 상태가 났다. 그 상태가 가장 나쁘다 — 파일과 인덱스가 갈라지고,
#:   갈라진 인덱스는 `verify_screens.py` 가 「어디서 온 화면인지 말하지 않는다」로 잡는다.
def _screens_dir() -> Path:
    for base in (ROOT / "docs", Path("/docs")):
        if (base / "agent" / "evidence" / "D-347" / "screens" / "INDEX.yaml").is_file():
            return base / "agent" / "evidence" / "D-347" / "screens"
    return ROOT / "docs" / "agent" / "evidence" / "D-347" / "screens"


SCREENS = _screens_dir()

# ═══════════════════════════════════════════════════════════════════════════
# P-154 · **대장은 줄지 않는다** — 생성기는 합쳐 쓰고, 이번 실행분은 따로 둔다 (턴 S · 조율자)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 턴 R 에 이 도구가 INDEX(32→2) · run_log(32단계→2) · screen_routes(27→2)를 **이번 실행분만
#:   남기고** 다시 썼다. 셋째는 게이트 셋의 입력이라 상용 63.2 · 영역 ① 3/39 가 보고에
#:   실릴 뻔했다(D-473). 생성기는 자기가 만든 것만 안다 — 그래서 대장을 통째로 주지 않는다.
#: ★ 열쇠는 **PNG 파일 경로**다. 경로에 역할이 들어 있어(`<벌>/<ROLE>/<route>.png`) 「같은
#:   화면을 다른 역할이 본 기록」이 접히지 않고, 같은 파일을 다시 찍으면 그 항목만 새 판이
#:   된다. **라우트로 묶으면 접힌다** — 조율자가 턴 R 에 그렇게 4건을 지웠다(D-477).
#: ★ 줄면 **예외로 멈춘다**(`assert_not_shrunk`). 경고는 다음 사람이 안 읽는다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ledger_merge import assert_not_shrunk, merge_records  # noqa: E402

RUNS_DIR = SCREENS.parent.parent / "P-157" / "runs"
RUN_STAMP = datetime.now().strftime("%Y%m%dT%H%M%S")
#: 이번 회가 심은 씨앗 id — 판정 뒤 `probe_marks.mark` 로 표시하고 정리한다 (P-156).
SEEDED_EVENT_IDS: list = []
#: ★★ [P-170 ② · 턴 U · 차선 Q] **이번 회가 심은 씨앗의 명세.** `seed_events` 가 채우고
#:   `_write_seed_file()` 이 `P-157/runs/<RUN_STAMP>/seed.json` 으로 낸다.
#:   턴 T 의 오판(D-487 ②)이 정확히 여기였다: 씨앗 id 배선을 옮겨 놨는데 capture 가
#:   **스스로 씨앗을 지워서** 넘길 id 가 없었다. 지금은 **기본이 남기기**이고
#:   지우려면 `--clean-seeds` 를 손으로 적어야 한다.
SEED_SPEC: dict = {}


def _by_file(r) -> str:
    return str(r.get("file", "")) if isinstance(r, dict) else str(r)


def _keep_run_copy(name: str, text: str) -> None:
    """이번 실행분 **그대로** — 대장과 별도로. 합친 뒤에는 무엇이 이번 것인지 못 가른다."""
    d = RUNS_DIR / RUN_STAMP
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def _existing_index_entries() -> list:
    """대장 INDEX.yaml 의 screens 목록. 없으면 빈 목록 — 깨졌으면 **멈춘다**(합치지 못하면 쓰지 않는다)."""
    p = SCREENS / "INDEX.yaml"
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8")
    try:
        import yaml
        doc = yaml.safe_load(text) or {}
        return list(doc.get("screens") or [])
    except ImportError:
        #: ★ gx-shell 에는 PyYAML 이 없다 [실측 2026-09-17]. 이 파일은 우리가 쓰는 모양이
        #:   정해져 있으니(아래 `row`) 그 모양만 읽는 작은 파서로 대신한다 — 컨테이너에서
        #:   합치기가 죽으면 INDEX 만 옛 시각을 가리키는 **거짓 색인**이 남는다(D-473).
        return _parse_index_plain(text)


def _parse_index_plain(text: str) -> list:
    """`screens:` 아래의 `  - route:` 항목만 읽는다. `row` 템플릿이 쓰는 모양 그대로."""
    body = text.partition("screens:")[2]
    out, cur, in_calls = [], None, False
    for line in body.splitlines():
        if line.startswith("  - route:"):
            cur = {"route": line.split(":", 1)[1].strip(), "calls": []}
            out.append(cur); in_calls = False
            continue
        if cur is None or not line.startswith("    "):
            continue
        s = line.strip()
        if in_calls and s.startswith("- "):
            cur["calls"].append(s[2:].strip().strip('"'))
            continue
        in_calls = False
        if ":" not in s:
            continue
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "calls":
            in_calls = not v.startswith("[")
            continue
        if v.startswith('"') and '"' in v[1:]:
            v = v[1:v.rindex('"')]
        cur[k] = v
    return out


def _read_json_ledger(p: Path) -> dict:
    """대장 JSON. 없으면 빈 벌 — 깨졌으면 멈춘다."""
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

#: 무엇을 찍나. `must_see` 는 **그 화면에만 있는 글자**다 — 로그인으로 튕겼는지
#: 빈 껍데기가 떴는지를 이것 하나로 가른다.
TARGETS = [
    {"step": 1, "persona": "U1", "route": "/dsm/dashboard", "must_see": "관제 대시보드"},
    {"step": 2, "persona": "U1", "route": "/dsm/events", "must_see": "이벤트 목록"},
    {"step": 3, "persona": "U1", "route": "/dsm/events/{event_id}", "must_see": "이벤트 상세"},
    # ── D-386 [실측 2026-09-13] 다섯 장을 더한다. 셋은 우리가 만든 화면이고
    #    이 다섯은 **인수받은 화면**이다 — 남의 화면을 여는 것이 값이 큰 이유는
    #    우리가 한 번도 열어 본 적 없는 배선이 거기 있기 때문이다.
    #    `must_see` 는 **실제로 띄워 보고** 그 화면에만 있는 글자로 골랐다(추측 아님).
    {"step": 4, "persona": "U5", "route": "/device", "must_see": "Add New Device"},
    {"step": 5, "persona": "U5", "route": "/roles", "must_see": "Add New Role"},
    {"step": 6, "persona": "U5", "route": "/menu", "must_see": "Menu Management"},
    {"step": 7, "persona": "U5", "route": "/configuration-management", "must_see": "Is Active?"},
    {"step": 8, "persona": "U5", "route": "/profile", "must_see": "Personal Information"},
    # ── D-396 [실측 2026-09-14] 여덟 장을 더해 **16/16** 을 채운다.
    #    고른 기준: 재난안전·감시 국면에 닿는 화면 우선 (§0.4 배송·주문·터미널은 뺐다).
    #    `must_see` 는 **후보 16개를 실제로 열어 본문을 읽고** 골랐다 — 추측이 아니다.
    #    (정찰 결과: 찍을 수 있는 것 13 · 찍을 수 없는 것 3. 셋은 아래 KNOWN_* 에 남긴다)
    {"step": 9, "persona": "U4", "route": "/surveillance-dashboard", "must_see": "Last Updated"},
    {"step": 10, "persona": "U5", "route": "/survey-profile", "must_see": "Add New Profile"},
    {"step": 11, "persona": "U4", "route": "/media-data", "must_see": "No preview available."},
    {"step": 12, "persona": "U4", "route": "/flight-log-analysis", "must_see": "Drone State Prediction"},
    {"step": 13, "persona": "U2", "route": "/multi-stream-monitor", "must_see": "Participants"},
    {"step": 14, "persona": "U5", "route": "/operation-settings", "must_see": "API URL"},
    {"step": 15, "persona": "U4", "route": "/report-template", "must_see": "Usage Count"},
    {"step": 16, "persona": "U4", "route": "/notam", "must_see": "SNOWTAM"},
    # ── [차선 C · 2026-09-23] **W1 관제 프리셋 넷 + W2 판정 칸** 다섯 장을 더해
    #    16 → 21 장으로 간다. 앞의 16 장과 다른 점이 하나 있다: 이 다섯은 **같은
    #    라우트를 질의로 가른 화면**이다. 프리셋을 화면 안 상태로만 뒀으면 여기에
    #    적을 주소가 없었을 것이고, 「그 화면이 떴다」를 단언할 방법도 없었다 —
    #    프리셋을 `?preset=` 으로 둔 이유의 절반이 이것이다.
    #
    #    ⚠ `must_see` 는 **그 프리셋에서만 나오는 글자**여야 한다. 넷이 같은 라우트라
    #      「이벤트 목록」 같은 공통 글자로 단언하면 **프리셋이 안 바뀌어도 초록**이다.
    #      그래서 각 프리셋의 안내 줄(headline)을 그대로 쓴다.
    #
    #    ★ [UX-20/UX-22 · 2026-09-26 · 차선 C] **여덟 개의 `must_see` 를 함께 고쳤다.**
    #      화면의 안내 줄에서 절 ID(「UX-17」·「UX-18」)와 우리 절 이름(「W1 프리셋」)을
    #      뺐기 때문이다(GX-COPY §4). 이 상수는 **화면 문자열의 사본**이므로 화면만
    #      고치고 여기를 안 고치면 다음 촬영이 전부 빨개진다 — 그 빨강은 화면의 결함이
    #      아니라 사본이 뒤처졌다는 뜻이고, 그것이 가장 헷갈리는 종류의 빨강이다.
    #      ⚠ 화면 문구를 또 바꾸면 **같은 커밋에서** 이 줄들도 바꾼다.
    {"step": 17, "persona": "U1", "route": "/dsm/events?preset=unhandled",
     "slug": "dsm_events_preset_unhandled",
     "must_see": "미처리 — 아직 아무도 손대지 않은 것"},
    {"step": 18, "persona": "U1", "route": "/dsm/events?preset=recent",
     "slug": "dsm_events_preset_recent",
     "must_see": "지난 12시간 — 이 시간 창 안에 난 것"},
    {"step": 19, "persona": "U1", "route": "/dsm/events?preset=mine",
     "slug": "dsm_events_preset_mine",
     "must_see": "내 담당 — 내가 판정한 이벤트"},
    {"step": 20, "persona": "U1", "route": "/dsm/events?preset=system",
     "slug": "dsm_events_preset_system",
     "must_see": "시스템 — 설비 자신이 낸 신호"},
    #: W2 상세의 판정·대응 칸. 상세 화면 자체는 step 3 이 이미 찍는다 —
    #: 여기서 단언하는 것은 **누를 자리가 생겼다**는 사실이다(U1 #11).
    {"step": 21, "persona": "U1", "route": "/dsm/events/{event_id}",
     "slug": "dsm_events_id_verdict_panel",
     "must_see": "처리 단계 · 진위 판정"},
    # ── [2파 병합 · 2026-09-24] **세 장을 더해 21 → 24 장으로 간다.**
    #    차선 C 가 지은 화면 셋이고, 이 셋이 찍히기 전까지 UX-13·17·18 은
    #    「서버 면은 섰고 화면은 못 봤다」였다 — 그 상태에서 '구현'으로 적는 것이
    #    이 대장이 금지하는 부풀리기다(D-346 · P-9).
    #
    #    ⚠ `must_see` 는 각 페이지의 `HEADLINE` 상수 원문이다. 공통 글자로 단언하면
    #      **다른 화면이 떠도 초록**이 된다 — 프리셋 넷에서 배운 것과 같은 함정이다.
    {"step": 22, "persona": "U1", "route": "/dsm/queue",
     "slug": "dsm_queue_focus",
     "must_see": "지금 처리할 것 — 가장 급한 하나"},
    {"step": 23, "persona": "U2", "route": "/dsm/drill",
     "slug": "dsm_drill_mode",
     "must_see": "훈련 모드 — 켜면 알림이 사람에게 가지 않습니다"},
    {"step": 24, "persona": "U2", "route": "/dsm/cameras/import",
     "slug": "dsm_cameras_import_dryrun",
     "must_see": "카메라 일괄 등록 — 표를 먼저 봅니다"},
    # ── [2026-09-05 · 차선 C] **세 장을 더하고, 처음으로 휴대전화 크기로 찍는다.**
    #
    #    ★ 앞의 24 장은 전부 1440×900 이다. U3(이동 중 수신)는 **잰 적이 없었다** —
    #      데스크톱 폭에서 뜨는 모바일 화면은 사람이 실제로 보는 그 화면이 아니다.
    #      그래서 항목마다 `viewport` 를 둘 수 있게 했고, 없으면 데스크톱이다.
    #    ⚠ 페이지를 새로 만들지 않고 **같은 페이지의 크기만 바꾼다.** 새 페이지를
    #      만들면 로그인 세션이 따라오지 않아 전부 `/login` 으로 튕긴다.
    {"step": 25, "persona": "U2", "route": "/dsm/cameras/address",
     "slug": "dsm_cameras_address_fill",
     "must_see": "카메라 주소 채우기 — 한 대씩"},
    {"step": 26, "persona": "U2", "route": "/start?role=OPERATOR",
     # ★ [2026-09-05 · 턴 E] 규약은 «<route 뿌리>[_꼬리표]» 다. 이 화면의 뿌리는
     #   `/dsm/...` 이 아니라 **`/start`** 다 — 온보딩만 관문 밖 최상위에 서기 때문이다.
     #   1차판 `dsm_onboarding_start` 는 뿌리를 잘못 붙였고, **이번에 처음 찍혀서** 이제 보였다.
     #   (같은 종류를 QA 가 둘 고쳤다 — 두 턴 동안 안 보인 이유는 거기까지 가 본 적이 없어서다.)
     "slug": "start_onboarding",
     "must_see": "처음 시작하기 — 첫 근무일에 혼자 시작하기"},
    #: M1 — 휴대전화의 첫 화면. `MobileInbox.HEADLINE` 원문이다.
    #: ⚠ [실측 2026-09-05 · 턴 E · 차선 Q] **`slug` 는 아무 이름이나가 아니다.**
    #:   `verify_screens.expected_prefix` 는 파일 이름이 **라우트 뿌리로 시작**할 것을
    #:   요구한다(`<scenario>/<role>/<route 뿌리>[_꼬리표].png`). 앞선 이름
    #:   `m1_mobile_inbox` 는 뿌리가 `m_inbox` 가 아니라 **빨강**이었다.
    #:   이 어긋남이 두 턴 동안 안 보인 이유: 촬영이 17번에서 죽어 **27·28번까지
    #:   가 본 적이 없었다.** 죽는 도구는 자기 뒤에 있는 결함을 함께 숨긴다.
    {"step": 27, "persona": "U3", "route": "/m/inbox", "viewport": MOBILE_VIEWPORT,
     "slug": "m_inbox_m1",
     "must_see": "내게 온 이벤트"},
    #: M3 — 현장 회신. `MobileEventDetail.FIELD_REPLY_HEADLINE` 원문이다.
    #: ⚠ 「현장 상세」로 단언하지 않는다 — 그것은 M2 의 글자이고, M3 가 없어도 뜬다.
    #: 뿌리는 `m_events_<id>` 이고, `route_stems` 가 숫자 자리를 `id` 로 눕힌 것도
    #: 받아 준다 — 씨앗 id 는 실행마다 바뀌므로 **눕힌 쪽**을 쓴다(step 21 과 같다).
    {"step": 28, "persona": "U3", "route": "/m/events/{event_id}", "viewport": MOBILE_VIEWPORT,
     "slug": "m_events_id_m3_field_reply",
     "must_see": "현장 회신 — 본 것을 한 줄로"},
    # ══ [턴 U · 차선 Q · P-169 절 1] **회색 25 의 사유가 낡아서 더한 석 장** ══════════
    #
    #   P-142 가 2026-09-15 에 적은 지배 사실은 이랬다:
    #     「회색 25 가운데 24 는 그 절을 사람에게 보여 주는 화면이 제품에 없다 —
    #      frontend/src/features 에서 `/api/dsm/settings` 를 부르는 코드가 0건이다」
    #   [재실측 2026-09-18 · 턴 U] **그 0건이 13건이 됐다**(`frontend/src/features/dsm/api.ts`
    #   의 `dsmU56Endpoint`·`dsmU56NotifyEndpoint`·`dsmU56IntegrationEndpoint`·
    #   `dsmU24StatsEndpoint`). 화면도 라우터에 섰다(`routes.ts` · `routes.u24.ts`).
    #   그런데 **찍은 적이 없어서** 그 절들은 여전히 회색이었다 — 사슬의 둘째 고리(캡처)가
    #   비어 있었다. 사유가 낡은 것이지 제품이 없는 것이 아니다.
    #
    #   ⚠ 사이드바에 줄이 없어도 **주소로는 열린다**(`roleNav.NAV_HIDDEN_BUT_REACHABLE`).
    #     여는 권한은 서버가 판정하고, 403 이면 403 인 채로 찍힌다 — 가리지 않는다.
    #   ⚠ `must_see` 를 달지 않는다. 이 석 장은 **이번이 첫 촬영**이라 화면이 실제로 무슨
    #     글자를 쓰는지 우리가 못 봤다. 안 본 글자를 정답으로 적으면 그 글자가 제품이
    #     아니라 **우리 기대**를 재게 된다(P-132 가 여덟 자리에서 고친 그 모양이다).
    #     닿았는지는 `verify_feature_reach` 가 **호출과 상태코드**로 판정한다.
    {"step": 29, "persona": "U4", "route": "/dsm/audit",
     "slug": "dsm_audit_read",
     "why": "F-12-c2 성공·실패 감사로그 — 화면 AuditLog.tsx:89 가 GET /api/dsm/audit 를 "
            "부른다. 읽는 사람은 U2·U4·U5 (api_u24.py:307 머리말)"},
    {"step": 30, "persona": "U5", "route": "/dsm/notify",
     "slug": "dsm_notify_recipients",
     "why": "F-12-c3 수신자 관리 — NotifySettings.tsx:117 이 "
            "GET /api/dsm/settings/notify-rules/list 를 부른다"},
    {"step": 31, "persona": "U5", "route": "/dsm/integrations",
     "slug": "dsm_integrations_api_keys",
     "why": "F-12-c8 API 키 관리 — Integrations.tsx:159 가 "
            "GET /api/dsm/settings/api_keys 를 부른다 (하이픈 아니다 · D-470)"},
]

# ═══════════════════════════════════════════════════════════════════════════
# 로그인 실패 **다섯 갈래** — 그리고 **각 갈래의 출처가 다르다** (턴 I · 차선 C)
# ═══════════════════════════════════════════════════════════════════════════
# 왜 이 다섯을 여기서 찍나 [P-78 ② · 턴 H 가 문구를 세웠다]
# ------------------------------------------------------------------------
# 다섯 갈래 문구는 이미 있고 이미 한 번 찍혔다 — `docs/agent/evidence/P-78/shots/`.
# 그런데 그 다섯 장은 **검수 콘솔에 없다.** 인덱스 밖의 PNG 이고, 어디서 온 화면인지
# 콘솔이 말하지 않는다. 그리고 고객이 로그인 실패 화면을 볼 때 가장 먼저 묻는 것이
# 정확히 그것이다: **「이건 진짜로 서버가 그렇게 답한 건가, 우리가 지어낸 건가?」**
#
# ★ 그 답이 갈래마다 다르다. 그래서 한 값으로 적을 수 없다:
#     · 비밀번호 틀림 — **실측**. 아무것도 가로채지 않았다. 진짜 서버가 거절한다
#     · 잠김 · 권한 없음 · 서버 오류 · 연결 끊김 — **모의**. 응답을 가로채 지어냈다.
#       계정을 진짜로 잠그거나 서버를 진짜로 죽여서 찍지 않는다 — 그것은 이 실행체가
#       할 일이 아니고, 하려 들면 다른 차선의 서버를 무너뜨린다
#
# ⚠ **없는 계정으로 두드린다.** 실재 계정으로 「비밀번호 틀림」을 찍으면 실패 횟수가
#   쌓이고 다섯 번째에 그 계정이 **진짜로 잠긴다** — 캡처 한 장 때문에 다음 차선이
#   못 들어간다. 화면은 「아이디가 틀렸다」와 「비밀번호가 틀렸다」를 **한 문장으로 접으므로**
#   (`loginCopy.judgeLoginFailure` — 계정 존재 여부를 남에게 알리지 않는다) 이 갈래의
#   화면은 없는 계정으로도 **똑같다.**
#
# ⚠ `must_see` 는 `frontend/src/features/login/loginCopy.ts` 의 **원문 사본**이다.
#   그 파일이 바뀌면 여기도 같은 커밋에서 바꾼다 (TARGETS 의 `must_see` 와 같은 규약).
LOGIN_NOBODY = "gxprobe_없는계정_ti"        # 실재하지 않는다 — 잠글 계정이 없다

LOGIN_BRANCHES = [
    {"step": "L1", "persona": "U1", "kind": "credentials", "slug": "login_credentials",
     "must_see": "아이디 또는 비밀번호가 올바르지 않습니다.",
     "inject": None,
     "data_source": "실측",
     "why": "가로채지 않았다 — 진짜 서버(8000)가 거절한 답이다"},
    {"step": "L2", "persona": "U1", "kind": "locked", "slug": "login_locked",
     "must_see": "계정이 잠겼습니다.",
     "inject": {"status": 423,
                "body": {"success": False, "status": 423,
                         "message": {"ko": "계정이 잠겼습니다."},
                         "lock_minutes": 12, "lock_seconds": 34}},
     "data_source": "모의",
     "why": "서버의 잠금 본문 모양을 주입했다 — 계정을 진짜로 잠그지 않는다"},
    {"step": "L3", "persona": "U1", "kind": "forbidden", "slug": "login_forbidden",
     "must_see": "이 계정에는 접근 권한이 없습니다.",
     "inject": {"status": 403,
                "body": {"success": False, "status": 403,
                         "message": {"ko": "권한이 없습니다."}}},
     "data_source": "모의",
     "why": "403 을 주입했다 — 권한 없는 실재 계정을 만들어 찍지 않는다"},
    {"step": "L4", "persona": "U1", "kind": "server", "slug": "login_server_error",
     "must_see": "지금 로그인할 수 없습니다.",
     "inject": {"status": 500, "html": True},
     "data_source": "모의",
     "why": "500 을 주입했다 · 본문은 HTML(장고 오류 쪽) — 그 바이트가 화면에 새는지도 본다"},
    {"step": "L5", "persona": "U1", "kind": "network", "slug": "login_network",
     "must_see": "서버에 연결하지 못했습니다.",
     "inject": {"abort": True},
     "data_source": "모의",
     "why": "연결 자체를 끊었다 — axios 원문이 태어나던 자리"},
]


#: ★ [실측 2026-09-13 · D-386] 열어 보고 **찍지 못한 화면**. 목록에 남긴다 —
#:   못 찍은 것을 목록에서 지우면 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아진다.
#:   `/users` 는 API 6건이 전부 200 인 채로 **본문 글자 수가 0** 이었다(빈 화면).
#:   결함으로 등재했다: DA-05/blockers.yaml :: RJCORE_BLANK_ON_NO_PERMISSION
#: ★★ [실측 2026-09-07 · P-98] **역할 있는 계정으로 다시 쟀다. 답이 갈렸다.**
#:   앞선 두 줄은 「빈 화면이 난다」까지만 알았고 **왜인지는 몰랐다.** 이제 안다 —
#:   같은 화면이 `admin` 에게는 그려진다:
#:       /users     역할 0개 → 본문 0자   ·  admin → **29행 + Add New User**  [실측]
#:       /handover  역할 0개 → 본문 0자   ·  admin → **8행 + Create A Handover** [실측]
#:   즉 이 둘의 빈 화면은 **권한 때문**이고, 결함은 「못 본다」가 아니라
#:   **「못 본다고 말하지 않는다」**다. RJCORE_BLANK_ON_NO_PERMISSION 의 정확한 모양이다.
#:
#:   ⚠ 그러나 `/handover` 는 **`fire_user` 에게도 본문 68자**다 [실측] — 곁줄만 있고
#:     내용이 없다. 그 화면의 자리(「인계 메모」)는 U1 의 곁줄에 **버젓이 있다.**
#:     관제요원이 자기 곁줄에서 누를 수 있는 자리가 눌러도 아무것도 없는 상태다.
KNOWN_BLANK = [
    {"route": "/users", "why": "역할 0개: 본문 0자 · API 6건 200 · JS 오류 0건 — 안내 대신 "
                               "빈 화면. **admin 으로는 29행이 그려진다**(권한 때문이다) "
                               "(DA-03 §3-4 위반 · rj-core §0.4)"},
    {"route": "/survey-profile", "role_checked": ["admin", "fire_admin", "fire_user"],
     "why": "★ [P-98] **역할이 있으면 더 안 보인다.** 역할 0개에서는 `Add New Profile` "
            "단추라도 떴는데, admin·fire_admin·fire_user 셋 다 **머리줄뿐**이다 "
            "(본문 296·172·103자 · API 전부 200 · JS 오류 0건). 권한이 올라갔는데 "
            "화면이 줄었다 — 이 뒤집힘은 권한 결함이 아니라 화면 결함이다"},
    # ★ [실측 2026-09-14 · D-396] **두 번째 빈 화면.** `/users` 와 같은 모양이다 —
    #   API 실패 0건 · JS 오류 0건인 채로 본문만 0자다. 한 건이면 그 화면의 사정이지만
    #   **둘이면 성질**이다. RJCORE_BLANK_ON_NO_PERMISSION 에 표본을 더했다.
    {"route": "/handover", "why": "본문 0자 · API 실패 0건 · JS 오류 0건 — /users 와 같은 모양"},
]

#: ★ [실측 2026-09-14 · D-396] 열었더니 **다른 화면이 떴다.** 빈 화면과는 다른 결함이다 —
#:   빈 화면은 「왔는데 아무것도 없다」이고, 이것은 **「거기 갈 수 없다」**이다.
#:   둘을 한 칸에 두면 고치는 사람이 어디를 볼지 모른다 (D-377 ㉠㉡㉢ 를 가른 것과 같은 이유).
#:   ⚠ 1차판은 「이 계정의 `role` 은 `NO_ROLE` 이다 — 역할이 있는 계정에서는 다를 수
#:     있고, 그것은 **아직 재 보지 않았다**」로 끝났다. [P-98 · 2026-09-07] **재 봤다.**
#:     `admin` 으로도 둘 다 `/profile` 로 간다 — 권한이 아니라 **라우팅**이다.
KNOWN_REDIRECT = [
    {"route": "/monitoring-dashboard", "landed": "/profile",
     "role_checked": ["admin"],
     "why": "요청한 경로가 아니라 이 계정의 홈 화면이 떴다 — 라우트에 도달하지 못한다. "
            "★ [P-98 2026-09-07] **`admin` 으로 다시 쟀다: 똑같이 /profile 로 간다.** "
            "위 주석이 열어 둔 물음(「역할이 있으면 다를 수 있다」)의 답이 나왔다 — "
            "**권한 문제가 아니다.** 최고 권한에서도 못 간다"},
    {"route": "/intergrated-dashboard", "landed": "/profile",
     "role_checked": ["admin"],
     "why": "같음 — `admin` 에서도 /profile 로 간다 [P-98 실측]. "
            "둘 다 App.tsx 의 별도 라우트 묶음(189~211줄)에 있다"},
]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _django():
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.apps import apps
    return apps


# ---------------------------------------------------------------------------
# 씨앗 — **시험 데이터만.** 빈 화면도 화면이지만, 빈 화면만 찍으면
#        「목록이 그린다」와 「목록이 비어 있다」가 구별되지 않는다 (D-301 의 화면 판).
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 분류 등록부 참조 (D-270 ③) — **주인 없는 행을 만들지 않는다**
# ---------------------------------------------------------------------------
def _assert_owned(label: str, group_id) -> None:
    """이 스크립트가 쓰는 모델이 **소유가 필요한 모델인가**를 등록부에 묻는다.

    ★ 형식적으로 등록부를 import 하는 것이 아니다. 이 스크립트는 시험 데이터를
      심었다가 지우는데, **심는 순간 주인이 없으면** 그 행은 어느 테넌트에도 안 보이거나
      (읽기 격리) 모두에게 보인다(공용 마스터로 오인). 둘 다 나쁘고, 둘의 차이가
      바로 `SHARED_MASTERS` 와 `TENANT_UNASSIGNED` 다.

    등록부가 「공용도 아니고 주인 없음도 아니다」라고 말하면 **group 이 반드시 있어야 한다.**
    """
    sys.path.insert(0, "/app")
    try:
        from tests.tenant_classification import SHARED_MASTERS, TENANT_UNASSIGNED
    except ImportError:                       # 등록부를 못 읽으면 **판정 불가**다
        raise RuntimeError(
            "분류 등록부(tests/tenant_classification.py)를 못 읽었다 — "
            "소유가 필요한지 모르는 채로 쓰지 않는다 (D-270 ③)")
    if label in SHARED_MASTERS or label in TENANT_UNASSIGNED:
        return                                 # 등록부가 「주인 없어도 된다」고 말한다
    if not group_id:
        raise RuntimeError(
            f"{label} 은 등록부에서 공용 마스터도 미배정 선언도 아니다 — "
            f"**소유(group)가 있어야 한다.** 주인 없이 심으면 그 행은 격리 판정에서 "
            f"「공용」과 구별되지 않는다 (D-270 ③)")


def _borrow_real_address(SM, gid):
    """**짐작하지 않는다** — 이 소속의 실재 카메라가 이미 든 주소를 그대로 빌린다.

    ★ [턴 U · 차선 Q · U3#2 빨강] 씨앗 카메라의 `install_address` 가 비어 있어서
      사건 상세의 `address` 가 늘 빈 값이었고, 「어디로 가나」(U3#2)는 **제품이 아니라
      씨앗 때문에** 빨강이었다. 그렇다고 여기서 주소 문자열을 지어내면 그것은
      **모의 데이터**다 — 알림에 나가는 값과 같은 칸이라 더더욱 지어내지 않는다.
      그래서 규칙은 하나다: **이미 DB 에 있는 실재 카메라의 주소를 재사용**하고,
      한 대도 없으면 **빈 채로 두고 그 사실을 씨앗 명세에 적는다**(빈 것은 빈 것이다).

    돌려주는 것: (install_address, install_address_detail, address_source, 빌린 카메라 pk)
    한 대도 없으면 ("", "", "unset", None).
    """
    row = (SM._base_manager
           .filter(group_id=gid)
           .exclude(code__startswith=PROBE_TAG)
           .exclude(install_address__isnull=True)
           .exclude(install_address="")
           .order_by("pk").first())
    if row is None:
        return "", "", "unset", None
    return (row.install_address or "",
            row.install_address_detail or "",
            row.address_source or "manual",
            row.pk)


def seed_events(username: str, n: int = 2, address: str | None = None) -> int:
    """★ 씨앗은 **그 계정이 실제로 볼 수 있는 자리**에 심는다.

    `address` — 씨앗 카메라의 설치 주소 (턴 U · P-169 절 6 · U3#2).
      · `None`(기본) = **DB 의 실재 카메라 주소를 재사용**한다(`_borrow_real_address`).
        한 대도 없으면 빈 채로 두고 씨앗 명세(`SEED_SPEC`)에 「빌릴 주소 없음」을 적는다.
      · 문자열 = 부르는 쪽이 정한 주소(V 가 특정 주소로 재야 할 때만). 지어낸 값을
        기본으로 삼지 않는다 — 기본값은 언제나 **실재 재사용**이다.

    1차판은 `group` 없이 심었고, 그래서 세 화면이 전부 「0건」·「404」로 찍혔다 —
    테넌트 좁히기가 **제대로 걸린 결과**다(F-09). 격리를 끄고 찍으면 그것은 고객이 볼
    화면이 아니므로, 끄는 대신 **계정에 소속을 주고 그 소속으로 심는다.**
    격리는 그대로 두고, 보이는 것만 진짜로 만든다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model

    from common.tenant_filters import get_user_group

    U = get_user_model()
    user = U._base_manager.get(username=username)
    # ★ 소속은 `CoreUser` 가 아니라 **프로필 연결**이 들고 있다. 제품이 그렇게 읽으므로
    #   (`common.tenant_filters.get_user_group`) 여기서도 그대로 읽는다 — 두 벌로 읽으면
    #   화면이 보는 소속과 씨앗이 심긴 소속이 갈라진다(D-369).
    group = get_user_group(user)
    if group is None:
        Link = apps.get_model("user", "UserProfileLink")
        Group = apps.get_model("user", "UserGroup")
        group = Group._base_manager.order_by("pk").first()
        if group is None:
            raise RuntimeError("UserGroup 이 한 건도 없다 — 씨앗을 심을 소속이 없다")
        link = getattr(user, "userprofilelink", None)
        if link is None:
            Link._base_manager.create(user=user, group=group)
        else:
            link.group = group
            link.save(update_fields=["group"])
        user.refresh_from_db()
        group = get_user_group(user)
        if group is None:
            raise RuntimeError("소속을 붙였는데도 제품이 읽지 못한다 — 두 경로가 갈라졌다")
    gid = group.pk
    _assert_owned("stream_monitors.StreamMonitor", gid)
    _assert_owned("stream_monitors.DetectionEvent", gid)
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    #: [턴 U · 절 6] 주소 있는 씨앗 — 기본은 **실재 카메라의 주소 재사용**이다.
    if address is None:
        addr, addr_detail, addr_src, borrowed_from = _borrow_real_address(SM, gid)
        addr_why = ("실재 카메라 pk=%s 의 주소를 재사용" % borrowed_from
                    if borrowed_from else
                    "이 소속에 주소 있는 실재 카메라가 0대 — 빈 채로 둔다(짐작하지 않는다)")
    else:
        addr, addr_detail, addr_src, borrowed_from = address, "", "manual", None
        addr_why = "부르는 쪽이 --seed-address 로 정한 값"
    monitor, _ = SM._base_manager.get_or_create(
        code=f"{PROBE_TAG}-CAM",
        defaults=dict(name=f"{PROBE_TAG} 캡처용 카메라", ip_source="127.0.0.1",
                      is_active=False, is_visualize=False, order=9998,
                      is_external=False, address_source="",
                      group_id=gid),
    )
    if monitor.group_id != gid:
        monitor.group_id = gid
        monitor.save(update_fields=["group"])
    #: 이미 있던 씨앗 카메라도 이번 회의 주소로 맞춘다 — 지난 회의 빈 주소가 남으면
    #: 「주소를 심었다」와 「화면이 빈 주소를 그린다」가 구별되지 않는다.
    if addr:
        monitor.install_address = addr
        monitor.install_address_detail = addr_detail
        monitor.address_source = addr_src
        monitor.save(update_fields=["install_address", "install_address_detail",
                                    "address_source"])
    now = datetime.now(timezone.utc)
    # ★★ [실측 2026-09-16 · P-9] 1차판은 여기서 `DE._base_manager.create(...)` 로
    #   행을 **직접 만들었다.** 지시서가 정한 「실제 이벤트」의 정의로는 그것이 **모형**이다:
    #       실제 = K1 이벤트 생성 경로를 통과해 생긴 행. 직접 INSERT 는 모형이다
    #   화면 16장은 그 모형 위에서 찍혔다. 무엇을 숨겼나 — 구체적으로:
    #     · `event_type` 이 `gxprobe-D384-screen` 이었다. **열거값이 아니다.**
    #       K1 의 `_validate` 를 안 지나므로 아무 문자열이나 들어가고, 화면과 통계는
    #       그것을 유형으로 읽는다
    #     · 중복 억제(F-04)·주소 조회(FX-5)·클립 참조가 **한 번도 안 돈다.**
    #       그 경로의 결함은 씨앗으로 찍은 화면에서 절대 드러나지 않는다
    #   **모형 데이터는 파이프라인을 건너뛴 만큼 결함을 숨긴다** — 화면을 띄우는 것이
    #   가장 강한 시험이라는 D-386 이 그만큼 약해진다. 그래서 실제 경로로 바꾼다.
    from common.tenant_scope import TenantScope
    from kernels.k1_event import record_detection

    scope = TenantScope.system(reason="캡처 씨앗 — 탐지 파이프라인에는 요청자가 없다")
    first = None
    for i in range(n):
        #: 시각을 벌린다 — 같은 (stream, type) 이 10초 안에 다시 오면 K1 이 접는다(F-04).
        #: 접히면 「심은 수」와 「생긴 수」가 갈라지고, 그 차이를 모르면 수가 거짓이 된다.
        result = record_detection(
            scope=scope, stream_monitor_id=monitor.pk,
            event_type=("fire" if i == 0 else "flood"),
            severity=("critical" if i == 0 else "warning"),
            occurred_at=now - timedelta(minutes=2 * (i + 1)),
            snapshot_path="",          # MinIO 부재 — 비어 있는 채로 둔다 (P-9)
            #: ★ [P-156] 심는 순간부터 **어느 회의 씨앗인지** 적는다(`track_id` — 화면이 안 그리는
            #:   자유 칸 · `probe_marks` 규약). 판정 뒤 `judged=1` 을 덧붙이고, 다음 회의 표본은
            #:   이 표식(또는 씨앗 카메라 이름)으로 걸러진다. 정리(`clean_events`)가 못 돈 회의
            #:   씨앗도 이 표식 덕에 다음 표본에 안 섞인다.
            track_id=_probe_mark_string(RUN_STAMP),
        )
        first = first or result.event_id
        SEEDED_EVENT_IDS.append(result.event_id)
        SEED_SPEC.setdefault("events", []).append({
            "event_id": result.event_id,
            "event_type": ("fire" if i == 0 else "flood"),
            "severity": ("critical" if i == 0 else "warning"),
            "occurred_at": (now - timedelta(minutes=2 * (i + 1)))
                           .replace(microsecond=0).isoformat(),
        })
    _ = DE  # 위 주석의 대상이었던 이름 — 지우지 않고 남긴다
    #: ★ [P-170 ②] **넘길 것을 여기서 적는다.** 아래 네 칸이 뒤 도구들이 읽는 전부다:
    #:   id · severity · probe 표식 · 시각. 주소는 절 6 의 산물이라 함께 적는다.
    SEED_SPEC.update({
        "note": "P-170 ② 씨앗 id 파이프 — capture_screens 가 심은 것. "
                "읽는 쪽: verify_click_completes · verify_feature_reach · measure_onboarding_t "
                "(`--seed-file`). 이 파일은 손으로 고치지 않는다(runs/ 는 실행분이다).",
        "run": RUN_STAMP,
        "seeded_at": datetime.now().replace(microsecond=0).isoformat(),
        "probe_mark": _probe_mark_string(RUN_STAMP),
        "probe_tag": PROBE_TAG,
        "monitor_code": monitor.code,
        "group_id": gid,
        "event_ids": list(SEEDED_EVENT_IDS),
        "first_event_id": first,
        "address": {"install_address": addr, "install_address_detail": addr_detail,
                    "address_source": addr_src, "borrowed_from_monitor": borrowed_from,
                    "why": addr_why},
    })
    return first


def _write_seed_file() -> Path | None:
    """`runs/<RUN_STAMP>/seed.json` — **뒤 도구가 읽는 단 하나의 자리** (P-170 ②).

    ★ 씨앗을 심지 않았으면 쓰지 않는다. **빈 파일을 쓰면 「최신」이 빈 것을 가리키고**,
      그러면 뒤 도구가 지난 회의 진짜 씨앗 대신 이번 회의 빈 것을 읽는다.
    """
    if not SEED_SPEC.get("event_ids"):
        return None
    _keep_run_copy("seed.json", json.dumps(SEED_SPEC, ensure_ascii=False, indent=2))
    p = RUNS_DIR / RUN_STAMP / "seed.json"
    print(f"[SHOT] 씨앗 명세 → {p} (사건 {len(SEED_SPEC['event_ids'])}건 · "
          f"표식 {SEED_SPEC['probe_mark']})")
    return p


def clean_events() -> dict:
    apps = _django()
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    #: ★ [실측 2026-09-16] 씨앗이 실제 경로로 바뀌면서 `event_type` 은 **열거값**이
    #:   됐다(fire·flood). 그러니 유형으로는 더 이상 못 고른다 — 골랐다면 씨앗이
    #:   **안 지워진 채 남고**, 다음 실행의 화면에 그 행이 섞인다.
    #:   지우는 근거는 이제 **씨앗 카메라 하나**다. 표는 하나여야 한다.
    ev = DE._base_manager.filter(stream_monitor__code__startswith=PROBE_TAG)
    n_ev = ev.count()
    ev.delete()
    mon = SM._base_manager.filter(code__startswith=PROBE_TAG)
    n_mon = mon.count()
    mon.delete()
    return {"events": n_ev, "monitors": n_mon}


# ---------------------------------------------------------------------------
# 로그인 — **동시 접속 잠금을 정직하게 푼다**
# ---------------------------------------------------------------------------
def _release_session(username: str) -> None:
    """dj-core 는 `user.token`/`refresh_token`/미소멸 토큰으로 「다른 기기 접속」을 판정한다.

    ★ 그 판정을 **끄지 않는다.** 끄면 제품의 성질이 바뀌고, 그러면 우리가 찍는 화면이
      고객이 볼 화면이 아니게 된다. 여기서는 **이 시험 계정의 흔적만** 지운다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model
    U = get_user_model()
    u = U._base_manager.filter(username=username).first()
    if u is None:
        return
    try:
        from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
        BlacklistedToken.objects.filter(token__user_id=u.id).delete()
        OutstandingToken.objects.filter(user_id=u.id).delete()
    except Exception as exc:                            # noqa: BLE001
        print(f"[SHOT] 토큰 정리 건너뜀: {type(exc).__name__} {exc}", file=sys.stderr)
    u.token = None
    u.refresh_token = None
    u.save(update_fields=["token", "refresh_token"])
    _ = apps  # django.setup() 만 필요했다


def read_roles(username: str) -> list:
    """찍은 사람의 역할을 **제품이 들고 있는 자리**에서 읽는다 (D-323).

    ★★ [실측 2026-09-07 · P-98] **두 판 연속으로 틀린 자리다.**
      1차판: `role = "OPERATOR"` 로 박아 두었다 — 진술이지 실측이 아니었다.
      2차판: `getattr(u, "role", None)` 로 읽었다 — 실측처럼 보였지만 이 제품에
             **`role` 이라는 단수 필드는 없다.** `getattr` 의 기본값이 조용히
             `None` 을 돌려주고, 그 `None` 이 `NO_ROLE` 로 적혔다.
      그래서 33장 전부가 `NO_ROLE` 로 표시됐고, 그 표시는 **역할이 있는 계정에서도
      똑같이 나온다.** 즉 이 칸은 아무것도 재고 있지 않았다 — 채워진 칸과 잰 칸은
      다르다. `getattr(x, "없는이름", None)` 은 **측정처럼 생긴 상수**다.

      제품이 실제로 들고 있는 자리는 **`user.roles` (M2M)** 다 [실측]:
          gxprobe_e2e        roles=[]                    ← 그래서 앞의 33장이 무효였다
          gxseed_u1_operator roles=[fire_user]
          gxseed_u2_manager  roles=[fire_admin]
          gxseed_u4_official roles=[view_only_-_anyang]
          gxseed_u5_sysop    roles=[admin]

    ⚠ 목록을 돌려준다 — 여러 역할을 가진 계정을 한 값으로 접으면 그 순간 다시
      「채워진 칸」이 된다. 파일 자리에 쓰는 이름은 `role_slug()` 가 따로 만든다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model
    u = get_user_model()._base_manager.filter(username=username).first()
    if u is None:
        raise RuntimeError(f"계정이 없다: {username} — 없는 계정으로 찍지 않는다")
    codes = []
    mgr = getattr(u, "roles", None)
    if mgr is not None and hasattr(mgr, "all"):
        for r in mgr.all():
            code = getattr(r, "code", None) or getattr(r, "name", None) or str(r)
            if code:
                codes.append(str(code))
    _ = apps
    return codes


def role_slug(codes: list) -> str:
    """파일 자리에 쓸 역할 이름 하나. **역할이 없으면 `NO_ROLE` 이라고 적는다.**

    ★ `NO_ROLE` 은 이제 **드문 값**이어야 한다. 읽는 곳이 맞으면 역할 있는 계정에서
      이 값이 나올 수 없다 — 나오면 그것은 화면의 사실이 아니라 **계정의 사실**이고,
      그 벌은 인수 증거로 쓰지 않는다 (P-98).
    """
    return "+".join(codes) if codes else "NO_ROLE"


def _wait_login_form(page) -> None:
    """로그인 칸이 **그려질 때까지** 기다린다 (P-98).

    * [실측 2026-09-07] 1차판은 `networkidle` 뒤 **1.5초 고정**이었다. 그 1.5초는
      두 번은 맞고 한 번은 틀린다 — 실제로 다섯 페르소나 벌의 첫 이동이
      「입력칸이 둘 미만」으로 죽었다. 그 빨강은 **화면의 결함이 아니라 기다림의
      결함**이고, 둘을 구별 못 하면 없는 결함을 쫓게 된다.
      `networkidle` 은 «요청이 멎었다»이지 «React 가 그렸다»가 아니다.
    """
    try:
        page.wait_for_selector("input", state="visible", timeout=30_000)
    except Exception as exc:                              # noqa: BLE001
        print("[SHOT] 로그인 칸을 30초 기다렸으나 안 떴다: %s %s"
              % (type(exc).__name__, exc), file=sys.stderr)
    page.wait_for_timeout(1_500)


def _confirm_end_session(page) -> bool:
    """「다른 기기에서 쓰이고 있다」 창이 떴으면 **확인을 누른다** (P-98).

    ★ 이 창은 제품의 진짜 갈래다(`end_previous_session`). 누르지 않고 서버 쪽에서
      토큰을 지워 우회할 수도 있지만, 그러면 우리가 찍는 화면이 **고객이 볼 화면이
      아니게 된다** — 이 실행체가 D-347 ①로 금지한 바로 그것이다.
    ⚠ 창이 없으면 **아무 일도 하지 않는다.** 「없었다」와 「눌렀다」는 다른 사실이므로
      돌려주는 값으로 가른다.
    """
    try:
        btn = page.get_by_role("button", name="Confirm")
        if btn.count() and btn.first.is_visible():
            btn.first.click()
            page.wait_for_timeout(9_000)
            return True
    except Exception as exc:                              # noqa: BLE001
        print(f"[SHOT] 세션 종료 확인창 처리 건너뜀: {type(exc).__name__} {exc}",
              file=sys.stderr)
    return False


def replace_plan(scenario_dir: Path, role: str) -> dict:
    """「대체」 규칙의 셈 — **지우지 않고** 무엇이 대체되고 무엇이 남는지 센다 (P-159 ③).

    같은 파일명은 새 것으로 대체(쓰기가 곧 대체다) · 없는 파일명은 남긴다 · 지우지 않는다.
    돌려주는 것은 수뿐이다: `existing`(지금 있는 PNG 전부) · `same_role`(이 역할 폴더의 PNG).
    """
    if not scenario_dir.is_dir():
        return {"existing": 0, "same_role": 0}
    pngs = list(scenario_dir.rglob("*.png"))
    #: 폴더 이름은 역할 코드다(`<벌>/<ROLE>/<slug>.png` · 예 `FIRE_USER`) — 페르소나가 아니라 역할로 묶인다.
    #: 정확한 대체 목록은 쓰는 순간 파일명으로 정해진다 — 여기서는 수만 센다.
    return {"existing": len(pngs),
            "same_role": sum(1 for p in pngs if p.parent.name.lower() == str(role).lower())}


def capture(*, web: str, user: str, password: str, event_id: int, role: str,
            api: str, persona: str, reset: bool) -> dict:
    from playwright.sync_api import sync_playwright

    # ★ 이번 실행이 남길 자리를 **먼저 비운다.** 이벤트 상세의 경로에는 그때그때의
    #   id 가 들어가므로, 비우지 않으면 지난 실행의 PNG 가 남아 인덱스와 어긋난다 —
    #   `verify_screens.py` 는 인덱스에 없는 PNG 를 「어디서 온 화면인지 말하지
    #   않는다」로 실패시킨다. 그 실패는 옳고, **비우는 것이 이쪽의 몫**이다.
    #
    # ★★ [P-98 · 2026-09-07] 그런데 **한 벌이 다섯 사람의 벌이 되면** 이 줄이 정확히
    #   반대로 나쁘다: U2 를 찍는 순간 U1 의 아홉 장이 사라지고, 인덱스만 남는다.
    #   그래서 비우는 것은 **`--reset` 을 받은 첫 실행 한 번뿐**이다. 그 뒤의 실행은
    #   자기 페르소나가 남길 자리만 덮어쓴다 — 남의 자리는 건드리지 않는다.
    #   ⚠ 비우기를 안 하면 지난 실행의 유령 PNG 가 남을 수 있다. 그 유령은
    #     `verify_screens.py` 가 「인덱스에 없는 캡처」로 **빨갛게** 잡는다 — 잡히는
    #     것이 옳다. 조용히 지우는 것보다 소리 나게 걸리는 편이 낫다.
    # ★★★ [P-159 ③ · 턴 T · 차선 Q] **비우지 않는다 — 「대체」 규칙이다.**
    #   위 두 문단이 말한 「첫 페르소나에서 한 번 비운다」는 P-154 뒤에는 틀린 처방이다:
    #   대장(INDEX · run_log · screen_routes)은 이제 **옛 항목 + 이번 항목**으로 합쳐 쓰는데,
    #   PNG 만 비우면 대장은 32장을 말하고 디스크에는 이번 장만 남는다 — 대장이 가리키는
    #   파일이 없는 상태가 「줄지 않았다」 게이트를 통과한 채 커밋된다.
    #   규칙: 같은 파일명이면 **새 것으로 대체** · 이번에 안 찍은 파일명은 **남긴다** · **지우지 않는다.**
    #   (`replace_plan` 이 무엇이 대체되고 무엇이 남는지 미리 센다 — 셈은 콘솔에 적힌다.)
    #   유령이 걱정되면 대장과 디스크를 **대조**한다(`verify_screens.py`) — 지우는 것으로 맞추지 않는다.
    if reset:
        plan = replace_plan(SCREENS / SCENARIO, role)
        print(f"[SHOT] 첫 페르소나 — 「대체」 규칙: 지우지 않는다 · 있는 파일 {plan['existing']}장 "
              f"(이 역할 폴더 {plan['same_role']}장은 같은 이름이면 새 것으로 대체 · 나머지는 남긴다)")
    SCREENS.mkdir(parents=True, exist_ok=True)
    #: 이 실행이 찍을 것만 고른다. 「누가 봤나」는 항목이 스스로 들고 있다.
    my_login = [b for b in LOGIN_BRANCHES if b.get("persona") == persona]
    my_targets = [t for t in TARGETS if t.get("persona") == persona]
    who = "%s · %s · %s" % (persona, user, role)
    entries, steps, page_errors = [], {}, []
    #: ★ [2026-09-05 · 턴 E · 차선 Q] **못 찍은 것 하나가 나머지를 삼키지 않는다.**
    #:   [실측] 이 파일은 첫 불일치에서 `raise` 했고, 17번(`?preset=unhandled`)의
    #:   문구가 **낡은 번들**과 안 맞아 **뒤의 12장(프리셋·큐·훈련·일괄등록·주소·
    #:   온보딩·모바일 둘)을 한 장도 못 찍었다.** 그 12장은 「해 봤더니 안 된다」가
    #:   아니라 **「해 보지도 못했다」**였고, 둘은 다른 사실이다(D-396 의 규칙을
    #:   이 파일 안에서 어기고 있었다).
    #:   그래서 **놓친 것을 모아 두고 계속 간다.** 색은 그대로다 —
    #:   `main` 이 `entries` 수로 빨강을 내므로 한 장이라도 못 찍으면 여전히 실패다.
    #:   ⚠ 그리고 이렇게 해야 `_rewrite_index` 가 돈다. 중간에 죽으면 PNG 는
    #:     지워진 채 인덱스만 옛 목록을 들고 남는다 — **인덱스가 없는 파일을
    #:     가리키는 것**이 이 저장소가 가장 싫어하는 종류의 거짓말이다.
    misses: list = []
    #: ★ [실측 2026-09-05 · 턴 E] **세션을 빼앗기면 화면 결함이 아니다.**
    #:   이 환경은 **동시 접속 1개**다. 다른 차선이 같은 계정으로 로그인하면
    #:   (`end_previous_session`) 이 브라우저가 로그인 화면으로 튕긴다. 그때
    #:   남은 화면은 전부 「문구가 없다」로 기록됐고 — 실제로 없던 것은 문구가
    #:   아니라 **세션**이었다. [그날 16장이 그렇게 기록됐다]
    #:   `walk_scenarios` 는 이미 이 갈래를 갖고 있다(`session_lost`). 이쪽에만
    #:   없어서 **같은 사고가 여기서만 화면 결함으로 읽혔다.**
    session_lost = False
    #: 화면이 **실제로 부른** API. 우리가 「이 화면은 이걸 부를 것이다」라고 적지 않는다 —
    #: 브라우저가 부른 것을 그대로 적고, `verify_route_alive.py` 가 그 목록을 때린다(D-386).
    api_calls: dict[str, list] = {}
    seen_calls: list = []
    #: ★ [실측 2026-09-07 · 턴 J · 차선 C] **찍은 화면은 API 기록 자리를 반드시 갖는다.**
    #:
    #:   `test_captured_screens_and_recorded_routes_agree` 가 빨갰다:
    #:       「`/login` 를 찍었는데 그 화면이 부른 API 가 기록되지 않았다」
    #:   시험이 옳았다. 로그인 실패 다섯 갈래(턴 I 에 늘린 것)는 `entries` 에는
    #:   다섯 줄을 넣으면서 `api_calls` 에는 **한 자도 안 적었다** — 그래서
    #:   인덱스에는 있고 기록에는 없는 화면이 생겼고, 그 화면 몫만큼
    #:   `verify_route_alive` 는 **때릴 것을 잃었다**(D-301: 때릴 것이 없는 판정기는
    #:   조용히 초록이 된다).
    #:
    #:   ⚠ **빈 목록을 사유 없이 남기지 않는다.** 「0건」과 「안 재 봤다」는 다른
    #:     사실이고, 사유가 없으면 다음 사람이 그 둘을 구별할 수 없다. 아래
    #:     `api_notes` 가 자리마다 그 한 줄을 들고 있다 — 목록이 비어도 **왜 비었는지**는
    #:     파일에 남는다.
    api_notes: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport=DESKTOP_VIEWPORT)
        page.on("pageerror", lambda e: page_errors.append(str(e)[:200]))
        page.on("response", lambda r: seen_calls.append(
            (r.request.method, r.url, r.status)))
        try:
            # ═══ 로그인 실패 **다섯 갈래** — 들어가기 **전에** 찍는다 (턴 I · 차선 C) ═══
            #   ★ 순서가 뜻이다: 성공한 세션을 만든 뒤에 실패를 찍으려면 로그아웃해야 하고,
            #     그러면 그 뒤 28장이 세션을 잃는다. 실패는 **문 앞에서** 찍는 것이 맞다.
            for b in my_login:
                inj = b.get("inject")
                handler_name = "**/api/v1/auth/login"

                def _make(inj):
                    def _h(route):
                        if inj.get("abort"):
                            route.abort()                     # 연결 자체를 끊는다
                        elif inj.get("html"):
                            route.fulfill(status=inj["status"], content_type="text/html",
                                          body="<html><body><h1>Server Error (500)</h1></body></html>")
                        else:
                            route.fulfill(status=inj["status"], content_type="application/json",
                                          body=json.dumps(inj["body"], ensure_ascii=False))
                    return _h

                if inj:
                    page.route(handler_name, _make(inj))
                try:
                    seen_calls.clear()
                    page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
                    _wait_login_form(page)
                    fields = page.locator("input")
                    if fields.count() < 2:
                        raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
                    fields.nth(0).fill(LOGIN_NOBODY)
                    fields.nth(1).fill("틀린비밀번호-ti")
                    page.get_by_role("button", name="Log In").click()
                    page.wait_for_timeout(4_000)
                    body_text = page.inner_text("body")
                    step = f"{SCENARIO}/{b['step']}"
                    if b["must_see"] not in body_text:
                        misses.append({"step": b["step"], "route": "/login",
                                       "must_see": b["must_see"],
                                       "why": f"실패 갈래 «{b['kind']}» 의 문구가 화면에 없다",
                                       "body": body_text[:200]})
                        print(f"[SHOT] X /login «{b['kind']}»: 「{b['must_see']}」 가 "
                              f"화면에 없다 — 찍지 않는다. 본문: {body_text[:160]!r}")
                        continue
                    when = datetime.now().replace(microsecond=0)
                    rel = "%s/%s/%s.png" % (SCENARIO, role, b["slug"])
                    out = SCREENS / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(out))
                    steps[step] = when.isoformat()
                    entries.append({
                        "route": "/login", "user_role": role, "scenario": step,
                        "captured_at": when.isoformat(), "file": rel,
                        #: ★ **갈래마다 다른 값이다.** 한 값으로 적으면 이 칸이 상수가 된다
                        "data_source": "%s (%s)" % (b["data_source"], b["why"]),
                        #: ★★ [P-98] **누가 봤나.** 이 칸이 없던 동안 33장 전부가
                        #:   역할 없는 계정의 화면이었고, 인덱스는 그것을 말하지 않았다.
                        #:   ⚠ 로그인 실패 다섯 갈래는 **로그인 전**이다 — 아직 아무도
                        #:     아니다. 그 사실을 「U1 이 봤다」로 적으면 그것이 거짓이 된다.
                        "persona": persona,
                        "viewed_by": "(로그인 전 · 아직 누구도 아니다) — %s 실행 중" % who,
                        "calls": [],
                    })
                    #: ★ [턴 J · 차선 C] **이 화면이 부른 것을 여기서 적는다.**
                    #:   ⚠ **주입한 응답은 세지 않는다.** L2~L5 의 로그인 응답은
                    #:     playwright 가 만들어 낸 것이고 **서버에 닿은 적이 없다** —
                    #:     그것을 「브라우저가 실제로 부른 것」 파일에 적으면 그 파일이
                    #:     거짓말을 하고, `verify_route_alive` 가 있지도 않은 상태값을
                    #:     기준으로 삼는다. 진짜로 나간 것(L1 의 401, 화면이 곁들여 부른
                    #:     설정 문 따위)만 남긴다.
                    real = {(m, u[len(api):], st) for m, u, st in seen_calls
                            if u.startswith(api + "/api/")
                            and not (inj and u.endswith("/api/v1/auth/login"))}
                    api_calls["/login"] = sorted(
                        set(api_calls.get("/login", ())) | real)
                    #: ★ [P-98] **이 화면이 부른 것**을 그 화면의 항목에 붙인다.
                    #:   `screen_routes.json` 은 라우트로 묶여 있어서 한 라우트가 여러
                    #:   장을 낼 때(로그인 다섯 장) 어느 장이 무엇을 불렀는지 못 가른다.
                    entries[-1]["calls"] = ["%s %s %s" % (m, pth, st)
                                            for m, pth, st in sorted(real)]
                    if real:
                        api_notes["/login"] = (
                            "로그인 실패 갈래에서 **서버에 실제로 나간 것만** 적었다 — "
                            "주입(L2~L5)한 응답은 서버에 닿지 않았으므로 세지 않는다")
                    else:
                        api_notes.setdefault("/login", (
                            f"이 갈래(«{b['kind']}»)에서 서버로 나간 우리 API 가 0건이다 — "
                            f"로그인 응답을 주입/차단했고 화면이 그 밖의 문을 부르지 않았다. "
                            f"0건은 통과가 아니라 **0건**이다 (D-301)"))
                    print(f"[SHOT] {rel} — 실패 갈래 «{b['kind']}» · 출처 {b['data_source']}"
                          f" · 실제로 나간 우리 API {len(real)}건")
                finally:
                    if inj:
                        page.unroute(handler_name)

            page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
            _wait_login_form(page)
            fields = page.locator("input")
            if fields.count() < 2:
                raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
            fields.nth(0).fill(user)
            fields.nth(1).fill(password)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(9_000)
            # ★★ [실측 2026-09-07 · P-98] **여기서 U1 이 못 들어갔다.**
            #   본문에 「End Session」이 떴다 — 제품이 「이 계정이 다른 기기에서
            #   쓰이고 있다. 앞 세션을 끊고 들어갈까?」를 **묻는 창**을 띄운 것이다
            #   (`LoginDesktop.tsx` · `end_previous_session`). 역할 없는 계정
            #   `gxprobe_e2e` 로 찍던 동안에는 이 창을 본 적이 없었고 — 아무도 그
            #   계정을 안 썼기 때문이다. **실제로 쓰이는 계정으로 옮기자마자** 제품의
            #   이 갈래가 처음 실행됐다. 역할 있는 계정으로 찍는 것이 왜 값이 큰지의
            #   작은 표본이다: 남이 쓰는 계정이라야 「남이 쓰고 있다」가 재현된다.
            #
            #   ⚠ 창을 **끄지 않고 누른다.** 서버의 동시 접속 판정을 우회하면 그것은
            #     고객이 볼 화면이 아니게 된다 — 사람이 하는 그대로 「확인」을 누른다.
            if _confirm_end_session(page):
                print("[SHOT] 다른 기기 세션 종료 확인창을 눌렀다 — "
                      "end_previous_session 갈래를 사람이 하는 그대로 지났다")
            if page.url.rstrip("/").endswith("/login"):
                raise RuntimeError(
                    f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
                    f"본문: {page.inner_text('body')[:160]!r}")


            for t in my_targets:
                route = t["route"].replace("{event_id}", str(event_id))
                seen_calls.clear()
                # ★ 크기를 **항목이 정한다.** 같은 페이지의 크기만 바꾼다 —
                #   새 페이지를 만들면 로그인 세션이 안 따라온다.
                page.set_viewport_size(t.get("viewport", DESKTOP_VIEWPORT))
                page.goto(f"{web}{route}", wait_until="networkidle", timeout=60_000)
                page.wait_for_timeout(6_000)
                # ★ **먼저 세션을 묻는다.** 문구를 먼저 보면 튕긴 화면의 본문에
                #   기다린 글자가 없다는 이유로 「화면 결함」이 기록된다.
                if page.url.rstrip("/").endswith("/login"):
                    session_lost = True
                    print(f"[SHOT] ★ {route}: **세션을 빼앗겼다** — 로그인 화면으로 "
                          f"튕겼다({page.url}). 이 환경은 **동시 접속 1개**다: 다른 "
                          f"차선이 같은 계정으로 들어오면 이쪽이 끝난다. "
                          f"**화면의 결함이 아니므로 여기서 멈춘다** — 남은 화면을 "
                          f"「문구가 없다」로 적으면 그 기록이 거짓이 된다")
                    break
                body = page.inner_text("body")
                #: ★★ [V 고침 2026-09-18 · 턴 U] **`must_see` 가 없는 항목이 생겼다.**
                #:   step 29~31(감사·수신자·API 키)은 「이번이 첫 촬영이라 화면의 글자를
                #:   우리가 못 봤다」는 사유로 **일부러 `must_see` 를 안 달았다**(위 TARGETS
                #:   머리말). 그런데 이 줄은 `t["must_see"]` 를 무조건 읽어 **KeyError 로
                #:   죽었고**, 그래서 U4 의 마지막 페르소나에서 실행 전체가 멈췄다 —
                #:   찍힌 장이 대장에 안 들어가고 뒤 도구(FC·온보딩)도 못 돌았다.
                #:   **문구를 지어내 채우지 않는다**(그러면 제품이 아니라 우리 기대를 잰다).
                #:   문구가 없으면 **문구 단언을 건너뛰고 찍는다** — 이 석 장의 판정은
                #:   `verify_feature_reach` 가 **호출과 상태코드**로 한다.
                must_see = t.get("must_see")
                if must_see and must_see not in body:
                    misses.append({
                        "step": t["step"], "route": route,
                        "must_see": t["must_see"], "why": "문구가 화면에 없다",
                        "body": body[:200]})
                    print(f"[SHOT] X {route}: 「{t['must_see']}」 가 화면에 없다 — "
                          f"찍지 않는다. 본문: {body[:160]!r}")
                    continue

                #: ★ [실측 2026-09-13] 1차판은 URL 을 `/api/` 로 잘랐고, 그래서
                #:   **구글 지도**(`maps.googleapis.com/maps/api/js`)가 우리 라우트
                #:   `/api/js` 로 둔갑했다. `verify_route_alive` 가 그 404 를
                #:   「죽은 라우트」로 보고했다 — 죽은 것은 라우트가 아니라 측정이었다(D-350).
                #: ★ 그리고 **질의문자열을 지우지 않는다.** 지우면 필수 인자가 사라져
                #:   살아 있는 라우트가 422 로 나온다 — 같은 종류의 두 번째 오답이었다.
                #: ★ [실측 2026-09-23 · 차선 C 가 잡은 것] **덮어쓰지 않고 합친다.**
                #:   한 라우트로 두 장을 찍으면(상세 화면 + 그 화면의 판정 패널)
                #:   1차판은 뒤엣것이 앞엣것의 기록을 **덮었다** — 인덱스는 21장인데
                #:   이 파일은 20자리였고, 사라진 한 자리만큼 `verify_route_alive` 가
                #:   때릴 것을 잃었다. **때릴 것이 줄어든 판정기는 조용히 더 초록이 된다**(D-301).
                #: ★ [P-98] **이 한 장이 부른 것**을 먼저 따로 센다. 아래 `api_calls`
                #:   는 라우트로 합치므로(같은 라우트 두 장) 항목에 그대로 붙이면
                #:   앞 장의 호출이 뒷 장의 기록에 섞인다 — 「이 화면이 무엇을 불렀나」를
                #:   묻는 자리에서 그 섞임은 오답이다.
                this_screen = sorted({(m, u[len(api):], st)
                                      for m, u, st in seen_calls
                                      if u.startswith(api + "/api/")})
                api_calls[route] = sorted(set(api_calls.get(route, ())) | set(this_screen))
                api_notes.setdefault(
                    route, "화면을 열고 브라우저가 부른 것을 그대로 적었다")
                #: ★ [실측 2026-09-14 · D-397] 이 접두 대조가 **조용히 0건을 낼 수 있다.**
                #:   `--api http://127.0.0.1:8000` 을 줬는데 번들은 `http://localhost:8000`
                #:   을 부르면 한 건도 안 맞는다. 화면은 다 떴고 데이터도 다 그려졌는데
                #:   기록만 비었다 — 그리고 그 빈 기록은 `verify_route_alive` 를
                #:   **「때릴 것이 없어 통과」**로 만든다. 0건은 통과가 아니다(D-301).
                #:   여기서는 세지 못한 URL 을 그대로 보여 준다 — 무엇과 안 맞았는지가
                #:   화면에 있어야 다음 사람이 5분 만에 고친다.
                if not api_calls[route]:
                    missed = sorted({u.split("/api/")[0] for _, u, _ in seen_calls
                                     if "/api/" in u})
                    misses.append({
                        "step": t["step"], "route": route,
                        "must_see": must_see or "(첫 촬영 · 기다린 글자 없음)",
                        "why": f"화면이 부른 우리 API 를 0건 기록했다 · "
                               f"`--api {api}` 와 번들 주소가 다르다 "
                               f"(실제로 부른 곳: {missed or '없음'})"})
                    print(f"[SHOT] X {route}: 화면이 부른 우리 API **0건** — "
                          f"`--api {api}` 와 번들이 부르는 주소가 다르다. "
                          f"실제로 `/api/` 를 부른 곳: {missed or '없음'}")
                    continue
                step = f"{SCENARIO}/{t['step']}"
                when = datetime.now().replace(microsecond=0)
                #: ★ [차선 C · 2026-09-23] 파일 이름을 **`slug` 로 받을 수 있게** 했다.
                #:   사유 둘, 둘 다 실측이다:
                #:     ① 질의문자열이 붙은 라우트(`/dsm/events?preset=unhandled`)를
                #:        그대로 파일 이름으로 쓰면 **`?` 가 들어간다.** 이 저장소의
                #:        `docs/` 는 윈도우 호스트에서 마운트되고, 윈도우는 파일 이름에
                #:        `?` 를 허용하지 않는다 — 캡처가 아니라 **저장**에서 죽는다.
                #:     ② 같은 라우트를 다른 단언으로 두 번 찍을 수 있다(상세 화면의
                #:        판정 칸). 이름이 route 뿐이면 뒤엣것이 앞엣것을 **덮고**,
                #:        인덱스에는 두 줄이 남는다 — 인덱스가 거짓말을 하게 된다.
                #:   `slug` 가 없으면 지금까지의 규칙 그대로다(기존 16장 불변).
                rel = "%s/%s/%s.png" % (SCENARIO, role,
                                        t.get("slug")
                                        or route.strip("/").replace("/", "_") or "root")
                out = SCREENS / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(out))
                steps[step] = when.isoformat()
                entries.append({
                    "route": route, "user_role": role, "scenario": step,
                    "captured_at": when.isoformat(), "file": rel,
                    #: ★ [턴 I · 차선 C] **항목이 자기 출처를 들고 다닌다.** 예전에는
                    #:   `_rewrite_index` 가 모든 줄에 `시드` 를 박았다 — 채워진 칸이었지
                    #:   잰 칸이 아니었다. 기본값은 여전히 「시드」다: 이 실행체는 씨앗을
                    #:   심고 그 씨앗이 그린 화면을 찍기 때문이다. 다른 값이 필요한 항목은
                    #:   `TARGETS` 에서 스스로 말한다.
                    "data_source": t.get("data_source", "시드"),
                    #: ★★ [P-98] **누가 봤나.** 페르소나 · 계정 · 역할코드.
                    #:   `user_role` 만으로는 U1 과 U3 이 구별되지 않는다 — 둘은 같은
                    #:   계정이고 **폭만 다르다**. 구별이 필요한 이유: U3 이 못 본 화면은
                    #:   권한 문제가 아니라 **화면 폭** 문제다.
                    "persona": t.get("persona"),
                    "viewed_by": who + (" · %dpx" % t.get("viewport", DESKTOP_VIEWPORT)["width"]),
                    "calls": ["%s %s %s" % (m, pth, st)
                              for m, pth, st in this_screen],
                })
                print("[SHOT] %s — %s" % (rel, ("「%s」 확인 후 캡처" % must_see)
                                          if must_see else "첫 촬영(기다린 글자 없음) · 찍었다"))
        finally:
            browser.close()

    return {"entries": entries, "steps": steps, "page_errors": page_errors,
            "api_calls": api_calls, "api_notes": api_notes, "misses": misses,
            "session_lost": session_lost}


#: 인덱스의 `screens:` 아래를 **이 실행체가 직접 쓴다.**
#: 사람이 손으로 옮겨 적게 두면 id 하나가 어긋나는 날 인덱스가 거짓말을 한다 —
#: 그리고 그 거짓말은 **고객이 보는 자리**에 실린다 (D-284).
_INDEX_HEAD = """screens:
  # ★ 아래는 `scripts/capture_screens.py` 가 **실행하면서 직접 쓴다.** 손으로 고치지 말 것 —
  #   손으로 옮겨 적으면 이벤트 id 하나가 어긋나는 날 인덱스가 거짓말을 하고,
  #   그 거짓말은 고객이 보는 자리에 실린다 (D-284).
  #
  #   전부 **브라우저가 실제로 지나간 화면**이다. 이 실행체는 화면마다
  #   「그 화면에만 있는 글자」를 먼저 찾고, 못 찾으면 **찍지 않고 실패한다** —
  #   로그인으로 튕긴 뒤 찍은 PNG 도 파일은 생기므로, 「파일이 생겼다」를 성공으로
  #   두면 이 인덱스가 거짓말을 싣게 된다.
  #
  #   ★★ [실측 2026-09-07 · P-98] **앞선 33장은 전부 역할 없는 계정이 찍은 것이었다.**
  #     `gxprobe_e2e` 의 역할 목록은 비어 있다(`user.roles` = []). 그 벌은 「제품이
  #     된다」의 증거가 아니라 **「역할 없는 사람에게 무엇이 보이는가」**의 측정이었고,
  #     그 자체로 값이 있으므로 지우지 않고 옮겼다:
  #         docs/agent/evidence/P-98/denied/  (33장 · 판정문 FINDINGS.md 와 함께)
  #     이번 벌은 **역할을 실제로 가진 계정 넷**으로 다시 찍는다. 그래서 항목마다
  #     `viewed_by` 가 붙는다 — 「누가 봤나」를 인덱스가 말하지 않으면 같은 사고가
  #     또 난다. 그 한 칸이 없어서 33장이 넉 달치 인수 증거 행세를 했다.
  #
  #   ⚠ `user_role` 은 계정의 **역할 코드**다(fire_user·fire_admin·admin·
  #     view_only_-_anyang). `NO_ROLE` 이 보이면 그것은 화면의 사실이 아니라
  #     **계정의 사실**이고, 그 줄은 인수 증거가 아니다.
"""


def _rewrite_index(entries: list) -> None:
    index = SCREENS / "INDEX.yaml"
    if not index.is_file():
        print(f"[SHOT] 인덱스가 없다: {index} — 항목을 적지 못했다", file=sys.stderr)
        return
    text = index.read_text(encoding="utf-8")
    head, sep, _ = text.partition("screens:")
    if not sep:
        print("[SHOT] 인덱스에 `screens:` 자리가 없다 — 항목을 적지 못했다", file=sys.stderr)
        return
    row = "\n".join((
        "  - route: {route}",
        "    user_role: {user_role}",
        "    scenario: {scenario}",
        '    captured_at: "{captured_at}"',
        "    file: {file}",
        #: ★ P-9 — **화면마다 데이터 출처를 적는다.** 시드로 찍은 화면은 실제 화면이지만
        #:   실제 사고는 아니다. 검수에서 고객이 그것을 구분할 수 있어야 하고,
        #:   구분 못 하면 「시드 화면」이 「현장 화면」으로 읽힌다 — 그건 착시가 아니라
        #:   거짓말이다(D-284). 실행체가 직접 쓴다 — 손으로 옮겨 적지 않는다.
        #: ★★ [턴 I · 차선 C] **여기 상수 `시드` 가 박혀 있었다.** 그래서 이 칸은
        #:   29장 내내 같은 값이었고, 같은 값만 나오는 칸은 출처가 아니라 상수다.
        #:   이제 **항목이 들고 온 값**을 쓴다 — 로그인 실패 다섯 갈래는 이 한 줄
        #:   때문에 서로 다른 출처(실측 1 · 모의 4)로 콘솔에 뜬다.
        "    data_source: {data_source}",
        #: ★★ [P-98 · 2026-09-07] **누가 봤나.** 이 칸이 없던 동안 인덱스는 33장 전부가
        #:   역할 없는 계정의 화면이라는 사실을 **한 번도 말하지 않았다.** `user_role`
        #:   칸은 있었지만 거기 적힌 `NO_ROLE` 이 「역할이 없다」인지 「읽는 곳이
        #:   틀렸다」인지 아무도 몰랐다 — 실제로는 후자였고, 그래서 아무도 안 봤다.
        #:   페르소나·계정·역할·폭을 **한 줄에** 적는다: 검수자가 한 눈에 읽어야 한다.
        "    persona: {persona}",
        "    viewed_by: \"{viewed_by}\"",
        #: ★ **이 화면이 부른 라우트.** 라우트로 묶인 `D-386/screen_routes.json` 은
        #:   같은 라우트의 두 장을 못 가른다. 여기는 **장 단위**다 — 0건이면 0건이
        #:   그대로 보인다(빈 목록은 통과가 아니다 · D-301).
        "    calls:{calls}",
        "",
    ))

    #: ★ P-154 — 이번 실행분은 runs/ 에, 대장에는 **옛 항목 + 이번 항목**을 쓴다.
    fresh_entries = list(entries)
    _keep_run_copy("INDEX_entries.json",
                   json.dumps(fresh_entries, ensure_ascii=False, indent=2, default=str))
    head_entries = _existing_index_entries()
    entries = merge_records(head_entries, fresh_entries, key=_by_file)
    assert_not_shrunk("INDEX.yaml", len(head_entries), len(entries))
    print(f"[SHOT] 대장 INDEX 합침 — 옛 {len(head_entries)}장 + 이번 {len(fresh_entries)}장 → {len(entries)}장")

    def _calls(e) -> str:
        got = e.get("calls") or []
        if not got:
            return " []   # 0건 — 이 화면은 우리 API 를 부르지 않았다"
        return "\n" + "\n".join('      - "%s"' % c for c in got)

    body = "".join(row.format(data_source=e.get("data_source", "시드"),
                              persona=e.get("persona") or "(없음)",
                              viewed_by=e.get("viewed_by") or "(적히지 않았다)",
                              calls=_calls(e),
                              **{k: v for k, v in e.items()
                                 if k not in ("data_source", "persona",
                                              "viewed_by", "calls")})
                   for e in entries)
    index.write_text(head + _INDEX_HEAD + body, encoding="utf-8")
    print(f"[SHOT] 인덱스 갱신 — {index.name} 에 {len(entries)}장")


# ═══════════════════════════════════════════════════════════════════════════
# 역할 0개 — **찍지 않는다**의 예외 하나 (P-105 · 턴 M · 차선 C)
# ═══════════════════════════════════════════════════════════════════════════
# ★ 위 `read_roles()` 가 역할 0개 계정에서 **판정 불가로 멈추는 것은 그대로 옳다.**
#   P-98 이 막은 것은 「역할 없는 계정으로 찍은 33장을 **인수 증거로** 싣는 일」이다.
#
#   그런데 P-105 에서 역할 0개 계정이 볼 화면이 **제품의 화면 하나로 정해졌다**
#   (온보딩 0행 · 「역할이 아직 없습니다」). 그 화면은 역할 0개 계정으로만 찍을 수
#   있다 — 역할이 있으면 뜨지 않기 때문이다. 그래서 **그 화면 하나만** 예외로 둔다.
#
# ⚠ 이 모드는 `SCREENS-1` 인덱스에 **넣지 않는다.** 넣으면 P-98 이 지운 혼동이
#   그대로 돌아온다(역할 없는 벌이 역할 있는 벌 행세를 한다). 자리는 따로다:
#       docs/agent/evidence/P-105/frontend/shots/
#   `verify_screens.py` 는 이 자리를 보지 않는다 — 보면 안 된다.
#
# ⚠ 그리고 이 모드는 **한 장을 찍는 것이 아니라 규칙을 확인한다**: 종전에 자료를
#   그리던 경로들을 그대로 다시 밟아, 그 자리마다 이 화면이 뜨는지 본다.
#   「한 화면만 보인다」는 한 장으로는 증명되지 않는다 — 나머지가 안 보여야 참이다.
ROLE0_HEADLINE = "역할이 아직 없습니다"

#: 종전에 **실제 자료를 그리던** 경로에서 골랐다 [실측 2026-09-07 · P-98/denied].
#: 첫 항목이 대표 장면이고, 나머지는 「여기도 이 화면인가」를 묻는 자리다.
ROLE0_ROUTES = [
    "/dsm/events",
    "/dsm/dashboard",
    "/profile",
    "/notam",
    "/multi-stream-monitor",
    "/m/inbox",
]


def capture_role0(*, web: str, user: str, password: str, out: Path) -> int:
    """역할 0개 계정으로 들어가 **그 하나뿐인 화면**을 찍는다 (P-105).

    돌려주는 값은 종료 코드다. 문구가 없으면 **찍지 않고 빨강**이다 —
    「파일이 생겼다」는 성공이 아니라는 이 파일의 규율은 여기서도 같다.
    """
    from playwright.sync_api import sync_playwright

    codes = read_roles(user)
    if codes:
        print(f"[SHOT] ★ «{user}» 에 역할이 있다({codes}) — 이 모드는 **역할 0개** "
              f"계정의 화면을 찍는 자리다. 역할이 있으면 그 화면은 뜨지 않는다")
        return EXIT_UNDECIDABLE
    print(f"[SHOT] {user} · 역할 **0개** [실측] — P-105 0행의 화면을 찍는다")

    out.mkdir(parents=True, exist_ok=True)
    shots, misses, page_errors = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport=DESKTOP_VIEWPORT)
        page.on("pageerror", lambda e: page_errors.append(str(e)[:200]))
        try:
            page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
            _wait_login_form(page)
            fields = page.locator("input")
            if fields.count() < 2:
                raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
            fields.nth(0).fill(user)
            fields.nth(1).fill(password)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(9_000)
            if _confirm_end_session(page):
                print("[SHOT] 다른 기기 세션 종료 확인창을 눌렀다")
            if page.url.rstrip("/").endswith("/login"):
                raise RuntimeError(
                    f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
                    f"본문: {page.inner_text('body')[:200]!r}")

            for i, route in enumerate(ROLE0_ROUTES):
                # 대표 장면(첫 자리)만 두 크기로 찍는다. 나머지는 「여기도 그 화면인가」를
                # 묻는 자리이므로 데스크톱 한 장이면 족하다.
                sizes = ([("desktop", DESKTOP_VIEWPORT), ("390", MOBILE_VIEWPORT)]
                         if i == 0 else [("desktop", DESKTOP_VIEWPORT)])
                for label, vp in sizes:
                    page.set_viewport_size(vp)
                    page.goto(f"{web}{route}", wait_until="networkidle", timeout=60_000)
                    page.wait_for_timeout(4_000)
                    if page.url.rstrip("/").endswith("/login"):
                        misses.append({"route": route, "why": "세션을 빼앗겼다",
                                       "landed": page.url})
                        print(f"[SHOT] ★ {route}: 세션을 빼앗겼다 — 멈춘다")
                        break
                    body = page.inner_text("body")
                    if ROLE0_HEADLINE not in body:
                        misses.append({"route": route, "size": label,
                                       "why": "역할 0개 화면이 아니다",
                                       "body": body[:240]})
                        print(f"[SHOT] X {route} [{label}]: 「{ROLE0_HEADLINE}」 가 "
                              f"없다 — 이 자리는 아직 다른 것을 그린다. "
                              f"본문: {body[:200]!r}")
                        continue
                    slug = route.strip("/").replace("/", "_") or "root"
                    rel = f"role0_{slug}_{label}.png"
                    page.screenshot(path=str(out / rel), full_page=(label == "390"))
                    shots.append({"route": route, "size": label, "file": rel,
                                  "body_len": len(body)})
                    print(f"[SHOT] {rel} — 「{ROLE0_HEADLINE}」 [실측]")
        finally:
            browser.close()

    (out / "role0_run.json").write_text(json.dumps(
        {"captured_at": datetime.now().isoformat(timespec="seconds"),
         "user": user, "roles": [], "headline": ROLE0_HEADLINE,
         "routes_tried": ROLE0_ROUTES, "shots": shots,
         "misses": misses, "page_errors": page_errors},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[SHOT] 찍은 것 {len(shots)}장 · 못 찍은 자리 {len(misses)} · "
          f"JS 오류 {len(page_errors)}건 → {out}")
    return EXIT_OK if shots and not misses else EXIT_FAIL



# ═══════════════════════════════════════════════════════════════════════════
# [P-170 ① · 2026-09-18 턴 U · 차선 Q] **재는 동안 아무도 로그인하지 않는다**
#
#   턴 T 에 V 가 48행을 재는 동안 조율자가 게이트를 돌렸고, 그 안의 로그인이 V 의 세션을
#   끊었다(계정당 세션 1개 → `end_previous_session` → 429 · D-487 ①). V 는 그 판을 버렸다.
#   이 도구는 **로그인을 한다** — 그러므로 LOCK 을 먼저 본다.
#
#   ★ **잠근 사람은 지나간다**: `GX_V_SESSION_ID` 가 LOCK 의 세션과 같으면 안 막는다.
#     그 밖의 사람에게는 **회색(exit 2)** 이다 — 회색은 초록이 아니다(D-301).
# ═══════════════════════════════════════════════════════════════════════════
def _v_lock_blocks(tag: str = "[SHOT]") -> bool:
    """V 단독 세션이 잠갔고 내가 그 사람이 아니면 True — 그때는 **재지 않는다**."""
    try:
        from v_lock import describe, is_locked
    except ImportError:                                   # 잠금 도구가 없으면 막지 않는다
        return False
    if not is_locked():
        return False
    print("%s ? **회색 — V 단독 중 · 재지 않음** (P-170 ① · docs/agent/evidence/V_LOCK)"
          % tag)
    print("%s   %s · 잠근 사람은 GX_V_SESSION_ID 를 주고 부른다" % (tag, describe()))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="화면 캡처 실행체 (D-347 · D-384 ②)")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--web", default="http://localhost:3002")
    ap.add_argument("--user", required=True,
                    help="첫 페르소나의 계정 — `--persona all` 이면 U1 의 계정이어야 한다")
    ap.add_argument("--password", required=True,
                    help="네 시드 계정은 **같은 비밀번호**를 쓴다 ($GX_SEED_ROLE_PASSWORD)")
    #: ★★ [P-98] **한 벌은 다섯 사람의 벌이다.** 33장을 한 계정으로 찍던 동안
    #:   그 계정이 역할 없는 계정이라는 사실을 아무도 못 봤다. 이제 화면마다
    #:   「누가 보는 화면인가」가 `TARGETS` 에 적혀 있고, 이 인자가 그 중 하나를 고른다.
    #:   `all` 은 U1→U2→U3→U4→U5 를 **차례로** 찍는다 — 이 환경은 동시 접속 1개다.
    ap.add_argument("--persona", default="all",
                    choices=["all"] + sorted(PERSONAS),
                    help="U1 관제요원 · U2 팀장 · U3 관제요원(390px) · "
                         "U4 재난안전과 · U5 관리자 · all(차례로 전부)")
    ap.add_argument("--dry-run", action="store_true",
                    help="씨앗·캡처 없이 두 자리에 닿는지만 본다")
    #: ★ [P-105 · 턴 M] **역할 0개 계정의 화면 하나.** 위 `read_roles()` 의 멈춤을
    #:   지나가는 유일한 길이고, 산출은 `SCREENS-1` 인덱스 **밖**에 남는다.
    ap.add_argument("--role0", action="store_true",
                    help="역할이 **0개**인 계정으로 P-105 0행의 화면을 찍는다 "
                         "(인덱스에 넣지 않는다 — 자리는 P-105/frontend/shots/)")
    #: ★★ [P-170 ② · 턴 U] **기본이 남기기로 바뀌었다.** 종전에는 `finally` 가 언제나
    #:   `clean_events()` 를 불러 씨앗을 지웠고, 그래서 뒤 도구에 넘길 id 가 없었다
    #:   (D-487 ② · 턴 T 오판). 지우려면 **손으로 적어야 한다.**
    ap.add_argument("--keep-seeds", dest="keep_seeds", action="store_true", default=True,
                    help="(기본) 씨앗을 **지우지 않는다** — runs/<stamp>/seed.json 으로 넘긴다")
    ap.add_argument("--clean-seeds", dest="keep_seeds", action="store_false",
                    help="캡처 뒤 씨앗을 지운다. 지우면 뒤 도구(click_completes·feature_reach·"
                         "measure_onboarding_t)가 읽을 사건이 없다 — 정리 담당이 따로 부를 때만")
    #: 절 6 — 기본은 **실재 카메라 주소 재사용**이다. 이 인자는 예외를 위한 것이고
    #: 값을 적으면 씨앗 명세에 「부르는 쪽이 정한 값」으로 남는다(짐작과 구별된다).
    ap.add_argument("--seed-address", default=None,
                    help="씨앗 카메라의 설치 주소를 손으로 정한다(기본: DB 의 실재 카메라 재사용)")
    args = ap.parse_args()

    if _v_lock_blocks():
        return EXIT_UNDECIDABLE

    import urllib.error
    import urllib.request
    for name, url in (("API", args.api + "/api/docs"), ("화면", args.web + "/")):
        try:
            urllib.request.urlopen(url, timeout=15)
        except urllib.error.HTTPError:
            pass                                  # 4xx 도 「서 있다」는 뜻이다
        except Exception as exc:                  # noqa: BLE001
            # ★ 닿지 못한 것은 **닿지 못했다**고 끝낸다. 0장을 통과로 만들지 않는다.
            print(f"[SHOT] {name} 에 닿지 못했다 ({url}): {type(exc).__name__} {exc}")
            print("[SHOT] 판정 불가 — 실행되지 않은 캡처를 성공으로 적지 않는다 (D-301)")
            return EXIT_UNDECIDABLE
    #: ★ [턴 I · 차선 C] 대상은 **둘을 더한 수**다 — 로그인 실패 다섯 갈래 + 화면 28장.
    #:   더하지 않으면 다섯 장이 늘어난 것만으로 이 명령이 빨개진다(수가 안 맞아서).
    #:   그 빨강은 「못 찍었다」가 아니라 **「셈이 낡았다」**이고, 가장 헷갈리는 종류다.
    print(f"[SHOT] [입력] API {args.api} · 화면 {args.web} · "
          f"대상 {len(TARGETS) + len(LOGIN_BRANCHES)}장"
          f" (화면 {len(TARGETS)} + 로그인 실패 갈래 {len(LOGIN_BRANCHES)})")
    _split = {}
    for _x in list(TARGETS) + list(LOGIN_BRANCHES):
        _split[_x.get("persona")] = _split.get(_x.get("persona"), 0) + 1
    print("[SHOT] [나눔] " + " · ".join(
        f"{k} {PERSONAS[k]['label']}({PERSONAS[k]['role']}) {v}장"
        for k, v in sorted(_split.items())))
    if args.dry_run:
        print("[SHOT] --dry-run — 두 자리 다 서 있다")
        return EXIT_OK

    #: ★ [P-105] 역할 0개 모드는 씨앗도 인덱스도 건드리지 않는다 — 여기서 갈라진다.
    if args.role0:
        for base in (ROOT / "docs", Path("/docs")):
            if (base / "agent" / "evidence").is_dir():
                out = base / "agent" / "evidence" / "P-105" / "frontend" / "shots"
                break
        else:
            out = ROOT / "docs" / "agent" / "evidence" / "P-105" / "frontend" / "shots"
        return capture_role0(web=args.web, user=args.user,
                             password=args.password, out=out)

    order = sorted(PERSONAS) if args.persona == "all" else [args.persona]
    #: ★ 목표 장수는 **고른 페르소나의 몫**이다. `all` 이면 33 그대로이고,
    #:   한 사람만 고르면 그 사람 몫이다 — 33 으로 재면 언제나 빨갛다.
    want_n = len([x for x in list(TARGETS) + list(LOGIN_BRANCHES)
                  if x.get("persona") in order])
    if args.persona != "all":
        print(f"[SHOT] ⚠ **한 사람만 찍는다({args.persona} · {want_n}장).** 인덱스는 "
              f"이 실행이 찍은 것만 싣게 되고, 남은 페르소나의 PNG 는 "
              f"`verify_screens.py` 가 「인덱스에 없는 캡처」로 빨갛게 잡는다. "
              f"온전한 벌은 `--persona all` 이다")

    # ★★ [P-98] **역할을 먼저 읽고, 없으면 찍지 않는다.**
    #   이 여섯 줄이 앞선 33장을 막았을 것이다. 역할 없는 계정으로 찍은 화면은
    #   「제품이 된다」의 증거가 아니라 「역할 없는 사람에게 무엇이 보이는가」의
    #   측정이고, 둘을 같은 폴더에 두면 뒤엣것이 앞엣것 행세를 한다.
    roles: dict = {}
    for pn in order:
        want = PERSONAS[pn]["username"]
        got_codes = read_roles(want)
        roles[pn] = role_slug(got_codes)
        print(f"[SHOT] {pn} {PERSONAS[pn]['label']} · {want} · "
              f"역할 {got_codes or '**없음**'} (제품이 들고 있는 값 · D-323)")
        if not got_codes:
            print(f"[SHOT] ★ {pn} 의 계정 «{want}» 에 역할이 **한 개도 없다.** "
                  f"역할 없는 계정으로 찍은 화면은 인수 증거가 아니다 — 찍지 않는다 (P-98)")
            return EXIT_UNDECIDABLE
        if got_codes != [PERSONAS[pn]["role"]]:
            print(f"[SHOT] ★ {pn} 의 역할이 대장과 다르다: 실측 {got_codes} · "
                  f"대장 {[PERSONAS[pn]['role']]} — 대장을 고치거나 계정을 고친 뒤 다시 온다")
            return EXIT_UNDECIDABLE
    if args.persona != "all" and args.user != PERSONAS[order[0]]["username"]:
        print(f"[SHOT] ★ --persona {order[0]} 의 계정은 "
              f"«{PERSONAS[order[0]]['username']}» 인데 --user 는 «{args.user}» 다 — "
              f"둘이 어긋나면 인덱스의 「누가 봤나」가 거짓이 된다")
        return EXIT_UNDECIDABLE

    #: 씨앗은 **한 번만** 심는다. 네 계정이 같은 소속(ETRI-Group)이므로 같은 행을 본다.
    #: 페르소나마다 다시 심으면 이벤트 id 가 바뀌고, 그러면 U1 이 찍은 상세 화면의
    #: 파일 이름과 U3 이 찍은 것이 서로 다른 사건을 가리킨다.
    _release_session(PERSONAS[order[0]]["username"])
    event_id = seed_events(PERSONAS[order[0]]["username"], address=args.seed_address)
    merged: dict = {"entries": [], "steps": {}, "page_errors": [],
                    "api_calls": {}, "api_notes": {}, "misses": [],
                    "session_lost": False}
    per_persona: dict = {}
    try:
        for i, pn in enumerate(order):
            who = PERSONAS[pn]
            print(f"[SHOT] ═══ {pn} {who['label']} · {who['username']} · "
                  f"{roles[pn]} — {who['note']} ═══")
            #: ⚠ **동시 접속 1개다.** 페르소나를 넘어갈 때마다 앞 계정의 흔적을 푼다.
            _release_session(who["username"])
            got = capture(web=args.web, user=who["username"],
                          password=args.password, event_id=event_id,
                          role=roles[pn], api=args.api, persona=pn,
                          reset=(i == 0 and args.persona == "all"))
            per_persona[pn] = len(got["entries"])
            merged["entries"] += got["entries"]
            merged["steps"].update(got["steps"])
            merged["page_errors"] += got["page_errors"]
            merged["misses"] += got["misses"]
            merged["api_notes"].update(got["api_notes"])
            for r, v in got["api_calls"].items():
                merged["api_calls"][r] = sorted(
                    set(merged["api_calls"].get(r, ())) | set(v))
            if got["session_lost"]:
                merged["session_lost"] = True
                print(f"[SHOT] ★ {pn} 에서 세션을 빼앗겼다 — 뒤의 페르소나는 찍지 않는다")
                break
    finally:
        #: ★ [P-156] **판정 뒤 표시 → 정리** 순서다. 정리가 실패해도 표시는 남아 다음 표본에서 빠진다.
        try:
            n_marked = _probe_mark(SEEDED_EVENT_IDS, RUN_STAMP, judged=True)
            print(f"[SHOT] probe 표시(judged=1): {n_marked}/{len(SEEDED_EVENT_IDS)}건")
        except Exception as exc:                        # noqa: BLE001
            print(f"[SHOT] ⚠ probe 표시 실패 — {type(exc).__name__}: {exc}", file=sys.stderr)
        #: ★ [P-170 ②] **표시 → 명세 쓰기 → (명시했을 때만) 정리.** 순서가 규약이다:
        #:   정리가 명세보다 먼저면 뒤 도구가 읽을 것이 없고, 표시가 정리보다 나중이면
        #:   정리가 실패한 회의 씨앗이 표식 없이 남아 다음 표본을 더럽힌다.
        try:
            _write_seed_file()
        except Exception as exc:                        # noqa: BLE001
            print(f"[SHOT] ⚠ 씨앗 명세 쓰기 실패 — {type(exc).__name__}: {exc}",
                  file=sys.stderr)
        if args.keep_seeds:
            print(f"[SHOT] 씨앗 정리: 건너뜀(--keep-seeds 기본) — 사건 "
                  f"{len(SEEDED_EVENT_IDS)}건을 남긴다. 지우려면 --clean-seeds")
        else:
            print(f"[SHOT] 씨앗 정리: {clean_events()}")
    got = merged
    print("[SHOT] 페르소나별 장수: "
          + " · ".join(f"{k} {v}장" for k, v in per_persona.items()))

    fresh_log = {
        "harness": "scripts/capture_screens.py",
        "scenario": SCENARIO,
        "ran_at": datetime.now().replace(microsecond=0).isoformat(),
        "steps": got["steps"],
        #: 브라우저가 뱉은 오류를 **숨기지 않는다.** 0건이면 0건이라고 적힌다.
        "page_errors": got["page_errors"],
    }
    #: ★ P-154 — 단계는 **합집합**(같은 단계는 새 판이 이긴다) · 오류는 이번 실행의 것
    #:   (지난 실행의 오류는 runs/ 사본과 git 이력에 있다 — 대장에 영원히 쌓으면 이번 것이 안 보인다).
    _keep_run_copy("run_log.json", json.dumps(fresh_log, ensure_ascii=False, indent=2))
    old_log = _read_json_ledger(SCREENS / "run_log.json")
    merged_log = dict(fresh_log)
    merged_log["steps"] = {**(old_log.get("steps") or {}), **fresh_log["steps"]}
    assert_not_shrunk("run_log.json steps", len(old_log.get("steps") or {}), len(merged_log["steps"]))
    (SCREENS / "run_log.json").write_text(
        json.dumps(merged_log, ensure_ascii=False, indent=2), encoding="utf-8")

    # ★★ [실측 2026-09-05 · 턴 E] **이 두 줄이 판정기를 두 턴 동안 속였다.**
    #
    #   1차판은 «`/repo/docs` 가 있으면 거기, 없으면 `/docs`» 로 골랐다. 그런데
    #   **자기가 `mkdir(parents=True)` 로 그 폴더를 만든다.** 첫 실행이 `/repo/docs/...`
    #   를 만들고 나면, 그 다음부터 이 판정은 **언제나 「여기가 맞다」**고 답한다 —
    #   판정이 자기가 만든 흔적을 근거로 삼는다.
    #
    #   결과: 인덱스(`_screens_dir()` 로 고른 자리)는 저장소에 닿는데 API 기록은
    #   **컨테이너 안에 갇혔다.** 저장소의 `screen_routes.json` 은 하루 전 것으로 멈춰 있었고,
    #   `test_captured_screens_and_recorded_routes_agree` 가 「찍었는데 기록이 없다」로
    #   계속 빨갰다. **두 표가 갈렸고, 갈린 이유가 파일 하나의 주소였다.**
    #
    #   고침: **인덱스가 실제로 있는 자리를 기준으로 삼는다**(`SCREENS`). 그 자리는
    #   `_screens_dir()` 가 **파일의 실재**로 골랐지 폴더의 실재로 고르지 않았다 —
    #   그래서 자기가 만든 것에 속지 않는다.
    routes_out = (SCREENS.parent.parent / "D-386" / "screen_routes.json")
    routes_out.parent.mkdir(parents=True, exist_ok=True)
    # ★★ [실측 2026-09-07 · 턴 J · 차선 C] **찍은 화면마다 자리를 만든다 — 비어도.**
    #
    #   빨갰던 시험: 「`/login` 를 찍었는데 그 화면이 부른 API 가 기록되지 않았다」.
    #   원인은 위 로그인 갈래가 `api_calls` 를 안 건드린 것이었고 거기서 고쳤다.
    #   그래도 **이 그물을 둔다**: 앞으로 누가 화면을 늘리면서 기록을 잊으면
    #   `screens` 에 그 라우트가 아예 없어지고, 없는 자리는 **아무도 못 센다.**
    #   여기서 빈 목록 + 사유로 자리를 만들면 그 자리가 눈에 보이고,
    #   시험은 「비었다」로 **빨개진다** — 그것이 옳다. 빈 기록은 통과가 아니다(D-301).
    #
    #   ⚠ 사유 없는 빈 목록은 만들지 않는다. 「0건이다」와 「안 재 봤다」가 같아지면
    #     다음 사람이 같은 자리를 다시 판다.
    api_notes = dict(got.get("api_notes", {}))
    shot_routes = {e["route"] for e in got["entries"]}
    for r in sorted(shot_routes - set(got["api_calls"])):
        got["api_calls"][r] = []
        api_notes[r] = ("찍었는데 이 화면이 부른 우리 API 를 **기록하지 못했다** — "
                        "기록기가 이 갈래에서 `api_calls` 를 채우지 않았다. "
                        "빈 목록은 통과가 아니다 (D-301)")
    fresh_doc = {
        "source": "scripts/capture_screens.py — 브라우저가 실제로 부른 것",
        "captured_at": datetime.now().replace(microsecond=0).isoformat(),
        #: ★ 키는 **라우트**이고, 화면 수와 다를 수 있다 — 한 라우트가 두 장을 낼 수 있기
        #:   때문이다(상세 + 판정 패널). 그래서 화면 수를 **따로 적는다**: 이 파일의 자리
        #:   수를 화면 수로 읽으면 「21장인데 20자리」가 결함처럼 보인다(실제로 그렇게 읽혔다).
        "screens_total": len(got["entries"]),
        "routes_total": len(got["api_calls"]),
        "screens": {k: [{"method": m, "path": p, "status": st}
                        for m, p, st in v] for k, v in got["api_calls"].items()},
        #: ★ P-9 — **데이터 출처를 화면마다 말한다.** 시드로 찍은 화면은 실제 화면이지만
        #:   **실제 사고는 아니다.** 고객이 검수에서 그것을 구분할 수 있어야 한다.
        #: ★ [턴 J · 차선 C] **자리마다 한 줄.** 목록이 비어 있을 때 그것이
        #:   「이 화면은 우리 API 를 안 부른다」인지 「기록기가 못 적었다」인지를
        #:   여기서 가른다 — 가르지 않으면 다음 사람이 그 둘을 같은 것으로 읽는다.
        "api_notes": api_notes,
        "data_source": "시드 (K1 record_detection 실제 경로 · 실제 사고 아님)",
        #: ★★ [P-98] **누가 봤나 — 장 단위로.** 라우트로 묶인 위 `screens` 만으로는
        #:   같은 라우트를 두 사람이 봤을 때 누가 무엇을 받았는지 못 가른다.
        "viewers": [{"file": e["file"], "route": e["route"],
                     "persona": e.get("persona"), "viewed_by": e.get("viewed_by"),
                     "user_role": e.get("user_role"),
                     "data_source": e.get("data_source"),
                     "calls": e.get("calls") or []}
                    for e in got["entries"]],
        "blank_screens": KNOWN_BLANK,
        #: 못 찍은 것을 **왜 못 찍었는지로 갈라** 적는다 (D-396). 한 칸에 두면
        #: 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아지고, 둘을 합치면
        #: 「아무것도 없다」와 「거기 갈 수 없다」도 같아진다.
        "redirected_screens": KNOWN_REDIRECT,
    }
    #: ★ P-154 — 대장에는 합쳐 쓴다. `screens` 는 라우트 합집합(새 판이 이긴다) · `viewers` 는
    #:   **파일 경로** 열쇠(같은 화면을 다른 역할이 본 기록은 다른 파일이다) · `api_notes` 는
    #:   이번에 호출을 기록한 라우트의 옛 사유를 **지운다**(「못 적었다」가 「적었다」 뒤에 남으면 거짓).
    _keep_run_copy("screen_routes.json", json.dumps(fresh_doc, ensure_ascii=False, indent=2))
    old_doc = _read_json_ledger(routes_out)
    merged = dict(fresh_doc)
    merged["screens"] = {**(old_doc.get("screens") or {}), **fresh_doc["screens"]}
    merged["api_notes"] = {k: v for k, v in (old_doc.get("api_notes") or {}).items()
                           if k not in fresh_doc["screens"]}
    merged["api_notes"].update(fresh_doc["api_notes"])
    merged["viewers"] = merge_records(list(old_doc.get("viewers") or []), fresh_doc["viewers"], key=_by_file)
    merged["screens_total"] = len(merged["viewers"])
    merged["routes_total"] = len(merged["screens"])
    assert_not_shrunk("screen_routes.json screens", len(old_doc.get("screens") or {}), len(merged["screens"]))
    assert_not_shrunk("screen_routes.json viewers", len(old_doc.get("viewers") or []), len(merged["viewers"]))
    routes_out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SHOT] 대장 screen_routes 합침 — 자리 {len(old_doc.get('screens') or {})} → {merged['routes_total']} · 화면 {len(old_doc.get('viewers') or [])} → {merged['screens_total']}")
    print(f"[SHOT] 화면이 부른 API 기록: {routes_out}")

    _rewrite_index(got["entries"])
    # ★ **못 찍은 것을 이름으로 남긴다.** 수만 적으면 다음 사람이 어느 화면인지
    #   다시 찾아야 하고, 다시 찾는 동안 「아마 데이터가 없었겠지」가 끼어든다.
    for m in got.get("misses", ()):
        print(f"[SHOT] 못 찍음 · step {m['step']} {m['route']} — {m['why']}"
              + (f" · 기다린 글자 「{m['must_see']}」" if m.get("must_see") else ""))
    if got.get("misses"):
        print(f"[SHOT] ★ 못 찍은 {len(got['misses'])}장은 **화면의 결함일 수도, "
              f"서버가 내는 번들이 낡은 것일 수도 있다.** 가르는 것은 P-59 게이트다: "
              f"`scripts/verify_bundle_hash.py --web <SPA>`")
    print(f"[SHOT] {len(got['entries'])}장 · 브라우저 오류 {len(got['page_errors'])}건")
    print(json.dumps(got["entries"], ensure_ascii=False, indent=2))
    if got.get("session_lost"):
        # ★ **판정 불가지 빨강이 아니다.** 세션을 빼앗긴 것은 환경의 사실이고
        #   화면의 결함이 아니다 — 빨강으로 적으면 다음 사람이 없는 결함을 쫓는다.
        #   ⚠ 그리고 이 실행의 증거는 **불완전하다**: 이 함수는 시작하면서 PNG 폴더를
        #     비우므로, 튕긴 실행은 앞선 온전한 벌을 **덮는다.** 다시 찍어야 한다.
        print(f"[SHOT] **판정 불가(exit 2)** — 세션을 빼앗겼다. 이번 벌은 "
              f"{len(got['entries'])}/{want_n}장에서 끊겼고, 이 실행이 앞선 벌을 "
              f"**덮었다.** 동시 접속 1개인 창을 확보한 뒤 **다시 찍는다**")
        return EXIT_UNDECIDABLE
    return EXIT_OK if len(got["entries"]) == want_n else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
