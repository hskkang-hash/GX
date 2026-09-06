#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07b — **파기를 되돌린다** (되돌림 도구 · 2026-09-06 · 턴 H · 차선 E).

    ga_readiness OPS-07b 제목:
      「DB 감사 로그 보존 — 보존 일수를 **선언하고** 파기가 **되돌릴 수 있어야 한다**」

턴 G 가 갚은 것 둘: ① 보존 일수를 **선언했다**(365 · dj-core 가 읽는 그 자리에)
② **미선언이면 안 부른다**(호출 0). 남은 하나가 **되돌림**이고 이 파일이 그것이다.

무엇을 하는가
-------------
    --list                     선언된 저널 자리의 저널을 나열한다
    --journal <경로>           그 저널을 **되돌린다** (기본 dry-run · D-209)
    --journal <경로> --apply   진짜로 되돌린다
    --drill                    **실측 1건** — 심고 · 파기하고 · 되돌리고 · 치운다
    --self-test                도커도 DB 도 없이 도는 판정 규칙만

`--drill` 이 재는 것 — **한 바퀴를 끝까지 돈다**
-----------------------------------------------
    ① 만료된 표본 행을 심는다 (실재 행을 복제해서 심는다 — 합성 더미가 아니다)
    ② `common.ops_audit_purge_beat` 을 **그대로** 부른다 (흉내 내지 않는다.
       그 안에서 저널이 뜨고 dj-core `purge_old_audit_logs` 가 하드 삭제한다)
    ③ 행이 **정말 없어졌는가** — `_base_manager` 로 센다
    ④ 저널로 **되돌린다** — pk 가 돌아오고 **직렬화 지문이 같아야** 한다.
       pk 만 견주면 「행이 있다」까지만 안다. 칸 값이 달라졌으면 그것은
       되돌림이 아니라 다시 쓰기다.
    ⑤ **치운다** — 심은 표본을 하드 삭제한다. 남으면 **exit 1** 이다.
       ⚠ **총 행 수로 판정하지 않는다.** 이 표는 공용 개발 DB 이고 다른 차선이
         지금도 감사 줄을 쓰고 있다 — 실제로 이 드릴이 심은 pk 사이에 남의 pk 가
         끼어들었다[실측 2026-09-06 · 158755 · **158756(남의 행)** · 158757].
         총량 일치를 판정으로 걸면 남이 한 줄 쓸 때마다 이 시험이 빨개진다.
         그것은 되돌림이 실패한 것이 아니라 **잣대가 틀린 것**이다.

★ 되돌릴 수 없는 조치 앞의 규약 (D-002 · D-209)
-----------------------------------------------
  ㉠ `--drill` 은 **개발·스테이징에서만** 돈다. 운영이면 그 자리에서 멈춘다.
  ㉡ 심는 행에는 **표식**(`PROBE_MARKER`)이 들어가고, 치울 때 그 표식이 있는
     행만 지운다. 표식 없이 개수만 세면 남의 행을 내 것으로 지운다.
  ㉢ 파기는 이 스크립트가 직접 하지 않는다 — **제품의 태스크**가 한다.
     여기서 흉내 내면 「제품이 되돌릴 수 있다」가 아니라 「이 스크립트가
     되돌릴 수 있다」를 재게 된다.

종료 코드: 0 됐다 · 1 쟀는데 어긋났다 · 2 **못 쟀다**(장고·DB 없음 · 운영 환경)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 컨테이너에서 `/repo/scripts/*.py` 를 부르면 `config` 가 안 잡힌다 — 앱을 먼저 얹는다.
sys.path.insert(0, "/app")

#: 심는 표본의 표식. 이 낱말이 든 행만 치운다.
PROBE_MARKER = "GX-PROBE-OPS07B"

#: 심는 표본 수. 하나로는 「한 행이 돌아왔다」까지만 알고, 순서·중복을 못 본다.
PROBE_ROWS = 3

#: 이 드릴이 도는 환경. **운영에서는 돌지 않는다.**
DRILL_ENVIRONMENTS = ("development", "staging")


def _say(line: str = "") -> None:
    print(line, flush=True)


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()


# ═══════════════════════════════════════════════════════════════════════════
# 1. 나열 · 되돌림
# ═══════════════════════════════════════════════════════════════════════════
def cmd_list() -> int:
    from pathlib import Path

    from common import audit_purge_journal as J

    where = J.journal_dir()
    if not where:
        _say("[OPS-07b] 저널 자리가 **선언되지 않았다** — "
             "`OPS_BACKUP_DIR` 이 비어 있다. 못 쟀다")
        return EXIT_UNDECIDABLE
    _say(f"[OPS-07b] 저널 자리: {where}")
    _say(f"[OPS-07b] 별도 볼륨인가: {J.journal_dir_is_separate_volume(where)!r}")
    directory = Path(where)
    if not directory.is_dir():
        _say("[OPS-07b] 그 자리가 아직 없다 — 파기가 한 번도 안 돌았다")
        return EXIT_OK
    found = sorted(directory.glob(J.JOURNAL_PREFIX + "*.json"))
    for path in found:
        check = J.verify_journal(str(path))
        _say(f"  {path.name}  {path.stat().st_size:,}바이트  "
             f"sha256 확인={check.get('ok')!r}")
    _say(f"[OPS-07b] 저널 {len(found)}개")
    return EXIT_OK


def cmd_restore(path: str, apply_it: bool) -> int:
    #: ★ 이름을 **가져와서** 부른다. 모듈 별명(`J.restore_journal`)으로만 부르면
    #:   잠자는 기능 래칫(D-377 ㉠)이 이 함수를 「부르는 쪽 없음」으로 센다 —
    #:   그리고 그 판정이 옳다: 되돌림은 **사람이 이 문으로** 부르는 일이다.
    from common.audit_purge_journal import restore_journal, verify_journal

    check = verify_journal(path)
    _say(f"[OPS-07b] 저널 확인 — {check}")
    if check.get("ok") is False:
        _say("[OPS-07b] **되돌리지 않는다** — 저널이 적힌 것과 다르다")
        return EXIT_FAIL
    result = restore_journal(path, dry_run=not apply_it)
    _say(f"[OPS-07b] {'되돌렸다' if apply_it else 'dry-run (아무것도 안 바꿨다)'} — "
         f"저널 {result['in_journal']}행 · 이미 있던 행 {result['already_present']} · "
         f"{'되돌린' if apply_it else '되돌릴'} 행 "
         f"{result['restored'] if apply_it else result['would_restore']}")
    if not apply_it:
        _say("[OPS-07b] 진짜로 되돌리려면 `--apply` 를 붙인다 (D-209)")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 2. 실측 한 바퀴
# ═══════════════════════════════════════════════════════════════════════════
def cmd_drill(evidence: str = "", json_out: str = "") -> int:
    from django.conf import settings

    from common import audit_purge_journal as J
    from common.audit_purge_journal import fingerprint, restore_journal
    from common.ops_tasks import (audit_retention_declared_days,
                                  ops_audit_purge_beat)
    from core.logger.models import AuditLogs

    env_name = getattr(settings, "GUARDIANX_ENVIRONMENT", "")
    if env_name not in DRILL_ENVIRONMENTS:
        _say(f"[OPS-07b] 환경이 {env_name!r} 다 — 이 드릴은 개발·스테이징에서만 "
             "돈다. **못 쟀다**")
        return EXIT_UNDECIDABLE

    declared = audit_retention_declared_days()
    if declared is None:
        _say("[OPS-07b] 보존 일수가 **미선언**이다 — 파기가 돌지 않으므로 "
             "되돌림도 잴 수 없다. `scripts/seed_retention_declaration.py --apply` "
             "가 먼저다. **못 쟀다**")
        return EXIT_UNDECIDABLE

    stamp = datetime.now(timezone.utc)
    facts: dict = {"measured_at": stamp.isoformat(timespec="seconds"),
                   "environment": env_name, "retention_days": declared,
                   "journal_dir": J.journal_dir()}

    # ── 분류 등록부 대조 (D-270 ③) — **되돌리기 전에 이 표가 누구 것인지 묻는다** ──
    #   `logger.AuditLogs` 는 공용 마스터도 미배정도 **아니다** — 테넌트 소유 데이터다
    #   (누가 무엇을 했는지). 그래서 등록부에 이름을 **넣지 않는다**: 그 파일에 모델을
    #   더하는 것은 면제를 늘리는 일이고, 감사 로그는 면제 대상이 아니다.
    #
    #   ★ 그러면 이 스크립트가 확인할 것이 달라진다. 공용 마스터라면 「전 테넌트가
#     보는가」를 물었겠지만, 테넌트 소유 표에서 되돌리기가 지켜야 할 것은
    #   **소유가 그대로 돌아오는가**이다. 되돌리면서 소유 칸이 바뀌면
    #   **남의 감사 로그가 내 것이 된다** — 파기보다 나쁜 사고다.
    import importlib.util as _ilu

    _spec = _ilu.spec_from_file_location(
        "tenant_classification",
        str(Path(__file__).resolve().parents[1] / "backend" / "tests"
            / "tenant_classification.py"))
    _reg = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_reg)
    TARGET_MODEL = "logger.AuditLogs"
    if TARGET_MODEL in _reg.SHARED_MASTERS or TARGET_MODEL in _reg.TENANT_UNASSIGNED:
        _say(f"[OPS-07b] **멈춘다** — {TARGET_MODEL} 이 등록부에 면제로 올라 있다. "
             f"감사 로그가 공용이나 미배정이면 이 되돌리기의 소유 검사가 뜻을 잃는다")
        return EXIT_FAIL
    _say(f"[OPS-07b] 분류 대조 — {TARGET_MODEL} 은 등록부의 면제 둘 중 어디에도 없다 "
         f"= **테넌트 소유**. 되돌림은 소유 칸까지 같아야 한다")

    base = AuditLogs._base_manager
    total_before = base.count()
    _, cutoff = J.expiring_queryset(declared)
    expired_before = base.filter(create_datetime__lt=cutoff).count()
    facts.update({"total_before": total_before,
                  "expired_rows_not_mine": expired_before,
                  "cutoff": cutoff.isoformat()})
    _say(f"[OPS-07b] [입력] 보존 {declared}일 · 표 {total_before:,}행 · "
         f"이미 만료된 행 {expired_before}건 · 저널 자리 {facts['journal_dir']}")

    # ── ① 심는다 — 실재 행을 복제한다(합성 더미가 아니다 · D-289) ──────────
    source = base.order_by("-id").first()
    if source is None:
        _say("[OPS-07b] 감사 로그가 한 행도 없다 — 복제할 표본이 없다. **못 쟀다**")
        return EXIT_UNDECIDABLE

    old_dt = cutoff - timedelta(days=7)
    probe_pks = []
    for index in range(PROBE_ROWS):
        clone = base.get(pk=source.pk)
        clone.pk = None
        clone.id = None
        clone.msg = f"[{PROBE_MARKER}] 되돌림 실측 표본 {index + 1}/{PROBE_ROWS}"
        clone.save()
        probe_pks.append(clone.pk)
    #: `create_datetime` 은 `auto_now_add=True` 라 `save()` 로는 못 옮긴다 —
    #: 큐리셋 `update()` 가 그 자물쇠를 지나간다.
    base.filter(pk__in=probe_pks).update(create_datetime=old_dt)
    fingerprint_before = fingerprint(probe_pks)
    facts.update({"probe_pks": probe_pks, "probe_create_datetime": old_dt.isoformat(),
                  "fingerprint_before": fingerprint_before})
    _say(f"[OPS-07b] ① 심었다 — pk {probe_pks} · create_datetime {old_dt:%Y-%m-%d} "
         f"· 지문 sha256 {fingerprint_before[:16]}…")

    verdicts: list[tuple[str, bool, str]] = []
    try:
        # ── ② 제품의 태스크를 그대로 부른다 ────────────────────────────────
        payload = ops_audit_purge_beat()
        facts["purge_payload"] = payload
        journal_path = (payload.get("journal") or {}).get("path")
        _say(f"[OPS-07b] ② 파기 — 판정 {payload.get('verdict')!r} · "
             f"{payload.get('purged')}건 · 저널 {journal_path}")

        verdicts.append(("① 파기가 돌았는가", payload.get("verdict") == "OK",
                         f"판정 {payload.get('verdict')!r} · "
                         f"{payload.get('reason', '')}"[:200]))
        verdicts.append(("② 저널이 떴는가", bool(journal_path),
                         f"저널 {journal_path}"))

        # ── ③ 행이 정말 없어졌는가 ────────────────────────────────────────
        gone = base.filter(pk__in=probe_pks).count()
        facts["rows_after_purge"] = gone
        verdicts.append(("③ 행이 정말 없어졌는가", gone == 0,
                         f"심은 {len(probe_pks)}행 중 남은 {gone}행"))

        # ── ④ 되돌린다 ────────────────────────────────────────────────────
        restored = {"restored": 0}
        if journal_path:
            restored = restore_journal(journal_path, dry_run=False)
            facts["restore"] = {k: v for k, v in restored.items() if k != "pks"}
        back = base.filter(pk__in=probe_pks).count()
        fingerprint_after = fingerprint(probe_pks) if back else ""
        facts.update({"rows_after_restore": back,
                      "fingerprint_after": fingerprint_after})
        _say(f"[OPS-07b] ④ 되돌렸다 — {restored.get('restored')}행 · "
             f"돌아온 표본 {back}/{len(probe_pks)} · "
             f"지문 sha256 {fingerprint_after[:16]}…")
        verdicts.append(("④ 행이 돌아왔는가", back == len(probe_pks),
                         f"{back}/{len(probe_pks)}행"))
        verdicts.append(("⑤ **같은 행인가** (직렬화 지문 sha256)",
                         bool(fingerprint_after) and
                         fingerprint_after == fingerprint_before,
                         "지문이 같다" if fingerprint_after == fingerprint_before
                         else "지문이 다르다 — 되돌림이 아니라 다시 쓰기다"))
    finally:
        # ── ⑤ 치운다 — 표식이 있는 행만 ───────────────────────────────────
        removed = base.filter(pk__in=probe_pks,
                              msg__contains=PROBE_MARKER).delete()
        left = base.filter(pk__in=probe_pks).count()
        total_after = base.count()
        facts.update({"cleanup_deleted": removed, "probe_rows_left": left,
                      "total_after": total_after})
        _say(f"[OPS-07b] ⑤ 치웠다 — {removed} · 남은 표본 {left}행 · "
             f"표 {total_after:,}행")

    #: ★ **총 행 수로 판정하지 않는다.** 이 표는 공용 개발 DB 이고 다른 차선이
    #:   지금도 감사 줄을 쓰고 있다 — 실제로 이 드릴이 심은 pk 사이에 남의 pk 가
    #:   끼어든다[실측 2026-09-06 · 158755 · **158756(남의 행)** · 158757].
    #:   총량 일치를 판정으로 걸면 **남이 한 줄 쓸 때마다 이 시험이 빨개진다** —
    #:   그것은 되돌림이 실패한 것이 아니라 잣대가 틀린 것이다. 그래서 판정은
    #:   「내가 심은 것이 남지 않았는가」이고, 총량 변화는 **적기만 한다**.
    drift = total_after - total_before
    facts["total_drift_others"] = drift
    verdicts.append(("⑥ 심은 표본이 표에서 사라졌는가", left == 0,
                     f"남은 표본 {left}행 · 표 총량 {total_before:,} → "
                     f"{total_after:,} ({drift:+d} — 이 사이 다른 차선이 쓴 줄이다. "
                     f"판정이 아니라 관찰이다)"))

    _say()
    for name, ok, why in verdicts:
        _say(f"[OPS-07b]   {'OK  ' if ok else 'FAIL'} {name} — {why}")
    passed = all(ok for _, ok, _ in verdicts)
    facts["verdicts"] = [{"name": n, "ok": o, "why": w} for n, o, w in verdicts]
    facts["verdict"] = "OK" if passed else "FAIL"
    _say("[OPS-07b] 통과 — **파기가 되돌려졌다**" if passed
         else "[OPS-07b] 실패 — 위 FAIL 줄이 어긋난 자리다")

    if json_out:
        with open(json_out, "w", encoding="utf-8") as handle:
            json.dump(facts, handle, ensure_ascii=False, indent=2, default=str)
        _say(f"[OPS-07b] 수를 적었다: {json_out}")
    if evidence:
        with open(evidence, "w", encoding="utf-8") as handle:
            handle.write(_evidence_text(facts, verdicts))
        _say(f"[OPS-07b] 증거를 적었다: {evidence}")
    return EXIT_OK if passed else EXIT_FAIL


def _evidence_text(facts: dict, verdicts) -> str:
    lines = [
        "# OPS-07b — **파기를 되돌렸다** (실측 1건 · 턴 H · 차선 E)",
        "",
        "> 이 문서는 `scripts/ops_audit_purge_undo.py --drill` 이 **기계로 적었다.**",
        "",
        f"- 잰 시각(UTC): `{facts.get('measured_at')}`",
        f"- 환경: `{facts.get('environment')}` · 선언된 보존 일수: "
        f"**{facts.get('retention_days')}일**",
        f"- 저널 자리: `{facts.get('journal_dir')}`",
        "",
        "## 수",
        "",
        "| | |",
        "|---|---|",
        f"| 표 (시작) | {facts.get('total_before'):,}행 |",
        f"| 이미 만료돼 있던 남의 행 | {facts.get('expired_rows_not_mine')}건 |",
        f"| 심은 표본 | {len(facts.get('probe_pks') or [])}행 "
        f"(`create_datetime` {str(facts.get('probe_create_datetime'))[:10]}) |",
        f"| 파기 판정 | `{(facts.get('purge_payload') or {}).get('verdict')}` · "
        f"{(facts.get('purge_payload') or {}).get('purged')}건 |",
        f"| 저널 파일 | `{((facts.get('purge_payload') or {}).get('journal') or {}).get('path')}` |",
        f"| 저널 sha256 | `{((facts.get('purge_payload') or {}).get('journal') or {}).get('sha256')}` (sha256 값) |",
        f"| 파기 뒤 남은 표본 | {facts.get('rows_after_purge')}행 |",
        f"| 되돌린 뒤 돌아온 표본 | {facts.get('rows_after_restore')}행 |",
        f"| 직렬화 지문 (전) | `{facts.get('fingerprint_before')}` (sha256 값) |",
        f"| 직렬화 지문 (후) | `{facts.get('fingerprint_after')}` (sha256 값) |",
        f"| 표 (끝) | {facts.get('total_after'):,}행 "
        f"({facts.get('total_drift_others'):+d} — 이 사이 **다른 차선이 쓴 줄**이다. "
        f"판정이 아니라 관찰이다) |",
        "",
        "## 판정",
        "",
    ]
    for name, ok, why in verdicts:
        lines.append(f"- {'**OK**' if ok else '**FAIL**'} {name} — {why}")
    lines += [
        "",
        "## 이 실측이 **말하지 않는 것**",
        "",
        "1. **저널이 있어야 되돌아온다.** 저널을 뜨기 전에 지워진 행은 이 도구로도",
        "   못 되돌린다 — 그래서 `ops_audit_purge_beat` 은 저널을 못 뜨면",
        "   dj-core 를 **부르지 않는다**(`SKIPPED_UNREVERSIBLE` · 호출 0).",
        "2. **저널이 사는 볼륨이 죽으면 되돌림도 죽는다.** 저널은 백업과 같은",
        "   볼륨(`/backup`)에 있고, 그 볼륨은 **같은 기계 안**이다(OPS-12a 미완).",
        "3. 저널은 **평문 JSON** 이다 — 감사 로그의 사용자명·IP 가 그대로 들어 있다.",
        "   그 자리는 백업과 같은 취급을 받아야 한다(D-204).",
        "4. 이것은 **감사 로그 표 하나**의 되돌림이다. 다른 표의 파기(영상·스냅샷)는",
        "   여기서 재지 않았다.",
        "",
    ]
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# 3. 자기시험 — 판정 규칙만
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    """DB 없이 도는 것만 시험한다. 0 통과 · 1 실패."""
    import hashlib
    import tempfile
    from pathlib import Path

    failures = []

    #: ㉠ sha256 곁파일이 맞으면 통과 · 틀리면 거부 · 없으면 **못 쟀다**
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "audit_purge_x.json"
        target.write_text("[]", encoding="utf-8")
        digest = hashlib.sha256(b"[]").hexdigest()

        sys.path.insert(0, "/app")
        from common import audit_purge_journal as J

        got = J.verify_journal(str(target))
        if got.get("ok") is not None:
            failures.append("① 곁파일이 없는데 참·거짓을 답했다 (못 쟀다여야 한다)")

        target.with_suffix(".json.sha256").write_text(
            f"{digest}  {target.name}\n", encoding="utf-8")
        if J.verify_journal(str(target)).get("ok") is not True:
            failures.append("② 맞는 sha256 을 거부했다")

        target.with_suffix(".json.sha256").write_text(
            "0" * 64 + f"  {target.name}\n", encoding="utf-8")
        if J.verify_journal(str(target)).get("ok") is not False:
            failures.append("③ 틀린 sha256 을 통과시켰다")

        if J.verify_journal(str(Path(tmp) / "없다.json")).get("ok") is not False:
            failures.append("④ 없는 파일을 통과시켰다")

    rc = J.self_test()
    if rc != 0:
        failures.append("⑤ audit_purge_journal.self_test 가 실패했다")

    for line in failures:
        _say("  실패 — " + line)
    _say("[OPS-07b] 자기시험 %s (5갈래)" % ("통과" if not failures else "실패"))
    return EXIT_FAIL if failures else EXIT_OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="OPS-07b 감사 로그 파기 되돌림")
    parser.add_argument("--list", action="store_true", help="저널을 나열한다")
    parser.add_argument("--journal", default="", help="되돌릴 저널 파일")
    parser.add_argument("--apply", action="store_true",
                        help="진짜로 되돌린다 (기본은 dry-run · D-209)")
    parser.add_argument("--drill", action="store_true", help="실측 한 바퀴")
    parser.add_argument("--evidence", default="", help="증거 문서 경로")
    parser.add_argument("--json", dest="json_out", default="", help="수 JSON 경로")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    try:
        _setup_django()
    except Exception as exc:                                # noqa: BLE001
        _say(f"[OPS-07b] 장고를 세우지 못했다 — **못 쟀다**: "
             f"{type(exc).__name__}: {exc}")
        return EXIT_UNDECIDABLE

    if args.list:
        return cmd_list()
    if args.journal:
        return cmd_restore(args.journal, args.apply)
    if args.drill:
        return cmd_drill(args.evidence, args.json_out)
    parser.print_help()
    return EXIT_UNDECIDABLE


if __name__ == "__main__":
    raise SystemExit(main())
