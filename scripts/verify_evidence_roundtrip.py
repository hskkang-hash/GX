#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-189 — **증거 JSON 을 다시 읽어도 같은 수가 나오는가** (2026-09-19 · 턴 W · 차선 Q).

    「썼다」는 초록이 아니다. **「다시 읽으니 같더라」가 초록이다.**

무엇을 막는가 — **깨진 증거는 파싱 오류를 내지 않는다. 수만 틀린다.**
------------------------------------------------------------------
증거가 깨지는 모양이 하나 있다. 한글이 든 JSON 을 cp949 로 흘려 보내고 utf-8 로
읽으면(또는 그 반대로) 글자가 뭉개진다. 그런데 **JSON 은 그대로 파싱된다** — 따옴표와
중괄호는 아스키라 멀쩡하기 때문이다. 그래서 판정기는 **죽지 않고**, 초록을 내고,
수를 말한다. 다만 그 수가 틀렸다.

[실측 2026-09-19 · 턴 W] 지금 살아 있는 FC 증거(`P-118/click_completes.json`)의
한글만 cp949 왕복으로 깨뜨려 **같은 판정기**에 먹였다:

    성한 증거   29/48   (빨강 4 · 회색 15)
    깨진 증거    8/48   (빨강 25 · 회색 15)   ← 초록 **21개**가 빨강으로 내려앉는다
    ↑ 어느 쪽도 예외를 내지 않는다. 둘 다 「판정 끝」이라고 말한다.

깨지는 자리는 네 칸 중 ④ **화면 문구**다. `_cell_text` 가 「대시보드」를 찾는데
증거에는 「���」가 적혀 있으니 못 찾는다. 사람이 보면 한눈에 아는 것을 도구는 모른다.

★ 왜 「재읽기」가 술어인가 — 「썼다」로는 아무것도 안 걸린다
----------------------------------------------------------
쓰는 자리에 `encoding="utf-8"` 을 적는 것만으로는 이 사고가 안 잡힌다. 깨지는 것은
**쓸 때가 아니라 읽어 들일 때**이고(`decode("utf-8", "replace")`), 그 뒤에 쓰는
쪽은 이미 깨진 글자를 **성실하게 utf-8 로** 적는다. 그러므로 술어는 하나뿐이다 —
**같은 파일을 다시 읽어 같은 수가 나오는가.**

★ 「낡아서 0」과 「깨져서 0」은 다르다 — 이 게이트가 **이름으로** 가른다
----------------------------------------------------------------------
[실측 2026-09-19 · 턴 W] 턴 U 가 보고한 `FC 28/48` 이 재현되지 않는다는 말이 있었다.
저장소에 남은 턴 U 증거(커밋 `7f90ec5`)를 **나이를 무시하고** 다시 재 보았다:

    턴 U 증거 → **28/48** (빨강 2 · 회색 18) · `measured_at=2026-09-18T05:45:10Z`

그대로 재현된다. 한글도 성하다(U+FFFD **0개** · 한글 13,313자). 즉 **그 파일은
깨지지 않았다.** 재현이 안 됐던 이유는 인코딩이 아니라
`verify_click_completes.py` 의 `MAX_AGE_HOURS = 12` 다 —
`rows = judge(obs if not stale else {})` 라, 12시간이 지난 증거는 **관측이 빈 것으로**
판정돼 `0/48` 이 된다. 그것은 고장이 아니라 **신선도 규율**이다.

그래서 이 게이트는 나이를 무시하고 센다. 그 수가 「지금 이 파일에 적힌 관측으로 낼 수
있는 수」이고, 살아 있는 판정기가 그보다 낮은 수를 말하면 그것은 **「못 잼」이지
「0점」이 아니다.** 다음 사람이 그 0 을 결함으로 읽지 않도록 이 게이트가 적는다.

무엇을 보는가 — 증거 한 종마다 **세 칸**
----------------------------------------
  ① **엄격 utf-8**   `errors` 없이 디코드된다 · U+FFFD 0개 · 한글이 실재한다
  ② **재읽기 = 같은 수**   읽어서 센 수 → 도구가 쓰는 그 방식으로 다시 써서 → 다시 읽어
                           센 수. 두 수가 다르면 그 증거는 증거가 아니다
  ③ **적힌 수 = 다시 센 수**   파일이 제 수를 적어 두었으면 행에서 **다시 세어** 댄다
                               (손으로 고친 수·낡은 수가 여기서 걸린다)

무엇을 재지 **않는가**
----------------------
· 그 수가 **좋은 수인지** — 이 게이트는 점수를 모른다. 같은지만 본다.
· 증거가 **신선한지** — 그것은 각 판정기의 `MAX_AGE_HOURS` 가 할 일이다.
· 증거가 **옳은지** — 깨지지 않았다고 맞는 것은 아니다.

쓰는 법
-------
    python scripts/verify_evidence_roundtrip.py              # 판정
    python scripts/verify_evidence_roundtrip.py --list       # 증거 종별 셈법
    python scripts/verify_evidence_roundtrip.py --self-test  # 규칙만 (증거 없이)

종료 코드: 0 성립 · 1 빨강(수가 달라졌다·깨졌다) · 2 회색(잴 증거가 없다)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "docs" / "agent" / "evidence"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[P-189]"
EXIT_OK, EXIT_RED, EXIT_GRAY = 0, 1, 2

_HANGUL = re.compile(r"[가-힣]")


# ──────────────────────────────────────────────────────────────────────────
# 깨뜨리는 법 — **음성 대조의 본체**
# ──────────────────────────────────────────────────────────────────────────
def corrupt_cp949(text: str) -> str:
    """증거가 실제로 깨지는 그 경로. cp949 로 흘러나온 바이트를 utf-8 로 읽는다.

    ★ 이 함수는 **증거를 쓰지 않는다.** 메모리 안에서만 깨뜨려 판정기에 먹인다 —
      저장소의 증거 파일은 건드리지 않는다(깨진 것은 깨진 대로 두고 이름을 적는 쪽이
      정직하다 · 세종 턴 W ㉠).
    """
    return text.encode("cp949", "replace").decode("utf-8", "replace")


# ──────────────────────────────────────────────────────────────────────────
# 셈법 — 증거 한 종마다 **하나**. 세는 법을 두 벌 두지 않는다.
# ──────────────────────────────────────────────────────────────────────────
def count_click_completes(doc: dict) -> dict:
    """FC(P-118) — 판정은 `verify_click_completes.judge` 에게 맡긴다.

    ★ 여기서 세는 법을 새로 쓰지 않는다. 두 벌을 두면 반드시 어긋나고,
      어긋나면 **조용한 쪽이 이긴다**(D-369).
    ★ 나이를 무시한다 — 위 머리말의 「낡아서 0」 절.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import verify_click_completes as VCC      # noqa: E402
    g, r, y = VCC.score(VCC.judge(doc.get("observations") or {}))
    return {"초록": g, "빨강": r, "회색": y}


def count_onboarding(doc: dict) -> dict:
    rows = doc.get("rows") or []
    c = Counter(r.get("verdict") for r in rows)
    return {"점수합": round(sum(float(r.get("score") or 0) for r in rows), 3),
            "초록": c.get("green", 0), "반": c.get("half", 0),
            "빨강": c.get("red", 0), "회색": c.get("gray", 0)}


def count_feature_reach(doc: dict) -> dict:
    c = Counter(r.get("color") for r in doc.get("rows") or [])
    return {"절": len(doc.get("rows") or []), "초록": c.get("초록", 0),
            "빨강": c.get("빨강", 0), "회색": c.get("회색", 0), "잠김": c.get("잠김", 0)}


def count_walk(doc: dict) -> dict:
    """걷기 대장. ★ [턴 W · ㉣] **안 걸은 것과 세션을 같이 센다.**

    두 수가 여기 있어야 하는 이유: 누가 `NOT_WALKED` 에서 W4 를 지우거나 세션 셈을
    떨어뜨리면 **수가 변하고**, 그러면 이 게이트의 「다시 읽어도 같은 수」가 그것을
    이름으로 말한다. 목록에서 조용히 사라지는 빈자리를 만들지 않는다(D-264).
    """
    runs = doc.get("runs") or []
    ledger = doc.get("ledger") or {}
    last = runs[-1] if isinstance(runs[-1] if runs else None, dict) else {}
    left = sum(1 for r in runs
               if isinstance(r, dict) and r.get("session_closed") is False)
    return {"회차": len(runs), "대장항목": len(ledger),
            "안 걸음": len(last.get("not_walked") or {}),
            "세션 열린 채 끝난 회차": left}


def walk_not_walked(doc: dict) -> dict:
    """마지막 회차가 **안 걷기로 한 것**과 그 사유. 사유 없는 이름은 면제다."""
    runs = doc.get("runs") or []
    return (runs[-1] if runs else {}).get("not_walked") or {}


# ── 적힌 수 ↔ 다시 센 수 대조표. 왼쪽이 파일에 적힌 칸, 오른쪽이 위 셈법의 칸. ──
RECORDED_ONBOARDING = {"green": "초록", "half": "반", "red": "빨강",
                       "gray_measured_fail": "회색"}
RECORDED_REACH = {"n": "절", "구현": "초록", "빨강": "빨강",
                  "미측정": "회색", "잠김": "잠김"}


class Spec:
    def __init__(self, key, path, label, count, recorded=None, indent=2):
        self.key, self.path, self.label = key, path, label
        self.count, self.recorded, self.indent = count, recorded or {}, indent


def latest(dirname: str, pattern: str):
    d = EV / dirname
    if not d.is_dir():
        return None
    got = sorted(d.glob(pattern))
    return got[-1] if got else None


def specs() -> list:
    """이 게이트가 지키는 증거. **여기에 없는 증거는 안 지켜진다** — 늘리는 것이 일이다."""
    out = [
        Spec("fc", EV / "P-118" / "click_completes.json",
             "FC 「누른 뒤」 48행 (P-118)", count_click_completes),
        Spec("reach", EV / "P-106" / "feature_reach.json",
             "영역 ① 기능 도달 39절 (P-106)", count_feature_reach,
             RECORDED_REACH, indent=1),
        Spec("walk", EV / "UX-WALK" / "walk.json",
             "걷기 대장 (UX-WALK)", count_walk),
    ]
    ob = latest("P-159", "onboarding_measure_*.json")
    if ob:
        out.insert(1, Spec("onboarding", ob,
                           "온보딩 48행 실측 (P-159 · 최신 회차)",
                           count_onboarding, RECORDED_ONBOARDING))
    return out


# ──────────────────────────────────────────────────────────────────────────
# 세 칸
# ──────────────────────────────────────────────────────────────────────────
def cell_utf8(raw: bytes) -> tuple:
    """① 엄격 utf-8 · U+FFFD 0 · 한글 실재."""
    try:
        text = raw.decode("utf-8")           # errors 없음 — 무르게 읽지 않는다
    except UnicodeDecodeError as exc:
        return False, "utf-8 로 못 읽는다: %s" % exc, ""
    n_bad = text.count("�")
    if n_bad:
        return False, ("U+FFFD 가 %d개 — 이미 한 번 무르게 읽힌 글자다. "
                       "이 파일로 잰 수는 틀린 수다" % n_bad), text
    n_ko = len(_HANGUL.findall(text))
    if n_ko == 0:
        return False, "한글이 한 자도 없다 — 이 저장소의 증거는 한글로 적힌다. 깨졌거나 빈 파일이다", text
    return True, "엄격 utf-8 · U+FFFD 0 · 한글 %d자" % n_ko, text


def cell_reread(text: str, count, indent: int) -> tuple:
    """② 읽어서 센 수 == 다시 써서 다시 읽어 센 수."""
    try:
        doc1 = json.loads(text)
    except ValueError as exc:
        return False, "JSON 이 아니다: %s" % exc, None
    n1 = count(doc1)
    # 도구가 쓰는 그 방식 그대로 — `ensure_ascii=False` + utf-8 바이트
    again = json.dumps(doc1, ensure_ascii=False, indent=indent).encode("utf-8")
    ok, why, text2 = cell_utf8(again)
    if not ok:
        return False, "다시 쓴 판이 utf-8 을 못 지킨다 — %s" % why, n1
    n2 = count(json.loads(text2))
    if n1 != n2:
        return False, "다시 읽으니 수가 다르다: %s → %s" % (n1, n2), n1
    return True, "다시 읽어도 %s" % n1, n1


def cell_recorded(doc: dict, got: dict, table: dict) -> tuple:
    """③ 파일이 적어 둔 수 == 행에서 다시 센 수."""
    if not table:
        return None, "이 증거는 제 수를 적지 않는다 — 셋째 칸은 잴 것이 없다"
    bad = []
    for field, cell in table.items():
        if field not in doc:
            bad.append("적힌 칸 `%s` 가 없다" % field)
            continue
        if doc[field] != got.get(cell):
            bad.append("`%s` 적힘 %r ≠ 다시 셈 %r" % (field, doc[field], got.get(cell)))
    if bad:
        return False, " · ".join(bad)
    return True, "적힌 %d칸이 다시 센 수와 같다" % len(table)


def run(only: str = "") -> int:
    rows, n_read = [], 0
    for s in specs():
        if only and s.key != only:
            continue
        if not Path(s.path).is_file():
            rows.append((s, None, "회색", "증거가 없다 (%s)" % Path(s.path).name, None))
            continue
        n_read += 1
        raw = Path(s.path).read_bytes()
        ok1, why1, text = cell_utf8(raw)
        if not ok1:
            rows.append((s, None, "빨강", "① %s" % why1, None))
            continue
        ok2, why2, n = cell_reread(text, s.count, s.indent)
        if not ok2:
            rows.append((s, n, "빨강", "② %s" % why2, None))
            continue
        ok3, why3 = cell_recorded(json.loads(text), n, s.recorded)
        color = "초록" if ok3 is not False else "빨강"
        rows.append((s, n, color, "① %s · ② %s · ③ %s" % (why1, why2, why3), ok3))

    print("%s 증거 파일 %d개 읽음 (선언 %d종)" % (TAG, n_read, len(specs())))
    print("%s 술어: ① 엄격 utf-8(errors 없음) · ② **다시 읽어도 같은 수** · "
          "③ 적힌 수 = 행에서 다시 센 수" % TAG)
    for s, n, color, why, _ in rows:
        print("  %s %-34s %s" % ({"초록": "O", "빨강": "X", "회색": "?"}[color],
                                 s.label, why))
        if n is not None:
            print("       %s 수: %s   [%s]" % (TAG, n, Path(s.path).relative_to(ROOT)))

    #: ★★ [턴 W · ㉣ · 차선 Q] **「안 걸었다」와 「걸었는데 괜찮다」는 다르다.**
    #:   걷기 대장이 안 걷기로 한 것을 **게이트 출력에 이름과 사유로** 올린다.
    #:   이 줄이 없으면 다음 사람은 그 빈자리를 초록으로 읽는다 — 그리고 그 자리를
    #:   다시 묻지 않는다. 사유가 비면 그것은 분류가 아니라 **면제**이고 빨강이다.
    wpath = EV / "UX-WALK" / "walk.json"
    if wpath.is_file():
        try:
            wdoc = json.loads(wpath.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            wdoc = {}
        nw = walk_not_walked(wdoc)
        if not nw:
            print("%s [안 걸음] 걷기 대장의 마지막 회차는 **안 걷기로 한 것이 없다**" % TAG)
        else:
            print("%s [안 걸음] %d건 — **초록이 아니다. 안 걸은 것이다**:" % (TAG, len(nw)))
            for k, why in sorted(nw.items()):
                print("       %-4s %s" % (k, why or "★ **사유가 없다**"))
            blank = sorted(k for k, v in nw.items() if not v)
            if blank:
                rows.append((Spec("walk-notwalked", wpath, "걷기 · 안 걸음 사유", count_walk),
                             None, "빨강",
                             "사유 없이 안 걷기로 한 것 %s — 사유 없는 제외는 **면제**이고, "
                             "면제는 분류가 아니다 (D-264)" % blank, None))
        last = (wdoc.get("runs") or [{}])[-1]
        if last.get("session_closed") is False:
            print("%s [세션] 마지막 걷기 회차(%s)가 **세션을 열어 둔 채 끝났다** — "
                  "이 환경은 동시 접속 1개다. 다음 사람이 튕긴다 (턴 W ㉢)"
                  % (TAG, last.get("when")))

    red = [r for r in rows if r[2] == "빨강"]
    grey = [r for r in rows if r[2] == "회색"]
    if red:
        print("%s 빨강 %d — **다시 읽으니 같지 않다.** 그 증거로 잰 수는 수가 아니다"
              % (TAG, len(red)))
        return EXIT_RED
    if n_read == 0:
        print("%s 회색 — 읽을 증거가 하나도 없다. 0건 검사는 통과가 아니다 (D-301)" % TAG)
        return EXIT_GRAY
    if grey:
        print("%s 회색 %d — 그 증거는 아직 안 잼(없다). 나머지 %d종은 다시 읽어 같았다"
              % (TAG, len(grey), n_read))
        return EXIT_GRAY
    print("%s 초록 %d종 — 증거를 다시 읽어도 같은 수가 나온다" % (TAG, n_read))
    return EXIT_OK


# ──────────────────────────────────────────────────────────────────────────
def self_test() -> int:
    bad = 0

    #: ★★ **출생 표본** (D-310) — 이 게이트를 만들게 한 **바로 그 모양**
    #:   [실측 2026-09-19 · 턴 W · 차선 Q]. 살아 있는 FC 증거를 cp949 왕복으로
    #:   깨뜨렸더니 같은 판정기가 **29/48 → 8/48** 을 냈다. 예외는 나지 않았고,
    #:   깨진 쪽도 「판정 끝」이라고 말했다. 아래 표본은 그 증거에서 뽑은 두 행을
    #:   같은 모양으로 줄인 것이다 — 성한 판은 **초록 2**, 깨진 판은 **초록 0** 이어야 한다.
    #:   여기서 두 수가 같게 나오면 이 게이트는 눈이 먼 것이고, 그러면 P-189 는
    #:   「썼다」만 남고 검사는 없는 상태로 돌아간다.
    BIRTH_SAMPLE = {
        "observations": {
            "U1#2": {
                "control": {"found": True, "clicked": True, "name": "화면 열기"},
                "calls": [{"method": "GET",
                           "url": "http://localhost:8000/api/dsm/dashboard/frame",
                           "status": 200}],
                "state": {"kind": "server_reflect", "field": "panel_total",
                          "after": 2, "on_screen": True},
                "text_after": "전체 상황판 · 대시보드 · 칸이 정상적으로 그려졌습니다",
            },
            "U1#3": {
                "control": {"found": True, "clicked": True, "name": "카메라 상태"},
                "calls": [{"method": "GET",
                           "url": "http://localhost:8000/api/dsm/cameras/pulse",
                           "status": 200}],
                "state": {"kind": "server_reflect", "field": "total",
                          "after": 6, "on_screen": True},
                "text_after": "카메라 전체 6대 · 응답 없음 0대",
            },
        },
    }
    good_text = json.dumps(BIRTH_SAMPLE, ensure_ascii=False, indent=2)
    n_good = count_click_completes(json.loads(good_text))
    broken_text = corrupt_cp949(good_text)
    n_broken = count_click_completes(json.loads(broken_text))
    ok = n_good["초록"] == 2 and n_broken["초록"] == 0
    bad += 0 if ok else 1
    print("  %s ★ 출생 표본 — 깨진 증거는 **파싱되고 수만 틀린다** "
          "(성한 판 초록 %d → 깨진 판 초록 %d)"
          % ("O" if ok else "X", n_good["초록"], n_broken["초록"]))

    # ① 깨진 글자를 ①칸이 잡는가
    ok1, why1, _ = cell_utf8(broken_text.encode("utf-8"))
    ok = (ok1 is False) and "U+FFFD" in why1
    bad += 0 if ok else 1
    print("  %s ① U+FFFD 가 섞인 증거는 빨강 (%s)" % ("O" if ok else "X", why1[:40]))

    # ① utf-8 이 아닌 바이트
    ok1b, why1b, _ = cell_utf8("깨짐".encode("cp949"))
    ok = ok1b is False
    bad += 0 if ok else 1
    print("  %s ① utf-8 로 못 읽는 바이트는 빨강" % ("O" if ok else "X"))

    # ① 한글이 없는 증거 — 다 깎여 나간 파일을 초록으로 주지 않는다
    ok1c, _, _ = cell_utf8(b'{"rows": []}')
    ok = ok1c is False
    bad += 0 if ok else 1
    print("  %s ① 한글이 한 자도 없는 증거는 초록이 아니다" % ("O" if ok else "X"))

    # ① 성한 증거는 통과
    ok1d, _, _ = cell_utf8(good_text.encode("utf-8"))
    bad += 0 if ok1d else 1
    print("  %s ① 성한 증거는 ①칸을 지난다" % ("O" if ok1d else "X"))

    # ② 왕복해도 같은 수
    ok2, why2, n2 = cell_reread(good_text, count_click_completes, 2)
    ok = ok2 and n2["초록"] == 2
    bad += 0 if ok else 1
    print("  %s ② 다시 써서 다시 읽어도 같은 수 (%s)" % ("O" if ok else "X", n2))

    # ② 세는 법이 실제로 민감한가 — 한 행을 빼면 수가 달라져야 한다
    less = json.loads(good_text)
    less["observations"].pop("U1#3")
    ok = count_click_completes(less)["초록"] == 1
    bad += 0 if ok else 1
    print("  %s ② 행을 하나 빼면 수가 달라진다 — 셈이 눈을 뜨고 있다" % ("O" if ok else "X"))

    # ③ 적힌 수를 손으로 고치면 잡히는가
    doc = {"rows": [{"verdict": "green", "score": 1.0},
                    {"verdict": "red", "score": 0.0}],
           "green": 1, "half": 0, "red": 1, "gray_measured_fail": 0}
    ok3, _ = cell_recorded(doc, count_onboarding(doc), RECORDED_ONBOARDING)
    bad += 0 if ok3 else 1
    print("  %s ③ 적힌 수가 맞으면 초록" % ("O" if ok3 else "X"))
    doc_bad = dict(doc, green=2)
    ok3b, why3b = cell_recorded(doc_bad, count_onboarding(doc_bad), RECORDED_ONBOARDING)
    ok = ok3b is False
    bad += 0 if ok else 1
    print("  %s ③ 적힌 수를 손으로 +1 하면 빨강 (%s)" % ("O" if ok else "X", why3b[:44]))

    # ③ 적을 수가 없는 증거는 빨강이 아니라 「잴 것이 없음」
    ok3c, _ = cell_recorded({}, {}, {})
    ok = ok3c is None
    bad += 0 if ok else 1
    print("  %s ③ 제 수를 안 적는 증거를 빨강으로 몰지 않는다" % ("O" if ok else "X"))

    # 셈법 셋이 다 살아 있는가 (이름만 있고 안 도는 셈을 막는다)
    ok = (count_feature_reach({"rows": [{"color": "초록"}, {"color": "잠김"}]})
          == {"절": 2, "초록": 1, "빨강": 0, "회색": 0, "잠김": 1}
          and count_walk({"runs": [{"session_closed": True},
                                   {"session_closed": False,
                                    "not_walked": {"W4": "부하용 혼합 시나리오"}}],
                           "ledger": {"a": 1}})
          == {"회차": 2, "대장항목": 1, "안 걸음": 1, "세션 열린 채 끝난 회차": 1})
    bad += 0 if ok else 1
    print("  %s 셈법 넷이 다 돈다 (FC · 온보딩 · 도달 · 걷기)" % ("O" if ok else "X"))

    print("%s 자기시험 %s" % (TAG, "전부 통과" if bad == 0 else "%d개 어긋남" % bad))
    return EXIT_OK if bad == 0 else EXIT_RED


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", default="", help="증거 한 종만 (fc · onboarding · reach · walk)")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.list:
        for s in specs():
            print("%-11s %-36s 적힌 수 대조 %s\n            %s"
                  % (s.key, s.label,
                     ", ".join(s.recorded) or "(없음 — 파일이 제 수를 안 적는다)",
                     Path(s.path).relative_to(ROOT) if Path(s.path).is_absolute() else s.path))
        return EXIT_OK
    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 깨졌다 — 재지 않는다" % TAG)
        return rc
    print("")
    return run(a.only)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header

    gate_header(
        __file__,
        measured=("보고에 적힌 수를 **증거 파일에서 다시 세어** 댄다 — "
                  "**분모 4종**(P-118 FC · P-159 온보딩 · P-106 도달 · UX-WALK "
                  "걷기) × 칸 %d(온보딩 %d · 도달 %d · 지금 셌다). "
                  "증거가 없으면 **0 이 아니라 못 잰 것**이다"
                  % (len(RECORDED_ONBOARDING) + len(RECORDED_REACH),
                     len(RECORDED_ONBOARDING), len(RECORDED_REACH))),
        target="저장소에 남은 증거 JSON 4종 (P-118 FC · P-159 온보딩 · P-106 도달 · UX-WALK 걷기)",
        as_="자격 없음 — 파일만 읽는다. 제품에 닿지 않는다",
        source="파일 바이트 그 자체 · 그리고 그것을 **다시 읽어** 다시 센 수",
    )
    raise SystemExit(main())
