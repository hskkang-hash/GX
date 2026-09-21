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

제외가 아니라 **분모를 밝히는 것**이 목적이다.

★★ [2026-09-21 · 턴 Z · 차선 U1] **카메라로 세는 갈래를 폐지했다** (P-201 마무리)
--------------------------------------------------------------------------------
종전 이 파일은 두 가지로 따로 셌다 — ① `track_id` 표식 ② **게이트 전용 카메라 이름**
(`gxprobe`). 둘이 어긋나면 빨강을 냈고, 실제로 빨강이었다(표식 4 · 카메라 8).

그 빨강의 뜻은 「하나를 놓쳤다」가 **아니었다.** 둘째 갈래가 **다른 것을 세고 있었다:**

    [실측 2026-09-21 · 운영 DB] 표식 `data_source=probe` **0건**(대표 결정으로
    씨앗 4건을 지웠다 · `docs/agent/evidence/P-184/deleted_probe_snapshot_20260921.json`).
    그런데 카메라 이름으로 세면 **4건** — 그 4건은 카메라 3947
    (`gxprobe-D384-screen 캡처용 카메라`)에 매달린 **훈련(`data_source=drill`) 사건**이다.

즉 카메라 이름은 **탐침이 아니라 훈련을 세고 있었다.** P-201 이 두 표식을 가른 뒤로
그 갈래는 「probe 를 세는 법」이 아니라 **「그 카메라에 매달린 모든 것을 세는 법」**이 됐고,
그 차이는 조용했다 — 이름이 `gxprobe` 였기 때문이다.

★ **이름은 표식이 아니다.** 표식은 행 안에 있고(`track_id`), 이름은 사람이 짓는 값이다.
  이름으로 세면 ① 이름을 바꾸는 날 수가 바뀌고 ② 같은 카메라로 심은 **다른 종류**
  (훈련·실사건)가 전부 탐침이 된다. ②가 오늘 실제로 일어난 일이다.

그래서 **세는 법은 하나다 — 표식.** 두 가지로 세고 대 보는 안전장치는 잃지만, 그 장치가
지키던 것(놓친 것을 잡는다)은 **두 판정기의 짝맞춤**이 대신 지킨다:
`backend/tests/test_u1_probe_not_counted.py` 가 이 파일과 `common/probe_marker.py` 를
출생 표본 전수로 맞대 본다.

⚠ 빌려 쓰던 곳 하나 — `scripts/measure_onboarding_t.py`(차선 Q)가 이 파일에서
  `PROBE_CAMERA_HINT` 를 **빌려다** HTTP 응답 행을 걸렀다. 그 갈래도 같은 이유로
  틀렸다(훈련을 탐침으로 읽는다). 그 파일은 Q 의 것이라 여기서 고치지 않고
  `docs/agent/checkpoints/turn-z/Q.md` 에 쪽지를 남겼다.
"""
from __future__ import annotations

import os
import sys

#: 행 안에 박힌 표식. 만든 쪽(`scripts/probe_*.py`)이 적는다.
PROBE_MARKER = "data_source=probe"

#: ⛔ **`PROBE_CAMERA_HINT` 는 없앴다** (2026-09-21 · 턴 Z · 머리말 ★★).
#:   이름 하나를 남겨 두면 다음 사람이 그것을 빌려다 다시 이름으로 센다.
#:   세는 법은 위 표식 하나다.


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
    """지금 몇 건인가 — **표식으로만 센다.** Django 가 있어야 한다.

    ★ 세는 법이 하나인 것이 이 함수의 계약이다(머리말 ★★). 둘째 갈래를 다시
      더하고 싶으면 그 갈래가 **무엇을 세는지** 먼저 적어라 — 종전 둘째 갈래는
      「probe」라고 적고 **훈련**을 셌다.
    """
    from stream_monitors.models import DetectionEvent as E

    ids = sorted(E.objects.filter(track_id__startswith=PROBE_MARKER)
                 .values_list("id", flat=True))
    #: ★ 미처리를 세는 법이 **둘**이다. 하나만 내면 다른 하나가 조용히 다른 답을 낸다.
    #:   2026-09-19 실측: `response_state='occurred'` → 5 · `status='new'` → 8.
    return {
        "all": ids,
        "total": len(ids),
        "open_by_response_state": E.objects.filter(
            id__in=ids, response_state="occurred").count(),
        "open_by_status": E.objects.filter(id__in=ids, status="new").count(),
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
    print("[PROBE] [입력] **표식 하나로 센다** — `track_id` 가 %r 로 시작하는 행"
          % PROBE_MARKER)
    print("[PROBE] probe 사건 **%d건**" % c["total"])
    print("[PROBE] id: %s" % c["all"])
    print("[PROBE] 미처리 — `response_state=occurred` **%d** · `status=new` **%d**"
          % (c["open_by_response_state"], c["open_by_status"]))
    if c["open_by_response_state"] != c["open_by_status"]:
        print("[PROBE] ⚠ 같은 행을 두 칸이 다르게 말한다. 「미처리 N건」을 적을 때는 "
              "**어느 칸으로 셌는지** 같이 적어라 (P-190 · 한 행 한 정본)")
    if c["total"] == 0:
        #: ★ 0 은 **재지 못한 0 이 아니다.** ㉠지움(대표 결정)이 2026-09-21 에 끝났고
        #:   [`docs/agent/evidence/P-184/deleted_probe_snapshot_20260921.json` · 4건],
        #:   그 뒤로 이 수는 0 이어야 한다. 0 이 아니면 **게이트가 또 심고 있다**는 뜻이다.
        print("[PROBE] 0건 — ㉠지움(2026-09-21 · 대표 결정 · 4건) 뒤의 옳은 0이다. "
              "게이트가 다시 심으면 이 수가 다시 오른다")
    else:
        print("[PROBE] ⚠ 이 수는 **잴 때마다 는다** — 게이트가 사건을 만들기 때문이다. "
              "㉠지움은 끝났다(2026-09-21) — 그 뒤에 난 행이다 (P-184 ㉡재심 ㉢잼)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
