# -*- coding: utf-8 -*-
"""P-201 — **표식을 둘로 가른다** (턴 Y · 차선 U1 · 2026-09-20).

세종 판정:
    표식 `data_source=probe` 는 **게이트 생존 탐침** — **제품이 안 센다**(P-193 그대로).
    새 표식 `data_source=drill`(훈련) — **제품이 센다.** 사람 화면에는 「훈련」 배지 ·
    청구에서는 뺀다 · 보고서 K4 는 「훈련 N건 별도」 한 줄.

왜 이 파일이 생겼나 — **P-193 에 비용이 따라왔다**
--------------------------------------------------
지난 턴에 P-193(게이트가 제 씨앗을 안 센다)이 섰는데, 씨앗을 안 세게 하니
**그 씨앗으로 잴 수도 없게** 됐다. 온보딩 `U1#11`(「미처리 사건이 화면에 뜬다」)이
그래서 내려갔다 — 잴 것을 심는 순간 안 세어지므로, 「센다」를 증명할 방법이 사라졌다.

즉 P-193 은 **한 방향으로만 옳았다.** 「게이트가 제 씨앗을 세지 않는다」는 참이지만,
그 문장이 **「심은 것은 무엇이든 안 센다」**로 넓어지면 제품의 셈 자체를 못 잰다.
표식이 둘이어야 하는 이유가 그것이고, 이 파일이 **두 방향을 한 파일에서** 잰다:

    ① drill 4건  →  `summary.unhandled` **+4**   (세는가)
    ② probe 4건  →  `summary.unhandled` **+0**   (P-193 회귀 — 안 세는가)

①만 있으면 「아무것도 안 거르는 코드」가 통과하고, ②만 있으면 「전부 0으로 만드는
코드」가 통과한다. 둘을 **같은 창·같은 자격·같은 URL** 로 이어 재야 「빠진 것은
probe 뿐」이 증명된다.

새 문 0 · 새 매개변수 0 — **이 파일이 그것도 잰다**
---------------------------------------------------
바뀐 것은 **심는 쪽이 적는 표식 값 하나**뿐이다. 제품의 거르는 자리
(`common.probe_marker.exclude_probe`)는 **정의 하나 그대로**이고 `data_source=probe`
만 거른다 — 그래서 drill 은 **아무 코드도 안 고치고** 세어진다. 세종이 이름으로
금지한 것이 그 반대다(`include_probe` 같은 새 매개변수). 아래 `DrillMarkerShapeTest`
가 그 모양을 **실물로** 잰다.

F-04 도 여기서 잰다 — **같은 손이 발송 축을 든다**
--------------------------------------------------
`suppress()` 의 억제창이 **발송 시각이 아니라 사건 발생 시각**에 못박혀 있었다.
그래서 답이 시간이 흘러도 안 바뀌고, 한 번 접힌 사건은 **영원히** 접혔다
[실측 2026-09-20 · 조율자: `POST /api/dsm/events/4798/notify` → 200 `{"total":0}`].
`SuppressionAnchorTest` 가 그 자리를 잰다.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`)를 `/events/summary` ·
`/events` 를 때리는 **모든 호출**에 붙인다. 이 파일은 같은 URL 을 네 번 때리고 그
사이의 **수가 변하는지/안 변하는지**로 판정한다. 캐시가 적중하면 적중 본문은 언제나
앞 요청의 답이므로(D-341 착시 ⑦ · 적중은 200), **거르는 자리가 없어도 「변화 0」이
나오고** ②는 아무것도 안 재면서 초록이 된다. 동시에 ①의 +4 도 안 보여 빨강이 되는데,
그때 사람이 고치는 것은 코드가 아니라 시험이다. 우회는 이 파일의 **판정 조건**이다.
"""
from __future__ import annotations

import contextlib
import re
from datetime import timedelta
from pathlib import Path

from django.utils import timezone

from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture
from tests.test_k2_notify_kernel import K2Fixture

#: ★ D-289 — 표본은 저장소 실물이다. 합성 더미를 부르지 않는다.
REAL_SAMPLE = (
    "GET /api/dsm/events/summary · GET /api/dsm/events (실제 라우트) · "
    "apps.dsm.services.focus_queue/event_data_sources · "
    "kernels.k1_event.query_events · kernels.k2_notify.{send,suppress} · "
    "common/probe_marker.py · frontend/src/features/dsm/copy.ts(실물 파일) · "
    "docs/design/GX-COPY_v1.md(사전 정본 실물)"
)


def _clear_thread_request() -> None:
    """스레드에 남은 요청을 지운다.

    HTTP 를 한 번 때리면 dj-core 의 스레드 지역 요청이 남고, 그 뒤의 `objects` 질의가
    **「없다」와 「못 봤다」를 같은 답으로** 만든다(D-253). 이 파일은 심기와 때리기를
    번갈아 하므로 매번 지운다.
    """
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


def _repo_file(*parts: str) -> Path:
    """저장소 실물 파일. 컨테이너에는 `backend/` 만 `/app` 으로 들어오고 저장소 뿌리
    모양은 `/repo` 로 들어온다(D-285 (4) 마운트)."""
    here = Path(__file__).resolve()
    roots = [Path("/repo"), *here.parents[1:4]]
    for root in roots:
        candidate = root.joinpath(*parts)
        if candidate.is_file():
            return candidate
    raise AssertionError(
        f"저장소 실물 {'/'.join(parts)} 을 찾지 못했습니다. 컨테이너라면 마운트가 "
        f"빠진 것입니다 (D-285 (4)). ★ 이 시험은 skip 하지 않습니다 — 못 찾으면 "
        f"짝을 확인하지 못한 것이고, 확인 못 한 것은 초록이 아닙니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ①② 세는가 / 안 세는가 — 한 파일 · 한 창
# ═══════════════════════════════════════════════════════════════════════════
class DrillFixture(DsmFixture):
    """심는 도구와 재는 도구. **시험은 아래 클래스들에 있다**(여긴 0건).

    두 표식을 **같은 손으로 심고 같은 자격으로 재야** 한쪽의 초록이 다른 쪽에 대해
    무언가를 말한다(`test_u1_probe_not_counted.py` 와 같은 규약 · 같은 모양).
    """

    SUMMARY_URL = "/api/dsm/events/summary?hours=24"

    def _plant(self, *, track_id=None, minutes_ago: int) -> int:
        """사건 하나를 **K1 생성 경로로** 심는다. 시드가 심는 그 길이다.

        ⚠ `minutes_ago` 를 서로 다르게 준다 — K1 은 10초 창 안의 같은 스트림·유형을
          **접는다**(DEDUP_WINDOW). 접히면 4건을 심었다고 믿으면서 1건을 심게 되고,
          그 시험은 아무것도 재지 않는다.
        """
        from kernels.k1_event import record_detection

        _clear_thread_request()
        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.pk,
            event_type="fire", severity="critical",
            occurred_at=timezone.now() - timedelta(minutes=minutes_ago),
            track_id=track_id,
            snapshot_path=f"minio://dsm/drill-{minutes_ago}.jpg")
        self.assertFalse(
            result.folded_into_existing,
            "심은 사건이 앞 건에 접혔습니다 — 시각 간격을 넓히십시오(표본 고장).")
        return result.event_id

    def _unhandled(self) -> int:
        _clear_thread_request()
        resp = self.client.get(self.SUMMARY_URL, **_bearer(self.user_a), **NO_CACHE)
        self.assertEqual(200, resp.status_code, resp.content[:400])
        body = resp.json()
        self.assertIn("unhandled", body, f"요약에 `unhandled` 칸이 없습니다: {body}")
        self.assertFalse(
            body.get("unhandled_capped"),
            "상한에 닿았습니다 — 상한에 걸린 수로는 +4 도 변화 0 도 주장할 수 없습니다.")
        return body["unhandled"]

    @staticmethod
    def _drill_mark(run: str) -> str:
        from common.probe_marker import drill_mark

        return drill_mark(run)

    @staticmethod
    def _probe_mark(run: str) -> str:
        from common.probe_marker import PROBE_MARKER

        return f"{PROBE_MARKER};run={run}"


class DrillIsCountedTest(DrillFixture):
    """**세는가** — 훈련 사건은 제품의 일감이다."""

    def test_four_drill_events_move_unhandled_by_four_and_four_probe_events_do_not(self):
        """drill 4건 → **+4** · 이어서 probe 4건 → **+0**.

        한 메서드에 둔 이유: 따로 재면 두 측정 사이에 다른 것이 바뀌어도 안 보인다.
        같은 창에서 **연달아** 재야 「가른 것은 표식뿐」이 증명된다.
        """
        before = self._unhandled()

        drill_ids = [self._plant(track_id=self._drill_mark("20260920T160000"),
                                 minutes_ago=m)
                     for m in (11, 12, 13, 14)]
        self.assertEqual(4, len(set(drill_ids)), "drill 4건이 서로 다른 행이어야 합니다.")

        after_drill = self._unhandled()
        self.assertEqual(
            before + 4, after_drill,
            f"drill 4건을 심었는데 `unhandled` 가 {before} → {after_drill} 입니다. "
            f"훈련은 **제품이 세는 것**입니다(P-201) — 안 세면 온보딩 U1#11 을 "
            f"증명할 방법이 다시 사라집니다.")

        probe_ids = [self._plant(track_id=self._probe_mark("20260920T160001"),
                                 minutes_ago=m)
                     for m in (21, 22, 23, 24)]
        self.assertEqual(4, len(set(probe_ids)), "probe 4건이 서로 다른 행이어야 합니다.")

        after_probe = self._unhandled()
        self.assertEqual(
            after_drill, after_probe,
            f"probe 4건에 `unhandled` 가 {after_drill} → {after_probe} 로 움직였습니다. "
            f"P-193 회귀입니다 — 게이트가 제 씨앗을 다시 세고 있습니다.")

    def test_the_queue_stands_the_drill_event_on_top_and_says_it_is_a_drill(self):
        """**큐 최상단 drill · 그리고 그 카드가 「훈련」이라고 말한다.**

        ★ 두 가지를 한 번에 잰다. 최상단에 서기만 하고 **말하지 않으면** 관제요원은
          훈련을 재난으로 읽고 사람을 보낸다 — 세는 것보다 나쁜 상태다.
        """
        from apps.dsm import services

        drill_id = self._plant(track_id=self._drill_mark("20260920T160002"),
                               minutes_ago=600)

        _clear_thread_request()
        queue = services.focus_queue(scope=self.scope_a, limit=200)
        focus = queue.get("focus") or {}
        self.assertEqual(
            drill_id, focus.get("event_id"),
            f"가장 오래 기다린 자리(10시간)에 훈련 사건 #{drill_id} 이 서지 않았습니다 "
            f"— 훈련은 제품이 세고, 세는 것은 큐에 섭니다(P-201). 초점: {focus!r}")
        self.assertEqual(
            "drill", focus.get("data_source"),
            f"큐 카드가 `data_source` 를 {focus.get('data_source')!r} 라고 합니다. "
            f"화면은 이 값으로 「훈련」 배지를 그립니다(`copy.ts::dataSourceBadge`) — "
            f"값이 없으면 배지도 없고, 배지 없는 훈련은 재난으로 읽힙니다.")

    def test_the_operator_list_says_which_rows_are_drills(self):
        """목록 행도 **스스로 말한다.**

        종전엔 `data_source` 가 **상세에만** 있었다. 그래서 목록에서 훈련을 가르려면
        한 건씩 열어 봐야 했고, 한 건씩 열어 보는 것은 **가르지 못하는 것**과 같다.
        """
        drill_id = self._plant(track_id=self._drill_mark("20260920T160003"),
                               minutes_ago=31)
        live_id = self._plant(track_id=None, minutes_ago=32)

        _clear_thread_request()
        resp = self.client.get("/api/dsm/events?limit=200",
                               **_bearer(self.user_a), **NO_CACHE)
        self.assertEqual(200, resp.status_code, resp.content[:400])
        rows = {row["event_id"]: row for row in resp.json()["events"]}

        self.assertIn(drill_id, rows, "훈련 사건이 운영자 목록에서 사라졌습니다.")
        self.assertEqual(
            "drill", rows[drill_id].get("data_source"),
            f"훈련 사건 #{drill_id} 의 목록 행이 "
            f"{rows[drill_id].get('data_source')!r} 라고 합니다.")

        #: ★ 양성 대조 — **전부 drill 이라고 답하는 코드**도 위 줄을 통과한다.
        self.assertIn(live_id, rows, "실운영 사건이 목록에서 사라졌습니다.")
        self.assertEqual(
            "live", rows[live_id].get("data_source"),
            f"표식 없는 사건 #{live_id} 까지 "
            f"{rows[live_id].get('data_source')!r} 로 적혔습니다 — 진짜 경보에 「훈련」 "
            f"배지가 붙으면 그것을 본 관제요원은 손을 늦춥니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 「훈련」 배지 — **새 말을 짓지 않았는가**
# ═══════════════════════════════════════════════════════════════════════════
class DrillBadgeUsesTheExistingWordTest(DrillFixture):
    """배지의 말은 **사전에 이미 있는 것**이어야 한다 (GX-COPY 규칙 1).

    새 말을 지으면 `verify_ui_copy` 래칫이 잡는다 — 그리고 잡히는 것이 옳다:
    같은 것을 두 이름으로 부르는 제품은 사람이 두 기능으로 읽는다.
    """

    #: 사전이 정한 글자. **여기서 만드는 값이 아니라** 사전의 값을 적어 둔 자리이고,
    #: 아래 두 시험이 사전·화면 양쪽 실물과 대조한다.
    WORD = "훈련"

    def test_the_word_is_already_in_the_dictionary(self):
        """GX-COPY §2 「출처 칩」 줄에 **이미 있다.**"""
        text = _repo_file("docs", "design", "GX-COPY_v1.md").read_text(encoding="utf-8")
        line = [ln for ln in text.splitlines()
                if "data_source" in ln and self.WORD in ln]
        self.assertTrue(
            line,
            f"사전에 「{self.WORD}」 배지 줄이 없습니다 — 그렇다면 이것은 **새 말**이고, "
            f"새 말을 짓는 것은 차선의 일이 아니라 조율자의 일입니다(GX-COPY 규칙 1).")
        self.assertIn(
            "시드", line[0],
            "사전 줄이 「실운영 / 시드(검수용) / 훈련」 셋을 말하지 않습니다 — 셋 중 "
            "하나만 그리면 배지가 무엇의 반대인지 알 수 없습니다.")

    def test_the_screen_draws_that_same_word_and_draws_nothing_for_live(self):
        """화면의 사전(`copy.ts`)이 **같은 글자**를 들고, 평상에는 **안 그린다.**

        평상에 배지를 붙이면 배지가 뜻을 잃는다 — 모두가 배지를 달면 아무도 눈에 안 띈다.
        """
        copy_ts = _repo_file("frontend", "src", "features", "dsm", "copy.ts").read_text(
            encoding="utf-8")
        self.assertRegex(
            copy_ts, r"drill:\s*'" + self.WORD + r"'",
            f"`copy.ts::DATA_SOURCE_LABEL` 이 `drill` 을 「{self.WORD}」로 적지 "
            f"않습니다 — 서버가 내는 낱말(`drill`)과 화면이 그리는 말이 갈렸습니다.")
        self.assertNotRegex(
            copy_ts, r"\blive:\s*'",
            "`live` 에 배지 글자가 붙었습니다 — 평상에도 배지가 그려집니다.")

    def test_the_two_screens_that_show_the_queue_actually_draw_it(self):
        """★ **누른 뒤를 본 것만 초록** 에 못 미치는 자리라 실물 파일로 잰다.

        사전에 낱말이 있고 서버가 값을 내도 **화면이 안 부르면** 배지는 없다 —
        그것이 착시 ⑥(정의 1건 · 읽기 0곳)이 태어나는 자리다.
        """
        for parts in (("frontend", "src", "features", "dsm", "pages", "FocusQueue.tsx"),
                      ("frontend", "src", "features", "dsm", "pages", "EventList.tsx")):
            body = _repo_file(*parts).read_text(encoding="utf-8")
            self.assertIn(
                "dataSourceBadge(", body,
                f"{parts[-1]} 이 `dataSourceBadge` 를 한 번도 부르지 않습니다 — "
                f"서버가 `data_source` 를 실어 보내도 화면에는 아무것도 안 뜹니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 새 문 0 · 새 매개변수 0 — **모양을 잰다**
# ═══════════════════════════════════════════════════════════════════════════
class DrillMarkerShapeTest(DrillFixture):
    """세종이 이름으로 금지한 모양을 **실물로** 잰다."""

    def test_exclude_probe_still_excludes_only_probe(self):
        """`exclude_probe` 는 **정의 하나 그대로**이고 `probe` 만 거른다.

        이것이 「새 문 0」의 실체다 — drill 이 세어지는 것은 새 코드 때문이 아니라
        **거르는 정의가 probe 만 거르기 때문**이다.
        """
        from common.probe_marker import (DRILL_MARKER, PROBE_MARKER, is_drill_track,
                                         is_probe_track)

        self.assertFalse(
            is_probe_track(f"{DRILL_MARKER};run=x"),
            "훈련 표식이 probe 로 읽혔습니다 — 그러면 훈련이 안 세어집니다.")
        self.assertFalse(
            is_drill_track(f"{PROBE_MARKER};run=x"),
            "게이트 탐침이 훈련으로 읽혔습니다 — 그러면 탐침이 세어집니다(P-193 회귀).")
        self.assertFalse(is_drill_track(None), "빈 값은 훈련이 아닙니다.")
        self.assertFalse(is_drill_track(""), "빈 값은 훈련이 아닙니다.")
        self.assertFalse(
            is_drill_track("xdata_source=drill"),
            "가운데 낀 표식을 훈련으로 읽었습니다 — 남이 적은 값이 훈련이 됩니다.")

    def test_no_new_include_like_parameter_was_born(self):
        """`include_drill` 같은 매개변수가 **안 생겼는가** (세종이 이름으로 금지).

        생기는 순간 세는 법이 부르는 자리마다 갈리고, 갈린 쪽이 조용히 이긴다 —
        `common/probe_marker.py` 가 존재하는 이유가 그것이다.
        """
        for parts in (("backend", "apps", "dsm", "services.py"),
                      ("backend", "apps", "dsm", "api.py"),
                      ("backend", "kernels", "k1_event", "services.py"),
                      ("backend", "kernels", "k2_notify", "services.py"),
                      ("backend", "common", "probe_marker.py"),
                      #: ★ 차선 U56 이 같은 턴에 세운 청구 쪽 정본. **읽기만 한다** —
                      #:   금지의 모양은 한 차선의 것이 아니라 저장소의 것이고,
                      #:   청구가 그 칸을 갖는 날이 바로 세종이 막으려던 날이다
                      #:   (「이번만 포함」이 다음 달 청구서의 구멍이 된다).
                      ("backend", "common", "billing_marks.py"),
                      ("backend", "apps", "dsm", "metering.py")):
            body = _repo_file(*parts).read_text(encoding="utf-8")
            #: **쓰이는 모양**만 잡는다 — 매개변수 선언(`name:` / `name=`)과
            #: 호출 인자(`name=`). 금지를 **적어 둔 주석**까지 잡으면, 금지를 기록한
            #: 사람이 빨강을 받고 **기록을 지우는 쪽**으로 간다.
            found = re.findall(r"\b(?:include|exclude)_drill\s*[:=]", body)
            self.assertEqual(
                [], found,
                f"{parts[-1]} 에 {sorted(set(found))} 가 있습니다 — 세종이 이름으로 "
                f"금지한 모양입니다(P-201 「새 매개변수를 만들면 빨강」).")

    def test_the_drill_mark_fits_the_column(self):
        """표식은 `track_id`(64자) 안에 들어가야 한다 — **자른 표식은 표식이 아니다.**"""
        from common.probe_marker import TRACK_ID_MAX, drill_mark

        mark = drill_mark("20260920T160000")
        self.assertLessEqual(len(mark), TRACK_ID_MAX, f"표식이 깁니다: {mark!r}")
        with self.assertRaises(ValueError, msg="상한을 넘겨도 조용히 통과했습니다."):
            drill_mark("X" * TRACK_ID_MAX)


# ═══════════════════════════════════════════════════════════════════════════
# F-04 — 억제창의 **기준이 움직이는가**
# ═══════════════════════════════════════════════════════════════════════════
class SuppressionAnchorTest(K2Fixture):
    """[F-04] 「5분 안에 같은 사건 재발송 억제」 — **기준은 직전 발송 시각이다.**

    캐시 처리: 해당 없음 — HTTP 를 때리지 않는다. 커널 함수를 직접 부르고 시각은
    `now=` 로 넘긴다(`renotify(now=)` 와 **같은 규약**). 시계를 기다리지 않는다:
    기다리는 시험은 느린 것이 아니라 **재현되지 않는** 시험이다.
    """

    def _last_sent_at(self, event_id: int):
        from django.apps import apps as django_apps

        return (django_apps.get_model("stream_monitors", "DeliveryRecord")
                ._base_manager.filter(event_id=event_id, succeeded=True)
                .order_by("-sent_at").values_list("sent_at", flat=True).first())

    def test_a_send_three_minutes_after_the_event_is_resent_six_minutes_later(self):
        """★★ **시험 1** — 발생 3분 뒤 발송 → **6분 뒤 재발송된다.**

        종전에는 `suppress` 가 `event.occurred_at` 에 못박힌 창을 봤다. 그 창은
        **지나간 한 순간**이라 시간이 흘러도 답이 안 바뀌고, 한 번 참이면 영원히
        참이었다 — 16일 뒤에 관제요원이 「알림 보내기」를 눌러도 200 `{"total":0}`.
        """
        from kernels.k2_notify import send, suppress

        occurred = timezone.now() - timedelta(minutes=30)
        event_id = self._event(self.stream_a, when=occurred)

        #: 발생 **3분 뒤**에 성공 발송이 있었다. 발송 시각은 `sent_at` 이 든다.
        sent_at = occurred + timedelta(minutes=3)
        deliveries = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(deliveries, "첫 발송이 0건입니다 — 표본이 고장났습니다.")
        self.assertTrue(deliveries[0].succeeded, "첫 발송이 실패했습니다(표본 고장).")
        from django.apps import apps as django_apps

        django_apps.get_model("stream_monitors", "DeliveryRecord")._base_manager.filter(
            event_id=event_id, succeeded=True).update(sent_at=sent_at)
        self.assertEqual(sent_at, self._last_sent_at(event_id),
                         "발송 시각을 못 옮겼습니다(표본 고장).")

        #: ① 음성 대조 — **3분 뒤**에는 아직 접힌다. 접히지 않으면 억제기가 없는 것이고,
        #:   그때는 아래 ②의 초록이 「고쳤다」가 아니라 「꺼 버렸다」가 된다.
        self.assertTrue(
            suppress(scope=self.scope_a, event_id=event_id,
                     now=sent_at + timedelta(minutes=3)),
            "직전 발송 3분 뒤인데 접히지 않았습니다 — 억제기를 고친 것이 아니라 "
            "**꺼 버린** 것입니다(F-04 「5분 안에 같은 사건 재발송 억제」).")

        #: ② **시험 1** — 발송으로부터 6분 뒤에는 접히지 않는다.
        later = sent_at + timedelta(minutes=6)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=event_id, now=later),
            f"직전 발송({sent_at:%H:%M})으로부터 6분 뒤({later:%H:%M})인데도 접혔습니다 "
            f"— 억제창의 기준이 여전히 **사건 발생 시각**에 못박혀 있습니다(F-04).")

        before = self._delivery_count(event_id)
        again = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(
            again,
            "접히지 않는다고 했는데 `send` 는 0건을 냈습니다 — 판정과 실행이 갈렸습니다. "
            "`suppress` 만 고치고 `send` 가 다른 문턱을 들고 있는 상태입니다.")
        self.assertGreater(
            self._delivery_count(event_id), before,
            "「보냈다」고 했는데 발송 이력이 안 늘었습니다 — 보고는 증거가 아닙니다.")

    def test_a_sixteen_day_old_event_is_not_suppressed_forever(self):
        """★ 실측이 잡은 그 모양 — **16일 지난 사건의 수동 알림이 영원히 접힌다.**

        [실측 2026-09-20 · 조율자] `POST /api/dsm/events/4798/notify` →
        200 `{"total":0,"deliveries":[]}`. 200 이라 누른 사람은 알 길이 없었다.
        """
        from kernels.k2_notify import send, suppress

        from django.apps import apps as django_apps

        long_ago = timezone.now() - timedelta(days=16)
        #: **옆 사건**이 그 사건보다 3분 앞서 났고 알림이 나갔다 — 종전 질의는
        #: `stream+type` 으로 묶으면서 창을 `event.occurred_at` 에 못박아, 그 옆 사건의
        #: 발송을 **영원히** 이 사건의 억제 근거로 썼다.
        neighbour = self._event(self.stream_a, when=long_ago - timedelta(minutes=3))
        send(scope=self.scope_a, event_id=neighbour)
        #: ★ 그 발송도 **16일 전에 나갔다.** 시험이 그것을 직접 적어야 한다 — 새 기준은
        #:   `sent_at` 이고, 픽스처는 지금 보내기 때문이다. 안 옮기면 이 시험은
        #:   「16일 지난 사건」이 아니라 「방금 보낸 옆 사건」을 재게 된다(표본 고장).
        django_apps.get_model("stream_monitors", "DeliveryRecord")._base_manager.filter(
            event_id=neighbour, succeeded=True).update(
                sent_at=long_ago - timedelta(minutes=3))

        event_id = self._event(self.stream_a, when=long_ago)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=event_id),
            "16일 지난 사건이 여전히 접힙니다 — 관제요원이 「알림 보내기」를 눌러도 "
            "200 `{\"total\":0}` 이 돌아옵니다(제품 결함 F-04).")
        self.assertTrue(
            send(scope=self.scope_a, event_id=event_id),
            "접히지 않는다고 했는데 발송이 0건입니다.")

    def test_a_failed_delivery_still_does_not_suppress(self):
        """★ 회귀 — **못 보낸 알림은 「이미 알렸다」가 아니다.**

        기준을 `sent_at` 으로 옮기면서 이 성질이 **더 단단해졌다**: `sent_at` 은
        성공했을 때만 찍히므로(`_send_one`) 실패 행은 창에 들어올 수가 없다.
        그래도 잰다 — 성질이 코드의 부수효과로 서 있으면 다음 손이 지운다.
        """
        from kernels.k2_notify import channels, send, suppress

        undo = channels.register(_Broken())
        try:
            event_id = self._event(self.stream_a, when=timezone.now())
            send(scope=self.scope_a, event_id=event_id)
        finally:
            undo()
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=event_id),
            "실패한 발송이 억제로 세어졌습니다 — 장애 구간의 알림이 사라집니다.")

    def _delivery_count(self, event_id: int) -> int:
        from django.apps import apps as django_apps

        return (django_apps.get_model("stream_monitors", "DeliveryRecord")
                ._base_manager.filter(event_id=event_id).count())


class _Broken:
    """메일 서버가 죽은 상태. `test_k2_notify_kernel._BrokenChannel` 과 같은 뜻이다 —
    거기 것을 import 하면 그 파일의 사유(`@override_settings`)까지 딸려 오므로
    **이 파일의 것으로 세운다**(같은 계약 · 다른 자리)."""

    name = "email"

    def send(self, *, address: str, subject: str, body: str):
        from kernels.k2_notify import channels

        return channels.SendOutcome(False, "메일 서버가 죽었다(시험용)")
