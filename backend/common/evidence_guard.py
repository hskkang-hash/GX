# -*- coding: utf-8 -*-
"""P-87 ④ — **시험은 운영 증거를 덮지 않는다.** 증거 폴더 쓰기 가드 (턴 I · 차선 Q).

무엇이 이 파일을 만들었나 — **시험 DB 의 수가 운영 증거로 둔갑했다**
--------------------------------------------------------------------
[실측 2026-09-06 · 턴 H · 차선 E]

    시험 뒤 파일   : {"verdict": "SKIPPED_UNDECLARED",    "purged": 0}   ← 시험 DB 의 사실
    개발 DB 의 사실 : {"verdict": "SKIPPED_UNREVERSIBLE", "purged": 0}

`gx-shell` 에는 `/docs` 가 붙어 있다. 그래서 `tests/…` 가 `ops_audit_purge_beat()` 을
부르는 순간 그 호출이 `docs/agent/evidence/D-373/audit_purge_last.json` 을 **진짜로
고쳤다.** 그 파일을 읽은 사람은 개발 환경이 미선언이라고 읽는다. 아니다 —
시험 DB 에 선언이 없었을 뿐이다. **「어느 DB 에서 난 수인가」가 사라지면 그 파일은
증거가 아니라 소음이다.**

그때 막은 자리는 **한 곳뿐이었다**(`ops_tasks._write_evidence`). 증거 폴더에 쓰는
자리는 그 하나가 아니다 — 장부 명령 둘, 등재부 하나, 시험 안의 부트스트랩 하나,
그리고 시험이 불러 쓰는 `scripts/` 의 도구 수십. **한 자리만 막은 가드는
「막혀 있다」는 착시를 준다.**

무엇을 하는가 — 두 층
---------------------
  ① **공통 술어**  `blocked_reason(path)` — 이 자리에 지금 써도 되는가.
     증거 폴더에 쓰는 모든 **우리 코드**가 이것을 부른다. 부르는 쪽은 조용히
     넘기지 않고 「안 썼다」를 사유와 함께 남긴다.

  ② **바닥 그물**  `install_pytest_net()` — pytest 세션에서 파일 쓰기 원시함수
     (`builtins.open`·`io.open`·`os.replace`·`os.rename`·`os.remove`)를 감싸
     증거 폴더로 가는 쓰기를 **예외로 세운다**. ①을 안 부르는 경로(우리가 아직
     모르는 자리, `scripts/` 의 도구, 남이 만든 라이브러리)까지 여기서 걸린다.

     ★ ②가 있는 이유: ①은 **부르는 쪽이 기억해야** 듣는다. 기억에 맡긴 규칙은
       바쁜 날 깨진다(D-286). 그물은 기억을 요구하지 않는다.

일부러 쓰는 자리는 **이름을 대고** 연다
---------------------------------------
E2E 시험은 자기 증거(`evidence/e2e/<시나리오>/steps.md`)를 남기는 것이 일이다.
그 자리는 `allow_evidence_writes("E2E-1 단계표")` 로 **이름을 대고** 연다 —
환경변수 하나로 통째로 끄는 길은 두지 않는다. 통째로 끄는 손잡이는 반드시
「일단 켜 두고 잊기」로 쓰인다.

    with allow_evidence_writes("E2E 단계표"):
        path.write_text(body, encoding="utf-8")

Django 를 안 쓴다 — `scripts/` 에서도 `backend/` 에서도 같은 함수를 부를 수 있게.
"""
from __future__ import annotations

import builtins
import io
import os
import threading
from contextlib import contextmanager
from pathlib import PurePath

#: 증거 폴더의 자리. **경로 조각으로 본다** — 문자열 `in` 으로 보면
#: `/tmp/xdocs/agent/evidenceX` 같은 것이 걸리거나 빠진다.
EVIDENCE_SEGMENTS = ("docs", "agent", "evidence")

#: pytest 세션 안인가. `PYTEST_CURRENT_TEST` 는 **시험 하나가 도는 동안에만** 선다 —
#: 수집·픽스처·세션 마무리에서 나는 쓰기는 그 깃발로 못 본다. 그래서 그물이
#: 세션 시작에 이 이름을 세우고, 술어는 **둘 다** 본다.
SESSION_ENV = "GX_UNDER_PYTEST"

_local = threading.local()


class EvidenceWriteBlocked(RuntimeError):
    """시험 중에 증거 폴더로 간 쓰기. **예외다** — 조용히 넘기면 가드가 아니다."""


# ═══════════════════════════════════════════════════════════════════════════
# 술어
# ═══════════════════════════════════════════════════════════════════════════
def is_evidence_path(path) -> bool:
    """이 경로가 `docs/agent/evidence/**` 안인가. **조각 세 개가 이어져야** 참이다."""
    try:
        parts = [p.lower() for p in PurePath(str(path).replace("\\", "/")).parts]
    except (TypeError, ValueError):
        return False
    n = len(EVIDENCE_SEGMENTS)
    return any(tuple(parts[i:i + n]) == EVIDENCE_SEGMENTS
               for i in range(max(0, len(parts) - n + 1)))


def under_pytest() -> bool:
    """지금 시험이 돌고 있는가. **깃발 둘을 다 본다** (하나는 시험 안, 하나는 세션)."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or \
        os.environ.get(SESSION_ENV) == "1"


def writes_allowed() -> bool:
    """이 스레드가 **이름을 대고** 증거 쓰기를 열어 두었는가."""
    return bool(getattr(_local, "allow", 0))


def synthetic_active() -> bool:
    """지금 **지어낸 상태**로 돌고 있는가 (판정기 자기시험·탐침)."""
    return bool(getattr(_local, "synthetic", 0))


@contextmanager
def synthetic_run(who: str):
    """★ **지어낸 상태로 부른 것은 증거가 아니다** [실측 2026-09-06 · 턴 I · 차선 E 가 잡음].

    무엇이 이 손잡이를 만들었나 — **판정기가 자기 증거를 덮었다**

        scripts/verify_retention_declared.py:371
            with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True, OPS_BACKUP_DIR=""):
                out = ops_tasks.ops_backup_beat()

    이 판정기는 「목적지가 미선언이면 백업 도구를 안 부르는가」를 재려고
    **설정을 일부러 비워** 백업 주기를 부른다. 그 호출이
    `docs/agent/evidence/D-373/backup_last.json` 에 그대로 떨어졌다:

        {"verdict": "SKIPPED_UNDECLARED", "reason": "백업 목적지가 선언되지 않았다"}

    그런데 이 환경의 사실은 `OPS_BACKUP_DIR='/backup'` · `ENABLED=True` 다 [실측].
    파일을 읽은 사람은 **개발 환경이 미선언이라 백업을 건너뛰었다**고 읽는다.
    아니다 — **판정기가 잠깐 비워 놓고 물어본 것**이다.

    ★ 그리고 이것이 `PYTEST_CURRENT_TEST` 가드를 **그냥 지나갔다.** 판정기는
      시험이 아니기 때문이다. 가드가 물은 질문이 틀렸던 것이다:
      물어야 할 것은 「시험 중인가」가 아니라 **「이 수가 진짜 상태에서 났는가」**다.

    ⚠ `allow_evidence_writes` 보다 **강하다.** 지어낸 상태 안에서는 이름을 대도
      못 쓴다 — 지어낸 수에 이름을 붙이면 그것이 가장 그럴듯한 거짓 증거가 된다.
    """
    if not str(who or "").strip():
        raise ValueError("지어낸 상태를 열려면 **무엇을 지어냈는지** 적어야 한다")
    _local.synthetic = getattr(_local, "synthetic", 0) + 1
    _local.synthetic_who = who
    try:
        yield
    finally:
        _local.synthetic = max(0, getattr(_local, "synthetic", 1) - 1)


@contextmanager
def allow_evidence_writes(who: str):
    """증거 쓰기를 **이 블록 동안만** 연다. `who` 는 사유이고 비울 수 없다."""
    if not str(who or "").strip():
        raise ValueError("증거 쓰기를 열려면 **누가·왜**를 적어야 한다 — "
                         "이름 없는 예외는 다음 사람이 지울 수 없다")
    _local.allow = getattr(_local, "allow", 0) + 1
    _local.who = who
    try:
        yield
    finally:
        _local.allow = max(0, getattr(_local, "allow", 1) - 1)


def looks_like_test_db(name) -> bool:
    """이 DB 이름이 **시험 DB** 인가. `test_` 로 시작하면 그렇다 (장고의 규칙)."""
    return str(name or "").lower().startswith("test_")


def blocked_reason(path, *, who: str = "", db_name: str = "") -> str | None:
    """막아야 하면 **사유 한 문장**, 써도 되면 `None`.

    막는 자리는 셋이고 **셋 다 「이 수가 진짜 상태에서 났는가」를 묻는다**:

      ① 지어낸 상태(`synthetic_run`)에서 났다 — 이름을 대도 못 쓴다
      ② 시험 DB 에서 났다(`test_…`) — 어느 프로세스든, pytest 밖이어도 막는다
      ③ 시험이 돌고 있다 — 「이름을 댄 예외」만 지나간다
    """
    if not is_evidence_path(path):
        return None
    tail = f" ({who})" if who else ""
    if synthetic_active():
        return (f"**지어낸 상태**에서 난 수는 증거가 아니다{tail} — {path}. "
                f"지금 열려 있는 것: {getattr(_local, 'synthetic_who', '?')}. "
                "판정기가 설정을 비워 놓고 물어본 답을 운영 증거로 적으면, 그 파일을 "
                "읽는 사람은 **환경이 그렇다고 읽는다** (실측 2026-09-06 · 턴 I)")
    if looks_like_test_db(db_name):
        return (f"**시험 DB**({db_name})에서 난 수는 증거가 아니다{tail} — {path}. "
                "「어느 DB 에서 난 수인가」가 사라지면 그 파일은 증거가 아니라 소음이다")
    if not under_pytest():
        return None
    if writes_allowed():
        return None
    return (f"시험 중에는 증거 폴더에 쓰지 않는다{tail} — {path}. "
            "시험 DB 의 수로 운영 증거를 덮으면 그 파일을 읽는 사람이 "
            "**개발 환경의 사실로 읽는다** (실측 2026-09-06 · 턴 H). "
            "일부러 쓰는 자리라면 `allow_evidence_writes(\"사유\")` 로 이름을 대고 연다")


def write_text_guarded(path, text: str, *, who: str = "", db_name: str = "",
                       encoding: str = "utf-8") -> str | None:
    """증거 파일 한 장을 쓴다. 막히면 **안 쓰고 `None`** — 예외를 던지지 않는다.

    부르는 쪽이 「썼는가」를 종료 코드가 아니라 **반환값**으로 알게 하려는 것이다.
    """
    from pathlib import Path

    if blocked_reason(path, who=who, db_name=db_name):
        return None
    target = Path(str(path))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=encoding)
    return str(target)


# ═══════════════════════════════════════════════════════════════════════════
# 바닥 그물 — 원시 쓰기 함수를 감싼다
# ═══════════════════════════════════════════════════════════════════════════
_WRITE_MODES = set("wax+")
_installed = False
_original: dict = {}


def _mode_writes(mode) -> bool:
    return bool(_WRITE_MODES & set(str(mode or "r")))


def _guard(path, verb: str) -> None:
    why = blocked_reason(path)
    if why:
        raise EvidenceWriteBlocked(f"[{verb}] {why}")


def install_pytest_net() -> bool:
    """쓰기 원시함수에 그물을 건다. 이미 걸려 있으면 `False`.

    ⚠ **읽기는 건드리지 않는다.** 증거를 읽는 시험은 많고, 그것은 정상이다.
    """
    global _installed
    if _installed:
        return False

    _original["builtins_open"] = builtins.open
    _original["io_open"] = io.open
    _original["os_replace"] = os.replace
    _original["os_rename"] = os.rename
    _original["os_remove"] = os.remove
    _original["os_unlink"] = os.unlink

    def _open(file, mode="r", *args, **kwargs):
        if _mode_writes(mode):
            _guard(file, "열기")
        return _original["io_open"](file, mode, *args, **kwargs)

    def _replace(src, dst, **kwargs):
        _guard(dst, "덮어쓰기")
        return _original["os_replace"](src, dst, **kwargs)

    def _rename(src, dst, **kwargs):
        _guard(dst, "이름 바꾸기")
        return _original["os_rename"](src, dst, **kwargs)

    def _remove(path, **kwargs):
        _guard(path, "지우기")
        return _original["os_remove"](path, **kwargs)

    def _unlink(path, **kwargs):
        _guard(path, "지우기")
        return _original["os_unlink"](path, **kwargs)

    builtins.open = _open
    io.open = _open
    os.replace = _replace
    os.rename = _rename
    os.remove = _remove
    os.unlink = _unlink
    os.environ[SESSION_ENV] = "1"
    _installed = True
    return True


def uninstall_pytest_net() -> None:
    """그물을 걷는다 — 시험 안에서 그물 자체를 시험할 때만 쓴다."""
    global _installed
    if not _installed:
        return
    builtins.open = _original["builtins_open"]
    io.open = _original["io_open"]
    os.replace = _original["os_replace"]
    os.rename = _original["os_rename"]
    os.remove = _original["os_remove"]
    os.unlink = _original["os_unlink"]
    os.environ.pop(SESSION_ENV, None)
    _installed = False


def net_is_installed() -> bool:
    return _installed
