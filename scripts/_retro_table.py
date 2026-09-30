# -*- coding: utf-8 -*-
"""P-431 · 턴 AQ · 차선 Q — 사람 표(`SPEC/<id>.retro.md`) 공용 읽개.

판정기가 아니다(verify_*/check_* 아님 — 판정기끼리 import 금지 D-212 에 안 걸린다).
`verify_spec_*.py` 가 증거 json 을 읽은 뒤 **제목 부분 표만은 이 파일로** 가져온다.

왜 있는가 — 출생 표본
---------------------
턴 AP: 시험 쓰개가 `SPEC/<id>.json` 을 다시 쓰면서 사람이 재판정한 `title_parts`
(`retro`)를 덮었다 — 조율자가 스냅숏 25 건을 복원했다(WO-20 §1 · P-431 청구 ①).
사람 표와 기계 표가 한 파일이면 이것은 다시 난다. 그래서 파일을 둘로 가른다:

    SPEC/<id>.json      기계 실측(요청/응답) — 시험 쓰개가 쓴다 · 덮어도 된다
    SPEC/<id>.retro.md  사람이 확인한 제목 부분 표 — 손(Edit)으로만 고친다

`.retro.md` 모양: 머리말 산문 + ```json 코드 블록 **하나**
(`{"id", "title_parts": [...], "title_parts_note"?, "retro"?, "retro_*"?}`).

이 모듈은 **읽기만** 한다. 쓰는 함수를 두지 않는다(두면 그것이 쓰개가 된다).
json 에 `title_parts`·`retro` 가 남아 있어도 **무시한다** — 정본은 `.retro.md` 다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "docs" / "agent" / "evidence" / "SPEC"
RETRO_SUFFIX = ".retro.md"

#: json 에서 걷어 내는(무시하는) 사람 표 키. `retro` 로 시작하는 키 전부(retro_ap 등) 포함.
HUMAN_KEYS = ("title_parts", "title_parts_note")

_BLOCK_RE = re.compile(r"```json[ \t]*\r?\n(.*?)\r?\n```", re.S)


def is_human_key(key) -> bool:
    return isinstance(key, str) and (key in HUMAN_KEYS or key.startswith("retro"))


def retro_path(clause_id: str, evidence_dir: Path | None = None) -> Path:
    return (evidence_dir or EVIDENCE_DIR) / ("%s%s" % (clause_id, RETRO_SUFFIX))


def parse_retro_md(text: str, clause_id: str | None = None) -> tuple[dict | None, str]:
    """순수 함수 — `.retro.md` 본문 → (표 dict, "") 또는 (None, 사유).

    json 블록이 정확히 하나여야 하고, 표(object)여야 하고, clause_id 를 주면
    블록의 `id` 가 그것과 같아야 한다(다른 절의 표를 옮겨 붙인 것을 막는다).
    """
    blocks = _BLOCK_RE.findall(text or "")
    if len(blocks) != 1:
        return None, "json 코드 블록이 %d개다(하나여야 한다)" % len(blocks)
    try:
        data = json.loads(blocks[0])
    except ValueError as exc:
        return None, "json 블록을 못 읽었다: %s" % exc
    if not isinstance(data, dict):
        return None, "json 블록이 표(object) 가 아니다"
    if clause_id is not None and data.get("id") != clause_id:
        return None, "json 블록의 id(%r) 가 파일 이름의 절(%s) 과 다르다" % (data.get("id"), clause_id)
    return data, ""


def read_retro(clause_id: str, evidence_dir: Path | None = None) -> tuple[dict | None, str, bool]:
    """(표 | None, 사유, 파일이 있었나). 파일 없음 = (None, 사유, False)."""
    path = retro_path(clause_id, evidence_dir)
    if not path.is_file():
        return None, "사람 표 파일이 없다: %s" % path.name, False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, "사람 표 파일을 못 읽었다(%s): %s" % (path.name, exc), True
    data, why = parse_retro_md(text, clause_id)
    return data, (why and "%s — %s" % (path.name, why)), True


def load_retro(clause_id: str, evidence_dir: Path | None = None) -> dict | None:
    """표 dict 또는 None(없음·못 읽음). 판정기가 부르는 가장 짧은 입구."""
    return read_retro(clause_id, evidence_dir)[0]


def overlay(payload, clause_id: str, evidence_dir: Path | None = None):
    """증거 json 페이로드에서 사람 표 키를 **버리고**, `.retro.md` 의 표를 얹어 돌려준다.

    판정기의 `_load_evidence` 끝에서 한 번 부른다 — 판정식·자기시험은 그대로 둔다.
    `.retro.md` 가 없거나 못 읽으면 `title_parts` 키가 **없는** 페이로드가 된다
    (각 판정기의 「표 없음」 갈래 그대로 — 옛 json 표로 떨어지지 않는다).
    """
    if not isinstance(payload, dict):
        return payload
    out = {k: v for k, v in payload.items() if not is_human_key(k)}
    table = load_retro(clause_id, evidence_dir)
    if table is not None:
        for k, v in table.items():
            if is_human_key(k):
                out[k] = v
    return out


def self_test() -> int:
    """순수 함수만 — 파일을 만들지 않는다."""
    cases = []
    good = "머리말\n\n```json\n" + json.dumps({"id": "X-01", "title_parts": [
        {"part": "a", "where": "b", "status": "measured"}], "retro": "사람"}) + "\n```\n"
    d, why = parse_retro_md(good, "X-01")
    cases.append(("json 블록 하나 → 표", d is not None and d["title_parts"][0]["part"] == "a"))
    cases.append(("id 가 다르면 → None", parse_retro_md(good, "X-02")[0] is None))
    cases.append(("블록 둘 → None", parse_retro_md(good + good, "X-01")[0] is None))
    cases.append(("블록 없음 → None", parse_retro_md("산문만", "X-01")[0] is None))
    # ★ 출생 표본(턴 AP · 조율자 스냅숏 25 복원) — 쓰개가 json 의 title_parts 를 다시 쓴다.
    #   json 쪽 표는 무시되어야 한다: .retro.md 가 없으면 표 없음, 있으면 .retro 의 것.
    stale = {"id": "Z-99", "request": {}, "title_parts": [{"part": "쓰개", "where": "w",
             "status": "measured"}], "retro": "쓰개가 덮은 값", "retro_ap": "x"}
    o = overlay(stale, "Z-99", Path("/__no_such_dir__"))
    cases.append(("★ 출생 표본 — .retro.md 가 없으면 json 의 title_parts·retro* 는 버린다",
                  "title_parts" not in o and not any(k.startswith("retro") for k in o)
                  and "request" in o))
    cases.append(("사람 키 술어 — retro_ap · title_parts_note 는 사람 키, request 는 아니다",
                  is_human_key("retro_ap") and is_human_key("title_parts_note")
                  and not is_human_key("request")))
    bad = [n for n, g in cases if not g]
    for n, g in cases:
        print("  %-4s %s" % ("OK" if g else "FAIL", n))
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    sys.exit(self_test() if "--self-test" in sys.argv else 0)
