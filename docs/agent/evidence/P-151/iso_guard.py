#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-151 — **가드 코드가 먼저**: 격리(`gx_e`)에서 새 값 4 로 7/7 을 내고,
나쁜 값으로는 **실제로 기동이 실패하는지** 보인다 (2026-09-16 · 턴 R · 차선 E).

    python docs/agent/evidence/P-151/iso_guard.py            # 세우고 · 재고 · 지운다
    python docs/agent/evidence/P-151/iso_guard.py --keep     # 지우지 않는다(다시 들여다볼 때)

무엇을 하는가 — 셋
------------------
  ① **격리 컨테이너 `gx_e` 를 세운다.** `gx-shell` 의 환경을 그대로 뜨고 자격 **넷만**
     저장소 밖 금고(`~/.guardianx-secrets/cred3_20260915.env`)의 새 값으로 갈아 끼운다.
     ★ 값은 명령줄에 안 실린다 — `docker run -e 이름`(값 없는 형태)으로 넘기고
       값은 docker 클라이언트 프로세스의 환경에만 산다(`iso_run.py` 와 같은 수법).
  ② **판정기를 그 안에서 돌린다** — `verify_prod_settings.py --no-delegate`.
     닫는 조건: **7/7 · exit 0**.
  ③ **나쁜 값 셋을 넣고 실제로 띄워 본다** — 짧은 값 · 둘이 같은 값 · 자리표.
     가드가 가드라면 **기동이 실패해야** 한다. 대조로 좋은 값 한 판도 같이 띄운다.
     두 자리에서 잰다: ㉠ 설정 기동(`django.conf.settings` 를 읽는 순간)
                      ㉡ **gunicorn `--check-config`**(앱이 실제로 서는 자리)

★ **운영계·본 서버를 건드리지 않는다.** 만드는 것은 `gx_e` 하나뿐이고 끝에 지운다.
  도는 컨테이너 열의 기동 시각을 전/후로 대조해 「한 자도 안 건드렸다」를 증거에 적는다.

★ **값을 출력하지 않는다** — 이 파일이 밖으로 내는 것은 이름 · 길이 · sha256 앞 12자 ·
  기동 성공/실패 · 거부 사유 줄뿐이다 (P-135 불변 · `verify_no_secret_echo`).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REPO = str(ROOT).replace("\\", "/")

NET = "gx-main-network"
IMG = "guardianx-backend:latest"
SRC = "gx-shell"                 # 환경을 뜨는 자리 (판정기가 평소 위임하는 그 컨테이너)
ISO = "gx_e"                     # 내가 만드는 격리 컨테이너 — 이것 하나만 만들고 지운다
VAULT = Path(os.path.expanduser("~/.guardianx-secrets/cred3_20260915.env"))
CREDS = ("MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "DB_PASSWORD", "DJANGO_SECRET_KEY")
SKIP_ENV = {"PATH", "LANG", "GPG_KEY", "PYTHON_VERSION", "PYTHON_SHA256",
            "LD_LIBRARY_PATH", "HOME", "HOSTNAME"}
UNTOUCHED = ("gx-shell", "gx-gunicorn-e", "gx-nginx-e", "gx-celery-e", "gx-beat-e",
             "postgres", "redis", "guardianx-source-minio-1",
             "guardianx-source-mailpit-1", "gx-fe-build")

#: ③ 이 쓰는 「나머지는 다 제대로」 선언. 판정기의 GOOD_* 와 같은 모양이다.
GOOD_HOSTS = "stg.guardianx.example.kr,guardianx.example.kr"
GOOD_ORIGINS = "https://stg.guardianx.example.kr,https://guardianx.example.kr"


def dk(*args, env_extra=None, timeout=900):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(["docker", *args], capture_output=True, env=env, timeout=timeout)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def sha12(v: str) -> str:
    return hashlib.sha256((v or "").encode("utf-8", "replace")).hexdigest()[:12]


def existing(name: str) -> bool:
    _, out, _ = dk("ps", "-a", "--format", "{{.Names}}")
    return name in out.split()


def started(names) -> dict:
    res = {}
    for n in names:
        rc, out, _ = dk("inspect", n, "--format",
                        "{{.State.StartedAt}} {{.State.Status}} restarts={{.RestartCount}}")
        res[n] = out.strip() if rc == 0 else None
    return res


def read_vault() -> dict:
    if not VAULT.is_file():
        raise SystemExit("[P-151] 금고 파일이 없다: %s — 창 전 조건 a 가 안 섰다" % VAULT)
    out = {}
    for line in VAULT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    missing = [k for k in CREDS if not out.get(k)]
    if missing:
        raise SystemExit("[P-151] 금고에 없는 이름: %s" % missing)
    return out


def shape(v: str) -> dict:
    """**값이 아니라 모양.** 길이 · sha256 앞 12자만."""
    return {"len": len(v), "sha256_12": sha12(v)}


def src_env() -> dict:
    _, out, _ = dk("inspect", SRC, "--format", "{{json .Config.Env}}")
    env = dict(e.split("=", 1) for e in json.loads(out) if "=" in e)
    return {k: v for k, v in env.items() if k not in SKIP_ENV}


def up(env: dict) -> None:
    args = ["run", "-d", "--name", ISO, "--network", NET,
            "-v", REPO + "/backend:/app:ro",
            "-v", REPO + "/backend:/repo/backend:ro",
            "-v", REPO + "/scripts:/repo/scripts:ro",
            "-w", "/app", "--entrypoint", "sleep",
            "--log-opt", "max-size=10m", "--log-opt", "max-file=2"]
    passthru = {}
    for k in sorted(env):
        if env[k] == "":
            args += ["-e", k + "="]
        else:
            args += ["-e", k]          # ← 값 없는 형태: 값은 명령줄에 안 실린다
            passthru[k] = env[k]
    args += [IMG, "infinity"]
    rc, _, err = dk(*args, env_extra=passthru)
    if rc != 0:
        raise RuntimeError("격리 컨테이너를 못 띄웠다: %s" % err.strip()[:300])


#: 「접근키 == 비밀키」를 재기 위한 **가짜** 값. 29자여야 한다 — 길이 검사를 먼저
#: 통과해야 그 다음 검사인 「둘이 같다」에 닿기 때문이다. 그리고 **엔트로피가 0**이다.
#:
#: ★ SEC-05 (2026-09-16 병합) — 1차판은 `gxverify-Rt2Xv6Bn1Cw8Hj3Kp5Sy` 를 소스에 박았다.
#:   비밀이 아닌 값이었지만 **스캐너는 뜻이 아니라 모양을 본다** — 29자 난수꼴이 보이자
#:   `verify_secret_scan` 이 「저장소가 나른다」로 빨개졌고, 대장이 「SEC-05 구현」이라
#:   말하는 동안 그 자리가 열려 보였다(P-85). 허용 목록에 넣어 스캐너를 무르게 하는 길도
#:   있었지만 그 길은 **다음에 진짜로 새는 값을 가린다.** 이 판이 재는 것은 난수성이
#:   아니라 「둘이 같다」이므로, 값에서 난수성을 뺐다.
_SAME_LOOKING = "gxverify-" + "0" * 20

#: ③ 의 판 — `(이름, 설명, 자격 덮어쓰기)`. 덮어쓰는 값은 **비밀이 아니다**(자리표·짧은 값)이라
#: 명령줄에 실려도 된다. 좋은 값은 passthru 로만 간다.
BAD_CASES = (
    ("short_minio", "MinIO 접근·비밀이 5자",
     {"MINIO_ACCESS_KEY": "abc12", "MINIO_SECRET_KEY": "abc12"}),
    ("same_minio", "MinIO 접근키 == 비밀키 (둘 다 29자 · 길이는 넉넉하다)",
     {"MINIO_ACCESS_KEY": _SAME_LOOKING,
      "MINIO_SECRET_KEY": _SAME_LOOKING}),
    ("placeholder_minio", "MinIO 자격이 자리표 그대로",
     {"MINIO_ACCESS_KEY": "CHANGE_ME_minioadmin_00000",
      "MINIO_SECRET_KEY": "CHANGE_ME_minioadmin_11111"}),
    ("short_db", "DB 비밀이 5자",
     {"DB_PASSWORD": "abc12"}),
)

BOOT_SETTINGS = ("from django.conf import settings as s;"
                 "s.DEBUG;"
                 "print('BOOTED profile=%s guard=%s' % (s.SECURITY_PROFILE,"
                 " getattr(s, 'CREDENTIAL_GUARD', 'none')))")


def boot(label: str, overrides: dict, passthru: dict, *, gunicorn: bool) -> dict:
    """한 판을 **실제로 띄운다.** 돌려주는 것: 떴나 · 우리 거부인가 · 거부 사유 줄."""
    args = ["exec",
            "-e", "DJANGO_SETTINGS_MODULE=config.settings_prod",
            "-e", "DJANGO_ALLOWED_HOSTS=" + GOOD_HOSTS,
            "-e", "DJANGO_CSRF_TRUSTED_ORIGINS=" + GOOD_ORIGINS,
            "-e", "DJANGO_SECRET_KEY",          # 좋은 값 — passthru
            "-e", "PYTHONIOENCODING=utf-8"]
    for k, v in overrides.items():
        args += ["-e", "%s=%s" % (k, v)]
    args += [ISO, "python"]
    if gunicorn:
        args += ["-m", "gunicorn", "config.wsgi:application", "--check-config",
                 "--bind", "127.0.0.1:18000"]
    else:
        args += ["-c", BOOT_SETTINGS]
    rc, out, err = dk(*args, env_extra=passthru, timeout=300)
    blob = out + "\n" + err
    refused = ("ImproperlyConfigured" in blob) and ("[SEC-18]" in blob)
    reasons = [l.strip() for l in blob.splitlines() if l.strip().startswith("· ")]
    #: ⚠ **두 자리는 뜬 것을 다르게 말한다.** 설정 기동은 우리가 `BOOTED` 를 찍게 했고,
    #:   `gunicorn --check-config` 는 아무것도 안 찍고 **rc=0 으로만** 「섰다」를 말한다.
    #:   한 자로 재면 좋은 값이 「기동 실패」로 찍힌다 — 첫 판이 실제로 그랬다.
    booted = (rc == 0) if gunicorn else (rc == 0 and "BOOTED" in out)
    return {"case": label, "where": "gunicorn --check-config" if gunicorn else "settings 기동",
            "exit": rc, "booted": booted,
            "refused_by_guard": refused,
            "refusal_lines": reasons,
            "tail": [l for l in blob.splitlines() if l.strip()][-3:]}


def main() -> int:
    keep = "--keep" in sys.argv
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    if existing(ISO):
        print("[P-151] `%s` 가 이미 있다 — **지우지 않고 멈춘다**(내 것인지 모른다)" % ISO)
        return 2

    vault = read_vault()
    passthru = {"DJANGO_SECRET_KEY": vault["DJANGO_SECRET_KEY"]}
    before = started(UNTOUCHED)
    env = src_env()
    src_shapes = {k: shape(env.get(k, "")) for k in CREDS}
    for k in CREDS:
        env[k] = vault[k]
    env.pop("DJANGO_SETTINGS_MODULE", None)     # 판정기가 판마다 스스로 준다

    result = {
        "measured_at": stamp,
        "container": ISO,
        "image": IMG,
        "env_names_from": SRC,
        "env_name_count": len(env),
        "credentials_swapped": list(CREDS),
        "shape_before_swap(gx-shell)": src_shapes,
        "shape_after_swap(new)": {k: shape(vault[k]) for k in CREDS},
        "minio_access_eq_secret_before":
            src_shapes["MINIO_ACCESS_KEY"]["sha256_12"] == src_shapes["MINIO_SECRET_KEY"]["sha256_12"],
        "minio_access_eq_secret_after":
            sha12(vault["MINIO_ACCESS_KEY"]) == sha12(vault["MINIO_SECRET_KEY"]),
        "untouched_before": before,
    }
    rc_all = 0
    try:
        up(env)
        print("[P-151] 격리 `%s` 섰다 — 환경 이름 %d개 · 자격 4 를 새 값으로"
              % (ISO, len(env)))

        # ② 판정기 — **그 안에서** 돌린다
        rc, out, err = dk("exec", "-e", "PYTHONIOENCODING=utf-8", ISO, "python",
                          "/repo/scripts/verify_prod_settings.py", "--no-delegate")
        text = out + ("\n" + err if err.strip() else "")
        print(text.rstrip())
        rows = [l.rstrip() for l in text.splitlines()
                if l.strip().startswith(("O  ", "X  ")) or "[SEC-18] 수 " in l
                or "[SEC-18] 통과" in l or "[SEC-18] 실패" in l]
        result["verify_prod_settings"] = {"exit": rc, "rows": rows,
                                          "stdout": text.splitlines()}
        if rc != 0:
            rc_all = 1

        # ③ 나쁜 값 — **실제로 기동이 실패하는가**
        trials = []
        trials.append(boot("good(새 값 4)", {}, passthru, gunicorn=False))
        for name, _why, over in BAD_CASES:
            trials.append(boot(name, over, passthru, gunicorn=False))
        # ㉡ 앱이 실제로 서는 자리 — gunicorn
        trials.append(boot("good(새 값 4)", {}, passthru, gunicorn=True))
        for name, _why, over in BAD_CASES:
            trials.append(boot(name, over, passthru, gunicorn=True))
        result["boot_trials"] = trials
        result["bad_case_labels"] = {n: w for n, w, _ in BAD_CASES}

        print("\n[P-151] 나쁜 값으로 **실제로 띄워 본다** — 떴으면 가드가 아니다")
        for t in trials:
            print("  %-22s %-22s exit=%-3d %s%s"
                  % (t["case"], t["where"], t["exit"],
                     "**떴다**" if t["booted"] else "기동 실패",
                     " · [SEC-18] 거부" if t["refused_by_guard"] else ""))
            for r in t["refusal_lines"]:
                print("       %s" % r[:160])
    except Exception as exc:                                   # noqa: BLE001
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        print("[P-151] 멈춤 — %s" % result["error"])
        rc_all = 1
    finally:
        if not keep and existing(ISO):
            dk("rm", "-f", "-v", ISO)
        result["iso_left_after_cleanup"] = [ISO] if existing(ISO) else []
        result["untouched_after"] = started(UNTOUCHED)
        result["untouched_unchanged"] = result["untouched_after"] == before

    out_path = HERE / ("iso_guard_%s.json" % stamp)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n[P-151] 정리: 남은 격리 %s · 도는 컨테이너 기동시각 불변 %s"
          % (result["iso_left_after_cleanup"], result["untouched_unchanged"]))
    print("[P-151] 증거: %s" % out_path.relative_to(ROOT).as_posix())
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
