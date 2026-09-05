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

    python scripts/capture_screens.py --user gxprobe_e2e --password ****
    python scripts/capture_screens.py --dry-run     # 씨앗·정리 없이 도달만 본다

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
PROBE_TAG = "gxprobe-D384-screen"

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

#: 무엇을 찍나. `must_see` 는 **그 화면에만 있는 글자**다 — 로그인으로 튕겼는지
#: 빈 껍데기가 떴는지를 이것 하나로 가른다.
TARGETS = [
    {"step": 1, "route": "/dsm/dashboard", "must_see": "관제 대시보드"},
    {"step": 2, "route": "/dsm/events", "must_see": "이벤트 목록"},
    {"step": 3, "route": "/dsm/events/{event_id}", "must_see": "이벤트 상세"},
    # ── D-386 [실측 2026-09-13] 다섯 장을 더한다. 셋은 우리가 만든 화면이고
    #    이 다섯은 **인수받은 화면**이다 — 남의 화면을 여는 것이 값이 큰 이유는
    #    우리가 한 번도 열어 본 적 없는 배선이 거기 있기 때문이다.
    #    `must_see` 는 **실제로 띄워 보고** 그 화면에만 있는 글자로 골랐다(추측 아님).
    {"step": 4, "route": "/device", "must_see": "Add New Device"},
    {"step": 5, "route": "/roles", "must_see": "Add New Role"},
    {"step": 6, "route": "/menu", "must_see": "Menu Management"},
    {"step": 7, "route": "/configuration-management", "must_see": "Is Active?"},
    {"step": 8, "route": "/profile", "must_see": "Personal Information"},
    # ── D-396 [실측 2026-09-14] 여덟 장을 더해 **16/16** 을 채운다.
    #    고른 기준: 재난안전·감시 국면에 닿는 화면 우선 (§0.4 배송·주문·터미널은 뺐다).
    #    `must_see` 는 **후보 16개를 실제로 열어 본문을 읽고** 골랐다 — 추측이 아니다.
    #    (정찰 결과: 찍을 수 있는 것 13 · 찍을 수 없는 것 3. 셋은 아래 KNOWN_* 에 남긴다)
    {"step": 9, "route": "/surveillance-dashboard", "must_see": "Last Updated"},
    {"step": 10, "route": "/survey-profile", "must_see": "Add New Profile"},
    {"step": 11, "route": "/media-data", "must_see": "No preview available."},
    {"step": 12, "route": "/flight-log-analysis", "must_see": "Drone State Prediction"},
    {"step": 13, "route": "/multi-stream-monitor", "must_see": "Participants"},
    {"step": 14, "route": "/operation-settings", "must_see": "API URL"},
    {"step": 15, "route": "/report-template", "must_see": "Usage Count"},
    {"step": 16, "route": "/notam", "must_see": "SNOWTAM"},
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
    {"step": 17, "route": "/dsm/events?preset=unhandled",
     "slug": "dsm_events_preset_unhandled",
     "must_see": "미처리 — 아직 아무도 손대지 않은 것"},
    {"step": 18, "route": "/dsm/events?preset=recent",
     "slug": "dsm_events_preset_recent",
     "must_see": "지난 12시간 — 이 시간 창 안에 난 것"},
    {"step": 19, "route": "/dsm/events?preset=mine",
     "slug": "dsm_events_preset_mine",
     "must_see": "내 담당 — 내가 판정한 이벤트"},
    {"step": 20, "route": "/dsm/events?preset=system",
     "slug": "dsm_events_preset_system",
     "must_see": "시스템 — 설비 자신이 낸 신호"},
    #: W2 상세의 판정·대응 칸. 상세 화면 자체는 step 3 이 이미 찍는다 —
    #: 여기서 단언하는 것은 **누를 자리가 생겼다**는 사실이다(U1 #11).
    {"step": 21, "route": "/dsm/events/{event_id}",
     "slug": "dsm_events_id_verdict_panel",
     "must_see": "처리 단계 · 진위 판정"},
    # ── [2파 병합 · 2026-09-24] **세 장을 더해 21 → 24 장으로 간다.**
    #    차선 C 가 지은 화면 셋이고, 이 셋이 찍히기 전까지 UX-13·17·18 은
    #    「서버 면은 섰고 화면은 못 봤다」였다 — 그 상태에서 '구현'으로 적는 것이
    #    이 대장이 금지하는 부풀리기다(D-346 · P-9).
    #
    #    ⚠ `must_see` 는 각 페이지의 `HEADLINE` 상수 원문이다. 공통 글자로 단언하면
    #      **다른 화면이 떠도 초록**이 된다 — 프리셋 넷에서 배운 것과 같은 함정이다.
    {"step": 22, "route": "/dsm/queue",
     "slug": "dsm_queue_focus",
     "must_see": "지금 처리할 것 — 가장 급한 하나"},
    {"step": 23, "route": "/dsm/drill",
     "slug": "dsm_drill_mode",
     "must_see": "훈련 모드 — 켜면 알림이 사람에게 가지 않습니다"},
    {"step": 24, "route": "/dsm/cameras/import",
     "slug": "dsm_cameras_import_dryrun",
     "must_see": "카메라 일괄 등록 — 표를 먼저 봅니다"},
    # ── [2026-09-05 · 차선 C] **세 장을 더하고, 처음으로 휴대전화 크기로 찍는다.**
    #
    #    ★ 앞의 24 장은 전부 1440×900 이다. U3(이동 중 수신)는 **잰 적이 없었다** —
    #      데스크톱 폭에서 뜨는 모바일 화면은 사람이 실제로 보는 그 화면이 아니다.
    #      그래서 항목마다 `viewport` 를 둘 수 있게 했고, 없으면 데스크톱이다.
    #    ⚠ 페이지를 새로 만들지 않고 **같은 페이지의 크기만 바꾼다.** 새 페이지를
    #      만들면 로그인 세션이 따라오지 않아 전부 `/login` 으로 튕긴다.
    {"step": 25, "route": "/dsm/cameras/address",
     "slug": "dsm_cameras_address_fill",
     "must_see": "카메라 주소 채우기 — 한 대씩"},
    {"step": 26, "route": "/start?role=OPERATOR",
     "slug": "dsm_onboarding_start",
     "must_see": "처음 시작하기 — 첫 근무일에 혼자 시작하기"},
    #: M1 — 휴대전화의 첫 화면. `MobileInbox.HEADLINE` 원문이다.
    #: ⚠ [실측 2026-09-05 · 턴 E · 차선 Q] **`slug` 는 아무 이름이나가 아니다.**
    #:   `verify_screens.expected_prefix` 는 파일 이름이 **라우트 뿌리로 시작**할 것을
    #:   요구한다(`<scenario>/<role>/<route 뿌리>[_꼬리표].png`). 앞선 이름
    #:   `m1_mobile_inbox` 는 뿌리가 `m_inbox` 가 아니라 **빨강**이었다.
    #:   이 어긋남이 두 턴 동안 안 보인 이유: 촬영이 17번에서 죽어 **27·28번까지
    #:   가 본 적이 없었다.** 죽는 도구는 자기 뒤에 있는 결함을 함께 숨긴다.
    {"step": 27, "route": "/m/inbox", "viewport": MOBILE_VIEWPORT,
     "slug": "m_inbox_m1",
     "must_see": "내게 온 이벤트"},
    #: M3 — 현장 회신. `MobileEventDetail.FIELD_REPLY_HEADLINE` 원문이다.
    #: ⚠ 「현장 상세」로 단언하지 않는다 — 그것은 M2 의 글자이고, M3 가 없어도 뜬다.
    #: 뿌리는 `m_events_<id>` 이고, `route_stems` 가 숫자 자리를 `id` 로 눕힌 것도
    #: 받아 준다 — 씨앗 id 는 실행마다 바뀌므로 **눕힌 쪽**을 쓴다(step 21 과 같다).
    {"step": 28, "route": "/m/events/{event_id}", "viewport": MOBILE_VIEWPORT,
     "slug": "m_events_id_m3_field_reply",
     "must_see": "현장 회신 — 본 것을 한 줄로"},
]

#: ★ [실측 2026-09-13 · D-386] 열어 보고 **찍지 못한 화면**. 목록에 남긴다 —
#:   못 찍은 것을 목록에서 지우면 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아진다.
#:   `/users` 는 API 6건이 전부 200 인 채로 **본문 글자 수가 0** 이었다(빈 화면).
#:   결함으로 등재했다: DA-05/blockers.yaml :: RJCORE_BLANK_ON_NO_PERMISSION
KNOWN_BLANK = [
    {"route": "/users", "why": "본문 0자 · API 6건 200 · JS 오류 0건 — 권한 없는 화면이 "
                               "안내 대신 빈 화면을 낸다 (DA-03 §3-4 위반 · rj-core §0.4)"},
    # ★ [실측 2026-09-14 · D-396] **두 번째 빈 화면.** `/users` 와 같은 모양이다 —
    #   API 실패 0건 · JS 오류 0건인 채로 본문만 0자다. 한 건이면 그 화면의 사정이지만
    #   **둘이면 성질**이다. RJCORE_BLANK_ON_NO_PERMISSION 에 표본을 더했다.
    {"route": "/handover", "why": "본문 0자 · API 실패 0건 · JS 오류 0건 — /users 와 같은 모양"},
]

#: ★ [실측 2026-09-14 · D-396] 열었더니 **다른 화면이 떴다.** 빈 화면과는 다른 결함이다 —
#:   빈 화면은 「왔는데 아무것도 없다」이고, 이것은 **「거기 갈 수 없다」**이다.
#:   둘을 한 칸에 두면 고치는 사람이 어디를 볼지 모른다 (D-377 ㉠㉡㉢ 를 가른 것과 같은 이유).
#:   ⚠ 이 계정의 `role` 은 `NO_ROLE` 이다 — 역할이 있는 계정에서는 다를 수 있고,
#:     그것은 **아직 재 보지 않았다.** 「권한 때문」이라고 적지 않는다 (D-322).
KNOWN_REDIRECT = [
    {"route": "/monitoring-dashboard", "landed": "/profile",
     "why": "요청한 경로가 아니라 이 계정의 홈 화면이 떴다 — 라우트에 도달하지 못한다"},
    {"route": "/intergrated-dashboard", "landed": "/profile",
     "why": "같음. 둘 다 App.tsx 의 별도 라우트 묶음(189~211줄)에 있다"},
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


def seed_events(username: str, n: int = 2) -> int:
    """★ 씨앗은 **그 계정이 실제로 볼 수 있는 자리**에 심는다.

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
        )
        first = first or result.event_id
    _ = DE  # 위 주석의 대상이었던 이름 — 지우지 않고 남긴다
    return first


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


def read_role(username: str) -> str:
    """찍은 사람의 역할을 **제품이 들고 있는 값**에서 읽는다 (D-323).

    ★ 1차판은 `role = "OPERATOR"` 로 박혀 있었다. 바로 위 주석이 「우리가 정해서 적지
      않는다」라고 말하면서 정해서 적고 있었다 — 그리고 그 진술은 **틀렸다**:
      이 계정의 `role` 은 [실측] **None** 이다. 그래서 `/users` 가 빈 화면으로 떴다.
      인덱스에 OPERATOR 라 적혔으면 그 사실이 통째로 가려졌을 것이다.
    """
    apps = _django()
    from django.contrib.auth import get_user_model
    u = get_user_model()._base_manager.filter(username=username).first()
    role = getattr(getattr(u, "role", None), "code", None) or getattr(u, "role", None)
    _ = apps
    return str(role) if role else "NO_ROLE"


def capture(*, web: str, user: str, password: str, event_id: int, role: str,
            api: str) -> dict:
    from playwright.sync_api import sync_playwright

    # ★ 이번 실행이 남길 자리를 **먼저 비운다.** 이벤트 상세의 경로에는 그때그때의
    #   id 가 들어가므로, 비우지 않으면 지난 실행의 PNG 가 남아 인덱스와 어긋난다 —
    #   `verify_screens.py` 는 인덱스에 없는 PNG 를 「어디서 온 화면인지 말하지
    #   않는다」로 실패시킨다. 그 실패는 옳고, **비우는 것이 이쪽의 몫**이다.
    import shutil
    shutil.rmtree(SCREENS / SCENARIO, ignore_errors=True)
    SCREENS.mkdir(parents=True, exist_ok=True)
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

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport=DESKTOP_VIEWPORT)
        page.on("pageerror", lambda e: page_errors.append(str(e)[:200]))
        page.on("response", lambda r: seen_calls.append(
            (r.request.method, r.url, r.status)))
        try:
            page.goto(f"{web}/login", wait_until="networkidle", timeout=60_000)
            page.wait_for_timeout(1_500)
            fields = page.locator("input")
            if fields.count() < 2:
                raise RuntimeError("로그인 화면에 입력칸이 둘 미만이다 — 화면이 안 떴다")
            fields.nth(0).fill(user)
            fields.nth(1).fill(password)
            page.get_by_role("button", name="Log In").click()
            page.wait_for_timeout(9_000)
            if page.url.rstrip("/").endswith("/login"):
                raise RuntimeError(
                    f"로그인 뒤에도 로그인 화면이다 ({page.url}) — "
                    f"본문: {page.inner_text('body')[:160]!r}")


            for t in TARGETS:
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
                if t["must_see"] not in body:
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
                api_calls[route] = sorted(set(api_calls.get(route, ())) | {
                    (m, u[len(api):], st)
                    for m, u, st in seen_calls
                    if u.startswith(api + "/api/")})
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
                        "must_see": t["must_see"],
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
                })
                print(f"[SHOT] {rel} — 「{t['must_see']}」 확인 후 캡처")
        finally:
            browser.close()

    return {"entries": entries, "steps": steps, "page_errors": page_errors,
            "api_calls": api_calls, "misses": misses,
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
  #   ⚠ [실측 2026-09-13 · D-386] 역할은 **`NO_ROLE`** 이다. 이 계정은 제품의 `role` 이
  #     **비어 있다** — 1차판이 `OPERATOR` 라 적어 두었던 자리이고, 그것은 진술이지
  #     실측이 아니었다(D-323). 지금은 제품이 들고 있는 값을 읽어 적는다.
  #     그리고 그 사실이 화면 하나를 설명한다: `/users` 는 **본문 0자**로 떴다.
  #     빈 화면은 찍지 않았고 결함으로 등재했다(RJCORE_BLANK_ON_NO_PERMISSION).
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
        "    data_source: 시드",
        "",
    ))
    body = "".join(row.format(**e) for e in entries)
    index.write_text(head + _INDEX_HEAD + body, encoding="utf-8")
    print(f"[SHOT] 인덱스 갱신 — {index.name} 에 {len(entries)}장")


def main() -> int:
    ap = argparse.ArgumentParser(description="화면 캡처 실행체 (D-347 · D-384 ②)")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--web", default="http://localhost:3002")
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="씨앗·캡처 없이 두 자리에 닿는지만 본다")
    args = ap.parse_args()

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
    print(f"[SHOT] [입력] API {args.api} · 화면 {args.web} · 대상 {len(TARGETS)}장")
    if args.dry_run:
        print("[SHOT] --dry-run — 두 자리 다 서 있다")
        return EXIT_OK

    _release_session(args.user)
    role = read_role(args.user)
    print(f"[SHOT] 찍는 사람의 역할 = {role} (제품이 들고 있는 값 · D-323)")
    event_id = seed_events(args.user)
    try:
        got = capture(web=args.web, user=args.user, password=args.password,
                      event_id=event_id, role=role, api=args.api)
    finally:
        print(f"[SHOT] 씨앗 정리: {clean_events()}")

    (SCREENS / "run_log.json").write_text(json.dumps({
        "harness": "scripts/capture_screens.py",
        "scenario": SCENARIO,
        "ran_at": datetime.now().replace(microsecond=0).isoformat(),
        "steps": got["steps"],
        #: 브라우저가 뱉은 오류를 **숨기지 않는다.** 0건이면 0건이라고 적힌다.
        "page_errors": got["page_errors"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    routes_out = ROOT / "docs" / "agent" / "evidence" / "D-386" / "screen_routes.json"
    if not routes_out.parent.parent.is_dir():          # 컨테이너에서는 /docs 가 따로다
        routes_out = Path("/docs") / "agent" / "evidence" / "D-386" / "screen_routes.json"
    routes_out.parent.mkdir(parents=True, exist_ok=True)
    routes_out.write_text(json.dumps({
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
        "data_source": "시드 (K1 record_detection 실제 경로 · 실제 사고 아님)",
        "blank_screens": KNOWN_BLANK,
        #: 못 찍은 것을 **왜 못 찍었는지로 갈라** 적는다 (D-396). 한 칸에 두면
        #: 「안 해 본 것」과 「해 봤더니 안 되는 것」이 같아지고, 둘을 합치면
        #: 「아무것도 없다」와 「거기 갈 수 없다」도 같아진다.
        "redirected_screens": KNOWN_REDIRECT,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
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
              f"{len(got['entries'])}/{len(TARGETS)}장에서 끊겼고, 이 실행이 앞선 벌을 "
              f"**덮었다.** 동시 접속 1개인 창을 확보한 뒤 **다시 찍는다**")
        return EXIT_UNDECIDABLE
    return EXIT_OK if len(got["entries"]) == len(TARGETS) else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
