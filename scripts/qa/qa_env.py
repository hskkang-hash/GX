# -*- coding: utf-8 -*-
"""QA 판 env 파일을 **새로 짓는다** — WO-GRDX-20261003-04 레인 B · 규격 09 M5.

운영 env 값을 복사하지 않는다. 비밀 칸은 여기서 난수로 처음 짓고, 저장소 **밖**
(`C:/GuardianX/qa-runtime/qa.env` — 기본값 · `GX_QA_ENV_FILE` 로 바꿀 수 있다)에 둔다.
이미 있으면 그대로 둔다(다시 지으면 QA DB 비밀번호가 갈려 기존 볼륨에 못 붙는다).

`--check-ops <컨테이너>`: 지은 값이 운영 컨테이너의 같은 이름 값과 **같은지** sha256 으로만 대조한다
(값은 어디에도 찍지 않는다). 하나라도 같으면 exit 3 — 「운영 키 0」이 깨진 것이다(M5 · 멈추고 보고).

출력은 **이름만**. 값 0.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = ROOT.parent / "qa-runtime" / "qa.env"

SECRET_NAMES = ("DJANGO_SECRET_KEY", "DB_PASSWORD", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")


def _fresh() -> dict[str, str]:
    db_password = "qa" + secrets.token_hex(16)
    return {
        "DJANGO_SECRET_KEY": "qa-" + secrets.token_urlsafe(48),
        "DB_PASSWORD": db_password,
        "POSTGRES_PASSWORD": db_password,
        "MINIO_ACCESS_KEY": "FAKE_qa_" + secrets.token_hex(6),
        "MINIO_SECRET_KEY": "FAKE_qa_" + secrets.token_hex(16),
    }


def _read(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v
    return out


def _sha(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def check_ops(values: dict[str, str], container: str) -> int:
    same = []
    for name in SECRET_NAMES:
        proc = subprocess.run(["docker", "exec", container, "printenv", name], capture_output=True, text=True)
        ops_value = proc.stdout.rstrip("\n") if proc.returncode == 0 else None
        if ops_value is not None and ops_value and _sha(ops_value) == _sha(values.get(name, "")):
            same.append(name)
    if same:
        print(f"[qa_env] 멈춤 — 운영({container})과 같은 값: {', '.join(same)} (값은 찍지 않음)")
        return 3
    print(f"[qa_env] 운영 키 0 — {len(SECRET_NAMES)} 이름 모두 운영({container}) 값과 다르다(sha256 대조)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-file", default=os.environ.get("GX_QA_ENV_FILE", str(DEFAULT_ENV)))
    ap.add_argument("--check-ops", metavar="CONTAINER")
    args = ap.parse_args(argv)

    path = Path(args.env_file)
    if path.exists():
        values = _read(path)
        print(f"[qa_env] 있다 — 그대로 쓴다: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        values = _fresh()
        body = "# guardianx-qa 전용 — scripts/qa/qa_env.py 가 지은 난수. 저장소에 넣지 않는다. 운영 값 복사 0.\n"
        body += "".join(f"{k}={v}\n" for k, v in values.items())
        path.write_text(body, encoding="utf-8")
        print(f"[qa_env] 새로 지었다: {path}")
    print("[qa_env] 이름: " + " · ".join(sorted(values)))
    if args.check_ops:
        return check_ops(values, args.check_ops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
