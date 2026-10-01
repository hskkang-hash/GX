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
import shutil
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


#: ★ P-393 (세종 판정 · 턴 AM SEC-05 FAIL) — 자기시험 표본을 무작위에서 고정으로 바꾼다.
#:   전에는 32자를 매번 새로 무작위로 뽑아 심었다(`secrets.choice`). 62진 어느 조합도
#:   나올 수 있다 — [추정] 극히 드물게 나온 조합의 섀넌 엔트로피가 기본 gitleaks
#:   엔트로피 임계 밑으로 떨어지면 그 회차만 못 잡을 수 있다. 부하 중(전량 시험과
#:   병렬) 두 번 실패하고 단독 실행에서는 통과했다는 관측은 이 저확률 사건이 반복
#:   횟수가 늘 때 표면화된 것과 앞뒤가 맞지만, 그날의 실패를 다시 재현하지는
#:   못했다 — 그래서 **추정**이다. 시간 제한(run_scan timeout=900s)이나 임시
#:   디렉터리 경합은 코드를 읽어도 원인으로 짚이지 않는다: `tempfile.mkdtemp` 는
#:   호출마다 새 이름을 받고, 병렬 self-test 는 서로 다른 프로세스의 서로 다른
#:   box 밑에서 돈다. 남는 것은 **표본값 자체의 우연**뿐이다 — 그래서 표본을
#:   고정한다: 같은 값은 매번 같은 결과를 낸다.
#:   ⚠ 이 판정기 자신도 저장소 파일 면 스캔 대상이다 — 표본 값을 리터럴 한 줄로
#:     적으면 이 게이트가 이 파일에서 스스로 유출을 본다. 그래서 기존 코드
#:     (`val = "".join(...)`)처럼 조각을 런타임에 이어 붙인다.
def _fixed_plant_samples() -> list[dict]:
    """형식별 고정 표본 5개 — **스캐너 규칙이 실제로 잡는 형식** 중에서 고른다
    (기본 gitleaks 룰셋 1 + `.gitleaks.toml` 커스텀 룰 3). 값은 전부 가짜다.
    스캐너의 판정 규칙(정규식·허용목록)은 이 표본 때문에 바꾸지 않았다 —
    아래 값들을 기존 규칙 경계 안에 맞췄을 뿐이다(P-203 예외 · 판정기만 고친다).
    """
    v_generic = "".join(["Qx7fT2mK", "9pL0wR4v", "N8sD1yA6", "Zc3hU5bJ"])         # 32자 — 기본 룰셋 generic(일반 키 규칙)
    v_kma = "".join(["Bn6xK2qW9e", "R4tY1uI0pA", "sQ"])                            # 22자 — gx-kma-auth-key
    v_datago = "".join(["aZ9bY8cX7dW6eV5fU4gT3", "%2B",
                         "hS2iR1jQ0kP9lO8mN7", "%3D%3D"])                           # gx-datago-service-key
    v_decoded = "".join(["QWxzZGZhc2RmYXNkZmFzZGZh", "c2RmYXNkZmFzZGZhc2RmYXNk",
                          "ZmFzZGZhc2RmYXNkZmFz", "ZGY="])                          # 72자 — gx-datago-service-key-decoded
    v_env = "".join(["Fk3", "Lm9", "Qs2", "Vt7"])                                  # gx-env-example-placeholder

    return [
        {"format": "generic(기본 룰셋 · 일반 키 규칙)", "path": "plant_generic.py",
         "content": 'outbound_api_key = "' + v_generic + '"\n',
         "clean_content": 'outbound_api_key = "CHANGE_ME"\n'},
        {"format": "gx-kma-auth-key", "path": "plant_kma.py",
         "content": 'kma_auth_key = "' + v_kma + '"\n',
         "clean_content": 'kma_auth_key = "your-kma-key-here"\n'},
        {"format": "gx-datago-service-key", "path": "plant_datago.py",
         "content": 'PUBLIC_DATA_SERVICE_KEY = "' + v_datago + '"\n',
         "clean_content": 'PUBLIC_DATA_SERVICE_KEY = "CHANGE_ME"\n'},
        {"format": "gx-datago-service-key-decoded", "path": "plant_datago_decoded.py",
         "content": 'legacy_service_key_decoded = "' + v_decoded + '"\n',
         "clean_content": 'legacy_service_key_decoded = "CHANGE_ME"\n'},
        {"format": "gx-env-example-placeholder", "path": "plant.env.example",
         "content": "SOME_SERVICE_TOKEN=" + v_env + "\n",
         "clean_content": "SOME_SERVICE_TOKEN=CHANGE_ME\n"},
    ]


#: 모듈 로드 시 한 번 고정한다 — 매 호출마다 같은 리스트를 새로 만들 이유가 없고,
#: 시험(test_p393)이 이 상수를 그대로 읽어 「값이 고정됐다」를 직접 확인한다.
FIXED_PLANT_SAMPLES = _fixed_plant_samples()

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


_BS = chr(92)


def norm_fingerprint(fp: str, root: Path | str | None = None) -> str:
    """[턴 AR · Q③] 지문을 **상대 · 슬래시 모양 하나로** 맞춘다.

    파일 면(`--no-git --source <ROOT 절대>`)의 지문은 `C:` + 역슬래시 + … + `X.json:rule:17` 모양(절대)이고
    `.gitleaksignore` 는 흔히 `docs/…/X.json:rule:17`(상대)이다 — 글자 그대로 견주면 어긋난다
    (턴 AQ 실측 · SEC-05 FAIL). 그래서 양쪽을 역슬래시→슬래시, ROOT 접두 제거로 맞춘 뒤 견준다.
    이력 면 지문(`커밋:파일:rule:줄`)도 같은 규칙으로 파일 부분만 맞춘다. 상대·절대 **둘 다** 맞는다.
    """
    r = str(root if root is not None else ROOT).replace(_BS, "/").rstrip("/") + "/"
    f = str(fp).strip().replace(_BS, "/")
    if f.lower().startswith(r.lower()):
        f = f[len(r):]
    else:
        i = f.lower().find(":" + r.lower())          # `커밋:C:/…/파일:rule:줄` 모양
        if i >= 0:
            f = f[:i + 1] + f[i + 1 + len(r):]
    return f


def load_ignored(path: Path | None = None) -> set[str]:
    """`.gitleaksignore` 의 지문 줄(주석·빈 줄 뺀)을 정규화해 모은다. 못 읽으면 빈 집합(= 아무것도 안 가린다)."""
    try:
        text = (path or ROOT / ".gitleaksignore").read_text(encoding="utf-8")
    except OSError:
        return set()
    return {norm_fingerprint(ln) for ln in text.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")}


def drop_ignored(hits: list[dict], ignored: set[str], root=None) -> tuple[list[dict], int]:
    """정규화 지문이 고정 목록에 있는 건을 뺀다 → (남은 것, 뺀 수). 뺀 수는 출력에 남긴다."""
    keep = [h for h in hits if norm_fingerprint(h.get("Fingerprint", ""), root) not in ignored]
    return keep, len(hits) - len(keep)


def _fingerprint_self_test() -> list[str]:
    bad: list[str] = []
    root = Path("C:" + _BS + "GuardianX" + _BS + "guardianx-source")
    ab = "C:" + _BS + "GuardianX" + _BS + "guardianx-source" + _BS + "docs" + _BS + "a" + _BS + "X.json:slack-webhook-url:17"
    rl = "docs/a/X.json:slack-webhook-url:17"
    if norm_fingerprint(ab, root) != rl or norm_fingerprint(rl, root) != rl:
        bad.append("지문 정규화 — 절대(역슬래시)와 상대(슬래시)가 같은 모양으로 안 모인다")
    if norm_fingerprint("abc123:" + ab, root) != "abc123:" + rl:
        bad.append("지문 정규화 — 이력 면 `커밋:절대경로:rule:줄` 을 못 맞춘다")
    if norm_fingerprint("docs/a/X.json:slack-webhook-url:18", root) == rl:
        bad.append("지문 정규화 — 줄 번호가 다른데 같다고 본다(과잉 가림)")
    hits = [{"Fingerprint": ab}, {"Fingerprint": "docs/a/X.json:slack-webhook-url:18"}]
    keep, n = drop_ignored(hits, {rl}, root)
    if n != 1 or len(keep) != 1 or keep[0]["Fingerprint"].endswith(":17"):
        bad.append("고정 목록 가리기 — 상대 줄 하나가 절대 지문 건을 못 가리거나 다른 줄까지 가린다")
    keep2, n2 = drop_ignored([{"Fingerprint": rl}], {norm_fingerprint(ab, root)}, root)
    if n2 != 1:
        bad.append("고정 목록 가리기 — 절대 줄이 상대 지문 건을 못 가린다")
    return bad


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
    bad: list[str] = _fingerprint_self_test()

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

        # ── 양성 5종 (P-393) — 형식별 고정 표본이 전부 잡히는가 ────────────
        #   ★ 예전에는 무작위 32자 하나만 심었다(위 상수 설명 참조). 이제는
        #   FIXED_PLANT_SAMPLES 다섯을 하나씩 심고 지운다 — 한 번에 하나만 두면
        #   어느 형식이 못 잡혔는지 바로 짚인다(집계 1건짜리 판정이면 못 짚는다).
        for _sample in FIXED_PLANT_SAMPLES:
            _target = box / _sample["path"]
            _target.write_text(_sample["content"], encoding="utf-8")
            hits = run_scan(exe, box, no_git=True)
            if hits is None:
                bad.append("자기시험 양성(" + _sample["format"] + "): 보고서를 못 읽었다 — 스캐너가 돌지 않았다")
            elif not hits:
                bad.append("자기시험 양성 실패(" + _sample["format"] + ") — "
                           "**고정 표본을 못 잡았다.** 이 게이트는 눈이 멀었다")
            _target.unlink()

        # ── 음성 5종 (P-393) — 같은 형식의 플레이스홀더 버전은 안 잡히는가 ──
        #   양성과 짝을 이룬다: 값만 가짜 티가 나는 플레이스홀더로 바꾸면
        #   같은 자리에서 0건이어야 한다(오탐 내는 룰은 사람이 끈다 · D-353).
        for _sample in FIXED_PLANT_SAMPLES:
            _target = box / _sample["path"]
            _target.write_text(_sample["clean_content"], encoding="utf-8")
            clean_hits = run_scan(exe, box, no_git=True)
            if clean_hits is None:
                bad.append("자기시험 음성(" + _sample["format"] + "): 보고서를 못 읽었다")
            elif clean_hits:
                bad.append("자기시험 음성 실패(" + _sample["format"] + ") — 플레이스홀더인데 "
                           + str(len(clean_hits)) + "건 잡았다. 오탐 내는 게이트는 꺼진다")
            _target.unlink()

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
          "양성 " + str(len(FIXED_PLANT_SAMPLES)) + "(고정 표본 · P-393) · "
          "음성 " + str(len(FIXED_PLANT_SAMPLES) + 2) + "(같은 형식 플레이스홀더 "
          + str(len(FIXED_PLANT_SAMPLES)) + " · 기존 플레이스홀더 1 · 큰 잠금 파일 4000줄 1)")
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
    # [턴 AR · Q③] 고정 목록(.gitleaksignore)을 상대·절대 둘 다 맞게 견주어 가린다.
    ignored = load_ignored()
    disk, n_dropped = drop_ignored(disk, ignored)
    if n_dropped:
        print("[SECRETS] 파일 면: 고정 목록(.gitleaksignore)과 정규화 지문이 맞아 " + str(n_dropped)
              + "건 뺐다(상대·절대 경로 모양 차이 · 턴 AR)")
    carried = carried_by_git([h["File"] for h in disk])
    inside = [h for h in disk if carried.get(h["File"], True)]
    outside = [h for h in disk if not carried.get(h["File"], True)]

    # ── ② 이력 면 (래칫 적용본) ─────────────────────────────────────────────
    hist = run_scan(exe, ROOT, no_git=False)
    if hist is None:
        print("[SECRETS] 이력 면을 훑지 못했다 — **판정 불가**")
        return EXIT_UNDECIDABLE
    hist, _n_h = drop_ignored(hist, ignored)

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
