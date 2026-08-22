#!/usr/bin/env python
"""tickets.yaml 의 meta.manifest 를 **실측으로** 생성·검증한다 (D-227 · D-228).

왜 이 스크립트가 필요한가
---------------------------
정본 무결성 게이트는 원래 `tickets.sha256`(파일 전체 해시)이었다. 그런데
에이전트는 `status`·`evidence`·`updated_at` 을 **정상 작업으로 계속 고친다.**
즉 그 해시는 **정상 동작에서 항상 어긋난다.** 설계 자기모순이라 게이트로
기능한 적이 없다 (D-228 → sha256 폐기).

manifest 는 그 자리를 대신하되 **바뀌지 않는 것만** 센다 — 티켓의 개수와 id
집합이다. 상태가 어떻게 바뀌든 이 둘은 사람이 티켓을 넣고 뺄 때만 바뀐다.

사용법
------
    python scripts/gen_manifest.py            # 대조만 (CI·STEP 0 용). 불일치 시 exit 1
    python scripts/gen_manifest.py --write    # meta.manifest 를 실측값으로 갱신

손으로 세지 않는다. 손으로 센 수가 틀렸던 것이 manifest 유실의 원인이다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

TICKETS = Path(__file__).resolve().parent.parent / "docs" / "agent" / "tickets.yaml"


def measure(doc: dict) -> dict:
    """tickets 배열을 실측해 manifest 를 만든다."""
    tickets = doc.get("tickets") or []
    ids = [t["id"] for t in tickets]

    by_phase: dict[str, int] = {}
    for t in tickets:
        by_phase[t.get("phase", "UNKNOWN")] = by_phase.get(t.get("phase", "UNKNOWN"), 0) + 1

    return {
        "total": len(tickets),
        "by_phase": dict(sorted(by_phase.items())),
        "ids": ids,
    }


def compare(actual: dict, recorded: dict | None) -> list[str]:
    """기록된 manifest 와 실측을 대조해 불일치 목록을 돌려준다."""
    if not recorded:
        return ["meta.manifest 가 없다 (--write 로 생성하라)"]

    problems: list[str] = []
    if recorded.get("total") != actual["total"]:
        problems.append(f"total: 기록 {recorded.get('total')} ≠ 실측 {actual['total']}")
    if recorded.get("by_phase") != actual["by_phase"]:
        problems.append(f"by_phase: 기록 {recorded.get('by_phase')} ≠ 실측 {actual['by_phase']}")

    rec_ids, act_ids = recorded.get("ids") or [], actual["ids"]
    if rec_ids != act_ids:
        missing = [i for i in rec_ids if i not in act_ids]
        added = [i for i in act_ids if i not in rec_ids]
        if missing:
            problems.append(f"기록에만 있는 id: {missing}")
        if added:
            problems.append(f"실측에만 있는 id: {added}")
        if not missing and not added:
            problems.append("id 집합은 같으나 순서가 다르다")

    # manifest 와 무관하게 항상 본다 — 중복 id 는 그 자체로 정본 파손이다
    dupes = {i for i in act_ids if act_ids.count(i) > 1}
    if dupes:
        problems.append(f"중복 id: {sorted(dupes)}")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="meta.manifest 를 실측값으로 갱신")
    args = ap.parse_args()

    doc = yaml.safe_load(TICKETS.read_text(encoding="utf-8"))
    actual = measure(doc)
    recorded = (doc.get("meta") or {}).get("manifest")

    if args.write:
        # 원문 주석을 보존해야 하므로 yaml.dump 로 통째로 다시 쓰지 않는다.
        # 삽입은 호출부(patch_registry.py)가 텍스트로 한다. 여기서는 값만 출력한다.
        print(yaml.safe_dump({"manifest": actual}, allow_unicode=True, sort_keys=False))
        return 0

    problems = compare(actual, recorded)
    print(f"[MANIFEST] total={actual['total']} by_phase={actual['by_phase']}")
    if problems:
        print("[MANIFEST] 불일치 — STOP(registry-mismatch)")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[MANIFEST] 대조 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
