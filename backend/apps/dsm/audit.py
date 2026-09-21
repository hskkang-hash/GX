# -*- coding: utf-8 -*-
"""F-12 설정 감사로그 — **성공도 실패도 남는다** (AC-12).

계약 AC-12 원문: *"무권한 계정의 설정 변경 시도가 차단되고, **성공·실패 모두**
감사로그에 남는다."*

실패를 남기지 않으면 무슨 일이 생기나
-------------------------------------
차단은 조용하다. 막힌 요청은 아무 흔적을 남기지 않고, 그러면
**"시도가 없었다" 와 "시도가 막혔다" 가 같은 상태(행 없음)** 가 된다.
그 둘이 같아지면 감사에서 답할 수 있는 질문이 하나 줄어든다 —
"누가 우리 설정을 만지려 했는가". D-290 이 이름 붙인 실패 모양 그대로다.

어디에 남기나 — 새 표를 만들지 않는다
-------------------------------------
`logger.AuditLogs` 가 이미 있다(dj-core). 새 감사 표를 만들면 감사 이력이 두 곳에
쌓이고, 두 곳에 쌓인 이력은 어느 쪽이 전부인지 아무도 모른다.

★ 2026-09-06 — **쓰는 자리는 `common/audit_writer.py` 하나다** (D-325 표 ②).
  K5 자격증명 표도 같은 표에 접근 감사를 남긴다. 커널(L3)은 App(L4)을 import 할 수
  없으므로, 그대로 두면 같은 모양으로 쓰는 코드가 두 벌이 된다. 판정식 복사본 하나가
  격리 사고의 원인이었고(D-212), **기록식도 같다.** 이 파일은 이제 F-12 의 앞면이다 —
  `LOGGER_NAME` 만 다르고 쓰는 손은 하나다.

  ⚠ dj-core 는 §0.4 금지구역(D-207)이다 — **모델을 고치지 않는다.** 우리는 행을
    쓸 뿐이고, FK 분류 열(action·service·command …)은 **비워 둔다.** 그 분류값이
    무엇을 뜻하는지 우리가 모르기 때문이다. 모르는 칸을 그럴듯하게 채우면 그 값이
    나중에 근거처럼 읽힌다 (D-280).

쓰기가 실패하면 — **삼키지 않는다**
-----------------------------------
감사 쓰기가 조용히 실패하면 그때부터 "감사로그 전건" 은 거짓이 되고, 아무도 모른다.
그래서 `record()` 는 예외를 올린다. 부르는 쪽(`guard`)은 그 예외를 잡지 않는다 —
**감사에 남길 수 없으면 그 설정 변경은 일어나지 않는다.**

  이것은 저하 운전(규약 ④)의 예외다. 화재 판정은 메일이 죽어도 살아야 하지만,
  설정 변경은 감사가 죽으면 **하지 않는 것이 옳다.** 둘은 다른 성질의 행위다.
"""
from __future__ import annotations

import logging
from typing import Any

from common import audit_writer
from common.audit_writer import AuditEntry
from common.tenant_scope import TenantScope

log = logging.getLogger("guardianx.audit.settings")

#: 감사 행의 `logger_name`. **이 문자열로 F-12 감사 전건을 뽑는다** —
#: 이름이 하나여야 "전건" 이라는 말이 성립한다 (D-285 ②).
LOGGER_NAME = "guardianx.f12.settings"

#: 감사에 남는 판정 두 가지. `common/audit_writer` 가 정본이고 여기서 이름만 다시 낸다 —
#: 값을 여기서 새로 적으면 두 벌이 되고, 두 벌은 반드시 어긋난다.
ALLOWED = audit_writer.ALLOWED
DENIED = audit_writer.DENIED

#: 메시지 머리 표시. 집계는 `LOGGER_NAME` 이 하고, 이것은 사람이 눈으로 가르는 표시다.
TAG = "[F-12]"


def record(
    *,
    scope: TenantScope,
    action: str,
    outcome: str,
    reason: str,
    before: Any = None,
    after: Any = None,
    api_name: str = "",
    api_method: str = "",
    status_http: int | None = None,
) -> AuditEntry:
    """감사 한 줄을 **실제로 저장한다.** 실패하면 예외가 올라간다.

    `outcome` 은 `ALLOWED` / `DENIED` 둘뿐이다. 자유 문자열을 받으면 다음 사람이
    "attempted" 같은 제3의 값을 넣고, 그러면 전건 집계가 갈린다.
    """
    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=scope.actor,
        action=action, outcome=outcome, reason=reason,
        before=before, after=after,
        api_name=api_name, api_method=api_method, status_http=status_http,
    )
    log.info("[F-12] %s %s actor=%s reason=%s",
             action, outcome, entry.actor_id, reason)
    return entry


def entries(*, action: str | None = None, limit: int = 100) -> tuple[AuditEntry, ...]:
    """F-12 감사 이력 조회. **검수에서 "전건" 을 세는 자리**다.

    ⚠ 테넌트로 좁히지 않는다 — 감사 이력은 운영자가 보는 것이고, 좁히는 판단은
      이 함수를 부르는 라우트가 한다. 여기서 좁히면 "전건" 이 조용히 부분집합이 된다.
      이 함수를 라우트에 직접 노출하지 않는 이유이기도 하다.
    """
    return audit_writer.read(logger_name=LOGGER_NAME, action=action, limit=limit)


# ═══════════════════════════════════════════════════════════════════════════
# 턴 T (P-164 U24 ②·③) — 사건 행위 감사 채널 + **테넌트로 좁힌 읽기**
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 사건 행위(상급 보고 체크 · 해제)는 F-12 설정 감사와 **다른 `logger_name`** 에 쓴다.
#   `LOGGER_NAME` 은 「F-12 설정 감사 전건」을 세는 이름이다(D-285 ②) — 거기에 사건
#   행위를 섞으면 그 전건이 조용히 늘고, 검수가 세는 수가 바뀐다. 쓰는 손은 여전히
#   `common/audit_writer.write` 하나다(두 벌을 만들지 않는다).
EVENT_LOGGER_NAME = "guardianx.u24.events"
EVENT_TAG = "[U24-EVENT]"

# ═══════════════════════════════════════════════════════════════════════════
# 턴 Z (P-178 U56 ① · **대표 결정 ⑤ 「넓혀라 — 접속 로그는 빼고」**)
# ═══════════════════════════════════════════════════════════════════════════
#
# 무엇이 틀려 있었나 — [실측 2026-09-21 · 차선 U56]
# ------------------------------------------------
# 이 울타리는 이름 **둘**만 열고 있었다. 그런데 우리가 이 표에 쓰는 이름은 둘이
# 아니다: `common/audit_writer.write` 를 지나는 채널이 열다섯이고, 감사 화면은 그중
# 둘만 봤다. 「감사 전건」이라고 부른 수가 실은 **전건의 1/2** 이었다 —
# 지난 턴에 「삭제된 사건을 가리키는 체인 행 29건」이라 적은 것이, 화면이 닿는
# 자리에서는 **2행**이었던 이유가 이것이다. 화면이 못 보는 행은 화면이 못 고친다.
#
# ★ **빼는 것은 접속 로그다 — 이름으로 뺀다** (대표 조건)
# -------------------------------------------------------
# dj-core 는 **요청 한 건마다 이 표에 한 행**을 쌓는다. 그 행의 모양은 우리 감사
# 행과 다르다: `api_name` 이 URL 이고 `client_ip` 가 차 있고 `note` 가 프레임워크의
# 영어 문장이다. [실측 2026-09-21] 그 이름 다섯과 행 수:
#
#     db          81,086     jwt     46,721     application  20,065
#     security     3,086     user_update   732            합 151,690
#
#   · `db` + `jwt` 만으로 127,807행이다(대표께 보고한 「약 13만」이 이 둘이다).
#   · 이 다섯을 넣으면 감사 화면은 **접속 기록 뷰어**가 되고, 우리 감사 행은
#     98% 의 요청 로그 밑에 묻힌다. 상한 200(`PAGE_SIZE_MAX`)짜리 표에서
#     「누가 우리 설정을 만지려 했는가」는 영원히 첫 쪽에 못 온다.
#   · ★ **누출**이기도 하다 [실측]: `security` 채널의 `note` 3,012행이
#     *"User <계정> logged in successfully from <IP>."* 다. `read_page` 는 `note` 를
#     `reason` 칸으로 **화면에 그대로 낸다** — 넣는 순간 접속자 IP 가 화면에 뜬다.
#     `db` 채널에는 컨테이너 사설 IP 225행과 우리 대장 이름(`D-290`) 3행이 있다
#     (`scripts/verify_ui_secrets.py` 의 금지 패턴 「결정 번호」 그 자리다).
#
# ★ **0행인 이름은 이번에 안 넣는다** — 재지 못한 것은 초록이 아니다 (D-400)
# ------------------------------------------------------------------------
# 코드에 선언돼 있으나 오늘 이 표에 **한 행도 없는** 채널이 넷 있다:
#
#     guardianx.k5.credentials · guardianx.k5.thresholds
#     guardianx.sec.key        · guardianx.dsm.drill
#
#   행이 없으면 **무엇이 화면에 뜰지 실물로 못 본다.** 자격증명 접근 감사
#   (`guardianx.k5.credentials`)를 안 보고 여는 것은 특히 그렇다. 화면에 올리는
#   것은 되돌리기 어렵다 — 첫 행이 생긴 날 그 행을 눈으로 보고 넣는다.
#   ⚠ 이 넷은 **모르는 것이 아니라 아는 빚**이고, 그래서 이름으로 적혀 있다.
#
#: 감사 읽기 라우트가 여는 채널. 여기 없는 이름은 그 라우트로 안 나간다 —
#: dj-core 가 같은 표에 쌓는 API 접근 로그 전체가 화면으로 새지 않게 하는 울타리다.
#:
#: ★ **여는 목록이지 거르는 목록이 아니다.** 「접속 로그만 빼라」를 `exclude` 로
#:   쓰면 내일 dj-core 가 새 로거를 하나 더 쌓을 때 그것이 **자동으로 화면에 뜬다.**
#:   여는 쪽으로 적으면 새 이름은 기본이 「안 보임」이고, 보이게 하려면 사람이
#:   이 줄을 고쳐야 한다 — 되돌리기 어려운 방향에 사람 손을 한 번 넣는다.
READABLE_LOGGER_NAMES = (
    # ── F-12 설정 감사 · 사건 행위 (턴 T 부터 열려 있던 둘) ──────────────
    LOGGER_NAME,                        # guardianx.f12.settings
    EVENT_LOGGER_NAME,                  # guardianx.u24.events
    # ── 턴 Z 에 새로 여는 열셋 ───────────────────────────────────────────
    "guardianx.law02a.retention",       # LAW-02a 보존기간 파기 (apps/dsm/retention.py)
    "guardianx.dsm.response",           # 대응 상태 전이 (K1 response_flow)
    "guardianx.test.law08_race",        # LAW-08 체인 경합 시험이 남긴 행 (P-191)
    "guardianx.dsm.notify",             # 알림 규칙 변경 · 오탐 고지 (K2)
    "guardianx.dsm.field_reply",        # 현장 회신 (K1 field_reply)
    "guardianx.k2.heartbeat",           # OPS-14 일일 맥박 요약 (K2 heartbeat)
    "guardianx.law07.privacy_request",  # LAW-07 열람·삭제 청구 처리
    "guardianx.u1.event_note",          # 사건 메모 (apps/dsm/event_note_service.py)
    "guardianx.dsm.push_subscription",  # 웹푸시 구독·시험발송 (K2 webpush)
    "guardianx.sec.otp_reset",          # P-113 OTP 재설정
    "guardianx.role_request",           # P-105 역할 부여 요청
    # ★ **옛 이름 둘.** 접두를 고치기 전에 태어난 행이 1건씩 남아 있다 [실측
    #   2026-09-21 · 각 1행]. 지금 코드는 이 이름으로 **안 쓴다**(위 두 줄이 정본).
    #   그래도 여는 이유: 이 행들도 LAW-08 체인의 칸을 차지하고 있고, 화면이 못 보는
    #   체인 칸은 화면에서 못 고친다. `logger_name__in` 은 정확 일치라 dj-core 의
    #   `security` 채널과 섞이지 않는다 — `security.otp_reset` 은 **다른 이름**이다.
    "security.otp_reset",               # ← guardianx.sec.otp_reset 의 옛 이름
    "gx.role_request",                  # ← guardianx.role_request 의 옛 이름
)

#: 접속 로그의 이름 — **여기 적는 것은 막기 위해서가 아니라 알기 위해서다.**
#: 위 목록이 여는 쪽이므로 이 이름들은 이미 안 나간다. 그런데 이름을 어디에도
#: 안 적어 두면 다음 사람이 「왜 db 는 없지」를 **다시 처음부터** 재야 한다.
#: `tests/test_u56_audit_channels.py` 가 이 둘이 겹치지 않는가를 묻고, 접속 로그처럼
#: 생긴 행을 **심어 놓고** 그것이 화면에 안 뜨는지를 뒷면(`read_page`)으로 확인한다 —
#: 글자만 보면 「목록은 옳은데 화면에는 뜬다」를 못 잡고, 그 상태가 가장 나쁘다.
ACCESS_LOG_LOGGER_NAMES = (
    "db", "jwt", "application", "security", "user_update",
)

#: 한 쪽의 상한. 화면 표 한 장이 감당하는 수 — 더 크면 「60초 안 도달」이 먼저 깨진다.
PAGE_SIZE_MAX = 200


def record_event_action(
    *,
    scope: TenantScope,
    action: str,
    outcome: str,
    reason: str,
    before: Any = None,
    after: Any = None,
    api_name: str = "",
    api_method: str = "",
    status_http: int | None = None,
) -> AuditEntry:
    """사건 행위 감사 한 줄(`EVENT_LOGGER_NAME`). `record()` 와 같은 규약 — 실패는 올라간다."""
    entry = audit_writer.write(
        logger_name=EVENT_LOGGER_NAME, tag=EVENT_TAG, actor=scope.actor,
        action=action, outcome=outcome, reason=reason,
        before=before, after=after,
        api_name=api_name, api_method=api_method, status_http=status_http,
    )
    log.info("[U24-EVENT] %s %s actor=%s reason=%s",
             action, outcome, entry.actor_id, reason)
    return entry


def _tenant_actor_ids(actor) -> "list[int] | None":
    """요청자와 **같은 테넌트**의 사용자 pk 목록. 전역 관리자면 `None`(좁히지 않는다).

    감사 표(`logger.AuditLogs`)에는 group 칸이 없다 — 행의 테넌트는 **행위자의 소속**
    으로만 정해진다. 그래서 테넌트 좁히기는 `user_id ∈ 우리 테넌트 사용자` 다.
    행위자가 없는 행(`user_id` null · 시스템 행위)은 소속을 말할 수 없으므로 테넌트
    사용자에게는 **안 보인다** — 닫는 쪽이 기본값이다(`filter_users_by_group` 과 같은 규약).
    """
    from django.apps import apps

    from common.tenant_filters import filter_users_by_group
    from common.tenant_roles import is_global_admin

    if is_global_admin(actor):
        return None
    CoreUser = apps.get_model("user", "CoreUser")
    qs = filter_users_by_group(CoreUser._base_manager.all(), actor)
    return list(qs.values_list("pk", flat=True))


def read_page(
    *,
    scope: TenantScope,
    since=None,
    until=None,
    actor_id: int | None = None,
    action: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """감사 이력을 **요청자의 테넌트로 좁혀** 한 쪽 낸다 (P-164 U24 ③ · 필터 3 + 쪽).

    `entries()` 와 다른 점은 단 하나 — **여기서는 좁힌다.** `entries()` 는 검수가 「전건」을
    세는 자리라 좁히지 않았고, 그래서 라우트에 직접 노출하지 않았다. 이 함수는 화면에
    나가는 자리이므로 좁히는 판단을 **여기서** 한다(머리말 규약 그대로 — 판단은 라우트
    쪽 몫이고, 이 함수가 그 라우트의 뒷면이다).

    필터 셋: 기간(`since`·`until` — `create_datetime`) · 행위자(`actor_id` — `user_id`) ·
    행위 종류(`action` — `api_name` 앞머리 일치 · 대소문자 무시).
    """
    from common import evidence_chain
    from common.tenant_filters import get_user_group

    actor = scope.require_actor()
    if page < 1:
        raise ValueError(f"page 는 1 이상이다 — page={page}")
    if not (1 <= page_size <= PAGE_SIZE_MAX):
        raise ValueError(f"page_size 는 1~{PAGE_SIZE_MAX} 다 — page_size={page_size}")

    Model = audit_writer._model()
    qs = Model._base_manager.filter(logger_name__in=READABLE_LOGGER_NAMES)

    allowed_ids = _tenant_actor_ids(actor)
    if allowed_ids is not None:
        if get_user_group(actor) is None:
            qs = qs.none()  # 소속 없는 계정 — 닫는 쪽이 기본값
        else:
            qs = qs.filter(user_id__in=allowed_ids)
    if since is not None:
        qs = qs.filter(create_datetime__gte=since)
    if until is not None:
        qs = qs.filter(create_datetime__lte=until)
    if actor_id is not None:
        qs = qs.filter(user_id=actor_id)
    if action:
        qs = qs.filter(api_name__istartswith=action)

    total = qs.count()
    start = (page - 1) * page_size
    rows = list(qs.order_by("-id")[start:start + page_size])
    items = [
        {
            "audit_id": r.pk,
            "at": r.create_datetime.isoformat() if r.create_datetime else None,
            "channel": r.logger_name,
            "outcome": ALLOWED if r.level_name == "INFO" else DENIED,
            "action": r.api_name or "",
            "method": r.api_method or "",
            "actor_id": r.user_id,
            "actor": r.username or "",
            "reason": r.note or "",
            "status_http": r.status_http,
            #: ★ 턴 Z (U24 요청 · 2026-09-21) — **이 행이 가리키는 사건 번호.**
            #:   [U24 실측 2026-09-21] 넓힌 뒤 「사건을 가리키는 행」이 2 → 273 이 됐는데,
            #:   화면의 「대상」 칸은 `action` 문자열
            #:   (`^upper_report:(set|clear):\d+$`) **한 모양만** 읽어서 **180행이
            #:   침묵한다** — 그 행들은 번호를 `action` 이 아니라 `data_*` 페이로드에 든다.
            #:   ⚠ **판정식을 여기서 새로 쓰지 않는다.** `common/evidence_chain.event_ref_of`
            #:     가 그 질문의 정본(순수 함수 · 차선 S)이고, `dangling_event_refs` 도
            #:     같은 함수를 부른다. 두 벌이 되면 화면이 세는 수와 체인이 세는 수가
            #:     갈리고, 갈린 두 수는 감사 앞에서 못 쓴다.
            #:   ⚠ **칸 하나를 더 낼 뿐 질의는 안 는다** — `rows` 는 이미 모델 인스턴스라
            #:     두 칸이 같이 실려 와 있다.
            #:   ⚠ 누출 아님: 사건 번호는 같은 테넌트 독자가 사건 목록에서 이미 보는 값이다.
            #:     **번호만** 낸다 — 페이로드의 나머지(예: LAW-07 청구인 이름·연락처)는
            #:     이 함수가 내는 칸에 **없다**.
            "event_ref": evidence_chain.event_ref_of(
                {"data_before": r.data_before, "data_after": r.data_after}),
        }
        for r in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "channels": list(READABLE_LOGGER_NAMES),
    }
