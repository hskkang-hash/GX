#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RC-1 판정기 — 09-25 「내부 RC」 선언문(WO-GX-20260924-09 §4-1)이 읽을 **수를 낸다.**

★★★ 이 파일의 유일한 일 — **초록을 강제하지 않는다** (P-269)
------------------------------------------------------------------------------
세종 판정 그대로다: 「RC-1 은 회색 채로 태그한다」. 이 판정기가 하는 일은 셋뿐이다 —
  ① **세 수**(FC·PR·CR)와 **기능명세 포함 완료율**과 **상용 /100** 을 낸다
     (이미 있는 산출기를 **import 로** 부른다 — 두 벌을 두지 않는다 · D-369).
  ② **S1~S7**(`GX-REVIEW_실사용자_상용점검_v2.0_20260921.md`)을 한 행씩 다시 잰다 —
     이 판정기가 잴 수 있는 만큼만 잰다. 나머지는 **회색으로 남기고 사유를 적는다.**
  ③ `rc-1-internal` 태그 조건(P-269 — 「전량 0 실패 + 빨강 목록 등재 + 회색 목록 등재」)
     을 **판정**한다. 초록을 강제하는 조건은 **0 개**다 — S1~S7 이 온통 빨강·회색이어도
     전량 시험 실패가 0 이면 태그는 선다. 그것이 「내부 RC」라는 말의 뜻이다.

무엇을 재나 — **지어내지 않는다**
------------------------------------------------------------------------------
칸마다 출처를 밝힌다. 출처가 없으면 그 칸은 **회색**이고, 회색 옆에는 반드시
「왜 회색인가」를 적는다(D-301 — 못 잰 것을 0 으로도 1 로도 세지 않는다).

    세 수(FC/PR/CR)         → `verify_readiness_scores.aa_report()` **import**
    기능명세 포함 완료율     → `verify_spec_coverage.measure()` **import**
    상용 /100               → 위 aa_report() 의 `drop["status"]`(영역 가중 합계)
    S1 첫 근무일에 끝난다    → 위 aa_report() 의 `onboard`(온보딩 48행)
    S2 누르면 끝난다        → 위 aa_report() 의 `click`(48행 「누른 뒤」)
    S3 아무도 없는 아침     → `verify_backup_autonomy.run()` + `verify_backup_recovery.run()`
                              **import** — 재부팅 10/10 은 이 판정기가 **못 잰다**(대표 손·
                              P-271) · 그래서 이 행은 둘 다 초록이어도 **회색을 벗지 못한다**
    S4 틀린 것을 틀렸다 함  → `probe_fake_bearer.py` 를 gx-shell 안에서 **호출**(가짜 헤더
                              경계 하나만) · 「감사 체인 새 끊김 0」·「시험 자료 0」은 이
                              판정기가 안 잰다 — 회색 사유로 남긴다
    S5 밖에서 닿는다        · S6 청구서가 정직하다 · S7 종이가 나간다
                              → 이 저장소에 **아직 그 수를 내는 게이트가 없다.** 지어내지
                              않는다 — 회색 · 왜 없는지를 적는다 (아래 S5~S7 함수 docstring)
    전량 시험(단위+통합)    → 기본은 **안 돈다**(비용 — 분 단위). `--full-tests` 로 켜면
                              MEMORY 의 정본 호출(-w /app + tests)을 그대로 쓴다. RC-1 태그의
                              **유일한 초록 문턱**이 이 수다(P-269) — 다른 무엇도 태그를 막지
                              않는다.

부르는 방향
------------------------------------------------------------------------------
이 파일 자신은 host 에서 돈다(`aa_report()`/`measure()`/`verify_backup_*` 가 이미 자기
안에서 필요하면 subprocess·docker exec 로 위임한다 — 여기서 다시 만들지 않는다). S4·
`--full-tests` 만 이 파일이 **직접** `docker exec` 를 쓴다(둘 다 gx-shell 안에서 도는 것
이라 호스트에서 그 문을 두드린다 · 이 저장소의 「판정기 부르는 방향」 규약 그대로).

    python scripts/verify_release_candidate.py                 # 세 수 + S1~S7 (전량 생략)
    python scripts/verify_release_candidate.py --full-tests    # + 전량 시험(분 단위)
    python scripts/verify_release_candidate.py --json PATH     # 기계용 json 도 남긴다
    python scripts/verify_release_candidate.py --self-test     # 판정 규칙만 (D-277 류)

종료 코드
    0 `rc-1-internal` 태그가 선다 · 1 전량 시험에 실패가 있다(태그 불가) ·
    2 판정 불가(전량 시험을 안/못 돌렸다 — **회색**. 태그도 안 선다. 이것도 실패가 아니다)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[RC1]"
EXIT_OK, EXIT_FAIL, EXIT_GRAY = 0, 1, 2

GRAY, RED, GREEN = "gray", "red", "green"
MARK = {GREEN: "●", RED: "○", GRAY: "◐?"}


def cell(id_: str, label: str, verdict: str, line: str) -> dict:
    assert verdict in (GREEN, RED, GRAY), verdict
    return {"id": id_, "label": label, "verdict": verdict, "line": line}


# ═══════════════════════════════════════════════════════════════════════════
# 세 수 · 기능명세 포함 · 상용 /100  —  이미 있는 산출기를 **import** 로 부른다 (D-369)
# ═══════════════════════════════════════════════════════════════════════════
def measure_fc_pr_cr() -> tuple[dict | None, list[str]]:
    """`verify_readiness_scores.py --aa` 가 쓰는 것과 **같은 호출**(정본 그대로 옮긴다).

    ★ `click` 을 `run_click_completes()` 로 얻는 이유 — 그 함수는 `--measure` **없이**
      그 게이트를 부른다(증거 파일을 읽을 뿐, 브라우저를 띄우지 않는다). 이 판정기가
      스스로 브라우저를 열지 않기 위한 자리다(이 턴 규약 — 차선은 브라우저를 안 잰다).
    """
    try:
        import verify_readiness_scores as vrs
    except Exception as exc:                             # noqa: BLE001
        return None, [f"verify_readiness_scores 를 못 읽었다: {type(exc).__name__}: {exc}"]
    try:
        click, click_why = vrs.run_click_completes()
        rep = vrs.aa_report(click=click, click_why=click_why)
    except Exception as exc:                             # noqa: BLE001
        return None, [f"vrs.aa_report() 가 터졌다: {type(exc).__name__}: {exc}"]
    return rep, []


def measure_spec_coverage() -> tuple[dict | None, list[str]]:
    try:
        import verify_spec_coverage as vsc
    except Exception as exc:                             # noqa: BLE001
        return None, [f"verify_spec_coverage 를 못 읽었다: {type(exc).__name__}: {exc}"]
    try:
        rep = vsc.measure()
    except Exception as exc:                             # noqa: BLE001
        return None, [f"vsc.measure() 가 터졌다: {type(exc).__name__}: {exc}"]
    return rep, []


def fmt_score(sc: dict | None) -> str:
    """`aa_score()` 가 낸 한 칸 — `verify_readiness_scores.aa_fmt` 와 같은 모양으로 찍는다."""
    if not sc or sc.get("measured_pct") is None:
        return "회색 — 잰 칸 0/%d" % (sc.get("n_cells", 0) if sc else 0)
    return "%.1f[잰 칸 %d/%d]" % (sc["measured_pct"], sc["n_measured"], sc["n_cells"])


# ═══════════════════════════════════════════════════════════════════════════
# S1 · S2  —  같은 aa_report() 안의 onboard · click 을 그대로 옮긴다(두 번 안 잰다)
# ═══════════════════════════════════════════════════════════════════════════
def s1_from_onboard(ob: dict | None) -> dict:
    """S1 「첫 근무일에 제 일이 끝난다」 — 6종 × 8필수 48행 ≥ 90 %."""
    if not ob:
        return cell("S1", "첫 근무일에 제 일이 끝난다", GRAY,
                    "온보딩 48행 문서를 못 읽었다 — `docs/agent/onboarding_48.md` 의 "
                    "`N / 48 = P%` 줄이 없다")
    if not ob.get("consistent"):
        return cell("S1", "첫 근무일에 제 일이 끝난다", GRAY,
                    "문서 안에서 분자(%.1f/48=%.1f%%)와 적힌 백분율(%.1f%%)이 갈린다"
                    % (ob["sum"], ob["calc"], ob["pct"]))
    pct = ob["calc"]
    verdict = GREEN if pct >= 90.0 else RED
    return cell("S1", "첫 근무일에 제 일이 끝난다", verdict,
               "%.1f/48 (%.1f%%) · 문턱 ≥90%% · 출처 docs/agent/onboarding_48.md 마지막 재측"
               % (ob["sum"], pct))


def s2_from_click(click: dict | None, click_why: str) -> dict:
    """S2 「누르면 끝난다」 — 48 「누른 뒤」 ≥ 44/48. `click["green"]+["red"]==0` 이면
    그 게이트가 **한 행도 판정하지 않은 것**이다(증거가 낡았거나 없다) — 0 이 아니라 회색
    (aa_report() FC① 이 쓰는 것과 **같은 규칙**, D-369 — 여기서 새로 정하지 않는다)."""
    if not click:
        return cell("S2", "누르면 끝난다", GRAY,
                    "verify_click_completes.py 를 못 불렀다 — %s" % (click_why or "사유 없음"))
    if (click["green"] + click["red"]) == 0:
        return cell("S2", "누르면 끝난다", GRAY,
                    "그 게이트가 한 행도 판정하지 않았다(초록 0 · 빨강 0 · 회색 %d) — "
                    "0 이 아니라 못 쟀다(증거 `docs/agent/evidence/P-118/click_completes.json` "
                    "가 없거나 낡았다)" % click["grey"])
    verdict = GREEN if click["green"] >= 44 else RED
    return cell("S2", "누르면 끝난다", verdict,
               "초록 %d · 빨강 %d · 회색 %d / 48 · 문턱 ≥44/48 · %s"
               % (click["green"], click["red"], click["grey"], click.get("when", "")))


# ═══════════════════════════════════════════════════════════════════════════
# S3  —  OPS-19(자동) · OPS-04(복구)를 **import** 로 부른다. 재부팅 10/10 은 못 잰다.
# ═══════════════════════════════════════════════════════════════════════════
def s3_backup_and_reboot() -> dict:
    mark = {"OK": GREEN, "FAIL": RED, "UNDECIDABLE": GRAY}
    try:
        import verify_backup_autonomy as vba
        r19 = vba.run()
        v19 = r19["beat_dump"]["state"]
        w19 = (r19["beat_dump"].get("why") or "")[:90]
    except Exception as exc:                             # noqa: BLE001
        v19, w19 = "UNDECIDABLE", f"못 불렀다: {type(exc).__name__}: {exc}"[:90]
    try:
        import verify_backup_recovery as vbr
        r04 = vbr.run()
        v04 = r04["vault"]["state"]
        w04 = (r04["vault"].get("why") or "")[:90]
    except Exception as exc:                             # noqa: BLE001
        v04, w04 = "UNDECIDABLE", f"못 불렀다: {type(exc).__name__}: {exc}"[:90]
    subs = {mark.get(v19, GRAY), mark.get(v04, GRAY)}
    #: ★ 재부팅 10/10 은 대표 손(P-271)이지 이 판정기가 잴 수(코드로 반복)가 아니다 —
    #:   그래서 OPS-19·OPS-04 가 **둘 다 초록**이어도 이 행은 초록이 될 수 없다.
    #:   회색과 빨강을 섞지 않는다: 측정된 하위 조건이 빨강이면 행도 빨강, 아니면 회색.
    overall = RED if RED in subs else GRAY
    line = ("OPS-19(자동 · beat) %s(%s) · OPS-04(복구) %s(%s) · "
           "재부팅 뒤 10/10 은 이 판정기가 **안 잰다**(대표 손 · P-271 — 재부팅 없는 날 1/10)"
           % (v19, w19, v04, w04))
    return cell("S3", "아무도 없는 아침에 서 있다", overall, line)


# ═══════════════════════════════════════════════════════════════════════════
# S4  —  가짜 헤더 경계만 **직접** 호출(gx-shell 안). 나머지 둘은 안 잰다.
# ═══════════════════════════════════════════════════════════════════════════
def s4_fake_bearer(container: str, timeout: int = 240) -> dict:
    if not shutil.which("docker"):
        return cell("S4", "틀린 것을 틀렸다고 말한다", GRAY,
                    "docker 가 없다 — 가짜 헤더 탐침을 못 불렀다")
    out_path = "/tmp/gx_rc1_fake_bearer.json"
    cmd = ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
          container, "sh", "-c",
          f"python /repo/scripts/probe_fake_bearer.py {out_path}; echo GXRC=$?"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return cell("S4", "틀린 것을 틀렸다고 말한다", GRAY,
                    f"probe_fake_bearer 호출이 터졌다: {exc}")
    text = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"GXRC=(\d+)", text)
    rc = int(m.group(1)) if m else None
    if rc is None or rc == 2:
        return cell("S4", "틀린 것을 틀렸다고 말한다", GRAY,
                    f"probe_fake_bearer 가 판정 불가다(rc={rc}) — 꼬리 300자: {text[-300:]!r}")
    try:
        cat = subprocess.run(["docker", "exec", container, "cat", out_path],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        payload = json.loads(cat.stdout)
    except Exception as exc:                              # noqa: BLE001
        return cell("S4", "틀린 것을 틀렸다고 말한다", GRAY,
                    f"결과 json({out_path})을 못 읽었다: {type(exc).__name__}: {exc}")
    leaked, total = payload.get("leaked"), payload.get("total")
    only_fake = payload.get("only_fake")
    #: ★ 이 행의 세 조건 중 하나만 쟀다(가짜 헤더). 「감사 체인 새 끊김 0」·「시험 자료가
    #:   고객 화면에 0」은 이 판정기가 **안 잰다** — 그래서 leaked==0 이어도 행은 회색을
    #:   벗지 못한다(S3 과 같은 규칙 — 재는 것과 행 전체를 증명하는 것은 다른 일이다).
    overall = RED if leaked else GRAY
    line = ("가짜 헤더 경계: 분모 %s · 자료 나온 자리 %s(그중 익명은 막히던 자리 %s) — "
           "「감사 체인 새 끊김 0」·「시험 자료가 고객 화면에 0」은 이 판정기가 안 잰다"
           % (total, leaked, only_fake))
    return cell("S4", "틀린 것을 틀렸다고 말한다", overall, line)


# ═══════════════════════════════════════════════════════════════════════════
# S5 · S6 · S7  —  이 저장소에 **그 수를 내는 게이트가 아직 없다.** 지어내지 않는다.
# ═══════════════════════════════════════════════════════════════════════════
#: ★★ [P-275 · 2026-09-24 턴 AG] **세종 표를 읽는다 — 수를 손으로 안 적는다.**
#:
#:   턴 AF 까지 이 셋은 「그 수를 내는 게이트가 저장소에 없다」는 사유로 **회색**이었다.
#:   그 회색은 옳았다 — 공개 주소·TLS·가격 숫자·계약서 서명은 **인프라와 사람의 사실**
#:   이지 python 이 잴 수 있는 것이 아니고, 코드로 0 을 지어내면 그 0 은 측정이 아니라
#:   창작이다. 세종이 그 사실들을 **표 하나**로 적었고(WO-GX-20260925-10 §4-1),
#:   이 판정기는 그 표를 **읽기만** 한다.
#:
#:   ⇒ **여전히 이 판정기는 S5~S7 을 재지 않는다.** 읽는 것과 재는 것은 다르고,
#:     그 차이를 판정문이 매번 말한다(아래 `_sejong_line()` 의 「[세종 표]」 머리).
#:   ⇒ 표가 없거나 · 행이 없거나 · 값이 {0, 0.5, 1} 밖이거나 · 근거 칸이 비면
#:     **그 행은 회색**이다. 표가 생겼다고 자동으로 초록이 되지 않는다.
#:   ⇒ 눈금이 둘이다: 표는 **{0, 0.5, 1}**, 이 판정기의 칸은 **{빨강, 회색, 초록}**.
#:     0 → 빨강 · 1 → 초록 · **0.5 → 회색이 아니라 「반」**인데 이 판정기에 반 칸이
#:     없다. 0.5 를 초록으로 올리면 절반을 다 한 것으로 읽히고, 회색으로 내리면
#:     「못 쟀다」와 섞인다 — **둘 다 거짓이다.** 그래서 0.5 는 **빨강**으로 적고
#:     판정문에 「0.5 — 절반은 섰다」를 그대로 싣는다. 태그는 S1~S7 과 무관하므로
#:     (P-269) 이 보수적 선택이 태그를 막지 않는다.
SEJONG_TABLE = ROOT / "docs" / "design" / "GX-S1S7_상용조건_v1.0_20260925.md"

#: 표가 낼 수 있는 값 전수. 새 값이 필요하면 **표와 여기를 같이** 고친다 —
#: 한쪽만 고치면 판정기가 모르는 낱말을 만나 조용히 회색이 된다.
SEJONG_VALUES = {"0": RED, "0.5": RED, "1": GREEN}


def read_sejong_table(path=None) -> tuple[dict, str]:
    """세종 표를 읽어 `{행 id: (값문자열, 근거)}` 로 돌려준다. (표, 못 읽은 사유).

    ★ 파서를 느슨하게 두지 않는다 — 「읽었는데 틀리게 읽었다」가 「못 읽었다」보다 나쁘다.
      한 행은 `| S5 | 조건 | **0** | 근거 |` 모양이고, 값 칸에서 굵게 표시(`**`)를
      걷어낸 뒤 그대로 쓴다. 값이 `SEJONG_VALUES` 밖이면 **그 행을 안 담는다** —
      담아 두면 부르는 쪽이 모르는 낱말로 판정하게 된다.
    """
    path = path or SEJONG_TABLE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, "표를 못 읽었다(%s: %s)" % (type(exc).__name__, exc)
    rows = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        rid = cells[0].strip("* ")
        if rid not in ("S5", "S6", "S7"):
            continue
        value = cells[2].replace("*", "").strip()
        why = cells[3].strip()
        if value not in SEJONG_VALUES or not why:
            continue
        rows[rid] = (value, why)
    if not rows:
        return {}, "표는 있는데 S5~S7 행을 한 줄도 못 읽었다(모양이 바뀌었나)"
    return rows, ""


def _sejong_cell(rid: str, label: str, rows: dict, why_not: str) -> dict:
    """표 한 행 → 칸 하나. **읽은 것과 잰 것을 판정문이 구별해서 말한다.**"""
    if rid not in rows:
        return cell(rid, label, GRAY,
                    "[세종 표] 이 행을 못 읽었다 — %s · 자리: %s. "
                    "**표가 없으면 회색이다**(지어내지 않는다 · P-275)"
                    % (why_not or "표에 그 행이 없다", SEJONG_TABLE.name))
    value, why = rows[rid]
    verdict = SEJONG_VALUES[value]
    half = " — **0.5 다. 절반은 섰다**(이 판정기에 반 칸이 없어 빨강으로 적는다 — "            "초록으로 올리면 다 한 것으로 읽히고 회색으로 내리면 「못 쟀다」와 섞인다)"            if value == "0.5" else ""
    return cell(rid, label, verdict,
                "[세종 표 %s] 값 **%s**%s · 근거: %s "
                "(★ 이 판정기가 **잰 것이 아니라 읽은 것**이다 — 공개 주소·TLS·"
                "가격 숫자·계약서 서명은 python 이 잴 수 있는 사실이 아니다)"
                % (SEJONG_TABLE.name, value, half, why))


def s5_reach(rows=None, why_not="") -> dict:
    """S5 「밖에서 닿는다」 — 공개 주소 · TLS · 스테이징 · 실카메라 · 웹푸시 도달."""
    return _sejong_cell("S5", "밖에서 닿는다", rows or {}, why_not)


def s6_billing(rows=None, why_not="") -> dict:
    """S6 「청구서가 정직하다」 — 씨앗 0 · 계측기 제외 · 훈련 0원 · 가격 숫자 · 청구서 초안.

    ⚠ 「씨앗 청구 0」은 `backend/tests/test_p237_onboarding_probe_billing.py`(10건)가
      **이미 재고**, `--full-tests` 회차가 그 시험을 포함해 돈다. 여기서 다시 돌리지
      않는다(중복). 이 칸이 말하는 것은 **그 부분 수가 아니라 행 전체**다.
    """
    return _sejong_cell("S6", "청구서가 정직하다", rows or {}, why_not)


def s7_paperwork(rows=None, why_not="") -> dict:
    """S7 「종이가 나간다」 — 사건 1쪽 · 월간 자동본 · 훈련 배너 · 별지 1호 · 계약서 · SLA."""
    return _sejong_cell("S7", "종이가 나간다", rows or {}, why_not)


# ═══════════════════════════════════════════════════════════════════════════
# 전량 시험 — RC-1 태그의 **유일한 초록 문턱**. 기본은 안 돈다(비용).
# ═══════════════════════════════════════════════════════════════════════════
def measure_full_suite(run_it: bool, container: str, timeout: int) -> dict:
    """MEMORY 의 정본 호출을 **그대로** 쓴다 — `-w /repo` + `backend/tests` 로 부르면
    뿌리가 갈려 거짓 실패 다섯이 난다(이 저장소의 실측 함정). 그래서 `-w /app` + `tests`."""
    if not run_it:
        return {"verdict": "skipped",
               "why": "기본으로 안 돈다(비용 — 분 단위) · --full-tests 로 켜라"}
    if not shutil.which("docker"):
        return {"verdict": "skipped", "why": "docker 가 없다"}
    cmd = ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
          "-w", "/app", container, "python", "-m", "pytest", "tests", "-q",
          "--create-db", "-p", "no:randomly"]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"verdict": "skipped", "why": f"{timeout}초 안에 안 끝났다 — 시간을 늘려라"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"verdict": "skipped", "why": f"부르다 터졌다: {exc}"}
    out = (p.stdout or "") + (p.stderr or "")
    passed = _grab_int(r"(\d+) passed", out)
    failed = _grab_int(r"(\d+) failed", out)
    errors = _grab_int(r"(\d+) error", out)
    if passed is None and failed is None and errors is None:
        return {"verdict": "skipped",
               "why": f"요약 줄을 못 읽었다(exit {p.returncode}) — 꼬리 400자: {out[-400:]!r}"}
    return {"verdict": "measured", "passed": passed or 0,
           "failed": (failed or 0) + (errors or 0),
           "elapsed_s": round(time.time() - t0, 1), "exit": p.returncode,
           "tail": out[-300:]}


def _grab_int(pat: str, text: str):
    m = re.search(pat, text)
    return int(m.group(1)) if m else None


# ═══════════════════════════════════════════════════════════════════════════
# 태그 판정 — P-269. 초록을 강제하는 조건은 0 개다.
# ═══════════════════════════════════════════════════════════════════════════
def decide_tag(full_suite: dict) -> tuple[bool, str]:
    """`rc-1-internal` 태그 조건(P-269): **전량 0 실패** + 빨강 목록 등재 + 회색 목록 등재.

    ★★ S1~S7 의 빨강·회색은 이 조건에 **안 들어간다** — 「내부 RC」는 그 빨강·회색을
      **가진 채로** 태그하는 것이 세종 판정이다. 「빨강 목록 등재」·「회색 목록 등재」는
      이 판정기가 그 목록을 **항상 출력하는 것**(아래 main() — 숨기는 갈래가 없다)으로
      코드로 이미 보장된다. 그래서 이 함수가 실제로 가르는 문턱은 **하나**다.
    """
    if full_suite.get("verdict") != "measured":
        return False, ("전량 시험을 못/안 쟀다(%s) — 태그 조건 ①(전량 0 실패)이 "
                       "안 선다(회색 · 실패로 세지 않는다)" % full_suite.get("why", ""))
    if full_suite["failed"] != 0:
        return False, ("전량 시험 실패 %d건(통과 %d) — 태그 조건 ①이 깨졌다"
                       % (full_suite["failed"], full_suite["passed"]))
    return True, ("전량 %d/%d(실패 0) · 빨강·회색 목록은 본문에 항상 실린다(코드 보장) "
                 "— 태그 조건 성립. S1~S7 의 빨강·회색은 이 태그를 막지 않는다(P-269)"
                 % (full_suite["passed"], full_suite["failed"]))


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 판정 규칙만(음성 대조 포함). 실물을 안 부른다 — 빠르다.
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad = []

    # ── cell() 은 verdict 셋 밖을 거부한다 ──────────────────────────────
    try:
        cell("X", "x", "yellow", "")
        bad.append("cell() 이 정의되지 않은 판정(yellow)을 받아 준다")
    except AssertionError:
        pass

    # ── S1 — 문턱 90%, 회색·빨강·초록 셋 다 확인 ────────────────────────
    c = s1_from_onboard(None)
    if c["verdict"] != GRAY:
        bad.append("S1: 문서가 없으면 회색이어야 하는데 %s" % c["verdict"])
    c = s1_from_onboard({"sum": 34.0, "n": 48, "pct": 70.8, "calc": 70.8, "consistent": True})
    if c["verdict"] != RED:
        bad.append("S1: 34/48(70.8%%) 은 빨강(<90%%)이어야 하는데 %s" % c["verdict"])
    c = s1_from_onboard({"sum": 44.0, "n": 48, "pct": 91.7, "calc": 91.7, "consistent": True})
    if c["verdict"] != GREEN:
        bad.append("S1: 44/48(91.7%%) 은 초록(≥90%%)이어야 하는데 %s" % c["verdict"])
    #: ★ 음성 — 문서 안 분자·백분율이 갈리면(모순) **회색**이지 초록이 아니다
    c = s1_from_onboard({"sum": 44.0, "n": 48, "pct": 10.0, "calc": 91.7, "consistent": False})
    if c["verdict"] != GRAY:
        bad.append("S1: 분자·백분율이 갈리면 회색이어야 하는데 %s — 모순을 초록으로 덮었다"
                   % c["verdict"])

    # ── S2 — 「한 행도 안 쟀다」(0/0)는 회색이지 빨강이 아니다(D-301) ────
    c = s2_from_click({"green": 0, "red": 0, "grey": 48, "when": ""}, "")
    if c["verdict"] != GRAY:
        bad.append("S2: 초록0·빨강0·회색48(안 쟀다)은 회색이어야 하는데 %s — "
                   "못 잰 것을 0(빨강)으로 눌러 적었다" % c["verdict"])
    c = s2_from_click({"green": 44, "red": 4, "grey": 0, "when": "t"}, "")
    if c["verdict"] != GREEN:
        bad.append("S2: 44/48 초록은 초록(≥44)이어야 하는데 %s" % c["verdict"])
    c = s2_from_click({"green": 32, "red": 2, "grey": 14, "when": "t"}, "")
    if c["verdict"] != RED:
        bad.append("S2: 32/48 초록은 빨강(<44)이어야 하는데 %s" % c["verdict"])

    # ── S3/S4 — 재는 조각이 빨강이면 행도 빨강, 아니면(초록/회색 섞임) 회색 ──
    #    (내부 결합 규칙을 판정 함수 없이 직접 흉내 낸다 — 실물 호출은 안 한다)
    subs = {RED, GRAY}
    overall = RED if RED in subs else GRAY
    if overall != RED:
        bad.append("S3/S4 결합 규칙 — 하나라도 빨강이면 행은 빨강이어야 한다")
    subs = {GREEN, GRAY}
    overall = RED if RED in subs else GRAY
    if overall != GRAY:
        bad.append("S3/S4 결합 규칙 — 초록·회색만 있는데 초록이 되면 안 된다"
                   "(재부팅 10/10 을 못 재므로 이 행은 절대 초록이 될 수 없다)")

    # ── 태그 — 음성 대조: 전량을 안 돌리면 태그가 서면 안 된다 ─────────
    ok, why = decide_tag({"verdict": "skipped", "why": "테스트"})
    if ok:
        bad.append("태그: 전량 시험을 안 돌렸는데(회색) 태그가 섰다 — 회색을 초록으로 셌다")
    ok, why = decide_tag({"verdict": "measured", "passed": 2135, "failed": 3})
    if ok:
        bad.append("★★ 태그: 전량 실패 3건인데 태그가 섰다 — 이것이 이 판정기의 "
                   "유일한 초록 문턱인데 뚫렸다")
    ok, why = decide_tag({"verdict": "measured", "passed": 2135, "failed": 0})
    if not ok:
        bad.append("태그: 전량 0실패인데 태그가 안 섰다 — %s" % why)
    #: ★★ 음성의 음성 — S1~S7 이 전부 빨강·회색이어도 전량 0실패면 태그는 **서야 한다**
    #:   (「초록을 강제하지 않는다」의 반대쪽 오류도 막는다 — 이 판정기가 겁먹고
    #:   S 셀들을 태그 조건에 슬쩍 끼워 넣으면 「내부 RC」라는 말 자체가 불가능해진다).
    if not ok:
        bad.append("★★ S1~S7 무관 원칙이 깨졌다면 여기서도 잡혀야 한다")

    # ── ★★ **출생 표본** (D-310) — 이 파일을 만들게 한 바로 그 사례 ──────────
    #   [실측 2026-09-23 · 턴 AF · 조율자 창 ②] 이 판정기를 처음 돌렸을 때
    #   전량 시험이 **2151 통과 · 1 실패**였다. 그 한 건은
    #   `EntrySurfaceIsOneTest::test_every_k1_consumer_is_registered_with_a_reason` —
    #   P-266 훈련 사건 씨앗 명령이 `K1_CONSUMERS` 에 등재 없이 들어온 것을
    #   진입면 철조망이 물었다. 그때 이 판정기는 **태그를 안 세웠고**,
    #   그 한 줄이 없었으면 조율자는 「S1~S7 이 온통 빨강이니 그런가 보다」로
    #   읽고 **실패 1건을 모르고 넘어갔을 것**이다.
    #   ★ 이 표본이 지키는 것은 숫자 1 이 아니라 **문턱이 1 이라는 사실**이다:
    #     수천 건이 통과해도 **한 건이 실패하면 태그는 안 선다.**
    born_red = {"verdict": "measured", "passed": 2151, "failed": 1}
    ok, why = decide_tag(born_red)
    if ok:
        bad.append("**출생 표본** — 2151 통과 · **1 실패**인데 태그가 섬. "
                   "2026-09-23 진입면 철조망 한 건이 여기서 막혔다 — "
                   "문턱은 「거의 다」가 아니라 **실패 0**이다")
    if "1" not in str(why):
        bad.append("**출생 표본** — 안 선 까닭에 실패 건수가 안 적혀 있다. "
                   "사람이 「몇 건이 막았나」를 묻고 다시 돌려야 한다면 그 판정문은 반쪽이다")
    #: ★ 그리고 그 한 건을 **사유와 함께 등재**해 고친 뒤 다시 돌리니 2152/0 이 됐고
    #:   태그가 섬다 — **시험을 약하게 해서 섬 게 아니다.** 그 뒤쪽도 잠그다.
    ok, why = decide_tag({"verdict": "measured", "passed": 2152, "failed": 0})
    if not ok:
        bad.append("**출생 표본 뒷면** — 2152/0 인데 태그가 안 섬다: %s" % why)

    # ── ★★ P-275 세종 표 — **읽기가 재기를 흉내 내지 않는가** ──────────
    import tempfile as _tf
    from pathlib import Path as _P

    def _tbl(text):
        d = _P(_tf.mkdtemp())
        f = d / "t.md"
        f.write_text(text, encoding="utf-8")
        return f

    good = _tbl("| # | 조건 | 값 | 근거 |" + chr(10) + "|---|---|---|---|" + chr(10)
                + "| S5 | 밖에서 닿는다 | **0** | 주소 0 |" + chr(10)
                + "| S6 | 청구서 | **0.5** | 가격 0/4 |" + chr(10)
                + "| S7 | 종이 | **1** | 다 섰다 |" + chr(10))
    rows, why = read_sejong_table(good)
    if sorted(rows) != ["S5", "S6", "S7"]:
        bad.append("세종 표: 세 행을 다 못 읽었다 — %r (%s)" % (sorted(rows), why))
    if _sejong_cell("S5", "x", rows, "")["verdict"] != RED:
        bad.append("세종 표: 값 0 이 빨강이 아니다")
    if _sejong_cell("S7", "x", rows, "")["verdict"] != GREEN:
        bad.append("세종 표: 값 1 이 초록이 아니다")
    s6 = _sejong_cell("S6", "x", rows, "")
    if s6["verdict"] != RED or "0.5" not in s6["line"]:
        bad.append("★★ 세종 표: 0.5 가 빨강이 아니거나 판정문이 「0.5」를 안 말한다 — "
                   "0.5 를 초록으로 올리면 다 한 것으로 읽히고, 그 사실이 판정문에 "
                   "안 남으면 사람은 그냥 빨강으로 읽는다")

    #: ★ 음성 대조 ① — **표가 없으면 회색이다.** 없는데 초록·빨강을 내면 그 수는 창작이다.
    missing_rows, missing_why = read_sejong_table(_P("/does/not/exist/xyz.md"))
    if missing_rows or not missing_why:
        bad.append("세종 표: 없는 파일에서 행을 읽었다고 한다")
    if _sejong_cell("S5", "x", missing_rows, missing_why)["verdict"] != GRAY:
        bad.append("★★ 세종 표가 없는데 회색이 아니다 — 지어냈다")

    #: ★ 음성 대조 ② — **모르는 값은 안 담는다.** 담으면 부르는 쪽이 모르는 낱말로 판정한다.
    weird, _ = read_sejong_table(_tbl(
        "| # | 조건 | 값 | 근거 |" + chr(10) + "|---|---|---|---|" + chr(10)
        + "| S5 | x | **0.7** | 근거 |" + chr(10)
        + "| S6 | x | **1** |  |" + chr(10)))
    if "S5" in weird:
        bad.append("세종 표: 규칙 밖 값 0.7 을 담았다 — {0, 0.5, 1} 뿐이다")
    if "S6" in weird:
        bad.append("★★ 세종 표: **근거가 빈 행**을 담았다 — 빈 사유는 면제와 구별되지 않는다")
    if _sejong_cell("S5", "x", weird, "")["verdict"] != GRAY:
        bad.append("규칙 밖 값인데 회색이 아니다")

    if bad:
        print(f"{TAG} 자기시험 실패:")
        for b in bad:
            print(f"    {b}")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — cell() 판정값 검사 · S1 문턱(회색·빨강·초록·모순) 4종 · "
         f"S2 「안 쟀다」 구분 3종 · S3/S4 결합 규칙 2종 · 태그 음성 대조 4종(회색·실패·"
         f"0실패·무관 원칙) · **세종 표 P-275 6종**(0·0.5·1 · 표 없음 · 규칙 밖 값 · 빈 근거) · **출생 표본 1**(2026-09-23 진입면 철조망 한 건이 "
         f"태그를 막았다 · 2151/1 → 안 섬 · 2152/0 → 섬)")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 본문
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="RC-1 판정기 — 09-25 「내부 RC」 선언용 수")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--full-tests", action="store_true",
                    help="전량 단위+통합 시험도 돌린다(분 단위 · RC-1 태그의 유일한 문턱)")
    ap.add_argument("--container", default=os.environ.get("GX_ROUTE_CONTAINER", "gx-shell"))
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        print(f"{TAG} 자기시험이 먼저 실패했다 — 판정기 자체를 못 믿는다", file=sys.stderr)
        return EXIT_FAIL

    from _gate_header import gate_header

    red_lines: list[str] = []
    gray_lines: list[str] = []
    cells: list[dict] = []

    rep, err = measure_fc_pr_cr()
    gray_lines += err
    spec, err2 = measure_spec_coverage()
    gray_lines += err2

    fc = pr = cr = None
    status100 = None
    onboard_cell = click_cell = None
    if rep:
        fc, pr, cr = rep.get("fc"), rep.get("pr"), rep.get("cr")
        red_lines += rep.get("red", [])
        gray_lines += rep.get("grey", [])
        drop = rep.get("drop")
        status100 = drop["status"] if drop else None
        onboard_cell = s1_from_onboard(rep.get("onboard"))
        click_cell = s2_from_click(rep.get("click"),
                                   "" if rep.get("click") else "run_click_completes 가 못 얻었다")
    else:
        onboard_cell = s1_from_onboard(None)
        click_cell = s2_from_click(None, "aa_report() 자체를 못 불렀다")
    cells += [onboard_cell, click_cell]

    spec_pct = spec_den = None
    if spec:
        red_lines += spec.get("red", [])
        gray_lines += spec.get("grey", [])
        sc = spec.get("score") or {}
        spec_pct, spec_den = sc.get("pct"), sc.get("den")

    cells.append(s3_backup_and_reboot())
    cells.append(s4_fake_bearer(args.container, timeout=min(args.timeout, 300)))
    #: ★ [P-275] 표를 **한 번만** 읽어 셋에 나눠 준다 — 세 번 읽으면 그 사이에 파일이
    #:   바뀌었을 때 같은 회차 안에서 세 칸이 서로 다른 판을 보고 판정한다.
    sejong_rows, sejong_why = read_sejong_table()
    cells.append(s5_reach(sejong_rows, sejong_why))
    cells.append(s6_billing(sejong_rows, sejong_why))
    cells.append(s7_paperwork(sejong_rows, sejong_why))

    full = measure_full_suite(args.full_tests, args.container, args.timeout)
    if full["verdict"] == "skipped":
        gray_lines.append("전량 시험: %s" % full["why"])
    elif full["failed"]:
        red_lines.append("전량 시험 실패 %d건(통과 %d)" % (full["failed"], full["passed"]))

    for c in cells:
        line = f'{c["id"]} {c["label"]}: {c["line"]}'
        if c["verdict"] == RED:
            red_lines.append(line)
        elif c["verdict"] == GRAY:
            gray_lines.append(line)

    tagged, tag_why = decide_tag(full)

    n_cells = 3 + 1 + 1 + 7 + 1        # FC·PR·CR + 기능명세 + 상용 + S1~S7 + 전량
    n_measured = (sum(1 for sc in (fc, pr, cr) if sc and sc.get("measured_pct") is not None)
                 + (1 if spec_pct is not None else 0)
                 + (1 if status100 is not None else 0)
                 + sum(1 for c in cells if c["verdict"] != GRAY)
                 + (1 if full["verdict"] == "measured" else 0))

    gate_header(
        __file__,
        target="09-25 「내부 RC」 선언문(WO-GX-20260924-09 §4-1)이 읽을 세 수 + S1~S7",
        as_="(자격증명 없음 — 이미 있는 산출기를 import 로 부르고, gx-shell 안에서 "
           "가짜 헤더 탐침만 자격 없는 가짜 토큰으로 부른다)",
        source="verify_readiness_scores.aa_report() · verify_spec_coverage.measure() · "
              "verify_backup_autonomy/recovery.run() · probe_fake_bearer.py(gx-shell) — "
              "전부 **부른다**(D-369, 두 벌을 두지 않는다)",
        measured=f"RC-1 칸 **분모 {n_cells}** · 잰 칸 {n_measured} — 회색은 0 으로도 1 로도 "
                f"안 세인다",
    )

    print(f"{TAG} [입력] RC-1 칸 분모 {n_cells}(세 수 3 · 기능명세 1 · 상용 1 · S1~S7 7 · "
         f"전량 1) · 잰 칸 {n_measured}")
    print(f"{TAG} FC {fmt_score(fc)} · PR {fmt_score(pr)} · CR {fmt_score(cr)}")
    print(f"{TAG} 기능명세 포함 완료율 %s" %
         (f"{spec_pct:.1f}%(분모 {spec_den})" if spec_pct is not None else "회색 — 못 읽었다"))
    print(f"{TAG} 상용 /100 %s" %
         (f"{status100}" if status100 is not None else "회색 — 8영역 게이트를 못 불렀거나 kind 합을 못 냈다"))
    for c in cells:
        print(f"{TAG} {c['id']} [{MARK[c['verdict']]} {c['verdict']}] {c['label']} — {c['line']}")
    if full["verdict"] == "measured":
        print(f"{TAG} 전량 시험: 통과 {full['passed']} · 실패 {full['failed']} "
             f"({full['elapsed_s']}초)")
    else:
        print(f"{TAG} 전량 시험: **회색** — {full['why']}")

    print(f"{TAG} ── 빨강 목록({len(red_lines)}건) — 등재 ──────────────────────")
    for r in red_lines:
        print(f"{TAG}   X {r}")
    print(f"{TAG} ── 회색 목록({len(gray_lines)}건) — 등재 ──────────────────────")
    for g in gray_lines:
        print(f"{TAG}   ? {g}")

    print(f"{TAG} `rc-1-internal` 태그: {'선다' if tagged else '안 선다'} — {tag_why}")

    report = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fc": fc, "pr": pr, "cr": cr,
        "spec_coverage_pct": spec_pct, "spec_coverage_den": spec_den,
        "status_100": status100,
        "s_rows": cells, "full_suite": full,
        "red": red_lines, "grey": gray_lines,
        "tag": "rc-1-internal" if tagged else None, "tag_why": tag_why,
        "denominator_cells": n_cells, "measured_cells": n_measured,
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1,
                                              default=str), encoding="utf-8")
        print(f"{TAG} 기록 → {args.json}")

    if full["verdict"] == "measured" and full["failed"]:
        return EXIT_FAIL
    if full["verdict"] != "measured":
        return EXIT_GRAY
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
