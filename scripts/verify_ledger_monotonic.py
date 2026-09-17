#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-154 — **대장은 줄지 않는다. 줄면 멈춘다.** (턴 S · 차선 F)

무엇이 이 게이트를 만들었나 [실측 2026-09-16 · 턴 R]
-----------------------------------------------------
`scripts/capture_screens.py` 가 대장 셋을 **이번 실행분만 남기고 덮어썼다**:

    D-347/screens/INDEX.yaml       32항목 →  2항목
    D-347/screens/run_log.json     32단계 →  2단계 (1,513B → 232B)
    D-386/screen_routes.json       27자리 →  2자리

그 셋은 `verify_feature_reach` · `verify_envelope` · `verify_route_alive` 의 **입력**이라,
게이트들이 그 상태로 **상용 63.2 · 손 안 84 · 영역 ① 3/39** 를 냈다. 되살린 뒤의 참값은
65.3 · 88 · 7/39 였다 — **하락은 처음부터 없었다.** 조율자가 눈으로 잡았고, 눈은 다음
턴에 거기 없다. 그래서 도구로 옮긴다.

⚠ 되살리다가 같은 죄를 짓는 자리가 있다: 턴 R 에 조율자가 `viewers` 를 **라우트 이름으로**
  묶어 32 → 28 로 만들었다. 같은 화면을 다른 역할 계정이 본 기록 4건이 그렇게 사라졌다.
  **열쇠가 좁으면 병합은 곧 삭제다** — 이 게이트는 그 28 도 빨강으로 읽는다(출생 표본 ②).

이 게이트가 하는 일은 하나다
----------------------------
    대장 4종의 **항목 수**를 HEAD 와 견준다. HEAD 보다 작으면 **빨강(exit 1)**.

    · 같다 · 늘었다        초록 — 대장은 쌓이는 것이다
    · 줄었다               빨강 — 덮어쓴 것이다. 되살리고 다시 오라
    · HEAD 에 없다 · 못 읽었다   **회색(exit 2)** — 못 잰 것이다. 초록이 아니다

셈은 `scripts/ledger_merge.py` 의 셋을 그대로 쓴다 — `head_bytes`(HEAD 바이트) ·
`assert_not_shrunk`(줄면 예외) · `record_key`(기록 전체가 열쇠). **두 벌을 만들지 않는다**
(D-369) — 두 벌은 반드시 어긋나고, 어긋나면 한쪽이 조용히 아무것도 안 본다.

    python scripts/verify_ledger_monotonic.py             # 판정
    python scripts/verify_ledger_monotonic.py --list      # 대장별 HEAD ↔ 지금
    python scripts/verify_ledger_monotonic.py --self-test # 판정 규칙만 (파일 없이)

★ 무엇을 「항목」으로 세는가 — 대장마다 다르고, **한 곳에만 적는다**(아래 `LEDGERS`).
  INDEX 는 화면 장수 · run_log 는 단계 수 · screen_routes 는 화면(자리) 수 ·
  row_map 은 행 수다. 바이트 수로 세지 않는다 — 주석 한 줄만 지워도 빨개지면
  사람이 게이트를 끄고, 꺼진 게이트는 없는 게이트보다 나쁘다(D-353).

★ 견주는 대상은 **작업본 파일**이다(HEAD 가 아니라 지금 디스크에 있는 것).
  커밋 훅으로 돌 때 그것이 곧 커밋되는 내용이다.

호스트에서 돈다 — Django 가 필요 없다. `git` 과 (INDEX 를 위해) PyYAML 이 있으면 좋고,
없으면 그 대장만 **회색**이다(다른 셋은 그대로 판정한다).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ★ 대장 병합의 셋을 **그대로** 쓴다 — 여기서 다시 짓지 않는다 (D-369).
from ledger_merge import (  # noqa: E402
    LedgerShrank,
    assert_not_shrunk,
    head_bytes,
    merge_records,
    record_key,
)

try:
    import yaml
except ImportError:                                    # pragma: no cover — 환경 미비
    yaml = None

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[LEDGER]"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2


# ══════════════════════════════════════════════════════════════════════════
# 셈 — 대장 한 종의 바이트를 **항목 수**로. 못 세면 `None` (0 이 아니다)
# ══════════════════════════════════════════════════════════════════════════
#: INDEX 의 한 항목이 시작하는 줄. PyYAML 이 없을 때의 대비책이다.
_INDEX_ROW = re.compile(rb"^  - route:", re.M)


def _text(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None


def count_index(data: bytes):
    """D-347 화면 인덱스 → `(화면 장수, 어떻게 셌나)`. `screens:` 아래 항목을 센다.

    ★ **분모를 손으로 적지 않는다** — 어떻게 셌는지를 수와 함께 돌려주고, 게이트가 그
      문장을 `[입력]` 줄에 그대로 찍는다. 수만 있고 셈법이 없는 줄은 다음 사람이 못 믿는다.

    ★ 0장은 실패가 아니다(사유 있는 0장은 `verify_screens` 의 자리다). 여기서 보는 것은
      **HEAD 보다 줄었는가** 하나뿐이다. 그래도 「못 읽었다」와 「0장」은 가른다 —
      틀이 깨진 파일은 `None`(회색)이고 0 이 아니다.
    """
    text = _text(data)
    if text is None:
        return None, "UTF-8 로 못 읽었다"
    if yaml is not None:
        try:
            doc = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            return None, "YAML 이 깨졌다 (%s)" % type(exc).__name__
        if isinstance(doc, dict):
            rows = doc.get("screens")
            if isinstance(rows, list):
                return len(rows), "YAML 의 screens 목록 길이"
            if rows is None and "screens:" in text:
                return 0, "YAML 의 screens 가 비었다"
            return None, "YAML 에 screens 목록이 없다"
        if doc is not None:
            return None, "YAML 최상위가 사전이 아니다"
        # PyYAML 이 None 을 냈다(빈 문서) — 아래 대비책이 센다
    if b"screens:" not in data:
        return None, "screens 칸이 없다"
    how = "「  - route:」 로 시작하는 줄 수" + ("" if yaml is not None else " (PyYAML 없음 — 대비책)")
    return len(_INDEX_ROW.findall(data)), how


def _json_len(data: bytes, field: str, unit_note: str = ""):
    text = _text(data)
    if text is None:
        return None, "UTF-8 로 못 읽었다"
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return None, "JSON 이 깨졌다 (%s)" % type(exc).__name__
    if not isinstance(doc, dict):
        return None, "JSON 최상위가 사전이 아니다"
    rows = doc.get(field)
    if isinstance(rows, list):
        return len(rows), "JSON 의 %s 배열 길이%s" % (field, unit_note)
    if isinstance(rows, dict):
        return len(rows), "JSON 의 %s 열쇠 수%s" % (field, unit_note)
    return None, "JSON 에 %s 칸이 없다" % field


def count_run_log(data: bytes):
    """D-347 실행 로그 → `(단계 수, 셈법)`. 32단계가 2단계가 되던 그 칸이다."""
    return _json_len(data, "steps")


def count_screen_routes(data: bytes):
    """D-386 화면↔라우트 → `(자리 수, 셈법)`. 27자리가 2자리가 되던 칸."""
    return _json_len(data, "screens")


def count_row_map(data: bytes):
    """P-142 행 대장 → `(행 수, 셈법)`.

    ⚠ 이 대장은 **두 판이 있다** — `evidence/P-142/row_map.json`(턴 Q · 25행)과
      `evidence/P-106/row_map.json`(18행). 머리 칸은 서로 다르지만(`branch`·`contract` ↔
      `source_doc`·`fc_lower_sum`) **둘 다 `rows` 배열을 들고 있다** [실측 2026-09-16].
      그래서 세는 칸은 `rows` 하나다 — 판마다 다른 칸을 세면 두 수가 견줄 수 없게 된다.
      등재된 것은 P-142 판이고, P-106 판을 대장으로 올리려면 `LEDGERS` 에 한 줄을 더한다.
    """
    return _json_len(data, "rows", " (P-142·P-106 두 판 다 이 칸이다)")


#: 대장 4종 — **이름 · 경로 · 세는 법 · 단위**. 늘리려면 여기 한 줄을 더한다.
LEDGERS: tuple[tuple[str, str, object, str], ...] = (
    ("INDEX.yaml", "docs/agent/evidence/D-347/screens/INDEX.yaml", count_index, "장"),
    ("run_log.json", "docs/agent/evidence/D-347/screens/run_log.json", count_run_log, "단계"),
    ("screen_routes.json", "docs/agent/evidence/D-386/screen_routes.json",
     count_screen_routes, "자리"),
    ("row_map.json", "docs/agent/evidence/P-142/row_map.json", count_row_map, "행"),
)


# ══════════════════════════════════════════════════════════════════════════
# 판정 — **관측만 받는다.** 대장 이름을 보고 봐주는 길이 없다 (D-327)
# ══════════════════════════════════════════════════════════════════════════
GREEN, RED, GREY = "green", "red", "grey"


def judge_one(label: str, before, after, unit: str = "항목"):
    """대장 하나 → (색, 한 줄). `before`·`after` 는 항목 수이고 `None` 은 **못 쟀다**다.

    ★ 줄었는지 아닌지는 `ledger_merge.assert_not_shrunk` 가 판정한다 — 이 파일이
      부등호를 다시 쓰지 않는다. 부등호를 두 곳에 쓰면 한 곳만 뒤집히는 날이 온다.
    """
    if before is None and after is None:
        return GREY, "HEAD 도 작업본도 못 읽었다 — 재지 못했다"
    if before is None:
        return GREY, ("HEAD 에 없거나 못 읽었다 (지금 %s%s) — 새 대장일 수 있다. "
                      "재지 못했으므로 초록이 아니다" % (after, unit))
    if after is None:
        return GREY, ("작업본을 못 읽었다 (HEAD %s%s) — 틀이 깨졌는지 보라. "
                      "0 으로 세지 않는다" % (before, unit))
    try:
        assert_not_shrunk(label, before, after)
    except LedgerShrank as exc:
        return RED, str(exc)
    if after == before:
        return GREEN, "HEAD %s%s → 지금 %s%s (유지)" % (before, unit, after, unit)
    return GREEN, "HEAD %s%s → 지금 %s%s (+%d · 쌓였다)" % (before, unit, after, unit,
                                                           after - before)


def observe(root: Path = ROOT):
    """대장 4종의 (이름, 경로, HEAD 수, 지금 수, 단위, **셈법 한 줄**). 지금 읽는다.

    ★ 셈법을 함께 들고 온다 — 「무엇을 세어 이 수가 나왔나」를 게이트가 `[입력]` 줄에
      그대로 적는다. **분모는 손으로 적지 않는다**(D-301).
    """
    rows = []
    for label, rel, counter, unit in LEDGERS:
        head = head_bytes(rel, root=root)
        before, before_how = counter(head) if head is not None else (None, "HEAD 에 없다")
        path = root / rel
        try:
            now, how = counter(path.read_bytes()) if path.is_file() else (None, "파일이 없다")
        except OSError as exc:
            now, how = None, "읽기 실패 (%s)" % type(exc).__name__
        if now is None and before is not None:
            how = "%s · HEAD 쪽은 %s" % (how, before_how)
        rows.append((label, rel, before, now, unit, how))
    return rows


def judge(rows):
    return [(label, rel) + judge_one(label, before, after, unit)
            for label, rel, before, after, unit, _how in rows]


# ══════════════════════════════════════════════════════════════════════════
# 자기시험 — ★ **출생 표본**: 턴 R 에 실제로 일어난 그 수들
# ══════════════════════════════════════════════════════════════════════════
#: ★★ **출생 표본 ①** — 2026-09-16 턴 R 에 캡처 도구가 낸 바로 그 수다.
#:   넷 다 **빨강**이어야 한다. 여기서 초록이 나오면 이 게이트는 태어난 이유를 못 본다.
BIRTH_SAMPLE = (
    ("INDEX.yaml", 32, 2, "장"),
    ("run_log.json", 32, 2, "단계"),
    ("screen_routes.json", 27, 2, "자리"),
    ("row_map.json", 25, 0, "행"),
)

#: ★★ **출생 표본 ②** — 되살리다 지은 죄. `viewers` 를 **라우트 이름으로** 묶어
#:   32 → 28 이 된 자리다(같은 화면을 다른 역할이 본 기록 4건이 접혔다).
BIRTH_SAMPLE_VIEWERS = ("INDEX.yaml", 32, 28, "장")

#: 실제 대장의 모양을 그대로 줄인 표본 — 셈 함수가 **그 모양을 센다**는 것을 보인다.
_INDEX_BYTES = (
    "meta:\n  decision: D-347\nscreens:\n"
    "  - route: /login\n    file: A/fire_user/login.png\n"
    "  - route: /dsm/home\n    file: A/fire_user/dsm_home.png\n"
).encode("utf-8")
_RUN_LOG_BYTES = json.dumps(
    {"harness": "x", "steps": {"S-1/1": "2026-09-16T08:00:00",
                               "S-1/2": "2026-09-16T08:01:00"}}).encode("utf-8")
_SCREEN_ROUTES_BYTES = json.dumps(
    {"captured_at": "2026-09-16T08:29:02",
     "screens": {"/login": [], "/dsm/home": [], "/dsm/events": []}}).encode("utf-8")
_ROW_MAP_BYTES = json.dumps({"lane": "Q", "rows": [{"id": 1}, {"id": 2}]}).encode("utf-8")


def self_test() -> int:
    bad: list[str] = []

    def check(label: str, ok: bool) -> None:
        if ok:
            print("%s O %s" % (TAG, label))
        else:
            bad.append(label)
            print("%s X %s" % (TAG, label))

    # ① ★ 출생 표본 — 턴 R 의 넷. **전부 빨강**이어야 한다
    caught = [name for name, before, after, unit in BIRTH_SAMPLE
              if judge_one(name, before, after, unit)[0] == RED]
    check("★ 출생 표본 — 덮어쓴 대장 넷(32→2 · 32→2 · 27→2 · 25→0)을 **빨강**으로 읽는다",
          len(caught) == len(BIRTH_SAMPLE))

    # ②-a ★ 출생 표본 — 좁은 열쇠로 묶어 32 → 28 이 된 자리도 빨강이다
    name, before, after, unit = BIRTH_SAMPLE_VIEWERS
    check("★ 출생 표본 — 같은 화면을 다른 역할이 본 기록 4건이 접힌 32→28 도 빨강이다",
          judge_one(name, before, after, unit)[0] == RED)

    # ②-b 그 4건이 **왜** 사라졌나 — 열쇠가 좁았기 때문이다.
    #     ★ 접히는 자리는 **새 기록이 들어올 때**다: 좁은 열쇠는 새 기록을 옛 기록의
    #       **자리에 덮어쓴다**(`merge_records` 의 `out[seen[k]] = r`). 그래서 같은 화면을
    #       다른 역할이 본 기록이 조용히 지워진다 — 대장은 줄고, 줄어든 것은 안 보인다.
    viewers = [
        {"file": "a.png", "route": "/dsm/events", "viewed_by": "fire_admin"},
        {"file": "b.png", "route": "/dsm/events", "viewed_by": "view_only"},
    ]
    fresh = [{"file": "c.png", "route": "/dsm/events", "viewed_by": "fire_admin"}]
    wide = merge_records(viewers, fresh, key=record_key)
    narrow = merge_records(viewers, fresh, key=lambda r: r["route"])
    check("기록 전체를 열쇠로 쓰면 3건이 남고, 라우트로 좁히면 2건으로 **지워진다**",
          len(wide) == 3 and len(narrow) == 2
          and any(r["file"] == "a.png" for r in wide)
          and not any(r["file"] == "a.png" for r in narrow))

    # ③ 같거나 늘어난 것은 초록 — 대장은 쌓이는 것이다
    check("같은 수는 초록", judge_one("x", 32, 32, "장")[0] == GREEN)
    check("늘어난 수는 초록", judge_one("x", 32, 33, "장")[0] == GREEN)
    check("한 항목만 줄어도 빨강 (32→31)", judge_one("x", 32, 31, "장")[0] == RED)

    # ④ 못 잰 것은 **회색이다 — 초록이 아니다** (D-301)
    check("HEAD 에 없으면 회색", judge_one("x", None, 3, "장")[0] == GREY)
    check("작업본을 못 읽으면 회색 — 0 으로 세지 않는다",
          judge_one("x", 32, None, "장")[0] == GREY)
    check("둘 다 못 읽으면 회색", judge_one("x", None, None, "장")[0] == GREY)

    # ⑤ 셈이 **실제 대장의 모양**을 센다
    check("INDEX 를 화면 장수로 센다 (2장)", count_index(_INDEX_BYTES)[0] == 2)
    check("run_log 를 단계 수로 센다 (2단계)", count_run_log(_RUN_LOG_BYTES)[0] == 2)
    check("screen_routes 를 자리 수로 센다 (3자리)",
          count_screen_routes(_SCREEN_ROUTES_BYTES)[0] == 3)
    check("row_map 을 행 수로 센다 (2행)", count_row_map(_ROW_MAP_BYTES)[0] == 2)
    check("row_map 의 다른 판(P-106 모양)도 같은 칸으로 센다",
          count_row_map(json.dumps({"source_doc": "x", "fc_lower_sum": 1,
                                    "rows": [1, 2, 3]}).encode("utf-8"))[0] == 3)

    # ⑤-b **셈법을 말한다** — 수만 있고 셈법이 없는 줄은 다음 사람이 못 믿는다
    check("셈마다 「어떻게 셌나」가 함께 온다 (분모를 손으로 적지 않는다)",
          all(isinstance(fn(raw)[1], str) and fn(raw)[1].strip()
              for fn, raw in ((count_index, _INDEX_BYTES),
                              (count_run_log, _RUN_LOG_BYTES),
                              (count_screen_routes, _SCREEN_ROUTES_BYTES),
                              (count_row_map, _ROW_MAP_BYTES))))

    # ⑥ 틀이 깨진 바이트는 **0 이 아니라 못 셈**이다
    check("깨진 JSON 은 0 이 아니라 못 셈", count_run_log(b"{broken")[0] is None)
    check("칸이 없는 JSON 도 못 셈", count_row_map(b'{"lane": "Q"}')[0] is None)
    check("대장 아닌 YAML 은 못 셈", count_index(b"hello: world\n")[0] is None)

    # ⑦ 바이트 수로 세지 않는다 — 주석 한 줄이 판정을 바꾸지 않는다
    commented = b"# \xea\xb8\xb0\xeb\xa1\x9d \xed\x95\x9c \xec\xa4\x84\n" + _INDEX_BYTES
    check("주석을 더해도 장수는 그대로다 (바이트가 아니라 항목을 센다)",
          count_index(commented)[0] == count_index(_INDEX_BYTES)[0])

    # ⑧ 대장 넷이 **이름으로** 등재돼 있다 — 하나가 빠지면 그 대장은 아무도 안 본다
    check("대장 4종이 등재돼 있다", len(LEDGERS) == 4
          and {r[0] for r in LEDGERS} == {n for n, _b, _a, _u in BIRTH_SAMPLE})

    if bad:
        print("%s 자기시험 **실패** %d건 — 이 게이트는 눈이 멀었다" % (TAG, len(bad)))
        return EXIT_FAIL
    print("%s 자기시험 통과 — 출생 표본 5(32→2 · 32→2 · 27→2 · 25→0 · 32→28) · "
          "음성 2(유지·증가) · 회색 3 · 셈 4 · 틀 3" % TAG)
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="대장은 줄지 않는다 (P-154)")
    ap.add_argument("--list", action="store_true", help="대장별 HEAD ↔ 지금")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # 판정 전에 판정기부터 시험한다 (D-277). 여기서 죽으면 아래 초록은 뜻이 없다.
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    seen = observe()
    rows = judge(seen)
    if not rows:
        print("%s 대장을 한 종도 못 찾았다 — 등재기가 눈이 멀었다 (D-301)" % TAG)
        return EXIT_FAIL

    greens = [r for r in rows if r[2] == GREEN]
    reds = [r for r in rows if r[2] == RED]
    greys = [r for r in rows if r[2] == GREY]

    # ★ **분모는 손으로 적지 않는다** — 대장마다 무엇을 세어 그 수가 나왔는지 그대로 찍는다.
    print("%s [입력] 대장 %d종 — HEAD 와 작업본의 항목 수를 견준다 · 셈법: %s"
          % (TAG, len(rows),
             " · ".join("%s=%s" % (label, how) for label, _rel, _b, _a, _u, how in seen)))
    for label, rel, color, why in rows:
        mark = {GREEN: "O", RED: "X", GREY: "?"}[color]
        print("%s   %s %-20s %s" % (TAG, mark, label, why))
        if args.list:
            print("%s       %s" % (TAG, rel))

    if reds:
        print("%s 빨강 — 줄어든 대장 %d종. **대장은 줄지 않는다**: 생성기가 이번 "
              "실행분만 남기고 덮어썼는지 보라. 되살리는 자리는 "
              "`git show HEAD:<파일>` 이고, 합치는 자리는 scripts/ledger_merge.py 다 "
              "(열쇠를 좁히지 말 것 — 좁은 열쇠는 병합이 아니라 삭제다)" % (TAG, len(reds)))
        return EXIT_FAIL
    if greys:
        print("%s **판정 불가**(회색 %d종 · 초록 %d종) — 회색은 초록이 아니다. "
              "못 잰 대장을 통과로 읽지 않는다 (D-301)" % (TAG, len(greys), len(greens)))
        return EXIT_UNDECIDABLE
    print("%s 통과 — 대장 %d종이 HEAD 보다 줄지 않았다" % (TAG, len(greens)))
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE

    gate_header(
        __file__,
        target="대장 4종의 항목 수 — HEAD ↔ 작업본 (판정은 호스트에서 돈다)",
        as_="자격증명 없음 — git 과 작업본 파일을 읽는다",
        source=" + ".join(file_stamp(ROOT / rel) for _l, rel, _c, _u in LEDGERS)
               + " · HEAD 쪽은 git show 로 지금 읽는다",
    )
    raise SystemExit(main())
