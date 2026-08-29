#!/usr/bin/env python
"""표 ① 임계값 게이트 — **표와 코드가 갈리지 않게 한다 + 새 매직 넘버를 막는다** (D-325).

두 가지를 본다. 둘 다 없으면 표는 문서가 된다.
-----------------------------------------------
  ① **대조** — 표 ①의 `used_by` 가 가리킨 상수가 실재하고, 값이 표와 같은가.
     표를 만들어 놓고 코드 상수를 따로 고치면 그 순간 표는 **거짓말하는 문서**가 된다.
     D-227(manifest 유실)이 만든 상태가 그것이었고, `verify_kernel_map.py` 가 같은 이유로 있다.

  ② **래칫** — 오늘의 하드코딩 임계값을 기준선으로 잠그고, **새로 태어나는 것만** 막는다.
     기존분에 소급 사유를 요구하지 않는다(D-311). 사후 사유는 사유란을 거짓으로 채우고,
     그 거짓이 다음 판정의 근거가 된다.

    python scripts/verify_threshold_table.py            # 판정
    python scripts/verify_threshold_table.py --freeze   # 오늘 현황을 기준선으로 잠근다
    python scripts/verify_threshold_table.py --list     # 표 ① 을 사람이 읽는 모양으로
    python scripts/verify_threshold_table.py --self-test

모수 (D-301)
------------
`scripts/probe_threshold_census.py` 가 낸 전수를 그대로 쓴다 — **모수와 술어를 두 벌
두지 않는다.** 전수기가 눈이 멀면 이 게이트도 함께 멀어야 한다. 조용히 초록이 나는
게이트보다 함께 실패하는 게이트가 낫다.

★ 출생 표본 (D-310)
-------------------
이 도구를 만들게 한 사례는 `DEDUP_WINDOW = timedelta(seconds=10)` 이다 —
표에 없이 코드에만 있던 값. 자기시험 첫 갈래가 **「표는 10 이라는데 코드는 12 인 상태」**다.
거기서 초록이 나오면 이 게이트는 표를 지키지 못한다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from probe_threshold_census import CONTRACT_SURFACE, scan_source, walk  # noqa: E402

BACKEND = ROOT / "backend"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-325" / "threshold_baseline.txt"
TABLE = BACKEND / "kernels" / "k5_trust" / "thresholds.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 표 ①에 올리지 않기로 **판정한** 자리. 면제가 아니라 **선언**이다 —
#: 빠진 줄이 보이게 하려고 이름을 적는다 (D-264 계열).
#: 여기 이름을 더하는 것은 "이 숫자는 계약도 운영도 부르지 않는다" 는 진술이다.
DECLARED_NOT_A_SETTING: dict[str, str] = {}


def _table_defs() -> dict[str, dict]:
    """표 ①을 **import 하지 않고** 읽는다 — 이 게이트는 Django 없이 pre-commit 에서 돈다.

    정규식이 아니라 AST 로 읽는다. 정규식은 주석 안의 예시를 정의로 읽는다.
    """
    import ast

    src = TABLE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "ThresholdDef":
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        try:
            key = ast.literal_eval(kw["key"])
            default = ast.literal_eval(kw["default"])
            used_by = list(ast.literal_eval(kw["used_by"]))
            unit = ast.literal_eval(kw["unit"])
            fixed = ast.literal_eval(kw["contract_fixed"])
            clause = ast.literal_eval(kw["clause"]) if "clause" in kw else ""
        except (KeyError, ValueError):
            continue
        out[key] = {"default": default, "used_by": used_by,
                    "unit": unit, "contract_fixed": fixed, "clause": clause}
    return out


#: 단위 → 그 단위를 만드는 `timedelta` 키워드. 표가 `minutes` 라 하면 코드도 분이어야 한다.
UNIT_KWARG = {"seconds": "seconds", "minutes": "minutes", "hours": "hours",
              "days": "days"}


def constant_value(src: str, name: str):
    """소스에서 `name = <숫자>` 또는 `name = timedelta(<단위>=<숫자>)` 의 숫자를 낸다.

    **순수 함수다** — 자기시험이 겨누는 과녁이 여기다 (D-277).
    못 찾으면 `None`. 못 찾은 것과 값이 다른 것은 다른 사실이므로 부르는 쪽이 가른다.
    """
    import ast

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            continue
        v = node.value
        if isinstance(v, ast.Constant) and isinstance(v.value, (int, float)):
            return v.value
        if isinstance(v, ast.Call):
            for kw in v.keywords:
                if kw.arg in UNIT_KWARG and isinstance(kw.value, ast.Constant):
                    return kw.value.value
    return None


def cross_check(defs: dict[str, dict], read=None) -> list[str]:
    """① 대조 — 표가 가리킨 상수가 실재하고 값이 같은가. **순수 함수다.**

    `read(path) -> str | None` 를 주입할 수 있다. 자기시험이 파일 없이 이 갈래를 돈다.
    """
    if read is None:
        def read(rel: str):
            p = BACKEND.parent / rel
            return p.read_text(encoding="utf-8") if p.is_file() else None

    problems: list[str] = []
    for key, spec in defs.items():
        for ref in spec["used_by"]:
            if ":" not in ref:
                problems.append(f"{key}: used_by 항목 {ref!r} 이 'path:NAME' 모양이 아니다")
                continue
            rel, name = ref.rsplit(":", 1)
            src = read("backend/" + rel)
            if src is None:
                problems.append(
                    f"{key}: used_by 가 가리킨 backend/{rel} 가 없다 — "
                    f"없는 자리를 적으면 표도 문서다 (D-286)")
                continue
            got = constant_value(src, name)
            if got is None:
                problems.append(
                    f"{key}: backend/{rel} 에 상수 {name} 이 없다 — "
                    f"표가 가리키는 곳과 코드가 갈렸다")
                continue
            if spec["default"] is None:
                problems.append(
                    f"{key}: 표의 기본값이 비어 있는데 코드에는 {name}={got} 이 있다 — "
                    f"「값이 아직 없다」와 「코드에 값이 있다」가 동시에 참일 수 없다")
                continue
            if float(got) != float(spec["default"]):
                problems.append(
                    f"★ {key}: **표는 {spec['default']}{spec['unit']} 인데 코드 {name} 은 "
                    f"{got} 이다** (backend/{rel}) — 표와 코드가 갈리면 표는 거짓말하는 "
                    f"문서가 된다. 둘을 같은 커밋에서 고쳐라")
    return problems


def fingerprints(hits) -> dict[str, object]:
    """래칫이 이름으로 잠그는 단위 — **줄 번호 대신 서수(序數)를 쓴다.**

    줄 번호를 넣으면 코드를 위아래로 옮기기만 해도 같은 값이 새 위반이 되고,
    그러면 아무도 이 게이트를 켜 두지 않는다.

    그런데 줄 번호를 통째로 빼면 **같은 파일에 같은 값이 하나 더 늘어도 안 잡힌다** —
    래칫에 구멍이 난다. 그래서 동일 지문끼리 **몇 번째인지**를 붙인다:
    옮기는 것은 서수를 바꾸지 않고, **늘어나는 것은 반드시 새 서수를 만든다.**
    """
    from collections import Counter

    seen: Counter = Counter()
    out: dict[str, object] = {}
    for hit in sorted(hits, key=lambda h: (h.path, h.line)):
        base = f"{hit.path}::{hit.kind}::{hit.name}::{hit.value}"
        seen[base] += 1
        out[f"{base}#{seen[base]}"] = hit
    return out


_HEADER = """\
# D-325 표 ① 임계값 래칫 기준선 — **오늘 코드에 있는 하드코딩 임계값** (2026-09-06 실측)
#
# ★ `python scripts/verify_threshold_table.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다 — 소급 사유를 요구하지 않는다(D-311). 오늘 있는 것에 사후 사유를 달게 하면
# 사유란이 거짓으로 채워지고, 그 거짓이 다음 판정의 근거가 된다.
# **여기 없는 새 임계값이 태어나는 것만** exit 1 이다.
# 줄이 사라지는 것은 표로 옮겨졌거나 지워졌다는 뜻이고, 그것은 환영이다.
#
# 모수와 술어는 scripts/probe_threshold_census.py 가 정한다 — 두 벌 두지 않는다.
"""


# ═══════════════════════════════════════════════════════════════════════════
# ③ 계약 대조 — **계약이 정한 값은 설정이 아니라 상수다** (D-336)
# ═══════════════════════════════════════════════════════════════════════════
#
# 런타임 덮어쓰기는 409 가 막는다. 그러나 409 만으로는 부족하다 —
# **저장된 값 자체가 처음부터 틀려 있으면** 아무도 덮어쓰지 않아도 계약이 깨진 채로 초록이다.
# 409 는 "바꾸지 마라"이고, 이 검사는 **"지금 값이 맞느냐"**이다. 둘은 다른 질문이다.
#
# 대조 상대는 계약 AC 대장(D-309)이다. 표의 값에서 만든 낱말(`5분`·`30초`)이
# 그 절의 AC 원문에 **글자로 있는가**를 본다. 없으면 표가 계약에서 떠난 것이다.

#: 계약 AC 대장 — `ac` 문장의 출처. **표가 아니라 계약이 기준이다.**
AC_LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-309" / "contract_ac_ledger.yaml"

#: 단위 → 계약 원문이 쓰는 한국어 낱말. 「30 seconds」가 아니라 「30초」로 적혀 있다.
UNIT_KO = {"seconds": "초", "minutes": "분", "hours": "시간", "days": "일"}


def _ac_texts(path: Path = None) -> dict[str, str]:
    """계약 AC 대장에서 `{절ID: ac 문장}` 을 읽는다.

    yaml 모듈에 기대지 않는다 — 이 게이트는 pre-commit 에서 돌고, 훅 환경에
    무엇이 깔려 있는지는 우리가 정하지 않는다. `- id:` / `ac:` 두 줄만 본다.
    """
    path = path or AC_LEDGER
    if not path.is_file():
        return {}
    out, cur = {}, None
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-\s+id:\s*(\S+)", ln)
        if m:
            cur = m.group(1).strip('"\'')
            continue
        m = re.match(r'\s*ac:\s*"(.*)"\s*$', ln)
        if m and cur:
            out[cur] = m.group(1)
            cur = None
    return out


def contract_check(defs: dict[str, dict], ac_texts: dict[str, str]) -> list[str]:
    """③ 계약 대조 — `contract_fixed` 항목이 계약 원문과 어긋나면 잡는다. **순수 함수다.**

    셋을 본다:
      · 절 번호가 링크되어 있는가          (D-336 — 계약 절과 표의 행이 서로를 가리켜야 한다)
      · 그 절이 계약 AC 대장에 실재하는가  (없는 절을 적으면 링크가 아니라 장식이다)
      · 표의 값이 그 절의 원문에 있는가    (409 가 못 잡는 「처음부터 틀린 값」)
    """
    problems: list[str] = []
    for key, spec in sorted(defs.items()):
        if not spec.get("contract_fixed"):
            continue
        clause = (spec.get("clause") or "").strip()
        if not clause:
            problems.append(
                f"★ {key}: contract_fixed 인데 `clause` 가 비었다 — "
                f"계약이 정한 값이라면서 **어느 절인지 적지 않았다.** "
                f"절 번호가 없으면 계약이 바뀔 때 무엇을 고칠지 사람이 찾아야 한다 (D-336)")
            continue
        ids = re.findall(r"\bF-\d+\b", clause)
        if not ids:
            problems.append(
                f"★ {key}: `clause` 에 절 번호(F-NN)가 없다: {clause!r} — "
                f"문장만 적으면 대장과 이어지지 않는다 (D-336)")
            continue
        if spec["default"] is None:
            problems.append(
                f"★ {key}: contract_fixed 인데 기본값이 비었다 — "
                f"계약이 값을 정했다면 그 값이 표에 있어야 한다")
            continue

        token = f"{_fmt_num(spec['default'])}{UNIT_KO.get(spec['unit'], spec['unit'])}"
        for cid in ids:
            ac = ac_texts.get(cid)
            if ac is None:
                problems.append(
                    f"★ {key}: `clause` 가 가리킨 {cid} 이 계약 AC 대장에 없다 — "
                    f"없는 절을 가리키면 링크가 아니라 장식이다")
                continue
            if token not in ac:
                problems.append(
                    f"★ {key}: **표는 {token} 인데 {cid} 원문에 그 값이 없다.** "
                    f"원문: {ac!r} — 계약이 정한 값은 설정이 아니라 상수다(D-336). "
                    f"표를 고치거나, 계약 해석이 바뀌었으면 대장을 먼저 고쳐라")
    return problems


def _fmt_num(v) -> str:
    """5.0 은 계약 원문에 「5분」으로 적혀 있지 「5.0분」으로 적혀 있지 않다."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def load_baseline() -> set[str]:
    if not BASELINE.is_file():
        return set()
    return {ln.strip() for ln in BASELINE.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def self_test() -> int:
    """★ 출생 표본 — 표는 10 이라는데 코드는 12 인 상태."""
    birth_defs = {"event.dedup_window": {
        "default": 10, "unit": "seconds", "contract_fixed": False,
        "used_by": ["kernels/k1_event/services.py:DEDUP_WINDOW"]}}

    def reader(value_src):
        return lambda rel: value_src

    cases = (
        ("★ 출생표본 표는 10 인데 코드는 12 — 잡는다",
         birth_defs, "DEDUP_WINDOW = timedelta(seconds=12)\n", True),
        ("표와 코드가 같으면 안 잡는다",
         birth_defs, "DEDUP_WINDOW = timedelta(seconds=10)\n", False),
        ("상수가 아예 없으면 잡는다",
         birth_defs, "SOMETHING_ELSE = 10\n", True),
        ("표의 기본값이 비었는데 코드에 값이 있으면 잡는다",
         {"waterlevel.baseline": {
             "default": None, "unit": "cm", "contract_fixed": False,
             "used_by": ["kernels/k1_event/services.py:BASELINE"]}},
         "BASELINE = 100\n", True),
        ("맨 숫자 대입도 읽는다",
         {"x": {"default": 30, "unit": "seconds", "contract_fixed": False,
                "used_by": ["a/b.py:LIMIT_SECONDS"]}},
         "LIMIT_SECONDS = 30\n", False),
    )
    bad = 0
    for label, defs, src, should_fail in cases:
        got = bool(cross_check(defs, read=reader(src)))
        ok = got == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1

    # 지문이 줄 번호에 흔들리지 않는가 — 흔들리면 아무도 이 게이트를 켜 두지 않는다
    a = fingerprints(scan_source("MAX_RETRY = 3\n", "t.py"))
    b = fingerprints(scan_source("\n\n\nMAX_RETRY = 3\n", "t.py"))
    ok_fp = set(a) == set(b)
    print(f"  {'OK  ' if ok_fp else 'FAIL'} 지문이 줄 이동에 흔들리지 않는다")
    if not ok_fp:
        bad += 1
    # ★ 그러나 **늘어나는 것은 잡아야 한다** — 줄 번호를 뺀 대가로 생긴 구멍을
    #   서수가 막는다. 좁히면 반대편이 열린다(D-326) — 그 반대편을 여기서 잰다.
    twice = fingerprints(scan_source("MAX_RETRY = 3\nMAX_RETRY = 3\n", "t.py"))
    ok_dup = len(set(twice) - set(a)) == 1
    print(f"  {'OK  ' if ok_dup else 'FAIL'} 같은 값이 하나 더 늘면 새 지문이 생긴다")
    if not ok_dup:
        bad += 1

    # ── ③ 계약 대조 (D-336) — 409 가 못 잡는 「처음부터 틀린 값」을 잡는가 ──────
    ac = {"F-04": "동일 이벤트에 대해 5분 내 중복 알림 0건을 보장한다"}

    def _fixed(default, unit="minutes", clause="F-04 「5분 내 중복 알림 0건」"):
        return {"notify.suppress_window": {
            "default": default, "unit": unit, "contract_fixed": True,
            "clause": clause, "used_by": []}}

    contract_cases = (
        ("★ 계약은 5분인데 표가 7분 — 잡는다", _fixed(7), True),
        ("표가 계약과 같으면 안 잡는다", _fixed(5), False),
        ("contract_fixed 인데 절 번호가 없으면 잡는다", _fixed(5, clause="5분 규칙"), True),
        ("contract_fixed 인데 clause 가 비면 잡는다", _fixed(5, clause=""), True),
        ("대장에 없는 절을 가리키면 잡는다", _fixed(5, clause="F-99 「5분」"), True),
        ("5.0 을 「5분」으로 읽는다", _fixed(5.0), False),
        ("contract_fixed 가 아니면 계약 대조 대상이 아니다",
         {"x": {"default": 99, "unit": "minutes", "contract_fixed": False,
                "clause": "", "used_by": []}}, False),
    )
    for label, defs, should_fail in contract_cases:
        got = bool(contract_check(defs, ac))
        ok = got == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1

    # 대장을 실제로 읽을 수 있는가 — 못 읽으면 이 갈래는 **검사 못함이지 0건이 아니다**(D-301)
    real_ac = _ac_texts()
    ok_ledger = "F-04" in real_ac and "F-10" in real_ac
    print(f"  {'OK  ' if ok_ledger else 'FAIL'} 계약 AC 대장을 읽는다 (F-04 · F-10)")
    if not ok_ledger:
        bad += 1

    if bad:
        print(f"[THRESHOLD] 자기시험 {bad}건 실패 — 이 게이트는 눈이 멀었다")
        return 1
    print(f"[THRESHOLD] 자기시험 {len(cases) + len(contract_cases) + 3}건 통과 "
          f"(양성 7 · 음성 6 · 출생 표본 포함 · 계약 대조 D-336)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != 0:
        return 1
    if not TABLE.is_file():
        print(f"[THRESHOLD] 표 ①이 없다: {TABLE.relative_to(ROOT)} — 판정 불가")
        return 1

    defs = _table_defs()
    hits, files = walk()
    surface = [h for h in hits if h.on_contract_surface]

    print(f"[THRESHOLD] 표 ① **{len(defs)}항목** · 코드 하드코딩 임계값 "
          f"**{len(hits)}건** (계약 기능 면 {len(surface)}건 · 모수 {files}파일)")
    if not defs:
        print("[THRESHOLD] 표가 0항목이다 — 못 읽은 것인지 빈 것인지 구별할 수 없다 (D-301)")
        return 1

    if args.list:
        for key, spec in sorted(defs.items()):
            lock = "계약고정" if spec["contract_fixed"] else "        "
            val = spec["default"] if spec["default"] is not None else "(값 없음)"
            print(f"    {lock}  {key:26} {str(val):>8} {spec['unit']:8} "
                  f"← {', '.join(spec['used_by']) or '(읽는 코드 없음)'}")

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(
            _HEADER + "\n" + "\n".join(sorted(fingerprints(hits))) + "\n",
            encoding="utf-8")
        print(f"[THRESHOLD] 기준선 {len(fingerprints(hits))}건 기록 "
              f"(전수 {len(hits)}건 · 지문 단위) — {BASELINE.relative_to(ROOT)}")
        return 0

    problems = cross_check(defs)

    # ③ 계약 대조 (D-336). 대장을 못 읽으면 **조용히 통과시키지 않는다** — D-301.
    ac_texts = _ac_texts()
    fixed_keys = [k for k, s in defs.items() if s.get("contract_fixed")]
    if not ac_texts:
        problems.append(
            f"계약 AC 대장을 읽지 못했다: {AC_LEDGER.relative_to(ROOT)} — "
            f"contract_fixed {len(fixed_keys)}항목을 **검사하지 못했다.** "
            f"「검사 못함」은 「0건」이 아니다 (D-301)")
    else:
        problems.extend(contract_check(defs, ac_texts))
        print(f"[THRESHOLD] 계약고정 **{len(fixed_keys)}항목**을 계약 AC 대장 "
              f"{len(ac_texts)}절과 대조했다 (D-336)")

    baseline = load_baseline()
    if not baseline:
        print("[THRESHOLD] 기준선 파일이 없다 — `--freeze` 로 오늘 현황을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return 1
    current = fingerprints(hits)
    fresh = sorted(set(current) - baseline - set(DECLARED_NOT_A_SETTING))
    healed = sorted(baseline - set(current))
    print(f"[THRESHOLD] 기준선 {len(baseline)}건 · **새 매직 넘버 {len(fresh)}건** · "
          f"사라진 것 {len(healed)}건")
    if healed:
        print("[THRESHOLD] `--freeze` 로 기준선을 줄인다 — 줄어드는 것이 보여야 갚는 맛이 난다")

    for f in fresh:
        h = current[f]
        problems.append(
            f"★ 새 매직 넘버 임계값: {h.path}:{h.line} [{h.kind}] {h.name}={h.value!r} — "
            f"표 ①(backend/kernels/k5_trust/thresholds.py)에 올리거나, 계약도 운영도 "
            f"부르지 않는 값이면 verify_threshold_table.DECLARED_NOT_A_SETTING 에 "
            f"사유와 함께 등재하라 (등재는 면제가 아니라 선언이다)")

    if problems:
        print("[THRESHOLD] 위반")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[THRESHOLD] 통과 — 표와 코드가 같고, 새 매직 넘버가 없다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
