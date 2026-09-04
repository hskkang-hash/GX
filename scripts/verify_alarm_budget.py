#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""QA-12 — **[시험]이 건수를 내는가** (2026-09-04 · 차선 Q).

    "규칙 저장 전 [시험]이 최근 7일 이벤트로 시간당 알림 수를 시뮬레이션한다.
     지금 [시험]은 판정만 보여 주고 **건수를 안 보여 준다.** 관제요원 1인당 시간당
     6건을 넘으면 빨강이 아닌 **주황** 경고. 상한 6은 EEMUA 191 [인용]이다."
                                        — 지시서 §2 Q행 · PRD v2.5 ⑤

무엇을 재는가 — **다섯 수**
---------------------------
    ① 판정 문장에 **수가 실려 있는가**   ← 이 절의 전부다
    ② 상한이 **EEMUA 191 인용**인가 (우리가 지은 수가 아니다)
    ③ 상한을 넘으면 **주황**인가 (빨강이 아니다 · ISA-101)
    ④ 상한 **아래**는 조용한가 (부작위 — 주황이 매번 뜨면 그 색이 무뎌진다)
    ⑤ 시뮬레이션이 **아무것도 남기지 않는가** (규칙·발송 이력 증가 0)

★ ①이 왜 전부인가 — **판정만 있는 [시험]은 지금 것과 같다**
------------------------------------------------------------
「이 규칙은 팀장에게 갑니다」는 이미 나온다. 나오지 않는 것은 **「그리고 시간당
40건입니다」** 이고, 그 한 줄이 없어서 규칙 하나가 알림 폭주를 만들 때까지 아무도
모른다. 그래서 이 판정기는 등급이 아니라 **문장 안의 수**를 본다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/verify_alarm_budget.py
    python scripts/verify_alarm_budget.py --self-test    # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 인용된 상한. **읽어 온다** — 아래 `collect` 가 커널에서 가져오고, 못 가져올 때만
#: 이 값을 마지막 그물로 쓴다. 여기서 복사한 것이 어긋나면 판정기는 엉뚱한 수를 잰다.
FALLBACK_LIMIT = 6.0

#: 판정 문장에 반드시 있어야 하는 출처. 문장에서 이것이 사라지면 다음 사람은 6을
#: **우리 수**로 읽고, 우리 수는 불편할 때 올라간다.
CITATION_TOKEN = "EEMUA 191"

#: 「수가 실려 있다」의 술어. 숫자가 한 개라도 있으면 통과가 아니다 —
#: 「상한 6건」의 6만 있고 **실제 건수가 없는** 문장이 정확히 지금 상태이기 때문이다.
#: 그래서 소수점을 가진 실측 수를 요구한다(`40.3건` · `0.1건`).
_NUMBER_IN_SENTENCE = re.compile(r"\d+\.\d+\s*건")


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔 이유는 시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list:
    """다섯 수를 판정한다. `(이름, 통과, 사유)`.

    ★ `None` 은 **못 쟀다**이지 거짓이 아니다 (D-301).
    """
    out: list = []

    headline = counts.get("headline")
    if headline is None:
        out.append(("판정 문장에 건수", False, "**못 쟀다** — [시험]을 못 불렀다"))
    else:
        has = bool(_NUMBER_IN_SENTENCE.search(str(headline)))
        out.append(("판정 문장에 건수", has,
                    f"「{headline}」" + ("" if has else
                                        " — **수가 없다.** 판정만 있는 [시험]은 지금 "
                                        "것과 같고, 규칙 하나가 폭주를 만들 때까지 "
                                        "아무도 모른다")))

    citation = counts.get("citation")
    limit = counts.get("limit")
    if citation is None or limit is None:
        out.append(("상한은 인용이다", False, "**못 쟀다** — 커널에서 상수를 못 읽었다"))
    else:
        ok = CITATION_TOKEN in str(citation) and float(limit) == FALLBACK_LIMIT
        out.append(("상한은 인용이다", ok,
                    f"{limit:g}건/시간 · 출처 「{citation}」" + ("" if ok else
                     f" — 출처에 {CITATION_TOKEN} 이 없거나 값이 {FALLBACK_LIMIT:g} 이 "
                     f"아니다. 우리가 지은 수는 불편할 때 올라간다")))

    level = counts.get("over_level")
    if level is None:
        out.append(("초과는 주황이다", False, "**못 쟀다**"))
    else:
        out.append(("초과는 주황이다", level == "orange",
                    f"{level}" + ("" if level == "orange" else
                                  " — 빨강은 critical 등급 전용이다(ISA-101). 예산 "
                                  "초과에 빨강을 쓰면 진짜 위험의 빨강이 무뎌진다")))

    level = counts.get("under_level")
    if level is None:
        out.append(("상한 아래는 조용하다 (부작위)", False, "**못 쟀다**"))
    else:
        out.append(("상한 아래는 조용하다 (부작위)", level == "ok",
                    f"{level}" + ("" if level == "ok" else
                                  " — 조용한 규칙에도 주황을 칠하면 그 색이 곧 "
                                  "배경이 되고, 진짜 폭주가 안 보인다")))

    left = counts.get("wrote_rows")
    if left is None:
        out.append(("아무것도 안 남긴다", False, "**못 쟀다**"))
    else:
        out.append(("아무것도 안 남긴다", left == 0,
                    "규칙·발송 이력 증가 0건" if left == 0 else
                    f"{left}행이 늘었다 — 재는 행위가 재는 대상을 바꾼다. "
                    f"[시험]은 **저장 전에** 재는 자리다"))
    return out


def self_test() -> int:
    """판정 규칙을 스스로 시험한다. **Django 없이 돈다** (D-277 · D-350).

    ★ **출생 표본** (D-310) — 이 판정기를 만들게 한 사례는 합성이 아니다.
      [실측 등재 2026-09-24 · PRD v2.5 ⑤ · ga_readiness QA-12]
      *"규칙 저장 전 [시험](DA-03 §3-3)은 **판정만 보여 주고 건수를 안 보여 준다.**"*
      그 상태의 문장이 아래 `birth` 다 — 「팀장에게 갑니다」. 등급도 있고 수신자도
      맞는데 **건수가 없다.** 첫 갈래가 그 문장에서 빨강을 내지 못하면 이 판정기는
      자기가 태어난 이유를 못 보는 것이다.
    """
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    # ── 출생 표본 — 판정은 있고 **건수가 없는** 문장 ──────────────────────
    birth = dict(headline="이 규칙은 팀장 역할에게 갑니다 (수신자 3명)",
                 citation="EEMUA 191 — Alarm Systems", limit=6.0,
                 over_level="orange", under_level="ok", wrote_rows=0)
    if names(judge(birth)).get("판정 문장에 건수"):
        bad.append("**출생 표본**(판정만 있고 건수가 없는 [시험] 문장)을 통과로 "
                   "읽는다 — 이 판정기가 태어난 이유를 못 본다 (D-310)")

    # ── 함정: 「상한 6건」만 있고 실측 수가 없는 문장 ─────────────────────
    trap = dict(birth, headline="EEMUA 191 권고 상한 6건을 넘습니다")
    if names(judge(trap)).get("판정 문장에 건수"):
        bad.append("상한의 6만 있고 **실측 건수가 없는** 문장을 통과로 읽는다 — "
                   "이 함정이 이 판정기의 술어가 소수점을 요구하는 이유다")

    # ── 초록 표본 ────────────────────────────────────────────────────────
    green = dict(headline="이 규칙은 시간당 40.3건을 보냅니다 — EEMUA 191 권고 상한 6건",
                 citation="EEMUA 191 — Alarm Systems: A Guide to Design, Management "
                          "and Procurement",
                 limit=6.0, over_level="orange", under_level="ok", wrote_rows=0)
    got = names(judge(green))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── 음성 갈래 ────────────────────────────────────────────────────────
    for key, value, expect_red in (
        ("over_level", "red", "초과는 주황이다"),
        ("over_level", "ok", "초과는 주황이다"),
        ("under_level", "orange", "상한 아래는 조용하다 (부작위)"),
        ("wrote_rows", 1, "아무것도 안 남긴다"),
        ("limit", 8.0, "상한은 인용이다"),
        ("citation", "우리가 정한 운영 기준", "상한은 인용이다"),
    ):
        sample = dict(green, **{key: value})
        if names(judge(sample)).get(expect_red):
            bad.append(f"{key}={value!r} 인데 「{expect_red}」를 통과로 읽는다")

    # ── 못 쟀다 ≠ 거짓 ──────────────────────────────────────────────────
    rows = judge(dict(green, headline=None))
    hit = [(n, ok, why) for (n, ok, why) in rows if n == "판정 문장에 건수"][0]
    if hit[1] or "못 쟀다" not in hit[2]:
        bad.append("[시험]을 **못 불렀는데** 통과로 읽거나 사유에 그 사실이 없다 (D-301)")

    if bad:
        print("[QA12] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[QA12] 자기시험 통과 — 출생 표본 1 · 함정 1 · 초록 표본 1 · 음성 6 · 판정 불가 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측 — **되돌리는 트랜잭션 안에서** 상한 위·아래를 둘 다 만든다
# ═══════════════════════════════════════════════════════════════════════════
class _Rollback(Exception):
    """되돌리기 위해 일부러 던지는 예외. 성공 경로에서 던진다."""


def collect() -> dict:
    """지금 있는 이벤트로 재고, 상한 **위**의 표본은 되돌리는 트랜잭션에서 만든다.

    ★ 상한 위를 재려면 7일에 1000건 넘는 표본이 필요하다. 개발 DB 에 그만큼 심어 두면
      다음 사람의 화면이 가짜 폭주로 덮인다. 그래서 심고 재고 **되돌린다** —
      되돌리지 못하면 그 자리에서 회색(exit 2)이지 초록이 아니다.
    """
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from datetime import timedelta

    from django.apps import apps
    from django.core.cache import cache
    from django.db import transaction
    from django.utils import timezone

    from common.tenant_scope import TenantScope
    from kernels.k2_notify import (BUDGET_WINDOW_DAYS,
                                   EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
                                   simulate_alarm_budget)

    # 캐시 처리: **비움** — 예산은 「지금까지 몇 건이 왔나」이고, 과거의 답이 오면
    # 그 답은 틀린 것이 아니라 질문에 답한 것이 아니다 (P-19).
    try:
        cache.clear()
        cache_note = "비움"
    except Exception as exc:                             # noqa: BLE001
        cache_note = f"못 비웠다({type(exc).__name__})"

    Event = apps.get_model("stream_monitors", "DetectionEvent")
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    Rule = apps.get_model("stream_monitors", "NotificationRule")
    Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
    UserGroup = apps.get_model("user", "UserGroup")

    out = {
        "cache_note": cache_note,
        "limit": EEMUA_191_ALARMS_PER_OPERATOR_HOUR,
        "window_days": BUDGET_WINDOW_DAYS,
        "citation": None, "headline": None,
        "over_level": None, "under_level": None, "wrote_rows": None,
        "events_in_window": None, "group_used": None, "rolled_back": False,
    }

    now = timezone.now()
    since = now - timedelta(days=BUDGET_WINDOW_DAYS)
    out["events_in_window"] = Event._base_manager.filter(
        occurred_at__gte=since, occurred_at__lte=now).count()

    group = UserGroup.objects.order_by("pk").first()
    if group is None:
        print("[QA12] 테넌트(UserGroup)가 하나도 없다 — 예산을 잴 대상이 없다. "
              "**판정 불가**이지 0건이 아니다 (D-301)")
        return out
    out["group_used"] = f"{group.pk}:{group.name}"

    scope = TenantScope.system(
        reason="QA-12 판정기 — 저장 전 시뮬레이션. 되돌리는 트랜잭션이다")
    marker = f"gx-qa12-probe-{int(now.timestamp())}"
    before = (Rule._base_manager.count(), Delivery._base_manager.count())

    try:
        with transaction.atomic():
            # ── 상한 **아래** — 지금 있는 것 그대로 (부작위 갈래) ──────────
            quiet = simulate_alarm_budget(scope=scope, severity="critical",
                                          group=group, now=now)
            out["citation"] = quiet.citation
            out["under_level"] = quiet.level

            # ── 상한 **위** — 표본을 심고 재고 되돌린다 ────────────────────
            cams = [
                Stream._base_manager.create(
                    name=f"{marker}-{i}", code=f"{marker}-{i}",
                    ip_source="rtsp://probe.invalid/x", is_active=True)
                for i in range(10)
            ]
            need = int(EEMUA_191_ALARMS_PER_OPERATOR_HOUR * BUDGET_WINDOW_DAYS * 24) + 60
            rows = [
                Event(stream_monitor=cams[i % len(cams)], event_type="fire",
                      severity="critical",
                      occurred_at=now - timedelta(minutes=(i % 9500) + 1),
                      snapshot_path="")
                for i in range(need)
            ]
            Event._base_manager.bulk_create(rows, batch_size=500)
            for row in Event._base_manager.filter(stream_monitor__in=cams):
                _own(row, group)
            for cam in cams:
                _own(cam, group)

            loud = simulate_alarm_budget(scope=scope, severity="critical",
                                         group=group, now=now)
            out["headline"] = loud.headline
            out["over_level"] = loud.level
            out["wrote_rows"] = ((Rule._base_manager.count() - before[0])
                                 + (Delivery._base_manager.count() - before[1]))
            print(f"[QA12]   상한 아래: {quiet.headline}")
            print(f"[QA12]   상한 위(되돌림): {loud.headline}")
            raise _Rollback
    except _Rollback:
        pass

    ghosts = Stream._base_manager.filter(code__startswith=marker).count()
    out["rolled_back"] = ghosts == 0
    if ghosts:
        print(f"[QA12] ⚠ 되돌리지 못했다 — 합성 카메라 {ghosts}대가 남아 있다")
    return out


def _own(row, group):
    """소유를 붙인다. 커널의 판단기를 그대로 쓴다 (D-212)."""
    from kernels.k1_event.services import _owner_field

    if _owner_field(type(row)) == "groups":
        row.groups.set([group])
    else:
        row.group = group
        row.save(update_fields=["group"])



def _refuse_if_shared_master(labels, fail):
    """★ 쓰기 전에 **공용 마스터인지 묻는다** (D-270 ③).

    이 도구는 재기 위해 행을 심고 되돌린다. 심는 표가 **공용 마스터**라면 그 행은
    되돌리기 전까지 **전 테넌트 화면에 뜬다** — 측정이 남의 관제에 얼룩을 남긴다.
    등록부(`tests/tenant_classification.py`)가 그 분류의 **유일한 출처**다 —
    판정식을 복사하지 않는다(D-212).

    ⚠ 못 읽으면 **통과시키지 않는다**: 「검사 못함」과 「대상 아님」은 다른 사실이다(D-301).
    """
    #: ★ 이름으로 못 찾으면 **파일로 찾는다.** 컨테이너는 `/repo` 와 `/app`(=backend)이
    #:   **따로** 마운트돼 `tests` 가 이름 공간에 없다 — 저장소가 이미 아는 함정이다
    #:   (`capture_screens._screens_dir` 이 같은 이유로 자리를 하나로 안 박는다).
    #:   그래도 **못 찾으면 통과시키지 않는다**: 「검사 못함」≠「대상 아님」(D-301).
    SHARED_MASTERS = None
    try:
        from tests.tenant_classification import SHARED_MASTERS
    except ImportError:
        import importlib.util

        here = Path(__file__).resolve().parent.parent
        for cand in (here / "backend" / "tests" / "tenant_classification.py",
                     Path("/app") / "tests" / "tenant_classification.py"):
            if not cand.is_file():
                continue
            spec = importlib.util.spec_from_file_location("_tenant_classification", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            SHARED_MASTERS = mod.SHARED_MASTERS
            break
    if SHARED_MASTERS is None:
        fail("분류 등록부(tests/tenant_classification.py)를 이름으로도 파일로도 읽지 "
             "못했다 — 공용 마스터인지 확인하지 못한 채로 쓰지 않는다 (D-270 ③ · D-301)")
        return
    for label in labels:
        if label in SHARED_MASTERS:
            fail(f"{label} 이 분류 등록부에서 **공용 마스터**다. 측정용 행을 공용 표에 "
                 f"심으면 되돌리기 전까지 전 테넌트가 그것을 본다")

def main() -> int:
    ap = argparse.ArgumentParser(
        description="QA-12 알림 예산 시뮬레이션 — [시험]이 건수를 내는가")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="수를 JSON 으로도 낸다")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    # ★ 여기서부터 **쓴다.** 쓰기 전에 분류 등록부에 묻는다 (D-270 ③) —
    #   못 읽으면 멈춘다. 자기시험은 아무것도 안 쓰므로 그 앞에 두지 않는다:
    #   등록부를 못 읽는 호스트에서도 판정 규칙 시험은 돌아야 한다.
    _refuse_if_shared_master(
        ("stream_monitors.DetectionEvent", "stream_monitors.NotificationRule"),
        lambda why: (_ for _ in ()).throw(SystemExit("[분류] " + why)))


    try:
        counts = collect()
    except Exception as exc:                             # noqa: BLE001
        print(f"[QA12] **판정 불가** — 환경을 세우지 못했다: {type(exc).__name__}: {exc}")
        print("[QA12] 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    print(f"[QA12] [입력] 최근 {counts['window_days']}일 이벤트 "
          f"{counts['events_in_window']}건 · 테넌트 {counts['group_used']} · "
          f"인용 상한 {counts['limit']:g}건/시간")
    print(f"[QA12] 캐시 처리: {counts['cache_note']} — 시뮬레이션은 ORM 으로 직접 "
          f"센다 (P-19)")
    if counts["group_used"] is None:
        print("[QA12] **판정 불가** — 잴 테넌트가 없다 (D-301)")
        return EXIT_UNDECIDABLE
    if not counts["rolled_back"]:
        print("[QA12] **회색(exit 2)** — 되돌리지 못했다. 판정기가 남긴 사실 위에서 "
              "낸 초록은 초록이 아니다")
        return EXIT_UNDECIDABLE

    rc = EXIT_OK
    for (name, ok, why) in judge(counts):
        print(f"[QA12] {'  ' if ok else 'X '}{name:22} {why}")
        if not ok:
            rc = EXIT_FAIL
    if args.json:
        print("[QA12] JSON " + json.dumps(counts, ensure_ascii=False, sort_keys=True,
                                          default=str))
    print("[QA12] " + ("통과 — [시험]이 건수를 내고, 초과는 주황이다"
                       if rc == EXIT_OK else
                       "실패 — 위의 X 가 아직 비어 있는 자리다"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
