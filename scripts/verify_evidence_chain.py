#!/usr/bin/env python
"""LAW-08 증거 해시 체인 게이트 — **행 하나를 고치면 exit 1** 이 되는 자리.

PRD v2.5 §E3 이 이 도구의 이름을 먼저 적었다: *"`verify_evidence_chain.py` — 행 하나를
고치면 체인 검증 exit 1."* 그 문장이 이 파일의 계약이고, `--self-test` 의 첫 갈래가
정확히 그 사건이다.

두 개의 눈 — 하나는 코드를, 하나는 표를 본다
---------------------------------------------
  ① **정적**(기본, Django 불필요) — *체인 밖에서 태어나는 감사 행이 있는가.*
     체인은 「쓰는 손이 하나」일 때만 성립한다. `common/audit_writer.py` 를 지나지 않고
     감사표에 행을 만드는 코드가 하나라도 있으면, 그 행은 두 칸이 없이 태어나고
     **그 뒤의 검증은 「끊겼다」를 상시로 낸다.** 상시 빨강은 아무도 안 본다(D-301 형제).
     그래서 잇는 호출이 쓰기 자리에 실제로 있는지, 그리고 우회로가 없는지를 본다.

  ② **표**(`--db`, gx-shell 위임) — *지금 쌓여 있는 행들이 서로 이어지는가.*
     판정식은 `backend/common/evidence_chain.py` 한 벌이다. 이 파일은 그것을 **부를 뿐**
     다시 적지 않는다 — 판정식 복사본 하나가 격리 사고의 원인이었다(D-212).

    python scripts/verify_evidence_chain.py              # ① 정적 판정
    python scripts/verify_evidence_chain.py --db         # ② 실제 표를 다시 계산해 대조
    python scripts/verify_evidence_chain.py --anchor 2026-09-04   # 그날의 종이 앵커
    python scripts/verify_evidence_chain.py --self-test  # 양성·음성 대조

★ 출생 표본 (D-310)
-------------------
이 도구를 태어나게 한 사건: *"감사로그에 무결성 칸이 없다 — **고치면 고쳐진다**"*
(D-346 LAW-08). 그래서 자기시험의 첫 갈래는 **감사 한 줄의 `msg` 를 고치는 것**이고,
거기서 초록이 나오면 이 게이트는 아무것도 아니다. 둘째 갈래는 **행을 지우는 것**이다 —
고치는 것만 잡고 지우는 것을 놓치면, 지우는 쪽이 더 쉬우므로 실제 공격은 그쪽으로 간다.

★ 이 게이트가 **혼자서 못 하는 것** — 적어 두는 것이 게이트의 일부다
--------------------------------------------------------------------
고친 뒤 그 행부터 꼬리까지 해시를 **다시 계산하면** 체인은 초록이 된다. 그것을 잡는 것은
코드가 아니라 **어제 종이에 인쇄된 40자**다(`--anchor`). 그래서 이 도구의 초록은
「아무도 안 고쳤다」가 아니라 **「고친 흔적이 없다 + 어제 앵커와 맞다」** 여야 완전하다.
앵커 대조는 사람이 종이를 들고 하는 일이라 여기서 자동화하지 않는다 —
자동화한 척하면 그것이 가장 나쁜 초록이다.
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 판정식은 여기 한 벌뿐이다. **순수 계산 부분만** import 한다 — Django 는 필요 없다.
from common import evidence_chain  # noqa: E402

#: 감사 행을 만들어도 되는 **유일한 자리**. 여기를 늘리면 체인이 그만큼 약해진다.
WRITER = "backend/common/audit_writer.py"

#: 체인을 잇는 호출의 이름. 쓰기 자리에 이 호출이 없으면 두 칸 없는 행이 태어난다.
LINK_CALL = "append_evidence_hash"

#: 감사표에 **행을 만드는** 동사. 읽기는 여기 없다 — 읽는 것은 체인을 안 깨뜨린다.
CREATE_VERBS = ("create", "bulk_create", "get_or_create", "update_or_create")

#: 훑는 범위 — **기능 코드**다. 시험·스크립트는 뺀다.
#:   · 시험은 일부러 날행을 만든다(`tests/test_dormant_wiring.py` 가 그렇다). 그 행들은
#:     `logger_name` 이 `guardianx.` 로 시작하지 않아 체인에 들지 않는다.
#:   · 스크립트는 조사·측정이고, 조사까지 막으면 상태를 볼 방법이 없어진다.
#:   ⚠ 뺀 것을 **적어 두는 것**이 요점이다. 면제가 아니라 등재다(D-261 c).
SCAN_ROOTS = ("backend/common", "backend/kernels", "backend/apps",
              "backend/stream_monitors", "backend/dashboard", "backend/surveillance")
SKIP_PARTS = {"__pycache__", "migrations", "tests", "node_modules"}

CONTAINER = os.environ.get("GX_SHELL", "gx-shell")

#: 종료코드에 이름을 준다 — 이 파일은 셋을 다 쓰면서 숫자로만 적고 있었다.
#: **2 는 「재서 틀렸다」가 아니라 「안 쟀다」다** (P-204 · D-301).
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2


# ══════════════════════════════════════════════════════════════════════════
# ① 정적 눈 — 순수 함수. 자기시험이 겨누는 과녁이 여기다 (D-277).
# ══════════════════════════════════════════════════════════════════════════

def _mentions_audit(node: ast.AST) -> bool:
    """이 식이 감사 모델을 가리키는가. 문자열 `"AuditLogs"` 도 이름도 같게 본다."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and sub.value == "AuditLogs":
            return True
        if isinstance(sub, ast.Name) and sub.id == "AuditLogs":
            return True
    return False


def _audit_aliases(tree: ast.AST) -> set[str]:
    """이 파일 안에서 **감사표를 가리키는 이름들**.

    ⚠ 이름 하나만 보면 놓친다 — 이 저장소의 실제 모양이 셋이다::

        AuditLogs = apps.get_model("logger", "AuditLogs")   # 변수
        from core.logger.models import AuditLogs            # import
        def _model(): return apps.get_model("logger", …)    # 헬퍼 (audit_writer 의 모양)

    셋째를 빼면 **정확히 우리 코드의 모양을 못 본다.** 자기가 태어난 코드를 못 보는
    도구가 되는 것이 D-310 이 이름 붙인 실패다.
    """
    aliases = {"AuditLogs"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _mentions_audit(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    aliases.add(t.id)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "AuditLogs":
                    aliases.add(a.asname or a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Return) and sub.value is not None
                        and _mentions_audit(sub.value)):
                    aliases.add(node.name)
                    break
    return aliases


def _base_names(node: ast.AST) -> set[str]:
    """`X._base_manager.create(...)` 에서 **X 로 쓰인 이름들**을 모은다."""
    out: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            out.add(sub.attr)
    return out


def _calls_link(tree: ast.AST) -> bool:
    """`append_evidence_hash(...)` 를 **실제로 부르는가**. 주석·독스트링은 부름이 아니다."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == LINK_CALL:
            return True
    return False


def judge_source(rel: str, src: str) -> list[str]:
    """파일 하나. **순수 함수다** — 자기시험이 이것을 직접 먹인다 (D-277).

    두 가지를 본다:
      · 쓰기 자리(`audit_writer`)가 **체인을 잇는가**
      · 그 밖의 기능 코드가 **감사표에 행을 만드는가**(= 체인 밖의 행)

    술어를 AST 로 두는 이유: 주석과 독스트링에 적힌 예시를 위반으로 세면 게이트가
    **문서를 벌하게 되고**, 그러면 다음 사람이 설명을 지운다.
    """
    rel = rel.replace("\\", "/")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    if rel == WRITER:
        if not _calls_link(tree):
            return [f"{rel}: 감사 쓰기 자리에 «{LINK_CALL}» 호출이 없다 — "
                    f"두 칸 없는 감사 행이 태어난다. 체인이 시작된 뒤의 그런 행은 "
                    f"검증에서 「끊겼다」로 잡히고, 그 빨강은 고칠 수 없다"]
        return []

    aliases = _audit_aliases(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in CREATE_VERBS:
            continue
        if _base_names(node.func.value) & aliases:
            out.append(
                f"{rel}: 감사표에 «.{node.func.attr}(» 로 행을 만든다 — {WRITER} 밖이다. "
                f"체인 밖에서 태어난 감사 행은 두 칸이 없고, 그 행 하나가 "
                f"검증 전체를 상시 빨강으로 만든다")
            break
    return out


def sources() -> list[tuple[str, str]]:
    out = []
    for root in SCAN_ROOTS:
        base = ROOT / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(p in SKIP_PARTS for p in path.relative_to(ROOT).parts):
                continue
            out.append((path.relative_to(ROOT).as_posix(),
                        path.read_text(encoding="utf-8", errors="replace")))
    writer = ROOT / WRITER
    if writer.is_file() and not any(r == WRITER for r, _ in out):
        out.append((WRITER, writer.read_text(encoding="utf-8", errors="replace")))
    return out


def static_judgement() -> int:
    files = sources()
    findings: list[str] = []
    for rel, src in files:
        findings += judge_source(rel, src)

    print(f"[입력] 감사 쓰기 후보 파일 {len(files)}건 "
          f"(범위={' · '.join(SCAN_ROOTS)} · 시험·스크립트 제외)")
    if not files:
        print("[CHAIN] 대상 0건 — 그 상태의 「위반 0」은 **재지 않은 것**이다 (D-301)")
        return 1
    if findings:
        print(f"[CHAIN] 체인 밖의 감사 쓰기 {len(findings)}건 — 멈춘다")
        for f in findings:
            print(f"  · {f}")
        return 1
    print("[CHAIN] ① 정적 — 체인 밖에서 태어나는 감사 행 0건 "
          f"(쓰는 손 1곳 = {WRITER})")
    return 0


# ══════════════════════════════════════════════════════════════════════════
# ② 표를 보는 눈 — gx-shell 에 위임한다. 호스트에는 dj-core 가 없다.
# ══════════════════════════════════════════════════════════════════════════

_DB_SNIPPET = r"""
import os, django, json, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from common import evidence_chain
r = evidence_chain.verify_chain()
print("GX_CHAIN_JSON " + json.dumps({
    "total": r.total, "chained": r.chained, "head": r.head,
    "tail_prev": r.tail_prev, "genesis": r.starts_at_genesis,
    "breaks": [{"id": b.audit_id, "kind": b.kind, "detail": b.detail} for b in r.breaks],
    # ★ **등재된 끊김도 실어 나른다** — 안 실으면 「어긋남 0건」이 그것들을 말없이 삼킨다.
    #   P-191 은 옛 끊김을 「고치지 말고 기록으로 남기라」고 했고, 기록은 **보여야** 기록이다.
    "recorded": [{"id": b.audit_id, "kind": b.kind, "detail": b.detail} for b in r.recorded],
}, ensure_ascii=False))
"""

_ANCHOR_SNIPPET = r"""
import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from datetime import date
from common import evidence_chain
d = date.fromisoformat(%(day)r)
a = evidence_chain.daily_anchor(d)
print("GX_ANCHOR_JSON " + json.dumps({"day": d.isoformat(), "anchor": a,
                                      "line": evidence_chain.anchor_line(d, a)},
                                     ensure_ascii=False))
"""


#: ★ LAW-08 QR — **진입점은 이 파일 하나다**(설계 v1.0 §7①).
#:   *사람이 부른* `--anchor … --qr` 호출 **1회 = QR 1장**. 스케줄러·크론·웹 라우트에서
#:   부르는 진입점을 **만들지 않는다** — 크론이 매일 종이를 찍으면 그것이 바로 자기증명이고,
#:   자기증명은 아무것도 증명하지 않는다(설계 §0 · §6-4).
#:   그려지는 자리는 **컨테이너 안**이다: `qrcode` 는 gx-shell 에만 있고,
#:   그래서 앵커 값이 **호스트 밖으로도 남의 서버로도 나가지 않는다**(설계 §7③).
_QR_SNIPPET = r"""
import os, django, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from datetime import date, timedelta
from common import evidence_chain, paper_anchor_qr
d = date.fromisoformat(%(day)r)
p = d - timedelta(days=1)
a = evidence_chain.daily_anchor(d)
pa = evidence_chain.daily_anchor(p)
r = evidence_chain.verify_chain()
out = {"day": d.isoformat(), "prev_day": p.isoformat(), "anchor": a, "prev_anchor": pa,
       "rows": r.total, "chained": r.chained, "gaps": len(r.recorded),
       "breaks": len(r.breaks), "head": r.head,
       "line": evidence_chain.anchor_line(d, a)}
try:
    payload = paper_anchor_qr.build_payload(
        for_day=d, anchor=a, prev_day=p, prev_anchor=pa,
        rows=r.total, chain=r.chained, gaps=len(r.recorded),
        head=r.head or "", exit_code=0)
    out["payload"] = payload
    out["block"] = paper_anchor_qr.printable_block(payload)
    out["qr_drawn"] = paper_anchor_qr.render_qr_ascii(payload) is not None
except Exception as exc:
    out["payload"] = None
    out["why"] = type(exc).__name__ + ": " + str(exc)
print("GX_QR_JSON " + json.dumps(out, ensure_ascii=False))
"""


def _in_container(snippet: str) -> tuple[int, str]:
    """gx-shell 안에서 한 조각을 돌린다. **도커가 없으면 회색(exit 2)이지 초록이 아니다.**"""
    if shutil.which("docker") is None:
        return 2, "docker 를 못 찾았다"
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    proc = subprocess.run(
        ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
         CONTAINER, "python", "-c", snippet],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _payload(out: str, marker: str) -> dict | None:
    import json

    for line in out.splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):].strip())
            except ValueError:
                return None
    return None


def db_judgement() -> int:
    code, out = _in_container(_DB_SNIPPET)
    data = _payload(out, "GX_CHAIN_JSON ")
    if data is None:
        print(f"[CHAIN] ② 표 — **판정 불가**(회색). 컨테이너 «{CONTAINER}» 에서 "
              f"검증을 못 돌렸다 (exit {code}). 회색은 초록이 아니다 (D-301)")
        print(out[-1500:])
        return 2

    rec = data.get("recorded")
    if rec is None:
        #: ★ 옛 컨테이너 코드가 `recorded` 를 안 실어 준다. **모르는 것을 0 으로 읽지 않는다** —
        #:   0 으로 읽으면 등재된 끊김이 「없는 것」이 되고, 그게 이 게이트가 막으려는 바로 그 일이다.
        print("[CHAIN] ② 표 — **판정 불가**(회색). 컨테이너 안 `evidence_chain` 이 "
              "`ChainReport.recorded` 를 안 준다 — 낡은 코드가 서 있다. "
              "`docker restart gx-gunicorn-e` 뒤 다시 재라. 회색은 초록이 아니다")
        return 2

    print(f"[입력] 감사 행 {data['total']}건 (그중 체인 {data['chained']}건 · "
          f"등재된 끊김 {len(rec)}건)")
    if data["breaks"]:
        print(f"[CHAIN] ② 표 — **새로 난 어긋남 {len(data['breaks'])}건** — 멈춘다")
        for b in data["breaks"][:20]:
            print(f"  · #{b['id']} {b['kind']} — {b['detail']}")
        if rec:
            print(f"  (그 밖에 **등재된 끊김 {len(rec)}건**이 따로 있다 — 아래 참고)")
            _print_recorded(rec)
        return 1
    if data["chained"] == 0:
        print("[CHAIN] ② 표 — 체인 행 0건. 「어긋남 0」이 아니라 **아직 아무것도 안 이었다**")
        return 1
    if not data["genesis"]:
        print(f"[CHAIN] ② 표 — 어긋남 0건. ⚠ 앞머리가 잘려 있다"
              f"(첫 prev={data['tail_prev'][:12]}…) — 보존기간 집행이거나 삭제다. "
              f"그 구간의 증거는 **그날 인쇄된 앵커**에 있다")
    if rec:
        #: ★ **여기가 이 게이트에서 가장 거짓말하기 쉬운 줄이었다.** 예전에는 이 자리가
        #:   그냥 「어긋남 0건」이었고, 등재된 22건은 한 글자도 안 나왔다. 등재는 「없던 일로
        #:   하기」가 아니라 「고치지 않고 **보이게** 두기」다 — 안 보이면 지운 것과 같다.
        print(f"[CHAIN] ② 표 — **새로 난 어긋남 0건**. 다만 줄은 깨끗하지 않다: "
              f"**등재된 끊김 {len(rec)}건**이 있고, 체인은 그 지점부터 이어진다 (P-191)")
        _print_recorded(rec)
        print(f"[CHAIN] ② 표 — 머리 해시 {data['head'][:16]}…")
        return 0
    print(f"[CHAIN] ② 표 — 어긋남 0건 · 등재된 끊김도 0건 · "
          f"머리 해시 {data['head'][:16]}…")
    return 0


def _print_recorded(rec: list) -> None:
    """등재된 끊김을 **이름으로** 인쇄한다. 수만 내면 다음 사람이 세어 보지 않는다."""
    for b in rec[:20]:
        print(f"  · (등재) #{b['id']} {b['kind']} — {b['detail']}")
    if len(rec) > 20:
        print(f"  · … 그 밖 {len(rec) - 20}건")


def anchor(day: date) -> int:
    code, out = _in_container(_ANCHOR_SNIPPET % {"day": day.isoformat()})
    data = _payload(out, "GX_ANCHOR_JSON ")
    if data is None:
        print(f"[CHAIN] 앵커 — **판정 불가**(회색, exit {code})")
        print(out[-1500:])
        return 2
    print(f"[입력] {data['day']} 하루")
    print(data["line"])
    return 0 if data["anchor"] else 1


def _qr_payload_is_sound(payload: str) -> tuple[bool, str]:
    """종이로 나가기 **직전**의 마지막 문. 판정식은 `common/paper_anchor_qr` 한 벌이다.

    ★ 이 파일은 판정식을 **다시 적지 않는다** — 판정식 복사본 하나가 격리 사고의
      원인이었다(D-212). 여기서 하는 일은 그 한 벌을 **다른 손으로 한 번 더 부르는 것**이다.
    """
    try:
        from common import paper_anchor_qr          # noqa: PLC0415 — 없으면 회색이다
    except Exception as exc:                        # noqa: BLE001
        return False, f"판정식을 못 불렀다({type(exc).__name__}) — 회색이지 초록이 아니다"

    low = payload.lower()
    for marker in paper_anchor_qr.URL_MARKERS:
        if marker in low:
            return False, (f"payload 에 URL 스킴 «{marker}» 가 있다 — 링크를 담은 QR 은 "
                           f"종이로 안 나간다(설계 §1 · §7②)")
    parsed = paper_anchor_qr.parse_payload(payload)
    if parsed is None:
        return False, "payload 를 못 읽었다"
    ok, why = parsed.is_well_formed()
    if not ok:
        return False, why
    return True, ""


def anchor_with_qr(day: date) -> int:
    """★ LAW-08 **열두 번째 칸** — 그날 줄의 QR 한 장을 사람 16자와 **함께** 낸다.

    ★ **QR 생성 실패는 이 판정기를 빨갛게 만들지 않는다**(설계 §7⑥). 섞으면 다음 사람은
      빨강을 끄려고 **QR 을 끄거나 대조를 끈다.** 앵커가 떴으면 그 줄은 유효하고,
      QR 이 없으면 「QR 없음 + 사유」를 적고 **나머지 열한 칸을 손으로 채운다**(설계 §5).
    """
    code, out = _in_container(_QR_SNIPPET % {"day": day.isoformat()})
    data = _payload(out, "GX_QR_JSON ")
    if data is None:
        print(f"[CHAIN] 앵커+QR — **판정 불가**(회색, exit {code}). 회색은 초록이 아니다")
        print(out[-1500:])
        return 2
    print(f"[입력] {data['day']} 하루 · 감사 행 {data['rows']}건 · 체인 {data['chained']}건 · "
          f"등재된 끊김 {data['gaps']}건 · 새로 난 어긋남 {data['breaks']}건")
    print(data["line"])
    if not data["anchor"]:
        print("[LAW-08] 그날 감사 기록이 없다 — QR 도 없다(담을 값이 없다)")
        return 1
    if data.get("payload") is None:
        print("[LAW-08] QR — **못 만들었다**(회색). 앵커 줄은 위에 그대로 있다. "
              "「QR 없음 + 사유」를 적고 나머지 열한 칸을 손으로 채운다 — **그 줄은 유효하다**")
        print(f"  · 사유: {data.get('why', '(사유 없음)')}")
        return 0                        # ★ 설계 §7⑥ — QR 실패는 체인 판정의 색이 아니다

    #: ★★ **인쇄 직전에 한 번 더 판다.** payload 를 만든 것은 컨테이너 안이고,
    #:   종이로 내보내는 것은 여기다. 만든 자리와 내보내는 자리가 **다른 손**이면,
    #:   한쪽이 무너져도 다른 쪽이 멈춘다 — 설계 §7② 가 「문자열로 검사한다」고 적은
    #:   자리가 정확히 이 경계다. 여기서 안 보면, 컨테이너 안 코드가 바뀌는 날
    #:   URL 한 줄이 종이까지 그대로 간다.
    ok, why = _qr_payload_is_sound(data["payload"])
    if not ok:
        print(f"[LAW-08] QR — **인쇄 직전 검사에서 멈췄다**(회색): {why}")
        print("  · 앵커 줄은 위에 그대로 있다. 「QR 없음 + 사유」를 적고 손으로 채운다")
        return 0                        # ★ 여기서도 빨강을 안 낸다(설계 §7⑥)
    print(data["block"])
    if not data.get("qr_drawn"):
        print("[LAW-08] ⚠ QR **그림은 못 그렸다**(리더용 도형 없음 · 평문은 위에 그대로다). "
              "회색이지 빨강이 아니다")
    print(f"[LAW-08] ⚠ `ref.head` 는 **대조 대상이 아니다** — 지금 값 {data['head'][:16]}… 는 "
          f"잴 때마다 달라진다. 어제와 달라도 **아무것도 하지 않는다**")
    return 0


# ══════════════════════════════════════════════════════════════════════════
# ③ 자기시험 — 양성·음성. **판정기가 눈이 멀었는지 먼저 본다** (D-277 · D-310).
# ══════════════════════════════════════════════════════════════════════════

def _chain(n: int = 4) -> list[dict]:
    out: list[dict] = []
    prev = evidence_chain.GENESIS
    for i in range(1, n + 1):
        rec = {"id": i, "msg": f"[F-12] set:threshold — allowed: 줄 {i}", "note": ""}
        h = evidence_chain.digest(prev_hash=prev, record=rec)
        out.append({"id": i, "record": rec, "prev_hash": prev, "hash": h})
        prev = h
    return out


def self_test() -> int:
    bad = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal bad
        ok = got == want
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1

    # ── 가. 체인 판정식 (양성 셋 · 음성 둘) ───────────────────────────────
    intact = _chain()
    check("손대지 않은 체인은 안 잡는다",
          bool(evidence_chain.verify_sequence(intact)), False)

    tampered = _chain()
    tampered[2]["record"]["msg"] = "[F-12] set:threshold — allowed: 줄 3 (고침)"
    breaks = evidence_chain.verify_sequence(tampered)
    check("★ 출생표본 — **감사 한 줄의 내용을 고치면 잡는다**", bool(breaks), True)
    check("   그리고 고쳐진 **그 행**을 지목한다",
          bool(breaks) and breaks[0].audit_id == 3, True)
    check("   판정 이름이 «내용이 바뀌었다» 다",
          bool(breaks) and breaks[0].kind == evidence_chain.HASH_MISMATCH, True)

    removed = _chain()
    del removed[2]
    kinds = {b.kind for b in evidence_chain.verify_sequence(removed)}
    check("★ 출생표본 ② — **가운데 행을 지우면 잡는다**(고치기보다 쉬운 쪽)",
          evidence_chain.PREV_MISMATCH in kinds, True)

    stripped = _chain()
    stripped[2]["hash"] = ""
    stripped[2]["prev_hash"] = ""
    kinds = {b.kind for b in evidence_chain.verify_sequence(stripped)}
    check("★ 출생표본 ③ — **두 칸만 지워도 잡는다**(가장 그럴듯한 은폐)",
          evidence_chain.MISSING in kinds, True)

    check("LAW-08 이전의 두 칸 없는 행은 **안 잡는다**(상시 빨강 금지)",
          bool(evidence_chain.verify_sequence(
              [{"id": 0, "record": {"id": 0}, "prev_hash": "", "hash": ""}] + intact)),
          False)
    check("보존기간이 앞에서부터 지운 모양은 **안 잡는다** — 그 자리는 종이가 본다",
          bool(evidence_chain.verify_sequence(_chain(5)[2:])), False)
    check("   그래도 **가운데**를 지우면 여전히 잡는다 (D-326)",
          bool(evidence_chain.verify_sequence(
              [e for e in _chain(5) if e["id"] != 3])), True)

    # ── 나. 정적 눈 (양성 둘 · 음성 셋) ──────────────────────────────────
    writer_ok = "row = M._base_manager.create(x=1)\nappend_evidence_hash(audit_id=row.pk)\n"
    writer_no = "row = M._base_manager.create(x=1)\nreturn row\n"
    check("★ 출생표본 ④ — 쓰기 자리에서 **잇는 호출이 사라지면** 잡는다",
          bool(judge_source(WRITER, writer_no)), True)
    check("   잇는 호출이 있으면 안 잡는다",
          bool(judge_source(WRITER, writer_ok)), False)
    check("체인 밖에서 감사 행을 만들면 잡는다",
          bool(judge_source("backend/apps/dsm/x.py",
                            'AuditLogs = apps.get_model("logger", "AuditLogs")\n'
                            "AuditLogs._base_manager.create(msg='x')\n")), True)
    check("감사표를 **읽기만** 하면 안 잡는다",
          bool(judge_source("backend/apps/dsm/x.py",
                            'AuditLogs = apps.get_model("logger", "AuditLogs")\n'
                            "rows = AuditLogs._base_manager.filter(pk=1)\n")), False)
    check("주석 안의 언급은 쓰기가 아니다",
          bool(judge_source("backend/apps/dsm/x.py",
                            "# AuditLogs._base_manager.create(msg='x')\n")), False)
    check("독스트링 안의 언급도 쓰기가 아니다",
          bool(judge_source("backend/apps/dsm/x.py",
                            '"""AuditLogs._base_manager.create(msg=1) 는 금지다."""\n')),
          False)
    check("감사표와 무관한 create 는 안 잡는다",
          bool(judge_source("backend/apps/dsm/x.py",
                            "Zone._base_manager.create(name='z')\n")), False)

    # ── 다. 열거기가 실제로 파일을 읽는가 — 0건이면 판정이 아니라 고장이다
    n = len(sources())
    check(f"기능 코드를 실제로 훑는다 ({n}건)", n > 0, True)

    # ── 라. **회색 갈래** — 모르는 것을 0 으로 읽지 않는가 (턴 X · 차선 S) ──────
    #
    #   이 게이트의 초록은 「어긋남 0」 하나가 아니다. 컨테이너가 무엇을 안 줬을 때
    #   **초록으로 접히는가**가 같은 무게다. 그 갈래는 `--db` 로 눌러도 안 보인다 —
    #   낡은 코드가 서 있는 컨테이너를 일부러 만들어야 보이기 때문이다.
    #   그래서 여기서 대답을 **가짜로 만들어** 갈래를 밟는다. 판정식은 안 베낀다:
    #   진짜 `db_judgement()` 를 그대로 부르고 **대답만** 갈아 끼운다.
    for label, reply, want in _GRAY_CASES:
        check(label, _db_exit_with(reply) == want, True)

    if bad:
        print(f"[CHAIN] 자기시험 {bad}건 실패 — **이 게이트는 눈이 멀었다**")
        return 1
    print("[CHAIN] 자기시험 21건 통과 (체인 양성 5 · 음성 3 · 정적 양성 2 · 음성 4 · "
          "열거 1 · 회색 갈래 4)")
    return 0


def _reply(**payload) -> str:
    """컨테이너가 돌려줬을 법한 한 줄. `json` 은 여기서만 쓴다."""
    import json

    return "GX_CHAIN_JSON " + json.dumps(payload, ensure_ascii=False)


#: 회색 갈래 네 가지. **기대값이 0 인 줄이 하나뿐**인 것이 요점이다 —
#: 나머지 셋은 「모르겠다」이고, 모르겠다는 초록이 아니다.
_GRAY_CASES = (
    ("★ 컨테이너가 «recorded» 를 안 주면 **회색(2)** — 0 으로 안 읽는다",
     _reply(total=9, chained=9, head="a" * 64, tail_prev="0" * 64,
            genesis=True, breaks=[]), 2),
    ("   컨테이너가 아예 대답을 못 하면 **회색(2)**",
     "Traceback (most recent call last): ModuleNotFoundError: common", 2),
    ("   등재된 끊김이 딸려 오면 **초록(0)** — 다만 그 수를 함께 낸다",
     _reply(total=9, chained=9, head="a" * 64, tail_prev="0" * 64, genesis=True,
            breaks=[], recorded=[{"id": 7, "kind": "prev_mismatch", "detail": "…"}]), 0),
    ("   새로 난 어긋남이 있으면 **빨강(1)**",
     _reply(total=9, chained=9, head="a" * 64, tail_prev="0" * 64, genesis=True,
            breaks=[{"id": 7, "kind": "hash_mismatch", "detail": "…"}], recorded=[]), 1),
)


def _db_exit_with(reply: str) -> int:
    """컨테이너의 대답을 `reply` 로 **갈아 끼우고** 진짜 `db_judgement()` 를 부른다.

    ⚠ 인쇄는 삼킨다 — 자기시험의 줄 사이에 남의 보고서가 끼면 사람이 어느 줄이
      판정인지 못 읽는다. 삼키는 것은 **글자뿐이고 판정은 그대로** 돌아온다.
    """
    import contextlib
    import io

    global _in_container
    original = _in_container
    _in_container = lambda snippet: (0, reply)      # noqa: E731
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return db_judgement()
    finally:
        _in_container = original


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--db", action="store_true",
                    help="실제 감사표를 다시 계산해 대조한다 (gx-shell 위임)")
    ap.add_argument("--anchor", metavar="YYYY-MM-DD",
                    help="그날의 종이 앵커 한 줄을 낸다")
    ap.add_argument("--qr", action="store_true",
                    help="`--anchor` 와 함께 — 그날 줄의 QR 한 장을 사람 16자와 **함께** 낸다 "
                         "(LAW-08 설계 v1.0 §7① · 사람이 부른 호출 1회 = QR 1장)")
    args = ap.parse_args()

    print("[CHAIN] LAW-08 증거 해시 체인 — 행 하나를 고치면 exit 1 (PRD v2.5 §E3-1)")
    if args.self_test:
        return self_test()
    if args.qr and not args.anchor:
        #: ★ QR 은 **그날 줄**에 붙는 칸이다. 날짜 없이 QR 만 내는 갈래를 두면
        #:   그 갈래가 곧 스케줄러의 진입점이 된다(설계 §6-4 가 금지한 자리).
        print("[CHAIN] `--qr` 는 `--anchor YYYY-MM-DD` 와 함께만 쓴다 — "
              "QR 은 **그날 한 줄**의 열두 번째 칸이다")
        return EXIT_UNDECIDABLE
    if args.anchor:
        day = date.fromisoformat(args.anchor)
        return anchor_with_qr(day) if args.qr else anchor(day)
    code = static_judgement()
    if args.db:
        return max(code, db_judgement())
    #: ★ [P-204 · 턴 Y · 차선 Q] **`--db` 없이 낸 0 은 「통과」가 아니라 「이 호출이 끝났다」다.**
    #:   이 게이트의 두 눈 중 **살아 있는 감사표를 다시 계산하는 눈**은 `--db` 에만 있다.
    #:   정적 눈만 뜬 채 0 을 내면 러너·대장은 그것을 **LAW-08 초록**으로 적는다 —
    #:   그런데 그때 잰 것은 소스이지 **사슬이 아니다.** 안 잰 것은 회색이다 (D-301).
    if code != EXIT_OK:
        return code
    print("[CHAIN] ? **못 쟀다** — `--db` 를 안 줬다. 정적 눈(소스)만 떴고 "
          "**살아 있는 감사표는 한 행도 다시 계산하지 않았다.** "
          "이 0 은 「이 호출이 통과」일 뿐이다 (P-204) — 재려면 `--db` 로 부른다")
    return EXIT_UNDECIDABLE


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    try:
        _n_src = len(sources())
    except Exception:                                        # noqa: BLE001
        _n_src = 0
    gate_header(
        __file__,
        measured=("① 감사 행을 쓰는 손을 AST 로 전수 — **분모 %d**(범위 %s 의 .py) · "
                  "② `--db` 를 준 실행에서만 살아 있는 감사표를 **행마다 다시 계산**한다 "
                  "(안 주면 ②는 분모 0 — 그래서 `--db` 없는 실행은 회색이다 · P-204)"
                  % (_n_src, " · ".join(SCAN_ROOTS))),
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    raise SystemExit(main())
