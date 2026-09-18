# -*- coding: utf-8 -*-
"""API-03·04 — **들어오는 키의 범위(scope)** (턴 U · 차선 U56).

한 문장
-------
    D-335 가 잡은 것은 「인증은 성했고 **범위**가 없다」였다. 이 파일이 그 범위다.

왜 이름 넷뿐인가
----------------
    events:read      사건 목록·상세를 읽는다 (U6 #2·#3)
    pulse:read       카메라 맥박을 읽는다 (OPS-15 · U6 #15 곁)
    stats:read       통계·반출을 읽는다 (U24 가 세운 `stats/*`)
    webhooks:manage  구독·필터를 만지는 **유일한 쓰기** 이름

    더 짓지 않는다. 이름이 늘면 「무엇을 줄지」가 아니라 「이름이 뭐였지」가 되고,
    그때부터 발급자는 전부 주는 쪽으로 틀린다. 모르는 이름은 **422** 다 —
    조용히 버리면 발급자는 준 줄 알고 상대는 못 쓴다.

★ **기본은 최소다** — `DEFAULT_SCOPES` 는 `events:read` 하나다. 발급 문이 `scopes`
  를 안 주면 그 하나만 붙는다. 기본을 전부로 두면 D-335 가 그대로 돌아온다.

★ **없는 것과 빈 것은 다르다**
    행이 없다  = 이 키는 범위를 정한 적 없다(옛 키). 판정은 `UNSET` — **호출자가
                 정한다.** 이 파일이 「전부 허용」으로 메우지 않는다.
    scopes=[]  = 아무 데도 못 간다. 명시적 거절이다.

★ 판정식은 **하나**다 — `_required_scope_for_path` 가 경로 → 필요한 이름을 정하고,
  `assert_path_scope` 가 그것 하나만 본다(D-212). 라우트마다 손으로 적으면
  두 벌이 되고, 두 벌 중 하나는 반드시 잊힌다.

공개 면은 셋뿐이다 — 나머지는 **비공개다** (D-281 · 턴 U 병합)
--------------------------------------------------------------
    get_key_scopes(*, scope, key_id)            이 키의 범위를 읽는다
    set_key_scopes(*, scope, key_id, scopes)    이 키의 범위를 정한다
    assert_path_scope(*, scope, key_id, path)   이 키로 이 경로를 부를 수 있는가

★ 셋 다 `*, scope: TenantScope` 를 **필수로** 받고, 셋 다 `common.tenant_filters` 의
  진짜 문지기를 실제로 부른다(주석이 아니라 호출이다). 커널에서는 `@tenant_scoped` 를
  쓰지 않는다 — `request` 가 없어 표식만 남고 아무것도 안 막는다(착시 ①).

★ 글자를 이름으로 바꾸는 **순수 계산** 셋(`_normalize_scopes` · `_required_scope_for_path`
  · `_key_allows`)은 비공개다. 테넌트 자료를 만지지 않아 `scope` 를 쓸 데가 없는데,
  쓰지도 않을 `scope` 를 시그니처에 달면 「테넌트마다 다른 답이 있다」는 **거짓 신호**가
  남고 다음 사람이 그 인자를 채우려다 없는 구별을 만든다. 같은 이유로 `_capability_now`
  가 비공개가 됐다(D-367 · `inbound_keys.py`) — 그 선례를 그대로 따른다.

★ `request` 를 받는 함수가 커널에 없다. 커널은 HTTP 를 모른다 — 요청을 아는 자리는
  `common/inbound_api_key.py` 이고, 그 자리가 경로와 키 id 를 꺼내 `assert_path_scope`
  를 부른다(옛 `check_request_key_scope` 가 하던 일).
"""
from __future__ import annotations

from dataclasses import dataclass

from common.tenant_scope import TenantScope

#: ★ 이름의 **정본**. 모델에 choices 로 또 적지 않는다(D-212).
SCOPE_EVENTS_READ = "events:read"
SCOPE_PULSE_READ = "pulse:read"
SCOPE_STATS_READ = "stats:read"
SCOPE_WEBHOOKS_MANAGE = "webhooks:manage"

ALLOWED_SCOPES: frozenset[str] = frozenset({
    SCOPE_EVENTS_READ, SCOPE_PULSE_READ, SCOPE_STATS_READ, SCOPE_WEBHOOKS_MANAGE,
})

#: 발급 문이 `scopes` 를 안 줄 때 붙는 것. **가장 좁은 하나.**
DEFAULT_SCOPES: tuple[str, ...] = (SCOPE_EVENTS_READ,)

#: 「행이 없다」의 판정값. `True`/`False` 로 접지 않는다 — 접으면 옛 키가
#: 조용히 전부 열리거나(참) 하룻밤에 전부 죽는다(거짓). 부르는 쪽이 정한다.
UNSET = "unset"


class InvalidScopeName(ValueError):
    """모르는 범위 이름. **422** — 요청 본문이 틀렸다(400 이 아니라 값이 틀렸다)."""


class KeyScopeDenied(PermissionError):
    """이 키에는 그 범위가 없다. **403** — 인증은 성했고 권한이 없다(401 이 아니다)."""

    def __init__(self, required: str, granted: tuple[str, ...]):
        self.required = required
        self.granted = tuple(granted)
        super().__init__(
            "이 키에는 범위 %s 가 없습니다 — 지금 가진 범위: %s"
            % (required, ", ".join(self.granted) if self.granted else "없음"))


# ═══════════════════════════════════════════════════════════════════════════
# 경로 → 필요한 범위. **한 곳**이다 (D-212)
# ═══════════════════════════════════════════════════════════════════════════
#
# ⚠ 접두 대조는 **긴 것부터** 본다 — `/api/dsm/events` 가 `/api/dsm/events/…` 를
#   먼저 먹으면 더 좁은 규칙이 영영 안 걸린다.
PATH_SCOPES: tuple[tuple[str, str], ...] = (
    ("/api/dsm/settings/webhook-subscriptions", SCOPE_WEBHOOKS_MANAGE),
    ("/api/dsm/webhook-subscriptions", SCOPE_WEBHOOKS_MANAGE),
    ("/api/dsm/cameras/pulse", SCOPE_PULSE_READ),
    ("/api/dsm/stats", SCOPE_STATS_READ),
    ("/api/dsm/events", SCOPE_EVENTS_READ),
)


def _normalize_scopes(raw) -> tuple[str, ...]:
    """사람이 준 것을 이름 목록으로 만든다. 모르는 이름이 하나라도 있으면 **멈춘다.**

    받는 모양 셋: 목록 · 쉼표 문자열 · JSON 배열 문자열(화면이 그렇게 보낸다).
    빈 입력은 **빈 목록**이다 — 기본값으로 메우지 않는다(메우는 자리는 발급 문 하나다).

    ★ **비공개다** (턴 U 병합 · D-281). 글자를 이름으로 바꾸는 순수 계산이고 테넌트
      자료를 만지지 않는다 — 어느 테넌트가 물어도 답이 같다. 커널 공개 면은
      `*, scope: TenantScope` 를 반드시 받아야 하는데, 쓰지도 않을 `scope` 를 여기
      붙이는 것은 거짓 신호다(`_capability_now` 와 같은 판단 · D-367).
      밖으로는 `set_key_scopes` 하나로 낸다 — **검사하는 자리와 쓰는 자리가 같아야**
      「검사만 하고 안 쓴」 이름이 생기지 않는다.
    """
    if raw is None:
        return ()
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return ()
        if text.startswith("["):
            import json
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                raise InvalidScopeName("scopes 가 JSON 배열이 아닙니다: %s" % exc)
            if not isinstance(parsed, list):
                raise InvalidScopeName("scopes 는 배열이어야 합니다.")
            items = parsed
        else:
            items = text.split(",")
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        raise InvalidScopeName("scopes 의 모양을 모릅니다: %s" % type(raw).__name__)

    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise InvalidScopeName("범위 이름은 문자열이어야 합니다.")
        name = item.strip()
        if not name:
            continue
        if name not in ALLOWED_SCOPES:
            raise InvalidScopeName(
                "모르는 범위 이름입니다: %s — 있는 것은 %s"
                % (name, ", ".join(sorted(ALLOWED_SCOPES))))
        if name not in out:
            out.append(name)
    return tuple(out)


def _required_scope_for_path(path: str) -> str | None:
    """이 경로를 부르려면 어떤 범위가 있어야 하는가. 규칙 밖이면 `None`(범위 규칙 없음).

    ★ 비공개 — `PATH_SCOPES` 라는 **설비의 사실**을 읽는 순수 계산이고 테넌트 자료가
      아니다. 밖에서 필요한 것은 「이 경로에 어떤 이름이 필요한가」가 아니라
      「이 키로 이 경로를 부를 수 있는가」이고, 그 답은 `assert_path_scope` 가 낸다.
    """
    p = (path or "").split("?", 1)[0]
    for prefix, scope_name in PATH_SCOPES:
        if p == prefix or p.startswith(prefix + "/"):
            return scope_name
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 저장·조회 — 우리 표 `dsm_api_key_scope`
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class KeyScopeView:
    key_id: int
    #: 정해진 적 없으면 `None` — 빈 튜플(「아무 데도 못 감」)과 다르다.
    scopes: tuple[str, ...] | None

    @property
    def state(self) -> str:
        return UNSET if self.scopes is None else "set"


#: 이 표에 쓰는 목적 코드(설계서 §3 ③). `TenantModel` 이 빈 값을 DB 에서 거절한다.
_PURPOSE_CODE = "dsm.integration"


def _model():
    from django.apps import apps
    return apps.get_model("stream_monitors", "DsmApiKeyScope")


def _mine(scope: TenantScope):
    """**내 테넌트의 범위 행만.** 문지기를 실제로 부른다 — 주석이 아니라 호출이다.

    ★ 전에는 「dj-core `CustomManagerGroup` 이 스레드의 요청자 group 으로 `objects` 를
      좁힌다」는 **주석**뿐이었다. 그 암묵은 스레드에 요청이 없는 자리(배치 · 시험 ·
      커널 직접 호출)에서 조용히 사라지고, **사라진 것은 아무도 못 본다** — 그래서
      `filter_by_group_field` 를 손으로 부른다. 암묵을 명시로 바꾸면 게이트도 서고
      남의 테넌트 시험도 강해진다(C-3.1 2차 · D-281).
    """
    from common.tenant_filters import filter_by_group_field

    actor = scope.require_actor()      # 시스템 스코프로는 남의 범위를 못 읽는다
    return filter_by_group_field(_model().objects.all(), actor)


def _assert_key_is_mine(scope: TenantScope, key_id: int) -> None:
    """그 키가 **내 테넌트의 키인가.** 아니면 `InboundKeyNotFound`(→ 404).

    ★ 판정을 새로 짓지 않는다 — `list_keys` 가 이미 테넌트로 좁힌 목록을 낸다(D-212).
      `key_id` 는 dj-core 표의 pk 라 전역에서 유일하고, 그래서 남의 키에 대한 쓰기는
      「내 행이 없으니 새로 만든다」로 잘못 이어진다. 여기서 먼저 끊는다.
    """
    from kernels.k5_trust.inbound_keys import InboundKeyNotFound, list_keys

    for view in list_keys(scope=scope):
        if view.key_id == key_id:
            return
    raise InboundKeyNotFound(key_id)


def get_key_scopes(*, scope: TenantScope, key_id: int) -> KeyScopeView:
    """이 키의 범위. **행이 없으면 `None`** — 이 함수는 기본값으로 메우지 않는다.

    ★ 남의 테넌트 키는 「범위가 다르다」가 아니라 **「행이 없다」**로 보인다(UNSET).
      그리고 UNSET 은 `assert_path_scope` 에서 **거짓**이다 — 즉 남의 키로는 아무 데도
      못 간다. 존재 여부도 새지 않는다(D-269 와 같은 결).
    """
    row = _mine(scope).filter(key_id=key_id).first()
    return KeyScopeView(key_id=key_id,
                        scopes=None if row is None else tuple(row.scopes or ()))


def set_key_scopes(*, scope: TenantScope, key_id: int, scopes) -> KeyScopeView:
    """범위를 정한다(덮어쓴다). 모르는 이름이 있으면 `InvalidScopeName`.

    ★ 문지기 둘을 실제로 부른다: `require_user_group`(소유자를 못 정하면 **만들지
      않는다** — 주인 없는 행은 어느 테넌트 것인지 아무도 모른다) ·
      `filter_by_group_field`(남의 행은 애초에 안 잡힌다 — 쓰기 IDOR).
    ★ 만드는 자리를 `objects.create(...)` 로 둔다. 생성자로 만들고 `save()` 하면
      `key_id` 가 **어느 정적 판정기에도 쓰기로 안 보이고**, 실제로 그 상태에서
      `verify_dead_fields.py` 가 이 칸을 「쓰기 0곳」으로 냈다(D-304 · 착시 ⑥).
    ★ 남의 키에는 **`InboundKeyNotFound`** 다 — 없는 것과 같다(D-269). 이 한 줄이
      없으면 남의 키에 대한 쓰기가 유일 제약(`dsm_api_key_scope_one_live_per_key`)에
      부딪혀 `IntegrityError` 로 죽는다 [실측 · 턴 U 병합]. 범위는 지켜지지만 답이
      **DB 오류**이고, DB 오류는 라우트에서 500 이 된다 — 거부는 거부로 말해야 한다.
    """
    from common.tenant_filters import require_user_group

    names = _normalize_scopes(scopes)
    group = require_user_group(scope.require_actor())
    _assert_key_is_mine(scope, key_id)
    row = _mine(scope).filter(key_id=key_id).first()
    if row is None:
        _model().objects.create(group=group, purpose_code=_PURPOSE_CODE,
                                key_id=key_id, scopes=list(names))
    else:
        row.scopes = list(names)
        row.save(update_fields=["scopes"])
    return KeyScopeView(key_id=key_id, scopes=names)


def _key_allows(granted, required: str) -> bool:
    """`granted` 가 `required` 를 덮는가. `granted` 가 `None`(미설정)이면 **거짓**이다.

    ★ 미설정을 참으로 읽으면 옛 키가 전부 열린다 — D-335 가 잡은 그 상태로 돌아간다.
      정책은 이 파일이 아니라 `assert_path_scope` 한 곳에서 정한다(D-212).
    ★ 비공개 — 집합 하나를 보는 순수 계산이다(`scope` 를 쓸 데가 없다).
    """
    if granted is None:
        return False
    return required in set(granted)


def assert_path_scope(*, scope: TenantScope, key_id: int, path: str) -> None:
    """이 키로 이 경로를 부를 수 있는가. 아니면 `KeyScopeDenied`(403).

    ★ **키 갈래에서만** 부른다 — 사람(JWT)은 역할로 판정한다. 키에 범위를 씌우고
      사람에게도 씌우면 관제요원이 자기 화면을 못 연다.
    ★ `request` 를 받지 않는다 — **커널은 HTTP 를 모른다.** 옛 `check_request_key_scope`
      는 `request` 를 받아 `.path` 만 읽었고, 그래서 커널 안에 요청을 아는 자리가
      생겼다. 요청을 아는 자리는 `common/inbound_api_key.py` 하나다(D-335). 그쪽이
      경로와 키 id 를 꺼내 이것을 부른다.
    ★ 세 판정이 여기 모인다: **① 미설정(행 없음)은 거짓** — 옛 키도 남의 키도 못
      지나간다 · **② 범위 밖은 `KeyScopeDenied`** · **③ 규칙 밖 경로는 그냥 지나간다**
      (범위 규칙이 없는 경로에 없는 규칙을 지어내지 않는다).
    """
    required = _required_scope_for_path(path)
    if required is None:
        return                                   # 이 경로에는 범위 규칙이 없다
    granted = get_key_scopes(scope=scope, key_id=key_id).scopes
    if not _key_allows(granted, required):
        raise KeyScopeDenied(required, tuple(granted or ()))
