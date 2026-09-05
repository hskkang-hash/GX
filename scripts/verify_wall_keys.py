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
GUARD_USE = re.compile(r"if\s*\([^;{}]*\.target[^;{}]*\)\s*\{?\s*return")
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


def check_wall_voice(src: str) -> list[str]:
    """⑤ 갱신이 실패했을 때 월 모드가 **그 사실을 말한다** (칸마다 따로).

    ★ 사전 밖 낱말은 여기서 재지 않는다 — `verify_ui_copy.py` 의 자리다.
      여기서 재는 것은 「말하는 자리가 실재하는가」 하나다.
    """
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


CHECKS = (
    ("① 키보드 · 입력창 갈래", "keys", check_keys),
    ("② 소리 — 심각만 · 묶음 1회", "alarm", check_sound),
    ("③ 월 모드 글자 24 이상", "wall", check_wall_font),
    ("④ 월 모드 자동 갱신 · 마지막 갱신", "wall", check_wall_refresh),
    ("⑤ 월 모드 실패를 말한다", "wall", check_wall_voice),
    ("⑥ 큐 화면 배선", "queue", check_wiring),
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

#: 음성 ⑨ — 훅은 만들었는데 화면이 **안 부른다**. 파일 수는 늘고 화면은 그대로다.
BAD_QUEUE_UNWIRED = """
<Alert message="소리가 꺼져 있습니다" />
"""


def self_test() -> int:
    fails = 0
    positives = (
        ("① 좋은 키 처리기", check_keys, GOOD_KEYS),
        ("② 좋은 소리 갈래", check_sound, GOOD_ALARM),
        ("③ 좋은 월 모드 글자", check_wall_font, GOOD_WALL),
        ("④ 좋은 월 모드 갱신", check_wall_refresh, GOOD_WALL),
        ("⑤ 좋은 월 모드 실패 문장", check_wall_voice, GOOD_WALL),
        ("⑥ 좋은 큐 배선", check_wiring, GOOD_QUEUE),
    )
    for name, fn, src in positives:
        bad = fn(src)
        if bad:
            print(f"[WALL] 자기시험 FAIL 양성 {name} 을 빨갛게 봤다: {bad}")
            fails += 1

    negatives = (
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
    raise SystemExit(main())
