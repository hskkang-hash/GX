#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-137 · OPS-13a/b — **격리에서** 앞단 재시도의 전/후 502 를 잰다 (2026-09-15 · 턴 Q · 차선 E).

    python docs/agent/evidence/P-137/iso_run.py --smoke     # 배관 확인 (A 한 벌 · 300 요청)
    python docs/agent/evidence/P-137/iso_run.py             # A/B/A/B 네 벌 × 3,600 요청

무엇을 바꾸고 무엇을 안 바꾸나
------------------------------
  A (전 · 지금 모양)  `nginx/gx-front.conf` 그대로 — upstream 한 줄만 뒷단 이름을 iso 로.
                      `proxy_next_upstream error timeout http_502` · `tries 3` · `timeout 15s`
                      (`nginx/gx-proxy.inc` · 생성물 `nginx/generated/gx-gate.conf` 도 **원본 그대로 물린다**)
  B (후 · 새 설정)    A 와 한 자리만 다르다: **같은 peer 를 세 줄**. `tries 3` 이 세 번 다 peer 로 간다.
  뒷단(둘 다 같음)    gx-gunicorn-e 와 같은 이미지·망·환경·명령 + `--max-requests 50 ±10`(재활용을
                      자주 일으키려고) + `--graceful-timeout 30`(= `backend/gunicorn.conf.py` 값을 명시).

★ 왜 B 가 「세 줄」인가 [가설 · nginx 소스 기억 — 이 판이 재서 가른다]
  `upstream` 에 peer 가 **하나**면 round-robin 이 실패한 연결을 놓을 때 `tries = 0` 으로 만든다
  (`ngx_http_upstream_free_round_robin_peer` 의 `single` 갈래). 예외는 **keepalive 로 재사용하던
  연결**의 `error` 뿐이다(`ngx_http_upstream_next` 의 `peer.cached` → `tries++`). 그래서 한 줄일 때
  재시도는 낡은 keepalive 연결에서만 일어나고, **새로 맺은 연결**이 죽어 가는 워커에 걸리면
  재시도 없이 502 가 나간다 — OPS-13b 가 남긴 「`$upstream_addr` 가 하나인 502」가 그 모양이다.
  두 줄이면 `tries` 가 2 로 묶이고(P-101 이 잰 `addr, addr, gx_app 0.000`), 세 줄이면 3 이다.

격리의 뜻 — **도는 것을 한 자도 안 건드린다**
  · 새 컨테이너 넷(`gx-redis-iso` · `gx-gunicorn-iso` · `gx-nginx-iso` · `gx-load-iso`)만 만들고 지운다.
  · 뒷단 소스는 **읽기 전용**으로 문다. 이미지의 `ENTRYPOINT`(자동 migrate)는 `--entrypoint python` 으로 비킨다.
  · ★ **DB 에 쓰지 않는다.** 모든 요청은 `CoreLoggingMiddleware` 가 `task_add_log.delay()` 로 감사 쓰기를
    싣는다(dj-core `core/logger/middleware.py`). 그 브로커가 공용 redis 면 `gx-celery-e` 가 받아
    `AuditLogs.objects.create` 한다. 그래서 iso 뒷단만 `REDIS_HOST` 를 **임시 redis** 로 돌린다 —
    소비자가 없어 쌓이기만 하고, 컨테이너를 지우면 함께 사라진다. 끝에 쌓인 건수를 센다(= 공용으로 안 갔다).
  · 환경 **값은 출력하지 않는다** — `docker exec -e 이름`(값 없는 형태)으로 넘긴다. 증거에는 이름 수만.
  · 부하는 익명 GET 한 자리(`/admin/login/` — 관문 밖 · 응답 캐시 우회 목록 · 세션 저장 없음).
"""
from __future__ import annotations

import hashlib
import json
import os
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
import verify_front_line_502 as J  # noqa: E402  (_ACCESS · clip_by_time · _DOCKER_TS_US)

NET = "gx-main-network"
IMG_BACK, IMG_FRONT, IMG_REDIS = "guardianx-backend:latest", "nginx:alpine", "redis:latest"
SRC_BACK = "gx-gunicorn-e"
REDIS_ISO, BACK_ISO, FRONT_ISO, LOAD_ISO = "gx-redis-iso", "gx-gunicorn-iso", "gx-nginx-iso", "gx-load-iso"
MINE = (FRONT_ISO, LOAD_ISO, BACK_ISO, REDIS_ISO)
UNTOUCHED = ("gx-shell", "gx-gunicorn-e", "gx-nginx-e", "gx-celery-e", "gx-beat-e", "postgres",
             "redis", "guardianx-source-minio-1", "guardianx-source-mailpit-1", "gx-fe-build")
REPO = str(ROOT).replace("\\", "/")
ISO_DIR = HERE / "iso"
PROBE_PATH = "/admin/login/"
CONC = 10
MAX_REQ, JITTER, GRACE = 50, 10, 30
SKIP_ENV = {"PATH", "LANG", "GPG_KEY", "PYTHON_VERSION", "PYTHON_SHA256", "LD_LIBRARY_PATH",
            "HOME", "HOSTNAME"}
ERR_MARKS = ("recv() failed (104", "upstream prematurely closed", "connect() failed (111",
             "no live upstreams", "upstream timed out", "writev() failed")


def dk(*args, env_extra=None, inp=None, timeout=300):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(["docker", *args], input=inp, capture_output=True, env=env, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def existing(names) -> list:
    _, out, _ = dk("ps", "-a", "--format", "{{.Names}}")
    have = set(out.split())
    return [n for n in names if n in have]


def started(names) -> dict:
    res = {}
    for n in names:
        rc, out, _ = dk("inspect", n, "--format", "{{.State.StartedAt}} {{.State.Status}} restarts={{.RestartCount}}")
        res[n] = out.strip() if rc == 0 else None
    return res


def sha12_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


# ── 설정 두 벌 — **원본에서 한 자리만 바꿔** 만든다 (손으로 베끼지 않는다 · D-369) ──────
ORIG_UPSTREAM = "server gx-gunicorn-e:8000 max_fails=0;"
ISO_UPSTREAM = "server %s:8000 max_fails=0;" % BACK_ISO


def render_confs() -> dict:
    src = (ROOT / "nginx" / "gx-front.conf").read_text(encoding="utf-8")
    if src.count(ORIG_UPSTREAM) != 1:
        raise SystemExit("[P-137] nginx/gx-front.conf 의 upstream 한 줄을 못 찾았다 — 원본이 바뀌었다. 멈춘다")
    body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#") and l.strip())
    head = ("# P-137 격리 설정 — **생성물**. docs/agent/evidence/P-137/iso_run.py 가 nginx/gx-front.conf 에서\n"
            "#   주석을 걷고 upstream 의 server 줄만 바꿨다. 나머지 지시어(관문 생성물 · gx-proxy.inc 포함)는 원본 그대로다.\n"
            "#   ⚠ nginx/ 아래에 두지 않은 까닭: verify_live_freshness 가 gx-nginx-e 를 nginx/**.conf 의 시각으로 잰다 —\n"
            "#     새 .conf 가 거기 생기면 도는 앞단이 「낡았다」로 읽힌다(거짓 빨강).\n")
    ISO_DIR.mkdir(exist_ok=True)
    a = head + "# A (전 · 지금 모양) — peer 한 줄\n" + body.replace(ORIG_UPSTREAM, ISO_UPSTREAM) + "\n"
    b = head + "# B (후 · 새 설정) — 같은 peer 세 줄: tries 3 이 세 번 다 peer 로 간다\n" + body.replace(
        ORIG_UPSTREAM, "\n        ".join([ISO_UPSTREAM] * 3)) + "\n"
    (ISO_DIR / "gx-front-iso-A.conf").write_text(a, encoding="utf-8", newline="\n")
    (ISO_DIR / "gx-front-iso-B.conf").write_text(b, encoding="utf-8", newline="\n")
    return {"gx-front.conf": sha12_file(ROOT / "nginx" / "gx-front.conf"),
            "gx-proxy.inc": sha12_file(ROOT / "nginx" / "gx-proxy.inc"),
            "generated/gx-gate.conf": sha12_file(ROOT / "nginx" / "generated" / "gx-gate.conf"),
            "iso/gx-front-iso-A.conf": sha12_file(ISO_DIR / "gx-front-iso-A.conf"),
            "iso/gx-front-iso-B.conf": sha12_file(ISO_DIR / "gx-front-iso-B.conf")}


def back_env() -> dict:
    _, out, _ = dk("inspect", SRC_BACK, "--format", "{{json .Config.Env}}")
    env = dict(e.split("=", 1) for e in json.loads(out) if "=" in e)
    env = {k: v for k, v in env.items() if k not in SKIP_ENV}
    env["REDIS_HOST"] = "redis://%s:6379" % REDIS_ISO      # ★ 감사 쓰기를 공용 브로커에서 떼어 낸다
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
    args = ["run", "-d", "--name", BACK_ISO, "--network", NET, "--entrypoint", "python", "-w", "/app",
            "-v", REPO + "/backend:/app:ro", "--log-opt", "max-size=10m", "--log-opt", "max-file=5"]
    passthru = {}
    for k in sorted(env):
        if env[k] == "":
            args += ["-e", k + "="]                      # 빈 값은 비밀이 아니다 — Windows 환경은 빈 값을 못 든다
        else:
            args += ["-e", k]                            # ← 값 없는 형태: 값은 명령줄에 안 실린다
            passthru[k] = env[k]
    args += [IMG_BACK, "-m", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000",
             "--workers", "4", "--threads", "4", "--worker-class", "gthread", "--timeout", "120",
             "--access-logfile", "-", "--error-logfile", "-",
             "--max-requests", str(MAX_REQ), "--max-requests-jitter", str(JITTER),
             "--graceful-timeout", str(GRACE)]
    rc, _, err = dk(*args, env_extra=passthru)
    if rc != 0:
        raise RuntimeError("iso 뒷단을 못 띄웠다: %s" % err.strip()[:200])
    if not wait_for(BACK_ISO, "Booting worker", 4):
        _, out, err = dk("logs", "--tail", "40", BACK_ISO)
        bad = [l[:200] for l in (out + err).splitlines() if "Error" in l or "error" in l][:8]
        raise RuntimeError("iso 뒷단이 안 섰다 — 오류 줄: %s" % bad)


def start_front(conf: str) -> dict:
    rc, _, err = dk("run", "-d", "--name", FRONT_ISO, "--network", NET,
                    "-v", REPO + "/nginx:/etc/nginx/gx:ro",
                    "-v", str(ISO_DIR).replace("\\", "/") + ":/etc/nginx/iso:ro",
                    "--log-opt", "max-size=10m", "--log-opt", "max-file=5",
                    IMG_FRONT, "nginx", "-c", "/etc/nginx/iso/" + conf, "-g", "daemon off;")
    if rc != 0:
        raise RuntimeError("iso 앞단을 못 띄웠다: %s" % err.strip()[:300])
    time.sleep(2)
    rc, dump, derr = dk("exec", FRONT_ISO, "nginx", "-T", "-c", "/etc/nginx/iso/" + conf)
    return {"nginx_T_rc": rc,
            "peer_lines": dump.count(ISO_UPSTREAM),
            "tries_3": dump.count("proxy_next_upstream_tries 3;"),
            "next_upstream": dump.count("proxy_next_upstream error timeout http_502;"),
            "non_idempotent": dump.count("non_idempotent")}


LOAD = r'''
import concurrent.futures, datetime, json, time, urllib.error, urllib.request
BASE = "http://%(front)s:8500"; PATH = "%(path)s"; N = %(n)d; C = %(c)d
def get(u, t=30):
    try:
        req = urllib.request.Request(u, headers={"X-GX-Probe": "p137-iso"})
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
                      "--entrypoint", "python", IMG_BACK, "-", inp=script.encode("utf-8"), timeout=900)
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


def analyze(load: dict) -> dict:
    _, out, err = dk("logs", FRONT_ISO)
    acc = [l for l in out.splitlines() if J._ACCESS.match(l)]
    win = J.clip_by_time(acc, load["t0"], load["t1"])
    st, attempts, shapes, samples = Counter(), Counter(), Counter(), []
    retried = rescued_2xx = 0
    for l in win:
        m = J._ACCESS.match(l)
        s, up = m.group("status"), m.group("up")
        parts = [x.strip() for x in up.split(",") if x.strip()]
        st[s] += 1
        attempts[len(parts)] += 1
        if len(parts) > 1:
            retried += 1
            rescued_2xx += s.startswith("2")
        if s == "502":
            shapes[", ".join("gx_app" if x == "gx_app" else "peer" for x in parts)] += 1
            if len(samples) < 6:
                samples.append(l)
    # 뒷단 자국 — 부하 창 [t0-1s, t1+2s]
    t0 = datetime.fromisoformat(load["t0_iso"]) - timedelta(seconds=1)
    t1 = datetime.fromisoformat(load["t1_iso"]) + timedelta(seconds=2)
    _, bo, be = dk("logs", "-t", BACK_ISO)
    ann = ex = boot = 0
    for l in (bo + "\n" + be).splitlines():
        ts = parse_ts(l)
        if ts is None or not (t0 <= ts <= t1):
            continue
        ann += "Autorestarting" in l
        ex += ("Worker exiting (pid" in l) and ("cleaning" not in l)
        boot += "Booting worker" in l
    return {"access_lines_in_window": len(win), "by_status": dict(sorted(st.items())),
            "n502": st.get("502", 0), "retried": retried, "rescued_2xx": rescued_2xx,
            "attempts_hist": {str(k): v for k, v in sorted(attempts.items())},
            "shapes_502": dict(shapes), "samples_502": samples,
            "front_error_marks": {k: err.count(k) for k in ERR_MARKS},
            "back_marks_in_window": {"Autorestarting": ann, "Worker_exiting": ex, "Booting_worker": boot}}


def run_judge(tag: str, load: dict, stamp: str) -> dict:
    ev = HERE / ("judge_%s_%s.md" % (stamp, tag))
    env = dict(os.environ, PYTHONIOENCODING="utf-8", MSYS_NO_PATHCONV="1")
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_front_line_502.py"),
                        "--front", FRONT_ISO, "--back", BACK_ISO,
                        "--since-time", load["t0"], "--until-time", load["t1"],
                        "--evidence", str(ev)], capture_output=True, env=env, timeout=600)
    out = p.stdout.decode("utf-8", "replace")
    rows = [l.strip() for l in out.splitlines() if l.strip()[:4] in ("OK  ", "FAIL", "GRAY")]
    return {"exit": p.returncode, "rows": rows, "evidence": ev.relative_to(ROOT).as_posix()}


def iso_queue_len() -> int | None:
    code = ("import os,redis;r=redis.Redis.from_url(os.environ['REDIS_HOST']+'/'+os.environ.get('REDIS_DB','0'));"
            "print(sum(r.llen(k) for k in r.scan_iter() if r.type(k)==b'list'))")
    rc, out, _ = dk("exec", BACK_ISO, "python", "-c", code)
    try:
        return int(out.strip().splitlines()[-1]) if rc == 0 else None
    except (ValueError, IndexError):
        return None


def main() -> int:
    smoke = "--smoke" in sys.argv
    n = 300 if smoke else 3600
    plan = [("A", "gx-front-iso-A.conf")] if smoke else [
        ("A", "gx-front-iso-A.conf"), ("B", "gx-front-iso-B.conf"),
        ("A2", "gx-front-iso-A.conf"), ("B2", "gx-front-iso-B.conf")]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    left = existing(MINE)
    if left:
        print("[P-137] 이미 있는 iso 컨테이너 %s — **지우지 않고 멈춘다**(내 것인지 모른다)" % left)
        return 2
    before = started(UNTOUCHED)
    confs = render_confs()
    env = back_env()
    result = {"measured_at": stamp, "smoke": smoke, "requests_per_run": n, "concurrency": CONC,
              "probe_path": PROBE_PATH, "back_cmd_delta": {"max_requests": MAX_REQ, "jitter": JITTER,
                                                           "graceful_timeout": GRACE},
              "back_env_names": len(env), "back_env_override": ["REDIS_HOST → gx-redis-iso (감사 쓰기 격리)"],
              "config_sha256_12": confs, "untouched_before": before, "runs": {}}
    rc_all = 0
    try:
        rc, _, err = dk("run", "-d", "--name", REDIS_ISO, "--network", NET, "--log-opt", "max-size=10m",
                        "--log-opt", "max-file=2", IMG_REDIS, "redis-server", "--save", "", "--appendonly", "no")
        if rc != 0:
            raise RuntimeError("iso redis 를 못 띄웠다: %s" % err.strip()[:200])
        start_back(env)
        for tag, conf in plan:
            fx = start_front(conf)
            load = run_load(n)
            stats = analyze(load)
            judge = run_judge(tag, load, stamp)
            result["runs"][tag] = {"conf": conf, "front_effective": fx, "load": load, "stats": stats,
                                   "judge_verify_front_line_502": judge}
            print("[P-137] %-2s %s · 502 %d/%d · 재시도 %d · 되살림(2xx) %d · 시도분포 %s · 재활용 %d/종료 %d · 판정기 exit %d"
                  % (tag, conf, stats["n502"], stats["access_lines_in_window"], stats["retried"],
                     stats["rescued_2xx"], stats["attempts_hist"],
                     stats["back_marks_in_window"]["Autorestarting"],
                     stats["back_marks_in_window"]["Worker_exiting"], judge["exit"]))
            dk("rm", "-f", FRONT_ISO)
        result["iso_broker_queued_tasks"] = iso_queue_len()
    except Exception as exc:  # noqa: BLE001
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("[P-137] 멈춤 — %s" % result["error"])
        rc_all = 1
    finally:
        for name in MINE:
            if existing([name]):
                dk("rm", "-f", "-v", name)
        result["iso_left_after_cleanup"] = existing(MINE)
        result["untouched_after"] = started(UNTOUCHED)
        result["untouched_unchanged"] = result["untouched_after"] == before
    out = HERE / ("iso_%s%s.json" % (stamp, "_smoke" if smoke else ""))
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[P-137] 정리: iso 남은 것 %s · 도는 컨테이너 기동시각 불변 %s · 공용 대신 iso 브로커에 쌓인 감사 작업 %s"
          % (result["iso_left_after_cleanup"], result["untouched_unchanged"],
             result.get("iso_broker_queued_tasks")))
    print("[P-137] 증거: %s" % out.relative_to(ROOT).as_posix())
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
