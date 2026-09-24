# -*- coding: utf-8 -*-
"""카메라 맥박과 **군집 두절** — OPS-15 (2026-09-04 · 차선 Q).

한 문장
-------
    같은 구역 카메라 N대(기본 3) 중 M대(기본 2)가 **5분 안에 함께** 맥박을 잃으면
    그것은 카메라 고장이 아니라 **그 구역에 무슨 일이 생겼다**는 뜻이다.

왜 이 파일이 생겼나 — 「조용함」과 「죽음」은 다른 사실이다
---------------------------------------------------------
D-415 의 `cameras_silent_24h` 는 「이벤트가 안 온 카메라」를 센다. 아무 일도 없던
카메라와 케이블이 끊긴 카메라가 그 수에서 **같은 모양**이다(온보딩 U1 #3 · 실측).
프레임은 사건이 없어도 온다 — 그래서 `StreamMonitor.last_frame_at` 이 그 둘을 가른다.

★ **한 대와 여러 대는 다른 화면에 간다** (이 파일의 요점)
---------------------------------------------------------
    한 대 두절     `camera_down`          시스템 이벤트 — 운영이 본다. 사람이 가서 본다
    군집 두절      `camera_cluster_down`  재난 징후 — 관제가 본다

  두 개를 한 유형으로 뭉치면 「카메라 한 대 고장」과 「하천변이 통째로 끊겼다」가
  같은 줄로 목록에 쌓이고, 두 번째 것은 첫 번째 것들 사이에 묻힌다.

★ **초록의 절반은 「1대만 끊기면 0건」이다** (부작위 · 지시서 §3-3)
------------------------------------------------------------------
  이 규칙은 무엇을 **만드는가**보다 무엇을 **안 만드는가**로 값이 정해진다.
  한 대가 끊길 때마다 재난 징후를 내면 관제 화면은 카메라 고장 목록이 되고,
  그러면 진짜 군집 두절이 왔을 때 아무도 그 줄을 못 본다.
  `backend/tests/test_q_camera_pulse.py` 와 `scripts/verify_camera_pulse.py` 가
  **양성 1건과 음성 0건을 함께** 잰다 — 한쪽만 재는 판정기는 이 저장소에서 초록으로 죽는다.

★ 정직 고지 — **F-08 이 아니다**
--------------------------------
  F-08 은 SDN 링크 상태를 말하고 그 절은 손 밖에 그대로 있다(명세 미수령).
  이것은 **새 절(OPS-15)** 이다. SDN 명세가 오면 링크 상태가 아래 `judge_cluster` 의
  **두 번째 입력**이 된다 — 규칙은 안 바뀌고 입력만 는다.

계층 — L3 Platform
------------------
구역과 카메라의 사실이므로 `stream_monitors` 안, `services/zones.py` 와 같은 자리다.
이벤트를 만드는 것은 **K1 경로 하나뿐**이다(`kernels.k1_event.record_detection`) —
`DetectionEvent` 행을 여기서 직접 만들지 않는다. 직접 만들면 등급 검증·소유 상속·중복
억제가 한 번도 안 돌고, 그 행은 화면에는 이벤트로 보이면서 아무 규칙도 안 탄다
(D-401 이 시드에서 잡은 것과 같은 병).

캐시 — P-19
-----------
이 모듈은 HTTP 를 지나지 않는다. 읽기는 `_base_manager` 로 직접 센다 —
「상태·가용성을 말하는 값」이 응답 캐시를 지나면 두절이 200 뒤에 숨는다(D-412).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from common.billing_marks import exclude_not_counted
from common.tenant_scope import TenantScope

# ═══════════════════════════════════════════════════════════════════════════
# 규칙의 수 — **한 곳에만 둔다** (D-212). 화면·시험·판정기가 여기를 인용한다
# ═══════════════════════════════════════════════════════════════════════════

#: 마지막 프레임 뒤 이 시간이 지나면 **맥박을 잃었다**고 본다.
PULSE_TIMEOUT: timedelta = timedelta(minutes=5)

#: 「동시에」의 폭. 두 카메라의 마지막 프레임 시각이 이 안에 함께 들어오면 동시로 본다.
CLUSTER_WINDOW: timedelta = timedelta(minutes=5)

#: N — 이 수보다 적은 카메라를 가진 구역은 **군집 판정을 하지 않는다.**
#: 2대짜리 구역에서 2대가 끊기면 그것은 「군집」이 아니라 「그 구역 전부」이고,
#: 전부가 끊기는 일은 카메라 2대짜리 현장에서 너무 흔하다.
CLUSTER_MIN_CAMERAS: int = 3

#: M — 동시에 맥박을 잃은 카메라가 이 수 이상이면 군집 두절이다.
CLUSTER_MIN_DOWN: int = 2

#: 만들어지는 이벤트. **등급은 경계(warning)** 다 — ISA-101 이 빨강을 즉시 개입이
#: 필요한 것 전용으로 쓰기 때문이다. 군집 두절은 「가서 봐야 하는 일」이지 그 자체가
#: 재난은 아니다. 실제 재난이면 그 구역의 다른 유형이 곧 빨강으로 온다.
CLUSTER_EVENT_TYPE: str = "camera_cluster_down"
CLUSTER_SEVERITY: str = "warning"

#: 같은 군집에서 이 시간 안에 이미 두절을 낸 적이 있으면 **다시 내지 않는다.**
#: K1 의 10초 중복 창은 이 주기(맥박 검사)에 비해 너무 짧다 — 1분마다 도는 검사가
#: 5분 동안 5건을 만들면 그것은 하나의 사건이 다섯 줄이 된 것이다.
CLUSTER_RENOTIFY_WINDOW: timedelta = timedelta(minutes=5)


def _product_cameras(**lookups):
    """**제품이 세는** 활성 카메라. 이 파일의 세 문이 전부 이 한 줄을 지난다.

    ★ **왜 `_scoped` 안에 안 넣었나.** `scan_clusters` 는 구역만 `_scoped` 로 좁히고
      카메라는 `zones=zone` 으로 따로 고른다 — `_scoped` 에 넣으면 **화면은 고쳐지고
      사건 내는 자리는 그대로** 탐침을 센다. 그러면 격자에는 안 보이는 카메라가
      군집 두절 사건을 만들어 큐에 쌓이고, 사람은 **없는 카메라의 고장**을 본다.

    ★ **`exclude_unbillable` 이 아니다.** 그것은 「청구서에 올릴 수 있나」를 묻고
      훈련(`drill`)·검수 씨앗(`seed`)까지 뺀다. 훈련은 사람이 **봐야** 하는 것이라
      (P-201) 여기서 빼면 훈련을 켠 날 격자가 빈다. 이 문이 묻는 것은
      「고객이 세야 하나」이고 그 답은 `exclude_not_counted` 다.

    ⚠ **표식이 없는 행은 여기서 안 사라진다** — 이름으로 추측하지 않는다(D-280).
      남는 것은 자료의 구멍이고, 구멍은 코드가 아니라 표식으로 메운다.
    """
    Stream = _model("StreamMonitor")
    return exclude_not_counted(
        Stream._base_manager.filter(is_active=True, **lookups))


def _model(name: str):
    return apps.get_model("stream_monitors", name)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 — **순수 함수.** DB 도 Django 도 모른다 (zones.py 의 폴리곤 판정과 같은 이유)
# ═══════════════════════════════════════════════════════════════════════════
#
# 판정이 모델에 붙어 있으면 경계 사례를 시험하려고 매번 행을 만들어야 하고,
# 그러면 **경계를 적게 시험하게 된다.** 1대/2대/3대 · 창 안/밖 · null 은 DB 없이 잰다.


@dataclass(frozen=True)
class ClusterVerdict:
    """한 구역의 판정. **왜 그렇게 봤는지를 값으로 들고 다닌다.**

    참/거짓만 돌려주면 「0건」이 「규칙이 안 걸렸다」인지 「구역이 작아서 아예 안 봤다」
    인지 구별되지 않는다 — 그 둘은 다른 사실이다 (D-290 · D-301).
    """

    #: 이 구역의 활성 카메라 수 (분모).
    total: int
    #: 맥박이 한 번도 온 적 없는 카메라 수 (`last_frame_at is None`).
    #: **두절로 세지 않는다** — 「아직 안 왔다」는 「죽었다」가 아니다.
    never_seen: int
    #: 지금 맥박을 잃은 카메라 id (마지막 프레임 시각 순).
    silent: tuple[int, ...] = ()
    #: 그중 **동시에** 잃은 묶음. 이것의 크기가 M 이상이면 발동한다.
    cluster: tuple[int, ...] = ()
    #: 발동하는가.
    fires: bool = False
    #: 사람이 읽는 사유. 발동하지 않은 경우에도 **비지 않는다.**
    reason: str = ""


def judge_cluster(
    pulses,
    now: datetime,
    *,
    min_cameras: int = CLUSTER_MIN_CAMERAS,
    min_down: int = CLUSTER_MIN_DOWN,
    timeout: timedelta = PULSE_TIMEOUT,
    window: timedelta = CLUSTER_WINDOW,
) -> ClusterVerdict:
    """`[(camera_id, last_frame_at|None), ...]` 를 보고 군집 두절인지 답한다.

    세 걸음이고, 각 걸음이 **다른 이유로** 0건을 낼 수 있다:

      ① 구역이 작다(`total < min_cameras`)      → 아예 안 본다
      ② 잃은 대수가 모자란다(`< min_down`)      → **1대만 끊긴 경우가 여기다**
      ③ 잃은 시각이 흩어져 있다(창 밖)          → 각자 고장이지 함께 끊긴 것이 아니다

    ★ ③ 이 이 규칙의 핵심이다. 「2대가 죽어 있다」와 「2대가 **함께** 죽었다」는 다르다.
      한 달 전에 고장 나 방치된 카메라 옆에서 오늘 한 대가 끊기면, 대수만 세는 규칙은
      그것을 재난 징후라고 말한다 — 그리고 그 말은 틀렸다.
    """
    rows = list(pulses)
    total = len(rows)
    never = [cid for (cid, last) in rows if last is None]

    if total < min_cameras:
        return ClusterVerdict(
            total=total, never_seen=len(never),
            reason=f"구역 카메라 {total}대 — 군집 규칙은 {min_cameras}대부터 본다")

    silent = sorted(
        [(cid, last) for (cid, last) in rows if last is not None and now - last > timeout],
        key=lambda r: r[1],
    )
    if len(silent) < min_down:
        tail = (f" · 맥박이 한 번도 안 온 카메라 {len(never)}대는 두절로 세지 않는다"
                if never else "")
        return ClusterVerdict(
            total=total, never_seen=len(never),
            silent=tuple(cid for (cid, _l) in silent),
            reason=f"맥박을 잃은 카메라 {len(silent)}대 — 군집은 {min_down}대부터다{tail}")

    # ── ③ **동시성** — 잃은 시각이 한 창 안에 몇 대나 들어오는가 ────────────
    best: tuple[int, ...] = ()
    for i, (_cid, start) in enumerate(silent):
        same = tuple(cid for (cid, last) in silent[i:] if last - start <= window)
        if len(same) > len(best):
            best = same

    if len(best) < min_down:
        span = silent[-1][1] - silent[0][1]
        return ClusterVerdict(
            total=total, never_seen=len(never),
            silent=tuple(cid for (cid, _l) in silent),
            reason=(f"맥박을 잃은 카메라 {len(silent)}대이지만 **함께 잃지 않았다** — "
                    f"가장 먼 두 대의 간격 {span} > 창 {window}. 각자 고장이다"))

    return ClusterVerdict(
        total=total, never_seen=len(never),
        silent=tuple(cid for (cid, _l) in silent),
        cluster=best, fires=True,
        reason=(f"구역 카메라 {total}대 중 {len(best)}대가 {window} 안에 함께 맥박을 "
                f"잃었다 (기준 {min_cameras}중 {min_down})"))


# ═══════════════════════════════════════════════════════════════════════════
# 맥박을 적는다 — **쓰기 면**
# ═══════════════════════════════════════════════════════════════════════════
@transaction.atomic
def record_frame(*, scope: TenantScope, stream_monitor_id: int,
                 at: datetime | None = None) -> datetime:
    """카메라 하나의 맥박을 갱신한다. 수집기가 프레임을 받을 때마다 부른다.

    ★ 사람이 부른 경우 **문지기가 먼저다** — 남의 카메라 맥박을 내가 갱신할 수 있으면
      남의 구역 두절을 **조용히 덮을 수 있다**. 그것은 데이터를 심는 것보다 나쁘다:
      심은 행은 보이지만, 덮인 두절은 아무 흔적도 남기지 않는다.
    """
    from common.tenant_filters import assert_scoped

    Stream = _model("StreamMonitor")
    if not scope.is_system:
        assert_scoped(Stream, stream_monitor_id, scope.actor)
    when = at or timezone.now()
    changed = Stream._base_manager.filter(pk=stream_monitor_id).update(last_frame_at=when)
    if not changed:
        raise ValueError(f"stream_monitor_id={stream_monitor_id} 가 없다 — "
                         f"없는 카메라의 맥박을 적으면 그 맥박은 아무 구역에도 안 든다")
    return when


# ═══════════════════════════════════════════════════════════════════════════
# 읽는다 — 맥박 N/N (OPS-14 생존 알림이 인용한다)
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class PulseCounts:
    """「카메라 맥박 N/N」의 두 수 + **셋째 수**.

    ★ 셋째 수(`never_seen`)를 빼지 않는다. `alive/total` 만 내면 「한 번도 안 온
      카메라」가 분모에 조용히 섞여 **매일 아침 낮은 수**를 만들고, 낮은 수가 매일
      같으면 사람은 그것을 배경으로 읽는다.
    """

    alive: int
    total: int
    never_seen: int

    def as_line(self) -> str:
        """생존 알림 본문에 들어가는 한 줄."""
        tail = f" (맥박 미수신 {self.never_seen}대 포함)" if self.never_seen else ""
        return f"카메라 맥박 {self.alive}/{self.total}{tail}"


def pulse_counts(*, scope: TenantScope, now: datetime | None = None,
                 group=None) -> PulseCounts:
    """살아 있는 카메라 / 전체. **활성 카메라만** 센다 — 탐침은 분모에 없다."""
    now = now or timezone.now()
    qs = _scoped(_product_cameras(), scope, group)
    total = qs.count()
    alive = qs.filter(last_frame_at__gt=now - PULSE_TIMEOUT).count()
    never = qs.filter(last_frame_at__isnull=True).count()
    return PulseCounts(alive=alive, total=total, never_seen=never)


@dataclass(frozen=True)
class CameraPulseRow:
    """카메라 한 대의 맥박. **세 사실을 세 값으로** 들고 다닌다.

    ★ 왜 `alive` 를 여기서 정하나 (2026-09-05 · 차선 C2 · UX-23)
    ------------------------------------------------------------
    화면(카메라 격자)이 카메라 목록을 받아 **자기 문턱으로** 생사를 정하면, 그 순간
    판정이 두 벌이 된다 — 화면의 「응답 없음」과 이 파일이 내는 `camera_down`·
    `camera_cluster_down` 이 서로 다른 카메라를 가리키게 되고, 그 어긋남은 아무도
    못 본다. 그래서 **문턱은 이 파일 밖으로 나가지 않는다.** 나가는 것은 답이다.

    ★ `last_frame_at is None` 은 **「아직 한 장도 안 왔다」**이지 「죽었다」가 아니다.
      `alive=False` 이지만 `last_frame_at` 이 `None` 인 것으로 그 둘이 갈린다 —
      두 값을 하나로 접으면 방금 등록한 카메라가 방금 끊긴 카메라로 보인다(D-290).
    """

    id: int
    name: str
    alive: bool
    last_frame_at: datetime | None

    @property
    def never_seen(self) -> bool:
        return self.last_frame_at is None

    def silent_seconds(self, now: datetime) -> int | None:
        """조용한 지 몇 초. **한 번도 안 온 카메라는 `None`** — 0이 아니다."""
        if self.last_frame_at is None:
            return None
        return int((now - self.last_frame_at).total_seconds())


def pulse_rows(*, scope: TenantScope, now: datetime | None = None,
               group=None) -> list[CameraPulseRow]:
    """카메라별 맥박 전수. **활성 카메라만** 센다 — `pulse_counts` 와 같은 모수다.

    ★ 이 함수와 `pulse_counts` 는 **같은 질의·같은 문턱**을 쓴다. 두 수가 갈리면
      화면의 「응답 없음 N대」와 생존 알림의 「맥박 N/N」이 다른 말을 하게 되고,
      `tests/test_c2_camera_grid.py::OneJudgementNotTwoTest` 가 그 자리를 잰다.

    ★ 이름을 함께 낸다. id 만 내면 부르는 쪽이 이름을 얻으려고 카메라 표를 다시
      질의하게 되고, 그 질의에는 이 파일의 스코프 규약이 안 붙는다.
    """
    now = now or timezone.now()
    qs = _scoped(_product_cameras(), scope, group)
    rows = qs.distinct().order_by("name", "pk").values_list(
        "pk", "name", "last_frame_at")
    return [
        CameraPulseRow(
            id=pk, name=name or "",
            alive=bool(last is not None and now - last <= PULSE_TIMEOUT),
            last_frame_at=last)
        for (pk, name, last) in rows
    ]


def _scoped(qs, scope: TenantScope, group=None):
    """스코프로 좁힌다. `zones._scoped` 와 **같은 판단**을 쓴다 (D-212).

    소속이 없는 사람에게는 **아무것도 없다.** 전체를 돌려주면 그 순간 소속 없음이
    전권이 된다 — §0.4 의 `created_by__isnull` OR 절과 같은 함정이다.
    """
    from common.tenant_filters import (_guess_group_lookup, get_user_group,
                                       is_global_admin)

    if group is not None:
        return qs.filter(**{_guess_group_lookup(qs.model): group})
    if scope.is_system:
        return qs
    if is_global_admin(scope.actor):
        return qs
    owner = get_user_group(scope.actor)
    if owner is None:
        return qs.none()
    return qs.filter(**{_guess_group_lookup(qs.model): owner})


# ═══════════════════════════════════════════════════════════════════════════
# 훑는다 — 구역마다 판정하고, 발동하면 **K1 경로로** 이벤트를 만든다
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class ScanResult:
    """훑기 한 번의 결과. **본 것과 만든 것을 따로 센다.**

    「이벤트 0건」이 「구역이 0개라 아무것도 안 봤다」인지 「봤는데 규칙이 안 걸렸다」
    인지 갈리지 않으면, 이 판정기는 아무 일도 안 하면서 매일 초록을 낸다 (D-301).
    """

    zones_seen: int = 0
    cameras_seen: int = 0
    created_event_ids: list = field(default_factory=list)
    suppressed_zone_ids: list = field(default_factory=list)
    #: `[(zone_id, zone_name, ClusterVerdict), ...]`
    verdicts: list = field(default_factory=list)

    @property
    def created(self) -> int:
        return len(self.created_event_ids)


def scan_clusters(*, scope: TenantScope, now: datetime | None = None,
                  create_events: bool = True, group=None) -> ScanResult:
    """활성 카메라묶음 구역을 전부 훑는다.

    `create_events=False` 면 **판정만 하고 아무것도 만들지 않는다** — 화면과 판정기가
    부작위(1대만 끊기면 0건)를 확인할 때 쓰는 문이다. 이 문이 없으면 부작위를 재려고
    진짜 이벤트를 만들어야 하고, 그러면 재는 행위가 재는 대상을 바꾼다.
    """
    from kernels.k1_event import record_detection

    Zone = _model("Zone")
    Event = _model("DetectionEvent")
    now = now or timezone.now()
    out = ScanResult()

    zones = _scoped(
        Zone._base_manager.filter(kind=Zone.Kind.CAMERA_GROUP, is_active=True),
        scope, group)
    for zone in zones.distinct():
        rows = list(
            _product_cameras(zones=zone)
            .values_list("pk", "last_frame_at"))
        out.zones_seen += 1
        out.cameras_seen += len(rows)
        verdict = judge_cluster(rows, now)
        out.verdicts.append((zone.pk, zone.name, verdict))
        if not verdict.fires or not create_events:
            continue

        # ── 대표 카메라 — **가장 먼저 끊긴 것** ──────────────────────────
        #   이벤트는 카메라 하나에 매달린다(모델의 FK). 어느 것으로 할지 규칙이
        #   흔들리면 같은 사건이 매번 다른 카메라로 기록되고, 그러면 아래 억제가
        #   자기 자신을 못 찾는다.
        lead = verdict.cluster[0]

        recent = (
            Event._base_manager
            .filter(event_type=CLUSTER_EVENT_TYPE,
                    stream_monitor_id__in=list(verdict.cluster),
                    occurred_at__gt=now - CLUSTER_RENOTIFY_WINDOW,
                    occurred_at__lte=now)
            .exists())
        if recent:
            out.suppressed_zone_ids.append(zone.pk)
            continue

        result = record_detection(
            scope=TenantScope.system(
                reason=f"OPS-15 카메라 맥박 군집 두절 — 구역 {zone.pk} · "
                       f"{len(verdict.cluster)}대 동시 두절. 맥박 검사에는 요청자가 없다"),
            stream_monitor_id=lead,
            event_type=CLUSTER_EVENT_TYPE,
            severity=CLUSTER_SEVERITY,
            occurred_at=now,
        )
        out.created_event_ids.append(result.event_id)
    return out


__all__ = [
    # 규칙의 수 — 화면·시험·판정기가 자기 숫자를 들지 않는다 (D-212)
    "PULSE_TIMEOUT",
    "CLUSTER_WINDOW",
    "CLUSTER_MIN_CAMERAS",
    "CLUSTER_MIN_DOWN",
    "CLUSTER_EVENT_TYPE",
    "CLUSTER_SEVERITY",
    "CLUSTER_RENOTIFY_WINDOW",
    # 판정 (순수)
    "ClusterVerdict",
    "judge_cluster",
    # 맥박
    "record_frame",
    "PulseCounts",
    "pulse_counts",
    # ★ 카메라별 전수 (UX-23 · 2026-09-05). **문턱은 이 파일 밖으로 안 나간다** —
    #   나가는 것은 `alive` 라는 답이다. 화면이 문턱을 들면 판정이 두 벌이 된다.
    "CameraPulseRow",
    "pulse_rows",
    # 훑기
    "ScanResult",
    "scan_clusters",
]
