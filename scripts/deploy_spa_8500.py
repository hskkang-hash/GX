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
- **직전 세대 자산 남김** (WO-GRDX-20261002-11 AC-1b): 교체 뒤 직전 세대의 `assets/` 해시 파일을 한 세대만 되살린다
  (옛 탭이 가리키는 번들이 404 가 되어 흰 화면이 되는 것을 막는다 · 두 세대 전 것은 지운다 · 키 모양이 든 옛 번들은 안 남긴다).
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
GEN_FILE = ".gx-spa-gen.json"  # 배포 때마다 「이번 세대가 가져온 자산 이름」을 적는다 — 한 세대 남김의 장부
# 키가 든 옛 번들은 남기지 않는다(WO-GRDX-20261002-11 AC-1b ①). 모양만 보는 거친 그물 — 값은 적지 않는다.
KEY_RE = re.compile(rb"AIza[0-9A-Za-z_-]{35}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----")


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


def carry_previous(old: Path, stage: Path, live: Path) -> tuple[list[str], list[str]]:
    """**직전 세대 해시 자산을 한 세대만 남긴다** (WO-GRDX-20261002-11 AC-1b ①).

    배포가 `assets/` 를 통째로 바꾸면, 전에 열어 둔 탭이 가리키는 옛 번들이 404 가 되어 흰 화면이 된다.
    그래서 `old`(배포 직전의 8500 = 백업)의 자산 중 **직전 세대가 가져온 것**을 새 `live/assets` 에 되살린다.
    - 직전 세대 = `old/GEN_FILE` 의 `current` 목록. 장부가 없으면(첫 적용) `old/assets` 전부.
    - 두 세대 전 것(옛 장부에 없고 직전에 남겨진 것)은 되살리지 않는다 → 저절로 지워진다.
    - 새 세대에도 있는 이름은 건드리지 않는다. 키 모양이 든 옛 파일은 남기지 않는다(`KEY_RE`).
    반환: (남긴 이름들, 키 때문에 버린 이름들). 새 장부(`live/GEN_FILE`)도 여기서 쓴다."""
    new_assets = stage / "assets"
    cur = sorted(p.name for p in new_assets.iterdir() if p.is_file()) if new_assets.is_dir() else []
    kept: list[str] = []
    dropped: list[str] = []
    old_assets = old / "assets"
    if old_assets.is_dir():
        try:
            prev = set(json.loads((old / GEN_FILE).read_text(encoding="utf-8"))["current"])
        except (OSError, ValueError, KeyError, TypeError):
            prev = {p.name for p in old_assets.iterdir() if p.is_file()}
        for name in sorted(prev):
            src = old_assets / name
            if name in cur or not src.is_file():
                continue
            if KEY_RE.search(src.read_bytes()):
                dropped.append(name)
                continue
            (live / "assets").mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, live / "assets" / name)
            kept.append(name)
    (live / GEN_FILE).write_text(json.dumps({"current": cur}, ensure_ascii=False), encoding="utf-8")
    return kept, dropped


def live_matches_stage(stage: Path, live: Path, kept: list[str]) -> bool:
    """배포본이 스테이징과 같다 — 단, 남긴 옛 자산과 장부 파일은 덤으로 허용한다(그 밖의 덤은 빨강)."""
    extra_ok = {f"assets/{n}" for n in kept} | {GEN_FILE}
    want = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in stage.rglob("*") if p.is_file()}
    got = {p.relative_to(live).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
           for p in live.rglob("*") if p.is_file()}
    return all(got.get(k) == v for k, v in want.items()) and set(got) - set(want) <= extra_ok


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
    kept, dropped = carry_previous(backup, stage, LIVE)
    print(f"{TAG} 직전 세대 자산 {len(kept)} 개 남김 · 키 모양이라 버린 것 {len(dropped)} 개")
    tree_ok = live_matches_stage(stage, LIVE, kept)
    served = _served_index()
    served_ok = served is not None and served == new_index and served != before_index
    text_ok = None
    if expect_text:
        text_ok = any(expect_text.encode("utf-8") in p.read_bytes()
                      for p in (stage / "assets").glob("*.js"))
    smoke_exit = None if no_smoke else _smoke()
    code, verdict = judge(drill_ok=True, tree_ok=tree_ok, served_ok=served_ok,
                          text_ok=text_ok, smoke_exit=smoke_exit)
    line.update(kept_prev_assets=len(kept), dropped_key_assets=len(dropped),
                served_index=served, tree_ok=tree_ok, text_ok=text_ok, smoke_exit=smoke_exit)
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
    # ── 한 세대 남김 (AC-1b ①) ──
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)

        def gen(name: str, files: dict[str, str]) -> Path:
            d = t / name
            (d / "assets").mkdir(parents=True)
            (d / "index.html").write_text("<script src=/assets/index-%s.js></script>" % name, encoding="utf-8")
            for fn, body in files.items():
                (d / "assets" / fn).write_text(body, encoding="utf-8")
            return d

        def deploy_sim(live: Path, stage: Path) -> tuple[list[str], list[str]]:
            before = t / ("bk_" + stage.name)
            shutil.copytree(live, before)
            replace_contents(stage, live)
            return carry_previous(before, stage, live)

        live = t / "live"
        live.mkdir()
        g1 = gen("g1", {"index-g1.js": "one"})
        g2 = gen("g2", {"index-g2.js": "two", "same.js": "s"})
        g3 = gen("g3", {"index-g3.js": "three"})
        replace_contents(g1, live)  # 장부 없는 첫 세대
        k2, _ = deploy_sim(live, g2)
        check("배포 뒤에도 직전 세대 자산이 서빙 자리에 있다", (live / "assets" / "index-g1.js").is_file()
              and (live / "assets" / "index-g2.js").is_file() and k2 == ["index-g1.js"])
        check("남긴 옛 자산을 덤으로 허용하고 나머지는 스테이징과 같다", live_matches_stage(g2, live, k2))
        k3, _ = deploy_sim(live, g3)
        check("두 세대 전 자산은 지워진다", not (live / "assets" / "index-g1.js").exists()
              and (live / "assets" / "index-g2.js").is_file() and (live / "assets" / "same.js").is_file()
              and k3 == ["index-g2.js", "same.js"])
        g4 = gen("g4", {"index-g4.js": "four", "same.js": "s2"})
        deploy_sim(live, g4)
        check("같은 이름은 새 세대 내용이다", (live / "assets" / "same.js").read_text(encoding="utf-8") == "s2")
        # 키 모양이 든 옛 번들은 남기지 않는다
        fake = "AIza" + "x" * 35
        g5 = gen("g5", {"index-g5.js": "five", "leaky.js": "var k='" + fake + "'"})
        replace_contents(g5, live)
        carry_previous(g5, g5, live)  # 장부를 g5 로 맞춘다
        g6 = gen("g6", {"index-g6.js": "six"})
        k6, d6 = deploy_sim(live, g6)
        check("키가 든 옛 번들은 남기지 않는다", "leaky.js" in d6 and not (live / "assets" / "leaky.js").exists()
              and "index-g5.js" in k6)
    print(f"{TAG} 자기시험 {15 - fails}/15")
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
