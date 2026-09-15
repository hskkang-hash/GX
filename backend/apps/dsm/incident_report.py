# -*- coding: utf-8 -*-
"""사건 보고서 **1쪽 서식** — UX-30 / P-125 (2026-09-10 · 차선 B).

왜 이 파일이 생겼나 — **실측이 먼저다**
---------------------------------------
재난안전과 공무원이 상황 보고서를 받으려고 손으로 API 를 불렀다:

    GET /api/dsm/reports/7.pdf                    → 200 · 14,848 bytes
    GET /api/dsm/reports/7.pdf?event_id=4802      → 200 · 14,848 bytes · **md5 동일**

나온 종이는 **「배송 완료 보고서」**였다. 안에 있던 칸 이름:
`Order Information` · `Sender Name` · `Recipient Name` · `Pickup Location Terminal` ·
`Delivery Fee` · `Tax Amount` · `ETRI Receipt ID` — 그리고 `{{ order__sender_name }}`
같은 자리표시자가 **치환되지 않은 채로** 인쇄돼 있었다.

원인은 렌더러가 아니다. 셋이 겹쳤다:

  ① `/api/dsm/reports/{template_id}.pdf` 의 경로 숫자는 **템플릿 id** 이지 사건 id 가
     아니다. `7` 은 택배 운송장 서식의 행 번호였다.
  ② `report_template` 표의 19행은 **전부 택배 제품의 운송장**이다 — 사건 보고서 서식은
     그 표에 **한 행도 없다**.
  ③ K4 의 치환은 `{{ events }}`·`{{ actions }}`·`{{ captures }}`·`{{ since }}`·
     `{{ until }}`·`{{ sources_failed }}`·`{{ manual_fields }}` **일곱 이름만** 바꾼다
     (`kernels/k4_report/services._fill`). 운송장 서식에는 그 일곱이 하나도 없으므로
     **바꿀 자리가 없고**, 그래서 `event_id` 를 붙여도 바이트가 같았다.
     ★ 「렌더러가 event 를 안 읽는다」가 아니라 **읽은 값을 꽂을 자리가 서식에 없었다.**

그래서 고치는 자리는 렌더러가 아니라 **서식**이다. 서식을 표의 행으로 심지 않고 코드에
두는 이유는 `kernels/k4_report/services.render_html` 독스트링에 적었다.

이 서식이 지키는 것
-------------------
· **택배 칸 0개.** 아래 `FORBIDDEN_FIELD_TOKENS` 가 그 목록이고,
  `tests/test_incident_report.py` 가 완성된 HTML 에서 하나라도 나오면 빨개진다.
· **고객의 언어.** 등급·유형·판정을 코드값(`critical`/`fire`/`rejected`)이 아니라
  계약이 정한 낱말로 적는다 — 등급 세 낱말은 DA-01 F-04 의 **심각·경계·주의**다
  (앞판의 「위험·경고·정보」가 아니다 · UX-22).
· **대응 시계 네 시각.** 발생 · 접수 · 조치 시작 · 종결. 없는 시각은 「기록 없음」이고
  **0 이 아니다** (D-290) — 빈 칸을 0 으로 적으면 「즉시 처리」로 읽힌다.
· **판정자는 사람의 이름으로.** 내부 id(`#105`)를 종이에 찍지 않는다. 이름이 없으면
  계정명으로 떨어지고, 그것도 없으면 **「확인 불가」라고 적는다** — 감사에게 나가는
  종이에 내부 식별자를 찍으면 받는 사람이 그것을 사람 이름으로 읽는다.
· **못 가져온 출처는 종이에 남는다.** K4 의 `INCOMPLETE_BANNER` 와 같은 규약(D-290):
  「조치가 없었다」와 「조치를 못 가져왔다」는 다른 사실이다.

모델을 직접 만지는 한 줄 — **예외이고, 이유는 이것 하나다**
-----------------------------------------------------------
`reviewer_label()` 이 `AUTH_USER_MODEL` 을 한 번 읽는다. K1 의 `EventView` 는
`reviewed_by_id` 만 나르고 **이름 칸이 없기 때문**이다(`kernels/k1_event/schemas.py:64`).
`apps/dsm/audit.py` 가 `logger.AuditLogs` 에 대해 든 것과 같은 예외이고, 같은 규약을 따른다:
읽기 한 줄 · 나가는 값은 이름 문자열 하나 · 판정식은 여기서 만들지 않는다
(`common/role_request._display_name` 을 그대로 쓴다 — 이름 규칙이 두 벌이 되면
어느 화면에서는 성이 앞이고 어느 종이에서는 뒤가 된다 · D-212).
⚠ 인계: K1 `EventView` 에 `reviewed_by_name` 이 서면 이 함수는 **지운다.**
"""
from datetime import datetime
from html import escape

#: 이 종이에 **있어서는 안 되는 칸 이름** (UX-30 검수: 「택배 필드 0」).
#:
#: ★ 목록은 실측에서 나왔다 — `reports/7.pdf` 가 실제로 인쇄한 칸 이름들이다.
#:   시험이 이 목록으로 완성된 HTML 을 훑는다. 늘리는 것은 언제나 옳고,
#:   줄이려면 **그 낱말이 왜 사건 보고서에 필요한지**를 먼저 적어야 한다.
FORBIDDEN_FIELD_TOKENS: tuple[str, ...] = (
    "order__", "Order Information", "Order Code", "Sender Name", "Sender",
    "Recipient", "Pickup Location", "Delivery Terminal", "Delivery Fee",
    "Delivery Operation", "Tax Amount", "Discount Amount", "Subtotal",
    "Total Amount", "Route Information", "ETRI Receipt", "배송", "운송장",
    "택배", "수하인", "송하인",
)

#: 등급 — **계약(DA-01 F-04)의 세 낱말**. 화면(`frontend/src/features/dsm/severity.ts`)과
#: 같은 표를 쓴다. 갈라지면 화면과 종이가 다른 등급 이름을 말한다.
SEVERITY_LABEL = {"critical": "심각", "warning": "경계", "info": "주의"}

#: 유형 — `DetectionEvent.EventType` 의 라벨. 모르는 값은 **원문을 그대로 적는다**
#: (지어내지 않는다 · D-280). 화면 표와 같은 목록이다.
EVENT_TYPE_LABEL = {
    "fire": "화재", "smoke": "연기", "flood": "침수", "person": "사람",
    "vehicle": "차량", "intrusion": "침입", "sos": "구조요청",
    "camera_down": "카메라 무응답", "storage_high": "저장 용량 임계",
    "camera_cluster_down": "카메라 군집 두절",
}

#: 판정 — **두 값뿐이다**. `new`·`closed` 는 수명주기이지 판정이 아니다 (D-293).
VERDICT_LABEL = {"confirmed": "확인 (실제 상황)", "rejected": "기각 (오탐)"}

#: 대응 진행 축(D-399)의 낱말.
RESPONSE_STATE_LABEL = {
    "occurred": "발생", "acknowledged": "접수 확인",
    "in_progress": "조치중", "closed": "종결",
}

#: 값이 없을 때 종이에 적는 말. **빈 칸을 만들지 않는다** — 빈 칸은 읽는 사람이
#: 「없었다」로도 「아직이다」로도 읽는다.
UNKNOWN = "기록 없음"

#: 한 쪽에 싣는 조치 이력의 최대 줄. 넘으면 **넘었다고 적는다** (D-301 · 잘린 표본은
#: 잘렸다고 말한다). 1쪽 서식이므로 수를 늘리지 않는다.
ACTION_ROWS_ON_PAGE = 6

#: 문서 이름. 화면의 단추와 이 이름이 같아야 사람이 「그 보고서」라고 부를 수 있다.
DOCUMENT_TITLE = "사건 보고서"


# ═══════════════════════════════════════════════════════════════════════════
# 값을 사람의 말로
# ═══════════════════════════════════════════════════════════════════════════
def _when(value: datetime | None) -> str:
    """시각 한 칸. **현지 시각으로 적는다** — UTC 를 그대로 찍으면 9시간 어긋난 종이가 된다."""
    if value is None:
        return UNKNOWN
    from django.utils import timezone

    try:
        local = timezone.localtime(value)
    except (ValueError, TypeError):       # naive datetime — 있는 그대로 적는다
        local = value
    return local.strftime("%Y-%m-%d %H:%M:%S")


def _elapsed(seconds: float | None) -> str:
    """구간. **없으면 「기록 없음」이고 0초가 아니다** (D-290)."""
    if seconds is None:
        return UNKNOWN
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}초"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}분 {sec}초"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}시간 {minutes}분"


def _label(table: dict, value, fallback: str = UNKNOWN) -> str:
    """표에 있으면 그 낱말, 없으면 **원문 그대로**. 지어내지 않는다 (D-280)."""
    if value in (None, ""):
        return fallback
    return table.get(value, str(value))


def person_label(user) -> str:
    """사람 한 명을 종이에 적는 법. **id 를 찍지 않는다.**

    이름 규칙은 `common/role_request._display_name` 한 곳에서 온다 — 두 벌을 두면
    어느 화면에서는 성이 앞이고 어느 종이에서는 뒤가 된다 (D-212).
    """
    if user is None:
        return "확인 불가 (계정 정보 없음)"
    from common.role_request import _display_name

    #: ★ `_display_name` 은 실명이 없으면 **계정명으로 떨어진다.** 그 사실을 여기서
    #:   되살린다 — 떨어진 값을 그대로 찍으면 종이에는 이름처럼 보이고, 읽는 사람은
    #:   `gxprobe_e2e` 를 사람 이름으로 읽는다. [실측 2026-09-10: 판정자 105 가 그 계정이다]
    name = (_display_name(user) or "").strip()
    username = (getattr(user, "username", "") or "").strip()
    if name and name != username:
        return f"{name} ({username})" if username else name
    if username:
        # 계정명은 사람을 가리키기는 한다 — 그러나 **실명이 아니라고 말해 준다.**
        return f"{username} (계정명 · 실명 미등록)"
    return "확인 불가 (실명 미등록)"


def reviewer_label(reviewed_by_id) -> str:
    """판정자 칸. 못 찾으면 그렇게 적는다 — **`#105` 를 종이에 찍지 않는다.**

    ★ 이 함수가 이 파일이 모델을 만지는 유일한 자리다(모듈 독스트링의 예외).
    """
    if reviewed_by_id in (None, ""):
        return "미판정 (판정자 없음)"
    try:
        from django.contrib.auth import get_user_model

        user = get_user_model()._base_manager.filter(pk=reviewed_by_id).first()
    except Exception:                      # DB 가 답을 못 줘도 종이는 나가야 한다
        user = None
    # ★ 「없는 계정」과 「이름 없는 계정」은 다른 사실이지만, **둘 다 id 를 안 찍는다.**
    return person_label(user)


def timezone_note() -> str:
    """이 종이의 시각이 **어느 시계로 적힌 것인가.**

    ★ 왜 이 한 줄이 필요한가 [실측 2026-09-10]: 이 서버의 `TIME_ZONE` 은
      **`Asia/Ho_Chi_Minh`(UTC+07:00)** 이다(`config/settings.py:799` · 기본값).
      그래서 사건 4802 의 발생 시각이 종이에 `2026-09-03 20:02:31` 로 찍히는데,
      한국 시각으로는 `22:02:31` 이다 — **두 시간 어긋난 종이**다. 그 종이가 감사에
      올라가면 아무도 두 시간을 되돌릴 수 없다.
      ⚠ 여기서 서울 시각을 **강제하지 않는다.** 강제하면 화면과 종이가 다른 시계를 쓰게
        되고, 두 수가 다른 것보다 나쁜 것은 **왜 다른지 아무도 모르는 것**이다.
        고칠 자리는 배포 설정 한 줄(`TIME_ZONE=Asia/Seoul`)이고 그것은 운영의 결정이다.
      대신 **어느 시계로 적었는지를 종이가 스스로 말한다.** 설정을 바꾸면 이 줄도 함께
      바뀐다 — 손으로 고칠 자리가 없다.
    """
    from django.conf import settings
    from django.utils import timezone

    now = timezone.localtime()
    offset = now.strftime("%z") or "+0000"
    #: 지역 이름을 그대로 적는다 — `+07` 은 숫자일 뿐이고, `Asia/Ho_Chi_Minh` 은
    #: 읽는 사람에게 **왜 두 시간 이른지**를 말해 준다.
    name = getattr(settings, "TIME_ZONE", "") or (now.tzname() or "?")
    return f"모든 시각은 서버 표준시 {name} (UTC{offset[:3]}:{offset[3:]}) 기준입니다."


def tenant_name(actor) -> str:
    """머리글의 기관명. `_watermark_text` 와 **같은 자리**에서 가져온다."""
    from common.tenant_filters import get_user_group

    group = get_user_group(actor)
    return (getattr(group, "name", "") or getattr(group, "code", "") or "(소속 미상)")


# ═══════════════════════════════════════════════════════════════════════════
# 서식
# ═══════════════════════════════════════════════════════════════════════════
_CSS = """
@page { size: A4; margin: 14mm 14mm 12mm 14mm; }
body { font-family: "Noto Sans KR","Nanum Gothic","NanumGothic",sans-serif;
       font-size: 9.5pt; color: #111; line-height: 1.45; }
h1 { font-size: 16pt; margin: 0 0 2mm 0; letter-spacing: 1px; }
.head { border-bottom: 2px solid #111; padding-bottom: 2mm; margin-bottom: 4mm; }
.head .org { font-size: 10pt; font-weight: bold; }
.head .meta { font-size: 8.5pt; color: #444; }
h2 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; padding: 1mm 2mm;
     background: #f0f0f0; border-left: 3px solid #111; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #999; padding: 1.4mm 2mm; vertical-align: top;
         font-size: 9pt; }
th { background: #f7f7f7; text-align: left; width: 26mm; font-weight: bold; }
table.rows th { width: auto; text-align: center; }
table.rows td { text-align: center; }
td.wide { width: auto; }
.note { font-size: 8pt; color: #555; margin-top: 1.5mm; }
.foot { margin-top: 5mm; padding-top: 2mm; border-top: 1px solid #999;
        font-size: 8pt; color: #444; }
.banner { border: 2px solid #111; padding: 2mm; margin-bottom: 3mm;
          font-size: 9pt; font-weight: bold; }
"""


def _row(label: str, value: str, colspan: int = 3) -> str:
    return (f"<tr><th>{escape(label)}</th>"
            f"<td class=\"wide\" colspan=\"{colspan}\">{escape(value)}</td></tr>")


def _pair(l1: str, v1: str, l2: str, v2: str) -> str:
    return (f"<tr><th>{escape(l1)}</th><td>{escape(v1)}</td>"
            f"<th>{escape(l2)}</th><td>{escape(v2)}</td></tr>")


def build_html(*, event, clock: dict, actions, tenant: str, issued_by: str,
               sources_failed=()) -> str:
    """1쪽 사건 보고서의 HTML. **여기가 서식이다.**

    Args:
        event: K1 `EventView` — 좁히기를 이미 통과한 이벤트 하나.
        clock: `apps.dsm.services.response_clock` 이 낸 네 시각 사전.
        actions: K4 `ActionRow` 들 (K2 발송 기록 그대로 · 두 벌로 적재하지 않는다).
        tenant: 머리글 기관명.
        issued_by: 이 종이를 뽑은 사람.
        sources_failed: 가져오지 못한 출처 이름들. 있으면 **종이에 배너로 남는다**.
    """
    from django.utils import timezone

    event_id = getattr(event, "event_id", None)
    verdict = getattr(event, "verdict", None)
    reason = (getattr(event, "reject_reason", None) or "").strip()
    address = (getattr(event, "address", None) or "").strip()
    address_status = getattr(event, "address_status", "") or ""
    if not address:
        # 「아직 안 물어봤다」와 「물어봤는데 실패했다」는 다른 사실이다 (D-290).
        address = {"pending": "확인 중", "failed": "확인 실패",
                   "disabled": "주소 변환 사용 안 함"}.get(address_status, UNKNOWN)

    parts: list[str] = []
    if sources_failed:
        parts.append(
            "<div class=\"banner\">[GuardianX] 이 보고서는 불완전합니다 — "
            f"가져오지 못한 출처: {escape(', '.join(sources_failed))}</div>")

    parts.append(
        "<div class=\"head\">"
        f"<div class=\"org\">{escape(tenant)}</div>"
        f"<h1>{escape(DOCUMENT_TITLE)}</h1>"
        f"<div class=\"meta\">사건번호 {escape(str(event_id))} · "
        f"발행 {escape(_when(timezone.now()))} · 발행자 {escape(issued_by)}</div>"
        "</div>")

    # ── ① 사건 개요 ──────────────────────────────────────────────────────
    parts.append("<h2>① 사건 개요</h2><table>")
    parts.append(_pair("사건번호", str(event_id),
                       "발생 시각", _when(getattr(event, "occurred_at", None))))
    parts.append(_pair("등급", _label(SEVERITY_LABEL, getattr(event, "severity", None)),
                       "유형", _label(EVENT_TYPE_LABEL,
                                     getattr(event, "event_type", None))))
    parts.append(_row("카메라", getattr(event, "stream_monitor_name", "") or UNKNOWN))
    parts.append(_row("설치 주소", address))
    parts.append("</table>")

    # ── ② 대응 경과 — 네 시각 ────────────────────────────────────────────
    parts.append("<h2>② 대응 경과 (대응 시계)</h2><table>")
    parts.append(_pair("발생", _when(clock.get("occurred_at")),
                       "접수", _when(clock.get("acknowledged_at"))))
    parts.append(_pair("조치 시작", _when(clock.get("arrived_at")),
                       "종결", _when(clock.get("closed_at"))))
    parts.append(_pair("발생→접수", _elapsed(clock.get("acknowledge_seconds")),
                       "발생→조치 시작", _elapsed(clock.get("arrive_seconds"))))
    parts.append(_pair("발생→종결", _elapsed(clock.get("close_seconds")),
                       "현재 상태",
                       _label(RESPONSE_STATE_LABEL, clock.get("response_state"))))
    if clock.get("auto_closed"):
        # ★ 사람이 닫은 것과 규칙이 닫은 것을 같은 모양으로 적지 않는다.
        parts.append(_row("종결 방식",
                          "오탐 판정에 따른 자동 종결 — 사람이 닫은 것이 아닙니다."))
    if clock.get("reopened"):
        parts.append(_row("재개 횟수",
                          f"{clock['reopened']}회 (종결 후 조치중으로 되돌린 기록)"))
    parts.append("</table>")

    # ── ③ 판정 ───────────────────────────────────────────────────────────
    parts.append("<h2>③ 판정</h2><table>")
    parts.append(_pair("판정", _label(VERDICT_LABEL, verdict, "미판정"),
                       "판정 시각", _when(getattr(event, "reviewed_at", None))))
    parts.append(_row("판정자", reviewer_label(getattr(event, "reviewed_by_id", None))))
    parts.append(_row("판정 사유", reason or "기재된 사유 없음"))
    parts.append("</table>")

    # ── ④ 조치 이력 — K2 발송 기록 그대로 ────────────────────────────────
    rows = list(actions)
    parts.append("<h2>④ 조치 이력 (알림 발송)</h2>")
    if not rows:
        parts.append("<table><tr><td class=\"wide\">"
                     "이 사건으로 발송된 알림 기록이 없습니다."
                     "</td></tr></table>")
    else:
        parts.append("<table class=\"rows\"><tr><th>채널</th><th>대상</th>"
                     "<th>발송 시각</th><th>결과</th></tr>")
        for row in rows[:ACTION_ROWS_ON_PAGE]:
            ok = "성공" if getattr(row, "succeeded", False) else (
                f"실패 — {getattr(row, 'failure_reason', '') or '사유 미기재'}")
            parts.append(
                "<tr>"
                f"<td>{escape(str(getattr(row, 'channel', '') or UNKNOWN))}</td>"
                f"<td>{escape(str(getattr(row, 'recipient_address', '') or UNKNOWN))}</td>"
                f"<td>{escape(_when(getattr(row, 'sent_at', None)))}</td>"
                f"<td>{escape(ok)}</td></tr>")
        parts.append("</table>")
        if len(rows) > ACTION_ROWS_ON_PAGE:
            parts.append(
                f"<div class=\"note\">이 쪽에는 {ACTION_ROWS_ON_PAGE}건만 실었습니다 — "
                f"전체 {len(rows)}건은 알림 이력 화면에서 확인하십시오.</div>")

    parts.append(
        "<div class=\"foot\">이 문서는 GuardianX 가 사건 기록에서 자동 생성했습니다. "
        "네 시각은 대응 전이 감사 기록에서 계산한 값이며, 기록이 없는 칸은 "
        "「기록 없음」으로 적습니다(0으로 적지 않습니다).<br>"
        f"{escape(timezone_note())}</div>")

    return ("<html><head><meta charset=\"utf-8\">"
            f"<title>{escape(DOCUMENT_TITLE)} {escape(str(event_id))}</title>"
            f"<style>{_CSS}</style></head><body>{''.join(parts)}</body></html>")
