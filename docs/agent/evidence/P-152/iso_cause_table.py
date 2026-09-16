#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-152 — **남은 502 열 건의 원인표** (2026-09-16 · 턴 R · 차선 E).

    python docs/agent/evidence/P-152/iso_cause_table.py            # B 한 벌 · 3,600 요청
    python docs/agent/evidence/P-152/iso_cause_table.py --smoke    # 배관 확인 · 300 요청

무엇이 남았나 — 턴 Q 가 세운 자리
---------------------------------
[실측 2026-09-15 · P-137] 격리에서 앞단 peer 를 한 줄 → 세 줄로 놓자
3,600 요청당 502 가 **29·33 → 10·11** 로 줄었다. 재시도가 절반을 먹었고
**나머지 절반은 재시도로 안 사라진다.** 그 「나머지」가 무엇인지는 그날 안 쟀다 —
`samples_502` 에 여섯 줄만 남겼고 열 건 각각의 사연은 없다.

세종 판정 P-152: **원인표 없이 OPS-13b 를 본 서버에 켜지 않는다.**

그래서 이 파일은 **같은 격리 B 판을 한 번 더 돌리고, 502 를 한 건도 빠뜨리지 않고**
넷을 적는다 — **요청 · 워커 상태 · 시각 · 분류**.

무엇으로 분류하는가 — **per-request 사실만 분류에 쓴다**
--------------------------------------------------------
  ㉠ `$upstream_addr` 의 칸 수와 `gx_app` 유무      ← 그 요청 하나의 사실
  ㉡ `$upstream_response_time` 의 칸별 시간         ← 그 요청 하나의 사실
  ㉢ **요청이 살아 있던 구간** 안의 뒷단 자국       ← µs 까지 맞댄다. pid 까지 적는다
     (`Worker exiting` = 연결이 실제로 끊기는 순간 · `Booting worker` = 새 워커)
  ㉣ 앞단 오류로그의 문구                            ← **초 단위**라 그 요청의 것이라고
     단정할 수 없다. **보조 증거로만** 적고 분류를 혼자 결정하지 못하게 한다.

★ ㉣ 를 분류의 주역으로 쓰지 않는 까닭: 3,600 요청에 `recv() failed (104` 가 230줄이다.
  초로 맞대면 **무엇이든** 그 옆에 놓인다 — `verify_front_line_502` 가 창을 넓힐 때마다
  배운 그 자리(음성 대조 없이 넓힌 창은 아무것도 안 가른다)와 같은 함정이다.

★ 격리의 뜻은 `iso_run.py` 와 같다 — 새 컨테이너 넷만 만들고 지운다 · 뒷단 소스는
  읽기 전용 · 감사 쓰기는 임시 redis 로 떼어 공용 브로커·DB 에 한 건도 안 보낸다.
  **본 서버·운영계에 아무것도 보내지 않는다.**
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_front_line_502 as J  # noqa: E402

REPO = str(ROOT).replace("\\", "/")
NET = "gx-main-network"
IMG_BACK, IMG_FRONT, IMG_REDIS = "guardianx-backend:latest", "nginx:alpine", "redis:latest"
SRC_BACK = "gx-gunicorn-e"
REDIS_ISO, BACK_ISO, FRONT_ISO, LOAD_ISO = ("gx-redis-i152", "gx-gunicorn-i152",
                                            "gx-nginx-i152", "gx-load-i152")
MINE = (FRONT_ISO, LOAD_ISO, BACK_ISO, REDIS_ISO)
UNTOUCHED = ("gx-shell", "gx-gunicorn-e", "gx-nginx-e", "gx-celery-e", "gx-beat-e",
             "postgres", "redis", "guardianx-source-minio-1",
             "guardianx-source-mailpit-1", "gx-fe-build")
ISO_DIR = HERE / "iso"
PROBE_PATH = "/admin/login/"
CONC = 10
MAX_REQ, JITTER, GRACE = 50, 10, 30          # P-137 B 판과 **같은 값** — 같은 자리를 다시 재려고
SKIP_ENV = {"PATH", "LANG", "GPG_KEY", "PYTHON_VERSION", "PYTHON_SHA256",
            "LD_LIBRARY_PATH", "HOME", "HOSTNAME"}
ORIG_UPSTREAM = "server gx-gunicorn-e:8000 max_fails=0;"
ISO_UPSTREAM = "server %s:8000 max_fails=0;" % BACK_ISO

_NGX_ERR_TS = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\]")
_PID = re.compile(r"\(pid:? ?(\d+)\)")
ERR_MARKS = ("recv() failed (104", "upstream prematurely closed", "connect() failed (111",
             "no live upstreams", "upstream timed out", "writev() failed")


def dk(*args, env_extra=None, inp=None, timeout=900):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(["docker", *args], input=inp, capture_output=True, env=env,
                       timeout=timeout)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def existing(names) -> list:
    _, out, _ = dk("ps", "-a", "--format", "{{.Names}}")
    have = set(out.split())
    return [n for n in names if n in have]


def started(names) -> dict:
    res = {}
    for n in names:
        rc, out, _ = dk("inspect", n, "--format",
                        "{{.State.StartedAt}} {{.State.Status}} restarts={{.RestartCount}}")
        res[n] = out.strip() if rc == 0 else None
    return res


def render_conf() -> dict:
    src = (ROOT / "nginx" / "gx-front.conf").read_text(encoding="utf-8")
    if src.count(ORIG_UPSTREAM) != 1:
        raise SystemExit("[P-152] nginx/gx-front.conf 의 upstream 한 줄을 못 찾았다 — 멈춘다")
    body = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith("#") and l.strip())
    head = ("# P-152 격리 설정 — **생성물**. docs/agent/evidence/P-152/iso_cause_table.py 가\n"
            "#   nginx/gx-front.conf 에서 주석을 걷고 upstream 의 server 줄만 세 줄로 폈다(P-137 B 와 같은 모양).\n"
            "#   ⚠ nginx/ 아래에 두지 않은 까닭: verify_live_freshness 가 gx-nginx-e 를 nginx/**.conf 의\n"
            "#     시각으로 잰다 — 거기 새 .conf 가 생기면 도는 앞단이 「낡았다」로 읽힌다(거짓 빨강).\n")
    ISO_DIR.mkdir(exist_ok=True)
    b = head + "# B — 같은 peer 세 줄: tries 3 이 세 번 다 peer 로 간다\n" + body.replace(
        ORIG_UPSTREAM, "\n        ".join([ISO_UPSTREAM] * 3)) + "\n"
    (ISO_DIR / "gx-front-iso-B.conf").write_text(b, encoding="utf-8", newline="\n")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    return {"gx-front.conf": sha(ROOT / "nginx" / "gx-front.conf"),
            "gx-proxy.inc": sha(ROOT / "nginx" / "gx-proxy.inc"),
            "generated/gx-gate.conf": sha(ROOT / "nginx" / "generated" / "gx-gate.conf"),
            "iso/gx-front-iso-B.conf": sha(ISO_DIR / "gx-front-iso-B.conf")}


def back_env() -> dict:
    _, out, _ = dk("inspect", SRC_BACK, "--format", "{{json .Config.Env}}")
    env = dict(e.split("=", 1) for e in json.loads(out) if "=" in e)
    env = {k: v for k, v in env.items() if k not in SKIP_ENV}
    env["REDIS_HOST"] = "redis://%s:6379" % REDIS_ISO     # 감사 쓰기를 공용 브로커에서 뗀다
    return env


def wait_for(name: str, needle: str, count: int = 1, timeout: int = 180) -> bool:
    t = time.time()
    while time.time() - t < timeout:
        _, out, err = dk("logs", name)
        if (out + err).count(needle) >= count:
            return True
        _, st, _ = dk("inspect", name, "--format", "{{.State.Status}}")
        if st.strip() != "running":
            return False
        time.sleep(1)
    return False


def start_back(env: dict) -> None:
    args = ["run", "-d", "--name", BACK_ISO, "--network", NET, "--entrypoint", "python",
            "-w", "/app", "-v", REPO + "/backend:/app:ro",
            "--log-opt", "max-size=20m", "--log-opt", "max-file=5"]
    passthru = {}
    for k in sorted(env):
        if env[k] == "":
            args += ["-e", k + "="]
        else:
            args += ["-e", k]                 # 값 없는 형태 — 값은 명령줄에 안 실린다
            passthru[k] = env[k]
    args += [IMG_BACK, "-m", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000",
             "--workers", "4", "--threads", "4", "--worker-class", "gthread", "--timeout", "120",
             "--access-logfile", "-", "--error-logfile", "-",
             "--max-requests", str(MAX_REQ), "--max-requests-jitter", str(JITTER),
             "--graceful-timeout", str(GRACE)]
    rc, _, err = dk(*args, env_extra=passthru)
    if rc != 0:
        raise RuntimeError("iso 뒷단을 못 띄웠다: %s" % err.strip()[:300])
    if not wait_for(BACK_ISO, "Booting worker", 4):
        _, out, err = dk("logs", "--tail", "40", BACK_ISO)
        raise RuntimeError("iso 뒷단이 안 섰다: %s"
                           % [l[:200] for l in (out + err).splitlines() if "rror" in l][:6])


def start_front() -> dict:
    conf = "gx-front-iso-B.conf"
    rc, _, err = dk("run", "-d", "--name", FRONT_ISO, "--network", NET,
                    "-v", REPO + "/nginx:/etc/nginx/gx:ro",
                    "-v", str(ISO_DIR).replace("\\", "/") + ":/etc/nginx/iso:ro",
                    "--log-opt", "max-size=20m", "--log-opt", "max-file=5",
                    IMG_FRONT, "nginx", "-c", "/etc/nginx/iso/" + conf, "-g", "daemon off;")
    if rc != 0:
        raise RuntimeError("iso 앞단을 못 띄웠다: %s" % err.strip()[:300])
    time.sleep(2)
    rc, dump, _ = dk("exec", FRONT_ISO, "nginx", "-T", "-c", "/etc/nginx/iso/" + conf)
    return {"nginx_T_rc": rc, "peer_lines": dump.count(ISO_UPSTREAM),
            "tries_3": dump.count("proxy_next_upstream_tries 3;"),
            "next_upstream": dump.count("proxy_next_upstream error timeout http_502;"),
            "non_idempotent": dump.count("non_idempotent")}


LOAD = r'''
import concurrent.futures, datetime, json, time, urllib.error, urllib.request
BASE = "http://%(front)s:8500"; PATH = "%(path)s"; N = %(n)d; C = %(c)d
def get(u, t=30):
    try:
        req = urllib.request.Request(u, headers={"X-GX-Probe": "p152-iso"})
        with urllib.request.urlopen(req, timeout=t) as r:
            r.read(); return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0
for _ in range(60):
    if get(BASE + "/_front/health", 5) == 200: break
    time.sleep(0.5)
warm = [get(BASE + PATH) for _ in range(40)]
time.sleep(1.5)
t0 = datetime.datetime.now(datetime.timezone.utc)
codes = {}
with concurrent.futures.ThreadPoolExecutor(C) as ex:
    for code in ex.map(lambda i: get(BASE + PATH), range(N)):
        codes[code] = codes.get(code, 0) + 1
t1 = datetime.datetime.now(datetime.timezone.utc)
print("GXLOAD " + json.dumps({"t0": t0.strftime("%%H:%%M:%%S"), "t1": t1.strftime("%%H:%%M:%%S"),
      "t0_iso": t0.isoformat(), "t1_iso": t1.isoformat(), "n": N, "concurrency": C,
      "elapsed_s": round((t1 - t0).total_seconds(), 2),
      "warmup_codes": {str(k): warm.count(k) for k in set(warm)},
      "codes": {str(k): v for k, v in sorted(codes.items())}}))
'''


def run_load(n: int) -> dict:
    script = LOAD % {"front": FRONT_ISO, "path": PROBE_PATH, "n": n, "c": CONC}
    rc, out, err = dk("run", "--rm", "-i", "--name", LOAD_ISO, "--network", NET,
                      "--entrypoint", "python", IMG_BACK, "-",
                      inp=script.encode("utf-8"), timeout=1800)
    line = next((l for l in out.splitlines() if l.startswith("GXLOAD ")), "")
    if not line:
        raise RuntimeError("부하가 답하지 않았다 (rc=%d): %s" % (rc, err.strip()[-300:]))
    return json.loads(line[len("GXLOAD "):])


def parse_ts(line: str):
    m = J._DOCKER_TS_US.match(line)
    if not m:
        return None
    return (datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            + timedelta(microseconds=int((m.group(2) + "000000")[:6])))


def back_marks(t0: datetime, t1: datetime) -> list:
    """뒷단 자국 — `(시각, 종류, pid)`. µs 까지 읽는다(초로 자르면 자국을 흘린다 · 턴 J)."""
    _, bo, be = dk("logs", "-t", BACK_ISO)
    out = []
    for l in (bo + "\n" + be).splitlines():
        kind = None
        if "Autorestarting" in l:
            kind = "Autorestarting"
        elif "Worker exiting (pid" in l and "cleaning" not in l:
            kind = "Worker_exiting"
        elif "Booting worker" in l:
            kind = "Booting_worker"
        if kind is None:
            continue
        ts = parse_ts(l)
        if ts is None or not (t0 <= ts <= t1):
            continue
        pid = _PID.search(l)
        out.append({"at": ts, "kind": kind, "pid": int(pid.group(1)) if pid else None})
    return sorted(out, key=lambda m: m["at"])


def front_errors(t0: datetime, t1: datetime) -> list:
    """앞단 오류로그 — `(시각(초), 문구)`. **초 단위**라 보조 증거로만 쓴다."""
    _, _, err = dk("logs", FRONT_ISO)
    out = []
    for l in err.splitlines():
        m = _NGX_ERR_TS.match(l)
        if not m:
            continue
        ts = datetime.strptime(m.group(1), "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if not (t0 - timedelta(seconds=2) <= ts <= t1 + timedelta(seconds=2)):
            continue
        mark = next((k for k in ERR_MARKS if k in l), "기타")
        out.append({"at": ts, "mark": mark, "line": l[:300]})
    return out


def classify(row: dict) -> tuple:
    """**per-request 사실만으로** 분류한다. 돌려주는 것: `(분류, 근거)`.

    ★ 앞단 오류로그(초 단위)는 여기 안 들어온다 — 보조 증거로 표에만 적는다.
    """
    tries = row["upstream_addrs"]
    times = row["upstream_times"]
    n_peer = sum(1 for a in tries if a != "gx_app")
    exhausted = tries and tries[-1] == "gx_app"
    exits = [m for m in row["marks_in_span"] if m["kind"] == "Worker_exiting"]
    slow = [t for t in times if t is not None and t >= 1.0]
    instant = [t for t in times if t is not None and t < 0.05]

    if any(t is not None and t >= 14.0 for t in times):
        return ("타임아웃", "한 시도가 %.3f초 — 앞단 `proxy_*_timeout 15s` 에 닿았다"
                % max(t for t in times if t is not None))
    if exhausted and n_peer >= 3:
        base = "재시도 3회 소진(`no live upstreams`)"
        if exits and len(instant) >= 2:
            return (base + " · 워커 재활용 순간",
                    "요청 구간 안에 `Worker exiting` %d건(pid %s) · 시도 %d/%d 가 0.05초 미만 — "
                    "죽어 가는 워커의 연결을 연달아 집었다"
                    % (len(exits), ",".join(str(m["pid"]) for m in exits),
                       len(instant), len(times)))
        if exits and slow:
            return (base + " · 느린 시도 뒤 재활용",
                    "첫 시도가 %.3f초 매달렸다가 끊겼고 구간 안에 `Worker exiting` %d건(pid %s)"
                    % (max(slow), len(exits), ",".join(str(m["pid"]) for m in exits)))
        if exits:
            return (base + " · 워커 재활용 순간",
                    "요청 구간 안에 `Worker exiting` %d건(pid %s)"
                    % (len(exits), ",".join(str(m["pid"]) for m in exits)))
        return (base + " · **자국 없음**",
                "요청 구간 안에 `Worker exiting` 이 **0건**이다 — 재활용으로 설명되지 않는다. "
                "**알려진 창에 묻지 마라**")
    if not exhausted and n_peer == 1:
        return ("재시도 없이 나간 502(OPS-13b 모양)",
                "`$upstream_addr` 가 한 칸이다 — peer 가 하나면 새 연결의 실패에 남은 시도가 0 이다")
    return ("미분류", "시도 %d칸 · 소진 %s · 구간 안 `Worker exiting` %d건"
            % (len(tries), exhausted, len(exits)))


def build_rows(load: dict, marks: list, errs: list) -> tuple:
    _, out, _ = dk("logs", FRONT_ISO)
    acc = [l for l in out.splitlines() if J._ACCESS.match(l)]
    win = J.clip_by_time(acc, load["t0"], load["t1"])
    st, attempts, shapes = Counter(), Counter(), Counter()
    retried = rescued = 0
    rows = []
    for l in win:
        m = J._ACCESS.match(l)
        status, up = m.group("status"), m.group("up")
        addrs = [x.strip() for x in up.split(",") if x.strip()]
        st[status] += 1
        attempts[len(addrs)] += 1
        if len(addrs) > 1:
            retried += 1
            rescued += status.startswith("2")
        if status != "502":
            continue
        when = datetime.strptime(m.group("t") + m.group("tz"), "%d/%b/%Y:%H:%M:%S%z")
        try:
            rt = float(m.group("rt"))
        except (TypeError, ValueError):
            rt = 0.0
        tail = l[l.rindex('"') + 1:].strip()
        times = []
        for x in tail.split(","):
            try:
                times.append(float(x.strip()))
            except ValueError:
                times.append(None)
        lo, hi = when - timedelta(seconds=max(rt, 0.0)), when + timedelta(seconds=1)
        in_span = [dict(m2, at=m2["at"].isoformat(timespec="microseconds"))
                   for m2 in marks if lo <= m2["at"] < hi]
        near_err = Counter(e["mark"] for e in errs if lo <= e["at"] < hi)
        shapes[", ".join("gx_app" if a == "gx_app" else "peer" for a in addrs)] += 1
        row = {"n": len(rows) + 1,
               "at": when.isoformat(timespec="seconds"),
               "span": "[%s − %.3fs, +1s)" % (when.strftime("%H:%M:%S"), rt),
               "request": m.group("req"), "status": status, "request_time": rt,
               "upstream_addrs": addrs, "upstream_times": times,
               "shape": ", ".join("gx_app" if a == "gx_app" else "peer" for a in addrs),
               "marks_in_span": [dict(x, at=x["at"]) for x in in_span],
               "front_error_marks_same_second": dict(near_err),
               "raw": l}
        row["marks_in_span"] = [{"at": x["at"], "kind": x["kind"], "pid": x["pid"]}
                                for x in in_span]
        kind, why = classify({**row, "marks_in_span":
                              [{"kind": x["kind"], "pid": x["pid"]} for x in in_span]})
        row["분류"], row["근거"] = kind, why
        rows.append(row)
    stats = {"access_lines_in_window": len(win), "by_status": dict(sorted(st.items())),
             "n502": st.get("502", 0), "retried": retried, "rescued_2xx": rescued,
             "attempts_hist": {str(k): v for k, v in sorted(attempts.items())},
             "shapes_502": dict(shapes),
             "front_error_marks_total": dict(Counter(e["mark"] for e in errs)),
             "back_marks_in_window": dict(Counter(m["kind"] for m in marks))}
    return rows, stats


def write_table(rows: list, stats: dict, load: dict, meta: dict, stamp: str) -> Path:
    p = HERE / ("cause_table_%s.md" % stamp)
    L = []
    L.append("# P-152 — 남은 502 의 **원인표** (격리 · %s)\n" % stamp)
    L.append("**이 파일은 `docs/agent/evidence/P-152/iso_cause_table.py` 가 실행하며 적었다.** "
             "본 서버·운영계에는 아무것도 보내지 않았다.\n")
    L.append("판: P-137 의 **B**(같은 peer 세 줄 · `proxy_next_upstream_tries 3`)를 "
             "같은 뒷단 모양(`--max-requests %d ±%d` · `--graceful-timeout %d`)으로 다시 한 벌.\n"
             % (MAX_REQ, JITTER, GRACE))
    L.append("부하 %d 요청 · 동시 %d · 익명 GET `%s` · %s~%s (%.1f초 · %.1f rps)\n"
             % (load["n"], load["concurrency"], PROBE_PATH, load["t0"], load["t1"],
                load["elapsed_s"], load["n"] / max(load["elapsed_s"], 0.001)))
    L.append("상태별 %s · 재시도 %d · 되살림(2xx) %d · 시도분포 %s · "
             "재활용 자국 %s\n"
             % (stats["by_status"], stats["retried"], stats["rescued_2xx"],
                stats["attempts_hist"], stats["back_marks_in_window"]))
    L.append("## 원인표 — 502 **%d건 전부**\n" % len(rows))
    L.append("| # | 시각(UTC) | 요청 | rt | 시도(`$upstream_addr`) | 시도별 시간 | "
             "요청 구간 안의 워커 상태 | 분류 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        marks = " · ".join("%s(pid %s) %s" % (m["kind"], m["pid"], m["at"][11:23])
                           for m in r["marks_in_span"]) or "**없음**"
        L.append("| %d | %s | `%s` | %.3f | %s | %s | %s | **%s** |"
                 % (r["n"], r["at"][11:19], r["request"], r["request_time"], r["shape"],
                    ", ".join("%.3f" % t if t is not None else "-" for t in r["upstream_times"]),
                    marks, r["분류"]))
    L.append("\n## 건별 근거\n")
    for r in rows:
        L.append("**%d. %s** — %s" % (r["n"], r["at"], r["근거"]))
        L.append("  · 구간 %s · 앞단 오류로그(같은 초 · **보조 증거**) %s"
                 % (r["span"], r["front_error_marks_same_second"] or "없음"))
        L.append("  · 접근로그 원문: `%s`" % r["raw"])
        L.append("")
    L.append("## 분류 요약\n")
    for k, v in sorted(Counter(r["분류"] for r in rows).items(), key=lambda x: -x[1]):
        L.append("* **%s** — %d건" % (k, v))
    L.append("\n## 읽는 규칙 (이 표를 오독하지 않기 위해)\n")
    L.append("* 분류는 **그 요청 하나의 사실**로만 했다 — `$upstream_addr` 칸 수 · 칸별 시간 · "
             "요청 구간(`[끝 − rt, 끝 + 1초)`) 안의 뒷단 자국(µs · pid).")
    L.append("* **앞단 오류로그는 초 단위**라 그 요청의 것이라고 단정할 수 없다. 표에 적되 "
             "분류를 혼자 결정하지 못하게 했다 (`recv() failed (104` 가 %s줄 났다 — "
             "초로 맞대면 무엇이든 그 옆에 놓인다)."
             % stats["front_error_marks_total"].get("recv() failed (104", 0))
    L.append("* 이 판의 재활용 밀도는 **운영 모양이 아니다**(`max_requests %d` = 운영의 약 4배 잦음). "
             "여기 수는 「이 밀도에서의 수」다." % MAX_REQ)
    L.append("* 격리 증거: 만든 컨테이너 %s → 끝에 남은 것 %s · 도는 컨테이너 기동시각 불변 **%s** · "
             "공용 대신 iso 브로커에 쌓인 감사 작업 %s건(공용 브로커·DB 로 간 것 0)."
             % (list(MINE), meta.get("iso_left_after_cleanup"),
                meta.get("untouched_unchanged"), meta.get("iso_broker_queued_tasks")))
    p.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    return p


def iso_queue_len():
    code = ("import os,redis;r=redis.Redis.from_url(os.environ['REDIS_HOST']+'/'"
            "+os.environ.get('REDIS_DB','0'));"
            "print(sum(r.llen(k) for k in r.scan_iter() if r.type(k)==b'list'))")
    rc, out, _ = dk("exec", BACK_ISO, "python", "-c", code)
    try:
        return int(out.strip().splitlines()[-1]) if rc == 0 else None
    except (ValueError, IndexError):
        return None


def main() -> int:
    smoke = "--smoke" in sys.argv
    n = 300 if smoke else 3600
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    left = existing(MINE)
    if left:
        print("[P-152] 이미 있는 iso 컨테이너 %s — **지우지 않고 멈춘다**" % left)
        return 2
    before = started(UNTOUCHED)
    confs = render_conf()
    env = back_env()
    result = {"measured_at": stamp, "smoke": smoke, "requests": n, "concurrency": CONC,
              "probe_path": PROBE_PATH,
              "back_cmd_delta": {"max_requests": MAX_REQ, "jitter": JITTER,
                                 "graceful_timeout": GRACE},
              "back_env_names": len(env),
              "back_env_override": ["REDIS_HOST → gx-redis-i152 (감사 쓰기 격리)"],
              "config_sha256_12": confs, "untouched_before": before}
    rc_all = 0
    try:
        rc, _, err = dk("run", "-d", "--name", REDIS_ISO, "--network", NET,
                        "--log-opt", "max-size=10m", "--log-opt", "max-file=2",
                        IMG_REDIS, "redis-server", "--save", "", "--appendonly", "no")
        if rc != 0:
            raise RuntimeError("iso redis 를 못 띄웠다: %s" % err.strip()[:200])
        start_back(env)
        result["front_effective"] = start_front()
        load = run_load(n)
        result["load"] = load
        t0 = datetime.fromisoformat(load["t0_iso"]) - timedelta(seconds=2)
        t1 = datetime.fromisoformat(load["t1_iso"]) + timedelta(seconds=2)
        marks = back_marks(t0, t1)
        errs = front_errors(t0, t1)
        rows, stats = build_rows(load, marks, errs)
        result["stats"] = stats
        result["rows"] = rows
        result["iso_broker_queued_tasks"] = iso_queue_len()
        print("[P-152] 502 %d건 · 재시도 %d · 되살림 %d · 시도분포 %s · 자국 %s"
              % (stats["n502"], stats["retried"], stats["rescued_2xx"],
                 stats["attempts_hist"], stats["back_marks_in_window"]))
        for r in rows:
            print("  %2d %s rt=%.3f %-28s %s" % (r["n"], r["at"][11:19], r["request_time"],
                                                 r["shape"], r["분류"]))
    except Exception as exc:                                    # noqa: BLE001
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("[P-152] 멈춤 — %s" % result["error"])
        rc_all = 1
        rows, stats = [], {}
    finally:
        dk("rm", "-f", FRONT_ISO)
        for name in MINE:
            if existing([name]):
                dk("rm", "-f", "-v", name)
        result["iso_left_after_cleanup"] = existing(MINE)
        result["untouched_after"] = started(UNTOUCHED)
        result["untouched_unchanged"] = result["untouched_after"] == before

    out = HERE / ("iso_%s.json" % stamp)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    if rows:
        table = write_table(rows, stats, result["load"], result, stamp)
        print("[P-152] 원인표: %s" % table.relative_to(ROOT).as_posix())
    print("[P-152] 정리: 남은 것 %s · 기동시각 불변 %s · iso 브로커에 쌓인 감사 작업 %s"
          % (result["iso_left_after_cleanup"], result["untouched_unchanged"],
             result.get("iso_broker_queued_tasks")))
    print("[P-152] 증거: %s" % out.relative_to(ROOT).as_posix())
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
