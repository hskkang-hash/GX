#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-20 시드 구멍 둘이 **실제로 메워졌는가** — 네 수를 잰다 (2026-09-22 · 차선 E2).

    "강제 도구: 시드 뒤 「발송 기록 N>0 · 스냅샷 객체 N>0 · MinIO 목록과 DB 참조 수 일치 ·
     시스템 이벤트 2」 [실측]"  — RESUME_NEXT 2026-09-22 §1 P-20

왜 판정기가 따로 있는가 — **심었다와 채워졌다는 다른 사실이다**
--------------------------------------------------------------
시드 명령이 끝에 찍는 수는 **자기가 방금 한 일**을 센 것이다. 그 수는 "내가 20번
불렀다"를 말하지 "지금 DB 와 저장소에 20이 있다"를 말하지 않는다. 둘이 갈리는 자리가
셋이나 있다:

  · 중복 억제(F-04)로 접힌 이벤트는 **부른 횟수보다 적게** 남는다
  · 발송 억제(K2 5분)로 접힌 알림은 **행을 만들지 않는다** — 옳은 동작이지만
    그 결과 「보냈다고 셌는데 행이 없다」가 된다
  · MinIO 객체는 DB 밖에 있다. 업로드가 조용히 실패해도 **DB 는 초록**이다

그래서 이 판정기는 **시드를 안 부르고** 지금 있는 것만 센다. 시드가 죽어도, 시드를
지우고 다시 심어도, 이 수는 언제나 「지금 이 환경에 무엇이 있는가」다.

★ **③은 목록 대조다.** 「스냅샷 참조 20건」과 「객체 20개」가 각각 20이어도 서로 다른
  20일 수 있다. 그래서 참조가 가리키는 **객체 이름 하나하나**가 목록에 있는지 본다 —
  수만 견주면 고아 객체와 깨진 참조가 서로를 가려 준다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
        -e MINIO_ENDPOINT=minio:9000 -e MINIO_ACCESS_KEY=… -e MINIO_SECRET_KEY=… \
        gx-shell python /repo/scripts/verify_seed_p20.py
    python scripts/verify_seed_p20.py --self-test        # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경·자격증명 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 씨앗의 표. 시드 명령과 **같은 값**을 봐야 한다 — 여기서 복사한 것이 어긋나면
#: 판정기는 아무것도 없는 곳을 세고 「0건」이라 말한다. 그래서 아래 `collect` 는
#: 커맨드 모듈에서 **읽어 온다**. 이 상수는 그것을 못 읽었을 때의 마지막 그물이다.
FALLBACK_SEED_CODE = "GX-SEED-DSM"

#: 기대값. P-20 이 정한 수다. 「2」만 정확한 수이고 나머지 둘은 **0보다 크면 된다** —
#: 몇 장이 옳은지는 지시서가 정하지 않았고, 정하지 않은 수를 판정기가 지어내지 않는다.
EXPECT_SYSTEM_EVENTS = 2


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔 이유는 시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list[tuple[str, bool, str]]:
    """네 수를 판정한다. `(이름, 통과, 사유)` 넷을 돌려준다.

    ★ `None` 은 **못 쟀다**이지 0 이 아니다 (D-301). 못 잰 칸은 통과가 아니고,
      그 사실이 사유에 남는다 — 「검사 못함」과 「0건 검사」를 가른다.
    """
    out: list[tuple[str, bool, str]] = []

    n = counts.get("deliveries")
    if n is None:
        out.append(("발송 기록", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("발송 기록", n > 0,
                    f"{n}행" + ("" if n > 0 else " — 규칙이 없거나 그 역할에 사람이 "
                                               "0명이다. M1(내게 온 이벤트)이 빈 화면이 된다")))

    n = counts.get("snapshot_refs")
    if n is None:
        out.append(("스냅샷 참조", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("스냅샷 참조", n > 0,
                    f"{n}건" + ("" if n > 0 else " — W2 상세의 스냅샷 자리가 영원히 비어 있다")))

    missing = counts.get("missing_objects")
    orphans = counts.get("orphan_objects")
    objects = counts.get("objects")
    if objects is None or missing is None:
        out.append(("MinIO 목록 ↔ DB 참조", False,
                    "**못 쟀다** — 저장소에 닿지 못했다(0건과 구별한다 · D-301)"))
    else:
        ok = not missing and not orphans
        why = f"객체 {objects}개 · 참조 {counts.get('snapshot_refs')}건"
        if missing:
            why += (f" · **참조가 가리키는데 없는 객체 {len(missing)}개** "
                    f"{missing[:3]} — 화면이 깨진 이미지를 띄운다")
        if orphans:
            why += (f" · **아무도 안 가리키는 객체 {len(orphans)}개** "
                    f"{orphans[:3]} — 지워도 되는지 아무도 모른다")
        if ok:
            why += " · 하나하나 이름으로 대조했다"
        out.append(("MinIO 목록 ↔ DB 참조", ok, why))

    n = counts.get("system_events")
    if n is None:
        out.append(("시스템 이벤트", False, "**못 쟀다** — DB 에 닿지 못했다"))
    else:
        out.append(("시스템 이벤트", n == EXPECT_SYSTEM_EVENTS,
                    f"{n}건 (기대 {EXPECT_SYSTEM_EVENTS})" +
                    ("" if n == EXPECT_SYSTEM_EVENTS
                     else " — W1 「시스템」 프리셋이 빈 목록을 그린다")))

    #: ★★ [턴 AD · 차선 Q · P-251 · 세종 결정 공백을 메움] 「씨앗은 청구·KPI 분모에서
    #:   뺀다」(P-237 낱말 밭) 게이트 술어 — `data_source=seed` 사건이 청구
    #:   (`kernels.k1_event.count_events` 가 쓰는 `exclude_unbillable`) 뒤에도
    #:   **남는가**. 분모는 씨앗 사건 수(런타임) — **손으로 안 넣는다**.
    #:   ⚠ 씨앗 사건이 0건이면 잴 표본이 없다 — 그 상태를 초록으로 적지 않는다
    #:   (분모 0 인 초록은 초록이 아니다 · D-301). 이 판정은 다른 4수와 같은 칸
    #:   (`seed_events`)을 분모로 쓴다 — 두 번째 분모를 새로 만들지 않는다(D-212).
    n_seed = counts.get("seed_events")
    leak = counts.get("seed_billable_leak")
    if n_seed is None or leak is None:
        out.append(("P-251 씨앗은 청구·KPI 0건", False,
                    "**못 쟀다** — DB 에 닿지 못했다(청구 셈 exclude_unbillable 을 "
                    "못 불렀다)"))
    elif n_seed == 0:
        out.append(("P-251 씨앗은 청구·KPI 0건", False,
                    "씨앗 사건이 **0건**이다 — 분모 0, 잴 표본이 없다(회색에 가깝다 · "
                    "D-301). 초록으로 적지 않는다 — 시드를 심은 뒤 다시 잰다"))
    else:
        ok = leak == 0
        out.append(("P-251 씨앗은 청구·KPI 0건", ok,
                    f"씨앗 {n_seed}건 중 청구 셈(`count_events` 의 "
                    f"`exclude_unbillable`)에 **남은 것 {leak}건**" +
                    ("" if ok else
                     " — data_source=seed 사건이 청구·월간 KPI 로 샌다(P-251). "
                     "씨앗 카메라(`GX-SEED-DSM`)는 `track_id` 표식도 없고 "
                     "`StreamMonitor.data_source` 도 기본값 `live` 그대로다(D-514) "
                     "— exclude_unbillable 의 세 갈래(㉠㉡㉢) 중 어느 것도 걸지 "
                     "않는다")))
    return out


def self_test() -> int:
    """판정 규칙을 스스로 시험한다. **Django 없이 돈다** (D-277 · D-350)."""
    bad: list[str] = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    # ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 사례는 합성이 아니다.
    #   [실측 2026-09-22] 착수 전 개발 DB 를 같은 도구로 재니 네 수가 이랬다:
    #       발송 기록 0 · 스냅샷 참조 0 · 객체 0 · 시스템 이벤트 0
    #   화면(모바일 M1)은 그 위에 지어질 참이었고, **빈 화면이 「데이터가 없다」인지
    #   「기능이 죽었다」인지 아무도 못 가르는 상태**였다. 아래 초록 표본은 시드 뒤의
    #   실측값(120·20·20·2)이고, 그 바로 뒤 음성 갈래들이 **착수 전의 0** 을 그대로 판정한다.
    #   즉 이 자기시험의 양·음 두 갈래가 **그날의 전후**다.
    green = dict(deliveries=120, snapshot_refs=20, objects=20,
                 missing_objects=[], orphan_objects=[], system_events=2,
                 seed_events=20, seed_billable_leak=0)
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 채워진 표본을 통과로 읽지 못한다: {got}")

    # ── 음성 갈래 — 하나씩 무너뜨린다 ────────────────────────────────────
    for key, value, expect_red in (
        ("deliveries", 0, "발송 기록"),
        ("snapshot_refs", 0, "스냅샷 참조"),
        ("system_events", 0, "시스템 이벤트"),
        ("system_events", 3, "시스템 이벤트"),   # 많아도 틀린 수다
    ):
        sample = dict(green, **{key: value})
        if names(judge(sample)).get(expect_red):
            bad.append(f"{key}={value} 인데 「{expect_red}」를 통과로 읽는다")

    # ── ★ P-251 출생 표본 — **씨앗이 청구로 새고 있었다** ─────────────────
    #    [실측 2026-09-22 · 코드] 씨앗 카메라(`GX-SEED-DSM`)는 `track_id` 표식도
    #    없고 `StreamMonitor.data_source` 도 기본값 `live` 그대로다(D-514) —
    #    `exclude_unbillable` 의 세 갈래 중 어느 것도 이 카메라의 사건을 걸지
    #    않는다. 그 상태(새는 채로 심어졌다)가 빨강이어야 한다.
    leaking = dict(green, seed_billable_leak=20)
    if names(judge(leaking)).get("P-251 씨앗은 청구·KPI 0건"):
        bad.append("**P-251 출생 표본** — 씨앗 20건이 전부 청구 셈에 남았는데(0건 "
                   "빠짐) 통과로 읽는다 — 씨앗이 청구로 새는 상태를 놓친다")
    partial_leak = dict(green, seed_billable_leak=1)
    if names(judge(partial_leak)).get("P-251 씨앗은 청구·KPI 0건"):
        bad.append("씨앗 1건만 새도(일부 유출) 통과로 읽는다 — 0이어야 통과다")
    # ── ★ 분모 0 — 씨앗이 아직 없다. 초록으로 적지 않는다 ────────────────
    no_seed = dict(green, seed_events=0, seed_billable_leak=0)
    if names(judge(no_seed)).get("P-251 씨앗은 청구·KPI 0건"):
        bad.append("씨앗 사건 0건(분모 0)인데 통과(초록)로 읽는다 — 분모 0인 초록은 "
                   "초록이 아니다 (D-301 · P-251 지시)")
    # ── 못 쟀다 ≠ 0 ────────────────────────────────────────────────────
    unmeasured_leak = dict(green, seed_billable_leak=None)
    hit = [(n, ok, why) for (n, ok, why) in judge(unmeasured_leak)
           if n == "P-251 씨앗은 청구·KPI 0건"][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("청구 셈을 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다 "
                   "(D-301)")

    # ── ★ 이 판정기가 있는 이유 — **수는 같은데 이름이 다른 경우** ───────
    #   객체 20 · 참조 20 이지만 서로 다른 20 이다. 수만 견주는 판정은 초록이다.
    crossed = dict(green, missing_objects=["detections/1/x.jpg"],
                   orphan_objects=["detections/1/y.jpg"])
    if names(judge(crossed)).get("MinIO 목록 ↔ DB 참조"):
        bad.append("수는 같고 **이름이 다른** 표본을 통과로 읽는다 — 이 판정기가 "
                   "수 대조가 아니라 목록 대조인 이유가 그것이다")

    # ── 못 쟀다 ≠ 0 ─────────────────────────────────────────────────────
    unknown = dict(green, objects=None, missing_objects=None)
    rows = judge(unknown)
    hit = [(n, ok, why) for (n, ok, why) in rows if n == "MinIO 목록 ↔ DB 참조"][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("저장소를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")

    if bad:
        print("[P20] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[P20] 자기시험 통과 — 초록 표본 1 · 음성 4 + 이름 어긋남 1 + 판정 불가 1 "
          "+ P-251 출생 표본 1 · 일부 유출 1 · 분모 0 1 · 판정 불가 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **시드를 부르지 않는다.** 지금 있는 것만 센다
# ═══════════════════════════════════════════════════════════════════════════
def collect() -> dict:
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps

    try:
        from stream_monitors.management.commands.seed_dsm_events import (
            SEED_CODE, SEED_RULE_CHANNEL, SYSTEM_SCENARIOS,
        )
        system_types = [t for (t, _s, _l) in SYSTEM_SCENARIOS]
    except Exception as exc:                             # noqa: BLE001
        print(f"[P20] ⚠ 시드 커맨드에서 표를 못 읽었다: {type(exc).__name__}: {exc} — "
              f"마지막 그물로 상수를 쓴다(값이 갈리면 0건이 나온다)")
        SEED_CODE, SEED_RULE_CHANNEL = FALLBACK_SEED_CODE, "log"
        system_types = ["camera_down", "storage_high"]

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    Rule = apps.get_model("stream_monitors", "NotificationRule")

    rows = Event._base_manager.filter(stream_monitor__code=SEED_CODE)
    refs = list(rows.exclude(snapshot_path="").values_list("snapshot_path", flat=True))
    out = {
        "seed_events": rows.count(),
        "rules": Rule._base_manager.filter(channels=[SEED_RULE_CHANNEL]).count(),
        "deliveries": Delivery._base_manager.filter(event__in=rows).count(),
        "snapshot_refs": len(refs),
        "system_events": rows.filter(event_type__in=system_types).count(),
        "objects": None, "missing_objects": None, "orphan_objects": None,
        "seed_billable_leak": None,
    }

    #: ★★ [P-251] 씨앗 사건이 **청구 셈(`exclude_unbillable`) 뒤에도 남는가**.
    #:   읽기만 한다 — `common/billing_marks.py` 는 B 소유, 여기서는 부르기만
    #:   한다(§0.4 와 같은 결의: 읽기·호출만). `kernels.k1_event.count_events` 와
    #:   같은 두 겹(청구 표식 + 소프트 삭제)을 씨앗 행에만 좁혀 그대로 적용한다 —
    #:   판정식을 다시 쓰지 않는다(D-212). 청구·월간 KPI(K6 `usage_snapshot`)는
    #:   둘 다 이 한 함수(`exclude_unbillable`)를 거친다 — 갈라져 있지 않다.
    if out["seed_events"] > 0:
        try:
            from common.billing_marks import exclude_soft_deleted, exclude_unbillable

            seed_ids = list(rows.values_list("pk", flat=True))
            billable = exclude_unbillable(Event._base_manager.all())
            billable = exclude_soft_deleted(billable, Event)
            out["seed_billable_leak"] = billable.filter(
                pk__in=seed_ids).distinct().count()
        except Exception as exc:                             # noqa: BLE001
            print(f"[P20] ⚠ 청구 셈(exclude_unbillable)을 못 불렀다: "
                  f"{type(exc).__name__}: {exc}")

    # ── 저장소 — **목록으로 대조한다** ───────────────────────────────────
    cam = apps.get_model("stream_monitors", "StreamMonitor")._base_manager.filter(
        code=SEED_CODE).first()
    if cam is None:
        print("[P20] 씨앗 카메라가 없다 — 시드가 아직 안 심겼다")
        return out
    try:
        from stream_monitors.services.detection_snapshot import PREFIX
        from stream_monitors.utils.minio_client import minio_client
    except Exception as exc:                             # noqa: BLE001
        print(f"[P20] MinIO 클라이언트를 못 가져왔다: {type(exc).__name__}: {exc}")
        return out
    if not getattr(minio_client, "available", False) or minio_client.client is None:
        print("[P20] MinIO 가 사용 불가다 — **판정 불가**(빈 것과 닿은 것은 다르다)")
        return out
    try:
        bucket = minio_client.bucket_name
        listed = {o.object_name for o in minio_client.client.list_objects(
            bucket, prefix=f"{PREFIX}/{cam.pk}/", recursive=True)}
    except Exception as exc:                             # noqa: BLE001
        print(f"[P20] 객체 목록을 못 읽었다: {type(exc).__name__}: {exc}")
        return out

    #: 참조는 `"{bucket}/{object}"` 로 저장된다(`upload_snapshot` 참조).
    wanted = {r.split("/", 1)[1] for r in refs if "/" in r}
    out["objects"] = len(listed)
    out["missing_objects"] = sorted(wanted - listed)
    out["orphan_objects"] = sorted(listed - wanted)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="P-20 시드 네 수 (2026-09-22)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="수를 JSON 으로도 낸다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    try:
        counts = collect()
    except Exception as exc:                             # noqa: BLE001
        print(f"[P20] **판정 불가** — 환경을 세우지 못했다: {type(exc).__name__}: {exc}")
        print("[P20] 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    print(f"[P20] [입력] 시드 이벤트 {counts['seed_events']}건 · "
          f"알림 규칙 {counts['rules']}건")
    rc = EXIT_OK
    for (name, ok, why) in judge(counts):
        print(f"[P20] {'  ' if ok else '✗ '}{name:22} {why}")
        if not ok:
            rc = EXIT_FAIL
    if args.json:
        print("[P20] JSON " + json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print("[P20] " + ("통과 — P-20 네 수가 전부 섰다" if rc == EXIT_OK else
                      "실패 — 위의 ✗ 가 아직 비어 있는 자리다"))
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    #: [턴 AD · 차선 Q · P-251] 다섯째 수를 더했다 — 씨앗은 청구·KPI 분모에서 빼야
    #: 한다(P-237). 분모는 `judge()` 가 매번 재는 다섯 수 이름 그대로다. 씨앗 사건
    #: **전수**(런타임)는 `[P20]` 줄에 그대로 찍힌다 — 0건이면 그 갈래는 회색에
    #: 가깝게 적는다(초록으로 안 적는다 · 위 judge() 참고).
    gate_header(
        __file__,
        measured=("시드 뒤 다섯 수(발송·스냅샷·MinIO 목록↔DB·시스템 이벤트·P-251 "
                  "청구·KPI 0건) — **분모 5개**(`judge()` 가 매 실행마다 재는 수 · "
                  "지금 셌다). 씨앗 사건 전수는 gx-shell 안에서 재고 `[P20]` 줄에 "
                  "그대로 찍힌다 — 0건이면 초록으로 적지 않는다"),
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    sys.exit(main())
