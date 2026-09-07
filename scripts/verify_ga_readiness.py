#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-346 — 상용 오픈 기준 8영역을 **절 단위**로 판정하고 가중 합계를 낸다.

왜 이 표가 계약 표와 따로인가 (D-345)
-------------------------------------
    계약 39절을 100% 채워도 **상용 출시는 되지 않는다.** 계약에 없는 것이 상용에는 필수다.
    그래서 축을 둘로 나눠 잰다. **합쳐서 하나의 %로 내지 않는다** —
    합치는 순간 어느 쪽도 알 수 없게 된다.

보는 것 — 일곱
--------------
  ① 가중치 합이 100 인가 (모수가 흔들리면 아래 수는 전부 무의미하다)
  ② 상태가 넷 안에 있는가 — 구현 · 미착수 · 잠김 · 미측정
  ③ **「부분」류가 한 칸이라도 있으면 exit 1** (D-314) — 「부분」은 상태가 아니라
     **아직 안 쪼갠 것의 이름**이다
  ④ ★ **'구현' 에 증명이 있고 그 파일이 실재하는가** — 없으면 그 칸은 '미측정'이다 (D-346)
  ⑤ '잠김' 의 blocker id 가 `DA-05/blockers.yaml` 에 실재하는가
  ⑥ '미착수'·'미측정' 에 사유가 있는가 (사유 없는 빈칸은 잊은 것과 구별되지 않는다)
  ⑦ 영역 ①은 **계약 절 대장에서 파생**한다 — 절 상태를 두 곳에 적지 않는다
  ⑧ ★★ **대장 상태와 게이트 색이 같은가** (P-85 · 2026-09-06 턴 I) — 아래를 보라

★★ P-85 [세종 판정 2026-09-06 · 턴 I] — **대장 상태와 게이트 색은 같아야 한다**
------------------------------------------------------------------------------
출생 표본은 `SEC-18` 이다. `scripts/verify_prod_settings.py` 가 **5/5 초록**을 내고
있는데 대장의 그 자리는 **미착수**였다. 아무 색도 안 났다 — 이 판정기가 절의 *모양*
(상태·증명·사유)만 보고 그 절이 가리키는 **게이트를 부르지 않았기** 때문이다.

    갈리는 방향은 둘이다. 둘 다 exit 1 이다.

    ① 게이트 **초록** · 대장 **미구현**  → 다 해 놓고 안 적었다.
       수가 실제보다 **낮게** 나가고, 낮은 수를 보는 사람은 이미 닫힌 것을 또 연다
    ② 대장 **구현** · 게이트 **빨강**   → 적어 놓고 무너졌다. **이쪽이 더 나쁘다** —
       대장이 「닫혔다」고 말하는 동안 그 자리는 열려 있다

그래서 절마다 `gate:` 칸에 **그 절을 지키는 판정기의 이름**을 적고, 이 판정기가
그것을 실제로 **부른다**(읽어서 답하지 않는다 · D-210).

    exit 0 초록 · exit 1 빨강 · exit 2 **회색**(못 쟀다 — 컨테이너가 필요한 게이트 등)

회색은 갈림으로 세지 않는다. 대신 **몇 개를 못 쟀는지 말한다** — 「검사 못함」과
「0건 검사」를 가르는 그 규칙 그대로다(D-301). 못 부른 것을 초록으로 세면 이 검사
자체가 거짓 초록이 된다.

★ 출생 표본 (D-310)
-------------------
이 도구를 만들게 한 문장은 D-346 의 이것이다:

    **증명이 없는 칸은 '구현'으로 적을 수 없다. 그런 칸은 '미측정'이다.**

그래서 자기시험의 첫 갈래가 **「증명 없는 '구현'」과 「없는 파일을 가리키는 증명」**이다.
거기서 초록이 나오면 이 표는 스스로를 부풀린다 — 착시 ①(부착률을 완성으로)의 상용판이다.

    python scripts/verify_ga_readiness.py            # 판정 + 가중 합계
    python scripts/verify_ga_readiness.py --list     # 영역별 절 표
    python scripts/verify_ga_readiness.py --table    # 대표 보고용 표 (마크다운)
    python scripts/verify_ga_readiness.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-346" / "ga_readiness.yaml"
BLOCKERS = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "blockers.yaml"
CONTRACT = ROOT / "docs" / "agent" / "evidence" / "D-309" / "contract_ac_ledger.yaml"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

DONE = "구현"
STATUSES = (DONE, "미착수", "잠김", "미측정")
BANNED = ("부분", "진행중", "일부", "대부분", "거의")
NEEDS_WHY = ("미착수", "미측정")

#: 「잠김」·「미측정」이 어디에 속하는가 (2026-09-21 · 세종 §3 판정).
#:   design 은 **분모에서 뺀다** — 하지 않기로 한 것은 못 한 것이 아니다.
#:   out 은 분모에 남기고 따로 센다 — 조건이 열어 준다.
HANDS = ("design", "out", "in")


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로 둔다
# ═══════════════════════════════════════════════════════════════════════════

def judge_clause(clause: dict, *, exists, blocker_ids: set[str]) -> list[str]:
    """절 하나를 판정한다. 어긋난 것들을 돌려준다 — **판정은 부르는 쪽이 한다.**"""
    cid = clause.get("id", "(id 없음)")
    status = (clause.get("status") or "").strip()
    out: list[str] = []

    if status in BANNED:
        out.append("%s: 상태 «%s» — 「부분」류는 상태가 아니다. 절로 쪼개라 (D-314)" % (cid, status))
        return out
    if status not in STATUSES:
        out.append("%s: 상태 «%s» 가 넷 밖이다 (%s)" % (cid, status, " · ".join(STATUSES)))
        return out

    if status == DONE:
        proof = (clause.get("proof") or "").strip()
        if not proof:
            out.append("%s: '구현' 인데 증명이 없다 — **그런 칸은 '미측정'이다** (D-346)" % cid)
        elif not exists(proof):
            out.append("%s: 증명이 가리킨 «%s» 가 없다 — 없는 증명은 문서다" % (cid, proof))

    #: ★ P-18 턴(2026-09-21) — **분류하지 않은 것은 분모에서 뺄 수 없다.**
    #:   「잠김」·「미측정」은 셋 중 하나여야 한다:
    #:     design  하지 않기로 한 것 — 기능이 아니라 규칙이다. 100%의 대상이 아니다
    #:     out     손 밖 — 상대방·기관·GPU·대표. 조건이 성립하면 열린다
    #:     in      손 안 — 우리가 닫을 수 있다. **이것이 남아 있는 한 100%가 아니다**
    #:   분류를 안 적으면 그 절은 조용히 「어쩔 수 없는 것」이 된다.
    if status in ("잠김", "미측정"):
        hand = (clause.get("hand") or "").strip()
        if hand not in HANDS:
            out.append("%s: '%s' 인데 hand 가 %r 다 — 허용: %s. **분류하지 않은 것은 "
                       "분모에서 뺄 수 없다**" % (cid, status, hand, ", ".join(HANDS)))
        elif len((clause.get("hand_why") or "").strip()) < 10:
            out.append("%s: hand=%s 인데 사유가 없다 — 「손 밖」은 선언이지 면제가 아니다"
                       % (cid, hand))

    if status == "잠김":
        blocker = (clause.get("blocker") or "").strip()
        if not blocker:
            out.append("%s: '잠김' 인데 blocker 가 없다 — 무엇이 막는지 말하지 않는다" % cid)
        elif blocker not in blocker_ids:
            out.append("%s: blocker «%s» 가 잠금 대장에 없다" % (cid, blocker))

    #: ★ P-85 — `gate:` 는 **그 절을 지키는 판정기의 이름**이다. 없는 이름을 적으면
    #:   불일치 검사가 그 절을 조용히 건너뛰고, 건너뛴 절은 지켜지는 것처럼 보인다.
    gate = (clause.get("gate") or "").strip()
    if gate and not exists(gate):
        out.append("%s: gate 가 가리킨 «%s» 가 없다 — 없는 판정기는 아무것도 안 지킨다" % (cid, gate))

    if status in NEEDS_WHY and not (clause.get("why") or "").strip():
        out.append("%s: '%s' 인데 사유가 없다 — 잊은 것과 구별되지 않는다" % (cid, status))

    # ★ '미착수'·'미측정' 인데 blocker 를 단 것은 허용한다(그 자리가 왜 안 되는지의 근거다).
    blocker = (clause.get("blocker") or "").strip()
    if blocker and blocker not in blocker_ids:
        out.append("%s: blocker «%s» 가 잠금 대장에 없다" % (cid, blocker))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ⑧ 대장 ↔ 게이트 불일치 (P-85)
# ═══════════════════════════════════════════════════════════════════════════

#: 게이트 하나에 주는 시간. 넘으면 **회색**이다 — 죽은 게이트를 초록으로 세지 않는다.
#: ⚠ 짧게 두는 이유: 이 검사가 느리면 사람이 `--no-gates` 로 끄고, 꺼진 게이트는
#:   아무것도 안 지킨다(D-353). 다른 게이트를 **또 부르는** 게이트(예:
#:   `verify_measure_repro.py`)는 여기서 가리키지 않는다 — 그것 하나가 4분을 먹었다.
GATE_TIMEOUT_S = 120

#: 자기 자신은 부르지 않는다. 부르면 무한히 자기를 부른다.
GATE_SELF = "scripts/verify_ga_readiness.py"

GATE_GREEN, GATE_RED, GATE_GREY = 0, 1, 2


def judge_gate_alignment(cid: str, status: str, rc, gate: str) -> str | None:
    """대장의 상태와 게이트의 색이 갈리는가. **판정식은 여기 한 곳에만 둔다** (D-212).

    rc 가 None 이거나 2 면 **못 쟀다**(회색) — 갈림이 아니다. 회색을 갈림으로 세면
    컨테이너가 없는 자리마다 빨강이 서고, 그런 빨강을 몇 번 본 사람은 게이트를 끈다(D-353).
    """
    if rc is None or rc == GATE_GREY:
        return None
    if rc == GATE_GREEN and status != DONE:
        return ("%s: 게이트 «%s» 가 **초록**인데 대장은 '%s' 다 — 다 해 놓고 안 적었다. "
                "수가 실제보다 낮게 나가고, 낮은 수를 보는 사람은 이미 닫힌 것을 또 연다 (P-85)"
                % (cid, gate, status))
    if rc == GATE_RED and status == DONE:
        return ("%s: 대장은 '구현' 인데 게이트 «%s» 가 **빨강**이다 — 적어 놓고 무너졌다. "
                "대장이 「닫혔다」고 말하는 동안 그 자리는 열려 있다 (P-85)"
                % (cid, gate))
    return None


#: ★ [실측 2026-09-06 · 턴 I · 조율자] **호스트에서 부르면 넷이 회색이었다.**
#:   첫 실행에서 못 잰 6절 중 넷(`verify_purge` · `verify_alarm_budget` ×2 ·
#:   `verify_camera_pulse`)이 낸 마지막 줄은 판정이 아니라 **사용법 안내**였다:
#:   「컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다」. Django 가 필요한
#:   판정기이고 호스트에는 dj-core 가 없다 — 그것은 제품의 회색이 아니라 **부르는
#:   자리를 틀린 회색**이다. 회색 여섯을 그대로 두면 P-85 는 그 여섯 절에서
#:   **아무것도 대조하지 않는다** — 대조하지 않는 검사가 초록처럼 보이는 자리다.
#:   그래서 그 자리를 이 저장소의 기존 문으로 넘긴다(`verify_route_alive` 와 같은 위임).
#:   ⚠ 비밀번호는 **이름만** 넘긴다 — `docker exec -e NAME`(값 없이)은 제 환경에서
#:     값을 가져가므로 프로세스 목록에 안 남는다.
NEEDS_DJANGO = (
    "verify_purge.py", "verify_alarm_budget.py", "verify_camera_pulse.py",
    "verify_migrations.py", "verify_minio.py", "ops_alert_routing.py",
)
PASS_BY_NAME = ("MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
                "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "MINIO_BUCKET_NAME")


#: ★ [실측 2026-09-07 · 턴 I · 조율자] **판정기가 부르는 사람의 셸에 기대고 있었다.**
#:   컨테이너로 넘기는 판정기들은 MinIO 자격증명과 차선 이름을 환경에서 받는데,
#:   그 값을 **부르는 사람이 export 해 주어야** 했다. 손으로 부르면 초록, pre-commit
#:   훅이 부르면 회색 — **같은 나무인데 부르는 자리에 따라 색이 달랐다.**
#:   회색은 초록이 아니므로 훅은 옳게 멈췄지만, 멈춘 이유는 제품이 아니라 환경이다(P-70).
#:   값이 사는 자리는 저장소 밖 한 곳이다 — 여기서 **직접 읽는다.**
#:   ⚠ 이미 환경에 있는 값은 덮지 않는다(CI 가 준 값이 파일에 지면 안 된다).
_LOCAL_ENV_FILES = (".env.gates", ".env.local", ".env")
_LOCAL_ENV_KEYS = ("GX_API", "GX_ROUTE_CONTAINER", "GX_ROUTE_USER", "GX_ROUTE_PASSWORD",
                   "GX_PROBE_USER", "GX_PROBE_PASSWORD", "GX_SEED_ROLE_PASSWORD",
                   "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
                   "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "MINIO_BUCKET_NAME")


def _load_local_env() -> None:
    for name in _LOCAL_ENV_FILES:
        f = ROOT / name
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k in _LOCAL_ENV_KEYS and not os.environ.get(k):
                os.environ[k] = v.strip().strip('"').strip("'")
    #: MinIO 는 저장소 안에서 이름이 둘이다(`ROOT_USER` 는 compose 가 읽고
    #: `ACCESS_KEY` 는 판정기가 읽는다). 한 자리에서 이어 준다 — 두 벌은 어긋난다(D-369).
    if not os.environ.get("MINIO_ACCESS_KEY") and os.environ.get("MINIO_ROOT_USER"):
        os.environ["MINIO_ACCESS_KEY"] = os.environ["MINIO_ROOT_USER"]
    if not os.environ.get("MINIO_SECRET_KEY") and os.environ.get("MINIO_ROOT_PASSWORD"):
        os.environ["MINIO_SECRET_KEY"] = os.environ["MINIO_ROOT_PASSWORD"]
    os.environ.setdefault("MINIO_ENDPOINT", "minio:9000")
    #: 게이트를 **전수로** 부르는 자리는 검증 차선(V)이다 — 「다섯째 이름」(P-70).
    #: 이 이름이 없으면 세션 판정기가 「차선 전용 계정이 아니다」로 회색을 낸다.
    if not os.environ.get("GX_LANE") and os.environ.get("GX_PROBE_USER", "").endswith("_v"):
        os.environ["GX_LANE"] = "v"


def _container() -> str:
    return os.environ.get("GX_ROUTE_CONTAINER", "").strip()


def run_gate(rel: str) -> tuple[int | None, str]:
    """게이트를 **부른다** — 읽어서 답하지 않는다 (D-210). (종료코드, 마지막 줄)."""
    path = ROOT / rel
    if not path.exists():
        return None, "그 파일이 없다"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    name = rel.rsplit("/", 1)[-1]
    cont = _container()
    if name in NEEDS_DJANGO and cont:
        #: 컨테이너의 WORKDIR 은 `/app`(=호스트 `backend/`)이고 판정기는 `/repo/scripts`
        #: 에 붙는다. `cd /repo` 로 부르면 `config`·`tests` 를 못 찾는다(마운트가 셋이라
        #: `/repo/backend` 와 `/app` 이 같은 디렉터리인데 경로가 다르다).
        cmd = ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
               "-e", "PYTHONIOENCODING=utf-8"]
        for k in PASS_BY_NAME:
            cmd += ["-e", k]
        cmd += [cont, "python", "/repo/" + rel]
    else:
        cmd = [sys.executable, str(path)]
    try:
        done = subprocess.run(
            cmd, cwd=str(ROOT), env=env,
            capture_output=True, timeout=GATE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, "%d초 안에 안 끝났다" % GATE_TIMEOUT_S
    except OSError as exc:                                   # noqa: BLE001
        return None, "부르지 못했다: %s" % exc
    text = (done.stdout or b"").decode("utf-8", "replace").strip().splitlines()
    return done.returncode, (text[-1][:120] if text else "")


def collect_gates(areas: list[dict]) -> list[tuple[str, str, str]]:
    """(절 id, 상태, 게이트 경로) — `gate:` 를 적은 절만."""
    out = []
    for area in areas:
        for clause in (area.get("clauses") or []):
            gate = (clause.get("gate") or "").strip()
            if gate:
                out.append(((clause.get("id") or "?").strip(),
                            (clause.get("status") or "").strip(), gate))
    return out


#: ★ [실측 2026-09-07 · 턴 I · `verify_measure_repro` 가 잡음] **로그인하는 게이트를
#:   나란히 부르면 색이 흔들린다.** 이 저장소는 **동시 접속 1개**다(UX-24 · §0.4).
#:   16벌을 한꺼번에 부르면 뒤에 로그인한 쪽이 앞선 쪽의 세션을 빼앗고, 빼앗긴 쪽은
#:   「로그인으로 못 쟀다」를 낸다 — **같은 나무를 두 번 재면 다른 수가 나온다.**
#:   두 벌을 견주자 「색이 같다 21」과 「색이 같다 20」이 나왔고, 갈린 것은 제품이 아니라
#:   **누가 먼저 세션을 잡았는가**였다. 재현되지 않는 측정은 측정이 아니다(D-344).
#:   그래서 **로그인하는 판정기만 줄 세운다.** 나머지는 그대로 나란히 부른다 —
#:   전부 직렬로 돌리면 이 검사가 몇 분씩 걸리고, 느린 검사는 결국 꺼진다(D-353).
SERIAL_GATES = (
    "verify_sidebar.py", "verify_route_alive.py", "verify_contract_route_reach.py",
    "verify_screens.py", "verify_write_auth.py", "verify_seed_roles.py",
)


def measure_gates(pairs: list[tuple[str, str, str]]) -> dict[str, tuple]:
    """게이트를 **한 벌씩만** 부른다 (한 게이트를 여러 절이 가리킬 수 있다)."""
    names = sorted({g for _cid, _st, g in pairs if g != GATE_SELF})
    if not names:
        return {}
    serial = [n for n in names if n.rsplit("/", 1)[-1] in SERIAL_GATES]
    parallel = [n for n in names if n not in serial]
    out: dict[str, tuple] = {}
    if parallel:
        with ThreadPoolExecutor(max_workers=16) as pool:
            out.update(zip(parallel, pool.map(run_gate, parallel)))
    for n in serial:                      # 세션을 쥐는 것들 — 한 번에 하나씩
        out[n] = run_gate(n)
    return out


def score(areas: list[dict], counts: dict[str, dict[str, int]]) -> tuple[float, list[tuple]]:
    """가중 합계. 영역 점수 = 구현 절 / 전체 절."""
    rows = []
    total = 0.0
    for area in areas:
        c = counts[area["id"]]
        n = sum(c.values())
        ratio = (c.get(DONE, 0) / n) if n else 0.0
        weighted = area["weight"] * ratio
        total += weighted
        rows.append((area["id"], area["name"], area["weight"], c.get(DONE, 0), n,
                     ratio, weighted))
    return total, rows


# ═══════════════════════════════════════════════════════════════════════════
# 읽기
# ═══════════════════════════════════════════════════════════════════════════

def contract_clause_counts() -> dict[str, int]:
    """영역 ①은 계약 절 대장에서 **파생한다** — 절 상태를 두 곳에 적지 않는다.

    두 곳에 적으면 반드시 갈리고, 갈리는 순간 하나는 거짓말이다(D-227 이 만든 상태).
    """
    text = CONTRACT.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    # 계약 절 대장은 칸 이름이 `state` 다 (`status` 가 아니다) —
    # 두 대장이 같은 낱말을 안 쓰는 것도 「같은 이름, 다른 것」의 이웃이다(D-337).
    for m in re.finditer(r"^\s*(?:-\s*)?state:\s*(\S+)", text, re.MULTILINE):
        value = m.group(1).strip().strip('"').strip("'")
        if value in STATUSES:
            counts[value] = counts.get(value, 0) + 1
    return counts


#: 계약 절 대장의 잠금 id → hand. 계약 절은 상태를 두 곳에 적지 않으므로(위 함수)
#: 분류도 **거기 있는 값**에서 파생한다.
CONTRACT_HAND = {
    #: 계약 11조 — 구간 추출은 **하지 않기로 한 것**이다. 기능이 아니라 규칙이므로
    #: 100%의 분모에서 뺀다. 「못 했다」로 세면 영원히 안 채워지는 칸이 생긴다.
    "CLIP_EXTRACTION": "design",
    #: 상대방(SDN) 명세가 오면 열린다 — 조건부다.
    "SDN_API_SPEC": "out",
}


def contract_clause_hands() -> dict[str, int]:
    """계약 절 중 잠김을 hand 별로 센다. 술어는 `unlock_id` 다."""
    text = CONTRACT.read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for m in re.finditer(r"^\s*unlock_id:\s*(\S+)", text, re.MULTILINE):
        hand = CONTRACT_HAND.get(m.group(1).strip())
        if hand:
            out[hand] = out.get(hand, 0) + 1
    return out


def blocker_ids() -> set[str]:
    if not BLOCKERS.exists():
        return set()
    return set(re.findall(r"^\s*-\s*id:\s*(\S+)", BLOCKERS.read_text(encoding="utf-8"),
                          re.MULTILINE))


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    ok_exists = {"backend/tests/x.py"}.__contains__
    ids = {"MIGRATE_ONE_LINER"}
    checks: list[tuple[str, bool]] = []

    def problems(clause):
        return judge_clause(clause, exists=ok_exists, blocker_ids=ids)

    checks.append((
        "★ 출생표본 — 증명 없는 '구현' 을 잡는다 (D-346)",
        any("'미측정'이다" in p for p in problems({"id": "X", "status": "구현"}))))
    checks.append((
        "★ 출생표본 — 없는 파일을 가리킨 증명을 잡는다",
        any("없는 증명은 문서다" in p
            for p in problems({"id": "X", "status": "구현", "proof": "backend/없다.py"}))))
    checks.append((
        "★ 「부분」은 상태가 아니다 (D-314)",
        any("절로 쪼개라" in p for p in problems({"id": "X", "status": "부분"}))))
    checks.append((
        "증명이 실재하는 '구현' 은 통과한다",
        not problems({"id": "X", "status": "구현", "proof": "backend/tests/x.py"})))
    checks.append((
        "'잠김' 인데 blocker 가 없으면 잡는다",
        any("무엇이 막는지" in p for p in problems({"id": "X", "status": "잠김"}))))
    checks.append((
        "잠금 대장에 없는 blocker 를 잡는다",
        any("잠금 대장에 없다" in p
            for p in problems({"id": "X", "status": "잠김", "blocker": "없는것"}))))
    checks.append((
        "대장에 있는 blocker 는 통과한다",
        not problems({"id": "X", "status": "잠김", "blocker": "MIGRATE_ONE_LINER",
                      "hand": "in", "hand_why": "우회 경로를 우리 층에 둔다"})))
    #: ★ 2026-09-21 — **분류하지 않은 것은 분모에서 뺄 수 없다** (세종 §3).
    checks.append((
        "'잠김' 인데 hand 가 없으면 잡는다",
        any("분모에서 뺄 수 없다" in p
            for p in problems({"id": "X", "status": "잠김",
                               "blocker": "MIGRATE_ONE_LINER"}))))
    checks.append((
        "hand 는 있는데 사유가 없으면 잡는다 — 「손 밖」은 선언이지 면제가 아니다",
        any("선언이지 면제가" in p
            for p in problems({"id": "X", "status": "미측정", "why": "재는 중",
                               "hand": "out"}))))
    checks.append((
        "사유 없는 '미착수' 를 잡는다",
        any("사유가 없다" in p for p in problems({"id": "X", "status": "미착수"}))))
    checks.append((
        "넷 밖의 상태를 잡는다",
        any("넷 밖이다" in p for p in problems({"id": "X", "status": "검토중"}))))

    # ── ⑧ 대장 ↔ 게이트 불일치 (P-85) ────────────────────────────────────
    #: ★★ **출생 표본** — 2026-09-06. `verify_prod_settings.py` 가 5/5 초록인데
    #:   대장의 SEC-18 은 '미착수' 였고, **아무 색도 안 났다.**
    checks.append((
        "★★ 출생표본 — 게이트 초록 · 대장 '미착수' 를 잡는다 (P-85)",
        judge_gate_alignment("SEC-18", "미착수", GATE_GREEN, "g.py") is not None))
    checks.append((
        "★★ 반대 방향 — 대장 '구현' · 게이트 빨강을 잡는다 (이쪽이 더 나쁘다)",
        judge_gate_alignment("X", DONE, GATE_RED, "g.py") is not None))
    checks.append((
        "게이트 초록 · 대장 '구현' 은 통과 (음성 대조)",
        judge_gate_alignment("X", DONE, GATE_GREEN, "g.py") is None))
    checks.append((
        "게이트 빨강 · 대장 '미착수' 는 통과 — 색이 같다 (음성 대조)",
        judge_gate_alignment("X", "미착수", GATE_RED, "g.py") is None))
    checks.append((
        "★ 게이트 초록 · 대장 '잠김' 도 잡는다 (미측정·잠김 전부)",
        judge_gate_alignment("X", "잠김", GATE_GREEN, "g.py") is not None))
    checks.append((
        "★ 회색(exit 2)은 갈림이 아니다 — 못 잰 것을 빨강으로 세지 않는다 (D-301)",
        judge_gate_alignment("X", DONE, GATE_GREY, "g.py") is None))
    checks.append((
        "★ 부르지 못한 게이트(None)도 갈림이 아니다 — 따로 센다",
        judge_gate_alignment("X", DONE, None, "g.py") is None))
    checks.append((
        "★ gate 가 없는 파일을 가리키면 잡는다",
        any("아무것도 안 지킨다" in p for p in problems(
            {"id": "X", "status": "구현", "proof": "backend/tests/x.py",
             "gate": "scripts/없다.py"}))))
    checks.append((
        "실재하는 gate 는 통과한다 (음성 대조)",
        not problems({"id": "X", "status": "구현", "proof": "backend/tests/x.py",
                      "gate": "backend/tests/x.py"})))
    checks.append((
        "★ 한 게이트를 여러 절이 가리켜도 **한 번만** 부른다",
        len({g for _c, _s, g in [("A", "구현", "x.py"), ("B", "구현", "x.py")]}) == 1))

    # 가중 합계 계산 — 손으로 검산할 수 있는 표본
    total, _ = score(
        [{"id": "a", "name": "A", "weight": 20}, {"id": "b", "name": "B", "weight": 80}],
        {"a": {DONE: 1, "미착수": 1}, "b": {DONE: 0, "미착수": 4}})
    checks.append(("가중 합계가 절 비율로 계산된다 (20×½ + 80×0 = 10)", abs(total - 10.0) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {DONE: 3}})
    checks.append(("전부 구현이면 100 이다", abs(total - 100.0) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {}})
    checks.append(("절이 0개인 영역은 0 이다 (1 이 아니다)", abs(total) < 1e-9))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[GA] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


# ═══════════════════════════════════════════════════════════════════════════

def load() -> tuple[list[dict], dict[str, dict[str, int]], list[str], dict[str, int],
                    dict[str, int], dict[str, int]]:
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    areas = data["areas"]
    ids = blocker_ids()
    counts: dict[str, dict[str, int]] = {}
    hands: dict[str, int] = dict(contract_clause_hands())   # 계약 절 몫을 먼저 담는다
    #: ★ 2026-09-24 (P-26) — hand 는 이제 '미착수' 에도 붙는다(PRD v2.5 15절이 전부 `hand: in`).
    #:   그래서 「잠김·미측정 중 손 안」을 따로 센다 — 안 가르면 아래 한 줄이
    #:   34 + 22 = 56 처럼 읽혀 **남은 40절과 어긋난다.** 분모는 그대로다(design·out 만 뺀다).
    hands_lock: dict[str, int] = dict(contract_clause_hands())
    #: ★ [2026-09-26] **'미착수' 도 손 밖일 수 있다** — P-30 이 OPS-12 를 쪼개며
    #:   「다른 호스트」 갈래를 미착수·손 밖으로 냈다. 계약 절(영역 ①)의 몫은 여기
    #:   담지 않는다: 그쪽 미착수는 잠금 대장이 아니라 계약 대장이 세고, 그 수는
    #:   `contract_clause_hands()` 가 이미 hands 에 넣었다.
    hands_todo: dict[str, int] = {}
    problems: list[str] = []

    for area in areas:
        c: dict[str, int] = {}
        if area.get("derived_from"):
            derived = contract_clause_counts()
            if not derived:
                problems.append("영역 %s: %s 에서 절을 읽지 못했다 — 판정이 아니라 열거기 고장이다"
                                % (area["id"], area["derived_from"]))
            c = derived
        else:
            clauses = area.get("clauses") or []
            if not clauses:
                problems.append("영역 %s(%s): 절이 0개다 — 쪼개지 않은 영역은 잴 수 없다"
                                % (area["id"], area["name"]))
            for clause in clauses:
                problems += ["영역 %s · %s" % (area["id"], p) for p in judge_clause(
                    clause, exists=lambda rel: (ROOT / rel).exists(), blocker_ids=ids)]
                status = (clause.get("status") or "").strip()
                c[status] = c.get(status, 0) + 1
                hand = (clause.get("hand") or "").strip()
                if hand in HANDS:
                    hands[hand] = hands.get(hand, 0) + 1
                    if status in ("잠김", "미측정"):
                        hands_lock[hand] = hands_lock.get(hand, 0) + 1
                    elif status == "미착수":
                        hands_todo[hand] = hands_todo.get(hand, 0) + 1
                elif status == "미착수":
                    #: hand 칸이 없는 미착수. **손 밖이라 적힌 적이 없으므로 손 안이다** —
                    #: 다만 「손 안이라고 적은 것」과 구별해 센다. 둘을 뭉치면
                    #: 분류를 잊은 절과 분류한 절이 같은 칸에 선다(D-301).
                    hands_todo["none"] = hands_todo.get("none", 0) + 1
        counts[area["id"]] = c

    # ── P-81 · 대장 id 는 **유일하다** (2026-09-06 · 턴 H) ──────────────────
    #   ★ **출생 표본**: 턴 G 에 새 절을 `SEC-14` 로 등재했는데 그 id 는 이미
    #     「익명 반출 0건」이 쓰고 있었다. YAML 은 같은 id 를 **두 항목으로 그냥 싣고**,
    #     이 판정기는 절을 세기만 했으므로 **아무 색도 안 났다** — 대장이 조용히 겹쳤다.
    #     세종·영실 둘 다 못 봤다. 사람이 두 번 놓친 자리는 사람을 한 번 더 세우는 것이
    #     아니라 **게이트를 세우는 자리**다(D-286).
    #   ⚠ 겹친 id 는 「어느 쪽이 진짜인가」를 아무도 못 답하게 만든다. 증명·상태·손이
    #     둘로 갈리고, 절 수는 그대로라 **수가 안 움직인다**. 조용한 것이 가장 나쁘다.
    seen: dict[str, str] = {}
    for area in areas:
        for clause in (area.get("clauses") or []):
            cid = (clause.get("id") or "").strip()
            if not cid:
                continue
            if cid in seen:
                problems.append(
                    "대장 id 가 겹친다: %s — 영역 %s 와 영역 %s 에 둘 다 있다. "
                    "겹친 id 는 「어느 쪽이 진짜인가」를 아무도 못 답하게 만든다"
                    % (cid, seen[cid], area["id"]))
            else:
                seen[cid] = area["id"]

    weights = sum(a["weight"] for a in areas)
    if weights != 100:
        problems.insert(0, "가중치 합이 %d 다 — 100 이 아니면 아래 수는 전부 무의미하다" % weights)
    return areas, counts, problems, hands, hands_lock, hands_todo


def main() -> int:
    _load_local_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-gates", action="store_true",
                    help="대장↔게이트 불일치 검사를 건너뛴다 (P-85 · 건너뛰면 그렇게 적는다)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not LEDGER.exists():
        print("[GA] 대장이 없다: %s" % LEDGER)
        return 1

    areas, counts, problems, hands, hands_lock, hands_todo = load()
    total, rows = score(areas, counts)
    all_clauses = sum(sum(c.values()) for c in counts.values())
    done = sum(c.get(DONE, 0) for c in counts.values())

    print("[GA] [입력] 영역 %d · 절 %d개 (구현 %d · 미착수 %d · 잠김 %d · 미측정 %d)"
          % (len(areas), all_clauses, done,
             sum(c.get("미착수", 0) for c in counts.values()),
             sum(c.get("잠김", 0) for c in counts.values()),
             sum(c.get("미측정", 0) for c in counts.values())))

    for aid, name, weight, d, n, ratio, weighted in rows:
        print("  %-2s %-22s 가중 %2d%%  절 %2d/%-2d = %3.0f%%  →  %5.2f"
              % (aid, name, weight, d, n, ratio * 100, weighted))
    print("[GA] ★ 상용 오픈 가중 합계 **%.1f%%** [실측]" % total)
    print("[GA] (계약 축과 합치지 않는다 — D-345. 계약 절은 영역 ①이 그대로 인용한다)")

    # ── 손 안 도달율 (2026-09-21 · 세종 §3) ────────────────────────────────
    # **우리가 닫을 수 있는 100%** 를 따로 낸다. 두 수를 함께 적는 이유:
    #   가중 합계만 적으면 「상대방이 안 주는 것」과 「우리가 안 한 것」이 같은 칸에서
    #   같은 무게로 눌러 앉는다. 그러면 아무리 일해도 수가 안 오르는 것처럼 보이고,
    #   반대로 손 안에 남은 것이 몇인지도 안 보인다.
    design, out_of_hand, in_hand = (hands.get(k, 0) for k in HANDS)
    denom = all_clauses - design - out_of_hand
    print("[GA] [입력] 분류 %d건 — 설계 잠금 %d(분모에서 뺀다) · 손 밖 %d · 손 안 %d"
          % (design + out_of_hand + in_hand, design, out_of_hand, in_hand))
    if denom > 0:
        print("[GA] ★ **손 안 도달율 %.1f%%** = 구현 %d / (%d − 설계 잠금 %d − 손 밖 %d = %d)"
              % (done / denom * 100, done, all_clauses, design, out_of_hand, denom))
        #: 미착수도 **손 안 것만** 센다 — 손 밖 미착수를 우리 잔여에 넣으면
        #: 갚을 수 없는 절이 진척률을 눌러 앉는다(D-311 이 잠자는 빚에서 한 것과 같다).
        #: 계약 절(영역 ①)의 미착수는 hand 칸이 없으므로 아래 「그 밖」이 받는다.
        marked = hands_todo.get("in", 0)
        unmarked = hands_todo.get("none", 0)
        in_lock = hands_lock.get("in", 0)
        contract_rest = (denom - done) - marked - unmarked - in_lock
        print("[GA]   손 안에 남은 %d절 = 미착수 %d(손 안이라 적힘) + 미착수 %d(hand 미기재) "
              "+ 잠김·미측정 중 손 안 %d + 계약 절 %d — "
              "이 %d절이 **우리가 닫을 수 있는 100%%** 까지의 거리다"
              % (denom - done, marked, unmarked, in_lock, contract_rest, denom - done))
        not_started = marked + unmarked + contract_rest
        if not_started + in_lock != denom - done:
            print("[GA]   ⚠ 두 몫의 합 %d 이 남은 %d 과 다르다 — 분류가 어긋났다"
                  % (not_started + in_lock, denom - done))
    else:
        print("[GA] 손 안 도달율 **판정 불가** — 분모가 0 이하다 (분류가 어긋났다)")

    # ── ⑧ 대장 ↔ 게이트 불일치 (P-85) ──────────────────────────────────────
    pairs = collect_gates(areas)
    #: ★ 규칙 ① — **못 잰 것은 초록이 아니다.** 부르지 못한 게이트가 하나라도 있으면
    #:   빨강이 없어도 이 실행은 **회색(exit 2)** 이다. `--no-gates` 로 초록을 살 수 없다.
    unmeasured = 0
    if args.no_gates:
        unmeasured = len(pairs)
        print("[GA] [입력] 대장↔게이트 불일치 검사 **건너뜀**(--no-gates) — 절 %d개가 "
              "게이트를 가리키고 있는데 부르지 않았다. 이 실행은 그 자리를 **못 잰 것**이다"
              % len(pairs))
    elif not pairs:
        print("[GA] ⚠ `gate:` 를 적은 절이 **0개**다 — 불일치 검사가 아무것도 안 본다 (D-301)")
    else:
        results = measure_gates(pairs)
        grey, aligned = [], 0
        for cid, status, gate in pairs:
            if gate == GATE_SELF:
                continue
            rc, tail = results.get(gate, (None, "부르지 못했다"))
            bad = judge_gate_alignment(cid, status, rc, gate)
            if bad:
                problems.append(bad + "  ← 게이트 마지막 줄: %s" % tail)
            elif rc is None or rc == GATE_GREY:
                grey.append("%s ← %s (%s)" % (cid, gate, tail or "exit 2"))
            else:
                aligned += 1
        unmeasured = len(grey)
        print("[GA] [입력] 대장↔게이트 %d절 · 게이트 %d벌 — 색이 같다 %d · **못 쟀다 %d**"
              % (len(pairs), len(results), aligned, len(grey)))
        for g in grey:
            print("[GA]   ? 못 쟀다: %s" % g)

    if args.list or args.table:
        _print_table(areas, counts, rows, total, markdown=args.table)

    if problems:
        for p in problems:
            print("[GA] FAIL %s" % p)
        #: 실패가 있으면 회색이 함께 있어도 **1** 이다 — 실패가 「모른다」 뒤에 숨으면 안 된다.
        return 1
    if unmeasured:
        print("[GA] **회색(exit 2)** — 절마다 상태·증명·사유는 실재한다. 그러나 게이트 색을 "
              "%d절에서 **못 쟀다.** 못 잰 것은 초록이 아니다 (D-301 · 규칙 ①)" % unmeasured)
        return 2
    print("[GA] 통과 — 절마다 상태·증명·사유가 실재하고, 대장 상태와 게이트 색이 같다 (P-85)")
    return 0


def _print_table(areas, counts, rows, total, *, markdown: bool) -> None:
    if markdown:
        print()
        print("| 영역 | 가중 | 절 구현/전체 | 영역 달성 | 가중 기여 |")
        print("|---|---:|---:|---:|---:|")
        for aid, name, weight, d, n, ratio, weighted in rows:
            print("| %s %s | %d%% | %d/%d | %.0f%% | %.2f |"
                  % (aid, name, weight, d, n, ratio * 100, weighted))
        print("| **합계** | **100%%** | | | **%.1f%%** |" % total)
        print()
    for area in areas:
        if area.get("derived_from"):
            print("\n[%s] %s — %s 에서 파생: %s"
                  % (area["id"], area["name"], area["derived_from"],
                     " · ".join("%s %d" % kv for kv in sorted(counts[area["id"]].items()))))
            continue
        print("\n[%s] %s" % (area["id"], area["name"]))
        for clause in area.get("clauses") or []:
            mark = clause.get("proof") or clause.get("blocker") or ""
            print("   %-8s %-8s %-58s %s"
                  % (clause.get("id", "?"), clause.get("status", "?"),
                     clause.get("title", "")[:58], mark))


if __name__ == "__main__":
    raise SystemExit(main())
