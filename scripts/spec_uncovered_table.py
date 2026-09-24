# -*- coding: utf-8 -*-
"""P-347 — **기능명세 미포함 절 표(Table A)를 산출기가 낸다** (2026-09-25 · 턴 AJ 차선 F).

왜 이 파일이 생겼나
-------------------
`scripts/verify_spec_coverage.py` 가 「기능명세 포함 완료율」의 **분모·분자**를 낸다.
그런데 그 표(어느 절이 화면 몇 번인지 · 누구 역할인지 · 다음 사람이 뭘 들고 시작하는지)는
아무도 안 냈다 — 손으로 세면 다음에 문서가 바뀔 때마다 표가 거짓말한다(P-93).
그래서 이 도구는 **`verify_spec_coverage.collect()`가 이미 뽑은 같은 id 목록**을 받아,
그 id 가 **어느 문서의 어느 절 제목 아래·어느 표 행에** 있었는지를 **다시 읽어서** 화면·역할을
붙인다. 손으로 짓지 않는다 — 문서에 없는 글자는 안 만든다.

「미포함」의 뜻 — **지어내지 않는다**
------------------------------------
`verify_spec_coverage.score()` 는 별표(`annex_2_spec`) 항목을 **분모에만** 넣고 분자에는
**절대** 안 넣는다(주석 「별표는 전부 `unmeasurable` 로 태어나 점수를 0 만큼 더한다」).
대장에 `id:` 로 등재되어 있어도(현재 136/136 등재) 그 등재는 「적었다」이지 「닫혔다」가
아니다 — score() 는 등재 여부를 안 본다. **그래서 이 목록(별표 전수)이 곧 「미포함 절」
전수다.** 등재되면 이 표에서 빠지는 것이 아니라, **닫힘(kind 가 실제 점수를 받는 상태)이
되어야** 빠진다 — 그 날은 아직 오지 않았다(전부 `status: 미착수`).

이 표가 지어내는 것 셋 — **실측이 아니라 추정**이라고 스스로 말한다
--------------------------------------------------------------------
① **화면** — 표 행의 첫 굵은 글씨(`**…**`) 또는 문단 형식(FWS §5.7)의 id 뒤 구절.
   문서가 적은 글자 그대로다. 굵은 글씨가 없으면 그 칸 전체를 자른다.
② **역할** — id 가 속한 절 제목(`### 4.1 U1 관제요원`류)에서 `U숫자`/`F숫자`/`U0` 토큰을
   그대로 읽는다. **DSM 은 U1~U6, FWS 는 F1~F6(현장) + U5(관리자), OPS 는 U0(운영자)**다 —
   FWS·OPS 를 억지로 U1~U6 표기에 끼우지 않는다(끼우면 지어낸 것이 된다).
③ **규모(S/M/L)·의존성** — 문서 문장 안의 낱말로 가르는 **규칙 기반 추정**이다
   (`_size`·`_dependency` 참고). 실측(공수)이 아니다 — 다음 사람이 어디부터 볼지
   빨리 잡게 돕는 자리이지, 견적이 아니다. 규칙은 이 파일에 적혀 있어 재현된다.
④ **게이트** — 이번 실측(2026-09-25)에서 `scripts/*.py` 를 다 훑어 이 id 문자열을
   그대로 참조하는 게이트가 **0건**이었다(id 문자열 자체를 `in` 으로 찾는다 —
   정규식이 아니라 리터럴 부분문자열 검색이다). 그래서 모든 행의 게이트 칸은
   「없음」이다 — 지어내지 않는다.

부르는 법
--------
    python scripts/spec_uncovered_table.py            # 표를 stdout 에 낸다(markdown)
    python scripts/spec_uncovered_table.py --json PATH  # 같은 자료를 json 으로도 낸다
    python scripts/spec_uncovered_table.py --self-test

호스트에서 돈다 — 문서·이 저장소의 `scripts/*.py` 만 읽는다. 네트워크·로그인 없음.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[UNCOV]"

from verify_spec_coverage import (SPEC_SOURCES, collect, extract_ids,  # noqa: E402
                                   ledger_text, registered)

OUT_JSON_DEFAULT = ROOT / "docs" / "agent" / "evidence" / "P-347" / "spec_uncovered.json"

#: ── ① 화면 ────────────────────────────────────────────────────────────────
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ROLE_HEADING = re.compile(r"^#{2,3}\s*[\d.]*\s*.*?\b(U0|U\d|F\d)\b\s*(.*)$")


def _strip_heading_tail(label: str) -> str:
    label = re.sub(r"\(\d+\)\s*$", "", label).strip()
    label = re.sub(r"^[—-]\s*", "", label).strip()
    return label


def role_headings(text: str) -> list[tuple[int, str]]:
    """줄 오프셋(문자 인덱스) → 그 지점에서 유효한 역할 라벨. 문서 순서대로 쌓는다."""
    out: list[tuple[int, str]] = []
    pos = 0
    current = "(역할 헤딩 없음)"
    for line in text.splitlines(keepends=True):
        m = _ROLE_HEADING.match(line.strip())
        if m:
            role, rest = m.group(1), _strip_heading_tail(m.group(2))
            current = "%s %s" % (role, rest) if rest else role
            out.append((pos, current))
        pos += len(line)
    return out


def role_at(headings: list[tuple[int, str]], offset: int) -> str:
    label = "(역할 헤딩 없음)"
    for pos, lab in headings:
        if pos <= offset:
            label = lab
        else:
            break
    return label


def role_tag(label: str) -> str:
    m = re.match(r"(U0|U\d|F\d)", label)
    return m.group(1) if m else "?"


def screen_of(text: str, id_: str, offset: int) -> str:
    """id 가 사는 **줄**에서 화면 이름을 뽑는다.

    표 행(`| id | **화면** — 설명 | …`)이면 둘째 칸의 첫 굵은 글씨.
    문단(FWS §5.7)이면 id 뒤부터 다음 `·`(가운뎃점) 또는 줄 끝까지.
    """
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    if line.lstrip().startswith("|"):
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2:
            b = _BOLD.search(cols[1])
            return b.group(1) if b else cols[1][:60]
        return line.strip()[:60]
    # 문단 형식 — id 뒤 구절
    tail = text[offset + len(id_):offset + len(id_) + 200]
    m = re.match(r"\s*(.+?)(?:\s*·\s*[A-Z]|\n|$)", tail)
    return (m.group(1).strip() if m else tail.strip()[:60])[:80]


#: ── ③ 규모/의존성 — **규칙 기반 추정**. 여기 목록이 규칙 전문이다(지어낸 수 아님) ──
_SIZE_L = ("연동", "API", "서명", "결제", "청구", "동기화", "프로토콜", "외부",
           "드론", "모델 활성", "TTA", "CAP 1.2", "어댑터", "브로커")
_SIZE_S = ("버튼", "알림", "기록", "조회", "1클릭", "체크", "배지", "표시", "확인",
           "번호 버튼", "1탭")

_DEP_RULES: tuple[tuple[str, str], ...] = (
    (r"카메라|PTZ|열화상|CCTV", "카메라 연동"),
    (r"지도|폴리곤|반경|위치", "위치/지도 데이터(주의: MapForRoute·FormRoute 는 금지구역 — 새 화면으로 만든다)"),
    (r"서명|키 회전|자격 참조", "서명키/자격 관리"),
    (r"청구|과금|결제", "과금 연동"),
    (r"드론", "드론 연동"),
    (r"AI|오탐|모델", "AI 모델 연동"),
    (r"CBS|재난문자|문자|SMS", "외부 알림 채널(문자·CBS)"),
    (r"NDMS|스마트시티|112|119|TTA|CAP", "외부 기관 연계 API"),
    (r"PS-LTE|무전|그룹통화", "재난안전통신망 연동"),
    (r"HWPX|PDF|ZIP", "문서 생성기"),
)


def _size(desc: str) -> str:
    if any(k in desc for k in _SIZE_L):
        return "L"
    if any(k in desc for k in _SIZE_S):
        return "S"
    return "M"


def _dependency(desc: str) -> str:
    for pat, label in _DEP_RULES:
        if re.search(pat, desc):
            return label
    return "커널/공통 모듈 내(새 외부 의존 없음)"


#: ── ④ 게이트 — 이번 실측: scripts/*.py 를 훑어 id 문자열을 참조하는 게이트가 있는가
#: ★ [실측 2026-09-25 · 차선 F] 처음엔 `in` 부분문자열로 찾았더니 `O-01`~`O-08` 이
#:   전부 「게이트 있음」으로 잡혔다 — 그런데 그 자리는 전부 `WO-01`·`ISO-02`·`OPS-04`
#:   같은 **다른 표식의 일부**였다(짧은 `O-NN` 표식이 긴 표식 속에 우연히 들어맞는다).
#:   그래서 앞뒤에 글자/숫자가 안 붙는 자리만 잡는다(단어 경계 + 하이픈 고려).
def gate_of(id_: str, script_texts: dict[str, str]) -> str:
    pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(id_) + r"(?![A-Za-z0-9])")
    hits = [name for name, text in script_texts.items() if pat.search(text)]
    return "없음(annex · P-234 8영역 밖 · 신설 필요)" if not hits else " · ".join(sorted(hits))


#: 이 둘은 **id 를 인용하지만 그 절을 검증하지 않는다** — 스스로 빼지 않으면
#: 자기시험 표본 문자열(`DSM-U1-01` 등)이 「게이트가 있다」는 거짓 초록을 만든다
#: [실측 2026-09-25 · 차선 F] `verify_spec_coverage.py::self_test()` 의 표본이
#: 바로 그 모양이었다 — id 를 그물 시험용으로 인용했을 뿐인데 "게이트 있음"으로 잡혔다.
_NOT_A_GATE = ("spec_uncovered_table.py", "verify_spec_coverage.py")


def _load_script_texts() -> dict[str, str]:
    out = {}
    for p in sorted((ROOT / "scripts").glob("*.py")):
        if p.name in _NOT_A_GATE:
            continue
        out[p.name] = p.read_text(encoding="utf-8", errors="replace")
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════
def build_rows() -> list[dict]:
    per, _red, _grey = collect()
    led = ledger_text()
    script_texts = _load_script_texts()
    rows: list[dict] = []
    for spec in SPEC_SOURCES:
        d = per[spec["key"]]
        if not d["path"]:
            continue
        text = d["path"].read_text(encoding="utf-8", errors="replace")
        headings = role_headings(text)
        #: ★ [실측 2026-09-25 · 차선 F] **`str.find` 로 찾으면 안 된다.** `O-01` 을
        #:   `text.find()` 로 찾으면 §1.1 의 `ISO-01~04`(다른 표식의 일부) 안에서
        #:   먼저 걸린다 — `verify_spec_coverage.extract_ids` 는 **경계가 있는 그물**
        #:   (`\bO-\d{2}\b`)로 뽑으므로 그 표식을 안 잡는다. 화면·역할도 **같은 그물,
        #:   같은 첫 자리**를 써야 같은 id 를 가리킨다 — 그래서 여기도 `spec["pattern"]`
        #:   으로 다시 찾는다(문자열 그대로 찾지 않는다).
        first_offset: dict[str, int] = {}
        for m in re.finditer(spec["pattern"], text):
            if m.group(0) not in first_offset:
                first_offset[m.group(0)] = m.start()
        for id_ in d["ids"]:
            off = first_offset.get(id_, -1)
            if off < 0:
                rows.append({"id": id_, "doc": spec["key"], "screen": "(못 찾았다)",
                            "role": "?", "size": "?", "gate": "?", "dependency": "?"})
                continue
            label = role_at(headings, off)
            screen = screen_of(text, id_, off)
            rows.append({
                "id": id_, "doc": spec["key"], "section": spec["section"],
                "role": role_tag(label), "role_label": label,
                "screen": screen, "size": _size(screen),
                "dependency": _dependency(screen),
                "gate": gate_of(id_, script_texts),
                "registered": id_ in registered(d["ids"], led),
            })
    return rows


def render_md(rows: list[dict]) -> str:
    out = ["| 절 번호 | 화면 | 역할 | 게이트 | 규모 | 의존성 |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            r["id"], r["screen"].replace("|", "/"), r["role"], r["gate"],
            r["size"], r["dependency"]))
    return "\n".join(out)


def self_test() -> int:
    bad = []
    dsm_sample = ("### 4.1 U1 관제요원\n\n"
                 "| ID | 기능 | 근거 |\n| --- | --- | --- |\n"
                 "| DSM-U1-01 | **유형별 행동 카드** — 설명 | 근거 |\n")
    headings = role_headings(dsm_sample)
    off = dsm_sample.find("DSM-U1-01")
    label = role_at(headings, off)
    if role_tag(label) != "U1":
        bad.append("표 헤딩에서 역할 U1 을 못 읽는다: %r" % label)
    screen = screen_of(dsm_sample, "DSM-U1-01", off)
    if screen != "유형별 행동 카드":
        bad.append("표 행에서 화면(첫 굵은 글씨)을 못 뽑는다: %r" % screen)

    fws_par = ("### 5.7 U5 관리자 — 산불 설정 보강 (5)\n\n"
              "FWS-U5-01 산불 감시 카메라 등록(고지대) · FWS-U5-02 초소·순찰함\n")
    headings2 = role_headings(fws_par)
    off2 = fws_par.find("FWS-U5-01")
    label2 = role_at(headings2, off2)
    if role_tag(label2) != "U5":
        bad.append("문단 헤딩에서 역할 U5 을 못 읽는다: %r" % label2)
    screen2 = screen_of(fws_par, "FWS-U5-01", off2)
    if "카메라" not in screen2:
        bad.append("문단 형식(id 뒤 구절)에서 화면을 못 뽑는다: %r" % screen2)

    #: ★★ 출생 표본 — `O-01` 이 §1.1 의 `ISO-01~04`(다른 표식) 속에서 먼저 잡히면 안 된다.
    ops_sample = ("## 1.1 L-P\n\n| 이름 | 근거 |\n| --- | --- |\n"
                 "| 테넌시 | `ISO-01~04` |\n\n"
                 "## 7. 플랫폼 운영자(U0) — 세부 기능명세\n\n"
                 "| ID | 기능 |\n| --- | --- |\n"
                 "| O-01 | **테넌트 발급** |\n")
    real_off = None
    for m in re.finditer(r"\bO-\d{2}\b", ops_sample):
        if m.group(0) == "O-01":
            real_off = m.start()
            break
    naive_off = ops_sample.find("O-01")
    if naive_off == real_off:
        bad.append("출생 표본이 안 갖춰졌다 — ISO-01~04 안의 우연한 일치가 없다")
    headings3 = role_headings(ops_sample)
    label3 = role_at(headings3, real_off)
    if role_tag(label3) != "U0":
        bad.append("경계 있는 그물의 첫 자리에서 역할 U0 을 못 읽는다: %r" % label3)
    screen3 = screen_of(ops_sample, "O-01", real_off)
    if screen3 != "테넌트 발급":
        bad.append("★★ 출생 표본 — `str.find` 로 짚으면 §1.1 의 `ISO-01~04` 안에서 "
                   "먼저 걸려 화면이 엉뚱해진다. 경계 있는 그물의 첫 자리를 써야 "
                   "한다: %r" % screen3)

    if _size("서명키 회전 API 연동") != "L":
        bad.append("규모 L 규칙이 안 걸린다")
    if _size("확인 버튼") != "S":
        bad.append("규모 S 규칙이 안 걸린다")
    if _size("아무 키워드도 없는 설명") != "M":
        bad.append("기본값 M 이 아니다")
    if "카메라" not in _dependency("PTZ 카메라 전환"):
        bad.append("카메라 의존성 규칙이 안 걸린다")
    if _dependency("아무 키워드도 없다") != "커널/공통 모듈 내(새 외부 의존 없음)":
        bad.append("기본 의존성이 다르다")

    if gate_of("DSM-U1-01", {"verify_x.py": "아무 관련 없음"}) == "없음(annex · P-234 8영역 밖 · 신설 필요)":
        pass
    else:
        bad.append("게이트 없음 판정이 깨졌다")
    if gate_of("DSM-U1-01", {"verify_x.py": "여기 DSM-U1-01 이 있다"}) != "verify_x.py":
        bad.append("게이트 있음 판정이 깨졌다")

    if bad:
        print("%s 자기시험 실패:" % TAG)
        for b in bad:
            print("    %s" % b)
        return 1
    print("%s 자기시험 통과 — 헤딩→역할 2종(표·문단) · 규모 3종 · 의존성 2종 · "
         "게이트 있음/없음 2종" % TAG)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="P-347 Table A — 기능명세 미포함 절")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", metavar="PATH", nargs="?",
                    const=str(OUT_JSON_DEFAULT))
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rows = build_rows()
    print("%s [입력] 별표(annex) id 전수 — 분모 %d건(DSM %d · FWS %d · OPS %d) · "
         "게이트 있는 행 %d건"
         % (TAG, len(rows),
            sum(1 for r in rows if r["doc"] == "DSM"),
            sum(1 for r in rows if r["doc"] == "FWS"),
            sum(1 for r in rows if r["doc"] == "OPS"),
            sum(1 for r in rows if not r["gate"].startswith("없음"))))
    print(render_md(rows))
    if args.json:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print("%s 기록 → %s" % (TAG, out_path.relative_to(ROOT).as_posix()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
