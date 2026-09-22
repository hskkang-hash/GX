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
  ② **객체저장** — 영상 클립·캡처가 사는 곳(MinIO).
     ★ 기본은 **버킷 전량이 아니라 「이벤트에 묶인 것만」**이다 (D-356 ① · `--object-scope`).
       전량은 크고 비싸고 제품이 필요로 하는 것도 아니다 — 재난안전에서 증빙이 되는 것은
       「그 이벤트의 그 장면」이고, 그것을 아는 표가 `EventClip`(D-306)이다.
       그래서 **영상 백업과 EventClip 이 한 덩어리**다.
  ③ 보존 기간 — `RETENTION_DAYS`. 정하지 않으면 **디스크가 정책을 대신 정한다**(D-356 ④)

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


def _major(text: str):
    """판 문자열에서 주 판 번호만 뽑는다. 못 읽으면 None — **0 이 아니라 모른다**이다."""
    for chunk in (text or "").replace("(", " ").replace(")", " ").split():
        head = chunk.split(".")[0]
        if head.isdigit():
            return int(head)
    return None


def server_major(prefix, cfg) -> int | None:
    """서버의 주 판. `psql` 로 센다 — 파이썬이 없는 DB 컨테이너에서도 돌아야 한다."""
    host = "localhost" if prefix else cfg["host"]
    env = dict(os.environ)
    env.setdefault("PGPASSWORD", os.environ.get("DB_PASSWORD", ""))
    proc = _run(prefix, ["psql", "-tAq", "-h", host, "-p", cfg["port"], "-U", cfg["user"],
                         "-d", cfg["name"], "-c", "show server_version"], env)
    return _major(proc.stdout) if proc.returncode == 0 else None


def preflight(via: str) -> dict:
    """★ **뜨기 전에 판을 잰다** [턴 AC · 차선 E].

    ═══════════════════════════════════════════════════════════════════════
    왜 이 함수가 생겼나 — **0바이트 유령 30개** [실측 2026-09-22]
    ═══════════════════════════════════════════════════════════════════════
        `pg_dump -f <경로>` 는 **파일을 먼저 만들고** 서버 판 검사에서 죽는다.
        그래서 실패한 백업이 **0바이트 덤프 파일을 남긴다.**

            /backup/20260917 ~ 20260921 : 덤프 30개 · **전부 0 바이트**

        `ls` 는 「매일 백업이 있다」고 말했고 크기는 「아무것도 없다」고 말했다.
        닷새 동안 아무도 크기를 안 봤다. **「파일이 생겼다」는 성공이 아니다** 는
        문장이 이 파일 머리말에 있었지만, 그 문장에는 **술어가 없었다.**

    그래서 이제 **뜨기 전에** 판을 재고, 안 맞으면 **파일을 만들지 않고** 죽는다.
    있는 것처럼 보이는 것을 남기지 않는 것이 실패의 예의다.
    """
    cfg = db_settings()
    prefix, container = _transport(via)
    client = _major(client_version(prefix))
    server = server_major(prefix, cfg)
    out = {"via": via, "client_major": client, "server_major": server}
    if client is None or server is None:
        out["ok"] = None            # 못 쟀다 — 회색. 뜨기는 해 본다.
        out["why"] = "판을 못 쟀다 (client=%r server=%r)" % (client, server)
        return out
    out["ok"] = client >= server
    out["why"] = ("클라이언트 %d ≥ 서버 %d" % (client, server) if out["ok"] else
                  "클라이언트 판(%d)이 서버 판(%d)보다 낮다 — 낮은 판은 높은 판을 못 뜬다. "
                  "고치는 자리는 **어디서 뜨는가**(--via docker:postgres)이거나 "
                  "**워커 이미지의 postgresql-client 판**이다" % (client, server))
    return out


def _mark_failed(prefix, container, remote) -> str | None:
    """실패가 남긴 0바이트 파일에 `.failed` 를 붙인다. **지우지 않는다.**

    ⚠ 바이트가 있으면 **손대지 않는다** — 반쯤 떠진 덤프도 증거이고, 그것을
      우리가 이름 바꿔 숨길 일이 아니다. 0바이트일 때만 이름을 고친다.
    """
    target = "%s.failed" % remote
    try:
        if container:
            probe = _run(["docker", "exec", container],
                         ["sh", "-c", "test -f %s && test ! -s %s && mv %s %s && echo moved"
                          % (remote, remote, remote, target)])
            return target if "moved" in (probe.stdout or "") else None
        path = Path(remote)
        if path.is_file() and path.stat().st_size == 0:
            path.rename(target)
            return target
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def dump_db(out_dir: Path, via: str = "local") -> dict:
    """DB 를 뜬다. `--via docker:<컨테이너>` 면 그 안에서 뜨고 파일을 꺼내 온다.

    ★ 뜨기 전에 `preflight()` 로 판을 재고, 안 맞으면 **파일을 만들지 않고** 죽는다.
    """
    cfg = db_settings()
    prefix, container = _transport(via)
    pre = preflight(via)
    if pre["ok"] is False:
        raise RuntimeError("뜨기 전 판 검사에서 멈췄다 — %s" % pre["why"])
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
        #: ★ 실패가 남긴 **0바이트 유령**에 이름을 붙인다 [턴 AC · 차선 E].
        #:   지우지 않는다(이 턴 삭제 0) — `.failed` 로 바꾸면 **다시는 덤프로 안 보인다.**
        #:   닷새 동안 30개가 `.dump` 라는 이름만으로 「백업이 있다」고 말했다.
        _mark_failed(prefix, container, remote)
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


#: ★ 보존 기간 (D-356 ④). **정하지 않으면 디스크가 정책을 대신 정한다** —
#: 그리고 디스크가 정하는 방식은 「가득 차면 백업이 멈춘다」이다.
#:
#: 왜 90일인가: 계약 검수(2027.1)와 그 뒤 안정화 구간을 한 번에 덮는 길이이고,
#: 재난·사고 보고서(F-11)가 사후에 영상을 부르는 창이 대개 분기 안이다.
#: **계약이 정한 수가 아니다** — 계약 [별첨1] 에 보존 기간 조항이 없다(D-280).
#: 고객이 다른 값을 요구하면 그때 이 상수 하나를 고친다.
RETENTION_DAYS: int = 90


def _minio_client():
    """객체저장 클라이언트. 설정이 비면 **예외** — 조용히 0개로 적지 않는다."""
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
    return client, bucket, endpoint


def event_bound_keys() -> set[str] | None:
    """★ **이벤트에 묶인 객체 키만** (D-356 ①). Django 가 없으면 `None`.

    왜 전량이 아닌가 — 버킷 전량은 크고 비싸고, **제품이 필요로 하는 것도 아니다.**
    재난안전에서 증빙이 되는 것은 「그 이벤트의 그 장면」이고, 그것을 아는 표가
    `EventClip`(D-306)이다. 그래서 ②(무엇을 뜨는가)와 EventClip 이 한 덩어리다.

    ★ `None` 과 `set()` 은 **다른 값**이다:
        None    이벤트 목록을 못 읽었다 (Django 없음) — 전량으로 물러난다
        set()   읽었는데 **묶인 객체가 0개다** — 뜰 것이 없는 것이 사실이다
      둘을 같은 값으로 두면 「못 읽었다」가 「없다」로 조용히 바뀐다 (D-301).
    """
    try:
        sys.path.insert(0, "/app")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django

        django.setup()
        from django.apps import apps as _apps

        Clip = _apps.get_model("stream_monitors", "EventClip")
    except Exception:
        return None
    return {k for k in Clip._base_manager.exclude(object_key="")
            .values_list("object_key", flat=True) if k}


def mirror_objects(out_dir: Path, *, scope: str = "event_bound") -> dict:
    """객체저장을 내려받는다. 닿지 못하면 **예외로 끝난다** — 조용히 0개로 적지 않는다.

    `scope` 둘 (D-356 ①):
        event_bound  이벤트(`EventClip`)에 묶인 객체만. **기본값** — 제품에 맞는다
        all          버킷 전량. 크고 비싸다. 이관·이사 때만 쓴다

    ★ 어느 쪽으로 떴는지를 **대조표에 적는다.** 안 적으면 복구할 때 「왜 이것밖에
      없나」를 아무도 못 읽는다 — 「빠졌다」와 「원래 안 떴다」가 같은 그림이 된다.
    """
    client, bucket, endpoint = _minio_client()

    wanted = event_bound_keys() if scope == "event_bound" else None
    fell_back = scope == "event_bound" and wanted is None

    target = out_dir / "objects"
    target.mkdir(parents=True, exist_ok=True)
    count = total = skipped = 0
    keys: list[str] = []
    for obj in client.list_objects(bucket, recursive=True):
        if wanted is not None and obj.object_name not in wanted:
            skipped += 1
            continue
        client.fget_object(bucket, obj.object_name,
                           str(target / obj.object_name.replace("/", "_")))
        count += 1
        total += int(obj.size or 0)
        keys.append(obj.object_name)

    #: ★ **묶여 있는데 버킷에 없는 것** — 이것이 가장 중요한 수다.
    #:   DB 는 「영상이 있다」고 말하는데 그 장면이 실제로는 없는 상태이고,
    #:   백업이 그것을 **처음으로 드러내는 자리**다 (착시 ⑥의 운영판).
    missing = sorted(wanted - set(keys)) if wanted is not None else []
    return {
        "bucket": bucket, "objects": count, "bytes": total, "endpoint": endpoint,
        "scope": scope,
        "retention_days": RETENTION_DAYS,
        "skipped_not_event_bound": skipped,
        "event_bound_expected": None if wanted is None else len(wanted),
        "missing_in_bucket": missing[:50],
        "missing_count": len(missing),
        #: 전량으로 물러났는가. **물러난 것을 적는다** — 안 적으면 다음 사람이
        #: 「이벤트 단위로 떴다」고 읽고 그 수를 인용한다.
        "fell_back_to_all": fell_back,
        "keys": sorted(keys)[:200],
    }


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
    ap.add_argument("--object-scope", default="event_bound",
                    choices=("event_bound", "all"),
                    help="event_bound(기본) = 이벤트에 묶인 객체만 · all = 버킷 전량")
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
            manifest["objects"] = mirror_objects(out_dir, scope=args.object_scope)
            info = manifest["objects"]
            print("[OPS-BACKUP] 객체 %d개 · %d bytes · 범위 %s · 보존 %d일"
                  % (info["objects"], info["bytes"], info["scope"],
                     info["retention_days"]))
            if info["fell_back_to_all"]:
                print("[OPS-BACKUP] ★ 이벤트 목록을 못 읽어 **전량으로 물러났다** — "
                      "이 백업을 '이벤트 단위' 로 인용하지 마라")
            if info["missing_count"]:
                # ★ DB 는 「영상이 있다」고 말하는데 그 장면이 없다.
                print("[OPS-BACKUP] ★ 이벤트에 묶였는데 **버킷에 없는 객체 %d개** — "
                      "복구해도 그 장면은 안 돌아온다: %s"
                      % (info["missing_count"], " · ".join(info["missing_in_bucket"][:5])))
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
