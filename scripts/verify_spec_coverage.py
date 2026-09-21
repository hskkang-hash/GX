# -*- coding: utf-8 -*-
"""P-234 — **기능명세서 포함 완료율**을 산출기가 낸다 (2026-09-21 · 턴 AB · 차선 Q).

왜 이 파일이 생겼나
-------------------
세종이 WO-04 §1 에 새 정본 줄 하나를 더했다:

    기능명세서 포함 완료율 ≈ 29 %   [세종 산출 · 산출기 아님]
      (155절 × 54.1 % = 83.9 절-점) ÷ (155 + DSM 32 + FWS 90 + 운영자 12 = 289)

그 수는 **손으로 적힌 수**다. 손으로 적은 수는 정본이 움직여도 안 움직인다(P-93).
P-234 가 그래서 「산출기(Q)가 낸다 · **손으로 적지 않는다**」고 못박았다.

★★ 그런데 전제가 **두 군데** 틀렸다 — 손대기 전에 대 봤다
----------------------------------------------------------
  [조율자 실측 09-21]  「그 문서들에 안정된 id 가 없다 (`DSM-01` 같은 표식 **0건**)」
  [차선 N 독립 재확인]  같은 결론 · 표 데이터행 **100 · 230 · 143 = 473**
  [Q 실측   09-21]     ★ **id 는 있다. 두 실측이 서로를 확인했지만 둘 다 못 찾았다.**
                       ① 그물이 틀렸다 — 실재 표식은 `DSM-01` 이 아니라
                          **`DSM-U1-01`** 이다. `DSM-U<역할>-<번호>` 로 뽑으면
                          **32건**이 한 번에 나온다. 「0건」은 「없다」가 아니라
                          **「못 찾았다」**였다. 이 파일이 막으려는 병이 바로 그것이다.
                       ② **473 은 다른 분모다.** 그것은 세 문서의 **모든** 표
                          데이터행(§5 업무처리명세 · §6~§9 화면구성도 · 매핑표까지)
                          이고, 이 도구가 세는 것은 **「사용자별 세부 기능명세」
                          절의 항목**뿐이다. 473 과 136 은 **다른 것을 센 두 수**이지
                          갈린 한 수가 아니다.
                       ⇒ **두 사람이 같은 답을 냈다고 해서 그 답이 실물은 아니다.**
                          같은 그물을 두 번 던지면 같은 0 이 두 번 나온다.
                          그래서 이 도구는 **그물을 소스에 적어** 다음 사람이
                          그물부터 의심할 수 있게 한다.

  [세종 판독]          운영자 콘솔 **12**
  [Q 실측   09-21]     ★ **14** 다 — 플랫폼 구조 설계서 §7 은 `O-01`~`O-14` 를 적는다.
                       ⇒ **분모가 둘 늘고, 수가 내려간다. 내려간 수가 정본이다.**

⚠ **별표 ②(기능명세)는 8영역 밖이다** [조율자 판정 · 턴 AB]. 8영역은 가중치 합 100
  으로 **상용/100** 을 만든다. 수백 항목을 그 안에 끼우면 가중치 표가 무너지고 상용
  점수가 다른 뜻이 된다. ⇒ **상용/100 은 절 155 그대로**이고, 이 도구의 수는
  **제 분모를 따로 가진다**(대장 절 + 미등재 명세 항목). 차선 N 이 대장 꼭대기에
  `annex_2_spec` 자리를 세웠고, 이 도구가 내는 목록이 그 자리의 입력이다.

그래서 이 도구의 한 줄
----------------------
    **세는 규칙을 코드에 적고, 그 규칙으로 기계가 뽑은 목록을 세서 분모로 쓴다.**
    규칙이 낸 수가 [세종 판독]과 다르면 **규칙이 낸 수가 정본**이고,
    다르다는 사실을 판정문이 먼저 말한다.

세는 규칙 — **이 절이 분모의 정의다**
-------------------------------------
  ① 한 항목 = 세 명세서의 「사용자별 **세부 기능명세**」 절이 부여한 **id 표식 하나**.
     문서마다 표식의 모양이 하나씩 못박혀 있다(아래 `SPEC_SOURCES`):
         DSM  §4  `DSM-U<역할>-<번호>`   (표 데이터행 하나 = 한 항목)
         FWS  §5  `FWS-[FU]<역할>-<번호>` (5.1~5.6 은 표 · **5.7 은 문단**이다)
         플랫폼 §7 `O-<번호>`             (표의 `#` 칸)
  ② **표 데이터행이 아니라 id 를 센다.** 처음에는 「§4·§5 의 표 데이터행 하나 =
     한 항목」으로 잡았는데 그러면 **FWS 5.7 의 다섯(`FWS-U5-01`~`05`)을 놓친다** —
     그 다섯은 표가 아니라 **문단 안에** 적혀 있다. 행을 세면 85, id 를 세면 90 이다.
     ★ **세종의 「FWS 90」과 맞는 쪽은 id 다.** 그래서 규칙을 id 로 정했다.
  ③ **같은 id 는 한 번만 센다.** DSM 문서에 `DSM-U2-05` 가 두 번 나오는데(본문
     인용 1) 둘을 세면 분모가 34 가 된다 — 한 번만 센다.
  ④ 세 문서 **밖**은 안 센다. PRD v1.1 은 같은 id 를 `DSM-U1-01~06` 처럼 **범위로**
     인용한다. 인용을 세면 같은 항목이 두 번 분모에 든다.
  ⑤ 뽑은 목록을 `docs/agent/evidence/P-234/spec_ids.json` 으로 낸다 —
     **그 파일이 차선 N 의 등재 입력이다.** 분모는 그 파일을 **센 수**다.

점수를 어떻게 매기나 — **0 과 회색을 가른다**
---------------------------------------------
    대장(`ga_readiness.yaml`)에 **등재된** id → 대장의 `kind` 점수를 쓴다
                                                (N 과 **같은 눈금** · D-369)
    대장에 **없는** id                        → **0 점이되 분모에 남는다**

  ★ 그 0 의 뜻은 **「기능이 없다」가 아니라 「대장에 없다」**이다. P-231 이
    「증거 경로가 대장에 실린 절만 closed」라고 못박았으므로, **등재되지 않은 항목은
    닫힘일 수 없다.** 이것은 추측이 아니라 대장의 성질이고, 기계가 확인한다.
  ★ 그래서 이 도구는 **한 수를 내지 않는다** — 대장 절과 같은 규칙으로:
        측정치 = 미등재를 0 으로 (대장의 `unmeasurable` 과 같은 취급)
        상한   = 미등재를 1 로   (「다 되어 있는데 안 적었다」의 최댓값)
    둘의 폭이 **우리가 모르는 만큼**이고, 등재 한 줄이 그 폭을 좁힌다.
  ★ **분자를 못 읽으면 수를 내지 않는다.** 대장을 못 부르면 **회색(exit 2)**이다 —
    분모만 있고 분자가 없는 수는 수가 아니다.

⚠⚠ **분모는 「절 + 별표 전수」다. 「절 + 미등재」가 아니다.**
  첫 판은 `대장 절 수 + **미등재** id 수` 로 셌고, 그 식은 「등재하면 대장 절 수에
  들어간다」를 전제했다. **안 들어간다** — 별표 ②는 **8영역 밖**이기 때문이다
  (조율자 판정 · 8영역은 가중치 합 100 으로 상용/100 을 만든다). 그래서 등재된 136 은
  「부류 N절」 줄에도 없고 「미등재」에서도 빠졌고, **분모가 291 → 155 로 새면서
  수가 25.6 → 50.0 으로 올라갔다.** 자세한 것은 `_DEN_LINES` 의 주석에 있다.
  ⇒ 분모는 대장이 찍는 **분모 정본 줄**에서 읽는다 — **등재 여부와 무관하다.**
  ⇒ 등재가 늘어도 **분모는 안 움직이고**, 별표가 닫히는 날 **분자만** 오른다.
    (등재는 일을 한 것이 아니라 적은 것이므로 수를 올리지 않는다 — 그 뜻은 그대로다.)

부르는 방향
-----------
    **호스트에서** — 이 도구는 `verify_ga_readiness.py` 를 **부른다**(그 안에
    `docker exec` 가 있다). gx-shell 안에서 부르면 뜻 없는 회색이 난다.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TAG = "[SPEC]"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

DESIGN = ROOT / "docs" / "design"
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-346" / "ga_readiness.yaml"
GA_SCRIPT = ROOT / "scripts" / "verify_ga_readiness.py"
WO_DIR = ROOT / "docs" / "workorders"
WO_GLOB = "WO-GX-20260921-04_*.md"
OUT_JSON = ROOT / "docs" / "agent" / "evidence" / "P-234" / "spec_ids.json"

EXIT_OK, EXIT_RED, EXIT_GREY = 0, 1, 2

#: 세는 규칙 ① — 문서 하나 · 표식 하나 · 그 표식이 사는 절 하나.
#: ⚠ 파일 이름을 **글자로** 적지 않는다(이름에 날짜가 붙어 있고 판이 오르면 바뀐다).
#:   앞머리로 찾고, **둘 이상 맞으면 빨강**이다 — 어느 것을 읽었는지 모르는 수는 수가 아니다.
SPEC_SOURCES = (
    {"key": "DSM", "prefix": "DSM_재난안전관리App_명세서_",
     "pattern": r"\bDSM-U\d+-\d+\b", "section": "§4 사용자별 세부 기능명세",
     "cpo_label": "DSM 지침"},
    {"key": "FWS", "prefix": "FWS_산불감시App_명세서_",
     "pattern": r"\bFWS-[FU]\d+-\d+\b", "section": "§5 사용자별 세부 기능명세",
     "cpo_label": "FWS"},
    {"key": "OPS", "prefix": "GuardianX_플랫폼구조설계서_",
     "pattern": r"\bO-\d{2}\b", "section": "§7 플랫폼 운영자(U0) 세부 기능명세",
     "cpo_label": "운영자 콘솔"},
)

#: [세종 판독] — WO-04 가 **적어 둔** 수. 규칙이 낸 수와 대조하려고 읽는다.
#: ⚠ 값을 여기 베끼지 않는다. 베끼는 순간 지시서가 움직여도 이 줄이 거짓말한다.
CPO_LINE = re.compile(
    r"DSM\s*지침\s*(\d+)\s*[·+]\s*FWS\s*(\d+)\s*[·+]\s*운영자\s*콘솔\s*(\d+)")


# ═══════════════════════════════════════════════════════════════════════════
# ① 표식을 뽑는다 — **규칙이 여기 있고, 분모는 이 함수가 낸 목록의 길이다**
# ═══════════════════════════════════════════════════════════════════════════

def find_source(prefix: str) -> tuple[Path | None, str]:
    """앞머리로 명세서를 찾는다. **둘 이상이면 빨강** — 어느 것인지 모른다."""
    if not DESIGN.is_dir():
        return None, "`docs/design/` 이 없다"
    hits = sorted(p for p in DESIGN.glob(prefix + "*.md") if p.is_file())
    if not hits:
        return None, "`%s*.md` 가 **없다**" % prefix
    if len(hits) > 1:
        return None, ("`%s*.md` 가 **%d개**다 (%s) — 어느 것을 센 수인지 모르는 "
                      "분모는 분모가 아니다"
                      % (prefix, len(hits), " · ".join(p.name for p in hits)))
    return hits[0], ""


def extract_ids(text: str, pattern: str) -> list[str]:
    """규칙 ①③ — 표식을 뽑고 **같은 id 는 한 번만** 센다. 나온 순서를 지킨다.

    ★ 순서를 지키는 이유: 이 목록이 N 의 등재 입력이고, 문서 순서대로 등재하면
      사람이 문서와 대장을 나란히 놓고 읽을 수 있다.
    """
    seen, out = set(), []
    for m in re.finditer(pattern, text):
        i = m.group(0)
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def collect() -> tuple[dict, list[str], list[str]]:
    """세 문서에서 표식을 뽑는다 → `(per_doc, red, grey)`."""
    per: dict = {}
    red: list[str] = []
    grey: list[str] = []
    for spec in SPEC_SOURCES:
        path, why = find_source(spec["prefix"])
        if path is None:
            if "없다" in why and "개" not in why:
                grey.append("%s: %s — 문서가 없으면 그 칸은 **0 이 아니라 회색**이다"
                            % (spec["key"], why))
            else:
                red.append("%s: %s" % (spec["key"], why))
            per[spec["key"]] = {"path": None, "ids": [], "why": why,
                                "section": spec["section"],
                                "cpo_label": spec["cpo_label"]}
            continue
        ids = extract_ids(path.read_text(encoding="utf-8", errors="replace"),
                          spec["pattern"])
        if not ids:
            grey.append("%s: `%s` 에서 표식 **0건** — 0 은 분모가 아니다. "
                        "그물(`%s`)이 문서의 표식 모양과 다른지 먼저 의심한다 "
                        "(「0건」은 「없다」가 아니라 「못 찾았다」일 수 있다)"
                        % (spec["key"], path.name, spec["pattern"]))
        per[spec["key"]] = {"path": path, "ids": ids, "why": "",
                            "section": spec["section"],
                            "cpo_label": spec["cpo_label"]}
    return per, red, grey


# ═══════════════════════════════════════════════════════════════════════════
# ② 대장 — 등재됐나 · 절 수와 kind 점수는 얼마인가
# ═══════════════════════════════════════════════════════════════════════════

def ledger_text() -> str:
    return (LEDGER.read_text(encoding="utf-8", errors="replace")
            if LEDGER.is_file() else "")


def registered(ids: list[str], text: str) -> set[str]:
    """대장에 **`id:` 칸으로** 실린 표식만 등재로 센다.

    ⚠ 본문 어디엔가 글자가 스쳐도 등재가 아니다 — 주석에 이름이 나오는 것과
      절로 실린 것은 다르다. 그래서 `id:` 자리에서만 찾는다.
    """
    if not text:
        return set()
    have = set()
    for m in re.finditer(r"^\s*-?\s*id:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*$",
                         text, re.M):
        have.add(m.group(1))
    return {i for i in ids if i in have}


def run_ga() -> tuple[str, int | None]:
    """대장 게이트를 **부른다**(읽어서 답하지 않는다 · D-210).

    ★★ **`--static` 으로 부른다. `--no-gates` 가 아니다** [차선 N 실측 · 턴 AB].
      `--no-gates` 는 **절의 게이트만 끄고 영역 ①의 게이트는 그대로 부른다** —
      그 갈래에서 `verify_contract_route_reach.py` 가 **로그인한다.** N 이 모르고
      세 번 로그인했다. **로그인을 0 으로 만드는 것은 `--static` 뿐이다.**
      이 도구가 필요한 것은 **부류 셈과 절 수**뿐이고 그 둘은 대장이 내는 수이지
      자식 게이트가 내는 수가 아니다 — 그래서 로그인할 이유가 처음부터 없다.
      ⇒ **로그인 창이 없는 차선은 `--static` 으로 부른다**(턴 AB 규약).
    """
    if not GA_SCRIPT.is_file():
        return "", None
    try:
        p = subprocess.run([sys.executable, str(GA_SCRIPT), "--static"],
                           capture_output=True, timeout=900, cwd=str(ROOT))
    except (OSError, subprocess.TimeoutExpired) as exc:        # noqa: BLE001
        return "부르지 못했다: %s" % exc, None
    return ((p.stdout or b"").decode("utf-8", "replace")
            + (p.stderr or b"").decode("utf-8", "replace")), p.returncode


def kind_table() -> tuple[dict, str]:
    """눈금 표는 **한 벌**이다 — 차선 Q 의 `verify_readiness_scores` 가 이미
    N 쪽에서 가져오는 일을 한다. 여기서 또 한 벌을 두지 않는다(D-369)."""
    try:
        from verify_readiness_scores import aa_kind_score_table
    except Exception as exc:                                   # noqa: BLE001
        return {}, "눈금 표를 못 가져왔다: %s" % exc
    return aa_kind_score_table()


def ga_roll(out: str):
    """`… 부류 155절 — closed 68 · …` 한 줄을 읽는다."""
    try:
        from verify_readiness_scores import parse_ga_kinds
    except Exception:                                          # noqa: BLE001
        return None
    return parse_ga_kinds(out or "")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 수 — 분모는 **센 수**이고, 분자를 못 읽으면 수를 내지 않는다
# ═══════════════════════════════════════════════════════════════════════════

#: ═══════════════════════════════════════════════════════════════════════
#: ★★★ [P-234 고침 · 2026-09-21 턴 AB · 차선 N 이 잡았다]
#:      **분모가 두 칸 사이로 샜다 — 그리고 수가 올라갔다**
#:
#: 무엇이 있었나
#: ------------
#:     등재 전:  25.6 % = 77.5 ÷ **291**  (절 155 + 미등재 136)
#:     등재 후:  **50.0 %** = 77.5 ÷ **155**  (절 155 + 미등재 **0**)
#:
#:   첫 판의 분모는 `대장 절 수 + **미등재** 명세 항목` 이었고, 그 식은
#:   **「등재하면 대장 절 수에 들어간다」**를 전제했다. **안 들어간다.**
#:   별표 ②(기능명세)는 **8영역 밖**이다 — 조율자 판정이고, 사유는
#:   8영역이 가중치 합 100 으로 **상용/100** 을 만들기 때문이다(수백 항목을
#:   그 안에 끼우면 가중치 표가 무너지고 상용 점수가 다른 뜻이 된다).
#:   그래서 등재된 136 은 「부류 N절」 줄에도 **없고**, 「미등재」에서도 **빠졌다.**
#:
#: ★★ **이것은 「분모가 늘어 수가 내려가면 첫 줄이다」의 거울상이다.**
#:    **분모가 줄어 올라간 수는 수가 아니다** — 재는 것이 깨져서 수가 좋아진 것이라
#:    내려간 수보다 위험하다. **아무도 안 본다.**
#:
#: ★★ 그리고 **내 자기시험이 이것을 못 잡았다** [N 지적]. `분모 291` 검사가
#:    `n_sections=155` 를 **손으로 넣어** 통과했다 — 실물이 무너졌는데 초록이었다.
#:    **분모를 손으로 넣는 자기시험은 분모를 안 재는 자기시험이다.**
#:    내가 이 턴에 다른 게이트에서 지킨 바로 그 규율이고, 내 시험에서만 안 지켰다.
#:
#: 고친 자리 — **한 줄이다**
#: ------------------------
#:   차선 N 이 대장 게이트에 **분모 정본 줄**을 박았다(별표 0건이어도 늘 찍힌다).
#:   이 도구는 이제 **그 줄을 읽는다.** 분모는 **등재 여부와 무관하게 절 + 별표**다.
#:   ⚠ **별표를 8영역 안으로 옮겨 고치지 않는다** — 내 분모는 맞아지지만
#:     가중치 합 100 이 무너져 **상용/100 이 다른 뜻**이 된다.
_DEN_LINES = (
    # N 이 박은 모양 ①  `분모 정본 — 절 155 · 별표 136 · 합 291`
    re.compile(r"분모\s*정본\s*[—:-]\s*절\s*(\d+)\s*[·+]\s*별표\s*(\d+)"
               r"\s*[·+]\s*합\s*(\d+)"),
    # N 이 박은 모양 ②  `kind 표 정본 = 155 + 136 = 291`
    re.compile(r"정본\s*=\s*\*{0,2}(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)"),
)


def parse_denominator(out: str):
    """대장이 **제 입으로 적은 분모 정본**을 읽는다 → `(절, 별표, 합, 사유)`.

    못 읽으면 `(None, None, None, 사유)` — **0 이 아니다.**
    ★ 셋을 다 읽고 **덧셈이 맞는지 여기서 댄다.** 안 맞으면 그 줄이 거짓이고,
      거짓 분모로 낸 수는 수가 아니다.
    """
    for rx in _DEN_LINES:
        m = rx.search(out or "")
        if not m:
            continue
        a, b, c = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if a + b != c:
            return None, None, None, (
                "대장이 적은 분모 정본이 **제 덧셈과 안 맞는다** — 절 %d + 별표 %d "
                "= %d 인데 합을 %d 라 적었다. 거짓 분모로 낸 수는 수가 아니다"
                % (a, b, a + b, c))
        return a, b, c, ""
    return None, None, None, (
        "대장이 **분모 정본 줄을 안 찍는다** — `절 N · 별표 M · 합 N+M` 을 "
        "찍어 주면 이 산출기가 그 줄을 분모로 쓴다. 그때까지는 "
        "`절 수 + 미등재` 로 물러서되 **물러선 사실을 적는다**")


def score(n_sections: int, sec_points: float, n_annex: int) -> dict:
    """대장 절 + **별표(기능명세) 전수** → 측정치·상한.

    측정치 = (대장 kind 점수 + 별표 0점) ÷ (절 + **별표 전수**)
    상한   = (대장 kind 점수 + 별표 × 1.0) ÷ **같은 분모**

    ★★ 셋째 인자는 **「미등재」가 아니라 「별표 전수」**다. 「미등재」를 쓰면
      **등재가 진행될수록 분모가 줄어 수가 올라간다** — 그 수는 수가 아니다
      (이 파일 머리의 `_DEN_LINES` 주석에 그날의 실측이 있다).
    ★ 별표는 전부 `미착수`·`unmeasurable` 로 태어나므로 **점수를 0 만큼 더한다.**
      그래서 이 수는 **분모만 늘어 내려간다.** 등재가 늘어도 **분모는 안 움직이고**,
      별표가 닫히는 날 **분자만** 오른다.
    """
    den = n_sections + n_annex
    if den <= 0:
        return {"den": 0, "num": None, "pct": None, "upper": None}
    return {"den": den, "num": sec_points,
            "pct": sec_points / den * 100.0,
            "upper": (sec_points + n_annex) / den * 100.0}


def cpo_stated() -> tuple[dict | None, str]:
    """[세종 판독] 세 수를 지시서에서 **읽는다**(베끼지 않는다)."""
    if not WO_DIR.is_dir():
        return None, "`docs/workorders/` 가 없다"
    hits = sorted(WO_DIR.glob(WO_GLOB))
    if not hits:
        return None, "`%s` 가 없다" % WO_GLOB
    m = CPO_LINE.search(hits[0].read_text(encoding="utf-8", errors="replace"))
    if not m:
        return None, "`%s` 에서 「DSM 지침 N · FWS N · 운영자 콘솔 N」 줄을 못 읽었다" % hits[0].name
    return ({"DSM": int(m.group(1)), "FWS": int(m.group(2)),
             "OPS": int(m.group(3))}, hits[0].name)


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **새 게이트는 양성/음성을 둘 다 붙인다**
# ═══════════════════════════════════════════════════════════════════════════

def self_test(verbose: bool = True) -> int:
    cases: list[tuple[str, bool]] = []

    def ok(name, good):
        cases.append((name, bool(good)))

    _dsm = ("| DSM-U1-01 | 카드 |\n| DSM-U1-02 | 통보 |\n"
            "본문에서 DSM-U1-01 을 한 번 더 인용한다\n| DSM-U2-01 | 판단 |")
    ok("★ 양성 · 규칙 ① — 표식을 문서 순서대로 뽑는다",
       extract_ids(_dsm, r"\bDSM-U\d+-\d+\b")
       == ["DSM-U1-01", "DSM-U1-02", "DSM-U2-01"])
    ok("★ 음성 · 규칙 ③ — **같은 id 를 두 번 세지 않는다**(세면 분모가 부푼다)",
       len(extract_ids(_dsm, r"\bDSM-U\d+-\d+\b")) == 3)

    # ★★ 출생 표본 — 이 게이트를 만들게 한 오독. 그물이 틀리면 **0건**이 나오고,
    #    0건을 「없다」로 읽으면 분모가 통째로 사라진다.
    ok("★★ 출생 표본 · 그물 `DSM-\\d+` 로는 **0건**이다 — 「0건」은 「없다」가 아니다",
       extract_ids(_dsm, r"\bDSM-\d+\b") == [])
    ok("★★ 출생 표본 · 옳은 그물 `DSM-U\\d+-\\d+` 로는 **3건**이다 — "
       "같은 문서에서 두 수가 난다",
       len(extract_ids(_dsm, r"\bDSM-U\d+-\d+\b")) == 3)

    _fws_tbl = "| FWS-F1-01 | a |\n| FWS-F1-02 | b |"
    _fws_par = _fws_tbl + "\n\nFWS-U5-01 카메라 · FWS-U5-02 초소 · FWS-U5-03 마을."
    ok("★ 양성 · 규칙 ② — **문단 안의 표식도 센다**(표 데이터행만 세면 놓친다)",
       len(extract_ids(_fws_par, r"\bFWS-[FU]\d+-\d+\b")) == 5)
    ok("★ 음성 · 표 데이터행만 세면 **2** 다 — 90 과 85 가 갈리는 자리가 여기다",
       len(extract_ids(_fws_tbl, r"\bFWS-[FU]\d+-\d+\b")) == 2)

    _led = ('  - id: "1"\n      - id: SEC-01\n      - id: DSM-U1-01\n'
            '  # 주석에 DSM-U1-02 이름만 스친다\n')
    _got = registered(["DSM-U1-01", "DSM-U1-02", "DSM-U2-01"], _led)
    ok("★ 양성 · 대장에 `id:` 로 실린 표식만 등재로 센다", _got == {"DSM-U1-01"})
    ok("★★ 음성 · **주석에 이름이 스친 것은 등재가 아니다** — "
       "이름을 본 것과 절로 실린 것은 다르다", "DSM-U1-02" not in _got)
    ok("★ 음성 · 대장이 비면 등재 0 이다(전부가 등재된 것으로 읽히지 않는다)",
       registered(["DSM-U1-01"], "") == set())

    # ══════════════════════════════════════════════════════════════════════
    # ★★★ 분모 — **손으로 넣지 않는다.** 대장이 찍은 줄에서 읽는다
    #
    #   [N 지적 · 턴 AB] 첫 판의 이 자리는 `score(n_sections=155, …)` 로
    #   **분모를 손으로 넣어** 통과했다. 그래서 실물이 무너졌는데
    #   (등재 뒤 291 → 155 · 수가 25.6 → 50.0 으로 **올라갔다**) 시험은 초록이었다.
    #   **분모를 손으로 넣는 자기시험은 분모를 안 재는 자기시험이다.**
    #   아래는 전부 **대장이 찍은 글자**에서 분모를 읽어 댄다.
    # ══════════════════════════════════════════════════════════════════════
    _NL = chr(10)
    _ROLL = ("[GA] [입력] 「초록」 부류 155절 — closed 71 · ratchet 3 · "
             "rule_only 3 · unmeasurable 74 · gate_only 4")
    #: 등재 **전** — 별표 0건. N 은 이 줄을 **별표가 0건이어도 늘 찍는다.**
    _GA_BEFORE = _NL.join([
        "[GA] [입력] ★★ 분모 정본 — 절 155 · 별표 136 · 합 291", _ROLL])
    #: 등재 **뒤** — 같은 줄, 같은 수. 달라지는 것은 「미등재」뿐이다.
    _GA_AFTER = _NL.join([
        "[GA]   ★ **kind 표 정본 = 155 + 136 = 291** (절 155 + 별표 136)", _ROLL])

    _b = parse_denominator(_GA_BEFORE)
    _a = parse_denominator(_GA_AFTER)
    ok("★ 양성 · 대장이 찍은 **분모 정본 줄**을 읽는다 (모양 ①)",
       _b[:3] == (155, 136, 291))
    ok("★ 양성 · 같은 줄의 **다른 모양**도 읽는다 (모양 ② · `155 + 136 = 291`)",
       _a[:3] == (155, 136, 291))
    ok("★★ **등재 전과 뒤의 분모가 같다** — 이것이 첫 판이 못 잡은 그 자리다",
       _b[2] == _a[2] == 291)

    #: ★★ 음성 — **등재가 분모를 움직이면 안 된다.** 옛 식은 여기서 무너졌다.
    _ids = ["DSM-U%d-%02d" % (i // 10 + 1, i % 10 + 1) for i in range(136)]
    _led_before = "  - id: SEC-01" + _NL          # 별표 0건 등재
    _led_after = _NL.join(["  - id: SEC-01"] + ["  - id: " + i for i in _ids])
    _n_unreg_before = len([i for i in _ids if i not in registered(_ids, _led_before)])
    _n_unreg_after = len([i for i in _ids if i not in registered(_ids, _led_after)])
    ok("★ 양성 · 등재가 진행되면 **미등재는 준다** (136 → 0)",
       _n_unreg_before == 136 and _n_unreg_after == 0)
    _old_before = score(155, 77.5, _n_unreg_before)["den"]
    _old_after = score(155, 77.5, _n_unreg_after)["den"]
    ok("★★★ **출생 표본 — 옛 식은 등재 뒤 분모가 291 → 155 로 줄었다**"
       "(그리고 수가 25.6 → 50.0 으로 **올라갔다**)",
       _old_before == 291 and _old_after == 155)
    _new_before = score(_b[0], 77.5, _b[1])
    _new_after = score(_a[0], 77.5, _a[1])
    ok("★★★ **고친 식은 등재 전·뒤가 같은 분모 291 · 같은 수다** — "
       "분모가 줄어 올라간 수는 수가 아니다",
       _new_before["den"] == _new_after["den"] == 291
       and abs(_new_before["pct"] - _new_after["pct"]) < 1e-9)
    #: ⚠ 여기서 **머리기사 수를 못박지 않는다.** 분자는 대장이 움직이면 움직인다
    #:   (이 턴에도 closed 68 → 71 로 움직였다). 못박을 것은 **셈**이다.
    ok("★ 그 수는 분자 ÷ 291 이다 — 77.5 ÷ 291 = 26.6 %",
       abs(_new_before["pct"] - 77.5 / 291 * 100.0) < 1e-9)
    ok("★ 별표가 닫히면 **분자만** 오른다 (분모는 안 움직인다)",
       score(155, 100.0, 136)["den"] == 291
       and score(155, 100.0, 136)["pct"] > _new_before["pct"])
    ok("★ 상한(별표를 1 로)은 (77.5 + 136) ÷ 291 = 73.4 %",
       abs(_new_before["upper"] - 73.37) < 0.05)

    #: ★ 음성 — **덧셈이 안 맞는 정본 줄은 거짓이다.** 거짓 분모로 낸 수는 수가 아니다.
    _lie = parse_denominator("[GA] 분모 정본 — 절 155 · 별표 136 · 합 300")
    ok("★★ 음성 · 대장이 적은 분모가 **제 덧셈과 안 맞으면** 안 쓴다",
       _lie[2] is None and "덧셈" in _lie[3])
    _none = parse_denominator("[GA] 아무 말 없음")
    ok("★ 음성 · 정본 줄이 **없으면** None 이다(0 으로 세지 않는다) · 사유를 낸다",
       _none[2] is None and "안 찍는다" in _none[3])
    ok("★★ 음성 · 분모 0 이면 **수를 내지 않는다** — 분모 0 인 초록은 초록이 아니다",
       score(0, 0.0, 0)["pct"] is None)

    ok("★ 양성 · [세종 판독] 줄을 **읽는다**(베끼지 않는다)",
       CPO_LINE.search("DSM 지침 32 + FWS 90 + 운영자 콘솔 12 = 289").groups()
       == ("32", "90", "12"))
    ok("★ 양성 · 가운뎃점으로 적힌 같은 줄도 읽는다",
       CPO_LINE.search("(DSM 지침 32 · FWS 90 · 운영자 콘솔 12 = 134)").groups()
       == ("32", "90", "12"))
    ok("★ 음성 · 그 줄이 없으면 **None** 이다(0 으로 세지 않는다)",
       CPO_LINE.search("아무 말 없음") is None)

    fails = [n for n, g in cases if not g]
    if verbose or fails:
        for name, good in cases:
            if verbose or not good:
                print("  %-4s %s" % ("OK" if good else "FAIL", name))
    if fails:
        print("%s 자기시험 **실패** %d건 — 판정기를 먼저 의심한다 (D-350)"
              % (TAG, len(fails)))
        return 1
    print("%s 자기시험 %d건 통과 — ★ 출생 표본 3(`DSM-\d+` 0건 오독 · "
          "**옛 식이 등재 뒤 분모를 291 → 155 로 줄였다**) · 음성 대조 9"
          "(중복 · 표만 세기 · 주석 스침 · 분모 0 · 거짓 덧셈 · 정본 줄 없음 …). "
          "★ **분모를 손으로 넣는 자기시험은 하나도 없다**"
          % (TAG, len(cases)))
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════

def measure() -> dict:
    per, red, grey = collect()
    all_ids: list[str] = []
    for spec in SPEC_SOURCES:
        all_ids += per[spec["key"]]["ids"]
    #: 규칙 ③ — 문서 사이에서도 한 번만 센다(접두가 달라 겹칠 일은 없지만, 세는
    #: 규칙은 「겹치지 않는다」를 **가정하지 않는다**).
    seen, uniq = set(), []
    for i in all_ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    if len(uniq) != len(all_ids):
        red.append("문서 사이에 **같은 표식이 %d건 겹쳤다** — 분모가 부푼다"
                   % (len(all_ids) - len(uniq)))

    led = ledger_text()
    reg = registered(uniq, led)
    unreg = [i for i in uniq if i not in reg]

    ga_out, ga_rc = run_ga()
    roll = ga_roll(ga_out)
    table, table_why = kind_table()
    pts = None
    if roll and table:
        bad = [k for k in roll["counts"] if k not in table]
        if bad:
            red.append("대장에 **눈금 밖의 부류**가 있다: %s — 모르는 부류를 0 으로도 "
                       "1 로도 세지 않는다" % " · ".join(bad))
        else:
            pts = sum(table[k] * n for k, n in roll["counts"].items())
            if roll["sum"] != roll["total"]:
                red.append("대장 부류 합 %d 이 절 수 %d 과 다르다 — 안 세어진 절은 "
                           "「닫혔다」로 읽힌다 (P-211)"
                           % (roll["sum"], roll["total"]))
    elif not roll:
        grey.append("대장의 **부류 줄을 못 읽었다** — `%s --no-gates` 를 못 불렀거나 "
                    "그 게이트가 지금 못 돈다(rc=%s). 분자가 없으면 수를 내지 않는다"
                    % (GA_SCRIPT.name, ga_rc))

    #: ★★ 분모는 **대장이 제 입으로 적은 정본 줄**에서 읽는다 — 등재 여부와 무관하다.
    n_sec, n_annex, n_all, den_why = parse_denominator(ga_out)
    den_src = "대장의 분모 정본 줄 (절 %s · 별표 %s)" % (n_sec, n_annex)
    if n_all is None:
        #: 못 읽으면 **물러서되 물러선 사실을 적는다.** 물러선 식은 등재가 늘면
        #: 분모가 줄어드는 그 식이므로, 회색으로 내어 눈에 띄게 둔다.
        if den_why and "덧셈" in den_why:
            red.append("분모: %s" % den_why)
        else:
            grey.append("분모: %s" % den_why)
        n_sec = roll["total"] if roll else None
        n_annex = len(unreg)
        den_src = "**물러선 식** (절 + 미등재) — 등재가 늘면 분모가 준다"
    else:
        #: ★ **두 도구가 같은 분모를 쓰는가.** 갈리면 두 수가 다 못 쓰게 된다.
        if roll and n_sec != roll["total"]:
            red.append("★ **절 수가 갈렸다** — 분모 정본 줄은 %d, 부류 줄은 %d. "
                       "같은 대장에서 두 분모가 난다 (D-369)" % (n_sec, roll["total"]))
        if n_annex != len(uniq):
            red.append("★ **별표 수가 갈렸다** — 대장은 %d, 이 규칙이 뽑은 id 는 %d. "
                       "N 과 내가 다른 분모를 쓰면 **두 수가 다 못 쓰게 된다**"
                       % (n_annex, len(uniq)))
    sc = (score(n_sec, pts, n_annex)
          if (n_sec is not None and pts is not None)
          else {"den": None, "num": None, "pct": None, "upper": None})

    cpo, cpo_src = cpo_stated()
    return {"per": per, "ids": uniq, "reg": reg, "unreg": unreg,
            "n_sec": n_sec, "n_annex": n_annex, "den_src": den_src,
            "roll": roll, "pts": pts, "score": sc, "table_why": table_why,
            "cpo": cpo, "cpo_src": cpo_src, "red": red, "grey": grey,
            "ga_rc": ga_rc}


def emit(rep: dict) -> str:
    """규칙 ⑤ — 뽑은 목록을 낸다. **이 파일이 N 의 등재 입력이다.**

    ⚠ 이 파일은 **파생물**이다. 정본은 세 명세서이고, 이 파일은 그 규칙이 낸 결과다.
      손으로 고치면 다음 실행이 덮는다 — 고칠 자리는 명세서다.
    """
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "생성": "scripts/verify_spec_coverage.py (파생물 — 손으로 고치지 않는다)",
        "규칙": "세 명세서의 사용자별 세부 기능명세 id 표식 하나 = 한 항목 · "
                "같은 id 는 한 번만 · 세 문서 밖의 인용은 안 센다",
        "합계": len(rep["ids"]),
        "등재": sorted(rep["reg"]),
        "미등재": rep["unreg"],
        "문서": {},
    }
    for spec in SPEC_SOURCES:
        d = rep["per"][spec["key"]]
        body["문서"][spec["key"]] = {
            "파일": d["path"].name if d["path"] else None,
            "절": d["section"], "그물": spec["pattern"],
            "수": len(d["ids"]), "id": d["ids"],
        }
    OUT_JSON.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    return str(OUT_JSON.relative_to(ROOT)).replace("\\", "/")


def measured_line(rep: dict) -> str:
    """`MEASURED=` — **분모는 머리글 시점에 지금 센 것**이다(거짓 분모 0건)."""
    n = len(rep["ids"])
    per = " · ".join("%s %d" % (s["key"], len(rep["per"][s["key"]]["ids"]))
                     for s in SPEC_SOURCES)
    den = rep["score"]["den"]
    return ("기능명세 항목을 **id 표식으로 세서** 대장 절과 한 분모에 놓는다 — "
            "**분모 %s칸**(대장 절 %s + **별표 전수** %s · 출처: %s) · "
            "명세 표식 **%d건**(%s) · 등재 %d · 미등재 %d. "
            "★ 분모는 **등재 여부와 무관하다** — 「미등재」로 세면 등재가 늘수록 "
            "분모가 줄어 **수가 올라간다**(그 수는 수가 아니다). 별표는 전부 "
            "`unmeasurable` 로 태어나 **점수를 0 만큼 더한다** (P-234 · D-301)"
            % (den if den else 0,
               rep.get("n_sec") if rep.get("n_sec") is not None else "?",
               rep.get("n_annex") if rep.get("n_annex") is not None else "?",
               rep.get("den_src", "?"), n, per, len(rep["reg"]), len(rep["unreg"])))


def report(rep: dict, wrote: str) -> int:
    red, grey = list(rep["red"]), list(rep["grey"])

    print("%s [입력] 명세서 3 · 표식 **%d건** · 대장 절 %s · 등재 %d · 미등재 %d"
          % (TAG, len(rep["ids"]),
             rep["roll"]["total"] if rep["roll"] else "?",
             len(rep["reg"]), len(rep["unreg"])))
    for spec in SPEC_SOURCES:
        d = rep["per"][spec["key"]]
        print("%s   · %-3s %-4d %s  ← %s  (%s)"
              % (TAG, spec["key"], len(d["ids"]), d["section"],
                 d["path"].name if d["path"] else "**문서 없음**",
                 spec["pattern"]))

    # ── [세종 판독] 과 대조 — **다르면 규칙이 낸 수가 정본이다** ──────────
    if rep["cpo"]:
        diff = []
        for spec in SPEC_SOURCES:
            got, said = len(rep["per"][spec["key"]]["ids"]), rep["cpo"][spec["key"]]
            if got != said:
                diff.append("%s **%d ↔ [세종 판독] %d** (%+d)"
                            % (spec["cpo_label"], got, said, got - said))
        if diff:
            print("%s ★★ **판독과 갈렸다** — %s" % (TAG, " · ".join(diff)))
            print("%s    규칙이 낸 수가 정본이다. 분모가 %d → %d 로 늘고 "
                  "**수가 내려간다**(WO §6 함정 ②). 내려간 것은 제품이 아니라 "
                  "**세는 눈**이다" % (TAG,
                                     sum(rep["cpo"].values()), len(rep["ids"])))
        else:
            print("%s   · [세종 판독](%s)과 **같다** — DSM %d · FWS %d · 운영자 %d"
                  % (TAG, rep["cpo_src"], rep["cpo"]["DSM"], rep["cpo"]["FWS"],
                     rep["cpo"]["OPS"]))
    else:
        grey.append("[세종 판독] 줄을 못 읽었다 — %s. 대조 없이 낸 수는 대조 없이 "
                    "낸 수다" % rep["cpo_src"])

    #: ★ 눈금 한 줄은 **대개 초록이다**("N 쪽에서 가져왔다"). 그것을 회색에 넣으면
    #:   「잘 된 일」이 「못 잰 일」로 세어지고, 이 게이트는 영영 초록이 못 된다.
    #:   갈렸을 때(`★`)만 빨강이고, 물러섰을 때(`아직 없다`)만 회색이다.
    if rep["table_why"]:
        if rep["table_why"].startswith("★"):
            red.append("눈금: %s" % rep["table_why"])
        elif "아직 없다" in rep["table_why"] or "못" in rep["table_why"]:
            grey.append("눈금: %s" % rep["table_why"])
        else:
            print("%s   · 눈금: %s" % (TAG, rep["table_why"]))

    print("")
    sc = rep["score"]
    if sc["pct"] is None:
        print("%s ? **기능명세 포함 완료율 — 회색.** 분모(%s)는 섰으나 "
              "**분자를 못 읽었다**. 분모만 있는 수는 수가 아니다"
              % (TAG, sc["den"] if sc["den"] else "?"))
    else:
        print("%s ★ **기능명세 포함 완료율 %.1f %%**  "
              "= 대장 kind 점수 %.1f ÷ **분모 %d**(대장 절 %d + **별표 전수** %d)"
              % (TAG, sc["pct"], sc["num"], sc["den"],
                 rep["n_sec"], rep["n_annex"]))
        print("%s    분모 출처: %s" % (TAG, rep["den_src"]))
        print("%s    상한(별표를 1 로) **%.1f %%** — 그 폭 %.1f 점이 "
              "**우리가 모르는 만큼**이다. 별표 한 항목이 닫히면 그 폭이 좁아진다"
              % (TAG, sc["upper"], sc["upper"] - sc["pct"]))
        print("%s    ★★ 분모는 **등재 여부와 무관하다**(등재 %d · 미등재 %d) — "
              "「미등재」로 세면 **등재가 늘수록 분모가 줄어 수가 올라간다.** "
              "분모가 줄어 올라간 수는 수가 아니다"
              % (TAG, len(rep["reg"]), len(rep["unreg"])))
        print("%s    ★ 별표 %d 의 0 은 **「기능이 없다」가 아니라 「아직 닫히지 "
              "않았다」**이다 — 전부 `미착수`·`unmeasurable` 로 태어난다(P-231)"
              % (TAG, rep["n_annex"]))
    if rep["roll"]:
        print("%s    대장: 절 %d · kind 점수 %s · closed %d"
              % (TAG, rep["roll"]["total"],
                 ("%.1f" % rep["pts"]) if rep["pts"] is not None else "?",
                 rep["roll"]["counts"].get("closed", 0)))
    print("%s    id 목록 → `%s` (N 의 등재 입력 · 파생물)" % (TAG, wrote))
    print("")

    for line in grey:
        print("%s   ? %s" % (TAG, line))
    for line in red:
        print("%s   X %s" % (TAG, line))

    if red:
        print("%s X **빨강** %d건" % (TAG, len(red)))
        return EXIT_RED
    if grey or sc["pct"] is None:
        print("%s ? **회색(exit 2)** — 회색은 초록이 아니다 (D-301). "
              "★ 이 줄은 **관측**이다: 지금 이 도구가 못 읽은 것이 무엇인지를 "
              "말할 뿐, 무엇을 하라고 말하지 않는다" % TAG)
        return EXIT_GREY
    #: ★ **마지막 줄은 관측이지 처방이 아니다.** 이 초록은 「제품이 됐다」가 아니라
    #:   **「이 수를 정직하게 셌다」**이다 — 수 자체는 %.1f 이고 그것은 초록이 아니다.
    #:   다음 사람이 이 줄을 선택지 목록으로 읽지 않게 한 문장으로 적는다.
    print("%s O **초록의 뜻**: 분모 %d 를 규칙이 센 목록으로 세웠고 분자 %.1f 를 "
          "대장에서 받았다. **수 %.1f %% 는 초록이 아니다** — 초록인 것은 "
          "「이 수를 다시 셀 수 있다」는 사실뿐이다"
          % (TAG, sc["den"], sc["num"], sc["pct"]))
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-emit", action="store_true",
                    help="id 목록 파일을 쓰지 않는다(읽기만)")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rep = measure()
    wrote = "(안 씀 · --no-emit)" if args.no_emit else emit(rep)
    return report(rep, wrote)


if __name__ == "__main__":
    #: ★ 머리글은 **자기시험 갈래에서도** 찍는다 [실측 2026-09-21 · 턴 AB].
    #:   `verify_gate_header` 는 게이트를 `--self-test` 로 열어 세 줄을 받는다 —
    #:   그 갈래에서 안 찍으면 「세 줄 중 **0줄**」로 빨강이 난다. 처음에 그렇게
    #:   냈고, **내 게이트가 내 머리글 검사에 걸렸다**(턴 AA 에도 한 번 있었다).
    if True:
        from _gate_header import gate_header, file_stamp  # P-107
        _paths = [p for p in (
            DESIGN / "DSM_재난안전관리App_명세서_v1.1_지침기반_20260915.md",
            LEDGER) if p.is_file()]
        #: ★ `MEASURED=` 는 **재고 난 뒤** 낼 수 없다(머리글이 먼저 나간다). 그래서
        #:   여기 적는 분모는 **지금 이 자리에서 센 수**다 — 손으로 적은 수가 아니다.
        _ids = 0
        for _s in SPEC_SOURCES:
            _p, _ = find_source(_s["prefix"])
            if _p:
                _ids += len(extract_ids(
                    _p.read_text(encoding="utf-8", errors="replace"),
                    _s["pattern"]))
        gate_header(
            __file__,
            measured=("기능명세 항목을 **id 표식으로** 세어 대장 절과 한 분모에 "
                      "놓는다 — **분모 %d건**(세 명세서에서 지금 센 표식 = 별표 전수) "
                      "+ 대장 절 수(대장의 **분모 정본 줄**에서 받는다). "
                      "★ 분모는 **등재 여부와 무관하다** — 「미등재」로 세면 등재가 "
                      "늘수록 분모가 줄어 수가 올라간다. 못 뽑으면 0 이 아니라 회색이다"
                      % _ids),
            target="명세서 3 + `%s` + `verify_ga_readiness.py --static`(로그인 0) 을 "
                   "**부른다**" % LEDGER.name,
            as_="(자격증명 없음 — 문서와 대장을 읽고 게이트를 부른다)",
            source=" + ".join(file_stamp(p) for p in _paths) or "문서 없음",
        )
    sys.exit(main())
