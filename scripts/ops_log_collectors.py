#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07 — **수집기 자체를 잰다.** 로그가 어디에 쌓이고 언제 지워지는가 (2026-09-04 · E3).

    OPS-07 로그 수집·보존 기간 — "**수집기 자체를 안 쟀다**"
        — docs/agent/remaining_40.md 43행

왜 「보존 기간」만으로는 절이 안 서나
------------------------------------
이 저장소에는 보존 기간이 **하나** 서 있다: 감사 로그(`ops_audit_purge_beat`,
매일 03:10, 고객이 정한 `security.audit_log_retention_days`). 그것을 근거로
「보존 기간이 있다」고 적으면 **거짓말이 된다** — 그 하나가 전부인지 아무도 안 봤기
때문이다. 절은 「어떤 수집기에 보존 기간이 있는가」가 아니라
**「보존 기간이 없는 수집기가 있는가」** 로 서야 한다.

그래서 이 판정기는 **수집기를 전수로 세는 것부터** 한다:

    ① 컨테이너 stdout   도커 `json-file` 드라이버. 컨테이너마다 하나씩
    ② DB 감사 로그      `logger_auditlogs` — 미들웨어가 `db` 로거로 밀어 넣는다
    ③ 파일              `settings.LOGGING` 의 파일 핸들러

그리고 각각에 대해 **자라는 속도**와 **지우는 자리**를 따로 잰다.
「쌓인다」와 「지워진다」는 다른 사실이고, 앞만 재면 디스크가 정책을 대신 정한다
(D-356 ④ · `ops_backup.py` 가 같은 말을 백업 쪽에서 했다).

★ 속도는 **한 시간 치를 재서 하루로 환산한다** — 총량이 아니라
------------------------------------------------------------
컨테이너 로그의 총량은 「그 컨테이너가 언제 떴는가」에 따라 달라진다. 그 수로는
"내일 얼마나 늘어날지"를 못 말한다. `docker logs --since 60m` 의 바이트가
**지금 이 시스템이 로그를 만드는 속도**이고, 보존 정책은 그 속도 위에서 정해진다.

    ⚠ 환산은 [추정]이다. 이 판정기는 실측(한 시간 치)과 추정(하루 치)을 **갈라서** 적는다.

★ 2026-09-24 — **재는 일에서 거는 일로** (차선 E)
--------------------------------------------------
첫 판(2026-09-04)이 답한 것은 「무엇이 무한히 쌓이는가」였고, 답은 **컨테이너 stdout
5개 전부**였다. 그 다음 할 일은 재는 것이 아니라 **거는 것**이다. 걸었다:
`docker-compose.yml` · `docker-compose.stg.yml` 의 모든 서비스에
`logging.driver: json-file` + `max-size: 10m` / `max-file: 5` (앵커 하나).

그런데 **거는 것과 걸린 것은 다른 사실이다.** 도커의 `LogConfig` 는 컨테이너를
**만들 때** 굳는다 — compose 를 고쳐도 이미 떠 있는 컨테이너에는 닿지 않는다.
그래서 이 판정기는 이제 **두 곳을 따로 읽는다**:

    ㉠ **적용** — 실행 중 컨테이너의 `HostConfig.LogConfig` (도커에게 묻는다)
    ㉡ **선언** — compose 파일의 `services.*.logging` (파일을 읽는다)

그리고 셋으로 가른다: **적용됨** · **선언은 섰고 적용은 다음 재기동** ·
**선언할 자리조차 없다**(compose 밖 `docker run` 으로 뜬 컨테이너).
셋을 하나로 합치면 「고쳤다」와 「고친 것이 돌고 있다」가 같아진다(D-301).

    python scripts/ops_log_collectors.py --evidence docs/agent/evidence/OPS-07/collectors.md
    python scripts/ops_log_collectors.py --self-test     # 판정 규칙만 (도커 없이)

종료 코드: 0 전수를 쟀고 보존 기간이 다 있다 · 1 쟀고 **없는 수집기가 있다** ·
          2 못 쟀다(도커·DB 없음). 회색은 초록이 아니다.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 이 제품이 띄우는 컨테이너들. **여기 없는 컨테이너는 세지 않는다** — 남의 것을
#: 우리 수집기로 세면 수가 부풀고, 부푼 수 위에서 정한 정책은 틀린다.
#:
#: ★ [실측 2026-09-05 · 턴 D] **이 목록이 낡아 있었다.** 턴 C 가 앞단을 세우며
#:   `gx-nginx-e` · `gx-gunicorn-e` 둘을 띄웠는데 목록에 안 들어왔고, 그래서 이
#:   판정기는 「수집기 6개를 **전수로** 셌다」고 초록을 냈다 — 여덟인데 여섯을 세고
#:   전수라고 적은 것이다. **목록으로 세는 판정기는 목록이 낡는 만큼 눈이 먼다.**
#:   그래서 ⑤(목록 신선도)를 아래에 두었다: 떠 있는데 목록에 없는 우리 컨테이너가
#:   하나라도 있으면 ①은 초록이 될 수 없다.
PROJECT_CONTAINERS = ("gx-shell", "postgres", "redis",
                      "guardianx-source-minio-1", "gx-fe-build",
                      "gx-nginx-e", "gx-gunicorn-e")

#: 「우리 것」을 이름으로 가른다 — ⑤가 목록 밖 컨테이너를 찾을 때 쓴다.
#: 남의 컨테이너(다른 제품)를 우리 빨강으로 세지 않기 위한 좁힘이다.
PROJECT_NAME_HINTS = ("gx-", "guardianx", "postgres", "redis", "minio")

#: 컨테이너 **안에서 파일로** 쌓이는 로그. **`--log-opt` 가 여기에는 닿지 않는다.**
#:
#: ★ [실측 2026-09-05 · 턴 D] 이 자리를 이 판정기가 한 번도 안 봤다. 앞단(nginx)은
#:   `access_log /var/log/nginx/gx-front.access.log` 로 **파일에** 적는다 — stdout 이
#:   아니므로 도커의 `json-file` 회전과 아무 상관이 없고, `nginx:alpine` 에는
#:   logrotate 도 없다. 즉 **상한이 걸린 줄 알았던 컨테이너 안에서 상한 없는 수집기가
#:   돌고 있었다.** 「컨테이너에 `--log-opt` 를 걸었다」가 「그 컨테이너의 로그에 상한이
#:   걸렸다」가 아니라는 것 — 이 절에서 가장 하기 쉬운 두 번째 거짓말이다.
CONTAINER_FILE_LOGS = {
    "gx-nginx-e": ("/var/log/nginx/gx-front.access.log",),
}

#: 파일 수집기의 한 시간 치를 잴 때 되읽는 꼬리의 상한. 이보다 빨리 자라면
#: **적게 잡힌다** — 그때는 「이 이상」이라고 적는다(모자라게 적지, 부풀리지 않는다).
FILE_TAIL_CAP = 16 * 1024 * 1024

#: DB 쪽 사실을 물어볼 자리. dj-core 가 여기에만 있다.
APP_CONTAINER = "gx-shell"

#: 한 시간 치를 잰다. 이보다 짧으면 조용한 순간에 걸려 0 이 나오고,
#: 길면 판정기 한 번 도는 데 오래 걸린다.
WINDOW_MINUTES = 60

#: 선언이 있어야 할 자리. **여기서 값을 정하지 않는다** — 파일에서 읽는다(D-369).
COMPOSE_FILES = ("docker-compose.yml", "docker-compose.stg.yml")

#: compose 가 만들지 않은 컨테이너 → 그 컨테이너에 **대응하는 compose 서비스**.
#:
#: ★ 왜 이 표가 필요한가 [실측 2026-09-24]: 떠 있는 다섯 중 compose 라벨을 가진 것은
#:   `guardianx-source-minio-1` **하나뿐**이다. 나머지 넷은 `docker run` 으로 떴다
#:   (`docs/agent/review/LOCAL_BRINGUP_결과.md` 가 그 명령을 기록해 두었다).
#:   그러므로 **compose 를 고치는 것만으로는 넷에 닿지 않는다.** 그 사실을 표로
#:   적어 두지 않으면, compose 에 선언을 넣고 「걸었다」고 적게 된다 — 그것이
#:   이 절에서 가장 하기 쉬운 거짓말이다.
#:
#: `None` = 대응하는 서비스가 compose 에 아예 없다. 그런 컨테이너의 상한은
#: `docker run --log-opt max-size=… --log-opt max-file=…` 로만 걸린다.
ADHOC_TO_SERVICE = {
    "gx-shell": "shell",          # compose 의 `shell` 서비스와 같은 이미지·같은 자리
    "redis": "redis",
    "postgres": "postgres",       # 2026-09-05 · 턴 D 에 compose 로 들였다 (profiles: local)
    "gx-fe-build": None,          # 프론트 빌드용 임시 컨테이너 — compose 밖이다
    # 턴 C 의 앞단 둘. compose 에 자리가 없고(포트 8500 은 차선 E 전용 형상이다),
    # 상한은 **띄우는 명령**에 산다 — `docs/agent/RUNBOOK_로컬기동.md` STEP 2A.
    "gx-nginx-e": None,
    "gx-gunicorn-e": None,
}


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list[tuple[str, bool, str]]:
    out = []
    sinks = facts.get("sinks")
    if sinks is None:
        return [("① 수집기 전수", False, "**못 쟀다** — 도커에 닿지 못했다"),
                ("② 보존 기간", False, "못 쟀다"),
                ("③ 자라는 속도", False, "못 쟀다")]

    unknown = [s["name"] for s in sinks if s.get("retention") is None]
    # ★ 「전수」는 **목록이 신선할 때만** 전수다. 떠 있는데 목록에 없는 우리 컨테이너가
    #   있으면 이 판정기는 그만큼 눈이 먼 것이고, 그 상태의 초록은 거짓이다.
    #   [실측 2026-09-05 · 턴 D] 실제로 둘(`gx-nginx-e`·`gx-gunicorn-e`)이 빠져 있었다.
    unlisted = facts.get("unlisted") or []
    out.append(("① 수집기 전수", not unknown and not unlisted,
                "수집기 %d개를 전수로 셌다" % len(sinks) if not unknown and not unlisted
                else ("보존 정책을 **못 읽은** 수집기: %s" % ", ".join(unknown)
                      if unknown else "")
                     + ("" if not (unknown and unlisted) else " · ")
                     + ("**목록에 없는데 떠 있는 컨테이너**: %s — 목록이 낡은 만큼 "
                        "이 판정기는 눈이 멀었다. `PROJECT_CONTAINERS` 에 넣어라"
                        % ", ".join(unlisted) if unlisted else "")))

    forever = [s["name"] for s in sinks if s.get("retention") == "무한"]
    out.append(("② 보존 기간", not forever,
                "%d개 전부에 보존 기간이 있다" % len(sinks) if not forever
                else "**보존 기간이 없다**(무한 적재): %s" % ", ".join(forever)))

    unmeasured = [s["name"] for s in sinks if s.get("bytes_per_hour") is None]
    out.append(("③ 자라는 속도", not unmeasured,
                "%d개의 한 시간 치를 쟀다" % len(sinks) if not unmeasured
                else "속도를 **못 잰** 수집기: %s" % ", ".join(unmeasured)))

    # ── ④ 선언 — **고치는 자리에 값이 적혀 있는가** (2026-09-24) ──────────────
    #
    # ★ ②와 무엇이 다른가. ②는 「지금 돌고 있는 것에 상한이 걸려 있는가」이고
    #   ④는 「다음에 뜰 것에 상한이 걸리는가」다. 둘을 합치면 **재기동만 하면
    #   고쳐지는 상태**와 **아무도 안 고친 상태**가 같아 보인다. 앞엣것은 「선언은
    #   섰고 적용은 다음 재기동」이고 뒤엣것은 그냥 빨강이다(D-301).
    decl = facts.get("declarations")
    if decl is None:
        out.append(("④ 선언", False,
                    "**못 쟀다** — compose 파일을 읽지 못했다 (PyYAML 없음/파일 없음). "
                    "회색은 초록이 아니다"))
    else:
        # ★ [2026-09-05 · 턴 D] **둘을 갈랐다.** 종전에는 「compose 선언이 없다」를
        #   전부 빨강으로 찍었는데, 그러면 `docker run` 으로만 뜨는 앞단 둘
        #   (`gx-nginx-e`·`gx-gunicorn-e`)은 상한이 **실제로 걸려 있어도** 영원히
        #   빨강이 된다 — 지울 수 없는 빨강은 다음 사람이 그냥 무시한다.
        #   그래서 빨강은 **상한이 실제로 없는 것**에만 남긴다:
        #     · compose 선언도 없고 상한도 안 걸림 → **빨강** (아무도 안 막았다)
        #     · compose 선언은 없지만 상한은 걸림  → 경고 한 줄 (상한이 **명령**에 산다.
        #       그 명령은 RUNBOOK STEP 2A 이고, 다음에 띄우는 사람이 빠뜨리면 사라진다)
        naked = [s["name"] for s in sinks
                 if s.get("kind") == "docker" and not s.get("declared")
                 and s.get("retention") == "무한"]
        out.append(("④ 선언", not naked,
                    "컨테이너 수집기 전부에 상한이 **선언돼 있다**" if not naked
                    else "**선언할 자리조차 없는 수집기**: %s — compose 밖 "
                         "`docker run` 으로 떴다. **compose 를 고쳐도 닿지 않는다.** "
                         "상한은 `--log-opt max-size=10m --log-opt max-file=5` 로만 걸리고, "
                         "그 문장은 `docs/agent/RUNBOOK_로컬기동.md` STEP 2A 에 적혀 있다 — "
                         "이 빨강은 **다음에 그 컨테이너를 띄우는 사람**이 지운다"
                         % ", ".join(naked)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════
def docker(*args: str, timeout: int = 300, binary: bool = False):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    p = subprocess.run(["docker", *args], capture_output=True, timeout=timeout, env=env)
    if binary:
        return p.returncode, p.stdout, p.stderr
    return (p.returncode,
            p.stdout.decode("utf-8", "replace").strip(),
            p.stderr.decode("utf-8", "replace").strip())


def compose_declarations() -> dict | None:
    """compose 파일의 `services.*.logging` 을 읽는다. **값을 여기서 정하지 않는다.**

    돌려주는 것: `{서비스이름: {"driver":…, "max-size":…, "max-file":…}}`.
    못 읽으면 `None` — **「선언이 없다」가 아니라 「못 읽었다」다**(D-301).
    """
    try:
        import yaml
    except ImportError:
        return None
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out: dict = {}
    read_any = False
    for fname in COMPOSE_FILES:
        path = os.path.join(root, fname)
        if not os.path.exists(path):
            continue
        try:
            with io.open(path, encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
        except Exception:                              # noqa: BLE001
            continue
        read_any = True
        for svc, body in (doc.get("services") or {}).items():
            log = (body or {}).get("logging") or {}
            opts = log.get("options") or {}
            out[svc] = {"file": fname, "driver": log.get("driver"),
                        "max-size": opts.get("max-size"),
                        "max-file": opts.get("max-file")}
    return out if read_any else None


def _compose_service_of(name: str) -> tuple[str | None, str]:
    """이 컨테이너의 **선언 자리**는 어느 compose 서비스인가.

    compose 가 만든 컨테이너는 라벨이 답한다 — 짐작하지 않는다. 라벨이 없으면
    `docker run` 으로 뜬 것이고, 그때만 `ADHOC_TO_SERVICE` 표를 본다.
    """
    rc, out, _ = docker("inspect", name, "--format",
                        '{{index .Config.Labels "com.docker.compose.service"}}')
    svc = out.strip() if rc == 0 else ""
    if svc and svc != "<no value>":
        return svc, "compose 라벨"
    return ADHOC_TO_SERVICE.get(name), "docker run — 이름 대응표"


def container_sinks(declarations: dict | None = None) -> list[dict]:
    sinks = []
    for name in PROJECT_CONTAINERS:
        rc, out, _ = docker("inspect", name, "--format", "{{json .HostConfig.LogConfig}}")
        if rc != 0:
            continue
        try:
            cfg = json.loads(out)
        except ValueError:
            cfg = {}
        opts = cfg.get("Config") or {}
        driver = cfg.get("Type")
        max_size, max_file = opts.get("max-size"), opts.get("max-file")
        if driver == "json-file" and not max_size:
            # ★ `max-size` 가 없으면 도커는 **자르지 않는다.** 디스크가 찰 때까지 쌓인다.
            retention = "무한"
            detail = "드라이버 %s · max-size 없음 · max-file 없음" % driver
        elif driver == "json-file":
            retention = "%s × %s" % (max_size, max_file or "1")
            detail = "드라이버 %s · 회전 %s" % (driver, retention)
        elif driver in ("none",):
            retention = "0 (수집 안 함)"
            detail = "드라이버 none — 로그를 버린다"
        else:
            retention = None                    # 모르는 드라이버는 **모른다**고 적는다
            detail = "드라이버 %s — 이 판정기가 모르는 드라이버다" % driver

        # ── 선언은 어디에 있는가 — **적용과 따로 읽는다** ────────────────
        svc, how = _compose_service_of(name)
        declared, decl_note = False, ""
        if declarations is None:
            decl_note = "선언을 **못 읽었다**"
        elif svc is None:
            decl_note = ("compose 에 대응 서비스가 **없다**(%s) — "
                         "`docker run --log-opt` 로만 걸린다" % how)
        else:
            d = declarations.get(svc)
            if d and d.get("max-size"):
                declared = True
                decl_note = "%s::%s 에 %s × %s 로 선언돼 있다 (%s)" % (
                    d["file"], svc, d["max-size"], d.get("max-file") or "1", how)
            else:
                decl_note = "%s 서비스에 `logging` 선언이 없다 (%s)" % (svc, how)

        if declared and retention == "무한":
            # ★ 이 자리가 이번 판의 요점이다. **선언은 섰고 적용이 안 됐다** —
            #   도커의 LogConfig 는 컨테이너를 만들 때 굳으므로, 다음 재기동에
            #   걸린다. 그냥 「무한」으로만 적으면 아무도 안 고친 것과 같아 보인다.
            detail = ("%s · **선언은 섰다 · 적용은 다음 재기동** — %s"
                      % (detail, decl_note))
        else:
            detail = "%s · %s" % (detail, decl_note)

        rc, blob, _ = docker("logs", "--since", "%dm" % WINDOW_MINUTES, name,
                             binary=True)
        per_hour = len(blob) if rc == 0 else None
        sinks.append({"name": "컨테이너 stdout · %s" % name,
                      "kind": "docker", "retention": retention,
                      "declared": declared, "declaration": decl_note,
                      "detail": detail, "bytes_per_hour": per_hour})
    return sinks


def running_containers() -> list[str]:
    rc, out, _ = docker("ps", "--format", "{{.Names}}")
    return [n.strip() for n in out.splitlines() if n.strip()] if rc == 0 else []


def unlisted_containers() -> list[str]:
    """떠 있는데 `PROJECT_CONTAINERS` 에 없는 **우리** 컨테이너.

    ★ 이것이 ⑤다. 목록으로 세는 판정기는 목록이 낡는 만큼 눈이 먼다 —
      그런데 **눈이 먼 채로 「전수」라고 적는다**. 그 초록이 이 절에서 가장 위험하다.
      [실측 2026-09-05 · 턴 D] 턴 C 의 앞단 둘이 그렇게 빠져 있었다.
    """
    known = set(PROJECT_CONTAINERS)
    out = []
    for name in running_containers():
        if name in known:
            continue
        low = name.lower()
        if any(h in low for h in PROJECT_NAME_HINTS):
            out.append(name)
    return out


#: `[05/Sep/2026:06:17:51 +0000]` — nginx 기본 `$time_local`.
_ACCESS_TIME = re.compile(r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}) ([+-]\d{4})\]")


def _parse_access_time(line: str):
    m = _ACCESS_TIME.search(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1) + m.group(2), "%d/%b/%Y:%H:%M:%S%z")
    except ValueError:
        return None


def file_sinks() -> list[dict]:
    """**컨테이너 안에서 파일로** 쌓이는 로그. `--log-opt` 가 닿지 않는 자리다.

    한 시간 치는 **파일 자신의 시계**로 잰다 — 가장 최근 줄의 시각에서 60분을 뺀 것을
    창의 시작으로 삼는다. 호스트 시계와 컨테이너 시계가 어긋나도 그 어긋남이
    수에 섞이지 않는다.
    """
    sinks: list[dict] = []
    for cname, paths in CONTAINER_FILE_LOGS.items():
        for path in paths:
            rc, out, _ = docker("exec", cname, "sh", "-c",
                                "test -f %s && test ! -L %s && wc -c < %s"
                                % (path, path, path))
            if rc != 0 or not out.strip().isdigit():
                continue                       # 없으면 **없다고** 세지 않는다
            total = int(out.strip())
            rc, blob, _ = docker("exec", cname, "sh", "-c",
                                 "tail -c %d %s" % (FILE_TAIL_CAP, path), binary=True)
            per_hour, note = None, ""
            if rc == 0:
                lines = blob.decode("utf-8", "replace").splitlines(keepends=True)
                stamped = [(t, len(l.encode("utf-8", "replace")))
                           for l in lines for t in (_parse_access_time(l),) if t]
                if stamped:
                    newest = max(t for t, _ in stamped)
                    cutoff = newest - timedelta(minutes=WINDOW_MINUTES)
                    per_hour = sum(n for t, n in stamped if t >= cutoff)
                    if total > FILE_TAIL_CAP and stamped[0][0] >= cutoff:
                        note = " · 꼬리 %dMB 가 한 시간을 못 덮는다 — **이 이상**" % (
                            FILE_TAIL_CAP // (1024 * 1024))
            sinks.append({
                "name": "파일 · %s:%s" % (cname, path),
                "kind": "file",
                # ★ 도커 회전과 **무관하다.** `--log-opt` 는 stdout 에만 건다.
                "retention": "무한",
                "declared": False,
                "bytes_per_hour": per_hour,
                "detail": ("컨테이너 **안의 파일**(총 %s바이트) — `json-file` 회전 밖이다. "
                           "`--log-opt` 도 compose 의 `logging` 도 여기 닿지 않고, "
                           "`nginx:alpine` 에는 logrotate 가 없다%s"
                           % (format(total, ","), note)),
            })
    return sinks


#: gx-shell 안에서 돌 조각. **DB 에 직접 묻는다** — 화면이나 요약을 믿지 않는다.
DB_PROBE = r'''
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
out = {}
try:
    from core.logger.models import AuditLogs
    tab = AuditLogs._meta.db_table
    with connection.cursor() as c:
        c.execute("SELECT count(*) FROM %s" % tab); out["rows"] = c.fetchone()[0]
        c.execute("SELECT pg_total_relation_size(%s)", [tab]); out["bytes"] = c.fetchone()[0]
        # ★ 시각 칸의 이름을 **짐작하지 않는다** — 정보 스키마에게 묻는다.
        #   [실측 2026-09-04] 이 표의 시각 칸은 `create_datetime` 하나뿐이고,
        #   `created_on` 을 짐작한 첫 판은 조용히 0행을 셌다.
        c.execute("SELECT column_name FROM information_schema.columns "
                  "WHERE table_name=%s AND data_type LIKE 'timestamp%%'", [tab])
        cols = [r[0] for r in c.fetchall()]
        for pref in ("create_datetime", "created_on", "created_at"):
            if pref in cols:
                out["time_col"] = pref
                break
        else:
            out["time_col"] = cols[0] if cols else None
        out["time_col_candidates"] = cols
        if out["time_col"]:
            col = out["time_col"]
            c.execute('SELECT min("%s"), max("%s") FROM %s' % (col, col, tab))
            lo, hi = c.fetchone()
            out["oldest"], out["newest"] = str(lo), str(hi)
            c.execute("SELECT count(*) FROM %s WHERE \"%s\" >= now() - interval '1 hour'"
                      % (tab, col))
            out["rows_last_hour"] = c.fetchone()[0]
    out["table"] = tab
except Exception as exc:
    out["error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from core.configuration.utils import get_config_value_by_path
    # ★ 인자 둘이다: (name, fieldpath). dj-core 의 정리 태스크가 부르는 그대로 부른다 —
    #   한 인자로 부르면 TypeError 가 나고, 그 예외를 삼키면 「보존기간 없음」으로 보인다.
    out["retention_days"] = get_config_value_by_path(
        "System", "security.audit_log_retention_days", 90)
except Exception as exc:
    out["retention_days_error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from config.celery import app
    sched = app.conf.beat_schedule or {}
    out["purge_beat"] = {k: str(v.get("schedule")) for k, v in sched.items()
                         if "audit" in k or "audit" in str(v.get("task", ""))}
except Exception as exc:
    out["purge_beat_error"] = "%s: %s" % (type(exc).__name__, exc)

# ★ **선언과 도는 것은 다른 사실이다** (2026-09-05 · 턴 D).
#   `beat_schedule` 에 이름이 있다는 것은 「일정이 적혀 있다」일 뿐이다. 그 일정을
#   밀어 줄 beat 도, 밀린 것을 **실행할 워커**도 따로 떠야 한다. 워커가 0개면
#   purge 태스크는 큐에 쌓이거나 아예 안 생기고, 어느 쪽이든 **아무것도 안 지워진다.**
#   그러므로 여기서 **브로커에 닿는가**와 **워커가 붙어 있는가**를 갈라서 잰다:
#     · 브로커에 못 닿음  → **회색**(못 쟀다). 「워커 없음」이 아니다
#     · 브로커는 닿고 워커 0 → **빨강**. 보존 기간은 선언일 뿐 걸려 있지 않다
try:
    from config.celery import app as _app
    _conn = _app.connection()
    try:
        _conn.ensure_connection(max_retries=0, timeout=5)
        out["broker_reachable"] = True
    finally:
        try:
            _conn.release()
        except Exception:
            pass
except Exception as exc:
    out["broker_reachable"] = False
    out["broker_error"] = "%s: %s" % (type(exc).__name__, exc)

if out.get("broker_reachable"):
    try:
        _pong = _app.control.inspect(timeout=5.0).ping()
        out["celery_workers"] = sorted(_pong) if _pong else []
    except Exception as exc:
        out["celery_workers_error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from django.conf import settings
    out["file_handlers"] = sorted(
        n for n, h in (settings.LOGGING.get("handlers") or {}).items()
        if "FileHandler" in str(h.get("class", "")))
except Exception as exc:
    out["file_handlers_error"] = "%s: %s" % (type(exc).__name__, exc)

print("###JSON###" + json.dumps(out, ensure_ascii=False, default=str))
'''


def db_sink() -> tuple[dict | None, dict]:
    rc, out, err = docker("exec", "-w", "/app", "-e", "PYTHONPATH=/app",
                          "-e", "DJANGO_SETTINGS_MODULE=config.settings",
                          APP_CONTAINER, "python", "-c", DB_PROBE, timeout=300)
    marker = "###JSON###"
    if marker not in out:
        return None, {"error": (err or out)[-300:]}
    try:
        info = json.loads(out.split(marker, 1)[1].strip().splitlines()[0])
    except ValueError as exc:
        return None, {"error": str(exc)}

    if info.get("error"):
        return None, info
    days = info.get("retention_days")
    beat = info.get("purge_beat") or {}
    workers = info.get("celery_workers")
    extra = ""
    if not (days and beat):
        # ★ 설정은 있는데 도는 자리가 없다 — 착시 ⑨. **무한과 같다.**
        retention = "무한" if days else None
    elif info.get("broker_reachable") is not True:
        # 브로커에 못 닿았다 → **못 쟀다**. 「워커 없음」으로 적으면 회색을 빨강으로
        # 옮기는 것이고, 옮긴 색은 다음 사람이 못 되돌린다(D-301).
        retention = None
        extra = " · 브로커에 **못 닿았다**(%s) — 워커 유무를 못 쟀다" % (
            info.get("broker_error") or "사유 없음")
    elif workers is None:
        retention = None
        extra = " · 워커 조회가 **실패했다**(%s)" % info.get("celery_workers_error")
    elif not workers:
        # ★ **이 자리가 이번 판의 요점이다.** 일정은 적혀 있고 브로커도 살아 있는데
        #   그 태스크를 **실행할 워커가 0개**다. 지우는 자리가 안 돈다 = 안 지워진다.
        retention = "무한"
        extra = (" · ⚠ 보존 %s일이 **선언돼 있으나 지우는 워커가 0개다** — beat 일정 "
                 "`%s` 은 적혀 있고, 그것을 실행할 celery 워커가 브로커에 하나도 "
                 "붙어 있지 않다. **선언은 삭제가 아니다**" % (days, ", ".join(beat)))
    else:
        retention = "%s일 (beat %s · 워커 %d)" % (days, ", ".join(beat), len(workers))
        extra = " · 워커 %s" % ", ".join(workers)
    return {"name": "DB 감사 로그 · %s" % info.get("table", "?"),
            "kind": "db", "retention": retention,
            "detail": "행 %s개 · %s바이트 · 가장 오래된 %s%s"
                      % (info.get("rows"), info.get("bytes"), info.get("oldest"), extra),
            "bytes_per_hour": info.get("rows_last_hour")}, info


def self_test() -> int:
    ok = True
    ok &= all(not p for _, p, _ in judge({}))

    #: 선언이 다 서 있는 세상. `kind` 가 `docker` 인 것만 ④가 본다 —
    #: DB 수집기는 compose 가 만드는 것이 아니므로 선언 대상이 아니다.
    good = {"declarations": {"a": {"max-size": "10m"}},
            "sinks": [{"name": "a", "kind": "docker", "retention": "10m × 3",
                       "declared": True, "bytes_per_hour": 100},
                      {"name": "b", "kind": "db", "retention": "90일 (beat x)",
                       "bytes_per_hour": 5}]}
    ok &= all(p for _, p, _ in judge(good))

    forever = {"declarations": {}, "sinks": [
        {"name": "a", "kind": "docker", "retention": "무한",
         "declared": True, "bytes_per_hour": 100}]}
    r = judge(forever)
    ok &= [p for _, p, _ in r] == [True, False, True, True]

    unknown = {"declarations": {}, "sinks": [
        {"name": "a", "kind": "docker", "retention": None,
         "declared": True, "bytes_per_hour": 100}]}
    r = judge(unknown)
    ok &= [p for _, p, _ in r] == [False, True, True, True]

    blind = {"declarations": {}, "sinks": [
        {"name": "a", "kind": "docker", "retention": "10m × 3",
         "declared": True, "bytes_per_hour": None}]}
    r = judge(blind)
    ok &= [p for _, p, _ in r] == [True, True, False, True]

    # ── ④ **이번 판의 요점** ─────────────────────────────────────────────
    #   ㉠ compose 선언은 없지만 **상한은 걸려 있다**(`docker run --log-opt`).
    #      ④는 **빨강이 아니다** — 빨강은 「아무도 안 막았다」에만 남긴다.
    #      [2026-09-05 · 턴 D] 종전에는 이것도 빨강이었고, 그래서 `docker run` 으로만
    #      뜨는 앞단 둘은 상한이 걸려 있어도 영원히 빨강이었다. 지울 수 없는 빨강은
    #      다음 사람이 그냥 무시한다 — 무시되는 빨강은 방어선이 아니다.
    applied_not_declared = {"declarations": {}, "sinks": [
        {"name": "a", "kind": "docker", "retention": "10m × 3",
         "declared": False, "bytes_per_hour": 1}]}
    r = judge(applied_not_declared)
    ok &= [p for _, p, _ in r] == [True, True, True, True]

    #   ㉠′ 그러나 **선언도 없고 상한도 없으면** 빨강이다 — 아무도 안 막았다.
    naked_and_unlimited = {"declarations": {}, "sinks": [
        {"name": "a", "kind": "docker", "retention": "무한",
         "declared": False, "bytes_per_hour": 1}]}
    r = judge(naked_and_unlimited)
    ok &= [p for _, p, _ in r] == [True, False, True, False]

    #   ㉠″ ⑤ **목록 신선도** — 떠 있는데 목록에 없는 컨테이너가 있으면 ①은 초록이
    #      될 수 없다. 나머지가 다 멀쩡해도 그렇다: **여섯을 세고 「전수」라고 적는**
    #      것이 이 판정기가 낼 수 있는 가장 조용한 거짓말이다.
    stale_list = {"declarations": {"a": {"max-size": "10m"}},
                  "unlisted": ["gx-nginx-e"],
                  "sinks": [{"name": "a", "kind": "docker", "retention": "10m × 5",
                             "declared": True, "bytes_per_hour": 1}]}
    r = judge(stale_list)
    ok &= [p for _, p, _ in r] == [False, True, True, True]

    #   ㉠‴ **음성 대조** — 목록 밖이 없으면 같은 표가 초록이다(위 빨강이 다른 데서
    #      온 것이 아님을 못박는다)
    fresh_list = dict(stale_list, unlisted=[])
    ok &= all(p for _, p, _ in judge(fresh_list))

    #   ㉡ 선언은 섰는데 적용이 아직이다 → ②는 빨강, ④는 초록.
    #      「선언은 섰고 적용은 다음 재기동」이 정확히 이 모양이다.
    declared_not_applied = {"declarations": {"a": {"max-size": "10m"}}, "sinks": [
        {"name": "a", "kind": "docker", "retention": "무한",
         "declared": True, "bytes_per_hour": 1}]}
    r = judge(declared_not_applied)
    ok &= [p for _, p, _ in r] == [True, False, True, True]

    #   ㉢ compose 를 **못 읽었다** → ④는 초록이 아니다. 회색은 초록이 아니다(D-301)
    cannot_read = {"declarations": None, "sinks": [
        {"name": "a", "kind": "docker", "retention": "10m × 3",
         "declared": True, "bytes_per_hour": 1}]}
    r = judge(cannot_read)
    ok &= [p for _, p, _ in r] == [True, True, True, False]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    rc, _, err = docker("version", "--format", "{{.Server.Version}}")
    if rc != 0:
        print("판정 불가(exit 2): 도커에 닿지 못했다 — %s" % err)
        return EXIT_UNDECIDABLE

    say("## 1. 수집기를 전수로 센다")
    say()
    declarations = compose_declarations()
    sinks = container_sinks(declarations)
    sinks.extend(file_sinks())
    unlisted = unlisted_containers()
    if unlisted:
        say("⚠ **떠 있는데 목록에 없는 컨테이너**: %s" % ", ".join(unlisted))
        say("  이 판정기는 `PROJECT_CONTAINERS` 로 센다 — 목록이 낡은 만큼 눈이 먼다.")
        say("  그리고 눈이 먼 채로 「전수」라고 적는다. 그래서 ①을 빨강으로 둔다.")
        say()
    dbs, dbinfo = db_sink()
    if dbs is not None:
        sinks.append(dbs)
    else:
        say("⚠ DB 수집기를 **못 쟀다** — %s" % dbinfo.get("error"))
        say("  「0건」이 아니라 「못 쟀다」다. 못 잰 것을 통과로 적지 않는다(D-301).")
        say()

    say("| 수집기 | 보존 기간 | 한 시간 치 [실측] | 하루 환산 [추정] | 비고 |")
    say("|---|---|---|---|---|")
    for s in sinks:
        per_h = s.get("bytes_per_hour")
        unit = "행" if s.get("kind") == "db" else "바이트"
        say("| %s | %s | %s%s | %s%s | %s |"
            % (s["name"], s.get("retention") or "**모름**",
               format(per_h, ",") if per_h is not None else "못 쟀다", unit if per_h is not None else "",
               format(per_h * 24, ",") if per_h is not None else "—",
               unit if per_h is not None else "",
               s.get("detail", "")))
    say()

    say("### 선언 — **다음에 뜰 컨테이너에는 걸리는가** [실측]")
    say()
    if declarations is None:
        say("  ⚠ compose 파일을 **못 읽었다**(PyYAML 없음/파일 없음). 「선언이 없다」가")
        say("    아니라 「못 읽었다」다 — 회색은 초록이 아니다(D-301).")
    else:
        say("| compose 서비스 | 파일 | 드라이버 | max-size | max-file |")
        say("|---|---|---|---|---|")
        for svc, d in sorted(declarations.items()):
            say("| `%s` | %s | %s | %s | %s |"
                % (svc, d["file"], d.get("driver") or "**없음**",
                   d.get("max-size") or "**없음**", d.get("max-file") or "**없음**"))
        say()
        say("★ **선언과 적용은 다른 사실이다.** 도커의 `LogConfig` 는 컨테이너를 **만들 때**")
        say("  굳는다 — 위 선언은 이미 떠 있는 컨테이너에 닿지 않는다. 그래서 ②(적용)는")
        say("  빨간 채로 두고 ④(선언)를 따로 둔다. ②가 초록이 되는 것은 **다음 재기동**")
        say("  때이고, 지금 재기동하지 않는 이유는 다른 차선 셋이 이 컨테이너 위에서")
        say("  일하고 있기 때문이다 — 그것은 판정기가 정할 일이 아니다.")
        say()
        say("★ **보존 기간은 [판정]이다** — `max-size 10m × max-file 5` = 컨테이너당 **50MB 상한**.")
        say("  근거는 `docker-compose.yml` 머리말에 실측과 함께 적혀 있다. 요약하면:")
        say("  가장 시끄러운 수집기(postgres · 363 KB/일 [실측])에 대해 50MB 는 약 140일 치이고,")
        say("  그런데도 **「N일 보존」이라고 적지 않는다** — `json-file` 회전은 크기 기반이라")
        say("  조용한 달에는 더 오래 남고 시끄러운 날에는 몇 시간 만에 밀린다. 약속할 수 있는")
        say("  것은 상한이지 기간이 아니다. **감사에 답하는 정본은 DB 감사 로그(90일)** 이고,")
        say("  컨테이너 stdout 은 운영 디버깅용 **단기 버퍼**다 — 이 판정이 없으면 상한을 거는")
        say("  일이 곧 「증거를 지우는 일」이 된다.")
    say()

    if dbs is not None:
        say("### DB 감사 로그의 자세한 사실")
        say()
        say("```")
        for k in ("table", "time_col", "time_col_candidates", "rows", "bytes",
                  "oldest", "newest", "rows_last_hour", "retention_days",
                  "purge_beat", "file_handlers"):
            if k in dbinfo:
                say("%-22s %s" % (k, dbinfo[k]))
        for k in sorted(dbinfo):                 # 못 읽은 것은 **못 읽었다고** 적는다
            if k.endswith("_error"):
                say("%-22s %s" % (k, dbinfo[k]))
        say("```")
        say()
        fh = dbinfo.get("file_handlers")
        if fh is not None:
            say("★ **파일 수집기는 %d개다.** `settings.LOGGING` 의 핸들러 중 `FileHandler` 는 %s — "
                % (len(fh), fh or "없다"))
            say("  즉 로그 파일이 디스크에 직접 쌓이는 자리는 없고, 전부 stdout 과 DB 로 간다.")
            say("  logrotate 를 찾을 이유가 없다는 뜻이고, 그 사실을 **찾아보고** 적는다.")
            say()

    say("## 2. 판정")
    say()
    facts = {"sinks": sinks, "declarations": declarations, "unlisted": unlisted}
    rows = judge(facts)
    for name, passed, why in rows:
        say("  %s %-14s %s" % ("OK  " if passed else "FAIL", name, why))
    ok = all(p for _, p, _ in rows)
    say()
    say("판정 **%s**." % ("통과" if ok else "실패"))
    say()
    # ★ 꼬리말을 **판정 결과에서 만든다.** 고정 문장으로 두면 「④가 초록인 것을」이라고
    #   적어 두고 ④가 빨간 날에도 그대로 나간다 — 보고서가 자기 표와 어긋나는 자리다.
    waiting = [s2["name"] for s2 in sinks
               if s2.get("kind") == "docker" and s2.get("declared")
               and s2.get("retention") == "무한"]
    naked = [s2["name"] for s2 in sinks
             if s2.get("kind") == "docker" and not s2.get("declared")]
    if waiting:
        say("**선언은 섰고 적용은 다음 재기동**인 수집기 %d개: %s"
            % (len(waiting), ", ".join(waiting)))
        say("  고치는 자리(`docker-compose.yml` 의 `logging.options`)에는 값이 **섰고**,")
        say("  이미 떠 있는 컨테이너에는 **닿지 않았다** — 도커의 `LogConfig` 는 컨테이너를")
        say("  **만들 때** 굳는다. 그러므로 ②는 다음 재기동에 초록이 된다.")
        say("  **지금 재기동하지 않는다** — 다른 차선이 `gx-shell`·`postgres`·`minio` 위에서")
        say("  동시에 일하고 있다. 그것은 판정기가 정할 일이 아니다.")
        say()
    if naked:
        say("**선언할 자리조차 없는 수집기 %d개**: %s" % (len(naked), ", ".join(naked)))
        say("  compose 밖에서 `docker run` 으로 떴다. 이 빨강은 compose 를 고쳐서는")
        say("  안 지워진다 — **다음에 그 컨테이너를 띄우는 사람**이 `--log-opt` 를 붙여야")
        say("  지워진다(`docs/agent/RUNBOOK_로컬기동.md` STEP 2A).")
        say()
    if not waiting and not naked:
        say("컨테이너 수집기 전부에 상한이 **걸려 있고 선언돼 있다.**")

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-07 — 로그 수집기를 전수로 쟀다 (%s)\n\n"
                        % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_log_collectors.py` 가 실행하며 적었다.**\n"
                        "한 시간 치는 [실측]이고 하루 환산은 [추정]이다 — 갈라서 적었다.\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
