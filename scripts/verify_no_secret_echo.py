#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""게이트는 값을 출력하지 않는다 — **그 규칙 자체를 재는 게이트** (P-135 ④).

    "`gxprobe_e2e`의 `GX_ROUTE_PASSWORD_ROLE0`이 세션 진단 출력에 나왔다."
     — 턴 Q §1-7, 사고 보고. 값이 저장소에 커밋되지 않았어도 세션 기록·로그
     파일에 남을 수 있다는 것이 이 게이트가 태어난 이유다.

세종 판정(P-135 ④): 「게이트·진단 스크립트가 값을 출력하지 않는다」 —
`.env`·`.env.gates`(저장소 루트 · 값은 저장소 밖 · `.gitignore` 가 잡는 파일)의
비밀값이 ⓐ `docs/agent/**`(evidence 포함)·`docs/review/**` 문서 ⓑ `--run "<명령>"`
으로 받은 명령의 stdout/stderr 에 **글자 그대로 · UTF-16-LE 로 · JSON 이스케이프된
채로** 나타나면 exit 1. 불변: 「게이트는 값을 출력하지 않는다 — 이름만.」이 규칙은
이 파일 자신에도 적용된다 — 아래 어디에도 실제 값을 담은 변수를 print 하지 않는다.

    python scripts/verify_no_secret_echo.py
    python scripts/verify_no_secret_echo.py --run "python scripts/verify_secret_scan.py"
    python scripts/verify_no_secret_echo.py --self-test   # 심어 보고 잡는가 (D-289)

대상 값 — 무엇을 「비밀」로 보는가
----------------------------------
키 이름에 `PASSWORD`·`SECRET`·`KEY`·`TOKEN`·`PASS`·`PW`·`CREDENTIAL` 중 하나가
(대소문자 무관) 들어 있고, 값 길이가 8자 이상인 것만 대상이다.

★ **제외 규칙은 손으로 뺀 목록이 아니라 이름의 생김새다.** URL·호스트·사용자명·
  컨테이너 이름은 위 낱말을 담지 않으므로 저절로 빠진다 — `.env.gates` 에 실제로
  있는 예로 이름을 대 둔다:
    `GX_API`(URL) · `GX_ROUTE_USER`·`GX_ROUTE_USER_ROLE0`·`GX_PROBE_USER`(사용자명) ·
    `GX_ROUTE_CONTAINER`(컨테이너 이름) · `MINIO_ENDPOINT`(호스트) ·
    `MINIO_BUCKET_NAME`(버킷 이름).
  이 여섯은 대상 낱말을 하나도 담지 않는다 — 대상 판정을 가르는 것은 이 정규식 하나뿐이고
  (`_SECRET_NAME`), 두 번째 목록을 손으로 만들지 않는다(두 벌은 반드시 어긋난다 · D-369).

값을 읽는 법 — 왜 `verify_route_alive.load_local_env` 를 그대로 부르지 않는가
------------------------------------------------------------------------------
`${VAR}` 참조를 펼치는 것(`expand_env_refs`)은 `verify_route_alive.py` 의 것을
**그대로** 가져다 쓴다 — D-457 이 밝힌 함정(셸은 펼치는데 로더가 안 펼겨 리터럴
`${NAME}` 을 그대로 보내는 것)이 두 번째 구현에서 되풀이되지 않게 하려는 것이다.
반면 `load_local_env` 자체는 **부르지 않는다** — 그 함수는 `LOCAL_ENV_KEYS`
화이트리스트만 `os.environ` 에 채운다(HTTP 호출용이라는 제 목적에 맞춘 것).
그 목록에는 `GX_ROUTE_PASSWORD_ROLE0`·`GX_PROBE_PASSWORD`(사고를 낸 바로 그 이름)가
없다 — 그대로 썼다면 **정작 사고가 난 값은 이 게이트의 사각지대**가 됐을 것이다.
그래서 이 파일은 `.env`·`.env.gates` 의 **모든** 키=값을 직접 읽고, 이름 패턴으로
대상을 가른다(위 문단). `expand_env_refs` 만 재사용하는 것이 반경 좁은 선택이다.

대조하는 법 — 파일은 바이트로 읽는다
-------------------------------------
값이 그대로(UTF-8) · UTF-16-LE 로 적힐 수도, JSON 문자열 안에서 이스케이프된
채로(큰따옴표·역슬래시 등) 적힐 수도 있다. 넷을 다 만들어 바이트로 찾는다(`_needles_for`).
이진·대용량(> 20MB)·`.bundle`·이미지·PDF·DB 덤프는 건너뛴다 — 건너뛴 수는 찍는다
(0건과 안 본 것을 가르는 규칙 · D-301의 반대편으로도 적용한다: 본 것을 안 본
것처럼 지우지 않되, 안 본 것을 본 것처럼 세지도 않는다).

종료 코드: 0 깨끗 · 1 값 발견 · 2 **판정 불가**(env 파일 없음 · 읽기 실패)
"""
from __future__ import annotations

import argparse
import json
import re
import secrets as _secrets
import shutil
import string as _string
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★ `verify_route_alive.expand_env_refs` 재사용 — `${VAR}` 를 셸과 같은 뜻으로 펼친다
#   (D-457). 값을 펼치는 까다로운 부분만 가져오고, 대상을 고르는 로직은 이 파일이
#   직접 가진다(위 문단 사유).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_route_alive import expand_env_refs  # noqa: E402

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[NO-ECHO]"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

#: 저장소 루트의 두 로컬(gitignored) env 파일. 이 절이 요구한 자리 그대로다.
ENV_FILES = (".env", ".env.gates")

#: 대상 이름 — 위 문단의 유일한 가르는 자리.
_SECRET_NAME = re.compile(r"(PASSWORD|SECRET|KEY|TOKEN|PASS|PW|CREDENTIAL)", re.I)
_MIN_VALUE_LEN = 8

#: 훑지 않는다 — 이진·대용량. `.dump` 는 postgres 커스텀 덤프(이진)라 여기 든다.
_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".pdf", ".bundle",
    ".zip", ".gz", ".7z", ".tar", ".exe", ".dll", ".so", ".pyc", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mov", ".avi", ".db", ".sqlite3", ".wasm", ".dump",
}
_MAX_FILE_BYTES = 20 * 1024 * 1024

#: 대조할 문서 자리 — evidence 는 `docs/agent` 아래에 이미 들어 있다(별도 트리 아님).
SCAN_ROOTS = ("docs/agent", "docs/review")


def _parse_env_file(path: Path) -> tuple[dict[str, str], str | None]:
    """`.env`·`.env.gates` 한 파일을 **모든** 키=값으로 읽는다(화이트리스트 없음).

    `${VAR}` 는 같은 파일의 앞줄 → `os.environ` 순으로 펼친다(`expand_env_refs`
    그대로 — D-457). 돌려준다: (키→값, 읽기 실패 사유 — 성공이면 None).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {}, type(exc).__name__
    seen: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if not k:
            continue
        seen[k] = expand_env_refs(v.strip().strip('"').strip("'"), seen)
    return seen, None


def collect_secrets(root: Path = ROOT) -> tuple[list[tuple[str, str, str]], list[str], list[str]]:
    """`.env`·`.env.gates` 를 읽어 「대상 값」만 추린다.

    돌려준다: ([(키, 값, 어느 파일들), ...], 읽은 파일 이름, 판정 불가 사유 목록).
    같은 (키, 값) 이 두 파일에 다 있으면 한 줄로 합친다; 같은 키가 파일마다
    **다른** 값이면(회전 도중 등) 둘 다 각각 대조한다 — 어느 쪽도 놓치지 않는다.
    """
    merged: dict[tuple[str, str], set[str]] = {}
    read_files: list[str] = []
    problems: list[str] = []
    for name in ENV_FILES:
        f = root / name
        if not f.is_file():
            problems.append(f"{name} 없음")
            continue
        kv, err = _parse_env_file(f)
        if err is not None:
            problems.append(f"{name} 읽기 실패: {err}")
            continue
        read_files.append(name)
        for k, v in kv.items():
            if _SECRET_NAME.search(k) and len(v) >= _MIN_VALUE_LEN:
                merged.setdefault((k, v), set()).add(name)
    rows = [(k, v, "+".join(sorted(files))) for (k, v), files in merged.items()]
    return rows, read_files, problems


def _needles_for(value: str) -> list[tuple[bytes, str]]:
    """이 값을 찾을 바이트 패턴들 — 평문 · JSON 이스케이프, 각각 UTF-8 · UTF-16-LE."""
    variants = [(value, "")]
    esc = json.dumps(value)[1:-1]
    if esc != value:
        variants.append((esc, "JSON 이스케이프 "))
    out: list[tuple[bytes, str]] = []
    seen: set[bytes] = set()
    for text, tag in variants:
        for enc in ("utf-8", "utf-16-le"):
            b = text.encode(enc)
            if not b or b in seen:
                continue
            seen.add(b)
            out.append((b, f"{tag}{enc}"))
    return out


def _find_all(content: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        idx = content.find(needle, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + len(needle)
    return offsets


def _line_no(content: bytes, offset: int, enc_tag: str) -> int:
    nl = b"\n\x00" if enc_tag.endswith("utf-16-le") else b"\n"
    return content[:offset].count(nl) + 1


def scan_bytes(content: bytes, secrets_rows: list[tuple[str, str, str]], label: str) -> list[str]:
    """`content` 안에서 대상 값을 찾는다.

    ★ 찾은 **줄은 절대 찍지 않는다** — 이름·자리·건수만 돌려준다. 이 함수의 반환값에
      값 자체가 들어가는 일이 없어야 한다(자기시험이 이것도 확인한다).
    """
    hits: list[str] = []
    for key, value, src in secrets_rows:
        count = 0
        first_line: int | None = None
        for needle, enc_tag in _needles_for(value):
            offsets = _find_all(content, needle)
            if offsets and first_line is None:
                first_line = _line_no(content, offsets[0], enc_tag)
            count += len(offsets)
        if count:
            where = f":{first_line}" if first_line else ""
            hits.append(f"{key}({src}) 가 {label}{where} 에 {count}건")
    return hits


def _is_skippable(path: Path, size: int) -> bool:
    return path.suffix.lower() in _BINARY_EXTS or size > _MAX_FILE_BYTES or size == 0


def scan_dir(base: Path, secrets_rows: list[tuple[str, str, str]]) -> tuple[list[str], int]:
    """`base` 아래 전부(`rglob`) — evidence 도 그 안에 있으므로 따로 훑지 않는다."""
    hits: list[str] = []
    skipped = 0
    if not base.is_dir():
        return hits, skipped
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        try:
            size = path.stat().st_size
        except OSError:
            skipped += 1
            continue
        if _is_skippable(path, size):
            skipped += 1
            continue
        try:
            content = path.read_bytes()
        except OSError:
            skipped += 1
            continue
        if b"\x00" in content[:8192]:               # 확장자로 못 거른 이진 파일
            skipped += 1
            continue
        hits += scan_bytes(content, secrets_rows, path.relative_to(ROOT).as_posix())
    return hits, skipped


def scan_run(command: str, secrets_rows: list[tuple[str, str, str]]) -> tuple[list[str], int]:
    """`--run` 이 받은 명령을 한 번 돌려 stdout/stderr 를 대조한다. 종료 코드는
    **이 게이트의 판정이 아니다** — 명령이 실패해도 그 출력에 값이 없으면 통과다.
    """
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"{TAG} --run 명령을 못 돌렸다: {type(exc).__name__} — 그 갈래는 못 쟀다")
        return [], -1
    hits = scan_bytes(proc.stdout, secrets_rows, "--run stdout")
    hits += scan_bytes(proc.stderr, secrets_rows, "--run stderr")
    print(f"{TAG} --run 종료 코드 {proc.returncode}")
    return hits, proc.returncode


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — 심어 보고 잡는가 (D-289). **값은 여기서도 찍지 않는다.**
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    bad: list[str] = []

    # ── 이름 걸러내기 규칙 자체 (제외 규칙 · 위 docstring 예시 그대로) ────────
    for non_secret_key in ("GX_API", "GX_ROUTE_USER", "GX_ROUTE_USER_ROLE0",
                           "GX_ROUTE_CONTAINER", "GX_PROBE_USER",
                           "MINIO_ENDPOINT", "MINIO_BUCKET_NAME"):
        if _SECRET_NAME.search(non_secret_key):
            bad.append(f"{non_secret_key} 가 대상 이름 패턴에 걸린다 — "
                       "URL·사용자명·컨테이너·호스트·버킷 이름까지 대상이 된다")
    for secret_key in ("GX_ROUTE_PASSWORD", "GX_ROUTE_PASSWORD_ROLE0",
                       "GX_SEED_ROLE_PASSWORD", "GX_PROBE_PASSWORD",
                       "MINIO_ROOT_PASSWORD", "SOME_API_KEY", "AUTH_TOKEN",
                       "DB_PW", "SIGNING_CREDENTIAL"):
        if not _SECRET_NAME.search(secret_key):
            bad.append(f"{secret_key} 가 대상 이름 패턴을 놓친다 — 진짜 비밀이 안 잡힌다")
    if len("ab1234") >= _MIN_VALUE_LEN:  # 6자 — 상수가 뒤집히지 않았는지
        bad.append("최소 길이 상수가 뒤집혔다")

    box = Path(tempfile.mkdtemp(prefix="gxnoecho.st."))
    try:
        alphabet = _string.ascii_letters + _string.digits
        #: 따옴표·역슬래시를 끝에 붙인다 — JSON 이스케이프 갈래가 **의미 있게** 다른
        #:   바이트열을 대조하도록(그렇지 않으면 이스케이프해도 값이 그대로라 갈래가
        #:   실은 아무것도 더 시험하지 않는다).
        planted = "".join(_secrets.choice(alphabet) for _ in range(28)) + '"\\tail'
        rows = [("GX_TEST_TOKEN", planted, ".env.selftest")]

        # ── 양성 ① 평문 UTF-8 ───────────────────────────────────────────
        plain = box / "evidence_like.md"
        plain.write_text("증거 문서 본문\n값: " + planted + "\n끝\n", encoding="utf-8")
        hits1 = scan_bytes(plain.read_bytes(), rows, "docs/agent/evidence_like.md")
        if not hits1:
            bad.append("자기시험 양성 실패 — 평문으로 심은 값 1건을 못 잡았다. "
                       "이 게이트는 눈이 멀었다")
        for h in hits1:
            if planted in h:
                bad.append("자기시험 — 판정 메시지에 값 자체가 그대로 남는다 (절대 금지)")

        # ── 양성 ② JSON 이스케이프 ──────────────────────────────────────
        esc_leaked = box / "evidence_like.json"
        esc_leaked.write_text(json.dumps({"note": "본문", "v": planted}, ensure_ascii=False),
                              encoding="utf-8")
        hits2 = scan_bytes(esc_leaked.read_bytes(), rows, "docs/agent/evidence_like.json")
        if not hits2:
            bad.append("자기시험 양성 실패 — JSON 이스케이프 형태로 심은 값을 못 잡는다")

        # ── 양성 ③ UTF-16-LE ────────────────────────────────────────────
        u16_leaked = box / "evidence_like.log"
        u16_leaked.write_bytes(("값: " + planted + "\n").encode("utf-16-le"))
        hits3 = scan_bytes(u16_leaked.read_bytes(), rows, "docs/agent/evidence_like.log")
        if not hits3:
            bad.append("자기시험 양성 실패 — UTF-16-LE 로 적힌 값을 못 잡는다")

        # ── 음성 — 비밀이 없는 문서에서 오탐하지 않는다 ─────────────────
        clean = box / "clean.md"
        clean.write_text(
            "API=http://localhost:8000\n사용자=gxprobe_e2e\n컨테이너=gx-shell\n"
            "버킷=guardianx-media\n짧은값=ab12\n임의 문장 여러 줄\n" * 3,
            encoding="utf-8")
        no_hits = scan_bytes(clean.read_bytes(), rows, "docs/agent/clean.md")
        if no_hits:
            bad.append("자기시험 음성 실패 — 비밀이 없는 파일에서 " + str(len(no_hits))
                       + "건을 잡는다. 오탐 내는 게이트는 꺼진다")

        # ── 양성 ④ --run 갈래 — 명령 stdout 에 심은 값이 나오면 잡는가 ────
        runner = box / "planted_print.py"
        runner.write_text("print(" + repr(planted) + ")\n", encoding="utf-8")
        run_cmd = f'"{sys.executable}" "{runner}"'
        run_hits, _rc = scan_run(run_cmd, rows)
        if not run_hits:
            bad.append("자기시험 --run 양성 실패 — 명령 stdout 에 심은 값이 나왔는데 못 잡았다")

        # ── 양성 ⑤ ★ 출생 표본 — 이 게이트를 태어나게 한 바로 그 사례 (P-135) ───
        #   [실측 2026-09-15 · 턴 P] 로그인 진단 중 게이트 계정 비밀번호(`GX_ROUTE_PASSWORD_ROLE0`)
        #   가 **stderr 의 진단 한 줄**에 찍혔고, 그 도구 출력이 세션 기록 5개에 남았다.
        #   그 모양 그대로다: 값이 stdout 이 아니라 stderr 로, 로그 접두 뒤 `key=값` 꼴로 나온다.
        birth = box / "birth_sample_p135.py"
        birth.write_text(
            "import sys\n"
            "print('[ALIVE] 로그인 /api/v1/auth/login → HTTP 400')\n"
            "print('[ALIVE] 진단: user=gxprobe_e2e password=' + " + repr(planted)
            + ", file=sys.stderr)\n",
            encoding="utf-8")
        birth_hits, _rc = scan_run(f'"{sys.executable}" "{birth}"', rows)
        if not any("stderr" in h for h in birth_hits):
            bad.append("자기시험 출생 표본 실패 — P-135 의 그 모양(진단 stderr 한 줄의 password=값)"
                       "을 못 잡았다. 이 게이트는 태어난 이유를 못 본다")

        # ── 이름 필터가 실제로 대상을 줄이는지 — collect_secrets 자체 ────
        env_box = Path(tempfile.mkdtemp(prefix="gxnoecho.env."))
        try:
            (env_box / ".env").write_text(
                "MINIO_ROOT_USER=probe_user\nMINIO_ROOT_PASSWORD=" + planted + "\n",
                encoding="utf-8")
            (env_box / ".env.gates").write_text(
                "GX_API=http://localhost:8000\nGX_ROUTE_USER=probe\n"
                "GX_ROUTE_PASSWORD=" + planted + "\n",
                encoding="utf-8")
            c_rows, c_read, c_problems = collect_secrets(env_box)
            if set(c_read) != {".env", ".env.gates"}:
                bad.append("collect_secrets 가 두 env 파일을 다 읽지 못했다: "
                           + ",".join(c_read))
            if c_problems:
                bad.append("collect_secrets 가 존재하는 파일에도 문제를 낸다: "
                           + ",".join(c_problems))
            c_keys = {k for k, _v, _s in c_rows}
            if "GX_API" in c_keys or "GX_ROUTE_USER" in c_keys or "MINIO_ROOT_USER" in c_keys:
                bad.append("collect_secrets 가 URL·사용자명 이름까지 대상으로 건진다")
            if "MINIO_ROOT_PASSWORD" not in c_keys or "GX_ROUTE_PASSWORD" not in c_keys:
                bad.append("collect_secrets 가 진짜 비밀 이름을 놓친다")

            # 판정 불가 갈래 — env 파일이 하나도 없으면 read_files 가 비어야 한다
            empty_box = Path(tempfile.mkdtemp(prefix="gxnoecho.empty."))
            try:
                _rows2, read2, problems2 = collect_secrets(empty_box)
                if read2 or not problems2:
                    bad.append("collect_secrets 가 env 파일이 없는데도 읽었다고 한다 "
                               "— 판정 불가(회색)가 초록으로 새어 나간다")
            finally:
                shutil.rmtree(empty_box, ignore_errors=True)
        finally:
            shutil.rmtree(env_box, ignore_errors=True)
    finally:
        shutil.rmtree(box, ignore_errors=True)

    if bad:
        print(f"{TAG} 자기시험 실패 — 이 게이트는 눈이 멀었다:")
        for b in bad:
            print(f"{TAG}     {b}")
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 이름 필터(양성9·음성7) · 값 탐지 양성 5"
          "(평문·JSON 이스케이프·UTF-16-LE·--run · ★출생 표본 P-135 진단 stderr) · "
          "음성 1(비밀 없는 문서) · collect_secrets 대상 가르기·판정 불가 갈래")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(
        description="게이트·문서가 값을 출력하지 않는지 잰다 (P-135 ④)")
    ap.add_argument("--run", metavar="<명령>",
                    help="이 명령의 stdout/stderr 도 대조한다 (셸로 한 번 돌린다)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    st = self_test()
    if st != EXIT_OK:
        return st
    if args.self_test:
        return EXIT_OK

    rows, read_files, problems = collect_secrets()
    for p in problems:
        print(f"{TAG} {p}")
    if not read_files:
        print(f"{TAG} .env·.env.gates 를 하나도 못 읽었다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    print(f"{TAG} [입력] 대상 값 {len(rows)}건 — {'·'.join(read_files)} 에서 "
          f"키 이름에 PASSWORD|SECRET|KEY|TOKEN|PASS|PW|CREDENTIAL 이 들고 "
          f"길이 ≥ {_MIN_VALUE_LEN} 인 것 (값은 적지 않는다)")

    all_hits: list[str] = []
    total_skipped = 0
    for base_name in SCAN_ROOTS:
        base = ROOT / base_name
        hits, skipped = scan_dir(base, rows)
        total_skipped += skipped
        exists = "있음" if base.is_dir() else "없음(회색 아님 — 훑을 것이 없다)"
        print(f"{TAG} {base_name}/** 훑음({exists}) — 건너뜀 {skipped}건(이진·대용량)")
        all_hits += hits

    if args.run:
        hits, _rc = scan_run(args.run, rows)
        all_hits += hits

    if all_hits:
        print(f"{TAG} 빨강 — 값이 나타난 자리 {len(all_hits)}건 (값 없음):")
        for h in all_hits:
            print(f"{TAG}   · {h}")
        return EXIT_FAIL
    print(f"{TAG} 통과 — 대상 {len(rows)}건 · 건너뜀 {total_skipped}건 · "
          f"새어 나온 자리 0건")
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target=".env·.env.gates(저장소 밖 값) → docs/agent/**·docs/review/**"
               " + --run 출력",
        as_="자격증명 없음 — 로컬 env 파일과 문서를 읽는다",
        source="로컬 파일 시스템 (지금 읽음 — 사진이 아니다)",
    )
    sys.exit(main())
