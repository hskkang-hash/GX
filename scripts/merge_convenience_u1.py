#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""편리성 계측을 대장에 **덧붙인다** — 줄면 멈춘다 (턴 S · 차선 U1 · 턴 V 에 축을 열었다).

무엇을 하는가
-------------
화면이 브라우저 안에서 잰 것(`window.__gxConvenience.export()` 의 JSON)을 받아
`docs/agent/evidence/U1-S/convenience_u1.json` 의 `runs` 에 **덧붙이고**, 지표별
가운뎃값을 `measured` 칸에 다시 적는다.

★ [턴 V] **이 도구는 U1 축 전용이 아니다.** 파일 이름은 태어난 자리라 그대로 두되,
  붙일 대장은 `--ledger` 가 정하고 **받는 모양은 그 대장의 `schema` 칸이 말한다.**
  그래서 U3 축(#5 · `evidence/U3-V/convenience_u3.json` · `gx.convenience.u3.v1`) 도
  같은 명령으로 붙는다:

      python scripts/merge_convenience_u1.py --ledger docs/agent/evidence/U3-V/convenience_u3.json --dump -

  축마다 도구를 따로 두면 규칙이 두 벌이 되고, **두 벌은 반드시 어긋난다**(D-369).
  U3 가 세웠던 이음새 파일 `merge_convenience_u3.py` 는 이 변경과 함께 지웠다.
  `schema` 칸이 없는 옛 대장은 지금까지대로 `SCHEMA` 를 기본값으로 쓴다.

왜 덧붙이기만 하나 — **대장은 줄지 않는다**
--------------------------------------------
직전 턴에 캡처 도구가 대장 넷을 「이번 실행분」으로 덮어써서, 게이트가 그 상태를
읽고 수가 내려간 것을 「하락」으로 낼 뻔했다. 같은 함정이 여기에도 있다: 한 사람이
한 번 걸은 결과로 대장을 갈아 끼우면 **어제의 측정이 사라진다.** 그래서 이 도구는
① 덧붙이기만 하고 ② 덧붙인 뒤 수가 **줄었으면 쓰지 않고 멈춘다.**

무엇을 하지 않나
----------------
· **판정하지 않는다.** 목표를 넘겼는지 아닌지 이 도구는 말하지 않는다 — 첫 수는
  기준선이지 합격선이 아니다. 적는 것은 잰 수와 몇 번 쟀는가뿐이다.
· 값을 지어내지 않는다. 한 번도 안 잰 지표의 `measured` 는 `null` 로 **그대로 둔다** —
  0 은 「재 봤더니 0」이고 `null` 은 「못 쟀다」다.

    python scripts/merge_convenience_u1.py --dump <브라우저가 낸 JSON 경로>
    python scripts/merge_convenience_u1.py --dump -          # 표준입력으로 받는다
    python scripts/merge_convenience_u1.py --status          # 대장만 읽어 지금 상태를 낸다
    python scripts/merge_convenience_u1.py --self-test

V 단독 세션이 값을 내는 순서 [턴 T · 턴 V 에 ②·③ 을 다듬었다]
--------------------------------------------------------------
  ① 브라우저(U1 계정 · SPA)에서 세 화면을 지나며 조작한다 — 어떤 조작 뒤 어떤 키에
     값이 생기는지는 `docs/agent/evidence/U1-S/convenience_u1.json` 의 `wired_at` 과
     아래 표가 말한다:
       u1_handle_event     /dsm/queue 초점 카드 뜸(시작) → 키 1(판정+접수) 성공 **또는**
                           종결 확인 「확인 — 종결」 성공(끝) → runs 에 1줄
       u1_handover_note    /handover 인계 자리 뜸(시작) → 「초안 가져오기」 또는
                           「인계 메모 쓰기」 누름(끝) → runs 에 1줄
       u1_dead_camera_check /dsm/cameras/grid 뜸(시작) → 무응답 수가 화면에 적힘(끝 ·
                           클릭 0 이 정상) → runs 에 1줄
  ② 같은 페이지에서 `JSON.stringify(window.__gxMetrics())` (또는
     `window.__gxConvenience.export()`) 를 evaluate 해 받는다. 파일로 남기려면
     `docs/agent/evidence/U1-S/dumps/convenience_dump_<UTC>.json` (대장 옆이다 —
     예전 머리말은 없는 폴더 `…/U1/` 을 가리키고 있었다).
     **파일을 안 만들어도 된다**: 받은 문자열을 그대로 `--dump -` 로 흘려보낸다.
  ③ `python scripts/merge_convenience_u1.py --dump <그 파일 또는 ->` — 자기시험(실물
     표본 포함)을 지나 대장에 덧붙이고, 붙인 뒤 **지표별 잰 수**를 표로 낸다.
     종료 0 · 「N줄 → N+k줄」 이 첫 값이다.

     그 표가 말하는 것 — **왜 값이 없는지를 도구가 먼저 말한다**:
       · `in_flight` 에 있는 지표 = 시작만 하고 **안 끝났다**(수가 아니다).
         V 는 그 화면으로 돌아가 끝내는 조작을 한 번 더 하고 다시 꺼내면 된다.
       · `storage_ok=false` = 그 브라우저는 저장이 막혔다(비공개 창 등).
         `runs` 는 이번 화면 수명 것도 못 담는다 — 창을 바꿔 다시 잰다.
       · 대장에 없는 지표 이름이 덤프에 있으면 그것도 말한다(표와 코드가 갈린 자리다).
     분모(지표 몇 개인가)는 **대장에서 센다** — 이 파일에 손으로 적힌 수는 없다.

종료 코드: 0 붙였다(또는 `--status` 가 상태를 냈다) · 1 붙이다 멈췄다(줄었다·모양이
다르다) · 2 못 붙였다(파일 없음·줄 덤프 없음)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "U1-S" / "convenience_u1.json"
#: 대장이 제 `schema` 칸을 안 들고 있을 때의 **기본값**이다 — 이 축의 이름이다.
#: 상수가 아니다: 받는 모양은 **대장이 말한다**(`ledger_schema`).
SCHEMA = "gx.convenience.u1.v1"
TAG = "[CONV]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _run_key(run: dict) -> tuple:
    """같은 측정인가. **시각 + 지표 + 대상**이 같으면 같은 줄로 본다 —
    걷기를 두 번 돌려 같은 덤프를 두 번 붙여도 수가 부풀지 않는다."""
    return (run.get("at"), run.get("metric"), run.get("subject"))


def ledger_schema(ledger: dict) -> str:
    """이 대장이 받는 모양의 이름. **대장이 스스로 말한다** — 순수 함수다.

    ★ [턴 V] 왜 상수가 아니게 됐나 — **축마다 도구를 두지 않기 위해서다.**
      U3 축(#5)이 제 대장을 세우면서 이 파일의 규칙(덧붙이기만 · 같은 줄 두 번 안 셈 ·
      줄면 멈춤 · 안 잰 칸은 null · 진단 칸은 붙이지 않고 말함)을 그대로 쓰려 했는데,
      막는 것이 **여기 박힌 이름 하나**뿐이었다. 그래서 U3 는 상수를 잠깐 바꿔 끼우는
      이음새 파일을 두었고, 그 순간 도구가 **두 벌**이 됐다. 두 벌은 반드시
      어긋난다(D-369) — 어긋나는 날 한쪽 대장만 조용히 다른 셈을 한다.
      이름은 축의 것이고 규칙은 공통이다. 그러니 이름은 **대장이 나른다.**

    ★ `schema` 칸이 없는 옛 대장은 지금까지대로 돈다 — 기본값이 `SCHEMA` 다.
      없는 것을 「모양이 다르다」로 읽어 멀쩡한 대장을 멈추면 그것이 더 나쁘다.
    """
    got = ledger.get("schema")
    return got.strip() if isinstance(got, str) and got.strip() else SCHEMA


def merge(ledger: dict, dump: dict) -> tuple[dict, int]:
    """대장에 덤프를 붙인 **새 대장**과 늘어난 줄 수를 돌려준다. 순수 함수다."""
    want = ledger_schema(ledger)
    if dump.get("schema") != want:
        raise ValueError(
            f"덤프의 모양이 다르다: {dump.get('schema')!r} — 이 대장은 {want!r} 만 받는다")

    old_runs = list(ledger.get("runs") or [])
    seen = {_run_key(r) for r in old_runs}

    added = []
    for run in dump.get("runs") or []:
        if not isinstance(run, dict):
            continue
        if _run_key(run) in seen:
            continue
        seen.add(_run_key(run))
        added.append(run)

    runs = old_runs + added

    #: ★ 여기가 래칫이다. 붙였는데 줄었으면 붙인 것이 아니다.
    if len(runs) < len(old_runs):
        raise ValueError("붙인 뒤 대장이 줄었다 — 멈춘다")

    out = dict(ledger)
    out["runs"] = runs
    out["metrics"] = [_remeasure(m, runs) for m in ledger.get("metrics") or []]
    return out, len(added)


def _remeasure(metric: dict, runs: list) -> dict:
    """한 지표의 `measured` 를 다시 적는다. **잰 것이 없으면 건드리지 않는다.**"""
    mine = [r for r in runs
            if r.get("metric") == metric.get("id") and r.get("completed") is not False]
    if not mine:
        return metric

    clicks = [int(r.get("clicks", 0)) for r in mine if r.get("clicks") is not None]
    elapsed = [int(r.get("elapsed_ms", 0)) for r in mine if r.get("elapsed_ms") is not None]

    out = dict(metric)
    out["measured"] = {
        "runs": len(mine),
        #: 가운뎃값이다 — 평균은 한 번의 긴 측정에 끌려간다.
        "clicks_median": statistics.median(clicks) if clicks else None,
        "elapsed_ms_median": statistics.median(elapsed) if elapsed else None,
    }
    out["measured_at"] = max((r.get("at") or "") for r in mine) or None
    out["why_null"] = None
    return out


def status_lines(ledger: dict) -> list[str]:
    """대장이 지금 무엇을 들고 있는가를 **줄로** 낸다. 순수 함수다.

    ★ **분모를 손으로 적지 않는다.** 「몇 개 중 몇 개를 쟀나」의 분모는 대장의
      `metrics` 길이다 — 표가 넷째 지표를 들이는 날 이 줄이 저절로 따라간다.

    ★ **판정하지 않는다.** 목표 칸을 함께 적되 「넘겼다/못 넘겼다」는 쓰지 않는다 —
      이 도구가 합격을 말하기 시작하면 첫 수가 합격선이 된다.
    """
    metrics = list(ledger.get("metrics") or [])
    runs = list(ledger.get("runs") or [])
    measured = [m for m in metrics if m.get("measured")]
    out = [f"{TAG} 대장 — 줄 {len(runs)} · 잰 지표 {len(measured)}/{len(metrics)}"]
    for m in metrics:
        mid = m.get("id") or "?"
        got = m.get("measured")
        if not got:
            why = m.get("why_null") or "사유가 적혀 있지 않다"
            out.append(f"{TAG}   ○ {mid:<20} 못 쟀다 — {why}")
            continue
        out.append(
            f"{TAG}   ● {mid:<20} n={got.get('runs')} · "
            f"클릭 가운뎃값={got.get('clicks_median')} · "
            f"경과 가운뎃값={got.get('elapsed_ms_median')}ms · "
            f"목표={m.get('target') or '?'} (판정은 이 도구가 하지 않는다)")
    return out


def dump_warnings(dump: dict, ledger: dict) -> list[str]:
    """덤프가 **왜 수를 못 냈는지**를 말한다. 붙이는 일과는 따로다 — 순수 함수다.

    브라우저가 함께 내는 진단 칸(`in_flight` · `storage_ok`)은 대장에 안 붙는다
    (붙이면 끝나지 않은 것이 수가 된다). 그렇다고 버리면 V 는 값이 왜 비었는지
    화면을 떠난 뒤에 알게 된다 — 그래서 **붙이지 않고 말한다.**
    """
    out: list[str] = []
    if dump.get("storage_ok") is False:
        out.append(f"{TAG} ⚠ 이 브라우저는 저장이 막혔다(storage_ok=false) — "
                   f"runs 는 이번 화면 수명 것도 못 담는다. 창을 바꿔 다시 잰다")
    for live in (dump.get("in_flight") or []):
        if not isinstance(live, dict):
            continue
        out.append(f"{TAG} ⚠ 안 끝난 측정 {live.get('metric')} "
                   f"(대상 {live.get('subject')} · 지금까지 클릭 "
                   f"{live.get('clicks_so_far')} · {live.get('elapsed_ms_so_far')}ms) — "
                   f"**수가 아니다.** 끝내는 조작을 한 번 더 하고 다시 꺼내라")
    known = {m.get("id") for m in (ledger.get("metrics") or [])}
    strange = sorted({r.get("metric") for r in (dump.get("runs") or [])
                      if isinstance(r, dict) and r.get("metric") not in known})
    for name in strange:
        out.append(f"{TAG} ⚠ 대장에 없는 지표가 덤프에 있다: {name!r} — "
                   f"표와 코드가 갈린 자리다(줄은 붙였다)")
    return out


def read_dump(path: str) -> dict:
    """덤프를 읽는다. `-` 면 **표준입력**이다 — V 가 브라우저에서 꺼낸 문자열을
    파일로 만들지 않고 그대로 흘려보낼 수 있게. 비어 있으면 그렇다고 말한다."""
    if path == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            raise ValueError("표준입력이 비었다 — 흘려보낸 것이 없다")
        return json.loads(raw)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def self_test(ledger_path: Path = LEDGER) -> int:
    """양성·음성을 함께 잰다 — 한쪽만 재는 도구는 초록으로 죽는다.

    `ledger_path` — **실물 표본으로 쓸 대장.** 기본은 U1 축이지만, `--ledger` 로 다른
    축의 대장을 다룰 때는 **그 대장**을 표본으로 잰다. 다루는 것과 재는 것이 다르면
    실물 표본은 남의 파일을 재는 셈이고, 그때의 초록은 이 실행에 대한 초록이 아니다.
    """
    fails = 0
    base = {
        "schema": SCHEMA,
        "metrics": [{"id": "u1_handle_event", "measured": None, "why_null": "아직"}],
        "runs": [],
    }
    dump = {
        "schema": SCHEMA,
        "runs": [
            {"metric": "u1_handle_event", "subject": "1", "clicks": 1,
             "elapsed_ms": 4000, "completed": True, "at": "2026-09-16T10:00:00Z"},
            {"metric": "u1_handle_event", "subject": "2", "clicks": 3,
             "elapsed_ms": 9000, "completed": True, "at": "2026-09-16T10:01:00Z"},
        ],
    }

    merged, added = merge(base, dump)
    if added != 2 or len(merged["runs"]) != 2:
        print(f"{TAG} 자기시험 FAIL 붙인 수가 다르다: {added}")
        fails += 1
    if merged["metrics"][0]["measured"]["clicks_median"] != 2:
        print(f"{TAG} 자기시험 FAIL 가운뎃값이 틀렸다")
        fails += 1

    # ① 같은 덤프를 다시 붙여도 **늘지 않는다**
    again, added2 = merge(merged, dump)
    if added2 != 0 or len(again["runs"]) != 2:
        print(f"{TAG} 자기시험 FAIL 같은 덤프가 두 번 세어졌다")
        fails += 1

    # ② 한 번도 안 잰 지표는 **null 로 남는다** (0 으로 채우지 않는다)
    untouched = merge(
        {"schema": SCHEMA, "metrics": [{"id": "u1_dead_camera_check", "measured": None}],
         "runs": []},
        {"schema": SCHEMA, "runs": []})[0]
    if untouched["metrics"][0]["measured"] is not None:
        print(f"{TAG} 자기시험 FAIL 안 잰 지표에 수가 생겼다")
        fails += 1

    # ③ 모양이 다른 덤프는 **거절한다**
    try:
        merge(base, {"schema": "something.else", "runs": []})
    except ValueError:
        pass
    else:
        print(f"{TAG} 자기시험 FAIL 남의 모양을 받았다")
        fails += 1

    # ④ [턴 T] **실물 표본** — 저장소의 실제 대장 + 가짜 값 1 → 줄지 않고 정확히 1 는다.
    #    합성 `base` 만 재면 실제 대장의 모양이 바뀌었을 때 못 본다.
    #    파일에는 쓰지 않는다 — 표본은 읽기다.
    #    [턴 V] 표본은 **지금 다루는 대장**이고, 그 대장이 말하는 모양으로 잰다.
    if ledger_path.exists():
        try:
            real = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{TAG} 자기시험 FAIL 실물 대장을 못 읽었다: {exc}")
            fails += 1
        else:
            before = len(real.get("runs") or [])
            ids_before = [m.get("id") for m in (real.get("metrics") or [])]
            first_id = ids_before[0] if ids_before else None
            if not first_id:
                print(f"{TAG} 자기시험 FAIL 실물 대장에 지표가 한 줄도 없다: {ledger_path}")
                fails += 1
            fake = {"schema": ledger_schema(real), "runs": [
                {"metric": first_id, "subject": "self-test",
                 "clicks": 1, "elapsed_ms": 1000, "completed": True,
                 "at": "1970-01-01T00:00:00Z"}]}
            grown, added_real = merge(real, fake)
            if added_real != 1 or len(grown["runs"]) != before + 1:
                print(f"{TAG} 자기시험 FAIL 실물 대장 {before}줄 + 1 이 "
                      f"{len(grown['runs'])}줄이 됐다")
                fails += 1
            #: 붙였다고 **지표가 늘거나 줄지 않는다.** 예전에는 U1 의 세 이름을 손으로
            #: 적어 견줬는데, 그러면 표가 넷째 지표를 들이는 날과 다른 축의 대장을
            #: 다루는 날 둘 다 거짓 빨강이 난다. 잠글 것은 이름 목록이 아니라
            #: **「붙이기가 지표를 건드리지 않는다」** 는 불변이다.
            if [m.get("id") for m in (grown.get("metrics") or [])] != ids_before:
                print(f"{TAG} 자기시험 FAIL 붙이기가 실물 대장의 지표 목록을 바꿨다")
                fails += 1
            # 브라우저 덤프의 진단 칸(in_flight · storage_ok)은 **붙이지 않는다** —
            # 대장에는 끝난 측정만 든다.
            noisy = dict(fake, in_flight=[{"metric": "u1_handover_note"}], storage_ok=True)
            same, added_noisy = merge(real, noisy)
            if added_noisy != 1 or "in_flight" in same:
                print(f"{TAG} 자기시험 FAIL 진단 칸이 대장에 새었다")
                fails += 1
    else:
        print(f"{TAG} 자기시험 FAIL 실물 대장이 없다: {LEDGER}")
        fails += 1

    # ⑤ [턴 V] **상태 줄의 분모는 대장이 정한다** — 손으로 적은 3 이 아니다.
    #    지표를 넷으로 늘린 벌을 주면 분모도 넷이어야 한다. 아니면 표가 자라는 날
    #    이 줄이 조용히 거짓말한다.
    four = {"schema": SCHEMA, "runs": [], "metrics": [
        {"id": "a", "measured": None, "why_null": "아직"},
        {"id": "b", "measured": None, "why_null": "아직"},
        {"id": "c", "measured": None, "why_null": "아직"},
        {"id": "d", "measured": None, "why_null": "아직"}]}
    if "0/4" not in status_lines(four)[0]:
        print(f"{TAG} 자기시험 FAIL 상태 줄의 분모가 대장을 안 따른다: "
              f"{status_lines(four)[0]}")
        fails += 1
    if "2/2" not in status_lines(merged | {"metrics": [
            merged["metrics"][0], dict(merged["metrics"][0], id="x")]})[0]:
        print(f"{TAG} 자기시험 FAIL 잰 지표를 못 센다")
        fails += 1

    # ⑥ [턴 V] **진단 칸은 붙이지 않고 말한다** — 양성(말한다)과 음성(조용하다) 둘 다.
    noisy_dump = {"schema": SCHEMA, "runs": [{"metric": "남의지표", "subject": "1"}],
                  "in_flight": [{"metric": "u1_handover_note", "subject": "9",
                                 "clicks_so_far": 2, "elapsed_ms_so_far": 1234}],
                  "storage_ok": False}
    said = dump_warnings(noisy_dump, base)
    if len(said) != 3:
        print(f"{TAG} 자기시험 FAIL 진단 셋을 다 말하지 않았다: {said}")
        fails += 1
    if dump_warnings({"schema": SCHEMA, "runs": [
            {"metric": "u1_handle_event", "subject": "1"}],
            "in_flight": [], "storage_ok": True}, base):
        print(f"{TAG} 자기시험 FAIL 멀쩡한 덤프에 경고를 냈다")
        fails += 1

    # ⑦ [턴 V] **대장이 제 모양을 들고 온다** — 이 파일에 U3 의 이름은 한 자도 없다.
    #    양성: 그 대장이 말한 모양의 덤프는 받는다. 음성: 이 파일의 기본값(U1 의 이름)을
    #    단 덤프는 **거절한다** — 축을 건너뛴 값이 남의 대장에 붙는 자리가 여기다.
    other = {"schema": "gx.convenience.u3.v1", "runs": [],
             "metrics": [{"id": "u3_receive_to_ack", "measured": None, "why_null": "아직"}]}
    if ledger_schema(other) != "gx.convenience.u3.v1":
        print(f"{TAG} 자기시험 FAIL 대장이 든 모양을 안 읽었다: {ledger_schema(other)!r}")
        fails += 1
    grown_other, added_other = merge(other, {
        "schema": "gx.convenience.u3.v1",
        "runs": [{"metric": "u3_receive_to_ack", "subject": "1", "clicks": 1,
                  "elapsed_ms": 25000, "completed": True, "at": "2026-09-18T10:00:00Z"}]})
    if added_other != 1 or not grown_other["metrics"][0]["measured"]:
        print(f"{TAG} 자기시험 FAIL 남의 축 대장에 제 모양의 덤프를 못 붙였다")
        fails += 1
    try:
        merge(other, {"schema": SCHEMA, "runs": []})
    except ValueError:
        pass
    else:
        print(f"{TAG} 자기시험 FAIL 대장이 안 부른 모양을 받았다(기본값으로 샜다)")
        fails += 1

    # ⑧ [턴 V] **`schema` 칸이 없는 옛 대장은 그대로 돈다** — 기본값이 받아 준다.
    #    양성: 기본값 모양의 덤프를 붙인다. 음성: 다른 모양은 그래도 거절한다.
    old = {"metrics": [{"id": "u1_handle_event", "measured": None}], "runs": []}
    if ledger_schema(old) != SCHEMA:
        print(f"{TAG} 자기시험 FAIL schema 칸 없는 대장이 기본값을 못 썼다")
        fails += 1
    if merge(old, dump)[1] != 2:
        print(f"{TAG} 자기시험 FAIL schema 칸 없는 옛 대장이 멈췄다")
        fails += 1
    try:
        merge(old, {"schema": "gx.convenience.u3.v1", "runs": []})
    except ValueError:
        pass
    else:
        print(f"{TAG} 자기시험 FAIL 옛 대장이 남의 모양을 받았다")
        fails += 1
    #: 빈 문자열·공백도 「없다」로 본다 — `"schema": ""` 를 모양 이름으로 믿으면
    #: 어떤 덤프도 못 붙는 대장이 조용히 생긴다.
    if ledger_schema({"schema": "  "}) != SCHEMA:
        print(f"{TAG} 자기시험 FAIL 빈 schema 칸을 이름으로 믿었다")
        fails += 1

    if fails:
        print(f"{TAG} 자기시험 {fails}건 실패")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 양성 7 · 음성 8 · 실물 표본 1(대장 줄지 않음 · "
          f"표본={ledger_path.name})")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="편리성 계측을 대장에 덧붙인다")
    ap.add_argument("--dump", default="",
                    help="브라우저가 낸 JSON 경로. `-` 면 표준입력에서 읽는다")
    ap.add_argument("--ledger", default=str(LEDGER),
                    help="붙일 대장. **받는 모양은 이 파일의 `schema` 칸이 말한다** — "
                         "축마다 도구를 따로 두지 않는다")
    ap.add_argument("--status", action="store_true",
                    help="붙이지 않고 대장의 지금 상태만 낸다(읽기다)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    ledger_path = Path(args.ledger)

    if args.self_test:
        return self_test(ledger_path)

    #: `--status` 는 **읽기**다. 자기시험을 지나지 않아도 된다 — 지나야 하는 것은
    #: 파일을 바꾸는 쪽이고, 상태를 못 보는 도구는 V 가 안 쓴다.
    if args.status:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"{TAG} **판정 불가** — 대장을 못 읽었다: {exc}")
            return EXIT_UNDECIDABLE
        for line in status_lines(ledger):
            print(line)
        return EXIT_OK

    if self_test(ledger_path) != EXIT_OK:
        return EXIT_FAIL
    if not args.dump:
        print(f"{TAG} **판정 불가** — 붙일 덤프가 없다. 브라우저에서 "
              f"JSON.stringify(window.__gxMetrics()) 를 받아 파일로 주거나 "
              f"`--dump -` 로 흘려보내라. 대장의 지금 상태만 보려면 `--status`")
        #: ★ 첫째 실패 방식은 「안 눌렀다」가 아니라 **「그 이름이 번들에 없다」**다.
        #:   계측은 `frontend/src/features/dsm/metrics.ts` 가 창에 거는 이름 하나에
        #:   달려 있고, 그 파일을 안 태운 번들에서는 export() 가 아예 없다.
        #:   걷기 전에 한 줄로 가른다 — 없는 것을 「0건 쟀다」로 적지 않기 위해서다.
        print(f"{TAG}   걷기 전에 먼저: 콘솔에 `typeof window.__gxMetrics` — "
              f"'function' 이 아니면 그 번들에 계측이 안 실린 것이고, "
              f"그때 나오는 빈 값은 **못 잰 것**이지 0 이 아니다")
        return EXIT_UNDECIDABLE

    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        dump = read_dump(args.dump)
    except (OSError, ValueError) as exc:
        print(f"{TAG} **판정 불가** — 못 읽었다: {exc}")
        return EXIT_UNDECIDABLE

    before = len(ledger.get("runs") or [])
    try:
        merged, added = merge(ledger, dump)
    except ValueError as exc:
        print(f"{TAG} 멈춘다 — {exc}")
        return EXIT_FAIL

    ledger_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{TAG} 붙였다 — {before}줄 → {len(merged['runs'])}줄 (새로 {added}줄)")
    #: 붙인 **뒤** 상태를 낸다 — V 가 화면을 떠나기 전에 「무엇이 아직 비었나」를 본다.
    for line in status_lines(merged):
        print(line)
    for line in dump_warnings(dump, merged):
        print(line)
    print(f"{TAG} ★ 이 수는 **기준선이지 합격선이 아니다** — 판정은 표와 사람이 한다")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
