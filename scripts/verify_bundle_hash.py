#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-59 — **서버가 내는 번들 = 현재 커밋** (2026-09-05 · 턴 E · 차선 Q).

무엇을 막는가 — **exit 0 이 「병합된 코드가 선다」로 읽혔다**
------------------------------------------------------------
[실측 2026-09-05 · 턴 D] 프런트 빌드 컨테이너가 **낡은 사본**을 묶었고 `exit 0` 이
났다. 사람은 그 0을 「병합된 코드가 선다」로 읽었다. 세종 판정 P-59 는 그래서
**번들이 스스로 어느 커밋인지 말하게** 하고, 게이트가 그 말을 현재 커밋과 맞춘다.

★ **빌더의 종료 코드는 산출물의 신원이 아니다.** `vite build` 의 0 은 「이 소스로
  묶는 데 실패하지 않았다」이지 「그 소스가 지금 커밋이다」가 아니다. 두 문장 사이의
  틈이 정확히 이 사고의 크기이고, 그 틈은 **산출물을 물어야만** 메워진다.

규약 (P-59 · `docs/agent/evidence/P-59/규약_QA.md`)
--------------------------------------------------
  ① 빌드는 **엔트리 JS 안에** 리터럴 토큰을 박는다:  ``GX_COMMIT:<40자리 소문자 16진>``
     (vite `define` 로 치환한 값이 문자열 그대로 번들에 남으면 된다)
  ② 화면 하단에 짧은 7자리를 사람에게 보인다 — 고객 지원이 읽는 자리.
     그 갈래는 **브라우저가** 확인한다(`capture_screens`). 이 게이트는 ①을 판정한다.
  ③ `version.json` 같은 곁파일은 **정본이 아니다.** 있으면 ①과 같은 말을 하는지만 본다.

★ 왜 접두 토큰인가 — **맨 40자리 16진을 찾으면 안 된다.** [실측 2026-09-05]
  지금 번들에서 ``[0-9a-f]{40}`` 은 이미 두 군데 걸린다(``30258509…`` 같은 **숫자
  상수**다). 접두어가 없으면 이 게이트는 남의 숫자를 커밋으로 읽고, 그 초록은
  아무것도 안 맞춘다.

★ 왜 `git rev-parse` 를 부르지 않는가 — 이 컨테이너에는 git 도 `.git` 도 없다
  (`gx-shell` 은 `backend`·`docs`·`scripts` 만 마운트한다 [실측 2026-09-05]).
  그리고 하위 프로세스로 git 을 부르면 **어디서 돌리느냐로 답이 달라진다.**
  `.git/HEAD` 는 파일이고, 어디서 읽어도 같은 답이다. 컨테이너 안에서는
  `GX_COMMIT` 환경변수로 넣는다.

★ **P-72 (2026-09-06 · 턴 G · 차선 S) — 대조 상대가 HEAD 에서 「배치 커밋」으로 바뀌었다**
  옛 규칙(번들 == HEAD) 아래에서는 배치를 마친 뒤 **보고서 한 장을 커밋하는 것만으로**
  이 게이트가 빨개졌다. 코드는 한 줄도 안 움직였는데. 그 빨강이 가리키는 사실은
  「서버가 낡은 코드를 낸다」가 아니라 「문서가 하나 늘었다」였고, 사실과 색이
  어긋나는 게이트는 곧 무시당한다(D-353). 그래서 **한 문장을 둘로 나눈다**:

      ① 서버가 내는 번들 = **`docs/agent/evidence/deploy/` 의 `deploy_commit`**
      ② HEAD − 배치 커밋 차이가 `docs/**` 뿐          ← 그 사이 코드가 움직였나

  둘 다 초록이라야 「지금 서는 것이 지금 코드다」라고 말할 수 있다. 배치 증거가 없는
  자리에서는 **옛 규칙 그대로** 돈다 — 증거를 아직 안 쓰는 사람의 게이트를 태어나면서
  부터 빨갛게 만들지 않는다.
  ⚠ ②는 `git` 이 필요하고 **컨테이너에는 `.git` 이 없다**. 그래서 호스트가 먼저 재서
    `GX_DRIFT_JSON` 으로 넘긴다(`--emit-drift`). `scripts/deploy.sh` 가 그 일을 한다.

    python scripts/verify_bundle_hash.py --self-test
    python scripts/verify_bundle_hash.py --dist frontend/dist
    python scripts/verify_bundle_hash.py --web http://localhost:3002 --commit <40hex>

종료 코드: **0 같다 · 1 다르다(또는 번들이 말하지 않는다) · 2 못 쟀다(회색)**
★ 회색은 초록이 아니다 (D-301). 「번들을 못 읽었다」와 「번들이 낡았다」는 다른 일이다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
PASS, FAIL, GRAY = "pass", "fail", "gray"
TAG = "[BUNDLE]"
ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ **규약의 한 줄.** 이 문자열을 바꾸는 것은 프런트와의 약속을 바꾸는 일이다 —
#:   바꾸려면 `docs/agent/evidence/P-59/규약_QA.md` 를 먼저 바꾸고 여기를 바꾼다.
TOKEN_PREFIX = "GX_COMMIT:"
TOKEN_RE = re.compile(re.escape(TOKEN_PREFIX) + r"([0-9a-f]{40})")
#: 사람이 보는 자리(화면 하단)는 7자리다. 게이트는 **40자리로** 판정한다 —
#: 7자리는 다른 커밋과 부딪힐 수 있고, 부딪히는 신원은 신원이 아니다.
SHORT = 7

#: ★ **P-72** — 배치 증거가 사는 자리. 배치한 사람이 「무엇을 배치했는지」를 여기에
#:   적고, 게이트는 그 적힌 커밋과 서버의 번들을 맞춘다.
DEPLOY_EVIDENCE_DIR = ROOT / "docs" / "agent" / "evidence" / "deploy"
#: 배치 뒤에 바뀌어도 **배치가 여전히 유효한** 자리. 여기를 넓히는 것은 규칙을
#:   바꾸는 일이다 — 넓히려면 왜 그것이 서버가 내주는 것과 무관한지를 먼저 적어라.
DOC_ONLY_PREFIXES = ("docs/",)

SCRIPT_RE = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)
PRELOAD_RE = re.compile(r"""<link[^>]+href=["']([^"']+\.js)["']""", re.I)
HEX40 = re.compile(r"^[0-9a-f]{40}$")


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다** (D-277). 자기시험이 합성 입력을 먹인다
# ═══════════════════════════════════════════════════════════════════════════
def judge(bundle: dict | None, commit: str | None,
          sidecar: str | None = None, deploy: dict | None = None,
          drift: dict | None = None) -> list:
    """`(이름, 판정, 사유)`.

    `bundle` = `{"source": 어디서 읽었나, "assets": [이름…], "commits": [40hex…],
    "html_only": [40hex…]}` · `None` 은 **못 읽었다**.

    ★ **P-72 (2026-09-06 · 턴 G)** — `deploy` 가 있으면 대조 상대가 바뀐다.
      `deploy` = `{"commit": 40hex, "source": 증거 경로}` ·
      `drift`  = `{"paths": [HEAD 와 배치 커밋 사이에 달라진 파일…], "ancestor": bool,
                   "error": str|None}`
    """
    out: list = []
    n_id = "번들이 자기 커밋을 말한다"
    n_eq = "번들 해시 = 현재 커밋" if not deploy else "번들 해시 = **배치 커밋**"
    n_drift = "HEAD − 배치 커밋 차이가 `docs/**` 뿐"
    n_side = "곁파일이 번들과 같은 말을 한다"

    # ★ 대조 상대를 여기서 한 번만 정한다. 아래 갈래들이 각자 정하면 반드시 어긋난다.
    target = (deploy or {}).get("commit") or commit
    target_name = "배치 커밋" if deploy else "현재 커밋"

    if bundle is None:
        out.append((n_id, GRAY, "**못 쟀다** — 번들을 읽지 못했다 (서버가 섰는가 · "
                                "`--dist` 자리가 맞는가). 못 읽은 것은 낡은 것과 다르다"))
        out.append((n_eq, GRAY, "**못 쟀다** — 번들이 없다"))
        if deploy:
            out.append((n_drift, GRAY, "**못 쟀다** — 번들이 없다. 번들을 못 읽은 "
                                       "자리에서 배치 이후 표류를 재면 한 고장을 "
                                       "두 번 센다"))
        return out

    found = sorted(set(bundle.get("commits") or []))
    html_only = sorted(set(bundle.get("html_only") or []))
    src = bundle.get("source", "?")
    assets = ", ".join(bundle.get("assets") or []) or "(자산 0개)"

    if not found and html_only:
        # ★ **곁에 적힌 해시는 번들의 신원이 아니다.** index.html 만 새로 쓰이고
        #   JS 는 낡은 채로 남는 것이 정확히 P-59 사고의 모양이다.
        out.append((n_id, FAIL,
                    f"해시가 **JS 밖에서만** 보인다({html_only}) — 규약 ①은 "
                    f"**엔트리 JS 안**이다. index.html 이나 곁파일은 번들과 따로 "
                    f"갱신될 수 있고, 따로 갱신되는 것은 번들의 신원이 아니다 · {src}"))
    elif not found:
        out.append((n_id, FAIL,
                    f"번들이 **자기가 어느 커밋인지 말하지 않는다** — "
                    f"`{TOKEN_PREFIX}<40hex>` 가 없다({assets}). 말하지 않는 번들은 "
                    f"낡은 사본과 구별되지 않는다. **그 구별 불가가 P-59 사고 "
                    f"그 자체다** — 빌더의 exit 0 은 산출물의 신원이 아니다 · {src}"))
    elif len(found) > 1:
        out.append((n_id, FAIL,
                    f"한 번들이 **커밋 둘**을 말한다 {found} — 자산 일부만 다시 "
                    f"묶였다는 뜻이다(부분 빌드). 섞인 번들은 어느 코드가 서는지 "
                    f"아무도 말할 수 없다 · {src}"))
    else:
        out.append((n_id, PASS,
                    f"`{TOKEN_PREFIX}{found[0][:SHORT]}…` ← {assets} · {src}"))

    if not target:
        out.append((n_eq, GRAY,
                    f"**못 쟀다** — {target_name}을 모른다. `.git/HEAD` 를 못 읽었고 "
                    f"`GX_COMMIT` 도 없다 (컨테이너 안에서는 환경변수로 넣는다)"))
    elif len(found) != 1:
        out.append((n_eq, GRAY,
                    f"**못 쟀다** — 번들 쪽 해시가 하나가 아니다({found or '없다'}). "
                    f"위 줄이 이미 빨강이다 — 여기까지 빨강으로 세면 한 고장을 "
                    f"두 번 센다"))
    elif found[0] == target:
        src = f" ← {deploy.get('source')}" if deploy else ""
        out.append((n_eq, PASS,
                    f"{found[0][:SHORT]} = {target[:SHORT]} — 서버가 내는 번들이 "
                    f"**{target_name}**이다{src}"))
    else:
        out.append((n_eq, FAIL,
                    f"번들 {found[0][:SHORT]} ≠ {target_name} {target[:SHORT]} — "
                    f"**서버가 내는 것은 배치했다고 적은 그 코드가 아니다.** 빌드 "
                    f"컨테이너가 낡은 사본을 묶었을 때 나는 색이다(턴 D). 다시 묶기 "
                    f"전에는 화면에서 본 것을 「병합된 코드」라고 부를 수 없다"
                    if deploy else
                    f"번들 {found[0][:SHORT]} ≠ 현재 {target[:SHORT]} — **서버가 내는 "
                    f"것은 지금 코드가 아니다.** 빌드 컨테이너가 낡은 사본을 묶었을 때 "
                    f"나는 색이다(턴 D). 다시 묶기 전에는 화면에서 본 것을 "
                    f"「병합된 코드」라고 부를 수 없다"))

    # ── P-72 ── **문서 커밋 하나가 배치를 빨갛게 만들면 안 된다** ──────────
    #   [실측 2026-09-05 · 턴 F] 「서버 번들 == HEAD」 규칙 아래에서는 배치 뒤에
    #   보고서 한 장을 커밋하는 순간 게이트가 빨개졌다. 그 빨강은 **아무 코드도
    #   달라지지 않았다는 사실**을 말하지 못한다 — 사람은 곧 그 색을 무시하게 된다.
    #   그래서 대조 상대를 **증거에 적힌 배치 커밋**으로 옮기고, HEAD 와의 거리는
    #   따로 잰다: 그 거리가 `docs/**` 뿐이면 배치는 여전히 유효하다.
    if deploy:
        d = drift or {}
        paths = d.get("paths")
        if d.get("error") or paths is None:
            out.append((n_drift, GRAY,
                        f"**못 쟀다** — HEAD 와 배치 커밋 사이를 못 읽었다 "
                        f"({d.get('error') or 'git 을 못 불렀다'})"))
        elif d.get("ancestor") is False:
            out.append((n_drift, FAIL,
                        f"배치 커밋 {target[:SHORT]} 이 **지금 가지에 없다** — "
                        f"되감겼거나 다른 가지에서 배치했다. 그 번들이 어느 코드인지 "
                        f"이 저장소가 말할 수 없다"))
        elif not paths:
            out.append((n_drift, PASS,
                        f"HEAD = 배치 커밋 {target[:SHORT]} — 배치 뒤 커밋이 없다"))
        else:
            bad = [p for p in paths
                   if not any(p.startswith(pre) for pre in DOC_ONLY_PREFIXES)]
            if bad:
                out.append((n_drift, FAIL,
                            f"배치 뒤에 **문서가 아닌 것**이 {len(bad)}건 바뀌었다: "
                            f"{', '.join(bad[:5])}"
                            f"{' …' if len(bad) > 5 else ''} — 서버는 그 변경을 "
                            f"내주지 않는다. 다시 배치해야 한다"))
            else:
                out.append((n_drift, PASS,
                            f"배치 뒤 {len(paths)}건이 바뀌었고 **전부 "
                            f"`{'`·`'.join(DOC_ONLY_PREFIXES)}` 아래다** — 문서 "
                            f"커밋은 배치 대상이 아니다 (P-72)"))

    if sidecar is not None:
        if len(found) == 1 and sidecar == found[0]:
            out.append((n_side, PASS, f"version.json {sidecar[:SHORT]} = 번들"))
        else:
            out.append((n_side, FAIL,
                        f"곁파일은 {sidecar[:SHORT]} 라고 하는데 번들은 "
                        f"{found or '아무 말도 안 한다'} — **곁파일이 먼저 "
                        f"갱신됐다.** 이때 곁파일만 보는 사람은 낡은 번들을 "
                        f"새것으로 읽는다"))
    return out


def exit_code(rows: list) -> int:
    """빨강 > 회색 > 초록. **회색은 초록이 아니다** (D-301)."""
    verdicts = {v for (_n, v, _w) in rows}
    if FAIL in verdicts:
        return EXIT_FAIL
    if GRAY in verdicts:
        return EXIT_UNDECIDABLE
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 현재 커밋 — **파일로 읽는다.** git 을 부르지 않는다
# ═══════════════════════════════════════════════════════════════════════════
def current_commit(root: Path = ROOT) -> tuple[str | None, str]:
    """`(40hex 또는 None, 어디서 왔나)`.

    차례: `GX_COMMIT` 환경변수 → `.git/HEAD` → (심볼릭이면) `refs/…` → `packed-refs`.
    컨테이너에는 `.git` 이 없으므로 **환경변수가 첫 자리**여야 한다.
    """
    env = (os.environ.get("GX_COMMIT") or "").strip().lower()
    if HEX40.match(env):
        return env, "GX_COMMIT 환경변수"

    head = root / ".git" / "HEAD"
    if not head.exists():
        return None, f"{head} 가 없다 (컨테이너에는 `.git` 이 마운트되지 않는다)"
    raw = head.read_text(encoding="utf-8", errors="replace").strip()
    if HEX40.match(raw):
        return raw, ".git/HEAD (분리된 HEAD)"
    if raw.startswith("ref:"):
        ref = raw.split(":", 1)[1].strip()
        loose = root / ".git" / ref
        if loose.exists():
            val = loose.read_text(encoding="utf-8", errors="replace").strip().lower()
            if HEX40.match(val):
                return val, f".git/{ref}"
        packed = root / ".git" / "packed-refs"
        if packed.exists():
            for line in packed.read_text(encoding="utf-8",
                                         errors="replace").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0].strip().lower(), f".git/packed-refs → {ref}"
    return None, f".git/HEAD 를 읽었으나 커밋을 못 골랐다: {raw!r}"


# ═══════════════════════════════════════════════════════════════════════════
# P-72 — **배치 증거**와 **배치 이후 표류**
#
# ★ 왜 「번들 == HEAD」를 버렸나 [실측 2026-09-05 · 턴 F]
#   그 규칙 아래에서는 배치를 마친 뒤 **보고서 한 장을 커밋하는 것만으로** 게이트가
#   빨개졌다. 그런데 그 빨강이 가리키는 사실은 「서버가 낡은 코드를 낸다」가 아니라
#   「문서가 하나 늘었다」였다. 사실과 색이 어긋나는 게이트는 곧 무시당하고,
#   무시당하는 게이트는 없는 게이트보다 나쁘다(D-353).
#
#   그래서 **두 문장으로 나눈다**:
#     ① 서버가 내는 번들 = **증거에 적힌 배치 커밋**   ← 배치가 실제로 그것이었나
#     ② HEAD − 배치 커밋 차이가 `docs/**` 뿐          ← 그 사이 코드가 움직였나
#   둘 다 초록이라야 「지금 서는 것이 지금 코드다」라고 말할 수 있다.
# ═══════════════════════════════════════════════════════════════════════════
def read_deploy_evidence(dirpath: Path) -> tuple:
    """`(deploy 정보 또는 None, 사유)`. **가장 최근 증거 한 장**을 읽는다.

    증거 JSON 은 `deploy_commit` (40hex) 을 갖는다. 없거나 형태가 아니면 **못 읽은
    것**이지 「배치를 안 한 것」이 아니다 — 그 구별을 사유로 남긴다.
    """
    if not dirpath.is_dir():
        return None, f"{dirpath} 가 없다 — 배치 증거가 아직 한 장도 없다"
    files = sorted(dirpath.glob("*.json"))
    if not files:
        return None, f"{dirpath} 에 증거 JSON 이 없다"
    for path in reversed(files):                    # 이름이 시각이라 뒤가 최신이다
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        val = str(data.get("deploy_commit") or "").strip().lower()
        if HEX40.match(val):
            return ({"commit": val, "source": path.as_posix(),
                     "deployed_at": data.get("deployed_at")},
                    f"배치 증거 {path.name}")
    return None, f"{dirpath} 의 증거에 40자리 `deploy_commit` 이 없다"


def measure_drift(deploy_commit: str, head: str | None,
                  root: Path = ROOT) -> dict:
    """배치 커밋과 HEAD 사이에 **무엇이** 달라졌나.

    ★ **컨테이너에는 `.git` 이 없다** [실측 2026-09-06 · `/repo/.git` 없음]. 이 게이트가
      도는 자리(`gx-shell`)에는 git 실행파일은 있는데 저장소가 없다 — 그러면 여기서만
      영영 회색이고, 영영 회색인 갈래는 아무도 안 읽는다. 그래서 **호스트가 먼저 재서
      `GX_DRIFT_JSON` 으로 넘겨줄 수 있다.** `scripts/deploy.sh` 가 그 일을 한다 —
      사람이 기억할 절차를 만들지 않는다(D-286). 넘어온 값이 없을 때만 git 을 부른다.
    """
    handed = (os.environ.get("GX_DRIFT_JSON") or "").strip()
    if handed:
        try:
            val = json.loads(handed)
            if isinstance(val, dict) and ("paths" in val or "ancestor" in val):
                val.setdefault("error", None)
                val["source"] = "GX_DRIFT_JSON (호스트가 재서 넘겼다)"
                return val
        except ValueError:
            return {"paths": None, "ancestor": None,
                    "error": "GX_DRIFT_JSON 이 JSON 이 아니다"}
    if head and head == deploy_commit:
        return {"paths": [], "ancestor": True, "error": None}
    try:
        anc = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor",
             deploy_commit, head or "HEAD"],
            capture_output=True, text=True, timeout=30)
        if anc.returncode not in (0, 1):
            return {"paths": None, "ancestor": None,
                    "error": (anc.stderr or "merge-base 실패").strip()[:120]}
        if anc.returncode == 1:
            return {"paths": [], "ancestor": False, "error": None}
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only",
             f"{deploy_commit}..{head or 'HEAD'}"],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace")
        if out.returncode != 0:
            return {"paths": None, "ancestor": True,
                    "error": (out.stderr or "diff 실패").strip()[:120]}
        paths = [ln.strip().strip('"') for ln in (out.stdout or "").splitlines()
                 if ln.strip()]
        return {"paths": paths, "ancestor": True, "error": None}
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return {"paths": None, "ancestor": None,
                "error": f"{type(exc).__name__} — git 을 못 불렀다 "
                         f"(컨테이너에는 `.git` 도 git 도 없다)"}


# ═══════════════════════════════════════════════════════════════════════════
# 번들 읽기 — **서버가 내는 것**을 문다. dist 는 곁길이다
# ═══════════════════════════════════════════════════════════════════════════
def _get(url: str, timeout: int = 20) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"{TAG} {url} — 못 읽었다: {type(exc).__name__} {exc}")
        return None


def entry_scripts(html: str) -> list[str]:
    """index.html 이 부르는 JS 들. **엔트리만이 아니라 프리로드까지** 본다 —
    코드 쪼개기(`router-*.js`)로 해시가 다른 덩이에 들어갈 수 있다."""
    seen: set = set()
    out: list = []
    for m in list(SCRIPT_RE.finditer(html)) + list(PRELOAD_RE.finditer(html)):
        src = m.group(1)
        if src.endswith(".js") and src not in seen:
            seen.add(src)
            out.append(src)
    return out


def read_from_web(web: str) -> dict | None:
    web = web.rstrip("/")
    html = _get(web + "/index.html") or _get(web + "/")
    if html is None:
        return None
    commits: list = []
    assets: list = []
    html_only = TOKEN_RE.findall(html)
    for src in entry_scripts(html):
        url = src if src.startswith("http") else web + "/" + src.lstrip("/")
        body = _get(url)
        if body is None:
            continue
        assets.append(src)
        commits += TOKEN_RE.findall(body)
    return {"source": f"서버 {web}", "assets": assets,
            "commits": commits, "html_only": html_only}


def read_from_dist(dist: Path) -> dict | None:
    index = dist / "index.html"
    if not index.exists():
        print(f"{TAG} {index} 가 없다")
        return None
    html = index.read_text(encoding="utf-8", errors="replace")
    commits: list = []
    assets: list = []
    html_only = TOKEN_RE.findall(html)
    for src in entry_scripts(html):
        path = dist / src.lstrip("/")
        if not path.exists():
            continue
        assets.append(src)
        commits += TOKEN_RE.findall(path.read_text(encoding="utf-8",
                                                   errors="replace"))
    return {"source": f"dist {dist}", "assets": assets,
            "commits": commits, "html_only": html_only}


def read_sidecar(web: str | None, dist: Path | None) -> str | None:
    """`version.json` 이 **있으면** 그 해시. 없으면 `None`(검사하지 않는다)."""
    raw = None
    if web:
        raw = _get(web.rstrip("/") + "/version.json")
    elif dist and (dist / "version.json").exists():
        raw = (dist / "version.json").read_text(encoding="utf-8", errors="replace")
    if not raw:
        return None
    try:
        val = str(json.loads(raw).get("commit", "")).strip().lower()
    except (ValueError, AttributeError):
        return None
    return val if HEX40.match(val) else None


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **양성과 음성을 함께** (D-277 · D-350)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list = []
    head = "3d40cf66411a22ec7d93501f4665781435ace788"
    old = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"

    def v(rows):
        return {n: verdict for (n, verdict, _w) in rows}

    def bundle(commits, *, html_only=(), assets=("assets/index-BaRLuf6q.js",)):
        return {"source": "자기시험", "assets": list(assets),
                "commits": list(commits), "html_only": list(html_only)}

    # ── ★★ **출생 표본** (D-310) — 이 도구를 만들게 한 바로 그 사례 ────────
    #   [실측 2026-09-05 · 턴 D] **빌드 컨테이너가 낡은 사본을 빌드했고 `exit 0`
    #   이 났다.** 사람(영실·세종 둘 다)은 그 0을 「병합된 코드가 선다」로 읽었다.
    #   빌더는 참말을 했다 — 「묶는 데 실패하지 않았다」. 거짓은 **읽는 쪽**에서
    #   났고, 산출물에 신원이 없었기 때문에 아무도 그것을 가릴 수 없었다.
    #   그래서 이 출생 표본은 **두 벌**이다:
    #     ㉠ 낡은 커밋을 말하는 번들  → 빨강이어야 한다 (다른 커밋이다)
    #     ㉡ 아무 말도 안 하는 번들   → 빨강이어야 한다 — 턴 D 의 **실제 산출물**이
    #        바로 이것이고, 해시가 없어서 낡았다는 것을 증명할 수조차 없었다
    born_old = v(judge(bundle([old]), head))
    if born_old.get("번들 해시 = 현재 커밋") != FAIL:
        bad.append("**출생 표본 ㉠** — 낡은 사본을 묶은 번들(다른 커밋)이 빨강이 "
                   "아니다. 턴 D 에 사람이 exit 0 을 「병합된 코드가 선다」로 읽은 "
                   "자리가 여기다")
    born_mute = v(judge(bundle([]), head))
    if born_mute.get("번들이 자기 커밋을 말한다") != FAIL:
        bad.append("**출생 표본 ㉡** — 자기 커밋을 말하지 않는 번들이 빨강이 아니다. "
                   "말하지 않는 번들은 낡은 사본과 구별되지 않는다")
    if born_mute.get("번들 해시 = 현재 커밋") != GRAY:
        bad.append("말하지 않는 번들에서 **대조 갈래까지 빨강**을 낸다 — 한 고장을 "
                   "두 번 세면 고친 뒤에도 빨강이 남은 것처럼 보인다")

    # ── 양성: 같으면 초록 ───────────────────────────────────────────────
    ok = v(judge(bundle([head]), head))
    if ok.get("번들 해시 = 현재 커밋") != PASS or \
            ok.get("번들이 자기 커밋을 말한다") != PASS:
        bad.append("번들 해시가 현재 커밋과 **같은데** 초록이 아니다 — 태어나면서부터 "
                   "빨간 게이트는 다음 사람이 우회한다")
    if exit_code(judge(bundle([head]), head)) != EXIT_OK:
        bad.append("전부 초록인데 종료 코드가 0이 아니다")

    # ── 음성: 다르면 빨강, 그리고 **종료 코드에 든다** ──────────────────
    if exit_code(judge(bundle([old]), head)) != EXIT_FAIL:
        bad.append("번들이 낡았는데 종료 코드가 1이 아니다 — 판정만 하고 아무것도 "
                   "막지 않는 게이트다")

    # ── 못 쟀다 ≠ 통과 (D-301) ──────────────────────────────────────────
    if exit_code(judge(None, head)) != EXIT_UNDECIDABLE:
        bad.append("번들을 **못 읽었는데** 회색(2)이 아니다. 서버가 안 선 날 이 "
                   "게이트가 초록으로 죽는다")
    if exit_code(judge(bundle([head]), None)) != EXIT_UNDECIDABLE:
        bad.append("현재 커밋을 **모르는데** 회색이 아니다 — 컨테이너에는 `.git` 이 "
                   "없다. 모르는 채로 초록을 내면 이 게이트는 아무것도 안 맞춘다")

    # ── **곁파일은 정본이 아니다** ──────────────────────────────────────
    side = v(judge(bundle([old]), head, sidecar=head))
    if side.get("곁파일이 번들과 같은 말을 한다") != FAIL:
        bad.append("`version.json` 은 새 커밋을 말하고 **번들은 낡았는데** 곁파일 "
                   "갈래가 초록이다 — 곁파일만 보는 사람이 낡은 번들을 새것으로 읽는다")
    if v(judge(bundle([head]), head, sidecar=head)).get(
            "곁파일이 번들과 같은 말을 한다") != PASS:
        bad.append("곁파일과 번들이 같은 말을 하는데 빨강이다")

    # ── **JS 밖에서만** 보이는 해시는 신원이 아니다 ─────────────────────
    if v(judge(bundle([], html_only=[head]), head)).get(
            "번들이 자기 커밋을 말한다") != FAIL:
        bad.append("해시가 index.html 에만 있는데 초록이다 — index.html 은 번들과 "
                   "따로 갱신될 수 있다(P-59 사고의 모양 그대로)")

    # ── 한 번들에 커밋 둘(부분 빌드) ────────────────────────────────────
    if v(judge(bundle([head, old]), head)).get("번들이 자기 커밋을 말한다") != FAIL:
        bad.append("한 번들이 커밋 둘을 말하는데 초록이다 — 자산 일부만 다시 묶였다")

    # ── **접두어 없는 40자리 16진을 커밋으로 읽지 않는다** ───────────────
    #   [실측 2026-09-05] 지금 번들에서 `[0-9a-f]{40}` 은 이미 두 군데 걸린다 —
    #   `3025850929940456840179914546843642076011` 같은 **숫자 상수**다.
    noise = "3025850929940456840179914546843642076011"
    if TOKEN_RE.findall(f"var x={noise};"):
        bad.append("접두어 없는 40자리 숫자를 커밋으로 읽는다 — 남의 상수를 신원으로 "
                   "읽는 게이트는 아무것도 안 맞춘다")
    if TOKEN_RE.findall(f'"{TOKEN_PREFIX}{head}"') != [head]:
        bad.append(f"규약대로 박은 `{TOKEN_PREFIX}<40hex>` 를 못 읽는다")

    # ── index.html 파싱: script + modulepreload 둘 다 ───────────────────
    html = ('<link rel="modulepreload" href="/assets/router-CWOBuQ2U.js">'
            '<script type="module" src="/assets/index-BaRLuf6q.js"></script>'
            '<link rel="stylesheet" href="/assets/index.css">')
    got = entry_scripts(html)
    if sorted(got) != ["/assets/index-BaRLuf6q.js", "/assets/router-CWOBuQ2U.js"]:
        bad.append(f"index.html 에서 JS 를 못 고른다: {got} — 코드 쪼개기로 해시가 "
                   f"프리로드 덩이에 들어가면 못 찾는다")

    # ── ★★ **P-72 출생 표본** (D-310) — 문서 커밋 하나가 배치를 빨갛게 만들었다 ──
    #   [실측 2026-09-05 · 턴 F] 배치를 마치고 보고서를 커밋하자 「번들 == HEAD」가
    #   깨져 게이트가 빨개졌다. 코드는 한 줄도 안 움직였다.
    dep = {"commit": old, "source": "docs/agent/evidence/deploy/x.json"}
    docs_only = v(judge(bundle([old]), head, deploy=dep,
                        drift={"paths": ["docs/agent/RESUME_NEXT.md"],
                               "ancestor": True, "error": None}))
    if docs_only.get("번들 해시 = **배치 커밋**") != PASS:
        bad.append("**P-72 출생 표본** — 번들이 **배치 커밋 그대로**인데 초록이 아니다. "
                   "문서 커밋 하나로 배치가 빨개지던 자리가 여기다")
    if docs_only.get("HEAD − 배치 커밋 차이가 `docs/**` 뿐") != PASS:
        bad.append("배치 뒤 바뀐 것이 `docs/**` 뿐인데 빨강이다 — 문서 커밋은 배치 "
                   "대상이 아니다")
    if exit_code(judge(bundle([old]), head, deploy=dep,
                       drift={"paths": ["docs/x.md"], "ancestor": True,
                              "error": None})) != EXIT_OK:
        bad.append("문서만 바뀐 상태인데 종료 코드가 0이 아니다")

    # ── 음성: **코드**가 배치 뒤에 움직였으면 빨강 ─────────────────────
    codedrift = judge(bundle([old]), head, deploy=dep,
                      drift={"paths": ["docs/x.md", "frontend/src/App.tsx"],
                             "ancestor": True, "error": None})
    if v(codedrift).get("HEAD − 배치 커밋 차이가 `docs/**` 뿐") != FAIL:
        bad.append("배치 뒤 `frontend/src` 가 바뀌었는데 초록이다 — 서버는 그 변경을 "
                   "내주지 않는다. 이 갈래가 없으면 P-72 는 **배치 게이트를 끈 것**이 된다")
    if exit_code(codedrift) != EXIT_FAIL:
        bad.append("코드가 표류했는데 종료 코드가 1이 아니다")

    # ── 배치 커밋이 지금 가지에 없다 ────────────────────────────────────
    if v(judge(bundle([old]), head, deploy=dep,
               drift={"paths": [], "ancestor": False, "error": None})).get(
            "HEAD − 배치 커밋 차이가 `docs/**` 뿐") != FAIL:
        bad.append("배치 커밋이 지금 가지에 없는데 초록이다 — 그 번들이 어느 코드인지 "
                   "저장소가 말할 수 없다")

    # ── **못 쟀다 ≠ 통과** — git 이 없는 자리 ───────────────────────────
    if exit_code(judge(bundle([old]), head, deploy=dep,
                       drift={"paths": None, "ancestor": None,
                              "error": "FileNotFoundError"})) != EXIT_UNDECIDABLE:
        bad.append("HEAD 와의 거리를 **못 쟀는데** 회색이 아니다 — 컨테이너에는 git 이 "
                   "없다. 모르는 채로 초록을 내면 이 갈래는 아무것도 안 맞춘다")

    # ── 배치 증거가 있으면 **HEAD 가 아니라 배치 커밋**과 맞춘다 ────────
    if v(judge(bundle([head]), head, deploy=dep,
               drift={"paths": [], "ancestor": True, "error": None})).get(
            "번들 해시 = **배치 커밋**") != FAIL:
        bad.append("증거는 배치 커밋이 %s 라는데 번들은 %s 다 — 그런데 초록이다. "
                   "대조 상대가 여전히 HEAD 라면 P-72 는 적용되지 않은 것이다"
                   % (old[:7], head[:7]))

    # ── 증거가 없으면 **옛 규칙 그대로**(번들 == HEAD) ──────────────────
    if v(judge(bundle([head]), head)).get("번들 해시 = 현재 커밋") != PASS:
        bad.append("배치 증거가 없는 자리에서 옛 규칙이 깨졌다 — 증거를 아직 안 쓰는 "
                   "사람의 게이트를 태어나면서부터 빨갛게 만들면 안 된다")

    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — **출생 표본 4**(턴 D · 낡은 사본 · 말없는 번들 · "
          f"**P-72 문서 커밋**) · 양성 2 · 음성 2 · 회색 2 · 곁파일 2 · 갈래 2 · "
          f"토큰 2 · 파싱 1 · **배치 6**(문서만 · 코드 표류 · 가지 밖 · git 없음 · "
          f"대조 상대 · 옛 규칙)")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="P-59 서버가 내는 번들 = 현재 커밋")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--web", default=os.environ.get("GX_WEB", ""),
                    help="SPA 주소. **이쪽이 본줄기다** — 게이트가 물어야 할 것은 "
                         "「서버가 내는 것」이지 「빌드 폴더에 있는 것」이 아니다")
    ap.add_argument("--dist", default="",
                    help="곁길: 번들 폴더를 곧장 읽는다")
    ap.add_argument("--commit", default="",
                    help="현재 커밋(40hex). 없으면 .git/HEAD · GX_COMMIT")
    ap.add_argument("--out", default="")
    # ── P-72 ─────────────────────────────────────────────────────────────
    ap.add_argument("--deploy-evidence", default=str(DEPLOY_EVIDENCE_DIR),
                    help="배치 증거 폴더. 가장 최근 `deploy_commit` 을 대조 상대로 쓴다")
    ap.add_argument("--deploy-commit", default="",
                    help="증거 대신 배치 커밋을 곧장 준다(드릴용 40hex)")
    ap.add_argument("--no-deploy-evidence", action="store_true",
                    help="옛 규칙(번들 == HEAD)으로 판정한다")
    ap.add_argument("--emit-drift", action="store_true",
                    help="**호스트에서** HEAD − 배치 커밋 차이만 재서 JSON 으로 낸다. "
                         "컨테이너 안 판정에 `GX_DRIFT_JSON` 으로 넘긴다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.emit_drift:
        # 호스트 전용 갈래 — **저장소가 있는 자리에서만** 답이 나온다.
        dep = (args.deploy_commit or "").strip().lower()
        if not HEX40.match(dep):
            dep, why = None, "--deploy-commit 이 없다"
            found, why = read_deploy_evidence(Path(args.deploy_evidence))
            dep = (found or {}).get("commit")
        head, _w = current_commit()
        if not dep:
            print(json.dumps({"paths": None, "ancestor": None,
                              "error": "배치 커밋을 모른다"}, ensure_ascii=False))
            return EXIT_UNDECIDABLE
        print(json.dumps(measure_drift(dep, head), ensure_ascii=False))
        return EXIT_OK
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    if args.commit:
        commit, whence = args.commit.strip().lower(), "--commit"
        if not HEX40.match(commit):
            commit, whence = None, f"--commit 이 40자리 16진이 아니다: {args.commit!r}"
    else:
        commit, whence = current_commit()
    print(f"{TAG} [현재 커밋] {commit or '모른다'} ← {whence}")

    dist = Path(args.dist) if args.dist else None
    if args.web:
        bundle = read_from_web(args.web)
    elif dist:
        bundle = read_from_dist(dist)
    else:
        print(f"{TAG} `--web` 또는 `--dist` 가 있어야 읽는다")
        bundle = None
    sidecar = read_sidecar(args.web or None, dist)

    # ── P-72 배치 증거 ───────────────────────────────────────────────────
    deploy, dwhy, drift = None, "옛 규칙(번들 == HEAD)으로 판정한다", None
    if not args.no_deploy_evidence:
        if args.deploy_commit:
            val = args.deploy_commit.strip().lower()
            if HEX40.match(val):
                deploy = {"commit": val, "source": "--deploy-commit"}
                dwhy = "배치 커밋을 인자로 받았다"
            else:
                dwhy = f"--deploy-commit 이 40자리 16진이 아니다: {args.deploy_commit!r}"
        else:
            deploy, dwhy = read_deploy_evidence(Path(args.deploy_evidence))
    print(f"{TAG} [배치 커밋] {(deploy or {}).get('commit') or '증거 없음'} ← {dwhy}")
    if deploy:
        drift = measure_drift(deploy["commit"], commit)

    rows = judge(bundle, commit, sidecar, deploy=deploy, drift=drift)
    mark = {PASS: "  ", FAIL: "X ", GRAY: "? "}
    for (name, verdict, why) in rows:
        print(f"{TAG} {mark[verdict]}{name:28} {why}")

    rc = exit_code(rows)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(
            {"commit": commit, "commit_source": whence, "bundle": bundle,
             "deploy": deploy, "deploy_source": dwhy, "drift": drift,
             "doc_only_prefixes": list(DOC_ONLY_PREFIXES),
             "sidecar": sidecar, "token_prefix": TOKEN_PREFIX,
             "rows": [{"name": n, "verdict": v, "why": w} for (n, v, w) in rows],
             "exit": rc}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{TAG} 기록 → {args.out}")
    print(f"{TAG} " + {
        EXIT_OK: ("통과 — 서버가 내는 번들이 **배치 커밋**이고, 그 뒤 바뀐 것은 "
                  "`docs/**` 뿐이다 (P-72)" if deploy else
                  "통과 — 서버가 내는 번들이 현재 커밋이다"),
        EXIT_FAIL: "실패 — **화면에서 본 것을 「병합된 코드」라고 부를 수 없다** (P-59)",
        EXIT_UNDECIDABLE: "**회색(exit 2)** — 못 쟀다. 회색은 초록이 아니다 (D-301)",
    }[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
