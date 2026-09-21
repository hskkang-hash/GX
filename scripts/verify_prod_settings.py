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
#: ⑦ 이 쓰는 「제대로 된 모양」의 자격 하나. 20자 이상 · 자리표 아님.
GOOD_MINIO = "gxverify-Rt2Xv6Bn1Cw8Hj3Kp5Sy"

#: 세 음성 대조가 공유하는 「나머지는 다 제대로」 선언 한 벌.
GOOD_DECL = {NAME_SECRET: GOOD_SECRET, NAME_HOSTS: GOOD_HOSTS, NAME_ORIGINS: GOOD_ORIGINS}

#: ⑦ 의 하한. `.env.example` 이 선언한 형식과 같은 수다. 서명 키는 ①이 50자를 따로 본다.
CRED_MIN_LEN = 20

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
    "SAFE_ERROR_BODY": getattr(s, "SAFE_ERROR_BODY", None),
    "ERROR_BODY_MIDDLEWARE": any("SafeErrorBody" in m for m in getattr(s, "MIDDLEWARE", [])),
    # ⑦ 자격의 **모양** (P-107 · 턴 M) — 값은 절대 내보내지 않는다. 길이와 같음 여부만.
    "MINIO_ACCESS_LEN": len(getattr(s, "MINIO_ACCESS_KEY", "") or ""),
    "MINIO_SECRET_LEN": len(getattr(s, "MINIO_SECRET_KEY", "") or ""),
    "MINIO_SAME": (_h(getattr(s, "MINIO_ACCESS_KEY", "")) ==
                   _h(getattr(s, "MINIO_SECRET_KEY", ""))),
    "MINIO_PLACEHOLDER": _ph(getattr(s, "MINIO_ACCESS_KEY", ""),
                             getattr(s, "MINIO_SECRET_KEY", "")),
    "DB_PASSWORD_LEN": len(_db(s).get("PASSWORD") or ""),
    "DB_PLACEHOLDER": _ph(_db(s).get("PASSWORD") or "", _db(s).get("USER") or ""),
    "SECRET_KEY_PLACEHOLDER_WORD": _ph(getattr(s, "SECRET_KEY", "") or ""),
}, ensure_ascii=False))
"""

#: 탐침 앞에 붙는 도우미 셋. **값을 문자열로 내보내는 자리가 하나도 없다** —
#: 길이 · 해시 동일성 · 자리표 여부만 넘어온다 (머리글 규칙과 같은 원칙).
PROBE = r"""
import hashlib, json
def _h(v):
    v = v or ""
    return hashlib.sha256(v.encode("utf-8", "replace")).hexdigest() if v else ""
_PLACEHOLDER_WORDS = ("change_me", "changeme", "your-", "please-change",
                      "example", "placeholder", "minioadmin", "secret-key")
def _ph(*values):
    return [w for w in _PLACEHOLDER_WORDS
            if any(w in (v or "").lower() for v in values)]
def _db(s):
    try:
        return s.DATABASES["default"]
    except Exception:
        return {}
""" + PROBE

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
    # ⑦ 자격의 모양 — **자리표로는 뜨면 안 된다** (P-107 · 턴 M)
    #   ★ 출생 표본: [실측 2026-09-07 · gx-shell] 앱이 든 `MINIO_ACCESS_KEY` 와
    #     `MINIO_SECRET_KEY` 는 **둘 다 5자이고 sha256 이 같다**(같은 문자열이다).
    #     그런데 앱은 그 자격으로 **떠 있고**, 화면이 부르는 라우트 둘이 503 을 낸다.
    #     자리표는 도는 앱이 아니라 **기동 실패**여야 한다.
    "placeholder_minio": (PROD_MODULE, dict(GOOD_DECL, MINIO_ACCESS_KEY="CHANGE_ME",
                                            MINIO_SECRET_KEY="CHANGE_ME")),
    "short_minio": (PROD_MODULE, dict(GOOD_DECL, MINIO_ACCESS_KEY="abc12",
                                      MINIO_SECRET_KEY="abc12")),
    "same_minio": (PROD_MODULE, dict(GOOD_DECL, MINIO_ACCESS_KEY=GOOD_MINIO,
                                     MINIO_SECRET_KEY=GOOD_MINIO)),
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

    # ⑥ 예외 응답이 **본문에 내부를 싣지 않는다** (P-100 · 턴 L)
    #
    #   이 자리가 열려 있으면 다른 500 도 다 말한다. 그날 실측된 것: 익명이
    #   `Authorization: Bearer <아무거나>` 를 붙이면 **705/705 라우트**가 165KB
    #   장고 디버그 전문을 냈다 — 존재하지 않는 라우트까지. URL 해석 **앞**이었다.
    #
    #   ★ 두 관측을 **함께** 본다. 스위치만 켜고 그물이 안 실리면 아무 일도 안 일어나고,
    #     그물만 실리고 스위치가 꺼져 있으면 그물이 통과시킨다. 하나만 재면
    #     「켰다」가 「막힌다」로 읽힌다 — 이 게이트가 다섯 자리에서 배운 것과 같다.
    if not full:
        out.append(("ERROR_BODY", False, "재지 못했다 — 판이 안 떴다"))
    else:
        flag = full.get("SAFE_ERROR_BODY")
        net = full.get("ERROR_BODY_MIDDLEWARE")
        out.append(("ERROR_BODY", flag is True and net is True,
                    "스위치 %r · 그물 실림 %r%s"
                    % (flag, net,
                       "" if (flag is True and net is True)
                       else " — **켜진 쪽과 실린 쪽이 함께여야 한다**")))

    # ⑦ 자격의 **모양** — 자리표로는 뜨지 않는다 (P-107 · 턴 M)
    #
    #   ★ 출생 표본 [실측 2026-09-07 · gx-shell]: 앱이 든 `MINIO_ACCESS_KEY` 와
    #     `MINIO_SECRET_KEY` 는 **둘 다 5자이고 sha256 이 같다** — 같은 문자열이다.
    #     그 자격으로 앱은 **떠 있었고**, 화면이 부르는 라우트 둘이 503 을 냈다.
    #     턴 L 은 그 503 의 원인을 다른 데서 찾았다. 원인은 여기였다.
    #
    #   ★ 두 가지를 **함께** 본다 — 지금 뜬 판의 자격이 제 모양인가, 그리고
    #     **자리표를 주면 거부하는가.** 앞엣것만 보면 「이 판에는 마침 좋은 값이
    #     들어 있었다」가 초록이 되고, 뒤엣것만 보면 도는 앱의 5자를 아무도 안 본다.
    if not full:
        out.append(("CREDENTIAL_FORMAT", False, "재지 못했다 — 판이 안 떴다"))
    else:
        a_len = full.get("MINIO_ACCESS_LEN", 0)
        s_len = full.get("MINIO_SECRET_LEN", 0)
        same = bool(full.get("MINIO_SAME"))
        db_len = full.get("DB_PASSWORD_LEN", 0)
        ph = (list(full.get("MINIO_PLACEHOLDER") or [])
              + list(full.get("DB_PLACEHOLDER") or [])
              + list(full.get("SECRET_KEY_PLACEHOLDER_WORD") or []))
        sk_len = full.get("SECRET_KEY_LEN", 0)

        shape_ok = (a_len >= CRED_MIN_LEN and s_len >= CRED_MIN_LEN
                    and db_len >= CRED_MIN_LEN and sk_len >= CRED_MIN_LEN
                    and not same and not ph)
        refused_ph = _refused(observations, "placeholder_minio")
        refused_short = _refused(observations, "short_minio")
        refused_same = _refused(observations, "same_minio")
        ok = shape_ok and refused_ph and refused_short and refused_same
        out.append(("CREDENTIAL_FORMAT", ok,
                    "MinIO 접근/비밀 %d·%d자%s · DB 비밀 %d자 · 서명 키 %d자 · 자리표 %s "
                    "| 자리표→거부 %s · 5자→거부 %s · 둘이 같음→거부 %s"
                    % (a_len, s_len,
                       " **둘이 같은 문자열이다**" if same else "",
                       db_len, sk_len, ph or "없음",
                       "O" if refused_ph else "**X 떴다**",
                       "O" if refused_short else "**X 떴다**",
                       "O" if refused_same else "**X 떴다**")))
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
    "SAFE_ERROR_BODY": True, "ERROR_BODY_MIDDLEWARE": True,
    "MINIO_ACCESS_LEN": 24, "MINIO_SECRET_LEN": 40, "MINIO_SAME": False,
    "MINIO_PLACEHOLDER": [], "DB_PASSWORD_LEN": 32, "DB_PLACEHOLDER": [],
    "SECRET_KEY_PLACEHOLDER_WORD": [],
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
                 "no_origins", "origins_no_scheme",
                 "placeholder_minio", "short_minio", "same_minio"):
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
        #: ★ ⑦ 의 출생 표본은 그날이 아니라 **턴 L(2026-09-07)** 이다 — 그리고 지금도
        #:   같다: 앱이 든 MinIO 자격은 5자이고 접근키와 비밀키가 **같은 문자열**이다.
        #:   그 자격으로 앱은 떠 있었고, 화면 라우트 둘이 503 이었다.
        "MINIO_ACCESS_LEN": 5, "MINIO_SECRET_LEN": 5, "MINIO_SAME": True,
        "MINIO_PLACEHOLDER": [], "DB_PASSWORD_LEN": 8, "DB_PLACEHOLDER": ["change_me"],
        "SECRET_KEY_PLACEHOLDER_WORD": ["your-"],
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
        print("%s O 닫힌 관측 %d/%d 초록 (양성 대조)" % (TAG, len(rows), len(rows)))

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
    m = _closed_observations(); m["full"]["settings"] = dict(_CLOSED_SETTINGS, SAFE_ERROR_BODY=False)
    mutants["ERROR_BODY"] = ("그물은 실렸는데 스위치가 꺼졌다", m)
    #: ⑦ — **도는 앱의 자격이 5자이고 접근·비밀이 같다** (턴 L 의 그 자리)
    m = _closed_observations()
    m["full"]["settings"] = dict(_CLOSED_SETTINGS, MINIO_ACCESS_LEN=5,
                                 MINIO_SECRET_LEN=5, MINIO_SAME=True)
    mutants["CREDENTIAL_FORMAT"] = ("MinIO 접근·비밀이 5자이고 같은 문자열이다", m)

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
        print("%s O 출생 표본 %d/%d 빨강 — 2026-09-06 의 settings.py 와 "
              "턴 L 의 5자 자리표 자격을 그대로 잡는다" % (TAG, len(born), len(born)))

    # 관측 0건은 **초록이 아니다** (D-301)
    if any(p for _, p, _ in judge({})):
        ok = False
        print("%s X 관측 0건을 초록으로 읽는다 — 못 잰 것이 통과가 되지 않는다" % TAG)
    else:
        print("%s O 관측 0건은 %d 수 다 빨강 (회색이 초록이 되지 않는다)"
              % (TAG, len(judge({}))))
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
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="gx-shell 컨테이너에서 파이썬을 %d번 **실제로 띄운다** (config.settings_prod / config.settings)" % len(CASES),
        as_="(계정 없음) — 자식 프로세스의 환경에 선언 이름만 준다: DJANGO_SECRET_KEY · DJANGO_ALLOWED_HOSTS · DJANGO_CSRF_TRUSTED_ORIGINS (값은 이 판정 안에서만 산다) · 앱이 든 MINIO_ACCESS_KEY/MINIO_SECRET_KEY 는 **길이와 같음 여부만** 본다",
        source="뜬 판이 스스로 낸 django.conf.settings — 소스에 적힌 글자가 아니다",
        #: ★ [P-204 · 턴 Z · Q] 분모는 **실제로 띄운 판의 수**다 — 소스를 읽은 수가 아니다.
        measured=("운영 프로필로 **실제로 띄운** 판에서 설정 관측을 낸다 — "
                  "**분모 %d**(CASES · 판을 %d번 띄운다) · 판정 갈래 7(SECRET_KEY · DEBUG · "
                  "ALLOWED_HOSTS · COOKIES · ORIGINS_TLS · DB · 관측 부재). "
                  "gx-shell 을 못 띄우면 **분모 0 — 안 쟀다**(회색 2)" % (len(CASES), len(CASES))),
    )
    raise SystemExit(main())
