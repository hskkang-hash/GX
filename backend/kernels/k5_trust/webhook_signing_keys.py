# -*- coding: utf-8 -*-
"""P-145 · SEC-16 — **나가는** 웹훅 서명키를 우리가 만든다 (턴 R 세종 판정).

한 문장
-------
    대표가 정할 값이 아니다 — 상대에게 주는 키이므로 **우리가 생성**해 우리 금고에 둔다.

세종 판정 P-145 원문 (RESUME_NEXT §2)
--------------------------------------
    "`WEBHOOK_SIGNING_KEYS` 는 **우리가 만드는 값**이다(상대에게 주는 키 · 회전 주기
     분기). 대표가 정할 것이 없다. `secrets.token_urlsafe(48)` 로 생성 → vault →
     `.env`(이름만 저장소) → 구독 발급 시 키 ID+값을 싣고 **값은 발급 응답에 한 번만**
     (D-335 ④ 해시 저장) → `verify_no_secret_echo` 통과."
    "원칙: 자격의 기본값은 없다 — 그리고 우리가 만드는 자격은 우리가 만든다."

무엇을 하는가 (네 걸음)
------------------------
    ① `secrets.token_urlsafe(48)` 로 값을 만든다 — 대표에게 값을 묻지 않는다.
    ② `settings.WEBHOOK_SIGNING_KEYS`(이름 → 값 표)에 채운다 — `common/webhook_outbox.py::
       signing_secret()` 이 그 표 **하나만** 읽는다(D-212). 여기서 두 번째 표를 만들지 않는다.
    ③ 값은 **이 함수의 반환값에 한 번만** 실린다. 그 뒤로 값을 돌려주는 자리는 없다 —
       잃어버리면 회전(재발급)만 가능하다. `k5_trust.inbound_keys.IssuedKey` 와 같은 성질이다.
    ④ 감사에는 **sha256 앞 12자만** 남긴다 — 값 자체는 로그·감사·응답 그 어디에도
       두 번 적지 않는다(이 저장소의 관례 — 자격은 앞 12자로 대조한다).

★ 왜 `WebhookSubscription` 모델에 칸을 더하지 않았나
------------------------------------------------------
    그 모델의 머리말이 이미 선언했다 — "**서명키 값은 여기 없다.** 칸이 있으면
    언젠가 채워지고, 채워진 값은 덤프·백업·화면·로그로 흘러나간다." 해시 칸을 더해도
    그 선언은 "칸이 없다"에서 "칸에 값 대신 지문이 있다"로 바뀔 뿐이고, 이 파일은
    그 표를 다시 열지 않는다 — 지문은 감사(`apps.dsm.audit`)가 이미 하는 "성공도
    실패도 남긴다"는 표로 간다(D-212, 두 번째 표를 열지 않는다).

★ 금고 — `.env` 에는 **이름만** 저장소에 남는다
--------------------------------------------------
    이 함수는 **이번 프로세스의 메모리**(`settings.WEBHOOK_SIGNING_KEYS`)에만 값을
    채운다. 그래야 발급 직후 같은 프로세스 안에서 서명 발송이 즉시 가능하다.
    재시작 뒤에도 서명이 살아야 하면, 운영자가 이 이름으로 **저장소 밖의** `.env`
    (`WEBHOOK_SIGNING_KEYS=name=value`)에 값을 옮겨 적어야 한다 — 그 옮겨 적는
    행위조차 이 코드가 대신 하지 않는다. 대신 하면 "코드가 파일에 비밀을 쓴다"는
    자리가 하나 더 생기고, 그 자리가 다음 유출 경로가 된다.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import PermissionDenied

from common.tenant_scope import TenantScope

#: 이름 뒤에 붙는 난수 자리(16진수 문자 수). 사람이 목록에서 "이 구독의 키"를
#: 지목할 수 있을 만큼만 — 이것으로 값을 추측할 수는 없다(이름은 비밀이 아니다).
_SUFFIX_HEX_CHARS = 10


class SigningKeyNameCollision(Exception):
    """이 이름이 이미 표에 값을 갖고 있다. **덮어쓰지 않는다** — 덮으면 그 이름을
    쓰던 다른 구독의 서명이 조용히 바뀐다(다른 상대에게 가는 서명이 깨진다)."""


@dataclass(frozen=True)
class IssuedSigningKey:
    """발급 결과. **`secret` 이 값을 담는 유일한 순간이다.**

    저장소·로그·감사에 이 값을 적지 않는다. 잃어버리면 회전한다 — 되찾기는 없고,
    되찾을 수 있으면 그것은 어딘가에 저장돼 있다는 뜻이다(`inbound_keys.IssuedKey`
    머리말과 같은 성질).
    """

    name: str
    secret: str
    #: sha256 앞 12자. 값 자체가 아니다 — 대조용 지문(이 저장소의 관례).
    sha256_12: str


def _sha256_12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _table() -> dict:
    """`settings.WEBHOOK_SIGNING_KEYS` 를 **그 자리 그대로** 돌려준다(복사하지 않는다) —
    이 함수가 표를 다시 만들면 `common/webhook_outbox.signing_secret()` 이 읽는 표와
    갈릴 수 있다. dict 는 참조 타입이라 여기서 채운 값이 곧 그쪽에서도 보인다."""
    table = getattr(settings, "WEBHOOK_SIGNING_KEYS", None)
    if table is None:
        table = {}
        settings.WEBHOOK_SIGNING_KEYS = table
    return table


def _group_of(scope: TenantScope):
    """이 사람의 테넌트. 못 정하면 **키를 만지지 않는다.**

    ★ 형제 파일 `inbound_keys._group_of` 와 같은 모양이다 — 판정식을 새로 짓지 않는다
      (D-212). `get_user_group`(있으면 준다)이 아니라 **`require_user_group`**(없으면
      멈춘다)을 부른다. 그리고 그것이 `common.tenant_filters` 의 진짜 문지기라
      `verify_tenant_scope.py` 의 호출 그래프가 인정한다 — 표식이 아니라 실제로 막기
      때문이다(P-K1-1).
    """
    from common.tenant_filters import require_user_group

    if scope.is_system:
        raise PermissionDenied(
            "나가는 서명키의 발급·회전은 사람이 한다 — 시스템 스코프로 하지 않는다. "
            "이 키는 「상대에게 우리 이름으로 경보를 낼 자격」이고, 주인이 없으면 "
            "어느 테넌트가 그 자격을 받았는지 아무도 모른다 (D-281)")
    return require_user_group(scope.actor)


def generate_signing_key(*, scope: TenantScope, name: str) -> IssuedSigningKey:
    """이름 하나에 **새 값**을 만들어 이번 프로세스의 표에 채운다.

    ★ 대표에게 값을 묻지 않는다 — 우리가 상대에게 주는 키이므로 우리가 만든다
      (세종 판정 P-145). 이 함수를 부르는 쪽이 사람에게 물어야 할 것은 **이름**
      (또는 이름을 만들 실마리)뿐이고, 값은 절대 아니다.

    ★ `scope` 를 받는 이유 (D-281 · 턴 R 에 게이트가 잡았다) — 커널(L3)에서는
      `@tenant_scoped` 가 **아무것도 막지 못한다.** `request` 가 없어 표식만 남기
      때문이다(착시 ①). 그래서 1차는 **시그니처**가 막고(테넌트 없이는 호출 자체가
      불가능하다) 2차는 위 `_group_of` 가 막는다.
    """
    _group_of(scope)
    name = (name or "").strip()
    if not name:
        raise ValueError("서명키 이름이 비었습니다.")
    table = _table()
    if table.get(name):
        raise SigningKeyNameCollision(
            "이름 %r 은 이미 이 환경에 값이 있습니다 — 새 이름을 쓰거나 회전하세요."
            % name)
    value = secrets.token_urlsafe(48)
    table[name] = value
    return IssuedSigningKey(name=name, secret=value, sha256_12=_sha256_12(value))


def rotate_signing_key(*, scope: TenantScope, name: str) -> IssuedSigningKey:
    """옛 값을 버리고 **같은 이름에 새 값**을 만든다.

    이름을 바꾸지 않는 이유: 구독 행(`WebhookSubscription.signing_key_ref`)이 그
    이름을 가리키고 있다 — 이름이 바뀌면 그 행도 같이 고쳐야 하고, 회전의 값은
    "구독은 그대로 두고 값만 바꾼다"는 것이다.

    `scope` 는 `generate_signing_key` 와 같은 이유로 받는다(D-281).
    """
    _group_of(scope)
    name = (name or "").strip()
    if not name:
        raise ValueError("서명키 이름이 비었습니다.")
    table = _table()
    value = secrets.token_urlsafe(48)
    table[name] = value
    return IssuedSigningKey(name=name, secret=value, sha256_12=_sha256_12(value))


def signing_key_name_for(*, scope: TenantScope) -> str:
    """테넌트마다 겹치지 않는 **이름**을 만든다. 이름은 값이 아니라 노출돼도 된다.

    ★ 1차판은 `group_id: int` 를 받았다. 숫자를 받으면 **부르는 쪽이 그 숫자를
      어디서든 가져올 수 있고**, 그 순간 「어느 테넌트의 이름인가」를 커널이 아니라
      호출자가 정하게 된다. `scope` 를 받아 여기서 소속을 묻는 것이 그 자리를 닫는다
      (D-281 · 턴 R 게이트).
    """
    group = _group_of(scope)
    return "wh_g%s_%s" % (group.pk, secrets.token_hex(_SUFFIX_HEX_CHARS // 2))


__all__ = [
    "IssuedSigningKey",
    "SigningKeyNameCollision",
    "generate_signing_key",
    "rotate_signing_key",
    "signing_key_name_for",
]
