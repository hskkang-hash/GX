# -*- coding: utf-8 -*-
"""E2E 3시나리오의 **등재부와 공통 규약** (D-291).

여기가 정본이다. 시나리오 이름·단계표·해금 조건·공통 규약이 전부 이 파일 하나에 있고,
`test_e2e_contract.py` 와 `scripts/verify_e2e_contract.py` 가 이것을 판정한다.

왜 등재부를 따로 두나 — 시나리오가 조용히 사라지는 것을 막는다
--------------------------------------------------------------
E2E 는 무겁다. 무거운 시험은 "일단 빼자"가 되고, 빠진 시험은 **초록 안에서 보이지 않는다.**
그래서 이름을 여기 박고, 파일이 없으면 **해금 조건이 충족된 순간 실패**하게 한다.
수(개수)가 아니라 **이름 집합**으로 잠근다 — D-285 (2) 가 정한 방식이다.
개수로 잠그면 시나리오 하나가 지워질 때 새 시나리오가 들어올 자리가 생긴다.

해금은 선언이 아니라 **실측**이다
--------------------------------
"K2 가 done 이다"를 사람이 적으면 그것은 다시 문서다(D-286). 이 파일은 커널 패키지가
**실제로 import 되는가**로 해금을 판정한다. 티켓 status 를 읽지 않는다 —
status 는 사람이 쓰고, import 는 코드가 답한다.

공통 규약 ①~⑥ (D-291)
----------------------
  ① 실 마이그레이션 DB 에서 돈다 — `--nomigrations` 금지
  ② 격리 단언 포함 — 읽기·쓰기 **양방향** (D-290)
  ③ 양성 대조 포함 — 표본 최소 1건은 실물 (D-289)
  ④ 저하 변형 포함 — 외부 의존을 죽여도 핵심 경로 200
  ⑤ 시간 단언은 **논리 시계**로 — 실시간 sleep 금지
  ⑥ 증거를 `evidence/e2e/<시나리오>/` 에 남기고, 실패 시 **어느 단계에서 끊겼는지 표로**

★ ①~⑤ 는 시험 **메서드 이름**으로 잠근다. 규약을 지켰다고 주석에 적는 것과,
  그 이름의 시험이 실제로 도는 것은 다르다 — 후자만 깨지면 멈춘다.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path

#: 저장소 뿌리 (backend/tests/e2e/ → 3단계 위)
ROOT = Path(__file__).resolve().parents[3]

#: 증거가 쌓이는 곳 (규약 ⑥)
EVIDENCE_ROOT = ROOT / "docs" / "agent" / "evidence" / "e2e"


# ═══════════════════════════════════════════════════════════════════════════
# 해금 — 커널이 실제로 있는가
# ═══════════════════════════════════════════════════════════════════════════
#: 커널 코드 → 그 커널의 **공개 면 패키지**. import 되면 그 커널은 존재한다.
#: DA-04 §1-4 가 정한 대로 App 은 이 이름만 만진다 — 여기서도 모델을 보지 않는다.
KERNEL_PACKAGES: dict[str, str] = {
    "K1": "kernels.k1_event",
    "K2": "kernels.k2_notify",
    "K3": "kernels.k3_dashboard",
    "K4": "kernels.k4_report",
    "K6": "kernels.k6_feedback",
    # SDN 어댑터는 커널이 아니라 L2 어댑터다. 이름을 함께 두는 이유는
    # E2E-3 의 해금 조건이 그것이기 때문이다 (D-291 증분 규칙).
    #
    # ★ 이 패키지는 **2026-08-31 에 실재하게 됐다** — 그러나 `KERNEL_READY = False` 다.
    #   포트·수령 요건·오류 계약만 세웠고 어댑터 구현은 없다(명세 미수령 · D-297).
    #   그래서 `kernel_present("SDN")` 은 여전히 False 이고 E2E-3 은 잠겨 있다.
    #   사유는 `adapters.sdn.NOT_READY_REASON` 에 있고, 비면 게이트가 멈춘다.
    "SDN": "adapters.sdn",
    # ★ ZONE 은 커널이 아니라 **L3 Platform 의 판정 서비스**다. 이름을 여기 두는 이유는
    #   E2E-2 3단계의 해금 조건이 그것이기 때문이다 (SDN 과 같은 계열의 등재).
    #
    #   2026-09-01 · D-299 로 **잠금이 풀렸다.** 이 이름을 아래 LOCKED_CAPABILITIES 에서
    #   지우고 여기 넣은 것이 곧 "이제 잴 수 있다"는 선언이고, 그 선언의 근거는
    #   `Zone` 모델(마이그 0019)과 `stream_monitors.services.zones` 다.
    #   그 모듈의 `KERNEL_READY` 는 True 이므로 3단계가 돈다 — 다만 **폴리곤은 여전히
    #   잠겨 있다**(`ZONE_POLYGON_READY=False`). 두 잠금이 다른 것을 잠근다:
    #   여기 것은 "구역 판정을 잴 수 있는가", 저기 것은 "폴리곤으로 잴 수 있는가".
    "ZONE": "stream_monitors.services.zones",
}


#: ★ 커널이 아닌 **잠긴 능력**. 단계가 이 이름을 가리키면 영영 열리지 않는다 —
#: 여는 사람이 여기서 이름을 지우고 `KERNEL_PACKAGES` 에 넣는 순간이 곧
#: **"이제 잴 수 있다"는 선언**이다.
#:
#: 왜 이 등재부가 필요한가 — D-264(모르면 멈춘다)의 E2E 판
#: -------------------------------------------------------
#: 계약 시나리오에는 **지금 기술로 잴 수 없는 단계**가 섞여 있다. 그것을 단계에서 빼면
#: 시나리오가 짧아진 채로 초록이 되고(빠진 줄은 보이지 않는다), 그렇다고 커널 이름을 붙이면
#: 커널이 붙는 순간 **못 재는 것을 재라고** 요구하게 된다.
#: 그래서 제3의 자리를 둔다: **이름은 있고, 사유가 있고, 안 열린다.**
LOCKED_CAPABILITIES: dict[str, str] = {
    "VIDEO":
        "이벤트 클릭 → 영상 재생 경로가 아직 없다. K3 는 **프레임**이고 영상이 아니다 — "
        "한 칸에 두면 프레임이 초록일 때 영상까지 초록으로 읽힌다. "
        "재생 경로가 서면 이 줄을 지우고 KERNEL_PACKAGES 에 넣는다. "
        "★ 사유 실측 (D-302, 2026-09-01): **실 스트림 부재가 아니라 배선 부재다.** "
        "`DetectionEvent.clip_path` 는 정의 1건 · 읽기 2곳(k1_event._to_view · "
        "k4_report.services)이고 **쓰기 0곳**이다 — 아무도 채우지 않는다. "
        "녹화는 스트림 단위로 존재하지만(`/start-record` · `/stop-record` → MinIO "
        "object_path) 그 산출물이 이벤트와 이어져 있지 않고, 이벤트 시각으로 구간을 "
        "찾아 되돌려주는 라우트도 없다(전수 라우트에 재생 경로 0건). "
        "즉 막고 있는 것은 카메라도 스트림도 아니라 **이벤트↔영상 구간의 연결과 "
        "재생 엔드포인트**이며, 이것은 개발로 풀 수 있는 항목이다(계약 블로커가 아니다). "
        "ZONE 처럼 지금 열 수는 없다 — 열려면 그 배선을 만들어야 하고, 그 전에 "
        "여는 것은 잴 수 없는 것을 재라고 요구하는 일이다.",
    # ★ FLOOD_EVENT_TYPE 은 **여기서 지워졌다** (D-294, 2026-08-31).
    #   지운 것이 곧 "이제 잴 수 있다"는 선언이고, 그 선언의 근거는 계약 문서 v1.1 과
    #   마이그레이션 0018 이다. 잠금 사유를 지우면서 단계의 `unlocked_by` 를 "K1" 로
    #   옮겼다 — 침수 이벤트를 만드는 것은 K1 의 일이기 때문이다.
    #   되돌아온다면(열거가 다시 빠진다면) `test_d294_event_type_separation.py` 가 먼저 멈춘다.
    # ★ ZONE 은 **여기서 지워졌다** (D-299, 2026-09-01).
    #   잠금 사유였던 "구역 개념이 모델에 없다" 가 사라졌다 — `Zone` 모델이 실재하고
    #   카메라 묶음 판정이 돈다. 지운 것이 곧 선언이고, 근거는 마이그레이션 0019 다.
    #   되돌아온다면(모델이 지워진다면) `test_zone_judgment.py` 가 먼저 멈춘다.
    #
    #   ⚠ 폴리곤은 여전히 미구현이다. 그것은 이 등재부가 아니라
    #   `stream_monitors.services.zones.ZONE_POLYGON_READY` 가 잠근다 — 잠기는 대상이
    #   다르기 때문이다. 여기는 "단계를 잴 수 있는가", 저기는 "어느 방식으로 재는가".
}


def kernel_present(code: str) -> bool:
    """그 커널이 **실재하는가.** 티켓 status 가 아니라 import 로 답한다.

    ★ 한 겹 좁혔다 — **파일이 있는 것과 잴 수 있는 것은 다르다** (2026-08-31).

      SDN 어댑터의 자리(`adapters/sdn/`)를 명세 수령 전에 세웠다. 포트·수령 요건·
      오류 계약처럼 **명세 없이도 확정할 수 있는 것**은 지금 확정해 두는 것이 옳고
      (DA-02 §3), 그래야 명세가 온 날 할 일이 "구현체 하나" 로 줄어든다.

      그런데 예전 술어대로라면 그 패키지가 import 되는 순간 E2E-3 이 **의무가 되고**
      E2E-1 의 7단계가 열린다 — 어댑터가 없는데 SDN 시나리오를 재라고 요구하게 된다.
      **잴 수 없는 것을 재라고 요구하는 것**은 이 등재부가 애초에 막으려던 일이다.

      그래서 모듈이 `KERNEL_READY = False` 를 **선언하면 없는 것으로 본다.**
      선언에 기대는 것이 아니냐 — 아니다. 값싼 선언이 못 되게 두 가지를 붙였다:

        · `NOT_READY_REASON` 이 비면 `scripts/verify_e2e_contract.py` 가 exit 1.
          "안 됐다" 는 말은 **사유를 요구한다** (D-264).
        · True 로 올리는 순간 그 시나리오 전체가 의무가 된다. 구현 없이 올리면
          시험이 **즉시 실패한다.** "됐다" 는 말은 **시험을 부른다.**

      선언이 거짓이면 어느 방향으로든 멈춘다. 그것이 이 술어가 여전히 실측인 이유다.
    """
    module = KERNEL_PACKAGES.get(code)
    if module is None:
        return False
    try:
        mod = importlib.import_module(module)
    except Exception:
        return False
    # 선언이 없으면 예전 그대로 — import 되면 있는 것이다.
    return bool(getattr(mod, "KERNEL_READY", True))


def not_ready_reason(code: str) -> str:
    """`KERNEL_READY=False` 인 모듈이 밝힌 사유. 없으면 빈 문자열.

    게이트가 이것을 읽어 **사유 없는 미준비**를 막는다. 사유가 없으면 그 False 는
    "아직" 인지 "영영" 인지 구별되지 않고, 구별되지 않는 것은 잊힌다.
    """
    module = KERNEL_PACKAGES.get(code)
    if module is None:
        return ""
    try:
        mod = importlib.import_module(module)
    except Exception:
        return ""
    if getattr(mod, "KERNEL_READY", True):
        return ""
    return str(getattr(mod, "NOT_READY_REASON", "") or "")


# ═══════════════════════════════════════════════════════════════════════════
# 단계표
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Step:
    """시나리오 한 단계.

    `unlocked_by` 가 None 이면 커널과 무관하게 **처음부터 돈다**.
    아니면 그 커널이 실재할 때 가동된다 (D-291 증분 규칙).
    """

    no: int
    title: str
    unlocked_by: str | None = None
    #: 이 단계가 재는 계약 AC. 없으면 빈 문자열 — **추측으로 채우지 않는다**(D-280).
    ac: str = ""


@dataclass(frozen=True)
class Scenario:
    code: str
    title: str
    steps: tuple[Step, ...]
    #: 이 시나리오의 시험 모듈. 해금되면 **실재해야 한다.**
    module: str
    #: ★ 이 커널이 붙는 순간 시험 파일이 **의무가 된다** — D-291 증분 규칙 그대로.
    #:      K2 done → E2E-1 가동 · K3 done → E2E-2 가동 · SDN → E2E-3 가동
    #:   단계별 `unlocked_by` 와 다른 값이다: 단계는 "무엇까지 잴 수 있나"를,
    #:   이것은 "언제부터 안 쓰면 실패인가"를 정한다. 둘을 합치면 K1 만으로 E2E-1 전체가
    #:   의무가 되고, 그러면 잴 수 없는 것을 재라고 요구하게 된다.
    required_from: str = ""
    #: 아직 못 쓴 이유. 해금 전에만 허용된다 — 해금 후에도 남아 있으면 실패한다.
    pending_reason: str = ""

    @property
    def active_steps(self) -> tuple[Step, ...]:
        return tuple(s for s in self.steps
                     if s.unlocked_by is None or kernel_present(s.unlocked_by))

    @property
    def unlocked(self) -> bool:
        """시험 파일이 의무인가. **단계가 하나 열렸다고 의무가 되지 않는다.**"""
        return kernel_present(self.required_from)

    @property
    def evidence_dir(self) -> Path:
        return EVIDENCE_ROOT / self.code


# ═══════════════════════════════════════════════════════════════════════════
# 등재부 — **이 집합이 정본이다** (D-285 ② · 이름으로 잠근다)
# ═══════════════════════════════════════════════════════════════════════════
SCENARIOS: dict[str, Scenario] = {
    "E2E-1": Scenario(
        code="E2E-1",
        title="화재 — 프레임 투입부터 보고서 PDF 까지",
        module="tests.e2e.test_e2e_1_fire",
        required_from="K2",          # D-291: "K2 done → E2E-1 의 1~5단계 가동"
        steps=(
            Step(1, "프레임 투입 → AI 탐지 결과가 파이프라인에 들어온다", None),
            Step(2, "K1 이벤트 기록 — 소유가 스트림에서 물려진다", "K1",
                 ac="F-01~03 탐지 저장"),
            Step(3, "F-04 판정 — 동일 이벤트 5분 내 중복 알림 0건", "K1",
                 ac="F-04 중복 알림 0건"),
            Step(4, "K2 수신자 결정 — 등급×역할 수신그룹", "K2",
                 ac="F-10 등급별 수신"),
            Step(5, "K2 발송 기록 — occurred_at → sent_at 30초 이내", "K2",
                 ac="F-10 30초 내 발송 기록"),
            Step(6, "K6 피드백 — 판정이 오탐률 분모·분자로 돌아온다", "K6",
                 ac="F-14 월간 오탐률"),
            Step(7, "SDN QoS 요청 (Mock · 10초)", "SDN", ac="F-06 10초"),
            Step(8, "K3 대시보드 프레임 — 프리셋 도달 0클릭 · 패널 5상태", "K3",
                 ac="F-09 5상태 100% · U3 도달 클릭 ≤ 2"),
            # ★ 8단계에서 **영상을 떼어냈다.** K3 가 붙었다고 "클릭→영상 3초"가
            #   측정되는 것이 아니다 — 영상 재생 경로가 아직 없다. 한 칸에 두면
            #   프레임이 초록일 때 영상까지 초록으로 읽힌다(미측정을 통과로 읽는 모양).
            #   `unlocked_by="VIDEO"` 는 `KERNEL_PACKAGES` 에 없으므로 **영영 안 열린다** —
            #   여는 사람이 그 이름을 등재하는 순간이 곧 "이제 잴 수 있다"는 선언이다.
            Step(9, "이벤트 클릭 → 영상 3초 이내 재생", "VIDEO", ac="F-09 영상 3초"),
            Step(10, "K4 보고서 PDF — 이벤트·조치·캡처 치환", "K4",
                 ac="F-11 템플릿 변수 3종"),
        ),
    ),
    "E2E-2": Scenario(
        code="E2E-2",
        title="침수 — 수위선 초과에서 등급 상향과 수신자 분기까지",
        module="tests.e2e.test_e2e_2_flood",
        required_from="K3",          # 실행 순서 ⑥: "K3 ‖ K4 착수 → … E2E-2 가동"
        steps=(
            Step(1, "수위선 초과 신호 투입", None),
            # ★ 2·3 은 **잠겨 있다.** 커널이 없어서가 아니라 **계약과 모델이 아직 그것을
            #   표현하지 못해서**다. 사유는 `LOCKED_CAPABILITIES` 에 있다.
            # ★ D-294 로 **열렸다.** 잠금 사유였던 FLOOD_EVENT_TYPE 은 위 등재부에서
            #   지워졌고, 이제 이 단계는 K1 이 있으면 돈다.
            Step(2, "F-02 이벤트 생성 (30초)", "K1", ac="F-02 30초"),
            Step(3, "같은 구역 인명(F-03) 결합 → 등급 상향", "ZONE", ac="F-03 결합"),
            Step(4, "등급별 수신자 그룹이 실제로 달라지는가", "K2",
                 ac="F-10 등급별 수신그룹 분기"),
        ),
    ),
    "E2E-3": Scenario(
        code="E2E-3",
        title="통신두절 — 링크다운에서 정찰 프로파일 초안까지 (비행 명령 미전송)",
        module="tests.e2e.test_e2e_3_linkdown",
        required_from="SDN",         # 실행 순서 ⑦: "SDN 어댑터 → E2E-3 가동"
        steps=(
            Step(1, "SDN 링크다운 (Mock I-3)", "SDN"),
            Step(2, "F-08 이벤트 (60초)", "SDN", ac="F-08 60초"),
            Step(3, "F-07 대체 경로 요청", "SDN", ac="F-07 대체 경로"),
            Step(4, "F-13 정찰 프로파일 초안 + **비행 명령 미전송 단언**", "SDN",
                 ac="F-13 spec_claim=0"),
        ),
        pending_reason=(
            "SDN 어댑터(F-06~08)가 없고, **만들 수 없다.** 에스비정보기술의 SDN 컨트롤러 "
            "API 명세를 아직 받지 못했다(계약 DEV-SBIT-GX-20260810 3조2항 — 착수 15일 내 제공, "
            "기한 2026-08-25 경과). DA-02 는 그래서 매핑서가 아니라 **수령 요건서**로 남아 있고 "
            "status=blocked 다. "
            "★ **Mock 도 못 만든다** — DA-02 §0: '각 인터페이스의 엔드포인트·필드 정의는 갑이 "
            "제공하는 명세를 기준으로 확정한다. Mock 조차 I-1~I-5 의 필드 이름과 타입이 있어야 "
            "만들 수 있다.' 추측한 필드명 위에 어댑터를 만들면 재작업이 확정된다(D-280). "
            "해소는 개발이 아니라 **명세 수령**이고, 대표 조치(계약 6조3항 기한 연장 통지) 사안이다."
        ),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# 공통 규약 — **메서드 이름으로 잠근다**
# ═══════════════════════════════════════════════════════════════════════════
#: 규약 번호 → (요구하는 시험 메서드 이름, 무엇을 재는가)
#:
#: 이름을 고정하는 이유: "격리도 봤습니다"는 보고이고, `test_isolation_...` 이 도는 것은
#: 사실이다. 규약을 문서에 적어 두면 다음 시나리오에서 조용히 빠진다 — D-286 이 이름 붙인
#: 실패 모양 그대로다.
REQUIRED_METHODS: dict[str, tuple[str, str]] = {
    "①": ("test_runs_on_migrated_database",
          "실 마이그레이션 DB 에서 도는가 — 표가 DB 에 실재하는지 직접 묻는다 (D-282 ②눈)"),
    "②": ("test_isolation_read_and_write_are_blocked",
          "다른 테넌트가 읽지도 쓰지도 못하는가 — 양방향 (D-290)"),
    "③": ("test_positive_control_without_the_event",
          "이벤트를 심지 않으면 이 E2E 가 실패하는가 (D-277 · D-289)"),
    "④": ("test_degraded_variant_keeps_core_path",
          "외부 의존을 죽여도 핵심 경로가 사는가 (W0-17)"),
}

#: 시나리오 모듈이 반드시 선언해야 하는 것.
#: `REAL_SAMPLE` 은 D-289 의 "표본 최소 1건은 실물" 을 **출처와 함께** 남기는 자리다.
REQUIRED_ATTRS: tuple[str, ...] = ("SCENARIO", "REAL_SAMPLE")

#: 규약 ⑤ — 실시간 대기 금지. 이 이름들이 시나리오 모듈에 나오면 실패한다.
#: `sleep` 하나만 막지 않는다 — 우회 형태(`wait`·`poll`)까지 이름으로 잠근다.
FORBIDDEN_WAITS: tuple[str, ...] = ("time.sleep(", "asyncio.sleep(", "sleep(")


def _active(steps: tuple["Step", ...]) -> tuple["Step", ...]:
    """해금된 단계만. `Scenario.active_steps` 와 **같은 술어**를 쓴다 —
    두 곳이 다른 말을 하면 어느 쪽도 못 믿는다 (D-227 이 만든 상태가 그것이었다)."""
    return tuple(s for s in steps
                 if s.unlocked_by is None or kernel_present(s.unlocked_by))


@dataclass
class StepOutcome:
    """단계 하나의 결과. 실패 표(규약 ⑥)의 한 줄이 된다."""

    no: int
    title: str
    ok: bool
    note: str = ""


@dataclass
class StepLedger:
    """★ 규약 ⑥ — **어느 단계에서 끊겼는지 표로 낸다** (D-274 의 E2E 판).

    E2E 는 길다. 3단계에서 죽으면 4~9단계는 **실행되지 않았을 뿐 실패한 것이 아니다**.
    그 둘을 같은 값으로 보고하면 "1건 실패"가 실제로는 "1건 실패 + 6건 미측정"이 된다 —
    이 저장소가 반복해서 만난 실패 모양이고, `TenantIsolationAPITest._report` 가
    같은 이유로 표를 낸다.
    """

    scenario: str
    rows: list[StepOutcome] = field(default_factory=list)

    def record(self, step: Step, ok: bool, note: str = "") -> None:
        self.rows.append(StepOutcome(step.no, step.title, ok, note))

    def render(self, planned: tuple[Step, ...]) -> str:
        """단계표. **미측정을 통과로 읽지 않게** 세 상태를 가른다.

        `OK` / `FAIL` / `잠김` / `미측정`. 미측정이 둘로 갈리는 것이 요점이다 —
        **잠겨서 못 잰 것**과 **앞 단계에서 끊겨 도달 못 한 것**은 다른 사실이고,
        전자는 기다릴 일이며 후자는 고칠 일이다.
        """
        unlocked = {s.no for s in _active(planned)}
        locked = len(planned) - len(unlocked)
        lines = [f"[{self.scenario}] 단계 {len(self.rows)}/{len(unlocked)} 도달 "
                 f"(계획 {len(planned)} · 잠김 {locked})"]
        for step in planned:
            row = next((r for r in self.rows if r.no == step.no), None)
            if row is not None:
                mark = "OK  " if row.ok else "FAIL"
                note = row.note
            elif step.no not in unlocked:
                mark = "잠김"
                note = f"해금 대기 — {step.unlocked_by}"
            else:
                mark = "미측정"
                note = "앞 단계에서 끊겨 도달하지 못했다"
            lines.append(f"  {mark}  {step.no}. {step.title[:44]:46} {note}")
        return "\n".join(lines)

    def write_evidence(self, scenario: Scenario) -> Path:
        """증거를 남긴다 (규약 ⑥). 경로를 돌려주어 보고에 그대로 쓴다.

        ★ **해금분이 아니라 계획된 전 단계**를 그린다. 해금분만 그리면 잠긴 단계가
          증거에서 사라지고, 그 순간 "2/2 도달"이 완주로 읽힌다 — 빠진 줄은 보이지
          않는다(D-274). 실측으로 그렇게 됐다: E2E-2 의 첫 증거가 4단계 중 잠긴 둘을
          지운 채 "2/2" 로 나왔다.
        """
        scenario.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = scenario.evidence_dir / "steps.md"
        body = self.render(scenario.steps)
        path.write_text(
            f"# {scenario.code} — {scenario.title}\n\n"
            f"해금 단계 {len(scenario.active_steps)}/{len(scenario.steps)}\n\n"
            f"```\n{body}\n```\n",
            encoding="utf-8",
        )
        return path
