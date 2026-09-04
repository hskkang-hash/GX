# -*- coding: utf-8 -*-
"""SEC-07 — **들어오는 키의 발급 · 폐기 · 회전**. 절차를 코드로 세운다.

무엇이 없었나
-------------
들어오는 키(F-05)는 **이미 살아 있었다**(D-335). 인증도 성했고, 범위도 D-335 가 좁혔다.
없던 것은 **키의 일생**이다:

    발급   누가 · 누구에게 · 언제까지. 지금은 dj-core 모델의 `create_key` 를 아무나 부른다
    폐기   끊는 자리가 없다. 유출된 키를 「그만 쓰라」고 말할 방법이 문서뿐이었다
    회전   **새 키가 서기 전에 옛 키를 끊으면 상대 연동이 그 순간 죽는다.**
           그래서 회전은 「지우고 새로 준다」가 아니라 **겹치는 창**이 있어야 한다

★ 회전은 조용한 파괴다 (선등록에 적어 둔 그대로)
------------------------------------------------
남의 키를 돌리면 그쪽 연동이 끊기고, **끊긴 쪽에서는 우리 잘못으로 안 보인다.**
그래서 이 파일의 세 함수는 전부 **누가 부르는지**를 먼저 묻는다 —
자기 테넌트의 키만 만질 수 있고, 전역 관리자만 경계를 넘는다.

★ 지우지 않는다 — `is_active=False` 로 끊는다
---------------------------------------------
행을 지우면 **그 키가 무엇을 했는지**가 함께 사라진다. 사고 뒤에 필요한 것이 정확히 그것이다.

§0.4 — dj-core 의 `APIKey` 모델은 **부르기만** 한다
    `core.apikey_account.models.APIKey` 는 저장소 밖이다. 고치지 않고 감싼다.
    모델에 없는 것(회전 이력·정책)은 **감사 한 줄**로 남긴다 — 열을 더하는 길은
    시험이 `--nomigrations` 로 도는 이 저장소에서 증거를 못 내는 길이다(LAW-08 이 만난 그 벽).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from common import audit_writer
from common.tenant_roles import is_global_admin, is_tenant_admin

log = logging.getLogger(__name__)

AUDIT_LOGGER = "guardianx.sec.key"
AUDIT_TAG = "[SEC-07]"

#: 키 하나를 **몇 날까지** 쓰게 둘 것인가. [판정] 90일 —
#: 짧으면 회전이 잦아 연동이 자주 흔들리고, 길면 유출된 키가 오래 산다.
KEY_MAX_AGE_DAYS = 90

#: 회전할 때 **옛 키가 더 사는 날**. 이 창이 0이면 회전은 곧 절단이다 —
#: 상대가 새 키를 받아 넣을 시간이 필요하고, 그 시간을 우리가 정해 준다.
KEY_ROTATION_OVERLAP_DAYS = 7

#: 「곧 만료」로 볼 남은 날. 감시가 이 수 안에 든 키를 사람에게 말한다.
KEY_EXPIRY_WARN_DAYS = 14


@dataclass(frozen=True)
class IssuedKey:
    """발급 결과. **원문은 여기서 딱 한 번 나온다** — 저장하지 않는다."""

    key_id: int
    prefix: str
    plaintext: str
    expires_at: object | None


def _model():
    """dj-core 의 **들어오는 키** 모델. 이름(`APIKey`)에는 방향이 없다 — 저장소 밖이라
    못 고친다. 그래서 부르는 자리마다 방향을 적는다(D-337: 같은 이름, 다른 것).
    """
    from core.apikey_account.models import APIKey as InboundKeyModel

    return InboundKeyModel


def _group_of(user):
    from common.tenant_filters import get_user_group

    return get_user_group(user)


def _guard(actor, target_user, *, action: str):
    """**남의 키를 만질 수 있는가.** 못 만지면 여기서 멈춘다.

    ★ 조용히 아무 일도 안 하는 길을 두지 않는다(D-284) — 거절은 예외로 말한다.
      회전이 조용히 실패하면 우리는 「돌렸다」고 믿고 상대는 옛 키를 계속 쓴다.
    """
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("인증이 필요합니다.")
    if is_global_admin(actor):
        return
    if not is_tenant_admin(actor):
        raise PermissionDenied("키를 관리할 권한이 없습니다.")
    mine, theirs = _group_of(actor), _group_of(target_user)
    if mine is None or theirs is None or mine.pk != theirs.pk:
        raise PermissionDenied("다른 소속의 키는 관리할 수 없습니다.")


def _audit(*, actor, action: str, outcome: str, reason: str, before=None, after=None):
    audit_writer.write(logger_name=AUDIT_LOGGER, tag=AUDIT_TAG, actor=actor,
                       action=action, outcome=outcome, reason=reason,
                       before=before, after=after)


# ═══════════════════════════════════════════════════════════════════════════
# 발급
# ═══════════════════════════════════════════════════════════════════════════
def issue_key(*, actor, owner, name: str, expires_days: int | None = None) -> IssuedKey:
    """새 키 하나. **원문은 이 반환값에만 있다.**

    `expires_days` 를 안 주면 정책값(`KEY_MAX_AGE_DAYS`)이 들어간다 —
    **만료 없는 키를 기본값으로 두지 않는다.** 기본값이 「영원」이면 회전 정책은
    문서로만 존재한다.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("키에 이름이 없다 — 이름 없는 키는 나중에 어느 것을 끊을지 못 고른다")
    _guard(actor, owner, action="issue")
    days = KEY_MAX_AGE_DAYS if expires_days is None else int(expires_days)
    if days <= 0:
        raise ValueError("만료 없는 키는 발급하지 않는다 (expires_days > 0)")

    inbound_key, plaintext = _model().create_key(owner, name, expires_days=days)
    _audit(actor=actor, action="key.issue", outcome=audit_writer.ALLOWED,
           reason=f"들어오는 키 발급 — {name} · {days}일",
           after={"key_id": inbound_key.pk, "prefix": inbound_key.prefix,
                  "owner_id": getattr(owner, "pk", None), "expires_days": days})
    return IssuedKey(key_id=inbound_key.pk, prefix=inbound_key.prefix,
                     plaintext=plaintext, expires_at=inbound_key.expires_at)


# ═══════════════════════════════════════════════════════════════════════════
# 폐기
# ═══════════════════════════════════════════════════════════════════════════
def revoke_key(*, actor, key_id: int, reason: str) -> None:
    """지금 끊는다. **사유가 필수다** — 사유 없는 폐기는 사고와 구별되지 않는다."""
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("폐기 사유가 없다 — 왜 끊었는지가 없으면 나중에 되돌릴 수 없다")
    key = _model().objects.select_related("user").get(pk=key_id)
    _guard(actor, key.user, action="revoke")

    before = {"key_id": key.pk, "prefix": key.prefix, "is_active": key.is_active}
    key.deactivate()
    _audit(actor=actor, action="key.revoke", outcome=audit_writer.ALLOWED,
           reason=f"들어오는 키 폐기 — {reason}",
           before=before, after={"key_id": key.pk, "is_active": False})


# ═══════════════════════════════════════════════════════════════════════════
# 회전
# ═══════════════════════════════════════════════════════════════════════════
def rotate_key(*, actor, key_id: int, overlap_days: int | None = None) -> IssuedKey:
    """옛 키를 **겹치는 창만큼 더 살려 두고** 새 키를 낸다.

    ★ 옛 키를 그 자리에서 끊지 않는 이유가 이 함수의 전부다. 상대는 우리 배포 일정을
      모른다 — 끊는 순간 그쪽 연동이 죽고, 죽은 쪽에서는 **우리 잘못으로 보이지 않는다.**
    ★ 겹치는 창은 `expires_at` 으로 준다. 새 시각이 지금 값보다 **뒤라면 당기지 않는다** —
      회전이 수명을 늘리는 일이 되면 안 된다.
    """
    overlap = KEY_ROTATION_OVERLAP_DAYS if overlap_days is None else int(overlap_days)
    if overlap < 0:
        raise ValueError("겹치는 창은 음수일 수 없다")
    old = _model().objects.select_related("user").get(pk=key_id)
    _guard(actor, old.user, action="rotate")
    if not old.is_active:
        raise ValueError("이미 끊긴 키는 회전하지 않는다 — 새로 발급한다(issue_key)")

    new = issue_key(actor=actor, owner=old.user, name=old.name)

    sunset = timezone.now() + timedelta(days=overlap)
    before = {"key_id": old.pk, "prefix": old.prefix,
              "expires_at": old.expires_at.isoformat() if old.expires_at else None}
    if old.expires_at is None or sunset < old.expires_at:
        old.expires_at = sunset
        old.save(update_fields=["expires_at"])
    _audit(actor=actor, action="key.rotate", outcome=audit_writer.ALLOWED,
           reason=f"들어오는 키 회전 — 겹치는 창 {overlap}일",
           before=before,
           after={"old_key_id": old.pk, "new_key_id": new.key_id,
                  "new_prefix": new.prefix,
                  "old_expires_at": old.expires_at.isoformat() if old.expires_at else None})
    return new


# ═══════════════════════════════════════════════════════════════════════════
# 주기 — 「돌려야 할 때가 됐다」를 **사람에게 말하는** 자리
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class KeyDue:
    key_id: int
    prefix: str
    owner: str
    age_days: int
    days_left: int | None
    why: str


def keys_due_for_rotation(*, now=None, max_age_days: int | None = None,
                          warn_days: int | None = None) -> tuple[KeyDue, ...]:
    """돌려야 할 키 전수. **판정만 한다 — 돌리지 않는다.**

    자동으로 돌리지 않는 이유: 회전은 상대의 연동을 흔든다. 언제 흔들지는
    사람이 정할 일이고, 도구는 **때가 됐다는 사실**을 말한다.
    """
    now = now or timezone.now()
    max_age = KEY_MAX_AGE_DAYS if max_age_days is None else int(max_age_days)
    warn = KEY_EXPIRY_WARN_DAYS if warn_days is None else int(warn_days)

    out: list[KeyDue] = []
    for key in _model().objects.select_related("user").filter(is_active=True):
        age = (now - key.created_at).days if key.created_at else 0
        left = (key.expires_at - now).days if key.expires_at else None
        why = ""
        if age >= max_age:
            why = f"발급한 지 {age}일 — 정책 {max_age}일을 넘었다"
        elif left is not None and left <= warn:
            why = f"만료까지 {left}일 남았다"
        if not why:
            continue
        out.append(KeyDue(key_id=key.pk, prefix=key.prefix,
                          owner=getattr(key.user, "username", "?"),
                          age_days=age, days_left=left, why=why))
    return tuple(sorted(out, key=lambda d: (d.days_left is None, d.days_left, d.key_id)))
