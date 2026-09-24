#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-20 — **화면이 우리 대장의 말로 말하는가.** 제품 언어 판정기 (P-29).

무엇이 이 판정기를 만들었나
---------------------------
화면 24장을 한 장씩 읽었더니 결함 31건이 나왔고 **11장의 뿌리가 하나**였다:

    「UX-17 훈련 모드」  「표시 7건(요청 상한 50건)」  「패널 상태 data 0/0 loading 0/0」
    「`response_state=occurred` 로 걸러 준 목록입니다」  「data_source = live」
    「종결(으)로」  「Network Error」

D-번호 · 절 ID · 백틱 · 마크다운 원문 · 영문 열거값 · 개발 계수기가 **사용자 본문**에 있었다.
뿌리는 「사유를 화면에 적어라」였다 — 시킨 쪽의 잘못이고, 정정은 사전과 이 판정기다.
사전은 `docs/design/GX-COPY_v1.md` 이고, 이 파일은 그 사전을 **강제하는 쪽**이다.

★ 래칫이다 (D-311). 오늘의 빚을 **이름으로** 잠그고 **새로 생기는 것만** 막는다.
  왜 처음부터 exit 1 이 아닌가: 오늘 31건이 걸린 채로 병합을 막으면 사람이 게이트를 끈다.
  꺼진 게이트는 없는 게이트보다 나쁘다. 그래서 **오늘 수를 적어 두고**, 그 수가 줄지 않으면
  줄지 않았다고 말하고, **새 것이 하나라도 생기면 exit 1** 이다.

    python scripts/verify_ui_copy.py            # 판정 (새 위반만 막는다 · 잔여 N 을 말한다)
    python scripts/verify_ui_copy.py --list     # 걸린 자리 전수
    python scripts/verify_ui_copy.py --strict   # 래칫 없이 — 잔여가 0 이어야 통과
    python scripts/verify_ui_copy.py --freeze   # 오늘의 빚을 기준선에 잠근다
    python scripts/verify_ui_copy.py --self-test

주석은 세지 않는다 — 금지된 것은 「사용자 본문」이지 「소스」가 아니다.
주석을 걷어 내는 일은 `verify_ui_secrets.strip_comments` 가 한다. **두 벌을 두지 않는다**
(D-369) — 두 벌은 반드시 어긋나고, 어긋나면 한쪽이 조용히 아무것도 안 본다.

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_ui_secrets import frontend_files, strip_comments  # noqa: E402

BASELINE = ROOT / "docs" / "agent" / "evidence" / "UX-20" / "copy_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 대장 언어 — 사전 §4 「사용자 본문에 쓰지 않는 것」이 이름으로 적은 것들
# ═══════════════════════════════════════════════════════════════════════════
PATTERNS: tuple[tuple[str, str], ...] = (
    #: 결정 번호. 뒤에 숫자가 더 붙으면 장비 일련번호다 — 그것은 우리 대장이 아니다.
    ("결정 번호", r"D-\d{3}(?!\d)"),
    #: 절 ID. 화면 제목이 「UX-17 훈련 모드」였다 — 절 이름은 제목이 아니다.
    #: ★★ [실측 2026-09-21 · 턴 Z · 차선 Q] **숫자를 1~2자리만 보고 있었다.**
    #:   그래서 `P-184` 같은 **세 자리 절 ID 를 한 번도 못 잡았다.** 턴 Y 에 U24 가
    #:   「스냅샷 P-184」를 화면 본문에 안 적은 것은 **사전이 막은 것이지 이 게이트가
    #:   막은 것이 아니다** — 게이트는 그 글자를 볼 눈이 없었다. 「안 잡혔다」를
    #:   「없다」로 읽던 자리이고, 그것이 이 저장소가 거듭 만난 실패 모양이다(D-301).
    #:   ⚠ 네 자리로는 안 넓힌다. 뒤의 경계(\b)가 장비 일련번호를 가른다 —
    #:     `P-184` 는 잡고 `P-1840` 은 안 잡는다(자릿수를 줄여도 경계가 안 선다).
    ("절 ID", r"\b(?:UX|SEC|OPS|QA|LAW|PERF|ISO|F|P|W|AC|FR|NFR|DA)-\d{1,3}\b"),
    #: 백틱과 마크다운 강조. **렌더되지 않고 그대로 보인다** — 화면에 별 두 개가 뜬다.
    ("백틱", r"`"),
    ("마크다운 강조", r"\*\*"),
    #: 영문 열거값이 그대로 뜨는 자리.
    ("출처 칩", r"data_source\s*="),
    ("영문 열거값", r"\b(?:occurred|acknowledged|in_progress|confirmed|rejected|"
                    r"response_state|event_type|severity)\b\s*[=:]"),
    #: 내부 경로 · 도구 이름. 「어디에 없는지」는 사용자에게 뜻이 없다.
    ("내부 경로", r"(?:scripts/|backend/|kernels\.|frontend/src)"),
)
COMPILED = tuple((name, re.compile(rx)) for name, rx in PATTERNS)

#: ★ **출생 표본** (D-310) — 그날 화면에 실제로 떠 있던 제목과 문단이다.
BIRTH_SAMPLES = (
    "UX-17 훈련 모드 — 이 화면은 **로그 어댑터로만** 보냅니다",
    "`response_state=occurred` 로 걸러 준 목록입니다",
    "data_source = live",
    #: ★ [턴 Z · Q] **세 자리 절 ID** — 이 표본이 없어서 1~2자리 그물이 오래 살았다.
    #:   양성 대조에 표본이 없으면 그물의 구멍은 영원히 안 보인다 (D-277 · D-289).
    "스냅샷 P-184 는 아직 안 올라왔습니다",
)

#: ★ **출생 표본 ②** (P-77 · 2026-09-06) — 앞선 정규식 파서가 **통째로 못 보던** 두 자리.
#:   둘 다 JSX 본문에 `{…}` 보간이 끼어 있고, 그래서 `>…<` 정규식이 배제했다.
#:   화면에는 떠 있었고 게이트는 「잔여 0 · 통과」를 냈다.
BIRTH_JSX: tuple[tuple[str, str], ...] = (
    ("<Tag>data_source = {current.data_source}</Tag>", "출처 칩"),
    ("""<Paragraph>같은 카메라·같은 유형이{' '}
     {Math.round(w / 60)}분 창 안에 연속으로 나면
     카드 한 장에 묶입니다. F-14 통계는 왼쪽 수를 봅니다.</Paragraph>""", "절 ID"),
)

# ═══════════════════════════════════════════════════════════════════════════
# P-221 · 턴 AA — **표시명 사전 · 빈 화면 · 오류 본문** (2026-09-21 · 차선 Q)
#
# 이 턴의 불변: **정직한 회색을 고객 말로.**
#   「서버가 404」는 정직하지만 고객 말이 아니다. 「못 골라 줍니다」는 우리 사정이다.
#   그리고 **실제 값이 없는 문구는 비표시**여야 한다 — 「장애 신고 창구 미등록」은
#   **우리 회색을 고객 발치에 적어 둔 것**이다(세종 관찰). 창구 번호가 오면 그때 뜬다.
#
# ★ 왜 「한글이 섞인 조각에서만」 보는가 — **이 그물의 눈금**
#   `fire_user` · `log` · `typed` 는 코드에서는 정당한 낱말이다. 문자열 리터럴에
#   그대로 있는 것을 전부 잡으면 첫 수가 수백이 되고, 수백은 아무도 안 고친다.
#   **고객이 읽는 자리**는 한국어 문장이다. 그래서 이 세 무리는 **조각에 한글이
#   있을 때만** 본다 — 「규칙은 … 역할을 가리킵니다 (예: fire_user · operator)」
#   같은 자리가 정확히 그 모양이고, 그것이 이 절의 출생 표본이다.
#   ⚠ 놓치는 쪽으로 틀린다: 순영문 라벨은 이 그물을 지나간다. 그 자리는 UX-21 이다.
#
# ★ 사전은 **남이 만든다** — U56 이 역할 표시명을, U24 가 채널 이름을 만들고 있다.
#   여기 있는 것은 **금지 목록**(내부 코드의 이름)이지 표시명 사전이 아니다.
#   표시명이 서면 `aa_display_dicts()` 가 그것을 찾아 **덮는다** — 두 벌을 두지 않는다
#   (D-369). 아직 없으면 **있는 것만** 쓰고 없는 것은 소리 내어 적는다.
# ═══════════════════════════════════════════════════════════════════════════

#: 표시명 사전이 설 자리. **U56·U24 의 것**이고 이 파일의 것이 아니다.
#: ★ [실측 2026-09-21 · 턴 AA] U56 의 역할 사전은 **이미 섰다** —
#:   `roleNames.ts::ROLE_DISPLAY_NAMES`. 새로 만들지 않고 **그것을 가리킨다.**
#:   U24 의 채널 이름은 **아직 없다**(`frontend/src` 전수에 `CHANNEL_LABEL` 0건).
#:   ⚠ 없는 것을 「0건」으로 읽지 않는다 — 판정문이 그 이름을 소리 내어 적는다.
DISPLAY_DICTS = (
    ("역할 표시명 (U56)", "frontend/src/features/dsm/roleNames.ts",
     r"ROLE_DISPLAY_NAMES"),
    ("채널 이름 (U24)", "frontend/src/features/dsm/copy.ts", r"CHANNEL_LABEL"),
    ("상태 표시명", "frontend/src/features/dsm/copy.ts", r"LINK_STATUS_LABEL"),
)


def aa_display_dicts():
    """표시명 사전이 **섰는가**. 선 것만 쓰고, 안 선 것은 이름으로 적는다.

    ★ 「없다」를 「0건」으로 읽지 않는다(D-301). 사전이 없으면 이 게이트는 금지
      목록만으로 도는 것이고, 그 사실이 판정문에 실려야 한다 — 안 실리면
      다음 턴에 누가 「표시명 게이트가 초록이니 사전이 있다」고 읽는다.
    """
    have, missing = [], []
    for name, rel, sym in DISPLAY_DICTS:
        p = ROOT / rel
        if p.is_file() and re.search(sym, p.read_text(encoding="utf-8", errors="replace")):
            have.append("%s(`%s`)" % (name, sym))
        else:
            missing.append("%s ← `%s` 에 `%s` 가 아직 없다" % (name, rel, sym))
    return have, missing


#: ── ① 역할 코드. `backend` 의 실제 값과 `roleNav.ts` 가 쓰는 이름들 ──────────
#:    ★ `admin` · `operator` 는 영어 낱말이기도 하다. 그래서 **한글 조각 안에서만**
#:      본다 — 아래 `HANGUL_ONLY` 무리에 들어간다.
AA_ROLE_CODES = ("fire_user", "fire_admin", "surveillance_operation",
                 "surveillance_manage", "view_only", "superuser", "dsm_admin")

#: ── ② 채널 코드. `ALLOWED_PREF_CHANNELS` 와 발사 어댑터 이름 ────────────────
AA_CHANNEL_CODES = ("webpush", "email", "sms", "log", "typed", "webhook", "stdout")

#: ── ③ 상태 코드. 기존 「영문 열거값」은 뒤에 `=`·`:` 가 붙은 자리만 봤다 —
#:    맨몸으로 선 자리(「지금 occurred 입니다」)는 한 번도 안 잡혔다.
AA_STATUS_CODES = ("occurred", "acknowledged", "in_progress", "confirmed",
                   "rejected", "resolved", "pending", "live", "drill", "seed")

#: **한글이 섞인 조각에서만** 보는 무리. 위의 눈금 설명을 참조.
HANGUL_ONLY_PATTERNS = (
    ("역할 코드", r"\b(?:%s)\b" % "|".join(AA_ROLE_CODES + ("admin", "operator"))),
    ("채널 코드", r"\b(?:%s)\b" % "|".join(AA_CHANNEL_CODES)),
    ("상태 코드", r"\b(?:%s)\b" % "|".join(AA_STATUS_CODES)),
    #: ── ④ 오류 본문 — 우리 사정을 고객 발치에 적어 둔 자리 ───────────────
    #:   ★ HTTP 상태 숫자. 「서버가 404」는 정직하지만 고객 말이 아니다.
    ("상태 코드 숫자", r"(?:\b(?:40[0-9]|41[0-9]|42[0-9]|50[0-4])\b\s*(?:오류|에러|입니다|"
                      r"응답|코드)|(?:서버가|응답이|상태)\s*\**(?:40[0-9]|50[0-4]))"),
    #: ★ 우리 사정을 고객에게 사과로 내미는 말. 원인도 다음 손도 없다.
    ("우리 사정", r"(?:못 골라 줍니다|골라 주지 못합니다|판별하지 못합니다|"
                 r"지원하지 않는 경로|알 수 없는 오류|처리 중 오류가 발생)"),
    #: ★★ **실제 값이 없는 문구는 비표시다.** 「미등록」·「미지정」·「준비 중」을
    #:   고객 화면에 적는 것은 **우리 회색을 고객 발치에 적어 둔 것**이다(세종 관찰).
    #:   값(창구 번호·주소)이 오면 그때 뜬다. 오기 전에는 그 줄이 **없어야** 한다.
    ("빈 값 표시", r"(?:미등록|미지정|미설정|등록되지 않았습니다|준비 중입니다|"
                  r"확인되지 않았습니다)"),
    #: ★ 영문 오류 원문이 그대로 나가는 자리 (그날 화면의 `Network Error`).
    #:   ⚠ [실측 2026-09-21 · 턴 AA] 처음에 `undefined` · `NaN` 을 넣었더니 **179건**이
    #:     나왔고 그중 대부분이 `push.ts` 의 코드였다 — 이 무리는 한글 없이도 보는
    #:     예외라서 **코드를 화면으로 읽었다.** 수백 건은 아무도 안 고친다. 그래서
    #:     **화면에 그 글자 그대로 뜬 것만** 남긴다. 놓치는 쪽으로 틀린다.
    ("영문 오류 원문", r"(?:Network Error|Request failed|Internal Server Error|"
                     r"Unexpected token in JSON)"),
)
HANGUL_ONLY_COMPILED = tuple((n, re.compile(rx)) for n, rx in HANGUL_ONLY_PATTERNS)

# ── ⑤ 빈 화면 — **0건이면 한 줄 + 다음 손** ───────────────────────────────
#   「조치를 마쳤다고 알려 온 사건이 없습니다」가 화면 절반을 차지하면 안 된다.
#   길이는 이 게이트가 못 잰다(그것은 화면의 일이다). 이 게이트가 잴 수 있는 것은
#   **다음 손이 같은 문장에 있는가** 하나다 — 없으면 고객은 막다른 곳에 선다.
#
# ⚠ **이 그물은 두 번 좁혔다** [실측 2026-09-21 · 턴 AA]. 첫 판은 179건을 냈고
#   그중 대부분이 빈 화면이 아니었다:
#     · 「승인 필요 **없음**」 「알 수 **없음**」 — 그냥 **라벨**이다. 그래서 `없음` 을 뺐다.
#     · 「둘 다 비우면 차단 없음입니다. 한쪽만 채울 수는 **없습니다** — 언제부터
#       언제까지 안 받는지 정해지지 않기 때문입니다.」 — **설명 문단**이다.
#   빈 화면 문구는 **짧다**. 그것이 이 둘을 가르는 유일한 기계적 술어다.
#   그래서 조각이 `EMPTY_MAX_LEN` 자를 넘으면 빈 화면으로 보지 않는다.
#   ★ 놓치는 쪽으로 틀린다 — 긴 빈 화면 문구는 이 그물을 지나간다. 그러나 수백 건을
#     내는 그물은 아무도 안 고치고, 안 고치는 게이트는 꺼진 게이트와 같다.
EMPTY_PHRASE = re.compile(r"(?:없습니다|비어 있습니다|0건|한 건도 없)")

#: 빈 화면 한 줄의 길이 바닥. 이보다 길면 **설명 문단**이지 빈 화면이 아니다.
EMPTY_MAX_LEN = 40

#: 「다음 손」의 표지 — 무엇을 하면 되는지가 **같은 조각 안에** 있는가.
#:   ⚠ 넓게 잡는다. 좁게 잡으면 멀쩡한 빈 화면이 전부 빨개지고, 그러면 사람이
#:     게이트를 끈다. 꺼진 게이트는 없는 게이트보다 나쁘다.
NEXT_HAND = re.compile(
    r"(?:하십시오|하세요|해 보십시오|누르|눌러|등록|추가|만들|설정|선택|바꾸|"
    r"넓|다시 시도|기다리|문의|새로 고침|초기화|지우|풀어|보십시오|보세요)")

#: ★ **출생 표본** (D-310) — 그날 화면에 실제로 떠 있던 말들이다.
#:   자기시험이 이 넷을 **직접** 시험한다. 여기서 초록이 나오면 이 절은 도구가 아니다.
AA_BIRTH = (
    ("규칙은 사람이 아니라 역할을 가리킵니다 (예: fire_user · operator).", "역할 코드"),
    ("보내는 채널이 log 로 잡혀 있습니다", "채널 코드"),
    ("지금 상태는 occurred 입니다", "상태 코드"),
    ("서버가 404 를 냈습니다", "상태 코드 숫자"),
    ("나에게 온 것만 못 골라 줍니다", "우리 사정"),
    ("장애 신고 창구 미등록", "빈 값 표시"),
    #: ★ 한글 문장 **안에** 섞여 나온 영문 원문만 본다 — 막으려고 적어 둔 목록은
    #:   그 자리에서 한글이 없고, 그래서 이 그물을 지나간다(위 `scan_line_aa` 참조).
    ("알림을 보내지 못했습니다 (Network Error)", "영문 오류 원문"),
)

#: ★ 빈 화면의 출생 표본 — 「한 줄 + 다음 손」이 아닌 것과 맞는 것.
AA_EMPTY_BIRTH = (
    ("조치를 마쳤다고 알려 온 사건이 없습니다", True),   # 다음 손이 없다 → 잡힌다
    ("아직 없습니다. 카메라를 먼저 등록하십시오", False),  # 다음 손이 있다 → 안 잡힌다
    ("0건입니다 — 기간을 넓혀 보십시오", False),
)


def scan_line_aa(text: str) -> list:
    """한 조각에서 걸린 **P-221 패턴 이름들**. 한글이 없으면 보지 않는다.

    ★ 왜 한글이 없으면 안 보는가는 이 절 머리의 「눈금」에 적었다. 요약하면:
      고객이 읽는 자리를 재는 것이고, 코드를 재는 것이 아니다.
    """
    #: ⚠⚠ [실측 2026-09-21 · 턴 AA] 처음에는 **영문 오류 원문만 한글 없이도** 보게
    #:   예외를 뒀다. 그랬더니 잡힌 것이 `copy.ts` 의 `RAW_MARKERS` 였다 —
    #:   `'Network Error'` · `'Internal Server Error'` 가 거기 있는 이유는 화면에
    #:   내보내려는 것이 아니라 **그 문장을 버리려고** 적어 둔 것이다.
    #:   ★ **이 게이트가 방어선을 결함으로 읽었다.** 예외를 지운다 — 이 무리도
    #:     한글 조각 안에서만 본다. 「알림을 못 보냈습니다 (Network Error)」는 잡고,
    #:     막으려고 적어 둔 목록은 안 잡는다. 놓치는 쪽으로 틀린다.
    if not HANGUL.search(text):
        return []
    return [name for name, rx in HANGUL_ONLY_COMPILED if rx.search(text)]


#: ★★ [실측 2026-09-21 · 턴 AB] **그물을 세 번째로 좁혔다 — 또 방어선을 결함으로 읽었다.**
#:   U24 가 `EventList.tsx` 에 빈 화면을 **옳게** 적었는데 이 게이트가 다섯 건을
#:   「다음 손 없음」으로 찍었다. 소스를 열어 보면:
#:       emptyText: '이 기관에 기록된 사건이 0건입니다.',
#:       emptyNext: '카메라가 무엇인가를 감지하면 이 자리에 첫 줄이 생깁니다.',
#:   **다음 손은 있다 — 같은 문장이 아니라 이웃 칸에 있었을 뿐이다.**
#:   턴 AA 의 술어는 「**같은 조각 안에** 있는가」였고, 그 「같은 조각」이 너무 좁았다.
#:   ★ 고친 방향: 조각 **바로 뒤**에 「다음 손 칸」이 서 있으면 다음 손이 있는 것으로 본다.
#:     칸 이름을 **못박아** 둔다 — 아무 이웃이나 봐주면 그물이 무뎌진다.
#:   ⚠ 이것은 면제가 아니다. 칸이 **비어 있으면**(한글 0) 여전히 잡힌다.
NEXT_HAND_FIELD = re.compile(
    #: ★ 맨 뒤의 `next` 는 **넓다** [실측 2026-09-21 · 턴 AB]. `EventList.tsx:705`
    #:   가 빈 화면 쌍을 `{ text: … , next: … }` 로 적었고, 칸 이름이 `emptyNext`
    #:   가 아니라 **`next`** 였다. 앞에 `{`·`,`·공백을 요구해 「줄머리 칸 이름」
    #:   일 때만 본다 — 그래도 넓다. **놓치는 쪽으로 틀린다**(이 게이트의 stance).
    #: ★★ [턴 AH · P-292 · 대표 결정] **콜론만 보다가 등호를 놓쳤다.**
    #:   객체 리터럴은 `emptyNext: '…'` 이지만 **JSX 는 `emptyNext="…"`** 다.
    #:   그래서 다음 손을 **이미 옳게 적어 둔 세 자리**(Reports · SettingsRules ·
    #:   SystemSettings)가 「다음 손 없음」으로 찍혔다 [실측 2026-09-24 · 3건].
    #:   판정식은 한 글자도 안 바뀐다 — **보지 못하던 모양 하나를 더 볼 뿐**이다.
    r"(?:^|[,{\s])(?:emptyNext|emptyAction|emptyHint|nextHand|nextStep"
    r"|actionLabel|cta|next)\s*[:=]",
    re.I)

#: ★★ [실측 2026-09-21 · 턴 AB] **같은 날 두 번째 방어선 오독.**
#:   `roleNames.ts` 의 `ROLE_NAMES_BLANK_BY_DECISION` 을 「절 ID 가 고객 본문에
#:   있다」로 찍었다. 그 표의 값은 이렇다:
#:       order: '인수 자산(배송 주문) — 이 제품의 역할이 아니다 (§4-2 · P-229)'
#:   그리고 바로 위 주석에 **「화면은 이 표를 읽지 않는다」**고 적혀 있다 —
#:   **「깜빡했다」와 「안 붙이기로 했다」를 가르려고 U56 이 일부러 세운 선언**이다.
#:   ★ 이 게이트는 **주석을 걷어 내고** 보기 때문에 그 선언을 볼 수 없었다.
#:     그래서 선언을 **이름으로** 받는다 — 이름은 주석이 아니라 코드다.
#:   ⚠ **면제가 아니다.** 건너뛴 조각 수를 판정문이 **소리 내어 센다** —
#:     안 세면 다음 사람이 「이 게이트가 전수를 봤다」고 읽는다.
DECLARED_NOT_ON_SCREEN = re.compile(
    r"export\s+const\s+([A-Z][A-Z0-9_]*_BY_DECISION|NAV_NO_SCREEN_YET)\b")


def declared_spans(body: str) -> list:
    """「화면이 읽지 않는다」고 **이름으로 선언한** 표의 자리 `[(시작, 끝)]`.

    끝은 **중괄호 짝**으로 찾는다 — 줄 수로 자르면 표가 길어지는 날 조용히 샌다.
    """
    out = []
    for m in DECLARED_NOT_ON_SCREEN.finditer(body):
        i = body.find("{", m.end())
        if i < 0:
            continue
        depth, j = 0, i
        while j < len(body):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((i, j))
    return out


def skipped_by_declaration(body: str, frag) -> bool:
    """그 조각이 **선언된 비표시 표 안**에 있는가."""
    return any(a <= frag.start <= b for a, b in declared_spans(body))


#: 이웃을 얼마나 보나. 객체 리터럴 한 칸 건너까지다 — 넓히면 옆 항목의 다음 손이
#: 이 항목을 덮는다.
NEIGHBOUR_CHARS = 260


#: 「다음 손 칸」이 **채워졌다**고 볼 한글 길이의 바닥. `emptyNext: ''` 는 지나가지 못한다.
NEXT_HAND_FIELD_MIN_HANGUL = 6


def has_next_hand_nearby(near: str) -> bool:
    """조각 **바로 뒤**에 「다음 손 칸」이 서 있고 **그 칸이 채워졌는가**.

    ⚠⚠ [실측 2026-09-21 · 턴 AB] 처음에는 이웃 칸에도 `NEXT_HAND` 어휘
      (「하십시오」·「누르」·「등록」…)를 요구했다. 그랬더니 U24 의 **옳은** 문구가
      여전히 걸렸다:
          emptyNext: '카메라가 무엇인가를 감지하면 이 자리에 첫 줄이 생깁니다.'
      명령문이 아니라 **무슨 일이 일어나면 이 자리가 찬다**는 설명이다. 그것도
      다음 손이다 — 고객은 막다른 곳에 서지 않는다. **어휘 목록으로 「다음 손인가」를
      가르려 한 것이 좁았다.**
    ★ 그래서 이웃 칸에서는 **어휘를 묻지 않는다.** 칸 이름을 못박아 두었으므로
      「다음 손을 적는 자리」라는 것은 **칸 이름이 이미 말한다** — 이 술어가 잴 것은
      **그 칸이 비었는가**뿐이다. (같은 조각 안에서는 칸 이름이 없으므로 어휘를
      그대로 쓴다.)
    """
    m = NEXT_HAND_FIELD.search(near or "")
    if not m:
        return False
    tail = near[m.end():m.end() + NEIGHBOUR_CHARS]
    return len(HANGUL.findall(tail)) >= NEXT_HAND_FIELD_MIN_HANGUL


def scan_empty_aa(text: str, near: str = "") -> list:
    """빈 화면 조각인데 **다음 손이 없으면** 이름을 낸다.

    긴 조각은 보지 않는다 — 위 `EMPTY_MAX_LEN` 의 주석에 그 사유를 적었다.
    `near` 는 그 조각 **바로 뒤의 소스**다 — 다음 손이 이웃 칸에 설 수 있다.
    """
    flat = " ".join(text.split())
    if not HANGUL.search(flat) or len(flat) > EMPTY_MAX_LEN:
        return []
    if not EMPTY_PHRASE.search(flat):
        return []
    if NEXT_HAND.search(flat) or has_next_hand_nearby(near):
        return []
    return ["빈 화면 · 다음 손 없음"]


#: 본 비율의 바닥. **이보다 낮으면 판정하지 않는다**(회색 · exit 2) —
#: 커버리지를 모르는 게이트는 판정한 것이 아니다.
COVERAGE_FLOOR = 0.90

#: 사용자 본문이 사는 곳. 여기 밖(설정·라우터·서비스)의 문자열은 화면에 뜨지 않는다.
#: ⚠ 좁게 잡는다 — 넓게 잡으면 첫 수가 수백이 되고, 수백은 아무도 안 고친다.
#: ★ [P-78 · 2026-09-06 턴 H] **로그인 화면을 범위에 넣었다.**
#:   직전 턴 실측에서 그 화면의 빈 값 문구가 영문(`This field is required.`)이었고,
#:   다섯 갈래는 아무 말도 안 했다. 그 자리를 우리 층으로 가져오면서 **판정기의 눈도
#:   함께 옮긴다** — 안 보는 자리에 새 문구를 쌓으면 사전이 그 화면을 못 따라간다.
#:   ⚠ 범위를 넓히면 잔여가 늘 수 있다. 늘면 늘었다고 적는다(래칫이 그 일을 한다).
SCOPE = ("frontend/src/features/dsm/", "frontend/src/features/mobile/",
         "frontend/src/features/login/", "frontend/src/features/LoginMobile/")


def in_scope(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel.startswith(prefix) for prefix in SCOPE)


#: 한글이 한 자라도 있는가. **이것이 「사용자 본문」의 술어다.**
#:
#:   왜 이 술어인가 [실측 2026-09-26]: 처음에는 줄 전체를 보았고 127건이 나왔는데
#:   그중 대부분이 코드였다 — `` `/m/events/${id}` `` 같은 템플릿 경로, `event.severity`
#:   같은 식별자. 그 수를 그대로 빚으로 잠그면 **기준선이 코드로 채워지고**, 진짜 빚
#:   서른한 건이 그 안에 묻힌다. 사용자가 읽는 것은 **한국어 문장**이다.
#:
#:   ⚠ 놓치는 쪽으로 틀린다. 순수 영문 라벨(`Add New Device`)은 이 술어를 지나간다 —
#:     그것은 UX-21(역할별 메뉴·영문 CRUD)의 자리이고, 이 판정기의 자리가 아니다.
HANGUL = re.compile(r"[가-힣]")

# ═══════════════════════════════════════════════════════════════════════════
# JSX 전수 파서 — **보간과 붙은 본문을 놓치지 않는다** (P-77 · 2026-09-06 · 차선 Q)
# ═══════════════════════════════════════════════════════════════════════════
#: ★ **출생 표본 ②** — 이 파서를 만들게 한 바로 그 두 자리다 [실측 2026-09-06 · 턴 H].
#:
#:   앞선 술어는 이랬다:
#:
#:       JSX_TEXT = re.compile(r">([^<>{}]*[가-힣][^<>{}]*)<")
#:
#:   `{}` 를 배제했기 때문에 **보간이 한 번이라도 끼면 그 본문 전체가 안 보였다.**
#:   그래서 `DrillMode.tsx` 의 <Tag>data_source = {current.data_source}</Tag> 가
#:   화면에 떠 있는데 게이트는 「잔여 0 · 통과」를 냈고, D-433 이 그 수를 근거로
#:   UX-20 을 닫았다. `FocusQueue.tsx` 의 「… F-14 통계는 왼쪽 수를 봅니다」도
#:   같은 사각이었다. **못 본 조각이 본 조각의 41%였다.**
#:
#:   그래서 이제 **JSX 로 읽는다** — 텍스트 노드 · 문자열 리터럴 · 템플릿 리터럴 조각 ·
#:   속성값(placeholder·title·aria-label·alt …) 전수.

_IDENT = re.compile(r"[A-Za-z0-9_$]")

#: JSX 도 정규식도 **식이 올 자리에서만** 시작한다. 앞 토큰이 식별자거나 닫는 괄호면
#: 그 `<` 는 `a < b` 이거나 `Array<T>` 다. 이 술어가 없으면 파서가 코드에서 샌다.
_EXPR_WORDS = frozenset(("return", "yield", "await", "typeof", "case", "in", "of",
                         "default", "else", "do", "void", "new", "delete"))


class Frag(NamedTuple):
    """사용자가 읽는 조각 하나. `start`·`end` 는 **소스 안의 자리**다 — 본 비율은
    이 자리들로 잰다(파서에게 「다 봤느냐」를 묻지 않기 위해서다)."""

    start: int
    end: int
    line: int
    kind: str
    text: str


def jsx_fragments(src: str) -> list[Frag]:
    """주석을 걷어 낸 소스를 **JSX 로 읽어** 사용자가 읽는 조각 전수를 뽑는다.

    되돌아가지 않는 한 벌 훑기다. 다섯 자리를 본다:

      ``문자열``    `'…'` · `"…"` 의 몸통
      ``템플릿``    백틱 문자열의 몸통 — **보간으로 잘라서** 조각마다 낸다
                    (사용자가 보는 것은 보간된 결과이지 그 안의 코드가 아니다)
      ``JSX본문``   태그 사이의 텍스트 노드 — **중괄호로 잘라서** 조각마다 낸다.
                    ★ 여기가 41%가 숨어 있던 자리다
      ``속성:이름`` placeholder="…" 처럼 속성에 박힌 문자열 (이름을 함께 남긴다)
      그리고 위 넷 안의 중괄호는 다시 코드로 읽는다 — 중첩은 깊이 제한 없이 돈다
    """
    frags: list[Frag] = []
    n = len(src)
    i = 0
    line = 1

    def adv(k: int = 1) -> None:
        nonlocal i, line
        for _ in range(k):
            if i < n and src[i] == "\n":
                line += 1
            i += 1

    def expr_position() -> bool:
        """지금 자리에 **식이 올 수 있는가.** `<` 와 `/` 의 뜻을 이것이 가른다."""
        j = i - 1
        while j >= 0 and src[j] in " \t\r\n":
            j -= 1
        if j < 0:
            return True
        if _IDENT.match(src[j]):
            k = j
            while k >= 0 and _IDENT.match(src[k]):
                k -= 1
            return src[k + 1:j + 1] in _EXPR_WORDS
        return src[j] not in ")]"

    def take_string() -> None:
        quote, start_line = src[i], line
        adv()
        start = i
        while i < n and src[i] != quote:
            if src[i] == "\\":
                adv(2)
                continue
            adv()
        frags.append(Frag(start, i, start_line, "문자열", src[start:i]))
        adv()

    def take_template() -> None:
        adv()                                   # 여는 백틱
        start, start_line = i, line
        while i < n and src[i] != "`":
            if src[i] == "\\":
                adv(2)
                continue
            if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                frags.append(Frag(start, i, start_line, "템플릿", src[start:i]))
                adv(2)
                take_code(closing_brace=True)
                start, start_line = i, line
                continue
            adv()
        frags.append(Frag(start, i, start_line, "템플릿", src[start:i]))
        adv()

    def take_regex() -> None:
        """정규식 리터럴을 통째로 넘긴다. **넘기지 않으면 따옴표가 든 정규식 하나가
        파서를 문자열 안으로 끌고 들어가고, 그 뒤 파일 전체가 안 보인다.**"""
        adv()
        in_class = False
        while i < n:
            ch = src[i]
            if ch == "\\":
                adv(2)
                continue
            if ch == "\n":
                return                          # 줄을 넘는 정규식은 없다 — 나눗셈이었다
            if ch == "[":
                in_class = True
            elif ch == "]":
                in_class = False
            elif ch == "/" and not in_class:
                adv()
                return
            adv()

    def take_code(closing_brace: bool = False) -> None:
        depth = 0
        while i < n:
            ch = src[i]
            if ch in "'\"":
                take_string()
                continue
            if ch == "`":
                take_template()
                continue
            if ch == "/" and i + 1 < n and src[i + 1] not in "/*" and expr_position():
                take_regex()
                continue
            if ch == "{":
                depth += 1
                adv()
                continue
            if ch == "}":
                if closing_brace and depth == 0:
                    adv()
                    return
                depth = max(0, depth - 1)
                adv()
                continue
            if ch == "<" and expr_position() and take_element():
                continue
            adv()

    def take_element() -> bool:
        """`<` 자리에서 부른다. **JSX 가 아니면 한 글자도 안 먹고 `False`.**"""
        nonlocal i, line
        snap = (i, line)
        adv()
        if i < n and src[i] == ">":             # 조각 태그
            adv()
            take_children()
            return True
        if i >= n or not (src[i].isalpha() or src[i] in "_$"):
            i, line = snap
            return False
        while i < n and (src[i].isalnum() or src[i] in "_$.:-"):
            adv()
        if take_attrs():
            return True                         # 자기 닫음 — 자식이 없다
        take_children()
        return True

    def take_attrs() -> bool:
        """속성부를 읽는다. 자기 닫음으로 끝나면 `True`, 자식이 이어지면 `False`."""
        while i < n:
            ch = src[i]
            if ch == "/" and i + 1 < n and src[i + 1] == ">":
                adv(2)
                return True
            if ch == ">":
                adv()
                return False
            if ch.isalpha() or ch in "_$":
                at = i
                while i < n and (src[i].isalnum() or src[i] in "_$-:."):
                    adv()
                name = src[at:i]
                while i < n and src[i] in " \t\r\n":
                    adv()
                if i < n and src[i] == "=":
                    adv()
                    while i < n and src[i] in " \t\r\n":
                        adv()
                    if i < n and src[i] in "'\"":
                        quote, start_line = src[i], line
                        adv()
                        start = i
                        while i < n and src[i] != quote:
                            if src[i] == "\\":
                                adv(2)
                                continue
                            adv()
                        frags.append(Frag(start, i, start_line,
                                          f"속성:{name}", src[start:i]))
                        adv()
                    elif i < n and src[i] == "{":
                        adv()
                        take_code(closing_brace=True)
                continue
            if ch == "{":                       # 펼침 속성
                adv()
                take_code(closing_brace=True)
                continue
            if ch in "'\"":
                take_string()
                continue
            adv()
        return True

    def take_children() -> None:
        nonlocal i, line
        start, start_line = i, line

        def flush() -> None:
            nonlocal start, start_line
            body = src[start:i]
            if body.strip():
                frags.append(Frag(start, i, start_line, "JSX본문", body))
            start, start_line = i, line

        while i < n:
            ch = src[i]
            if ch == "{":
                flush()
                adv()
                take_code(closing_brace=True)
                start, start_line = i, line
                continue
            if ch == "<":
                flush()
                if i + 1 < n and src[i + 1] == "/":
                    adv(2)
                    while i < n and src[i] != ">":
                        adv()
                    adv()
                    return
                snap = (i, line)
                if not take_element():
                    i, line = snap
                    adv()
                start, start_line = i, line
                continue
            adv()
        flush()

    take_code()
    return frags


def user_texts(src: str) -> list[tuple[int, str]]:
    """주석을 걷어 낸 소스에서 **사용자가 읽는 글자** 전수 — `(줄, 조각)`.

    줄 번호는 조각이 **시작하는 줄**이다 — 여러 줄 본문이면 첫 줄을 가리킨다.
    """
    return [(f.line, f.text) for f in jsx_fragments(src)]


def hangul_coverage(src: str, frags: list[Frag]) -> tuple[int, int]:
    """`(조각이 덮은 한글 글자 수, 소스의 한글 글자 수)` — **본 비율**의 분자와 분모.

    ★ **왜 파서 밖의 잣대인가.** 바뀐 파서에게 「다 봤느냐」를 물으면 언제나 100%다.
      그 대답은 아무것도 재지 않는다 — 41%를 못 보던 그날의 파서도 자기 기준으로는
      100%였다. 그래서 파서가 만들지 않은 수를 분모로 쓴다: **주석을 걷어 낸 화면
      소스에 남은 한글**은 사실상 전부 사용자 본문이고, 그 글자가 어느 조각에도
      안 담기면 그만큼을 **못 본 것**이다. 파서가 어디선가 새면 이 수가 떨어진다.

    ⚠ 이 잣대가 못 세는 것: 순영문 본문(data_source = live)에는 한글이 없다.
      그 자리는 패턴이 본다 — 본 비율은 **파서가 샜는지**를 재는 수이지
      「빠짐없이 걸렀는가」를 재는 수가 아니다.
    """
    total = len(HANGUL.findall(src))
    if total == 0:
        return 0, 0
    seen = bytearray(len(src))
    for f in frags:
        for pos in range(f.start, min(f.end, len(src))):
            seen[pos] = 1
    covered = sum(1 for pos, ch in enumerate(src) if seen[pos] and HANGUL.match(ch))
    return covered, total


def scan_line(line: str, near: str = "") -> list[str]:
    """한 조각(문자열 몸통 · JSX 본문)에서 걸린 패턴 이름들.

    `near` 는 그 조각 **바로 뒤의 소스**다 — 빈 화면의 「다음 손」이 같은 문장이
    아니라 **이웃 칸**에 설 수 있기 때문이다(턴 AB 에 그것 때문에 다섯 건을
    잘못 찍었다 · `scan_empty_aa` 의 주석 참조).

    ★ [P-221 · 턴 AA] 세 무리를 **한 술어로** 본다 — 기존 사전 + 표시명/오류 무리
      + 빈 화면. 갈래를 나누어 두 번 훑으면 한쪽이 조용히 아무것도 안 보게 된다
      (D-369 가 말하는 「두 벌」이 정확히 그 모양이다).
    """
    return ([name for name, rx in COMPILED if rx.search(line)]
            + scan_line_aa(line) + scan_empty_aa(line, near))


def norm(snippet: str) -> str:
    """기준선 열쇠에 쓸 모양. **줄 번호를 쓰지 않는다** — 줄은 늘 밀리고,
    밀린 줄로 잠그면 다음 커밋에서 빚 전부가 「새 위반」으로 되살아난다."""
    #: ★ 자르고 나서 다시 `strip()` 한다 [실측 2026-09-26]. 100자에서 잘린 자리가
    #:   공백이면 열쇠 끝에 공백이 남고, **pre-commit 의 trailing-whitespace 훅이 그것을
    #:   지운다.** 그러면 어제 잠근 빚 한 줄이 오늘 「새 위반」으로 되살아난다 —
    #:   게이트가 자기 기준선을 스스로 깨뜨리는 모양이다.
    return " ".join(snippet.split())[:100].strip()


def scan() -> tuple[int, list[tuple[str, int, str, str]], int, int, int]:
    """`(본 파일 수, [(상대경로, 줄, 패턴, 발췌)], 덮은 한글, 전체 한글)`."""
    findings: list[tuple[str, int, str, str]] = []
    files = [p for p in frontend_files() if in_scope(p)]
    covered = total = 0
    n_declared = 0
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        body = strip_comments(src)
        frags = jsx_fragments(body)
        c, t = hangul_coverage(body, frags)
        covered += c
        total += t
        for f in frags:
            if skipped_by_declaration(body, f):
                n_declared += 1
                continue
            near = body[f.end:f.end + NEIGHBOUR_CHARS * 2]
            for name in scan_line(f.text, near):
                findings.append((rel, f.line, name, norm(f.text)))
    return len(files), findings, covered, total, n_declared


def key(f: tuple[str, int, str, str]) -> str:
    rel, _lineno, name, snippet = f
    return f"{rel}\t{name}\t{snippet}"


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {ln for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")}


def self_test() -> int:
    #: ★★ [턴 AH · P-292 · 실측 2026-09-24] **일곱 건이 장식이었다.**
    #:   이 함수 안에 `ok = False` 가 일곱 번 있었는데 `ok` 는 **초기화도 안 됐고
    #:   읽는 데도 없었다** — 마지막 판정은 `fails` 만 본다. 그래서 그 일곱은
    #:   FAIL 을 찍고도 「자기시험 통과」로 끝났다(턴 AB 의 이웃 칸 셋 · 선언 표 둘
    #:   · 턴 AH 의 JSX 등호형 둘). **실패할 수 없는 시험은 시험이 아니다.**
    #:   찾은 경위: 정규식을 일부러 되돌려 새 출생 표본이 빨개지는지 보다가,
    #:   FAIL 이 찍혔는데 마지막 줄이 「통과」라고 말하는 것을 봤다.
    fails = 0
    for sample in BIRTH_SAMPLES:
        if not scan_line(sample):
            print(f"[COPY] 자기시험 FAIL 출생 표본을 못 잡았다: {sample}")
            fails += 1
    #: ★ **출생 표본 ②** (P-77) — 파서가 통째로 못 보던 두 자리. 조각 뽑기까지
    #:   끝까지 돌린다. `scan_line` 만 시험하면 **파서가 눈이 멀어도 초록**이다 —
    #:   그것이 2026-09-06 까지 이 게이트가 있던 상태다.
    for src, want in BIRTH_JSX:
        hits = {name for _line, text in user_texts(src) for name in scan_line(text)}
        if want not in hits:
            print(f"[COPY] 자기시험 FAIL 출생 표본 ②를 못 잡았다 ({want}): "
                  f"{norm(src)[:60]}")
            fails += 1
        covered, total = hangul_coverage(src, jsx_fragments(src))
        if total and covered != total:
            print(f"[COPY] 자기시험 FAIL 출생 표본 ②의 한글 {total}자 중 "
                  f"{covered}자만 조각에 담겼다 — 파서가 샌다")
            fails += 1
    # ═══════════════════════════════════════════════════════════════════════
    # ★ P-221 · 턴 AA — 표시명 · 빈 화면 · 오류 본문. **양성과 음성 둘 다.**
    #   턴 Z 에 `verify_classification` 이 **자기시험이 아예 없어서** 칸 이름을
    #   동사로 읽는 오독이 오래 살았다. 새 술어에는 출생 표본을 반드시 붙인다.
    # ═══════════════════════════════════════════════════════════════════════
    # ── 양성 ① — 출생 표본 일곱을 **하나씩** 잡는가 ────────────────────────
    for sample, want in AA_BIRTH:
        hits = scan_line(sample)
        if want not in hits:
            print(f"[COPY] 자기시험 FAIL P-221 출생 표본을 못 잡았다 "
                  f"({want}): {sample}")
            fails += 1
    # ── 양성 ② — JSX 본문으로 들어가도 잡는가 (파서까지 끝까지 돌린다) ──────
    jsx = ("<Paragraph>규칙은 사람이 아니라 역할을 가리킵니다 "
           "(예: fire_user · operator).</Paragraph>")
    if "역할 코드" not in {n for _l, t in user_texts(jsx) for n in scan_line(t)}:
        print("[COPY] 자기시험 FAIL 역할 코드가 JSX 본문 안에서 안 잡힌다 — "
              "`scan_line` 만 시험하면 파서가 눈이 멀어도 초록이다")
        fails += 1
    # ── 음성 ① — **코드는 화면이 아니다.** 한글이 없으면 보지 않는다 ────────
    #    이 음성 대조가 없으면 첫 수가 수백이 되고, 수백은 아무도 안 고친다.
    for code in ("role === 'fire_user'", "channels: ['webpush', 'email']",
                 "if (state === 'occurred') return null;", "const admin = true;",
                 #: ★★ **방어선을 결함으로 읽지 않는다** — `copy.ts::RAW_MARKERS` 는
                 #:   그 문장을 화면에 내려는 것이 아니라 **버리려고** 적어 둔 목록이다.
                 #:   턴 AA 에 이 게이트가 그 목록을 세 건 잡았다. 그것이 이 줄의 사유다.
                 "'Network Error',", "'Internal Server Error',",
                 "'Request failed with status code',"):
        if scan_line_aa(code):
            print(f"[COPY] 자기시험 FAIL 코드를 화면으로 읽었다: {code}")
            fails += 1
    # ── 음성 ② — 표시명으로 **고친** 문장은 잡히면 안 된다 ─────────────────
    for good in ("규칙은 사람이 아니라 역할을 가리킵니다 (예: 소방 담당 · 관제 요원).",
                 "보내는 채널이 웹푸시로 잡혀 있습니다",
                 "지금 상태는 접수됨 입니다",
                 "사진을 불러오지 못했습니다. 잠시 뒤 다시 시도해 보십시오."):
        if scan_line_aa(good):
            print(f"[COPY] 자기시험 FAIL 고쳐 쓴 문장을 잡았다: {good}")
            fails += 1
    # ── 음성 ③ — 숫자가 다 상태 코드는 아니다 (장비 수 · 분 · 건수) ─────────
    for good in ("카메라 404 대가 붙어 있습니다", "500 건을 내려받았습니다"):
        if "상태 코드 숫자" in scan_line_aa(good):
            print(f"[COPY] 자기시험 FAIL 장비 수·건수를 상태 코드로 읽었다: {good}")
            fails += 1
    # ── 빈 화면 — **0건이면 한 줄 + 다음 손** ──────────────────────────────
    for sample, want_hit in AA_EMPTY_BIRTH:
        hit = bool(scan_empty_aa(sample))
        if hit != want_hit:
            print(f"[COPY] 자기시험 FAIL 빈 화면 술어가 틀렸다 "
                  f"(기대 {'잡힘' if want_hit else '안 잡힘'}): {sample}")
            fails += 1
    # ── ★★ [턴 AB] 다음 손이 **이웃 칸**에 설 때 — 양성/음성 셋 ─────────────
    #   U24 가 `EventList.tsx` 에 빈 화면을 옳게 적었는데 이 게이트가 다섯 건을
    #   「다음 손 없음」으로 찍었다. 다음 손은 **이웃 칸**에 있었다.
    _NL = chr(10)
    _near_ok = (_NL + "      emptyNext: '카메라가 무엇인가를 감지하면 이 자리에 "
                "첫 줄이 생깁니다.',")
    if scan_empty_aa("이 기관에 기록된 사건이 0건입니다.", _near_ok):
        fails += 1
        print("[COPY] 자기시험 FAIL 다음 손이 **이웃 칸**에 있는데 잡았다 — "
              "U24 의 옳은 빈 화면 다섯을 이것으로 잘못 찍었다(턴 AB)")
    if not scan_empty_aa("이 기관에 기록된 사건이 0건입니다.", _NL + "      query: {},"):
        fails += 1
        print("[COPY] 자기시험 FAIL 이웃에 다음 손 칸이 **없는데** 안 잡았다 — "
              "이웃을 보는 것이 면제가 되면 안 된다")
    if not scan_empty_aa("이 기관에 기록된 사건이 0건입니다.",
                         _NL + "      emptyNext: '',"):
        fails += 1
        print("[COPY] 자기시험 FAIL 다음 손 칸이 **비었는데** 안 잡았다 — "
              "칸이 있는 것과 채워진 것은 다르다")

    # ── ★★ [턴 AH · P-292] 같은 칸이 **JSX 등호형**으로 설 때 ────────────────
    #   객체 리터럴만 보던 눈이 `emptyNext="…"` 를 못 봤다. 양성·음성을 함께 못박는다 —
    #   넓히기만 하고 음성을 안 두면 「칸이 있으면 무조건 면제」가 되어 빈 칸도 지나간다.
    _near_jsx = (_NL + '          emptyNext="위 서식에서 「만들기」를 누르면 '
                 '여기에 한 줄이 생깁니다."')
    if scan_empty_aa("아직 만든 보고서가 없습니다.", _near_jsx):
        fails += 1
        print("[COPY] 자기시험 FAIL 다음 손이 **JSX 등호형 이웃 칸**에 있는데 잡았다 — "
              "Reports·SettingsRules·SystemSettings 세 자리가 이것으로 찍혔다(턴 AH)")
    if not scan_empty_aa("아직 만든 보고서가 없습니다.", _NL + '          emptyNext=""'):
        fails += 1
        print("[COPY] 자기시험 FAIL JSX 등호형 칸이 **비었는데** 안 잡았다 — "
              "넓힌 것이 면제가 되면 안 된다")

    # ── ★★ [턴 AH · P-320] 재는 자리 — **gx-shell 의 모양을 그대로 재현한다** ──
    #   임시 나무 둘로 잰다(어디서 돌아도 같은 답 — 자기시험이 자리를 타면 안 된다).
    #   ㉠ 제자리: 표지 셋 다 있음 → 문제 0
    #   ㉡ 그날의 gx-shell: `docs/agent/evidence` 는 **있는데** 사전은 없음 → 잡아야 한다
    #      (디렉터리 존재만 보는 판정이면 ㉡ 을 통과시킨다 — 그것이 이 표본의 이유다)
    import tempfile
    with tempfile.TemporaryDirectory() as _tmp:
        _good = Path(_tmp) / "good"
        _shell = Path(_tmp) / "gxshell"
        for _m in WHERE_MARKERS:
            _p = _good / _m
            _p.parent.mkdir(parents=True, exist_ok=True)
            (_p.mkdir() if "." not in _p.name else _p.write_text("x", encoding="utf-8"))
        (_shell / "docs" / "agent" / "evidence").mkdir(parents=True)
        (_shell / "frontend" / "src" / "features").mkdir(parents=True)
        (_shell / "backend" / "config").mkdir(parents=True)
        (_shell / "backend" / "config" / "settings.py").write_text("x", encoding="utf-8")
        if where_problem(_good):
            fails += 1
            print("[COPY] 자기시험 FAIL 제자리를 틀린 자리로 읽었다: %s"
                  % where_problem(_good))
        if "docs/design/GX-COPY_v1.md" not in where_problem(_shell):
            fails += 1
            print("[COPY] 자기시험 FAIL **그날의 gx-shell 모양**(docs/agent 는 있고 사전은 "
                  "없음)을 제자리로 읽었다 — 재는 자리 확인이 디렉터리 존재만 본다")

    # ── ★★ [턴 AB] 「화면이 안 읽는다」고 **이름으로 선언한 표**는 건너뛴다 ──
    _decl_src = ("export const ROLE_NAMES_BLANK_BY_DECISION = {" + _NL
                 + "  order: '인수 자산(배송 주문) — 이 제품의 역할이 아니다 (§4-2 · P-229)',"
                 + _NL + "};" + _NL
                 + "export const SHOWN = { a: '사건 P-229 를 보십시오' };" + _NL)
    _spans = declared_spans(_decl_src)
    _in = _decl_src.index("인수 자산")
    _out = _decl_src.index("사건 P-229")
    if not (len(_spans) == 1 and any(a <= _in <= b for a, b in _spans)):
        fails += 1
        print("[COPY] 자기시험 FAIL 선언된 표를 못 찾았다")
    if any(a <= _out <= b for a, b in _spans):
        fails += 1
        print("[COPY] 자기시험 FAIL **선언 밖**의 조각까지 건너뛰었다 — "
              "선언이 면제가 되는 자리다")

    # ── 음성 ④ — 빈 화면 술어가 **빈 화면이 아닌 문장**을 잡으면 안 된다 ────
    for good in ("사건 12건을 보고 있습니다", "종결하기 (3)"):
        if scan_empty_aa(good):
            print(f"[COPY] 자기시험 FAIL 빈 화면이 아닌 문장을 잡았다: {good}")
            fails += 1
    # ── ★ 사전이 **섰는지**를 소리 내어 확인한다 (없다 ≠ 0건 · D-301) ──────
    _have, _missing = aa_display_dicts()
    if not isinstance(_have, list) or not isinstance(_missing, list):
        print("[COPY] 자기시험 FAIL 표시명 사전 확인기가 목록을 안 낸다")
        fails += 1
    if len(_have) + len(_missing) != len(DISPLAY_DICTS):
        print("[COPY] 자기시험 FAIL 사전 셈이 어긋난다 — 있는 것과 없는 것의 합이 "
              "전체와 다르다. 안 세어진 사전은 「있다」로 읽힌다")
        fails += 1

    # 음성 ① — 주석은 소스의 자리다
    if scan_line(strip_comments("// UX-17 · D-421 · `kernels.k1_event`" + chr(10)).strip()):
        print("[COPY] 자기시험 FAIL 주석을 잡았다 — 소스가 아니라 화면을 본다")
        fails += 1
    # 음성 ② — 사전대로 고친 문장은 잡히면 안 된다
    for good in ("'훈련 모드'", "'미처리'", "'연계 대기'", "'사진을 불러오지 못했습니다'"):
        if scan_line(good):
            print(f"[COPY] 자기시험 FAIL 사전대로 고친 문장을 잡았다: {good}")
            fails += 1
    # 음성 ③ — 열쇠가 줄 번호를 타면 안 된다 (한 줄 밀면 빚이 되살아난다)
    a = key(("x.tsx", 10, "백틱", norm("  const a = `b`;")))
    b = key(("x.tsx", 99, "백틱", norm("const a = `b`;")))
    if a != b:
        print("[COPY] 자기시험 FAIL 줄 번호·들여쓰기가 열쇠를 바꾼다 — 빚이 되살아난다")
        fails += 1
    # 음성 ④ — **부등호는 태그가 아니다.** 이 술어가 없으면 파서가 코드로 새고,
    #          샌 파서는 조용히 파일 하나를 통째로 안 본다.
    for code in ("if (a < b && c > d) { doIt(); }",
                 "const m: Array<string> = useMemo<Foo>(() => [], []);"):
        if [t for _l, t in user_texts(code) if HANGUL.search(t)]:
            print(f"[COPY] 자기시험 FAIL 부등호·제네릭을 JSX 로 읽었다: {code}")
            fails += 1
    # 음성 ⑤ — 따옴표가 든 정규식 하나가 파서를 끌고 가면 안 된다
    derail = "const rx = /['\"]/; const msg = '사진을 불러오지 못했습니다';"
    if "사진을 불러오지 못했습니다" not in [t for _l, t in user_texts(derail)]:
        print("[COPY] 자기시험 FAIL 정규식 뒤의 본문을 못 봤다 — 파서가 새고 있다")
        fails += 1
    if fails:
        print(f"[COPY] 자기시험 {fails}건 실패")
        return 1
    print(f"[COPY] 자기시험 통과 — 양성 {len(BIRTH_SAMPLES)}(문구) + "
          f"{len(BIRTH_JSX)}(JSX 파서) · 음성 8")
    return 0


#: ★★ [턴 AH · P-320] **재는 자리는 코드가 확인한다 — 머리글이 아니라.**
#:   이 파일 머리글은 「호스트에서 돈다」고 적었는데 조율자가 gx-shell 안에서 돌렸다.
#:   거기엔 `docs/` 가 없어 기준선을 못 봤고, 「83 새 위반」은 실은 **84 전체 위반**
#:   이었다(재는 자리 두 번째 · 2026-09-24). 머리글은 늙고, 사람은 머리글을 안 읽는다.
#:
#:   ⚠⚠ **「디렉터리가 있나」로는 못 잡는다** [실측 2026-09-24]. gx-shell 안의
#:   `/repo/docs` 는 **존재한다** — 다른 게이트가 증거를 쓰다 `docs/agent/evidence`
#:   부분 나무를 만들어 뒀다. `docs/agent` 를 표지로 삼았으면 그 함정을 그대로
#:   통과했다(표지 후보를 양쪽에서 재 보다가 잡혔다). 그래서 표지는 **이 게이트가
#:   실제로 기대는 입력**이다: 사전이 안 보이면 사전과 대 보는 판정이 성립하지 않는다.
WHERE_MARKERS = (
    "docs/design/GX-COPY_v1.md",    # 이 게이트의 사전 — docs 가 진짜로 물렸는가
    "frontend/src/features",        # 재는 대상
    "backend/config/settings.py",   # 저장소 뿌리가 맞는가
)


def where_problem(root: Path = ROOT) -> list[str]:
    """재는 자리에 **없는 표지**들. 비면 제자리다."""
    return [m for m in WHERE_MARKERS if not (root / m).exists()]


def main() -> int:
    ap = argparse.ArgumentParser(description="UX-20 제품 언어 판정기")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--strict", action="store_true", help="래칫 없이 — 잔여 0 이어야 통과")
    ap.add_argument("--freeze", action="store_true", help="오늘의 빚을 기준선에 잠근다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    #: 자기시험은 파일을 안 읽으니 어디서 돌아도 된다. **판정만** 자리를 묻는다.
    _missing_here = where_problem()
    if _missing_here:
        print("[COPY] **판정 불가 · 회색** — 재는 자리가 틀렸다. 없는 표지: "
              + " · ".join(_missing_here))
        print("[COPY]   이 게이트는 **호스트에서** 돈다. 컨테이너 안에서는 docs 가 "
              "물려 있지 않아 기준선·사전을 못 본다 — 수를 내지 않는다 (P-320)")
        return 2

    seen, findings, covered, total, n_declared = scan()
    if seen == 0:
        print(f"[COPY] **판정 불가** — {' · '.join(SCOPE)} 에서 파일을 한 개도 못 읽었다 "
              "(0건 검사와 검사 못 함은 다르다 · D-301)")
        return 2

    #: ★ **첫 줄이 본 비율이다** (P-77). 커버리지를 모르는 게이트는 판정한 것이 아니다 —
    #:   41%를 못 보던 그날의 게이트도 「잔여 0 · 통과」라고 적었다.
    ratio = (covered / total) if total else 0.0
    print(f"[COPY] **본 비율 {ratio:.0%}** — 화면 소스의 한글 {total:,}자 중 "
          f"{covered:,}자가 조각에 담겼다 (기준 {COVERAGE_FLOOR:.0%})")
    print(f"[COPY] [입력] {seen}개 화면 파일 (주석 걷어낸 뒤) · 패턴 "
          f"{len(COMPILED) + len(HANGUL_ONLY_COMPILED) + 1}종"
          f"(사전 {len(COMPILED)} + P-221 표시명·오류 {len(HANGUL_ONLY_COMPILED)} + 빈 화면 1)")
    #: ★★ [턴 AB] **선언으로 건너뛴 조각을 소리 내어 센다.** 안 세면 다음 사람이
    #:   「이 게이트가 전수를 봤다」고 읽는다 — 면제와 선언은 **수로** 갈린다.
    print("[COPY] [입력] 선언으로 건너뛴 조각 **%d개** — `*_BY_DECISION` · "
          "`NAV_NO_SCREEN_YET` 처럼 **이름으로** 「화면이 안 읽는다」고 적은 표. "
          "면제가 아니라 선언이고, 그 표의 값이 화면에 뜨면 그것은 그 표의 결함이다"
          % n_declared)
    #: ★ P-221 — **사전이 섰는지를 소리 내어 말한다.** 안 말하면 다음 턴에 누가
    #:   「표시명 게이트가 초록이니 사전이 있다」고 읽는다. 「없다」는 「0건」이 아니다.
    _have, _missing = aa_display_dicts()
    print("[COPY] [입력] 표시명 사전 %d/%d — 선 것: %s"
          % (len(_have), len(DISPLAY_DICTS), " · ".join(_have) or "(없다)"))
    for _m in _missing:
        print("[COPY]   ? 사전이 아직 없다: %s — 이 게이트는 그 칸을 **금지 목록만으로** "
              "본다. 표시명이 서면 그쪽이 정본이다 (새로 만들지 않는다 · D-369)" % _m)

    if total and ratio < COVERAGE_FLOOR:
        print(f"[COPY] **판정 불가** — 본 비율 {ratio:.0%} 가 기준 {COVERAGE_FLOOR:.0%} "
              "아래다. 파서가 화면 글자의 일부를 못 보고 있고, **못 본 자리에서 나온 "
              "「잔여 0」은 사실이 아니다** (D-301). 회색으로 둔다")
        return 2

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# UX-20 제품 언어 — **오늘의 빚**. 줄이는 것만 허용한다 (래칫 · D-311).",
                 "# 열쇠: 파일<TAB>패턴<TAB>발췌(공백 정규화). 줄 번호는 쓰지 않는다.",
                 f"# 잠근 날: 2026-09-06(턴 I) · "
                 f"{len(set(map(key, findings)))}건 · 본 비율 {ratio:.0%}",
                 ""]
        lines += sorted({key(f) for f in findings})
        BASELINE.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        print(f"[COPY] 기준선에 {len(set(map(key, findings)))}건을 잠갔다 → "
              f"{BASELINE.relative_to(ROOT).as_posix()}")
        return 0

    baseline = load_baseline()
    fresh = [f for f in findings if key(f) not in baseline]
    seen_keys = {key(f) for f in findings}
    paid = sorted(baseline - seen_keys)

    if args.list:
        for rel, lineno, name, snippet in findings:
            mark = "NEW " if key((rel, lineno, name, snippet)) not in baseline else "빚  "
            print(f"          {mark}{rel}:{lineno}  [{name}]  {snippet}")

    print(f"[COPY] 잔여 {len(seen_keys)}건 (기준선 {len(baseline)}건 · 갚은 것 {len(paid)}건)")

    if args.strict and seen_keys:
        print(f"[COPY] FAIL --strict — 잔여 {len(seen_keys)}건")
        return 1

    if fresh:
        for rel, lineno, name, snippet in fresh:
            print(f"[COPY] FAIL 새 위반 {rel}:{lineno}  [{name}]  {snippet}")
        print(f"[COPY] FAIL 새로 생긴 대장 언어 {len(fresh)}건 — "
              "사전에 없는 문구는 만들지 않는다 (docs/design/GX-COPY_v1.md)")
        return 1

    #: ★ [P-87 · 2026-09-06 턴 I] **「파일이 없다」와 「빚이 0이다」는 다른 칸이다.**
    #:   여기가 `if not baseline:` 이었다 — 빚을 전부 갚고 기준선을 0건으로 잠그면
    #:   그 순간 게이트가 「기준선이 없다 · 회색」을 냈다. 다 갚은 것이 못 잰 것과
    #:   같은 칸에 들어간 것이다. 「없다」는 **파일의 부재**로만 판정한다.
    if not BASELINE.exists():
        print("[COPY] **판정 불가** — 기준선 파일이 없다 "
              "(`--freeze` 로 오늘의 빚을 먼저 잠근다)")
        return 2
    print("[COPY] 통과 — 새로 생긴 대장 언어 0건")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("화면이 **대장의 말**로 말하는가 — 화면 파일 **분모 %d개**(지금 셌다 · 주석은 "
               "걷어낸다) × 패턴 %d종(사전 %d + P-221 표시명·오류 %d + 빈 화면 1). "
               "래칫이라 **새 위반만** 빨강이고, 잔여는 수로 말한다"
               % (len([p for p in frontend_files() if in_scope(p)]),
                  len(COMPILED) + len(HANGUL_ONLY_COMPILED) + 1,
                  len(COMPILED), len(HANGUL_ONLY_COMPILED))),
    )
    raise SystemExit(main())
