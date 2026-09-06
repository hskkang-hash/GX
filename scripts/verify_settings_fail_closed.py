#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SEC-14 — **보안 설정의 기본값이 열린 쪽이면 안 된다** (2026-09-06 · 턴 G · 조율자).

무엇이 이 판정기를 만들게 했나 — **아무도 이 자리를 안 보고 있었다**
--------------------------------------------------------------------
[실측 2026-09-06 · 차선 V 가 떠 있는 서버의 `settings` 를 읽어 보고 · 조율자 재확인]

    backend/config/settings.py:28  SECRET_KEY = env(…, default="your-secret-key-here")
    backend/config/settings.py:31  DEBUG = env.bool("DJANGO_DEBUG", default=True)
    backend/config/settings.py:34  ALLOWED_HOSTS = ["*"]
    backend/config/settings.py:45  # CSRF_COOKIE_SECURE = (not DEBUG)      ← 주석
    backend/config/settings.py:47  # SESSION_COOKIE_SECURE = (not DEBUG)   ← 주석

넷 다 **아무 선언 없이 뜨면 가장 열린 쪽**으로 선다. 그리고 `scripts/`·`backend/tests/`
전수에서 이 넷을 보는 판정기가 **0건**이었다 — 상용 공개 URL 을 여는 순간
① 오류 화면이 트레이스백을 그대로 내고 ② 어떤 Host 머리글자든 받고 ③ **저장소에
적힌 서명 키**로 세션을 위조할 수 있고 ④ 쿠키가 평문 위로 흐른다.

★ 이것은 P-67 과 **같은 문장**이다 — 「보존 일수의 기본값은 없다. 선언만 있다」.
  보안 설정도 같다: **아무도 정하지 않았을 때 제품이 골라 주는 값이 위험한 값이면,
  그 제품은 잊어버린 사람을 벌한다.**

무엇을 재는가 — 다섯 수
-----------------------
    ① `SECRET_KEY` 에 **코드 기본값이 없다** — 선언이 없으면 뜨지 않아야 한다
    ② `DEBUG` 의 기본값이 **False** 다 — 켜는 것은 선언이어야 한다
    ③ `ALLOWED_HOSTS` 가 **`["*"]` 로 못 박혀 있지 않다** — 선언에서 읽는다
    ④ `CSRF_COOKIE_SECURE` · `SESSION_COOKIE_SECURE` 가 **주석이 아니라 실효 줄**이다
    ⑤ 이 판정기 자신이 **위 다섯을 실제로 잡는가**(자기시험 · 변이 표본)

★ **정적으로 읽는다 — 지금 뜬 서버를 묻지 않는다.** 떠 있는 프로세스는 개발 환경변수를
  물고 있어서 「지금은 안전하다」고 답할 수 있다. 우리가 묻는 것은
  **「아무 선언 없이 뜨면 무엇이 되는가」**이고, 그 답은 소스에만 있다.

⚠ 이 판정기는 **처음에 빨강으로 태어난다.** 그 빨강이 이 파일의 존재 이유다 —
  고치는 것과 재는 것은 다른 일이고, 재는 것이 먼저다(D-327: 칸을 채우려고
  초록을 만들지 않는다).

    python scripts/verify_settings_fail_closed.py
    python scripts/verify_settings_fail_closed.py --self-test    # 판정 규칙만

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(파일 없음)
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "backend" / "config" / "settings.py"
TAG = "[SEC-14]"

#: `SECRET_KEY` 기본값으로 절대 서면 안 되는 것 — **저장소에 적힌 서명 키**.
#: 목록이 아니라 술어다: 「기본값이 **있다**」가 곧 실패다. 이 목록은 사유 표기용.
KNOWN_PLACEHOLDERS = ("your-secret-key-here", "changeme", "secret", "django-insecure")


def _name(node) -> str:
    """대입 왼쪽의 이름. 튜플 대입·속성 대입은 우리 관심 밖이라 빈 문자열."""
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _call_default(node):
    """`env(...)` · `env.bool(...)` 의 `default=` 값.

    ★ **「기본값이 None 이다」와 「기본값 인자가 없다」를 가른다** — 앞엣것은
      선언이고 뒤엣것은 부재다. 그래서 `(있는가, 값)` 두 칸으로 답한다.
    """
    if not isinstance(node, ast.Call):
        return False, None
    for kw in node.keywords:
        if kw.arg == "default":
            try:
                return True, ast.literal_eval(kw.value)
            except (ValueError, SyntaxError):
                return True, "<계산식>"
    return False, None


def judge(source: str) -> list:
    """소스 한 벌을 보고 **(이름, 통과, 사유)** 다섯 줄을 낸다. **순수 함수다.**"""
    tree = ast.parse(source)
    assigns = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            key = _name(node.targets[0])
            if key and key not in assigns:      # 첫 대입이 기본값이다
                assigns[key] = node.value

    out = []

    # ① SECRET_KEY — 코드 기본값이 있으면 그 값이 곧 저장소에 적힌 서명 키다
    node = assigns.get("SECRET_KEY")
    if node is None:
        out.append(("SECRET_KEY", False, "선언 자체가 없다"))
    elif isinstance(node, ast.Constant):
        out.append(("SECRET_KEY", False,
                    "리터럴이 그대로 박혀 있다 — 저장소가 서명 키를 나른다"))
    else:
        has_default, value = _call_default(node)
        if has_default:
            hint = " (알려진 자리표)" if any(
                p in str(value) for p in KNOWN_PLACEHOLDERS) else ""
            out.append(("SECRET_KEY", False,
                        "코드 기본값 %r%s — 선언이 없으면 **뜨지 않아야** 한다"
                        % (value, hint)))
        else:
            out.append(("SECRET_KEY", True, "기본값 없음 — 선언에서만 온다"))

    # ② DEBUG — 켜는 것이 선언이어야 한다
    node = assigns.get("DEBUG")
    if node is None:
        out.append(("DEBUG", False, "선언 자체가 없다"))
    elif isinstance(node, ast.Constant):
        out.append(("DEBUG", node.value is False,
                    "리터럴 %r%s" % (node.value,
                                    "" if node.value is False
                                    else " — 상용에서 트레이스백이 나간다")))
    else:
        has_default, value = _call_default(node)
        if not has_default:
            out.append(("DEBUG", True, "기본값 없음 — 선언에서만 온다"))
        else:
            out.append(("DEBUG", value is False,
                        "기본값 %r%s" % (value, "" if value is False
                                        else " — 잊으면 켜진다")))

    # ③ ALLOWED_HOSTS — 아무 Host 머리글자나 받으면 안 된다
    node = assigns.get("ALLOWED_HOSTS")
    if node is None:
        out.append(("ALLOWED_HOSTS", False, "선언 자체가 없다"))
    elif isinstance(node, (ast.List, ast.Tuple)):
        items = [getattr(e, "value", None) for e in node.elts]
        out.append(("ALLOWED_HOSTS", "*" not in items,
                    "리터럴 %r%s" % (items,
                                    " — 어떤 Host 든 받는다" if "*" in items else "")))
    else:
        has_default, value = _call_default(node)
        if has_default and "*" in str(value):
            out.append(("ALLOWED_HOSTS", False,
                        "기본값 %r — 어떤 Host 든 받는다" % (value,)))
        else:
            out.append(("ALLOWED_HOSTS", True, "선언에서 읽는다"))

    # ④ 쿠키 둘 — **주석은 선언이 아니다**
    for key in ("CSRF_COOKIE_SECURE", "SESSION_COOKIE_SECURE"):
        if key not in assigns:
            out.append((key, False,
                        "실효 줄이 없다 — 주석으로 적힌 것은 **적히지 않은 것**이다"))
        else:
            node = assigns[key]
            if isinstance(node, ast.Constant) and node.value is False:
                out.append((key, False, "리터럴 False — 쿠키가 평문 위로 흐른다"))
            else:
                out.append((key, True, "실효 줄이 있다"))
    return out


#: 자기시험 표본. **다섯 수마다 하나씩** — 「고쳐진 소스」에서 그 줄만 되돌린다.
_SAFE = """
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
"""

#: ★ **출생 표본** — 이 도구를 만들게 한 **바로 그 다섯 줄** (2026-09-06 · `settings.py`).
#: 변이는 「이 규칙이 무엇을 잡아야 하는가」를 시험하고, 이 표본은 **「그날 무엇이 있었는가」**
#: 를 시험한다. 둘은 다른 질문이다 — 소스가 고쳐진 뒤에도 이 표본은 그날을 기억한다.
BIRTH_SAMPLE = """
SECRET_KEY = env("DJANGO_SECRET_KEY", default="your-secret-key-here")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["*"]
# CSRF_COOKIE_SECURE = (not DEBUG)
# SESSION_COOKIE_SECURE = (not DEBUG)
"""

_MUTANTS = {
    "SECRET_KEY": _SAFE.replace(
        'SECRET_KEY = env("DJANGO_SECRET_KEY")',
        'SECRET_KEY = env("DJANGO_SECRET_KEY", default="your-secret-key-here")'),
    "DEBUG": _SAFE.replace("default=False", "default=True"),
    "ALLOWED_HOSTS": _SAFE.replace(
        'ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])',
        'ALLOWED_HOSTS = ["*"]'),
    "CSRF_COOKIE_SECURE": _SAFE.replace("CSRF_COOKIE_SECURE = not DEBUG",
                                        "# CSRF_COOKIE_SECURE = not DEBUG"),
    "SESSION_COOKIE_SECURE": _SAFE.replace("SESSION_COOKIE_SECURE = not DEBUG",
                                           "SESSION_COOKIE_SECURE = False"),
}


def self_test() -> int:
    """판정 규칙만 시험한다 — 파일도 Django 도 없이 (D-277)."""
    ok = True
    rows = judge(_SAFE)
    if not all(passed for _, passed, _ in rows):
        ok = False
        print("%s X 안전한 소스를 빨강으로 읽는다: %s"
              % (TAG, [n for n, p, _ in rows if not p]))
    else:
        print("%s O 안전한 소스 5/5 초록 (양성 대조)" % TAG)

    caught = 0
    for name, source in _MUTANTS.items():
        verdicts = dict((n, p) for n, p, _ in judge(source))
        if verdicts.get(name) is False:
            caught += 1
        else:
            ok = False
            print("%s X 변이 「%s」를 못 잡는다 — 이 수는 시험된 적이 없다" % (TAG, name))
    print("%s O 변이 %d/%d 를 잡는다 (음성 대조)" % (TAG, caught, len(_MUTANTS)))

    # ★ 출생 표본 — 그날의 다섯 줄을 **다섯 다** 잡아야 한다
    born = judge(BIRTH_SAMPLE)
    if any(passed for _, passed, _ in born):
        ok = False
        print("%s X 출생 표본을 다 못 잡는다: %s — 이 도구가 태어난 사유가 안 재진다"
              % (TAG, [n for n, p, _ in born if p]))
    else:
        print("%s O 출생 표본 5/5 빨강 — 2026-09-06 의 settings.py 를 그대로 잡는다" % TAG)

    # 빈 소스는 **초록이 아니라 빨강**이다 — 「선언이 없다」는 안전이 아니다
    if any(p for _, p, _ in judge("")):
        ok = False
        print("%s X 빈 소스를 초록으로 읽는다 — 0건 통과는 통과가 아니다" % TAG)
    else:
        print("%s O 빈 소스는 다섯 다 빨강 (0건이 초록이 되지 않는다)" % TAG)
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser(description="보안 설정 기본값이 닫힌 쪽인가 (SEC-14)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--path", default=str(SETTINGS))
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 빨강이다 — 판정을 신뢰할 수 없다" % TAG)
        return rc

    path = Path(args.path)
    if not path.exists():
        print("%s ? 못 쟀다 — %s 가 없다" % (TAG, path))
        return EXIT_UNDECIDABLE

    rows = judge(path.read_text(encoding="utf-8"))
    failed = [(n, why) for n, passed, why in rows if not passed]
    print("%s [입력] %s · 수 %d" % (TAG, path.name, len(rows)))
    for name, passed, why in rows:
        print("  %s  %-22s %s" % ("O" if passed else "X", name, why))
    if failed:
        print("%s 실패 %d/%d — **아무 선언 없이 뜨면 이 넷이 가장 열린 쪽으로 선다**"
              % (TAG, len(failed), len(rows)))
        print("%s ⚠ 지금 뜬 서버가 안전한 것과 이 수는 다른 사실이다 — "
              "이 판정기는 소스만 읽는다" % TAG)
        return EXIT_FAIL
    print("%s 통과 — 선언이 없으면 닫힌 쪽으로 선다" % TAG)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
