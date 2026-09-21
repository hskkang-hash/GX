#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-200 — **카메라 자격이 로그에 적히는가** (2026-09-20 · 턴 X · 차선 U3).

    막은 것을 지키는 판정기가 없으면, 막은 것은 **다음 한 줄에 되돌아온다.**

무엇이 이 파일을 만들게 했나 — 턴 W 에 막았고, 턴 X 에 **그대로 살아 있었다**
-------------------------------------------------------------------------
턴 W(P-192)에 `capture_service.py` 가 `print("rtsp_url: ", rtsp_url)` 과
`logger.info(f"… RTSP: {rtsp_url}")` 로 카메라 주소를 **통째로** 찍던 것을 `_redact`
로 막았다. 그런데 **판정기를 안 세웠다.** 그래서 턴 X 에 열어 보니 옆 파일에서
같은 줄이 멀쩡히 살아 있었다 [실측 2026-09-20]:

    stream_monitor_services.py:649  rtsp_url = stream_monitor.ip_source
    stream_monitor_services.py:651  logger.info(f"🔍 [START_RECORD] RTSP URL: {rtsp_url}")
    stream_monitor_services.py:686  logger.info(f"… Request body: {json.dumps(body_data, …)}")
                                     └ body_data['rtsp_url'] 이 그 주소다 (**한 겹 건너 샌다**)

한 파일을 고치는 것으로는 이 결함이 안 닫힌다. 고쳐야 하는 것은 **줄**이 아니라
「자격이 든 주소가 로그로 가는 길」이고, 그 길은 사람이 새 줄을 쓸 때마다 다시 생긴다.

왜 자격이 거기 있나 — `StreamMonitor.ip_source` 는 **운영자가 손으로 적는 칸**이다
-----------------------------------------------------------------------------
외부 카메라(`is_external`)의 주소는 운영자가 넣고, 그 꼴은 흔히
`rtsp://아이디:비밀번호@호스트:554/…` 다. 즉 **카메라 비밀번호가 모델 필드에 들어
있다.** 그 필드가 f-string 을 타고 로그로 나가면 접근 로그에 비밀번호가 남는다.
로그 줄은 지우지 않는 것이 규약이므로(D-004 회전) **애초에 안 적는 것**밖에 없다.

술어 둘 — **로그는 회전으로 사라지고, 코드는 남는다. 그래서 둘 다 본다.**
------------------------------------------------------------------------
  ① **살아 있는 로그** (`docker logs`)  지금 돌고 있는 컨테이너의 stdout 을 실제로
     훑어 `rtsp://<무엇>:<무엇>@` 꼴이 **몇 줄인가**를 센다. 0 이라야 초록.
     · 이 판의 로그는 전부 stdout 이다 — `settings.LOGGING` 의 root 핸들러가
       `console`(StreamHandler) 하나뿐이고 파일 핸들러가 없다 [실측 settings.py:742].
       그래서 「살아 있는 로그」는 곧 `docker logs` 다. 앞단(nginx)도 같이 본다 —
       주소가 질의로 오면 접근 로그에 찍히기 때문이다.
     · 자른 기준은 **줄이 아니라 시각**이다(`--since`). 회전하는 로그에서 「마지막
       N줄」은 매번 다른 것을 가리킨다.
  ② **정적 검사** (파이썬 AST)  `ip_source` 에서 흘러나온 값이 `logger.*`/`print`
     의 인자에 **씻기지 않고** 닿는 줄을 찾는다.
     · 이름으로 안 센다 — `rtsp_url` 이라는 **이름**은 죄가 없다. 같은 이름이
       `settings.RTSP_URL`(내부 미디어 서버 · 자격 없음)일 때가 더 많다.
       씨앗은 **`.ip_source` 하나**이고, 거기서 대입을 따라 물든 이름만 위험하다.
       그래서 `backend/delivery/` 의 `print("stream_urls: ", stream_urls)` 는
       **안 걸린다** — 그 값은 `ip_source` 에서 오지 않는다 [실측].
     · **한 겹 건너가는 것도 본다**: `body = {'rtsp_url': rtsp_url}` 뒤의
       `logger.info(f"{json.dumps(body)}")` 가 실제 결함이었다.
     · 씻김의 정의: `_redact(...)` 같은 **씻는 함수의 호출 안에 든 것**은 통과.
       씻는 함수 이름은 `SANITIZERS` 에 적혀 있고, 그 목록은 이 파일에만 있다.

무엇을 재지 **않는가** — 재지 않는 것을 적어야 다음 사람이 이 초록을 안 넓혀 읽는다
--------------------------------------------------------------------------------
· **API 응답**에 주소가 실리는 것 — `schemas_djantic_out.py` 는 카메라 상세에
  `ip_source` 를 그대로 내준다. 그것은 운영자가 제 카메라를 보는 화면이고, 로그와는
  다른 질문이다. 이 게이트는 **로그만** 본다.
· **DB 감사로그** — `db` 로거는 미들웨어 전용이고 root 는 `console` 뿐이다
  (`DB_LOG_ROOT_ENABLED=False` 가 기본). 그 스위치를 켜면 이 게이트의 ①이 보는
  면이 좁아진다 — 켜는 사람이 여기 한 줄을 더해야 한다.
· **주소가 옳은지 · 카메라가 닿는지** — 그것은 P-192 의 일이다.
· 로그에 `rtsp` 언급이 **한 줄도 없으면** 이 게이트의 ①은 「0건 잡았다」가 아니라
  「그 길이 안 돌았다」이다. 그래서 훑은 줄 수와 **언급 줄 수를 따로 찍는다.**

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 못 쟀다
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = "[P-200]"

EXIT_OK, EXIT_RED, EXIT_GREY = 0, 1, 2

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# ─────────────────────────────────────────────────────────────────────────────
# ① 살아 있는 로그
# ─────────────────────────────────────────────────────────────────────────────

#: 자격이 **실제로 든** rtsp 주소. 사용자정보 칸에 `:` 가 있고 `@` 로 끝난다.
#:   잡는다   rtsp://gxop:pw@cam:554/live · "rtsp_url": "rtsps://a:b@h/x"
#:   안 잡는다 rtsp://***@cam:554/live (씻긴 꼴 — `:` 가 없다)
#:            rtsp://cam:554/live      (포트일 뿐 · `@` 가 없다)
#:            rtsp://cam:554/live@2x   (`@` 가 경로에 있다 — `/` 를 못 넘는다)
CRED_RE = re.compile(r"rtsps?://[^/\s\"'@]*:[^/\s\"'@]*@", re.IGNORECASE)

#: rtsp 를 **입에 올리기라도 했는가**. 0 이면 그 길이 안 돈 것이지 지켜진 것이 아니다.
MENTION_RE = re.compile(r"rtsps?://", re.IGNORECASE)

#: 훑을 컨테이너. 앱이 도는 것 셋 + 앞단 하나.
DEFAULT_CONTAINERS = ("gx-gunicorn-e", "gx-celery-e", "gx-beat-e", "gx-nginx-e")

DEFAULT_SINCE = "48h"


def scan_container(name: str, since: str):
    """`docker logs` 를 실제로 읽는다. `(훑은 줄, 언급 줄, 걸린 줄 목록, 사유)`."""
    try:
        proc = subprocess.run(
            ["docker", "logs", "--since", since, name],
            capture_output=True, timeout=180,
        )
    except FileNotFoundError:
        return 0, 0, [], "docker 가 없다"
    except subprocess.TimeoutExpired:
        return 0, 0, [], "docker logs 가 180초 안에 안 끝났다"
    if proc.returncode != 0:
        why = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        return 0, 0, [], (why[-1] if why else "docker logs 실패 rc=%d" % proc.returncode)
    text = (proc.stdout + proc.stderr).decode("utf-8", "replace")
    nlines = nmention = 0
    hits = []
    for line in text.splitlines():
        nlines += 1
        if MENTION_RE.search(line):
            nmention += 1
        if CRED_RE.search(line):
            hits.append(line)
    return nlines, nmention, hits, ""


def mask_hit(line: str) -> str:
    """걸린 줄을 **보고에 그대로 못 옮긴다** — 그러면 판정기가 유출기가 된다.

    자격 자리를 지우고, 어떤 꼴이 걸렸는지만 남긴다.
    """
    masked = CRED_RE.sub(lambda m: m.group(0).split("://")[0] + "://<자격>@", line)
    masked = masked.strip()
    return masked[:160] + ("…" if len(masked) > 160 else "")


# ─────────────────────────────────────────────────────────────────────────────
# ② 정적 검사 — AST 로 `ip_source` 의 흐름을 좇는다
# ─────────────────────────────────────────────────────────────────────────────

#: 물이 드는 **샘**. 운영자가 손으로 적는 카메라 주소 칸 하나뿐이다.
TAINT_SOURCE_ATTRS = ("ip_source",)

#: 씻는 함수. 여기 든 호출 **안에** 있으면 통과다.
SANITIZERS = ("_redact", "redact", "redact_url", "redact_payload",
              "mask_url", "_mask", "mask_credentials")

#: 로그 싱크. 받는 쪽이 logger 든 self.logger 든 logging 이든 이름만 본다.
LOG_METHODS = ("debug", "info", "warning", "warn", "error", "exception", "critical", "log")

#: **물이 그대로 통과하는 호출.** 글자를 옮겨 담을 뿐 지우지 않는 것들이다.
#:
#: ⚠ 여기 없는 호출은 **막이다** — 물이 거기서 끊긴다. 겁이 많은 판정이 아니라
#:   **덜 재는** 판정이고, 그렇게 고른 이유가 있다 [실측 2026-09-20]:
#:   막을 안 두면 `capture_service.py` 의 `reason = _probe_tcp(rtsp_url, …)` 처럼
#:   **안에서 이미 씻고 나오는** 도우미의 반환값까지 물든 것으로 세어, 19건 중
#:   여섯이 오탐이 됐다. 오탐이 섞인 게이트는 다음 사람이 통째로 무시한다.
#:   → 그래서 이 게이트가 잡는 것은 **「물든 값을 로그 줄에 직접 끼워 넣는 줄」**이다.
#:     도우미를 한 번 거친 값은 **그 도우미의 일**이고 여기서 안 센다.
PASSTHROUGH_CALLS = ("dumps", "dump", "str", "repr", "format", "join",
                     "strip", "lower", "upper", "get", "list", "dict", "tuple")


def _dotted(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _dotted(node.value) + "." + node.attr
    return ""


def _is_sanitizer_call(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = _dotted(node.func).rsplit(".", 1)[-1]
    return name in SANITIZERS


def _is_log_sink(node) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name) and node.func.id == "print":
        return True
    if isinstance(node.func, ast.Attribute) and node.func.attr in LOG_METHODS:
        return True
    return False


def _is_barrier(node) -> bool:
    """이 호출에서 물이 끊기는가. 씻는 호출 · 그리고 **옮겨 담지 않는 모든 호출**."""
    if not isinstance(node, ast.Call):
        return False
    if _is_sanitizer_call(node):
        return True
    name = _dotted(node.func).rsplit(".", 1)[-1]
    return name not in PASSTHROUGH_CALLS


def _touches_taint(node, tainted) -> bool:
    """이 식이 물든 것을 건드리는가. **막 뒤는 안 본다.**"""
    stack = [node]
    while stack:
        cur = stack.pop()
        if _is_barrier(cur):
            continue                       # 여기서 끊긴다 (씻겼거나 · 남의 일이거나)
        if isinstance(cur, ast.Attribute) and cur.attr in TAINT_SOURCE_ATTRS:
            return True
        if isinstance(cur, ast.Name) and cur.id in tainted:
            return True
        stack.extend(ast.iter_child_nodes(cur))
    return False


def _assign_targets(node):
    out = []
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    for t in targets:
        for sub in ast.walk(t):
            if isinstance(sub, ast.Name):
                out.append(sub.id)
    return out


def _scope_bodies(tree):
    """함수 하나 = 한 통. 모듈 본문도 한 통으로 센다."""
    scopes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            scopes.append(node)
    return scopes


def _scope_nodes(scope):
    """**이 통에만** 속한 노드. 안쪽 함수는 제 통에서 따로 본다.

    ⚠ 이걸 안 가르면 두 가지가 한꺼번에 어긋난다: 같은 줄이 **두 번** 세어지고
      (모듈 통 + 함수 통), 함수 A 에서 물든 이름이 함수 B 의 같은 이름을 물들인다.
    """
    out = []
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        cur = stack.pop()
        # ⚠ `Lambda` 는 **안 가른다.** 람다에는 대입이 없어 남의 통을 물들일 수 없고,
        #   가르면 바깥에서 물든 이름이 람다 안 로그 줄에서 사라진다(덜 보게 된다).
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue                      # 제 통에서 본다
        out.append(cur)
        stack.extend(ast.iter_child_nodes(cur))
    return out


def analyze_source(src: str, path: str = "<mem>"):
    """물든 값이 씻기지 않고 로그로 가는 줄 목록."""
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [], "구문 오류 %s" % exc
    findings = []
    for scope in _scope_bodies(tree):
        nodes = _scope_nodes(scope)
        tainted = set()
        # ★ 고정점 — 대입이 로그 줄보다 **뒤에** 있어도 잡아야 한다.
        #   `rtsp_url = a; a = m.ip_source` 같은 순서를 사람이 안 쓴다는 보장이 없다.
        for _ in range(6):
            grew = False
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                    if node.value is not None and _touches_taint(node.value, tainted):
                        for name in _assign_targets(node):
                            if name not in tainted:
                                tainted.add(name)
                                grew = True
            if not grew:
                break
        for node in nodes:
            if not _is_log_sink(node):
                continue
            args = list(node.args) + [kw.value for kw in node.keywords]
            if any(_touches_taint(a, tainted) for a in args):
                findings.append((path, node.lineno, _dotted(node.func) or "print"))
    findings = sorted(set(findings), key=lambda f: (f[0], f[1]))
    return findings, ""


#: 훑을 파이썬. 시험 파일은 뺀다 — 가짜 자격을 **일부러** 쓰는 자리다.
SCAN_ROOTS = ("backend",)
SKIP_DIRS = ("__pycache__", "migrations", "node_modules", ".venv", "tests")


def iter_py_files():
    for rootname in SCAN_ROOTS:
        base = ROOT / rootname
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                if fn.endswith(".py"):
                    yield Path(dirpath) / fn


def scan_static():
    findings, nfiles, broken = [], 0, []
    for path in iter_py_files():
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            broken.append((str(path), str(exc)))
            continue
        nfiles += 1
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        got, why = analyze_source(src, rel)
        if why:
            broken.append((rel, why))
        findings.extend(got)
    return findings, nfiles, broken


# ─────────────────────────────────────────────────────────────────────────────
# 출생 표본 (D-310 · D-400) — **이 결함이 실제로 있던 그 모양**을 시험으로 박는다
# ─────────────────────────────────────────────────────────────────────────────

BIRTH_LEAK = '''
def start_record(cls, stream_monitor_id):
    rtsp_url = f"{settings.RTSP_URL}/stream/{stream_monitor_id}"
    if stream_monitor.is_external:
        rtsp_url = stream_monitor.ip_source
    logger.info(f"[START_RECORD] RTSP URL: {rtsp_url}")
'''

BIRTH_INDIRECT = '''
def start_record(cls, sid):
    rtsp_url = stream_monitor.ip_source
    body_data = {"rtsp_url": rtsp_url, "stream_id": sid}
    logger.info(f"[START_RECORD] Request body: {json.dumps(body_data, indent=2)}")
'''

BIRTH_PRINT = '''
def capture(stream_id):
    rtsp_url = stream_monitor.ip_source
    print("rtsp_url: ", rtsp_url)
'''

BIRTH_REDACTED = '''
def capture(stream_id):
    rtsp_url = stream_monitor.ip_source
    logger.info(f"[capture_frame] Starting capture from RTSP: {_redact(rtsp_url)}")
    subprocess.Popen(["ffmpeg", "-i", rtsp_url])
'''

#: f-string 이 아닌 꼴 둘. 다음 사람이 쓸 법한 모양은 f-string 만이 아니다 —
#: `%s` 지연 포매팅은 로깅에서 **권장되는** 쓰기라 오히려 더 자주 온다.
BIRTH_LAZY_FORMAT = '''
def capture(stream_id):
    rtsp_url = stream_monitor.ip_source
    logger.info("capture from RTSP: %s", rtsp_url)
'''

#: 대입조차 안 거치고 **칸을 바로** 찍는 꼴.
BIRTH_DIRECT_ATTR = '''
def capture(stream_monitor):
    logger.warning(f"external camera: {stream_monitor.ip_source}")
'''

#: 막의 경계선. **이 줄이 왜 안 걸리는지**를 표본으로 박아 둔다 — 다음 사람이
#: 「이것도 잡아야 하는 것 아닌가」를 물을 때 답이 코드에 있어야 한다.
BIRTH_HELPER = '''
def capture(stream_id):
    rtsp_url = stream_monitor.ip_source
    reason = _probe_tcp(rtsp_url, 5)
    logger.error(f"capture failed: {reason}")
'''

#: 고친 꼴 — 한 겹 건너 새던 것을 `redact_payload` 로 씻은 실물 (P-200 처방).
BIRTH_FIXED_PAYLOAD = '''
def start_record(cls, sid):
    rtsp_url = stream_monitor.ip_source
    body_data = {"rtsp_url": rtsp_url, "stream_id": sid}
    logger.info(f"[START_RECORD] body: {json.dumps(redact_payload(body_data), indent=2)}")
    requests.post(url, json=body_data)
'''

BIRTH_INNOCENT = '''
def process(operation):
    stream_urls = [s.stream_url for s in operation.streams]
    print("stream_urls: ", stream_urls)
    rtsp_url = f"{settings.RTSP_URL}/stream/{operation.code}"
    logger.info(f"internal rtsp: {rtsp_url}")
'''

#: 로그 줄 표본 — 잡아야 하는 것 / 잡으면 안 되는 것
LINE_SAMPLES = (
    ("rtsp://gxfake:fakepw@cam.invalid:554/live", True, "자격이 든 주소"),
    ('{"rtsp_url": "rtsps://u1:p2@h.invalid/x"}', True, "JSON 몸통 안에 든 것"),
    ("INFO capture from RTSP: rtsp://***@cam.invalid:554/live", False, "씻긴 꼴"),
    ("INFO rtsp://cam.invalid:554/live", False, "자격 없는 주소 (포트의 : 뿐)"),
    ("INFO rtsp://cam.invalid/live@2x.mp4", False, "@ 가 경로에 있는 것"),
    ("GET /api/v1/x?u=rtsp%3A%2F%2Fa%3Ab%40h HTTP/1.1", False, "URL 인코딩된 것 (못 본다 — 아래 ⚠)"),
)


def self_test() -> int:
    bad = 0
    print("%s 자기시험 — 출생 표본" % TAG)

    for src, label, want in (
        (BIRTH_LEAK, "① 턴 X 실물: ip_source → rtsp_url → logger.info", True),
        (BIRTH_INDIRECT, "② 한 겹 건너: dict → json.dumps → logger.info", True),
        (BIRTH_PRINT, "③ 턴 W 실물: print(\"rtsp_url: \", rtsp_url)", True),
        (BIRTH_LAZY_FORMAT, "③' `logger.info(\"… %s\", rtsp_url)` 지연 포매팅도 잡는다", True),
        (BIRTH_DIRECT_ATTR, "③'' 대입 없이 `{m.ip_source}` 를 바로 찍는 줄도 잡는다", True),
        (BIRTH_REDACTED, "④ _redact 로 씻은 줄은 **안** 걸린다", False),
        (BIRTH_FIXED_PAYLOAD, "④' redact_payload 로 씻은 몸통은 **안** 걸린다", False),
        (BIRTH_INNOCENT, "⑤ ip_source 에서 안 온 url 은 **안** 걸린다 (금지구역 오탐)", False),
        (BIRTH_HELPER, "⑥ 도우미를 한 번 거친 반환값은 **안** 센다 (막 — 덜 재는 쪽)", False),
    ):
        got, why = analyze_source(src, "<표본>")
        ok = (len(got) > 0) == want and not why
        bad += 0 if ok else 1
        print("  %s %s  → %d건" % ("O" if ok else "X", label, len(got)))

    for line, want, label in LINE_SAMPLES:
        ok = bool(CRED_RE.search(line)) == want
        bad += 0 if ok else 1
        print("  %s 로그 줄: %s (%s)" % ("O" if ok else "X", label,
                                         "잡는다" if want else "안 잡는다"))

    # 씻는 함수 목록이 비면 이 게이트는 **모든 것을 빨강**으로 몬다 — 그것도 고장이다.
    ok = len(SANITIZERS) > 0 and "_redact" in SANITIZERS
    bad += 0 if ok else 1
    print("  %s 씻는 함수 목록이 살아 있다 (_redact 포함)" % ("O" if ok else "X"))

    # 샘이 비면 ②는 **언제나 초록**이다.
    ok = len(TAINT_SOURCE_ATTRS) > 0
    bad += 0 if ok else 1
    print("  %s 물드는 샘 목록이 살아 있다 (%s)" % ("O" if ok else "X",
                                                 ", ".join(TAINT_SOURCE_ATTRS)))

    print("%s 자기시험 %s" % (TAG, "전부 통과" if bad == 0 else "%d개 어긋남" % bad))
    return EXIT_OK if bad == 0 else EXIT_RED


# ─────────────────────────────────────────────────────────────────────────────


def run(containers, since: str, skip_logs: bool) -> int:
    red = grey = 0

    # ② 정적 — 먼저 본다. 도커가 없어도 이쪽은 늘 잴 수 있다.
    findings, nfiles, broken = scan_static()
    print("파이썬 파일 %d개 훑음 (AST)" % nfiles)
    if nfiles == 0:
        print("  ? 훑은 파일이 0개 — **검사 못 함**이지 0건이 아니다")
        grey += 1
    elif findings:
        print("  X 자격이 씻기지 않고 로그로 가는 줄 %d개" % len(findings))
        for rel, lineno, func in findings:
            print("       %s:%d  %s(…)" % (rel, lineno, func))
        red += 1
    else:
        print("  O 자격이 씻기지 않고 로그로 가는 줄 0개")
    for rel, why in broken:
        print("  ? 못 읽음: %s — %s" % (rel, why))
        grey += 1

    # ① 살아 있는 로그
    if skip_logs:
        print("\n살아 있는 로그 — 건너뜀 (--no-logs)")
        grey += 1
    else:
        total = mentions = 0
        allhits = []
        print("")
        for name in containers:
            n, m, hits, why = scan_container(name, since)
            if why:
                print("  ? %-14s 못 읽음 — %s" % (name, why))
                grey += 1
                continue
            total += n
            mentions += m
            allhits.extend((name, h) for h in hits)
            mark = "X" if hits else "O"
            print("  %s %-14s %6d줄 훑음 · rtsp 언급 %d줄 · **자격 %d줄**"
                  % (mark, name, n, m, len(hits)))
        print("로그 줄 %d개 훑음 (docker logs --since %s)" % (total, since))
        if total == 0:
            print("  ? 훑은 로그 줄이 0개 — 컨테이너가 안 떴거나 docker 가 없다. **못 잼**")
            grey += 1
        elif allhits:
            print("  X 살아 있는 로그에 카메라 자격 %d줄 (아래는 **자격을 지운** 꼴)"
                  % len(allhits))
            for name, h in allhits[:10]:
                print("       %-14s %s" % (name, mask_hit(h)))
            red += 1
        else:
            print("  O 살아 있는 로그에 카메라 자격 0줄")
            if mentions == 0:
                print("       ⚠ rtsp 언급 자체가 0줄이다 — **그 길이 이 창에 안 돌았다.**"
                      " 이 0 은 「지켜졌다」가 아니라 「지나간 것이 없다」에 가깝다."
                      " ②(정적)가 이 창의 실질적인 지킴이다.")

    if red:
        print("\n%s 빨강 — 카메라 자격이 로그로 간다 (막은 것이 돌아왔다)" % TAG)
        return EXIT_RED
    if grey:
        print("\n%s 회색 — 한 면을 못 쟀다. 회색은 초록이 아니다" % TAG)
        return EXIT_GREY
    print("\n%s 초록 — 자격이 로그로 가는 줄 0 (살아 있는 로그 · 코드 둘 다)" % TAG)
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--since", default=DEFAULT_SINCE,
                    help="docker logs --since (줄이 아니라 **시각**으로 자른다)")
    ap.add_argument("--container", action="append", default=[],
                    help="훑을 컨테이너 (여러 번 · 기본은 앱 셋 + 앞단)")
    ap.add_argument("--no-logs", action="store_true",
                    help="정적 검사만 (도커 없는 자리 — 회색이 된다)")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 깨졌다 — 재지 않는다" % TAG)
        return rc
    print("")
    return run(tuple(a.container) or DEFAULT_CONTAINERS, a.since, a.no_logs)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header

    _n_py = sum(1 for _r in SCAN_ROOTS for _p in (ROOT / _r).rglob("*.py")
                if not set(_p.parts) & set(SKIP_DIRS)) if SCAN_ROOTS else 0
    gate_header(
        __file__,
        measured=("카메라 **자격이 로그로 새는가** — **분모 %d대**(`%s` 의 stdout) "
                  "+ **%s개**(`%s` 파이썬 전수 · AST 로 새는 길을 잇는다 · 지금 "
                  "셌다) · 헹굼 %d종 · 로그 호출 %d종. ★ `rtsp://` **언급이 0건**"
                  "이면 그 길이 안 돈 것이지 지켜진 것이 아니다"
                  % (len(DEFAULT_CONTAINERS), " · ".join(DEFAULT_CONTAINERS),
                     _n_py or "못 셌다", " · ".join(SCAN_ROOTS),
                     len(SANITIZERS), len(LOG_METHODS))),
        target="살아 있는 컨테이너의 stdout (docker logs) + backend/ 파이썬 AST",
        as_="자격 없음 — 로그를 읽고 코드를 읽는다. 제품에 요청을 보내지 않는다",
        source="docker logs --since (지금 도는 컨테이너) · 저장소 파일 바이트",
    )
    raise SystemExit(main())
