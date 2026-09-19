#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-184 — 게이트가 만든 probe 사건을 **지우지 않고 세지 않는다**.

세종 P-184:
    씨앗 찌꺼기 — 삭제는 대표. 지우기 전까지 probe 사건에 `data_source=probe` 표기
    + 큐·인계·온보딩 **측정에서 제외**(필터). 지우지 않고 세지 않는다.
    대표 승인 뒤 순서 ㉠지움 ㉡재심 ㉢잼.

★ 여기는 **한 곳**이다. 세는 법을 차선마다 따로 쓰면 어긋나고, 어긋난 쪽이 조용히 이긴다.
  probe 를 거르는 모든 자리는 이 파일의 `is_probe_track()` 하나만 부른다.

★ **새 문을 만들지 않는다.** 조율자 선등록 턴 W ㉢ 이 못 박았다 — 표기하는 새 제품 면을
  만들면 그건 「지우지 않고 세지 않기」가 아니라 새 쓰기 면이고 **빨강**이다.
  표기는 이미 행 안에 있다(`track_id`), 우리가 할 일은 **세는 쪽**이다.

★ 표기가 `track_id` 에 얹혀 있는 것은 **우리가 고른 것이 아니라 발견한 것**이다.
  `DetectionEvent` 에 `data_source` 칸은 없다 — 그것은 의도다(`apps/dsm/services.py`
  `event_data_source`: 「칸이 아니라 **창 판정**이다 … 새 칸이 태어나는 순간 과거가 비고,
  빈 과거는 「훈련이 아니었다」로 읽힌다」). probe 는 훈련(drill)과 달리 **창이 없어서**
  창 판정으로 답할 수 없고, 그래서 만든 쪽이 `track_id` 에 적어 두었다.
  이 얹힘은 **빚**이다. 지우는 날(대표 승인) 같이 갚는다.

제외가 아니라 **분모를 밝히는 것**이 목적이다. 그래서 이 파일은 두 가지로 따로 세고,
둘이 어긋나면 **빨강**을 낸다 — 한 가지로만 세면 놓친 것이 조용히 살아 있는다.
"""
from __future__ import annotations

import os
import sys

#: 행 안에 박힌 표식. 만든 쪽(`scripts/probe_*.py`)이 적는다.
PROBE_MARKER = "data_source=probe"

#: 두 번째로 세는 법 — 게이트 전용 카메라 이름. 표식과 **따로** 센다.
PROBE_CAMERA_HINT = "gxprobe"


def is_probe_track(track_id) -> bool:
    """이 행이 게이트가 만든 것인가 — **한 줄짜리 정본**.

    `None`·빈 문자열은 사람이 만든 것으로 본다(모르면 세는 쪽에 둔다 — 빠뜨리는 쪽보다
    낫다: 우리 수가 낮게 나오는 것은 보이지만, 높게 나오는 것은 안 보인다).
    """
    return bool(track_id) and str(track_id).startswith(PROBE_MARKER)


def exclude_probe(qs):
    """queryset 에서 probe 를 뺀다. ORM 이 있는 자리에서만 쓴다."""
    return qs.exclude(track_id__startswith=PROBE_MARKER)


def census() -> dict:
    """지금 몇 건인가 — **두 가지로 따로 세고 대 본다**. Django 가 있어야 한다."""
    from stream_monitors.models import DetectionEvent as E
    from stream_monitors.models import StreamMonitor as S

    by_mark = set(E.objects.filter(track_id__startswith=PROBE_MARKER)
                  .values_list("id", flat=True))
    cams = S.objects.filter(name__icontains=PROBE_CAMERA_HINT)
    by_cam = set(E.objects.filter(stream_monitor__in=cams).values_list("id", flat=True))

    all_ids = sorted(by_mark | by_cam)
    #: ★ 미처리를 세는 법이 **둘**이다. 하나만 내면 다른 하나가 조용히 다른 답을 낸다.
    #:   2026-09-19 실측: `response_state='occurred'` → 5 · `status='new'` → 8.
    return {
        "by_mark": sorted(by_mark),
        "by_cam": sorted(by_cam),
        "only_mark": sorted(by_mark - by_cam),
        "only_cam": sorted(by_cam - by_mark),
        "all": all_ids,
        "total": len(all_ids),
        "open_by_response_state": E.objects.filter(
            id__in=all_ids, response_state="occurred").count(),
        "open_by_status": E.objects.filter(id__in=all_ids, status="new").count(),
        "cameras": sorted(c.name for c in cams),
    }


def self_test() -> list[str]:
    """출생 표본 — **이 판정기가 태어난 날 실제로 있던 행들**로 잰다.

    BIRTH_SAMPLE 은 2026-09-19 17:2x 에 이 데이터베이스에 있던 `track_id` 그대로다.
    표본이 상상이면 자기시험은 자기를 통과시킬 뿐이다.
    """
    BIRTH_SAMPLE = [
        # (track_id, probe 인가)
        ("data_source=probe;run=20260917T084325;judged=1", True),   # 231073 · 첫 무리
        ("data_source=probe;run=20260918T052947;judged=1", True),   # 268494 · 세종이 이름 댄 것
        ("data_source=probe;run=20260919T061925;judged=1", True),   # 274947 · **턴 V 측정 중에 태어났다**
        (None, False),                                              # 사람이 만든 사건 — 표식 없음
        ("", False),                                                # 빈 값도 사람 쪽
        ("data_source=seed;run=x", False),                          # 씨앗은 probe 가 아니다
        ("data_source=drill;run=x", False),                         # 훈련은 창 판정이 따로 본다
        ("track-4471", False),                                      # 진짜 추적 id — 원래 이 칸의 주인
        ("xdata_source=probe", False),                              # 가운데 끼면 아니다(앞에서만 센다)
        ("DATA_SOURCE=PROBE;run=x", False),                         # 대문자는 우리 표식이 아니다
    ]
    bad = []
    for track, want in BIRTH_SAMPLE:
        got = is_probe_track(track)
        if got != want:
            bad.append("자기시험 어긋남: %r -> %s (기대 %s)" % (track, got, want))
    #: 양성 3 · 음성 7 — 양성만 있으면 「전부 probe」라고 답해도 통과한다.
    if sum(1 for _, w in BIRTH_SAMPLE if w) < 2:
        bad.append("자기시험 표본에 양성이 모자라다")
    if sum(1 for _, w in BIRTH_SAMPLE if not w) < 2:
        bad.append("자기시험 표본에 음성이 모자라다")
    return bad


def main() -> int:
    sys.path.insert(0, "/app") if os.path.isdir("/app") else None
    bad = self_test()
    for b in bad:
        print("[PROBE] " + b)
    if bad:
        print("[PROBE] 빨강 — 자기시험이 깨졌다. 아래 수를 믿지 마라")
        return 1
    print("[PROBE] 자기시험 통과 — **출생 표본 10**(양성 3 · 음성 7)")

    if "--census" not in sys.argv:
        return 0

    import django
    django.setup()
    c = census()
    print("[PROBE] [입력] probe 표식으로 %d건 · gxprobe 카메라로 %d건 — **따로 세서 댄다**"
          % (len(c["by_mark"]), len(c["by_cam"])))
    print("[PROBE] 카메라: %s" % ", ".join(c["cameras"]))
    if c["only_mark"] or c["only_cam"]:
        print("[PROBE] 표식에만: %s" % c["only_mark"])
        print("[PROBE] 카메라에만: %s" % c["only_cam"])
        print("[PROBE] 빨강 — 두 가지 세는 법이 어긋난다. 어느 쪽이 정본인지 정하기 전엔 "
              "필터를 믿지 마라")
        return 1
    print("[PROBE] 두 가지가 같다 — probe 사건 **%d건**" % c["total"])
    print("[PROBE] id: %s" % c["all"])
    print("[PROBE] 미처리 — `response_state=occurred` **%d** · `status=new` **%d**"
          % (c["open_by_response_state"], c["open_by_status"]))
    if c["open_by_response_state"] != c["open_by_status"]:
        print("[PROBE] ⚠ 같은 행을 두 칸이 다르게 말한다. 「미처리 N건」을 적을 때는 "
              "**어느 칸으로 셌는지** 같이 적어라 (P-190 · 한 행 한 정본)")
    print("[PROBE] ⚠ 이 수는 **잴 때마다 는다** — 게이트가 사건을 만들기 때문이다. "
          "지우는 것은 대표 결정이다(P-184 ㉠지움 ㉡재심 ㉢잼)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
