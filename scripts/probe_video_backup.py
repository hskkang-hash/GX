#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""영상 백업 실측 **발판** — 재 볼 것을 만들고, 재고, 치운다 (D-356 · D-384 ③).

왜 이 스크립트가 필요한가
-------------------------
`ops_backup.py` · `ops_restore.py` 는 **이미 있다**(D-354 ①). 두 턴 동안 「미측정」으로
남은 이유는 도구가 없어서가 아니라 **잴 것이 없어서**였다 — 클립 0건 · MinIO 미도달.

    [실측 2026-09-12] `MINIO_ENDPOINT=minio.invalid` · `MINIO_ACCESS_KEY=dummy`
    → 이름 풀이부터 실패한다. **닿지 못한 이유는 설정이었다** (D-384 ③ 그대로).

그래서 이 스크립트가 하는 일은 **측정 발판**이다: 이벤트에 묶인 객체를 몇 개 만들고,
`ops_backup` 이 그것을 뜨게 하고, `ops_restore` 가 **해시로** 되살려 보게 한 뒤,
**만든 것을 전부 치운다.**

    ★ 이것은 「시험용 데이터를 넣어 초록을 만든다」가 아니다. 재는 대상은 **도구**이지
      데이터가 아니다 — 백업이 이벤트 묶음을 골라내는가, 복구가 바이트를 되살리는가.
      그 둘은 데이터가 있어야만 물어볼 수 있는 질문이고, 없으면 영원히 「미측정」이다.

    ★ 만든 것에는 전부 `PROBE_TAG` 가 붙는다. 치우기가 실패해도 **무엇이 남았는지
      이름으로 안다** — 조용히 섞이는 것이 가장 나쁘다.

    python scripts/probe_video_backup.py --seed      # 발판 놓기
    python scripts/probe_video_backup.py --clean     # 치우기 (몇 번 불러도 안전)
    python scripts/probe_video_backup.py --report    # 지금 상태만 본다

되돌림: `--clean` 이 만든 것만 지운다. `PROBE_TAG` 가 없는 행·객체는 손대지 않는다.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

#: 이 스크립트가 만든 것에만 붙는 표. **지울 때의 유일한 근거**다.
PROBE_TAG = "gxprobe-D384"

#: 몇 개를 만드나. 셋이면 「하나만 맞았다」와 「전부 맞았다」가 구별된다.
N_CLIPS = 3

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _django():
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.apps import apps
    return apps


def _minio():
    from minio import Minio
    ep = os.environ.get("MINIO_ENDPOINT", "")
    bucket = os.environ.get("MINIO_BUCKET_NAME", "")
    if not ep or not bucket:
        raise RuntimeError("MINIO_ENDPOINT / MINIO_BUCKET_NAME 이 비었다 — "
                           "이것이 D-384 ③ 이 말한 ㉢(설정 빔)이다")
    c = Minio(ep.replace("http://", "").replace("https://", ""),
              access_key=os.environ.get("MINIO_ACCESS_KEY", ""),
              secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
              secure=ep.startswith("https"))
    if not c.bucket_exists(bucket):
        c.make_bucket(bucket)
    return c, bucket


# ---------------------------------------------------------------------------
# 분류 등록부 참조 (D-270 ③) — **주인 없는 행을 만들지 않는다**
# ---------------------------------------------------------------------------
def _assert_owned(label: str, group_id) -> None:
    """이 스크립트가 쓰는 모델이 **소유가 필요한 모델인가**를 등록부에 묻는다.

    ★ 형식적으로 등록부를 import 하는 것이 아니다. 이 스크립트는 시험 데이터를
      심었다가 지우는데, **심는 순간 주인이 없으면** 그 행은 어느 테넌트에도 안 보이거나
      (읽기 격리) 모두에게 보인다(공용 마스터로 오인). 둘 다 나쁘고, 둘의 차이가
      바로 `SHARED_MASTERS` 와 `TENANT_UNASSIGNED` 다.

    등록부가 「공용도 아니고 주인 없음도 아니다」라고 말하면 **group 이 반드시 있어야 한다.**
    """
    sys.path.insert(0, "/app")
    try:
        from tests.tenant_classification import SHARED_MASTERS, TENANT_UNASSIGNED
    except ImportError:                       # 등록부를 못 읽으면 **판정 불가**다
        raise RuntimeError(
            "분류 등록부(tests/tenant_classification.py)를 못 읽었다 — "
            "소유가 필요한지 모르는 채로 쓰지 않는다 (D-270 ③)")
    if label in SHARED_MASTERS or label in TENANT_UNASSIGNED:
        return                                 # 등록부가 「주인 없어도 된다」고 말한다
    if not group_id:
        raise RuntimeError(
            f"{label} 은 등록부에서 공용 마스터도 미배정 선언도 아니다 — "
            f"**소유(group)가 있어야 한다.** 주인 없이 심으면 그 행은 격리 판정에서 "
            f"「공용」과 구별되지 않는다 (D-270 ③)")


def seed() -> int:
    apps = _django()
    client, bucket = _minio()
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    EC = apps.get_model("stream_monitors", "EventClip")

    from django.contrib.auth import get_user_model

    from common.tenant_filters import get_user_group

    # 소유를 아무 데서나 집어오지 않는다 — **처음 만들어진 소속** 하나를 쓰고,
    # 그 사실을 출력에 적는다. 「어느 테넌트에 심었나」를 모르면 지울 때도 모른다.
    Group = apps.get_model("user", "UserGroup")
    group = Group._base_manager.order_by("pk").first()
    if group is None:
        raise RuntimeError("UserGroup 이 한 건도 없다 — 심을 소속이 없다")
    gid = group.pk
    _ = (get_user_model, get_user_group)

    _assert_owned("stream_monitors.StreamMonitor", gid)
    _assert_owned("stream_monitors.DetectionEvent", gid)
    _assert_owned("stream_monitors.EventClip", gid)

    monitor, _ = SM._base_manager.get_or_create(
        code=f"{PROBE_TAG}-CAM",
        defaults=dict(name=f"{PROBE_TAG} 측정용 카메라", ip_source="127.0.0.1",
                      is_active=False, is_visualize=False, order=9999,
                      is_external=False, address_source="", group_id=gid),
    )
    #: ★ [턴 AD · 차선 B · P-224 발급 순간] `--clean` 이 실패하거나 안 불리면 이 행은
    #:   `get_or_create` 라 다음 회에도 그대로 남는다 — 남으면 `data_source` 기본값
    #:   `live` 위에 청구된다(billing_marks.py 발급 순간 규약). 소급이 아니라 **여기서**
    #:   판다 — 태어나는 순간에 표식이 없으면 다음 청구 회차가 그대로 센다.
    from common.billing_marks import PROBE_MARKER, mark_unbillable
    mark_unbillable(monitor, PROBE_MARKER.split("=", 1)[1],
                     reason="probe_video_backup.py seed() — OPS-04 백업 실측 발판 카메라")
    now = datetime.now(timezone.utc)
    event = DE._base_manager.create(
        stream_monitor=monitor, event_type=f"{PROBE_TAG}", severity="info",
        occurred_at=now, snapshot_path="", status="new", address_status="pending",
        group_id=gid,
    )

    made = []
    for i in range(N_CLIPS):
        key = f"{PROBE_TAG}/clip-{i}.bin"
        # ★ 영상 파일을 흉내 내되 **실제 영상은 넣지 않는다** (D-347 ④ · D-306 반출 규약).
        #   재는 것은 바이트가 왕복하는가이지 그것이 영상인가가 아니다.
        blob = (f"{PROBE_TAG} clip {i} ".encode() * 512)
        client.put_object(bucket, key, io.BytesIO(blob), len(blob))
        EC._base_manager.create(
            event=event, object_key=key, start_offset=float(i),
            duration=5.0, clip_status="referenced", group_id=gid,
        )
        made.append({"key": key, "bytes": len(blob)})

    print(json.dumps({
        "seeded": True, "bucket": bucket, "event_id": event.id,
        "monitor_id": monitor.id, "group_id": gid, "clips": made,
        "retention_days_hint": 90,
    }, ensure_ascii=False, indent=2))
    return 0


def clean() -> int:
    apps = _django()
    SM = apps.get_model("stream_monitors", "StreamMonitor")
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    EC = apps.get_model("stream_monitors", "EventClip")

    removed_objects = 0
    try:
        client, bucket = _minio()
        for obj in client.list_objects(bucket, prefix=f"{PROBE_TAG}/", recursive=True):
            client.remove_object(bucket, obj.object_name)
            removed_objects += 1
    except Exception as exc:                       # noqa: BLE001
        # 객체를 못 지운 것은 **못 지웠다고 적는다.** 조용히 0으로 넘기지 않는다.
        print(f"[PROBE] 객체 정리 실패: {type(exc).__name__} {exc}", file=sys.stderr)

    clips = EC._base_manager.filter(object_key__startswith=f"{PROBE_TAG}/")
    n_clips = clips.count()
    clips.delete()
    events = DE._base_manager.filter(event_type=PROBE_TAG)
    n_events = events.count()
    events.delete()
    monitors = SM._base_manager.filter(code__startswith=PROBE_TAG)
    n_mon = monitors.count()
    monitors.delete()

    print(json.dumps({
        "cleaned": True, "objects": removed_objects,
        "clips": n_clips, "events": n_events, "monitors": n_mon,
    }, ensure_ascii=False, indent=2))
    return 0


def report() -> int:
    apps = _django()
    EC = apps.get_model("stream_monitors", "EventClip")
    total = EC._base_manager.exclude(object_key="").count()
    probe = EC._base_manager.filter(object_key__startswith=f"{PROBE_TAG}/").count()
    out = {"event_bound_clips_total": total, "of_which_probe": probe}
    try:
        client, bucket = _minio()
        objs = list(client.list_objects(bucket, recursive=True))
        out["bucket"] = bucket
        out["objects_in_bucket"] = len(objs)
        out["bytes_in_bucket"] = sum(int(o.size or 0) for o in objs)
        out["reachable"] = True
    except Exception as exc:                       # noqa: BLE001
        out["reachable"] = False
        out["unreachable_reason"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="영상 백업 측정 발판 (D-384 ③)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--seed", action="store_true")
    g.add_argument("--clean", action="store_true")
    g.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.seed:
        return seed()
    if a.clean:
        return clean()
    return report()


if __name__ == "__main__":
    sys.exit(main())
