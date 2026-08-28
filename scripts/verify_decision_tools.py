#!/usr/bin/env python
"""D-286 의 최상위 원칙을 **도구로** 강제한다.

    「문서는 기억을 요구하고, 도구는 기억을 요구하지 않는다」

D-286 이 정한 것: *"앞으로 모든 결정문은 마지막 줄에 **'이 판정을 강제하는 도구'** 를
적는다. 없으면 미완이다."*

그 규칙 자체가 문서에만 있으면 D-286 이 진단한 실패를 그대로 재현한다 —
사람의 기억에 맡긴 절차는 도구가 우회한다. 그래서 이 스크립트가 판정한다.

    python scripts/verify_decision_tools.py          # 판정 (미완 결정문이 있으면 exit 1)
    python scripts/verify_decision_tools.py --list   # D-286 이후 결정문의 도구 목록
    python scripts/verify_decision_tools.py --self-test   # 양성 대조 (D-277 · D-289)

무엇을 보는가 — 세 가지다
-------------------------
  ① `enforced_by` **존재**       — D-286 이후 번호의 결정문에 이 필드가 없으면 실패.
  ② `enforced_by` **실질**       — "조심한다"·"주의한다" 류의 다짐은 도구가 아니다.
                                   최소 하나는 **실행 가능한 것**(스크립트 경로 · 시험 이름 ·
                                   설정 파일 경로)을 가리켜야 한다.
  ③ 가리킨 **파일이 실재**하는가 — 없는 스크립트를 적어 두면 그것도 문서일 뿐이다.

왜 "D-286 이후"만 보나 (소급하지 않는 이유)
-------------------------------------------
D-285 까지의 96건에 지금 `enforced_by` 를 채우면, 그 작업은 **사후 정당화**가 된다.
없던 도구를 있다고 적게 되고, 그것이 이 프로젝트가 반복해 만난 실패 모양이다
(부착률 466/466 을 완결로 착각한 착시 ①·D-249).
과거는 그대로 두고, **여기서부터 규칙이 산다**. 경계는 아래 `FIRST_ENFORCED` 하나다.

★ 소급하지 않는다는 것은 **과거를 면제한다**는 뜻이지 **잊는다**는 뜻이 아니다.
  D-285 이전 중 도구가 실재하는 것은 `--list` 가 참고로 함께 센다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "docs" / "agent" / "decisions.yaml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 규칙이 사는 경계. D-286 이 이 규칙을 만든 결정문이므로 **자기 자신부터** 적용된다.
FIRST_ENFORCED = 286

#: 도구로 인정하는 형태. 하나라도 맞으면 ②를 통과한다.
#:
#: **수가 아니라 형태로 잠근다** — "도구를 N개 적었다"는 세는 순간 채워 넣게 된다.
#: 여기서 묻는 것은 "실행하거나 열어 볼 수 있는 것을 가리켰는가" 하나다.
TOOL_SHAPES = (
    # scripts/foo.py · backend/tests/test_x.py · docker-compose.yml · .pre-commit-config.yaml
    re.compile(r"[\w./-]+\.(py|sh|ya?ml|toml|cfg|ini|json)\b"),
    # 시험 이름 — TestCase::test_x 또는 pytest 노드 표기
    re.compile(r"\b\w+::\w+"),
    # 시험 함수/클래스 이름 직접 지목
    re.compile(r"\btest_[a-z0-9_]+\b"),
)

#: 도구가 **아닌** 것. 다짐·의지·기억은 D-286 이 이름 붙인 바로 그 실패다.
VOWS = re.compile(
    r"(조심|주의|유의|명심|기억|잊지|노력|지향|권장|가급적|되도록|앞으로는)"
)


def load() -> list[dict]:
    doc = yaml.safe_load(DECISIONS.read_text(encoding="utf-8"))
    return doc.get("decisions") or []


def number(did: str) -> int | None:
    m = re.fullmatch(r"D-(\d+)", str(did).strip())
    return int(m.group(1)) if m else None


def cited_paths(text: str) -> list[str]:
    """`enforced_by` 가 가리킨 저장소 경로들. 시험 이름·클래스는 경로가 아니므로 뺀다."""
    out = []
    for m in TOOL_SHAPES[0].finditer(text):
        p = m.group(0).lstrip("·-— ").strip()
        # 문서 안에서 예시로 든 확장자 조각(`*.py` 등)은 경로가 아니다
        if p.startswith("*") or " " in p:
            continue
        out.append(p)
    return out


def judge(dec: dict) -> list[str]:
    """결정문 하나에 대한 문제 목록. 빈 목록이면 통과."""
    did = dec.get("id", "?")
    problems: list[str] = []

    raw = dec.get("enforced_by")
    if not raw or not str(raw).strip():
        return [
            f"{did}: `enforced_by` 가 없다 — D-286 이 요구한 "
            f"'이 판정을 강제하는 도구'가 비어 있다. 없으면 미완이다"
        ]

    text = str(raw)
    if not any(shape.search(text) for shape in TOOL_SHAPES):
        problems.append(
            f"{did}: `enforced_by` 에 **실행 가능한 것**이 없다. "
            f"스크립트 경로·시험 이름·설정 파일 중 하나는 가리켜야 한다"
        )
    vow = VOWS.search(text)
    if vow:
        problems.append(
            f"{did}: `enforced_by` 에 다짐이 섞였다 ({vow.group(0)!r}) — "
            f"다짐은 도구가 아니다. 깨지면 멈추는 것만 적는다 (D-286)"
        )

    for path in cited_paths(text):
        # 증거 문서(evidence/…)는 등재처이므로 아직 없을 수 있다 — 실재 검사에서 뺀다.
        # ★ 그러나 스크립트·시험은 **지금 돌아야 한다.** 없는 도구를 적는 것은
        #   D-286 이 막으려던 "문서로만 있는 절차" 그 자체다.
        if path.startswith("docs/"):
            continue
        if not (ROOT / path).exists():
            problems.append(
                f"{did}: `enforced_by` 가 가리킨 {path} 가 저장소에 없다 — "
                f"없는 도구는 문서다"
            )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="결정문별 도구를 출력한다")
    ap.add_argument("--self-test", action="store_true",
                    help="양성 대조 — 이 판정기가 위반을 실제로 잡는가 (D-277 · D-289)")
    args = ap.parse_args()

    decisions = load()
    if args.self_test:
        return self_test(decisions)

    scoped = [d for d in decisions
              if (n := number(d.get("id"))) is not None and n >= FIRST_ENFORCED]
    legacy_with_tool = [d for d in decisions
                        if (n := number(d.get("id"))) is not None
                        and n < FIRST_ENFORCED and d.get("enforced_by")]

    problems: list[str] = []
    for dec in scoped:
        problems.extend(judge(dec))
        if args.list:
            first = str(dec.get("enforced_by", "")).strip().splitlines()
            print(f"  {dec['id']}  {dec.get('title', '')[:46]}")
            for line in first:
                print(f"       {line.strip()}")

    print(f"[DECISION-TOOL] 대상 {len(scoped)}건 (D-{FIRST_ENFORCED} 이후) · "
          f"전체 {len(decisions)}건 · 소급 대상 아님 {len(decisions) - len(scoped)}건 "
          f"(그중 도구 기재 {len(legacy_with_tool)}건)")

    if problems:
        print("[DECISION-TOOL] 미완 결정문 — 판정을 강제하는 도구가 없다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[DECISION-TOOL] 전건 통과 — 모든 결정문이 깨지면 멈추는 도구를 갖는다")
    return 0


def self_test(decisions: list[dict]) -> int:
    """★ 양성 대조 — 판정기가 **위반을 실제로 잡는가**.

    D-277 이 만든 절차이고, D-289 가 한 겹 더 조인 것이다:
    **표본 최소 1건은 저장소 실물에서 뽑는다.** 합성 표본만으로 검증한 탐지기는
    "내가 만든 것만 잡는" 상태가 되고, 그 상태는 초록으로 보인다.
    """
    synthetic = [
        ({"id": "D-999", "title": "도구 없음"},
         "enforced_by 결측"),
        ({"id": "D-999", "title": "빈 값", "enforced_by": "   "},
         "빈 값"),
        ({"id": "D-999", "title": "다짐", "enforced_by": "앞으로는 조심한다"},
         "다짐만 있음"),
        ({"id": "D-999", "title": "산문", "enforced_by": "리뷰에서 사람이 확인한다"},
         "실행 가능한 것 없음"),
        ({"id": "D-999", "title": "없는 도구",
          "enforced_by": "scripts/verify_nothing_at_all.py 가 판정한다"},
         "가리킨 파일 부재"),
    ]
    failures = []
    for dec, label in synthetic:
        if not judge(dec):
            failures.append(f"합성 대조 [{label}] 를 통과시켰다 — 판정기가 눈이 멀었다")

    # ── 실물 표본 (D-289) ────────────────────────────────────────────────
    # 저장소의 **진짜 결정문**을 가져와, 그 도구 줄을 지운 판을 넣어 본다.
    # 합성 문자열이 아니라 실물에서 뽑았으므로 "내가 만든 것만 잡는" 상태가 아니다.
    real = next((d for d in decisions
                 if (n := number(d.get("id"))) is not None
                 and n >= FIRST_ENFORCED and d.get("enforced_by")), None)
    if real is None:
        failures.append(
            "실물 표본을 뽑을 수 없다 — D-286 이후 결정문에 enforced_by 가 하나도 없다. "
            "D-289 가 요구한 '표본 최소 1건은 실물' 을 만족하지 못한다"
        )
    else:
        stripped = {k: v for k, v in real.items() if k != "enforced_by"}
        if not judge(stripped):
            failures.append(
                f"실물 표본 [{real['id']} 의 도구 줄 제거판] 을 통과시켰다"
            )
        # 반대 방향 — 손대지 않은 실물은 통과해야 한다. 통과하지 못하면 이 판정기는
        # 위반이 아니라 **모든 것**을 잡는 상태이고, 그 초록도 아무것도 증명하지 않는다.
        if judge(real):
            failures.append(
                f"실물 표본 [{real['id']} 원본] 을 위반으로 잡았다 — 오탐 "
                f"({judge(real)})"
            )

    print(f"[DECISION-TOOL] 양성 대조 — 합성 {len(synthetic)}건 + "
          f"실물 {'1' if real is not None else '0'}건(출처 {real['id'] if real else '없음'})")
    if failures:
        for f in failures:
            print(f"  · {f}")
        return 1
    print("[DECISION-TOOL] 양성 대조 통과 — 판정기가 위반을 잡고, 정상을 통과시킨다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
