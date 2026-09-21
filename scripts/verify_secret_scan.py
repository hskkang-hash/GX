#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""시크릿 스캔 판정 — **어디를 보는가가 판정의 절반이다** (P-12 ② · D-311).

    "secrets — 사유: 스캐너 미설치. 해제: 스캐너 설치 + lock 고정(D-387) → 잼."

스캐너를 깔면 끝날 줄 알았다. 깔고 나서 처음 돌린 날 [실측 2026-09-17] 나온 것:

    파일 면(--no-git)   19건        이력 면(--source .)   1건

같은 저장소, 같은 규칙, **열아홉 배 차이.** 어느 쪽도 거짓말이 아니었다 —
**서로 다른 질문에 답하고 있었다.**

    파일 면 : 이 디스크에 무엇이 있는가   ← 빌드 산출물·로컬 `.env.stg` 까지 센다
    이력 면 : 무엇이 저장소에 들어갔는가  ← 커밋된 것만 센다

우리가 물어야 하는 것은 **「저장소가 무엇을 나르는가」**다. 로컬 빌드 산출물에 든 지도
클라이언트 키는 유출이 아니다(D-003 — 클라이언트 키는 원래 브라우저에 간다). 반대로
예제 HTML 에 박힌 토큰 한 줄은 유출이다 — 그것은 **모두에게 복제된다.**

그래서 이 판정기는 파일 면을 훑고 나서 **git 이 그 파일을 나르는지**로 가른다.
「무시된 파일에서 나온 것」은 건수로 말하되 빨강으로 세지 않는다(D-301 — 0건과
안 본 것을 가르는 그 규칙의 반대편: **본 것을 안 본 것처럼 지우지도 않는다**).

    python scripts/verify_secret_scan.py             # 판정
    python scripts/verify_secret_scan.py --self-test # 심어 보고 잡는가 (D-289)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(스캐너 없음)

★ 래칫 (D-311): 이력에 이미 든 것은 `.gitleaksignore` 가 사유와 함께 고정한다.
  기존 빚에 영원히 빨간 게이트는 꺼진다 — 꺼진 게이트는 아무것도 안 지킨다(D-353).
"""
from __future__ import annotations

import argparse
import json
import secrets as _secrets
import shutil
import string as _string
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".gitleaks.toml"
EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 큰 잠금 파일 표본의 한 줄. **이 모양이 오탐을 내던 자리다** — 60자 이상 base64 + `==`.
_INTEGRITY_SAMPLE = ("sha512-kzy+Az4Dn+5dCR0FMk1qzlGaqbgNSi0a7qLr17ghfVnqbLYmhh"
                     "ELjgLOKU9cjjIm5L2KMEH2qRq5QHlacO90kA==")

#: ★ **출생 표본** (D-310) — 이 도구를 만들게 한 것은 합성 예제가 아니라 그날의 세 수다.
#:   [실측 2026-09-17] 스캐너를 처음 깔고 돌린 자리:
#:
#:       파일 면 19건 · 이력 면 1건 · 그중 저장소가 실제로 나르던 것 1건
#:
#:   열아홉과 하나 사이의 차이가 전부 **스캔 면**이었다. 어느 수를 보고하느냐로
#:   「유출 19건」도 되고 「유출 1건」도 된다 — 그래서 이 도구의 첫 일은 탐지가 아니라
#:   **면을 가르는 것**이다. 아래 자기시험이 세 수 각각의 갈래를 판정한다.
BIRTH_SAMPLE_SURFACE = (19, 1, 1)   # (파일 면, 이력 면, 저장소가 나르던 것)

#: ★ 출생 표본 ② — **큰 파일에서 눈이 감기던 자리.** 같은 `integrity` 한 줄이
#:   118바이트에서는 허용되고 202KB 에서는 오탐이었다. 규칙이 아니라 **크기**가 갈랐다.
BIRTH_SAMPLE_CHUNK = (118, 202_000)   # (허용되던 크기, 오탐 나던 크기) 단위 바이트

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def find_scanner() -> Path | None:
    """`tools/` 를 먼저 본다 — lock 이 고정한 판이 거기 산다(D-387)."""
    for cand in (ROOT / "tools" / "gitleaks.exe", ROOT / "tools" / "gitleaks"):
        if cand.is_file():
            return cand
    found = shutil.which("gitleaks")
    return Path(found) if found else None


def run_scan(exe: Path, source: Path, no_git: bool) -> list[dict] | None:
    """스캔 한 번. 보고서를 못 읽으면 **None** — 0건과 구별한다(D-301)."""
    tmp = Path(tempfile.mkdtemp(prefix="gxleaks."))
    report = tmp / "report.json"
    cmd = [str(exe), "detect", "--source", str(source), "--config", str(CONFIG),
           "--no-banner", "--redact", "--report-format", "json",
           "--report-path", str(report)]
    if no_git:
        cmd.append("--no-git")
    try:
        subprocess.run(cmd, capture_output=True, timeout=900)
        if not report.is_file():
            return None
        return json.loads(report.read_text(encoding="utf-8") or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def rel(path: str) -> str:
    """저장소 기준 상대 경로로 만든다.

    ★ [실측 2026-09-17] 이 함수가 없을 때 `git check-ignore` 가 **한 건도 못 맞혔다.**
      스캐너는 `C:\\GuardianX\\…\\frontend\\.env.stg` 를 절대 경로로 돌려주는데
      `check-ignore` 는 저장소 기준 경로를 받는다. 그래서 **무시되는 파일이 전부
      「저장소가 나른다」로 분류**되었고, 게이트는 있지도 않은 유출로 빨개졌다 —
      잘못된 빨강은 잘못된 초록만큼 게이트를 빨리 죽인다(D-353).
    """
    p = path.replace("\\", "/")
    root = str(ROOT).replace("\\", "/").rstrip("/") + "/"
    return p[len(root):] if p.startswith(root) else p.lstrip("/")


def carried_by_git(paths: list[str]) -> dict[str, bool]:
    """git 이 이 파일을 나르는가 — 무시되면 아니다. **한 번에 물어본다.**"""
    if not paths:
        return {}
    norm = [rel(p) for p in paths]
    # ★ `-z` 로 주고받는다. 줄 단위로 하면 두 군데서 조용히 깨진다 [실측 2026-09-17]:
    #     ① `text=True` 로 보내면 윈도우에서 `\n` 이 `\r\n` 이 되고, git 은 그 **CR 까지
    #        경로 이름의 일부**로 받는다.
    #     ② 경로에 그런 제어문자가 섞이면 git 은 답을 **C-따옴표로 감싸** 돌려준다:
    #        `"frontend/.env.stg\r"`. 그 문자열은 우리가 물어본 경로와 안 맞는다.
    #   결과는 「무시되는 파일을 저장소가 나른다고 읽는 것」 — 있지도 않은 유출로 빨개졌다.
    #   NUL 구분에는 줄바꿈 변환도 따옴표 감싸기도 없다. **묻는 말과 듣는 답이 같아진다.**
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-z", "--stdin"],
                             input="\0".join(norm).encode("utf-8"),
                             capture_output=True, timeout=120)
        ignored = {chunk.decode("utf-8", "replace").replace("\\", "/")
                   for chunk in out.stdout.split(b"\0") if chunk}
    except (OSError, subprocess.SubprocessError):
        # 못 물어봤으면 **전부 나른다고 본다** — 모르는 쪽으로 안전하게 기운다.
        return {p: True for p in paths}
    return {p: rel(p) not in ignored for p in paths}


def self_test(exe: Path) -> int:
    """**심어 보고 잡는지 본다.** 안 심어 본 탐지기는 눈이 멀어도 초록이다 (D-289)."""
    bad: list[str] = []

    # ── 출생 표본 ① 스캔 면 (D-310) ────────────────────────────────────────
    #   그날의 세 수가 서로 어긋나지 않는지부터 본다. 「저장소가 나르던 것」이
    #   「파일 면」보다 크면 분류가 뒤집힌 것이고, 그 뒤집힘이 이 도구의 유일한 판정이다.
    _disk, _hist, _carried = BIRTH_SAMPLE_SURFACE
    if not (_carried <= _disk and _hist <= _disk):
        bad.append("출생 표본 ① — 스캔 면 세 수가 어긋난다 "
                   "(저장소가 나르는 것이 파일 면보다 많을 수 없다)")
    if _disk == _carried:
        bad.append("출생 표본 ① — 파일 면과 저장소가 나르는 것이 같다면 이 도구는 "
                   "가를 것이 없다. 그날의 수는 19 대 1 이었다")
    _small, _large = BIRTH_SAMPLE_CHUNK
    if _small >= _large:
        bad.append("출생 표본 ② — 허용되던 크기가 오탐 나던 크기보다 크거나 같다. "
                   "이 도구가 태어난 사례는 **큰 파일에서만** 눈이 감기던 것이다")

    box = Path(tempfile.mkdtemp(prefix="gxleaks.st."))
    try:
        shutil.copy(CONFIG, box / ".gitleaks.toml")

        # ── 양성 ① 실제 형태의 키 ─────────────────────────────────────────
        #   AWS 문서 예제값(AKIA…EXAMPLE)을 심으면 기본 룰셋의 허용목록에 걸려
        #   **안 잡힌다** — 첫 시도가 정확히 그렇게 헛돌았다 [실측 2026-09-17].
        #   심는 값은 매번 새로 만든다. 고정 값을 쓰면 그 값이 곧 허용목록에 오른다.
        alphabet = _string.ascii_letters + _string.digits
        val = "".join(_secrets.choice(alphabet) for _ in range(32))
        plant = box / "plant.py"
        #: 이름에 **방향**을 붙인다 (D-337) — 나가는 키(우리가 남을 부름)와
        #:   들어오는 키(남이 우리를 부름)는 다른 것이고, 맨 이름은 그 둘을 덮는다.
        #:   수식어를 붙여도 스캐너는 그대로 잡는다 [실측 2026-09-17: 1건].
        plant.write_text('outbound_api_key = "' + val + '"\n', encoding="utf-8")
        hits = run_scan(exe, box, no_git=True)
        if hits is None:
            bad.append("자기시험: 보고서를 못 읽었다 — 스캐너가 돌지 않았다")
        elif not hits:
            bad.append("자기시험 양성 실패 — **심은 키 1건을 못 잡았다.** 이 게이트는 눈이 멀었다")
        plant.unlink()

        # ── 음성 ① 플레이스홀더·빈 값·공개 URL ────────────────────────────
        #   오탐 내는 룰은 사람이 끈다. 꺼진 룰은 없는 룰이다(D-353).
        ok = box / "ok.env.example"
        ok.write_text(
            "JUSO_API_KEY=CHANGE_ME\n"
            "KMA_APIHUB_KEY=\n"
            "SCHOOL_URL=https://api.data.go.kr/openapi/tn_pubr_public_elesch_mskul_lc_api\n",
            encoding="utf-8")
        clean = run_scan(exe, box, no_git=True)
        if clean is None:
            bad.append("자기시험: 음성 갈래에서 보고서를 못 읽었다")
        elif clean:
            bad.append("자기시험 음성 실패 — 플레이스홀더·빈 값·공개 URL 을 "
                       + str(len(clean)) + "건 잡았다. 오탐 내는 게이트는 꺼진다")
        ok.unlink()

        # ── 음성 ② 큰 잠금 파일의 integrity 해시 ──────────────────────────
        #   ★ 여기가 이 자기시험의 존재 이유다 [실측 2026-09-17]:
        #     같은 한 줄이 118바이트 파일에서는 허용되고 202KB 파일에서는 **오탐**이었다.
        #     gitleaks 가 파일을 청크로 나눠 읽으면 `regexTarget="line"` 이 볼 줄을 잃는다.
        #     규칙은 그대로인데 **눈만 감긴다.** 그래서 자리(paths)로 한 번 더 잠갔고,
        #     그 잠금이 살아 있는지를 **큰 파일로** 확인한다 — 작은 표본은 이 결함을 못 본다.
        rows = ['{"packages":{']
        for i in range(4000):
            rows.append('  "n' + str(i) + '": {"integrity": "' + _INTEGRITY_SAMPLE + '"},')
        rows.append("}}")
        (box / "package-lock.json").write_text("\n".join(rows), encoding="utf-8")
        lock_hits = run_scan(exe, box, no_git=True)
        if lock_hits is None:
            bad.append("자기시험: 잠금 파일 갈래에서 보고서를 못 읽었다")
        elif lock_hits:
            bad.append("자기시험 음성 실패 — package-lock.json 의 integrity 해시를 "
                       + str(len(lock_hits)) + "건 시크릿으로 읽는다 "
                       "(큰 파일에서 줄 허용목록이 꺼지는 자리 · 자리(paths) 잠금 확인)")
    finally:
        shutil.rmtree(box, ignore_errors=True)

    if bad:
        print("[SECRETS] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[SECRETS] 자기시험 통과 — 출생 표본 2(스캔 면 " + str(BIRTH_SAMPLE_SURFACE[0])
          + "대" + str(BIRTH_SAMPLE_SURFACE[1]) + " · 청크 경계 "
          + str(BIRTH_SAMPLE_CHUNK[0]) + "B/" + str(BIRTH_SAMPLE_CHUNK[1]) + "B) · "
          "양성 1(심은 키 32자) · 음성 2(플레이스홀더 · 큰 잠금 파일 4000줄)")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="시크릿 스캔 판정 (P-12 ② · D-311)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    exe = find_scanner()
    if exe is None:
        print("[SECRETS] 스캐너가 없다 — **판정 불가**")
        print("[SECRETS] 해제: python scripts/install_secret_scanner.py "
              "(판·해시는 scripts/secret_scanner.lock.json 이 고정 · D-387)")
        return EXIT_UNDECIDABLE
    print("[SECRETS] 스캐너: " + str(exe))

    if args.self_test:
        return self_test(exe)
    if self_test(exe) != EXIT_OK:
        return EXIT_FAIL

    # ── ① 파일 면 ───────────────────────────────────────────────────────────
    disk = run_scan(exe, ROOT, no_git=True)
    if disk is None:
        print("[SECRETS] 파일 면을 훑지 못했다 — **판정 불가**")
        return EXIT_UNDECIDABLE
    carried = carried_by_git([h["File"] for h in disk])
    inside = [h for h in disk if carried.get(h["File"], True)]
    outside = [h for h in disk if not carried.get(h["File"], True)]

    # ── ② 이력 면 (래칫 적용본) ─────────────────────────────────────────────
    hist = run_scan(exe, ROOT, no_git=False)
    if hist is None:
        print("[SECRETS] 이력 면을 훑지 못했다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    print("[SECRETS] [입력] " + str(len(disk)) + "건 — 파일 면 검출 "
          "(저장소가 나르는 것 " + str(len(inside)) + " · 저장소 밖 " + str(len(outside)) + ")")
    print("[SECRETS] [입력] " + str(len(hist)) + "건 — 이력 면 검출 "
          "(.gitleaksignore 래칫 적용 후 · D-311)")

    for h in outside:
        print("[SECRETS]   · 저장소 밖 " + h["RuleID"].ljust(24) + " "
              + rel(h["File"]) + ":" + str(h["StartLine"])
              + " — git 이 무시하는 자리다(빌드 산출물·로컬 env). 빨강으로 세지 않는다")

    rc = EXIT_OK
    for h in inside:
        print("[SECRETS] ✗ 저장소가 나른다 " + h["RuleID"].ljust(24) + " "
              + rel(h["File"]) + ":" + str(h["StartLine"]))
        rc = EXIT_FAIL
    for h in hist:
        print("[SECRETS] ✗ 이력에 있다 " + h["RuleID"].ljust(24) + " "
              + rel(h["File"]) + ":" + str(h["StartLine"]) + " (커밋 " + h["Commit"][:12] + ")")
        print("[SECRETS]     고쳤으면 **사유와 함께** .gitleaksignore 에 지문을 적는다 — "
              "지문: " + h["Fingerprint"])
        rc = EXIT_FAIL
    if rc == EXIT_OK:
        print("[SECRETS] 통과 — 저장소가 나르는 자리 0건 · 이력 0건 (래칫 적용)")
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    _n_py = sum(1 for _p in ROOT.rglob("*.py")
                if ".git" not in _p.parts and "node_modules" not in _p.parts)
    gate_header(__file__, measured=("저장소에 **비밀 값이 남았는가** — **분모 %s개**(저장소 파이썬 전수 · "
              "지금 셌다) + 이력 면(git). 표면과 이력은 **다른 분모**다 — "
              "한쪽만 초록이면 다른 쪽은 안 잰 것이다" % (_n_py or "못 셌다")))
    sys.exit(main())
