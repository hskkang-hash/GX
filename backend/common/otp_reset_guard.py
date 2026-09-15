# -*- coding: utf-8 -*-
"""P-113 — **익명이 남의 2단계 인증을 꺼 버리던 자리**를 우리 층에서 막는다.

무엇이 있었나 [실측 2026-09-10 · TARGET=8500 · 인증 없음]
---------------------------------------------------------
    POST /api/v1/auth/otp/reset   본문 {"username": "..."} 하나
      -> dj-core `core/api/v1/auth.py:1990 reset_otp` 가 **권한 검사 한 줄 없이** 돈다:

            otp_secret = pyotp.random_base32()
            user.otp_exempt = False
            user.opt_mandatory = False       # <- 2단계 인증 **의무 해제**
            user.otp_is_verified = False     # <- 검증 상태 **취소**
            user.save()
            profile.otp_secret = otp_secret  # <- 비밀키를 **새로 심는다**

    즉 **익명이 아무 계정의 2단계 인증을 끌 수 있다.** 비밀번호 하나만 알면(또는
    P-112 처럼 74계정이 같은 비밀번호를 쓰면) 2FA 는 더 이상 두 번째 벽이 아니다.

    전 [실측 · 없는 사용자명 `gx_nonexistent_probe_zzz`] -> **404** "User not found"
       404 는 관문의 답이 아니다. **핸들러가 실제로 돌아서 조회까지 갔다**는 뜻이다
       (P-83 과 같은 눈금: 404·422 는 도달이지 관문이 아니다).
       ⚠ 실재 사용자명으로는 **일부러 두드리지 않았다** — 그 한 번이 곧 사고다.
          「쓴다」의 근거는 위 호출 그래프이고, 「이 입력으로는 안 썼다」의 근거는
          없는 이름으로 잰 404 다. 둘을 섞지 않는다 (D-322).

규칙 — CPO 판정 그대로
----------------------
  ① **익명 -> 401.** `access_gate.AUTHN_REQUIRED_PATHS` 에 이름을 올려
     `reset-password-for-user` 와 **같은 자리**에서 끊는다.
  ② **본인 -> 재인증을 요구한다.** 현재 비밀번호(`current_password`) 또는
     현재 OTP 코드(`otp_code`) 중 하나가 맞아야 한다. 없거나 틀리면 **401**.
     ★ 2FA 를 끄는 행위는 「로그인한 상태」보다 센 증명을 요구한다 — 탈취된 세션
       하나로 두 번째 벽이 무너지면 안 된다.
  ③ **남의 계정 -> 관리자만.** 관리자면 통과시키되 **감사 한 줄을 반드시 남긴다.**
     관리자가 아니면 **403**(누구인지는 아는데 안 된다 — D-290).
  ④ 감사에 남길 수 없으면 그 행위는 **일어나지 않는다**(audit_writer 머리말 규약) —
     쓰기가 실패하면 500 이 아니라 **403 으로 끊는다.** 조용히 통과시키지 않는다.

★ 왜 dj-core 를 안 고치나 — `core/api/v1/auth.py` 는 §0.4 금지구역이다(D-207).
  D-348 그대로 **막는 자리를 우리 층으로 옮긴다.** 라우트 선언도 핸들러도 그대로다.

★ 이 관문은 **두 번째 인증기가 아니다.** 토큰을 스스로 풀지 않는다 —
  앞 겹(dj-core `JWTUserRestoreMiddleware`)이 세워 준 `request.user` 만 본다.
  여기서 검사하는 것은 **재인증 증거**(비밀번호·OTP)이고 그건 인증과 다른 질문이다.

⚠ 운영에 남는 결과 — **「인증기를 잃어버렸다」는 이제 관리자 일이다.**
  종전에는 누구든(익명 포함) 이 자리를 불러 OTP 를 초기화할 수 있었다. 규칙 ②③ 이
  서면 인증기를 잃은 사람은 스스로 못 푼다 — 관리자가 대신 부르고 감사 줄이 남는다.
  그것이 이 규칙의 **의도**다. 자가 복구 창구가 필요하면 그것은 별도 흐름이고,
  이 자리를 다시 여는 것으로 대신하지 않는다.

되돌리기 (D-212)
----------------
    settings.OTP_RESET_GUARD_ENABLED = False

False 면 이 판정은 한 요청도 안 막는다. `access_gate` 의 익명 401 은 별개 줄이다 —
그쪽을 되돌리려면 `AUTHN_REQUIRED_PATHS` 에서 이름 한 줄을 뺀다.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

#: 되돌리기 한 줄의 이름. 시험도 운영도 이 이름만 본다 (D-212).
FLAG = "OTP_RESET_GUARD_ENABLED"

#: 이 관문이 보는 **단 한 자리**. 접두가 아니라 이름이다 — 이름이 규칙보다 세다(P-83).
GUARDED_PATH = "/api/v1/auth/otp/reset"

#: 재인증 증거를 담아 보내는 칸. 둘 중 **하나**면 된다.
REAUTH_PASSWORD_FIELD = "current_password"
REAUTH_OTP_FIELD = "otp_code"

#: 관리자로 세는 역할 코드. `is_superuser`·`is_staff` 는 코드 밖에서 따로 본다.
ADMIN_ROLE_CODES = frozenset({"admin", "superuser"})

#: 감사 한 줄의 이름표.
#: ★ 반드시 `evidence_chain.CHAIN_PREFIX`(= "guardianx.") 로 시작해야 한다 (LAW-08).
#:   [실측 2026-09-10] 접두 없이 `security.otp_reset` 로 쓰자 행은 만들어지고
#:   **체인 잇기가 예외로 터졌다**(`감사 행 #199137 를 못 찾았다`). 규약대로 감사
#:   쓰기가 통째로 실패했고 이 관문은 **403 으로 끊었다** — 조용히 통과하지 않았다.
AUDIT_LOGGER_NAME = "guardianx.sec.otp_reset"
AUDIT_TAG = "[P-113]"
AUDIT_ACTION = "otp_reset"

REASON_ANONYMOUS = "authentication required"
REASON_REAUTH = "re-authentication required"
REASON_NOT_ADMIN = "administrator required to reset another account's OTP"
REASON_AUDIT_FAILED = "audit row could not be written"


def enabled() -> bool:
    """이 겹이 켜져 있는가. 기본은 **켜짐**(닫힌 쪽이 기본이다)."""
    return bool(getattr(settings, FLAG, True))


def _normalize(path: str) -> str:
    return (str(path or "").rstrip("/")) or "/"


def is_guarded(*, method: str, path: str) -> bool:
    """이 요청이 이 관문의 일인가. **순수 함수다** — 요청 객체 없이 시험한다."""
    return str(method or "").upper() == "POST" and _normalize(path) == GUARDED_PATH


def is_administrator(user) -> bool:
    """관리자인가. **세 갈래를 한 자리에서 본다** (D-212).

    `is_superuser` · `is_staff` · 역할 코드. 셋을 흩으면 한쪽만 고쳐지는 날이 온다.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    roles = getattr(user, "roles", None)
    if roles is None:
        # 역할 관계가 없는 사용자 객체다. **모르는 것을 관리자로 세지 않는다**(D-284).
        return False
    try:
        return roles.filter(code__in=sorted(ADMIN_ROLE_CODES)).exists()
    except Exception:                                     # pragma: no cover
        logger.warning("%s roles 를 못 읽었다 — 관리자가 아닌 쪽으로 센다", AUDIT_TAG)
        return False


def _otp_secret(user):
    """이 사용자의 현재 OTP 비밀키. 못 읽으면 None — **모르면 통과시키지 않는다.**"""
    try:
        from django.apps import apps
        profile = apps.get_model("user", "Profile")._base_manager.filter(
            user=user).first()
    except Exception:                                     # pragma: no cover
        return None
    return getattr(profile, "otp_secret", None) if profile else None


def verify_reauth(user, body: dict) -> bool:
    """재인증 증거가 맞는가. **비밀번호 또는 현재 OTP 코드** 중 하나.

    ★ 값을 로그에도 응답에도 싣지 않는다 (D-335 규약 ④).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    password = (body or {}).get(REAUTH_PASSWORD_FIELD)
    if password:
        try:
            if user.check_password(str(password)):
                return True
        except Exception:                                 # pragma: no cover
            logger.warning("%s check_password 가 터졌다 — 통과시키지 않는다", AUDIT_TAG)

    code = (body or {}).get(REAUTH_OTP_FIELD)
    if code:
        secret = _otp_secret(user)
        if secret:
            try:
                import pyotp
                if pyotp.TOTP(secret).verify(str(code), valid_window=1):
                    return True
            except Exception:                             # pragma: no cover
                logger.warning("%s OTP 검증이 터졌다 — 통과시키지 않는다", AUDIT_TAG)
    return False


def read_body(request) -> dict:
    """요청 본문을 JSON 으로 읽는다. **못 읽으면 빈 칸** — 추측하지 않는다(D-280).

    ★ `request.body` 를 여기서 읽어도 뒤의 뷰가 다시 읽을 수 있다 — Django 가
      한 번 읽은 본문을 캐시한다. 스트리밍 업로드가 아닌 JSON 요청만 이 자리에 온다.
    """
    try:
        raw = request.body
    except Exception:                                     # pragma: no cover
        return {}
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8", "replace"))
    except Exception:                                     # noqa: BLE001
        return {}
    return parsed if isinstance(parsed, dict) else {}


def judge(*, user, body: dict, is_admin: bool | None = None):
    """거절 사유와 상태를 돌려준다. 통과면 `None`. **요청 객체 없이 시험한다.**

    돌려주는 값: `(status, reason, needs_audit)` 또는 `None`.
      `status` 가 None 이고 `needs_audit` 이 참이면 **관리자가 남의 계정을 건드리는
      경우**이고, 부르는 쪽이 감사 한 줄을 남긴 뒤에야 통과시킨다 (규칙 ④).

    순서가 규칙이다:
      ① 익명 -> 401 (누구인지 모른다)
      ② 본인 -> 재인증 증거가 있어야 통과. 없으면 401
      ③ 남 + 관리자 -> 통과하되 **감사 필수**
      ④ 남 + 비관리자 -> 403 (누구인지는 아는데 안 된다)
    """
    body = body or {}
    if user is None or not getattr(user, "is_authenticated", False):
        return (401, REASON_ANONYMOUS, False)

    target = str(body.get("username") or "").strip()
    me = str(getattr(user, "username", "") or "").strip()

    # 대상 이름이 비어 있으면 **본인 요청**으로 읽는다 — 가장 좁은 해석이다.
    if not target or target == me:
        if verify_reauth(user, body):
            return None
        return (401, REASON_REAUTH, False)

    admin = is_administrator(user) if is_admin is None else bool(is_admin)
    if admin:
        return (None, "administrator reset of another account", True)
    return (403, REASON_NOT_ADMIN, False)


def write_audit(*, actor, target: str, allowed: bool, reason: str, status: int | None):
    """감사 한 줄. **실패하면 예외가 올라간다** — 삼키지 않는다(audit_writer 규약)."""
    from common import audit_writer
    return audit_writer.write(
        logger_name=AUDIT_LOGGER_NAME,
        tag=AUDIT_TAG,
        actor=actor,
        action=AUDIT_ACTION,
        outcome=audit_writer.ALLOWED if allowed else audit_writer.DENIED,
        reason=reason,
        before={"target_username": target},
        after=None,
        api_name=GUARDED_PATH,
        api_method="POST",
        status_http=status,
    )
