#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""probe 표식 — **게이트용 씨앗 사건은 매 회 생성 · 판정 뒤 표시 · 다음 표본에서 제외** (P-156 · P-159 ② · 턴 T · 차선 Q).

왜 있나
------
게이트(`capture_screens` · `verify_click_completes`)는 잴 사건이 있어야 잰다. 그래서 씨앗을 심는다.
그런데 심은 씨앗이 다음 회의 표본에 섞이면, 그 회의 수는 **제품이 아니라 지난 회의 씨앗**을 잰 수다
(턴 S: 캡처 직후 4/39 — 판정기가 씨앗 번호를 못박아 생긴 거짓 빨강). 그래서 셋을 규약으로 못박는다:

    ① 씨앗은 **매 회 새로** 심는다 (`capture_screens.seed_events` — K1 생성 경로를 지난 진짜 행)
    ② 판정이 끝나면 그 사건에 `data_source=probe` 를 **표시**한다 (이 모듈 `mark`)
    ③ 다음 회의 표본은 표시된 사건을 **제외**한다 (이 모듈 `exclude` / `is_probe`)

표식을 어디에 두나 — [실측 2026-09-17 · `backend/stream_monitors/models.py` `DetectionEvent`]
------------------------------------------------------------------------------------------
`data_source` 는 **열이 아니다.** `apps/dsm/services.py:211 event_data_source` 가 훈련 창(감사)으로 **계산**해
`drill`/`live` 를 낸다 — 열을 만들면 과거가 비고 「빈 과거 = 훈련 아님」으로 읽힌다고 그 함수가 스스로 적었다.
그래서 **모델을 고치지 않는다.** 이벤트의 기존 자유 칸 가운데 화면이 그리지 않고(`frontend/src` 에 `track_id` 0건)
길이가 넉넉하며(64자) K1 생성 경로가 받는(`record_detection(track_id=…)`) 칸이 하나 있다 — **`track_id`** 다.
규약 문자열을 거기 넣는다:

    data_source=probe;run=<RUN_STAMP>            심을 때 (씨앗이 어느 회의 것인지)
    data_source=probe;run=<RUN_STAMP>;judged=1   판정 뒤 (표본에서 뺄 것)

⚠ `reject_reason` 은 사람이 읽는 칸(오탐 사유)이라 쓰지 않는다. `bbox` 는 JSON 이지만 검출 좌표라 뜻이 다르다.

HTTP 쪽 필터 — 목록 문(`GET /api/dsm/events`)은 `track_id` 를 **내지 않는다** [실측 `apps/dsm/api.py:244-252`].
그래서 HTTP 로 고르는 게이트(`verify_click_completes` 드라이버)는 **씨앗 카메라 이름**(`stream_monitor_name` 이
`PROBE_TAG` 로 시작)으로 가른다 — 씨앗은 전부 그 카메라 한 대에 심기므로(`seed_events`) 같은 집합이다.
`is_probe` 가 두 표식을 다 본다: `track_id` 가 있으면 그것을, 없으면 카메라 이름을.

이번 회의 씨앗은 남긴다 — `exclude(records, keep_ids=[이번에 심은 id])`. 지난 회의 것만 빠진다.

쓰는 법
------
    python scripts/probe_marks.py --self-test          # 순수 함수 (Django 없이 · 호스트에서 돈다)
    docker exec gx-shell python /repo/scripts/probe_marks.py --list      # DB 의 표시된 사건 (gx-shell)
    docker exec gx-shell python /repo/scripts/probe_marks.py --mark 123 124 --run 20260917T1300

종료 코드: 0 통과 · 1 실패 · 2 판정 불가(Django 없음 등)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAG = "[PROBE]"

#: 게이트가 만든 것에 붙는 표. `capture_screens.PROBE_TAG` 가 **여기서 가져간다** — 두 벌로 두지 않는다.
PROBE_TAG = "gxprobe-D384-screen"

#: 규약 문자열의 머리. 이 뒤에 `;run=…` `;judged=1` 이 붙는다.
MARK = "data_source=probe"

#: `DetectionEvent.track_id` 는 `max_length=64` 다 [실측 models.py]. 넘기면 DB 가 자른다 — 자른 표식은 표식이 아니다.
TRACK_ID_MAX = 64


def run_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%dT%H%M%S")


def mark_string(run_id: str, *, judged: bool = False) -> str:
    """규약 문자열. **길이를 여기서 검사한다** — 넣는 쪽마다 검사하면 한 곳이 빠진다."""
    s = "%s;run=%s" % (MARK, run_id)
    if judged:
        s += ";judged=1"
    if len(s) > TRACK_ID_MAX:
        raise ValueError("probe 표식이 %d자 — track_id 상한 %d자를 넘는다: %r" % (len(s), TRACK_ID_MAX, s))
    return s


def parse_mark(track_id) -> dict | None:
    """`data_source=probe;run=X;judged=1` → {"run": "X", "judged": True}. 표식이 아니면 `None`."""
    if not isinstance(track_id, str) or not track_id.startswith(MARK):
        return None
    out = {"run": None, "judged": False}
    for part in track_id.split(";")[1:]:
        k, _, v = part.partition("=")
        if k == "run":
            out["run"] = v
        elif k == "judged":
            out["judged"] = v == "1"
    return out


def is_probe(rec) -> bool:
    """이 기록이 probe 사건인가. `track_id` 표식 **또는** 씨앗 카메라 이름 — 둘 중 하나면 참.

    `rec` 는 dict(HTTP 응답 한 줄) 이거나 속성 객체(ORM 행)다. 없는 칸은 없는 것으로 본다.
    """
    def _get(name):
        if isinstance(rec, dict):
            return rec.get(name)
        return getattr(rec, name, None)

    if parse_mark(_get("track_id")) is not None:
        return True
    for name in ("stream_monitor_name", "stream_monitor_code"):
        v = _get(name)
        if isinstance(v, str) and v.startswith(PROBE_TAG):
            return True
    sm = _get("stream_monitor")
    code = getattr(sm, "code", None) if sm is not None and not isinstance(sm, (int, str)) else None
    return isinstance(code, str) and code.startswith(PROBE_TAG)


def exclude(records, *, keep_ids=()) -> list:
    """표본에서 probe 사건을 뺀다. **이번 회의 씨앗(`keep_ids`)은 남긴다.**

    ★ 빼는 쪽이 아니라 남기는 쪽을 명시한다 — 「이번 것」을 모르면 전부 뺀다. 그러면 이번 회의
      표본이 0건이 되고, 0건은 판정기가 회색으로 적는다(분모 0 인 초록은 초록이 아니다).
    """
    keep = {int(k) for k in keep_ids}
    out = []
    for r in records:
        eid = r.get("event_id") if isinstance(r, dict) else getattr(r, "event_id", getattr(r, "pk", None))
        if is_probe(r) and (eid is None or int(eid) not in keep):
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# 씨앗 명세 파이프 — **id 를 넘기는 자리는 하나다** (P-170 ② · 턴 U · 차선 Q)
#
#   턴 T 의 오판(D-487 ②)이 여기였다: 씨앗 id 배선을 옮겨 놨는데 `capture_screens` 가
#   씨앗을 **스스로 지워** 넘길 id 가 없었다. 규약을 둘로 못박는다:
#     ① `capture_screens` 는 씨앗을 **지우지 않는다**(`--keep-seeds` 기본).
#     ② 심은 것의 명세를 `P-157/runs/<RUN_STAMP>/seed.json` 에 쓴다.
#   읽는 쪽(`verify_click_completes` · `verify_feature_reach` · `measure_onboarding_t`)은
#   `--seed-file` 로 그 파일을 읽고, 안 주면 **runs/ 의 최신**을 읽는다.
#
#   ⚠ 「최신」은 **디렉터리 이름(시각)** 으로 고른다 — 파일 mtime 으로 고르면 git 체크아웃이
#     전부 같은 시각으로 만들어 놓은 뒤 아무 회차나 최신이 된다.
# ---------------------------------------------------------------------------
#: `scripts/` 의 부모 = 저장소 뿌리. `runs/` 는 P-157 아래다(P-157 README 의 표 그대로).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(_ROOT, "docs", "agent", "evidence", "P-157", "runs")
SEED_FILE_NAME = "seed.json"


def latest_seed_file(runs_dir: str | None = None):
    """`runs/` 에서 **가장 나중 회차**의 `seed.json` 경로. 없으면 None."""
    base = runs_dir or RUNS_DIR
    if not os.path.isdir(base):
        return None
    stamps = sorted(d for d in os.listdir(base)
                    if os.path.isfile(os.path.join(base, d, SEED_FILE_NAME)))
    if not stamps:
        return None
    return os.path.join(base, stamps[-1], SEED_FILE_NAME)


def load_seed(path=None, runs_dir: str | None = None) -> dict:
    """씨앗 명세를 읽는다 — **없으면 빈 벌**이다(없는 것은 없는 것이다 · D-301).

    돌려주는 벌에는 언제나 다음이 있다:
      `event_ids`(list[int]) · `first_event_id` · `probe_mark` · `run` · `seeded_at`
      · `severity_by_id`(dict) · `source`(읽은 파일 경로 또는 "") · `why`(못 읽은 사유)

    ★ **지어내지 않는다.** 파일이 없으면 `event_ids` 는 빈 목록이고, 부르는 쪽은 그것을
      회색으로 적어야 한다 — 빈 씨앗으로 잰 초록은 분모 0 인 초록이다.
    """
    empty = {"event_ids": [], "first_event_id": None, "probe_mark": "", "run": "",
             "seeded_at": "", "severity_by_id": {}, "address": {}, "source": "", "why": ""}
    p = path or latest_seed_file(runs_dir)
    if not p:
        empty["why"] = "씨앗 명세가 없다 — capture_screens 를 --keep-seeds(기본)로 먼저 돌린다"
        return empty
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception as exc:                            # noqa: BLE001
        empty["source"] = str(p)
        empty["why"] = "씨앗 명세를 못 읽었다(%s) — 깨진 파일로 재지 않는다" % type(exc).__name__
        return empty
    ids = [int(x) for x in (doc.get("event_ids") or [])]
    sev = {}
    for e in (doc.get("events") or []):
        try:
            sev[int(e.get("event_id"))] = e.get("severity") or ""
        except (TypeError, ValueError):
            continue
    return {"event_ids": ids,
            "first_event_id": doc.get("first_event_id") or (ids[0] if ids else None),
            "probe_mark": doc.get("probe_mark") or "",
            "run": doc.get("run") or "",
            "seeded_at": doc.get("seeded_at") or "",
            "severity_by_id": sev,
            "address": doc.get("address") or {},
            "events": doc.get("events") or [],
            "source": str(p),
            "why": "" if ids else "씨앗 명세는 있는데 event_ids 가 비었다"}


# ---------------------------------------------------------------------------
# ORM 쪽 — gx-shell 안에서만 돈다
# ---------------------------------------------------------------------------
def _django():
    #: gx-shell 은 `/app` = host `backend` 마운트다 — `capture_screens._django` 와 같은 줄 (`/repo/scripts` 에서 부르면 이 줄이 없어 못 올린다 [실측 12:43]).
    if os.path.isdir("/app") and "/app" not in sys.path:
        sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    from django.apps import apps
    if not apps.ready:
        django.setup()
    return apps


def mark(event_ids, run_id: str, *, judged: bool = True) -> int:
    """판정 뒤 표시. 돌려주는 값은 **실제로 갱신된 행 수**다 — 요청한 수가 아니다.

    분류 등록부(`backend/tests/tenant_classification.py` · D-270 ③): `DetectionEvent` 는
    테넌트 자료(SHARED_MASTERS 도 TENANT_UNASSIGNED 도 아니다) — 이 쓰기는 `track_id` 한 칸이고
    **판정기가 심은 probe 사건에만** 닿는다(`pk__in=ids` · ids 는 `seed_events` 가 낸 것).
    """
    apps = _django()
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    ids = [int(i) for i in event_ids]
    if not ids:
        return 0
    return DE._base_manager.filter(pk__in=ids).update(track_id=mark_string(run_id, judged=judged))


def list_marked() -> list[dict]:
    """표시된 사건 전부(표식 + 씨앗 카메라). 화면·표본이 아니라 **점검용**이다."""
    apps = _django()
    DE = apps.get_model("stream_monitors", "DetectionEvent")
    from django.db.models import Q
    qs = (DE._base_manager
          .filter(Q(track_id__startswith=MARK) | Q(stream_monitor__code__startswith=PROBE_TAG))
          .select_related("stream_monitor").order_by("pk"))
    out = []
    for e in qs:
        pm = parse_mark(e.track_id) or {}
        out.append({"event_id": e.pk, "track_id": e.track_id,
                    "camera": getattr(e.stream_monitor, "code", None),
                    "run": pm.get("run"), "judged": bool(pm.get("judged")),
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None})
    return out


# ---------------------------------------------------------------------------
# 자기시험 — 출생 표본. 이 필터가 **실제로 무엇을 빼고 무엇을 남기는지** 여기서 보인다.
# ---------------------------------------------------------------------------
def self_test() -> int:
    bad = []
    stamp = "20260917T130000"

    # ① 표식 문자열 왕복
    s = mark_string(stamp)
    if parse_mark(s) != {"run": stamp, "judged": False}:
        bad.append("표식 왕복이 안 된다: %r" % s)
    if parse_mark(mark_string(stamp, judged=True)) != {"run": stamp, "judged": True}:
        bad.append("judged 표식 왕복이 안 된다")
    if len(s) > TRACK_ID_MAX:
        bad.append("표식이 track_id 상한을 넘는다")
    try:
        mark_string("x" * 80)
        bad.append("80자 run_id 인데 멈추지 않았다 — 잘린 표식은 표식이 아니다")
    except ValueError:
        pass
    if parse_mark("live") is not None or parse_mark(None) is not None:
        bad.append("표식 아닌 값을 표식으로 읽는다")

    # ② HTTP 한 줄(목록 문 — track_id 없음): 카메라 이름으로 가른다
    live = {"event_id": 1, "stream_monitor_name": "동문 카메라"}
    seed_old = {"event_id": 2, "stream_monitor_name": PROBE_TAG + " 캡처용 카메라"}
    seed_now = {"event_id": 3, "stream_monitor_name": PROBE_TAG + " 캡처용 카메라"}
    marked = {"event_id": 4, "stream_monitor_name": "동문 카메라", "track_id": mark_string(stamp, judged=True)}
    if is_probe(live) or not is_probe(seed_old) or not is_probe(marked):
        bad.append("is_probe 가 셋 중 하나를 잘못 본다")
    got = [r["event_id"] for r in exclude([live, seed_old, seed_now, marked], keep_ids=[3])]
    if got != [1, 3]:
        bad.append("exclude 가 [1, 3] 이 아니라 %r 을 남겼다 — 이번 씨앗은 남고 지난 씨앗·표시된 것은 빠져야 한다" % got)
    # ③ keep 을 안 주면 씨앗은 전부 빠진다 — 그것이 「모르면 뺀다」다
    got = [r["event_id"] for r in exclude([live, seed_old, seed_now, marked])]
    if got != [1]:
        bad.append("keep 없이 exclude 했는데 %r — 씨앗이 남았다" % got)
    # ④ 속성 객체(ORM 행 흉내)도 같은 답
    class Row:
        def __init__(self, pk, code, track_id=None):
            self.event_id, self.track_id = pk, track_id
            self.stream_monitor = type("SM", (), {"code": code})()
    rows = [Row(10, "CAM-1"), Row(11, PROBE_TAG + "-CAM"), Row(12, "CAM-2", mark_string(stamp))]
    got = [r.event_id for r in exclude(rows, keep_ids=[12])]
    if got != [10, 12]:
        bad.append("ORM 행 흉내에서 %r — dict 와 답이 다르다" % got)

    # ⑤ [P-170 ② · 턴 U] 씨앗 명세 파이프 — **없으면 빈 벌 · 최신은 이름으로 고른다**
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        if latest_seed_file(td) is not None:
            bad.append("빈 runs/ 인데 최신 씨앗을 찾았다고 한다")
        got = load_seed(runs_dir=td)
        if got["event_ids"] or not got["why"]:
            bad.append("씨앗이 없는데 빈 벌·사유를 안 낸다 (없는 것은 없는 것이다)")
        for st, ids in (("20260918T090000", [11, 12]), ("20260918T100000", [21, 22])):
            os.makedirs(os.path.join(td, st))
            with open(os.path.join(td, st, SEED_FILE_NAME), "w", encoding="utf-8") as fh:
                json.dump({"run": st, "probe_mark": mark_string(st),
                           "event_ids": ids, "first_event_id": ids[0],
                           "seeded_at": "2026-09-18T09:00:00",
                           "events": [{"event_id": ids[0], "severity": "critical"},
                                      {"event_id": ids[1], "severity": "warning"}]},
                          fh, ensure_ascii=False)
        got = load_seed(runs_dir=td)
        if got["event_ids"] != [21, 22] or got["run"] != "20260918T100000":
            bad.append("최신 회차를 안 고른다: %r" % got["event_ids"])
        if got["first_event_id"] != 21 or got["severity_by_id"].get(21) != "critical":
            bad.append("씨앗의 첫 id·severity 를 못 읽는다")
        if parse_mark(got["probe_mark"]) != {"run": "20260918T100000", "judged": False}:
            bad.append("씨앗 명세의 표식이 probe 표식 규약과 어긋난다")
        # 명시한 회차를 주면 그것을 읽는다 (최신이 아니어도)
        old = load_seed(os.path.join(td, "20260918T090000", SEED_FILE_NAME))
        if old["event_ids"] != [11, 12]:
            bad.append("--seed-file 로 준 회차를 안 읽는다")
        # 깨진 파일은 **빈 벌 + 사유**다 — 깨진 것으로 재지 않는다
        os.makedirs(os.path.join(td, "20260918T110000"))
        with open(os.path.join(td, "20260918T110000", SEED_FILE_NAME), "w",
                  encoding="utf-8") as fh:
            fh.write("{not json")
        got = load_seed(runs_dir=td)
        if got["event_ids"] or "못 읽었다" not in got["why"]:
            bad.append("깨진 씨앗 명세를 읽고도 사유 없이 넘어간다")

    for b in bad:
        print("%s 자기시험 실패 — %s" % (TAG, b))
    print("%s 자기시험 %s (표본 4 · 판정 9 + 씨앗 파이프 8 = 17)" % (TAG, "실패" if bad else "통과"))
    return EXIT_FAIL if bad else EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="probe 표식 — mark · list · exclude (P-156)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true", help="DB 의 probe 사건 (gx-shell)")
    ap.add_argument("--mark", nargs="*", type=int, help="판정 뒤 표시할 event_id 들 (gx-shell)")
    ap.add_argument("--run", default=None, help="표식에 적을 회차 (기본: 지금 시각)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.list or args.mark is not None:
        try:
            _django()
        except Exception as exc:                        # noqa: BLE001
            print("%s 판정 불가 — Django 를 못 올렸다(%s). gx-shell 에서 부른다" % (TAG, type(exc).__name__))
            return EXIT_UNDECIDABLE
        if args.mark is not None:
            n = mark(args.mark, args.run or run_stamp())
            print("%s 표시 %d/%d건" % (TAG, n, len(args.mark)))
        if args.list:
            rows = list_marked()
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            print("%s probe 사건 %d건" % (TAG, len(rows)))
        return EXIT_OK
    ap.print_help()
    return EXIT_UNDECIDABLE


if __name__ == "__main__":
    sys.exit(main())
