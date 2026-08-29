#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""운영 기반 ① — **백업.** DB 와 객체저장을 뜨고, 무엇을 떴는지 대장을 남긴다 (D-354 ①).

★ 이 스크립트만으로는 절을 갚지 못한다
---------------------------------------
    **복구를 해 보지 않은 백업은 백업이 아니다.**
    「백업 있음」은 절이 아니고 **「복구 성공」이 절이다** (D-354 ①).

그래서 이 스크립트는 짝이 있다: `scripts/ops_restore.py`.
백업은 **대조표(manifest)** 를 함께 남기고, 복구는 그 대조표와 **행 수를 맞춰 본다.**
대조표가 없으면 복구가 성공했는지 판정할 수 없다 — 「파일이 생겼다」는 성공이 아니다.

무엇을 뜨나 — 둘
----------------
  ① **DB** — `pg_dump -Fc`(custom). 스키마·데이터·인덱스가 한 파일에 들어간다
  ② **객체저장** — 영상 클립·캡처가 사는 곳(MinIO). 버킷의 객체를 내려받는다

    ★ 둘 다 떠야 한다. DB 만 뜨면 이벤트 행은 살아나고 **그 이벤트의 영상은 사라진다** —
      복구된 시스템이 「영상이 있었다고 말하는 DB」가 된다. 착시 ⑥(스키마)의 운영판이다.

★ 못 뜬 것을 뜬 것으로 세지 않는다 (D-301)
------------------------------------------
객체저장에 닿지 못하면 **exit 2(판정 불가)** 로 끝난다. exit 0 이 아니다.
「이 환경에 객체저장이 없다」와 「객체가 0개다」는 다른 사실이고, 대장에 다르게 적힌다.

    docker exec gx-shell python /repo/scripts/ops_backup.py --db --objects \
        --out /docs/agent/evidence/D-354/backup
    python scripts/ops_backup.py --self-test        # 호스트에서도 돈다

되돌림: 이 스크립트는 **읽기만** 한다. 원본 DB·버킷을 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

# ═══════════════════════════════════════════════════════════════════════════
# ★ 어디서 뜨는가 — **클라이언트 판이 서버 판과 맞아야 한다** [실측 2026-09-09]
# ═══════════════════════════════════════════════════════════════════════════
#
#     pg_dump: error: aborting because of server version mismatch
#     detail: server version: 18.1 · pg_dump version: 17.7
#
# 앱 컨테이너의 클라이언트가 DB 서버보다 낮았다. **백업은 뜨는 자리가 정해져 있다** —
# 아무 데서나 돌리면 안 되고, 그 사실이 매뉴얼에 없으면 운영자가 새벽에 알게 된다.
# 그래서 「어디서 실행하는가」를 인자로 만든다. 기본은 이 자리(local), 필요하면 다른 자리.
#
#     --via local                # 이 자리에서 pg_dump 를 부른다
#     --via docker:postgres      # DB 컨테이너 안의 클라이언트로 부른다 (판이 반드시 맞는다)


def _transport(via: str):
    """(명령 앞머리, 컨테이너 이름 또는 None) 을 돌려준다."""
    if via == "local":
        return [], None
    if via.startswith("docker:"):
        name = via.split(":", 1)[1]
        return ["docker", "exec", name], name
    raise ValueError("--via 는 local 또는 docker:<컨테이너> 다: %r" % via)


def _run(prefix, argv, env=None):
    proc = subprocess.run([*prefix, *argv], capture_output=True, text=True,
                          env=env or dict(os.environ))
    return proc


def client_version(prefix) -> str:
    proc = _run(prefix, ["pg_dump", "--version"])
    return (proc.stdout or proc.stderr or "").strip()

#: 대조표에 행 수를 적을 표. **복구 성공의 술어가 이 표들이다.**
#: 「전체 테이블」이 아니라 **계약 기능이 사는 표**를 고른다 — 전체를 세면 느리고,
#: 느린 검사는 안 돌게 되고, 안 도는 검사는 없는 것과 같다.
WITNESS_TABLES = (
    "stream_monitors_streammonitor",   # 카메라 — F-10 알림의 위치가 여기 산다
    "stream_monitors_detectionevent",  # 탐지 이벤트 — 계약 F-01~03 의 산출물
    "stream_monitors_eventclip",       # 이벤트↔영상 구간 참조 (계약 11조의 자리)
    "user_coreuser",                   # 사람
    "auth_group",                      # 테넌트 경계의 뿌리
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_settings() -> dict[str, str]:
    """어느 DB 를 뜨는가. **환경에서 읽는다** — 코드에 박으면 다른 환경에서 엉뚱한 것을 뜬다."""
    return {
        "name": os.environ.get("DB_NAME", "database_guardianx"),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "postgres"),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_counts(tables=WITNESS_TABLES, via: str = "local") -> dict[str, int | None]:
    """대조표의 행 수. 없는 표는 **None** 으로 적는다 — 0 으로 적으면 「없음」과 「빈 표」가 섞인다.

    `psql` 로 센다(psycopg2 가 아니다). 파이썬이 없는 DB 컨테이너에서도 돌아야 하기 때문이다.
    """
    cfg = db_settings()
    prefix, container = _transport(via)
    host = "localhost" if container else cfg["host"]
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
    out: dict[str, int | None] = {}
    for table in tables:
        proc = _run(prefix, ["psql", "-tAq", "-h", host, "-p", cfg["port"], "-U", cfg["user"],
                             "-d", cfg["name"], "-c", 'SELECT COUNT(*) FROM "%s"' % table], env)
        value = (proc.stdout or "").strip()
        out[table] = int(value) if proc.returncode == 0 and value.isdigit() else None
    return out


def dump_db(out_dir: Path, via: str = "local") -> dict:
    """DB 를 뜬다. `--via docker:<컨테이너>` 면 그 안에서 뜨고 파일을 꺼내 온다."""
    cfg = db_settings()
    prefix, container = _transport(via)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = "db_%s_%s.dump" % (cfg["name"], stamp)
    remote = "/tmp/" + name if container else str(out_dir / name)

    host = "localhost" if container else cfg["host"]   # 컨테이너 안에서는 자기 자신이다
    argv = ["pg_dump", "-Fc", "-h", host, "-p", cfg["port"], "-U", cfg["user"],
            "-d", cfg["name"], "-f", remote]
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
    proc = _run(prefix, argv, env)
    if proc.returncode != 0:
        raise RuntimeError("pg_dump 실패: %s" % (proc.stderr or "").strip()[:400])

    commands = [" ".join(shlex.quote(x) for x in [*prefix, *argv])]
    if container:
        cp = ["docker", "cp", "%s:%s" % (container, remote), str(out_dir / name)]
        if subprocess.run(cp, capture_output=True, text=True).returncode != 0:
            raise RuntimeError("덤프를 꺼내오지 못했다: %s" % " ".join(cp))
        commands.append(" ".join(shlex.quote(x) for x in cp))
        _run(["docker", "exec", container], ["rm", "-f", remote])

    dump = out_dir / name
    return {
        "file": dump.name,
        "bytes": dump.stat().st_size,
        "sha256": sha256(dump),
        "via": via,
        "client_version": client_version(prefix),
        "command": commands,
        "rows": row_counts(via=via),
    }


def mirror_objects(out_dir: Path) -> dict:
    """객체저장을 내려받는다. 닿지 못하면 **예외로 끝난다** — 조용히 0개로 적지 않는다."""
    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "")
    bucket = os.environ.get("MINIO_BUCKET_NAME", "")
    if not endpoint or not bucket:
        raise RuntimeError("MINIO_ENDPOINT / MINIO_BUCKET_NAME 이 비었다")
    client = Minio(
        endpoint.replace("http://", "").replace("https://", ""),
        access_key=os.environ.get("MINIO_ACCESS_KEY", ""),
        secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
        secure=endpoint.startswith("https"),
    )
    target = out_dir / "objects"
    target.mkdir(parents=True, exist_ok=True)
    count = total = 0
    for obj in client.list_objects(bucket, recursive=True):
        client.fget_object(bucket, obj.object_name, str(target / obj.object_name.replace("/", "_")))
        count += 1
        total += int(obj.size or 0)
    return {"bucket": bucket, "objects": count, "bytes": total, "endpoint": endpoint}


def self_test() -> int:
    """★ 출생 표본 — **복구를 안 해 본 백업**을 백업으로 세지 않는가.

    이 스크립트가 태어난 문장은 D-354 의 이것이다:
        「백업 있음」은 절이 아니고 **「복구 성공」이 절이다.**
    그래서 첫 갈래는 **대조표에 행 수가 없으면 그 백업은 복구를 판정할 수 없다**는 것이다.
    """
    checks = [
        ("★ 출생표본 — 행 수 없는 대조표는 복구를 판정할 수 없다",
         not manifest_is_verifiable({"db": {"file": "x.dump", "rows": {}}})),
        ("행 수가 있으면 판정할 수 있다",
         manifest_is_verifiable({"db": {"file": "x.dump", "rows": {"core_user": 3}}})),
        ("없는 표는 None 으로 적고, 0 으로 적지 않는다",
         manifest_is_verifiable({"db": {"file": "x.dump", "rows": {"a": None, "b": 1}}})),
        ("db 칸이 없으면 판정 불가",
         not manifest_is_verifiable({"objects": {"objects": 0}})),
        ("증인 표가 비어 있지 않다 (D-301)", len(WITNESS_TABLES) > 0),
    ]
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[OPS-BACKUP] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_FAIL if bad else EXIT_OK


def manifest_is_verifiable(manifest: dict) -> bool:
    """이 대조표로 **복구 성공을 판정할 수 있는가.** 파일만 있고 행 수가 없으면 못 한다."""
    db = manifest.get("db") or {}
    if not db.get("file"):
        return False
    rows = db.get("rows") or {}
    return any(v is not None for v in rows.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", action="store_true")
    ap.add_argument("--objects", action="store_true")
    ap.add_argument("--out", default="/docs/agent/evidence/D-354/backup")
    ap.add_argument("--via", default="local",
                    help="local | docker:<컨테이너> — pg_dump 를 **어디서** 부를 것인가")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not (args.db or args.objects):
        print("[OPS-BACKUP] --db · --objects 중 하나는 있어야 한다")
        return EXIT_FAIL

    out_dir = Path(args.out)
    manifest: dict = {"created_at": utcnow(), "db_settings": db_settings()}
    undecidable: list[str] = []

    if args.db:
        manifest["db"] = dump_db(out_dir, via=args.via)
        print("[OPS-BACKUP] DB %s · %d bytes · sha256 %s…"
              % (manifest["db"]["file"], manifest["db"]["bytes"],
                 manifest["db"]["sha256"][:12]))
        print("[OPS-BACKUP] 증인 표 행 수: " + " · ".join(
            "%s=%s" % (k, v) for k, v in manifest["db"]["rows"].items()))

    if args.objects:
        try:
            manifest["objects"] = mirror_objects(out_dir)
            print("[OPS-BACKUP] 객체 %d개 · %d bytes"
                  % (manifest["objects"]["objects"], manifest["objects"]["bytes"]))
        except Exception as exc:
            # ★ 「닿지 못했다」와 「0개다」는 다른 사실이다 (D-301).
            manifest["objects"] = {"unreachable": True, "reason": str(exc)[:200],
                                   "endpoint": os.environ.get("MINIO_ENDPOINT", "")}
            undecidable.append("객체저장에 닿지 못했다: %s" % str(exc)[:120])

    # ★ 대조표는 **덧쓴다, 덮지 않는다.** DB 와 객체저장은 클라이언트가 사는 자리가 달라
    # 따로 뜨게 되는데(이 환경이 그렇다), 덮으면 먼저 뜬 쪽이 사라진다 —
    # 그러면 대조표가 「DB 만 백업됐다」고 거짓말한다.
    out_dir.mkdir(parents=True, exist_ok=True)
    _target = out_dir / "manifest.json"
    if _target.is_file():
        try:
            _previous = json.loads(_target.read_text(encoding="utf-8"))
        except ValueError:
            _previous = {}
        _previous.update(manifest)
        manifest = _previous
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[OPS-BACKUP] 대조표 → %s" % (out_dir / "manifest.json"))
    print("[OPS-BACKUP] ★ 이것만으로는 절을 갚지 못한다 — ops_restore.py 로 **복구해 봐야** 한다")

    if undecidable:
        for line in undecidable:
            print("[OPS-BACKUP] 판정 불가 — %s" % line)
        return EXIT_UNDECIDABLE
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
