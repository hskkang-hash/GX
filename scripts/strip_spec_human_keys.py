#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-431 · 턴 AQ · 차선 Q — 기계 증거 json 에서 사람 표 키를 걷는다(이주 2단계).

`docs/agent/evidence/SPEC/<id>.json` 에서 `title_parts` · `title_parts_note` · `retro*`
키만 지운다. 다른 키·키 순서는 그대로다. 사람 표의 정본은 `<id>.retro.md` 다
(1단계에서 조율자가 복사 · `scripts/_retro_table.py` 가 읽는다).

★ 안전줄: `<id>.retro.md` 가 **없는** json 에서 사람 표 키를 걷으면 그 표가 영영
  사라진다 — 그런 파일은 걷지 않고 「보류」로 이름을 낸다(exit 1).

재실행해도 된다(멱등) — 시험 쓰개가 옛 모양으로 다시 쓴 json 이 생기면 다시 부른다.

    python scripts/strip_spec_human_keys.py            # 건너뛸 것 없이 수만 본다(쓰지 않는다)
    python scripts/strip_spec_human_keys.py --apply    # 실제로 걷는다
    python scripts/strip_spec_human_keys.py --self-test

종료 코드: 0 = 걷을 것 0 이거나 다 걷었다 · 1 = 보류(.retro.md 없음)가 있다 · 2 = 못 읽은 json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from _retro_table import EVIDENCE_DIR, is_human_key, retro_path  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[STRIP-HUMAN]"


def plan_one(payload, has_retro: bool) -> tuple[str, list]:
    """순수 함수 — (할 일, 걷을 키). 할 일: "none" | "strip" | "hold" | "bad"."""
    if not isinstance(payload, dict):
        return "bad", []
    keys = [k for k in payload if is_human_key(k)]
    if not keys:
        return "none", []
    if not has_retro:
        return "hold", keys
    return "strip", keys


def stripped(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if not is_human_key(k)}


def dump_like(original: str, payload: dict) -> str:
    """원래 파일의 끝 줄바꿈 유무를 따른다(diff 를 키 줄로만 좁힌다)."""
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return body + ("\n" if original.endswith("\n") else "")


def run(apply: bool, evidence_dir: Path = EVIDENCE_DIR) -> int:
    counts = {"none": 0, "strip": 0, "hold": 0, "bad": 0}
    held, bad = [], []
    for path in sorted(evidence_dir.glob("*.json")):
        cid = path.stem
        try:
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text)
        except (OSError, ValueError):
            counts["bad"] += 1
            bad.append(path.name)
            continue
        what, keys = plan_one(payload, retro_path(cid, evidence_dir).is_file())
        counts[what] += 1
        if what == "hold":
            held.append("%s(%s)" % (cid, ",".join(keys)))
        if what == "strip" and apply:
            #: newline="" — 윈도 호스트에서 돌려도 LF 그대로(원본이 LF 다).
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(dump_like(text, stripped(payload)))
    print("%s %s · json %d · 걷음 %d · 걷을 것 없음 %d · 보류(.retro.md 없음) %d · 못 읽음 %d"
          % (TAG, "적용" if apply else "미리보기(쓰지 않음)", sum(counts.values()),
             counts["strip"], counts["none"], counts["hold"], counts["bad"]))
    if held:
        print("%s   보류: %s" % (TAG, ", ".join(held)))
    if bad:
        print("%s   못 읽음: %s" % (TAG, ", ".join(bad)))
    return 2 if bad else (1 if held else 0)


def self_test() -> int:
    cases = []
    # ★ 출생 표본 — 턴 AP DSM-U5-05.json: 쓰개가 title_parts·retro 를 json 에 다시 썼다.
    birth = {"id": "DSM-U5-05", "request": {}, "title_parts": [{"part": "a"}],
             "retro": "P-421 채움", "retro_ap": "x", "title_parts_note": "n", "what": "w"}
    cases.append(("★ 출생 표본 — .retro.md 있으면 사람 키 넷을 걷는다",
                  plan_one(birth, True) == ("strip", ["title_parts", "retro", "retro_ap",
                                                      "title_parts_note"])))
    cases.append(("★ 걷은 뒤 다른 키·순서는 그대로",
                  list(stripped(birth)) == ["id", "request", "what"]))
    cases.append(("★★ .retro.md 없으면 걷지 않고 보류(표가 사라지지 않게)",
                  plan_one(birth, False)[0] == "hold"))
    cases.append(("사람 키가 없으면 할 일 없음", plan_one({"id": "x"}, True) == ("none", [])))
    cases.append(("표(object) 가 아니면 bad", plan_one([1], True)[0] == "bad"))
    cases.append(("끝 줄바꿈 유무를 따른다",
                  dump_like("{}" + chr(10), {}).endswith(chr(10))
                  and not dump_like("{}", {}).endswith(chr(10))))
    for n, g in cases:
        print("  %-4s %s" % ("OK" if g else "FAIL", n))
    return 0 if all(g for _, g in cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="SPEC json 에서 사람 표 키(title_parts·retro*) 걷기")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    return run(a.apply)


if __name__ == "__main__":
    sys.exit(main())
