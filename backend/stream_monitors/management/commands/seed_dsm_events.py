# -*- coding: utf-8 -*-
"""검수용 이벤트를 **실제 경로로** 심는다 (P-9 · D-401).

왜 이 명령이 생겼나 — 「실제」의 정의 [인용: 지시서 2026-09-16 P-9]
--------------------------------------------------------------------
    실제 이벤트 = K1 이벤트 생성 경로를 통과해 DB 에 행이 생긴 이벤트.
    **DB 에 직접 INSERT 하거나 화면 코드에 고정값을 넣으면 모형이다 — 금지.**

그 정의로 저장소를 재니 [실측 2026-09-16] **기존 씨앗이 모형이었다:**
`scripts/capture_screens.py::seed_events` 가 `DetectionEvent._base_manager.create(...)`
로 행을 직접 만들고 있었다. 화면 16장은 그 위에서 찍혔다.

직접 INSERT 가 왜 나쁜가 — 우리 경우에 구체적으로:
  · `event_type` 이 `gxprobe-D384-screen` 이었다. **열거값이 아니다.** K1 의 `_validate`
    를 지나지 않으므로 아무 문자열이나 들어간다. 화면·통계는 그 값을 유형으로 읽는다
  · 중복 억제(F-04)·주소 조회(FX-5)·클립 참조가 **한 번도 안 돈다.** 그 경로의 결함은
    씨앗으로 찍은 화면에서 절대 드러나지 않는다
  · 즉 **모형 데이터는 파이프라인을 건너뛴 만큼 결함을 숨긴다.** 화면을 띄우는 것이
    가장 강한 시험인 이유(D-386)가 그대로 뒤집힌다

그래서 이 명령은 `kernels.k1_event.record_detection` 하나만 부른다.
상태를 옮길 때도 `advance_response`·`review_event` 를 부른다 — **칸을 직접 쓰지 않는다.**

    python manage.py seed_dsm_events --user gxprobe_e2e            # 심는다
    python manage.py seed_dsm_events --user gxprobe_e2e --purge    # 지운다
    python manage.py seed_dsm_events --user gxprobe_e2e --report   # 세기만 한다

★ 심은 것에는 표가 붙는다(`SEED_CODE` 카메라). **지울 때의 유일한 근거**이고,
  검수 콘솔의 「데이터 출처: 시드」 표기도 이 표에서 나온다 — 시드로 찍은 화면은
  실제 화면이지만 **실제 사고는 아니다.** 고객이 그것을 구분할 수 있어야 한다(P-9).
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

#: 씨앗 카메라의 코드. 이 표 하나가 「시드인가」의 유일한 근거다.
SEED_CODE = "GX-SEED-DSM"
SEED_ADDRESS = "경기도 안양시 만안구 안양천서로 100 (시드 카메라)"

#: 시나리오 셋 — 계약이 말하는 재난 계열에서 고른다. 배송 계열은 §0.4 라 쓰지 않는다.
#: `(event_type, severity)` 는 **열거값**이다. 아무 문자열이나 못 넣는 것이 요점이다.
SCENARIOS = [
    ("fire", "critical", "화재 — 하천 둔치 소각"),
    ("flood", "critical", "침수 — 수위 급상승"),
    ("intrusion", "warning", "침입 — 야간 출입 통제구역"),
    ("person", "info", "사람 — 통제구역 보행"),
]

#: 대응 축 × 판정 축의 조합. **한 축만 채우면 두 축이 있다는 사실이 화면에 안 보인다.**
#: (대응 진행 몇 칸을 갈 것인가, 판정 verdict 를 붙일 것인가)
COMBOS = [
    (0, None),              # 발생 · 미판정 — 당직자가 지금 봐야 하는 것
    (1, None),              # 접수 확인 · 미판정
    (2, "confirmed"),       # 조치중 · 진짜였다
    (3, "confirmed"),       # 종결 · 진짜였다
    #: ★ 2026-09-20 (P-16) — 종결 · 오탐이었다. **대응 축은 시드가 걷지 않는다.**
    #:   판정 하나가 결합 규칙으로 종결까지 끌고 간다(`steps` 를 3 으로 둔 것은
    #:   「여기까지 가 있어야 한다」는 **기대값**이고, 그 값을 아래에서 대조한다).
    (3, "rejected"),        # 종결 · 오탐이었다 — 오탐률의 분자
]
FORWARD = ["acknowledged", "in_progress", "closed"]


class Command(BaseCommand):
    help = "검수용 DSM 이벤트를 K1 실제 경로로 심는다 (P-9)"

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True,
                            help="이 계정이 볼 수 있는 소속에 심는다")
        parser.add_argument("--purge", action="store_true", help="심은 것을 지운다")
        parser.add_argument("--report", action="store_true", help="세기만 한다")

    # ── 소속 ─────────────────────────────────────────────────────────────
    def _group(self, username):
        """★ 소속은 제품이 읽는 방식 그대로 읽는다 (`common.tenant_filters.get_user_group`).

        두 벌로 읽으면 **화면이 보는 소속과 씨앗이 심긴 소속이 갈라지고**, 그러면
        화면은 「0건」을 그린다 — 격리가 제대로 걸린 결과인데 결함처럼 보인다(D-369).
        """
        from django.contrib.auth import get_user_model

        from common.tenant_filters import get_user_group

        user = get_user_model()._base_manager.filter(username=username).first()
        if user is None:
            raise CommandError(f"계정이 없다: {username}")
        group = get_user_group(user)
        if group is None:
            raise CommandError(
                f"{username} 에 소속이 없다 — 심어도 그 계정에는 안 보인다. "
                "격리를 끄지 않는다(D-105): 소속을 먼저 붙여라")
        return user, group

    def _assert_not_shared(self):
        """쓰기 전에 **분류 등록부**에 묻는다 (D-270 ③).

        왜 진짜 검사인가: 시드 카메라와 그 이벤트는 **한 테넌트의 것**이다.
        `StreamMonitor`·`DetectionEvent` 가 언젠가 공용 마스터로 분류되면, 여기서 심은
        검수용 행이 **전 테넌트 화면에 나타난다** — 남의 관제 화면에 우리 시드가 뜬다.
        그때 이 커맨드는 멈춰야 한다.

        등록부(`tests/tenant_classification.py`)가 그 분류의 **유일한 출처**다 —
        판정식을 복사하지 않는다(D-212). 못 읽으면 **통과시키지 않는다**:
        「검사 못함」과 「대상 아님」은 다른 사실이다(D-301).
        """
        try:
            from tests.tenant_classification import SHARED_MASTERS
        except ImportError as exc:
            raise CommandError(
                f"분류 등록부(tests/tenant_classification.py)를 읽지 못했다: {exc} — "
                f"공용 마스터인지 확인하지 못한 채로 쓰지 않는다 (D-270 ③ · D-301)")
        for label in ("stream_monitors.StreamMonitor",
                      "stream_monitors.DetectionEvent"):
            if label in SHARED_MASTERS:
                raise CommandError(
                    f"{label} 이 분류 등록부에서 **공용 마스터**다. 검수용 시드를 공용 행에 "
                    f"심으면 **전 테넌트 화면에 우리 시드가 뜬다** (D-270 ③)")

    def _camera(self, group):
        """씨앗 카메라. **주소를 넣는다**(FX-5) — 알림·보고서의 위치란이 이 값을 쓴다."""
        from stream_monitors.models import StreamMonitor

        cam, created = StreamMonitor._base_manager.get_or_create(
            code=SEED_CODE,
            defaults=dict(name="시드 카메라 (검수용)", ip_source="127.0.0.1",
                          is_active=False, is_visualize=False, order=9997,
                          is_external=False,
                          # ★ [실측 2026-09-16] 1차판은 여기에 주소 문자열을 넣었고
                          #   `DataError: value too long for varchar(16)` 로 죽었다.
                          #   `address_source` 는 **자유 문자열이 아니라 열거값**이다
                          #   (unset/manual · D-330). 설치 주소는 `install_address` 다.
                          #   이름이 비슷한 칸 둘을 섞은 것 — 동음이의의 작은 판이다(D-337).
                          install_address=SEED_ADDRESS,
                          install_address_detail="하천 둔치 감시탑",
                          address_source="manual",
                          group_id=group.pk),
        )
        if cam.group_id != group.pk:
            cam.group_id = group.pk
            cam.save(update_fields=["group"])
        return cam, created

    # ── 실행 ─────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        from stream_monitors.models import DetectionEvent

        self._assert_not_shared()          # 쓰기 전에 등록부에 묻는다 (D-270 ③)
        user, group = self._group(opts["user"])

        if opts["purge"]:
            cam = DetectionEvent._base_manager.filter(stream_monitor__code=SEED_CODE)
            n = cam.count()
            cam.delete()
            from stream_monitors.models import StreamMonitor
            m = StreamMonitor._base_manager.filter(code=SEED_CODE).delete()[0]
            self.stdout.write(f"[SEED] 지웠다 — 이벤트 {n}건 · 카메라 {m}건")
            return

        if opts["report"]:
            self._report(DetectionEvent)
            return

        from common.tenant_scope import TenantScope
        from kernels.k1_event import advance_response, record_detection, review_event

        cam, created = self._camera(group)
        scope_user = TenantScope.of(user)
        scope_pipe = TenantScope.system(
            reason="시드 — 탐지 파이프라인에는 요청자가 없다 (D-281)")

        now = timezone.now()
        made, moved, judged, coupled = 0, 0, 0, 0
        nth = 0
        for (etype, severity, label) in SCENARIOS:
            for (steps, verdict) in COMBOS:
                nth += 1
                #: ★ 시각을 **벌린다.** 같은 (stream, type) 이 10초 안에 다시 오면 K1 이
                #:   중복 억제로 접는다(F-04) — 접히면 심은 수와 생긴 수가 갈라지고,
                #:   그 차이를 모르면 「N건 심었다」가 거짓이 된다.
                result = record_detection(
                    scope=scope_pipe, stream_monitor_id=cam.pk,
                    event_type=etype, severity=severity,
                    occurred_at=now - timedelta(minutes=3 * nth),
                    snapshot_path="",          # MinIO 부재 — **비어 있는 채로 둔다**(P-9)
                    address=SEED_ADDRESS, address_status="resolved",
                )
                made += 1
                if verdict:
                    review_event(result.event_id, verdict=verdict,
                                 reason=f"시드 — {label}", scope=scope_user)
                    judged += 1
                #: ★ 2026-09-20 (P-16) — `rejected` 는 **대응 축을 직접 걷지 않는다.**
                #:   여기서 세 칸을 더 걸으면 시드가 규칙을 **흉내 내는 것**이 되고,
                #:   그러면 규칙이 안 돌아도 시드는 똑같이 보인다. 2026-09-17 에
                #:   「시드가 rejected 4 · closed 8 이니 돌아가는 듯하다」로 잘못 읽은
                #:   자리가 정확히 여기다 — **수는 원인을 말하지 않는다**(세종 09-18 §0-4).
                #:   이제 이 네 건의 `closed` 는 **결합 소비자가 한 일**이고,
                #:   아래 대조가 그것을 말로가 아니라 수로 확인한다.
                for to in ([] if verdict == "rejected" else FORWARD[:steps]):
                    advance_response(result.event_id, to_state=to,
                                     reason=f"시드 — {label}", scope=scope_user)
                    moved += 1
                if verdict == "rejected":
                    state = DetectionEvent._base_manager.values_list(
                        "response_state", flat=True).get(pk=result.event_id)
                    if state != "closed":
                        raise CommandError(
                            f"[SEED] 오탐 판정 뒤에도 대응 축이 {state!r} 입니다 — "
                            f"결합 소비자가 안 돌고 있습니다(P-16). 시드가 그 자리를 "
                            f"대신 닫으면 규칙의 부재가 안 보입니다.")
                    coupled += 1

        self.stdout.write(
            f"[SEED] 카메라 {'새로 만듦' if created else '기존 사용'} ({SEED_CODE}) · "
            f"소속 {group.pk}")
        self.stdout.write(
            f"[SEED] **심은 이벤트 {made}건** (record_detection 호출 {made}회) · "
            f"판정 {judged}건 · 대응 전이 {moved}회 — 전부 K1 공개 면을 통과했다")
        self.stdout.write(
            f"[SEED] [실측] 오탐 결합으로 **자동 종결된 것 {coupled}건** — 이 수는 시드가 "
            f"옮긴 것이 아니라 소비자가 옮긴 것이다 (P-16)")
        self._report(DetectionEvent)

    def _report(self, DetectionEvent):
        """[실측] 무엇이 몇 건인가. **손으로 세지 않는다.**"""
        from collections import Counter

        rows = DetectionEvent._base_manager.filter(stream_monitor__code=SEED_CODE)
        total = rows.count()
        by_resp = Counter(rows.values_list("response_state", flat=True))
        by_status = Counter(rows.values_list("status", flat=True))
        by_type = Counter(rows.values_list("event_type", flat=True))
        self.stdout.write(f"[SEED] [실측] 시드 이벤트 총 {total}건")
        self.stdout.write(f"[SEED]   대응 진행: {dict(by_resp)}")
        self.stdout.write(f"[SEED]   탐지 판정: {dict(by_status)}")
        self.stdout.write(f"[SEED]   유형:      {dict(by_type)}")
        if total == 0:
            self.stdout.write("[SEED] ⚠ 0건이다 — **0건은 통과가 아니다**(D-301)")
