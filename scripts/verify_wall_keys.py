#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""UX-15 · UX-16 — **키보드 · 소리 · 월 모드**를 브라우저 없이 잰다 (차선 C1 · 2026-09-05).

왜 이 판정기가 필요한가
-----------------------
이 두 절이 고치는 것은 **화면이 뜨는가**가 아니다. 화면은 어느 쪽으로 망가져도
멀쩡히 뜬다:

    · 입력창 갈래를 빠뜨리면 → 화면은 그대로고 **검색창에 j 를 못 친다**
    · 등급 문지기를 빠뜨리면 → 화면은 그대로고 **주의 등급까지 8시간 운다**
    · 묶음 접기를 빠뜨리면   → 화면은 카드 한 장인데 **귀는 일곱 번 맞는다**
    · 24 미만 글자가 하나 남으면 → 화면은 그대로고 **3m 밖에서 그 줄만 없다**
    · 갱신 시각을 안 적으면   → 얼어붙은 화면이 **평온한 화면과 똑같이 생겼다**

전부 **캡처로는 안 보이는** 고장이다. 그래서 소스에서 그 갈래의 **실재**를 센다.

이 저장소에는 화면 동시 접속이 하나뿐이라 걷기와 캡처는 병합 뒤 조율자가 한다.
이 판정기는 **브라우저 없이 호스트에서** 돈다 — Django 도 node 도 필요 없다.

    python scripts/verify_wall_keys.py
    python scripts/verify_wall_keys.py --list
    python scripts/verify_wall_keys.py --self-test

종료 코드 — 세 갈래다 (이 저장소의 규약):
    0  쟀고 통과
    1  쟀고 실패
    2  **못 쟀다** (파일이 없다 · 읽을 수 없다)  ← 통과로 세지 않는다

★ 사전 밖 낱말·금지어는 **여기서 재지 않는다.** 그것은 `verify_ui_copy.py` 의 자리이고,
  같은 것을 두 벌 만들면 둘이 어긋나고 어긋난 쪽이 조용히 아무것도 안 본다(D-369).
  주석을 걷어 내는 일도 마찬가지로 `verify_ui_secrets.strip_comments` 한 벌만 쓴다 —
  주석을 세면 「하겠다고 적은 것」이 「한 것」으로 통과한다.


★ 출생 표본 (D-310) — **이 도구를 만들게 한 바로 그 사례**
----------------------------------------------------------
차선 C1 이 단축키를 `event.key` 로 짰다가 잡은 것이다:

    한글 입력기가 켜진 채 `j` 를 누르면 `event.key` 는 **`"ㅓ"`** 로 온다.

관제요원은 8시간 내내 한국어를 친다. 그래서 이 결함은 「가끔 안 먹는다」로 보고되고
**아무도 재현하지 못한다** — 재현하려는 사람의 자판이 영문이면 언제나 잘 되기 때문이다.
자판의 **자리**(`event.code` = `"KeyJ"`)는 입력기와 무관하다.

그 사례가 `BAD_KEYS_IME_ONLY_KEY` fixture 로 이 파일 안에 박혀 있고, 자기시험의
음성 갈래가 그것을 먹는다. 술어 ①의 마지막 줄이 지킨다 — 글자만 보고 자리를 안 보는
갈래가 다시 생기면 빨개진다.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_ui_secrets import strip_comments  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 보는 자리
# ═══════════════════════════════════════════════════════════════════════════
FE = "frontend/src/features/dsm"
TARGETS = {
    "keys": f"{FE}/hooks/useQueueKeys.ts",
    "alarm": f"{FE}/hooks/useCriticalAlarm.ts",
    "sound": f"{FE}/hooks/useAlertSound.ts",
    "queue": f"{FE}/pages/FocusQueue.tsx",
    "wall": f"{FE}/pages/Wall.tsx",
}

#: 월 모드의 최소 글자. 대장이 못박은 수다 — 이보다 작은 선언이 하나라도 있으면 실패다.
MIN_WALL_PX = 24

#: 조율자가 세운 자리표의 글자. 병합 뒤에도 보이면 그 절은 **닫히지 않은 것**이다.
PLACEHOLDER = "이 화면은 아직 준비 중입니다"


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 전부 **소스 문자열 하나**만 받는다. 그래야 자기시험이 가짜 소스로 잴 수 있다.
# ═══════════════════════════════════════════════════════════════════════════

#: `if (isTypingTarget(ev.target)) return;` 처럼 **초점을 물어보고 빠져나가는** 자리.
_GUARD_USE = GUARD_USE = re.compile(r"if\s*\([^;{}]*\.target[^;{}]*\)\s*\{?\s*return")
#: 무엇을 초점으로 보는가 — 입력칸 · 여러 줄 칸 · 편집 가능한 자리.
GUARD_TAGS = ("INPUT", "TEXTAREA")
GUARD_EDIT = re.compile(r"isContentEditable|contenteditable", re.I)

#: 등급 문지기. 상수로 뺀 것도 잡는다 (`card.severity !== CRITICAL`).
SEVERITY_GATE = re.compile(
    r"\.severity\s*(?:===|!==)\s*(?:['\"]critical['\"]|[A-Z_][A-Z0-9_]*)"
)
#: 그 상수가 정말 `critical` 인가. 이름만 CRITICAL 이고 값이 다른 것을 막는다.
CRITICAL_CONST = re.compile(r"[A-Z_][A-Z0-9_]*\s*=\s*['\"]critical['\"]")

#: 글자 크기 선언. 세 모양을 다 본다.
FONT_PX = re.compile(
    r"fontSize\s*[:=]\s*['\"]?(\d+)(?:px)?['\"]?|font-size\s*:\s*(\d+)px"
)

#: 주기 갱신이 **수로** 선언돼 있는가.
PERIOD = re.compile(r"(?:refreshMs|REFRESH_MS|refresh_ms)\s*[:=]\s*([\d_]+)")


#: 자판의 **자리**를 읽는가. `ev.code` · `event.code` · 구조분해(`{ code }`) 를 다 받는다 —
#: 읽는 방법을 하나로 못박으면 판정기가 문법을 강요하게 되고, 그것은 이 절의 내용이 아니다.
CODE_READ = re.compile(r"\.code\b|\bcode\s*[,}]|\bcode\s*=")


def check_keys(src: str) -> list[str]:
    """① 큐 화면에 키 처리기가 있고 **입력창 포커스에서 무시하는 갈래**가 실재한다."""
    bad: list[str] = []
    if "keydown" not in src:
        bad.append("키 처리기가 없다 — 누를 자리가 없다")
    if not all(tag in src for tag in GUARD_TAGS):
        bad.append("입력칸·여러 줄 칸을 가리는 갈래가 없다 — 검색창에 j 를 못 친다")
    if not GUARD_EDIT.search(src):
        bad.append("편집 가능한 자리를 가리는 갈래가 없다")
    if not GUARD_USE.search(src):
        bad.append("입력창 갈래가 **불리지 않는다** — 정의만 있고 쓰이지 않으면 없는 것이다")
    # ★ 출생 표본을 지키는 갈래 (D-310) — 아래 머리말의 그 사례다.
    #   자판의 **자리**(`ev.code`)를 안 보고 글자(`ev.key`)만 보면, 한글 입력기가 켜진
    #   순간 단축키가 전부 죽는다. 그 고장은 **영문 자판으로 재현하면 언제나 잘 된다** —
    #   그래서 「가끔 안 먹는다」로만 보고되고 아무도 못 잡는다.
    if not CODE_READ.search(src):
        bad.append("자판의 자리(ev.code)를 안 본다 — 한글 입력기가 켜지면 단축키가 전부 죽는다")
    return bad


def check_sound(src: str) -> list[str]:
    """② 소리가 **심각에서만** 울리고, 묶음(×N)에서 **1회로 접히는** 자리가 실재한다."""
    bad: list[str] = []
    gate = SEVERITY_GATE.search(src)
    if not gate:
        bad.append("등급 문지기가 없다 — 경계·주의까지 8시간 운다")
    elif "'critical'" not in gate.group(0) and '"critical"' not in gate.group(0):
        # 상수로 뺐다면 그 상수의 값이 정말 그것인지 본다.
        if not CRITICAL_CONST.search(src):
            bad.append("등급 문지기가 무엇을 재는지 알 수 없다 — 상수의 값이 안 보인다")
    if "member_event_ids" not in src:
        bad.append("묶인 원본 id 를 안 본다 — 카드 한 장에 소리가 여러 번 난다")
    if ".has(" not in src or "Set" not in src:
        bad.append("이미 울린 것을 기억하는 자리가 없다 — 갱신마다 다시 운다")
    return bad


def check_wall_font(src: str) -> list[str]:
    """③ 월 모드의 글자 크기 선언이 **전부 24 이상**이다."""
    sizes: list[int] = []
    for m in FONT_PX.finditer(src):
        raw = m.group(1) or m.group(2)
        if raw is not None:
            sizes.append(int(raw))
    if not sizes:
        # ★ 0건을 통과로 세지 않는다. 선언이 없으면 **라이브러리 기본값 14** 가 그린다.
        return ["글자 크기 선언이 한 개도 없다 — 잰 것이 아니라 못 잰 것이다"]
    small = sorted({n for n in sizes if n < MIN_WALL_PX})
    if small:
        return [f"24 미만 글자 선언 {len(small)}종: {small} (선언 {len(sizes)}건)"]
    return []


def check_wall_refresh(src: str) -> list[str]:
    """④ 월 모드가 **자동 갱신**과 **마지막 갱신 시각**을 화면에 말한다."""
    bad: list[str] = []
    if "자동 갱신 중" not in src:
        bad.append("자동 갱신 중이라고 말하는 자리가 없다")
    if "마지막 갱신" not in src:
        bad.append("마지막 갱신 시각을 말하는 자리가 없다 — 멈춘 화면이 평온해 보인다")
    m = PERIOD.search(src)
    if not m:
        bad.append("갱신 주기가 수로 선언돼 있지 않다")
    else:
        ms = int(m.group(1).replace("_", ""))
        if ms <= 0:
            bad.append("갱신 주기가 0 이하다 — 갱신이 없다")
    if "setInterval" not in src:
        # 주기 호출과 별개다: 상대시각 글자가 스스로 자라지 않으면 그 줄이 거짓말을 한다.
        bad.append("화면 시계가 스스로 돌지 않는다 — 「마지막 갱신」이 얼어붙는다")
    return bad


#: ★ [턴 S · 조율자] **말은 사전에서 온다.** UX-31′ 로 월 모드의 실패 문장이 `copy.ts`
#:   (`WALL_COPY` · `CAMERA_COPY`)로 옮겨 갔다. 술어 ⑤ 는 글자를 `Wall.tsx` 안에서만 찾았고,
#:   그래서 **제품은 그대로 말하는데 판정기만 빨개졌다** — D-470 이 이름 붙인 그 모양이다.
#:   글자를 화면에 되돌려 놓는 쪽은 택하지 않았다(그러면 사전이 두 벌이 된다).
#:   대신 판정기가 참조를 **풀어 읽는다**: `WALL_COPY.stale` 을 보면 `copy.ts` 의 그 블록에서
#:   값을 꺼내 소스 뒤에 붙이고, 그 다음에야 글자를 찾는다.
#:   ⚠ **없는 이름을 가리키면 풀리지 않는다** — 그러면 글자가 없으니 그대로 빨강이다. 그것이
#:     옳다: 사전에 없는 말을 화면이 부르는 것은 「말하는 자리가 없다」와 같은 사실이다.
COPY_TS = f"{FE}/copy.ts"
_COPY_REF = re.compile(r"(?<![A-Za-z0-9_])(WALL_COPY|CAMERA_COPY)[.]([A-Za-z_][A-Za-z0-9_]*)")


def _copy_value(copy_src: str, block: str, name: str):
    """`export const <block> = { … } as const;` 안에서 `name: '…'` 하나를 꺼낸다."""
    m = re.search(rf"export const {block}\s*=\s*\{{(.*?)\}}\s*as const", copy_src, re.S)
    if not m:
        return None
    v = re.search(rf"(?m)^\s*{name}\s*:\s*'([^']*)'", m.group(1))
    return v.group(1) if v else None


def inline_copy_refs(src: str, copy_src=None) -> str:
    """상수 참조를 사전 값으로 풀어 소스 뒤에 붙인다. 못 푼 참조는 그대로 둔다."""
    refs = sorted(set(_COPY_REF.findall(src)))
    if not refs:
        return src
    if copy_src is None:
        cp = Path(__file__).resolve().parents[1] / COPY_TS
        copy_src = cp.read_text(encoding="utf-8") if cp.is_file() else ""
    found = [_copy_value(copy_src, b, n) for b, n in refs]
    return src + "\n" + "\n".join(v for v in found if v)


def check_wall_voice(src: str, copy_src=None) -> list[str]:
    """⑤ 갱신이 실패했을 때 월 모드가 **그 사실을 말한다** (칸마다 따로).

    ★ 상수(`WALL_COPY.*` · `CAMERA_COPY.*`)로 말해도 인정한다 — 단 사전에 그 이름이
      **실제로** 있어야 한다. `inline_copy_refs` 가 푼다.

    ★ 사전 밖 낱말은 여기서 재지 않는다 — `verify_ui_copy.py` 의 자리다.
      여기서 재는 것은 「말하는 자리가 실재하는가」 하나다.
    """
    src = inline_copy_refs(src, copy_src)
    bad: list[str] = []
    if "불러오지 못했습니다" not in src:
        bad.append("못 가져온 것을 말하는 자리가 없다")
    if "카메라 상태를 불러오지 못했습니다" not in src:
        bad.append("카메라 상태 칸이 혼자 실패했을 때 말하는 자리가 없다")
    if PLACEHOLDER in src:
        bad.append("자리표 글자가 그대로 남아 있다 — 이 절은 닫히지 않았다")
    return bad


def check_wiring(src: str) -> list[str]:
    """⑥ 큐 화면이 위 갈래들을 **실제로 부른다.** 훅만 있고 안 부르면 없는 것이다."""
    bad: list[str] = []
    for name in ("useQueueKeys", "useCriticalAlarm", "useAlertSound"):
        if name not in src:
            bad.append(f"큐 화면이 {name} 을 부르지 않는다")
    if "소리가 꺼져 있습니다" not in src:
        bad.append("음소거일 때 그 사실을 먼저 말하는 자리가 없다")
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# ⑦ **한글 IME 상태 재현** — 세종 P-58 이 더 요구한 것 (2026-09-05 턴 E · 차선 S)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 술어 ①만으로는 부족한가
# --------------------------
# ①은 「소스 어딘가에 `.code` 를 읽는 자리가 있는가」를 센다. 그것으로는 **이 모양을
# 못 잡는다**:
#
#     const code = ev.code;                 // 읽기는 읽는다 (①은 초록)
#     logDebug(code);
#     switch (ev.key) { case 'j': ... }      // 그런데 **판정은 글자로 한다** (전멸)
#
# 즉 ①은 「읽는가」를 묻고, ⑦은 **「무엇으로 고르는가」**를 묻는다. 둘은 다른 물음이다.
#
# 어떻게 브라우저 없이 재는가 — **잰 것과 못 잰 것을 먼저 가른다**
# ----------------------------------------------------------------
# 이 판정기는 브라우저를 열지 않는다(그 자리는 이 턴에 QA/E2E 것이다). 대신:
#
#     ① 소스에서 **배선**을 뽑는다 — switch 가 무엇을 받고, case 라벨이 무엇인가
#     ② 한글 입력기가 켜진 상태의 **키 이벤트 모형**을 만든다
#     ③ 그 이벤트를 ①의 배선에 흘려 보내 **먹는지**를 본다
#
# ★ 이것은 **모형에 대한 재현**이지 브라우저 실측이 아니다. 그 사실을 숨기지 않는다.
#   모형이 옳다는 근거는 아래 `IME_MODEL_BASIS` 에 적었고, 모형이 틀리면 이 술어도
#   틀린다 — 그래서 **다음 사람이 브라우저에서 확인할 것 셋**을 `BROWSER_TODO` 에
#   남겼다. 「못 잰 것을 잰 척하지 않는다」가 이 절의 규약이다.

#: 모형의 근거. 이 셋이 깨지면 ⑦의 답도 깨진다.
IME_MODEL_BASIS = (
    "한글 입력기가 켜지면 `event.key` 는 두벌식 낱자로 온다 (j→ㅓ · k→ㅏ · m→ㅡ · r→ㄱ) "
    "— 턴 D 실측",
    "`event.code` 는 자판의 **자리**라 입력기와 무관하다 (KeyJ 는 언제나 KeyJ)",
    "숫자열·Enter 는 입력기가 바꾸지 않는다 — 그래서 고장이 **부분적**이고, "
    "그래서 「가끔 안 먹는다」로만 보고된다",
)

#: ⑦이 **못 재는 것** 셋. 브라우저에서만 답이 난다.
BROWSER_TODO = (
    "한글 입력기가 켜진 채 **입력칸 밖**에서 j 를 눌렀을 때 `ev.isComposing` 이 "
    "참인가. 참이면 `if (ev.isComposing) return;` 한 줄이 단축키를 전부 삼킨다 "
    "— 물리 키로 바꾼 것과 무관하게 죽는다",
    "그때 `ev.code` 가 정말 'KeyJ' 로 오는가 (일부 입력기는 keydown 을 "
    "keyCode 229 로만 올린다고 알려져 있다)",
    "월 모드처럼 **초점이 아무 데도 없는** 화면에서 window 리스너가 그 keydown 을 "
    "받는가",
)

#: **한글 입력기 켜짐** — 그 자리를 눌렀을 때 `event.key` 로 오는 것 (두벌식).
#:
#: ★ 여기서 가장 중요한 칸은 낱자가 아니라 **숫자열과 Enter 다.** 입력기는 그것들을
#:   바꾸지 않는다 — 그래서 글자로 고르는 배선에서도 1·2·3·Enter 는 **멀쩡히 먹는다.**
#:   고장이 여덟 자리 중 넷에만 나므로 사람은 「가끔 안 먹는다」라고 보고하고,
#:   재현하려는 사람의 자판은 영문이라 **언제나 잘 된다.** 이 표가 그 함정 자체다.
KEY_WHEN_IME_ON = {
    "KeyJ": "ㅓ", "KeyK": "ㅏ", "KeyM": "ㅡ", "KeyR": "ㄱ",
    "Digit1": "1", "Digit2": "2", "Digit3": "3",
    "Numpad1": "1", "Numpad2": "2", "Numpad3": "3",
    "Enter": "Enter",
}

#: **영문 자판** — 대조군. 재현하려는 사람이 늘 보는 세상이다.
KEY_WHEN_IME_OFF = {
    "KeyJ": "j", "KeyK": "k", "KeyM": "m", "KeyR": "r",
    "Digit1": "1", "Digit2": "2", "Digit3": "3",
    "Numpad1": "1", "Numpad2": "2", "Numpad3": "3",
    "Enter": "Enter",
}


@dataclass(frozen=True)
class KeyEvent:
    """브라우저가 올리는 keydown 하나의 **모형**."""

    code: str                  # 자판의 자리 — 입력기와 무관
    key: str                   # 입력기가 만든 글자
    is_composing: bool = False
    target_tag: str = "BODY"   # 초점이 있는 요소
    ctrl: bool = False
    alt: bool = False
    meta: bool = False


#: switch 가 받는 값이 무엇에서 왔는가.
_SWITCH = re.compile(r"switch\s*\(\s*([A-Za-z_$][\w$.]*)\s*\)")
_CASE = re.compile(r"case\s*['\"]([^'\"]+)['\"]\s*:")
_ASSIGN = re.compile(r"(?:const|let|var)\s+%s\s*=\s*([^;]+);")
_FN_BODY = re.compile(r"function\s+%s\s*\([^)]*\)[^{]*\{")
#: 입력창 갈래가 **불리는** 자리 (①과 같은 술어를 쓴다 — 두 벌을 만들지 않는다).
_COMPOSING_GUARD = re.compile(r"if\s*\([^;{}]*isComposing[^;{}]*\)\s*\{?\s*return")
_MODIFIER_GUARD = re.compile(r"if\s*\([^;{}]*(?:ctrlKey|metaKey|altKey)[^;{}]*\)\s*\{?\s*return")


def _resolve_reader(src: str, subject: str) -> str | None:
    """switch 가 받는 값이 **자리(`code`)** 에서 왔는가 **글자(`key`)** 에서 왔는가.

    셋을 차례로 본다: 직접 읽기 → 변수 대입 → 함수 반환. 못 풀면 `None` 을 돌려
    **판정 불가**로 만든다 — 모르는 것을 「code 일 것이다」로 채우지 않는다.
    """
    if subject.endswith(".code"):
        return "code"
    if subject.endswith(".key"):
        return "key"
    name = subject.split(".")[0]

    m = re.search(_ASSIGN.pattern % re.escape(name), src)
    if m:
        expr = m.group(1)
        call = re.match(r"\s*([A-Za-z_$][\w$]*)\s*\(", expr)
        if call:
            fn = re.search(_FN_BODY.pattern % re.escape(call.group(1)), src)
            if fn:
                body = src[fn.end():]
                order = [(body.find(".code"), "code"), (body.find(".key"), "key")]
                order = [(i, k) for i, k in order if i >= 0]
                if order:
                    return min(order)[1]
            return None
        if ".code" in expr:
            return "code"
        if ".key" in expr:
            return "key"
    return None


def extract_dispatch(src: str) -> tuple[str | None, list[str]]:
    """소스에서 **배선**을 뽑는다 — (무엇으로 고르는가, 고를 수 있는 라벨들)."""
    m = _SWITCH.search(src)
    if not m:
        return None, []
    reader = _resolve_reader(src, m.group(1))
    labels = _CASE.findall(src[m.end():])
    return reader, labels


def dispatch(src: str, ev: KeyEvent) -> str | None:
    """이 소스의 배선에 이벤트 하나를 흘려 보낸다. 먹으면 라벨, 안 먹으면 None."""
    if _GUARD_USE.search(src) and (
        ev.target_tag.upper() in GUARD_TAGS or ev.target_tag.upper() == "CONTENTEDITABLE"
    ):
        return None
    if _MODIFIER_GUARD.search(src) and (ev.ctrl or ev.alt or ev.meta):
        return None
    if _COMPOSING_GUARD.search(src) and ev.is_composing:
        return None
    reader, labels = extract_dispatch(src)
    if reader is None:
        return None
    subject = ev.code if reader == "code" else ev.key
    return subject if subject in labels else None


def ime_event(code: str, *, target: str = "BODY", composing: bool = False) -> KeyEvent:
    """한글 입력기가 **켜진** 채 그 자리를 눌렀을 때 올라오는 것 (모형)."""
    return KeyEvent(code=code, key=KEY_WHEN_IME_ON.get(code, code),
                    target_tag=target, is_composing=composing)


def latin_event(code: str, *, target: str = "BODY") -> KeyEvent:
    """영문 자판 — 대조군."""
    return KeyEvent(code=code, key=KEY_WHEN_IME_OFF.get(code, code), target_tag=target)


def check_ime_replay(src: str) -> list[str]:
    """⑦ 한글 입력기 상태에서 단축키가 **실제로 먹는가** — 배선에 흘려 본다."""
    bad: list[str] = []
    reader, labels = extract_dispatch(src)
    if reader is None:
        # 못 푼 것을 통과로 세지 않는다 (exit 2 와 같은 뜻을 술어 안에서 낸다).
        return ["**판정 불가** — switch 가 무엇을 받는지 못 풀었다. 배선을 못 읽었으므로 "
                "이 술어는 아무것도 재지 못했다 (0건 검사와 검사 못 함은 다르다)"]
    if not labels:
        return ["**판정 불가** — case 라벨이 0건이다"]
    if reader == "key":
        # 머리부터 말한다. 아래 여덟 갈래를 다 세면 「라벨이 없다」로 보여서
        # **진짜 원인(글자로 고른다)** 이 목록에 묻힌다.
        bad.append(
            "★ 배선이 **글자(`event.key`)로 고른다** — 한글 입력기가 켜지는 순간 "
            "글자 단축키가 전부 죽는다. 자판의 **자리**(`event.code`)로 골라야 한다 (P-58)"
        )

    # ① 한글 입력기가 켜진 채 여덟 자리가 **다** 먹어야 한다.
    #
    # ★ 자리마다 두 세상을 함께 흘려 본다 — 영문 자판과 한글 입력기. 한쪽만 재면
    #   「배선이 아예 없다」와 「입력기에서만 죽는다」가 구별되지 않는다. 그 구별이
    #   이 절의 전부다: 앞엣것은 누구나 보고, 뒤엣것은 **아무도 재현하지 못한다.**
    dead: list[str] = []
    for code in ("KeyJ", "KeyK", "KeyM", "KeyR", "Enter", "Digit1", "Digit2", "Digit3"):
        latin = dispatch(src, latin_event(code))
        hangul = dispatch(src, ime_event(code))
        if latin is None:
            bad.append(f"{code} 를 고르는 자리가 아예 없다 — 단축키 안내와 배선이 어긋난다")
        elif hangul is None:
            dead.append(code)
    if dead:
        bad.append(
            "한글 입력기가 켜지면 죽는 자리 %d개: %s "
            "(영문 자판에서는 **전부 먹는다** — 그래서 아무도 재현하지 못한다)"
            % (len(dead), " · ".join(dead))
        )
    # ② 대조군 — 영문 자판에서는 언제나 잘 된다. 그래서 아무도 재현하지 못했다.
    if dispatch(src, latin_event("KeyJ")) is None:
        bad.append("영문 자판에서도 안 먹는다 — 이건 입력기 문제가 아니라 배선이 없는 것이다")
    # ③ 음성 — 입력칸 안에서는 먹으면 안 된다 (검색창에 j 를 칠 수 있어야 한다).
    if dispatch(src, ime_event("KeyJ", target="INPUT")) is not None:
        bad.append("입력칸 안에서도 먹는다 — 글자 하나가 화면을 스크롤한다")
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# ⑧⑨ **UX-16 이 부르는 셋 중 둘** — 지도 · 카메라 맥박 (턴 AA · 차선 A · P-219)
#
# 왜 이 둘인가 [턴 Y · 차선 N 이 `ga_readiness.yaml` UX-16 주석에 적은 사실]
#   그 절의 제목이 부르는 것은 **셋**(미처리 큐 · 지도 · 카메라 맥박)인데 술어는
#   ⑥(큐 배선) 하나뿐이었다. 지도 **0개** · 카메라 맥박 **0개**. 그래서 그 절은
#   「재는 잣대가 없는 채로」 색을 받고 있었다 — 안 잰 것과 된 것이 같은 칸에 있었다.
#
# ★★ **이 판정기는 브라우저를 열지 않는다.** 소스 배선을 읽는다. 그러므로 아래는
#   **(가) 소스로 지금 잴 수 있는 것**만 잰다. (나) 브라우저에서만 나는 답은 아래
#   `BROWSER_ONLY` 에 이름으로 적어 두고 **재지 않았다고 말한다** — (나)를 (가)인 척
#   적으면 이 절이 또 「분모 0인 초록」이 된다.
#
# ★ 이 화면은 **바깥 지도를 부르지 않는다**(열쇠 없음 · 좌표 산포다). 술어가 배경
#   지도 타일을 찾으면 영영 빨강이다 — **찾지 않는다.** 재는 것은 「좌표가 화면까지
#   왔는가」다.
# ═══════════════════════════════════════════════════════════════════════════
#: 재지 **못한** 것. 이름을 적어야 다음 사람이 무엇을 브라우저로 재야 하는지 안다.
BROWSER_ONLY = (
    "⑧ `svg[role=img][aria-label=위치]` 안의 `circle` 수가 화면이 적은 「위치를 아는 "
    "카드 N장」의 N 과 같은가 — 소스는 같아야 한다고 말할 뿐이고, 같은지는 못 잰다",
    "⑧ 좌표가 한 점뿐일 때 `spanLat`·`spanLng` 의 바닥값(0.01)이 점을 칸 밖으로 밀지 "
    "않는가 — 한 점짜리 밤이 실재하고, 그때 빈 칸은 「사건이 없다」와 구별되지 않는다",
    "⑨ 「카메라 상태」 칸의 줄 수가 `GET /api/dsm/cameras/pulse` 의 `rows` 수(상한 "
    "10줄)와 맞는가",
    "⑨ 응답에서 `alive === false` 인 행 수와 화면의 「응답 없음」 개수가 같은가 — "
    "상한을 넘으면 화면은 「그 밖 N대」로 말해야 한다(말없이 잘리면 죽은 카메라가 사라진다)",
)

#: 점을 찍기 전에 **좌표가 수이고 유한한지** 거르는 자리. 안 거르면 「위치를 아는
#: 카드」가 전체와 늘 같아지고, 그 순간 분모를 적는 문장이 참인 척하는 장식이 된다.
FINITE_GUARD = re.compile(r"Number\.isFinite\s*\(")

#: 분모를 화면이 **스스로 말하는** 자리. 사전 상수로 말해도, 글자로 말해도 인정한다 —
#: 재는 것은 「말하는 자리가 실재하는가」이지 어느 문법으로 말하는가가 아니다.
LOCATED_LINE = re.compile(r"WALL_COPY\.located|위치를\s*아는\s*카드")


def check_wall_map(src: str, copy_src=None) -> list[str]:
    """⑧ 월 모드의 **지도** — 칸이 실재하고 · 없음/못 가져옴을 가르고 · 분모를 말하고
    · 좌표를 거른다. **넷이 다 서야 ⑧ 이 선다.**
    """
    src = inline_copy_refs(src, copy_src)
    bad: list[str] = []
    if '"지도"' not in src and "'지도'" not in src:
        bad.append("「지도」 칸이 없다 — 제목이 부르는 셋 중 하나가 화면에 없다")
    if PLACEHOLDER in src:
        bad.append("자리표 글자가 그대로 남아 있다 — 이 절은 닫히지 않았다")
    empty = "지도에 표시할 위치가 없습니다."
    broken = "지도에 표시할 위치를 불러오지 못했습니다."
    if empty not in src:
        bad.append("위치가 **없다**고 말하는 자리가 없다")
    if broken not in src:
        bad.append("위치를 **못 가져왔다**고 말하는 자리가 없다")
    if empty in src and broken in src and empty == broken:
        bad.append("「없다」와 「못 가져왔다」가 같은 문장이다 — 못 가져온 밤에 "
                   "「위치가 없습니다」는 **「평온하다」로 읽힌다**")
    if not LOCATED_LINE.search(src):
        bad.append("분모를 화면이 스스로 말하지 않는다 — 「전체」만 적는 화면은 지도에 "
                   "안 뜬 카드를 **고장**으로 읽히게 한다")
    if not FINITE_GUARD.search(src):
        bad.append("점을 찍기 전에 좌표가 **수이고 유한한지** 거르는 자리가 없다 — "
                   "안 거르면 「위치를 아는 카드」가 전체와 늘 같아지고, 그 순간 분모를 "
                   "적는 문장이 참인 척하는 장식이 된다")
    return bad


def check_camera_pulse(src: str, copy_src=None) -> list[str]:
    """⑨ 월 모드의 **카메라 맥박** — 칸이 제 문을 부르고 · 혼자 실패를 말하고 ·
    세 상태를 세 문장으로 가르고 · 「못 알아들었다」를 「비었다」로 안 읽는다.
    """
    raw = src
    src = inline_copy_refs(src, copy_src)
    bad: list[str] = []
    if '"카메라 상태"' not in src and "'카메라 상태'" not in src:
        bad.append("「카메라 상태」 칸이 없다")
    for name in ("useCameraPulse", "CAMERA_PULSE_PATH"):
        if name not in raw:
            bad.append(f"그 칸이 제 문을 안 부른다 — {name} 이 없다 "
                       f"(훅만 있고 안 부르면 없는 것이다)")
    if "카메라 상태를 불러오지 못했습니다." not in src:
        bad.append("그 칸만 따로 실패를 말하는 자리가 없다")
    # ★ 세 상태를 **세 문장**으로. 둘이 같으면 밤새 죽어 있던 카메라가 새 카메라와
    #   같은 그림이 된다 — 「없다」와 「언제부터 없다」와 「한 번도 없었다」는 다른 사실이다.
    three = {"응답 없음": "죽은 카메라", "마지막 응답": "산 카메라",
             "아직 없음": "한 번도 안 온 카메라"}
    for word, who in three.items():
        if word not in src:
            bad.append(f"「{word}」({who})를 말하는 자리가 없다 — 세 상태가 세 문장으로 "
                       f"갈리지 않으면 죽은 카메라가 새 카메라와 같은 그림이 된다")
    # ★★ ⑨ 의 심장 — 응답은 왔는데 우리가 **못 읽는** 상태가 실재한다. 그때
    #   「표시할 항목이 없습니다」를 적으면 그것은 거짓이다.
    if not re.search(r"understood\s*===\s*false", src):
        bad.append("`understood === false` 를 **실패 갈래**로 보내는 자리가 없다 — "
                   "「못 알아들었다」를 「비었다」로 읽으면 화면이 거짓말을 한다")
    return bad


CHECKS = (
    ("① 키보드 · 입력창 갈래", "keys", check_keys),
    ("② 소리 — 심각만 · 묶음 1회", "alarm", check_sound),
    ("③ 월 모드 글자 24 이상", "wall", check_wall_font),
    ("④ 월 모드 자동 갱신 · 마지막 갱신", "wall", check_wall_refresh),
    ("⑤ 월 모드 실패를 말한다", "wall", check_wall_voice),
    ("⑥ 큐 화면 배선", "queue", check_wiring),
    ("⑦ 한글 IME 상태 재현 (P-58)", "keys", check_ime_replay),
    ("⑧ 월 모드 지도 (UX-16)", "wall", check_wall_map),
    ("⑨ 월 모드 카메라 맥박 (UX-16)", "wall", check_camera_pulse),
)


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성과 음성을 함께** 잰다. 한쪽만 재는 판정기는 초록으로 죽는다.
# ═══════════════════════════════════════════════════════════════════════════
GOOD_KEYS = """
window.addEventListener('keydown', (ev) => {
  if (isTypingTarget(ev.target)) return;
  // 자판의 자리를 먼저 본다 — 입력기와 무관하다 (출생 표본)
  switch (ev.code) { case 'KeyJ': onNext(); break; }
});
export function isTypingTarget(t) {
  const tag = t.tagName.toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
  if (t.isContentEditable) return true;
  return false;
}
"""
#: 음성 ① — 처리기는 있는데 **입력창 갈래가 없다**. 화면은 멀쩡하고 검색만 죽는다.
BAD_KEYS_NO_GUARD = """
window.addEventListener('keydown', (ev) => { move(ev.code); });
"""
#: 음성 ② — 갈래를 **정의만 하고 안 부른다**. 있는 것처럼 보이는 가장 흔한 모양이다.
BAD_KEYS_UNUSED = """
window.addEventListener('keydown', (ev) => { move(ev.code); });
export function isTypingTarget(t) {
  const tag = t.tagName.toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
  if (t.isContentEditable) return true;
  return false;
}
"""

GOOD_ALARM = """
const CRITICAL = 'critical';
const heard = new Set();
for (const card of cards) {
  if (card.severity !== CRITICAL) continue;
  const ids = [card.event_id, ...card.member_event_ids];
  if (!ids.some((id) => heard.has(id))) { play('newCritical'); }
}
"""
#: 음성 ③ — **등급 문지기가 없다**. 주의 한 건까지 밤새 운다.
BAD_ALARM_NO_GATE = """
const heard = new Set();
for (const card of cards) {
  const ids = [card.event_id, ...card.member_event_ids];
  if (!ids.some((id) => heard.has(id))) { play('newCritical'); }
}
"""
#: 음성 ④ — **묶음을 안 본다**. 카드 한 장에 소리 일곱 번.
BAD_ALARM_NO_FOLD = """
const CRITICAL = 'critical';
for (const card of cards) {
  if (card.severity !== CRITICAL) continue;
  play('newCritical');
}
"""

GOOD_WALL = """
const REFRESH_MS = 20_000;
const SHELL = { fontSize: 24 };
const TITLE = { fontSize: 40 };
setInterval(() => setNow(Date.now()), 5000);
<div>자동 갱신 중</div>
<div>마지막 갱신 12초 전</div>
<div>불러오지 못했습니다. 아래는 마지막으로 받은 내용입니다.</div>
<div>카메라 상태를 불러오지 못했습니다.</div>
"""

#: ★ 출생 표본 ⑤′ — 문장이 화면이 아니라 **사전**에 있고 화면은 이름으로 부른다 (턴 S).
GOOD_COPY_TS = """
export const WALL_COPY = {
  stale: '불러오지 못했습니다. 아래는 마지막으로 받은 내용입니다.',
  calm: '평온합니다.',
} as const;
export const CAMERA_COPY = {
  broken: '카메라 상태를 불러오지 못했습니다.',
} as const;
"""
GOOD_WALL_COPYREF = GOOD_WALL.replace(
    "<div>불러오지 못했습니다. 아래는 마지막으로 받은 내용입니다.</div>", "<div>{WALL_COPY.stale}</div>"
).replace("<div>카메라 상태를 불러오지 못했습니다.</div>", "<div>{CAMERA_COPY.broken}</div>")
#: 음성 ⑤′ — 사전에 **없는** 이름을 부른다. 풀리지 않으니 글자가 없고, 그래서 빨강이어야 한다.
BAD_WALL_COPYREF_MISSING = GOOD_WALL_COPYREF.replace("{WALL_COPY.stale}", "{WALL_COPY.nope}")
#: 음성 ⑤ — 24 미만이 **한 줄** 섞였다. 3m 밖에서 그 줄만 없다.
BAD_WALL_SMALL = GOOD_WALL + "\nconst NOTE = { fontSize: 12 };\n"
#: 음성 ⑥ — 크기 선언이 **아예 없다**. 라이브러리 기본값 14 가 그린다 — 통과가 아니다.
BAD_WALL_NO_FONT = """
const REFRESH_MS = 20_000;
setInterval(() => setNow(Date.now()), 5000);
<div>자동 갱신 중</div><div>마지막 갱신 12초 전</div>
"""
#: 음성 ⑦ — 갱신은 도는데 **시각을 안 적는다**. 얼어붙은 화면이 평온해 보인다.
BAD_WALL_SILENT = """
const REFRESH_MS = 20_000;
const SHELL = { fontSize: 24 };
setInterval(() => tick(), 5000);
<div>지금 처리할 것</div>
"""
#: 음성 ⑧ — 자리표가 그대로다. 경로만 살고 절은 안 닫혔다.
BAD_WALL_PLACEHOLDER = GOOD_WALL + f"\n<p>{PLACEHOLDER}</p>\n"

GOOD_QUEUE = """
useQueueKeys({ onNext });
useCriticalAlarm({ cards });
const sound = useAlertSound();
<Alert message="소리가 꺼져 있습니다" />
"""
#: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 코드다.
#:
#:   차선 C1 이 처음 짠 모양이고, **영문 자판에서는 완벽히 동작한다.**
#:   한글 입력기가 켜지는 순간 `ev.key` 가 `"ㅓ"` 로 와서 전부 죽는다.
#:   위 `check_keys` 의 마지막 갈래가 이것을 빨갛게 본다.
BAD_KEYS_IME_ONLY_KEY = """
useEffect(() => {
  const onKeyDown = (ev) => {
    if (isTypingTarget(ev.target)) return;
    switch (ev.key) {
      case 'j': onNext(); break;
      case 'k': onPrev(); break;
    }
  };
  window.addEventListener('keydown', onKeyDown);
}, []);
const isTypingTarget = (el) =>
  el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable;
"""

#: ★ ⑦의 양성 — 실제 배선과 같은 모양이다. 자리를 먼저 보고, 자리를 못 읽는 옛
#: 브라우저에서만 글자로 물러선다.
GOOD_IME_KEYS = """
function slotOf(ev) {
  const code = ev.code || '';
  if (code) return code;
  const key = (ev.key || '').toLowerCase();
  if (key === 'j') return 'KeyJ';
  return '';
}
const onKeyDown = (ev) => {
  if (isTypingTarget(ev.target)) return;
  if (ev.ctrlKey || ev.altKey || ev.metaKey) return;
  const slot = slotOf(ev);
  switch (slot) {
    case 'KeyJ': act.onNext(); break;
    case 'KeyK': act.onPrev(); break;
    case 'Enter': act.onOpen(); break;
    case 'KeyM': act.onToggleSound(); break;
    case 'KeyR': act.onReload(); break;
    case 'Digit1': case 'Numpad1': act.onStep(0); break;
    case 'Digit2': case 'Numpad2': act.onStep(1); break;
    case 'Digit3': case 'Numpad3': act.onStep(2); break;
  }
};
function isTypingTarget(t) {
  const tag = t.tagName.toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
  if (t.isContentEditable) return true;
  return false;
}
"""

#: ★★ **⑦이 있는 이유 그 자체** — 술어 ①은 이것을 **초록으로 본다.**
#:
#:   `ev.code` 를 읽기는 읽는다(로그로). 그런데 **고르는 것은 글자**다.
#:   ①은 「읽는가」를 묻고 ⑦은 「무엇으로 고르는가」를 묻는다 — 그 틈이 여기다.
#:   물리 키로 고쳤다고 보고된 코드가 이 모양으로 남아 있으면 관제실에서는
#:   여전히 j·k·m·r 이 죽고 1·2·3 만 산다. 「가끔 안 먹는다」의 정확한 모양이다.
BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY = """
window.addEventListener('keydown', onKeyDown);
const onKeyDown = (ev) => {
  if (isTypingTarget(ev.target)) return;
  const slot = ev.code;
  trace('key pressed', slot);
  switch (ev.key) {
    case 'j': act.onNext(); break;
    case 'k': act.onPrev(); break;
    case 'Enter': act.onOpen(); break;
    case 'm': act.onToggleSound(); break;
    case 'r': act.onReload(); break;
    case '1': act.onStep(0); break;
    case '2': act.onStep(1); break;
    case '3': act.onStep(2); break;
  }
};
function isTypingTarget(t) {
  const tag = t.tagName.toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true;
  if (t.isContentEditable) return true;
  return false;
}
"""

#: 음성 ⑨ — 훅은 만들었는데 화면이 **안 부른다**. 파일 수는 늘고 화면은 그대로다.
BAD_QUEUE_UNWIRED = """
<Alert message="소리가 꺼져 있습니다" />
"""


# ── ⑧⑨ 의 표본 (턴 AA · 차선 A) — **양성 하나에 음성 여럿.** 한쪽만 재면 초록으로 죽는다
GOOD_MAP = """
<Panel title="지도">
  const points = cards.filter((p) =>
    typeof p.lat === 'number' && Number.isFinite(p.lat) && Number.isFinite(p.lng));
  if (points.length === 0) {
    return <div>{broken ? '지도에 표시할 위치를 불러오지 못했습니다.'
                        : '지도에 표시할 위치가 없습니다.'}</div>;
  }
  <svg role="img" aria-label="위치">{points.map((p) => <circle />)}</svg>
  <div>위치를 아는 카드 {points.length}장 · 전체 {cards.length}장</div>
</Panel>
"""

#: 못 가져온 밤에 「위치가 없습니다」라고 적는 화면 — **「평온하다」로 읽힌다.**
BAD_MAP_ONE_SENTENCE = GOOD_MAP.replace(
    "{broken ? '지도에 표시할 위치를 불러오지 못했습니다.'\n                        : '지도에 표시할 위치가 없습니다.'}",
    "'지도에 표시할 위치가 없습니다.'")
BAD_MAP_NO_DENOMINATOR = GOOD_MAP.replace(
    "<div>위치를 아는 카드 {points.length}장 · 전체 {cards.length}장</div>",
    "<div>전체 {cards.length}장</div>")
BAD_MAP_NO_FINITE = GOOD_MAP.replace("Number.isFinite(p.lat) && Number.isFinite(p.lng)",
                                     "true")

GOOD_PULSE = """
import { CAMERA_PULSE_PATH, useCameraPulse } from '../hooks/useCameraPulse';
const pulse = useCameraPulse(REFRESH_MS, () => dsmGet(CAMERA_PULSE_PATH));
const pulseBroken = pulse.state === 'error' || (pulse.state === 'data' && pulse.data?.understood === false);
<Panel title="카메라 상태">
  {pulseBroken ? <div>{CAMERA_COPY.broken}</div> : null}
  {row.alive === false ? '응답 없음' : null}
  {row.alive !== false && row.lastSeenAt ? `마지막 응답 ${line}` : null}
  {row.alive !== false && !row.lastSeenAt ? '아직 없음' : null}
  {!pulseBroken && pulseRows.length === 0 ? <div>표시할 항목이 없습니다.</div> : null}
</Panel>
"""

#: ★★ ⑨ 의 심장 — 응답은 왔는데 **우리가 못 읽는** 상태를 빈 갈래로 보낸다.
#:   그러면 화면이 「표시할 항목이 없습니다」라고 **거짓말**을 한다.
BAD_PULSE_UNDERSTOOD_AS_EMPTY = GOOD_PULSE.replace(
    "|| (pulse.state === 'data' && pulse.data?.understood === false)", "")
BAD_PULSE_TWO_SENTENCES = GOOD_PULSE.replace(
    "{row.alive !== false && !row.lastSeenAt ? '아직 없음' : null}",
    "{row.alive !== false && !row.lastSeenAt ? '응답 없음' : null}")
BAD_PULSE_NO_DOOR = GOOD_PULSE.replace("CAMERA_PULSE_PATH", "SOME_OTHER_PATH")


def self_test() -> int:
    fails = 0
    positives = (
        ("① 좋은 키 처리기", check_keys, GOOD_KEYS),
        ("② 좋은 소리 갈래", check_sound, GOOD_ALARM),
        ("③ 좋은 월 모드 글자", check_wall_font, GOOD_WALL),
        ("④ 좋은 월 모드 갱신", check_wall_refresh, GOOD_WALL),
        ("⑤ 좋은 월 모드 실패 문장", check_wall_voice, GOOD_WALL),
        ("⑤′ 상수로 말하는 월 모드 (사전을 풀어 읽는다)",
         lambda s: check_wall_voice(s, copy_src=GOOD_COPY_TS), GOOD_WALL_COPYREF),
        ("⑥ 좋은 큐 배선", check_wiring, GOOD_QUEUE),
        ("⑦ 자리로 고르는 배선 — IME 재현", check_ime_replay, GOOD_IME_KEYS),
        ("⑧ 좋은 지도 칸 (UX-16)", check_wall_map, GOOD_MAP),
        ("⑨ 좋은 카메라 맥박 칸 (UX-16)", check_camera_pulse, GOOD_PULSE),
    )
    for name, fn, src in positives:
        bad = fn(src)
        if bad:
            print(f"[WALL] 자기시험 FAIL 양성 {name} 을 빨갛게 봤다: {bad}")
            fails += 1

    negatives = (
        ("⑤′ 사전에 없는 이름을 부른다", lambda s: check_wall_voice(s, copy_src=GOOD_COPY_TS), BAD_WALL_COPYREF_MISSING),
        ("입력창 갈래 없음", check_keys, BAD_KEYS_NO_GUARD),
        ("입력창 갈래 안 불림", check_keys, BAD_KEYS_UNUSED),
        ("등급 문지기 없음", check_sound, BAD_ALARM_NO_GATE),
        ("묶음 안 접음", check_sound, BAD_ALARM_NO_FOLD),
        ("24 미만 글자 섞임", check_wall_font, BAD_WALL_SMALL),
        ("글자 선언 0건", check_wall_font, BAD_WALL_NO_FONT),
        ("갱신 시각 안 적음", check_wall_refresh, BAD_WALL_SILENT),
        ("자리표 남음", check_wall_voice, BAD_WALL_PLACEHOLDER),
        ("화면이 훅을 안 부름", check_wiring, BAD_QUEUE_UNWIRED),
        ("★ 출생 표본 — 글자만 보고 자리를 안 봄(한글 입력기)", check_keys, BAD_KEYS_IME_ONLY_KEY),
        ("★ 출생 표본 — IME 재현으로 다시 잰다", check_ime_replay, BAD_KEYS_IME_ONLY_KEY),
        ("★★ 자리를 읽지만 **글자로 고른다** — ①이 못 보는 자리",
         check_ime_replay, BAD_KEYS_READS_CODE_BUT_SWITCHES_ON_KEY),
        ("★ ⑧ 「없다」와 「못 가져왔다」가 한 문장 — 못 가져온 밤이 평온해 보인다",
         check_wall_map, BAD_MAP_ONE_SENTENCE),
        ("★ ⑧ 분모를 안 말한다 — 안 뜬 카드가 고장으로 읽힌다",
         check_wall_map, BAD_MAP_NO_DENOMINATOR),
        ("★ ⑧ 좌표를 안 거른다 — 「위치를 아는 카드」가 전체와 늘 같아진다",
         check_wall_map, BAD_MAP_NO_FINITE),
        ("★★ ⑨ `understood === false` 를 **빈 갈래**로 보낸다 — 못 알아들은 것을 "
         "「비었다」로 적는다", check_camera_pulse, BAD_PULSE_UNDERSTOOD_AS_EMPTY),
        ("★ ⑨ 세 상태가 두 문장으로 뭉쳤다 — 죽은 카메라가 새 카메라와 같은 그림",
         check_camera_pulse, BAD_PULSE_TWO_SENTENCES),
        ("★ ⑨ 훅 이름만 있고 문을 안 부른다", check_camera_pulse, BAD_PULSE_NO_DOOR),
    )
    for name, fn, src in negatives:
        if not fn(src):
            print(f"[WALL] 자기시험 FAIL 음성 {name} 을 초록으로 봤다")
            fails += 1

    # 음성 ⑩ — 주석에 적어 둔 것은 **한 것이 아니다.**
    pledge = "// 여기서 isTypingTarget(ev.target) 로 INPUT TEXTAREA isContentEditable 을 거른다\n"
    if not check_keys(strip_comments(pledge)):
        print("[WALL] 자기시험 FAIL 주석에 적은 다짐을 통과로 봤다")
        fails += 1

    if fails:
        print(f"[WALL] 자기시험 {fails}건 실패")
        return 1
    print(f"[WALL] 자기시험 통과 — 양성 {len(positives)} · 음성 {len(negatives) + 1}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="UX-15 키보드·소리 · UX-16 월 모드 판정기")
    ap.add_argument("--list", action="store_true", help="걸린 자리 전수")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # ── 못 잰 것을 통과로 세지 않는다: 파일이 하나라도 없으면 **판정 불가** ──
    sources: dict[str, str] = {}
    missing: list[str] = []
    for name, rel in TARGETS.items():
        path = ROOT / rel
        try:
            sources[name] = strip_comments(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            missing.append(rel)
    if missing:
        print("[WALL] **판정 불가** — 볼 파일을 못 읽었다 (0건 검사와 검사 못 함은 다르다)")
        for rel in missing:
            print(f"          없음: {rel}")
        return 2

    print(f"[WALL] [입력] 파일 {len(sources)}개 (주석 걷어낸 뒤) · 술어 {len(CHECKS)}종")

    failed = 0
    for label, key, fn in CHECKS:
        bad = fn(sources[key])
        if bad:
            failed += 1
            print(f"[WALL] FAIL {label}  ({TARGETS[key]})")
            for line in bad:
                print(f"          - {line}")
        else:
            print(f"[WALL] PASS {label}")
            if args.list:
                print(f"          {TARGETS[key]}")

    if failed:
        print(f"[WALL] FAIL 술어 {failed}/{len(CHECKS)}종이 빨갛다")
        return 1
    print(f"[WALL] 통과 — 술어 {len(CHECKS)}/{len(CHECKS)}종")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("벽 화면의 열쇠 다루기 — 술어 **분모 %d종**을 대상 파일 전수에 건다(주석은 걷어낸다)"
               % len(CHECKS)),
    )
    raise SystemExit(main())
