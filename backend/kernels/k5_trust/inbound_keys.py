# -*- coding: utf-8 -*-
"""**들어오는** API Key 의 발급·폐기 — 계약 F-05 「API Key 발급·폐기 포함」 (D-367).

한 문장
-------
    키를 **만들지 않았다.** 이관 자산에 이미 있던 발급기를 **감싸고 테넌트에 묶었다.**

★ 이 절이 세 번 미뤄진 내력 — 미룬 것이 옳았다
----------------------------------------------
    2026-09-06 (D-325)  표 ②(자격증명 저장처)가 이 절을 갚을 것으로 봤다.
                        **틀렸다** — 표 ②는 **나가는** 키(우리가 남을 부를 때)이고
                        이 절은 **들어오는** 키(남이 우리를 부를 때)다. 둘 다 "API Key"
                        라 불려서 같은 것으로 읽혔다 (D-337 · 같은 이름 다른 것).
    2026-09-07 (D-335)  착수해 보니 인증은 **이미 성했고** 성하지 않은 것은 **범위**였다.
                        키 하나가 F-05 진입면 7자리 전부에 닿았고, 거기엔 원본 영상
                        (`clip/stream` · 계약 11조)도 있었다. 그래서 **좁혔다.**
                        ★ 그러나 좁히기는 「소비 면의 범위」이고 이 절은 「발급·폐기」다.
                          범위를 좁혔다고 발급·폐기를 만든 것이 아니므로 **미착수를 유지**했다.
    2026-09-10 (D-367)  이 파일. 남은 것 하나 — **발급·폐기의 면**을 우리 층에 세운다.

세 번 다 「올릴 수 있을 것 같은」 상태였고 세 번 다 안 올렸다. 그 덕에 지금 이 파일이
갚는 것이 **정확히 무엇인지**가 남아 있다.

§0.4 — dj-core 는 **읽고 호출만 한다** (D-207 · D-335)
------------------------------------------------------
발급기는 `core.apikey_account.models.APIKey` 에 이미 있다:
`APIKey.create_key(user, name, expires_days)` · `APIKey.deactivate()`.
**그 파일을 한 줄도 고치지 않는다.** 우리가 더하는 것은 셋이고, 셋 다 우리 층에 있다:

    ① **테넌트 귀속**  — dj-core 의 키는 `user` FK 만 갖는다. 테넌트 개념이 없다.
                         우리는 `user__userprofilelink__group` 으로 좁힌다
    ② **마스킹 조회**  — 값은 어디에도 돌려주지 않는다. `prefix` 와 사실만 낸다
    ③ **회전**         — 「폐기하고 새로 발급」을 한 동작으로 묶는다. 둘로 두면
                         폐기만 하고 발급을 잊는 날 그 앱이 죽는다

★ 값은 **발급 순간 한 번만** 나간다 (D-204 · D-319)
---------------------------------------------------
`APIKey` 는 원문을 저장하지 않는다(sha256 해시만 있다). 그래서 잃어버린 키는
**되찾을 수 없고 회전만 가능하다.** 그것이 옳은 설계이고, 우리는 그 성질을 지킨다 —
조회에 값을 실어 주는 순간 그 값이 로그·화면·덤프로 흘러나간다.

표 ②의 어휘를 **빌려 쓴다. 표 ②에 넣지는 않는다** (D-337)
----------------------------------------------------------
표 ②(`credentials.py`)는 **환경변수에 있는 나가는 키**의 표다. 들어오는 키는
테넌트별 DB 행이므로 그 표에 들어갈 수 없다 — 넣으면 표 하나가 두 방향을 갖고,
그 순간 D-337 이 잡은 혼동이 표 안으로 들어온다.

빌려 오는 것은 **어휘**다: `api_type`(발급처가 부르는 이름) · `capability`(이 키로
할 수 있는 일) · 5값 상태. 같은 말로 말해야 화면·보고서가 두 방향을 나란히 보여 준다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from common.tenant_scope import TenantScope
from kernels.k5_trust.credentials import (ABSENT, ROTATED, TYPED, VERIFIED)

#: ★ 이 키가 무엇인가 — 표 ②의 `api_type` 자리. **발급처가 부르는 그 이름 그대로.**
#: 여기서 발급처는 우리다(우리가 남에게 준다). 그래서 계약 조항으로 이름을 댄다.
INBOUND_API_TYPE: str = "GuardianX 재난 이벤트 OpenAPI (계약 F-05)"

#: ★ 이 키로 **할 수 있는 일** — 표 ② `capability` 자리. **비울 수 없다.**
#:
#: 실측으로 적는다: 지금 이 키가 닿는 자리는 `common.access_gate.INBOUND_KEY_ALLOWED`
#: 하나가 정본이다. 여기에 문장으로 다시 적으면 두 벌이 되고 갈리므로,
#: `capability_now()` 가 **그 집합을 읽어서** 만든다 (D-286 — 문서가 거짓말을 시작하는 자리).
CAPABILITY_PREFIX: str = "읽기 전용 · 닿는 자리"

#: 발급 기본 수명(일). 무기한 키를 기본으로 두지 않는다 — 무기한 키는 폐기되지 않는다.
DEFAULT_EXPIRES_DAYS: int = 90


class InboundKeyNotFound(Exception):
    """그 키가 **내 테넌트에 없다.** 남의 키인지 없는 키인지 구별해 알리지 않는다(D-269)."""


@dataclass(frozen=True)
class InboundKeyView:
    """키 하나의 **사실.** 값이 없다 — 이 dataclass 에는 값 칸 자체가 없다.

    ★ "마스킹해서 저장" 은 저장이다(D-319). 여기에 칸이 있으면 언젠가 채워지고,
      채워진 값은 덤프·백업·화면·로그로 흘러나간다.
    """

    key_id: int
    name: str
    #: 앞 8자. 사람이 "그 키" 를 지목할 수 있을 만큼만. 이것으로는 인증되지 않는다.
    prefix: str
    api_type: str
    capability: str
    #: 표 ②의 5값 어휘. 아래 `_status` 가 무엇을 어떻게 옮겼는지 적혀 있다.
    status: str
    is_active: bool
    created_at: datetime | None
    last_used: datetime | None
    expires_at: datetime | None
    #: 테넌트. **키가 어느 고객의 것인지** — dj-core 는 이 칸을 모른다.
    group_id: int | None


@dataclass(frozen=True)
class IssuedKey:
    """발급 결과. **`secret` 이 사람에게 보이는 유일한 순간이다.**

    저장소·로그·감사에 이 값을 적지 않는다. 잃어버리면 회전한다 — 되찾기는 없고,
    되찾을 수 있으면 그것은 어딘가에 저장돼 있다는 뜻이다.
    """

    view: InboundKeyView
    secret: str


def _apikey_model():
    """dj-core 의 모델. **부르기만 한다** (§0.4)."""
    return apps.get_model("apikey_account", "APIKey")


def _capability_now() -> str:
    """이 키가 **지금 닿는 자리**. 미들웨어의 허용 집합에서 읽는다.

    ★ **비공개다.** 이것은 설비의 사실이고 테넌트의 사실이 아니라 `scope` 를 받을
      이유가 없는데, 커널 공개 면은 D-281 로 `scope` 를 **반드시** 받아야 한다.
      쓰지도 않을 `scope` 를 시그니처에 다는 것은 「테넌트마다 다른 답이 있다」는
      거짓 신호를 남기는 일이고, 다음 사람이 그 인자를 채우려다 없는 구별을 만든다.
      그래서 비공개로 두고, 밖에는 아래 `inbound_key_facts(*, scope)` 하나로 낸다 —
      그쪽은 **키 목록을 함께 내므로 scope 를 실제로 쓴다.**

    문장으로 따로 적지 않는 이유: 적으면 허용 집합이 바뀌는 날 이 문장만 옛말이 되고,
    **옛말이 된 문장은 옛말인 것이 안 보인다** (D-286).
    """
    from common.access_gate import INBOUND_KEY_ALLOWED

    routes = sorted(f"{m} {p}" for m, p in INBOUND_KEY_ALLOWED)
    return f"{CAPABILITY_PREFIX} {len(routes)}곳 — " + " · ".join(routes)


def _status(row) -> str:
    """표 ②의 5값으로 옮긴다. **옮긴 규칙을 여기 적는다** — 안 적으면 아무도 못 읽는다.

        absent    폐기됐거나 만료됐다 — **쓸 수 없는 키**. "없다" 와 같은 값으로 둔다:
                  살아 있지 않은 키를 `present` 로 두면 목록에서 살아 보인다
        typed     발급됐고 살아 있다. **무엇인지는 안다** — 우리가 발급했으므로
        verified  한 번이라도 실제로 쓰였다(`last_used`). 「발급됐다」와 「이 환경에서
                  동작한다」의 차이가 juso 사건이 가르친 그 차이다 (D-323)
        rotated   회전으로 대체됐다 — 아래 `rotate_key` 만이 이 값을 만든다

    `present` 는 **쓰지 않는다.** 표 ②에서 그것은 "파일에 값이 있으나 무슨 API 인지
    모른다" 는 뜻인데, 우리가 발급한 키에는 그런 상태가 없다. 없는 상태를 억지로
    채우면 그 칸이 곧 거짓이 된다 (D-290).
    """
    if not row.is_active:
        return ROTATED if (row.name or "").endswith(ROTATED_SUFFIX) else ABSENT
    if row.expires_at and timezone.now() > row.expires_at:
        return ABSENT
    return VERIFIED if row.last_used else TYPED


#: 회전으로 폐기된 키의 이름 꼬리표. 폐기와 회전을 **상태로 구별하기 위한 표식**이고,
#: 이름에 남기는 이유는 dj-core 의 표에 우리 칸을 더할 수 없기 때문이다(§0.4).
ROTATED_SUFFIX: str = f" [{ROTATED}]"


def _group_of(scope: TenantScope):
    """이 사람의 테넌트. 못 정하면 **키를 만지지 않는다.**"""
    # ★ **`require_user_group` 을 부른다** — `get_user_group`(있으면 준다) 이 아니다.
    #   둘의 차이가 이 함수의 전부다: 앞엣것은 소속이 없으면 `None` 을 주고, 그러면
    #   부르는 쪽이 그 `None` 을 어떻게든 처리하게 된다. 뒤엣것은 **멈춘다.**
    #   그리고 `common.tenant_filters` 의 진짜 문지기라 `verify_tenant_scope.py` 의
    #   호출 그래프 추적이 이것을 인정한다 — 표식이 아니라 실제로 막기 때문이다(P-K1-1).
    from common.tenant_filters import require_user_group

    if scope.is_system:
        raise PermissionDenied(
            "들어오는 키의 발급·폐기는 사람이 한다 — 시스템 스코프로 하지 않는다. "
            "주인 없는 키는 어느 테넌트의 것인지 아무도 모른다 (D-281)")
    return require_user_group(scope.actor)


def _scoped(scope: TenantScope):
    """**내 테넌트의 키만.** dj-core 에 없는 이 좁히기가 우리가 더하는 것의 전부다."""
    group = _group_of(scope)
    return _apikey_model().objects.filter(
        user__userprofilelink__group=group).distinct()


def _view(row, group_id: int | None = None) -> InboundKeyView:
    if group_id is None:
        # ★ 소속 판정을 **다시 구현하지 않는다** (D-212). `get_user_group` 한 곳만 부른다 —
        #   판정식 복사본 하나가 우회 지점 하나이고, 실제로 그 복사본이 이 저장소
        #   격리 사고의 원인이었다.
        from common.tenant_filters import get_user_group

        group_id = getattr(get_user_group(row.user), "pk", None)
    return InboundKeyView(
        key_id=row.pk,
        name=(row.name or "").replace(ROTATED_SUFFIX, ""),
        prefix=row.prefix,
        api_type=INBOUND_API_TYPE,
        capability=_capability_now(),
        status=_status(row),
        is_active=bool(row.is_active),
        created_at=row.created_at,
        last_used=row.last_used,
        expires_at=row.expires_at,
        group_id=group_id,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 네 동작 — 발급 · 폐기 · 회전 · 목록. **전부 테넌트 귀속** (D-360 ③)
# ═══════════════════════════════════════════════════════════════════════════
def inbound_key_facts(*, scope: TenantScope) -> dict:
    """★ 설정 화면이 읽는 **들어오는 키의 사실 한 묶음** (F-12 「API키」).

    셋을 함께 낸다: 무슨 API 인가(`api_type`) · 무엇을 할 수 있나(`capability`) ·
    지금 어떤 키가 있나(`keys`). 나눠 부르게 하면 화면이 셋 중 하나를 빠뜨리고,
    빠뜨린 것이 **capability** 이면 운영자는 이 키가 어디까지 닿는지 모른 채 발급한다.
    """
    return {
        "api_type": INBOUND_API_TYPE,
        "capability": _capability_now(),
        "keys": list_keys(scope=scope),
    }


def issue_key(*, scope: TenantScope, name: str,
              expires_days: int | None = DEFAULT_EXPIRES_DAYS) -> IssuedKey:
    """발급. **값은 지금 한 번만 나간다.**

    소유자는 `scope.actor` 다 — 발급받는 사람과 키의 주인을 갈라 두면 "누가 발급했나"
    와 "누구 키인가" 가 어긋나고, 어긋난 채로는 폐기할 사람을 못 찾는다.
    """
    _group_of(scope)                       # 소속 없으면 여기서 멈춘다
    if not (name or "").strip():
        raise ValueError(
            "이름 없는 키는 발급하지 않는다 — 폐기할 때 어느 키인지 못 고른다")
    if expires_days is not None and expires_days <= 0:
        raise ValueError(
            f"만료일이 {expires_days} 다 — 0 이하는 '무기한' 이 아니라 '이미 만료' 다. "
            f"무기한이 필요하면 expires_days=None 을 **명시**하라")

    APIKey = _apikey_model()
    row, secret = APIKey.create_key(scope.actor, name.strip(), expires_days)
    return IssuedKey(view=_view(row), secret=secret)


def revoke_key(*, scope: TenantScope, key_id: int) -> InboundKeyView:
    """폐기. **행을 지우지 않는다** — 지우면 "그 키가 언제까지 살아 있었나" 가 사라진다.

    사고 조사에서 필요한 것은 "지금 없다" 가 아니라 **"언제부터 없었나"** 다.
    """
    row = _get_or_404(scope, key_id)
    if row.is_active:
        row.deactivate()                   # dj-core 의 메서드를 **부른다** (§0.4)
        row.refresh_from_db()
    return _view(row)


def rotate_key(*, scope: TenantScope, key_id: int) -> IssuedKey:
    """회전 — **폐기와 발급을 한 동작으로.**

    둘로 두면 폐기만 하고 발급을 잊는 날 그 앱이 죽는다. 반대로 발급만 하고 폐기를
    잊으면 **낡은 키가 계속 산다** — 회전의 값은 그 둘을 못 잊게 하는 것이다.

    ★ 옛 키는 `ABSENT` 가 아니라 `ROTATED` 로 남는다. "폐기됐다" 와 "새것으로
      바뀌었다" 는 다른 사실이고, 뒤엣것은 **후속 키가 있다**는 뜻이다.
    """
    old = _get_or_404(scope, key_id)
    name = (old.name or "").replace(ROTATED_SUFFIX, "")
    expires_days = None
    if old.expires_at and old.created_at:
        expires_days = max(1, (old.expires_at - old.created_at).days)

    old.name = f"{name}{ROTATED_SUFFIX}"
    old.is_active = False
    old.save(update_fields=["name", "is_active"])
    return issue_key(scope=scope, name=name, expires_days=expires_days)


def list_keys(*, scope: TenantScope, include_inactive: bool = True
              ) -> list[InboundKeyView]:
    """목록 — **언제나 마스킹된 사실만.** 값은 나오지 않는다.

    폐기된 키를 기본으로 **포함한다**: 빼면 "폐기했다" 가 화면에서 "없었다" 와
    같은 그림이 되고, 그러면 폐기 이력을 아무도 못 읽는다 (D-290).
    """
    group = _group_of(scope)
    rows = _scoped(scope)
    if not include_inactive:
        rows = rows.filter(is_active=True)
    return [_view(row, group_id=group.pk) for row in rows.order_by("-created_at", "-id")]


def _get_or_404(scope: TenantScope, key_id: int):
    """내 테넌트의 그 키. 남의 것이면 **없는 것으로** 답한다 (D-269).

    403 을 내면 "있는데 못 만진다" 가 알려지고, 그것만으로 남의 테넌트에 그 id 가
    있다는 사실이 샌다.
    """
    row = _scoped(scope).filter(pk=key_id).first()
    if row is None:
        raise InboundKeyNotFound(f"키 #{key_id} 가 없다")
    return row


__all__ = [
    "INBOUND_API_TYPE",
    "DEFAULT_EXPIRES_DAYS",
    "InboundKeyNotFound",
    "InboundKeyView",
    "IssuedKey",
    "inbound_key_facts",
    "issue_key",
    "revoke_key",
    "rotate_key",
    "list_keys",
]
