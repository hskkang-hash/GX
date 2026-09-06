#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-67 — **보존 일수·백업의 기본값은 없다. 선언만 있다** (판정기 · 2026-09-06 · 차선 E).

    "강제: `verify_retention_declared.py` — 미선언 테넌트에서 purge/backup 호출 0 ·
     선언 테넌트에서 backup 파일 1 · restore dry-run 기록 1."   — 지시서 §2 P-67

무엇을 재는가 — **다섯 수**
---------------------------
    ① 미선언 테넌트에서 **purge 호출 0**       ← 선언이 먼저다
    ② 미선언이면 **backup 호출 0**             ← 목적지 없는 백업은 백업이 아니다
    ③ 선언 테넌트에서 **backup 파일 1개 이상 실재** ← 「뜬다」가 아니라 「떴다」
    ④ **restore dry-run 기록 1건 + RTO 실측 분**    ← 재지 않은 수는 약속이 아니다
    ⑤ 코드에 보존 일수 **기본값이 없다**(정적 검사)  ← 이 절이 태어난 자리

★ **⑥ 양성 대조** 를 함께 잰다 — 없으면 ①②가 거짓 초록이 된다
---------------------------------------------------------------
    「아무것도 안 하는 함수」는 ①②를 **언제나** 통과한다. 그래서 **선언된 테넌트에서는
    실제로 파기 경로가 불린다**를 같이 잰다(dry-run 이라 한 행도 안 지운다).
    그 대조가 없으면 이 판정기는 「파기 기능을 통째로 지운 것」에 초록을 준다.

★ 어디서 도는가 — **못 재는 자리를 회색으로 말한다** (P-70)
-----------------------------------------------------------
    ①②⑥ Django 가 필요하다 → 없으면 그 칸은 **판정 불가**(사유 = "Django 환경")
    ③   백업 볼륨을 봐야 한다 → 컨테이너 안에는 `/backup` 이 안 붙어 있다.
        호스트에서는 도커로 본다 → 도커가 없으면 **판정 불가**(사유 = "도커")
    ④   증거 파일을 읽는다 → 호스트·컨테이너 둘 다 읽을 수 있다(`/docs` 마운트)
    ⑤   파일만 읽는다 → **어디서나 돈다**

    즉 **한 자리에서 다섯 칸이 다 초록일 수는 없다**. 그것을 숨기지 않는다 —
    호스트에서 ③④⑤가 초록이고 컨테이너에서 ①②⑤⑥이 초록이면 그것이 지금의 사실이고,
    두 실행을 합쳐야 다섯이 채워진다. 못 잰 칸을 초록으로 적는 것이 거짓 초록이다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/verify_retention_declared.py     # ①②④⑤⑥
    python scripts/verify_retention_declared.py               # ③④⑤
    python scripts/verify_retention_declared.py --self-test   # 판정 규칙만

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[P-67]"

#: 정적 검사가 훑는 **집행하는 자리**. 여기에 수가 있으면 그것이 기본값이다.
#: ⚠ `config/retention_seed.py` 는 여기 없다 — 그 파일은 **선언**이고, 대신
#:   ⑤가 「그 선언이 환경으로 잠겨 있는가」를 따로 잰다.
ENFORCEMENT_FILES = (
    "backend/apps/dsm/retention.py",
    "backend/common/ops_tasks.py",
    "backend/config/celery.py",
)

#: 선언 자리. **여기에는 수가 있어야 정상**이고, 대신 환경으로 잠겨 있어야 한다.
SEED_FILE = "backend/config/retention_seed.py"

#: 보존·백업 일수를 뜻하는 이름. 이 낱말이 든 이름에 수 기본값이 붙으면 잡는다.
RETENTION_NAME = re.compile(
    r"(retention|보존).*(day|일수)|(day|일수).*(retention|보존)", re.I)

#: 증거를 찾는 자리들. 호스트와 컨테이너가 같은 파일을 다른 이름으로 본다.
RESTORE_EVIDENCE = (
    "docs/agent/evidence/OPS-19/restore_drill_last.json",
    "/docs/agent/evidence/OPS-19/restore_drill_last.json",
    "docs/agent/evidence/D-373/restore_drill_last.json",
    "/docs/agent/evidence/D-373/restore_drill_last.json",
)


def repo_root() -> Path:
    """저장소 뿌리. 컨테이너에서는 `/repo` 가 그 모양이다."""
    here = Path(__file__).resolve()
    for cand in (here.parents[1], Path("/repo"), Path.cwd()):
        if (cand / "backend").is_dir():
            return cand
    return here.parents[1]


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **순수 함수다. 그래서 시험할 수 있다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list:
    """`(이름, 통과, 사유)` 여섯. `None` 은 **못 쟀다**이지 0 이 아니다 (D-301)."""
    out = []

    n = facts.get("purge_calls_undeclared")
    if n is None:
        out.append(("① 미선언 → purge 호출 0", False,
                    "**판정 불가** — Django 환경이 없다. 컨테이너에서 돌린다"))
    else:
        out.append(("① 미선언 → purge 호출 0", n == 0,
                    "호출 0 · 판정 SKIPPED_UNDECLARED" if n == 0 else
                    f"**{n}번 불렸다** — 아무도 선언하지 않은 수로 남의 영상을 지운다"))

    n = facts.get("backup_calls_undeclared")
    if n is None:
        out.append(("② 미선언 → backup 호출 0", False,
                    "**판정 불가** — Django 환경이 없다"))
    else:
        out.append(("② 미선언 → backup 호출 0", n == 0,
                    "호출 0 · 판정 SKIPPED_UNDECLARED" if n == 0 else
                    f"**{n}번 불렸다** — 어디에 뜰지 모르는 백업이 돌았다"))

    n = facts.get("backup_files")
    if n is None:
        out.append(("③ 선언 → backup 파일 1+", False,
                    "**판정 불가** — 백업 볼륨을 못 봤다(도커가 필요하다)"))
    else:
        out.append(("③ 선언 → backup 파일 1+", n >= 1,
                    f"{n}개 실재" if n >= 1 else
                    "**0개** — 「백업이 돈다」는 선언이고 파일이 사실이다"))

    rto = facts.get("restore_rto_minutes")
    rec = facts.get("restore_records")
    if rec is None:
        out.append(("④ restore 기록 1 + RTO", False,
                    "**판정 불가** — 복구 시험 기록을 못 찾았다"))
    elif rec < 1:
        out.append(("④ restore 기록 1 + RTO", False,
                    "**0건** — 복구를 해 보지 않은 백업은 백업이 아니다"))
    elif rto is None:
        out.append(("④ restore 기록 1 + RTO", False,
                    f"기록 {rec}건인데 **RTO 가 없다** — 재지 않은 수를 "
                    "약속하면 그것은 종이다"))
    else:
        ok = bool(facts.get("restore_ok"))
        out.append(("④ restore 기록 1 + RTO", ok,
                    f"기록 {rec}건 · RTO **{rto:.2f}분**" +
                    ("" if ok else " — 그런데 **살아나지 않았다**")))

    hits = facts.get("default_hits")
    if hits is None:
        out.append(("⑤ 코드에 기본값 없음", False, "**판정 불가** — 파일을 못 읽었다"))
    else:
        out.append(("⑤ 코드에 기본값 없음", len(hits) == 0,
                    "집행하는 자리 셋에 수 기본값 0개" if not hits else
                    "**" + " · ".join(hits[:4]) + "** — 아무도 정하지 않은 수가 "
                    "되돌릴 수 없는 일을 한다"))

    n = facts.get("purge_calls_declared")
    if n is None:
        out.append(("⑥ 양성 대조 — 선언 → 돈다", False,
                    "**판정 불가** — Django 환경이 없다"))
    else:
        out.append(("⑥ 양성 대조 — 선언 → 돈다", n > 0,
                    f"선언한 테넌트에서 파기 경로가 {n}번 불렸다(dry-run)" if n > 0
                    else "**0번** — 파기가 통째로 죽었다. ①②는 그래도 초록이다"))
    return out


def self_test() -> int:
    bad = []
    if any(ok for _, ok, _ in judge({})):
        bad.append("빈 사실에서 초록이 났다")
    good = {"purge_calls_undeclared": 0, "backup_calls_undeclared": 0,
            "backup_files": 2, "restore_records": 1, "restore_rto_minutes": 0.14,
            "restore_ok": True, "default_hits": [], "purge_calls_declared": 3}
    if [ok for _, ok, _ in judge(good)] != [True] * 6:
        bad.append("정상 갈래가 초록이 아니다")
    # ★ **출생 표본** — 이 도구를 만들게 한 **바로 그 두 사실** (2026-09-06 · 턴 G).
    #   ㉠ 「보존 90일」이 거짓이었다: 코드 기본값이었고 아무도 정한 적이 없다.
    #      `retention.py:68 DEFAULT_RETENTION_DAYS = 30` · `ops_tasks` 의 「기본 90」.
    #   ㉡ **백업이 한 번도 저장된 적 없다**: 뜨는 것·살리는 것은 구현인데
    #      일정·목적지가 비어 있었다. 그래서 RPO 24h 를 약속할 수 없었다.
    #   이 둘이 아래 표본 목록의 「기본값 남음」·「백업 파일 0」이다. 변이 표본은
    #   「이 규칙이 무엇을 잡아야 하는가」를 묻고, 출생 표본은 **「그날 무엇이 있었는가」**
    #   를 묻는다 — 소스가 고쳐진 뒤에도 이 둘은 그날을 기억한다.
    for name, patch, want in (
        ("미선언 파기", {"purge_calls_undeclared": 1}, 0),
        ("미선언 백업", {"backup_calls_undeclared": 1}, 1),
        ("백업 파일 0", {"backup_files": 0}, 2),
        ("복구 기록 0", {"restore_records": 0}, 3),
        ("RTO 없음", {"restore_rto_minutes": None}, 3),
        ("복구 실패", {"restore_ok": False}, 3),
        ("기본값 남음", {"default_hits": ["retention.py:68 DEFAULT_RETENTION_DAYS=30"]}, 4),
        ("파기가 죽음", {"purge_calls_declared": 0}, 5),
    ):
        rows = judge(dict(good, **patch))
        if rows[want][1]:
            bad.append(f"음성 표본을 못 잡는다: {name}")
    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 정상 1 · 음성 8(**출생 표본 2** 포함) · 빈 사실 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 정적 검사 — **어디서나 돈다.** Django 도 도커도 필요 없다
# ═══════════════════════════════════════════════════════════════════════════
def _is_number(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
        and not isinstance(node.value, bool)


def scan_defaults(root: Path):
    """집행하는 자리에 **보존 일수 수 기본값**이 있는가. `(자리 목록, 읽은 파일 수)`.

    잡는 세 모양 — 셋 다 「아무도 정하지 않았는데 수가 나오는」 자리다:
        ㉠ `DEFAULT_RETENTION_DAYS = 30`         이름에 보존·일수가 든 수 대입
        ㉡ `getattr(settings, "…RETENTION_DAYS…", 30)`   읽기의 세 번째 인자
        ㉢ `get_config_value_by_path("System", "…retention_days", 90)`  같은 모양
    ⚠ 주석·문자열 안의 수는 **안 잡는다.** AST 로 보므로 「예전에 30이 있었다」는
      설명 주석이 판정기를 빨갛게 만들지 않는다 — 그런 주석은 남겨야 하는 것이다.
    """
    hits, read = [], 0
    for rel in ENFORCEMENT_FILES:
        path = root / rel
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        read += 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [t.id for t in targets if isinstance(t, ast.Name)]
                if node.value is not None and _is_number(node.value):
                    for nm in names:
                        if RETENTION_NAME.search(nm):
                            hits.append(f"{rel}:{node.lineno} {nm}={node.value.value}")
            if isinstance(node, ast.Call):
                fn = node.func
                fname = getattr(fn, "attr", None) or getattr(fn, "id", "")
                if fname not in ("getattr", "get_config_value_by_path", "env",
                                 "int", "get"):
                    continue
                args = node.args
                if len(args) < 3:
                    continue
                key = " ".join(a.value for a in args[:2]
                               if isinstance(a, ast.Constant) and isinstance(a.value, str))
                if key and RETENTION_NAME.search(key) and _is_number(args[2]):
                    hits.append(f"{rel}:{node.lineno} {fname}({key!r}, "
                                f"기본 {args[2].value})")
    return (hits if read else None), read


def scan_seed_is_env_locked(root: Path):
    """선언 시드가 **환경으로 잠겨 있는가.** 잠기지 않은 선언은 그냥 기본값이다.

    `DECLARED_ENVIRONMENTS` 가 있고 거기에 `production` 이 **없어야** 한다.
    """
    path = root / SEED_FILE
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if "DECLARED_ENVIRONMENTS" in names and node.value is not None:
                try:
                    envs = ast.literal_eval(node.value)
                except ValueError:
                    return None
                return [str(e) for e in envs]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# ①②⑥ Django 가 필요한 칸 — **한 행도 지우지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
def collect_django(facts: dict, say) -> None:
    #: ⚠ 컨테이너에서 `/repo/scripts` 로 부르면 `config` 가 안 잡힌다 — 앱은 `/app` 에
    #:   있고 저장소 사본은 `/repo/backend` 에 있다. 둘 다 넣어 준다(호스트에서는
    #:   앞엣것이 없고 뒤엣것이 있다). 이것을 빠뜨리면 **Django 칸이 통째로 회색**이 되고,
    #:   회색은 초록이 아니므로 판정기가 아무 말도 못 하게 된다 [실측 2026-09-06].
    for cand in ("/app", str(repo_root() / "backend")):
        if cand not in sys.path and Path(cand).is_dir():
            sys.path.insert(0, cand)
    try:
        import django

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from django.apps import apps
        from django.test.utils import override_settings

        from apps.dsm import retention
        from common import ops_tasks
    except Exception as exc:                                   # noqa: BLE001
        say(f"{TAG} [환경] Django 를 세우지 못했다 — ①②⑥은 **회색**이다: "
            f"{type(exc).__name__}: {exc}"[:200])
        return

    UserGroup = apps.get_model("user", "UserGroup")
    group = UserGroup._base_manager.order_by("pk").first()
    if group is None:
        say(f"{TAG} [환경] 테넌트가 하나도 없다 — ①②⑥은 **회색**이다")
        return

    # ── ① 미선언 테넌트에서 파기 경로가 **몇 번 불리는가** ────────────────
    #    실제로 지우는 손(`_sweep_target`)을 세는 것이 요점이다. 판정 낱말만 보면
    #    「SKIPPED 라고 적고 지우는」 함수를 못 잡는다.
    calls = {"n": 0}
    real_sweep_target = retention._sweep_target

    def spy(*a, **k):
        calls["n"] += 1
        return real_sweep_target(*a, **k)

    blank = {name: None for name in retention.SETTING_NAMES}
    retention._sweep_target = spy
    try:
        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={}, **blank):
            got = retention.purge(group_id=group.pk, dry_run=True,
                                  reason="P-67 판정기 — 미선언 갈래를 잰다")
        facts["purge_calls_undeclared"] = calls["n"]
        facts["purge_verdict_undeclared"] = got.get("verdict")
        facts["purge_audit_undeclared"] = got.get("audit_id")

        # 전역 집행(sweep) 도 같은 답을 내야 한다 — 문이 둘이면 하나만 막아도 샌다.
        calls["n"] = 0
        with override_settings(**blank):
            swept = retention.sweep(dry_run=True,
                                    reason="P-67 판정기 — 전역 미선언 갈래를 잰다")
        facts["sweep_calls_undeclared"] = calls["n"]
        facts["sweep_verdict_undeclared"] = swept.get("verdict")
        facts["purge_calls_undeclared"] += calls["n"]

        # ── ⑥ 양성 대조 — 선언하면 **실제로 불린다**(dry-run) ─────────────
        calls["n"] = 0
        with override_settings(VIDEO_RETENTION_DAYS_BY_TENANT={group.pk: 30}):
            ran = retention.purge(group_id=group.pk, dry_run=True,
                                  reason="P-67 판정기 — 양성 대조(미리보기)")
        facts["purge_calls_declared"] = calls["n"]
        facts["purge_verdict_declared"] = ran.get("verdict")
        facts["purge_deleted_declared"] = ran.get("deleted_total")
    finally:
        retention._sweep_target = real_sweep_target

    # ── ② 목적지 미선언이면 백업 도구가 **한 번도 안 불린다** ─────────────
    hits = {"n": 0}

    class _Spy:
        def dump_db(self, *a, **k):
            hits["n"] += 1
            return {}

        def mirror_objects(self, *a, **k):
            hits["n"] += 1
            return {}

        def manifest_is_verifiable(self, *a, **k):
            return True

    real_load = ops_tasks._load
    ops_tasks._load = lambda name: _Spy()
    try:
        with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True, OPS_BACKUP_DIR=""):
            out = ops_tasks.ops_backup_beat()
        facts["backup_calls_undeclared"] = hits["n"]
        facts["backup_verdict_undeclared"] = out.get("verdict")
    finally:
        ops_tasks._load = real_load

    # 감사 로그 쪽도 같은 질문을 받는다 — 선언이 없으면 dj-core 를 안 부른다.
    facts["audit_declared_days"] = ops_tasks.audit_retention_declared_days()
    facts["audit_source"] = ops_tasks.audit_retention_source()


def collect_django_via_container(name: str, say):
    """Django 칸을 **컨테이너에게 대신 재게 한다.** 못 하면 `None`.

    ★ 왜 필요한가 — 이 판정기가 재는 다섯 수는 **한 자리에 다 있지 않다.**
      호스트에는 도커가 있고 Django 가 없다. 컨테이너에는 Django 가 있고 도커가 없다.
      둘을 안 이으면 어느 자리에서 돌려도 회색 셋이 남고, **언제나 회색인 판정기는
      아무 말도 하지 않는 판정기**다 (D-301 의 반대쪽 함정).

    ⚠ 위임한 수는 **위임한 수라고 적는다** — 어느 기계에서 잰 것인지 되짚을 수 있어야 한다.
    """
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    cmd = ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings", name,
           "python", "/repo/scripts/verify_retention_declared.py",
           "--json", "--no-docker"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=900, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        say(f"{TAG} [환경] 컨테이너 {name!r} 에 위임하지 못했다: {type(exc).__name__}")
        return None
    line = ""
    for row in (p.stdout or "").splitlines():
        if row.startswith(f"{TAG} JSON "):
            line = row[len(f"{TAG} JSON "):]
    if not line:
        say(f"{TAG} [환경] 컨테이너 {name!r} 가 수를 내지 않았다 — ①②⑥은 회색으로 둔다")
        return None
    try:
        data = json.loads(line)
    except ValueError:
        return None
    say(f"{TAG} [위임] Django 칸 ①②⑥ 은 컨테이너 {name!r} 이 쟀다 "
        f"(이 기계에는 Django 가 없다)")
    keep = ("purge_calls_undeclared", "purge_calls_declared",
            "backup_calls_undeclared", "purge_verdict_undeclared",
            "purge_verdict_declared", "backup_verdict_undeclared",
            "sweep_verdict_undeclared", "sweep_calls_undeclared",
            "purge_audit_undeclared", "audit_declared_days", "audit_source")
    out = {k: data[k] for k in keep if k in data}
    out["django_measured_in"] = name
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ③ 백업 파일이 **실재하는가** — 도커로 볼륨을 들여다본다
# ═══════════════════════════════════════════════════════════════════════════
def count_backup_files(say):
    """`(개수, 사유)`. `None` 은 **못 쟀다**이지 0 이 아니다."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from ops_backup_volume import DEST_VOLUME, MOUNT_PATH
    except Exception:                                          # noqa: BLE001
        DEST_VOLUME, MOUNT_PATH = "gx_backup_vault_e", "/backup"

    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    try:
        p = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{DEST_VOLUME}:{MOUNT_PATH}:ro",
             "postgres:latest", "sh", "-c",
             f"ls -1 {MOUNT_PATH}/*.dump 2>/dev/null | wc -l"],
            capture_output=True, text=True, errors="replace", timeout=300, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"도커를 부르지 못했다: {type(exc).__name__}"
    if p.returncode != 0:
        return None, f"백업 볼륨 {DEST_VOLUME!r} 를 못 봤다"
    text = (p.stdout or "").strip().splitlines()
    n = int(text[-1]) if text and text[-1].strip().isdigit() else None
    return n, f"볼륨 {DEST_VOLUME}:{MOUNT_PATH}"


# ═══════════════════════════════════════════════════════════════════════════
# ④ 복구 시험 기록 — 호스트·컨테이너 둘 다 읽는다
# ═══════════════════════════════════════════════════════════════════════════
def read_restore_record(root: Path):
    for rel in RESTORE_EVIDENCE:
        path = Path(rel) if rel.startswith("/") else root / rel
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rto = data.get("rto_minutes")
        src, got = data.get("tables_source"), data.get("tables_restored")
        ok = bool(got) and got == src
        return {"restore_records": 1, "restore_rto_minutes": rto,
                "restore_ok": ok, "restore_path": str(path),
                "restore_target": data.get("target_db")}
    return {"restore_records": None}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="P-67 보존·백업 선언 — 미선언이면 안 돈다 · 선언이면 파일이 있다")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-django", action="store_true",
                    help="Django 칸을 아예 재지 않는다(회색으로 남는다)")
    ap.add_argument("--no-docker", action="store_true",
                    help="도커를 아예 안 부른다(컨테이너 안에서 부를 때)")
    ap.add_argument("--via-container", default="gx-shell",
                    help="Django 칸을 대신 재 줄 컨테이너. 빈 값이면 위임하지 않는다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    root = repo_root()
    facts: dict = {}
    lines: list = []

    def say(line: str) -> None:
        print(line)
        lines.append(line)

    hits, read = scan_defaults(root)
    facts["default_hits"] = hits
    facts["files_scanned"] = read
    envs = scan_seed_is_env_locked(root)
    facts["seed_environments"] = envs

    if not args.no_django:
        collect_django(facts, say)
        #: ★ 여기서 **위임한다** — 호스트에는 Django 가 없고 컨테이너에는 도커가 없다.
        #:   위임하지 않으면 어느 자리에서 돌려도 **언제나 회색**이고, 언제나 회색인
        #:   판정기는 아무 말도 하지 않는 판정기다. 위임한 사실을 숨기지 않고 적는다.
        if facts.get("purge_calls_undeclared") is None and not args.no_docker                 and args.via_container:
            got = collect_django_via_container(args.via_container, say)
            if got:
                facts.update(got)

    if args.no_docker:
        facts["backup_files"] = None
        facts["backup_where"] = "도커를 안 불렀다(--no-docker)"
    else:
        n, why = count_backup_files(say)
        facts["backup_files"] = n
        facts["backup_where"] = why

    facts.update(read_restore_record(root))

    say(f"{TAG} [입력] 저장소 {root} · 정적 검사 파일 {read}/{len(ENFORCEMENT_FILES)} · "
        f"백업 자리 {facts.get('backup_where')} · "
        f"복구 기록 {facts.get('restore_path', '못 찾았다')}")
    if envs is None:
        say(f"{TAG} X  선언 시드가 환경으로 안 잠겼다 — `{SEED_FILE}` 의 "
            f"`DECLARED_ENVIRONMENTS` 를 못 읽었다. 잠기지 않은 선언은 기본값이다")
        facts["seed_locked"] = False
    else:
        locked = "production" not in envs
        facts["seed_locked"] = locked
        say(f"{TAG} {'  ' if locked else 'X '}선언 시드 잠금            "
            + (f"{envs} — 운영은 한 칸도 안 읽는다" if locked else
               "**운영이 시드를 읽는다** — 그것은 선언이 아니라 기본값이다"))

    rc, undecidable = EXIT_OK, []
    for name, ok, why in judge(facts):
        mark = "  " if ok else ("? " if "판정 불가" in why else "X ")
        say(f"{TAG} {mark}{name:24} {why}")
        if not ok:
            if "판정 불가" in why:
                undecidable.append(name)
            else:
                rc = EXIT_FAIL
    if facts.get("seed_locked") is False:
        rc = EXIT_FAIL

    if args.json:
        say(f"{TAG} JSON " + json.dumps(facts, ensure_ascii=False, sort_keys=True,
                                        default=str))
    if rc == EXIT_FAIL:
        say(f"{TAG} 실패 — 위의 X 가 아직 「아무도 정하지 않은 수」가 도는 자리다")
        return EXIT_FAIL
    if undecidable:
        say(f"{TAG} **판정 불가(exit 2)** — 잰 칸은 통과했으나 못 잰 칸이 있다: "
            + " · ".join(undecidable)
            + ". 머리말의 두 명령을 **둘 다** 돌려야 다섯이 채워진다. "
              "못 잰 것을 초록으로 적지 않는다")
        return EXIT_UNDECIDABLE
    say(f"{TAG} 통과 — 미선언이면 파기·백업이 돌지 않고, 선언하면 파일이 실재하고, "
        f"복구는 해 봤고 RTO 를 쟀다. 코드에 보존 일수 기본값은 없다")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
