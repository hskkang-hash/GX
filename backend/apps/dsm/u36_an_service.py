# -*- coding: utf-8 -*-
"""DSM-U3-01(역할별 M2 문안) · U3-02(통제 실행 회신) · U6-01(외부 이벤트 연계) ·
U6-03(사회적약자 요청 → 객체 검색 사건) — 명세 §3.3·§3.6 원문이 정본
(`docs/design/DSM_재난안전관리App_명세서_v1.1_지침기반_20260915.md` 90·91·123·125행).

턴 AO · WO-18 · 차선 N4 단독 소유 파일.

★ U3-02(통제 실행 회신)은 이 파일에 로직이 없다 — `apps/dsm/control_board_service.py`
  (턴 AM·N4 가 지었고 턴 AN·N1 이 「일일보고 반영」을 더한 그 파일)의 `advance()`
  가 이미 「도달→결정→실행→해제」 4단계 순서를 전부 판정한다(`u4_regulations.
  CONTROL_STAGE_ORDER`). U3-02 의 완결조건("도달→결정→실행 3시각")은 그 함수를
  `stage="실행"` 으로 부르는 것과 같은 일이다 — **두 번째 판정식을 짓지 않는다**
  (D-212). `api_u36_an.py` 가 `control_board_service.advance` 를 새 리터럴
  `/controls/{id}/executed` 로 직접 연다.

★ U6-01·U6-03 — **F-05 잠금을 지킨다.** `kernels.k1_event` 를 이 파일이 직접
  import 하면 `tests/test_f05_event_api.py::EntrySurfaceIsOneTest` 가 즉시 빨개진다
  (K1 을 소비하는 App 이 `apps/dsm/services.py` 하나뿐이어야 한다). 그래서 사건
  생성은 `apps.dsm.services.record_external_event()`(이 턴에 그 파일에 새로 더한
  얇은 래퍼 하나) 를 거친다 — 두 번째 진입면을 열지 않는다.

★ 「외부」 표식 — `DetectionEvent` 에는 `data_source` 칸이 **없다**
  (`apps/dsm/services.py::event_data_source` 머리말 — 칸이 아니라 창/행 판정이다).
  probe(`data_source=probe`)·drill(`data_source=drill`) 은 `common/probe_marker.py`
  가 `track_id` 위에 얹는 표식이고, 이 파일은 **같은 자리, 새 낱말**(`data_source=
  external`)을 쓴다 — `probe_marker.py`(공용 L1)는 고치지 않는다(그 파일을 고치면
  probe/drill 판정식과 한 커밋에서 갈릴 위험이 생긴다, D-212). 세종 판정이 이
  낱말을 못박았다 — 「세종 판정: … data_source=external」.

★ U6-01 인증 — 들어오는 키(범위 `events:ingest` · `inbound_key=True` · D-335 래칫 예외 1 ·
  P-427) + 본문 HMAC. **서명 비밀은 그 기관의 들어오는 키 자체다**(P-432 · 턴 AQ) —
  우리가 남을 부를 때의 웹훅 서명키 `agency` 를 재사용하던 P-427 모양은 방향이 반대라
  걷어냈다(턴 AP N4 반론). 이 서비스는 키 값을 모른다: HTTP 층이
  `common.inbound_api_key.verify_signed_with_request_key` 를 `verify_signature` 로 넘긴다.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from common.tenant_scope import TenantScope

from apps.dsm.u5_an_service import SERVICE_FIRE_119, SERVICE_POLICE_112, SERVICE_SMART_CITY

LOGGER_NAME_SEARCH = "guardianx.u6.search_request"

# ═══════════════════════════════════════════════════════════════════════════
# DSM-U3-01 — 역할별 M2 문안 (역할 × 유형 문안 표 · 「문안 사전 일치」)
# ═══════════════════════════════════════════════════════════════════════════
#: 명세 예시 그대로: "상주 경찰관/119/시설/당직에 따라 「지금 할 일」 한 줄이
#: 다르다(예: 시설 담당 「도로 통제 후 회신」)". 값은 **역할 코드**(API 계약) —
#: 화면에 내는 한글은 `ROLE_LABELS` 가 따로 쥔다(셋째 조건: 화면은 한국어 · 코드는
#: 화면에 내지 않는다).
ROLE_POLICE = "police"      # 상주 경찰관
ROLE_119 = "119"
ROLE_FACILITY = "facility"  # 시설
ROLE_DUTY = "duty"          # 당직

ROLES: tuple[str, ...] = (ROLE_POLICE, ROLE_119, ROLE_FACILITY, ROLE_DUTY)

ROLE_LABELS: dict[str, str] = {
    ROLE_POLICE: "상주 경찰관", ROLE_119: "119", ROLE_FACILITY: "시설", ROLE_DUTY: "당직",
}

#: **역할 × 유형 문안 표** — 완결조건이 부르는 그 표. 값은 DetectionEvent.EventType
#: 열거값(`stream_monitors.models.StreamMonitor.EventType`)의 코드를 그대로 쓴다
#: (새 열거값을 만들지 않는다 — DA-01 OPEN-05, 이 턴은 "새 표 0"이 배정 조건이다).
M2_PHRASE_TABLE: dict[tuple[str, str], str] = {
    (ROLE_POLICE, "intrusion"): "현장 확인 후 112 공조 요청",
    (ROLE_POLICE, "sos"): "현장 확인 후 구조 지원",
    (ROLE_POLICE, "fire"): "대피 유도 후 상황실 보고",
    (ROLE_POLICE, "flood"): "통제 협조 후 상황실 보고",
    (ROLE_119, "fire"): "즉시 출동 · 진화 개시",
    (ROLE_119, "smoke"): "화재 여부 확인 후 출동",
    (ROLE_119, "sos"): "즉시 출동 · 구급 개시",
    (ROLE_119, "flood"): "인명 구조 대기 · 출동 판단",
    #: ★ 명세 원문의 예시 그 자체 — 시험이 이 한 줄을 이름으로 대조한다.
    (ROLE_FACILITY, "flood"): "도로 통제 후 회신",
    (ROLE_FACILITY, "fire"): "소방 설비 가동 확인 후 회신",
    (ROLE_FACILITY, "intrusion"): "출입 통제 확인 후 회신",
    (ROLE_FACILITY, "sos"): "현장 안전 확보 후 회신",
    (ROLE_DUTY, "fire"): "비상연락망 가동 후 상황 전파",
    (ROLE_DUTY, "flood"): "통제 현황판 갱신 후 상황 전파",
    (ROLE_DUTY, "intrusion"): "상황실 보고 후 지시 대기",
    (ROLE_DUTY, "sos"): "상황실 보고 후 지시 대기",
}

#: 표에 없는 (역할, 유형) 조합의 자리 — **빈 문자열을 돌려주지 않는다**(D-284, 없는
#: 것과 비어 있는 것은 다르다). 역할마다 한 줄은 반드시 있다.
M2_DEFAULT_TEXT: dict[str, str] = {
    ROLE_POLICE: "현장 확인 후 상황실 보고",
    ROLE_119: "출동 여부 확인 후 회신",
    ROLE_FACILITY: "현장 점검 후 회신",
    ROLE_DUTY: "상황실 보고 후 지시 대기",
}


class M2RoleUnknown(ValueError):
    """role 이 계약에 없다 — 422 로 번역된다."""


def m2_brief(*, scope: TenantScope, event_id: int, role: str) -> dict[str, Any]:
    """`GET /events/{id}/m2-brief` — **M2 상단 한 줄**.

    문지기는 `apps.dsm.services.event_detail`(F-05 잠금을 그대로 따른다 — 이
    함수가 새 조회 경로를 짓지 않는다)이 진다: 남의 테넌트 이벤트면 거기서
    404 가 난다.

    Raises:
        M2RoleUnknown: role 이 `ROLES` 밖이다.
    """
    if role not in ROLES:
        raise M2RoleUnknown(f"role={role!r} 은 계약에 없다. 허용: {ROLES}")

    from apps.dsm import services

    event = services.event_detail(scope=scope, event_id=event_id)
    text = M2_PHRASE_TABLE.get((role, event.event_type), M2_DEFAULT_TEXT[role])
    return {
        "event_id": event_id,
        "role": role,
        "role_label": ROLE_LABELS[role],
        "event_type": event.event_type,
        "text": text,
    }


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U6-01 · U6-03 — 「외부」 표식 (track_id 위에 얹는다, 새 칸 0)
# ═══════════════════════════════════════════════════════════════════════════
#: 세종 판정 그대로: `data_source=external`. `common/probe_marker.py` 의
#: `PROBE_MARKER`·`DRILL_MARKER` 와 **같은 자리**(track_id), **다른 낱말**이다.
EXTERNAL_MARKER = "data_source=external"

#: `DetectionEvent.track_id` 의 상한 — `common/probe_marker.py::TRACK_ID_MAX`
#: 와 같은 수(64). 공용 파일을 다시 열지 않으려고 **같은 값을 여기 한 번 더**
#: 적는다(정의가 아니라 상수 — 값이 갈리면 어느 한쪽 DB 마이그레이션 없이는
#: 절대 조용히 못 갈린다, 둘 다 모델의 `max_length=64` 를 그대로 읽는 값이다).
TRACK_ID_MAX = 64


def is_external_track(track_id) -> bool:
    """이 행이 **외부에서 들어온 것인가** — `is_probe_track`·`is_drill_track` 과
    같은 규약(`common/probe_marker.py`): 앞에서만 센다, `None`/빈 문자열은 아니다.
    """
    return bool(track_id) and str(track_id).startswith(EXTERNAL_MARKER)


def _external_track_id(*, source: str, ref: str = "") -> str:
    s = f"{EXTERNAL_MARKER};source={source}" + (f";ref={ref}" if ref else "")
    if len(s) > TRACK_ID_MAX:
        s = s[:TRACK_ID_MAX]
    return s


def _parse_when(when: str | None):
    """`control_board_service._parse_when` 과 같은 규약 — 두 번째 판정식을 짓지
    않으려 했으나 그 함수는 `apps/dsm/control_board_service.py`(차선 경계 밖
    파일)의 사유이고, 여기는 독립된 조각이라 **같은 세 줄**을 다시 쓴다(공용
    유틸로 옮기는 것은 이 턴의 범위 밖 — D-212 의 정신은 "판정식을 두 벌 짓지
    말라"이지 "세 줄짜리 파싱을 공유하라"가 아니다)."""
    if not when:
        return timezone.now()
    parsed = parse_datetime(when)
    if parsed is None:
        raise ValueError(f"시각을 읽을 수 없습니다: {when!r}")
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


class ExternalEventRejected(Exception):
    """서명 검증 실패 — 401 로 번역된다. 사유 문자열에 서명 값을 담지 않는다."""


class ExternalEventInvalid(Exception):
    """입력이 계약과 안 맞는다(모르는 source · 본문이 JSON 이 아니다 등) — 422."""


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U6-01 — 스마트시티 통합플랫폼 이벤트 연계 (112 긴급영상 · 119 출동 · 재난상황
# 긴급대응 · CAP 1.2 프로파일). **F-05 읽기 문(`GET /events`)의 짝인 쓰기 하나.**
# ═══════════════════════════════════════════════════════════════════════════
#: 이 셋만 받는다(U5-03 「연계 설정」이 이미 등록한 서비스 이름과 **같은 코드**를
#: 재사용한다 — `apps.dsm.u5_an_service.SERVICES` 중 NDMS 는 뺐다. NDMS 는
#: U6-02(별표 · 이 턴 범위 밖)의 **내보내기** 대상이지 우리에게 이벤트를 들여보내는
#: 쪽이 아니다).
EXTERNAL_EVENT_SOURCES: tuple[str, ...] = (
    SERVICE_SMART_CITY, SERVICE_POLICE_112, SERVICE_FIRE_119,
)


#: [P-432] 서명 비밀 = **그 기관의 들어오는 키**(범위 `events:ingest`). 우리가 남을 부를 때의
#: 웹훅 서명키(`agency`) 재사용(P-427)은 방향이 반대라 폐지했다 · 새 자격 체계 0.
#: 서비스는 키 값을 모른다 — HTTP 층이 `verify_signature` 로 검증만 넘긴다(값 전달 0).
SignatureVerifier = Callable[[bytes, Mapping[str, str]], "tuple[bool, str]"]


def intake_external_event(
    *, scope: TenantScope, headers: Mapping[str, str], raw_body: bytes,
    verify_signature: SignatureVerifier,
) -> dict[str, Any]:
    """`POST /external-events` — DSM-U6-01.

    서명(`common/webhook_contract.verify` 그대로 재사용 — 판정식을 다시 짓지
    않는다 · `X-GX-Schema`·`X-GX-Timestamp`·`X-GX-Signature`)이 위조를 막고,
    `scope`(JWT 가 정한 테넌트)가 어느 테넌트로 적립할지를 정한다.

    본문(JSON, CAP 1.2 발신 쪽 모양):
        source               "smart_city" | "police_112" | "fire_119"
        event_type           기존 EventType 열거값 그대로(새 값 신설 없음)
        severity              기존 Severity 열거값 그대로
        stream_monitor_id     사건 + 카메라 스트림 URL(명세 원문) — **그 카메라가
                              이 요청의 테넌트 것이어야** 한다(record_detection 의
                              기존 IDOR 문지기가 그대로 선다)
        occurred_at            선택, ISO 8601
        lat · lng              선택
        external_ref            선택, 상대측 사건 식별자 — track_id 표식에 실린다

    Raises:
        ExternalEventInvalid: 본문이 JSON 이 아니다 · source 가 셋 밖이다 ·
            stream_monitor_id 가 없다.
        ExternalEventRejected: 서명 검증 실패(스키마·타임스탬프·서명 불일치 등).
        apps.dsm.services.InvalidEventInput: event_type·severity 가 계약 밖이다 ·
            그 stream_monitor_id 가 없다.
    """
    try:
        body = json.loads((raw_body or b"{}").decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ExternalEventInvalid(f"본문이 JSON 이 아닙니다 — {exc}") from exc
    if not isinstance(body, dict):
        raise ExternalEventInvalid("본문은 JSON 객체여야 합니다.")

    source = str(body.get("source") or "").strip()
    if source not in EXTERNAL_EVENT_SOURCES:
        raise ExternalEventInvalid(
            f"source={source!r} 는 연계 대상이 아닙니다. 허용: {EXTERNAL_EVENT_SOURCES}")

    ok, reason = verify_signature(raw_body, headers)
    if not ok:
        raise ExternalEventRejected(f"서명 검증 실패 — {reason}")

    stream_monitor_id = body.get("stream_monitor_id")
    if not isinstance(stream_monitor_id, int):
        raise ExternalEventInvalid("stream_monitor_id(정수)가 있어야 합니다.")
    event_type = str(body.get("event_type") or "").strip()
    severity = str(body.get("severity") or "warning").strip()
    external_ref = str(body.get("external_ref") or "").strip()

    try:
        occurred_at = _parse_when(body.get("occurred_at"))
    except ValueError as exc:
        raise ExternalEventInvalid(str(exc)) from exc

    from apps.dsm import services

    result = services.record_external_event(
        scope=scope, stream_monitor_id=stream_monitor_id, event_type=event_type,
        severity=severity, occurred_at=occurred_at,
        lat=body.get("lat"), lng=body.get("lng"),
        track_id=_external_track_id(source=source, ref=external_ref))
    return {
        **result, "source": source, "data_source": "external",
        "external_ref": external_ref,
    }


# ═══════════════════════════════════════════════════════════════════════════
# DSM-U6-03 — 사회적약자(실종) 요청 수신 → 객체 검색 사건 생성
# ═══════════════════════════════════════════════════════════════════════════
#: ★ **범위를 좁힌다.** 「객체 검색」(용모 기반 재식별) 판별 모델은 이 저장소 어디에도
#:   없다(턴 AN `N1_promotions.md`§U6-03 실측 — grep "객체 검색"·`object_search`·
#:   재식별 0건. AI 모델 연동은 L 규모 · 대표 승인이 필요한 별도 사업). 그것을
#:   지어내지 않는다(D-284). 이 함수가 닫는 것은 완결조건이 말 그대로 요구하는
#:   **"요청 → 사건 1"** 뿐이다 — 요청을 받아 **사람이 눈으로 찾는 수색**의 출발점이
#:   되는 사건 하나를 K1 경로로 남긴다(우리 제품은 CCTV 통합관제이지 재식별 엔진이
#:   아니다 — 관제요원이 카메라로 찾는다). 감사 한 줄(LAW-05 범위 — 사회적약자 개인
#:   정보가 실린 요청의 접수를 **누가·언제** 남겼는지)을 더해 "재식별 검색"이라는
#:   이름이 지어낸 능력을 약속하지 않으면서도 요청의 흔적을 남긴다.
SEARCH_EVENT_TYPE = "person"
SEARCH_SOURCE_TAG = "missing_person_search"


class SearchRequestInvalid(ValueError):
    """입력이 비었다 — 422."""


def intake_search_request(
    *, scope: TenantScope, requester_agency: str, subject_description: str,
    last_seen_stream_monitor_id: int, last_seen_at: str | None = None,
    contact: str = "",
) -> dict[str, Any]:
    """`POST /search-requests` — DSM-U6-03.

    Raises:
        SearchRequestInvalid: `requester_agency`·`subject_description` 이 비었다.
        apps.dsm.services.InvalidEventInput: `last_seen_stream_monitor_id` 가 없다.
    """
    requester_agency = (requester_agency or "").strip()
    subject_description = (subject_description or "").strip()
    if not requester_agency:
        raise SearchRequestInvalid("requester_agency(요청 기관)가 비어 있습니다.")
    if not subject_description:
        raise SearchRequestInvalid("subject_description(인상착의 등)이 비어 있습니다.")

    when = _parse_when(last_seen_at)

    from apps.dsm import audit, services
    from common import audit_writer

    result = services.record_external_event(
        scope=scope, stream_monitor_id=last_seen_stream_monitor_id,
        event_type=SEARCH_EVENT_TYPE, severity="critical", occurred_at=when,
        lat=None, lng=None,
        track_id=_external_track_id(source=SEARCH_SOURCE_TAG))

    #: LAW-05 범위 안 — **감사 줄 1.** 사회적약자 개인정보(인상착의 등)가 실린
    #: 요청의 접수를 감사에 남긴다. 본문 전체가 아니라 **요청 기관 · 사건 id**만
    #: 남긴다(인상착의 원문은 사건 자체가 아니라 이 감사에도 싣지 않는다 — 화면
    #: 밖 감사 표에까지 개인정보 원문을 복제하지 않는다).
    #: ★ `api_name` 을 따로 주지 않는다 — `audit_writer.write()` 는 `api_name=
    #:   api_name or action` 으로 저장하고, `audit_writer.read(action=...)` 는
    #:   그 `api_name` 칸으로 되묻는다(`common/audit_writer.py::read` — 이름은
    #:   `action` 이지만 실제로 대조하는 칸은 `api_name`이다). 여기서 다른
    #:   `api_name` 을 주면 `action="search_request_received"` 로 되읽는 질의가
    #:   0건이 된다(실측 — 시험이 그 자리에서 잡았다).
    audit.record_event_action(
        scope=scope, action="search_request_received",
        outcome=audit_writer.ALLOWED,
        reason=f"요청기관={requester_agency} · event_id={result['event_id']} · "
               f"연락처={'(있음)' if contact else '(미기재)'}",
        api_method="POST", status_http=200,
    )
    return {
        **result, "requester_agency": requester_agency,
        "data_source": "external",
    }
