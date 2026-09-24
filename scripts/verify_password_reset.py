#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-325 · P-326 — 비밀번호 찾기 「보냈습니다」 길목 + `frontendUrl` 배선 판정기 (턴 S · 2026-09-24).

무엇을 재는가 — 둘
--------------------
    ① **길목** — `backend/tests/test_p325_reset_mail_gate.py` 3건을 gx-shell 안에서
       그대로 돌린다. 판정 규칙은 그 시험이 이미 정했다(있는 주소·없는 주소가 SMTP
       죽음일 때 바이트까지 같은 본문 · SMTP 살면 dj-core 로 그대로 넘어간다). 이
       판정기는 **다시 구현하지 않는다** — 같은 코드로 두 번 재면 언젠가 갈린다(D-212).
    ② **링크 host == frontendUrl 칸** — SMTP 가 살아 있다고 놓은 상태에서(P-325 길목을
       일부러 통과시킨다) dj-core 가 실제로 만드는 재설정 링크의 host 를
       `AdminConfig('System').settings['frontendUrl']` 과 글자 그대로 견준다.

       ★ 이 둘은 **다른 겹**을 잰다 — 헷갈리면 안 된다. ①은 우리 겹(`common/
         reset_mail_gate.py`)이 SMTP 죽음을 가리는가. ②는 dj-core(§0.4·안 고침)가
         살아 있을 때 **어느 주소로** 링크를 만드는가. SMTP 가 죽어 있으면 링크
         자체가 안 만들어지므로(①이 막는다), ②는 SMTP 를 **살아 있다고 놓고** 재야
         한다 — 안 그러면 이 컨테이너의 더미값(`SMTP_SERVER=smtp.invalid`) 때문에
         ②가 매번 "링크가 없다"로 못 재게 된다.

이 게이트를 만든 사고 [실측 2026-09-24 · 턴 S]
------------------------------------------------
`AdminConfig('System').settings` 에 `frontendUrl` 칸이 **없어서** dj-core 의 기본값
`http://localhost:3001`(아무도 안 듣는 포트)이 매 링크에 실렸다. P-326 이 개발 DB
한 칸에 `http://localhost:8500` 을 넣었지만, **칸을 채우는 것과 링크가 그 칸을 따라
움직이는 것은 다른 사실**이다 — 코드가 다른 자리에서 값을 읽거나, 캐시가 옛 값을
들고 있으면 칸은 바뀌어도 고객이 받는 링크는 안 바뀐다. 그래서 ②는 **DB 를 읽는
것으로 끝내지 않고**, 실제로 발송 경로를 한 번 통과시켜 **오늘 만들어진 링크**의
host 를 견준다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_password_reset.py                 # 판정 (호스트 — docker 를 부른다)
    python scripts/verify_password_reset.py --self-test      # 판정 규칙만 · 그날의 실패 표본 포함
    python scripts/verify_password_reset.py --shell gx-shell # 컨테이너 이름을 바꿔 잰다

호스트에서 돈다 — docker exec 로 gx-shell 안(= 호스트 backend/)에 위임한다
(`guardianx-host-cannot-see-gate-servers` — 서버를 때리는 것은 gx-shell 안이다).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
TESTS = BACKEND / "tests" / "test_p325_reset_mail_gate.py"
SHELL_CONTAINER = "gx-shell"
TAG = "[PW-RESET]"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: dj-core 가 링크에 붙이는 고정 꼬리 (`core/api/v1/auth.py::forgot_password`
#: — `f"{frontend_url}/reset-password?token={token}"`). MARK **앞부분**이 host 다.
MARK = "/reset-password?token="

#: 링크 안의 `frontend_url` 자리에 **일부러 만든 주소를 심어** 되읽는 자리표.
#: 실제 host 값(비밀 아님)이 아니라 **탐침용 상수**라 그대로 남겨 둔다.
PROBE_EMAIL = "gxprobe_p326_link_host@test.invalid"
PROBE_USERNAME = "gxprobe_p326_link_host"
PROBE_PASSWORD = "GxProbe-P326-2026!aa"  # nosec — 시험 계정. 실 자격 아님(D-204 무관)

#: gx-shell 안에서 도는 탐침. **표준입력으로** 넘긴다(`verify_live_code.py` 와 같은
#: 관례 — 따옴표·특수문자가 셸을 안 탄다). 이 문자열에는 백슬래시가 **0개**다
#: (guardianx-bash-tool-strips-backslashes 함정을 피하려는 것이 아니라, 이 파일은
#: Write 도구로 썼으므로 애초에 그 함정이 없다 — 그래도 습관은 지킨다).
_LINK_PROBE = """
import json
import django
django.setup()
from unittest import mock
from django.apps import apps
from django.test import Client


class _Recorder:
    sent = []

    def __init__(self, *a, **k):
        pass

    def send_notification(self, email_data):
        _Recorder.sent.append(email_data)
        return True


AdminConfig = apps.get_model('configuration', 'AdminConfig')
row = AdminConfig.objects.filter(name='System').first()
frontend_url = (row.settings or {}).get('frontendUrl') if row else None

CoreUser = apps.get_model('user', 'CoreUser')
user = CoreUser.objects.filter(email='__PROBE_EMAIL__').first()
if user is None:
    user = CoreUser.objects.create_user(
        username='__PROBE_USERNAME__', password='__PROBE_PASSWORD__',
        is_active=True, email='__PROBE_EMAIL__')

with mock.patch('common.reset_mail_gate.smtp_reachable', return_value=True), \\
     mock.patch('core.api.v1.auth.SMTPEmailBackend', _Recorder):
    client = Client(REMOTE_ADDR='127.0.0.9')
    resp = client.post('/api/v1/auth/forgot-password',
                       data=json.dumps({'email': '__PROBE_EMAIL__'}),
                       content_type='application/json')

body = _Recorder.sent[0].get('body', '') if _Recorder.sent else ''
print(json.dumps({
    'frontend_url': frontend_url,
    'status': resp.status_code,
    'body': body,
}))
"""
#: ★ 위 문자열의 `\\` 하나(계속줄)는 **Write 도구가 쓴 그대로** 파일에 남는다 —
#:   파이썬 삼중따옴표 문자열 리터럴 안의 줄바꿈 이음줄이다. `python -` 로 그대로
#:   먹인다(별도 이스케이프 불필요 — subprocess 가 문자열을 그대로 stdin 에 준다).


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수** (자기시험이 docker 없이 이것을 잰다)
# ═══════════════════════════════════════════════════════════════════════════
def parse_pytest_summary(output: str) -> tuple[int, int, int] | None:
    """(passed, failed, errors). 못 읽으면 `None`.

    pytest `-q` 의 마지막 요약 줄(`3 passed in 0.52s` · `2 passed, 1 failed in 0.3s`)
    을 읽는다. 정규식 — 이 파일은 Write 도구로 썼으므로 백슬래시 함정이 없다.
    """
    m = re.search(
        r"(?:(\d+) passed)?(?:, )?(?:(\d+) failed)?(?:, )?(?:(\d+) error)?[^\n]*"
        r"in [\d.]+s", output)
    tail = None
    for line in reversed(output.splitlines()):
        if " in " in line and ("passed" in line or "failed" in line or "error" in line):
            tail = line
            break
    if tail is None:
        return None
    passed = int(m.group(1)) if m and m.group(1) else (
        int(re.search(r"(\d+) passed", tail).group(1)) if "passed" in tail else 0)
    failed = int(re.search(r"(\d+) failed", tail).group(1)) if "failed" in tail else 0
    errors = int(re.search(r"(\d+) error", tail).group(1)) if "error" in tail else 0
    return passed, failed, errors


def judge_gate_tests(summary: tuple[int, int, int] | None) -> tuple[int, str]:
    """① 길목 시험 3/3. `None` 이면 못 쟀다(회색) — 0건도 「돌았지만 다 죽었다」와 다르다."""
    if summary is None:
        return EXIT_UNDECIDABLE, "길목 시험 출력에서 요약 줄을 못 읽었다 — 못 쟀다"
    passed, failed, errors = summary
    if failed or errors:
        return (EXIT_FAIL,
                "길목 시험 %d실패 · %d에러 (통과 %d) — 「보냈습니다」가 다시 새고 있을 "
                "수 있다" % (failed, errors, passed))
    if passed == 0:
        return EXIT_UNDECIDABLE, "길목 시험이 0건 통과·0건 실패 — 수집조차 안 됐다(못 쟀다)"
    return EXIT_OK, "길목 시험 %d건 전부 통과" % passed


def host_of(link_body: str) -> str | None:
    """메일 본문에서 링크의 host(= MARK 앞부분). 없으면 `None`."""
    at = link_body.find(MARK)
    if at == -1:
        return None
    # host 는 그 앞의 마지막 공백/따옴표/꺾쇠부터 MARK 까지.
    start = 0
    for i in range(at - 1, -1, -1):
        ch = link_body[i]
        if ch in (" ", chr(34), chr(39), "<", ">", chr(10), chr(13), chr(9)):
            start = i + 1
            break
    return link_body[start:at]


def judge_link_host(frontend_cell: str | None, link_body: str) -> tuple[int, str]:
    """② 링크 host == frontendUrl 칸.

    ★ 칸이 비어 있는데 링크가 만들어졌다면 그것은 **오늘의 실제 사고**(기본값
      `http://localhost:3001` 이 몰래 쓰인 것)와 같은 모양이라 FAIL 이다 — 「칸이
      없다」는 「어디로도 안 보낸다」가 아니라 「dj-core 의 숨은 기본값으로 샌다」였다.
    """
    host = host_of(link_body)
    if host is None:
        return EXIT_UNDECIDABLE, "링크를 못 만들었다(메일 본문에 %r 없음) — 못 쟀다" % MARK
    if not frontend_cell:
        return (EXIT_FAIL,
                "frontendUrl 칸이 비어 있는데 링크는 %r 로 만들어졌다 — dj-core 의 숨은 "
                "기본값이 몰래 쓰이고 있다(오늘의 실제 사고와 같은 모양)" % host)
    if host != frontend_cell:
        return (EXIT_FAIL,
                "링크 host(%r)가 frontendUrl 칸(%r)과 다르다 — 칸을 채워도 고객이 받는 "
                "링크는 안 바뀐다는 뜻이다" % (host, frontend_cell))
    return EXIT_OK, "링크 host 가 frontendUrl 칸과 같다 (%r)" % host


def combine(codes: list[int]) -> int:
    if EXIT_FAIL in codes:
        return EXIT_FAIL
    if EXIT_UNDECIDABLE in codes:
        return EXIT_UNDECIDABLE
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 재기 — gx-shell 안에 위임
# ═══════════════════════════════════════════════════════════════════════════
def run_gate_tests(shell: str) -> str | None:
    try:
        r = subprocess.run(
            ["docker", "exec",
             "-e", "DJANGO_SETTINGS_MODULE=config.settings",
             "-e", "DB_TEST_NAME=test_gx_verify_password_reset",
             "-w", "/app", shell,
             "python", "-m", "pytest", "tests/test_p325_reset_mail_gate.py",
             "-q", "--create-db", "-p", "no:randomly"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            #: ★ [실측 2026-09-24] 차선이 여럿 겹치면(공유 gx-shell) 3건짜리 시험도
            #:   190~380초 걸렸다 — 180초는 짧아 매번 GRAY(못 쟀다)를 냈다. 여유를
            #:   10분으로 둔다(`guardianx-lane-count-ceilings` — 동시 차선이 이 컨테이너를 나눠 쓴다).
            timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("%s [입력] docker exec pytest 를 못 불렀다 — %s" % (TAG, exc))
        return None
    return (r.stdout or "") + (r.stderr or "")


def probe_link_host(shell: str) -> dict | None:
    script = (_LINK_PROBE
              .replace("__PROBE_EMAIL__", PROBE_EMAIL)
              .replace("__PROBE_USERNAME__", PROBE_USERNAME)
              .replace("__PROBE_PASSWORD__", PROBE_PASSWORD))
    try:
        r = subprocess.run(
            ["docker", "exec", "-i",
             "-e", "DJANGO_SETTINGS_MODULE=config.settings",
             "-w", "/app", shell, "python", "-"],
            input=script, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("%s [입력] docker exec 링크 탐침을 못 불렀다 — %s" % (TAG, exc))
        return None
    for line in reversed((r.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    print("%s [입력] 링크 탐침 출력에서 JSON 줄을 못 찾았다:\n%s"
          % (TAG, ((r.stdout or "") + (r.stderr or ""))[-2000:]))
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310) — **그날의 실제 모양이 출생 표본이다**
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    fails = 0

    def check(label: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))

    # ── ① 길목 시험 요약 파싱 ────────────────────────────────────────────
    p, f, e = parse_pytest_summary("....                                    [100%]\n"
                                   "3 passed in 0.41s\n")
    check("pytest 요약 — 3 passed 를 읽는다", (p, f, e) == (3, 0, 0))
    p, f, e = parse_pytest_summary("F.F                                     [100%]\n"
                                   "1 passed, 2 failed in 0.55s\n")
    check("pytest 요약 — 실패 섞인 줄도 읽는다", (p, f, e) == (1, 2, 0))
    check("요약 줄이 없으면 None(못 쟀다)", parse_pytest_summary("collected 0 items\n") is None)

    code, _ = judge_gate_tests((3, 0, 0))
    check("① 3/3 통과 → 초록", code == EXIT_OK)
    code, _ = judge_gate_tests((2, 1, 0))
    check("★ ① 1건 실패 → 빨강", code == EXIT_FAIL)
    code, _ = judge_gate_tests(None)
    check("① 요약을 못 읽으면 → 회색(못 쟀다)", code == EXIT_UNDECIDABLE)
    code, _ = judge_gate_tests((0, 0, 0))
    check("① 0통과·0실패(수집 실패)도 → 회색", code == EXIT_UNDECIDABLE)

    # ── ② host 추출 ──────────────────────────────────────────────────────
    check("host_of — 따옴표 앞에서 끊는다",
         host_of('"body": "http://gx.example:8500/reset-password?token=abc"')
         == "http://gx.example:8500")
    check("host_of — 링크가 없으면 None", host_of("no link here") is None)

    # ── ★★ 출생 표본 — **오늘 실제로 있었던 사고 모양** [실측 2026-09-24] ──
    #    칸이 비어 있었고(`frontendUrl` 없음), dj-core 의 숨은 기본값
    #    `http://localhost:3001` 이 몰래 실렸다. 이것을 초록으로 읽으면 이 게이트는
    #    없느니만 못하다 — **반드시 빨강이어야 한다.**
    code, msg = judge_link_host(
        frontend_cell=None,
        link_body="...링크: http://localhost:3001/reset-password?token=deadbeef ...")
    check("★★ 출생표본 — 칸 없음 + 숨은 기본값 링크 → 빨강 (오늘의 실제 사고)",
         code == EXIT_FAIL)

    # ── 음성 대조 — P-326 적용 뒤(칸과 링크가 같다) → 초록 ─────────────────
    code, msg = judge_link_host(
        frontend_cell="http://localhost:8500",
        link_body="...링크: http://localhost:8500/reset-password?token=cafebabe ...")
    check("음성 대조 — 칸과 링크가 같으면 초록", code == EXIT_OK)

    # ── 드리프트 — 칸은 채웠는데 링크가 다른 주소로 나간다 → 빨강 ──────────
    code, msg = judge_link_host(
        frontend_cell="http://localhost:8500",
        link_body="...링크: http://stale-cache.invalid/reset-password?token=x ...")
    check("★ 드리프트 — 칸과 링크가 다르면 빨강(캐시가 옛 값을 든 모양)", code == EXIT_FAIL)

    # ── 링크 자체가 안 만들어졌다 → 회색(못 쟀다) ──────────────────────────
    code, msg = judge_link_host(frontend_cell="http://localhost:8500", link_body="")
    check("링크가 아예 없으면 → 회색(못 쟀다, 빨강 아님)", code == EXIT_UNDECIDABLE)

    # ── combine ─────────────────────────────────────────────────────────
    check("combine — 하나라도 빨강이면 빨강", combine([EXIT_OK, EXIT_FAIL]) == EXIT_FAIL)
    check("combine — 빨강 없고 회색 있으면 회색",
         combine([EXIT_OK, EXIT_UNDECIDABLE]) == EXIT_UNDECIDABLE)
    check("combine — 전부 초록이면 초록", combine([EXIT_OK, EXIT_OK]) == EXIT_OK)

    print("%s 자기시험 %d건 실패" % (TAG, fails))
    return EXIT_FAIL if fails else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="P-325 · P-326 비밀번호 찾기 길목 + frontendUrl 배선")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--shell", default=SHELL_CONTAINER)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not TESTS.exists():
        print("%s **판정 불가 · 회색** — 길목 시험 파일이 없다: %s"
              % (TAG, TESTS.relative_to(ROOT).as_posix()))
        return EXIT_UNDECIDABLE

    # ① 길목 시험
    raw = run_gate_tests(args.shell)
    summary = parse_pytest_summary(raw) if raw is not None else None
    code1, verdict1 = judge_gate_tests(summary)
    print("%s [입력] 길목 시험 = tests/test_p325_reset_mail_gate.py (gx-shell=%s)"
          % (TAG, args.shell))
    if summary is not None:
        print("%s [입력] pytest 요약 — 통과 %d · 실패 %d · 에러 %d"
              % (TAG, summary[0], summary[1], summary[2]))
    print("%s %s ① %s" % (TAG, "OK  " if code1 == EXIT_OK else
                          ("FAIL" if code1 == EXIT_FAIL else "GRAY"), verdict1))
    if code1 != EXIT_OK and raw:
        print("%s ── 길목 시험 원문 꼬리 ──\n%s" % (TAG, raw[-2000:]))

    # ② 링크 host == frontendUrl 칸
    probe = probe_link_host(args.shell)
    if probe is None:
        code2, verdict2 = EXIT_UNDECIDABLE, "링크 탐침을 못 돌렸다 — 못 쟀다"
    else:
        print("%s [입력] AdminConfig('System').settings['frontendUrl'] = %r · "
              "탐침 응답 상태 %s" % (TAG, probe.get("frontend_url"), probe.get("status")))
        code2, verdict2 = judge_link_host(probe.get("frontend_url"), probe.get("body") or "")
    print("%s %s ② %s" % (TAG, "OK  " if code2 == EXIT_OK else
                          ("FAIL" if code2 == EXIT_FAIL else "GRAY"), verdict2))

    final = combine([code1, code2])
    if final == EXIT_OK:
        print("%s PASS 길목 3/3 · 링크 host == frontendUrl 칸" % TAG)
    return final


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="gx-shell(%s) 안 backend/ · dj-core forgot_password(§0.4·읽기만) · "
               "AdminConfig('System') 행" % SHELL_CONTAINER,
        as_="탐침 계정 %s(고정 시험 계정 · 새 권한 없음) — pytest 는 자격증명 없이 "
            "--create-db 로 돈다" % PROBE_USERNAME,
        source="살아 있는 gx-shell 컨테이너(docker exec) · 개발 DB 의 AdminConfig 행 — "
               "사진·기록이 아니라 지금 이 순간",
        measured="① 길목 시험 3/3(있는 주소·없는 주소·SMTP 죽음이 바이트까지 같은 답) · "
                 "② 오늘 만든 링크의 host 가 frontendUrl 칸과 같은가 · 분모 2(판정 둘)",
    )
    raise SystemExit(main())
