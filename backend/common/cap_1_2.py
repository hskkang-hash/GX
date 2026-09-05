# -*- coding: utf-8 -*-
"""UX-19 — 나가는 이벤트를 **표준(OASIS CAP 1.2)** 으로 낸다.

왜 우리 스키마로 내보내지 않는가 (정본 `ga_readiness.yaml` UX-19)
-----------------------------------------------------------------
    [실측 2026-09-24 등재] 나가는 이벤트 스키마가 **우리 것**이다. 상급기관·SDN·
    에스비 App 이 각자 파싱하면 **우리가 바뀔 때마다 셋이 깨진다.**

우리 `EventView` 는 이 저장소의 사정에 따라 자란다 — `response_state` 가 붙었고
`address_status` 가 붙었고 앞으로 또 붙는다. 그 모양을 그대로 내보내면 우리의 내부
변경이 곧 남의 장애가 된다. **표준은 우리 사정으로 바뀌지 않는다** — 그것이 표준을
쓰는 이유의 전부다.

이 모듈이 하는 일 — **번역 하나**
---------------------------------
    to_cap_alert(...)  →  CAP 1.2 `<alert>` 한 벌 (dict)
    to_cap_xml(...)    →  같은 것의 XML (urn:oasis:names:tc:emergency:cap:1.2)
    render(...)        →  구독이 고른 형식으로 **바이트**를 낸다

★ **라우트가 없다.** 이 파일은 번역기이고, 문은 `apps/dsm/api.py` 가 낸다.
★ **서명하지 않는다.** 서명·재시도는 SEC-16(`common/webhook_contract.py`)이다 —
  문과 규약을 다른 절로 둔 것과 같은 이유로, 번역과 서명도 다른 파일에 둔다.

CAP 1.2 에서 우리가 지키는 것 (표준의 필수 요소)
------------------------------------------------
    alert: identifier · sender · sent · status · msgType · scope   ← 여섯 다 필수
    info : category+ · event · urgency · severity · certainty      ← 다섯 다 필수
    area : areaDesc                                                ← 있으면 필수

★ **닫힌 어휘를 지어내지 않는다.** CAP 은 위 값들의 어휘를 문서로 못박아 뒀고,
  그 밖의 낱말을 넣으면 받는 쪽 파서가 거절한다. 아래 `_CAP_*` 집합이 그 어휘이고,
  시험이 우리가 내는 모든 값이 그 안에 있는지 잰다.

★ **모르는 것은 `Unknown` 으로 낸다 — 지어내지 않는다** (D-290 · D-301).
  CAP 은 `Unknown` 을 어휘 안에 두었다. 「모른다」를 표준이 이미 표현할 수 있는데
  그럴듯한 값으로 채우면, 받는 쪽은 우리가 **재지 않은 것을 잰 것으로** 읽는다.

★ 유형 표는 **전수여야 한다** (시험이 잰다). 새 `EventType` 이 생겼는데 여기 없으면
  그 이벤트는 조용히 `Other` 로 나가고, 받는 쪽은 그것이 무엇인지 영영 모른다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from xml.etree import ElementTree as ET

#: CAP 1.2 의 XML 이름공간. 판이 바뀌면 이 문자열이 바뀐다 — 한 곳에만 둔다(D-212).
CAP_NAMESPACE = "urn:oasis:names:tc:emergency:cap:1.2"

#: 우리가 내는 CAP 판. `X-GX-Schema`(전송 규약의 판)와 **다른 것**이다:
#: 전자는 「봉투의 판」이고 이것은 「내용물의 판」이다. 섞으면 하나를 올릴 때
#: 다른 하나가 함께 올라간다.
CAP_VERSION = "1.2"

#: 형식 이름과 그 MIME. 구독이 이 중 하나를 고른다.
FORMAT_JSON = "json"
FORMAT_XML = "xml"
CONTENT_TYPES: dict[str, str] = {
    FORMAT_JSON: "application/cap+json",
    FORMAT_XML: "application/cap+xml",
}
SUPPORTED_FORMATS = frozenset(CONTENT_TYPES)

# ═══════════════════════════════════════════════════════════════════════════
# CAP 1.2 의 **닫힌 어휘** — 표준이 정한 낱말. 우리가 늘리지 않는다.
# ═══════════════════════════════════════════════════════════════════════════
CAP_STATUS = frozenset({"Actual", "Exercise", "System", "Test", "Draft"})
CAP_MSG_TYPE = frozenset({"Alert", "Update", "Cancel", "Ack", "Error"})
CAP_SCOPE = frozenset({"Public", "Restricted", "Private"})
CAP_CATEGORY = frozenset({
    "Geo", "Met", "Safety", "Security", "Rescue", "Fire", "Health",
    "Env", "Transport", "Infra", "CBRNE", "Other",
})
CAP_URGENCY = frozenset({"Immediate", "Expected", "Future", "Past", "Unknown"})
CAP_SEVERITY = frozenset({"Extreme", "Severe", "Moderate", "Minor", "Unknown"})
CAP_CERTAINTY = frozenset({"Observed", "Likely", "Possible", "Unlikely", "Unknown"})

# ═══════════════════════════════════════════════════════════════════════════
# 우리 열거값 → CAP 어휘. **전수여야 한다** (시험이 잰다)
# ═══════════════════════════════════════════════════════════════════════════

#: `DetectionEvent.EventType` → (CAP category, CAP `<event>` 에 적을 한 줄)
#: ★ `<event>` 는 자유 문자열이다. 우리 열거값(`camera_down`)을 그대로 넣지 않는다 —
#:   그 낱말은 우리 대장의 말이고, 받는 쪽 담당자가 읽는 자리다(UX-20 과 같은 규율).
EVENT_TYPE_TO_CAP: dict[str, tuple[str, str]] = {
    "fire": ("Fire", "화재 감지"),
    "smoke": ("Fire", "연기 감지"),
    "flood": ("Met", "침수 감지"),
    "person": ("Security", "사람 감지"),
    "vehicle": ("Security", "차량 감지"),
    "intrusion": ("Security", "침입 감지"),
    "sos": ("Rescue", "구조 요청"),
    # ★ 아래 셋은 **탐지가 아니라 설비의 상태**다(P-20 ③ · OPS-15).
    #   `Safety` 로 내면 받는 쪽이 재난으로 읽는다 — `Infra` 가 그 구별이다.
    "camera_down": ("Infra", "감시 카메라 무응답"),
    "camera_cluster_down": ("Infra", "감시 카메라 군집 두절"),
    "storage_high": ("Infra", "영상 저장 용량 임계"),
}

#: `DetectionEvent.Severity`(3값) → CAP `severity`(5값).
#: ★ **`Extreme` 를 쓰지 않는다.** 우리 등급은 셋뿐이고, 다섯 칸에 억지로 펴면
#:   재지 않은 구별을 낸 것이 된다. 위는 비워 두는 쪽이 정직하다(D-301).
SEVERITY_TO_CAP: dict[str, str] = {
    "critical": "Severe",
    "warning": "Moderate",
    "info": "Minor",
}

#: 우리 등급 → CAP `urgency`. **등급과 긴급도는 다른 축**이지만 우리는 긴급도를
#: 따로 재지 않는다. 그래서 등급에서 파생하고, **그 사실을 여기 적는다** —
#: 나중에 긴급도를 실제로 재게 되면 이 표가 사라지는 것이 옳다.
SEVERITY_TO_URGENCY: dict[str, str] = {
    "critical": "Immediate",
    "warning": "Expected",
    "info": "Unknown",
}

#: 사람의 판정(`verdict`) → CAP `certainty`.
#: `None`(아직 아무도 안 봤다)은 `Possible` 이다 — `Likely` 로 올리면 AI 한 벌의
#: 판단이 사람의 확인처럼 나간다.
VERDICT_TO_CERTAINTY: dict[str | None, str] = {
    "confirmed": "Observed",
    "rejected": "Unlikely",
    None: "Possible",
}

#: `scope` 가 `Restricted` 면 CAP 은 `restriction` 을 요구한다. 왜 `Private` 이
#: 아닌가: `Private` 은 `addresses` 를 요구하고, 거기 적을 것은 **구독의 수신 URL**
#: 이다. 그 URL 을 본문에 적으면 본문이 지나가는 모든 자리에 남는다.
DEFAULT_SCOPE = "Restricted"
DEFAULT_RESTRICTION = "F-05 구독으로 등록된 연계 기관에만 배포"

#: 우리가 모르는 값이 왔을 때. **조용히 버리지 않고 이 낱말로 낸다.**
UNKNOWN_CATEGORY = "Other"
UNKNOWN = "Unknown"


class CapMappingError(ValueError):
    """CAP 으로 옮길 수 없다. **빈 알림을 만들지 않는다** — 필수 요소가 빈
    `<alert>` 는 받는 쪽에서 파싱 오류가 되고, 그것은 우리 쪽 결함이다."""


def cap_time(value: datetime) -> str:
    """CAP 의 시각 표기 — `yyyy-MM-ddTHH:mm:ss±hh:mm`.

    ★ **`Z` 를 쓰지 않는다.** CAP 1.2 는 UTC 를 `Z` 로 적는 것을 허용하지 않고
      `+00:00` 형태의 오프셋을 요구한다. 파이썬 `isoformat()` 은 오프셋을 그렇게
      내지만, **naive 한 값이면 오프셋을 아예 안 낸다** — 그때 오프셋 없는 문자열이
      나가고 받는 쪽은 그것을 자기 지역시로 읽는다. 몇 시간이 조용히 어긋난다.
    """
    if value.tzinfo is None:
        raise CapMappingError(
            "시각에 시간대가 없다 — 오프셋 없는 CAP 시각은 받는 쪽이 자기 지역시로 "
            "읽는다. `django.utils.timezone` 이 붙인 값을 그대로 넘겨라")
    return value.replace(microsecond=0).isoformat()


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def category_for(event_type: str) -> tuple[str, str]:
    """유형 → (CAP category, `<event>` 한 줄). 모르면 `Other` 로 **낸다**.

    모르는 유형을 예외로 막지 않는 이유: 그러면 새 유형 하나가 **모든 구독의 발송을
    멈춘다.** 표준으로 내보내는 일이 우리 열거값의 인질이 되면 안 된다. 대신
    `Other` 로 나가고, 시험이 「표가 전수인가」를 따로 잰다.
    """
    known = EVENT_TYPE_TO_CAP.get(event_type)
    if known is not None:
        return known
    return (UNKNOWN_CATEGORY, "분류되지 않은 감지 (%s)" % (event_type or "미상"))


def to_cap_alert(
    event: Mapping[str, Any],
    *,
    sender: str,
    identifier: str,
    sent: datetime,
    status: str = "Actual",
    msg_type: str = "Alert",
    sender_name: str = "",
) -> dict[str, Any]:
    """이벤트 하나를 CAP 1.2 `<alert>` 한 벌로 옮긴다.

    `event` 는 **dict 다** — 모델도 `EventView` 도 받지 않는다. 이 번역기가 우리
    모델을 알면 모델이 바뀔 때 번역기가 깨지고, 그러면 표준으로 내보내는 의미가 없다.

    필수 여섯(alert) · 다섯(info) 을 **여기서 전부 채운다.** 부르는 쪽이 빠뜨릴 수
    있는 자리를 남기지 않는다.
    """
    if not sender or " " in sender or "," in sender:
        raise CapMappingError(
            "sender 가 비었거나 공백·쉼표를 담고 있다 — CAP 의 `sender` 는 공백을 "
            "허용하지 않는다. `settings.CAP_SENDER` 를 보라")
    if not identifier or " " in identifier or "," in identifier:
        raise CapMappingError("identifier 에 공백·쉼표를 넣을 수 없다 (CAP 1.2)")
    if status not in CAP_STATUS:
        raise CapMappingError("CAP status 어휘 밖이다: %r" % status)
    if msg_type not in CAP_MSG_TYPE:
        raise CapMappingError("CAP msgType 어휘 밖이다: %r" % msg_type)

    event_type = _text(event.get("event_type"))
    category, event_line = category_for(event_type)
    severity = SEVERITY_TO_CAP.get(_text(event.get("severity")), UNKNOWN)
    urgency = SEVERITY_TO_URGENCY.get(_text(event.get("severity")), UNKNOWN)
    verdict = event.get("verdict")
    certainty = VERDICT_TO_CERTAINTY.get(verdict if verdict else None, UNKNOWN)

    info: dict[str, Any] = {
        "language": "ko-KR",
        "category": [category],
        "event": event_line,
        "urgency": urgency,
        "severity": severity,
        "certainty": certainty,
        "senderName": sender_name or sender,
        "headline": event_line,
        "description": _describe(event, event_line),
        #: ★ `parameter` 는 CAP 이 **표준 밖 값을 담으라고 만든 자리**다.
        #:   우리 식별자를 `<info>` 본문에 흩뿌리지 않고 여기에만 둔다 —
        #:   받는 쪽은 표준 요소만 읽어도 알림을 이해할 수 있어야 한다.
        "parameter": [
            {"valueName": "GX-Event-Id", "value": _text(event.get("event_id"))},
            {"valueName": "GX-Event-Type", "value": event_type},
            {"valueName": "GX-Response-State",
             "value": _text(event.get("response_state"))},
        ],
    }
    area = _area(event)
    if area:
        info["area"] = [area]

    return {
        # ★ CAP 은 XML 이 정본이다. JSON 으로 낼 때도 **요소 이름을 그대로** 쓴다 —
        #   snake_case 로 바꾸면 그 순간 그것은 CAP 이 아니라 우리 스키마다.
        "identifier": identifier,
        "sender": sender,
        "sent": cap_time(sent),
        "status": status,
        "msgType": msg_type,
        "scope": DEFAULT_SCOPE,
        "restriction": DEFAULT_RESTRICTION,
        "info": [info],
    }


def _describe(event: Mapping[str, Any], event_line: str) -> str:
    """사람이 읽는 한 문단. **우리 대장의 말·내부 경로를 넣지 않는다**(UX-20 · SEC-17)."""
    parts = [event_line]
    where = _text(event.get("address")) or _text(event.get("stream_monitor_name"))
    if where:
        parts.append("위치: %s" % where)
    confidence = event.get("confidence")
    if confidence is not None:
        parts.append("AI 신뢰도 %.2f" % float(confidence))
    if not event.get("verdict"):
        parts.append("사람의 확인 전입니다.")
    return " / ".join(parts)


def _area(event: Mapping[str, Any]) -> dict[str, Any] | None:
    """CAP `<area>`. `areaDesc` 가 없으면 **area 자체를 내지 않는다** —
    CAP 은 area 가 있으면 areaDesc 를 필수로 요구한다. 빈 문자열로 채우면
    「위치를 모른다」가 「위치가 빈 문자열이다」가 된다."""
    desc = _text(event.get("address")) or _text(event.get("stream_monitor_name"))
    lat, lng = event.get("lat"), event.get("lng")
    if not desc and lat is None:
        return None
    area: dict[str, Any] = {"areaDesc": desc or "위치 미상"}
    if lat is not None and lng is not None:
        # CAP `circle` 은 `위도,경도 반경(km)`. 반경 0 은 **점**이다 —
        # 우리가 아는 것이 카메라 한 대의 좌표뿐이므로 넓히지 않는다.
        area["circle"] = ["%s,%s 0" % (lat, lng)]
    return area


def to_cap_xml(alert: Mapping[str, Any]) -> str:
    """같은 알림의 XML. **CAP 의 정본 표현은 XML 이다.**

    상급기관 연계는 대개 XML 을 요구한다. JSON 만 낼 수 있으면 「표준으로 낸다」가
    반만 참이 된다 — 그래서 두 형식을 같은 dict 하나에서 만든다(D-212: 두 벌로
    만들면 두 형식이 서로 다른 말을 하게 된다).
    """
    root = ET.Element("alert", {"xmlns": CAP_NAMESPACE})
    for key in ("identifier", "sender", "sent", "status", "msgType", "scope",
                "restriction"):
        value = alert.get(key)
        if value:
            ET.SubElement(root, key).text = str(value)
    for info in alert.get("info", ()):
        node = ET.SubElement(root, "info")
        for key in ("language",):
            if info.get(key):
                ET.SubElement(node, key).text = str(info[key])
        for value in info.get("category", ()):
            ET.SubElement(node, "category").text = str(value)
        for key in ("event", "urgency", "severity", "certainty", "senderName",
                    "headline", "description"):
            if info.get(key):
                ET.SubElement(node, key).text = str(info[key])
        for param in info.get("parameter", ()):
            pnode = ET.SubElement(node, "parameter")
            ET.SubElement(pnode, "valueName").text = str(param.get("valueName", ""))
            ET.SubElement(pnode, "value").text = str(param.get("value", ""))
        for area in info.get("area", ()):
            anode = ET.SubElement(node, "area")
            ET.SubElement(anode, "areaDesc").text = str(area.get("areaDesc", ""))
            for circle in area.get("circle", ()):
                ET.SubElement(anode, "circle").text = str(circle)
    return ET.tostring(root, encoding="unicode")


def render(alert: Mapping[str, Any], payload_format: str) -> tuple[bytes, str]:
    """구독이 고른 형식으로 **바이트와 그 MIME**. 서명은 이 바이트를 덮는다.

    바이트를 돌려주는 이유: 서명 대상은 **보내는 바로 그 바이트**여야 한다.
    문자열을 돌려주고 부르는 쪽이 다시 인코딩하면, 인코딩이 갈리는 날 서명이
    조용히 깨진다(그리고 그 실패는 상대 쪽에서만 보인다).
    """
    import json

    if payload_format == FORMAT_XML:
        return to_cap_xml(alert).encode("utf-8"), CONTENT_TYPES[FORMAT_XML]
    if payload_format != FORMAT_JSON:
        raise CapMappingError(
            "모르는 형식 %r — 아는 것은 %s" % (payload_format, ", ".join(sorted(SUPPORTED_FORMATS))))
    body = json.dumps(alert, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return body, CONTENT_TYPES[FORMAT_JSON]
