#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-347 — 피드백 콘솔의 화면은 **실제 실행 캡처만**. 진술을 증거로 바꾼다.

왜 게이트가 필요한가
--------------------
D-347 은 「E2E 실행 중에 찍는다」고 정했다. 그런데 **그 문장은 진술이다.**

    ★ 이게 없으면 「E2E 중에 찍었다」가 진술로만 남는다 (D-323 — 확인 행위가 잠금을 내린다).

그래서 이 게이트가 **시각으로** 대조한다. 캡처 시각이 그 시나리오·단계의 E2E 실행 시각과
±5분 안에 있지 않으면, 그것은 시험이 지나간 화면이 아니다.

이 페이지는 **고객이 본다.** 실제가 아닌 화면이 한 장이라도 들어가면
**착시가 아니라 거짓말**이다 — D-284(거짓 성공 금지)의 대외 판이다.

보는 것 — 다섯
--------------
  ① 항목마다 메타 5칸이 **찼는가** (route · user_role · scenario · captured_at ·
     **data_source** — 시드인가 현장인가 · P-9)
  ② `file` 이 가리킨 PNG 가 **실재하는가** (없는 파일을 적으면 그것도 문서다)
  ③ 파일 자리가 규약대로인가 — `<scenario>/<role>/<route>.png`
  ④ `captured_at` 이 E2E 실행 로그의 그 단계 시각과 **±5분** 안인가
  ⑤ 0장일 때 **사유가 있는가** — 「0장」과 「못 찍었다」는 다르다 (D-301)

★ 0장은 실패가 아니다. **사유 없는 0장이 실패다.**
  지금은 브라우저를 여는 E2E 가 없어 0장이고, 그 사유가 `empty_reason` 과
  잠금 대장(BROWSER_E2E_HARNESS)에 적혀 있다. 사유를 지우면 이 게이트가 빨개진다.

    python scripts/verify_screens.py             # 판정
    python scripts/verify_screens.py --list      # 화면 목록
    python scripts/verify_screens.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:                                    # pragma: no cover — 환경 미비
    #: ★ [실측 2026-09-23 · 차선 C] 이 판정기를 `gx-shell` 안에서 돌리면
    #:   `ModuleNotFoundError: yaml` 로 **역추적만 뱉고 죽었다.** 그 화면은
    #:   「빨강」과 구별되지 않는다 — 차선 C 가 실제로 그것을 「검증기만 판정 불가」로
    #:   읽었고, 그 사이 호스트에서는 **진짜 빨강**(파일 이름 규약)이 나 있었다.
    #:   못 잰 것은 **못 잰다고 말한다**(exit 2 · D-301). 이 판정기는 호스트에서 돈다.
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "docs" / "agent" / "evidence" / "D-347" / "screens"
INDEX = SCREENS / "INDEX.yaml"
BLOCKERS = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ [P-9 · 2026-09-16] **다섯째 칸을 더했다 — `data_source`.**
#:   시드로 찍은 화면은 실제 화면이지만 **실제 사고는 아니다.** 그 둘이 구분되지
#:   않으면 검수 자리에서 시드 화면이 현장 화면으로 읽힌다 — 착시가 아니라 거짓말이다
#:   (D-284). 비어 있으면 이 게이트가 멈춘다: 출처 없는 화면은 싣지 않는다.
META_FIELDS = ("route", "user_role", "scenario", "captured_at", "data_source")

#: ★ [P-9 확장 · 2026-09-06 턴 I · 차선 C] **어휘를 정하고, 콘솔이 그것을 말한다.**
#:
#:   턴 H 까지 이 칸은 「비어 있지 않은가」만 봤고, 실행체(`capture_screens.py`)는
#:   **모든 항목에 `시드` 를 박아 넣고 있었다** [실측 · `_rewrite_index` 의 상수 줄].
#:   그래서 이 칸은 채워져 있었지만 **아무것도 재지 않았다** — 29장이 전부 같은 값을
#:   들고 있으면 그것은 출처가 아니라 상수다. 채워진 칸과 잰 칸은 다른 것이다(D-323).
#:
#:   세 가지만 받는다. 셋의 뜻은 **「화면에 뜬 수가 어디서 왔는가」**다:
#:     실측 — 제품이 실제로 들고 있는 값. 아무도 심지 않았고 아무도 가로채지 않았다
#:     시드 — 우리가 시험용으로 **심은** 값. 화면은 진짜지만 **사고는 진짜가 아니다**
#:     모의 — 응답을 **가로채 지어낸** 값. 서버는 이 요청을 본 적조차 없을 수 있다
#:
#:   ★ 어휘 밖의 이름은 **초록이 아니다.** 「seed」·「실제」·「live」 가 섞이기 시작하면
#:     검수 자리에서 세 칸이 다시 한 칸이 된다 — 이 칸을 만든 이유가 사라진다.
DATA_SOURCES = ("실측", "시드", "모의")


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로
# ═══════════════════════════════════════════════════════════════════════════

def route_stem(route: str) -> str:
    """라우트에서 **파일 이름의 뿌리**를 만든다 — 질의문자열은 뺀다.

    ★ [실측 2026-09-23 · 차선 C] 질의를 그대로 파일명에 넣던 규칙이 두 곳에서 깨졌다:
      ⓐ `?` 는 윈도우 마운트에서 **저장이 죽는다** (`/dsm/events?preset=mine`)
      ⓑ 같은 라우트를 다른 단언으로 두 번 찍으면 **뒤엣것이 앞엣것을 덮는데
        인덱스에는 두 줄이 남는다** — 인덱스가 거짓말을 한다
    """
    path = str(route or "").split("?", 1)[0]
    return path.strip("/").replace("/", "_") or "root"


def route_stems(route: str) -> tuple[str, ...]:
    """받아 줄 뿌리 둘 — **날 것**과 **id 를 눕힌 것**.

    ★ [실측 2026-09-23] 상세 화면의 라우트에는 씨앗 id 가 박힌다(`/dsm/events/4796`).
      그 id 는 실행마다 바뀌므로 파일 이름에 넣으면 **한 장 찍을 때마다 새 파일**이 남고,
      넣지 않으면 뿌리가 라우트와 안 맞는다. 둘 다 받아 준다:
          날 것    dsm_events_4796        (지금까지의 16장이 이 모양이다)
          눕힌 것  dsm_events_id_…        (변하는 자리를 `id` 로 눕힌다)
      ⚠ 「아무 이름이나」가 아니다. 숫자 자리 **하나만** 눕힌다.
    """
    import re as _re

    raw = route_stem(route)
    laid = _re.sub(r"(^|_)\d+(?=_|$)", r"\1id", raw)
    return (raw,) if laid == raw else (raw, laid)


def expected_prefix(entry: dict) -> tuple[str, ...]:
    """규약 ⑤(정정) — `<scenario>/<role>/<route 뿌리>…png`.

    ★ 왜 「같아야 한다」에서 「**로 시작해야 한다**」로 늦췄나 [2026-09-23]:
      한 라우트가 화면 여러 장을 낼 수 있다(프리셋 넷 · 상세의 판정 패널).
      그때 파일 이름이 갈리지 않으면 **덮어쓰기**가 나고, 덮어쓰기는 인덱스와
      파일이 조용히 갈라지는 가장 흔한 길이다. 그래서 뒤에 붙는 꼬리표를 허용한다.

    ★ 그러나 **뿌리는 여전히 라우트에서 나온다.** 이름을 완전히 자유롭게 두면
      「이 그림이 어느 화면인지」를 파일만 보고 못 판정하게 되고, 그 순간 이 판정기가
      할 일이 없어진다. 늦추되 **끈은 남긴다.**
    """
    scenario = str(entry.get("scenario", "")).split("/")[0]
    role = str(entry.get("user_role", ""))
    return tuple("%s/%s/%s" % (scenario, role, stem)
                 for stem in route_stems(entry.get("route", "")))


def parse_when(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def judge_entry(entry: dict, *, exists, run_log: dict, tolerance_min: int) -> list[str]:
    """화면 한 장을 판정한다."""
    label = entry.get("file") or entry.get("route") or "(이름 없음)"
    out: list[str] = []

    missing = [f for f in META_FIELDS if not str(entry.get(f) or "").strip()]
    if missing:
        out.append("%s: 메타가 비었다 — %s" % (label, ", ".join(missing)))

    #: 출처는 **어휘 안**이어야 한다. 꼬리표(괄호 설명)는 붙여도 되지만 머리는 셋 중 하나다.
    src = str(entry.get("data_source") or "").strip()
    if src and not any(src == v or src.startswith(v + " ") or src.startswith(v + "(")
                       for v in DATA_SOURCES):
        out.append("%s: 출처 이름이 어휘 밖이다 — «%s» (받는 것: %s). "
                   "이름이 흩어지면 검수에서 세 칸이 다시 한 칸이 된다"
                   % (label, src, " · ".join(DATA_SOURCES)))

    rel = str(entry.get("file") or "").strip()
    if not rel:
        out.append("%s: file 이 없다" % label)
        return out
    if not exists(rel):
        out.append("%s: 파일이 없다 — 없는 캡처를 적으면 그것도 문서다" % rel)
    wants = expected_prefix(entry)
    if not (rel.endswith(".png")
            and any(rel == w + ".png" or rel.startswith(w + "_") for w in wants)):
        want = wants[0]
        out.append("%s: 자리가 규약과 다르다 — «%s[_꼬리표].png» 여야 한다 (<scenario>/<role>/<route 뿌리>)"
                   % (rel, want))

    when = parse_when(entry.get("captured_at"))
    if entry.get("captured_at") and when is None:
        out.append("%s: captured_at 이 날짜·시각이 아니다: %r" % (rel, entry.get("captured_at")))
    elif when is not None:
        step = str(entry.get("scenario") or "")
        ran = parse_when((run_log.get("steps") or {}).get(step))
        if ran is None:
            # ★ 「E2E 중에 찍었다」가 진술로만 남는 자리다.
            out.append("%s: E2E 로그에 «%s» 단계의 시각이 없다 — "
                       "「시험 중에 찍었다」를 확인할 수 없다 (D-323)" % (rel, step))
        elif abs(when - ran) > timedelta(minutes=tolerance_min):
            out.append("%s: 캡처 %s 와 E2E 단계 %s 가 %d분 넘게 벌어졌다 — "
                       "시험이 지나간 화면이 아니다"
                       % (rel, when.isoformat(), ran.isoformat(), tolerance_min))
    return out


def source_tally(entries) -> dict:
    """검수 콘솔의 **출처 셈**. 어휘 밖·빈 칸은 삼키지 않고 따로 센다.

    ★ 이 함수가 이 게이트의 ④ 다 [턴 I · 차선 C]. 앞의 셋은 「싣지 않는다」를
      집행하고, 이것은 **「무엇을 보고 있는지 말한다」**를 집행한다. 검수자가
      스물아홉 장을 같은 눈으로 보면 시드 화면이 현장 화면으로 읽힌다 —
      그 오독을 막는 것은 잠금이 아니라 **표시**다.
    """
    out = {v: 0 for v in DATA_SOURCES}
    out["(빈칸)"] = 0
    out["(어휘 밖)"] = 0
    for e in entries or ():
        src = str((e or {}).get("data_source") or "").strip()
        if not src:
            out["(빈칸)"] += 1
            continue
        for v in DATA_SOURCES:
            if src == v or src.startswith(v + " ") or src.startswith(v + "("):
                out[v] += 1
                break
        else:
            out["(어휘 밖)"] += 1
    return out


def tally_line(tally: dict) -> str:
    """셈을 한 줄로. **0 인 칸도 적는다** — 안 적으면 「없다」와 「안 셌다」가 같아진다."""
    head = " · ".join("%s %d" % (v, tally.get(v, 0)) for v in DATA_SOURCES)
    tail = "".join(" · %s %d" % (k, tally[k]) for k in ("(빈칸)", "(어휘 밖)") if tally.get(k))
    return head + tail


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """★ 출생 표본: **「E2E 중에 찍었다」가 진술로만 남은 상태**.

    로그와 대조되지 않는 캡처, 시각이 벌어진 캡처, 없는 파일 — 셋 다 잡혀야 한다.
    거기서 초록이 나오면 이 게이트는 합성 화면을 고객 앞에 통과시킨다.
    """
    log = {"steps": {"E2E-1/8": "2026-09-08T11:20:00"}}
    good = {"route": "/dashboard", "user_role": "OPERATOR", "scenario": "E2E-1/8",
            "data_source": "시드",
            "captured_at": "2026-09-08T11:22:00", "file": "E2E-1/OPERATOR/dashboard.png"}
    have = {"E2E-1/OPERATOR/dashboard.png"}.__contains__

    def p(entry, *, exists=have, run=log):
        return judge_entry(entry, exists=exists, run_log=run, tolerance_min=5)

    checks = [
        ("음성 대조 — 규약대로 찍힌 한 장은 통과한다", not p(good)),
        ("★ 출생표본 — E2E 로그에 그 단계가 없으면 잡는다 (진술만 남는다)",
         any("확인할 수 없다" in x for x in p(good, run={"steps": {}}))),
        ("★ 출생표본 — 시각이 5분 넘게 벌어지면 잡는다",
         any("벌어졌다" in x for x in p(dict(good, captured_at="2026-09-08T11:40:00")))),
        ("★ 없는 파일을 적으면 잡는다",
         any("파일이 없다" in x for x in p(dict(good, file="E2E-1/OPERATOR/없다.png")))),
        ("메타 한 칸이 비면 잡는다",
         any("메타가 비었다" in x for x in p(dict(good, user_role="")))),
        ("자리가 규약과 다르면 잡는다",
         any("자리가 규약과 다르다" in x for x in p(dict(good, file="아무데나.png"),
                                                exists=lambda r: True))),
        ("captured_at 이 시각이 아니면 잡는다",
         any("날짜·시각이 아니다" in x for x in p(dict(good, captured_at="어제")))),
        ("경로의 / 는 _ 로 눕힌다",
         expected_prefix({"scenario": "E2E-2/3", "user_role": "ADMIN",
                          "route": "/events/1/clip"})[0] == "E2E-2/ADMIN/events_1_clip"),
        # ★ 2026-09-23 출생 표본 — 아래 셋이 이번 턴에 실제로 깨진 자리다
        ("★ 질의문자열은 파일 이름에서 뺀다 (윈도우에서 `?` 는 저장이 죽는다)",
         not p(dict(good, route="/dashboard?preset=mine",
                    file="E2E-1/OPERATOR/dashboard_preset_mine.png"),
               exists=lambda r: True)),
        ("★ 한 라우트가 두 장을 내면 꼬리표로 갈린다 (덮어쓰기가 인덱스를 거짓말로 만든다)",
         not p(dict(good, file="E2E-1/OPERATOR/dashboard_verdict_panel.png"),
               exists=lambda r: True)),
        ("★ 상세의 씨앗 id 는 `id` 로 눕혀도 받는다",
         not p(dict(good, route="/events/4796", scenario="E2E-1/8",
                    file="E2E-1/OPERATOR/events_id_verdict_panel.png"),
               exists=lambda r: True)),
        ("그래도 남의 라우트 이름을 붙이면 잡는다 — 끈은 남는다",
         any("자리가 규약과 다르다" in x
             for x in p(dict(good, file="E2E-1/OPERATOR/handover_note.png"),
                        exists=lambda r: True))),
        # ── ★ 출생 표본 [턴 I · 차선 C] — **출처 칸이 상수였다**
        #    실행체가 29장 전부에 `시드` 를 박고 있었고, 이 게이트는 「비었는가」만 봤다.
        #    아래 넷이 그 자리를 잠근다: 어휘를 벗어난 이름 · 셈 · 표시.
        ("★ 출처 이름이 어휘 밖이면 잡는다 (seed·live 가 섞이면 세 칸이 한 칸이 된다)",
         any("어휘 밖" in x for x in p(dict(good, data_source="seed")))),
        ("어휘 안이면 통과한다 — 실측", not p(dict(good, data_source="실측"))),
        ("어휘 안이면 통과한다 — 모의(꼬리표 붙여도 받는다)",
         not p(dict(good, data_source="모의 (403 을 주입했다)"))),
        ("★ 검수 콘솔의 셈이 갈래를 가른다 — 실측 1 · 모의 2 · 빈칸 1",
         source_tally([{"data_source": "실측"}, {"data_source": "모의 (주입)"},
                       {"data_source": "모의"}, {}])
         == {"실측": 1, "시드": 0, "모의": 2, "(빈칸)": 1, "(어휘 밖)": 0}),
        ("★ 셈은 0 인 칸도 말한다 — 「없다」와 「안 셌다」가 같아지지 않게",
         tally_line({"실측": 0, "시드": 3, "모의": 0}) == "실측 0 · 시드 3 · 모의 0"),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[SCREENS] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if yaml is None:
        # ★ 판정 규칙 자체는 yaml 없이도 시험된다(위 `--self-test` 는 순수 함수만 쓴다).
        #   인덱스를 못 읽는 것은 **판정 불가**이지 통과도 실패도 아니다.
        print("[SCREENS] PyYAML 이 없다 — 인덱스를 못 읽는다. **판정 불가**(exit 2). "
              "이 판정기는 호스트에서 돈다 (컨테이너 `gx-shell` 에는 PyYAML 이 없다 [실측])")
        return 2

    if not INDEX.exists():
        print("[SCREENS] 인덱스가 없다: %s — 판정이 아니라 틀이 없는 것이다" % INDEX)
        return 1

    data = yaml.safe_load(INDEX.read_text(encoding="utf-8")) or {}
    meta = data.get("meta") or {}
    entries = data.get("screens") or []
    tolerance = int(meta.get("tolerance_minutes", 5))

    run_log: dict = {}
    log_path = ROOT / str(meta.get("run_log", ""))
    if log_path.is_file():
        try:
            run_log = json.loads(log_path.read_text(encoding="utf-8"))
        except ValueError:
            run_log = {}

    print("[SCREENS] [입력] 인덱스 항목 %d장 · E2E 로그 %s · 허용 오차 ±%d분"
          % (len(entries), "있음" if run_log else "없음", tolerance))

    problems: list[str] = []
    for entry in entries:
        problems += judge_entry(entry, exists=lambda rel: (SCREENS / rel).is_file(),
                                run_log=run_log, tolerance_min=tolerance)

    # ★ 인덱스에 없는 파일 — 어디서 왔는지 모르는 화면이 콘솔에 실리지 않게 한다.
    listed = {str(e.get("file") or "") for e in entries}
    stray = sorted(p.relative_to(SCREENS).as_posix()
                   for p in SCREENS.rglob("*.png") if p.relative_to(SCREENS).as_posix() not in listed)
    for s in stray:
        problems.append("%s: 인덱스에 없는 캡처다 — 어디서 온 화면인지 말하지 않는다" % s)

    if not entries:
        # ⑤ 0장은 실패가 아니다. **사유 없는 0장이 실패다** (D-301).
        reason = str(meta.get("empty_reason") or "").strip()
        if not reason:
            print("[SCREENS] FAIL 0장인데 사유가 없다 — 「아직 안 찍었다」와 "
                  "「찍을 수 없다」가 구별되지 않는다")
            return 1
        print("[SCREENS] 0장 · 사유: %s" % reason.splitlines()[0])
        blocked = "BROWSER_E2E_HARNESS" in (
            BLOCKERS.read_text(encoding="utf-8") if BLOCKERS.exists() else "")
        print("[SCREENS] 잠금 대장 등재: %s" % ("BROWSER_E2E_HARNESS" if blocked else "★ 없음"))
        if not blocked:
            print("[SCREENS] FAIL 0장의 사유가 잠금 대장에 없다 — 사유가 문서에만 있으면 늙는다")
            return 1

    #: ★ [턴 I · 차선 C] **검수 콘솔이 출처를 말한다.** 이 줄이 없던 동안 `data_source`
    #:   는 판정에만 쓰이고 사람 눈에는 한 번도 안 보였다 — 재기만 하고 말하지 않는
    #:   칸은 검수자에게 없는 칸이다.
    tally = source_tally(entries)
    print("[SCREENS] 출처(data_source) — %s" % tally_line(tally))
    if tally.get("(빈칸)") or tally.get("(어휘 밖)"):
        print("[SCREENS] ⚠ 출처를 말하지 않는 캡처가 있다 — 아래 FAIL 줄이 이름을 댄다")

    if args.list:
        print("  %-28s %-10s %-10s %-8s %s"
              % ("route", "role", "scenario", "출처", "file"))
        for entry in entries:
            print("  %-28s %-10s %-10s %-8s %s"
                  % (entry.get("route"), entry.get("user_role"), entry.get("scenario"),
                     str(entry.get("data_source") or "(빈칸)")[:8], entry.get("file")))

    if problems:
        for p in problems:
            print("[SCREENS] FAIL %s" % p)
        return 1
    print("[SCREENS] 통과 — 실린 화면은 전부 실제 실행 캡처다 (지금 %d장 · 출처 %s)"
          % (len(entries), tally_line(tally)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
