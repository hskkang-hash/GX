#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-341 — **8500 에 새 화면을 올린다. 백업 → 교체 → 검증 → 실패하면 복원.** (턴 AJ · 2026-09-25)

한 문장
-------
    python scripts/deploy_spa_8500.py --from-build dist_aj --expect-text "forgot-password/availability" \\
        --reason "P-341 턴 AJ 새 화면"
    → 빌드 통(`gx-fe-build:/app/_bld_u1ab/<dist>`)에서 스테이징으로 꺼낸다
    → 지금 `C:/GuardianX/gx-spa` 를 백업(파일 수 · 나무 sha)하고 백업이 원본과 같은지 잰다
    → **되돌리기 연습**: 백업을 연습 자리로 복원해 원본과 같은지 잰다 — 안 같으면 올리지 않는다
    → 교체 → 검증(나무 sha == 스테이징 · 8500 이 새 index 를 준다 · 새 문구 1 · 스모크)
    → 검증이 하나라도 빨강이면 **백업으로 자동 복원**하고 복원도 잰다
    → `evidence/OPS-27/deploys.jsonl` 에 한 줄(시각 · 사유 · 커밋 · 백업 · 전후 index · 결과).

왜 이 모양인가 [세종 P-341 · 불변 「배포하지 않은 화면은 잰 화면이 아니다」]
---------------------------------------------------------------------------
8500 은 대표 PC 의 운영 모양 서버(nginx 가 `C:/GuardianX/gx-spa` 를 준다)이지 운영계가
아니다. 되돌리기는 백업 복사 한 줄 — 그래서 **복원이 되는지를 올리기 전에 먼저 잰다.**
폴더 자체는 지우지 않고 **안의 것만** 바꾼다(nginx 가 그 폴더를 묶어 두었다 — 폴더를 새로
만들면 묶임이 옛 inode 를 볼 수 있다).

지키는 선
---------
- 자리는 하나다: `LIVE`(인자로 다른 폴더를 받지 않는다 · 시험만 함수 인자로 바꾼다).
- 백업은 지우지 않는다(덧붙이기만) · 로그 줄도 지우지 않는다.
- 값 0 — 로그인 자격은 `smoke_live` 가 제 규칙으로 읽고, 여기는 이름도 안 적는다.

    python scripts/deploy_spa_8500.py --from-build dist_aj --reason "…"   # 올리기
    python scripts/deploy_spa_8500.py --restore <백업 폴더> --reason "…"   # 되돌리기 한 줄
    python scripts/deploy_spa_8500.py --self-test                         # 판정 규칙만

종료 코드: 0 초록(올라갔다) · 1 빨강(검증 실패 → 복원했다 · 또는 복원 연습 실패로 안 올렸다) · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAG = "[DEPLOY-8500]"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

LIVE = Path("C:/GuardianX/gx-spa")
BACKUPS = Path("C:/GuardianX/_spa_backups")
STAGE = Path("C:/GuardianX/_spa_stage")
BUILD_CONTAINER = "gx-fe-build"
BUILD_ROOT = "/app/_bld_u1ab"
SITE = "http://localhost:8500"
LOG = ROOT / "docs" / "agent" / "evidence" / "OPS-27" / "deploys.jsonl"
KST = dt.timezone(dt.timedelta(hours=9))
INDEX_RE = re.compile(r"assets/(index-[A-Za-z0-9_-]+\.js)")


# ── 순수 함수(시험이 부른다) ──────────────────────────────────────────────────────
def tree(root: Path) -> tuple[int, str]:
    """(파일 수, 나무 sha) — 상대 경로와 파일 sha 를 정렬해 한 번 더 해시한다. 시각은 안 본다."""
    lines = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            lines.append(f"{rel}\t{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return len(lines), hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def index_name(root: Path) -> str | None:
    """index.html 이 부르는 진입 js 이름. 폴더에 옛 index-*.js 가 여럿 남아 있어도 이것 하나가 정본이다."""
    html = root / "index.html"
    if not html.is_file():
        return None
    m = INDEX_RE.search(html.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def replace_contents(src: Path, dst: Path) -> None:
    """`dst` 폴더는 두고 **안의 것만** `src` 와 같게 만든다."""
    dst.mkdir(parents=True, exist_ok=True)
    for child in list(dst.iterdir()):
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def judge(*, drill_ok: bool, tree_ok: bool, served_ok: bool, text_ok: bool | None,
          smoke_exit: int | None) -> tuple[int, str]:
    """검증 넷 → (종료 코드, 한 줄). `text_ok`·`smoke_exit` 가 None 이면 그 칸은 안 잰 것 — 회색."""
    if not drill_ok:
        return EXIT_FAIL, "빨강 — 되돌리기 연습이 원본과 다르다 · 올리지 않았다"
    bad = []
    if not tree_ok:
        bad.append("배포본 나무 sha ≠ 스테이징")
    if not served_ok:
        bad.append("8500 이 새 index 를 안 준다")
    if text_ok is False:
        bad.append("새 문구가 번들에 없다")
    if smoke_exit not in (None, 0, 2):
        bad.append(f"스모크 빨강(exit {smoke_exit})")
    if bad:
        return EXIT_FAIL, "빨강 — " + " · ".join(bad) + " → 백업으로 복원"
    gray = []
    if text_ok is None:
        gray.append("새 문구 안 잼")
    if smoke_exit in (None, 2):
        gray.append("스모크 회색")
    if gray:
        return EXIT_OK, "초록(회색 칸 " + " · ".join(gray) + ") — 올라갔다"
    return EXIT_OK, "초록 — 올라갔다 · 새 index · 새 문구 · 스모크 셋 200"


def drill(backup: Path, original: tuple[int, str]) -> bool:
    """되돌리기 연습 — 백업을 **연습 자리**로 복원하고(진짜 복원과 같은 함수) 원본과 대 본다."""
    with tempfile.TemporaryDirectory(prefix="gx_spa_drill_") as tmp:
        target = Path(tmp) / "spa"
        replace_contents(backup, target)
        return tree(target) == original


# ── 바깥(호스트) ────────────────────────────────────────────────────────────────
def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _fetch(path: str) -> bytes | None:
    try:
        req = urllib.request.Request(SITE + path, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read() if r.status == 200 else None
    except OSError:
        return None


def _served_index() -> str | None:
    body = _fetch("/")
    if body is None:
        return None
    m = INDEX_RE.search(body.decode("utf-8", errors="replace"))
    return m.group(1) if m else None


def _stage_from_build(dist: str) -> Path | None:
    if not re.fullmatch(r"dist[A-Za-z0-9_]*", dist):
        print(f"{TAG} 빌드 폴더 이름이 이상하다: {dist!r}")
        return None
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    r = subprocess.run(["docker", "cp", f"{BUILD_CONTAINER}:{BUILD_ROOT}/{dist}", STAGE.as_posix()],
                       capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0 or not (STAGE / "index.html").is_file():
        print(f"{TAG} 빌드 통에서 못 꺼냈다: {r.stderr.strip()[:200]}")
        return None
    return STAGE


def _smoke() -> int:
    r = subprocess.run([sys.executable, str(HERE / "smoke_live.py")], cwd=ROOT, timeout=120)
    return r.returncode


def _log(line: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _now() -> str:
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def deploy(dist: str, expect_text: str | None, reason: str, no_smoke: bool) -> int:
    if not LIVE.is_dir():
        print(f"{TAG} 못 쟀다 — {LIVE} 가 없다")
        return EXIT_UNDECIDABLE
    stage = _stage_from_build(dist)
    if stage is None:
        return EXIT_UNDECIDABLE
    new_tree, new_index = tree(stage), index_name(stage)

    before_tree, before_index = tree(LIVE), index_name(LIVE)
    stamp = dt.datetime.now(KST).strftime("%Y%m%dT%H%M%S")
    backup = BACKUPS / stamp
    shutil.copytree(LIVE, backup)
    if tree(backup) != before_tree:
        print(f"{TAG} 못 쟀다 — 백업이 원본과 다르다 · 아무것도 안 바꿨다")
        return EXIT_UNDECIDABLE
    print(f"{TAG} 백업 {backup} · 파일 {before_tree[0]} · 나무 sha {before_tree[1][:12]} · index {before_index}")

    drill_ok = drill(backup, before_tree)
    print(f"{TAG} 되돌리기 연습: {'같다' if drill_ok else '다르다'}")
    line = {"at": _now(), "reason": reason, "commit": _git("rev-parse", "--short", "HEAD"),
            "build": dist, "backup": backup.as_posix(),
            "before": {"files": before_tree[0], "tree": before_tree[1][:12], "index": before_index},
            "new": {"files": new_tree[0], "tree": new_tree[1][:12], "index": new_index},
            "drill_ok": drill_ok}
    if not drill_ok:
        code, verdict = judge(drill_ok=False, tree_ok=False, served_ok=False, text_ok=None, smoke_exit=None)
        _log({**line, "exit": code, "verdict": verdict})
        print(f"{TAG} {verdict}")
        return code

    replace_contents(stage, LIVE)
    tree_ok = tree(LIVE) == new_tree
    served = _served_index()
    served_ok = served is not None and served == new_index and served != before_index
    text_ok = None
    if expect_text:
        text_ok = any(expect_text.encode("utf-8") in p.read_bytes()
                      for p in (LIVE / "assets").glob("*.js"))
    smoke_exit = None if no_smoke else _smoke()
    code, verdict = judge(drill_ok=True, tree_ok=tree_ok, served_ok=served_ok,
                          text_ok=text_ok, smoke_exit=smoke_exit)
    line.update(served_index=served, tree_ok=tree_ok, text_ok=text_ok, smoke_exit=smoke_exit)
    if code == EXIT_FAIL:
        replace_contents(backup, LIVE)
        line["restored_ok"] = tree(LIVE) == before_tree
    _log({**line, "exit": code, "verdict": verdict})
    print(f"{TAG} 새 index {new_index} · 8500 이 준 index {served}")
    print(f"{TAG} {verdict}")
    return code


def restore(backup_dir: str, reason: str) -> int:
    backup = Path(backup_dir)
    if not (backup / "index.html").is_file():
        print(f"{TAG} 못 쟀다 — {backup} 에 index.html 이 없다")
        return EXIT_UNDECIDABLE
    want = tree(backup)
    before_index = index_name(LIVE)
    replace_contents(backup, LIVE)
    ok = tree(LIVE) == want
    served = _served_index()
    code = EXIT_OK if ok and served == index_name(backup) else EXIT_FAIL
    verdict = "초록 — 복원했다" if code == EXIT_OK else "빨강 — 복원한 것이 백업과 다르다"
    _log({"at": _now(), "reason": reason, "commit": _git("rev-parse", "--short", "HEAD"),
          "restore_from": backup.as_posix(), "before_index": before_index, "served_index": served,
          "files": want[0], "tree": want[1][:12], "exit": code, "verdict": verdict})
    print(f"{TAG} {verdict} · 파일 {want[0]} · index {served}")
    return code


def self_test() -> int:
    """판정 규칙과 복원 경로를 임시 폴더로만 잰다 — 8500 은 안 건드린다."""
    fails = 0

    def check(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        fails += 0 if cond else 1

    check("되돌리기 연습 실패 → 빨강(안 올린다)",
          judge(drill_ok=False, tree_ok=True, served_ok=True, text_ok=True, smoke_exit=0)[0] == EXIT_FAIL)
    check("8500 이 옛 index → 빨강",
          judge(drill_ok=True, tree_ok=True, served_ok=False, text_ok=True, smoke_exit=0)[0] == EXIT_FAIL)
    check("새 문구 없음 → 빨강",
          judge(drill_ok=True, tree_ok=True, served_ok=True, text_ok=False, smoke_exit=0)[0] == EXIT_FAIL)
    check("스모크 빨강 → 빨강",
          judge(drill_ok=True, tree_ok=True, served_ok=True, text_ok=True, smoke_exit=1)[0] == EXIT_FAIL)
    ok_code, ok_line = judge(drill_ok=True, tree_ok=True, served_ok=True, text_ok=True, smoke_exit=0)
    check("넷 다 초록 → 초록", ok_code == EXIT_OK and "회색" not in ok_line)
    check("스모크 회색은 초록이라 적되 회색 칸을 말한다",
          "회색" in judge(drill_ok=True, tree_ok=True, served_ok=True, text_ok=True, smoke_exit=2)[1])
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a", Path(tmp) / "b"
        (a / "assets").mkdir(parents=True)
        (a / "index.html").write_text('<script src="/assets/index-AAA.js"></script>', encoding="utf-8")
        (a / "assets" / "index-AAA.js").write_text("x", encoding="utf-8")
        b.mkdir()
        (b / "stale.txt").write_text("old", encoding="utf-8")
        replace_contents(a, b)
        check("안의 것만 바꾼다 — 옛 파일은 남지 않는다", tree(a) == tree(b) and not (b / "stale.txt").exists())
        check("index.html 이 부르는 이름을 읽는다", index_name(b) == "index-AAA.js")
        check("되돌리기 연습 — 같은 백업이면 같다", drill(a, tree(a)))
        (a / "assets" / "index-AAA.js").write_text("y", encoding="utf-8")
        check("되돌리기 연습 — 내용이 한 바이트 달라도 다르다", not drill(a, tree(b)))
    print(f"{TAG} 자기시험 {10 - fails}/10")
    return EXIT_OK if fails == 0 else EXIT_FAIL


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--from-build", help="빌드 통 안 폴더 이름(예: dist_aj)")
    ap.add_argument("--restore", help="되돌리기 — 백업 폴더 경로")
    ap.add_argument("--expect-text", help="새 번들에 있어야 할 글자(값 아님)")
    ap.add_argument("--reason")
    ap.add_argument("--no-smoke", action="store_true", help="재는 중(V_LOCK)이면 스모크를 건너뛴다")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if not a.reason:
        ap.error("--reason 이 필요하다 — 줄에 사유가 없으면 누가 왜 올렸는지 모른다")
    if a.restore:
        return restore(a.restore, a.reason)
    if not a.from_build:
        ap.error("--from-build 또는 --restore")
    return deploy(a.from_build, a.expect_text, a.reason, a.no_smoke)


if __name__ == "__main__":
    sys.exit(main())
