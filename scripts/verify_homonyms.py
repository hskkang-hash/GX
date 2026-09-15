#!/usr/bin/env python
"""D-337 — 「같은 이름, 다른 것」. 등재된 이름을 **수식어 없이** 쓰면 exit 1.

    이름의 유사성으로 오판한 것이 네 번이다 (D-321 · D-328 · D-337 · D-334).
    네 번 다 같은 병이다: 두 개의 다른 것이 한 이름을 쓰고 있었고,
    **그 이름을 단독으로 읽는 순간 한쪽이 다른 쪽으로 보였다.**

무엇을 보는가
    `docs/agent/evidence/D-337/homonym_ledger.yaml` 에 등재된 이름이 소스에 나타날 때,
    **방향이나 주체를 붙였는가**를 본다. 붙지 않은 것이 「단독 사용」이다.

    ★ 술어를 행위로 긋는다 (D-324). 금지 대상은 **낱말이 아니라 낱말의 단독 사용**이다.
      `outbound_api_key` 는 `api_key` 를 포함하지만 방향이 붙어 있으므로 위반이 아니다.
      낱말 자체를 금지하면 정당한 이름까지 죽는다 — D-324 가 정정한 바로 그 실수다.

★ 래칫이다 (D-311) — 소급 사유를 요구하지 않는다
    이 저장소에는 이미 `api_key` 가 수백 곳에 있고, 그 대부분은 dj-core 가 쓰는 이름이라
    우리가 고칠 수도 없다(§0.4). 오늘 있는 것을 **파일별 건수로 잠그고**, 늘어나는 것만 막는다.
    · 줄 번호가 아니라 **파일별 건수**로 잠근다 — 위아래가 밀렸다고 새 위반이 되면 안 된다
    · 줄어드는 것은 환영이고, 줄면 기준선도 내려간다(--freeze)

★ 이 도구의 **출생 표본** (D-310)
    2026-09-07 D-337 실측: 표 ②(**나가는** 키)가 FR-05-3(**들어오는** 키)을 갚는 것으로 계산했다.
    둘 다 "API Key" 라 불려서 같은 것으로 읽었고, 잔여 절이 10 이 아니라 12 였다.
    그래서 자기시험의 첫 갈래가 **수식어 없는 `api_key` 를 잡고 `outbound_api_key` 는 통과시키는가**다.

    python scripts/verify_homonyms.py            # 판정
    python scripts/verify_homonyms.py --list     # 파일별 건수
    python scripts/verify_homonyms.py --freeze   # 기준선 갱신
    python scripts/verify_homonyms.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-337" / "homonym_ledger.yaml"
BASELINE = ROOT / "docs" / "agent" / "evidence" / "D-337" / "homonym_baseline.txt"

#: 어디를 보는가. **우리 것만 본다** — dj-core 는 §0.4 라 고칠 수 없고,
#: 고칠 수 없는 것을 세면 기준선이 영원히 안 내려간다.
SCAN_ROOTS = ("backend", "scripts")
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "migrations", "static", "media", "dist", "build"}

_HEADER = """\
# D-337 동음이의 기준선 — **오늘 수식어 없이 쓰이는 건수** (2026-09-07 실측)
#
# ★ `python scripts/verify_homonyms.py --freeze` 가 만든다. 손으로 고치지 말 것.
#
# 래칫이다(D-311). **파일별 건수**로 잠근다 — 줄 번호로 잠그면 위아래가 밀릴 때마다
# 새 위반이 되어 게이트가 거짓말을 한다. 건수가 늘거나 새 파일이 나타나면 exit 1.
# 건수가 줄어드는 것은 환영이고, --freeze 로 내린다.
#
# 형식:  <이름키> <탭> <파일> <탭> <건수>
"""


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 「단독 사용」이란 무엇인가
# ═══════════════════════════════════════════════════════════════════════════

#: 등재 이름별 판정 규칙. 대장은 사람이 읽는 문서이고, 기계 술어는 여기 둔다.
#: 대장에 있는데 여기 없는 이름은 **판정하지 않는다** — 그리고 그 사실을 출력한다
#: (「검사 못함」과 「0건」은 다르다 — D-301).
RULES = {
    # 출생 표본. 방향(inbound/outbound)이 붙지 않은 api_key / apikey 는 단독 사용이다.
    "api_key": {
        "ledger_name": "API Key",
        "pattern": r"\bapi[_-]?keys?\b",
        "qualifiers": (r"inbound", r"outbound", r"incoming", r"outgoing"),
        "why": "나가는 키(우리가 남을 부름) 와 들어오는 키(남이 우리를 부름) 는 다른 것이다",
    },
    # D-342 에서 등재된 넷째 이름의 **기계 술어**.
    #
    # ★ 술어를 행위에 긋는다 (D-324). 금지 대상은 낱말 `auth` 가 아니라
    #   **우리가 새로 짓는 이름이 `auth` 인 것**이다. 그래서 셋만 본다:
    #     · 줄 처음의 대입     `auth = request.headers.get(...)`   ← 우리가 지은 이름
    #     · 함수 이름          `def auth(`
    #     · 속성 대입          `self.auth = `
    #   `django.contrib.auth` · `core.api.v1.auth` 는 **남의 이름**이라 못 고치고(§0.4),
    #   ninja 의 `auth=CustomJWTAuth()` 는 **프레임워크의 인자 이름**이라 못 고친다.
    #   낱말을 금지하면 그 낱말을 정확히 쓰는 줄까지 죽는다 — 처음 넓게 걸었을 때 151건이
    #   잡혔고 그 대부분이 임포트 경로와 설명문이었다. 좁히고 나니 **3건**, 그중 진짜는 1건이었다.
    "auth": {
        "ledger_name": "권한 · 인증 (authz 와 authn)",
        "pattern": r"^\s*auth\s*(?::[^=]+)?=(?!=)|def\s+auth\s*\(|self\.auth\s*=",
        "qualifiers": (
            r"authn", r"authz",
            # ninja 라우트 선언의 인자 이름. 우리가 지은 이름이 아니다.
            r"=\s*[A-Z]\w*\(",
        ),
        "why": "인가(무엇을 할 수 있나)와 인증(누구인가)은 다른 것이다 — 「auth」 는 둘 다로 읽힌다",
    },
}

#: ★ 술어를 **식별자에만** 건다 — 산문에 걸지 않는다.
#:
#: 처음에는 「권한」이라는 한국어 낱말에도 술어를 걸었다. 그러자 이 파일 자신의 설명문까지
#: 위반으로 잡혔다(184건). 그건 게이트가 아니라 소음이다 — **낱말을 금지하면 그 낱말을
#: 정확히 쓰는 문장까지 죽는다.** D-324 가 정정한 바로 그 실수의 한국어판이다.
#:
#: 그래서 판정 대상을 **코드가 실제로 쓰는 이름**(식별자·문자열)로 좁히고, 주석은 지운다.
#: 대장에 있으나 식별자 술어가 없는 이름은 **「검사 못함」으로 출력한다** —
#: 「검사 못함」과 「0건」은 다르다(D-301). 조용히 통과시키지 않는다.
LEDGER_UNJUDGED_REASON = {
    "CCTV · 재난안전정보": "코드 식별자가 아니라 **문서에서의 개념 혼동**이다. 기계 술어가 없다",
    "juso 승인키": "키 이름은 표 ②(자격증명 저장처)가 잠근다 — verify_credential_store.py 의 자리다",
}

#: 같은 줄 안에서 수식어를 찾는 창. 줄 단위로 본다 — 사람이 그 줄만 읽고 가르는지가 기준이다.
QUALIFIER_WINDOW = "line"


def _iter_files():
    for root in SCAN_ROOTS:
        base = ROOT / root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_dir() or path.suffix not in (".py",):
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path


def _strip_comments(line: str) -> str:
    """`#` 뒤를 지운다. 문자열 안의 `#` 까지 지우는 거친 방법이지만, 이 판정에서는
    **덜 잡는 쪽**으로 틀리는 것이 맞다 — 산문을 잡는 게이트가 되지 않게."""
    return line.split("#", 1)[0]


def _violations_in_text(text: str, key: str) -> list[tuple[int, str]]:
    rule = RULES[key]
    pat = re.compile(rule["pattern"], re.IGNORECASE)
    quals = [re.compile(q, re.IGNORECASE) for q in rule["qualifiers"]]
    out = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = _strip_comments(raw)       # ★ 산문이 아니라 코드를 본다
        if not pat.search(line):
            continue
        if any(q.search(line) for q in quals):
            continue                      # 수식어가 붙었다 — 위반이 아니다
        out.append((i, line.strip()[:120]))
    return out


def census() -> dict:
    """{이름키: {파일: [(줄, 내용), ...]}}"""
    found = {k: {} for k in RULES}
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for key in RULES:
            hits = _violations_in_text(text, key)
            if hits:
                found[key][rel] = hits
    return found


def _load_baseline() -> dict:
    if not BASELINE.is_file():
        return {}
    out = {}
    for ln in BASELINE.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) != 3:
            continue
        key, rel, n = parts
        out[(key, rel)] = int(n)
    return out


def _ledger_names() -> list[str]:
    if not LEDGER.is_file():
        return []
    names = []
    for ln in LEDGER.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*-\s+name:\s*"?(.+?)"?\s*$', ln)
        if m:
            names.append(m.group(1))
    return names


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 출생 표본이 첫 갈래다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

#: ★ 출생 표본. D-337 이 태어난 그 혼동 그대로다.
BIRTH_SAMPLE_BARE = "key = settings.API_KEY  # 남이 우리를 부를 때 쓰는 api_key"
BIRTH_SAMPLE_QUALIFIED = "key = settings.OUTBOUND_API_KEY  # 우리가 juso 를 부를 때"


def self_test() -> int:
    failures = []

    # ① 출생 표본 — 수식어 없는 api_key 는 잡혀야 한다
    if not _violations_in_text(BIRTH_SAMPLE_BARE, "api_key"):
        failures.append("★ 출생 표본(수식어 없는 api_key)을 잡지 못했다 — 이 도구가 태어난 이유다")

    # ② 대조군 — 방향이 붙으면 위반이 아니다
    if _violations_in_text(BIRTH_SAMPLE_QUALIFIED, "api_key"):
        failures.append("방향이 붙은 outbound_api_key 를 위반으로 잘못 잡았다 — 낱말을 금지하면 안 된다(D-324)")

    # ③ 산문을 잡지 않는가 — 주석 안의 이름은 위반이 아니다
    if _violations_in_text("# 여기서 api_key 라는 이름이 왜 모호한지 설명한다", "api_key"):
        failures.append("주석(산문) 안의 이름을 위반으로 잡았다 — 게이트가 소음이 된다")

    # ④ D-342 의 넷째 이름 — **우리가 지은 `auth` 는 잡고, 남의 이름은 안 잡는다**
    #    출생 표본: `common/inbound_api_key.py` 가 실제로 갖고 있던 한 줄이다.
    if not _violations_in_text('    auth = request.headers.get("Authorization", "")', "auth"):
        failures.append("★ 출생 표본(우리가 지은 이름 auth)을 잡지 못했다 — D-342 의 술어가 죽었다")
    if _violations_in_text('    authn_header = request.headers.get("Authorization", "")', "auth"):
        failures.append("authn_ 로 고친 이름을 위반으로 잡았다 — 고친 것을 벌하면 안 된다")
    for benign in (
        "from django.contrib.auth import get_user_model",   # 남의 이름 (§0.4)
        "from core.api.v1.auth import CustomJWTAuth",       # 남의 이름 (§0.4)
        "    auth=CustomJWTAuth(),",                        # ninja 의 인자 이름
        "@route.get('', auth=JwtOrInboundKey())",           # 같은 것, 한 줄 모양
    ):
        if _violations_in_text(benign, "auth"):
            failures.append("고칠 수 없는 남의 이름을 위반으로 잡았다(D-324): %s" % benign.strip())

    # ⑤ 대장의 모든 이름이 **판정되거나 사유와 함께 검사 못함으로** 나오는가 (D-301)
    names = _ledger_names()
    if not names:
        failures.append("대장을 읽지 못했다: %s" % LEDGER)
    judged = {r["ledger_name"] for r in RULES.values()}
    for n in names:
        if n not in judged and n not in LEDGER_UNJUDGED_REASON:
            failures.append("대장의 «%s» 이 판정도 안 되고 검사 못함 사유도 없다 — 조용히 통과한다" % n)

    for f in failures:
        print("  [자기시험 실패] %s" % f)
    print("[SELFTEST] verify_homonyms: %s" % ("FAIL" if failures else "OK"))
    return 1 if failures else 0


def _print_unjudged(unjudged: list[str]) -> None:
    """★ 「검사 못함」을 「0건」으로 출력하지 않는다 (D-301)."""
    if not unjudged:
        return
    print("[HOMONYM] ★ 식별자 술어가 없어 **검사 못한** 이름 %d종 — 0건이 아니다(D-301):"
          % len(unjudged))
    for n in unjudged:
        print("    · %s — %s" % (n, LEDGER_UNJUDGED_REASON.get(n, "사유 미기재")))


def main() -> int:
    ap = argparse.ArgumentParser(description="동음이의 단독 사용 게이트 (D-337)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not LEDGER.is_file():
        print("[HOMONYM] 대장이 없다: %s" % LEDGER.relative_to(ROOT))
        return 1

    found = census()
    counts = {(k, rel): len(hits) for k, files in found.items() for rel, hits in files.items()}
    baseline = _load_baseline()

    # 대장에 있는데 술어가 없는 이름 — **검사 못함이지 0건이 아니다** (D-301)
    judged = {r["ledger_name"] for r in RULES.values()}
    unjudged = [n for n in _ledger_names() if n not in judged]

    if args.list:
        for (key, rel), n in sorted(counts.items()):
            print("  %-8s %-60s %d" % (key, rel, n))
        print("[HOMONYM] 이름 %d종 · 파일 %d개 · 단독 사용 %d건"
              % (len(RULES), len({r for _, r in counts}), sum(counts.values())))
        _print_unjudged(unjudged)
        return 0

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        lines = ["%s\t%s\t%d" % (k, rel, n) for (k, rel), n in sorted(counts.items())]
        BASELINE.write_text(_HEADER + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
        print("[HOMONYM] 기준선 %d행 (%d건) -> %s"
              % (len(lines), sum(counts.values()), BASELINE.relative_to(ROOT)))
        return 0

    if self_test() != 0:
        print("[HOMONYM] 자기시험이 실패했다 — 판정을 신뢰할 수 없다")
        return 1

    grown = []
    for (key, rel), n in sorted(counts.items()):
        was = baseline.get((key, rel), 0)
        if n > was:
            grown.append((key, rel, was, n, found[key][rel]))

    rc = 0
    if grown:
        print("\n[HOMONYM] 등재된 이름을 수식어 없이 새로 썼다 — %d 파일" % len(grown))
        for key, rel, was, n, hits in grown:
            print("    %s  %s  기준선 %d → %d" % (key, rel, was, n))
            print("      사유: %s" % RULES[key]["why"])
            for ln, src in hits[: (n - was) + 2]:
                print("        %s:%s  %s" % (rel, ln, src))
        print("    → 방향이나 주체를 붙여라(예: outbound_api_key · authz). "
              "정당하면 --freeze 로 기준선에 올려라.")
        rc = 1

    total, base_total = sum(counts.values()), sum(baseline.values())
    print("[HOMONYM] 이름 %d종(대장 %d종) · 단독 사용 %d건 (기준선 %d건) -> %s"
          % (len(RULES), len(_ledger_names()), total, base_total, "FAIL" if rc else "OK"))
    _print_unjudged(unjudged)
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(__file__)
    raise SystemExit(main())
