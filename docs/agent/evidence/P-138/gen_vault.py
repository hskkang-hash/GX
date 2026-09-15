#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-138 — 자격 3의 **새 값을 금고에만** 만든다 (2026-09-15 · 턴 Q · 차선 E).

    python docs/agent/evidence/P-138/gen_vault.py            # 만들고 형식을 잰다
    python docs/agent/evidence/P-138/gen_vault.py --check    # 이미 만든 금고 파일의 형식만 다시 잰다

★ **값은 이 스크립트 밖으로 한 글자도 나가지 않는다.** 터미널·증거에 가는 것은
  이름 · 길이 · sha256 앞 12자 · 규칙 통과 여부뿐이다(P-135 불변 「게이트는 값을 출력하지 않는다」).
  값이 가는 곳은 저장소 밖 금고 `~/.guardianx-secrets/` 둘뿐이다(D-002 · `.gitignore:73`).

형식 규칙은 **여기서 새로 짓지 않는다** — 코드가 쓰는 수를 코드에서 읽는다(D-369):
  · `scripts/verify_prod_settings.py::CRED_MIN_LEN`(20) · 탐침 속 `_PLACEHOLDER_WORDS`
  · `backend/config/settings_prod.py::SECRET_KEY_MIN_LEN`(50) · `SECRET_KEY_PLACEHOLDERS`
  그리고 **실제 탐침으로 한 번 더 잰다**: `gx-shell` 안에서 `verify_prod_settings.PROBE` 를
  운영 프로필(`config.settings_prod`)로 띄우고 새 값을 **자식 환경에만** 준다. 값은
  `docker exec -e 이름`(값 없는 형태)으로 넘긴다 — 명령줄에도 값이 실리지 않는다.

MinIO 접근키를 **정확히 20자**로 두는 까닭: 우리 하한(20)과 MinIO 의 오래된 상한
(접근키 3~20 · 비밀키 8~40)을 동시에 만족하는 자리가 20 하나다 [가정 — MinIO 소스는
이 저장소에 없다. 창에서 minio 가 거부하면 되돌리기 절로 간다].
"""
from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import string
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parents[4]
VAULT = Path.home() / ".guardianx-secrets"
STAMP = "20260915"
ENV_FILE = VAULT / ("cred3_%s.env" % STAMP)
SQL_FILE = VAULT / ("cred3_%s_alter_db_role.sql" % STAMP)
EVIDENCE = Path(__file__).resolve().parent / ("vault_prepared_%s.json" % STAMP)

ALNUM = string.ascii_letters + string.digits
#: 이름 → (길이, 무엇). 영숫자만 — `#`·`$`·따옴표는 `--env-file`·셸 소싱에서 잘리거나 펴진다
#: (메모리: `.env.gates` 의 `#` 사고 · `${VAR}` 사고).
PLAN = {
    "MINIO_ACCESS_KEY": (20, "MinIO 접근키 = 서버 MINIO_ROOT_USER 와 같은 글자"),
    "MINIO_SECRET_KEY": (40, "MinIO 비밀키 = 서버 MINIO_ROOT_PASSWORD 와 같은 글자"),
    "DB_PASSWORD": (32, "앱 DB 비밀번호 (postgres 역할 비밀번호)"),
    "DJANGO_SECRET_KEY": (64, "서명 키"),
}


def sha12(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:12]


def gen(n: int) -> str:
    # 첫 글자는 영문 — 어떤 파서도 숫자·기호로 시작하는 값을 다르게 읽지 않게
    return secrets.choice(string.ascii_letters) + "".join(secrets.choice(ALNUM) for _ in range(n - 1))


def code_rules() -> dict:
    """형식 규칙을 **코드에서** 읽는다."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import verify_prod_settings as v  # noqa: PLC0415  (모듈 머리에 부작용 없음 · __main__ 가드)

    m = re.search(r"_PLACEHOLDER_WORDS\s*=\s*(\([^)]*\))", v.PROBE, re.S)
    words = ast.literal_eval(m.group(1)) if m else ()
    tree = ast.parse((ROOT / "backend/config/settings_prod.py").read_text(encoding="utf-8"))
    sk_ph, sk_min = (), None
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "SECRET_KEY_PLACEHOLDERS":
                sk_ph = ast.literal_eval(node.value)
            elif node.targets[0].id == "SECRET_KEY_MIN_LEN":
                sk_min = ast.literal_eval(node.value)
    return {"CRED_MIN_LEN": v.CRED_MIN_LEN, "PLACEHOLDER_WORDS": tuple(words),
            "SECRET_KEY_MIN_LEN": sk_min, "SECRET_KEY_PLACEHOLDERS": tuple(sk_ph),
            "_v": v}


def check(values: dict, rules: dict) -> dict:
    """값을 보지 않고 **판정만** 돌려준다."""
    words = [w.lower() for w in rules["PLACEHOLDER_WORDS"]]
    skph = [w.lower() for w in rules["SECRET_KEY_PLACEHOLDERS"]]
    out = {}
    for name, val in values.items():
        low = val.lower()
        out[name] = {
            "len": len(val), "sha256_12": sha12(val),
            "min_len_ok": len(val) >= (rules["SECRET_KEY_MIN_LEN"] if name == "DJANGO_SECRET_KEY"
                                       else rules["CRED_MIN_LEN"]),
            "placeholder_words_hit": [w for w in words if w in low],
            "secret_key_placeholder_hit": ([w for w in skph if w in low]
                                           if name == "DJANGO_SECRET_KEY" else []),
            "alnum_only": all(c in ALNUM for c in val),
        }
    vals = list(values.values())
    out["_all_distinct"] = len(set(vals)) == len(vals)
    out["_minio_access_ne_secret"] = values["MINIO_ACCESS_KEY"] != values["MINIO_SECRET_KEY"]
    out["_minio_access_le_20"] = len(values["MINIO_ACCESS_KEY"]) <= 20
    out["_minio_secret_le_40"] = len(values["MINIO_SECRET_KEY"]) <= 40
    return out


def scram_verifier(password: str, iterations: int = 4096) -> str:
    """PostgreSQL SCRAM-SHA-256 검증자. **서버 로그에 문장이 남아도 평문이 없다.**"""
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", "sha256").digest()
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.new(salted, b"Server Key", "sha256").digest()
    b64 = lambda b: base64.b64encode(b).decode("ascii")  # noqa: E731
    return "SCRAM-SHA-256$%d:%s$%s:%s" % (iterations, b64(salt), b64(stored_key), b64(server_key))


def container_env(name: str) -> dict:
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    p = subprocess.run(["docker", "inspect", name, "--format", "{{json .Config.Env}}"],
                       capture_output=True, env=env, timeout=60)
    if p.returncode != 0:
        return {}
    return dict(e.split("=", 1) for e in json.loads(p.stdout.decode("utf-8")) if "=" in e)


#: gx-shell 안에서 도는 탐침 — **값을 받아 길이·같음·자리표만** 돌려준다.
PROBE_RUNNER = r'''
import json, os, subprocess, sys
sys.path.insert(0, "/repo/scripts")
import verify_prod_settings as v
KEYS = ["profile", "MINIO_ACCESS_LEN", "MINIO_SECRET_LEN", "MINIO_SAME", "MINIO_PLACEHOLDER",
        "DB_PASSWORD_LEN", "DB_PLACEHOLDER", "SECRET_KEY_LEN", "SECRET_KEY_IS_PLACEHOLDER",
        "SECRET_KEY_PLACEHOLDER_WORD"]
def run(over):
    env = v._child_env(v.PROD_MODULE, dict(v.GOOD_DECL))
    env.update(over)
    p = subprocess.run([sys.executable, "-c", v.PROBE], cwd="/app", env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    line = next((l for l in p.stdout.decode("utf-8", "replace").splitlines()
                 if l.startswith("GXPROD ")), "")
    if p.returncode != 0 or not line:
        err = p.stderr.decode("utf-8", "replace")
        return {"booted": False, "rc": p.returncode,
                "refused_by_tag": ("ImproperlyConfigured" in err and "[SEC-18]" in err)}
    s = json.loads(line[len("GXPROD "):])
    return dict({"booted": True}, **{k: s.get(k) for k in KEYS})
new = {"MINIO_ACCESS_KEY": os.environ["GXNEW_MINIO_ACCESS_KEY"],
       "MINIO_SECRET_KEY": os.environ["GXNEW_MINIO_SECRET_KEY"],
       "DB_PASSWORD": os.environ["GXNEW_DB_PASSWORD"],
       "DJANGO_SECRET_KEY": os.environ["GXNEW_DJANGO_SECRET_KEY"]}
print("GXVAULT " + json.dumps({
    # 지금 컨테이너가 든 값 — 단, 서명 키만은 판정기의 합성 키(GOOD_SECRET)다(아래 주의)
    "current_container_values": run({}),
    # 새 값 넷 — 서명 키까지 새 값으로 settings_prod ① 을 실제로 통과하는가
    "new_values": run(new),
}))
'''


def probe_in_container(values: dict) -> dict:
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    args = ["docker", "exec", "-i"]
    for name, val in values.items():
        env["GXNEW_" + name] = val
        args += ["-e", "GXNEW_" + name]          # ← 값 없는 형태: 값은 명령줄에 안 실린다
    args += ["gx-shell", "python", "-"]
    p = subprocess.run(args, input=PROBE_RUNNER.encode("utf-8"), capture_output=True,
                       env=env, timeout=600)
    line = next((l for l in p.stdout.decode("utf-8", "replace").splitlines()
                 if l.startswith("GXVAULT ")), "")
    if not line:
        return {"error": "탐침이 답하지 않았다 (rc=%d)" % p.returncode}
    return json.loads(line[len("GXVAULT "):])


def read_vault() -> dict:
    vals = {}
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            vals[k] = v
    return {k: vals[k] for k in PLAN}


def lock_down(path: Path) -> str:
    """Windows ACL — **사용자 한 명만**. 상속을 끊고 그 사용자에게만 전권."""
    user = os.environ.get("USERNAME", "")
    if not user:
        return "USERNAME 없음 — ACL 을 못 걸었다"
    p = subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        "%s:(OI)(CI)F" % user], capture_output=True, timeout=60)
    q = subprocess.run(["icacls", str(path)], capture_output=True, timeout=60)
    text = q.stdout.decode("mbcs", "replace") if os.name == "nt" else q.stdout.decode()
    principals = sorted({ln.strip().split(":")[0].split()[-1] for ln in text.splitlines()
                         if ":(" in ln})
    return "icacls rc=%d · 남은 주체 %s" % (p.returncode, principals)


def main() -> int:
    rules = code_rules()
    v = rules.pop("_v")
    if "--check" in sys.argv:
        values = read_vault()
    else:
        if ENV_FILE.exists():
            print("[P-138] 금고 파일이 이미 있다 — **덮지 않는다**: %s (--check 로 재기만 한다)" % ENV_FILE.name)
            return 2
        for _ in range(20):
            values = {name: gen(n) for name, (n, _w) in PLAN.items()}
            c = check(values, rules)
            if (c["_all_distinct"] and all(c[k]["min_len_ok"] and not c[k]["placeholder_words_hit"]
                                           and not c[k]["secret_key_placeholder_hit"] for k in PLAN)):
                break
        VAULT.mkdir(exist_ok=True)
        acl = lock_down(VAULT)
        db_user = container_env("gx-gunicorn-e").get("DB_USER", "")
        lines = ["# P-138 자격 3 — 새 값 · %s 생성 · 턴 Q 차선 E" % STAMP,
                 "# ⚠ 창(대표 결정 ③)에서만 쓴다. 저장소·.env* 로 옮기지 않는다(D-002).",
                 "# 서버쪽(minio 컨테이너)",
                 "MINIO_ROOT_USER=%s" % values["MINIO_ACCESS_KEY"],
                 "MINIO_ROOT_PASSWORD=%s" % values["MINIO_SECRET_KEY"],
                 "# 앱쪽(gx-gunicorn-e · gx-celery-e · gx-beat-e · gx-shell) — 서버쪽과 같은 글자",
                 "MINIO_ACCESS_KEY=%s" % values["MINIO_ACCESS_KEY"],
                 "MINIO_SECRET_KEY=%s" % values["MINIO_SECRET_KEY"],
                 "DB_PASSWORD=%s" % values["DB_PASSWORD"],
                 "DJANGO_SECRET_KEY=%s" % values["DJANGO_SECRET_KEY"], ""]
        ENV_FILE.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        # 역할 이름은 앱 컨테이너의 DB_USER 를 **스크립트 안에서만** 읽는다.
        ident = '"%s"' % db_user.replace('"', '""') if db_user else "<DB_USER>"
        SQL_FILE.write_text(
            "-- P-138 · 창 단계 ②-a — 평문이 아니라 SCRAM 검증자를 싣는다(서버 로그에 문장이 남아도 평문 없음)\n"
            "ALTER ROLE %s PASSWORD '%s';\n" % (ident, scram_verifier(values["DB_PASSWORD"])),
            encoding="utf-8", newline="\n")
        print("[P-138] 금고에 적었다: %s · %s (ACL: %s)" % (ENV_FILE.name, SQL_FILE.name, acl))
        print("[P-138] DB 역할 이름: 앱 컨테이너 DB_USER 에서 읽음 (%s)" % ("있음" if db_user else "**없음 — SQL 에 자리표**"))
    c = check(values, rules)
    probe = probe_in_container(values)
    for name in PLAN:
        r = c[name]
        print("  %-18s 길이 %2d · sha256 %s · 하한 %s · 자리표 %s · 영숫자 %s"
              % (name, r["len"], r["sha256_12"], "O" if r["min_len_ok"] else "X",
                 r["placeholder_words_hit"] or r["secret_key_placeholder_hit"] or "없음",
                 "O" if r["alnum_only"] else "X"))
    print("  넷이 서로 다름 %s · MinIO 접근≠비밀 %s" % (c["_all_distinct"], c["_minio_access_ne_secret"]))
    print("  탐침(gx-shell · config.settings_prod) 새 값: %s"
          % json.dumps(probe.get("new_values"), ensure_ascii=False))
    print("  탐침 지금 컨테이너 값: %s"
          % json.dumps(probe.get("current_container_values"), ensure_ascii=False))
    payload = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vault_dir": "~/.guardianx-secrets/ (저장소 밖 · D-002)",
        "vault_files": [ENV_FILE.name, SQL_FILE.name],
        "rules_from_code": {k: (list(v2) if isinstance(v2, tuple) else v2) for k, v2 in rules.items()},
        "values": {k: c[k] for k in PLAN},
        "all_distinct": c["_all_distinct"], "minio_access_ne_secret": c["_minio_access_ne_secret"],
        "minio_access_le_20": c["_minio_access_le_20"], "minio_secret_le_40": c["_minio_secret_le_40"],
        "probe_gx_shell_settings_prod": probe,
        "note": ("값은 이 파일에 없다 — 이름·길이·sha256 앞 12자·판정뿐. "
                 "current_container_values 의 SECRET_KEY_LEN 은 판정기의 합성 키(GOOD_SECRET)의 길이다 "
                 "(verify_prod_settings._child_env 가 DJANGO_* 를 지우고 GOOD_DECL 을 싣는다) — "
                 "앱이 든 33자 키는 이 줄에 안 보인다."),
    }
    EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[P-138] 증거: %s" % EVIDENCE.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
