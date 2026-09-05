#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""운영 기반 ③ — **감시 3종.** 죽었을 때 사람이 안다 (D-354 ①).

세 가지만 본다. 더 보면 아무도 안 본다.
--------------------------------------
  ① **살아 있는가** (liveness)  — DB · 캐시 · 객체저장에 닿는가
  ② **밀리는가** (lag)          — 최신 이벤트가 얼마나 오래됐나 · 못 보낸 알림이 쌓였나
  ③ **채워지는가** (fill)       — DB 가 얼마나 컸나 · 최근에 이벤트가 들어왔나

★ 임계값은 **목표가 아니라 출발점**이다 (D-280)
-----------------------------------------------
지금 이 값들은 2026-09-09 첫 측정에서 나온 수를 근거로 **넉넉하게** 잡았다.
운영 데이터가 쌓이면 조이는 것이 맞고, **재기 전에 정한 값이 아니다.**
값 하나하나에 「왜 이 수인가」를 적어 둔다 — 적을 수 없는 임계값은 임계값이 아니다.

★ 「닿지 못했다」와 「0이다」를 가른다 (D-301)
---------------------------------------------
객체저장이 죽어서 못 센 것과 객체가 0개인 것은 다른 사실이다.
못 잰 칸은 `null` 로 나가고 판정은 **UNKNOWN** 이다 — 초록이 아니다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/ops_monitor.py            # 사람이 읽는 표
    docker exec ... python /repo/scripts/ops_monitor.py --check   # 경보용: 0 정상 / 1 경보 / 2 판정 불가
    python scripts/ops_monitor.py --self-test

    ★ `--check` 를 크론에 걸고 exit 1 을 사람에게 보내면 그것이 경보다.
      **보내는 자리(메일·문자·챗)는 고객 환경마다 다르므로 여기서 정하지 않는다** —
      정하면 그 환경에서만 도는 감시가 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_ALARM, EXIT_UNKNOWN = 0, 1, 2

OK, ALARM, UNKNOWN = "OK", "ALARM", "UNKNOWN"

#: 임계값 — **왜 이 수인가**를 함께 적는다. 적을 수 없으면 임계값이 아니다.
THRESHOLDS = {
    # ① 살아 있는가
    "db_ping_ms": (500, "DB 왕복 500ms. 첫 측정에서 이벤트 처리 전체가 p95 13ms 였다 — "
                        "왕복 하나가 500ms 면 그건 지연이 아니라 고장이다"),
    # ② 밀리는가
    "latest_event_age_min": (60, "최신 이벤트가 60분보다 오래됐으면 파이프라인이 멈춘 것으로 본다. "
                                 "★ 카메라가 조용한 밤에도 울린다 — 그래서 이 값은 "
                                 "**운영 데이터를 보고 조여야 하는 첫 후보**다"),
    "unsent_deliveries": (10, "못 보낸 알림 10건. F-10 은 30초 내 발송이므로 10건이 쌓였다는 것은 "
                              "발송 경로가 막혔다는 뜻이다"),
    # ── P-65 감사 쓰기 지연 (2026-09-05 · 턴 F · 열두 번째 신호) ────────────
    "audit_queue_lag_sec": (300, "★ 감사 큐 지연 **5분**. 근거는 [실측]이다 — 턴 E 에 celery "
                                 "워커가 0개이던 **사흘** 동안 `task_add_log` 가 12,468건 "
                                 "밀려 있었고, 그동안 이 저장소의 어떤 신호도 울리지 않았다. "
                                 "감사 로그는 「나중에 쓰면 되는 것」이 아니다 — 사고가 난 "
                                 "순간의 기록이 사고 뒤에 쓰이면 그 기록은 **그 순간을 "
                                 "증명하지 못한다**. 5분을 고른 이유: 정상일 때 이 큐는 "
                                 "초 단위로 비고(쓰는 속도 [실측]), 5분이면 사람이 "
                                 "붙어야 하는 정도의 밀림이다. ⚠ 지연은 [추정]이다 — "
                                 "celery 메시지에 넣은 시각이 없다"
                                 "(`common/audit_queue.py` 머리말)"),
    # ③ 채워지는가
    "db_size_gb": (50, "DB 50GB. 지금 4MB 다 — 이 값은 상한이 아니라 **증가를 눈치채는 자리**다"),
    # ── 평상 운영 ① 죽은 카메라 (2026-09-20 · 차선 E) ──────────────────────
    "cameras_silent_24h": (0, "★ [추정] 0 대. **한 대라도 조용하면 사람이 본다** — 카메라는 "
                              "수십 대 규모이므로 「몇 대까지는 괜찮다」는 값이 없다. "
                              "⚠ 이 신호는 죽은 카메라와 **아무 일도 없던 카메라**를 못 가른다 "
                              "(아래 collect 의 ⚠ 를 보라). 그래서 경보의 뜻은 「죽었다」가 "
                              "아니라 **「가서 봐라」**다"),
    # ── 평상 운영 ④ 저장 용량 (2026-09-20 · 차선 E) ────────────────────────
    "storage_used_pct": (80, "★ [추정] 80%. 근거는 이 저장소에 없다 — 영상 보존기간·카메라 수가 "
                             "정해지면 그때 다시 잡는다. 80 을 고른 이유는 **남은 20% 가 "
                             "사람이 움직일 시간**이기 때문이다(주말 하나를 버티는 폭). "
                             "용량 상한이 선언되지 않으면 이 신호는 **판정 불가**다 — 모르는 "
                             "것을 초록으로 적지 않는다(D-301)"),
}

#: 용량 상한은 **환경이 선언한다.** 코드가 추측하면 그 추측이 곧 초록이 된다.
#:   GX_STORAGE_CAPACITY_GB=500   (없으면 storage_used_pct 는 UNKNOWN)
STORAGE_CAPACITY_ENV = "GX_STORAGE_CAPACITY_GB"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def judge(signal: str, value, thresholds=THRESHOLDS) -> str:
    """한 신호의 판정. **못 잰 것은 초록이 아니다** (D-301)."""
    if value is None:
        return UNKNOWN
    limit = (thresholds.get(signal) or (None, ""))[0]
    if limit is None:
        return OK
    return ALARM if value > limit else OK


def collect() -> dict:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.db import connection

    out: dict = {"measured_at": _now().isoformat(timespec="seconds"), "signals": {}}

    def put(name, value, note=""):
        out["signals"][name] = {"value": value, "verdict": judge(name, value), "note": note}

    # ① 살아 있는가 ────────────────────────────────────────────────────────
    try:
        start = time.perf_counter()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        put("db_ping_ms", round((time.perf_counter() - start) * 1000, 2))
    except Exception as exc:
        put("db_ping_ms", None, "DB 에 닿지 못했다: %s" % type(exc).__name__)

    try:
        from django.core.cache import cache

        start = time.perf_counter()
        cache.set("ops_monitor_ping", "1", 10)
        alive = cache.get("ops_monitor_ping") == "1"
        out["signals"]["cache_alive"] = {
            "value": alive, "verdict": OK if alive else ALARM,
            "note": "왕복 %.1fms" % ((time.perf_counter() - start) * 1000)}
    except Exception as exc:
        out["signals"]["cache_alive"] = {"value": None, "verdict": UNKNOWN,
                                         "note": "캐시에 닿지 못했다: %s" % type(exc).__name__}

    # ★ [실측 2026-09-18] 앞판은 `default_storage.exists(...)` 를 불러 **예외가 안 나면
    #   닿은 것**으로 읽었다. MinIO 를 실제로 내리고 재어 보니 그 호출은 **예외 없이
    #   False** 를 돌려주었고, 이 신호는 저장소가 죽은 채로 **OK** 를 냈다.
    #
    #     저장소 살아 있을 때   object_store_alive  OK
    #     저장소 내렸을 때      object_store_alive  OK      ← 눈이 감겼다
    #
    #   「없다」와 「못 물어봤다」를 한 값으로 읽은 것이다 — D-301 이 이름 붙인 그 모양이고,
    #   하필 **「살아 있는가」를 보라고 세운 신호**에서 났다.
    #   그래서 저장소에게 **저장소만 답할 수 있는 것**을 묻는다: 버킷의 존재.
    #   닿지 못하면 그 호출은 **예외를 던진다** — 그것이 우리가 원하는 갈림이다.
    #   ⚠ 쓰지 않는다. 감시가 데이터를 만들면 그건 감시가 아니다.
    try:
        from django.conf import settings as _s
        from minio import Minio

        _ep = str(getattr(_s, "MINIO_ENDPOINT", "") or "")
        for _scheme in ("http://", "https://"):
            if _ep.startswith(_scheme):
                _ep = _ep[len(_scheme):]
        _bucket = getattr(_s, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        _c = Minio(_ep.rstrip("/"), access_key=_s.MINIO_ACCESS_KEY,
                   secret_key=_s.MINIO_SECRET_KEY,
                   secure=bool(getattr(_s, "MINIO_USE_HTTPS", False)))
        _found = _c.bucket_exists(_bucket)
        out["signals"]["object_store_alive"] = {
            "value": True, "verdict": OK if _found else ALARM,
            "note": ("저장소가 답했다 · 버킷 %s %s"
                     % (_bucket, "있음" if _found else "**없음** — 닿았지만 담을 곳이 없다"))}
    except Exception as exc:
        # 닿지 못한 것은 **모른다가 아니라 나쁨**이다. 「살아 있는가」의 답은 「아니오」다.
        out["signals"]["object_store_alive"] = {
            "value": False, "verdict": ALARM,
            "note": "저장소에 닿지 못했다: %s %s" % (type(exc).__name__, str(exc)[:80])}

    # ② 밀리는가 ──────────────────────────────────────────────────────────
    try:
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        latest = Event._base_manager.order_by("-occurred_at").values_list(
            "occurred_at", flat=True).first()
        if latest is None:
            put("latest_event_age_min", None, "이벤트가 한 건도 없다 — 「밀렸다」가 아니라 「비었다」")
        else:
            put("latest_event_age_min", round((_now() - latest).total_seconds() / 60, 1))
    except Exception as exc:
        put("latest_event_age_min", None, "재지 못했다: %s" % type(exc).__name__)

    try:
        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        put("unsent_deliveries", Delivery._base_manager.filter(succeeded=False).count())
    except Exception as exc:
        put("unsent_deliveries", None, "재지 못했다: %s" % type(exc).__name__)

    # ── P-65 **감사 쓰기 지연** — 열두 번째 신호 (2026-09-05 · 턴 F) ──────
    #
    # ★ 왜 이 신호가 없으면 안 되는가. 이 저장소는 감사 로그를 「지워지는가」로만
    #   지켜 왔다(OPS-07 ②). 그런데 감사에 못 답하는 길은 둘이고, 둘째가 더 조용하다:
    #   **생긴 것이 안 쓰이는 것.** 표는 그대로고 행 수도 안 줄고 화면도 멀쩡하다.
    #   [실측 턴 E] 워커 0개인 사흘 동안 12,468건이 큐에 갇혀 있었고 아무도 몰랐다.
    #
    # ★ 재는 자리는 **한 곳**이다 — `common/audit_queue.py`. 생존 알림 본문도 같은
    #   함수를 부른다. 두 벌로 재면 반드시 어긋나고, 어긋난 쪽이 조용히 초록이 된다(D-369).
    #
    # ★ 경보를 **어디로 보내는가는 여기서 정하지 않는다.** `--check` 의 exit 1 이
    #   경보이고, 그 exit 를 받아 사람에게 보내는 자리는 P-41 이 이미 정했다
    #   (`K2_OPS_ALERT_ROLE_CODES` = U5 시스템관리자 · `K2_SEND_ALLOWED_DOMAINS`
    #   밖으로는 실발송하지 않는다). 여기서 새 발송 경로를 만들면 그 경로만 허용
    #   목록을 비켜 간다.
    try:
        from common.audit_queue import measure as _audit_measure

        aq = _audit_measure(now=_now())
        keys = aq.get("queue_keys") or {}
        out["signals"]["audit_queue_backlog"] = {
            "value": aq.get("backlog"),
            "verdict": OK if aq.get("backlog") is not None else UNKNOWN,
            "note": ("밀린 감사 쓰기 [실측] · 담긴 큐 %s — ⚠ `LLEN %s` 하나만 재면 "
                     "**언제나 0**이다 — kombu 가 우선순위마다 **다른 키**를 쓴다(이름 뒤 두 바이트 + 우선순위 숫자). 임계는 건수가 "
                     "아니라 **지연**에 건다"
                     % (keys or "없음", aq.get("queue_base") or "default"))
                    if aq.get("backlog") is not None
                    else "밀린 건수를 **못 쟀다**: %s"
                         % (aq.get("errors", {}).get("backlog") or "사유 없음")}
        put("audit_queue_lag_sec", aq.get("lag_seconds"), aq.get("lag_basis") or "")
        out["signals"]["audit_write_rate_per_min"] = {
            "value": aq.get("write_rate_per_min"),
            "verdict": OK if aq.get("write_rate_per_min") is not None else UNKNOWN,
            "note": ("최근 %d분간 `logger_auditlogs` 에 들어온 행/분 [실측] · "
                     "마지막 쓰기 %s (임계 없음 — **세어 두는 수**다. 조용한 밤에 "
                     "0인 것은 장애가 아니다)"
                     % (getattr(__import__("common.audit_queue", fromlist=["x"]),
                                "RATE_WINDOW_MINUTES", 10),
                        aq.get("last_write_at") or "없음"))}
    except Exception as exc:
        put("audit_queue_lag_sec", None, "재지 못했다: %s: %s"
            % (type(exc).__name__, str(exc)[:120]))

    # ③ 채워지는가 ────────────────────────────────────────────────────────
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_database_size(current_database())")
            size = int(cur.fetchone()[0])
        put("db_size_gb", round(size / (1024 ** 3), 3))
    except Exception as exc:
        put("db_size_gb", None, "재지 못했다: %s" % type(exc).__name__)

    try:
        Monitor = apps.get_model("stream_monitors", "StreamMonitor")
        out["signals"]["cameras"] = {"value": Monitor._base_manager.count(), "verdict": OK,
                                     "note": "등록 카메라 수 — 늘고 줄어드는 것이 보인다"}
    except Exception as exc:
        out["signals"]["cameras"] = {"value": None, "verdict": UNKNOWN,
                                     "note": "재지 못했다: %s" % type(exc).__name__}

    # ── 평상 운영 ① 죽은 카메라 ───────────────────────────────────────────
    # ★★ **감시 유무를 먼저 잰다** (세종 09-20 차선 E). 답: **없다.**
    #   `StreamMonitor` 에는 「마지막으로 살아 있던 시각」 칸이 없다 —
    #   `is_active` 는 **운영자가 켜고 끄는 스위치**이지 카메라가 살아 있다는 증거가
    #   아니다. 스위치가 켜진 채 죽은 카메라와 살아 있는 카메라는 그 칸에서 같다.
    #
    #   그래서 지금 잴 수 있는 것은 **간접 증거 하나**뿐이다: 그 카메라에서 마지막
    #   이벤트가 언제 왔나.
    #   ⚠ 이것은 「죽었다」의 증거가 아니다. **아무 일도 없던 카메라도 조용하다.**
    #     둘을 가르려면 스트림 하트비트(마지막 프레임 시각)가 필요하고 그것은 칸이
    #     없다 — 잠금으로 등재한다(DA-05/blockers.yaml :: CAMERA_LIVENESS_HEARTBEAT).
    #     못 가르는 것을 「가른다」고 적는 것이 이 저장소가 반복해 만난 실패다(D-301).
    try:
        from datetime import timedelta

        Monitor = apps.get_model("stream_monitors", "StreamMonitor")
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        since = _now() - timedelta(hours=24)
        active = list(Monitor._base_manager.filter(is_active=True)
                      .values_list("pk", "code"))
        recent = set(Event._base_manager.filter(occurred_at__gte=since)
                     .values_list("stream_monitor_id", flat=True))
        ever = set(Event._base_manager.values_list("stream_monitor_id", flat=True))
        # ★★ **한 번도 안 울린 카메라와 울리다 멈춘 카메라는 다른 사실이다.**
        #   [실측 2026-09-20] 개발 DB 에서 켜진 40대 중 **39대가 한 번도** 이벤트를 낸
        #   적이 없다(배송 도메인에서 온 `drone_*`). 그 39를 「죽은 카메라」로 세면
        #   경보가 첫날부터 39 로 시작하고, **그 경보는 아무도 안 본다**
        #   (이 파일 머리말: 「더 보면 아무도 안 본다」).
        #   죽은 카메라의 뜻은 **「살아 있던 것이 조용해졌다」**이다.
        silent = [c for pk, c in active if pk in ever and pk not in recent]
        never = [c for pk, c in active if pk not in ever]
        put("cameras_silent_24h", len(silent),
            "켜져 있고 **전에 울린 적 있는데** 24시간 조용한 것: %s — 「죽었다」가 아니라 "
            "**「가서 봐라」**다" % (", ".join(silent[:5]) + ("…" if len(silent) > 5 else "")
                                    or "없음"))
        out["signals"]["cameras_never_seen"] = {
            "value": len(never), "verdict": OK,
            "note": ("켜져 있는 %d대 중 **한 번도 이벤트를 낸 적 없는** 것 — 설치 미완·"
                     "외부 드론일 수 있다. 경보가 아니라 **세어 두는 수**다 (임계 없음)"
                     % len(active))}
    except Exception as exc:
        put("cameras_silent_24h", None, "재지 못했다: %s" % type(exc).__name__)

    # ── 평상 운영 ④ 저장 용량 ─────────────────────────────────────────────
    # 용량 상한은 **환경이 선언한다.** 선언이 없으면 판정 불가다 — 「몇 % 찼나」는
    # 분모 없이 답할 수 없는 질문이고, 분모를 코드가 지어내면 그 추측이 초록이 된다.
    try:
        capacity_gb = float(os.environ.get(STORAGE_CAPACITY_ENV, "") or 0)
    except ValueError:
        capacity_gb = 0
    used_gb, detail = None, ""
    try:
        from django.conf import settings as _s2
        from minio import Minio

        _ep2 = str(getattr(_s2, "MINIO_ENDPOINT", "") or "")
        for _scheme in ("http://", "https://"):
            if _ep2.startswith(_scheme):
                _ep2 = _ep2[len(_scheme):]
        _b2 = getattr(_s2, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        _c2 = Minio(_ep2.rstrip("/"), access_key=_s2.MINIO_ACCESS_KEY,
                    secret_key=_s2.MINIO_SECRET_KEY,
                    secure=bool(getattr(_s2, "MINIO_USE_HTTPS", False)))
        total = sum(o.size or 0 for o in _c2.list_objects(_b2, recursive=True))
        used_gb = round(total / (1024 ** 3), 4)
        detail = "버킷 %s 객체 합계 %.4fGB" % (_b2, used_gb)
    except Exception as exc:
        detail = "저장소 사용량을 못 셌다: %s" % type(exc).__name__
    out["signals"]["storage_used_gb"] = {
        "value": used_gb, "verdict": OK if used_gb is not None else UNKNOWN,
        "note": detail}
    if used_gb is None or capacity_gb <= 0:
        out["signals"]["storage_used_pct"] = {
            "value": None, "verdict": UNKNOWN,
            "note": ("용량 상한이 선언되지 않았다(%s) — **분모 없이 「몇 %% 찼나」에 답하지 "
                     "않는다**(D-301)" % STORAGE_CAPACITY_ENV)
                    if capacity_gb <= 0 else detail}
    else:
        put("storage_used_pct", round(used_gb / capacity_gb * 100, 2),
            "상한 %.0fGB (%s 가 선언)" % (capacity_gb, STORAGE_CAPACITY_ENV))
    return out


def self_test() -> int:
    """★ 출생 표본 — **못 잰 것을 초록으로 세지 않는가** (D-301)."""
    checks = [
        ("★ 출생표본 — 못 잰 값(None)은 UNKNOWN 이다. 초록이 아니다",
         judge("db_ping_ms", None) == UNKNOWN),
        ("임계값을 넘으면 ALARM", judge("db_ping_ms", 5000) == ALARM),
        ("임계값 안이면 OK", judge("db_ping_ms", 12) == OK),
        ("0 은 못 잰 것이 아니다 — 0 은 OK 다", judge("unsent_deliveries", 0) == OK),
        ("임계값이 없는 신호는 OK 로 둔다", judge("무명신호", 1) == OK),
        ("★ 임계값마다 사유가 있다 — 적을 수 없는 임계값은 임계값이 아니다",
         all(len(note) > 10 for _limit, note in THRESHOLDS.values())),
        ("신호가 셋 이상이다 (살아있나·밀리나·채워지나)", len(THRESHOLDS) >= 3),
        # ★ 2026-09-20 (차선 E) — 새 신호 둘의 **음성 갈래**를 함께 둔다.
        ("★ 조용한 카메라 한 대는 경보다 — 「몇 대까지는 괜찮다」가 없다",
         judge("cameras_silent_24h", 1) == ALARM),
        ("조용한 카메라 0대는 정상이다", judge("cameras_silent_24h", 0) == OK),
        ("★ 용량 상한이 없으면 **판정 불가**다 — 분모 없이 %는 없다",
         judge("storage_used_pct", None) == UNKNOWN),
        ("80% 를 넘으면 경보", judge("storage_used_pct", 80.1) == ALARM),
        # ── P-65 감사 쓰기 지연 — **양성과 음성을 함께** (2026-09-05 · 턴 F) ──
        ("★ 감사 큐 지연이 5분을 넘으면 경보 — 턴 E 의 사흘을 이 줄이 잡는다",
         judge("audit_queue_lag_sec", 300.1) == ALARM),
        ("정확히 5분은 아직 경보가 아니다 — 경계를 못박는다",
         judge("audit_queue_lag_sec", 300) == OK),
        ("★ **음성 대조** — 밀린 것이 없으면 지연 0이고 초록이다. 조용한 밤은 장애가 아니다",
         judge("audit_queue_lag_sec", 0.0) == OK),
        ("감사 큐를 **못 쟀으면** 판정 불가다 — 브로커에 못 닿은 것은 0건이 아니다",
         judge("audit_queue_lag_sec", None) == UNKNOWN),
    ]
    # ── 큐 이름과 지연 셈 — **순수 함수를 따로 시험한다** (브로커 없이) ─────
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "backend"))
        from common import audit_queue as _aq

        names = _aq.queue_names("default", list(range(10)))
        checks += [
            ("★ 우선순위 큐 이름을 전수로 만든다 — `default` 하나만 재면 언제나 0이다",
             len(names) == 10 and names[0] == "default"
             and names[9] == "default9"),
            ("우선순위 0 에는 접미가 붙지 않는다 (kombu 규칙)",
             "default0" not in names),
            ("★ 밀린 것이 0건이면 지연은 0이다 — 지어내지 않는다",
             _aq.judge_lag(0, 0, 99999)[0] == 0.0),
            ("★ 밀린 것이 있고 쓰는 속도가 있으면 나눗셈이다 — 120건 ÷ 60건/분 = 120초",
             _aq.judge_lag(120, 60.0, 5)[0] == 120.0),
            ("★★ **턴 E 의 사흘** — 12,468건이 밀렸고 아무것도 안 쓰였다 → 하한을 적는다",
             _aq.judge_lag(12468, 0.0, 259200)[0] == 259200.0),
            ("브로커에 못 닿으면 **못 쟀다**(None)이지 0이 아니다 (D-301)",
             _aq.judge_lag(None, 1.0, 1)[0] is None),
            ("밀린 것이 있는데 속도도 마지막 쓰기도 못 쟀으면 **못 쟀다**",
             _aq.judge_lag(5, 0.0, None)[0] is None),
        ]
    except Exception as exc:                       # noqa: BLE001
        checks.append(("감사 큐 순수 함수를 **못 불렀다**: %s" % exc, False))
    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[OPS-MONITOR] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_ALARM if bad else EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="경보용 — 0 정상 / 1 경보 / 2 판정 불가")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    report = collect()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[OPS-MONITOR] [입력] 신호 %d개 · %s"
              % (len(report["signals"]), report["measured_at"]))
        for name, row in report["signals"].items():
            limit = (THRESHOLDS.get(name) or (None, ""))[0]
            print("  %-7s %-22s %-10s %s"
                  % (row["verdict"], name, row["value"],
                     ("한계 %s · " % limit if limit is not None else "") + (row["note"] or "")))

    verdicts = [row["verdict"] for row in report["signals"].values()]
    if ALARM in verdicts:
        print("[OPS-MONITOR] ★ 경보 — %d개 신호가 한계를 넘었다"
              % sum(1 for v in verdicts if v == ALARM))
        return EXIT_ALARM if args.check else EXIT_OK
    if UNKNOWN in verdicts:
        print("[OPS-MONITOR] 판정 불가 %d개 — **못 잰 것은 초록이 아니다**(D-301)"
              % sum(1 for v in verdicts if v == UNKNOWN))
        return EXIT_UNKNOWN if args.check else EXIT_OK
    print("[OPS-MONITOR] 전 신호 정상")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
