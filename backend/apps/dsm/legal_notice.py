# -*- coding: utf-8 -*-
"""LAW-02 · LAW-03 — 서식의 **「제품 자동」 칸을 제품이 채운다** (턴 C · 차선 E).

세종(CPO)이 두 서식을 썼다:

    docs/design/GX-LAW-02_영상정보처리기기_고지_초안_v0.1.md
    docs/design/GX-LAW-03_개인정보처리방침_초안_v0.1.md

두 문서 모두 표의 어떤 칸은 **제품 자동**, 어떤 칸은 **[확인]**(운영자·법률대리인)이라고
스스로 갈라 적었다. 이 파일은 **그 갈래를 코드로 옮긴 것**이고, 그 이상은 하지 않는다.

★ 무엇을 하지 않는가 — **문안을 쓰지 않는다**
---------------------------------------------
법률 문안은 세종의 것이고 법률대리인이 대조한다. 여기서 하는 일은 **배선**이다:
서식이 「제품 자동」이라고 표시한 칸에 **지금 이 제품의 값**을 넣고, 못 넣는 칸은
**비운 채로 「확인」이라고 적는다.**

★ 왜 못 채운 칸을 기본값으로 메우지 않는가 (D-301 · D-290)
----------------------------------------------------------
서식의 안내판에는 「보관 기간 : 기본 30일」이라고 적혀 있다. 이 파일이 처음 섰을 때
**이 저장소에는 영상 보존 일수를 선언한 자리가 없었고**, 그래서 그 칸을 `None` +
`confirm` 으로 두었다 [실측 2026-09-05 · 턴 C]. 없는 수를 안내판에 적으면 그 순간
**안내판이 거짓말을 시작하고**, 게시된 고지는 되돌릴 수 없다.

    ★ **2026-09-05 · 턴 D · 차선 L — 그 자리가 생겼다.** `apps/dsm/retention.py` 가
      보존 일수를 선언하고 **그 수대로 지운다**(LAW-02a). 값이 생긴 이유는 집행이
      생겼기 때문이지 서식을 베껴 적었기 때문이 아니다 — 그 순서가 요점이다.
      나머지 `confirm` 칸들의 규칙은 그대로다: **값이 없으면 0 도 30 도 아니다.**

★ 대장 상태는 **미측정**이다
----------------------------
법률 대조 전이라 이 라우트가 있다고 LAW-02·LAW-03 이 「구현」이 되는 것은 아니다.
제품이 채울 수 있는 칸을 채운 것뿐이고, 문안이 법에 맞는지는 **다른 사람의 판정**이다.
"""
from __future__ import annotations

from typing import Any

from django.apps import apps
from django.conf import settings

#: 서식이 「제품 사양으로 고정」이라고 적은 것. 설정이 아니라 **제품이 그렇게 생겼다**는
#: 사실이므로 값이 아니라 사양으로 낸다 (LAW-02 §3 · LAW-03 §1 「수집하지 않는 것」).
PRODUCT_SPEC: dict[str, str] = {
    "audio_recording": "없음 — 제품 사양으로 고정 (LAW-02 §3)",
    "shooting_hours": "24시간",
    "face_recognition": "없음 — 얼굴 인식 특징값을 만들지 않는다",
    "plate_recognition": "없음",
}

#: 영상 보존 일수를 선언했을 법한 자리. **하나도 없으면 `None` 이다** — 지어내지 않는다.
RETENTION_SETTING_NAMES: tuple[str, ...] = (
    "VIDEO_RETENTION_DAYS", "RETENTION_DAYS", "EVENT_RETENTION_DAYS",
)


def retention_days() -> int | None:
    """보존 일수. **한 곳에서만 정한다** — `apps/dsm/retention.py` 가 그 자리다.

    ★ 2026-09-05 · 차선 L — 이 함수는 이제 **직접 정하지 않는다.**
      LAW-02a 가 선언 자리와 **집행**을 함께 세웠고, 안내판이 보는 수와 삭제가 보는
      수가 갈리면 그 순간 안내판이 거짓말이 된다. 그래서 부르는 자리를 하나로 둔다.

    ★ 예전에는 여기서 `None` 이 나왔다. 그때는 **지우는 손이 없었기 때문**이고,
      집행 없이 적힌 수는 문서가 실측 행세를 하는 자리였다(D-301 · D-316).
      집행이 생긴 지금은 수가 나온다 — 그 수의 출처는 `retention.retention_source()`.
    """
    from apps.dsm.retention import retention_days as _declared

    try:
        return _declared()
    except Exception:                                          # noqa: BLE001
        #: 못 읽은 것을 0으로 적지 않는다 — 「없다」와 「0일」은 다른 사실이다.
        return None


# ═══════════════════════════════════════════════════════════════════════════
# LAW-03 — 수집 항목 표를 **모델에서 만든다**
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 표를 손으로 적지 않고 모델에 못박는가
#   처리방침의 수집 항목 표는 **제품이 실제로 저장하는 것**이어야 한다. 손으로 적으면
#   모델이 바뀌어도 표는 그대로 남고, 그 표는 「우리는 이것만 모읍니다」라고 말하면서
#   실제로는 다른 것을 모으는 문서가 된다 — 그것이 처리방침에서 가장 위험한 실패다.
#   그래서 항목마다 **어느 모델의 어느 칸**인지를 적고, 그 자리가 실재하는지 잰다.
#   자리가 사라지면 이 표는 `model_present: false` 로 그 사실을 드러낸다(숨기지 않는다).
COLLECTION_ROWS: tuple[dict[str, Any], ...] = (
    {"item": "영상 정지 이미지(스냅샷)", "where": "객체저장소",
     "why": "이벤트 판단 증거", "kept": "이벤트와 같은 기간",
     "model": "stream_monitors.EventClip", "fields": ("object_key",)},
    {"item": "영상 구간 참조(시각·카메라)", "where": "DB",
     "why": "증거 추적 · 원본은 저장소 밖으로 안 나감", "kept": "이벤트와 같은 기간",
     "model": "stream_monitors.EventClip", "fields": ("start_offset", "duration", "event")},
    {"item": "사용자 계정(이름·이메일·역할)", "where": "DB",
     "why": "로그인 · 알림 수신", "kept": "계정 삭제 시까지",
     "model": "user.CoreUser", "fields": ("email",)},
    {"item": "접속·조작 기록(감사로그)", "where": "DB · 해시 체인",
     "why": "안전성 확보 · 감사 대응", "kept": "[확인] 최소 1년",
     "model": "logger.AuditLogs", "fields": ()},
    {"item": "알림 발송 기록(수신자·시각·채널)", "where": "DB",
     "why": "대응 이력", "kept": "이벤트와 같은 기간",
     "model": "stream_monitors.DeliveryRecord",
     "fields": ("recipient_address", "channel", "sent_at")},
    {"item": "위치(카메라 설치 주소)", "where": "DB",
     "why": "알림·보고서", "kept": "카메라 등록 기간",
     "model": "stream_monitors.StreamMonitor",
     "fields": ("install_address", "address_source")},
    {"item": "이벤트 발생 좌표", "where": "DB",
     "why": "출동 안내", "kept": "이벤트와 같은 기간",
     "model": "stream_monitors.DetectionEvent", "fields": ("lat", "lng")},
)


def _resolve(label: str, fields: tuple[str, ...]) -> dict[str, Any]:
    """모델과 칸이 **실재하는가.** 없으면 그 사실을 그대로 낸다 (D-301)."""
    try:
        model = apps.get_model(label)
    except Exception:                                        # noqa: BLE001
        return {"model_present": False, "missing_fields": list(fields),
                "why_not": f"{label} 모델이 없다"}
    names = {f.name for f in model._meta.get_fields()}
    missing = [f for f in fields if f not in names]
    return {"model_present": True, "missing_fields": missing,
            "why_not": None if not missing else f"{label} 에 {missing} 칸이 없다"}


def collection_table() -> dict[str, Any]:
    """LAW-03 §1 수집 항목 표. **모델에서 만든다.**"""
    rows = []
    for row in COLLECTION_ROWS:
        got = _resolve(row["model"], tuple(row["fields"]))
        rows.append({**row, "fields": list(row["fields"]), **got})
    broken = [r["item"] for r in rows if not r["model_present"] or r["missing_fields"]]
    return {
        "rows": rows,
        "not_collected": [
            {"item": "음성", "why": PRODUCT_SPEC["audio_recording"]},
            {"item": "얼굴 인식 특징값", "why": PRODUCT_SPEC["face_recognition"]},
            {"item": "차량 번호", "why": PRODUCT_SPEC["plate_recognition"]},
        ],
        #: ★ 표가 모델과 갈린 자리. **0이 아니면 이 방침 초안은 아직 내면 안 된다.**
        "drifted": broken,
        "source_doc": "docs/design/GX-LAW-03_개인정보처리방침_초안_v0.1.md",
        "status": "초안 — 법률 검토 전 (대장 상태 미측정)",
    }


# ═══════════════════════════════════════════════════════════════════════════
# LAW-02 — 안내판·방침의 「제품 자동」 칸
# ═══════════════════════════════════════════════════════════════════════════
AUTO, CONFIRM = "제품 자동", "확인"


def _cell(label: str, value: Any, source: str, why: str = "") -> dict[str, Any]:
    """칸 하나. **값이 없으면 `확인`이다** — 비어 있는 것과 없는 것을 가른다."""
    if value is None or value == "":
        return {"label": label, "value": None, "source": CONFIRM,
                "why": why or "제품이 이 값을 선언한 자리가 없다"}
    return {"label": label, "value": value, "source": source, "why": why}


def notice_draft(*, scope) -> dict[str, Any]:
    """LAW-02 안내판 문안 + 운영·관리 방침의 「제품 자동」 칸.

    카메라 수·주소 채움률은 **분모와 함께** 낸다 (D-301) — 「39대」만 보면 그것이
    40 중 39인지 400 중 39인지 모르고, 안내판은 그 차이로 틀린 종이가 된다.
    """
    from stream_monitors.services import bulk_register

    gap = bulk_register.address_gap(scope=scope)
    days = retention_days()

    board = [
        _cell("설치 목적", None, AUTO, "재난·안전 감시 — 조례 근거는 운영자가 적는다"),
        _cell("설치 장소", gap.get("with_address"), AUTO,
              f"주소가 적힌 카메라 {gap.get('with_address')}/{gap.get('total')}대 · "
              f"주소 없음 {gap.get('without_address')}대는 안내판을 만들 수 없다"),
        _cell("촬영 범위", None, AUTO, "카메라 화각 설명은 설치자가 적는다"),
        _cell("촬영 시간", PRODUCT_SPEC["shooting_hours"], AUTO),
        _cell("관리책임자", None, AUTO, "부서·직위·연락처는 운영자가 적는다"),
        _cell("보관 기간", days, AUTO,
              "LAW-02a 가 선언한 값이다. 출처와 「그 수대로 지우는가」는 "
              "보존 정책 면이 함께 낸다 — 집행 없이 적힌 수는 안내판을 "
              "거짓말로 만든다(D-301)"),
        _cell("위탁 여부", None, AUTO, "수탁자 계약은 운영자가 적는다"),
    ]

    policy = [
        _cell("설치 대수", gap.get("total"), AUTO),
        _cell("주소 채움률", gap.get("coverage"), AUTO,
              "분모가 0이면 비율은 null 이다 — 0이 아니다"),
        _cell("촬영 시간·보관 기간", days, AUTO,
              "24시간 · 보존 일수는 LAW-02a 선언값이다"),
        _cell("음성 녹음", PRODUCT_SPEC["audio_recording"], AUTO),
        _cell("안전성 확보 조치", "접근 통제(역할) · 접속 기록(감사로그) · 무반출(계약 11조)",
              AUTO, "암호화 항목은 [확인]"),
    ]

    cells = board + policy
    return {
        "board": board,
        "policy": policy,
        #: ★ 손으로 채워야 하는 칸을 **스스로 센다** — K4 `manual_fields` 와 같은 규약.
        #:   이 수가 0이 아니면 안내판은 아직 게시할 수 없다.
        "confirm_fields": [c["label"] for c in cells if c["source"] == CONFIRM],
        "auto_fields": [c["label"] for c in cells if c["source"] == AUTO],
        "camera_census": gap,
        "source_doc": "docs/design/GX-LAW-02_영상정보처리기기_고지_초안_v0.1.md",
        "status": "초안 — 법률 검토 전 (대장 상태 미측정)",
    }
