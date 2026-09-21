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

★★★ P-216 [세종 판정 2026-09-21 · 턴 AA] — **점수를 `kind` 로 센다**
--------------------------------------------------------------------
턴 Z 까지 영역 점수는 `구현 절 / 전체 절` 이었다. 그 식은 P-211 의 다섯 부류를
**전부 1점**으로 세었다 — 그래서 세 턴 동안 「67.x」라 부르던 수가 실은
**닫힌 절 80/154** 였고, 그 둘의 거리를 아무도 못 봤다.

    closed 1.0 · ratchet 1.0(늘지 않음이 조건) · rule_only 0.5 · gate_only 0.5
    unmeasurable 0.0 · **잠김은 분모에서 빼지 않는다**

같은 턴에 P-215 가 「`closed` 이려면 **무엇을 분모 몇으로 쟀는가**가 대장에 있어야 한다.
없으면 닫힌 것이 아니다」를 세웠다. 두 판정이 함께 수를 내린다. **내려간 수가 정본이다.**

⚠ **출력 줄의 계약** — 영역 줄 앞 조각(`절 d/n = p%`)은 `verify_readiness_scores.py`
  (차선 Q)가 읽는다. 그 조각의 뜻은 **상태로 센 수** 그대로 두고, 점수를 만드는 수는
  뒤에 `kind pts/n = p%` 로 **덧붙였다.** 모양을 바꾸려면 **같은 커밋에서** 저쪽도 고친다.

    python scripts/verify_ga_readiness.py            # 판정 + 가중 합계
    python scripts/verify_ga_readiness.py --list     # 영역별 절 표
    python scripts/verify_ga_readiness.py --table    # 대표 보고용 표 (마크다운)
    python scripts/verify_ga_readiness.py --self-test

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs" / "agent" / "evidence" / "D-346" / "ga_readiness.yaml"
#: P-170 ① — V 단독 잠금. 게이트 종료코드 2 = 회색(못 쟀다) 의 규약 그대로.
EXIT_UNDECIDABLE_GATE = 2
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from v_lock import is_locked as _v_locked, GRAY_NOTE as _V_GRAY_NOTE  # noqa: E402
except ImportError:                                                     # pragma: no cover
    _v_locked, _V_GRAY_NOTE = (lambda: False), "V 단독 중"
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

#: ★★★ [P-211 · 2026-09-21 · 턴 Z · 차선 N] **「초록」은 다섯 부류다.**
#:
#:   턴 Y 에 후보 23 을 돌고 드러난 것: 한 글자 「초록」이 **다섯 가지 다른 뜻**을
#:   삼키고 있었고, 그 다섯 중 **하나만** 닫힘이다. 영역 요약이 `16/20` 한 줄만 내면
#:   읽는 사람은 그 16 을 전부 「닫혔다」로 읽는다 — 그것이 이 표의 가장 조용한 거짓말이다.
#:
#:     closed        누른 뒤를 봤다. 분모가 실재하고 면제가 없다
#:     ratchet       「**새로** 생긴 것 0건」 — 면제를 업고 있다
#:     rule_only     규칙은 섰는데 **현장이 비었다**(분모 0)
#:     unmeasurable  못 쟀다 — 회색이거나 잰 적이 없거나 상태가 구현이 아니다
#:     gate_only     게이트는 초록인데 **절은 안 닫혔다**(제목이 게이트보다 넓다)
#:
#:   ⚠ **이 칸은 점수를 안 만든다.** 수는 여전히 `구현 절 / 전체 절` 이다 —
#:     부류로 가중을 바꾸려면 결정이 먼저 있어야 한다(턴 Z 에는 안 바꾼다).
#:     이 칸이 하는 일은 **같은 수 옆에 그 수의 뜻을 세우는 것**이다.
KINDS = ("closed", "ratchet", "rule_only", "unmeasurable", "gate_only")
#: 영역 요약에서 **닫힘이 아닌** 셋(+하나)을 이름으로 부른다. 0 이어도 지우지 않는다 —
#: 「0건 검사」와 「검사 안 함」은 다르고, 지우면 둘이 같아 보인다(D-301).
KIND_LABEL = {"ratchet": "래칫", "rule_only": "규칙만",
              "unmeasurable": "못 잼", "gate_only": "게이트만"}

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

    #: ★ P-211 — **부류를 안 적은 절은 「초록」이 무슨 뜻인지 말하지 않는다.**
    #:   적지 않으면 읽는 사람이 전부 closed 로 읽는다 — 그 읽기가 공짜로 일어나는 것이
    #:   이 칸을 의무로 만든 이유다. 「몰라서 안 적었다」는 `unmeasurable` 로 적는다.
    kind = (clause.get("kind") or "").strip()
    if not kind:
        out.append("%s: `kind` 가 없다 — 「초록」이 다섯 뜻 중 무엇인지 말하지 않는 절이다 "
                   "(%s · P-211)" % (cid, " · ".join(KINDS)))
    elif kind not in KINDS:
        out.append("%s: kind «%s» 가 다섯 밖이다 (%s)" % (cid, kind, " · ".join(KINDS)))
    elif len((clause.get("kind_why") or "").strip()) < 10:
        out.append("%s: kind=%s 인데 사유가 없다 — 부류는 판정이고, 근거 없는 판정은 "
                   "옮겨 적은 것과 구별되지 않는다 (P-211)" % (cid, kind))

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


def _expand(value: str, seen: dict[str, str]) -> str:
    """`${NAME}` 을 셸과 같은 뜻으로 펼친다. 펼치는 눈은 `verify_route_alive` 한 벌이다."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from verify_route_alive import expand_env_refs  # noqa: PLC0415
    except Exception:                                    # noqa: BLE001
        return value
    return expand_env_refs(value, seen)


def _load_local_env() -> None:
    for name in _LOCAL_ENV_FILES:
        f = ROOT / name
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        #: ★★ [D-457 · 2026-09-11 턴 P] **이 로더가 세 벌째였고, 셋이 어긋났다.**
        #:   `.env.gates` 에는 `GX_ROUTE_PASSWORD=${GX_SEED_ROLE_PASSWORD}` 처럼
        #:   **다른 이름을 가리키는 줄**이 산다(사람이 셸로도 소싱하는 파일이라서).
        #:   안 펼치면 리터럴 `${GX_SEED_ROLE_PASSWORD}` 가 값이 되고, 이 자리는
        #:   **부모**라서 그 오염된 값이 자식 판정기에게 그대로 내려간다 —
        #:   자식은 「이미 환경에 있는 값은 덮지 않는다」를 지키느라 **제 파일을 안 읽는다.**
        #:   그래서 판정기를 손으로 부르면 초록, `verify_ga_readiness` 로 부르면 회색이었다
        #:   (P-70 이 적어 둔 「부르는 자리에 따라 색이 달랐다」와 **같은 모양 · 다른 뿌리**).
        #:   펼치는 눈은 한 벌이다 — `verify_route_alive.expand_env_refs` 를 부른다(D-369).
        seen: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            raw = _expand(v.strip().strip('"').strip("'"), seen)
            seen[k] = raw
            if k in _LOCAL_ENV_KEYS and not os.environ.get(k):
                os.environ[k] = raw
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
    #: ★ [P-170 ① · 2026-09-18 턴 U · D-487] **V 단독 중에는 로그인하는 게이트를 부르지 않는다.**
    #:   `evidence/V_LOCK` 이 있으면 직렬 묶음(로그인하는 판정기)은 돌리지 않고 회색으로 적는다 —
    #:   턴 T 에 이 판정기가 V 의 세션을 끊었다. 잠근 V 자신(`GX_V_SESSION_ID`)은 지나간다.
    if name in SERIAL_GATES and _v_locked():
        return EXIT_UNDECIDABLE_GATE, "회색 — " + _V_GRAY_NOTE
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
#: ★★ [D-459 · 2026-09-15 턴 P · `verify_measure_repro` 가 또 잡음] 목록이 **닫혀 있지 않았다.**
#:   커밋 훅에서 이 판정기를 두 번 돌리자 1회차 「못 쟀다 1」 · 2회차 「못 쟀다 2」 —
#:   2회차에만 SEC-04 가 「제품 로그인에서 토큰을 못 받았다」로 회색이었다. SEC-04 의 판정기
#:   `verify_authn_paths.py` 는 `verify_route_alive.login` 으로 **같은 계정에 로그인**하는데
#:   이 목록에 없어서 병렬 묶음에서 돌았다. D-457 로 그 판정기가 비로소 로그인하게 되자
#:   턴 I 의 사고가 **같은 모양으로 다시** 났다 — 로그인하게 된 판정기는 줄에 서야 한다.
#:   `verify_feature_reach.py` 는 스스로는 로그인하지 않지만 F-05 절을 재려고
#:   `verify_contract_route_reach.py`(로그인)를 **안에서 부른다** — 그래서 같이 줄 세운다.
SERIAL_GATES = (
    "verify_sidebar.py", "verify_route_alive.py", "verify_contract_route_reach.py",
    "verify_screens.py", "verify_write_auth.py", "verify_seed_roles.py",
    "verify_authn_paths.py",
    "verify_feature_reach.py",
)


#: ★★ [가설 하나 · 2026-09-21 턴 AA · 차선 N — **A/B 로 기각했다. 적어 둔다**]
#:   조율자 판정으로 `ops_log_collectors.py` 를 OPS-07 의 `gate:` 에 처음 달자
#:   같은 실행에서 **못 쟀다 6 → 13** 이 됐다(일곱이 「120초 안에 안 끝났다」).
#:   가설: 「그 판정기가 `docker exec` 를 46번 불러 병렬 묶음의 다른 Django 게이트와
#:   **같은 `gx-shell` 한 대의 문**을 다툰다 — 세션이 아니라 컨테이너의 문을 다투는
#:   D-459 의 이웃이다.」 그래서 **줄 세워 보았다(A/B).**
#:     A 병렬  09:13–09:17  못 쟀다 13
#:     B 직렬  09:17–09:23  못 쟀다 13   ← **안 달라졌다**
#:   그리고 09:23 에 **`docker ps` 자체가 500** 을 냈다
#:   (`...dockerDesktopLinuxEngine/v1.54/containers/json`). ⇒ **가설 기각.**
#:   범인은 이 판정기가 아니라 **도커 데몬이 아픈 것**이었고, 그 위에서 잰 회색 13은
#:   제품의 색이 아니다. **그래서 줄 세우지 않는다** — 안 밝혀진 가설로 공유 게이트의
#:   거동을 바꾸면, 다음 사람은 「왜 느린가」를 제 손으로 다시 물어야 한다.


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


#: ★★★ [P-216 · 2026-09-21 · 턴 AA · 세종 판정] **점수를 `kind` 로 센다.**
#:
#:   턴 Z 까지 영역 점수는 `구현 절 / 전체 절` 이었다. 그 식은 다섯 부류를 **전부 1점**으로
#:   세었다 — `rule_only`(현장이 비었다)도 `gate_only`(제목이 게이트보다 넓다)도
#:   `closed` 와 같은 무게였다. 그래서 세 턴 동안 「67.x」라 부르던 수가 실은
#:   **닫힌 절 80/154** 였고, 그 둘의 거리를 아무도 못 봤다.
#:
#:     closed        1.0   누른 뒤를 봤다
#:     ratchet       1.0   **늘지 않음이 조건**이다 — 면제를 업고 있어도 「새로 0」은 지켜진다
#:     rule_only     0.5   규칙은 섰고 현장이 비었다 — 절반만 서 있다
#:     gate_only     0.5   게이트는 초록이고 절은 안 닫혔다 — 절반만 잰다
#:     unmeasurable  0.0   못 쟀다. **회색은 초록이 아니다**(D-301)
#:
#:   ⚠ **잠김은 분모에서 빼지 않는다.** 잠긴 절도 「아직 안 된 것」이고, 분모에서 빼면
#:     잠글수록 수가 오른다. (설계 잠금·손 밖은 아래 「손 안 도달율」이 따로 가른다)
KIND_POINTS = {"closed": 1.0, "ratchet": 1.0, "rule_only": 0.5,
               "gate_only": 0.5, "unmeasurable": 0.0}
#: ★ [N ↔ Q 쪽지 · 턴 AA] 차선 Q 의 `verify_readiness_scores.py` 가 **이 이름으로 import**
#:   한다(「두 벌을 두지 않는다」 · D-369). 눈금을 여기서 바꾸면 저쪽도 따라 바뀐다 —
#:   **베끼지 말고 가져다 쓰라**는 뜻이므로 이 별명을 지우지 말 것.
KIND_SCORE = KIND_POINTS


def kind_points(kinds: dict[str, int]) -> float:
    """부류 셈 → 점수(절 단위). **판정식은 여기 한 곳에만 둔다** (D-212)."""
    return sum(KIND_POINTS[k] * kinds.get(k, 0) for k in KINDS)


def score(areas: list[dict], counts: dict[str, dict[str, int]],
          kinds: dict[str, dict[str, int]] | None = None) -> tuple[float, list[tuple]]:
    """가중 합계. **영역 점수 = Σ(kind 가중) / 전체 절** (P-216).

    `구현 절 / 전체 절` 도 함께 돌려준다 — **없애지 않는다.** 두 수를 나란히 두어야
    「상태로 센 수」와 「부류로 센 수」의 거리가 보인다. 그 거리가 이 턴에 드러난 것이다.
    """
    rows = []
    total = 0.0
    for area in areas:
        c = counts[area["id"]]
        n = sum(c.values())
        ratio = (c.get(DONE, 0) / n) if n else 0.0          # 상태로 센 수 (참고)
        k = (kinds or {}).get(area["id"], {})
        pts = kind_points(k)
        kratio = (pts / n) if n else 0.0                    # ★ 점수를 만드는 수
        weighted = area["weight"] * kratio
        total += weighted
        rows.append((area["id"], area["name"], area["weight"], c.get(DONE, 0), n,
                     ratio, weighted, pts, kratio))
    return total, rows


# ═══════════════════════════════════════════════════════════════════════════
# 읽기
# ═══════════════════════════════════════════════════════════════════════════

#: 영역 게이트가 남긴 한 줄. 표 아래에 그대로 찍는다 — **왜 그 수가 나왔는지**가
#: 수와 같은 화면에 있어야 한다.
AREA_GATE_NOTE: dict[str, str] = {}
#: ★ 별표 ②(기능명세 id · P-234)를 `load()` 에서 `main()` 으로 나른다. 8영역 밖이라
#:   `counts`·`kinds` 에 안 섞는다 — 섞으면 상용/100 이 다른 뜻이 된다.
ANNEX: dict[str, dict] = {"data": {}}


def reach_counts(gate_rel: str) -> tuple[dict[str, int], str, str]:
    """영역의 `gate:` 를 **부른다**(읽어서 답하지 않는다 · D-210).

    돌려주는 것: (상태 셈, 한 줄 설명, 못 부른 사유)

    ★ 왜 게이트가 세는가 (P-106 · 턴 M) — 절이 스스로 적은 `state` 를 세면 그 영역은
      **자기 신고**다. 턴 L 까지 영역 ①이 정확히 그랬고, 그 자기 신고가 가중 20%를
      들고 있었다. 이제 사슬(절↔화면↔라우트↔역할 계정의 200↔data_source)이 이어진
      절만 구현이다. **못 이은 절은 미측정**이고, 미측정은 분모에 남는다 —
      그래서 수가 내려간다. 내려간 수가 지금 아는 것의 전부다 (D-301).
    """
    path = ROOT / gate_rel
    if not path.is_file():
        return {}, "", "영역 게이트 «%s» 가 없다 — 못 잰 것이다" % gate_rel
    try:
        proc = subprocess.run([sys.executable or "python", str(path), "--json"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=1800, cwd=str(ROOT))
    except (OSError, subprocess.SubprocessError) as exc:
        return {}, "", "영역 게이트 «%s» 를 못 불렀다: %s" % (gate_rel, exc)
    text = proc.stdout.decode("utf-8", "replace")
    start = text.find("{")
    if start < 0:
        return {}, "", ("영역 게이트 «%s» 가 셈을 내지 않았다 (exit %d) — "
                        "판정이 아니라 도구 고장이다" % (gate_rel, proc.returncode))
    try:
        data = json.loads(text[start:])
    except ValueError as exc:
        return {}, "", "영역 게이트 «%s» 의 셈을 못 읽었다: %s" % (gate_rel, exc)

    green = int(data.get("구현", 0))
    grey = int(data.get("미측정", 0))
    locked = int(data.get("잠김", 0))
    red = int(data.get("빨강", 0))
    #: ★ 빨강은 **갈림**이다 — 대장이 「구현」이라 적은 자리에서 게이트가 무너졌다.
    #:   상태 네 낱말 안에서는 「미측정」에 담되(구현이 아니다), 갈림으로 **말한다**.
    counts = {DONE: green, "미측정": grey + red, "잠김": locked}
    note = ("게이트 «%s» 가 셌다 — 도달 %d · **못 이음(회색) %d** · 끊김(빨강) %d · 잠김 %d"
            % (gate_rel, green, grey, red, locked))
    why = ""
    if red:
        bad = [r.get("id") for r in (data.get("rows") or []) if r.get("color") == "빨강"]
        why = ("영역 게이트 «%s» 가 **빨강 %d절**을 냈다: %s — 대장이 「구현」이라 적어 둔 "
               "자리에서 사슬이 끊겼다 (P-85 갈림 ②)" % (gate_rel, red, bad[:8]))
    return counts, note, why


#: ★ [P-204 ③ · 2026-09-20 · 턴 Y · 차선 Q] **정적 갈래 — 로그인 0.**
#:   이 판정기는 안에서 게이트를 부르고, 그중 여섯이 **로그인한다.** 그래서
#:   커밋 훅에 걸면 2분이 걸리고 **계정을 다툰다**(동시 접속 1개 · UX-24 · §0.4).
#:   훅이 느리고 계정을 빼앗으면 사람은 훅을 끈다 — 꺼진 훅은 아무것도 안 지킨다(D-353).
#:   ⇒ **부르는 갈래와 안 부르는 갈래를 가른다.** 정적 갈래는 대장의 구조만 본다:
#:     증명 없는 '구현' · 사유 없는 '잠김' · 가리키는 게이트 파일의 실재.
#:     그 갈래는 게이트 색을 **못 잰 것**이므로 언제나 회색(2)이고, **1 일 때만 막는다.**
NO_LOGIN = False


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
        not problems({"id": "X", "status": "구현", "proof": "backend/tests/x.py",
                      "kind": "closed", "kind_why": "누른 뒤를 봤다 · 분모 실재"})))

    # ── ★ P-211 「초록」 다섯 부류 (2026-09-21 · 턴 Z) ─────────────────────
    #   ★★ **출생 표본**: 턴 Y 에 차선 N 이 후보 23 을 돌자 `exit 0` 스물이 나왔는데
    #     그중 **래칫 셋 · 규칙만 둘 · 게이트만 둘**이 섞여 있었다. 대장은 그 전부를
    #     한 글자 「구현」으로 적고 있었고, **아무 색도 안 났다** — 부류 칸이 없었으니까.
    _ok = {"id": "X", "status": "구현", "proof": "backend/tests/x.py"}
    checks.append((
        "★★ 출생표본 — `kind` 가 없는 절을 잡는다 (P-211)",
        any("다섯 뜻 중 무엇인지" in p for p in problems(dict(_ok)))))
    checks.append((
        "★ 다섯 밖의 kind 를 잡는다",
        any("다섯 밖이다" in p for p in problems(
            dict(_ok, kind="초록", kind_why="그냥 초록이다")))))
    checks.append((
        "★ kind 는 있는데 사유가 없으면 잡는다 — 부류는 판정이다",
        any("옮겨 적은 것과 구별되지" in p for p in problems(
            dict(_ok, kind="ratchet")))))
    checks.append((
        "★ `status: 구현` + `kind: rule_only` 는 **모순이 아니다**(가장 자주 나오는 거짓 초록)",
        not problems(dict(_ok, kind="rule_only",
                          kind_why="분모 0 — 활성 구역이 0개다"))))
    checks.append((
        "★ 영역 요약 꼬리가 넷을 **0 이어도** 부른다 (지우면 「0건」과 「안 셌다」가 같아진다)",
        kind_tail({"closed": 9}) == "(래칫 0 · 규칙만 0 · 못 잼 0 · 게이트만 0)"))
    checks.append((
        "★ 파생 영역(①)은 `kind_derived` 에서 센다 — 절이 그 파일에 없다",
        kind_counts_of({"id": "1", "derived_from": "x.yaml",
                        "kind_derived": {"closed": ["F-01-c2"],
                                         "unmeasurable": ["F-02-c1", "F-02-c2"]}})
        == {"closed": 1, "ratchet": 0, "rule_only": 0,
            "unmeasurable": 2, "gate_only": 0}))
    checks.append((
        "★ 절에 적은 kind 를 영역이 셈한다 (음성 대조)",
        kind_counts_of({"id": "9", "clauses": [{"kind": "closed"}, {"kind": "ratchet"},
                                               {"kind": "closed"}]})
        == {"closed": 2, "ratchet": 1, "rule_only": 0,
            "unmeasurable": 0, "gate_only": 0}))
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
                      "hand": "in", "hand_why": "우회 경로를 우리 층에 둔다",
                      "kind": "unmeasurable", "kind_why": "잠김이다 — 잰 초록이 없다"})))
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
                      "gate": "backend/tests/x.py",
                      "kind": "closed", "kind_why": "누른 뒤를 봤다 · 분모 실재"})))
    checks.append((
        "★ 한 게이트를 여러 절이 가리켜도 **한 번만** 부른다",
        len({g for _c, _s, g in [("A", "구현", "x.py"), ("B", "구현", "x.py")]}) == 1))

    # ── ★★★ P-216 — **점수를 `kind` 로 센다** (2026-09-21 · 턴 AA · 세종) ───────
    #   ★★ **출생 표본**: 세 턴 동안 「67.x」라 부르던 수가 실은 **닫힌 절 80/154** 였다.
    #     옛 식(`구현 절 / 전체 절`)이 다섯 부류를 **전부 1점**으로 세었기 때문이다.
    #     그래서 아래 다섯 갈래를 **각 kind 하나씩 표본 5**로 박는다 — 어느 한 칸의
    #     무게가 조용히 바뀌면 여기가 빨개진다.
    _S = [{"id": "a", "name": "A", "weight": 100}]
    _one = lambda k: score(_S, {"a": {DONE: 1}}, {"a": {k: 1}})[0]   # noqa: E731
    checks.append(("★ 표본① closed 는 **1.0** 이다 (누른 뒤를 봤다)",
                   abs(_one("closed") - 100.0) < 1e-9))
    checks.append(("★ 표본② ratchet 도 **1.0** 이다 — 「늘지 않음」이 조건인 절이다",
                   abs(_one("ratchet") - 100.0) < 1e-9))
    checks.append(("★ 표본③ rule_only 는 **0.5** 다 (규칙은 섰고 현장이 비었다)",
                   abs(_one("rule_only") - 50.0) < 1e-9))
    checks.append(("★ 표본④ gate_only 는 **0.5** 다 (게이트는 초록 · 절은 안 닫혔다)",
                   abs(_one("gate_only") - 50.0) < 1e-9))
    checks.append(("★★ 표본⑤ unmeasurable 은 **0.0** 이다 — 회색은 초록이 아니다 (D-301)",
                   abs(_one("unmeasurable")) < 1e-9))
    #: ★ **음성 대조 — 옛 식이면 다섯이 전부 100 이다.** 다섯 절 전부 `status: 구현` 이고
    #:   부류만 다른 영역을 세워, **새 식은 셋으로 갈리고**(1.0·0.5·0.0) 옛 식은
    #:   **하나로 뭉친다**(전부 구현이니 100)는 것을 같은 자리에서 본다.
    _five = {k: _one(k) for k in KINDS}
    checks.append((
        "★ 음성 대조 — 다섯을 **상태로** 세면 전부 100 으로 뭉친다 (옛 식이 삼키던 것)",
        all(abs(score(_S, {"a": {DONE: 1}}, {"a": {k: 1}})[1][0][5] * 100 - 100.0) < 1e-9
            for k in KINDS)))
    checks.append((
        "★ 그런데 **부류로 세면 셋으로 갈린다** — 1.0 · 0.5 · 0.0",
        sorted({round(v, 6) for v in _five.values()}) == [0.0, 50.0, 100.0]))
    #: ★ **잠김은 분모에서 빼지 않는다** — 빼면 잠글수록 수가 오른다.
    checks.append((
        "★ 잠김 절은 분모에 남는다 (closed 1 + 잠김 1 → 50%, 100% 가 아니다)",
        abs(score(_S, {"a": {DONE: 1, "잠김": 1}},
                  {"a": {"closed": 1, "unmeasurable": 1}})[0] - 50.0) < 1e-9))
    checks.append((
        "★ 섞인 영역을 손으로 검산한다 (closed 2 + ratchet 1 + rule_only 1 + gate_only 1 "
        "+ unmeasurable 1 = 4.0/6)",
        abs(kind_points({"closed": 2, "ratchet": 1, "rule_only": 1,
                         "gate_only": 1, "unmeasurable": 1}) - 4.0) < 1e-9))

    # 가중 합계 계산 — 손으로 검산할 수 있는 표본
    total, _ = score(
        [{"id": "a", "name": "A", "weight": 20}, {"id": "b", "name": "B", "weight": 80}],
        {"a": {DONE: 1, "미착수": 1}, "b": {DONE: 0, "미착수": 4}},
        {"a": {"closed": 1, "unmeasurable": 1}, "b": {"unmeasurable": 4}})
    checks.append(("가중 합계가 부류 비율로 계산된다 (20×½ + 80×0 = 10)", abs(total - 10.0) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {DONE: 3}},
                     {"a": {"closed": 3}})
    checks.append(("전부 closed 면 100 이다", abs(total - 100.0) < 1e-9))
    #: ★ **상태가 전부 '구현' 이어도 부류가 전부 `unmeasurable` 이면 0 이다** — P-216 의 본문.
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {DONE: 3}},
                     {"a": {"unmeasurable": 3}})
    checks.append(("★★ 상태가 전부 '구현' 이어도 부류가 못 잼이면 **0** 이다 (P-216)",
                   abs(total) < 1e-9))
    total, _ = score([{"id": "a", "name": "A", "weight": 100}], {"a": {}}, {"a": {}})
    checks.append(("절이 0개인 영역은 0 이다 (1 이 아니다)", abs(total) < 1e-9))

    # ── ★★ P-236 (턴 AB) — 「같은 칸이 둘」을 양성·음성으로 박는다 ─────────
    _dup = """
areas:
  - id: "4"
    clauses:
      - id: OPS-07
        status: 미착수
        why: |
          앞의 글 — 조율자 판정
        why: |
          뒤의 글 — 이것만 남는다
"""
    _dp = duplicate_key_problems(_dup)
    checks.append((
        "★★ 출생표본 — 한 절에 `why:` 가 둘이면 잡는다 (P-236)",
        any("칸 `why` 가 **둘**이다" in x for x in _dp)))
    checks.append((
        "★ 잡을 때 **절 이름**을 말한다 (사람이 찾아갈 수 있어야 한다)",
        any(x.startswith("OPS-07:") for x in _dp)))
    checks.append((
        "★ 잡을 때 **두 줄 번호**를 다 말한다 — 어느 글이 사라졌는지 봐야 한다",
        any("(7줄 · 9줄)" in x for x in _dp)))
    #: ★★ 음성 — **`safe_load` 로는 못 잡는다.** 이 줄이 이 검사가 있는 이유다:
    #:   파서가 먼저 삼키므로 결과만 보면 흠이 **없는 것처럼 보인다.**
    checks.append((
        "★★ 음성 — `safe_load` 결과만 보면 **흠이 안 보인다**(파서가 먼저 삼킨다)",
        yaml.safe_load(_dup)["areas"][0]["clauses"][0]["why"].strip() == "뒤의 글 — 이것만 남는다"))
    #: 같은 글인데 **둘째 칸 이름만 다른** 대장 — 이것이 흠을 고친 모양이다(삭제 0).
    _fixed = """
areas:
  - id: "4"
    clauses:
      - id: OPS-07
        status: 미착수
        why: |
          앞의 글 — 조율자 판정
        note_turn_ab: |
          뒤의 글 — 이제 둘 다 산다
"""
    checks.append((
        "★ 음성 — 칸 이름이 다르면 0건이다 (없는 빨강을 세우지 않는다)",
        duplicate_key_problems(_fixed) == []))
    #: 절 밖에서도 겹칠 수 있다 — 가중치가 둘이면 **합이 100 인지조차 거짓이 된다.**
    _dup_area = """
areas:
  - id: "4"
    weight: 15
    weight: 20
"""
    checks.append((
        "★ 절 밖(영역·meta)에서 겹쳐도 잡는다 — 나무 전체를 걷는다",
        any("칸 `weight` 가 **둘**이다" in x
            for x in duplicate_key_problems(_dup_area))))

    # ── ★★ 별표 ②(기능명세 id · P-234 · P-237) — 턴 AB ────────────────────
    _led = {"OPS-07", "OPS-07b", "SEC-14"}
    _good = {"id": "SPEC-DSM-0001", "status": "미착수", "kind": "unmeasurable"}
    checks.append((
        "★★ 별표 ② — **비어 있는 것은 흠이 아니다**(사유가 있으면 통과)",
        annex_problems({"registered": False, "why": "Q 의 목록이 안 왔다"}, _led) == []))
    checks.append((
        "★★ 별표 ② — 사유 없는 빈칸은 잡는다 (잊은 것과 구별되지 않는다)",
        any("사유 없는 빈칸" in p for p in annex_problems({"registered": False}, _led))))
    checks.append((
        "★ 별표 ② — `registered: true` 인데 0개면 잡는다 (분모 0 인 초록)",
        any("분모 0 인 초록" in p
            for p in annex_problems({"registered": True, "why": "x"}, _led))))
    checks.append((
        "★★ 별표 ② — 규칙 없는 목록은 **분모가 아니다**",
        any("규칙 없는 목록은 분모가 아니다" in p
            for p in annex_problems({"clauses": [dict(_good)]}, _led))))
    checks.append((
        "★ 별표 ② — 출처(기계 산출물) 없는 목록을 잡는다 (손으로 적은 분모)",
        any("손으로 적은 분모와 구별되지 않는다" in p
            for p in annex_problems({"rule": "표 데이터행", "clauses": [dict(_good)]}, _led))))
    #: ★★ **P-237 출생 표본** — 턴 AA 에 내가 `OPS-07-b` 를 쓸 뻔했고, 대장에는
    #:   `OPS-07b` 가 이미 살아 있었다. P-81 은 둘을 **다 통과시킨다.**
    _full = {"rule": "표 데이터행", "source": "scripts/verify_ga_readiness.py"}
    checks.append((
        "★★ 출생표본 — 대장 `OPS-07b` 와 별표 `OPS-07-b` 를 잡는다 (붙임표 하나 · P-237)",
        any("붙임표·밑줄·대소문자만 다르다" in p for p in annex_problems(
            dict(_full, clauses=[{"id": "OPS-07-b", "status": "미착수",
                                  "kind": "unmeasurable"}]), _led))))
    checks.append((
        "★ 음성 — P-81(똑같은 id)은 **따로** 잡는다 (두 검사는 다른 것을 본다)",
        any("어느 쪽이 진짜인가" in p for p in annex_problems(
            dict(_full, clauses=[{"id": "OPS-07b", "status": "미착수",
                                  "kind": "unmeasurable"}]), _led))))
    checks.append((
        "★ 별표 ② 안에서 붙임표만 다른 쌍도 잡는다",
        any("(P-237)" in p for p in annex_problems(
            dict(_full, clauses=[dict(_good), {"id": "SPEC_DSM_0001", "status": "미착수",
                                               "kind": "unmeasurable"}]), _led))))
    checks.append((
        "★★ 별표 ② — 기능명세가 `구현` 으로 태어나면 잡는다 (코드 0줄이다)",
        any("코드 0줄로 태어난다" in p for p in annex_problems(
            dict(_full, clauses=[dict(_good, status="구현")]), _led))))
    checks.append((
        "★★ 별표 ② — kind 가 못 잼이 아니면 잡는다 (못 잰 칸은 0 이 아니라 회색)",
        any("못 잰 칸은 0 이 아니라 회색이다" in p for p in annex_problems(
            dict(_full, clauses=[dict(_good, kind="closed")]), _led))))
    checks.append((
        "★ 음성 — 바르게 등재된 별표는 통과한다 (없는 빨강을 세우지 않는다)",
        annex_problems(dict(_full, registered=True, clauses=[dict(_good)]), _led) == []))
    checks.append((
        "★ 없는 `source` 를 가리키면 잡는다 (없는 산출물은 문서다)",
        any("없는 산출물은 문서다" in p for p in annex_problems(
            dict(_full, source="scripts/없다.py", clauses=[dict(_good)]), _led))))

    # ── ★★ P-231 증거 경로 (턴 AB) ────────────────────────────────────────
    _a1 = {"id": "1", "kind_derived": {"closed": ["F-12-c5"], "unmeasurable": ["F-12-c1"]},
           "kind_evidence": {"F-12-c5": {
               "json": "scripts/verify_ga_readiness.py",
               "capture": "scripts/verify_ga_readiness.py",
               "measured_at": "2026-09-21T12:19:30Z"}}}
    checks.append((
        "★ 음성 — 파일이 실재하는 증거 경로는 통과한다",
        evidence_problems(_a1) == []))
    checks.append((
        "★★ P-231 — **없는 파일을 가리킨 증거를 잡는다**(없는 증거는 주장이다)",
        any("없는 증거는 주장이다" in p for p in evidence_problems(
            {"id": "1", "kind_derived": _a1["kind_derived"],
             "kind_evidence": {"F-12-c5": dict(_a1["kind_evidence"]["F-12-c5"],
                                               json="docs/없다.json")}}))))
    checks.append((
        "★★ P-231 — `closed` 가 아닌 절에 붙은 경로를 잡는다 (올린 줄로 속인다)",
        any("올린 줄로 속인다" in p for p in evidence_problems(
            {"id": "1", "kind_derived": _a1["kind_derived"],
             "kind_evidence": {"F-12-c1": _a1["kind_evidence"]["F-12-c5"]}}))))
    checks.append((
        "★ P-231 — `measured_at` 없는 증거를 잡는다 (늙었는지 못 묻는다)",
        any("늙었는지" in p for p in evidence_problems(
            {"id": "1", "kind_derived": _a1["kind_derived"],
             "kind_evidence": {"F-12-c5": {"json": "scripts/verify_ga_readiness.py",
                                           "capture": "scripts/verify_ga_readiness.py"}}}))))
    checks.append((
        "★ 증거 칸이 아예 없는 영역은 통과한다 (옛 영역을 빨갛게 만들지 않는다)",
        evidence_problems({"id": "2", "clauses": []}) == []))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[GA] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


# ═══════════════════════════════════════════════════════════════════════════

def kind_counts_of(area: dict) -> dict[str, int]:
    """영역의 부류 셈. **파생 영역(①)은 절이 여기 없으므로 `kind_derived` 를 읽는다.**

    ⚠ 그 이름표는 계약 절 대장에 안 적는다 — 한 파일은 한 차선이고, 옮겨 적으면
    두 표가 갈린다(D-227). 여기 있는 것은 **이름표**이지 상태가 아니다.
    """
    out = {k: 0 for k in KINDS}
    derived = area.get("kind_derived")
    if derived:
        for k in KINDS:
            out[k] += len(derived.get(k) or [])
        return out
    for clause in (area.get("clauses") or []):
        k = (clause.get("kind") or "").strip()
        if k in out:
            out[k] += 1
    return out


def kind_tail(kinds: dict[str, int]) -> str:
    """영역 요약 뒤에 붙는 한 조각 — `(래칫 a · 규칙만 b · 못 잼 c · 게이트만 d)`.

    **0 이어도 지우지 않는다.** 지우면 「0건」과 「안 셌다」가 같아 보인다(D-301).
    """
    return "(" + " · ".join("%s %d" % (KIND_LABEL[k], kinds.get(k, 0))
                            for k in ("ratchet", "rule_only", "unmeasurable",
                                      "gate_only")) + ")"


# ── ★★ P-236 · 2026-09-21 · 턴 AB · 차선 N — **한 절에 같은 칸이 둘이면 앞엣것이 사라진다**
#   ★ **출생 표본**: 턴 AA 에 내가 `OPS-07` 에 조율자 판정 블록을 `why:` 로 써 넣었는데
#     그 절에는 이미 `why:` 가 **있었다.** YAML 은 같은 키를 겹쳐 실으면 **뒤엣것만 남기고
#     앞의 글 전부를 조용히 버린다** — 버려진 것은 하필 「왜 '미착수'인가 · `gate:` 를 왜
#     달았나 · `OPS-07b` 와 어떻게 다른가 · 감사 표가 연 9.3 GiB 로 자란다」였다.
#     같은 흠이 `OPS-19` 에도 있었다(`note_turn_i` 둘 — **새로 잰 턴 J 글이 옛 턴 I 글에 덮였다**).
#   ⚠ **아무 색도 안 났다.** P-81(id 겹침)은 절을 세니까 잡을 수 있었지만, 이것은
#     **판정기가 보기 전에 파서가 먼저 삼킨다** — 판정기는 사라진 글을 볼 방법이 없다.
#     절 수도 안 움직이고 점수도 안 움직인다. **조용한 것이 가장 나쁘다**(P-81 과 같은 말).
#   ⇒ 그래서 `safe_load` 의 **결과**가 아니라 **원문의 노드 나무**(`yaml.compose`)를 본다.
#     닫힌 사실 하나: 대장이 스스로 안 읽히는 자리는 `gate:` 없는 `closed` 의 **한 겹 아래**다.
#: ★ P-237 · 2026-09-21 · 턴 AB · 차선 N — **붙임표 하나 차이는 유일성이 아니다**
#:   `OPS-07-b` 와 `OPS-07b` 는 P-81 검사를 **둘 다 통과한다.** 아무 색도 안 나고
#:   읽는 사람만 헷갈린다(턴 AA 에 내가 실제로 밟을 뻔한 자리다). 새 id 를 **수백 개씩**
#:   들이는 별표 ② 가 그 함정이 가장 크게 벌어지는 자리라, **꼴을 같게 만들어** 대 본다.
def id_shape(cid: str) -> str:
    """id 를 **대조용 꼴**로 줄인다 — 붙임표·밑줄·공백을 걷고 소문자로."""
    return re.sub(r"[-_\s]", "", cid).lower()


def annex_problems(annex: dict, ledger_ids: set[str]) -> list[str]:
    """별표 ②(기능명세 id)를 판정한다. **비어 있는 것은 흠이 아니다 — 거짓이 흠이다.**

    비었으면 `why` 를 요구하고(사유 없는 빈칸은 잊은 것과 구별되지 않는다),
    찼으면 **규칙·출처·id 유일성·꼴 겹침**을 요구한다.
    """
    out: list[str] = []
    if not annex:
        return out
    clauses = annex.get("clauses") or []
    registered = bool(annex.get("registered"))
    rule = (annex.get("rule") or "").strip()
    source = (annex.get("source") or "").strip()

    if not clauses:
        if registered:
            out.append("별표 ②: `registered: true` 인데 id 가 **0개**다 — "
                       "**분모 0 인 초록은 초록이 아니다**")
        if not (annex.get("why") or "").strip():
            out.append("별표 ②: 등재가 0건인데 `why` 가 없다 — **사유 없는 빈칸은 잊은 "
                       "것과 구별되지 않는다**")
        return out

    #: 찼다 — 여기서부터는 **분모가 된다.** 분모에는 출처가 있어야 한다.
    if not rule:
        out.append("별표 ②: id 가 %d개인데 `rule`(세는 규칙)이 비었다 — "
                   "**규칙 없는 목록은 분모가 아니다**" % len(clauses))
    if not source:
        out.append("별표 ②: id 가 %d개인데 `source`(기계 산출물 경로)가 비었다 — "
                   "**손으로 적은 분모와 구별되지 않는다**" % len(clauses))
    elif not (ROOT / source).exists():
        out.append("별표 ②: `source` 가 가리키는 %s 가 **없다** — 없는 산출물은 문서다"
                   % source)

    seen: dict[str, str] = {}
    shapes: dict[str, str] = {}
    for c in clauses:
        cid = (c.get("id") or "").strip()
        if not cid:
            out.append("별표 ②: id 가 빈 항목이 있다")
            continue
        if cid in ledger_ids:
            out.append("별표 ② %s: **대장 8영역의 절 id 와 겹친다** — 겹친 id 는 "
                       "「어느 쪽이 진짜인가」를 아무도 못 답하게 만든다 (P-81)" % cid)
        if cid in seen:
            out.append("별표 ② %s: 별표 안에서 **두 번** 적혔다" % cid)
        else:
            seen[cid] = cid
        sh = id_shape(cid)
        if sh in shapes and shapes[sh] != cid:
            out.append("별표 ② %s 와 %s: **붙임표·밑줄·대소문자만 다르다.** P-81 유일성 "
                       "검사는 둘을 **다른 id 로 통과시킨다** — 아무 색도 안 나면서 읽는 "
                       "사람만 헷갈린다 (P-237)" % (shapes[sh], cid))
        else:
            shapes[sh] = cid
        #: ★ 별표는 **미착수·못 잼**으로 태어난다. 그렇지 않은 것이 있으면 말한다 —
        #:   기능명세는 이 턴에 **코드 0줄**이고, 0줄인 것이 닫혀 있으면 그것이 거짓이다.
        if (c.get("status") or "").strip() != "미착수":
            out.append("별표 ② %s: status 가 '미착수' 가 아니다(%r) — 기능명세는 "
                       "코드 0줄로 태어난다. 올리려면 **증거 경로**가 있어야 한다"
                       % (cid, c.get("status")))
        if (c.get("kind") or "").strip() != "unmeasurable":
            out.append("별표 ② %s: kind 가 'unmeasurable' 이 아니다(%r) — "
                       "**못 잰 칸은 0 이 아니라 회색이다**" % (cid, c.get("kind")))
    #: ★ 대장 절과 **꼴까지** 대 본다 — 별표 ↔ 8영역 사이의 붙임표 함정.
    led_shapes = {id_shape(i): i for i in ledger_ids}
    for cid in seen:
        sh = id_shape(cid)
        if sh in led_shapes and led_shapes[sh] != cid:
            out.append("별표 ② %s 와 대장 절 %s: **붙임표·밑줄·대소문자만 다르다** — "
                       "유일성 검사를 둘 다 통과한다 (P-237)" % (cid, led_shapes[sh]))
    return out


#: ★★ P-231 · 2026-09-21 · 턴 AB · 차선 N — **증거 경로가 있는 절만 `closed` 다**
#:   P-231 이 요구한 것은 「누른 뒤」 초록 **그리고 증거 파일 경로가 대장에 실릴 것**이다.
#:   ⚠ 경로는 **적어 두면 끝나는 것이 아니다** — 그 파일이 **사라져도 아무 색이 안 난다.**
#:     「없는 시험은 문서다」와 같은 자리이고, 여기서는 「**없는 증거는 주장이다**」다.
#:     그래서 매 실행 실재를 확인한다. 그리고 `closed` 가 아닌 절에 경로가 붙어 있으면
#:     그것도 말한다 — 안 올린 절의 경로는 **읽는 사람을 올린 줄로 속인다.**
def evidence_problems(area: dict) -> list[str]:
    """영역 ①의 `kind_evidence` 를 판정한다. 없는 파일을 가리킨 증거는 증거가 아니다."""
    ev = area.get("kind_evidence") or {}
    if not ev:
        return []
    out: list[str] = []
    derived = area.get("kind_derived") or {}
    closed = set(derived.get("closed") or [])
    other = {c for k in ("unmeasurable", "ratchet", "rule_only", "gate_only")
             for c in (derived.get(k) or [])}
    for cid, e in sorted(ev.items()):
        if cid not in closed:
            where = "다른 부류에 있다" if cid in other else "어느 부류에도 없다"
            out.append("영역 %s · %s: 증거 경로가 실려 있는데 `closed` 가 아니다(%s) — "
                       "**안 올린 절의 경로는 읽는 사람을 올린 줄로 속인다** (P-231)"
                       % (area["id"], cid, where))
        for key in ("json", "capture"):
            rel = (e.get(key) or "").strip()
            if not rel:
                out.append("영역 %s · %s: 증거 `%s` 칸이 비었다 — **경로 없는 승격은 "
                           "P-231 이 금한 것이다**" % (area["id"], cid, key))
            elif not (ROOT / rel).exists():
                out.append("영역 %s · %s: 증거 `%s` 가 가리키는 %s 가 **없다** — "
                           "**없는 증거는 주장이다** (P-231)" % (area["id"], cid, key, rel))
        if not (e.get("measured_at") or "").strip():
            out.append("영역 %s · %s: `measured_at` 이 없다 — **언제 잰 것인지 모르는 "
                       "초록은 「늙었는지」를 아무도 못 묻는다**" % (area["id"], cid))
    return out


def duplicate_key_problems(text: str) -> list[str]:
    """대장 원문에서 **같은 자리에 두 번 적힌 칸**을 전부 찾는다 (절·영역·meta 어디든).

    `yaml.safe_load` 는 이미 하나를 버린 뒤라 늦다. 노드 나무를 걸어 **줄 번호까지** 낸다.
    """
    try:
        root = yaml.compose(text)
    except yaml.YAMLError as exc:            # 원문이 아예 안 읽히면 그것부터 말한다
        return ["대장 YAML 을 구성하지 못했다: %s" % exc]
    out: list[str] = []
    stack: list[tuple] = [(root, "(뿌리)")]
    while stack:
        node, where = stack.pop()
        if isinstance(node, yaml.MappingNode):
            name = where
            for k, v in node.value:          # 이름을 먼저 찾아 사람이 읽게 한다
                if getattr(k, "value", None) == "id" and isinstance(v, yaml.ScalarNode):
                    name = v.value
            seen: dict[str, int] = {}
            for k, v in node.value:
                key = getattr(k, "value", None)
                if key is None:
                    continue
                line = k.start_mark.line + 1
                if key in seen:
                    out.append(
                        "%s: 칸 `%s` 가 **둘**이다 (%d줄 · %d줄) — YAML 은 뒤엣것만 남기고 "
                        "**앞의 글을 조용히 버린다.** 절 수도 점수도 안 움직이므로 "
                        "아무 색도 안 난다. 합치거나 다른 이름을 줘라 (P-236)"
                        % (name, key, seen[key], line))
                else:
                    seen[key] = line
                stack.append((v, name))
        elif isinstance(node, yaml.SequenceNode):
            for item in node.value:
                stack.append((item, where))
    return sorted(out)


def load() -> tuple[list[dict], dict[str, dict[str, int]], list[str], dict[str, int],
                    dict[str, int], dict[str, int], dict[str, dict[str, int]]]:
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    areas = data["areas"]
    ids = blocker_ids()
    counts: dict[str, dict[str, int]] = {}
    kinds: dict[str, dict[str, int]] = {a["id"]: kind_counts_of(a) for a in areas}
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
            #: ★★ [P-106 · 턴 M] 영역에 `gate:` 가 붙으면 **세는 쪽이 바뀐다.**
            #:   절이 스스로 적은 `state` 를 세는 것이 아니라, 게이트를 **불러**
            #:   도달한 절만 구현으로 센다. 이 한 자리가 가중 20%였다.
            if area.get("gate") and NO_LOGIN:
                #: 정적 갈래 — **부르지 않는다.** 분모는 그대로 두고 전부 미측정으로 센다.
                #: (지난 실행의 셈을 읽어 오지 않는다 — 사진을 실측으로 적지 않는다 · D-210)
                base = contract_clause_counts()
                c = {"미측정": sum(base.values())}
                AREA_GATE_NOTE[area["id"]] = (
                    "정적 갈래(--static) — 이 영역의 게이트 «%s» 를 **부르지 않았다**(로그인 0). "
                    "절 %d개를 전부 **못 쟀다**로 센다. 이 영역의 %% 는 점수가 아니다"
                    % (area["gate"], sum(base.values())))
            elif area.get("gate"):
                derived, note, why = reach_counts(area["gate"])
                if why:
                    problems.append("영역 %s: %s" % (area["id"], why))
                AREA_GATE_NOTE[area["id"]] = note
                c = derived
            else:
                derived = contract_clause_counts()
                if not derived:
                    problems.append("영역 %s: %s 에서 절을 읽지 못했다 — 판정이 아니라 "
                                    "열거기 고장이다" % (area["id"], area["derived_from"]))
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

    #: ★★ P-236 — **원문을 본다.** 위 `data` 는 이미 하나를 버린 뒤라 늦다.
    problems += duplicate_key_problems(LEDGER.read_text(encoding="utf-8"))

    #: ★ 별표 ②(기능명세 id · P-234). **8영역 밖이라 상용/100 을 안 건드린다** —
    #:   여기 수백 절을 끼우면 가중치 표가 무너지고 상용 점수가 다른 뜻이 된다.
    _led_ids = {(c.get("id") or "").strip()
                for a in areas for c in (a.get("clauses") or [])} - {""}
    ANNEX["data"] = data.get("annex_2_spec") or {}
    problems += annex_problems(ANNEX["data"], _led_ids)

    #: ★ P-231 — 승격한 절의 증거 파일이 **지금도 실재하는가**.
    for area in areas:
        problems += evidence_problems(area)

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

    #: ★ P-211 — **부류의 합은 절 수와 같아야 한다.** 어긋나면 어딘가가 조용히 안 세어졌고,
    #:   안 세어진 절은 「닫혔다」로 읽힌다. 영역 ①은 `kind_derived` 가 게이트의 셈과
    #:   같은 수를 들어야 한다 — 이름표가 낡으면 표가 갈린다(D-227).
    for area in areas:
        n_clause = sum(counts[area["id"]].values())
        n_kind = sum(kinds[area["id"]].values())
        if n_kind != n_clause:
            problems.append(
                "영역 %s(%s): 부류 합 %d 이 절 수 %d 과 다르다 — **안 세어진 절은 "
                "「닫혔다」로 읽힌다** (P-211)" % (area["id"], area["name"], n_kind, n_clause))

    weights = sum(a["weight"] for a in areas)
    if weights != 100:
        problems.insert(0, "가중치 합이 %d 다 — 100 이 아니면 아래 수는 전부 무의미하다" % weights)
    return areas, counts, problems, hands, hands_lock, hands_todo, kinds


def main() -> int:
    _load_local_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-gates", action="store_true",
                    help="대장↔게이트 불일치 검사를 건너뛴다 (P-85 · 건너뛰면 그렇게 적는다)")
    ap.add_argument("--static", action="store_true",
                    help="[P-204 ③] **로그인 없는 갈래만** — 게이트를 한 벌도 부르지 않는다 "
                         "(커밋 훅용 · 계정 다툼 0 · 언제나 회색이고 구조가 깨졌을 때만 1)")
    args = ap.parse_args()
    if args.static:
        global NO_LOGIN
        NO_LOGIN = True
        args.no_gates = True
    if _v_locked():
        print("[GA] ⚠ %s — 로그인하는 게이트(직렬 묶음)는 이 실행에서 회색이다. 조율자는 V 가 끝난 뒤 "
              "`scripts/v_lock.py --unlock` 하고 다시 잰다" % _V_GRAY_NOTE)

    if args.self_test:
        return self_test()

    if not LEDGER.exists():
        print("[GA] 대장이 없다: %s" % LEDGER)
        return 1

    areas, counts, problems, hands, hands_lock, hands_todo, kinds = load()
    total, rows = score(areas, counts, kinds)
    all_clauses = sum(sum(c.values()) for c in counts.values())
    done = sum(c.get(DONE, 0) for c in counts.values())

    print("[GA] [입력] 영역 %d · 절 %d개 (구현 %d · 미착수 %d · 잠김 %d · 미측정 %d)"
          % (len(areas), all_clauses, done,
             sum(c.get("미착수", 0) for c in counts.values()),
             sum(c.get("잠김", 0) for c in counts.values()),
             sum(c.get("미측정", 0) for c in counts.values())))

    for aid, name, weight, d, n, ratio, weighted, pts, kratio in rows:
        #: ★ P-211 — 수 옆에 **그 수의 뜻**을 세운다. `16/20` 만 내면 그 16 은 전부
        #:   「닫혔다」로 읽힌다. 다섯 부류 중 닫힘이 아닌 넷을 이름으로 부른다.
        #: ★★ P-216 — **두 수를 나란히 둔다.** 앞의 `절 d/n` 은 **상태로 센 수**(참고),
        #:   뒤의 `kind` 가 **점수를 만드는 수**다. 둘의 거리가 이 턴에 드러난 것이다.
        #:   ⚠ 앞 조각의 모양은 `verify_readiness_scores.py`(차선 Q)가 읽는다 — 바꾸려면
        #:     같은 커밋에서 저쪽도 함께 고친다. 갈리면 한쪽이 다른 쪽을 빨갛게 한다.
        print("  %-2s %-22s 가중 %2d%%  절 %2d/%-2d = %3.0f%%  kind %5.2f/%-2d = %3.0f%%"
              "  →  %5.2f   %s"
              % (aid, name, weight, d, n, ratio * 100, pts, n, kratio * 100, weighted,
                 kind_tail(kinds.get(aid, {}))))
        if AREA_GATE_NOTE.get(aid):
            print("     ↳ %s" % AREA_GATE_NOTE[aid])
    if args.static:
        print("[GA] ★★ 이 실행은 **정적 갈래(--static)** 다 — 게이트를 **한 벌도 안 불렀다**"
              "(로그인 0 · 계정 다툼 0). 아래 가중 합계는 **점수가 아니다**: "
              "영역 ①의 **상태**는 전부 「못 쟀다」로 세어져 있고, 부류(`kind_derived`)는 "
              "**지난 실행이 남긴 이름표**라 이 실행이 다시 잰 것이 아니다. "
              "점수는 게이트를 부르는 실행이 낸다 (D-210)")
    print("[GA] ★ 상용 오픈 가중 합계 **%.1f%%** [실측]" % total)
    #: ★★★ P-216 — **이 수가 무엇으로 세어졌는지 같은 화면에 적는다.** 안 적으면
    #:   다음 턴에 누군가 옛 식으로 다시 세고 「수가 올랐다」고 말한다.
    print("[GA]   이 수는 **부류(`kind`)로 센 수**다 — closed 1.0 · ratchet 1.0 · "
          "rule_only 0.5 · gate_only 0.5 · unmeasurable 0.0 · **잠김은 분모에서 빼지 않는다** "
          "(P-216 · 2026-09-21 턴 AA). 상태(`구현`)로 세던 옛 식과 다르다")
    old_total = sum(w * r for _a, _n, w, _d, _c, r, _wt, _p, _kr in rows)
    print("[GA]   (참고 · 옛 식 `구현 절 / 전체 절` 로 세면 **%.1f%%** — 그 수는 다섯 부류를 "
          "**전부 1점**으로 세었다. 거리 %.1f 가 P-216 이 드러낸 것이다)"
          % (old_total, old_total - total))
    print("[GA] (계약 축과 합치지 않는다 — D-345. 계약 절은 영역 ①이 그대로 인용한다)")

    # ── 「초록」 다섯 부류 (P-211 · 2026-09-21 · 턴 Z) ──────────────────────
    #   **수와 같은 화면에** 둔다. 다른 쪽에 두면 아무도 같이 읽지 않는다.
    roll = {k: sum(c.get(k, 0) for c in kinds.values()) for k in KINDS}
    print("[GA] [입력] 「초록」 부류 %d절 — closed %d · ratchet %d · rule_only %d · "
          "unmeasurable %d · gate_only %d"
          % (sum(roll.values()), roll["closed"], roll["ratchet"], roll["rule_only"],
             roll["unmeasurable"], roll["gate_only"]))
    not_closed = sum(roll.values()) - roll["closed"]
    print("[GA]   ★ 닫힌 절은 **%d/%d** 이고 나머지 %d절의 「초록」은 **닫힘이 아니다** — "
          "래칫 %d(늘지 않았다) · 규칙만 %d(현장이 비었다) · 못 잼 %d · "
          "게이트만 %d(제목이 게이트보다 넓다)"
          % (roll["closed"], sum(roll.values()), not_closed, roll["ratchet"],
             roll["rule_only"], roll["unmeasurable"], roll["gate_only"]))

    # ── ★★ 별표 ② — 기능명세 id (P-234 · 2026-09-21 · 턴 AB) ──────────────
    #   **상용/100 은 위에서 이미 났고 이 줄은 그 수를 안 건드린다.** 여기 있는 것은
    #   `kind` 표의 정본(절 + 별표)이고, Q 의 「기능명세 포함 완료율」이 읽을 분모다.
    _annex = ANNEX.get("data") or {}
    _acl = _annex.get("clauses") or []
    _n_sec = sum(roll.values())
    if _acl:
        print("[GA] [입력] ★ 별표 ② 기능명세 **%d개** 등재 — 규칙 «%s» · 출처 %s"
              % (len(_acl), " ".join((_annex.get("rule") or "?").split()),
                 _annex.get("source") or "?"))
        print("[GA]   ★ **kind 표 정본 = %d + %d = %d** (절 %d + 별표 %d). 별표는 전부 "
              "`미착수`·`unmeasurable` 로 태어나므로 **점수를 0 만큼 더한다** — "
              "그래서 「기능명세 포함 완료율」은 **분모만 늘어 내려간다.** "
              "**내려간 수가 정본이다**"
              % (_n_sec, len(_acl), _n_sec + len(_acl), _n_sec, len(_acl)))
        print("[GA]   ⚠ **별표는 위의 상용 오픈 가중 합계에 0 을 더했다** — 8영역 밖이라 "
              "가중치 표를 건드리지 않는다. 위 수가 움직였다면 그것은 **절의 부류가 "
              "바뀌어서**이지 별표 때문이 아니다. 두 수는 다른 것을 잰다 (D-345 와 같은 이유)")
        #: ★★ [2026-09-21 · 턴 AB] **이 줄이 없으면 별표 136 이 분모에서 사라진다.**
        #:   Q 의 `verify_spec_coverage.py` 는 위의 「부류 N절」 줄에서 절 수를 읽는데
        #:   그 줄은 **8영역만** 센다. 별표를 8영역 밖에 둔 순간(가중치 표를 지키려고)
        #:   Q 의 분모에서 136 이 **조용히 빠졌고 수가 25.6 → 50.0 으로 올라갔다.**
        #:   **분모가 줄어 올라간 수는 수가 아니다.** 그래서 합을 **따로 한 줄로** 낸다.
        print("[GA] [입력] ★★ **분모 정본 — 절 %d · 별표 %d · 합 %d**  "
              "(`verify_spec_coverage.py` 가 읽을 자리. 위의 「부류 %d절」은 **8영역만** "
              "센 수다 — 그 줄을 분모로 쓰면 별표 %d 이 조용히 빠진다)"
              % (_n_sec, len(_acl), _n_sec + len(_acl), _n_sec, len(_acl)))
    else:
        print("[GA] [입력] ★ 별표 ② 기능명세 **등재 0건 — 회색이다(0 이 아니다)**. "
              "kind 표 정본은 **%d 그대로**다" % _n_sec)
        print("[GA]   ★ 사유: %s"
              % " ".join((_annex.get("why") or "사유가 적혀 있지 않다").split())[:240])
    #: ★ [N → Q · 턴 AA] 셈법 규칙 2 가 「① = 영역 ⑧ 비율」이라 한다. 그 비율이
    #:   **상태로 센 것과 부류로 센 것 중 어느 쪽인가**는 이 턴에 갈릴 수 있다 —
    #:   그래서 **둘 다 찍는다.** 한쪽만 찍으면 읽는 쪽이 어느 것인지 모른 채 베낀다.
    for aid, _name, _w, d, n, ratio, _wt, pts, kratio in rows:
        if aid == "8":
            print("[GA] [입력] 영역 ⑧ 비율 — 상태(구현 %d/%d) **%.3f** · 부류(kind %.2f/%d) "
                  "**%.3f** (`verify_readiness_scores.py` 셈법 ①이 읽는 자리)"
                  % (d, n, ratio, pts, n, kratio))

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
    if args.static:
        print("[GA] **회색(exit 2)** — 정적 갈래다. 대장의 구조(절마다 상태·증명·사유)는 "
              "**실재한다**. 그러나 게이트 색은 %d절에서 **한 벌도 안 쟀다** — "
              "`exit 0` 을 낼 자리가 아니다 (P-204 · D-301)" % unmeasured)
        return 2
    if unmeasured:
        print("[GA] **회색(exit 2)** — 절마다 상태·증명·사유는 실재한다. 그러나 게이트 색을 "
              "%d절에서 **못 쟀다.** 못 잰 것은 초록이 아니다 (D-301 · 규칙 ①)" % unmeasured)
        return 2
    print("[GA] 통과 — 절마다 상태·증명·사유가 실재하고, 대장 상태와 게이트 색이 같다 (P-85)")
    return 0


def _print_table(areas, counts, rows, total, *, markdown: bool) -> None:
    if markdown:
        print()
        #: ★ P-216 — 대표 보고용 표에도 **두 수를 나란히** 둔다. 「구현/전체」만 실으면
        #:   읽는 사람은 그 수로 가중 기여를 검산하려다 안 맞아서 표를 의심한다.
        print("| 영역 | 가중 | 절 구현/전체 | (참고) 상태 달성 | **부류 점수** | 영역 달성 | 가중 기여 |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        for aid, name, weight, d, n, ratio, weighted, pts, kratio in rows:
            print("| %s %s | %d%% | %d/%d | %.0f%% | **%.2f/%d** | %.0f%% | %.2f |"
                  % (aid, name, weight, d, n, ratio * 100, pts, n, kratio * 100, weighted))
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
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE
    try:
        _led = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
        _areas = _led.get("areas") or []
        _n_area = len(_areas)
        _n_clause = sum(len(a.get("clauses") or []) for a in _areas)
        _n_gate = sum(1 for a in _areas for c in (a.get("clauses") or [])
                      if (c.get("gate") or "").strip())
    except Exception:                                        # noqa: BLE001
        _n_area = _n_clause = _n_gate = 0
    gate_header(
        __file__,
        measured=("GA 대장의 절마다 상태·증명·사유가 실재하는가 — **분모 %d절**(영역 %d) · "
                  "그중 `gate:` 를 적은 **%d절은 그 판정기를 실제로 불러** 색을 받는다. "
                  "부른 판정기가 2 를 내면 그 절은 **회색**이고 회색은 초록이 아니다 (P-204 · D-301)"
                  % (_n_clause, _n_area, _n_gate)),
        target="대장 " + str(LEDGER.relative_to(ROOT)).replace("\\", "/") + " · 그리고 절이 가리키는 게이트들을 **실제로 부른다**",
        as_="이 게이트 자신은 자격 없이 대장을 읽는다 — 부르는 게이트마다 **제 머리글(TARGET/AS/SOURCE)** 을 낸다",
        source=file_stamp(LEDGER) + " + " + file_stamp(CONTRACT) + " + " + file_stamp(BLOCKERS),
    )
    raise SystemExit(main())
