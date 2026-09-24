#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-107 — **머리글 없는 게이트는 회색이다** (2026-09-07 · 턴 M · 차선 Q).

무엇을 재는가 — 셋
------------------
  ① **머리글 보유** — `scripts/verify_*.py` 마다 `gate_header(...)` 를 부르는가.
     안 부르면 그 게이트는 **회색**이다. 통과가 아니다(D-301).
  ② **머리글 성립** — 게이트를 실제로 **돌려서** 세 줄이 나오는지 본다.
     ★ 읽어서 답하지 않는다(D-210). 소스에 `gate_header(` 가 적혀 있는 것과
       그 줄이 **실제로 찍히는 것**은 다른 사실이고, 우리를 물었던 것은 늘 뒤엣것이다.
     여기서 `AS=root`/`admin` 인데 사유가 없으면 **빨강**이다.
  ③ **거짓 초록 패턴** — `… | tail …; echo "$?"` 가 복사해 쓰는 자리에 남아 있는가.
     [실측 2026-09-07 · 턴 L] 그 한 줄이 **여덟 줄의 판정을 무의미하게** 만들었다.
     회고문이 그 실수를 **인용**한 문장은 위반이 아니다 — 울타리(```) 밖의 산문이다.

무엇이 이 게이트를 만들게 했나 — 출생 표본 넷 (D-310)
------------------------------------------------------
`scripts/_gate_header.py` 의 머리말에 적힌 넷이다. 넷 다 **초록이었고**, 넷 다
제품이 아닌 것을 재고 있었다:

    verify_tenant_scope  8월 라우트 사진(531)   ← 살아 있는 라우터는 705
    verify_write_auth    손으로 적은 분모 30    ← 살아 있는 쓰기 표면은 377
    verify_screens       역할 0 계정으로 걸음   ← 「됐다」가 아니라 「못 갔다」
    verify_minio         호스트 root 자격       ← 앱의 자격은 5자 자리표, 앱은 503

  자기시험이 이 넷을 **관측의 말로** 직접 시험한다. 거기서 초록이 나오면 이 파일은
  도구가 아니다.

    python scripts/verify_gate_header.py             # 판정 (게이트를 실제로 돌린다)
    python scripts/verify_gate_header.py --no-run    # ①③만 (돌리지 않는다 · 빠르다)
    python scripts/verify_gate_header.py --list      # 게이트별 머리글
    python scripts/verify_gate_header.py --self-test # 판정 규칙만

exit 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(게이트를 하나도 못 열었다)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gate_header import (KEY_AS, KEY_MEASURED, KEY_SOURCE, KEY_TARGET,  # noqa: E402
                          MEASURED_NONE, OTHER_LANE,
                          audit, escalation, gate_files, gate_header, judge_as,
                          judge_header, judge_measured, judge_source, pipe_scan,
                          pipe_violations, self_test_can_fail_audit)

#: ★★ [P-217 · 턴 AB · 차선 Q] **기한은 코드가 아니라 결정문에 있다.**
#:   턴 AA 가 「MEASURED 남은 회색 28 은 턴 AC 부터 빨강」을 **문서에만** 적었고,
#:   문서에 적힌 기한은 그날이 와도 색을 안 바꾼다 — 조용히 지나간다.
#:   ⇒ 기한은 `docs/agent/decisions.yaml` 의 `D-511::deadline` 에 있고,
#:     이 게이트가 **그 파일을 읽어서** 오늘과 댄다. 여기 날짜를 베끼지 않는다 —
#:     베끼면 결정문이 움직여도 이 줄이 거짓말한다(P-93).
MEASURED_DEADLINE_DECISION = "D-511"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[P-107]"
ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 게이트를 열어 보는 인자. 판정을 돌리지 않고 **머리글만** 나오게 하는 자리다.
#: (`--self-test` 이 없는 게이트는 argparse 가 죽지만, 머리글은 그 **앞에** 찍힌다.)
OPEN_ARGS = ["--self-test"]
OPEN_TIMEOUT = 150


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수다** (D-277). 관측만 먹는다
# ═══════════════════════════════════════════════════════════════════════════
def parse_header(text: str) -> dict:
    """게이트가 찍은 출력에서 세 줄을 뽑는다. 없으면 그 자리는 비어 있다."""
    out = {"target": "", "as": "", "source": "", "measured": "", "found": 0}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith(TAG):
            continue
        body = s[len(TAG):].strip()
        for key, slot in ((KEY_TARGET, "target"), (KEY_AS, "as"), (KEY_SOURCE, "source")):
            if body.startswith(key) and not out[slot]:
                out[slot] = body[len(key):].strip()
                out["found"] += 1
        #: ★ [P-204] 네 번째 줄은 **`found` 에 안 센다.** 세면 「세 줄 중 몇 줄」이
        #:   말이 달라지고, 머리글이 없는 게이트와 분모를 안 말한 게이트가 한 칸에 섞인다.
        if body.startswith(KEY_MEASURED) and not out["measured"]:
            out["measured"] = body[len(KEY_MEASURED):].strip()
    return out


def judge(observations: dict) -> list:
    """관측 → **(수 이름, 통과, 사유)** 세 줄.

    관측의 모양:
      {"declared": [(이름, 머리글부름?)…],
       "opened":   {이름: {"target":…, "as":…, "source":…, "found":n, "reason":…}},
       "pipes":    [(경로, 줄, 글, 종류)…],
       "other":    [(이름, 누구, 머리글?)…]}
    """
    out = []
    declared = observations.get("declared") or []
    opened = observations.get("opened") or {}
    pipes = observations.get("pipes")
    other = observations.get("other") or []

    # ① 보유 — 부르지 않는 게이트는 회색이다
    if not declared:
        out.append(("HEADER_DECLARED", False,
                    "게이트를 하나도 못 열거했다 — 판정이 아니라 열거기 고장이다 (D-301)"))
    else:
        missing = [n for n, ok in declared if not ok]
        out.append(("HEADER_DECLARED", not missing,
                    "게이트 %d개 중 %d개가 머리글을 부른다%s · 다른 차선 %d개는 자기 칸"
                    % (len(declared), len(declared) - len(missing),
                       "" if not missing else " · **회색 %d: %s**" % (len(missing), missing),
                       len(other))))

    # ② 성립 — **실제로 찍혔는가**. 소스에 적힌 것과 찍히는 것은 다른 사실이다
    if opened is None:
        out.append(("HEADER_LIVE", False, "게이트를 못 열었다 — 재지 못한 것이다"))
    elif not opened:
        out.append(("HEADER_LIVE", False,
                    "열어 본 게이트가 0개다 — **0건 검사는 통과가 아니다** (D-301)"))
    else:
        bad = []
        for name, h in sorted(opened.items()):
            if h.get("found", 0) < 3:
                bad.append("%s(세 줄 중 %d줄)" % (name, h.get("found", 0)))
                continue
            problems = judge_header(h.get("target", ""), h.get("as", ""),
                                    h.get("source", ""), h.get("reason", ""))
            if problems:
                bad.append("%s(%s)" % (name, problems[0][:70]))
        out.append(("HEADER_LIVE", not bad,
                    "%d개를 실제로 열어 세 줄을 받았다%s"
                    % (len(opened), "" if not bad
                       else " · **어긋남 %d: %s**" % (len(bad), bad[:6]))))

    # ③ 거짓 초록 패턴 — 복사해 쓰는 자리에 남은 것만
    if pipes is None:
        out.append(("PIPE_EXIT", False, "훑지 못했다 — 재지 않은 것은 초록이 아니다"))
    else:
        bad = pipe_violations(pipes)
        out.append(("PIPE_EXIT", not bad,
                    "`| tail … $?` 자리 %d건 (복사해 쓰는 자리 **%d** · 회고문 인용 %d)%s"
                    % (len(pipes), len(bad), len(pipes) - len(bad),
                       "" if not bad else " · " + str([h[0] + ":" + str(h[1]) for h in bad[:5]]))))

    # ④ ★ [P-204 · 턴 Y] **분모 — 무엇을 몇 건 쟀나.**
    #
    #   이 수는 **빨강이 아니라 회색**을 낸다(`None`). 「분모를 말하지 않는다」는
    #   「제품이 무너졌다」가 아니라 **「우리가 그 게이트에 대해 모른다」**이기 때문이다.
    #   회색은 초록이 아니다 — 러너는 2 로 받는다.
    if opened is None:
        out.append(("MEASURED_LINE", None,
                    "게이트를 안 열었다(`--no-run`) — 분모를 **물어보지 못했다**"))
    elif not opened:
        out.append(("MEASURED_LINE", None,
                    "열어 본 게이트가 0개다 — 분모를 물어볼 자리가 없었다 (D-301)"))
    else:
        gray = []
        for name, h in sorted(opened.items()):
            problems = judge_measured(h.get("measured", ""))
            if problems:
                gray.append("%s(%s)" % (name, problems[0][:46]))
        #: ★ 기한을 **결정문에 물어본다.** 셋 중 하나가 온다:
        #:     grey    아직 기한 전 — 회색(None)
        #:     red     기한이 왔다 — **빨강(False)**. 사람이 코드를 안 고쳐도 바뀐다
        #:     unknown 결정문을 못 읽었다 — 회색이되 **그 사실을 말한다**
        #:   ⚠ `unknown` 을 `grey` 와 같은 낱말로 적지 않는다. 결정문을 지운 것이
        #:     「아직 기한 전」으로 읽히면 배선이 조용히 꺼진 것이다.
        level, note = escalation(MEASURED_DEADLINE_DECISION,
                                 today=observations.get("today"))
        verdict = True if not gray else (False if level == "red" else None)
        out.append(("MEASURED_LINE", verdict,
                    "게이트 %d개 중 **%d개가 「무엇을 · 분모 N」을 말한다** · "
                    "**%s %d**(분모를 안 말하는 게이트는 그 `exit 0` 이 "
                    "「이 호출이 통과」일 뿐이다 · P-204)%s · [기한] %s"
                    % (len(opened), len(opened) - len(gray),
                       "빨강" if level == "red" else "회색", len(gray),
                       "" if not gray else " · " + str([g.split("(")[0] for g in gray[:8]]),
                       note)))

    # ⑤ ★★ [P-319 · P-323 · 턴 AI 차선 F] **TheSelfTestCanFail 짝 — 새 게이트부터.**
    #
    #   기존 게이트 수십 개를 한꺼번에 빨강으로 만들지 않는다 — `BASELINE_GATES_SELF_TEST_DEBT`
    #   에 얼려 둔 것은 **빚으로 항상 보이게** 출력한다(숨긴 빚은 거짓 초록이다 · P-322 ⓐ).
    #   이 목록에 없는 새 게이트만 판정한다: `SELF_TEST_LINKS` 에 적힌 짝이 **실재하는지**
    #   (파일이 있고 · `TheSelfTestCanFail` 이 구조로 있고 · 그 안에 「자기시험을 망가뜨려
    #   실패를 본다」는 시험이 있는지) `self_test_can_fail_audit` 가 매번 다시 연다 — 적어
    #   둔 것을 믿지 않는다(D-479 교훈).
    stl = observations.get("self_test_link")
    if stl is None:
        out.append(("SELF_TEST_CAN_FAIL", None, "TheSelfTestCanFail 짝을 안 물었다"))
    else:
        new_rows = [r for r in stl.get("rows", []) if r[1] == "new"]
        missing = stl.get("new_missing") or []
        debt = stl.get("baseline_debt", 0)
        out.append(("SELF_TEST_CAN_FAIL", not missing,
                    "새 게이트 %d개 중 짝 실재 %d개%s · **기준선 빚 %d**"
                    "(이 요구 전부터 있던 게이트 — 숨기지 않는다 · P-322 ⓐ)"
                    % (len(new_rows), len(new_rows) - len(missing),
                       "" if not missing
                       else " · **짝 없음(거짓 짝 포함) %d: %s**" % (len(missing), missing),
                       debt)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-310)
# ═══════════════════════════════════════════════════════════════════════════
def _good_observations() -> dict:
    return {
        "declared": [("verify_a.py", True), ("verify_b.py", True)],
        "opened": {
            "verify_a.py": {"found": 3,
                            "target": "http://localhost:8000 (gx-shell)",
                            "as": "gxprobe_q · 역할 fire_user · 자격 이름 GX_PROBE_PASSWORD",
                            "source": "살아 있는 라우터 (django get_resolver)", "reason": "",
                            "measured": "살아 있는 라우트를 HTTP 로 두드린다 · 분모 705"},
            "verify_b.py": {"found": 3,
                            "target": "저장소 @ 6cf2c19",
                            "as": "(자격증명 없음 — 소스를 읽는다)",
                            "source": "파일 docs/x.json (기록 2026-09-07T10:00)", "reason": "",
                            "measured": "선언된 절의 증거 줄 · 분모 112"},
        },
        "pipes": [("docs/agent/RESUME_NEXT.md", 4, "… | tail; echo $?", "인용(산문)")],
        "other": [("verify_front_line_502.py", "DevOps 차선", False)],
        #: [P-319 · P-323] 새 게이트 0 · 기준선 빚만 있는 성립한 상태.
        "self_test_link": {
            "rows": [("verify_a.py", "baseline", True, "기준선 빚")],
            "baseline_debt": 1, "new_total": 0, "new_missing": []},
    }


#: ★ **출생 표본** — 턴 L 의 넷을 관측의 말로 옮긴 것. **세 수가 다 빨강이어야 한다.**
#:
#:   그날 넷은 머리글을 **하나도 안 갖고 있었다**(이 규칙이 없었다). 그래서
#:   `declared` 는 넷 다 False 다 — 그것이 그날의 사실이다.
#:   `opened` 는 **「그날 억지로 세 줄을 적게 했다면 뭐라고 적혔을까」**를 옮긴 것이다:
#:   8월 사진에 날짜가 없고 · 손 목록의 출처가 비었고 · 역할 0 계정이라 AS 가 비었고 ·
#:   root 자격에 사유가 없다. 넷 다 지금 규칙에 걸린다.
def BIRTH_SAMPLE() -> dict:
    return {
        "declared": [("verify_tenant_scope.py", False), ("verify_write_auth.py", False),
                     ("verify_screens.py", False), ("verify_minio.py", False)],
        "opened": {
            # ① 8월 사진을 읽으면서 날짜를 안 적었다
            "verify_tenant_scope.py": {
                "found": 3, "target": "gx-shell",
                "as": "(자격증명 없음)",
                "source": "파일 docs/agent/evidence/W0-14/openapi_routes.json", "reason": ""},
            # ② 손 목록 30 — 어디서 왔는지 SOURCE 가 비어 있었다
            "verify_write_auth.py": {
                "found": 2, "target": "쓰기 표면 30자리", "as": "(자격증명 없음)",
                "source": "", "reason": ""},
            # ③ 역할 0 계정으로 걸었다 — AS 가 아예 없었다
            "verify_screens.py": {
                "found": 2, "target": "gxprobe_e2e 로 걸었다", "as": "",
                "source": "화면 사진 (기록 2026-09-07)", "reason": ""},
            # ④ 호스트 root 자격 — 사유 없이
            "verify_minio.py": {
                "found": 3, "target": "minio:9000",
                "as": "MINIO_ROOT_USER (호스트 .env)",
                "source": "살아 있는 저장소", "reason": ""},
        },
        "pipes": [("docs/agent/report.md", 12,
                   'python scripts/X.py 2>&1 | tail -18; echo "[exit=$?]"', "코드")],
        "other": [],
    }


def self_test() -> int:
    ok = True

    rows = judge(_good_observations())
    if not all(p for _, p, _ in rows):
        ok = False
        print("%s X 성립한 관측을 빨강으로 읽는다: %s" % (TAG, [n for n, p, _ in rows if not p]))
    else:
        print("%s O 성립한 관측 %d/%d 초록 (양성 대조)" % (TAG, len(rows), len(rows)))

    mutants = {}
    m = _good_observations(); m["declared"][1] = ("verify_b.py", False)
    mutants["HEADER_DECLARED"] = ("머리글을 안 부르는 게이트가 섞였다", m)
    m = _good_observations(); m["opened"]["verify_a.py"]["as"] = "root"
    mutants["HEADER_LIVE"] = ("사유 없는 AS=root 로 쟀다", m)
    #: ★★ [P-319 · P-323 · 턴 AI 차선 F] 새 게이트가 짝 없이 태어난 그 모양 그대로.
    m = _good_observations()
    m["self_test_link"] = {
        "rows": [("verify_new_thing.py", "new", False, "SELF_TEST_LINKS 에 짝이 없다")],
        "baseline_debt": 0, "new_total": 1, "new_missing": ["verify_new_thing.py"]}
    mutants["SELF_TEST_CAN_FAIL"] = ("새 게이트가 TheSelfTestCanFail 짝 없이 태어났다", m)
    m = _good_observations(); m["pipes"] = [("scripts/x.sh", 3, "x | tail; echo $?", "코드")]
    mutants["PIPE_EXIT"] = ("복사해 쓰는 자리에 `| tail … $?` 가 남았다", m)

    caught = 0
    for name, (label, obs) in mutants.items():
        verdicts = dict((n, p) for n, p, _ in judge(obs))
        if verdicts.get(name) is False:
            caught += 1
        else:
            ok = False
            print("%s X 변이 「%s — %s」를 못 잡는다" % (TAG, name, label))
    print("%s O 변이 %d/%d 를 잡는다 (음성 대조 · 규칙)" % (TAG, caught, len(mutants)))

    # ★ 출생 표본 — 턴 L 의 넷. **세 수가 다 빨강**이어야 한다
    born = judge(BIRTH_SAMPLE())
    if any(p for _, p, _ in born):
        ok = False
        print("%s X 출생 표본을 다 못 잡는다: %s — 이 도구가 태어난 사유가 안 재진다"
              % (TAG, [n for n, p, _ in born if p]))
    else:
        print("%s O 출생 표본 3/3 빨강 — 턴 L 의 게이트 넷(사진·손목록·역할0·root)을 잡는다"
              % TAG)

    # 넷을 하나씩도 잡는가 — **넷이 뭉쳐서 잡히는 것**과 다르다
    one_by_one = 0
    for name, h in BIRTH_SAMPLE()["opened"].items():
        obs = _good_observations()
        obs["opened"] = {name: h}
        if dict((n, p) for n, p, _ in judge(obs)).get("HEADER_LIVE") is False:
            one_by_one += 1
        else:
            ok = False
            print("%s X 출생 표본 「%s」를 혼자서는 못 잡는다" % (TAG, name))
    print("%s O 출생 표본 %d/4 를 **하나씩도** 잡는다" % (TAG, one_by_one))

    # 관측 0건은 초록이 아니다 (D-301)
    if any(p for _, p, _ in judge({})):
        ok = False
        print("%s X 관측 0건을 초록으로 읽는다 — 못 잰 것이 통과가 되지 않는다" % TAG)
    else:
        print("%s O 관측 0건은 세 수 다 빨강 (회색이 초록이 되지 않는다)" % TAG)

    # ★★ **P-204 출생 표본** — [실측 2026-09-20 · 턴 Y] 이 규칙을 만든 두 사례.
    #
    #   그날 두 게이트가 **exit 0** 을 냈고 세 줄(TARGET/AS/SOURCE)도 다 성립했다.
    #   그런데 둘 다 **살아 있는 것을 한 자리도 안 쟀다**:
    #     · `verify_evidence_chain`  `--db` 없이 소스만 읽고 0 → 대장은 LAW-08 을 초록으로 적었다
    #     · `verify_onboarding_walk` `--api` 없이 구조만 보고 0 → UX-46 이 **걸어 본 적 없이** 초록
    #   머리글 셋은 「누구로 · 어디서 · 무엇을 향해」를 말하지만 **「몇 건을 쟀나」는
    #   말하지 않는다.** 그래서 넷째 줄이 생겼다.
    _P204_SAMPLE = [
        ("살아 있는 감사표를 행마다 다시 계산 · 분모 240", True,
         "무엇을 · 분모 몇으로 쟀는지 말한다"),
        ("온보딩 카드를 실제로 걷는다 · 분모 38장", True, "같은 모양"),
        ("", False, "★ 아무 말도 안 한다 — 그 `exit 0` 은 「이 호출이 통과」일 뿐이다"),
        ("(선언 없음 — 이 게이트는 무엇을 쟀는지 말하지 않는다)", False,
         "★ 「말 안 했다」고 적은 줄은 **없는 것과 같다**"),
        ("살아 있는 감사표를 다시 계산한다", False, "★ 분모가 없다 — 0건 검사와 전수가 같은 글자"),
        ("`--db` 없이 불렀다 · 분모 0", False, "★ **분모 0인 초록은 초록이 아니다** (D-301)"),
        ("계약 진입면을 HTTP 로 때린다 · 분모 109", True, "분모가 있다"),
    ]
    _pbad = [why for text, want, why in _P204_SAMPLE
             if (not judge_measured(text)) is not want]
    if _pbad:
        ok = False
        print("%s X ★ P-204 출생 표본이 깨졌다: %s" % (TAG, _pbad[:3]))
    else:
        print("%s O ★ **P-204 출생 표본 %d — 「`exit 0` 은 「이 호출이 통과」다」** "
              "(분모 없음·분모 0·선언 없음을 다 잡는다 · 턴 Y 의 evidence_chain·onboarding_walk)"
              % (TAG, len(_P204_SAMPLE)))

    # 그리고 **수 하나로도** 잡히는가 — 분모를 안 말하는 게이트가 섞이면 그 수는 회색이다
    #: ★ [실측 2026-09-24 · 차선 F] `today` 를 **못 박는다.** D-511 기한(09-23)이 지나면
    #:   `escalation()` 이 스스로 red 를 낸다(그것이 P-217 배선의 목적이다) — 그런데 이
    #:   시험은 「기한과 무관한 steady-state 회색」만 보려는 자리다. 벽시계 날짜에 걸리면
    #:   기한이 지난 **모든 날**에 이 시험이 자기 뜻과 다르게 빨개진다. 기한 앞뒤 판정은
    #:   아래 [기한] 전용 시험이 이미 따로 잰다 — 여기서는 **기한 전**으로 고정한다.
    _m = _good_observations()
    _m["opened"]["verify_b.py"]["measured"] = ""
    _m["today"] = "2026-09-21"
    _verdict = dict((n, p_) for n, p_, _w in judge(_m)).get("MEASURED_LINE")
    if _verdict is None:
        print("%s O ★ 분모를 안 말하는 게이트가 하나 섞이면 MEASURED_LINE 은 **회색**이다 "
              "(빨강이 아니다 — 「제품이 무너졌다」가 아니라 「우리가 모른다」이므로)" % TAG)
    else:
        ok = False
        print("%s X 분모를 안 말하는 게이트가 섞였는데 MEASURED_LINE=%r 다 — "
              "회색이어야 한다 (P-204)" % (TAG, _verdict))

    # ★★ [P-217 · 턴 AB] **기한 배선 — 문서가 아니라 이 줄이 집행한다**
    #    기한 전 회색 · 기한 후 **빨강** · 결정문을 못 읽으면 **회색 + 사유**.
    #    세 갈래를 다 붙인다. 붙이지 않으면 기한이 와도 아무도 모른다.
    _d = _good_observations()
    _d["opened"]["verify_b.py"]["measured"] = ""
    _d["today"] = "2026-09-21"
    if dict((n, p_) for n, p_, _w in judge(_d)).get("MEASURED_LINE") is None:
        print("%s O ★ [기한] 그날 **전**에는 회색이다 — 「아직 아니다」" % TAG)
    else:
        ok = False
        print("%s X 기한 전인데 회색이 아니다" % TAG)
    _d["today"] = "2026-09-30"
    if dict((n, p_) for n, p_, _w in judge(_d)).get("MEASURED_LINE") is False:
        print("%s O ★★ [기한] 그날 **뒤**에는 **빨강**이다 — 사람이 코드를 "
              "안 고쳐도 색이 바뀐다 (D-511 · 결정문이 집행한다)" % TAG)
    else:
        ok = False
        print("%s X 기한이 지났는데 빨강이 아니다 — **기한이 조용히 지나갔다.** "
              "이 배선이 막으려던 바로 그 모양이다 (P-217)" % TAG)
    #: ★ 분모를 **다 말하면** 기한이 지나도 초록이다 — 기한은 회색을 빨강으로
    #:   올릴 뿐, 없는 어긋남을 만들지 않는다.
    _d2 = _good_observations()
    _d2["today"] = "2026-09-30"
    if dict((n, p_) for n, p_, _w in judge(_d2)).get("MEASURED_LINE") is True:
        print("%s O ★ [기한] 분모를 다 말하면 기한이 지나도 **초록**이다 "
              "(없는 빨강을 만들지 않는다)" % TAG)
    else:
        ok = False
        print("%s X 기한이 회색 0건에도 색을 바꿨다 — 없는 어긋남이다" % TAG)
    _lvl, _note = escalation("D-000-없는-결정문")
    if _lvl == "unknown" and "없다" in _note:
        print("%s O ★★ [기한] 결정문을 **지우면 꺼지지 않고 「못 읽었다」고 말한다** "
              "— 조용히 꺼지는 배선은 배선이 아니다" % TAG)
    else:
        ok = False
        print("%s X 결정문이 없는데 %r 로 지나갔다 — 배선이 조용히 꺼졌다"
              % (TAG, _lvl))

    # 판정기의 조각들이 살아 있는가 (D-289 — 규칙을 지우면 잡히지 않는다)
    if judge_as("admin") and judge_source("파일 x/y.json") and not judge_as("gxprobe_q"):
        print("%s O 술어 셋(root·날짜·정상)이 살아 있다" % TAG)
    else:
        ok = False
        print("%s X 술어가 무뎌졌다 — `_gate_header.judge_*` 를 먼저 의심한다" % TAG)
    return EXIT_OK if ok else EXIT_FAIL


# ═══════════════════════════════════════════════════════════════════════════
# 관측 — 게이트를 **실제로 연다**
# ═══════════════════════════════════════════════════════════════════════════
def open_gate(path: Path, timeout: int = OPEN_TIMEOUT) -> dict:
    """게이트를 열어 머리글 세 줄을 받는다. 못 열면 빈 자리(=빨강)."""
    try:
        proc = subprocess.run([sys.executable or "python", str(path)] + OPEN_ARGS,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, cwd=str(ROOT))
    except (OSError, subprocess.SubprocessError):
        return {"target": "", "as": "", "source": "", "found": 0}
    text = proc.stdout.decode("utf-8", "replace")
    h = parse_header(text)
    # `reason=` 는 `AS=` 줄 뒤에 붙어 나온다 — 판정이 그것을 볼 수 있어야 한다
    h["reason"] = h["as"].split("· 사유:", 1)[1].strip() if "· 사유:" in h["as"] else ""
    return h


def observe(run: bool = True) -> dict:
    a = audit()
    #: [P-319 · P-323] 구조 확인이라 `--no-run` 에도 잰다 — 게이트를 **열지 않고** 그
    #: 짝(파일 + 클래스)만 읽는다. `HEADER_LIVE`(②)와 다른 층이다.
    obs = {"declared": a["rows"], "other": a["other"],
           "pipes": pipe_scan(), "opened": {},
           "self_test_link": self_test_can_fail_audit()}
    if not run:
        obs["opened"] = None
        return obs
    for p in gate_files():
        if p.name in OTHER_LANE:
            continue
        obs["opened"][p.name] = open_gate(p)
    return obs


def main() -> int:
    ap = argparse.ArgumentParser(description="게이트 머리글 (P-107)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-run", action="store_true",
                    help="게이트를 열지 않는다 (①③만 · 빠르다)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 빨강이다 — 판정을 신뢰할 수 없다" % TAG)
        return rc

    obs = observe(run=not args.no_run)
    n_open = len(obs["opened"] or {})
    print("%s [입력] 게이트 %d개 · 실제로 연 것 %d개 · 파이프 자리 %d건 · 다른 차선 %d개"
          % (TAG, len(obs["declared"]), n_open, len(obs["pipes"]), len(obs["other"])))

    if not obs["declared"]:
        print("%s ? **못 쟀다** — scripts/verify_*.py 를 하나도 못 찾았다" % TAG)
        return EXIT_UNDECIDABLE

    if args.list:
        for name, h in sorted((obs["opened"] or {}).items()):
            print("  %-34s 세 줄 %d" % (name, h.get("found", 0)))
            for key in ("target", "as", "source", "measured"):
                print("      %-8s %s" % (key.upper(), (h.get(key) or "(없다)")[:150]))
        for name, who, ok in obs["other"]:
            print("  (다른 차선) %-30s %s · 머리글 %s" % (name, who, "있음" if ok else "없음"))
        print("%s ? **못 쟀다** — `--list` 는 머리글을 **찍을 뿐** 판정하지 않는다 (P-204)" % TAG)
        return EXIT_UNDECIDABLE

    rows = judge(obs)
    #: ★ [P-204] **빨강과 회색을 가른다.** `None` 은 「안 잼」이고 `False` 는 「재서 틀림」이다.
    #:   `not passed` 하나로 묶으면 둘이 같은 칸에 들어가고, 그러면 회색을 고치는 일과
    #:   빨강을 고치는 일이 같은 일로 보인다 — 다른 일이다.
    failed = [(n, why) for n, passed, why in rows if passed is False]
    grayed = [(n, why) for n, passed, why in rows if passed is None]
    print("%s 수 %d" % (TAG, len(rows)))
    for name, passed, why in rows:
        print("  %s  %-16s %s"
              % ("O" if passed is True else ("?" if passed is None else "X"), name, why))
    if args.no_run:
        print("%s ⚠ `--no-run` 이다 — ②는 **재지 않았다**. 회색을 초록으로 읽지 않는다" % TAG)
    if failed:
        print("%s 실패 %d/%d — **무엇을 쟀는지 말하지 않는 게이트가 남아 있다**"
              % (TAG, len(failed), len(rows)))
        return EXIT_FAIL
    if grayed:
        print("%s ? **회색 %d/%d** — %s" % (TAG, len(grayed), len(rows),
                                            " · ".join(n for n, _ in grayed)))
        print("%s 회색은 초록이 아니다 — 이 호출은 **통과가 아니라 「못 잰 것」**이다 (P-204)"
              % TAG)
        return EXIT_UNDECIDABLE
    print("%s 통과 %d/%d — 게이트마다 TARGET/AS/SOURCE 와 **분모**를 먼저 말한다"
          % (TAG, len(rows), len(rows)))
    return EXIT_OK


if __name__ == "__main__":
    _n_gate = len([p for p in gate_files() if p.name not in OTHER_LANE])
    gate_header(
        __file__,
        measured=("게이트마다 ① 머리글을 부르는가 ② 열어 보면 세 줄이 **실제로 찍히는가** "
                  "③ `| tail … $?` 거짓 초록 자리 ④ **MEASURED 줄로 분모를 말하는가** — "
                  "**분모 %d**(scripts/verify_*.py · 다른 차선 %d개는 제 칸) · "
                  "`--no-run` 이면 ②④는 분모 0 이고 그 실행은 회색이다 (P-204)"
                  % (_n_gate, len(OTHER_LANE))),
        target="이 저장소의 scripts/verify_*.py 를 **실제로 연다** (읽어서 답하지 않는다)",
        as_="(자격증명 없음 — 게이트를 자기 자리에서 돌리고 그 첫 세 줄을 읽는다)",
        source="게이트들이 지금 찍은 머리글 + 저장소 작업본 트리",
    )
    raise SystemExit(main())
