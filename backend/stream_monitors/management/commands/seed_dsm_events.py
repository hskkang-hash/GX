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

★ 2026-09-22 — **P-20 시드 구멍 둘** (알림 규칙 0건 · 스냅샷 0건)
-----------------------------------------------------------------
[실측 2026-09-21] 개발 DB: 카메라 40 · 이벤트 20 · **스냅샷 있는 이벤트 0** ·
**알림 규칙 0**. 그래서 모바일 M1(내게 온 이벤트)은 빈 화면이고, W2 상세의 스냅샷 자리는
영원히 비어 있다. **화면이 비어 있는 이유가 「사건이 없어서」인지 「규칙이 없어서」인지
화면만 봐서는 갈리지 않는다.**

그 둘을 이 명령이 채운다. 채우는 방식은 앞의 규약 그대로다:

    ① 알림 규칙   `kernels.k2_notify.save_notification_rule` **하나만** 부른다
    ② 스냅샷      MinIO 에 **실제 객체**를 올리고, 참조는 `record_detection(snapshot_path=)`
                  즉 **K1 경로**로 붙인다. 행을 고치지 않는다
    ③ 시스템 이벤트  `camera_down` · `storage_high` — W1 「시스템」 프리셋이 읽는 유형
    ④ **시드는 규칙을 흉내 내지 않는다** — 발송은 K2 가 한다. 시드는 `send` 를 부르고
      **결과를 셀 뿐** 발송 이력 행을 직접 만들지 않는다. 억제(F-04·5분)로 접힌 것도
      접힌 대로 센다

★ 스냅샷 이미지는 **합성 표식 프레임**이다 — 단색 바탕에 「SEED · 테넌트 · event_id ·
  시각」을 적는다. 실제 사고 장면을 흉내 내지 않는다(P-20 ② · 불변 제약). 시드로 찍은
  화면은 실제 화면이지만 **실제 사고는 아니다** — 그 구분이 이미지 안에 있어야 한다.

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

# ═══════════════════════════════════════════════════════════════════════════
# P-20 ① 알림 규칙 — **역할을 가리킨다. 사람을 가리키지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
#: 발송 채널. **`log` 는 사람이 아니라 로그에 도달한다**(`k2_notify.channels.LogChannel`).
#: 검수 환경에는 도달할 수신자가 없고 업체도 미정(D4-1)이라, 메일로 보내면 이력이
#: **전부 실패 행**이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.
#: 이 값이 발송 이력의 `channel` 칸에 그대로 남으므로 「사람에게 갔다」로 읽히지 않는다.
SEED_RULE_CHANNEL = "log"

#: 수신 역할 셋 — U1·U2·U4. 역할 **코드**로 적는다(번호는 환경마다 다르다).
#: 코드는 `config/k3_roles.py` 가 DA-03 §3-4 의 사람 다섯과 이어 둔 그 실측 목록에서 골랐다.
#: ⚠ 여기 적힌 역할에 **그 테넌트의 사람이 0명이면 수신자도 0명**이다. 규칙이 있다는 것과
#:   받을 사람이 있다는 것은 다른 사실이고, 아래 보고가 그 둘을 따로 센다 (D-301).
SEED_RULE_ROLES = (
    ("fire_user", "U1 관제요원 — 화면 앞에 앉아 이벤트를 처리하는 사람"),
    ("operator", "U1 관제요원(운용) — 같은 자리의 다른 역할 코드"),
    ("fire_admin", "U2 관제팀장/상황실장 — 규칙·수신자를 정하는 사람"),
    ("view_only_-_anyang", "U4 재난안전과 담당 공무원 — 열람 전용"),
)

#: 규칙이 걸릴 등급. **`critical` 하나다** — 시드 이벤트 20건 중 화재 5 + 침수 5 가
#: 이 등급이므로 정확히 절반이 규칙에 걸린다(P-20 ①: "절반이 규칙에 걸려").
SEED_RULE_SEVERITY = "critical"

# ═══════════════════════════════════════════════════════════════════════════
# P-20 ③ 시스템 이벤트 — 죽은 카메라 · 저장 용량
# ═══════════════════════════════════════════════════════════════════════════
#: W1 프리셋 4 「시스템」이 읽는 유형. `ops_monitor` 안에만 있던 신호가 **이벤트로**
#: 나오는 자리다 — 새 화면 없이 U5 가 기존 목록에서 본다.
SYSTEM_SCENARIOS = [
    ("camera_down", "warning", "시스템 — 카메라 무응답(24시간 이벤트 0건)"),
    ("storage_high", "warning", "시스템 — 저장 용량 임계 초과"),
]

#: 합성 표식 프레임의 크기·바탕색. **실제 CCTV 장면이 아니다**는 것이 한눈에 보여야 하므로
#: 사진처럼 보이지 않는 단색을 쓴다.
FRAME_SIZE = (640, 360)
FRAME_BG = (23, 33, 48)
FRAME_FG = (236, 240, 245)
FRAME_FONT_PATHS = (
    "/app/fonts/NanumGothic-Bold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic-Bold.ttf",
)


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
            from stream_monitors.models import StreamMonitor

            #: ★ **객체를 먼저 지운다.** 카메라 행이 사라지면 어느 접두를 지워야 하는지
            #:   알 수 없게 되고, MinIO 에는 아무도 가리키지 않는 스냅샷이 남는다.
            #:   그 고아 객체는 다음 판정에서 「DB 참조 수와 객체 수가 다르다」로 빨개진다.
            objects = self._purge_objects(StreamMonitor)
            rules = self._purge_rules(group)
            cam = DetectionEvent._base_manager.filter(stream_monitor__code=SEED_CODE)
            n = cam.count()
            cam.delete()                      # 발송 이력은 이벤트를 따라 함께 지워진다
            m = StreamMonitor._base_manager.filter(code=SEED_CODE).delete()[0]
            self.stdout.write(
                f"[SEED] 지웠다 — 이벤트 {n}건 · 카메라 {m}건 · 알림 규칙 {rules}건 · "
                f"MinIO 객체 {objects if objects is not None else '판정 불가'}")
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
        #: 심은 것의 (event_id, 시각, 객체경로, 순번). 아래 ② 마무리와 ④ 대조가 읽는다.
        planted: list[tuple[int, object, str, int]] = []
        for (etype, severity, label) in SCENARIOS:
            for (steps, verdict) in COMBOS:
                nth += 1
                #: ★ 시각을 **벌린다.** 같은 (stream, type) 이 10초 안에 다시 오면 K1 이
                #:   중복 억제로 접는다(F-04) — 접히면 심은 수와 생긴 수가 갈라지고,
                #:   그 차이를 모르면 「N건 심었다」가 거짓이 된다.
                occurred_at = now - timedelta(minutes=3 * nth)
                #: ★ P-20 ② — **올리고 나서 참조를 붙인다.** 순서가 반대면(먼저 행을
                #:   만들고 나중에 칸을 고치면) 그 고치기가 곧 직접 INSERT 와 같은 일이
                #:   된다(P-9). 못 올렸으면 빈 문자열이고, 빈 채로 심는다 —
                #:   **가짜 경로를 만들지 않는다**(detection_snapshot 머리말).
                snapshot_path = self._upload_frame(cam, group, occurred_at, seq=nth)
                result = record_detection(
                    scope=scope_pipe, stream_monitor_id=cam.pk,
                    event_type=etype, severity=severity,
                    occurred_at=occurred_at,
                    snapshot_path=snapshot_path,
                    address=SEED_ADDRESS, address_status="resolved",
                )
                made += 1
                planted.append((result.event_id, occurred_at, snapshot_path, nth))
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

        # ── P-20 ③ 시스템 이벤트 ─────────────────────────────────────────
        #   죽은 카메라·저장 용량은 지금까지 `ops_monitor` 안에만 있었다(온보딩 U5 #14).
        #   같은 신호를 **이벤트로** 내면 W1 「시스템」 프리셋에서 새 화면 없이 보인다.
        system_made, system_skipped = 0, []
        for (etype, severity, label) in SYSTEM_SCENARIOS:
            nth += 1
            occurred_at = now - timedelta(minutes=3 * nth)
            try:
                result = record_detection(
                    scope=scope_pipe, stream_monitor_id=cam.pk,
                    event_type=etype, severity=severity, occurred_at=occurred_at,
                    snapshot_path="",     # 시스템 이벤트에는 **프레임이 없다.**
                                          # 없는 것에 그림을 붙이면 그것이 거짓말이다
                    address=SEED_ADDRESS, address_status="resolved",
                )
            except Exception as exc:      # noqa: BLE001 — 열거 밖이면 K1 이 막는다
                system_skipped.append(f"{etype}: {type(exc).__name__}: {exc}")
                continue
            system_made += 1
            planted.append((result.event_id, occurred_at, "", nth))

        # ── P-20 ② 마무리 — **참조가 가리키는 객체에 event_id 를 적는다** ──
        #   왜 두 번 올리나: 첫 번째는 **K1 이 참조를 만들게** 하기 위해서다(그때는
        #   event_id 가 아직 없다). 두 번째는 그 참조가 가리키는 바로 그 객체에
        #   번호를 적기 위해서다. 객체 이름은 `(카메라, 시각)` 으로 정해지므로 같은
        #   이름에 덮어쓰기이고 **객체 수는 늘지 않는다** — 아래 대조가 그것을 확인한다.
        stamped = 0
        for (event_id, occurred_at, path, seq) in planted:
            if not path:
                continue
            again = self._upload_frame(cam, group, occurred_at, seq=seq,
                                       event_id=event_id)
            if again == path:
                stamped += 1

        # ── P-20 ① 알림 규칙 · ④ 발송은 K2 가 한다 ───────────────────────
        rules = self._rules(scope_user, group)
        sent, folded, no_recipient, failed = self._deliveries(scope_pipe, planted)

        self.stdout.write(
            f"[SEED] 카메라 {'새로 만듦' if created else '기존 사용'} ({SEED_CODE}) · "
            f"소속 {group.pk}")
        self.stdout.write(
            f"[SEED] [실측] **알림 규칙 {len(rules)}건** — "
            f"{', '.join(f'{r.severity}/{r.role_code}' for r in rules) or '없다'} "
            f"(채널 {SEED_RULE_CHANNEL} · K2 save_notification_rule 경로)")
        self.stdout.write(
            f"[SEED] [실측] **스냅샷 객체 {stamped}장** (합성 표식 프레임 · MinIO 실제 객체)")
        self.stdout.write(
            f"[SEED] [실측] **시스템 이벤트 {system_made}건**" +
            (f" · 못 심은 것 {len(system_skipped)}: {'; '.join(system_skipped)}"
             if system_skipped else ""))
        self.stdout.write(
            f"[SEED] [실측] **발송 기록 {sent}행** — K2 가 만든 것이다(시드가 아니다). "
            f"억제로 접힌 이벤트 {folded} · 수신자 0명 {no_recipient} · 실패 행 {failed}")
        self.stdout.write(
            f"[SEED] **심은 이벤트 {made}건** (record_detection 호출 {made}회) · "
            f"판정 {judged}건 · 대응 전이 {moved}회 — 전부 K1 공개 면을 통과했다")
        self.stdout.write(
            f"[SEED] [실측] 오탐 결합으로 **자동 종결된 것 {coupled}건** — 이 수는 시드가 "
            f"옮긴 것이 아니라 소비자가 옮긴 것이다 (P-16)")
        self._report(DetectionEvent)

    # ═══════════════════════════════════════════════════════════════════
    # P-20 ② 합성 표식 프레임 — **실제 장면을 흉내 내지 않는다**
    # ═══════════════════════════════════════════════════════════════════
    @staticmethod
    def synthetic_frame(*, tenant: str, event_id, when, seq: int) -> bytes:
        """단색 바탕에 「SEED · 테넌트 · event_id · 시각」을 적은 JPEG 한 장.

        ★ **왜 사진처럼 만들지 않나.** 검수 자리에서 시드 화면이 현장 화면으로 읽히면
          그것은 착시가 아니라 거짓말이다(D-284 · P-9). 그림 자체가 「나는 시드다」라고
          말해야 한다 — 표기는 화면 밖에도 있지만, 이미지가 잘려 나가도 남는 것은
          이미지 안의 글자뿐이다.

        ★ `event_id` 가 `None` 이면 「미부여」로 적는다. 첫 번째 올리기 때는 K1 이
          아직 행을 안 만들었으므로 번호가 없다 — **없는 번호를 지어내지 않는다.**
        """
        from io import BytesIO

        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", FRAME_SIZE, FRAME_BG)
        draw = ImageDraw.Draw(img)

        font = small = None
        for path in FRAME_FONT_PATHS:
            try:
                font = ImageFont.truetype(path, 34)
                small = ImageFont.truetype(path, 22)
                break
            except OSError:
                continue
        if font is None:                      # 글꼴이 없어도 **글자는 넣는다**
            font = small = ImageFont.load_default()

        draw.rectangle([(0, 0), (FRAME_SIZE[0] - 1, FRAME_SIZE[1] - 1)],
                       outline=(214, 76, 76), width=6)
        marked = event_id if event_id is not None else "미부여(#%d)" % seq
        lines = [
            ("SEED / 합성 표식 프레임", font),
            ("실제 CCTV 장면이 아닙니다", small),
            ("테넌트  %s" % tenant, small),
            ("event_id  %s" % marked, small),
            ("시각  %s" % when.strftime("%Y-%m-%d %H:%M:%S"), small),
            ("출처  data_source=seed", small),
        ]
        y = 44
        for (text, f) in lines:
            draw.text((36, y), text, fill=FRAME_FG, font=f)
            y += 50 if f is font else 38

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    def _upload_frame(self, cam, group, occurred_at, *, seq, event_id=None) -> str:
        """프레임 한 장을 MinIO 에 올리고 **경로를 돌려준다.** 못 올리면 빈 문자열.

        올리는 것은 `stream_monitors.services.detection_snapshot.upload_snapshot` 이다 —
        파이프라인이 쓰는 그 함수를 그대로 쓴다. 시드가 자기 업로더를 따로 두면
        **시드가 통과하는 경로와 제품이 통과하는 경로가 갈리고**, 갈린 두 경로는
        어긋나도 아무도 모른다(D-369).
        """
        from stream_monitors.services.detection_snapshot import upload_snapshot

        try:
            jpeg = self.synthetic_frame(
                tenant=str(getattr(group, "name", None) or group.pk),
                event_id=event_id, when=occurred_at, seq=seq)
        except Exception as exc:              # noqa: BLE001
            self.stdout.write(
                "[SEED] ⚠ 프레임을 못 만들었다 (#%d): %s: %s"
                % (seq, type(exc).__name__, exc))
            return ""
        path, reason = upload_snapshot(
            stream_monitor_id=cam.pk, jpeg_bytes=jpeg, occurred_at=occurred_at)
        if not path:
            self.stdout.write("[SEED] ⚠ 스냅샷을 못 올렸다 (#%d): %s" % (seq, reason))
        return path

    def _purge_objects(self, StreamMonitor):
        """씨앗 카메라의 스냅샷 객체를 지운다. **못 지우면 None** — 0건과 구별한다."""
        cam = StreamMonitor._base_manager.filter(code=SEED_CODE).first()
        if cam is None:
            return 0
        try:
            from stream_monitors.services.detection_snapshot import PREFIX
            from stream_monitors.utils.minio_client import minio_client
        except Exception:                     # noqa: BLE001
            return None
        if not getattr(minio_client, "available", False) or minio_client.client is None:
            return None
        try:
            names = [o.object_name for o in minio_client.client.list_objects(
                minio_client.bucket_name, prefix="%s/%s/" % (PREFIX, cam.pk),
                recursive=True)]
            for name in names:
                minio_client.client.remove_object(minio_client.bucket_name, name)
            return len(names)
        except Exception as exc:              # noqa: BLE001
            self.stdout.write("[SEED] ⚠ 객체를 못 지웠다: %s: %s"
                              % (type(exc).__name__, exc))
            return None

    # ═══════════════════════════════════════════════════════════════════
    # P-20 ① 알림 규칙 — **K2 진입 경로로만 만든다**
    # ═══════════════════════════════════════════════════════════════════
    def _rules(self, scope_user, group):
        """수신 규칙을 세운다. 없는 역할은 **조용히 건너뛰지 않고 말한다**(D-301).

        ★ 두 번 돌려도 규칙이 두 배가 되지 않아야 한다. 같은 (등급·역할·구역) 규칙이
          이미 있으면 `rule_id` 로 **고친다** — 같은 사람에게 두 번 가는 규칙을
          시드가 만들면, 중복 알림이 배선의 결함인지 시드의 결함인지 갈리지 않는다.
        """
        from django.apps import apps

        from kernels.k2_notify import save_notification_rule
        from kernels.k2_notify.exceptions import InvalidNotifyInput

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        out = []
        for (code, why) in SEED_RULE_ROLES:
            existing = Rule._base_manager.filter(
                severity=SEED_RULE_SEVERITY, role__code=code, zone__isnull=True,
                channels=[SEED_RULE_CHANNEL]).first()
            try:
                out.append(save_notification_rule(
                    scope=scope_user, severity=SEED_RULE_SEVERITY, role_code=code,
                    channels=[SEED_RULE_CHANNEL], zone=None, is_active=True,
                    rule_id=existing.pk if existing else None))
            except InvalidNotifyInput as exc:
                self.stdout.write("[SEED] ⚠ 규칙을 못 만들었다 (%s · %s): %s"
                                  % (code, why, exc))
        self._report_recipients(scope_user, group)
        return out

    def _purge_rules(self, group) -> int:
        """시드가 세운 규칙을 지운다. **표는 채널이다** — 사람이 만든 규칙에
        `log` 채널을 넣을 이유가 없다(사람에게 도달하지 않으므로). 그 값 하나가
        「이것은 시드가 만든 규칙이다」의 유일한 근거다.

        ⚠ **그 소속 안에서만 지운다.** 채널만 보고 지우면 다른 테넌트가 검수용으로
          세워 둔 규칙까지 사라진다 — 지우는 쪽의 격리도 격리다(D-290 쓰기 방향).
        """
        from django.apps import apps

        from kernels.k1_event.services import _owner_field

        Rule = apps.get_model("stream_monitors", "NotificationRule")
        qs = Rule._base_manager.filter(channels=[SEED_RULE_CHANNEL])
        field = _owner_field(Rule)
        qs = (qs.filter(groups=group) if field == "groups"
              else qs.filter(group=group))
        return qs.delete()[0]

    def _report_recipients(self, scope_user, group):
        """[실측] **규칙이 있다**와 **받을 사람이 있다**는 다른 사실이다 (D-301).

        역할에 사람이 0명이면 규칙은 서 있고 수신자는 0명이다. 그 상태를 「규칙 N건」
        하나로 보고하면, 모바일 M1 이 빈 화면일 때 원인을 여기서 못 찾는다.
        """
        from kernels.k2_notify import resolve_recipients

        people = resolve_recipients(scope=scope_user, severity=SEED_RULE_SEVERITY,
                                    group=group)
        by_role = {}
        for r in people:
            by_role[r.role_code] = by_role.get(r.role_code, 0) + 1
        self.stdout.write(
            "[SEED] [실측] 이 규칙들이 고르는 **수신자 %d명** — 역할별 %s"
            % (len(people),
               by_role or "0명 (규칙은 섰으나 그 역할에 사람이 없다)"))

    # ═══════════════════════════════════════════════════════════════════
    # P-20 ④ 발송 — **시드는 규칙을 흉내 내지 않는다.** K2 가 한다
    # ═══════════════════════════════════════════════════════════════════
    def _deliveries(self, scope_pipe, planted):
        """심은 이벤트를 K2 에 넘긴다. **행은 K2 가 만든다.**

        시드가 `DeliveryRecord` 를 직접 만들면, 발송 경로가 죽어 있어도 화면은 똑같이
        보인다 — 2026-09-17 에 「시드가 rejected 4 이니 규칙이 도는 듯하다」로 잘못 읽은
        자리와 정확히 같은 모양이다(P-16). 여기서 세는 넷은 전부 **K2 의 답**이다.
        """
        from django.apps import apps

        from kernels.k2_notify import send
        from kernels.k2_notify.exceptions import NoRecipients

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        sent = folded = no_recipient = failed = f10 = 0
        for (event_id, _occurred_at, _path, _seq) in planted:
            severity = Event._base_manager.values_list(
                "severity", flat=True).get(pk=event_id)
            if severity != SEED_RULE_SEVERITY:
                continue                      # 규칙이 없는 등급 — 안 보내는 것이 맞다
            try:
                views = send(scope=scope_pipe, event_id=event_id)
            except NoRecipients:
                no_recipient += 1
                continue
            if not views:
                folded += 1                   # F-04 5분 억제로 접혔다 — 그것도 사실이다
                continue
            sent += len(views)
            failed += sum(1 for v in views if not v.succeeded)
            f10 += sum(1 for v in views if v.meets_f10)
        #: ★ [실측] **시드 데이터로는 F-10 이 초록이 될 수 없다.** 시드는 중복 억제
        #:   (F-04 · 10초)를 피하려고 이벤트를 3분씩 과거로 민다. F-10 이 재는 두 점은
        #:   `occurred_at → sent_at` 이므로 지연이 언제나 3분을 넘는다 — 그것은
        #:   **발송 경로의 사실이 아니라 시드의 사실**이다. 이 수를 함께 찍는 이유는
        #:   보고서·화면이 시드의 지연을 제품의 지연으로 읽지 않게 하기 위해서다(P-9).
        self.stdout.write(
            f"[SEED] [실측] 그중 F-10(30초 내 발송)을 만족하는 행 {f10}행 — "
            f"시드는 이벤트를 과거로 밀어 심으므로 **이 수는 0이 정상이다.** "
            f"F-10 은 시드가 아니라 시험(tests/test_k2_notify_kernel)이 잰다")
        return sent, folded, no_recipient, failed

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

        # ── P-20 네 수 — **판정은 `scripts/verify_seed_p20.py` 가 한다** ──────
        #   여기서 다시 판정하지 않는다. 두 곳이 판정하면 언젠가 갈리고, 갈린 뒤에는
        #   어느 쪽이 정본인지 아무도 모른다(D-212). 이 자리는 **세기만** 한다.
        from django.apps import apps

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        system_types = [t for (t, _s, _l) in SYSTEM_SCENARIOS]
        self.stdout.write(
            f"[SEED]   P-20 ① 알림 규칙 {Rule._base_manager.filter(channels=[SEED_RULE_CHANNEL]).count()}건 · "
            f"발송 기록 {Delivery._base_manager.filter(event__in=rows).count()}행")
        self.stdout.write(
            f"[SEED]   P-20 ② 스냅샷 참조 {rows.exclude(snapshot_path='').count()}건")
        self.stdout.write(
            f"[SEED]   P-20 ③ 시스템 이벤트 "
            f"{rows.filter(event_type__in=system_types).count()}건 "
            f"(기대 {len(SYSTEM_SCENARIOS)})")
        if total == 0:
            self.stdout.write("[SEED] ⚠ 0건이다 — **0건은 통과가 아니다**(D-301)")
