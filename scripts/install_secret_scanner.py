#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""시크릿 스캐너를 **고정된 판으로** 세운다 — P-12 ② · D-387.

    "secrets — 사유: 스캐너 미설치. 해제: 스캐너 설치 + lock 고정(D-387) → 잼."

왜 설치 스크립트가 따로 있는가
------------------------------
`gate_secrets` 는 `command -v gitleaks` 가 비면 **SKIP** 한다. SKIP 은 통과가 아니라
「못 쟀다」이고(D-400), 못 잰 게이트는 회색이다. 회색은 색이 아니라 **빚**이다 —
누군가 손으로 깔아 주기를 기다리는 동안 그 자리는 영원히 안 재진다.

그런데 손으로 깔면 **판이 사람마다 다르다.** 내 기계에서 8.18 이 통과한 스캔이
CI 의 8.21 에서 빨개지면 우리는 그 빨강을 「환경 탓」으로 읽고 끄게 된다(D-353).
그래서 판과 **해시**를 저장소가 들고 있고, 받은 파일이 그 해시가 아니면 **거절한다.**
「깔았다」가 진술이 아니라 확인 행위가 되는 자리다(D-323).

    python scripts/install_secret_scanner.py            # 없으면 받고, 있으면 그대로 둔다
    python scripts/install_secret_scanner.py --check    # 설치 여부·판만 말한다 (받지 않는다)
    python scripts/install_secret_scanner.py --self-test

종료 코드: 0 준비됨 · 1 실패(해시 불일치 포함) · 2 **판정 불가**(망이 없다 등)

★ 받은 것을 저장소에 넣지 않는다. `tools/` 는 `.gitignore` 가 잡는다 —
  저장소가 들고 있는 것은 **무엇을 받아야 하는가**(lock)이지 받은 물건이 아니다.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "scripts" / "secret_scanner.lock.json"
TOOLS = ROOT / "tools"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def platform_key() -> str | None:
    """이 기계가 lock 의 어느 칸인가. **모르면 모른다고 한다** — 짐작해서 받지 않는다."""
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    if machine not in ("x86_64", "amd64"):
        return None
    if sysname == "windows":
        return "windows_x64"
    if sysname == "linux":
        return "linux_x64"
    return None


def load_lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def installed_path() -> Path | None:
    """이미 있는 스캐너를 찾는다 — **밖에 사러 가기 전에 안을 뒤진다**(D-333 ①)."""
    for cand in (TOOLS / "gitleaks.exe", TOOLS / "gitleaks"):
        if cand.is_file():
            return cand
    found = shutil.which("gitleaks")
    return Path(found) if found else None


def installed_version(exe: Path) -> str | None:
    try:
        out = subprocess.run([str(exe), "version"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (out.stdout or b"").decode("utf-8", "replace").strip()
    return text.lstrip("v") or None


def sha256_of(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def extract(blob: bytes, member: str, dest_dir: Path) -> Path:
    """압축에서 실행 파일 **하나만** 꺼낸다. 이름을 lock 이 정한다 — 압축 안을 훑어
    「실행 파일 같아 보이는 것」을 고르면 그 판단이 다음 판에서 조용히 달라진다."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / member
    if blob[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            data = z.read(member)
    else:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
            fh = t.extractfile(member)
            if fh is None:
                raise KeyError(member)
            data = fh.read()
    out.write_bytes(data)
    out.chmod(0o755)
    return out


def install(lock: dict, key: str) -> tuple[int, Path | None]:
    art = lock["artifacts"][key]
    url, want = art["url"], art["sha256"]
    print(f"[SCANNER] 받는다: {lock['tool']} {lock['version']} ({key})")
    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            blob = r.read()
    except (urllib.error.URLError, OSError) as exc:
        print(f"[SCANNER] 내려받지 못했다: {type(exc).__name__} {exc}")
        print("[SCANNER] **판정 불가** — 망이 없는 것과 해시가 틀린 것은 다른 사실이다")
        return EXIT_UNDECIDABLE, None
    got = sha256_of(blob)
    if got != want:
        # ★ 여기가 lock 의 전부다. 다르면 **쓰지 않는다** — 「아마 맞겠지」로 넘기면
        #   고정한 적이 없는 것과 같다.
        print(f"[SCANNER] ✗ 해시 불일치 — 설치를 **거절한다**\n"
              f"          기대 {want}\n          실제 {got}")
        return EXIT_FAIL, None
    print(f"[SCANNER] ✓ 해시 일치 {got[:16]}… (lock: {LOCK.relative_to(ROOT)})")
    try:
        exe = extract(blob, art["member"], TOOLS)
    except (KeyError, OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(f"[SCANNER] 압축에서 {art['member']} 를 못 꺼냈다: {type(exc).__name__} {exc}")
        return EXIT_FAIL, None
    print(f"[SCANNER] 설치: {exe}")
    return EXIT_OK, exe


def self_test() -> int:
    """lock 이 lock 노릇을 하는지 본다 (D-277 양성·음성)."""
    bad = []
    lock = load_lock()
    if lock.get("version", "").startswith("v"):
        bad.append("판에 'v' 가 붙어 있다 — `gitleaks version` 출력과 대조가 어긋난다")
    for key, art in lock["artifacts"].items():
        if len(art.get("sha256", "")) != 64:
            bad.append(f"{key}: sha256 이 64자가 아니다 — 고정한 적이 없는 것과 같다")
        if lock["version"] not in art.get("url", ""):
            bad.append(f"{key}: url 이 판({lock['version']})과 어긋난다 — "
                       f"판만 올리고 주소를 안 고치면 lock 이 거짓말을 한다")
    # 음성 대조 — 한 바이트만 달라도 해시가 갈리는가
    if sha256_of(b"a") == sha256_of(b"b"):
        bad.append("해시 함수가 두 입력을 같다고 한다 — 대조가 눈이 멀었다")
    # 양성 대조 — 알려진 값
    if sha256_of(b"") != ("e3b0c44298fc1c149afbf4c8996fb924"
                          "27ae41e4649b934ca495991b7852b855"):
        bad.append("빈 입력의 sha256 이 알려진 값과 다르다")
    # ★ pre-commit 과 판이 어긋나면 두 벌이 다른 것을 잡는다 (D-369)
    pc = ROOT / ".pre-commit-config.yaml"
    if pc.is_file():
        text = pc.read_text(encoding="utf-8", errors="replace")
        if "gitleaks" in text and f"v{lock['version']}" not in text:
            bad.append(f".pre-commit-config.yaml 의 gitleaks 판이 lock({lock['version']})과 "
                       f"다르다 — 두 벌은 반드시 어긋난다 (D-369)")
    if bad:
        print("[SCANNER] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print(f"    {b}")
        return EXIT_FAIL
    print(f"[SCANNER] 자기시험 통과 — lock {lock['tool']} {lock['version']} · "
          f"판/주소/해시 정합 · pre-commit 판 일치")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="시크릿 스캐너 고정 설치 (P-12 ② · D-387)")
    ap.add_argument("--check", action="store_true", help="받지 않고 상태만 말한다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    lock = load_lock()
    exe = installed_path()
    if exe:
        ver = installed_version(exe)
        same = ver == lock["version"]
        print(f"[SCANNER] 이미 있다: {exe} (판 {ver or '알 수 없음'}) — "
              f"lock {lock['version']} {'일치' if same else '★ 불일치'}")
        if same:
            return EXIT_OK
        if args.check:
            return EXIT_FAIL
    elif args.check:
        print(f"[SCANNER] 스캐너가 없다 — `python {Path(__file__).name}` 로 세운다")
        return EXIT_FAIL

    key = platform_key()
    if key is None or key not in lock["artifacts"]:
        print(f"[SCANNER] 이 기계({platform.system()}/{platform.machine()})에 맞는 칸이 "
              f"lock 에 없다 — **판정 불가**. 짐작해서 받지 않는다")
        return EXIT_UNDECIDABLE
    rc, exe = install(lock, key)
    if rc != EXIT_OK or exe is None:
        return rc
    ver = installed_version(exe)
    if ver != lock["version"]:
        print(f"[SCANNER] ✗ 받은 것이 스스로 말하는 판({ver})이 lock({lock['version']})과 다르다")
        return EXIT_FAIL
    print(f"[SCANNER] 준비됨 — {lock['tool']} {ver}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
