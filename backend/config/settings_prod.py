# -*- coding: utf-8 -*-
"""운영 프로필 — **보안 설정의 기본값은 닫힌 쪽이고, 열린 값은 선언으로만 열린다**.

세종 판정 P-75 · 대장 절 SEC-18 · 2026-09-06 턴 H · 차선 S

무엇이 이 파일을 만들게 했나 — **아무도 정하지 않으면 제품이 가장 위험한 값을 고른다**
------------------------------------------------------------------------------------
[실측 2026-09-06 · 턴 G · 차선 V 가 떠 있는 서버의 `settings` 를 읽어 보고]

    backend/config/settings.py:28  SECRET_KEY = env(…, default="your-secret-key-here")
    backend/config/settings.py:31  DEBUG = env.bool("DJANGO_DEBUG", default=True)
    backend/config/settings.py:34  ALLOWED_HOSTS = ["*"]
    backend/config/settings.py:45  # CSRF_COOKIE_SECURE = (not DEBUG)      ← 주석
    backend/config/settings.py:47  # SESSION_COOKIE_SECURE = (not DEBUG)   ← 주석

넷 다 **아무 선언 없이 뜨면 가장 열린 쪽**으로 선다. 공개 URL 을 여는 순간
① 오류 화면이 트레이스백을 그대로 내고 ② 어떤 Host 머리글자든 받고 ③ **저장소에
적힌 서명 키**로 세션을 위조할 수 있고 ④ 쿠키가 평문 위로 흐른다.

이 파일이 하는 일 — **닫힌 쪽에서 시작하고, 열린 값은 선언으로만 받는다**
-------------------------------------------------------------------------
  ① `DJANGO_SECRET_KEY` 가 없거나 자리표면 **기동을 거부한다**(`ImproperlyConfigured`).
     조용히 뜨지 않는다 — 조용히 뜨는 것이 사고의 모양이었다.
  ② `DEBUG = False` **고정**. 환경변수로 켤 수 없다(`DJANGO_DEBUG=true` 를 줘도 False).
  ③ `ALLOWED_HOSTS` 선언 필수 · **`*` 는 거부**.
  ④ 쿠키 여섯: `SESSION/CSRF_COOKIE_SECURE` · `*_HTTPONLY` · `SameSite=Lax`.
  ⑤ `CSRF_TRUSTED_ORIGINS` 선언 필수(스킴 포함) · HSTS(TLS 뒤) ·
     `SECURE_PROXY_SSL_HEADER`(nginx 뒤).

★ **개발 프로필(`config.settings`)은 지금 값 그대로 남는다 — 지우지 않는다.**
  순서는 세종이 정했다(P-67 이 보존 일수에서 밟은 그 순서 그대로):
  **선언 먼저, 기본값 나중.** 뒤집으면 `DJANGO_SECRET_KEY` 가 없는 지금 컨테이너들이
  settings 를 읽는 순간 죽고 개발 환경 전체가 안 뜬다. 코드의 열린 기본값 제거는
  **재기동 창 뒤**다.

★ **선언 이름은 새로 짓지 않았다** — 조율자가 `.env.example` 에 세운 그 이름을 쓴다:
  `DJANGO_SECRET_KEY` · `DJANGO_DEBUG` · `DJANGO_ALLOWED_HOSTS` ·
  `DJANGO_CSRF_TRUSTED_ORIGINS`.

쓰는 법
-------
    DJANGO_SETTINGS_MODULE=config.settings_prod

  판정: `python scripts/verify_prod_settings.py` (5/5 · 음성 대조를 **실제로 돌린다**)
  배치: `scripts/deploy.sh --profile prod --target staging` — 개발 프로필로
        공개 URL 을 열려고 하면 배치가 **거부**된다.

⚠ **거부는 결함이 아니라 이 파일의 일이다.** 선언이 없는 환경에서 이 프로필이
  뜨면 그때가 사고다.
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from config.settings import *  # noqa: F401,F403  (개발 프로필을 **읽고 덮는다**)

TAG = "[SEC-18]"

#: 이 프로필이 무엇인지 스스로 말한다 — `deploy.sh`·판정기가 프로필을 되짚는 자리.
SECURITY_PROFILE = "prod"

#: `SECRET_KEY` 로 절대 설 수 없는 것 — **저장소나 예시 파일에 적힌 값**.
#: 목록이 아니라 술어다: 「저장소를 읽은 사람이 아는 값」이면 그것은 서명 키가 아니다.
SECRET_KEY_PLACEHOLDERS = (
    "your-secret-key-here",
    "change_me",
    "changeme",
    "django-insecure",
    "secret-key",
    "please-change",
)

#: 서명 키 최소 길이. `.env.example` 이 선언한 형식(50자 이상 무작위)과 같은 수다.
SECRET_KEY_MIN_LEN = 50

_errors: list = []


def _declared(name: str) -> str:
    """선언된 값. **없음과 빈 문자열을 같게 본다** — 둘 다 「아무도 안 정했다」다."""
    return (os.environ.get(name) or "").strip()


def _split(value: str) -> list:
    """쉼표로 나눈 목록. 빈 칸은 버린다."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _fail(line: str) -> None:
    _errors.append(line)


# ─────────────────────────────────────────────────────────────────────────────
# ① SECRET_KEY — 없으면 **뜨지 않는다**. 자리표는 없는 것보다 나쁘다
# ─────────────────────────────────────────────────────────────────────────────
_secret = _declared("DJANGO_SECRET_KEY")
if not _secret:
    _fail("DJANGO_SECRET_KEY 가 선언되지 않았다 — 운영 프로필은 서명 키 없이 뜨지 않는다. "
          "만드는 법: python -c \"import secrets;print(secrets.token_urlsafe(64))\"")
else:
    _lowered = _secret.lower()
    _hit = [p for p in SECRET_KEY_PLACEHOLDERS if p in _lowered]
    if _hit:
        _fail("DJANGO_SECRET_KEY 가 자리표다(%s) — **저장소를 읽은 사람이 아는 값**으로는 "
              "세션을 서명할 수 없다" % ", ".join(_hit))
    elif len(_secret) < SECRET_KEY_MIN_LEN:
        _fail("DJANGO_SECRET_KEY 가 %d자다 — 선언한 형식은 %d자 이상 무작위다(.env.example)"
              % (len(_secret), SECRET_KEY_MIN_LEN))
    else:
        SECRET_KEY = _secret

# ─────────────────────────────────────────────────────────────────────────────
# ② DEBUG — **고정 False**. 환경변수로 켤 수 없다
# ─────────────────────────────────────────────────────────────────────────────
# ★ 여기서 `env.bool("DJANGO_DEBUG")` 를 읽지 않는 것이 핵심이다. 읽는 순간
#   「한 번만 켜 두자」가 가능해지고, 그 한 번이 공개 URL 에서 트레이스백을 낸다.
DEBUG = False

#: 개발용 선언이 운영 환경에 섞여 들어왔다는 사실 자체는 남긴다 — 값은 안 따른다.
DEBUG_DECLARATION_IGNORED = _declared("DJANGO_DEBUG").lower() in ("1", "true", "yes", "on")

# ─────────────────────────────────────────────────────────────────────────────
# ③ ALLOWED_HOSTS — 선언 필수 · `*` 거부
# ─────────────────────────────────────────────────────────────────────────────
_hosts_raw = _declared("DJANGO_ALLOWED_HOSTS")
_hosts = _split(_hosts_raw)
if not _hosts:
    _fail("DJANGO_ALLOWED_HOSTS 가 선언되지 않았다 — 어떤 Host 머리글자를 받을지 "
          "정하지 않은 채로 공개 URL 을 열지 않는다 (예: guardianx.example.kr,stg.guardianx.example.kr)")
elif any("*" in h for h in _hosts):
    _fail("DJANGO_ALLOWED_HOSTS 에 `*` 가 있다(%r) — 어떤 Host 든 받는 것은 선언이 아니라 "
          "선언의 부재다" % (_hosts,))
elif any("CHANGE_ME" in h.upper() for h in _hosts):
    _fail("DJANGO_ALLOWED_HOSTS 가 자리표 그대로다(%r) — .env.example 을 복사만 하고 "
          "채우지 않았다" % (_hosts,))
else:
    ALLOWED_HOSTS = _hosts

# ─────────────────────────────────────────────────────────────────────────────
# ④ 쿠키 여섯 — Secure · HttpOnly · SameSite=Lax
# ─────────────────────────────────────────────────────────────────────────────
# ★ 개발 프로필에서 이 여섯은 **주석**이었다. 주석으로 적힌 것은 적히지 않은 것이다.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# ⚠ `CSRF_COOKIE_HTTPONLY = True` 는 자바스크립트가 `csrftoken` 쿠키를 **못 읽게** 한다.
#   우리 프런트는 JWT 를 쓰고 CSRF 토큰을 쿠키에서 읽지 않는다(읽어야 하는 화면이
#   생기면 `X-CSRFToken` 을 서버가 내려 주는 쪽으로 고친다 — 이 줄을 지우지 말 것).
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ─────────────────────────────────────────────────────────────────────────────
# ⑤ 공개 출처 · TLS 뒤 배선 — CSRF_TRUSTED_ORIGINS · HSTS · 프록시 머리글자
# ─────────────────────────────────────────────────────────────────────────────
_origins_raw = _declared("DJANGO_CSRF_TRUSTED_ORIGINS")
_origins = _split(_origins_raw)
if not _origins:
    _fail("DJANGO_CSRF_TRUSTED_ORIGINS 가 선언되지 않았다 — 개발 프로필의 기본값은 "
          "`http://localhost:8000` 두 개다. 그 값으로 공개 URL 을 열면 폼 제출이 막힌다 "
          "(예: https://guardianx.example.kr)")
elif any("CHANGE_ME" in o.upper() for o in _origins):
    _fail("DJANGO_CSRF_TRUSTED_ORIGINS 가 자리표 그대로다(%r)" % (_origins,))
elif any("*" in o for o in _origins):
    _fail("DJANGO_CSRF_TRUSTED_ORIGINS 에 `*` 가 있다(%r) — 믿을 출처를 세지 않겠다는 뜻이다"
          % (_origins,))
else:
    _no_scheme = [o for o in _origins if not (o.startswith("https://") or o.startswith("http://"))]
    if _no_scheme:
        _fail("DJANGO_CSRF_TRUSTED_ORIGINS 에 스킴이 없다(%r) — Django 4+ 는 스킴을 요구한다"
              % (_no_scheme,))
    else:
        CSRF_TRUSTED_ORIGINS = _origins

# HSTS — **TLS 뒤에서만 뜻이 있다.** 기본 1년, 선언으로 줄일 수 있다(첫 배치의 관례).
SECURE_HSTS_SECONDS = int(_declared("DJANGO_HSTS_SECONDS") or 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# nginx 가 TLS 를 끝낸다 — 그 뒤의 Django 는 스스로를 평문으로 안다.
# ⚠ 이 머리글자는 **앞단이 반드시 덮어써야** 한다(`proxy_set_header X-Forwarded-Proto $scheme`).
#   덮어쓰지 않는 앞단 뒤에서는 클라이언트가 이 머리글자를 위조할 수 있다.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# ─────────────────────────────────────────────────────────────────────────────
# ⑦ 자격의 **모양** — 짧은 값 · 같은 값 · 자리표로는 **뜨지 않는다**
#    (P-107 · 턴 M / P-151 · 턴 R · blockers.yaml:1654 `unlock_step` ③)
# ─────────────────────────────────────────────────────────────────────────────
#
# ★ 무엇이 이 절을 만들게 했나 [실측 2026-09-07 · 턴 L · gx-shell]
#   앱이 든 `MINIO_ACCESS_KEY` 와 `MINIO_SECRET_KEY` 는 **둘 다 5자이고 sha256 이 같다**
#   — 같은 문자열이다. 그 자격으로 앱은 **떠 있었고**, 화면이 부르는 라우트 둘이 503 을
#   냈다. 턴 L 은 그 503 의 원인을 다른 데서 찾았다. 원인은 여기였다.
#   **자리표는 도는 앱이 아니라 기동 실패여야 한다.**
#
# ★ 왜 「경고만 찍고 뜨는」 것이 안 되는가 — 그것은 가드가 아니다. 경고는 로그에
#   묻히고, 묻힌 경고 뒤에서 5자 자격이 여섯 달을 돌았다. ①~⑤ 와 **같은 줄에**
#   `_fail()` 로 쌓아 함께 거부한다.
#
# ★ 접근키 == 비밀키는 「짧다」와 **다른 종류의 결함**이다 — 접근키는 사용자 이름처럼
#   로그·URL 에 남는 쪽이고 비밀키는 안 남는 쪽이다. 둘이 같으면 접근키가 남는
#   모든 자리에 **비밀키가 같이 남아 있다**(blockers.yaml:1644).
#
# ⚠ **값을 메시지에 싣지 않는다.** 이 절이 밖으로 내보내는 것은 이름 · 길이 ·
#   「같다/다르다」 · 자리표 낱말뿐이다 (P-135 불변 · `verify_no_secret_echo`).

#: 자격의 하한. `.env.example` 이 선언한 형식이고 `verify_prod_settings.CRED_MIN_LEN`
#: 과 **같은 수**다. 서명 키는 ①이 50자를 따로 본다(이 절은 20자만 다시 본다).
CRED_MIN_LEN = 20

#: 「저장소·예시·기본값을 읽은 사람이 아는 값」의 낱말. 판정기
#: `verify_prod_settings.PROBE._PLACEHOLDER_WORDS` 와 **같은 목록**이다 —
#: 둘이 갈리면 코드는 거부하는데 판정기는 초록을 내거나 그 반대가 된다.
CREDENTIAL_PLACEHOLDER_WORDS = (
    "change_me", "changeme", "your-", "please-change",
    "example", "placeholder", "minioadmin", "secret-key",
)


def _placeholder_words(*values) -> list:
    """주어진 값들에 박힌 자리표 낱말. **값은 안 돌려준다** — 낱말만."""
    return [w for w in CREDENTIAL_PLACEHOLDER_WORDS
            if any(w in (v or "").lower() for v in values)]


def _from_settings(name: str) -> str:
    """앱이 **실제로 쓰는** 값. `config.settings` 가 환경에서 읽어 세운 그 자리다.

    ★ 여기서 `os.environ` 을 다시 읽지 않는 것이 중요하다 — 앱은 환경이 아니라
      `django.conf.settings` 를 본다. 둘이 갈리면(기본값·형변환) 가드는 환경을
      검사하고 앱은 다른 값으로 돈다.
    """
    return (globals().get(name) or "").strip()


_minio_access = _from_settings("MINIO_ACCESS_KEY")
_minio_secret = _from_settings("MINIO_SECRET_KEY")
try:
    _db_default = globals().get("DATABASES", {})["default"]
except (KeyError, TypeError):
    _db_default = {}
_db_password = (_db_default.get("PASSWORD") or "").strip()
_db_user = (_db_default.get("USER") or "").strip()

for _name, _value in (("MINIO_ACCESS_KEY", _minio_access),
                      ("MINIO_SECRET_KEY", _minio_secret),
                      ("DB_PASSWORD", _db_password)):
    if not _value:
        _fail("%s 가 비어 있다 — 운영 프로필은 자격 없이 뜨지 않는다" % _name)
    elif len(_value) < CRED_MIN_LEN:
        _fail("%s 가 %d자다 — 하한은 %d자다. **짧은 자격으로 뜬 앱이 곧 사고다**"
              % (_name, len(_value), CRED_MIN_LEN))

#: 접근키와 비밀키가 **같은 문자열**이면 거부. 길이가 같은 것이 아니라 값이 같은 것을
#: 본다 — 비교만 하고 어느 쪽도 밖으로 내보내지 않는다.
if _minio_access and _minio_secret and _minio_access == _minio_secret:
    _fail("MINIO_ACCESS_KEY 와 MINIO_SECRET_KEY 가 **같은 문자열이다**(둘 다 %d자) — "
          "접근키는 로그·URL 에 남는 쪽이고 비밀키는 안 남는 쪽이다. 둘이 같으면 "
          "접근키가 남는 모든 자리에 비밀키가 같이 남는다" % len(_minio_access))

_cred_placeholders = _placeholder_words(_minio_access, _minio_secret,
                                        _db_password, _db_user, _secret)
if _cred_placeholders:
    _fail("자격에 자리표 낱말이 남아 있다(%s) — **저장소·예시를 읽은 사람이 아는 값**은 "
          "자격이 아니다. 네 이름(MINIO_ACCESS_KEY · MINIO_SECRET_KEY · DB_PASSWORD · "
          "DJANGO_SECRET_KEY) 을 저장소 밖 금고의 값으로 채워라"
          % ", ".join(_cred_placeholders))

#: 이 프로필이 ⑦ 을 **실제로 보고 있다**는 것을 판정기·다음 사람이 되짚는 자리.
#: (값이 아니라 「검사했다」는 사실이다.)
CREDENTIAL_GUARD = "SEC-18-⑦"

# ─────────────────────────────────────────────────────────────────────────────
# **거부는 조용하지 않다** — 모아서 한 번에 말한다
# ─────────────────────────────────────────────────────────────────────────────
# ★ 첫 실패에서 바로 죽지 않고 다섯을 다 본 뒤 말한다: 한 번 고치고 다시 죽는 것을
#   다섯 번 반복하면 사람은 프로필을 버리고 개발 프로필로 공개 URL 을 연다.
if _errors:
    raise ImproperlyConfigured(
        "%s 운영 프로필 기동 거부 — 선언이 %d건 빠졌거나 열린 쪽이다:\n%s\n"
        "%s 채울 이름은 저장소 뿌리 `.env.example` 의 「운영 프로필 선언」 절에 있다. "
        "개발은 `DJANGO_SETTINGS_MODULE=config.settings` 로 그대로 뜬다."
        % (TAG, len(_errors),
           "\n".join("  · %s" % e for e in _errors), TAG)
    )
