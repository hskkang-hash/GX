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
    """사람 한 명을 종이에 적는 법. **id 도 계정명도 찍지 않는다.**

    이름 규칙은 `common/role_request._display_name` 한 곳에서 온다 — 두 벌을 두면
    어느 화면에서는 성이 앞이고 어느 종이에서는 뒤가 된다 (D-212).

    ★★ [턴 AA · 대표 결정 ⑩ · 2026-09-21] **괄호 안 계정명을 지운다.**
      [실측 2026-09-21 · 사건 4798 검수본] 이 함수가 종이에 찍은 것:
          판정자  「… (gxseed_u1_operator)」   발행자  「… (gxseed_u4_official)」
      이 파일의 머리말은 「내부 id 를 종이에 찍지 않는다」고 적어 두었는데, 그 규율이
      **계정명으로 샜다** — 계정명은 로그인에 쓰는 내부 식별자이고, 사전 §4 가 사용자
      본문에서 금한 자리다. 감사에게 나가는 종이에 로그인 이름이 다섯 줄 박히면
      받는 사람은 그것을 조직의 사람 목록으로 읽는다.

    ★ 대표는 「표시명으로」라고 했다. **표시명 사전은 U56 이 만든다** — 아직 없으면
      이 함수는 **가리는 쪽**으로 떨어진다(지어내지 않는다). 사전이 서는 날 고칠 자리는
      아래 `_role_display_name` **한 곳**이다 — 부르는 쪽은 한 줄도 안 바뀐다.
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
        #: 실명이 있으면 **그것만** 적는다. 계정명은 종이에 더 보탤 사실이 없다 —
        #: 사람을 가리키는 일은 이미 이름이 끝냈다.
        return name
    role = _role_display_name(user) if username else ""
    if role:
        return role
    if username:
        #: 실명도 표시명도 없다 — **계정명을 적지 않고, 없다고 적는다.**
        #: 여기서 계정명을 적으면 「가린다」는 결정이 이 한 줄에서 새어 나간다.
        return "실명 미등록 (계정명은 적지 않습니다)"
    return "확인 불가 (실명 미등록)"


def _role_display_name(user) -> str:
    """계정명 대신 종이에 적을 **역할 표시명**. 없으면 빈 문자열.

    ★ **U56 이 만드는 사전 한 곳만 본다.** 여기서 계정명을 잘라 역할을 유추하지 않는다 —
      `gxseed_u1_operator` 에서 「관제요원」을 뽑아내는 것은 추측이고, 추측이 감사 종이에
      찍히면 나중에 근거처럼 읽힌다 (D-280). 사전이 아직 없으면 **없는 것이 답이다.**

    [실측 2026-09-21 · 턴 AA] `common.role_request` 에 역할 표시명 사전이 **아직 없다.**
    U56 에게 쪽지로 청했고(`turn-aa/U56.inbox/U24.md`), 그때까지 이 함수는 빈 문자열을
    내고 부르는 쪽은 계정명을 **가린다**.
    """
    try:
        from common import role_request
    except Exception:                      # noqa: BLE001 — 종이는 나가야 한다
        return ""
    table = getattr(role_request, "ROLE_DISPLAY_NAMES", None)
    if not isinstance(table, dict):
        return ""
    username = (getattr(user, "username", "") or "").strip()
    return str(table.get(username) or "").strip()


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


# ═══════════════════════════════════════════════════════════════════════════
# 턴 AA — **가리는 자리 셋** (대표 결정 ⑩ · 2026-09-21)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 이 절이 생겼나 — **재서 적었다.** [실측 2026-09-21 · 사건 4798 검수용 DOCX]
#   상급기관에 나가는 1쪽 종이에 이런 것들이 실제로 찍혀 있었다:
#
#       ④ 조치 이력 「대상」   geumsan@org.kr · oper_chi1@yopmail.com · …  (수신자 메일 5줄)
#       ④ 같은 열(웹푸시)      drill:webpush:dc716379fa14                  (표식 + 기기 토큰)
#       ① 「설치 주소」        경기도 안양시 만안구 안양천서로 100          (번지까지)
#
# ★ **가린 것은 가렸다고 적는다.** 아래 함수들은 지운 자리에 **왜 비었는지**를 남긴다 —
#   빈 칸은 「없었다」로도 읽히고(D-290), 그러면 「알림을 아무에게도 안 보냈다」가 된다.
#
# ★ 조건을 두지 않았다. 「대외본일 때만 가린다」는 칸을 만들면 그 칸을 안 켠 종이가
#   언젠가 나가고, 나간 종이는 되돌릴 수 없다. **한 모양으로 나간다.**

#: 가린 칸에 적는 말. 낱말을 여기 한 곳에 둔다 — 자리마다 적으면 종이가 자리마다
#: 다른 말로 「가렸다」고 말한다.
MASK_NOTE_CONTACT = "수신자 연락처 비표시"
MASK_NOTE_DEVICE = "기기 등록 (식별자 비표시)"
MASK_NOTE_ADDRESS = "이하 비표시"
MASK_NOTE_UNKNOWN = "대상 비표시"

#: 종이 맨 아래에 남기는 **가림 고지**. 가린 사실을 숨기면 그것도 거짓말이다.
MASK_FOOTNOTE = ("수신자 연락처 · 기기 등록 정보 · 상세 주소는 이 종이에 적지 않습니다 "
                 "(가린 칸에는 그 사유를 적습니다). 원본은 알림 이력 화면에서 "
                 "권한이 있는 사람만 볼 수 있습니다.")

#: 행정구역 이름의 끝 글자. 여기까지가 **동까지만**이고 그 뒤(도로명·번지·건물)는 지운다.
_ADMIN_SUFFIXES = ("도", "시", "군", "구", "읍", "면", "동", "리", "가")


def mask_recipient(address, channel: str = "") -> str:
    """조치 이력 「대상」 한 칸. **연락처를 종이에 적지 않는다.**

    갈래를 나눠 적는다 — 「가렸다」 한 낱말로 뭉치면 메일로 보낸 것과 기기로 보낸 것이
    같은 글자가 되고, 읽는 사람은 **몇 갈래로 알렸는지**를 못 읽는다.

    · 메일     `geumsan@org.kr`            → `(비표시)@org.kr`
      ★ 아이디는 통째로 지우고 **도메인은 남긴다** — 도메인은 사람이 아니라 **기관**이고,
        「어느 기관에 알렸나」는 결재가 읽어야 할 사실이다. 아이디 앞 글자를 남기는
        방식은 쓰지 않았다: 한 글자라도 남으면 그것은 여전히 그 사람의 조각이다.
    · 기기 토큰 `drill:webpush:dc716379fa14` → 「기기 등록 (식별자 비표시)」
      ★ 여기는 **한 글자도 안 남긴다.** 토큰 자체가 기기를 가리키고, 앞머리
        (`drill:webpush:`)는 우리 표식이라 사전 §4 가 사용자 본문에서 금한다.
    · 전화     `010-1234-5678`             → `010-****-****`
    · 그 밖    모양을 모른다               → 「대상 비표시」
      ★ 모르는 모양을 **그대로 내보내지 않는다** — 닫는 쪽이 기본값이다.
    """
    raw = str(address or "").strip()
    if not raw:
        return UNKNOWN
    if "@" in raw and raw.count("@") == 1:
        local, _, domain = raw.partition("@")
        if local and domain and "." in domain:
            return f"(비표시)@{domain}"
    digits = [c for c in raw if c.isdigit()]
    if len(digits) >= 9 and all(c.isdigit() or c in "-+ " for c in raw):
        head = raw.lstrip("+")[:3]
        return f"{head}-****-****"
    return MASK_NOTE_DEVICE if _looks_like_device_token(raw, channel) else MASK_NOTE_UNKNOWN


def _looks_like_device_token(raw: str, channel: str) -> bool:
    """이 값이 **기기 등록 토큰**인가 — 채널이 먼저 답하고, 모양은 거들기만 한다.

    ★ 모양(`:` 가 있다 · 16진수가 길다)으로만 판정하지 않는다: 모양은 남의 값과
      우연히 같아질 수 있고, 그때 사람 연락처가 「기기」로 적힌다.
    """
    kind = (channel or "").strip().lower()
    if "push" in kind or "webpush" in kind or "fcm" in kind or "device" in kind:
        return True
    return ":" in raw and len(raw) >= 16


def mask_address(address: str) -> str:
    """설치 주소 한 칸. **동까지만 적는다** (대표 결정 ⑩).

    ★ 못 가르면 **통째로 가린다.** 「경기도 안양시 만안구 안양천서로 100」에서 행정구역
      세 마디만 남기는 것이 규칙인데, 모양이 낯선 주소에서 규칙이 빗나가면 번지가
      그대로 나간다 — 빗나가는 쪽이 여는 쪽이면 안 된다.
    ★ 값이 주소가 아니라 **상태 글자**(「확인 중」·「확인 실패」·「기록 없음」)면 그대로 둔다.
      가릴 것이 없는 칸을 가리면 「주소가 있는데 감췄다」로 읽힌다.
    """
    raw = (address or "").strip()
    if not raw or raw in (UNKNOWN, "확인 중", "확인 실패", "주소 변환 사용 안 함"):
        return raw or UNKNOWN
    kept: list[str] = []
    for token in raw.split():
        if not token.endswith(_ADMIN_SUFFIXES):
            break                            # 행정구역이 끝났다 — 여기부터는 도로명·번지다
        kept.append(token)
    if not kept:
        #: 행정구역 마디를 한 개도 못 찾았다 — 이 모양을 우리가 모른다. 닫는다.
        return f"({MASK_NOTE_ADDRESS})"
    if len(kept) == len(raw.split()):
        return raw                          # 지울 것이 없었다 — 이미 동까지다
    return f"{' '.join(kept)} ({MASK_NOTE_ADDRESS})"


# ═══════════════════════════════════════════════════════════════════════════
# 턴 AA — **「훈련」 배너** (대표 결정 ⑨ · 2026-09-21)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 — **재서 적었다.** [실측 2026-09-21 · 턴 Z] 훈련(`drill`) 사건 305027 로 1쪽을
#   실물로 뽑았더니 완성된 HTML 에 「훈련」 0건 · `drill` 0건이었다. 청구는 훈련을 빼는데
#   (`common/billing_marks.exclude_unbillable`) **종이는 훈련이라고 말하지 않았다.**
#   그 종이가 결재에 올라가면 읽는 사람은 그것을 실제 재난으로 읽는다.
#
# ★ 기울기는 **실운영 쪽**이다(`probe_marker.is_drill_track` 머리말): 실제 경보를 훈련으로
#   잘못 적으면 결재가 손을 늦춘다. 그래서 모르면 배너를 **안 붙인다.**

#: 종이에 적는 한 줄. 낱말 「훈련」은 사전 §2 에 이미 있다(실운영 / 시드(검수용) / 훈련).
DRILL_BANNER = ("[GuardianX] 훈련 — 이 보고서는 훈련 상황의 기록입니다. "
                "실제 재난 상황이 아닙니다.")

#: 훈련을 가리키는 **한 낱말**. `stream_monitors.services.drill.DATA_SOURCE` 가 정본이고
#: 여기서 문자열을 새로 적지 않는다 — 두 벌이면 한쪽을 고친 날 다른 쪽이 남는다.
def _drill_word() -> str:
    from stream_monitors.services.drill import DATA_SOURCE

    return DATA_SOURCE


def data_source_of(event, given: str = "") -> str:
    """이 사건이 **훈련인가 실운영인가** — 종이가 쓰는 한 낱말.

    `given` 이 오면 그것을 믿는다: 부르는 쪽(`build_incident_html`)이 축 **둘**을 다 보는
    정본(`apps/dsm/services.event_data_source`)을 이미 물었다는 뜻이다.
    안 오면 **행 표식 한 축**만 본다 — 이 함수는 DB 를 안 만진다.

    ⚠ 그래서 `given` 없이 부르면 **훈련 창(UX-17)에서 난 사건을 놓친다.** 놓치는 쪽이
      실운영이라 안전한 방향이지만, 놓친다는 사실은 적어 둔다.
    """
    if given:
        return given
    from common.probe_marker import is_drill_track

    return _drill_word() if is_drill_track(getattr(event, "track_id", "")) else "live"


def drill_banner(data_source: str) -> str:
    """훈련이면 배너 한 줄, 아니면 **빈 문자열**. 실사건에는 한 글자도 안 붙는다.

    ⚠ 강조를 **인라인으로** 준다(`.banner.drill` 같은 규칙을 CSS 에 두지 않는다).
      [실측 2026-09-21 · 턴 AA] 규칙 한 줄과 그 위 주석을 `_CSS` 에 뒀더니 **실사건 종이의
      HTML 에도 「훈련」·`drill` 글자가 들어갔다** — 찍힌 종이에는 안 보이지만
      (`docx_export` 가 `<style>` 을 떼어낸다) HTML 을 훑어 재는 사람에게는 **실사건에
      훈련 표시가 있는 것으로 보인다.** 거짓 양성을 만드는 측정면은 만들지 않는다.
    ⚠ 색과 굵기에 기대지 않는다 — DOCX 로 옮기면 서식이 떨어지고 흑백 인쇄도 있다.
      **글자가 「훈련」이라고 말하는 것**이 이 배너의 본체다.
    """
    try:
        word = _drill_word()
    except Exception:                       # noqa: BLE001 — 배너가 종이를 죽이지 않는다
        word = "drill"
    if (data_source or "").strip() != word:
        return ""
    return ("<div class=\"banner\" style=\"border-width:3px;font-size:10pt\">"
            f"{escape(DRILL_BANNER)}</div>")


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
               sources_failed=(), data_source: str = "") -> str:
    """1쪽 사건 보고서의 HTML. **여기가 서식이다.**

    Args:
        event: K1 `EventView` — 좁히기를 이미 통과한 이벤트 하나.
        clock: `apps.dsm.services.response_clock` 이 낸 네 시각 사전.
        actions: K4 `ActionRow` 들 (K2 발송 기록 그대로 · 두 벌로 적재하지 않는다).
        tenant: 머리글 기관명.
        issued_by: 이 종이를 뽑은 사람.
        sources_failed: 가져오지 못한 출처 이름들. 있으면 **종이에 배너로 남는다**.
        data_source: `live` | `drill`. 비면 **행 표식 한 축**으로 여기서 정한다
            (`data_source_of` 머리말 ⚠ — 훈련 창은 못 본다).
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
    #: ★ 훈련 배너는 **맨 위**다. 아래에 있으면 읽는 사람이 표를 먼저 읽고, 표를 읽은
    #:   뒤에 「훈련이었다」를 알면 이미 실제 상황으로 한 번 읽은 것이다.
    parts.append(drill_banner(data_source_of(event, data_source)))
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
    #: 대표 결정 ⑩ — **동까지만.** 번지는 이 종이에 안 적는다.
    parts.append(_row("설치 주소", mask_address(address)))
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
            channel = str(getattr(row, "channel", "") or UNKNOWN)
            parts.append(
                "<tr>"
                f"<td>{escape(channel)}</td>"
                #: 대표 결정 ⑩ — **수신자 연락처·기기 토큰을 가린다.** 갈래는 남긴다.
                f"<td>{escape(mask_recipient(getattr(row, 'recipient_address', ''), channel))}</td>"
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
        #: ★ 가린 사실을 종이가 **스스로 말한다.** 말하지 않으면 읽는 사람은 빈 자리를
        #:   「없었다」로 읽고, 그때 「아무에게도 안 알렸다」가 된다.
        f"{escape(MASK_FOOTNOTE)}<br>"
        f"{escape(timezone_note())}</div>")

    return ("<html><head><meta charset=\"utf-8\">"
            f"<title>{escape(DOCUMENT_TITLE)} {escape(str(event_id))}</title>"
            f"<style>{_CSS}</style></head><body>{''.join(parts)}</body></html>")


# ═══════════════════════════════════════════════════════════════════════════
# 턴 U (P-173 U24) — 서식 둘이 더 선다: 「이번 달 우리 센터」 · 상급기관 제출용
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 같은 파일인가 — 이 파일은 「사건 보고서」가 아니라 **재난안전과에 나가는 종이의
#   서식**이다. 택배 칸 금지 목록(`FORBIDDEN_FIELD_TOKENS`) · 등급/유형 낱말 ·
#   「기록 없음」 규약 · 시간대 고지(`timezone_note`) · CSS 한 벌이 여기 있고, 서식이
#   갈리면 종이 셋이 서로 다른 낱말을 쓰게 된다. 값을 모으는 일(집계 · 사건 조회 ·
#   실행 기록)은 여기서 하지 않는다 — `apps/dsm/monthly_report.py` 가 한다.
#   **이 절의 함수들은 DB 를 만지지 않는다**(인자로 받은 값만 그린다) — 그래서
#   시험이 DB 없이 「택배 필드 0」을 셀 수 있다.

#: 월간본 제목 · 상급 제출용 제목. 화면 단추(`Reports.tsx`)와 **같은 글자**여야
#: 사람이 「그 보고서」라고 부를 수 있다.
MONTHLY_TITLE = "이번 달 우리 센터"
UPPER_TITLE = "상급기관 제출용 보고서"

#: 자동본인가 사람이 부른 것인가 — 종이에 적는다. PRD §7.4 「사람 손 없이 나왔는가」는
#: `DsmReportRun.trigger` 칸이 답하고, 그 답이 **종이에도** 남아야 결재가 그것을 본다.
TRIGGER_LABEL = {"auto": "자동 생성 (사람 손 없음)", "manual": "사람이 요청"}

#: 월간본 표에 싣는 축 행의 상한. 넘으면 **넘었다고 적는다**(D-301).
AXIS_ROWS_ON_PAGE = 10
#: 상급 제출용에 싣는 사건 줄의 상한.
UPPER_ROWS_ON_PAGE = 40


def _head(*, tenant: str, title: str, meta: str) -> str:
    from django.utils import timezone

    return ("<div class=\"head\">"
            f"<div class=\"org\">{escape(tenant)}</div>"
            f"<h1>{escape(title)}</h1>"
            f"<div class=\"meta\">{escape(meta)} · 발행 {escape(_when(timezone.now()))}</div>"
            "</div>")


def _note_block(note: str) -> str:
    """「특이사항」 — 자동본을 사람이 고치는 칸(부속서 A U2#7).

    ★ 비어 있어도 **칸은 남긴다.** 칸이 사라지면 「특이사항이 없었다」와 「아무도 안
      적었다」를 가를 수 없고, 결재자는 빈 자리를 전자로 읽는다.
    """
    body = (note or "").strip() or "기재된 특이사항이 없습니다."
    return ("<h2>특이사항</h2><table><tr><td class=\"wide\">"
            f"{escape(body)}</td></tr></table>")


def _foot(extra: str = "") -> str:
    return ("<div class=\"foot\">이 문서는 GuardianX 가 사건 기록에서 자동 생성했습니다. "
            "기록이 없는 칸은 「기록 없음」으로 적습니다(0으로 적지 않습니다)."
            f"{(' ' + escape(extra)) if extra else ''}<br>"
            f"{escape(timezone_note())}</div>")


def _axis_table(rows, *, key_title: str, labels: dict | None = None) -> str:
    """축 하나를 표로. `rows` 는 `stats.stats_axes` 가 낸 행들(`key`·`label`·`count`).

    ★ 행이 0 이면 **빈 표를 그리지 않는다** — 「0건이었다」를 글자로 적는다.
      빈 표는 「아직 안 불러왔다」로도 읽힌다(분모 0 인 초록은 초록이 아니다).
    """
    rows = list(rows or ())
    if not rows:
        return ("<table><tr><td class=\"wide\">"
                f"{escape(key_title)} — 이 기간에 해당하는 건이 0건입니다."
                "</td></tr></table>")
    labels = labels or {}
    out = ["<table class=\"rows\"><tr><th>", escape(key_title), "</th><th>건수</th></tr>"]
    for r in rows[:AXIS_ROWS_ON_PAGE]:
        key = str(r.get("key", ""))
        label = labels.get(key) or str(r.get("label") or key)
        out.append(f"<tr><td>{escape(label)}</td><td>{escape(str(r.get('count', 0)))}</td></tr>")
    out.append("</table>")
    if len(rows) > AXIS_ROWS_ON_PAGE:
        out.append(f"<div class=\"note\">{len(rows)}줄 중 {AXIS_ROWS_ON_PAGE}줄만 실었습니다 "
                   "— 전체는 통계 화면에서 확인하십시오.</div>")
    return "".join(out)


def build_monthly_html(*, tenant: str, issued_by: str, since, until,
                       summary: dict, axes: dict, note: str = "",
                       trigger: str = "auto") -> str:
    """「이번 달 우리 센터」 자동본 — **집계는 받아서 그리기만 한다.**

    Args:
        summary: `apps.dsm.stats.stats_summary` 가 낸 사전 그대로.
        axes: `apps.dsm.stats.stats_axes` 가 낸 사전 그대로.
        trigger: `auto` | `manual` — 종이에 적는다.

    ★ 여기서 더하거나 나누지 않는다. 합계를 종이에서 다시 세면 화면의 수와 종이의
      수가 갈리고, 갈린 두 수는 **어느 쪽이 맞는지 아무도 모른다**(AC-5 규약).
    """
    total = summary.get("total")
    parts: list[str] = [
        _head(tenant=tenant, title=MONTHLY_TITLE,
              meta=(f"집계 기간 {_when(since)} ~ {_when(until)} · "
                    f"{TRIGGER_LABEL.get(trigger, trigger)} · 발행자 {issued_by}")),
    ]
    if summary.get("capped"):
        parts.append("<div class=\"banner\">[GuardianX] 이 보고서는 불완전합니다 — "
                     f"집계 상한({summary.get('row_cap')}건)에 닿아 그 위는 세지 못했습니다."
                     "</div>")

    parts.append("<h2>① 이번 달 한 장 요약</h2><table>")
    parts.append(_pair("집계 기간 시작", _when(since), "집계 기간 끝", _when(until)))
    parts.append(_pair("전체 사건 수", UNKNOWN if total is None else f"{total}건",
                       "생성 방식", TRIGGER_LABEL.get(trigger, trigger)))
    parts.append("</table>")

    by_sev = summary.get("by_severity") or {}
    parts.append("<h2>② 등급별</h2><table class=\"rows\">"
                 "<tr><th>등급</th><th>건수</th></tr>")
    for code in ("critical", "warning", "info"):
        #: 세 등급은 **언제나 세 줄**이다 — 0건인 등급이 사라지면 「없었다」가 표에서
        #: 지워지고, 읽는 사람은 그 등급을 안 센 것으로 읽는다.
        parts.append(f"<tr><td>{escape(SEVERITY_LABEL[code])}</td>"
                     f"<td>{escape(str(by_sev.get(code, 0)))}</td></tr>")
    parts.append("</table>")

    axis_rows = (axes or {}).get("axes") or {}
    parts.append("<h2>③ 유형별</h2>")
    parts.append(_axis_table(axis_rows.get("event_type"), key_title="유형",
                             labels=EVENT_TYPE_LABEL))
    parts.append("<h2>④ 카메라별 (많은 순)</h2>")
    parts.append(_axis_table(axis_rows.get("camera"), key_title="카메라"))
    parts.append("<h2>⑤ 시간대별</h2>")
    parts.append(_axis_table(axis_rows.get("hour"), key_title="시간대"))

    by_state = summary.get("by_response_state") or {}
    parts.append("<h2>⑥ 대응 진행</h2><table class=\"rows\">"
                 "<tr><th>단계</th><th>건수</th></tr>")
    for code, label in RESPONSE_STATE_LABEL.items():
        parts.append(f"<tr><td>{escape(label)}</td>"
                     f"<td>{escape(str(by_state.get(code, 0)))}</td></tr>")
    parts.append("</table>")

    parts.append(_note_block(note))
    parts.append(_foot("집계 수는 통계 화면(같은 기간)의 수와 같은 함수에서 나옵니다."))
    return ("<html><head><meta charset=\"utf-8\">"
            f"<title>{escape(MONTHLY_TITLE)}</title>"
            f"<style>{_CSS}</style></head><body>{''.join(parts)}</body></html>")


def build_upper_html(*, tenant: str, issued_by: str, since, until,
                     rows, note: str = "", missing: int = 0) -> str:
    """상급기관 제출용 — **체크된 사건만** + 요약.

    Args:
        rows: 사전들. `event_id` · `occurred_at` · `severity` · `event_type` ·
            `camera` · `verdict` · `reported_at` 칸을 본다.
        missing: 체크는 있는데 사건을 못 읽은 수(파기·권한). **0 이 아니면 종이에 적는다** —
            「없었다」와 「못 가져왔다」는 다른 사실이다(D-290).

    ★ 체크(`DsmUpperReportFlag`)가 0건이면 **빈 표를 내지 않는다.** 「이 기간에 상급기관
      보고 대상으로 표시된 사건이 없습니다」라고 적는다.
    """
    rows = list(rows or ())
    parts: list[str] = [
        _head(tenant=tenant, title=UPPER_TITLE,
              meta=(f"대상 기간 {_when(since)} ~ {_when(until)} · 발행자 {issued_by}")),
    ]
    if missing:
        parts.append("<div class=\"banner\">[GuardianX] 이 보고서는 불완전합니다 — "
                     f"표시된 사건 {missing}건을 읽지 못했습니다(보존 기한 경과 또는 접근 불가)."
                     "</div>")

    sev_count = {"critical": 0, "warning": 0, "info": 0}
    for r in rows:
        code = r.get("severity")
        if code in sev_count:
            sev_count[code] += 1

    parts.append("<h2>① 제출 요약</h2><table>")
    parts.append(_pair("대상 사건 수", f"{len(rows)}건",
                       "심각 등급", f"{sev_count['critical']}건"))
    parts.append(_pair("경계 등급", f"{sev_count['warning']}건",
                       "주의 등급", f"{sev_count['info']}건"))
    parts.append("</table>")

    parts.append("<h2>② 대상 사건</h2>")
    if not rows:
        parts.append("<table><tr><td class=\"wide\">이 기간에 상급기관 보고 대상으로 "
                     "표시된 사건이 없습니다.</td></tr></table>")
    else:
        parts.append("<table class=\"rows\"><tr><th>사건번호</th><th>발생</th>"
                     "<th>등급</th><th>유형</th><th>카메라</th><th>판정</th>"
                     "<th>보고 시각</th></tr>")
        for r in rows[:UPPER_ROWS_ON_PAGE]:
            parts.append(
                "<tr>"
                f"<td>{escape(str(r.get('event_id', '')))}</td>"
                f"<td>{escape(_when(r.get('occurred_at')))}</td>"
                f"<td>{escape(_label(SEVERITY_LABEL, r.get('severity')))}</td>"
                f"<td>{escape(_label(EVENT_TYPE_LABEL, r.get('event_type')))}</td>"
                f"<td>{escape(str(r.get('camera') or UNKNOWN))}</td>"
                f"<td>{escape(_label(VERDICT_LABEL, r.get('verdict'), '미판정'))}</td>"
                f"<td>{escape(_when(r.get('reported_at')))}</td>"
                "</tr>")
        parts.append("</table>")
        if len(rows) > UPPER_ROWS_ON_PAGE:
            parts.append(f"<div class=\"note\">{len(rows)}건 중 {UPPER_ROWS_ON_PAGE}건만 "
                         "실었습니다 — 나머지는 사건 목록 화면에서 확인하십시오.</div>")

    parts.append(_note_block(note))
    parts.append(_foot("「대상」은 사람이 남긴 상급 보고 체크입니다 — 규칙이 자동으로 "
                       "고른 것이 아닙니다."))
    return ("<html><head><meta charset=\"utf-8\">"
            f"<title>{escape(UPPER_TITLE)}</title>"
            f"<style>{_CSS}</style></head><body>{''.join(parts)}</body></html>")


def build_incident_html(*, scope, event_id: int) -> str:
    """사건 1쪽의 **HTML** — PDF 와 DOCX 가 같은 글자에서 나오게 하는 자리.

    `apps/dsm/services.incident_report()` 는 이 조립을 자기 안에 갖고 PDF 만 냈다. DOCX
    정본(결정 ⑤)이 서면서 같은 조립이 두 번째로 필요해졌고, **두 벌이 되면 어느 날
    한쪽만 고쳐진다** — 그래서 조립을 여기 한 곳에 둔다.
    ⚠ 등록 요청(조율자): `services.incident_report()` 의 조립 다섯 줄을 이 함수 호출로
      바꾸면 조립이 하나가 된다. `services.py` 는 이번 턴 U24 소유가 아니라 손대지 않았다.

    Raises:
        Http404: 없는 사건 · 남의 사건 (문지기는 K1 이 선다 — 여기서 다시 세우지 않는다)
        IncidentReportUnavailable: 사건은 있는데 자료를 못 가져왔다 (409)
    """
    from kernels.k4_report import build_context

    from apps.dsm import services
    from apps.dsm.exceptions import IncidentReportUnavailable

    context = build_context(scope=scope, event_id=event_id)
    events = list(getattr(context, "events", ()) or ())
    if not events:
        raise IncidentReportUnavailable(
            "사건 자료를 가져오지 못해 보고서를 만들 수 없습니다 — "
            f"실패한 출처 {list(context.sources_failed) or ['(사유 미기재)']}")
    actor = scope.require_actor()
    #: ★ [턴 AA · 대표 ⑨] 훈련 판정은 **축이 둘**이다(행 표식 · 훈련 창 — P-201).
    #:   그 둘을 하나로 답하는 정본은 `services.event_data_source` 이고, 서식은 그것을
    #:   **묻기만** 한다. 서식이 제 손으로 `track_id` 를 가르기 시작하면 뜻이 두 벌이 된다.
    #:   못 물으면 서식이 행 표식 한 축으로 떨어진다 — 배지 하나 때문에 종이가 500 이
    #:   되지 않는다(보조 정보가 본문을 죽이지 않는다 · `event_data_sources` 와 같은 규율).
    try:
        source = services.event_data_source(view=events[0])
    except Exception:                       # noqa: BLE001
        source = ""
    return build_html(
        event=events[0],
        clock=services.response_clock(scope=scope, event_id=event_id),
        actions=context.actions, tenant=tenant_name(actor),
        issued_by=person_label(actor),
        sources_failed=tuple(context.sources_failed),
        data_source=source)
