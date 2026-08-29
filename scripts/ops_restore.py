#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""운영 기반 ② — **복구.** 백업에서 실제로 살아나는지 해 본다 (D-354 ①).

    **복구를 해 보지 않은 백업은 백업이 아니다.**
    「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.**

무엇을 하나 — 넷
----------------
  ① 대조표(manifest)를 읽고, 그 대조표로 **판정이 가능한지** 먼저 본다
     (행 수가 없으면 복구가 됐는지 알 수 없다 — 그런 백업은 판정 불가로 끝난다)
  ② **임시 DB** 를 만들어 거기에 복구한다
  ③ 증인 표의 행 수를 대조표와 **맞춰 본다** — 하나라도 어긋나면 실패
  ④ 임시 DB 를 지운다. 그리고 **쓴 명령을 그대로 남긴다** (사람이 재현할 수 있게)

★ 원본을 건드리지 않는다 — 세 겹으로 막는다
--------------------------------------------
  · 복구 대상 이름이 원본과 같으면 **시작하지 않는다**
  · 복구 대상 이름은 `restore_check_` 로 시작해야 한다 (다른 이름을 주면 거부)
  · 끝나면 지운다. 실패해도 지운다 (`finally`)
  운영 서버·운영 DB 는 직접 건드리지 않는다(불변 제약). 이 스크립트는 **DB 옆에
  새 DB 를 만들었다 지우는 것**이고, 원본에는 쓰기 연결을 열지 않는다.

★ 어디서 복구하는가 — 클라이언트 판이 서버 판과 맞아야 한다
------------------------------------------------------------
`ops_backup.py` 머리말 참조. `--via docker:postgres` 로 DB 컨테이너 안의 클라이언트를 쓴다.

    python scripts/ops_restore.py --via docker:postgres \
        --manifest docs/agent/evidence/D-354/backup/manifest.json \
        --evidence docs/agent/evidence/D-354/restore_run.md
    python scripts/ops_restore.py --self-test
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_backup import _run, _transport  # noqa: E402  — 술어를 두 벌 두지 않는다

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 임시 DB 이름의 앞머리. 이걸로 시작하지 않는 이름에는 복구하지 않는다.
SCRATCH_PREFIX = "restore_check_"


def guard(target: str, source: str) -> str | None:
    """복구 대상이 안전한가. 안전하지 않으면 사유를 돌려준다.

    ★ 이 함수가 이 스크립트에서 가장 중요한 열 줄이다.
      복구 스크립트가 원본을 덮으면, 그건 백업이 아니라 **사고를 부르는 도구**다.
    """
    if not target:
        return "복구 대상 이름이 비었다"
    if target == source:
        return "복구 대상이 원본과 같다 (%s) — 원본을 덮을 뻔했다" % target
    if not target.startswith(SCRATCH_PREFIX):
        return "복구 대상 이름이 «%s» 로 시작하지 않는다: %s" % (SCRATCH_PREFIX, target)
    return None


def compare_rows(expected: dict, actual: dict) -> list[str]:
    """대조표와 복구본의 행 수를 맞춘다. 어긋난 것들을 돌려준다.

    ★ 대조표에서 `None`(그 표가 없었다) 인 칸은 **비교하지 않는다** —
      없던 표가 복구본에도 없는 것은 어긋남이 아니다.
    """
    out = []
    for table, want in (expected or {}).items():
        if want is None:
            continue
        got = (actual or {}).get(table)
        if got != want:
            out.append("%s: 백업 %s → 복구 %s" % (table, want, got))
    return out


def _sql(dbname: str, sql: str, via: str) -> tuple[int, str]:
    """`psql` 로 한 문장. 파이썬이 없는 DB 컨테이너에서도 돌아야 하므로 CLI 를 쓴다."""
    prefix, container = _transport(via)
    host = "localhost" if container else os.environ.get("DB_HOST", "localhost")
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
    proc = _run(prefix, ["psql", "-tAq", "-h", host, "-p", os.environ.get("DB_PORT", "5432"),
                         "-U", os.environ.get("DB_USER", "postgres"), "-d", dbname,
                         "-c", sql], env)
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def _row_counts(dbname: str, tables, via: str) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for table in tables:
        code, value = _sql(dbname, 'SELECT COUNT(*) FROM "%s"' % table, via)
        out[table] = int(value) if code == 0 and value.isdigit() else None
    return out


def self_test() -> int:
    """★ 출생 표본 — **원본을 덮으려는 복구**를 막는가."""
    checks = [
        ("★ 출생표본 — 원본과 같은 이름이면 시작하지 않는다",
         guard("database_guardianx", "database_guardianx") is not None),
        ("★ 임시 이름이 아니면 거부한다",
         guard("some_other_db", "database_guardianx") is not None),
        ("임시 이름이면 통과한다",
         guard("restore_check_20260909", "database_guardianx") is None),
        ("빈 이름은 거부한다", guard("", "database_guardianx") is not None),
        ("행 수가 같으면 어긋남 0", compare_rows({"a": 3, "b": 0}, {"a": 3, "b": 0}) == []),
        ("★ 행 수가 다르면 잡는다 — 파일이 생긴 것은 복구가 아니다",
         compare_rows({"a": 3}, {"a": 2}) != []),
        ("복구본에 표가 없으면 잡는다", compare_rows({"a": 3}, {}) != []),
        ("백업 때 없던 표(None)는 어긋남으로 세지 않는다",
         compare_rows({"a": None}, {"a": None}) == []),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[OPS-RESTORE] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_FAIL if bad else EXIT_OK


#: ★ 복구가 **써도 되는** 버킷의 접두어. 원본 버킷에는 절대 쓰지 않는다.
#:   DB 복구가 `gx_restore_*` 임시 DB 로만 가는 것과 **같은 규약**이다 —
#:   복구 예행이 원본을 덮으면 그것은 예행이 아니라 사고다.
RESTORE_BUCKET_PREFIX = "gx-restore-"


def restore_objects(manifest: dict, backup_dir: Path) -> dict:
    """★ **객체를 실제로 되살린다** (D-356 ③).

    「복구를 해 보지 않은 백업은 백업이 아니다」 — DB 에 적용한 그 규정을 영상에도
    그대로 적용한다. 그리고 DB 때와 같이 **원본에는 쓰지 않는다**: 새 버킷을 만들어
    거기에 올리고, **해시로 대조**한 뒤 그 버킷을 지운다.

    ★ 왜 해시인가 — 「파일이 생겼다」는 성공이 아니다(D-354 ①). 0바이트 파일도 생긴다.
      바이트가 **그때 그 바이트인지**를 재는 것만이 복구 판정이다.
    """
    import hashlib

    from minio import Minio

    obj_info = manifest.get("objects") or {}
    if obj_info.get("unreachable"):
        raise RuntimeError("대조표에 객체가 '닿지 못함' 으로 적혀 있다 — 뜬 것이 없다")

    endpoint = os.environ.get("MINIO_ENDPOINT", "")
    if not endpoint:
        raise RuntimeError("MINIO_ENDPOINT 가 비었다")
    client = Minio(
        endpoint.replace("http://", "").replace("https://", ""),
        access_key=os.environ.get("MINIO_ACCESS_KEY", ""),
        secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
        secure=endpoint.startswith("https"),
    )
    source_bucket = obj_info.get("bucket", "")
    target_bucket = RESTORE_BUCKET_PREFIX + datetime.now(timezone.utc).strftime(
        "%Y%m%d%H%M%S")
    if source_bucket.startswith(RESTORE_BUCKET_PREFIX):
        raise RuntimeError(
            "원본 버킷 이름이 복구 접두어로 시작한다 — 예행 버킷을 원본으로 뜬 것이다")

    files = sorted((backup_dir / "objects").glob("*"))
    keys = list(obj_info.get("keys") or [])
    commands = [
        "# 복구는 **새 버킷**으로만 간다 — 원본에는 쓰지 않는다",
        f"mc mb {target_bucket}",
        f"mc cp --recursive {backup_dir / 'objects'}/ {target_bucket}/",
    ]

    client.make_bucket(target_bucket)
    restored = matched = 0
    mismatched: list[str] = []
    try:
        for key in keys:
            flat = backup_dir / "objects" / key.replace("/", "_")
            if not flat.is_file():
                mismatched.append(f"{key}: 백업 파일이 없다")
                continue
            data = flat.read_bytes()
            client.put_object(target_bucket, key, io.BytesIO(data), len(data))
            restored += 1

            # ★ 원본과 **바이트로** 대조한다. 되살린 것이 그때 그것인가.
            back = client.get_object(target_bucket, key).read()
            origin = client.get_object(source_bucket, key).read()
            if hashlib.sha256(back).hexdigest() == hashlib.sha256(origin).hexdigest():
                matched += 1
            else:
                mismatched.append(f"{key}: 되살린 바이트가 원본과 다르다")
    finally:
        # 예행이므로 치운다. 남기면 다음 예행이 「이미 있다」로 죽는다.
        for key in keys:
            try:
                client.remove_object(target_bucket, key)
            except Exception:
                pass
        try:
            client.remove_bucket(target_bucket)
            commands.append(f"mc rb --force {target_bucket}")
        except Exception:
            pass

    return {
        "source_bucket": source_bucket,
        "restore_bucket": target_bucket,
        "files_in_backup": len(files),
        "expected": len(keys),
        "restored": restored,
        "hash_matched": matched,
        "mismatched": mismatched,
        "ok": bool(keys) and not mismatched and matched == len(keys),
        "commands": commands,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="docs/agent/evidence/D-354/backup/manifest.json")
    ap.add_argument("--evidence", default="docs/agent/evidence/D-354/restore_run.md")
    ap.add_argument("--via", default="local",
                    help="local | docker:<컨테이너> — pg_restore 를 **어디서** 부를 것인가")
    ap.add_argument("--objects", action="store_true",
                    help="객체저장도 **실제로 되살린다** (D-356 ③). 새 버킷으로만 간다")
    ap.add_argument("--objects-only", action="store_true",
                    help="DB 는 건드리지 않고 객체만 되살린다 — 둘의 클라이언트가 "
                         "사는 자리가 달라 따로 돌게 되는 환경이 있다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print("[OPS-RESTORE] 대조표가 없다: %s — 먼저 ops_backup.py 를 돌려라" % manifest_path)
        return EXIT_FAIL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if args.objects_only:
        # ★ 객체만. **성공·실패를 수로 낸다** — 「했다」로 적지 않는다 (D-301).
        try:
            out = restore_objects(manifest, manifest_path.parent)
        except Exception as exc:
            print("[OPS-RESTORE] 판정 불가 — 객체저장에 닿지 못했다: %s" % str(exc)[:200])
            return EXIT_UNDECIDABLE
        print("[OPS-RESTORE] 객체 복구: 대상 %d개 · 되살림 %d개 · **해시 일치 %d개**"
              % (out["expected"], out["restored"], out["hash_matched"]))
        print("[OPS-RESTORE] 복구 버킷 %s (원본 %s 에는 쓰지 않았다)"
              % (out["restore_bucket"], out["source_bucket"]))
        for line in out["mismatched"]:
            print("[OPS-RESTORE] FAIL — %s" % line)
        evidence = Path(args.evidence)
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(_render_object_evidence(manifest, out), encoding="utf-8")
        print("[OPS-RESTORE] 증거 → %s" % evidence)
        print("[OPS-RESTORE] %s" % ("영상 복구 성공 — 바이트가 원본과 같다"
                                    if out["ok"] else "영상 복구 실패"))
        return EXIT_OK if out["ok"] else EXIT_FAIL

    db = manifest.get("db") or {}
    expected = {k: v for k, v in (db.get("rows") or {}).items()}
    if not db.get("file") or not any(v is not None for v in expected.values()):
        print("[OPS-RESTORE] 판정 불가 — 대조표에 행 수가 없다. "
              "「파일이 생겼다」로는 복구 성공을 판정할 수 없다")
        return EXIT_UNDECIDABLE

    source = (manifest.get("db_settings") or {}).get("name", "")
    target = SCRATCH_PREFIX + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    reason = guard(target, source)
    if reason:
        print("[OPS-RESTORE] 중단 — %s" % reason)
        return EXIT_FAIL

    dump = manifest_path.parent / db["file"]
    if not dump.is_file():
        print("[OPS-RESTORE] 덤프 파일이 없다: %s" % dump)
        return EXIT_FAIL

    prefix, container = _transport(args.via)
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
    host = "localhost" if container else os.environ.get("DB_HOST", "localhost")
    port, user = os.environ.get("DB_PORT", "5432"), os.environ.get("DB_USER", "postgres")

    # 덤프를 pg_restore 가 있는 자리로 보낸다 (컨테이너면 그 안으로).
    remote = "/tmp/" + dump.name if container else str(dump)
    commands: list[str] = []
    if container:
        cp = ["docker", "cp", str(dump), "%s:%s" % (container, remote)]
        if subprocess.run(cp, capture_output=True, text=True).returncode != 0:
            print("[OPS-RESTORE] 덤프를 넣지 못했다: %s" % " ".join(cp))
            return EXIT_FAIL
        commands.append(" ".join(cp))

    restore_argv = ["pg_restore", "--no-owner", "--no-privileges", "-h", host, "-p", port,
                    "-U", user, "-d", target, remote]
    commands += [
        " ".join([*prefix, "psql", "-U", user, "-c", 'CREATE DATABASE "%s"' % target]),
        " ".join([*prefix, *restore_argv]),
        " ".join([*prefix, "psql", "-U", user, "-c", 'DROP DATABASE "%s"' % target]),
    ]

    print("[OPS-RESTORE] 원본 %s → 임시 %s (원본에는 쓰지 않는다)" % (source, target))
    code, msg = _sql("postgres", 'CREATE DATABASE "%s"' % target, args.via)
    if code != 0:
        print("[OPS-RESTORE] 임시 DB 를 만들지 못했다: %s" % msg[:200])
        return EXIT_FAIL

    ok, notes, actual = True, [], {}
    try:
        proc = _run(prefix, restore_argv, env)
        if proc.returncode != 0:
            # pg_restore 는 소유자·권한 경고로도 1 을 낸다. **행 수 대조가 진짜 판정이다.**
            tail = (proc.stderr or "").strip().splitlines()[-1:] or [""]
            notes.append("pg_restore exit=%d · 마지막 줄: %s" % (proc.returncode, tail[0][:160]))
        actual = _row_counts(target, list(expected), args.via)
        mismatch = compare_rows(expected, actual)
        ok = not mismatch
        print("[OPS-RESTORE] 증인 표 대조: " + (" · ".join(
            "%s %s→%s" % (t, expected[t], actual.get(t)) for t in expected) or "(없음)"))
        for m in mismatch:
            print("[OPS-RESTORE] FAIL 어긋남 — %s" % m)
    finally:
        _sql("postgres", 'DROP DATABASE "%s"' % target, args.via)
        if container:
            _run(prefix, ["rm", "-f", remote])
        print("[OPS-RESTORE] 임시 DB 를 지웠다: %s" % target)

    evidence = Path(args.evidence)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(_render_evidence(manifest, target, commands, expected, actual, ok, notes),
                        encoding="utf-8")
    print("[OPS-RESTORE] 증거 → %s" % evidence)
    print("[OPS-RESTORE] %s" % ("복구 성공 — 행 수가 백업과 같다" if ok else "복구 실패"))
    return EXIT_OK if ok else EXIT_FAIL


def _render_evidence(manifest, target, commands, expected, actual, ok, notes) -> str:
    db = manifest.get("db") or {}
    lines = [
        "# 복구 실행 기록 — **해 봤다** (D-354 ①)",
        "",
        "> 「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.** 이 문서는 그 절의 증거다.",
        "> `scripts/ops_restore.py` 가 만든다 — 손으로 적지 않는다.",
        "",
        "| | |",
        "|---|---|",
        "| 실행 시각 | %s |" % datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "| 백업 시각 | %s |" % manifest.get("created_at", "?"),
        "| 원본 DB | `%s` |" % (manifest.get("db_settings") or {}).get("name", "?"),
        "| 복구 대상 | `%s` (임시 · 끝나고 지웠다) |" % target,
        "| 덤프 파일 | `%s` · %s bytes |" % (db.get("file", "?"), db.get("bytes", "?")),
        "| sha256 | `%s` |" % db.get("sha256", "?"),
        "| 뜬 자리 | `%s` · 클라이언트 `%s` |" % (db.get("via", "?"), db.get("client_version", "?")),
        "| 판정 | **%s** |" % ("복구 성공" if ok else "복구 실패"),
        "",
        "## 쓴 명령 — 그대로 재현할 수 있다",
        "",
        "```",
        *[c for c in (db.get("command") or [])],
        *commands,
        "```",
        "",
        "## 증인 표 행 수 대조",
        "",
        "| 표 | 백업 | 복구 |",
        "|---|---:|---:|",
    ]
    for table, want in expected.items():
        lines.append("| `%s` | %s | %s |" % (table, want, (actual or {}).get(table)))
    if notes:
        lines += ["", "## 남은 말", ""] + ["- %s" % n for n in notes]

    obj = manifest.get("objects") or {}
    lines += ["", "## 객체저장 (영상·캡처)", ""]
    if obj.get("unreachable"):
        lines += [
            "**닿지 못했다** — `%s`." % obj.get("endpoint", "?"),
            "",
            "「닿지 못했다」와 「0개다」는 다른 사실이다(D-301). 이 환경에는 객체저장이 뜨지 않는다.",
            "그래서 **객체 백업·복구는 미측정**이고 DB 복구만 실측이다 —",
            "한 칸에 두면 「복구 성공」이 절반의 사실이 된다.",
            "",
            "★ DB 만 살아나면 이벤트 행은 돌아오고 **그 이벤트의 영상은 사라진다.**",
            "  복구된 시스템이 「영상이 있었다고 말하는 DB」가 된다 — 착시 ⑥(스키마)의 운영판이다.",
        ]
    else:
        lines.append("객체 %s개 · %s bytes" % (obj.get("objects"), obj.get("bytes")))
    return "\n".join(lines) + "\n"


def _render_object_evidence(manifest: dict, out: dict) -> str:
    """영상 복구 기록. **명령을 그대로 적는다** — 사고 나는 날 이걸 보고 친다 (D-356 ③)."""
    obj = manifest.get("objects") or {}
    lines = [
        "# 영상(객체저장) 복구 실행 기록 — **해 봤다** (D-356 ③)",
        "",
        "> 「복구를 해 보지 않은 백업은 백업이 아니다」 — DB 에 적용한 그 규정을",
        "> 영상에도 그대로 적용한 기록이다. **파일이 생겼다**가 아니라",
        "> **바이트가 그때 그 바이트인가**를 잰다.",
        "",
        "## 1. 무엇을 떴나",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 원본 버킷 | `{out['source_bucket']}` |",
        f"| 범위 | `{obj.get('scope', '?')}` — "
        + ("**이벤트에 묶인 것만**(D-356 ①)" if obj.get("scope") == "event_bound"
           else "버킷 전량") + " |",
        f"| 뜬 객체 | {obj.get('objects')}개 · {obj.get('bytes')} bytes |",
        f"| 이벤트에 묶인 총수 | {obj.get('event_bound_expected')}개 |",
        f"| 안 묶여서 건너뛴 것 | {obj.get('skipped_not_event_bound')}개 |",
        f"| 묶였는데 버킷에 없던 것 | {obj.get('missing_count')}개 |",
        f"| 보존 기간 | {obj.get('retention_days')}일 |",
        "",
        "## 2. 되살려 봤나 — **수로 답한다**",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 복구 대상 | {out['expected']}개 |",
        f"| 되살린 것 | {out['restored']}개 |",
        f"| **해시 일치** | **{out['hash_matched']}개** |",
        f"| 어긋난 것 | {len(out['mismatched'])}개 |",
        f"| 복구 버킷 | `{out['restore_bucket']}` (예행 뒤 지웠다) |",
        "",
        "★ **원본 버킷에는 쓰지 않았다.** DB 복구가 `gx_restore_*` 임시 DB 로만 가는 것과",
        "같은 규약이다 — 복구 예행이 원본을 덮으면 그것은 예행이 아니라 사고다.",
        "",
        "## 3. 친 명령 — 그대로",
        "",
        "```",
        *out["commands"],
        "```",
        "",
        "## 4. 판정",
        "",
        ("**성공** — 되살린 바이트가 원본과 같다." if out["ok"]
         else "**실패** — 아래를 보라."),
    ]
    for line in out["mismatched"]:
        lines.append(f"- {line}")
    lines += [
        "",
        "## 5. ★ 아직 아닌 것 — 적어 둔다 (D-356 ②)",
        "",
        "이 예행의 백업 목적지는 **저장소 안**(`docs/agent/evidence/`)이다.",
        "**같은 디스크는 백업이 아니다.** 운영에서는 최소 다른 볼륨, 가능하면 다른 호스트로",
        "가야 하고, 그 목적지는 **배포 구성에서 정해진다** — 지금 그 경로를 적으면",
        "실측하지 않은 경로가 매뉴얼에 들어간다(D-286). 그래서 여기에는",
        "**「해 봤다」와 「아직 어디에 둘지는 안 정했다」를 함께** 적는다.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
