#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SEC-18 · P-75 — **운영 프로필로 뜨면 닫혀 있는가** (2026-09-06 · 턴 H · 차선 S).

이 판정기는 `verify_settings_fail_closed.py` 와 **다른 질문을 잰다**
---------------------------------------------------------------
    verify_settings_fail_closed.py :  「**아무 선언 없이** 개발 소스가 뜨면 무엇이 되는가」
                                      → 소스를 **정적으로** 읽는다. 지금 5/5 빨강이고 그것이 옳다.
    verify_prod_settings.py (이 파일):  「**운영 프로필로 실제로 뜨면** 닫혀 있는가」
                                      → 파이썬을 **실제로 띄워서** 그 결과를 읽는다.

둘 다 필요하다. 앞엣것이 초록이 되는 것은 재기동 창 **뒤**의 일이고(코드의 열린 기본값
제거), 뒷엣것은 **그 전에** 초록이어야 한다 — 공개 URL 은 이 게이트 없이 열지 않는다.

무엇이 이 판정기를 만들게 했나 — **출생 표본**
----------------------------------------------
[실측 2026-09-06 · 턴 G · 차선 V 가 떠 있는 서버의 `settings` 를 읽어 보고]

    backend/config/settings.py:28  SECRET_KEY = env(…, default="your-secret-key-here")
    backend/config/settings.py:31  DEBUG = env.bool("DJANGO_DEBUG", default=True)
    backend/config/settings.py:34  ALLOWED_HOSTS = ["*"]
    backend/config/settings.py:45  # CSRF_COOKIE_SECURE = (not DEBUG)      ← 주석
    backend/config/settings.py:47  # SESSION_COOKIE_SECURE = (not DEBUG)   ← 주석

그날의 이 다섯 줄이 아래 `BIRTH_SAMPLE` 이다. 이 표본을 **관측으로 옮겨 놓고** 판정하면
다섯 수가 전부 빨강이어야 한다. 거기서 초록이 나오면 이 파일은 도구가 아니다(D-310).

무엇을 재는가 — 다섯 수 · **각각 음성 대조를 실제로 돌린다**
-----------------------------------------------------------
    ① SECRET_KEY   선언이 없으면 **기동 거부** · 자리표여도 거부 · 50자 이상
                   음성 대조: `no_secret` · `placeholder_secret` 두 번을 **띄워 본다**
    ② DEBUG        `False` 고정 — `DJANGO_DEBUG=true` 를 줘도 켜지지 않는다
                   음성 대조: `debug_on` 을 띄워서 그래도 False 인지 본다
    ③ ALLOWED_HOSTS 선언 필수 · `*` 거부
                   음성 대조: `no_hosts` · `star_hosts`
    ④ 쿠키 여섯    Secure 2 · HttpOnly 2 · SameSite=Lax 2
                   대조: **개발 프로필로 같은 자리를 재서** 무엇이 다른지 나란히 적는다
    ⑤ 공개 출처·TLS `CSRF_TRUSTED_ORIGINS` 선언 필수(스킴) · HSTS · 프록시 머리글자
                   음성 대조: `no_origins` · `origins_no_scheme`

★ **띄워 본 것만 센다.** 「settings_prod 를 읽어 보니 그렇게 적혀 있더라」는 이 판정기의
  답이 아니다 — 적힌 것과 뜬 것은 다른 사실이고, 우리를 물었던 것은 늘 뒤엣것이다.

    python scripts/verify_prod_settings.py             # 판정 (9번 띄운다)
    python scripts/verify_prod_settings.py --self-test # 판정 규칙만 (파이썬 기동 없이)
    python scripts/verify_prod_settings.py --list      # 관측만 찍어 본다

⚠ **판은 컨테이너 안에서 뜬다.** 호스트에는 `celery`·dj-core 가 없어 `config` 를 못 읽는다
  [실측 2026-09-06]. 그래서 호스트에서 부르면 **스스로 `gx-shell` 에 위임한다**:
    python scripts/verify_prod_settings.py                          # 호스트 → 위임 → 판정
    docker exec gx-shell python /repo/scripts/verify_prod_settings.py   # 안에서 직접
  위임까지 안 되면 **회색(exit 2)** 이다. 회색은 통과가 아니다(D-301).
  `--no-delegate` 는 위임을 끈다(컨테이너 안에서 도는 판이 쓴다).

종료 코드: 0 쟀고 5/5 · 1 쟀고 실패 · 2 **못 쟀다**(파이썬·Django·프로필 부재)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2
TAG = "[SEC-18]"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent

#: 선언 이름은 **새로 짓지 않는다** — `.env.example` 의 「운영 프로필 선언」 절 그대로.
NAME_SECRET = "DJANGO_SECRET_KEY"
NAME_DEBUG = "DJANGO_DEBUG"
NAME_HOSTS = "DJANGO_ALLOWED_HOSTS"
NAME_ORIGINS = "DJANGO_CSRF_TRUSTED_ORIGINS"

PROD_MODULE = "config.settings_prod"
DEV_MODULE = "config.settings"

#: 판정용 선언 한 벌. **이 값들은 어디에도 저장되지 않는다** — 자식 프로세스 환경에만 산다.
GOOD_SECRET = "gx-verify-" + ("z9Qm4Ld7Rt2Xv6Bn1Cw8Hj3Kp5Sy0Fa" * 3)   # 50자 이상 · 자리표 아님
GOOD_HOSTS = "stg.guardianx.example.kr,guardianx.example.kr"
GOOD_ORIGINS = "https://stg.guardianx.example.kr,https://guardianx.example.kr"

#: 자식 파이썬이 돌릴 탐침. **앱 레지스트리를 세우지 않는다** — 우리가 묻는 것은 설정이고,
#: `django.setup()` 은 MinIO 같은 곁길을 두드려 판정과 무관한 소음·지연을 만든다.
PROBE = r"""
import json
from django.conf import settings as s
print("GXPROD " + json.dumps({
    "profile": getattr(s, "SECURITY_PROFILE", "dev"),
    "DEBUG": s.DEBUG,
    "ALLOWED_HOSTS": list(s.ALLOWED_HOSTS),
    "SESSION_COOKIE_SECURE": getattr(s, "SESSION_COOKIE_SECURE", None),
    "CSRF_COOKIE_SECURE": getattr(s, "CSRF_COOKIE_SECURE", None),
    "SESSION_COOKIE_HTTPONLY": getattr(s, "SESSION_COOKIE_HTTPONLY", None),
    "CSRF_COOKIE_HTTPONLY": getattr(s, "CSRF_COOKIE_HTTPONLY", None),
    "SESSION_COOKIE_SAMESITE": getattr(s, "SESSION_COOKIE_SAMESITE", None),
    "CSRF_COOKIE_SAMESITE": getattr(s, "CSRF_COOKIE_SAMESITE", None),
    "CSRF_TRUSTED_ORIGINS": list(getattr(s, "CSRF_TRUSTED_ORIGINS", [])),
    "SECURE_HSTS_SECONDS": getattr(s, "SECURE_HSTS_SECONDS", 0),
    "SECURE_PROXY_SSL_HEADER": list(getattr(s, "SECURE_PROXY_SSL_HEADER", []) or []),
    "SECRET_KEY_LEN": len(s.SECRET_KEY or ""),
    "SECRET_KEY_IS_PLACEHOLDER": "your-secret-key-here" in (s.SECRET_KEY or ""),
}, ensure_ascii=False))
"""

#: 아홉 번 띄운다. `(설정모듈, 그 판에서 **선언한 것만**)`.
#: ★ 선언하지 않은 이름은 자식 환경에서 **지운다** — 지금 컨테이너에 실려 있는 개발
#:   `DJANGO_SECRET_KEY` 가 새어 들어오면 「없어도 뜬다」가 초록으로 보인다.
CASES = {
    "full": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: GOOD_HOSTS,
                           NAME_ORIGINS: GOOD_ORIGINS}),
    "no_secret": (PROD_MODULE, {NAME_HOSTS: GOOD_HOSTS, NAME_ORIGINS: GOOD_ORIGINS}),
    "placeholder_secret": (PROD_MODULE, {NAME_SECRET: "your-secret-key-here",
                                         NAME_HOSTS: GOOD_HOSTS, NAME_ORIGINS: GOOD_ORIGINS}),
    "debug_on": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: GOOD_HOSTS,
                               NAME_ORIGINS: GOOD_ORIGINS, NAME_DEBUG: "true"}),
    "no_hosts": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_ORIGINS: GOOD_ORIGINS}),
    "star_hosts": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: "*",
                                 NAME_ORIGINS: GOOD_ORIGINS}),
    "no_origins": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: GOOD_HOSTS}),
    "origins_no_scheme": (PROD_MODULE, {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: GOOD_HOSTS,
                                        NAME_ORIGINS: "guardianx.example.kr"}),
    # 대조 — **개발 프로필**은 같은 자리에서 무엇을 하는가. 판정의 조건이 아니라 증거다
    # (코드의 열린 기본값이 재기동 뒤에 사라지면 이 줄의 내용이 바뀐다. 그래도 ④는 산다).
    "dev_profile": (DEV_MODULE, {}),
}


# ═════════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수다** (D-277). 관측(뜬 결과) 만 먹고 다섯 줄을 낸다
# ═════════════════════════════════════════════════════════════════════════════
def _obs(observations: dict, name: str) -> dict:
    return observations.get(name) or {}


def _refused(observations: dict, name: str) -> bool:
    """그 판이 **기동을 거부**했는가 — 거부는 우리 이름표가 붙은 거부여야 한다."""
    o = _obs(observations, name)
    return bool(o.get("refused"))


def _booted(observations: dict, name: str) -> dict:
    """뜬 판의 설정 한 벌. 못 떴으면 빈 사전."""
    o = _obs(observations, name)
    return o.get("settings") or {}


def judge(observations: dict) -> list:
    """관측 → **(수 이름, 통과, 사유)** 다섯 줄."""
    out = []
    full = _booted(observations, "full")

    # ① SECRET_KEY — 없으면 뜨지 않는다 · 자리표도 거부
    if not full:
        out.append(("SECRET_KEY", False,
                    "선언을 다 주었는데도 운영 프로필이 안 떴다 — 프로필이 못 쓰는 상태다"))
    else:
        no_secret = _refused(observations, "no_secret")
        placeholder = _refused(observations, "placeholder_secret")
        length = full.get("SECRET_KEY_LEN", 0)
        ok = no_secret and placeholder and length >= 50 and not full.get("SECRET_KEY_IS_PLACEHOLDER")
        why = ("선언 없음→거부 %s · 자리표→거부 %s · 길이 %d"
               % ("O" if no_secret else "**X 떴다**",
                  "O" if placeholder else "**X 떴다**", length))
        out.append(("SECRET_KEY", ok, why))

    # ② DEBUG — False 고정. 선언으로도 못 켠다
    debug_on = _booted(observations, "debug_on")
    if not full or not debug_on:
        out.append(("DEBUG", False, "재지 못했다 — 판이 안 떴다"))
    else:
        ok = full.get("DEBUG") is False and debug_on.get("DEBUG") is False
        out.append(("DEBUG", ok,
                    "기본 %r · DJANGO_DEBUG=true 를 줘도 %r%s"
                    % (full.get("DEBUG"), debug_on.get("DEBUG"),
                       "" if ok else " — **환경변수로 켜진다**")))

    # ③ ALLOWED_HOSTS — 선언 필수 · `*` 거부
    if not full:
        out.append(("ALLOWED_HOSTS", False, "재지 못했다 — 판이 안 떴다"))
    else:
        hosts = full.get("ALLOWED_HOSTS") or []
        no_hosts = _refused(observations, "no_hosts")
        star = _refused(observations, "star_hosts")
        ok = bool(hosts) and not any("*" in h for h in hosts) and no_hosts and star
        out.append(("ALLOWED_HOSTS", ok,
                    "선언대로 %r · 선언 없음→거부 %s · `*`→거부 %s"
                    % (hosts, "O" if no_hosts else "**X 떴다**",
                       "O" if star else "**X 떴다**")))

    # ④ 쿠키 여섯 — Secure 2 · HttpOnly 2 · SameSite=Lax 2
    if not full:
        out.append(("COOKIES", False, "재지 못했다 — 판이 안 떴다"))
    else:
        want = {
            "SESSION_COOKIE_SECURE": True, "CSRF_COOKIE_SECURE": True,
            "SESSION_COOKIE_HTTPONLY": True, "CSRF_COOKIE_HTTPONLY": True,
            "SESSION_COOKIE_SAMESITE": "Lax", "CSRF_COOKIE_SAMESITE": "Lax",
        }
        bad = [k for k, v in want.items() if full.get(k) != v]
        dev = _booted(observations, "dev_profile")
        dev_open = [k for k, v in want.items() if dev and dev.get(k) != v]
        contrast = ("개발 프로필 대조: %d/6 이 열려 있다 %s" % (len(dev_open), dev_open)
                    if dev else "개발 프로필 대조를 못 했다")
        out.append(("COOKIES", not bad,
                    ("여섯 다 닫혔다 · %s" % contrast) if not bad
                    else "열린 자리 %r · %s" % (bad, contrast)))

    # ⑤ 공개 출처 · TLS 뒤 배선
    if not full:
        out.append(("ORIGINS_TLS", False, "재지 못했다 — 판이 안 떴다"))
    else:
        origins = full.get("CSRF_TRUSTED_ORIGINS") or []
        no_origins = _refused(observations, "no_origins")
        no_scheme = _refused(observations, "origins_no_scheme")
        hsts = full.get("SECURE_HSTS_SECONDS") or 0
        proxy = full.get("SECURE_PROXY_SSL_HEADER") or []
        ok = (bool(origins)
              and all(o.startswith("https://") or o.startswith("http://") for o in origins)
              and no_origins and no_scheme and hsts > 0 and len(proxy) == 2)
        out.append(("ORIGINS_TLS", ok,
                    "출처 %d개 · 선언 없음→거부 %s · 스킴 없음→거부 %s · HSTS %ds · 프록시 %r"
                    % (len(origins), "O" if no_origins else "**X 떴다**",
                       "O" if no_scheme else "**X 떴다**", hsts, proxy)))
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 자기시험 — **파이썬을 띄우지 않고** 판정 규칙만 (D-277)
# ═════════════════════════════════════════════════════════════════════════════
_CLOSED_SETTINGS = {
    "profile": "prod", "DEBUG": False,
    "ALLOWED_HOSTS": ["stg.guardianx.example.kr"],
    "SESSION_COOKIE_SECURE": True, "CSRF_COOKIE_SECURE": True,
    "SESSION_COOKIE_HTTPONLY": True, "CSRF_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax", "CSRF_COOKIE_SAMESITE": "Lax",
    "CSRF_TRUSTED_ORIGINS": ["https://stg.guardianx.example.kr"],
    "SECURE_HSTS_SECONDS": 31536000,
    "SECURE_PROXY_SSL_HEADER": ["HTTP_X_FORWARDED_PROTO", "https"],
    "SECRET_KEY_LEN": 86, "SECRET_KEY_IS_PLACEHOLDER": False,
}


def _closed_observations() -> dict:
    """**닫힌 쪽**이 다 성립한 관측 — 양성 대조."""
    o = {"full": {"refused": False, "settings": dict(_CLOSED_SETTINGS)},
         "debug_on": {"refused": False, "settings": dict(_CLOSED_SETTINGS)},
         "dev_profile": {"refused": False, "settings": {
             "profile": "dev", "DEBUG": True, "ALLOWED_HOSTS": ["*"],
             "SESSION_COOKIE_SECURE": False, "CSRF_COOKIE_SECURE": False,
             "SESSION_COOKIE_HTTPONLY": True, "CSRF_COOKIE_HTTPONLY": False,
             "SESSION_COOKIE_SAMESITE": "Lax", "CSRF_COOKIE_SAMESITE": "Lax",
             "CSRF_TRUSTED_ORIGINS": ["http://localhost:8000"],
             "SECURE_HSTS_SECONDS": 0, "SECURE_PROXY_SSL_HEADER": [],
             "SECRET_KEY_LEN": 33, "SECRET_KEY_IS_PLACEHOLDER": False}}}
    for name in ("no_secret", "placeholder_secret", "no_hosts", "star_hosts",
                 "no_origins", "origins_no_scheme"):
        o[name] = {"refused": True, "settings": None}
    return o


#: ★ **출생 표본** — 이 도구를 만들게 한 **바로 그 다섯 줄**(2026-09-06 · `settings.py`)을
#: 관측의 말로 옮긴 것이다. 그날 이 저장소를 「운영 프로필」이라 부르며 띄웠다면 무엇이
#: 관측됐을까: **아무 선언 없이도 떴고**(거부 0건) · DEBUG 켜졌고 · Host 무제한 ·
#: 쿠키는 주석이라 없고 · 출처는 localhost 기본값이었다. 다섯 다 빨강이어야 한다.
def _birth_sample_observations() -> dict:
    born = {
        "profile": "dev", "DEBUG": True, "ALLOWED_HOSTS": ["*"],
        "SESSION_COOKIE_SECURE": None, "CSRF_COOKIE_SECURE": None,
        "SESSION_COOKIE_HTTPONLY": True, "CSRF_COOKIE_HTTPONLY": False,
        "SESSION_COOKIE_SAMESITE": None, "CSRF_COOKIE_SAMESITE": None,
        "CSRF_TRUSTED_ORIGINS": ["http://localhost:8000", "http://127.0.0.1:8000"],
        "SECURE_HSTS_SECONDS": 0, "SECURE_PROXY_SSL_HEADER": [],
        "SECRET_KEY_LEN": len("your-secret-key-here"), "SECRET_KEY_IS_PLACEHOLDER": True,
    }
    o = {}
    for name in CASES:
        # **그날은 무엇을 빼도 떴다** — 거부라는 것이 없었다. 그것이 사고의 모양이다.
        o[name] = {"refused": False, "settings": dict(born)}
    return o


BIRTH_SAMPLE = _birth_sample_observations  # 검색으로 찾을 이름 (출생 표본 · D-310)


def self_test() -> int:
    ok = True

    rows = judge(_closed_observations())
    if not all(passed for _, passed, _ in rows):
        ok = False
        print("%s X 닫힌 관측을 빨강으로 읽는다: %s"
              % (TAG, [n for n, p, _ in rows if not p]))
    else:
        print("%s O 닫힌 관측 5/5 초록 (양성 대조)" % TAG)

    # 변이 — 다섯 수마다 하나씩. **그 수만** 빨개져야 한다
    mutants = {}
    m = _closed_observations(); m["no_secret"] = {"refused": False, "settings": dict(_CLOSED_SETTINGS)}
    mutants["SECRET_KEY"] = ("선언 없이도 떴다", m)
    m = _closed_observations(); m["debug_on"]["settings"] = dict(_CLOSED_SETTINGS, DEBUG=True)
    mutants["DEBUG"] = ("DJANGO_DEBUG=true 로 켜졌다", m)
    m = _closed_observations(); m["star_hosts"] = {"refused": False, "settings": dict(_CLOSED_SETTINGS)}
    mutants["ALLOWED_HOSTS"] = ("`*` 를 주었는데 떴다", m)
    m = _closed_observations(); m["full"]["settings"] = dict(_CLOSED_SETTINGS, CSRF_COOKIE_SECURE=False)
    mutants["COOKIES"] = ("CSRF 쿠키가 평문 위로 흐른다", m)
    m = _closed_observations(); m["origins_no_scheme"] = {"refused": False, "settings": dict(_CLOSED_SETTINGS)}
    mutants["ORIGINS_TLS"] = ("스킴 없는 출처를 받아들이고 떴다", m)

    caught = 0
    for name, (label, obs) in mutants.items():
        verdicts = dict((n, p) for n, p, _ in judge(obs))
        if verdicts.get(name) is False:
            caught += 1
        else:
            ok = False
            print("%s X 변이 「%s — %s」를 못 잡는다" % (TAG, name, label))
    print("%s O 변이 %d/%d 를 잡는다 (음성 대조 · 규칙)" % (TAG, caught, len(mutants)))

    # ★ 출생 표본 — 2026-09-06 의 그 다섯 줄. **다섯 다** 빨강이어야 한다
    born = judge(BIRTH_SAMPLE())
    if any(passed for _, passed, _ in born):
        ok = False
        print("%s X 출생 표본을 다 못 잡는다: %s — 이 도구가 태어난 사유가 안 재진다"
              % (TAG, [n for n, p, _ in born if p]))
    else:
        print("%s O 출생 표본 5/5 빨강 — 2026-09-06 의 settings.py 를 그대로 잡는다" % TAG)

    # 관측 0건은 **초록이 아니다** (D-301)
    if any(p for _, p, _ in judge({})):
        ok = False
        print("%s X 관측 0건을 초록으로 읽는다 — 못 잰 것이 통과가 되지 않는다" % TAG)
    else:
        print("%s O 관측 0건은 다섯 다 빨강 (회색이 초록이 되지 않는다)" % TAG)
    return EXIT_OK if ok else EXIT_FAIL


# ═════════════════════════════════════════════════════════════════════════════
# 관측 — **실제로 아홉 번 띄운다**
# ═════════════════════════════════════════════════════════════════════════════
class Undecidable(Exception):
    """못 쟀다 — 회색(exit 2). 실패와 구별한다."""


def _backend_dir(explicit: str = "") -> Path:
    """`config/settings_prod.py` 가 실재하는 자리. 컨테이너의 `/app` 이 먼저다."""
    for cand in ([Path(explicit)] if explicit else []) + [Path("/app"), ROOT / "backend"]:
        try:
            if (cand / "config" / "settings_prod.py").is_file():
                return cand
        except OSError:
            continue
    raise Undecidable("config/settings_prod.py 를 못 찾았다 (본 자리: %s · /app · %s)"
                      % (explicit or "-", ROOT / "backend"))


def _child_env(module: str, declared: dict) -> dict:
    """자식 환경 — **선언하지 않은 `DJANGO_*` 이름은 지운다.**

    ★ 이 한 줄이 이 판정기의 정직성이다. 지금 컨테이너에는 개발용
      `DJANGO_SECRET_KEY` 가 실려 있고, 그것을 지우지 않으면 「선언이 없어도 거부하는가」
      라는 물음이 **선언이 있는 채로** 던져진다 — 초록이 거짓이 된다.
    """
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("DJANGO_"):
            del env[key]
    env["DJANGO_SETTINGS_MODULE"] = module
    env.update(declared)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def observe(backend: Path, python: str, timeout: int = 180) -> dict:
    """아홉 판을 띄우고 **(거부했나 · 떴다면 무엇으로 떴나)** 를 모은다."""
    out = {}
    for name, (module, declared) in CASES.items():
        try:
            proc = subprocess.run(
                [python, "-c", PROBE], cwd=str(backend), env=_child_env(module, declared),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except FileNotFoundError as exc:
            raise Undecidable("파이썬을 못 불렀다: %s" % exc)
        except subprocess.TimeoutExpired:
            raise Undecidable("판 「%s」이 %d초 안에 안 끝났다" % (name, timeout))

        stdout = proc.stdout.decode("utf-8", "replace")
        stderr = proc.stderr.decode("utf-8", "replace")
        line = next((l for l in stdout.splitlines() if l.startswith("GXPROD ")), "")

        if proc.returncode == 0 and line:
            out[name] = {"refused": False, "settings": json.loads(line[len("GXPROD "):])}
            continue
        if "ImproperlyConfigured" in stderr and TAG in stderr:
            reason = next((l.strip() for l in stderr.splitlines()
                           if l.strip().startswith("· ")), "")
            out[name] = {"refused": True, "settings": None, "reason": reason}
            continue
        # ★ 우리 이름표가 없는 실패는 **거부가 아니라 못 잰 것**이다 —
        #   ImportError 를 「잘 막았다」로 세면 그것이 거짓 초록이다.
        raise Undecidable("판 「%s」이 우리 거부가 아닌 이유로 죽었다(rc=%d):\n%s"
                          % (name, proc.returncode, (stderr or stdout)[-800:]))
    return out


def _delegate(container: str):
    """컨테이너에 그대로 위임한다. 위임조차 못 하면 `None`(=회색)."""
    cmd = ["docker", "exec", container, "python",
           "/repo/scripts/verify_prod_settings.py", "--no-delegate"]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    except (OSError, subprocess.SubprocessError) as exc:
        print("%s   위임 실패: %s" % (TAG, exc))
        return None
    out = proc.stdout.decode("utf-8", "replace")
    print(out.rstrip())
    # 도커가 명령 자체를 못 돌린 것(125·126·127)은 **판정이 아니라 회색**이다
    if proc.returncode in (125, 126, 127) or "/repo/scripts" in out and "No such file" in out:
        return None
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="운영 프로필로 뜨면 닫혀 있는가 (SEC-18 · P-75)")
    ap.add_argument("--self-test", action="store_true", help="판정 규칙만 (기동 없이)")
    ap.add_argument("--list", action="store_true", help="관측만 찍는다")
    ap.add_argument("--backend", default="", help="backend 디렉터리(기본: /app 또는 ./backend)")
    ap.add_argument("--python", default=sys.executable or "python")
    ap.add_argument("--no-delegate", action="store_true",
                    help="컨테이너 위임을 하지 않는다(컨테이너 안에서 도는 판이 쓴다)")
    ap.add_argument("--container", default=os.environ.get("GX_SHELL_CONTAINER", "gx-shell"))
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 빨강이다 — 판정을 신뢰할 수 없다" % TAG)
        return rc

    try:
        backend = _backend_dir(args.backend)
        print("%s [입력] %s · 판 %d개를 **실제로 띄운다**" % (TAG, backend, len(CASES)))
        observations = observe(backend, args.python)
    except Undecidable as exc:
        # ★ **호스트에서는 못 뜬다** — Django 는 있어도 `celery`·dj-core 가 없다
        #   [실측 2026-09-06]. 회색은 통과가 아니지만, **되는 방법이 있는데 회색으로
        #   끝내는 것**도 답이 아니다. 저장소 관례대로 `gx-shell` 에 위임한다.
        print("%s 이 자리에서는 못 띄웠다 — %s" % (TAG, str(exc).splitlines()[0]))
        if not args.no_delegate and not args.backend:
            print("%s → %s 에 위임한다 (호스트에는 dj-core·celery 가 없다)"
                  % (TAG, args.container))
            rc = _delegate(args.container)
            if rc is not None:
                return rc
        print("%s ? **못 쟀다** — 컨테이너에서 돌린다: docker exec %s python "
              "/repo/scripts/verify_prod_settings.py" % (TAG, args.container))
        return EXIT_UNDECIDABLE

    for name in CASES:
        o = observations[name]
        print("    %-18s %s %s" % (name, "거부" if o["refused"] else "떴다",
                                   o.get("reason", "") if o["refused"] else ""))
    if args.list:
        print(json.dumps(observations, ensure_ascii=False, indent=2))
        return EXIT_OK

    rows = judge(observations)
    failed = [(n, why) for n, passed, why in rows if not passed]
    print("%s 수 %d" % (TAG, len(rows)))
    for name, passed, why in rows:
        print("  %s  %-14s %s" % ("O" if passed else "X", name, why))
    if failed:
        print("%s 실패 %d/%d — **운영 프로필이 닫혀 있지 않다. 공개 URL 을 열지 않는다**"
              % (TAG, len(failed), len(rows)))
        return EXIT_FAIL
    print("%s 통과 %d/%d — 운영 프로필로 뜨면 닫혀 있고, 선언이 빠지면 **뜨지 않는다**"
          % (TAG, len(rows), len(rows)))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
