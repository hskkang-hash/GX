# -*- coding: utf-8 -*-
"""플랫폼 운영자 U0 — O-01·02·05~12 (명세 제목이 정본 · §7 플랫폼구조설계서).

턴 AO · WO-18 · 차선 N3 단독 소유 파일. `api_ops_an.py` 는 이 모듈의 함수를 HTTP 로
여는 얇은 문일 뿐이고, 실제 판단은 전부 여기 있다(D-212 — 판정 모양은 한 곳에서).

★ 새 DB 모델을 만들지 않는다 — **쓰기는 감사 로그(`logger.AuditLogs`)에 싣는다**
--------------------------------------------------------------------------------
`stream_monitors/services/response_clock.py` 가 이미 보여 준 방식이다: 대응 네 시각을
새 칸에 두지 않고 감사에서 접어 읽는다(D-333 — "새 표를 만들지 않는다"). 이 모듈도
같은 방식을 O-02(앱 설치)·O-06(인시던트)·O-09(테넌트 열람 요청)·O-12(시드 토글)에
쓴다 — `common.audit_writer.write()` 로 **매번 그 시점의 전체 스냅샷**을 `data_after` 에
싣고, 읽을 때는 같은 키(예: incident_id)로 가장 최근 행을 고른다. 새 모델 0 이므로
"새 모델은 차선당 ≤ 1"(공통 규약)을 아예 안 쓴다 — 다른 차선과 마이그레이션 번호
충돌도 없다.

★ dj-core 는 **호출만** 한다 (금지구역은 아니지만 소스가 이 저장소에 없다)
----------------------------------------------------------------------------
`user.UserGroup`(테넌트) · `user.CoreUser` · `user.UserProfileLink` · `role.Role` ·
`logger.AuditLogs` 는 전부 `pip install`된 `core` 패키지(사이트 패키지)가 정의한다 —
이 저장소 트리에 소스가 없다(`docker exec gx-shell python -c "import core.user, os;
print(os.path.dirname(core.user.__file__))"` → `/usr/local/lib/.../site-packages/core/user`).
그래서 "dj-core 수정 금지"는 자동으로 지켜진다 — 고칠 파일 자체가 없다. 이 모듈이
하는 일은 그 모델을 **ORM 으로 읽고**, 테넌트 관리자 발급 한 곳만 실제 생성 경로
(`POST /api/v1/user/create-user`, `core/api/v1/user.py::create_user`)를 **인프로세스로
호출**하는 것이다 — `stream_monitors/management/commands/seed_role_users.py` 머리말이
적어 둔 이유 그대로("시드는 규칙을 흉내 내지 않는다") 와 같은 원칙을 지키되, 실행
경로는 `django.test.Client`(WSGI 인프로세스 — 소켓을 열지 않는다. gunicorn 워커 안에서
자기 자신에게 실제 아웃바운드 HTTP 를 거는 것은 워커 고갈·교착의 위험이 있어 피했다)
를 쓴다. ORM 으로 `CoreUser.objects.create_user(...)` 를 직접 부르지 않는 이유는
`seed_role_users.py` 가 이미 적은 이유(중복 검사·기본 역할 대체·`UserSettings` 생성·
`ensure_complete_profile`·알림 채널 구독을 건너뛴다)와 같다.

무엇을 하지 않는가
------------------
· `is_global_admin` 판정을 다시 하지 않는다 — `common.tenant_roles` 한 곳만 부른다(D-212).
· 테넌트 데이터(카메라·이벤트 원문)를 이 모듈이 직접 읽지 않는다 — O-05 건강 보드는
  이미 있는 집계 파일(`docs/agent/evidence/D-373/monitor_last.json`)과 카메라 **대수**만
  읽는다(개별 이벤트 열람은 O-09 승인 전에는 0).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from django.apps import apps
from django.db.models import Q

from common import audit_writer
from common.tenant_roles import is_global_admin

# ═══════════════════════════════════════════════════════════════════════════
# 예외 — u5_an_service.py 와 같은 모양(D-212 · 이름만 이 파일 접두어)
# ═══════════════════════════════════════════════════════════════════════════
class OpsAnPermissionDenied(Exception):
    """U0(플랫폼 운영자)가 아니다."""


class OpsAnInputRejected(Exception):
    """입력이 완결 조건을 못 채운다(중복 · 형식 오류 등)."""


class OpsAnNotFound(Exception):
    """테넌트·설치·인시던트·요청 행이 없다."""


# ═══════════════════════════════════════════════════════════════════════════
# 공통 — U0 문지기 · 시각 · 감사 스냅샷 읽고 쓰기
# ═══════════════════════════════════════════════════════════════════════════
def _require_operator(actor: Any):
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise OpsAnPermissionDenied("인증이 필요합니다.")
    if not is_global_admin(actor):
        raise OpsAnPermissionDenied(
            "플랫폼 운영자(U0)만 접근할 수 있습니다 — 고객 테넌트 역할은 /ops/* 에 들어오지 않습니다(P-415).")
    return actor


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


#: docs 장부 루트 — 컨테이너 안에서는 `/docs`(README·gx-shell 실측), 없으면 회색으로
#: 답한다(지어내지 않는다). 값은 이 모듈 안의 상수 하나뿐이다 — 공용 settings.py 를
#: 이 차선이 고치면 남의 차선과 충돌하므로, 이 파일 안에 둔다.
DOCS_ROOT = Path(os.environ.get("GX_DOCS_ROOT", "/docs"))


def _read_json(*parts: str) -> tuple[dict | None, str]:
    path = DOCS_ROOT.joinpath(*parts)
    if not path.is_file():
        return None, str(path)
    try:
        return json.loads(path.read_text(encoding="utf-8")), str(path)
    except (ValueError, OSError):
        return None, str(path)


def _read_jsonl(*parts: str, limit: int = 100) -> tuple[list[dict], str]:
    path = DOCS_ROOT.joinpath(*parts)
    if not path.is_file():
        return [], str(path)
    rows: list[dict] = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return [], str(path)
    return rows[-limit:], str(path)


#: 이 차선이 쓰는 감사 계열 — 이름이 다른 것이 "어느 전건인가"를 가른다(D-212).
LOG_TENANTS = "guardianx.ops.tenants"
LOG_APPS = "guardianx.ops.apps"
LOG_INCIDENTS = "guardianx.ops.incidents"
LOG_SEED = "guardianx.ops.seed"
LOG_ACCESS = "guardianx.ops.tenant_access"
LOG_KEYS = "guardianx.ops.keys"

#: O-09 "운영자 행위 전건"이 훑는 계열 전부.
ALL_OPS_LOGGERS = (LOG_TENANTS, LOG_APPS, LOG_INCIDENTS, LOG_SEED, LOG_ACCESS, LOG_KEYS)


def _audit(actor: Any, logger_name: str, tag: str, action: str, reason: str,
          before: Any = None, after: Any = None) -> None:
    audit_writer.write(
        logger_name=logger_name, tag=tag, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, before=before, after=after,
        api_name=action,
    )


def _audit_rows(logger_name: str, action_prefix: str | None = None) -> list[dict]:
    """이 계열의 감사 행을 **오래된 것 → 최신 순**으로, `data_after` 스냅샷에
    부가 칸(`_audit_id`·`_actor`·`_at`)을 얹어 돌려준다.
    """
    Model = apps.get_model("logger", "AuditLogs")
    qs = Model._base_manager.filter(logger_name=logger_name).order_by("id")
    if action_prefix:
        qs = qs.filter(api_name__startswith=action_prefix)
    out: list[dict] = []
    for r in qs:
        after = r.data_after
        if not isinstance(after, dict):
            continue
        row = dict(after)
        row["_audit_id"] = r.id
        row["_actor"] = r.username or ""
        row["_at"] = r.create_datetime.isoformat() if r.create_datetime else None
        row["_action"] = r.api_name or ""
        out.append(row)
    return out


def _latest_by_key(rows: list[dict], key_fn) -> list[dict]:
    """같은 키(예: incident_id)가 여러 번 나오면 **가장 최근(마지막) 것만** 남긴다.
    `rows` 는 이미 오래된 것 → 최신 순이어야 한다(`_audit_rows` 가 그렇게 준다).
    """
    latest: dict[Any, dict] = {}
    for row in rows:
        latest[key_fn(row)] = row
    return list(latest.values())


# ═══════════════════════════════════════════════════════════════════════════
# 테넌트(UserGroup) 읽기 — dj-core 모델을 **읽기만**
# ═══════════════════════════════════════════════════════════════════════════
def _UserGroup():
    return apps.get_model("user", "UserGroup")


def _CoreUser():
    return apps.get_model("user", "CoreUser")


def _UserProfileLink():
    return apps.get_model("user", "UserProfileLink")


def _Department():
    return apps.get_model("user", "Department")


def _split_departments(raw: str) -> list[str]:
    """쉼표로 가른 부서 이름 — 빈 이름·중복은 버린다(입력 순서 유지)."""
    out: list[str] = []
    for part in (raw or "").split(","):
        name = part.strip()
        if name and name not in out:
            out.append(name)
    return out


def _Role():
    return apps.get_model("role", "Role")


def _get_tenant(code: str):
    tenant = _UserGroup()._base_manager.filter(code=code).first()
    if tenant is None:
        raise OpsAnNotFound("테넌트 코드 %r 를 찾을 수 없습니다." % code)
    return tenant


def _tenant_created_at(tenant) -> datetime | None:
    return getattr(tenant, "created_on", None) or getattr(tenant, "modified_on", None)


# ═══════════════════════════════════════════════════════════════════════════
# O-01 — 테넌트 발급
# ═══════════════════════════════════════════════════════════════════════════
def list_tenants(actor: Any) -> dict:
    _require_operator(actor)
    UserGroup = _UserGroup()
    UPL = _UserProfileLink()
    rows = []
    for g in UserGroup._base_manager.all().order_by("id"):
        member_count = UPL._base_manager.filter(group_id=g.id).count()
        settings = g.settings if isinstance(g.settings, dict) else {}
        rows.append({
            "tenant_code": g.code,
            "name": g.name,
            "member_count": member_count,
            "public_url": settings.get("public_url", ""),
            "domain": settings.get("domain", ""),
            "issued_via_ops": bool(settings.get("issued_via_ops")),
            #: [턴 AQ · N2] 계층 — 시도(settings.region) → 시군구(이 테넌트) → 부서
            #:   (user.Department · group=이 테넌트). 화면 테넌트 표가 그대로 그린다.
            "region": settings.get("region", ""),
            "departments": [d.department_name for d in
                            _Department()._base_manager.filter(group_id=g.id).order_by("id")],
            "created_at": _tenant_created_at(g).isoformat() if _tenant_created_at(g) else None,
        })
    return {"tenants": rows, "count": len(rows)}


#: [턴 AP · P-427 ⑤ · 차선 N3] 대행 호출(아래 `issue_tenant` 의 `auth_header`)이
#: 실어 나를 수 있는 U0 자격의 **나이 상한**. 청구 ⑤(턴 AO)가 "이미 인증된 U0 의
#: 대행 · 새 구멍 아님"이라 판단했지만, 그 판단은 **자격이 언제 발급됐는지**를
#: 묻지 않았다 — 가로챈 지 오래된 Authorization 헤더도 그대로 안쪽 호출을 지난다.
#: 이 상한이 그 창을 좁힌다: U0 이 이 절을 부르기 **15분 전 이내에 로그인한
#: 자격**만 대행에 쓴다. 200분짜리 액세스 토큰(`NINJA_JWT.ACCESS_TOKEN_LIFETIME`)
#: 전체를 대행 창으로 열어 두지 않는다.
PROXY_FRESHNESS_LIMIT_SECONDS = 15 * 60

#: 감사 action — 시간 제한 위반으로 대행을 거절한 줄. `issue`(성공)와 다른
#: 이름으로 둬서, 감사 화면에서 「거절된 대행 시도」를 따로 셀 수 있다.
LOG_TENANTS_PROXY_DENIED_ACTION = "issue_denied_stale_proxy"


def _forwarded_auth_age_seconds(auth_header: str) -> float | None:
    """대행에 실어 보내는 U0 자격이 **발급된 지 몇 초 됐는가.** 못 읽으면 `None`
    (신선함을 증명할 수 없으므로 신선하지 않은 것으로 다룬다 — D-301 과 같은 결).

    `ninja_jwt.tokens.AccessToken(token)` 로 서명·구조를 함께 검사한다(서명이
    틀리거나 구조가 깨진 토큰은 여기서 예외가 나 `None` 이 된다 — 지어낸 나이를
    내지 않는다).
    """
    token = (auth_header or "").strip()
    if token.lower().startswith("bearer "):
        token = token[len("bearer "):].strip()
    if not token:
        return None
    try:
        from ninja_jwt.tokens import AccessToken

        decoded = AccessToken(token)
        iat = decoded.get("iat")
        if iat is None:
            return None
        issued_at = datetime.fromtimestamp(int(iat), tz=timezone.utc)
    except Exception:                                            # noqa: BLE001
        return None
    return (_now() - issued_at).total_seconds()


def issue_tenant(actor: Any, *, code: str, name: str, admin_username: str,
                 admin_email: str, admin_password: str, region: str = "",
                 public_url: str = "", domain: str = "", auth_header: str = "",
                 departments: str = "") -> dict:
    """테넌트(시군구) 생성 + 초기 관리자 1 — O-01.

    ★ [턴 AQ · 차선 N2] `departments` — 쉼표로 가른 부서 이름. 계층(시도 →
      시군구 → 부서)의 셋째 층을 dj-core `user.Department`(group=이 테넌트)
      행으로 **실제로 만든다**(시도는 `region` 칸 · 시군구는 테넌트 자신).
      비우면 부서 0 — 기본 부서를 지어 넣지 않는다.

    완결 조건("테넌트 관리자가 로그인 → 역할 홈")은 이 함수가 스스로 증명하지 않는다
    — 이 함수는 **발급**만 하고, 그 관리자로 실제 `/api/v1/auth/login` 을 두드려
    역할 홈에 닿는지는 부르는 쪽(시험)이 잇따라 확인한다(발급과 로그인은 다른 행위).

    ★ `auth_header` — **바깥 요청의 Authorization 을 그대로 물려준다** [실측
      2026-09-30 · `common/access_gate.py::AccessGateMiddleware`]. `POST
      /api/v1/user/create-user` 는 dj-core 원본에 권한 검사가 **한 줄도 없는**
      알려진 구멍이라(주석 "문서엔 Requires admin privileges, 코드엔 그 검사가
      없다") 이 저장소가 전역 관문에서 **자격증명이 아예 없는 요청만** 막아
      뒀다(`AUTHN_REQUIRED_PATHS`). 우리는 이미 `_require_operator` 를 지난
      U0 이므로, 그 자격증명(바깥 요청의 Authorization 헤더)을 안쪽 호출에
      그대로 실어 관문을 "새 익명 구멍"이 아니라 "이미 인증된 U0 의 대행"으로
      지난다 — 새 세션을 만들지 않는다(actor 의 세션 토큰을 안 건드린다).

    ★ [턴 AP · P-427 ⑤] **재확인 셋** — 턴 AO 의 청구 ⑤(`docs/agent/evidence/
      SPEC/O-01_proxy_review.md`)에 답한다:
        ① **U0 만** — 이 함수 첫 줄 `_require_operator(actor)` 가 이미 막는다
           (바뀌지 않았다 — 재확인).
        ② **감사 줄 1** — 성공하면 아래 `_audit(... "issue" ...)` 가 1줄(기존
           그대로). **이 턴이 더한 것**: 시간 제한 위반으로 거절해도 감사 줄이
           남는다(`issue_denied_stale_proxy`) — 거절도 흔적을 남겨야 "누가
           언제 대행을 시도했다 막혔다"를 되짚을 수 있다.
        ③ **시간 제한(15분)** — **이 턴이 새로 더한 것.** `auth_header` 가
           있으면 `_forwarded_auth_age_seconds()` 로 그 자격의 나이를 재고,
           `PROXY_FRESHNESS_LIMIT_SECONDS`(900초)를 넘으면 대행을 **거절**한다
           (`OpsAnPermissionDenied`). 나이를 못 읽어도(서명 불량·`iat` 없음)
           신선하지 않은 것으로 본다 — 모르면 통과시키지 않는다.
    """
    _require_operator(actor)
    code = (code or "").strip()
    name = (name or "").strip()
    admin_username = (admin_username or "").strip()
    if not code or not name or not admin_username or not admin_email or not admin_password:
        raise OpsAnInputRejected("code·name·admin_username·admin_email·admin_password 는 비울 수 없습니다.")

    #: [턴 AP · P-427 ⑤] 대행에 쓸 자격이 있으면 **신선함부터** 확인한다 — 테넌트를
    #: 만들기 전에 거절해야, 거절된 시도가 half-created 테넌트를 안 남긴다.
    if auth_header:
        age = _forwarded_auth_age_seconds(auth_header)
        if age is None or age > PROXY_FRESHNESS_LIMIT_SECONDS:
            _audit(actor, LOG_TENANTS, "[OPS-TENANT]", LOG_TENANTS_PROXY_DENIED_ACTION,
                  "대행 호출 거절 — 자격 나이 %s (제한 %d초)"
                  % ("모름" if age is None else "%.0f초" % age,
                     PROXY_FRESHNESS_LIMIT_SECONDS),
                  after={"tenant_code": code,
                        "auth_age_seconds": age,
                        "limit_seconds": PROXY_FRESHNESS_LIMIT_SECONDS})
            raise OpsAnPermissionDenied(
                "테넌트 발급 대행 호출은 %d분 이내에 로그인한 자격만 씁니다 — "
                "다시 로그인한 뒤 시도하세요."
                % (PROXY_FRESHNESS_LIMIT_SECONDS // 60))

    UserGroup = _UserGroup()
    if UserGroup._base_manager.filter(code=code).exists():
        raise OpsAnInputRejected("테넌트 코드 %r 는 이미 발급돼 있습니다." % code)
    CoreUser = _CoreUser()
    if CoreUser._base_manager.filter(username=admin_username).exists():
        raise OpsAnInputRejected("관리자 계정 %r 는 이미 있습니다." % admin_username)

    tenant = UserGroup._base_manager.create(
        name=name, code=code,
        settings={"public_url": public_url, "domain": domain, "region": region,
                 "issued_via_ops": True, "issued_at": _now_iso()},
    )

    Role = _Role()
    admin_role, _created = Role._base_manager.get_or_create(
        code="admin", defaults={"role_name": "admin"})

    from django.test import Client  # 인프로세스 WSGI — 실제 소켓을 열지 않는다(머리말)

    client = Client(enforce_csrf_checks=False)
    payload = {
        "username": admin_username, "email": admin_email, "password": admin_password,
        "is_active": True, "roles": [admin_role.id], "group_id": tenant.id,
        "employee_id": "GX-OPS-TENANT-%s" % code, "is_default": True,
    }
    extra = {"HTTP_AUTHORIZATION": auth_header} if auth_header else {}
    resp = client.post("/api/v1/user/create-user", data=json.dumps(payload),
                       content_type="application/json", **extra)
    if resp.status_code not in (200, 201):
        tenant.delete()
        raise OpsAnInputRejected(
            "초기 관리자 발급이 실패했습니다(status=%s) — 테넌트 발급을 되돌립니다."
            % resp.status_code)

    Department = _Department()
    dept_names = _split_departments(departments)
    for i, dept_name in enumerate(dept_names, start=1):
        Department._base_manager.create(
            department_name=dept_name, code="%s-%02d" % (code, i), group_id=tenant.id)

    after = {"tenant_code": code, "tenant_id": tenant.id, "name": name,
             "admin_username": admin_username, "admin_role": "admin",
             "region": region, "departments": dept_names, "issued_at": _now_iso()}
    _audit(actor, LOG_TENANTS, "[OPS-TENANT]", "issue", "테넌트 발급 · 초기 관리자 1",
          after=after)
    return after


# ═══════════════════════════════════════════════════════════════════════════
# O-02 — 앱 설치·버전
# ═══════════════════════════════════════════════════════════════════════════
def list_app_installs(actor: Any, tenant_code: str | None = None) -> dict:
    _require_operator(actor)
    rows = _audit_rows(LOG_APPS)
    latest = _latest_by_key(rows, key_fn=lambda r: (r.get("tenant_code"), r.get("app_code")))
    if tenant_code:
        latest = [r for r in latest if r.get("tenant_code") == tenant_code]
    marks = _marked_counts()
    return {"installs": latest, "count": len(latest), "marked": marks["marked"],
            "marked_probe": marks["probe"], "marked_seed": marks["seed"]}


def _marked_counts() -> dict:
    """P-453 「표식됨 N」 — 곁표 `common.BillingMark` 에서 `probe`·`seed` 로 적힌 줄 수.

    유령 시드는 **지우지 않고 표식한다**(지우는 것은 대표). 이 수는 그 곁표를 그대로
    센다 — 새 저장소 0 · 가리키는 행은 안 건드린다. 곁표를 못 읽으면 0 이 아니라
    None(못 쟀다)을 돌려 화면이 「못 쟀다」로 그린다(D-301).
    """
    none = {"marked": None, "probe": None, "seed": None}
    try:
        from common.billing_marks import NOT_COUNTED_SOURCES, SEED_SOURCE, _mark_model

        Mark = _mark_model()
        if Mark is None:
            return none
        probe = Mark._base_manager.filter(data_source=NOT_COUNTED_SOURCES[0]).count()
        seed = Mark._base_manager.filter(data_source=SEED_SOURCE).count()
        return {"marked": probe + seed, "probe": probe, "seed": seed}
    except Exception:  # noqa: BLE001
        return none


def install_app(actor: Any, *, tenant_code: str, app_code: str, version: str) -> dict:
    _require_operator(actor)
    if not app_code or not version:
        raise OpsAnInputRejected("app_code·version 은 비울 수 없습니다.")
    tenant = _get_tenant(tenant_code)

    rows = _audit_rows(LOG_APPS)
    existing = [r for r in rows
               if r.get("tenant_code") == tenant_code and r.get("app_code") == app_code]
    #: ★ 완결 조건 "시드 대장 0 충돌" — **같은 테넌트·같은 앱에 같은 버전이 이미
    #:   active 로 서 있는데 또 설치하면** 충돌이다(행이 둘로 갈려 "설치 상태가
    #:   무엇인가"에 답이 두 개가 된다). 다른 버전이면 업그레이드로 받는다(충돌 아님).
    if existing and existing[-1].get("status") == "active" and existing[-1].get("version") == version:
        raise OpsAnInputRejected(
            "%s 에 %s %s 는 이미 설치돼 있습니다(시드 대장 충돌 방지)."
            % (tenant_code, app_code, version))

    after = {"tenant_code": tenant_code, "tenant_group_id": tenant.id, "app_code": app_code,
             "version": version, "status": "active", "installed_at": _now_iso(),
             "upgraded_from": (existing[-1].get("version") if existing else None)}
    _audit(actor, LOG_APPS, "[OPS-APP]", "install:%s" % app_code,
          "%s 에 %s %s 설치" % (tenant_code, app_code, version), after=after)
    return after


def set_app_status(actor: Any, *, tenant_code: str, app_code: str, status: str) -> dict:
    _require_operator(actor)
    if status not in ("active", "inactive"):
        raise OpsAnInputRejected("status 는 active·inactive 만 받습니다.")
    rows = _audit_rows(LOG_APPS)
    existing = [r for r in rows
               if r.get("tenant_code") == tenant_code and r.get("app_code") == app_code]
    if not existing:
        raise OpsAnNotFound("%s 에 설치된 %s 가 없습니다." % (tenant_code, app_code))
    current = dict(existing[-1])
    current["status"] = status
    current["updated_at"] = _now_iso()
    _audit(actor, LOG_APPS, "[OPS-APP]", "status:%s" % app_code,
          "%s 의 %s 상태를 %s 로" % (tenant_code, app_code, status), after=current)
    return current


# ═══════════════════════════════════════════════════════════════════════════
# O-05 — 건강 보드(전 테넌트) — 이미 있는 집계만 읽는다(새 저장 0)
# ═══════════════════════════════════════════════════════════════════════════
def _front_door_snapshot() -> dict:
    from common import front_door_counter

    return front_door_counter.snapshot()


def health_board(actor: Any) -> dict:
    """건강 보드(전 테넌트) — O-05.

    ★ 완결 조건은 **설명 칸의 일곱(카메라 맥박·큐 지연·5xx·저장 %·백업 회수증·
      생존 알림·게이트 16 색)이 아니라, §7 표 자신의 "완결 조건" 칸** — "테넌트 수
      = 보드 행 수 · 빨강 → 인시던트 자동 생성" 이다(명세 원문 §7 · P-417 "명세
      제목이 정본"). 이 함수는 그 둘을 **둘 다** 실측한다: 행 하나 = `UserGroup.
      objects.all()` 그대로(테넌트를 거르지 않는다) · 빨강이면 `open_incident()`
      를 **그대로 재사용**(O-06 과 새 판정식을 두 벌 두지 않는다, D-212)해서 실제
      인시던트를 연다 — 이미 열린 것이 있으면 또 열지 않는다(같은 빨강이 매초
      인시던트를 복제하면 "자동 생성"이 사고가 된다).
    """
    _require_operator(actor)
    monitor, monitor_path = _read_json("agent", "evidence", "D-373", "monitor_last.json")
    backup, backup_path = _read_json("agent", "evidence", "D-373", "backup_last.json")
    signals = ((monitor or {}).get("report") or {}).get("signals", {}) if monitor else {}
    heartbeat = ((monitor or {}).get("report") or {}).get("heartbeat_late") if monitor else None

    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    UserGroup = _UserGroup()
    open_incidents = _latest_by_key(_audit_rows(LOG_INCIDENTS), key_fn=lambda r: r.get("incident_id"))
    rows = []
    for g in UserGroup._base_manager.all().order_by("id"):
        total = StreamMonitor._base_manager.filter(group_id=g.id).count()
        active = StreamMonitor._base_manager.filter(group_id=g.id, is_active=True).count()
        color = "red" if (total > 0 and active == 0) else (
            "red" if (monitor and (heartbeat or {}).get("verdict") == "ALARM") else "green")
        auto_incident_id = None
        if color == "red":
            already_open = [
                r for r in open_incidents
                if r.get("tenant_code") == g.code and r.get("app_code") == "dsm"
                and r.get("status") in ("open", "acknowledged", "escalated")
                and r.get("summary", "").startswith("[건강 보드 자동]")
            ]
            if already_open:
                auto_incident_id = already_open[-1]["incident_id"]
            else:
                why = ("카메라 %d대 중 활성 0" % total if (total > 0 and active == 0)
                      else "생존 알림(heartbeat) ALARM")
                opened = open_incident(
                    actor, tenant_code=g.code, app_code="dsm", severity="critical",
                    summary="[건강 보드 자동] %s" % why)
                auto_incident_id = opened["incident_id"]
        rows.append({
            "tenant_code": g.code,
            "name": g.name,
            "cameras": {"active": active, "total": total},
            "queue_lag_sec": (signals.get("audit_queue_lag_sec") or {}).get("value")
                if monitor else None,
            "storage_used_pct": (signals.get("storage_used_pct") or {}).get("value")
                if monitor else None,
            "backup_receipt_at": (backup or {}).get("measured_at") if backup else None,
            "backup_verdict": (backup or {}).get("verdict") if backup else None,
            "survival_alert_late": (heartbeat or {}).get("value") if heartbeat else None,
            "color": color,
            "auto_incident_id": auto_incident_id,
        })
    return {
        "tenants": rows, "tenant_count": len(rows),
        "monitor_source": monitor_path, "monitor_read": monitor is not None,
        "backup_source": backup_path, "backup_read": backup is not None,
        #: ★ 정직하게 비운다 — 설명 칸의 일곱 중 둘은 이 차선이 못 잰다
        #:   (D-274·P-418 「무엇이 없는가」). 완결 조건(위 docstring)에는 없다.
        #: [턴 AR · N1] 5xx 는 앞문 응답 카운터(`common/front_door_counter.py` · 새 저장소 0)가
        #: 서버에서 센다. 못 재면 `measured=False` 가 그대로 나간다(0 으로 덮지 않는다).
        "front_door": _front_door_snapshot(),
        "not_measured": {
            "gate_16_colors": "ga_readiness.yaml 의 절별 색은 있으나 '게이트 16색'"
                              "(테넌트별 게이트 격자)은 이번 턴에 안 붙였다 — 무엇이 없는가로 남긴다.",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# O-06 — 인시던트 (접수 → 1차 대응 → 에스컬레이션 → 종결)
# ═══════════════════════════════════════════════════════════════════════════
_KST = timezone(timedelta(hours=9))


def _snap_to_business_start(dt: datetime) -> datetime:
    dt = dt.astimezone(_KST)
    while True:
        if dt.weekday() >= 5:  # 토(5)·일(6)
            dt = (dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            continue
        if dt.hour < 9:
            dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
            return dt
        if dt.hour >= 18:
            dt = (dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            continue
        return dt


def business_hours_deadline(start: datetime, hours: float) -> datetime:
    """영업일 09:00~18:00(KST) 기준 `hours` 시간 뒤 시각 — O-06 1차 대응(4시간)."""
    cur = _snap_to_business_start(start)
    remaining = hours
    while remaining > 0:
        day_end = cur.replace(hour=18, minute=0, second=0, microsecond=0)
        available = (day_end - cur).total_seconds() / 3600.0
        if available >= remaining:
            cur = cur + timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= available
            cur = _snap_to_business_start(cur + timedelta(days=1))
    return cur.astimezone(timezone.utc)


def business_days_deadline(start: datetime, days: int) -> datetime:
    """영업일 기준 `days`일 뒤 시각 — O-06 에스컬레이션(1영업일)."""
    cur = _snap_to_business_start(start)
    added = 0
    while added < days:
        cur = _snap_to_business_start(cur + timedelta(days=1))
        added += 1
    return cur.astimezone(timezone.utc)


def _incident_current(incident_id: str) -> dict | None:
    rows = _audit_rows(LOG_INCIDENTS)
    mine = [r for r in rows if r.get("incident_id") == incident_id]
    return mine[-1] if mine else None


def list_incidents(actor: Any, tenant_code: str | None = None, status: str | None = None) -> dict:
    _require_operator(actor)
    rows = _audit_rows(LOG_INCIDENTS)
    latest = _latest_by_key(rows, key_fn=lambda r: r.get("incident_id"))
    if tenant_code:
        latest = [r for r in latest if r.get("tenant_code") == tenant_code]
    if status:
        latest = [r for r in latest if r.get("status") == status]
    latest.sort(key=lambda r: r.get("opened_at") or "", reverse=True)
    return {"incidents": latest, "count": len(latest)}


def open_incident(actor: Any, *, tenant_code: str, app_code: str, severity: str,
                  summary: str) -> dict:
    _require_operator(actor)
    if severity not in ("critical", "major", "minor"):
        raise OpsAnInputRejected("severity 는 critical·major·minor 만 받습니다.")
    _get_tenant(tenant_code)  # 존재 확인
    incident_id = uuid.uuid4().hex[:12]
    opened_at = _now()
    after = {
        "incident_id": incident_id, "tenant_code": tenant_code, "app_code": app_code,
        "severity": severity, "summary": summary, "status": "open",
        "opened_at": opened_at.isoformat(),
        "sla_first_response_due": business_hours_deadline(opened_at, 4).isoformat(),
        "sla_escalation_due": business_days_deadline(opened_at, 1).isoformat(),
        "acknowledged_at": None, "escalated_at": None, "closed_at": None,
        "cause": "", "prevention": "", "closing_report": "",
    }
    _audit(actor, LOG_INCIDENTS, "[OPS-INC]", "open",
          "인시던트 접수 · %s · %s" % (tenant_code, severity), after=after)
    return after


def respond_incident(actor: Any, *, incident_id: str, note: str = "") -> dict:
    """1차 대응 — "조치 중"으로 넘긴다(완결 조건의 SLA 시계 절반)."""
    _require_operator(actor)
    current = _incident_current(incident_id)
    if current is None:
        raise OpsAnNotFound("인시던트 %r 를 찾을 수 없습니다." % incident_id)
    if current.get("status") != "open":
        raise OpsAnInputRejected("이미 %r 상태입니다 — open 만 조치 중으로 넘길 수 있습니다."
                                 % current.get("status"))
    current = dict(current)
    current["status"] = "acknowledged"
    current["acknowledged_at"] = _now_iso()
    current["response_note"] = note
    _audit(actor, LOG_INCIDENTS, "[OPS-INC]", "respond", "1차 대응 시작 — %s" % note,
          after=current)
    return current


def escalate_incident(actor: Any, *, incident_id: str, note: str = "") -> dict:
    _require_operator(actor)
    current = _incident_current(incident_id)
    if current is None:
        raise OpsAnNotFound("인시던트 %r 를 찾을 수 없습니다." % incident_id)
    if current.get("status") not in ("open", "acknowledged"):
        raise OpsAnInputRejected("이미 %r 상태입니다." % current.get("status"))
    current = dict(current)
    current["status"] = "escalated"
    current["escalated_at"] = _now_iso()
    current["escalation_note"] = note
    _audit(actor, LOG_INCIDENTS, "[OPS-INC]", "escalate", "2차 에스컬레이션 — %s" % note,
          after=current)
    return current


def close_incident(actor: Any, *, incident_id: str, cause: str, prevention: str) -> dict:
    _require_operator(actor)
    if not cause:
        raise OpsAnInputRejected("cause(원인) 없이 종결할 수 없습니다.")
    current = _incident_current(incident_id)
    if current is None:
        raise OpsAnNotFound("인시던트 %r 를 찾을 수 없습니다." % incident_id)
    if current.get("status") == "closed":
        raise OpsAnInputRejected("이미 종결됐습니다.")
    current = dict(current)
    current["status"] = "closed"
    current["closed_at"] = _now_iso()
    current["cause"] = cause
    current["prevention"] = prevention
    current["closing_report"] = (
        "인시던트 %s — %s/%s(%s) 종결. 원인: %s. 재발 방지: %s."
        % (incident_id, current.get("tenant_code"), current.get("app_code"),
           current.get("severity"), cause, prevention))
    _audit(actor, LOG_INCIDENTS, "[OPS-INC]", "close", "종결 · 원인 기록", after=current)
    return current


# ═══════════════════════════════════════════════════════════════════════════
# O-07 — 백업·복구 (이미 있는 회수증만 읽는다 · 새 저장 0)
# ═══════════════════════════════════════════════════════════════════════════
def backup_board(actor: Any) -> dict:
    _require_operator(actor)
    backup, backup_path = _read_json("agent", "evidence", "D-373", "backup_last.json")
    drill, drill_path = _read_json("agent", "evidence", "D-373", "restore_drill_last.json")

    backup_fresh = None
    if backup and backup.get("measured_at"):
        age = _now() - datetime.fromisoformat(backup["measured_at"].replace("Z", "+00:00"))
        backup_fresh = age <= timedelta(hours=25)  # 일 1 자동 + 1시간 여유

    drill_fresh = None
    if drill and drill.get("measured_at"):
        age = _now() - datetime.fromisoformat(drill["measured_at"].replace("Z", "+00:00"))
        drill_fresh = age <= timedelta(days=32)  # 월 1

    return {
        "backup": {
            "read": backup is not None, "source": backup_path,
            "measured_at": (backup or {}).get("measured_at"),
            "verdict": (backup or {}).get("verdict"),
            "db_bytes": ((backup or {}).get("manifest") or {}).get("db", {}).get("bytes"),
            "destination": ((backup or {}).get("manifest") or {}).get("db", {}).get("via"),
            "fresh_within_24h": backup_fresh,
        },
        "restore_drill": {
            "read": drill is not None, "source": drill_path,
            "measured_at": (drill or {}).get("measured_at"),
            "verdict": (drill or {}).get("verdict"),
            "rto_seconds": (drill or {}).get("rto_seconds"),
            "tables_restored": (drill or {}).get("tables_restored"),
            "tables_source": (drill or {}).get("tables_source"),
            "fresh_within_31d": drill_fresh,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# O-08 — 온보딩 관제 (이미 있는 48행 장부만 읽는다 · 새 저장 0)
# ═══════════════════════════════════════════════════════════════════════════
def _latest_onbt_file() -> Path | None:
    onbt_dir = DOCS_ROOT / "agent" / "evidence" / "ONB-T"
    if not onbt_dir.is_dir():
        return None
    files = sorted(onbt_dir.glob("turn_*.json"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def onboarding_board(actor: Any) -> dict:
    _require_operator(actor)
    path = _latest_onbt_file()
    if path is None:
        return {"read": False, "source": str(DOCS_ROOT / "agent" / "evidence" / "ONB-T"),
               "why": "48행 재측 장부(ONB-T/turn_*.json)를 못 읽었다 — 회색"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"read": False, "source": str(path), "why": "장부 파싱 실패 — 회색"}

    rows = payload.get("rows") or []
    by_role: dict[str, dict] = {}
    blocked = []
    for row in rows:
        role = (row.get("row") or "").split("#")[0]
        bucket = by_role.setdefault(role, {"green": 0, "half": 0, "red": 0, "total": 0})
        bucket["total"] += 1
        verdict = row.get("verdict")
        score = row.get("score")
        if verdict == "green" or score == 1.0:
            bucket["green"] += 1
        elif score == 0.5:
            bucket["half"] += 1
        else:
            bucket["red"] += 1
            blocked.append({"row": row.get("row"), "why": row.get("gray_why") or
                            row.get("evidence") or "빨강 — 근거 미확인"})

    role_progress = {
        role: {"green": v["green"], "half": v["half"], "red": v["red"], "total": v["total"],
              "ratio": round((v["green"] + v["half"] * 0.5) / v["total"], 3) if v["total"] else 0.0}
        for role, v in sorted(by_role.items())
    }

    #: 테넌트별 D-7~D+30 — 테넌트 생성 시각(UserGroup) 기준 진행 일수.
    UserGroup = _UserGroup()
    tenants = []
    for g in UserGroup._base_manager.all().order_by("id"):
        created = _tenant_created_at(g)
        day_n = (date.today() - created.date()).days if created else None
        tenants.append({
            "tenant_code": g.code, "name": g.name,
            "day_n": day_n,
            "stage": ("D-7~D0(착수)" if day_n is not None and day_n <= 0 else
                     "D1~D7(초기 관제)" if day_n is not None and day_n <= 7 else
                     "D8~D30(정착)" if day_n is not None and day_n <= 30 else
                     "D30+(정상 운영)" if day_n is not None else "미확인"),
        })

    return {
        "read": True, "source": str(path),
        "denominator": payload.get("denominator", 48),
        "score_over_denominator": payload.get("score_over_denominator"),
        "green": payload.get("green"), "half": payload.get("half"), "red": payload.get("red"),
        "role_progress_6": role_progress,
        "role_count": len(role_progress),
        "blocked_cards": blocked,
        "tenants": tenants,
    }


# ═══════════════════════════════════════════════════════════════════════════
# O-09 — 감사(플랫폼) — 운영자 행위 전건 · 테넌트 열람 요청·승인
# ═══════════════════════════════════════════════════════════════════════════
def platform_audit_log(actor: Any, limit: int = 200) -> dict:
    _require_operator(actor)
    rows: list[dict] = []
    for logger_name in ALL_OPS_LOGGERS:
        for r in _audit_rows(logger_name):
            rows.append({"logger": logger_name, **r})
    rows.sort(key=lambda r: r.get("_audit_id") or 0, reverse=True)
    return {"entries": rows[:limit], "total": len(rows), "loggers": list(ALL_OPS_LOGGERS)}


def request_tenant_access(actor: Any, *, tenant_code: str, reason: str) -> dict:
    """운영자가 테넌트 원 데이터(구성원 목록)를 보려면 먼저 요청을 남긴다."""
    _require_operator(actor)
    if not reason:
        raise OpsAnInputRejected("사유 없는 테넌트 열람 요청은 받지 않습니다.")
    tenant = _get_tenant(tenant_code)
    request_id = uuid.uuid4().hex[:12]
    after = {"request_id": request_id, "tenant_code": tenant_code, "tenant_id": tenant.id,
             "reason": reason, "status": "requested",
             "requested_by": getattr(actor, "username", ""), "requested_at": _now_iso(),
             "approved_by": None, "approved_at": None, "expires_at": None}
    _audit(actor, LOG_ACCESS, "[OPS-ACCESS]", "request",
          "테넌트 %s 열람 요청 — %s" % (tenant_code, reason), after=after)
    return after


def approve_tenant_access(actor: Any, *, request_id: str) -> dict:
    _require_operator(actor)
    rows = _audit_rows(LOG_ACCESS)
    mine = [r for r in rows if r.get("request_id") == request_id]
    if not mine:
        raise OpsAnNotFound("요청 %r 를 찾을 수 없습니다." % request_id)
    current = dict(mine[-1])
    if current.get("status") != "requested":
        raise OpsAnInputRejected("이미 %r 상태입니다." % current.get("status"))
    current["status"] = "approved"
    current["approved_by"] = getattr(actor, "username", "")
    current["approved_at"] = _now_iso()
    current["expires_at"] = (_now() + timedelta(minutes=30)).isoformat()
    _audit(actor, LOG_ACCESS, "[OPS-ACCESS]", "approve",
          "테넌트 %s 열람 승인(30분)" % current.get("tenant_code"), after=current)
    return current


def _active_access_grant(tenant_code: str) -> dict | None:
    rows = _audit_rows(LOG_ACCESS)
    mine = [r for r in rows if r.get("tenant_code") == tenant_code]
    latest = _latest_by_key(mine, key_fn=lambda r: r.get("request_id"))
    now_iso = _now_iso()
    for r in latest:
        if r.get("status") == "approved" and (r.get("expires_at") or "") > now_iso:
            return r
    return None


def view_tenant_members(actor: Any, *, tenant_code: str) -> dict:
    """승인된 요청이 없으면 **테넌트 데이터 열람 0** — O-09 완결 조건의 그 문장을
    이 함수 하나로 실측 가능하게 만든다(우리가 여는 유일한 원 데이터 열람 문이므로).
    """
    _require_operator(actor)
    tenant = _get_tenant(tenant_code)
    grant = _active_access_grant(tenant_code)
    if grant is None:
        raise OpsAnPermissionDenied(
            "승인된 열람 요청이 없습니다 — O-09 완결 조건(승인 없이 테넌트 데이터 열람 0).")
    UPL = _UserProfileLink()
    members = [{"name": p.name, "employee_id": p.employee_id}
              for p in UPL._base_manager.filter(group_id=tenant.id)]
    return {"tenant_code": tenant_code, "members": members, "granted_by": grant.get("approved_by"),
           "expires_at": grant.get("expires_at")}


# ═══════════════════════════════════════════════════════════════════════════
# O-10 — 키·자격 회전 (기존 k5_trust 공개 면 재사용 · 읽기 위주)
# ═══════════════════════════════════════════════════════════════════════════
def key_rotation_board(actor: Any) -> dict:
    """O-10 — **회전 절차·기록**(P-421 ⑤ · 턴 AP N3): 콘솔 문 · 감사 줄 · 다음
    회전일 셋을 한 응답에 낸다.

    ★ [턴 AP · P-428] 완결 조건의 AND 반쪽(「회전 뒤 게이트 계정 로그인 4/4」)은
      여전히 못 잰다 — 게이트 계정을 실제로 회전해 **운영 서버에 로그인**해 보는
      것은 이 저장소 차선 공통 규칙이 금지한다. 그 부분은 결정 번호(P-428)로
      빼고, 절차·기록 셋(콘솔 문·감사 줄·다음 회전일)을 이 함수가 실측으로 낸다
      — annex 제목이 부르는 「회전 주기 · runbook」이 그 셋으로 이루어진다.
    """
    _require_operator(actor)
    payload, path = _read_json("agent", "evidence", "D-373", "key_rotation_last.json")
    policy_days = (payload or {}).get("policy_days")
    now = _now()
    keys = []
    for row in (payload or {}).get("keys", [])[:50]:
        row = dict(row)
        age_days = row.get("age_days")
        #: ★ **다음 회전일** — 정책 주기(policy_days)에서 이미 지난 나이(age_days)를
        #:   뺀 날짜. 스냅샷 시각(measured_at) 기준이 아니라 **지금(now)** 기준으로
        #:   다시 센다 — 그래야 「오늘 이 화면을 보면 언제까지 미뤘는지」가 맞다.
        #:   음수면 이미 지났다는 뜻이고, 그 값을 지우지 않고 그대로 낸다(D-301).
        if policy_days is not None and isinstance(age_days, (int, float)):
            row["next_rotation_due_at"] = (
                now + timedelta(days=policy_days - age_days)).isoformat()
        else:
            row["next_rotation_due_at"] = None
        keys.append(row)

    rotation_rows = _audit_rows(LOG_KEYS, action_prefix="rotate")
    latest_rotation = rotation_rows[-1] if rotation_rows else None

    return {
        "read": payload is not None, "source": path,
        "measured_at": (payload or {}).get("measured_at"),
        "policy_days": policy_days,
        "rotation_cycle_days": policy_days,
        "due_count": (payload or {}).get("due"),
        "keys": keys,
        #: 콘솔 문 — 이 GET 자신 + `POST /api/dsm/ops/keys/rotate`(rotate_api_key).
        "rotate_endpoint": "POST /api/dsm/ops/keys/rotate",
        #: 감사 줄 — 가장 최근 회전 감사 행(있으면). `rotate_api_key()` 가 매 회전마다
        #: `LOG_KEYS` 에 쓰는 그 줄이다.
        "last_rotation_audit": latest_rotation,
        "rotation_audit_count": len(rotation_rows),
        #: 정직한 한 줄 — 완결 조건의 AND 반쪽(라이브 로그인)은 이 차선이 못 잰다.
        "gray_why": ("완결 조건은 '회전 뒤 게이트 계정 로그인 4/4' 인데, 게이트 계정 "
                    "자체를 회전해 실제 서버에 로그인해 보는 것은 이 저장소 차선 공통 "
                    "규칙이 금지한다(라이브 로그인 금지) — 그래서 이 부분은 "
                    "excluded_by=P-428 로 뺀다(runbook·감사·다음 회전일은 위 칸이 "
                    "실측한다)."),
    }


def _tenant_member_for_proxy(tenant) -> Any:
    """이 테넌트에 속한 실제 사람 하나. **U0 자신의 스코프로는 이 테넌트의 키를
    못 만진다** [턴 AP · 실측 2026-10-01] — `kernels.k5_trust.inbound_keys
    ._group_of()` 가 `require_user_group(scope.actor)` 를 부르고, U0 은
    어느 테넌트에도 속하지 않아(플랫폼 운영자는 그 자체로 테넌트가 아니다)
    `NoTenantGroupError` 로 죽는다 — `_group_of` 는 시스템 스코프도 대놓고
    거절한다("들어오는 키의 발급·폐기는 사람이 한다"). 이것은 §0.4 밖(우리
    코드) 함수가 아니라 `k5_trust`(공개 커널 면)의 **의도된 설계**이고, 이
    차선은 그 문을 못 바꾼다(D-278 공개 면만 부른다) — 그래서 **대행 자체를
    바꾼다**: U0 대신 그 테넌트에 **실제로 속한** 사람의 스코프로 부른다.
    `_scoped()` 가 보는 것은 그 사람의 **그룹**뿐이라(행 코드 확인 — 개인
    권한을 보지 않는다), 그룹만 같으면 누구든 같은 키 집합을 본다 — 그래서
    "누구를 고르는가"는 중요하지 않고 "그 테넌트에 속하는가"만 중요하다.

    Raises:
        OpsAnInputRejected: 그 테넌트에 활성 사용자가 하나도 없다.
    """
    UPL = _UserProfileLink()
    link = (UPL._base_manager.filter(group_id=tenant.id, user__is_active=True)
           .select_related("user").order_by("id").first())
    if link is None:
        raise OpsAnInputRejected(
            "테넌트 %r 에 활성 사용자가 없어 키 회전을 대행할 수 없습니다 — "
            "최소 1명(예: 초기 관리자)이 있어야 합니다." % tenant.code)
    return link.user


def rotate_api_key(actor: Any, *, tenant_code: str, key_id: int) -> dict:
    """API 키 회전 — `kernels.k5_trust` 공개 면의 `rotate_key` **재사용**(새로 안
    만든다). ★ [조율자 지적 · verify_layers 금지①] `kernels.k5_trust.inbound_keys`
    (비공개 하위 모듈)를 직접 import 하지 않는다 — `rotate_key` 는 `k5_trust/
    __init__.py::__all__` 에 이미 올라 있는 **공개 면의 이름**이므로 패키지
    최상위에서 가져온다(D-278 · `kernels.k1_event` 와 같은 규약).

    ★ [턴 AP · 차선 N3] `scope` 는 U0(`actor`)가 아니라 **그 테넌트의 실제
    구성원**으로 만든다 — `_tenant_member_for_proxy()` 머리말이 그 이유다.
    O-01(`issue_tenant`)의 "U0 의 자격을 안쪽 호출에 물려준다"와는 **다른
    모양의 대행**이다: 그쪽은 U0 자신의 Authorization 을 그대로 옮기고, 이쪽은
    k5_trust 가 애초에 U0 을 받지 않으므로 그 테넌트의 실제 구성원 스코프를
    빌린다 — 두 대행 모두 **U0 만 이 함수 자체를 부를 수 있다**는 문턱
    (`_require_operator`)은 그대로다.
    """
    _require_operator(actor)
    tenant = _get_tenant(tenant_code)
    from common.tenant_scope import TenantScope
    from kernels.k5_trust import rotate_key

    scope = TenantScope.of(_tenant_member_for_proxy(tenant))
    issued = rotate_key(scope=scope, key_id=key_id)
    #: ★ [턴 AP · 차선 N3] 실측 버그 수정 — `IssuedKey` 에는 `.id` 칸이 없다(`.view`·
    #:   `.secret` 뿐, `kernels/k5_trust/inbound_keys.py::IssuedKey`). `getattr(issued,
    #:   "id", None)` 은 **항상 `None`** 을 냈다(자기 조용히 실패 — 시험이 응답
    #:   바디를 값으로 대조하지 않아 이 턴까지 안 걸렸다). 새 키의 진짜 식별자는
    #:   `issued.view.key_id` 다.
    after = {"tenant_code": tenant_code, "tenant_id": tenant.id, "key_id": key_id,
             "new_key_id": issued.view.key_id, "rotated_at": _now_iso()}
    _audit(actor, LOG_KEYS, "[OPS-KEY]", "rotate",
          "%s 의 키 %s 회전(k5_trust 재사용)" % (tenant_code, key_id), after=after)
    return after


# ═══════════════════════════════════════════════════════════════════════════
# O-11 — 릴리스·배포 (이미 있는 deploys.jsonl 만 읽는다 · 새 저장 0)
# ═══════════════════════════════════════════════════════════════════════════
def release_board(actor: Any) -> dict:
    """O-11 — 릴리스·배포. 완결 조건은 **3항 AND**(「deploy.sh exit 0 · 걷기(smoke)
    초록 · 되돌리기 1회 시험」).

    ★ [턴 AP · P-421 ⑤ · 차선 N3] **되돌리기 1회 시험 = `drill_ok`.**
      `scripts/deploy_spa_8500.py::drill()` 가 배포 **때마다** 백업을 연습
      자리로 복원해 원본과 같은지 대조한다(그 파일 106~135행) — 그 결과가
      이미 `deploys.jsonl` 의 `drill_ok` 칸에 실려 있다(턴 AO 의 "grep 0건"은
      `restore`·`rollback` 이라는 **낱말**을 찾은 것이지, 되돌리기를 **실제로
      실측한 값**(`drill_ok`)을 못 본 것이다 — 이 함수가 그 값을 화면/문에
      명시적으로 끌어올린다). 이 함수는 그 세 칸을 **AND** 로 접어
      `deploy_gate_passed` 를 낸다 — 새로 재지 않는다, 이미 있는 장부를 읽을
      뿐이다(새 저장 0).
    """
    _require_operator(actor)
    rows, path = _read_jsonl("agent", "evidence", "OPS-27", "deploys.jsonl", limit=20)
    rows = list(reversed(rows))  # 최신 먼저
    latest = rows[0] if rows else None

    def _passed(row: dict | None) -> bool | None:
        if row is None:
            return None
        return bool(row.get("exit") == 0 and row.get("smoke_exit") == 0
                   and row.get("drill_ok") is True)

    return {
        "read": bool(rows), "source": path,
        "deploys": rows, "count": len(rows),
        "latest": latest,
        "latest_green": bool(latest and latest.get("exit") == 0),
        #: 완결 조건 3항 각각 — 없으면 None(못 쟀다), 있으면 실측값 그대로.
        "latest_deploy_exit_ok": (latest or {}).get("exit") == 0 if latest else None,
        "latest_smoke_ok": (latest or {}).get("smoke_exit") == 0 if latest else None,
        "latest_rollback_drill_ok": (latest or {}).get("drill_ok") if latest else None,
        #: 완결 조건 3항 AND — 기록에 있는 배포 전부에 대해.
        "deploy_gate_passed": _passed(latest),
        "rollback_drill_history": [
            {"at": r.get("at"), "commit": r.get("commit"),
             "drill_ok": r.get("drill_ok")}
            for r in rows
        ],
        "rollback_drill_all_ok": bool(rows) and all(
            r.get("drill_ok") is True for r in rows),
    }


# ═══════════════════════════════════════════════════════════════════════════
# O-12 — 시드·훈련 데이터
# ═══════════════════════════════════════════════════════════════════════════
def seed_board(actor: Any) -> dict:
    _require_operator(actor)
    rows = _audit_rows(LOG_SEED)
    latest = _latest_by_key(rows, key_fn=lambda r: (r.get("tenant_code"), r.get("scenario_code")))

    #: 실데이터 혼입 0 — StreamMonitor 등 실물 표에서 `data_source` 값 분포를 그대로
    #: 센다(우리가 지어내지 않는다 — 이미 있는 칸을 읽는다).
    StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
    seed_field_present = any(f.name == "data_source" for f in StreamMonitor._meta.get_fields())
    contamination = None
    if seed_field_present:
        contamination = {
            "seed": StreamMonitor._base_manager.filter(data_source="seed").count(),
            "unknown_or_live": StreamMonitor._base_manager
                .exclude(data_source="seed").count(),
        }
    #: [턴 AQ · 차선 N2] 테넌트별 훈련 상태 — 「훈련 시나리오 배포」가 실제로 켠
    #:   스위치(stream_monitors drill)를 그대로 읽는다(새 저장 0).
    from common.tenant_scope import TenantScope
    from stream_monitors.services import drill

    scope = TenantScope.of(actor)
    drill_rows = []
    for g in _UserGroup()._base_manager.all().order_by("id"):
        state = drill.drill_state(scope=scope, group_id=g.id)
        drill_rows.append({
            "tenant_code": g.code, "name": g.name, "drill_mode": state.enabled,
            "since": state.since.isoformat() if state.since else None,
            "by": state.by, "reason": state.reason,
        })
    return {"toggles": latest, "count": len(latest), "contamination_by_data_source": contamination,
            "drill_by_tenant": drill_rows}


def toggle_seed(actor: Any, *, tenant_code: str, action: str, scenario_code: str = "",
                note: str = "") -> dict:
    _require_operator(actor)
    if action not in ("plant", "hide", "deploy_scenario", "end_scenario"):
        raise OpsAnInputRejected(
            "action 은 plant·hide·deploy_scenario·end_scenario 만 받습니다.")
    tenant = _get_tenant(tenant_code)
    after = {"tenant_code": tenant_code, "tenant_id": tenant.id,
             "scenario_code": scenario_code or "default", "action": action,
             "note": note, "data_source": "seed", "at": _now_iso()}
    #: [턴 AQ · 차선 N2] **훈련 시나리오 배포 = 그 테넌트 훈련 모드를 실제로 켠다**
    #:   (설계서 OF-1 3단계 「훈련 켬」 · 7단계 「훈련 끔」). 스위치는 새로 만들지
    #:   않는다 — FWS-F3-19 가 쓰는 그 스위치(`stream_monitors.services.drill`)를
    #:   그대로 부르고, 켜져 있는 동안 그 테넌트 알림은 실채널이 아니라 훈련
    #:   채널로 간다(스위치 자신의 규약). U0 는 전역 운영자라 `group_id` 로
    #:   대상 테넌트를 지정할 수 있다(drill._target_group 의 문지기 그대로).
    if action in ("deploy_scenario", "end_scenario"):
        from common.tenant_scope import TenantScope
        from stream_monitors.services import drill

        reason = (note or "").strip() or (
            "플랫폼 운영 — 훈련 시나리오 %s %s"
            % (scenario_code or "default", "배포" if action == "deploy_scenario" else "종료"))
        try:
            switched = drill.set_drill_mode(
                scope=TenantScope.of(actor), enabled=(action == "deploy_scenario"),
                reason=reason, group_id=tenant.id)
        except ValueError as exc:
            raise OpsAnInputRejected(str(exc))
        after["drill_mode"] = bool(switched.get("drill_mode"))
        after["drill_changed"] = bool(switched.get("changed", True))
    _audit(actor, LOG_SEED, "[OPS-SEED]", action,
          "%s 시드 %s(%s)" % (tenant_code, action, scenario_code or "default"), after=after)
    return after
