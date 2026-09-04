#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-12 — 백업을 **다른 볼륨**에 둔다. 그리고 거기서 읽힌다 (2026-09-04 · 차선 E3).

    OPS-12 백업 목적지 — 다른 볼륨·다른 호스트
      "목적지 호스트가 없다. **볼륨 갈래는 지금 가능**"
        — docs/agent/remaining_40.md 67행

지금 어디에 뜨고 있나 — **같은 디스크다**
------------------------------------------
`설치운영매뉴얼_v0.1.md` §4 가 스스로 적어 두었다:

    "지금 백업 목적지는 **저장소 안**이다. **같은 디스크는 백업이 아니다.**"

`ops_backup.py --out /docs/agent/evidence/…` 는 백업 파일을 **저장소 작업복사본**에
떨어뜨린다. 저장소가 사는 디스크가 죽으면 백업도 같이 죽는다. 그 상태에서 「백업이
있다」고 말하는 것은 사실이 아니라 착시다.

이 스크립트가 여는 갈래 — **다른 볼륨**
---------------------------------------
호스트를 하나 더 살 수는 없다. 그러나 **볼륨을 가르는 것은 지금 할 수 있다.**
여기서 「다르다」는 두 가지를 뜻하고, 둘 다 이 스크립트가 **잰다**:

    ① DB 의 데이터 볼륨(`gx_pgdata`)과 **다른 볼륨**이다
       — 같은 볼륨에 두면 그 볼륨이 죽을 때 원본과 백업이 함께 죽는다
    ② 저장소 작업복사본 **밖**이다 — `git status` 에도, 디스크의 저장소 경로에도 없다

★ 그리고 **거기서 읽히는지**까지 본다 (D-354 ①의 규약)
-------------------------------------------------------
    **복구를 해 보지 않은 백업은 백업이 아니다.**

그래서 뜬 뒤에 **완전히 다른 컨테이너를 하나 더** 띄워 그 볼륨만 붙이고
`pg_restore --list` 로 목차를 읽는다. 뜬 컨테이너에서 그대로 확인하면 "방금 쓴 파일이
아직 열려 있다"를 확인하는 것이지 **목적지에 남았다**를 확인하는 것이 아니다.

★ 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다** (⚠ 지시 규약)
--------------------------------------------------------------------
  만드는 것: 도커 볼륨 하나 (`gx_backup_vault_e`). **이 실행이 처음 만든다.**
  쓰는 컨테이너: `--rm` 이라 명령이 끝나면 사라진다. 이름을 가진 컨테이너를 남기지 않는다.
  **건드리지 않는 것**: `postgres` · `gx-shell` · `redis` · MinIO — 다른 차선이 쓰고 있다.
                        `gx_pgdata` 볼륨은 **읽지도 붙이지도 않는다.**
  지우는 법:  docker volume rm gx_backup_vault_e        ← 이 한 줄이면 원상태다

자격증명은 저장소에 없다 (D-204)
--------------------------------
`--from-container gx-shell` 이 그 컨테이너의 환경에서 `DB_*` 를 읽어 온다.
값은 이 스크립트가 화면에도 증거 파일에도 **적지 않는다** — 이름만 적는다.

    python scripts/ops_backup_volume.py --evidence docs/agent/evidence/OPS-12/volume_branch.md
    python scripts/ops_backup_volume.py --self-test        # 판정 규칙만 (도커 없이)

종료 코드: 0 떴고 다른 볼륨에서 읽혔다 · 1 쟀는데 어긋났다 · 2 **못 쟀다**(도커 없음)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 목적지 볼륨. 차선 E3 의 접두(`e_`)를 꼬리에 단다 — 다른 차선의 것과 안 겹친다.
DEST_VOLUME = "gx_backup_vault_e"

#: **절대 목적지가 될 수 없는 볼륨.** DB 가 사는 곳에 그 DB 의 백업을 두지 않는다.
FORBIDDEN_DEST = {"gx_pgdata"}

#: DB 컨테이너. 판(version)이 맞는 `pg_dump` 를 얻으려고 **이 컨테이너의 이미지**를 쓴다.
#: [실측 2026-09-09 · ops_backup.py 머리말] 앱 컨테이너의 클라이언트가 낮아
#: `server version mismatch` 로 죽은 적이 있다. 이미지를 빌려 오면 그 일이 없다.
DB_CONTAINER = "postgres"


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list[tuple[str, bool, str]]:
    """`None` 은 **못 쟀다**이지 0 도 거짓도 아니다 (D-301)."""
    out = []

    size = facts.get("dump_bytes")
    if size is None:
        out.append(("① 떴는가", False, "**못 쟀다** — 덤프 파일을 확인하지 못했다"))
    else:
        out.append(("① 떴는가", size > 0, "덤프 %s바이트" % format(size, ",")
                    if size > 0 else "0바이트 — 뜬 것이 아니다"))

    dest, dbvol = facts.get("dest_volume"), facts.get("db_volume")
    if dest is None or dbvol is None:
        out.append(("② 다른 볼륨인가", False, "**못 쟀다** — 볼륨 이름을 확인하지 못했다"))
    else:
        ok = dest != dbvol and dest not in FORBIDDEN_DEST
        out.append(("② 다른 볼륨인가", ok,
                    "목적지 %r · DB 데이터 %r — 다르다" % (dest, dbvol) if ok
                    else "목적지가 DB 데이터 볼륨과 같다: %r" % dest))

    inrepo = facts.get("inside_repo")
    if inrepo is None:
        out.append(("③ 저장소 밖인가", False, "**못 쟀다**"))
    else:
        out.append(("③ 저장소 밖인가", not inrepo,
                    "이번 덤프는 저장소 작업복사본 안에 없다" if not inrepo
                    else "이번 덤프가 저장소 안에 있다 — 같은 디스크는 백업이 아니다"))

    toc = facts.get("toc_entries")
    if toc is None:
        out.append(("④ 거기서 읽히는가", False,
                    "**못 쟀다** — 다른 컨테이너에서 목차를 읽지 못했다"))
    else:
        out.append(("④ 거기서 읽히는가", toc > 0,
                    "다른 컨테이너에서 `pg_restore --list` 목차 %d줄" % toc
                    if toc > 0 else "목차가 비었다 — 파일은 있는데 읽을 것이 없다"))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 도커 심부름
# ═══════════════════════════════════════════════════════════════════════════
def docker(*args: str, timeout: int = 900) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"           # Git Bash 가 /vault 를 C:\ 로 바꾸지 않게
    p = subprocess.run(["docker", *args], capture_output=True, text=True,
                       errors="replace", timeout=timeout, env=env)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def container_env(name: str) -> dict:
    """그 컨테이너의 환경에서 자격증명을 **빌려 온다.** 저장소에 값을 두지 않으려고."""
    rc, out, _ = docker("inspect", name, "--format", "{{json .Config.Env}}")
    if rc != 0:
        return {}
    try:
        pairs = json.loads(out)
    except ValueError:
        return {}
    got = {}
    for item in pairs:
        if "=" in item:
            k, v = item.split("=", 1)
            if k.startswith("DB_"):
                got[k] = v
    return got


def db_data_volume() -> str | None:
    rc, out, _ = docker(
        "inspect", DB_CONTAINER, "--format",
        "{{range .Mounts}}{{if eq .Destination \"/var/lib/postgresql\"}}{{.Name}}{{end}}{{end}}")
    return out or None


def self_test() -> int:
    ok = True
    ok &= all(not p for _, p, _ in judge({}))

    good = {"dump_bytes": 12345, "dest_volume": "gx_backup_vault_e",
            "db_volume": "gx_pgdata", "inside_repo": False, "toc_entries": 480}
    ok &= all(p for _, p, _ in judge(good))

    same = dict(good); same["dest_volume"] = "gx_pgdata"
    r = judge(same)
    ok &= [p for _, p, _ in r] == [True, False, True, True]

    inrepo = dict(good); inrepo["inside_repo"] = True
    r = judge(inrepo)
    ok &= [p for _, p, _ in r] == [True, True, False, True]

    empty = dict(good); empty["toc_entries"] = 0
    r = judge(empty)
    ok &= [p for _, p, _ in r] == [True, True, True, False]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--volume", default=DEST_VOLUME)
    ap.add_argument("--from-container", default="gx-shell",
                    help="DB 자격증명을 빌려 올 컨테이너 (값은 적지 않는다)")
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    rc, out, err = docker("version", "--format", "{{.Server.Version}}")
    if rc != 0:
        print("판정 불가(exit 2): 도커에 닿지 못했다 — %s" % (err or out))
        return EXIT_UNDECIDABLE

    dest = args.volume
    if dest in FORBIDDEN_DEST:
        print("거부: %r 는 DB 가 사는 볼륨이다. 원본과 백업을 한 볼륨에 두지 않는다." % dest)
        return EXIT_UNDECIDABLE

    creds = container_env(args.from_container)
    missing = [k for k in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST") if not creds.get(k)]
    if missing:
        print("판정 불가(exit 2): %s 에서 %s 를 못 읽었다 — 값은 저장소에 없다(D-204)"
              % (args.from_container, ", ".join(missing)))
        return EXIT_UNDECIDABLE

    rc, image, _ = docker("inspect", DB_CONTAINER, "--format", "{{.Config.Image}}")
    rc2, net, _ = docker("inspect", DB_CONTAINER, "--format",
                         "{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}")
    if rc != 0 or rc2 != 0 or not image or not net:
        print("판정 불가(exit 2): %r 컨테이너를 읽지 못했다" % DB_CONTAINER)
        return EXIT_UNDECIDABLE

    dbvol = db_data_volume()
    stamp = time.strftime("%Y%m%dT%H%M%S")
    fname = "%s_%s.dump" % (creds["DB_NAME"], stamp)

    say("## 0. 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다**")
    say()
    say("만드는 것: 도커 볼륨 `%s` 하나. 쓰는 컨테이너는 `--rm` 이라 남지 않는다." % dest)
    say("건드리지 않는 것: `postgres` · `gx-shell` · `redis` · MinIO (다른 차선이 쓴다) ·")
    say("그리고 DB 데이터 볼륨 `%s` — **붙이지도 않는다.**" % dbvol)
    say("지우는 법: `docker volume rm %s` — 이 한 줄이면 원상태다." % dest)
    say()
    say("빌려 온 자격증명: `%s` 컨테이너의 %s. **값은 여기 적지 않는다**(D-204)."
        % (args.from_container, " · ".join(sorted(creds))))
    say()

    facts: dict = {"dest_volume": dest, "db_volume": dbvol}

    say("## 1. 목적지 볼륨을 만든다")
    say()
    say("```")
    rc, out, err = docker("volume", "create", dest)
    say("docker volume create %-24s rc=%d" % (dest, rc))
    if rc != 0:
        say(err); say("```")
        return EXIT_UNDECIDABLE
    rc, mp, _ = docker("volume", "inspect", dest, "--format", "{{.Mountpoint}}")
    say("목적지 볼륨의 자리: %s" % mp)
    rc, mp2, _ = docker("volume", "inspect", dbvol or "", "--format", "{{.Mountpoint}}") \
        if dbvol else (1, "", "")
    say("DB 데이터 볼륨의 자리: %s" % (mp2 or "(못 읽었다)"))
    say("```")
    say()

    say("## 2. **다른 볼륨으로** 뜬다 — 판이 맞는 클라이언트로")
    say()
    say("판이 맞아야 한다 [실측 2026-09-09]: 앱 컨테이너의 `pg_dump` 가 서버보다 낮으면")
    say("`aborting because of server version mismatch` 로 죽는다. 그래서 **DB 컨테이너와")
    say("같은 이미지**(`%s`)를 하나 띄워 그 안의 `pg_dump` 를 쓴다." % image)
    say()
    dump_cmd = ("pg_dump -h %s -p %s -U %s -d %s -Fc -f /vault/%s"
                % (creds["DB_HOST"], creds.get("DB_PORT", "5432"),
                   creds["DB_USER"], creds["DB_NAME"], fname))
    say("```")
    say("docker run --rm --network %s -v %s:/vault \\" % (net, dest))
    say("    -e PGPASSWORD=**** %s \\" % image)
    say("    %s" % dump_cmd)
    rc, out, err = docker(
        "run", "--rm", "--network", net, "-v", "%s:/vault" % dest,
        "-e", "PGPASSWORD=%s" % creds["DB_PASSWORD"], image,
        "sh", "-c", dump_cmd)
    say("rc=%d" % rc)
    if err:
        say(err.splitlines()[-1] if err.splitlines() else err)
    say("```")
    if rc != 0:
        say()
        say("**뜨지 못했다.** 목적지 볼륨은 남겨 둔다 — 지우려면 위 §0 의 한 줄.")
        return EXIT_FAIL
    say()

    say("## 3. **다른 컨테이너**에서 그 볼륨만 붙여 읽는다")
    say()
    say("방금 뜬 컨테이너는 이미 사라졌다(`--rm`). 여기서 다시 띄우는 것은 **그 볼륨만**")
    say("아는 새 컨테이너다 — DB 에도 안 붙는다. 「목적지에 남았고, 거기서 읽힌다」를")
    say("보는 것이 이 단계의 전부다.")
    say()
    say("```")
    read_cmd = ("ls -l /vault/%s && sha256sum /vault/%s && "
                "pg_restore --list /vault/%s | wc -l" % (fname, fname, fname))
    say("docker run --rm -v %s:/vault %s sh -c '<ls · sha256sum · pg_restore --list | wc -l>'"
        % (dest, image))
    rc, out, err = docker("run", "--rm", "-v", "%s:/vault" % dest, image,
                          "sh", "-c", read_cmd)
    for line in (out or "").splitlines():
        say(line)
    if err:
        say(err.splitlines()[-1])
    say("rc=%d" % rc)
    say("```")

    lines = (out or "").splitlines()
    if rc == 0 and len(lines) >= 3:
        try:
            facts["dump_bytes"] = int(lines[0].split()[4])
        except (IndexError, ValueError):
            facts["dump_bytes"] = None
        facts["sha256"] = lines[1].split()[0] if lines[1].split() else None
        try:
            facts["toc_entries"] = int(lines[-1].strip())
        except ValueError:
            facts["toc_entries"] = None
    say()

    say("## 4. 저장소 안에 있는가 — **없어야 한다**")
    say()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for root, _dirs, files in os.walk(repo):
        if ".git" in root:
            continue
        for f in files:
            if f.endswith(".dump") and creds["DB_NAME"] in f:
                hits.append(os.path.join(root, f))
    mine = [h for h in hits if os.path.basename(h) == fname]
    facts["inside_repo"] = bool(mine)
    say("이번 덤프(`%s`)가 저장소 작업복사본 안에 있는가: **%s**"
        % (fname, "있다" if mine else "없다"))
    say()
    say("★ 그리고 **옛 백업이 아직 저장소 안에 있다** — 이것이 OPS-12 가 말하던 빚이다.")
    say("  `*%s*.dump` 로 저장소를 훑으니 **%d건**:" % (creds["DB_NAME"], len(hits)))
    for h in hits[:5]:
        say("  · %s" % os.path.relpath(h, repo))
    say("  이 갈래(볼륨)가 그 자리를 대신할 수 있다는 것을 이 실행이 보였다. **옮기는 것은")
    say("  이 스크립트가 하지 않는다** — 지우는 일에는 되돌림이 없고, 무엇을 남길지는")
    say("  보존 정책(OPS-07)이 정할 일이다.")
    say()

    say("## 5. 판정")
    say()
    rows = judge(facts)
    for name, passed, why in rows:
        say("  %s %-16s %s" % ("OK  " if passed else "FAIL", name, why))
    ok = all(p for _, p, _ in rows)
    say()
    say("파일 이름 `%s` · sha256 `%s`" % (fname, facts.get("sha256")))
    say("판정 **%s**" % ("통과" if ok else "실패"))
    say()
    say("## 6. 아직 못 넘은 것 — **다른 호스트**")
    say()
    say("이것은 **볼륨 갈래**다. 호스트 갈래가 아니다. 이 기계에는 목적지가 될 두 번째")
    say("호스트가 없고, 없는 것을 있다고 적지 않는다(D-286). 볼륨을 갈랐다는 사실은")
    say("「저장소와 함께 죽지 않는다」까지 말하고, 「이 기계와 함께 죽지 않는다」는")
    say("**말하지 않는다.** 그 절반은 배포 형상이 정해질 때 갚는다.")

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-12 — 백업을 다른 볼륨에 두고, 거기서 읽었다 (%s)\n\n"
                        % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_backup_volume.py` 가 실행하며 적었다.**\n"
                        "아래 rc·바이트·해시는 전부 그 실행의 것이다.\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
