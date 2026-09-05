#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-57 — **「지운다」는 「그대로 지운다」다** (파기 판정기 · 2026-09-05 · 차선 E).

    "판정 P-57: **파기 = 하드 삭제 + 객체(스냅샷) 삭제 + 파기 기록(감사).**
     `verify_purge.py`: 보존 만료 시드 1건 → 행 0 · 객체 0 · 파기 기록 1"
                                                        — 지시서 §2 P-57

무엇을 재는가 — **여섯 수**
---------------------------
    ① 만료 시드 1건을 파기하면 **행 0**   ← 「지움」 표시가 아니라 행이 없어야 한다
    ② 그 행이 가리키던 **객체 0**         ← 바이트가 저장소에서 사라져야 한다
    ③ **파기 기록 1**                     ← 부름 하나에 감사 한 줄
    ④ 안 만료된 시드는 **남는다**         ← 「지킨다」와 「다 버린다」를 가른다
    ⑤ 보존 일수 **미선언 테넌트는 0건**   ← 선언이 먼저다 (지시서 §4 함정 ㉡)
    ⑥ 인자 없이 부르면 **0건**            ← 되돌릴 수 없는 일의 기본값은 dry-run (D-209)

★ ④⑤⑥ 이 초록의 절반이다. 다 지우는 함수는 ①②③ 을 언제나 통과한다.

★ **출생 표본** (D-310) — 이 도구를 만들게 한 사례
--------------------------------------------------
합성이 아니다. [실측 2026-09-05 · gx-shell · test DB · `stream_monitors.EventClip` 1행]

    clip.delete()  →  _base_manager 1 · all_objects 1 · deleted_objects 1 · objects 1

즉 **`delete()` 를 불렀는데 행이 남아 있었다.** dj-core `BaseModel` 이
`SafeDeleteModel(SOFT_DELETE_CASCADE)` 이기 때문이다 [실측 core/base.py:2059].
보존 기간을 약속해 놓고 표시만 하면 그것은 **지운 척**이고, 평범한 조회에서 똑같이
안 보이므로 **아무도 모른다** — 그 상태가 아래 `self_test()` 의 `birth` 다.

★ **되돌릴 수 없다** — 이 도구가 지키는 셋
------------------------------------------
    ㉠ 자기가 심은 시드만 지운다. **한 트랜잭션 안에서 재고 반드시 되돌린다** —
      되돌리지 못하면 그 자리에서 **회색(exit 2)** 이지 초록이 아니다.
    ㉡ 심는 표가 **공용 마스터면 멈춘다**(D-270 ③). 못 확인해도 멈춘다.
    ㉢ 객체는 이 도구가 **올린 것만** 지운다. 접두는 `PROBE_PREFIX` 하나다.

★ 객체를 못 재는 환경 — **실패 갈래를 대신 재고 「판정 불가」로 적는다**
-----------------------------------------------------------------------
이 환경의 기본 설정은 `MINIO_ENDPOINT=minio.invalid` 라 바이트가 사라지는 것을
못 잰다. 그때 ②는 **`None`(못 쟀다)** 이고 0이 아니다 — 그리고 도구는 대신
**실패 갈래**를 잰다: 「바이트를 못 지웠으면 행을 남기는가」. 그 갈래가 빨가면
그것은 판정 불가가 아니라 **실패**다(고아 영상이 생긴다).

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/verify_purge.py
    # 객체까지 재려면 저장소를 주고 돌린다 (뿌리 .env 의 MinIO 자격증명)
    docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
        -e MINIO_ENDPOINT=minio:9000 -e MINIO_ACCESS_KEY=... \
        -e MINIO_SECRET_KEY=... gx-shell python /repo/scripts/verify_purge.py
    python scripts/verify_purge.py --self-test    # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음 · 안 되돌아갔음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 이 도구가 올리는 객체의 접두. **이 접두 밖의 바이트는 건드리지 않는다.**
PROBE_PREFIX = "gx-purge-probe/"

#: 시드를 얼마나 과거로 미는가. 어떤 보존 일수를 선언해도 만료되게 넉넉히 민다.
SEED_AGE_DAYS = 999

#: 시드가 선언하는 보존 일수. `retention.DEFAULT_RETENTION_DAYS` 와 무관하게
#: **이 도구가 명시적으로 선언한다** — 선언 없는 파기를 재는 도구가 아니다.
PROBE_RETENTION_DAYS = 30


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔 이유는 시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list:
    """여섯 수를 판정한다. `(이름, 통과, 사유)` 여섯.

    ★ `None` 은 **못 쟀다**이지 0 이 아니다 (D-301). 못 잰 칸은 통과가 아니다 —
      단 ②(객체)만은 예외로 `object_store` 가 거짓이면 **판정 불가**로 따로 샌다.
      그 구분은 `main()` 이 종료 코드로 옮긴다.
    """
    out: list = []

    n = counts.get("rows_after")
    if n is None:
        out.append(("만료 시드 → 행 0", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("만료 시드 → 행 0", n == 0,
                    f"{n}행" + ("" if n == 0 else
                                " — **지운 척이다.** delete() 가 행에 「지움」 표시만 "
                                "하고 행을 남겼다(출생 표본과 같은 상태)")))

    n = counts.get("objects_after")
    if n is None:
        out.append(("그 행의 객체 → 0", False,
                    "**판정 불가** — 객체저장소에 닿지 못했다. 「0」이 아니다(D-301)"))
    else:
        out.append(("그 행의 객체 → 0", n == 0,
                    f"{n}개" + ("" if n == 0 else
                                " — 행은 지웠는데 바이트가 남았다. 가리키는 것이 "
                                "없는 영상이 저장소에 영원히 남는다")))

    n = counts.get("purge_records")
    if n is None:
        out.append(("파기 기록 → 1", False, "**못 쟀다** — 감사 표를 읽지 못했다"))
    else:
        out.append(("파기 기록 → 1", n == 1,
                    f"{n}건" + ("" if n == 1 else
                                " — 「지웠다」와 「원래 없었다」가 같은 상태가 됐다"
                                if n == 0 else
                                " — 한 번의 파기가 여러 줄이 됐다. 전건 집계가 갈린다")))

    n = counts.get("fresh_rows_after")
    if n is None:
        out.append(("안 만료 시드는 남는다", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("안 만료 시드는 남는다", n == 1,
                    f"{n}행" + ("" if n == 1 else
                                " — **「지킨다」가 아니라 「다 버린다」이다.** "
                                "보존기간을 보지 않고 지웠다")))

    n = counts.get("undeclared_rows_after")
    if n is None:
        out.append(("미선언 테넌트 → 0건 파기", False,
                    "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("미선언 테넌트 → 0건 파기", n == 1,
                    f"남은 행 {n}" + ("" if n == 1 else
                                      " — **선언하지 않은 테넌트의 영상을 지웠다.** "
                                      "제품 기본값 30일이 남의 자료에 대한 파기 "
                                      "명령이 됐다 (지시서 §4 함정 ㉡)")))

    n = counts.get("dry_run_deleted")
    default_is_dry = counts.get("dry_run_default")
    if n is None or default_is_dry is None:
        out.append(("기본값은 dry-run → 0건", False,
                    "**못 쟀다** — 기본값을 확인하지 못했다"))
    else:
        ok = (n == 0) and bool(default_is_dry)
        out.append(("기본값은 dry-run → 0건", ok,
                    f"기본값 dry_run={default_is_dry} · 지운 건수 {n}"
                    + ("" if ok else
                       " — 되돌릴 수 없는 일의 기본값이 「한다」이면 그것은 "
                       "기본값이 아니라 함정이다 (D-209)")))
    return out


def orphan_branch_ok(counts: dict):
    """객체를 못 지웠을 때 **행을 남기는가.** `None` 이면 안 재 봤다.

    ★ 객체저장소에 못 닿는 환경에서 ②를 대신하는 갈래다(머리말). 이쪽이 빨가면
      그것은 판정 불가가 아니라 **실패**다 — 가리키는 것이 없는 영상이 남는다.
    """
    kept = counts.get("orphan_row_kept")
    reported = counts.get("orphan_failure_reported")
    if kept is None or reported is None:
        return None
    return bool(kept) and bool(reported)


def self_test() -> int:
    """판정 규칙을 스스로 시험한다. **Django 없이 돈다** (D-277 · D-350)."""
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    green = dict(rows_after=0, objects_after=0, purge_records=1,
                 fresh_rows_after=1, undeclared_rows_after=1,
                 dry_run_deleted=0, dry_run_default=True)

    # ── 출생 표본 — **`delete()` 를 불렀는데 행이 남아 있었다** ────────────
    #    [실측 2026-09-05 · EventClip 1행] 소프트 삭제라 행이 남고, 객체는 그
    #    행이 살아 있으니 지워지지도 않았고, 파기 기록도 없었다. 그날의 수다.
    birth = dict(green, rows_after=1, objects_after=1, purge_records=0)
    got = names(judge(birth))
    if got.get("만료 시드 → 행 0"):
        bad.append("**출생 표본**(delete() 를 불렀는데 행이 남은 상태)을 통과로 "
                   "읽는다 — 이 판정기가 태어난 이유를 못 본다 (D-310)")
    if got.get("파기 기록 → 1"):
        bad.append("출생 표본에서 파기 기록 0을 통과로 읽는다 — 「지웠다」와 "
                   "「원래 없었다」가 같은 상태다")
    if not got.get("안 만료 시드는 남는다"):
        bad.append("출생 표본에서 부작위 갈래까지 빨갛게 읽는다 — 그날 안 만료 행이 "
                   "남은 것은 사실이었다. 판정기가 사실을 틀렸다고 말하면 안 된다")

    # ── 초록 표본 ────────────────────────────────────────────────────────
    if not all(names(judge(green)).values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {names(judge(green))}")

    # ── 음성 갈래 — 하나씩 무너뜨린다 ────────────────────────────────────
    for key, value, expect_red in (
        ("rows_after", 1, "만료 시드 → 행 0"),
        ("objects_after", 1, "그 행의 객체 → 0"),
        ("purge_records", 0, "파기 기록 → 1"),
        ("purge_records", 2, "파기 기록 → 1"),        # 많아도 틀린 수다
        ("fresh_rows_after", 0, "안 만료 시드는 남는다"),
        ("undeclared_rows_after", 0, "미선언 테넌트 → 0건 파기"),
        ("dry_run_deleted", 1, "기본값은 dry-run → 0건"),
        ("dry_run_default", False, "기본값은 dry-run → 0건"),
    ):
        sample = dict(green, **{key: value})
        if names(judge(sample)).get(expect_red):
            bad.append(f"{key}={value} 인데 「{expect_red}」를 통과로 읽는다")

    # ── **다 지우는 함수**를 통과시키지 않는가 (초록의 절반) ──────────────
    #    ①②③ 은 만족하는데 ④⑤ 가 무너진 상태다. 이것을 통과시키면 이 판정기는
    #    「기간을 지킨다」가 아니라 「다 버린다」에 초록을 준다.
    deletes_everything = dict(green, fresh_rows_after=0, undeclared_rows_after=0)
    got = names(judge(deletes_everything))
    if got.get("안 만료 시드는 남는다") or got.get("미선언 테넌트 → 0건 파기"):
        bad.append("**다 지우는 함수**를 통과로 읽는다 — 그것은 보존기간 집행이 "
                   "아니라 전량 폐기다")

    # ── 못 쟀다 ≠ 0 ─────────────────────────────────────────────────────
    rows = judge(dict(green, objects_after=None))
    hit = [(n, ok, why) for (n, ok, why) in rows if n.startswith("그 행의 객체")][0]
    if hit[1] or "판정 불가" not in hit[2]:
        bad.append("객체를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")
    rows = judge(dict(green, rows_after=None))
    hit = [(n, ok, why) for (n, ok, why) in rows if n.startswith("만료 시드")][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("행을 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")

    # ── 고아 갈래 ────────────────────────────────────────────────────────
    if orphan_branch_ok({}) is not None:
        bad.append("안 재 본 고아 갈래를 판정으로 읽는다")
    if orphan_branch_ok(dict(orphan_row_kept=False, orphan_failure_reported=True)):
        bad.append("바이트를 못 지웠는데 행을 지운 상태를 통과로 읽는다 — "
                   "그 영상은 이제 고아다")
    if orphan_branch_ok(dict(orphan_row_kept=True, orphan_failure_reported=False)):
        bad.append("못 지운 사실이 응답에 안 남았는데 통과로 읽는다 — 조용한 실패다")
    if not orphan_branch_ok(dict(orphan_row_kept=True, orphan_failure_reported=True)):
        bad.append("고아 갈래의 초록을 초록으로 못 읽는다")

    if bad:
        print("[P-57] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[P-57] 자기시험 통과 — 출생 표본 1 · 초록 표본 1 · 음성 8 · "
          "전량폐기 1 · 판정 불가 2 · 고아 갈래 4")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 쓰기 전에 묻는다 — **공용 마스터에 시드를 심지 않는다** (D-270 ③)
# ═══════════════════════════════════════════════════════════════════════════
def _refuse_if_shared_master(labels, fail) -> None:
    """등록부를 못 읽으면 **통과시키지 않는다** — 「검사 못함」≠「대상 아님」(D-301)."""
    shared = None
    try:
        from tests.tenant_classification import SHARED_MASTERS as shared
    except ImportError:
        import importlib.util

        here = Path(__file__).resolve().parent.parent
        for cand in (here / "backend" / "tests" / "tenant_classification.py",
                     Path("/app") / "tests" / "tenant_classification.py"):
            if not cand.is_file():
                continue
            spec = importlib.util.spec_from_file_location(
                "_tenant_classification", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            shared = mod.SHARED_MASTERS
            break
    if shared is None:
        fail("분류 등록부(tests/tenant_classification.py)를 이름으로도 파일로도 읽지 "
             "못했다 — 공용 마스터인지 확인하지 못한 채로 쓰지 않는다 (D-270 ③)")
        return
    for label in labels:
        if label in shared:
            fail(f"{label} 이 분류 등록부에서 **공용 마스터**다. 측정용 시드를 공용 "
                 f"표에 심으면 되돌리기 전까지 전 테넌트가 그것을 본다")


class _Rollback(Exception):
    """되돌리기 위해 일부러 던지는 예외. **성공 경로에서 던진다** — 실패가 아니다."""


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **한 트랜잭션 안에서 재고 통째로 되돌린다**
# ═══════════════════════════════════════════════════════════════════════════
def _put_probe_object(key: str):
    """시험용 바이트 하나를 올린다. `(bucket, name)` 또는 `None`(못 올렸다)."""
    import io as _io

    try:
        from django.conf import settings

        from stream_monitors.utils.minio_client import minio_client

        bucket = getattr(minio_client, "bucket_name", "") or getattr(
            settings, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        data = b"gx-purge-probe"
        minio_client.client.put_object(bucket, key, _io.BytesIO(data), len(data))
        return bucket, key
    except Exception as exc:                                 # noqa: BLE001
        print(f"[P-57] ⚠ 객체를 못 올렸다: {type(exc).__name__}: {exc} — "
              f"②(객체 0)는 **판정 불가**다")
        return None


def _object_exists(bucket: str, key: str):
    """그 바이트가 아직 있는가. `None` 이면 **못 물어봤다.**"""
    try:
        from stream_monitors.utils.minio_client import minio_client

        minio_client.client.stat_object(bucket, key)
        return True
    except Exception as exc:                                 # noqa: BLE001
        name = type(exc).__name__
        #: S3Error(NoSuchKey) = 「없다」. 그 밖의 예외는 **「못 물어봤다」**다 —
        #: 둘을 뭉치면 저장소가 죽은 것이 「지워졌다」로 읽힌다 (D-290).
        if name == "S3Error" and "NoSuchKey" in str(exc):
            return False
        print(f"[P-57] ⚠ 객체 존재를 못 물어봤다: {name}: {exc}")
        return None


def collect() -> dict:
    """여섯 수 + 고아 갈래를 재고 **되돌린다.**"""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.conf import settings
    from django.db import transaction
    from django.utils import timezone
    from datetime import timedelta

    from apps.dsm import retention

    out = {
        "rows_after": None, "objects_after": None, "purge_records": None,
        "fresh_rows_after": None, "undeclared_rows_after": None,
        "dry_run_deleted": None, "dry_run_default": None,
        "orphan_row_kept": None, "orphan_failure_reported": None,
        "object_store": None, "rolled_back": False,
        "seed_group": None, "audit_id": None,
    }

    #: ⑥ 기본값은 **서명에서** 읽는다 — 「부르는 쪽이 침묵하면 무엇이 되나」다.
    import inspect

    out["dry_run_default"] = (
        inspect.signature(retention.purge).parameters["dry_run"].default is True)

    UserGroup = apps.get_model("user", "UserGroup")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    Record = apps.get_model("stream_monitors", "StreamMonitorRecord")
    AuditLogs = apps.get_model("logger", "AuditLogs")

    tag = uuid.uuid4().hex[:10]
    obj_key = f"{PROBE_PREFIX}{tag}.mp4"
    placed = _put_probe_object(obj_key)
    out["object_store"] = placed is not None

    saved = getattr(settings, retention.TENANT_RETENTION_SETTING, None)
    try:
        with transaction.atomic():
            g_declared = UserGroup._base_manager.create(
                name=f"gx-purge-probe-declared-{tag}")
            g_silent = UserGroup._base_manager.create(
                name=f"gx-purge-probe-undeclared-{tag}")
            out["seed_group"] = g_declared.pk

            cam_d = Stream._base_manager.create(
                name=f"probe-d-{tag}", code=f"probe-d-{tag}",
                ip_source="rtsp://purge.invalid/1", group=g_declared)
            cam_s = Stream._base_manager.create(
                name=f"probe-s-{tag}", code=f"probe-s-{tag}",
                ip_source="rtsp://purge.invalid/2", group=g_silent)

            def _seed(cam, code, *, path="", days=SEED_AGE_DAYS):
                row = Record._base_manager.create(
                    stream_id=str(cam.pk), code=code, object_path=path)
                Record._base_manager.filter(pk=row.pk).update(
                    created_at=timezone.now() - timedelta(days=days))
                return row.pk

            #: ★ 시드 넷. ①②는 만료 + 객체, ④는 안 만료, ⑤는 미선언 테넌트.
            expired = _seed(cam_d, f"expired-{tag}",
                            path=(f"{placed[0]}/{obj_key}" if placed else ""))
            fresh = _seed(cam_d, f"fresh-{tag}", days=0)
            silent = _seed(cam_s, f"silent-{tag}")

            #: **이 도구가 선언한다.** 선언 없는 파기를 재는 도구가 아니다.
            setattr(settings, retention.TENANT_RETENTION_SETTING,
                    {g_declared.pk: PROBE_RETENTION_DAYS})

            #: ⑥ 인자 없이 — 기본값이 무엇을 하는가.
            preview = retention.purge(group_id=g_declared.pk)
            out["dry_run_deleted"] = preview["deleted_total"]

            before_records = AuditLogs._base_manager.filter(
                logger_name=retention.LOGGER_NAME,
                api_name=retention.PURGE_ACTION).count()

            result = retention.purge(
                group_id=g_declared.pk, dry_run=False, actor=None,
                reason="verify_purge — 만료 시드 1건을 그대로 지운다")
            out["audit_id"] = result.get("audit_id")

            out["rows_after"] = Record._base_manager.filter(pk=expired).count()
            out["fresh_rows_after"] = Record._base_manager.filter(pk=fresh).count()
            out["purge_records"] = AuditLogs._base_manager.filter(
                logger_name=retention.LOGGER_NAME,
                api_name=retention.PURGE_ACTION).count() - before_records

            #: ⑤ 미선언 테넌트 — **한 행도 안 지워져야 한다.**
            skipped = retention.purge(
                group_id=g_silent.pk, dry_run=False, actor=None,
                reason="verify_purge — 미선언 테넌트는 대상이 아니다")
            out["undeclared_rows_after"] = Record._base_manager.filter(
                pk=silent).count()
            out["undeclared_verdict"] = skipped["verdict"]

            #: 고아 갈래 — 바이트를 못 지웠을 때 **행을 남기는가.**
            from unittest.mock import patch

            orphan = _seed(cam_d, f"orphan-{tag}",
                           path="gx-bucket/purge-probe/never.mp4")
            with patch.object(retention, "_remove_object",
                              return_value="저장소가 죽었다"):
                orphan_result = retention.purge(
                    group_id=g_declared.pk, dry_run=False, actor=None,
                    reason="verify_purge — 저장소가 죽었을 때")
            out["orphan_row_kept"] = bool(
                Record._base_manager.filter(pk=orphan).exists())
            out["orphan_failure_reported"] = (
                orphan_result["object_failure_total"] >= 1)

            raise _Rollback
    except _Rollback:
        out["rolled_back"] = True
    finally:
        if saved is None:
            if hasattr(settings, retention.TENANT_RETENTION_SETTING):
                delattr(settings, retention.TENANT_RETENTION_SETTING)
        else:
            setattr(settings, retention.TENANT_RETENTION_SETTING, saved)

    #: ② 객체 — **행을 되돌린 뒤에도 바이트는 안 돌아온다.** 그것이 파기다.
    if placed:
        still = _object_exists(*placed)
        out["objects_after"] = None if still is None else (1 if still else 0)
        if still:
            #: 파기가 못 지웠으면 **우리가 치운다** — 우리가 올린 바이트다.
            try:
                from stream_monitors.utils.minio_client import minio_client

                minio_client.client.remove_object(*placed)
                print("[P-57] ⚠ 파기가 객체를 안 지웠다 — 판정기가 치웠다")
            except Exception:                                # noqa: BLE001
                print(f"[P-57] ⚠ 판정기가 올린 객체를 못 치웠다: {placed[1]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="P-57 파기 — 만료 시드 1건 → 행 0 · 객체 0 · 파기 기록 1")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="수를 JSON 으로도 낸다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    # ★ 여기서부터 **쓴다.** 쓰기 전에 분류 등록부에 묻는다 (D-270 ③).
    stop = []
    _refuse_if_shared_master(
        ("user.UserGroup", "stream_monitors.StreamMonitor",
         "stream_monitors.StreamMonitorRecord"), stop.append)
    if stop:
        for why in stop:
            print("[P-57] [분류] " + why)
        return EXIT_UNDECIDABLE

    try:
        counts = collect()
    except Exception as exc:                                 # noqa: BLE001
        print(f"[P-57] **판정 불가** — 환경을 세우지 못했다: "
              f"{type(exc).__name__}: {exc}")
        print("[P-57] 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    print(f"[P-57] [입력] 시드 테넌트 {counts['seed_group']} · 보존 선언 "
          f"{PROBE_RETENTION_DAYS}일 · 시드 나이 {SEED_AGE_DAYS}일 · "
          f"객체저장소 {'닿았다' if counts['object_store'] else '못 닿았다'} · "
          f"되돌림 {'했다' if counts['rolled_back'] else '**못 했다**'}")
    if not counts["rolled_back"]:
        print("[P-57] **회색(exit 2)** — 되돌리지 못했다. 판정기가 남긴 사실 위에서 "
              "낸 초록은 초록이 아니다. 그리고 파기는 되돌릴 수 없다")
        return EXIT_UNDECIDABLE

    rc, undecidable = EXIT_OK, False
    for (name, ok, why) in judge(counts):
        mark = "  " if ok else ("? " if "판정 불가" in why else "X ")
        print(f"[P-57] {mark}{name:24} {why}")
        if not ok:
            if "판정 불가" in why:
                undecidable = True
            else:
                rc = EXIT_FAIL

    orphan = orphan_branch_ok(counts)
    print(f"[P-57] {'  ' if orphan else 'X '}{'고아 갈래 — 바이트를 못 지우면 행을 남긴다':24} "
          + ("행을 남겼고 사유가 응답에 있다" if orphan else
             "**못 쟀다**" if orphan is None else
             "바이트를 못 지웠는데 행을 지웠다 — 그 영상은 고아다"))
    if orphan is False:
        rc = EXIT_FAIL
    elif orphan is None:
        undecidable = True

    if args.json:
        print("[P-57] JSON " + json.dumps(counts, ensure_ascii=False,
                                          sort_keys=True, default=str))
    if rc == EXIT_FAIL:
        print("[P-57] 실패 — 위의 X 가 아직 「지운 척」인 자리다")
        return EXIT_FAIL
    if undecidable:
        print("[P-57] **판정 불가(exit 2)** — 잰 칸은 통과했으나 못 잰 칸이 있다. "
              "객체저장소를 주고 다시 돌린다(머리말의 두 번째 명령). "
              "못 잰 것을 초록으로 적지 않는다")
        return EXIT_UNDECIDABLE
    print("[P-57] 통과 — 만료 시드 1건이 행 0 · 객체 0 · 파기 기록 1 로 사라졌고, "
          "안 만료·미선언은 그대로 남았다")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
