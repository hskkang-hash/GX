# -*- coding: utf-8 -*-
"""P-107 — **게이트는 자기가 무엇을 쟀는지 먼저 말한다** (2026-09-07 · 턴 M · 차선 Q).

무엇이 이 파일을 만들게 했나 — **출생 표본 넷**
-----------------------------------------------
턴 L 이 초록인 게이트 넷을 열어 보니, 넷 다 **제품이 아닌 것**을 재고 있었다:

  ① `verify_tenant_scope`  8월에 찍은 **라우트 사진**(531)을 읽고 있었다. 살아 있는
     라우터는 **705** 였고, 99개 라우트는 그 사진에 아예 없었다.
  ② `verify_write_auth`    분모 **30** 은 손으로 적은 목록이었다. 실제 쓰기 표면은
     **377**. 나머지 347 은 **한 번도 불린 적이 없다.**
  ③ `verify_screens` · `walk_scenarios.py`  **역할이 0개인 계정**(`gxprobe_e2e`)으로
     걸었다. 「걷기 3/3 · 콘솔 0」은 「됐다」가 아니라 **「거기까지 못 갔다」**였다.
  ④ `verify_minio`         「저장소 health 200 · 객체 21」은 **호스트 `.env` 의 root
     자격**으로 잰 수다. 앱이 들고 있는 자격은 5자짜리 자리표이고, 앱은 **503** 을 받는다.

넷의 공통점은 초록/빨강이 아니다. **무엇을 쟀는지 아무도 말하지 않았다**는 것이다.

그래서 규칙 (세종 · 턴 M)
-------------------------
    게이트는 **앱의 자격으로 · 앱의 출처에서 · 앱의 대상을** 잰다.
    root 로 잰 초록 · admin 으로 잰 초록 · **사진으로** 잰 초록 · **손 목록으로**
    잰 초록은 초록이 아니다.

    그래서 모든 게이트는 **세 줄을 먼저 찍는다** (⚠ **stderr 로** — stdout 은 기계용
    출력의 자리다. 2026-09-07 에 이것을 stdout 으로 냈다가 `deploy.sh` 의
    `--emit-drift` JSON 을 깨뜨려 배치가 되돌려졌다):

        [P-107] TARGET=무엇을 향해 쟀나   (URL · 컨테이너 · 커밋)
        [P-107] AS=누구로 쟀나            (계정 · 역할 · **자격의 이름**. 값은 절대 아니다)
        [P-107] SOURCE=어디서 읽었나      (살아 있는 라우터 · DB · 파일 — 파일이면 **적힌 날짜**)

    · `AS=root` · `AS=admin` 인데 **사유가 없으면 빨강**이다 (`reason=` 필수).
    · 머리글 **없는 게이트는 회색**으로 센다 — 검증 차선의 셈에서 초록이 아니다.

쓰는 법
-------
    if __name__ == "__main__":
        from _gate_header import gate_header
        gate_header(__file__,
                    target="http://localhost:8000 (gx-shell)",
                    as_="gxprobe_q · 역할 fire_user · 자격 이름 GX_PROBE_PASSWORD",
                    source="살아 있는 라우터 (django get_resolver)")
        raise SystemExit(main())

  세 값을 안 주면 **자동으로 유도한다** — 부르는 모듈의 최상위 `Path` 상수를 읽어
  `SOURCE=파일 …(기록 …)` 로 찍고, `TARGET` 은 저장소 경로와 HEAD, `AS` 는
  「자격증명 없음 — 파일을 읽는다」가 된다. 유도된 값도 **실측**이다(mtime 은 지금 잰다).
  다만 살아 있는 것을 재는 게이트는 유도로 덮이지 않는다 — 그런 게이트는 손으로 적는다.

도구로도 쓴다
-------------
    python scripts/_gate_header.py --audit      # 게이트 머리글 보유율 N/N
    python scripts/_gate_header.py --pipe-scan  # `| tail … $?` 거짓 초록 패턴 훑기
    python scripts/_gate_header.py --self-test  # 판정 규칙만

  `--audit` 과 `--pipe-scan` 의 **판정**은 `scripts/verify_gate_header.py` 가 낸다.
  여기 있는 것은 셈이고, 거기 있는 것이 게이트다.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 머리글은 **stderr** 로 나간다(아래 `gate_header` 의 ★★ 참조). 그래서 둘 다 세운다 —
#: 한쪽만 세우면 윈도 콘솔(cp949)에서 한글 머리글이 예외로 죽는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

TAG = "[P-107]"

#: 세 이름. **바꾸면 검사기(`verify_gate_header.py`)도 같은 커밋에서 바뀐다.**
KEY_TARGET, KEY_AS, KEY_SOURCE = "TARGET=", "AS=", "SOURCE="
#: ★ [P-204 · 2026-09-20 · 턴 Y · 차선 Q] **네 번째 줄 — 무엇을 · 분모 몇으로 쟀나.**
#:   세 줄은 「누구로 · 어디서 · 무엇을 향해」를 말하지만 **「몇 건을 쟀나」는 말하지 않는다.**
#:   그래서 `exit 0` 이 「제품이 성립한다」로 읽혔다. 그것은 틀린 독해다 —
#:   **`exit 0` 은 「이 호출이 통과」다.** 인자를 안 주면 정적만 보는 게이트,
#:   `--db` 없이 소스만 읽는 게이트가 **같은 0** 을 냈고, 셋째 줄까지 다 성립했다.
#:   ⇒ 머리글의 **마지막 줄**로 분모를 말하게 한다. 분모를 말 못 하면 그 통과는 회색이다.
KEY_MEASURED = "MEASURED="
KEYS = (KEY_TARGET, KEY_AS, KEY_SOURCE, KEY_MEASURED)

#: MEASURED 줄이 「분모」를 말했는지 본다. **수가 없으면 분모가 아니다.**
_DENOM = re.compile(r"분모\s*([0-9][0-9,]*)")

#: 게이트가 「나는 안 쟀다」고 스스로 적는 자리. 이 글자가 있으면 **없는 것과 같다**
#: (있는 척하는 줄보다 없다고 말하는 줄이 낫다 — 세는 쪽은 둘을 같게 센다).
MEASURED_NONE = "(선언 없음"

#: 사유 없이 서면 빨강인 이름들. **앱이 아닌 자격**이다.
PRIVILEGED = ("root", "admin", "superuser", "슈퍼", "관리자")

#: 자격의 **값**이 새어 들어오는 것을 막는다 — 머리글에는 이름만 적는다.
#: (이름은 대문자·밑줄이고, 값은 그렇지 않은 것이 보통이다. 그래서 값처럼 생긴
#:  긴 토큰이 섞이면 잘라 내고 자리에 표시를 남긴다.)
#: ★ 좁게 친다. 넓게 쳤더니 `DJANGO_SETTINGS_MODULE=config.settings` 와
#:   `docs/agent/evidence/.../openapi_routes` 가 «값 가림» 이 됐다 — 머리글이
#:   **읽을 수 없게 되는 것**은 머리글이 없는 것과 같다.
#:   자격의 **값**은 보통 대소문자와 숫자가 섞인 긴 덩어리이고, 경로도 이름도 아니다.
_SECRETISH = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z0-9+=_-]{20,}(?![A-Za-z0-9_])")


def _looks_like_value(token: str) -> bool:
    """이 덩어리가 **자격의 값**처럼 생겼는가 — 대·소문자와 숫자가 다 섞였는가.

    ★ `이름=값` 꼴이면 **`=` 뒤만** 본다. 이 한 줄이 없으면
      `captured_at=2026-09-07T20:20:03` 이 «값 가림» 이 되어 **사진의 날짜가 사라진다** —
      날짜를 지우려고 만든 규칙이 아니다.
    """
    tail = token.rsplit("=", 1)[-1]
    if len(tail) < 20:
        return False
    return (any(c.islower() for c in tail) and any(c.isupper() for c in tail)
            and any(c.isdigit() for c in tail))

#: 파일 안에 적혀 있는 「언제 만든 것인가」. 사진의 날짜는 mtime 이 아니라 이것이다.
_STAMP_FIELD = re.compile(
    r"[\"']?(captured_at|generated_at|updated_at|measured_at|as_of|created_at|"
    r"snapshot_at|run_at)[\"']?\s*[:=]\s*[\"']([^\"'\n]{4,40})[\"']")

#: **파일을 가리키는 자리**의 모양 — 경로 조각(`/`) 이나 아는 확장자가 붙어야 파일이다.
#: 「파일 사진이 아니다」 같은 문장은 파일을 가리키지 않는다.
_NAMES_A_FILE = re.compile(
    r"(file:\S|파일\s+\S*[/\\]\S|\.(json|ya?ml|md|txt|csv|png|sha256|lock)\b)", re.I)

_STATE = {"violations": [], "emitted": False}


# ═══════════════════════════════════════════════════════════════════════════
# 순수 판정 — 파일 없이 시험한다 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge_as(as_line: str, reason: str = "") -> list[str]:
    """`AS=` 한 줄을 판정한다. 어긋난 것들을 돌려준다 — **판정은 부르는 쪽이 한다.**

    빨강이 되는 자리 셋:
      ① 비었다               — 누구로 쟀는지 말하지 않은 게이트는 잰 것이 아니다
      ② root/admin 인데 사유가 없다 — 턴 L 의 `verify_minio` 가 바로 이 모양이었다
      ③ 자격의 **값**처럼 생긴 긴 토큰이 들어 있다 — 머리글에 값은 적지 않는다
    """
    out: list[str] = []
    text = (as_line or "").strip()
    if not text:
        out.append("AS= 가 비었다 — **누구로 쟀는지 말하지 않은 초록은 초록이 아니다**")
        return out
    low = text.lower()
    if any(p in low for p in PRIVILEGED) and not (reason or "").strip():
        out.append("AS=«%s» 는 앱의 자격이 아니다(root/admin). **사유가 없으면 빨강**이다 "
                   "— reason= 에 「무엇을 재려고 이 자격을 썼나」를 적는다" % text)
    if any(_looks_like_value(m.group(0)) for m in _SECRETISH.finditer(text)):
        out.append("AS= 에 자격의 **값**처럼 생긴 토큰이 있다 — 머리글에는 **이름만** 적는다")
    return out


def judge_source(source_line: str) -> list[str]:
    """`SOURCE=` 한 줄을 판정한다.

    파일을 읽었다고 말하면서 **언제 쓰인 것인지** 안 적으면 빨강이다 —
    턴 L 의 `verify_tenant_scope` 가 8월 사진을 읽으며 초록이었던 자리가 여기다.
    """
    out: list[str] = []
    text = (source_line or "").strip()
    if not text:
        out.append("SOURCE= 가 비었다 — 어디서 읽었는지 모르는 수는 실측이 아니다")
        return out
    #: 「파일」이라는 낱말이 아니라 **파일을 가리키는 자리**를 본다 —
    #: 「파일 사진이 아니다」라고 적은 줄까지 걸면 규칙이 스스로를 무디게 만든다.
    if _NAMES_A_FILE.search(text):
        if not re.search(r"(기록|written|\*\*없다\*\*|\d{4}-\d{2}-\d{2})", text):
            out.append("SOURCE= 가 파일을 가리키는데 **쓰인 날짜가 없다** — "
                       "사진에는 날짜가 붙어야 한다 (출생 표본 ①: 8월 라우트 사진)")
    return out


def judge_measured(measured: str) -> list[str]:
    """`MEASURED=` 한 줄을 판정한다 — **P-204 「`exit 0` 은 「이 호출이 통과」다」.**

    빨강이 되는 자리 셋:
      ① 없다        — 무엇을 몇 건 쟀는지 말하지 않은 `exit 0` 은 「통과」가 아니라 「이 호출이 끝났다」다
      ② 분모가 없다 — 「무엇을」만 적고 「몇 건」을 안 적으면 0건 검사와 전수 검사가 같은 글자가 된다
      ③ 분모가 0    — **분모 0인 초록은 초록이 아니다** (D-301)

    ⚠ 이 판정은 `judge_header` 에 **넣지 않았다.** 넣으면 P-204 이 생긴 순간
      머리글을 옳게 단 게이트 일흔일곱이 전부 「머리글 어긋남」으로 붉어져서
      **「머리글이 없다」와 「분모를 안 말한다」가 한 칸에 섞인다.** 칸을 가른다.
    """
    out: list[str] = []
    text = (measured or "").strip()
    if not text or text.startswith(MEASURED_NONE):
        out.append("MEASURED= 가 없다 — **`exit 0` 은 「이 호출이 통과」다.** "
                   "무엇을 · 분모 몇으로 쟀는지 말하지 않은 0 은 초록이 아니다 (P-204)")
        return out
    m = _DENOM.search(text)
    if not m:
        out.append("MEASURED= 에 **분모가 없다** — 「무엇을 · 분모 N」으로 적는다. "
                   "분모를 안 적으면 0건 검사와 전수 검사가 같은 글자다 (P-204)")
        return out
    if int(m.group(1).replace(",", "")) == 0:
        out.append("MEASURED= 의 **분모가 0**이다 — 0건 검사는 통과가 아니다 (D-301)")
    return out


def judge_header(target: str, as_: str, source: str, reason: str = "") -> list[str]:
    """세 줄을 한꺼번에. **비어 있는 머리글은 통과가 아니다.**"""
    out: list[str] = []
    if not (target or "").strip():
        out.append("TARGET= 이 비었다 — 무엇을 향해 쟀는지 모르는 수는 실측이 아니다")
    out += judge_as(as_, reason)
    out += judge_source(source)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 관측 — 지금 이 순간의 사실을 모은다
# ═══════════════════════════════════════════════════════════════════════════
def git_head(short: bool = True) -> str:
    """저장소의 지금 커밋. 못 읽으면 그렇게 말한다 — 「없음」을 지어내지 않는다."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short" if short else "HEAD", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "커밋 못 읽음"
    if proc.returncode != 0:
        return "커밋 못 읽음"
    return proc.stdout.decode("utf-8", "replace").strip() or "커밋 못 읽음"


def dirty_count() -> str:
    """작업본이 커밋과 몇 파일 어긋나 있는가. **재는 것은 커밋이 아니라 작업본이다.**"""
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "작업본 못 읽음"
    if proc.returncode != 0:
        return "작업본 못 읽음"
    n = len([l for l in proc.stdout.decode("utf-8", "replace").splitlines() if l.strip()])
    return "작업본 %d파일 어긋남" % n if n else "작업본 깨끗"


def file_stamp(path) -> str:
    """파일 하나를 **날짜와 함께** 적는다 — 「기록 …」 이 붙어야 SOURCE 가 성립한다.

    두 날짜를 다 본다. 파일이 스스로 적어 둔 `captured_at`/`updated_at` 이 있으면
    그것이 **사진을 찍은 날**이고, mtime 은 **파일이 마지막으로 닿은 날**이다.
    둘이 다르면 둘 다 적는다 — 어느 하나만 적으면 8월 사진이 9월로 보인다.
    """
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return "%s (**없다**)" % _rel(p)
    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M")
    inner = ""
    if p.suffix.lower() in (".json", ".yaml", ".yml", ".md") and st.st_size <= 8 * 1024 * 1024:
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:20000]
        except OSError:
            head = ""
        m = _STAMP_FIELD.search(head)
        if m:
            inner = " · 자기기록 %s=%s" % (m.group(1), m.group(2))
    return "%s (기록 %s%s · %d바이트)" % (_rel(p), mtime, inner, st.st_size)


def _rel(p: Path) -> str:
    try:
        return "파일 " + str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except (ValueError, OSError):
        return "파일 " + str(p).replace("\\", "/")


def files_source(paths) -> str:
    """여러 파일을 `SOURCE=` 한 줄로. **다 적는다** — 셋 넘으면 셋 + 나머지 수."""
    stamped = [file_stamp(p) for p in paths]
    if not stamped:
        return ""
    if len(stamped) <= 3:
        return " · ".join(stamped)
    return " · ".join(stamped[:3]) + " · 그 밖 %d개" % (len(stamped) - 3)


#: 역할 조회 결과를 여기 적어 둔다. **날짜와 함께** 적는다 — 이 파일도 사진이고,
#: 사진에는 날짜가 붙어야 한다(출생 표본 ①).
ROLE_CACHE = ROOT / "docs" / "agent" / "evidence" / "P-107" / "probe_roles.json"
ROLE_CACHE_MAX_AGE_SEC = 6 * 3600

_ROLE_SNIPPET = r"""
import json, os, sys
sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()
from django.contrib.auth import get_user_model
U = get_user_model()
out = {}
for name in sys.argv[1:]:
    u = U._base_manager.filter(username=name).first()
    out[name] = None if u is None else {
        "roles": sorted(r.code for r in u.roles.all()),
        "is_superuser": bool(u.is_superuser),
        "is_active": bool(u.is_active),
    }
print("GXROLES " + json.dumps(out, ensure_ascii=False))
"""


def roles_of(username: str, container: str = "") -> str:
    """계정의 **역할**을 살아 있는 DB 에서 읽어 한 마디로. 못 읽으면 **못 읽었다고** 쓴다.

    ★ 출생 표본 ③ — `verify_screens` 와 `walk_scenarios.py` 가 **역할 0개**인
      `gxprobe_e2e` 로 걸으면서 「걷기 3/3」을 냈다. 역할을 안 적었기 때문에 아무도
      몰랐다. 그래서 `AS=` 는 계정 이름만으로 성립하지 않는다 — **역할까지** 적는다.

    조회는 비싸다(docker exec). 그래서 **날짜가 붙은 캐시**에 적어 두고 6시간 쓴다.
    캐시에서 읽었으면 그 사실과 날짜를 그대로 말한다 — 사진을 사진이라 부른다.
    """
    if not username:
        return "계정 이름 없음"
    cached = _role_cache_read(username)
    if cached is not None:
        return cached

    name = container or os.environ.get("GX_ROUTE_CONTAINER") \
        or os.environ.get("GX_SHELL_CONTAINER") or "gx-shell"
    try:
        proc = subprocess.run(
            ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings", name,
             "python", "-c", _ROLE_SNIPPET, username],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return "역할 **못 읽었다**(docker 실패) — 0개일 수도 있다"
    line = next((l for l in proc.stdout.decode("utf-8", "replace").splitlines()
                 if l.startswith("GXROLES ")), "")
    if proc.returncode != 0 or not line:
        return "역할 **못 읽었다**(rc=%d) — 0개일 수도 있다" % proc.returncode
    import json as _json
    try:
        data = _json.loads(line[len("GXROLES "):])
    except ValueError:
        return "역할 **못 읽었다**(응답 해독 실패)"
    _role_cache_write(data)
    return _role_phrase(data.get(username))


def _role_phrase(entry) -> str:
    if entry is None:
        return "**그런 계정이 없다**"
    roles = entry.get("roles") or []
    if not roles:
        return "역할 **0개** ← 이 계정으로 낸 초록은 「됐다」가 아니라 「거기까지 못 갔다」다"
    tail = " · superuser" if entry.get("is_superuser") else ""
    return "역할 %s%s" % ("/".join(roles), tail)


def _role_cache_read(username: str):
    import json as _json
    try:
        st = ROLE_CACHE.stat()
        if (datetime.now(timezone.utc).timestamp() - st.st_mtime) > ROLE_CACHE_MAX_AGE_SEC:
            return None
        data = _json.loads(ROLE_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    users = data.get("users") or {}
    if username not in users:
        return None
    when = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%dT%H:%M")
    return "%s (캐시 %s · %s)" % (_role_phrase(users[username]), when,
                                  str(ROLE_CACHE.relative_to(ROOT)).replace("\\", "/"))


def _role_cache_write(data: dict) -> None:
    import json as _json
    try:
        ROLE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        old = {}
        if ROLE_CACHE.exists():
            old = (_json.loads(ROLE_CACHE.read_text(encoding="utf-8")) or {}).get("users") or {}
        old.update(data)
        ROLE_CACHE.write_text(_json.dumps(
            {"measured_at": datetime.now().isoformat(timespec="seconds"),
             "source": "docker exec <gx-shell> · django ORM · u.roles.all()",
             "users": old}, ensure_ascii=False, indent=1), encoding="utf-8")
    except (OSError, ValueError):
        pass


def account_as(user_env: str = "GX_ROUTE_USER", pw_env: str = "GX_ROUTE_PASSWORD",
               *, container: str = "", lookup: bool = True) -> str:
    """`AS=` 한 줄 — **계정 · 역할 · 자격의 이름**. 값은 절대 찍지 않는다."""
    user = (os.environ.get(user_env) or "").strip()
    if not user:
        return "%s 가 선언되지 않았다 — **누구로 잴지 모르는 채 잰 것이다**" % user_env
    role = roles_of(user, container) if lookup else "역할 미조회"
    return "%s · %s · 자격 이름 %s (값 아님)" % (user, role, pw_env)


def _caller_module_paths(script: str) -> list[Path]:
    """부르는 모듈의 **최상위 `Path` 상수**를 실제 값에서 모은다.

    읽어서 답하지 않는다(D-210) — `sys.modules` 에 이미 올라와 있는 그 모듈의
    전역을 본다. 그래서 여기 나오는 경로는 **그 게이트가 실제로 들고 있는 값**이다.
    """
    mod = None
    want = Path(script).resolve()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f:
            continue
        try:
            if Path(f).resolve() == want:
                mod = m
                break
        except OSError:
            continue
    if mod is None:
        return []
    out: list[Path] = []
    for name, value in sorted(vars(mod).items()):
        if not name.isupper() or not isinstance(value, Path):
            continue
        if name in ("ROOT", "REPO", "BASE"):      # 저장소 뿌리는 출처가 아니다
            continue
        try:
            if value.is_file():
                out.append(value)
        except OSError:
            continue
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 찍기
# ═══════════════════════════════════════════════════════════════════════════
def gate_header(script, *, target: str = "", as_: str = "", source: str = "",
                reason: str = "", measured: str = "", files=None,
                tag: str = TAG, stream=None) -> int:
    """**세 줄을 먼저 찍는다.** 어긋난 자리가 있으면 그 수를 돌려준다(0 이면 성립).

    이 함수는 **게이트를 죽이지 않는다.** 죽이면 「머리글이 없어서 빨강」과
    「제품이 무너져서 빨강」이 한 칸에 섞인다. 대신 어긋난 줄을 **소리 내어** 찍고,
    검증 차선의 `verify_gate_header.py` 가 그 자리를 판정한다 — 색은 거기서 난다.
    """
    #: ★★ [2026-09-07 · 턴 M · 프런트 차선이 실측] **머리글은 stderr 로 나간다.**
    #:
    #:   처음엔 stdout 으로 냈다. 그날 `deploy.sh:554` 가
    #:   `verify_bundle_hash.py --emit-drift` 의 **stdout 을 변수에 담고** 있었고,
    #:   그 변수는 `[P-107] TARGET=… {json}` 이 되어 JSON 해석에 실패했다 →
    #:   게이트가 **회색(exit 2)** → **배치가 되돌려졌다.**
    #:   17:01·17:51 기록의 JSON 은 깨끗했고 20:28 이후만 깨졌다 — 이 턴의 회귀다.
    #:
    #:   고치는 자리는 「그 게이트가 머리글을 끄게 하는 것」이 아니다. 그러면 기계용
    #:   출력을 내는 게이트마다 **머리글을 끌 수 있게** 되고, 끌 수 있는 규칙은
    #:   결국 꺼진다(D-353). 진단은 stderr 로 간다 — **머리글은 여전히 의무다.**
    #:   러너·`gate_run.sh`·`verify_gate_header.py` 는 셋 다 `2>&1` 로 받는다.
    out = stream or sys.stderr
    name = Path(script).name

    if not target:
        target = "저장소 %s @ %s · %s (살아 있는 것을 재지 않는 게이트다)" % (
            str(ROOT).replace("\\", "/"), git_head(), dirty_count())
    if not as_:
        as_ = "(자격증명 없음 — 소스·문서 파일을 읽는다)"
    if not source:
        paths = list(files) if files else _caller_module_paths(script)
        source = files_source(paths) if paths else ""
        if not source:
            source = ("저장소 작업본 트리 (%s · 지금 읽는다)" % git_head())

    target, as_, source = (_scrub(target), _scrub(as_), _scrub(source))

    #: ★ [P-204] **마지막 줄은 분모다.** 안 주면 그 게이트가 스스로 「안 말했다」고 적는다 —
    #:   조용히 빠지면 세는 쪽이 「없는 것」과 「말 안 한 것」을 못 가른다.
    if not measured:
        measured = ("%s — 이 게이트는 **무엇을 · 분모 몇으로** 쟀는지 말하지 않는다. "
                    "그 `exit 0` 은 「이 호출이 통과」일 뿐이다 · P-204)" % MEASURED_NONE)
    measured = _scrub(measured)

    print("%s %s%s" % (tag, KEY_TARGET, target), file=out)
    print("%s %s%s" % (tag, KEY_AS, as_ + (" · 사유: " + reason if reason else "")), file=out)
    print("%s %s%s" % (tag, KEY_SOURCE, source), file=out)
    print("%s %s%s" % (tag, KEY_MEASURED, measured), file=out)

    problems = judge_header(target, as_, source, reason) + judge_measured(measured)
    for why in problems:
        print("%s   ✗ 머리글: %s  ← %s" % (tag, why, name), file=out)
    _STATE["emitted"] = True
    _STATE["violations"] = list(problems)
    return len(problems)


def _scrub(text: str) -> str:
    """값처럼 생긴 긴 토큰은 **자른다** — 머리글이 자격을 새게 하지 않는다.

    ★ **이름과 경로는 자르지 않는다.** 한 번 넓게 쳤더니
      `DJANGO_SETTINGS_MODULE=config` 가 «값 가림» 이 됐고, 그 머리글은 읽을 수
      없었다 — 읽을 수 없는 머리글은 없는 머리글이다.
    """
    def _mask(m):
        return "«값 가림»" if _looks_like_value(m.group(0)) else m.group(0)
    return _SECRETISH.sub(_mask, str(text or "")).replace("\n", " ")


def header_violations() -> list[str]:
    return list(_STATE["violations"])


# ═══════════════════════════════════════════════════════════════════════════
# 셈 — 보유율 · 거짓 초록 패턴
# ═══════════════════════════════════════════════════════════════════════════
#: 이번 턴 **다른 차선이 들고 있는 파일**. 병합 때 조정자가 머리글을 붙인다.
#: 여기 적힌 것은 「없다」가 아니라 **「이 차선이 손대지 않기로 한 것」**이다.
OTHER_LANE = {
    "verify_read_auth.py": "보안 차선 (턴 M)",
    "probe_read_surface.py": "보안 차선 (턴 M)",
    "verify_front_line_502.py": "DevOps 차선 (턴 M)",
}
OTHER_LANE_GLOBS = ("ops_*.py",)


def gate_files(root: Path = None) -> list[Path]:
    base = (root or ROOT) / "scripts"
    return sorted(base.glob("verify_*.py"))


def has_header(text: str) -> bool:
    """그 파일이 머리글을 **부르는가**. 문자열로 흉내 낸 것은 세지 않는다."""
    return bool(re.search(r"gate_header\s*\(", text))


def audit(root: Path = None) -> dict:
    """게이트별 머리글 보유. **다른 차선 파일은 자기 칸으로 뺀다**(0건 아님 · D-301)."""
    rows, mine, carried, other = [], 0, 0, []
    for p in gate_files(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        if p.name in OTHER_LANE:
            other.append((p.name, OTHER_LANE[p.name], has_header(text)))
            continue
        mine += 1
        ok = has_header(text)
        carried += 1 if ok else 0
        rows.append((p.name, ok))
    return {"rows": rows, "mine": mine, "carried": carried, "other": other}


#: 턴 L 이 여덟 줄을 거짓 초록으로 만든 그 패턴 —
#:     python scripts/X.py 2>&1 | tail -18; echo "[exit=$?]"
#: `$?` 는 파이프의 **마지막 명령**(`tail`) 값이라 언제나 0 이다.
#: 그물은 넓게 친다: 파이프가 있는 줄 **뒤**에서 `$?` 를 읽는 자리를 본다.
_PIPE_LINE = re.compile(r"\|\s*(tail|head|grep|sed|awk|tee|less|cat|jq)\b")
_READS_RC = re.compile(r"\$\?")

#: **그물은 자기를 잡지 않는다.** 이 둘은 그 패턴을 글자 그대로 인용해야 하는 자리다 —
#: 인용을 위반으로 세면 규칙을 적어 둔 것이 규칙 위반이 된다.
SELF_REFERENCE = ("scripts/_gate_header.py", "scripts/verify_gate_header.py")


def pipe_scan(root: Path = None, exts=(".sh", ".bash", ".py", ".yaml", ".yml", ".md")) -> list:
    """`… | tail …; echo $?` 를 찾는다 — **거짓 초록을 만드는 그 한 줄.**

    ★ 왜 **같은 줄**만 보는가 (턴 M 에 한 번 넓게 쳐 봤다가 좁혔다)
      `$?` 는 **바로 앞 명령**의 값이다. 파이프 다음 **줄**에 있는 `echo "$?"` 는
      제 줄의 명령을 읽는 것이지 파이프를 읽는 것이 아니다 — 넓게 치면
      `WP-0/ENTRY.md:199` 처럼 **멀쩡한 줄**이 잡힌다. 좁혀도 턴 L 의 그 줄
      (`python X.py 2>&1 | tail -18; echo "[exit=$?]"`)은 **한 줄이라 잡힌다.**

    `PIPESTATUS`·`pipefail` 이 같은 줄에 있으면 **제대로 잡은 줄**이다.
    """
    base = root or ROOT
    hits = []
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
    for path in base.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        rel = str(path.relative_to(base)).replace("\\", "/")
        if rel in SELF_REFERENCE:
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # 줄 끝 `\` 이어짐은 한 줄로 본다 — 셸이 그렇게 읽는다
        lines = raw.replace("\\\n", " ").splitlines()
        md = path.suffix.lower() == ".md"
        fenced = False
        for i, line in enumerate(lines):
            if md and line.lstrip().startswith("```"):
                fenced = not fenced
            if not (_PIPE_LINE.search(line) and _READS_RC.search(line)):
                continue
            if "PIPESTATUS" in line or "pipefail" in line:
                continue
            #: ★ **인용은 위반이 아니다.** 턴 L 의 회고문이 자기 실수를 글자 그대로
            #:   적어 두었는데, 그 문장을 위반으로 세면 「적어 두지 마라」가 된다.
            #:   무디게 만드는 것이 아니다 — **돌지 않는 줄은 거짓 초록을 못 만든다.**
            #:   그래서 셋으로 가른다. 셋 다 **찍는다**(숨기지 않는다). 빨강이 되는 것은
            #:   **복사해 쓰는 자리**뿐이다:
            #:     코드        울타리 안 · 셸/파이썬의 도는 줄   ← 위반
            #:     주석(인용)  `#` 로 시작하는 줄               ← 안 돈다
            #:     인용(산문)  마크다운 울타리 밖               ← 안 돈다
            if line.lstrip().startswith("#"):
                kind = "주석(인용)"
            elif md and not fenced:
                kind = "인용(산문)"
            else:
                kind = "코드"
            hits.append((rel, i + 1, line.strip()[:150], kind))
    return hits


def pipe_violations(hits) -> list:
    """복사해 쓰는 자리에 남은 것만. **인용은 뺀다.**"""
    return [h for h in hits if h[3] == "코드"]


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-310)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    ok = True

    def check(label, cond):
        nonlocal ok
        if cond:
            print("%s O %s" % (TAG, label))
        else:
            ok = False
            print("%s X %s" % (TAG, label))

    check("성립한 머리글은 통과",
          not judge_header("http://localhost:8000 (gx-shell)",
                           "gxprobe_q · 역할 fire_user · 자격 이름 GX_PROBE_PASSWORD",
                           "살아 있는 라우터 (django get_resolver)"))
    check("빈 TARGET 은 빨강", judge_header("", "gxprobe_q", "살아 있는 라우터"))
    check("빈 AS 는 빨강", judge_header("t", "", "살아 있는 라우터"))
    check("빈 SOURCE 는 빨강", judge_header("t", "gxprobe_q", ""))
    # 출생 표본 ④ — 턴 L 의 verify_minio
    check("사유 없는 AS=root 는 빨강 (출생 표본 ④ · verify_minio)",
          judge_as("MINIO_ROOT_USER (호스트 .env)"))
    check("사유가 붙은 root 는 통과",
          not judge_as("MINIO_ROOT_USER (호스트 .env)", reason="저장소 자체의 생존만 잰다"))
    check("AS=admin 도 사유 없으면 빨강", judge_as("admin"))
    # 출생 표본 ① — 8월 사진을 읽던 verify_tenant_scope
    check("날짜 없는 파일 SOURCE 는 빨강 (출생 표본 ① · 8월 라우트 사진)",
          judge_source("파일 docs/agent/evidence/W0-14/openapi_routes.json"))
    check("날짜가 붙으면 통과",
          not judge_source("파일 docs/.../openapi_routes.json (기록 2026-08-27T10:00)"))
    _FAKE_VALUE = "Xk93mQ2vLp8Rt5Zw1Yb7Nc4Hd6Fs0Ga"   # 값처럼 생긴 것 (진짜 자격 아님)
    check("자격 값이 새면 빨강", judge_as("gxprobe_q / " + _FAKE_VALUE))
    check("값 가림이 실제로 자른다", "«값 가림»" in _scrub("token " + _FAKE_VALUE))
    check("환경변수 이름은 안 가린다",
          "DJANGO_SETTINGS_MODULE" in _scrub("DJANGO_SETTINGS_MODULE=config.settings"))
    check("경로는 안 가린다",
          "openapi_routes" in _scrub("파일 docs/agent/evidence/W0-14/openapi_routes.json"))
    check("사진의 날짜는 안 가린다",
          "2026-09-07T20:20:03" in _scrub("자기기록 captured_at=2026-09-07T20:20:03"))

    # 파일 도장 — 실재하는 파일에는 날짜가 붙고, 없는 파일은 **없다고** 말한다
    check("실재 파일에 날짜가 붙는다", "기록 " in file_stamp(Path(__file__)))
    check("없는 파일은 «없다» 로 적힌다",
          "**없다**" in file_stamp(ROOT / "이런파일은없다.json"))

    # 거짓 초록 패턴 — 그물이 그 줄을 실제로 잡는가
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "bad.sh").write_text('python x.py 2>&1 | tail -18; echo "[exit=$?]"\n',
                                  encoding="utf-8")
        (d / "good.sh").write_text('python x.py 2>&1 | tail -18; echo "${PIPESTATUS[0]}"\n',
                                   encoding="utf-8")
        (d / "plain.sh").write_text('python x.py; echo "$?"\n', encoding="utf-8")
        (d / "quoted.sh").write_text('#  python x.py | tail -5; echo "$?"\n',
                                     encoding="utf-8")
        found = pipe_scan(d)
        names = {h[0] for h in found if h[3] == "코드"}
        allnames = {h[0] for h in found}
        check("`| tail … $?` 를 잡는다 (턴 L 의 거짓 초록 8줄)", "bad.sh" in names)
        check("주석의 인용은 위반이 아니다 (그래도 **찍는다**)",
              "quoted.sh" not in names and "quoted.sh" in allnames)
        check("PIPESTATUS 로 잡은 줄은 안 잡는다", "good.sh" not in names)
        check("파이프 없는 줄은 안 잡는다", "plain.sh" not in names)

    # 아무것도 안 준 머리글이 **조용히 통과하지 않는다**
    check("관측 0건(빈 머리글 셋)은 세 줄 다 빨강", len(judge_header("", "", "")) >= 3)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="게이트 머리글 (P-107)")
    ap.add_argument("--audit", action="store_true", help="게이트 머리글 보유율")
    ap.add_argument("--pipe-scan", action="store_true", help="`| tail … $?` 패턴 훑기")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.audit:
        a = audit()
        print("%s 게이트 %d개 중 머리글 %d개" % (TAG, a["mine"], a["carried"]))
        for name, ok in a["rows"]:
            if not ok:
                print("    없음  %s" % name)
        for name, who, ok in a["other"]:
            print("    (다른 차선) %-32s %s · 머리글 %s" % (name, who, "있음" if ok else "없음"))
        return 0 if a["carried"] == a["mine"] else 1
    if args.pipe_scan:
        hits = pipe_scan()
        bad = pipe_violations(hits)
        print("%s `| tail … $?` 자리 %d건 (복사해 쓰는 자리 %d · 회고문 인용 %d)"
              % (TAG, len(hits), len(bad), len(hits) - len(bad)))
        for path, line, text, kind in hits:
            print("    [%s] %s:%d  %s" % (kind, path, line, text[:110]))
        return 0 if not bad else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
