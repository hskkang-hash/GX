# -*- coding: utf-8 -*-
"""역할 부여 요청 — **관리자에게 알림 1건** (P-105 · 2026-09-07 차선 B).

CPO 가 정한 것은 둘이다: 역할 0 계정이 닿는 화면 하나, 그리고 **관리자에게 알림 1건.**
이 파일이 뒤의 하나를 든다.

무엇을 「알림」으로 삼았나 — **로그가 아니라 행이다**
----------------------------------------------------
로그 한 줄은 관리자가 읽을 수 없다(컨테이너 안에 있고, 재기동하면 사라진다).
그래서 **감사 대장에 행을 쓴다** — `common.audit_writer` 가 이 저장소의 「쓰는 자리
하나」이고(D-212), 그 표는 관리자가 조회할 수 있으며 재기동을 넘어 남는다.

    logger_name = "guardianx.role_request"   ← 이 이름이 곧 「역할 요청함」이다
    outcome     = DENIED                 ← 「아직 못 들어왔다」는 사실 그대로
    username    = 요청한 사람
    note/reason = 어느 관리자에게 갔나

관리자는 `pending_requests()` 로 전건을 읽는다. 새 표도, 새 마이그레이션도 만들지
않았다 — **없는 표를 새로 만드는 것보다 있는 표에 이름을 붙이는 쪽**이 되돌리기 쉽다.

★ **1건이 계약이다** — 새로고침마다 1건은 계약 위반이다
-------------------------------------------------------
역할 대기 화면은 새로고침될 수 있고, 앞단은 이 문을 매번 부른다. 부를 때마다 알림이
나가면 관리자의 대장이 같은 사람으로 가득 찬다. 그래서 **이미 남아 있으면 다시 쓰지
않는다**(`already_sent=True`). 억제의 기준은 캐시가 아니라 **그 표 자신**이다 —
캐시는 재기동에 비고, 비면 억제가 풀린다.

★ 관리자를 어떻게 고르나 — **가까운 쪽부터**
---------------------------------------------
    ① 같은 테넌트의 운영자(`tenant_admin_<group_id>` 역할)  ← 실제로 부여할 수 있는 사람
    ② 전역 관리자(`common.tenant_roles.is_global_admin`)
    ③ 없으면 **없다고 말한다** (`source="none"`, 이름 빈 문자열)

③ 이 요점이다. 못 찾았을 때 아무 이름이나 지어 넣으면 화면이 **틀린 사람에게 연락하라**
고 말한다. 모르는 것은 모른다고 낸다(D-301 · D-290).

⚠ 판정식을 복사하지 않는다 — 전역 관리자인지의 답은 `common.tenant_roles` 만 낸다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

#: 감사 대장에서 이 계열을 가르는 이름. 집계는 이 값이 한다.
#:
#: ★ 접두 `guardianx.` 는 **고를 수 있는 값이 아니다** [실측 2026-09-07 · 처음에는
#:   `gx.role_request` 로 적었고 알림이 통째로 실패했다]:
#:       "감사 행 #1 를 못 찾았다 — 체인에 이을 수 없다.
#:        logger_name 이 'guardianx.' 로 시작하지 않는 행은 우리가 쓴 행이 아니다"
#:   `common/evidence_chain.py::CHAIN_PREFIX` 가 그 경계다(LAW-08). 접두가 다르면
#:   감사 쓰기 자체가 예외로 끝나고, 그러면 **알림이 남지 않는다.**
LOGGER_NAME = "guardianx.role_request"
#: 대장의 `api_name` 자리. 조회가 이 값으로 좁힌다.
ACTION = "role_request"
#: 사람이 로그를 눈으로 훑을 때 계열을 가르는 표시.
TAG = "[P-105]"
#: 채널 이름 — 응답이 이 값을 그대로 싣는다. 「어디로 갔나」를 화면이 말할 수 있게.
CHANNEL = "audit"


def _display_name(user) -> str:
    """사람이 읽을 이름. 없으면 계정명으로 떨어진다 — **비워 두지 않는다.**"""
    if user is None:
        return ""
    for attr in ("full_name", "display_name", "name"):
        value = getattr(user, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    first = (getattr(user, "first_name", "") or "").strip()
    last = (getattr(user, "last_name", "") or "").strip()
    if first or last:
        return (last + first).strip() if last and first else (first or last)
    return (getattr(user, "username", "") or "").strip()


def administrator_for(user) -> dict:
    """이 사람에게 역할을 줄 수 있는 관리자 한 명. **못 찾으면 없다고 낸다.**

    돌려주는 것은 화면이 그대로 읽는 dict 다:
        {"name": …, "username": …, "source": …}
    `source` 가 `"none"` 이면 이름이 빈 문자열이고, 그때 화면은 이름 없는 문장을 쓴다.

    ★ **주소(email)를 싣지 않는다.** [실측 2026-09-07 · 처음 만들 때는 실었다 —
      `admin@guardianx.com` 이 역할 0 계정에게 그대로 나갔다.] 이 화면의 계약은
      「관리자에게 **요청했습니다**」이지 「관리자에게 **연락하세요**」가 아니다.
      알림은 서버가 이미 보냈고, 사람이 주소를 쓸 일이 없다. 쓸 일 없는 남의 연락처를
      권한 0 계정에게 내주는 것은 이 절이 막으려는 바로 그 부류의 유출이다.
    """
    from common.tenant_roles import is_global_admin, tenant_admin_role_code

    def _as(candidate, source: str) -> dict:
        return {"name": _display_name(candidate),
                "username": (getattr(candidate, "username", "") or ""),
                "source": source}

    try:
        from django.contrib.auth import get_user_model

        model = get_user_model()

        # ① 같은 테넌트의 운영자 — **실제로 역할을 줄 수 있는 사람**이 먼저다.
        group = None
        try:
            from common.tenant_filters import get_user_group

            group = get_user_group(user)
        except Exception:  # pragma: no cover - 소속을 못 읽는 사용자 방어
            group = None
        if group is not None:
            code = tenant_admin_role_code(group.id)
            found = model.objects.filter(is_active=True, roles__code=code).first()
            if found is not None:
                return _as(found, "tenant_admin")

        # ② 전역 관리자. 판정은 `tenant_roles` 가 낸다 — 여기서 다시 세지 않는다.
        for candidate in model.objects.filter(is_active=True).order_by("id")[:200]:
            if is_global_admin(candidate):
                return _as(candidate, "global_admin")
    except Exception as exc:  # pragma: no cover - DB 를 못 읽는 판 방어
        logger.warning("[P-105] 관리자를 찾지 못했다 — %s", exc)

    # ③ **없다고 말한다.** 아무 이름이나 지어 넣지 않는다.
    #
    # ⚠ 여기 「설정에 적어 둔 이름」 단계를 두지 **않았다** [실측 2026-09-07 ·
    #   `verify_dormant.py` ㉢ 가 잡았다]. 기본값이 비면 그 분기는 한 번도 안 도는
    #   코드이고, 값을 채우면 화면이 **DB 가 아니라 설정 파일이 말하는 사람**에게
    #   연락하라고 말한다. 둘 다 원하지 않는다.
    return {"name": "", "username": "", "source": "none"}


def already_notified(user) -> bool:
    """이 계정에 대한 알림이 **이미 대장에 있는가.**

    억제의 기준을 캐시가 아니라 표로 둔다 — 캐시는 재기동에 비고, 비면 같은 사람이
    다시 알림을 만든다. 「알림 1건」이 계약이면 그 계약도 재기동을 넘어야 한다.
    """
    user_id = getattr(user, "pk", None)
    if user_id is None:
        return False
    try:
        from django.apps import apps

        model = apps.get_model("logger", "AuditLogs")
        return model._base_manager.filter(
            logger_name=LOGGER_NAME, api_name=ACTION, user_id=user_id).exists()
    except Exception as exc:  # pragma: no cover - 표를 못 읽는 판 방어
        logger.warning("[P-105] 알림 이력을 못 읽었다 — %s", exc)
        return False


def notify_admin(user, administrator: dict | None = None) -> dict:
    """관리자에게 알림 **1건**. 이미 있으면 다시 쓰지 않는다.

    돌려주는 dict 가 그대로 응답의 `notification` 이 된다:
        {"sent": bool, "already_sent": bool, "channel": str,
         "requested_at": iso8601, "error": str|None}

    ★ 실패를 **삼키지 않되 화면을 죽이지도 않는다.** 알림을 못 남겼으면
      `sent=False` + `error` 로 응답에 보인다 — 「보낸 적 없음」과 「보내려다 실패」가
      뭉개지지 않는다. 이 문의 목적은 사람에게 상태를 보여 주는 것이고, 알림이 실패한
      상태도 상태다.
    """
    now = datetime.now(timezone.utc).isoformat()
    admin = administrator if administrator is not None else administrator_for(user)

    if already_notified(user):
        return {"sent": False, "already_sent": True, "channel": CHANNEL,
                "requested_at": now, "error": None}

    to = admin.get("username") or admin.get("name") or "(관리자 미지정)"
    try:
        from common import audit_writer

        audit_writer.write(
            logger_name=LOGGER_NAME,
            tag=TAG,
            actor=user,
            action=ACTION,
            outcome=audit_writer.DENIED,
            reason=f"역할 부여 요청 — 수신 {to} (경로 {admin.get('source')})",
            api_name=ACTION,
            api_method="GET",
            status_http=403,
        )
    except Exception as exc:
        logger.warning("[P-105] 역할 요청 알림을 남기지 못했다 — %s", exc)
        return {"sent": False, "already_sent": False, "channel": CHANNEL,
                "requested_at": now, "error": str(exc)[:200]}

    logger.warning("%s 역할 부여 요청 — 계정 %s · 수신 %s",
                   TAG, getattr(user, "username", "?"), to)
    return {"sent": True, "already_sent": False, "channel": CHANNEL,
            "requested_at": now, "error": None}


def pending_requests(limit: int = 100) -> tuple:
    """관리자가 읽는 자리 — **누가 역할을 기다리고 있는가.**

    ⚠ 테넌트로 좁히지 않는다. 좁히는 판단은 부르는 쪽이 한다 — 여기서 좁히면
      「전건」이 조용히 부분집합이 된다(`audit_writer.read` 와 같은 규율).
    """
    from common import audit_writer

    return audit_writer.read(logger_name=LOGGER_NAME, action=ACTION, limit=limit)


def message_for(administrator: dict, has_roles: bool) -> str:
    """화면에 뜨는 한 줄. **서버가 짓는다** (GX-COPY 규칙 1).

    앞단이 문장을 만들면 사전과 화면이 갈라진다. 관리자를 못 찾았을 때 괄호 안이
    비지 않게, **이름이 없으면 이름 없는 문장**으로 간다.
    """
    if has_roles:
        return "역할이 부여되어 있습니다."
    name = (administrator or {}).get("name") or ""
    if name:
        return f"역할이 아직 없습니다 — 관리자({name})에게 역할 부여를 요청했습니다."
    return "역할이 아직 없습니다 — 관리자에게 역할 부여를 요청했습니다."
