# -*- coding: utf-8 -*-
"""WO-GX-20260915-01 §4.2 — 차선 **F(기반)** 의 두 번째 라우터: **점검 창 기록 문**.

무엇을 여는가 — 하나다
----------------------
    POST /api/dsm/system/requests/{request_id}/handled

재시작 **요청**(`POST /system/restart-request` · U56 이 세운 문)은 행 하나와 감사 한 줄을
남길 뿐이고, 실제 재시작은 **점검 창에서 사람이** 한다(운영계 외부 행위는 대표 · WO-01 불변).
이 문은 그 사람이 **돌아와서 적는 자리**다: 무엇을 했는가(`handled_note`)와 그래서 그 요청이
어떻게 됐는가(`status`).

★★ 이 문도 **컨테이너를 건드리지 않는다.** 건드리면 요청 문이 태어난 이유가 사라진다 —
   그 표는 「눌렀다」와 「일어났다」를 **가르려고** 생겼고, 이 문은 그 둘 사이에 사람이
   한 일을 적는 칸일 뿐이다. 그래서 여기서 일어나는 일도 행 하나와 감사 한 줄이 전부다.

왜 `api_f.py` 가 아니라 새 파일인가 [판정 · 턴 V · 차선 F]
---------------------------------------------------------
`api_f.py` 는 **온보딩 진행률 라우터**이고, `verify_onboarding_walk` 가 그 파일에
**쓰기 문이 있으면 빨강**을 낸다 — 「카드를 사람이 눌러 닫는 문」을 잡는 술어다(WO-01 §12).
그 술어는 옳다. 술어를 느슨하게 해서 이 문을 통과시키는 대신, **이 문을 다른 파일로** 냈다.
판정기를 고쳐 초록을 만드는 것과 판정기가 옳게 보도록 자리를 옮기는 것은 다르다.

★ `api_u56.py` 에 넣지 않은 이유는 규약이다 — **한 파일은 한 차선**(WO-01). 요청 문은
  U56 의 것이고 이 턴의 U56 이 그 파일을 고치고 있다. 같은 턴에 두 차선이 한 라우트
  파일을 고치면 충돌하고, 충돌한 라우트는 **라우팅 침묵**으로 나타난다(`urls.py` 머리말).

라우트 삼킴 [실측 · 턴 V]
-------------------------
`@route.*("/system/...` 전수 — `restart-request`(POST) · `requests`(GET) ·
`backup-receipts`(GET) · `storage`(GET). **변수 조각이 하나도 없다.** 그러므로
`/system/requests/{int:request_id}/handled` 를 삼킬 앞선 경로가 없고, 이 컨트롤러는
`urls.py` 에서 **맨 뒤**에 붙는다(앞의 경로를 가리지 못한다).
"""
from ninja.errors import HttpError
from ninja_extra import api_controller, route

from common.inbound_api_key import JwtOrInboundKey
from common.tenant_scope import TenantScope, tenant_scoped

#: 사람이 적을 수 있는 결말. **`requested` 는 없다** — 되돌리는 문이 아니다.
#: `scheduled` 는 「점검 창에 잡았다」이고, 그때도 무엇을 했는지는 적어야 한다.
HANDLED_STATUSES = ("scheduled", "done", "rejected")

#: 이미 끝난 요청. 다시 적으면 **앞사람이 적은 사실이 사라진다** — 그래서 409 다.
CLOSED_STATUSES = ("done", "rejected")

HANDLED_ACK = ("점검 창에서 한 일이 기록됐습니다 — 이 문은 서버를 내리거나 "
               "올리지 않습니다. 적힌 것은 사람이 한 일입니다.")


def _scope(request) -> TenantScope:
    """요청자에서 스코프를 만든다. **없으면 401.** `api_f.py::_scope` 와 같은 규약."""
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        raise HttpError(401, "인증이 필요합니다.")
    return TenantScope.of(user)


def _one_request(scope, request_id: int, model):
    """내 테넌트의 그 요청. 남의 것이면 **`None`**(404 로 답한다 · D-269).

    ★ `objects` 의 스레드 맥락에 기대지 않는다 — 「스레드에 남은 요청」 함정
      (`api_u56.py::_one_camera` 와 같은 모양 · 같은 이유).
    """
    from common.tenant_filters import get_user_group
    from common.tenant_roles import is_global_admin

    actor = scope.require_actor()
    qs = model._base_manager.filter(deleted__isnull=True)
    if not is_global_admin(actor):
        group = get_user_group(actor)
        group_id = getattr(group, "pk", None)
        if group_id is None:
            return None
        qs = qs.filter(group_id=group_id)
    return qs.filter(pk=request_id).first()


@api_controller("", tags=["DSM — 점검 창 기록 (WO-01 차선 F)"])
class DsmFOpsAPI:
    """F 차선의 두 번째 라우트 — 점검 창에서 한 일을 적는 문."""

    @route.post("/system/requests/{int:request_id}/handled", auth=JwtOrInboundKey())
    @tenant_scoped(reason="WS-22 점검 창 기록 — 남의 테넌트 요청에 「했다」를 적으면 "
                          "그 테넌트의 점검 이력이 우리 말로 바뀐다 (쓰기 IDOR)")
    def mark_handled(self, request, request_id: int, note: str,
                     status: str = "done"):
        """재시작 요청 하나에 **점검 창에서 한 일**을 적는다. 관리자만 · 감사 1행.

        · 메모가 비면 **422** — 「했다」만 남는 기록은 다음 사람에게 아무것도 아니다.
          그 표가 태어난 이유가 「무엇을 했는지 남기는 것」이었다.
        · 모르는 `status` 는 **422**(값이 틀렸다). `requested` 로 되돌리는 것도 422 다 —
          이 문은 적는 문이지 되돌리는 문이 아니다.
        · 이미 `done`·`rejected` 인 요청은 **409** — 다시 적으면 앞사람이 적은 사실이
          조용히 사라진다.
        · 남의 테넌트 요청은 **404** — 403 은 「있는데 못 만진다」를 알려 주고, 그것만으로
          남의 테넌트에 그 id 가 있다는 사실이 샌다(D-269).
        """
        from apps.dsm.services import guard_setting
        from stream_monitors.models import DsmSystemRequest

        scope = _scope(request)
        text = (note or "").strip()
        if not text:
            raise HttpError(422, "점검 창에서 무엇을 했는지가 비었습니다 — "
                                 "내용 없는 「완료」는 아무도 되짚을 수 없습니다.")
        if len(text) > 255:
            raise HttpError(422, "기록이 255자를 넘습니다.")
        target = (status or "").strip().lower()
        if target not in HANDLED_STATUSES:
            raise HttpError(422, "적을 수 있는 결말은 %s 입니다 — 「요청됨」으로 "
                                 "되돌리는 문이 아닙니다." % " · ".join(HANDLED_STATUSES))

        access = guard_setting(
            scope=scope, action="write:system:request-handled:%s" % request_id,
            api_method="POST")
        if not access.allowed:
            raise HttpError(403, access.reason)

        row = _one_request(scope, request_id, DsmSystemRequest)
        if row is None:
            raise HttpError(404, "그런 요청이 없습니다.")
        if row.status in CLOSED_STATUSES:
            raise HttpError(409, "이미 끝난 요청입니다(%s) — 덮어쓰면 앞사람이 적은 "
                                 "사실이 사라집니다." % row.get_status_display())

        before_status, before_note = row.status, row.handled_note
        row.handled_note = text
        row.status = target
        row.save(update_fields=["handled_note", "status"])
        return {"request_id": row.pk, "kind": row.kind,
                "status": row.status, "status_label": row.get_status_display(),
                "handled_note": row.handled_note,
                #: ★ 「무엇에서 무엇으로」 — 화면이 「처음 적었다」와 「고쳤다」를 가른다.
                "previous_status": before_status,
                "was_blank": not before_note,
                "executed_by_app": False,
                "message": HANDLED_ACK, "audit_id": access.audit_id}
