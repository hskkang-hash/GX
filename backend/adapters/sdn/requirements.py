# -*- coding: utf-8 -*-
"""SDN 명세 **수령 요건서 — 기계가 읽는 판**  (DA-02 §1·§2 그대로).

왜 문서를 코드로 한 번 더 적나 — 문서는 사람이 세고, 코드는 기계가 센다
------------------------------------------------------------------------
`docs/design/DA-02_SDN_API_매핑서_v0.1_수령요건.md` 가 정본이고, 이 파일은 그 §1·§2 표를
**같은 내용으로** 옮긴 것이다. 옮기는 이유는 하나다: 명세가 도착했을 때
"이제 만들 수 있는가"를 **사람의 기억이 아니라 함수**가 답하게 하기 위해서다.

    missing_blocking()          # A 등급 중 아직 안 받은 것. 비어야 착수 가능
    can_start("I-1")            # 그 인터페이스 하나를 만들 수 있는가

D-286 이 정한 모양 그대로다 — 「문서는 기억을 요구하고, 도구는 기억을 요구하지 않는다」.

무엇을 **적지 않았나** — 여기가 요점이다 (D-280)
------------------------------------------------
엔드포인트 경로·필드 이름·타입·오류 코드는 **한 줄도 없다.** 계약 [별첨1] §4 각주가
*"각 인터페이스의 엔드포인트·필드 정의는 갑이 제공하는 명세를 기준으로 확정한다"* 라고
못박았고, 추측한 필드 위에 어댑터를 만들면 재작업이 확정된다.

  이 파일에 있는 것은 **"무엇을 받아야 하는가"** 이고,
  없는 것은 **"받으면 무엇일 것 같은가"** 다. 후자를 적는 순간 이 파일이 명세인 척한다.

명세가 도착하면
---------------
① `docs/design/DA-02...md` 의 빈칸을 채워 매핑서 v1.0 으로 승격한다.
② 여기 `received=True` 와 근거(수령 문서·날짜)를 적는다.
③ `adapters/sdn/port.py` 의 구현체를 만든다. **그때 처음으로** 저쪽 필드 이름이 등장한다.
④ `KERNEL_READY` 를 True 로 올린다 → E2E-3 이 자동으로 의무가 된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

#: 계약 [별첨 1] §4 가 확정한 인터페이스 5종. **여기는 협의 대상이 아니다** — 계약 본문이다.
#: 방향·주요 데이터·대응 기능까지 계약이 적었고, 못 적은 것은 그 데이터의 **형식**뿐이다.
INTERFACES: dict[str, dict[str, str]] = {
    "I-1": {
        "title": "영상 QoS 우선 제어 요청",
        "direction": "GX → SDN",
        "contract_data": "카메라/드론 식별자, 소스·목적지, 우선순위, 대역폭, 유지 시간",
        "feature": "F-06",
        "note": "REST(JSON) · 결과 코드 수신",
    },
    "I-2": {
        "title": "경로 우회 요청",
        "direction": "GX → SDN",
        "contract_data": "스트림 식별자, 장애 링크, 대체 경로 정책",
        "feature": "F-07",
        "note": "",
    },
    "I-3": {
        "title": "링크·장비 상태 통보",
        "direction": "SDN → GX",
        "contract_data": "링크 ID, 상태(UP/DOWN/혼잡), 대역폭, 시각, 위치 매핑",
        "feature": "F-08",
        "note": "Webhook 또는 주기 폴링 — 계약이 '또는' 으로 열어 두었다",
    },
    "I-4": {
        "title": "제어 결과·감사 이력",
        "direction": "SDN → GX",
        "contract_data": "요청 ID, 처리 결과, 처리 시각",
        "feature": "F-09 표시 · F-11 보고서 반영",
        "note": "",
    },
    "I-5": {
        "title": "인증",
        "direction": "양방향",
        "contract_data": "API Key 또는 OAuth2 토큰, TLS 1.2 이상",
        "feature": "전 인터페이스",
        "note": "키는 코드 외부(비밀저장소) 보관 — D-204",
    },
}

Grade = Literal["A", "B", "C"]


@dataclass(frozen=True)
class Requirement:
    """받아야 할 것 한 줄.

    `grade`
        A = **차단.** 이것이 비면 그 인터페이스는 **Mock 조차** 만들 수 없다.
        B = 설계 제약. 없어도 만들 수는 있으나 나중에 장애로 돌아온다.
        C = 있으면 좋음.

    `blocks`
        없으면 **무엇이 막히는가.** 등급만 적으면 다음 사람이 "왜 A 인가"를 다시 묻는다.

    `received`
        받았는가. **전부 False 다** — 2026-08-25 기한이 지났고 아직 미수령이다.
        받은 것을 True 로 바꿀 때는 `source` 에 **근거(문서명·날짜)** 를 함께 적는다.
    """

    key: str
    interface: str
    what: str
    grade: Grade
    blocks: str
    received: bool = False
    source: str = ""


#: DA-02 §2 전체. 순서·문구를 문서와 맞춘다 — 두 곳이 다른 말을 하면 어느 쪽도 못 믿는다.
REQUIREMENTS: tuple[Requirement, ...] = (
    # ── §2-1 공통 ────────────────────────────────────────────────────────
    Requirement("C-1", "공통", "Base URL (시험환경 / 운영환경 각각)", "A",
                "호출 대상이 없다"),
    Requirement("C-2", "공통", "인증 방식 확정 — API Key 인가 OAuth2 인가", "A",
                "어댑터의 인증 계층 설계가 갈린다. 둘은 갱신·만료 처리가 전혀 다르다"),
    Requirement("C-3", "공통", "토큰/키의 유효기간·갱신 절차", "A",
                "만료 처리를 못 쓴다. 새벽에 조용히 죽는 연동이 된다"),
    Requirement("C-4", "공통", "오류 응답 형식 — HTTP 상태 코드 사용 여부 + 오류 바디 스키마", "A",
                "상대가 200 으로 실패를 돌려주는 API 라면 우리 쪽에 판정 계층이 하나 더 "
                "필요하고, 그건 견적 항목이다 (W0-18 이 겪은 그 모양)"),
    Requirement("C-5", "공통", "타임아웃 권장값 및 서버측 최대 처리 시간", "B",
                "값을 정할 근거가 없다. 임의값은 나중에 장애로 돌아온다"),
    Requirement("C-6", "공통", "재시도 허용 여부 — 멱등성", "B",
                "재시도가 이중 제어를 일으키면 네트워크를 두 번 흔든다"),
    Requirement("C-7", "공통", "호출 빈도 제한(rate limit)", "B",
                "이벤트 폭주 시 우리가 SDN 을 때린다"),
    Requirement("C-8", "공통", "TLS 인증서 — 사설 CA 인가 공인 CA 인가", "B",
                "사설 CA 면 신뢰 저장소 배포 절차가 추가된다"),
    Requirement("C-9", "공통", "OpenAPI/Swagger 문서 파일", "C",
                "있으면 매핑 작업이 며칠 줄어든다"),
    # ── §2-2 I-1 ─────────────────────────────────────────────────────────
    Requirement("1-1", "I-1", "엔드포인트 경로 · HTTP 메서드", "A", "호출 불가"),
    Requirement("1-2", "I-1", "'카메라/드론 식별자' 의 실제 형식 (IP? 포트? 장비 ID?)", "A",
                "★ 최대 위험. StreamMonitor.id 와 SDN 식별자가 다르면 **둘을 잇는 매핑 "
                "테이블이 신규 개발 항목**이 된다. 그 항목은 지금 견적에 없다"),
    Requirement("1-3", "I-1", "우선순위 값의 범위와 의미 (1이 높은가 낮은가)", "A",
                "반대로 걸면 재난 시 영상을 **낮추는** 요청이 된다"),
    Requirement("1-4", "I-1", "대역폭 단위(Mbps? Kbps?)와 허용 범위", "A",
                "단위 오해는 3자리 오차다"),
    Requirement("1-5", "I-1", "'유지 시간' 만료 시 자동 원복인가 해제 요청이 따로인가", "A",
                "원복이 없으면 우선순위가 영구히 남아 평시 트래픽을 왜곡한다. "
                "해제 API 가 별도면 **인터페이스가 6개**다"),
    Requirement("1-6", "I-1", "결과 코드 목록과 각 코드의 의미", "A",
                "F-06 AC 가 '결과 코드 기록' 이다. 코드표 없이는 기록이 무의미하다"),
    Requirement("1-7", "I-1", "동시 다발 요청 처리 — 같은 링크에 QoS 요청이 겹치면", "B",
                "재난은 동시다발이다. 겹침이 기본 상황이다"),
    # ── §2-3 I-2 ─────────────────────────────────────────────────────────
    Requirement("2-1", "I-2", "엔드포인트 · 메서드", "A", "호출 불가"),
    Requirement("2-2", "I-2", "'스트림 식별자' 가 I-1 의 식별자와 같은 체계인가", "A",
                "다르면 매핑 테이블이 하나 더 필요하다"),
    Requirement("2-3", "I-2", "'대체 경로 정책' 의 표현식 — 이름인가 경로 명세인가 자동 선택인가", "A",
                "우리가 경로를 골라야 하면 GuardianX 가 망 토폴로지를 알아야 한다. "
                "**그것은 계약 범위 밖이다** — 반드시 확인"),
    Requirement("2-4", "I-2", "전환 완료를 어떻게 아는가 — 동기 응답인가 I-4 통보인가", "A",
                "F-07 AC 가 '전환 확인' 이다. 확인 경로가 계약에 명시돼 있지 않다"),
    Requirement("2-5", "I-2", "전환 실패 시 원 경로 유지가 보장되는가", "B",
                "실패가 단절로 이어지면 우리 요청이 장애 원인이 된다"),
    # ── §2-4 I-3 ─────────────────────────────────────────────────────────
    Requirement("3-1", "I-3", "Webhook 인가 폴링인가", "A",
                "설계가 통째로 갈린다. Webhook 이면 **우리가 수신 엔드포인트를 공개**해야 "
                "하고 그 인증·방화벽이 새 과제다"),
    Requirement("3-2", "I-3", "(Webhook) 재전송 정책 · 서명 검증 방식", "A",
                "유실·위조를 못 막는다"),
    Requirement("3-3", "I-3", "(폴링) 권장 주기와 변경분만 받는 방법", "A",
                "전량 폴링은 60초 AC 를 못 지키거나 SDN 을 때린다"),
    Requirement("3-4", "I-3", "'위치 매핑' 을 누가 관리하는가 — 링크 ID ↔ 지리 좌표", "A",
                "★ 두 번째 최대 위험. SDN 이 좌표를 주지 않으면 우리가 대응표를 관리해야 "
                "하고, 그것은 **운영 데이터 관리 화면 신규**다. F-09 지도와 F-13 정찰이 여기 걸린다"),
    Requirement("3-5", "I-3", "상태값 열거 — UP/DOWN 외 '혼잡' 의 판정 기준", "A",
                "'혼잡' 을 재난 징후로 쓸지 말지가 갈린다"),
    Requirement("3-6", "I-3", "'지정 지역' 을 어떻게 표현하는가 (링크 묶음? 행정구역?)", "A",
                "F-08 은 '지정 지역 통신 두절' 을 만든다. 지역 정의가 없으면 이벤트를 만들 수 없다"),
    # ── §2-5 I-4 ─────────────────────────────────────────────────────────
    Requirement("4-1", "I-4", "요청 ID 를 누가 만드는가 — GX 인가 SDN 이 발급하는가", "A",
                "요청과 결과를 못 잇는다. 감사로그가 반쪽이 되고 F-11 의 '조치 이력' 이 빈다"),
    Requirement("4-2", "I-4", "결과 통보 방식 — Push 인가 polling 인가", "A",
                "I-3 과 같은 갈림"),
    Requirement("4-3", "I-4", "보관 기간 · 과거 이력 조회 가능 여부", "B",
                "보고서가 사후에 조치 이력을 못 넣으면 F-11 이 반쪽이다"),
    Requirement("4-4", "I-4", "처리 시각의 시간대·형식 (UTC? KST? ISO8601?)", "A",
                "30초·60초 AC 를 시간대 어긋난 값으로 재면 판정이 뒤집힌다"),
    # ── §2-6 I-5 ─────────────────────────────────────────────────────────
    Requirement("5-1", "I-5", "시험환경 자격증명 발급 절차", "A", "연동 시험 불가"),
    Requirement("5-2", "I-5", "자격증명 회전 주기·절차", "B", "만료 시 운영 중단"),
    Requirement("5-3", "I-5", "권한 범위(scope) — 조회만/제어까지 구분되는가", "B",
                "최소권한 원칙 적용 불가"),
)


def missing_blocking(interface: str | None = None) -> tuple[Requirement, ...]:
    """아직 못 받은 **A 등급**. 비면 착수 가능, 아니면 착수 불가.

    `interface` 를 주면 그 인터페이스와 공통(`공통`)만 본다 — I-1 만 받아도 F-06 은
    시작할 수 있어야 하고, 전부 받을 때까지 기다리면 부분 수령의 값이 사라진다.
    """
    return tuple(
        r for r in REQUIREMENTS
        if r.grade == "A" and not r.received
        and (interface is None or r.interface in (interface, "공통"))
    )


def can_start(interface: str) -> bool:
    """그 인터페이스의 어댑터를 **만들 수 있는가.** 사람의 판단이 아니라 목록이 답한다."""
    if interface not in INTERFACES:
        raise KeyError(f"{interface!r} 는 계약 [별첨1] §4 의 인터페이스가 아니다. "
                       f"있는 것: {', '.join(INTERFACES)}")
    return not missing_blocking(interface)


def summary() -> str:
    """보고에 그대로 쓰는 한 문단. **모수를 함께 적는다** (D-271)."""
    total = len(REQUIREMENTS)
    blocking = [r for r in REQUIREMENTS if r.grade == "A"]
    got = [r for r in REQUIREMENTS if r.received]
    lines = [
        f"[SDN] 수령 요건 {total}건 (A 차단 {len(blocking)} · 수령 {len(got)})",
    ]
    for code in INTERFACES:
        miss = missing_blocking(code)
        state = "착수 가능" if not miss else f"착수 불가 — A 미수령 {len(miss)}건"
        lines.append(f"  {code} {INTERFACES[code]['title']:<20} {state}")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - 손으로 확인할 때만
    print(summary())
