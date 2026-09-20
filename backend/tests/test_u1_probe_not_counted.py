# -*- coding: utf-8 -*-
"""P-193 — **게이트는 제 씨앗을 세지 않는다** (턴 X · 차선 U1 · 2026-09-20).

세종 판정:
    `/api/dsm/events/summary` 의 `unhandled` 칸을 비롯해 **모든 집계·큐·온보딩 술어가
    `data_source=probe`(track_id 표식)를 뺀다. 삭제가 아니라 셈이다.**
    음성 대조: **probe 4건 심은 뒤 summary unhandled 변화 0.**

이 파일이 묻는 것 넷
--------------------
    ① **음성 대조** — probe 4건을 심어도 `unhandled` 가 안 움직이는가.
    ② **양성 대조** — probe 아닌 1건은 움직이는가.
       ①만 있으면 「전부 0으로 만드는 코드」도 통과한다. 둘을 **한 측정 안에서**
       이어서 잰다 — 따로 재면 두 측정 사이에 다른 것이 바뀌어도 안 보인다.
    ③ **제품을 감추지 않았는가** — 같은 사건이 운영자의 목록에는 그대로 있는가
       (D-497 「거르는 곳은 측정이지 제품이 아니다」). 감췄으면 그것은 세지 않기가
       아니라 **사건을 숨긴 것**이다.
    ④ **세는 법이 한 곳인가** — 게이트 쪽 정본(`scripts/probe_events.py`)과 백엔드 쪽
       정본(`common/probe_marker.py`)이 **출생 표본 전수에서 같은 답**을 내는가.
       갈리면 게이트는 「probe 0건」이라 하는데 집계는 세고 있는 상태가 된다.

왜 HTTP 로 재나
---------------
`unhandled` 는 함수가 아니라 **칸**이다. 서비스 함수만 불러 초록을 내면 착시 ⑨
(코드는 있고 시험은 초록인데 나가는 문은 다른 답을 내는 자리)를 그대로 재현한다.
그래서 **실제 라우트를 실제 자격으로** 때린다.

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`X-No-Cache`)를 `/events/summary` ·
`/events` 를 때리는 **모든 호출**에 붙인다. 이 시험은 같은 URL 을 세 번 때리고 그
사이의 **수가 변하는지/안 변하는지**로 판정하므로, 캐시가 적중하면 **필터가 없어도
「변화 0」이 나온다** — 적중 본문은 언제나 앞 요청의 답이기 때문이다(D-341 착시 ⑦ ·
적중은 200). 즉 **이 파일이 캐시를 타는 순간 음성 대조(probe 4건 → 변화 0)는
아무것도 안 재면서 초록**을 내고, P-193 은 「고쳤다」로 보고된 채 그대로 살아 있다.
양성 대조(비probe 1건 → +1)도 같이 죽는다: 적중이면 +1 이 안 보여 **빨강으로 보이는
초록**이 아니라 **빨강으로 보이는 빨강**이 되지만, 그때 사람이 고치는 것은 코드가
아니라 시험이 된다. 그래서 우회는 이 파일의 **판정 조건**이지 위생이 아니다.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.utils import timezone

from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "GET /api/dsm/events/summary · GET /api/dsm/events (실제 라우트) · "
    "apps.dsm.services.recent_events · kernels.k1_event.query_events · "
    "common.probe_marker · scripts/probe_events.py(게이트 정본 파일 실물) — "
    "합성 더미를 부르지 않는다"
)

#: 게이트 쪽 정본을 **파일로** 찾는다. 컨테이너에는 `backend/` 만 `/app` 으로 들어오고
#: 저장소 뿌리 모양은 `/repo` 로 들어온다(D-285 (4) 마운트).
REPO_ROOT_CANDIDATES = ("/repo",)


def _find_gate(name: str):
    here = Path(__file__).resolve()
    roots = [*(Path(c) for c in REPO_ROOT_CANDIDATES), *here.parents[1:4]]
    for root in roots:
        candidate = root / "scripts" / name
        if candidate.is_file():
            return candidate
    return None


def _load_gate_module(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("gate_probe_events", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clear_thread_request() -> None:
    """스레드에 남은 요청을 지운다.

    HTTP 를 한 번 때리면 dj-core 의 스레드 지역 요청이 남고, 그 뒤의 `objects` 질의가
    **「없다」와 「못 봤다」를 같은 답으로** 만든다(D-253). 이 파일은 심기와 때리기를
    번갈아 하므로 매번 지운다 — 픽스처가 태어날 때 하는 것과 같은 한 줄이다.
    """
    import contextlib

    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class ProbeFixture(DsmFixture):
    """심는 도구와 재는 도구. **시험은 아래 두 클래스에 있다**(여긴 0건).

    두 축(사건·발송)이 **같은 손으로 심고 같은 자격으로 재야** 한 축의 초록이 다른 축에
    대해 무언가를 말한다. 그래서 도구를 한 벌만 둔다.
    """

    SUMMARY_URL = "/api/dsm/events/summary?hours=24"

    # ── 심는 도구 ────────────────────────────────────────────────────────
    def _plant(self, *, track_id=None, minutes_ago: int):
        """사건 하나를 **K1 생성 경로로** 심는다. 게이트가 심는 그 길이다.

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
            snapshot_path=f"minio://dsm/probe-{minutes_ago}.jpg")
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
            "상한에 닿았습니다 — 상한에 걸린 수로는 변화 0 을 주장할 수 없습니다.")
        return body["unhandled"]

    @staticmethod
    def _gate_marker() -> str:
        """게이트가 실제로 적는 표식. **우리 상수로 심지 않는다** — 우리 상수로 심고
        우리 상수로 거르면 그 시험은 자기가 자기를 통과시킬 뿐이다."""
        path = _find_gate("probe_events.py")
        assert path is not None, (
            "게이트 정본 `scripts/probe_events.py` 를 찾지 못했습니다. 컨테이너라면 "
            "`./scripts:/repo/scripts:ro` 마운트가 빠진 것입니다 (D-285 (4)). "
            "★ 이 시험은 skip 하지 않습니다 — 못 찾으면 짝을 확인하지 못한 것입니다.")
        return _load_gate_module(path).PROBE_MARKER


class ProbeIsNotCountedTest(ProbeFixture):
    """**사건 축** — 게이트가 심은 사건이 일감으로 읽히지 않는가."""

    # ── ①②  음성 대조와 양성 대조 — **한 측정 안에서** ──────────────────
    def test_four_probe_events_do_not_move_unhandled_but_one_real_event_does(self):
        """probe 4건 → 변화 **0** · 그 직후 비probe 1건 → **+1**.

        둘을 한 메서드에 둔 이유: 따로 재면 「전부 0으로 만드는 코드」가 음성 대조만
        통과하고, 양성 대조는 **다른 실행**에서 초록이 될 수 있다. 같은 창·같은 자격·
        같은 URL 로 이어 재야 「빠진 것은 probe 뿐」이 증명된다.
        """
        marker = self._gate_marker()

        before = self._unhandled()

        planted = [self._plant(track_id=f"{marker};run=20260920T124500", minutes_ago=m)
                   for m in (11, 12, 13, 14)]
        self.assertEqual(4, len(set(planted)), "probe 4건이 서로 다른 행이어야 합니다.")

        after_probe = self._unhandled()
        self.assertEqual(
            before, after_probe,
            f"probe 4건을 심었더니 `unhandled` 가 {before} → {after_probe} 로 움직였습니다. "
            f"게이트가 심은 사건을 게이트가 일감으로 읽고 있습니다 (P-193 · 턴 W 실측: "
            f"FC 29→32 의 오른 세 행이 전부 이 위에 서 있었습니다).")

        real = self._plant(track_id=None, minutes_ago=15)
        after_real = self._unhandled()
        self.assertEqual(
            before + 1, after_real,
            f"probe 아닌 사건 #{real} 을 심었는데 `unhandled` 가 {after_probe} → "
            f"{after_real} 입니다. **분모를 0으로 만드는 필터**는 필터가 아닙니다 — "
            f"거르는 자리가 probe 아닌 것까지 지우고 있습니다.")

    # ── ③ 제품을 감추지 않았는가 ─────────────────────────────────────────
    def test_the_operator_list_still_shows_the_probe_event(self):
        """운영자의 목록에는 **그대로 있다** (D-497).

        세는 것과 보는 것은 다른 일이다. 목록에서까지 빼면 그것은 「지우지 않고 세지
        않기」가 아니라 **사건을 숨긴 것**이고, 숨긴 사건은 아무도 못 고친다.
        """
        marker = self._gate_marker()
        planted = self._plant(track_id=f"{marker};run=20260920T124501", minutes_ago=9)

        _clear_thread_request()
        resp = self.client.get("/api/dsm/events?limit=200",
                               **_bearer(self.user_a), **NO_CACHE)
        self.assertEqual(200, resp.status_code, resp.content[:400])
        ids = [row["event_id"] for row in resp.json()["events"]]
        self.assertIn(
            planted, ids,
            "probe 사건이 운영자 목록에서 사라졌습니다 — 이것은 셈을 고친 것이 아니라 "
            "제품을 감춘 것입니다 (D-497 · P-193 은 「삭제가 아니라 셈」입니다).")

    # ── ③′ 인계 초안의 「미처리 N」 ──────────────────────────────────────
    def test_the_handover_draft_does_not_count_probe(self):
        """다음 근무자가 읽는 첫 줄이 **게이트가 몇 번 돌았는지**를 말하면 안 된다."""
        from apps.dsm import handover_service

        marker = self._gate_marker()
        _clear_thread_request()
        before = handover_service.build_draft(scope=self.scope_a, hours=24)

        probe_ids = [self._plant(track_id=f"{marker};run=20260920T124502", minutes_ago=m)
                     for m in (21, 22, 23, 24)]
        _clear_thread_request()
        after = handover_service.build_draft(scope=self.scope_a, hours=24)

        self.assertEqual(
            before.unresolved_count, after.unresolved_count,
            f"인계 초안의 「미처리 N」이 probe 4건에 움직였습니다 "
            f"({before.unresolved_count} → {after.unresolved_count}).")
        for event_id in probe_ids:
            self.assertNotIn(
                f"#{event_id}", after.body,
                f"인계 본문이 probe 사건 #{event_id} 을 일감으로 적었습니다.")

    # ── ③″ 큐 술어 ──────────────────────────────────────────────────────
    def test_the_focus_queue_does_not_stand_a_probe_on_top(self):
        """초점 큐는 보는 목록이 아니라 **「다음에 무엇을 누를 것인가」라는 술어**다.

        씨앗이 최상단에 서면 관제요원의 다음 손이 씨앗으로 간다.
        """
        from apps.dsm import services

        marker = self._gate_marker()
        probe_id = self._plant(track_id=f"{marker};run=20260920T124503", minutes_ago=90)

        _clear_thread_request()
        queue = services.focus_queue(scope=self.scope_a, limit=200)
        focus = queue.get("focus") or {}
        self.assertNotEqual(
            probe_id, focus.get("event_id"),
            "가장 오래 기다린 자리에 게이트 씨앗이 섰습니다 — 큐 술어가 probe 를 "
            "세고 있습니다 (P-193).")
        #: 카드는 원본을 **묶어서** 낸다 — 대표 한 줄만 보면 묶인 안쪽에 숨은 씨앗을
        #: 놓친다. 그래서 `member_event_ids` 까지 전부 본다.
        cards = [c for c in ([focus] if focus else []) + list(queue.get("queue", [])) if c]
        seen = {event_id for card in cards
                for event_id in card.get("member_event_ids", [])}
        self.assertNotIn(probe_id, seen,
                         "큐 카드 안에 probe 사건이 들어 있습니다 (P-193).")
        self.assertEqual(
            0, sum(1 for c in cards if c.get("event_id") == probe_id),
            "큐 카드의 대표가 probe 사건입니다 (P-193).")

    # ── 턴 W 회귀 — 셈을 고치면서 이 둘이 안 상했는가 ────────────────────
    def test_turn_w_regressions_still_hold_after_the_count_changed(self):
        """턴 W 가 닫은 둘을 **다시 잰다** (회귀는 다시 재야 회귀다).

            ㉠ 「가장 오래 기다린」 자리가 **실측과 일치**한다 — 최신순이 아니다.
            ㉡ **대기 카드에는 되돌림이 안 실린다** — 화면의 단추는 서버의
               `allowed_next` 를 그대로 그리므로(`FocusQueue.tsx::renderActions`),
               그 목록에 되돌림이 없으면 단추도 없다. 표는 하나다(D-399).

        probe 를 세지 않게 된 뒤에도 ㉠이 참인지가 이 시험의 요점이다: 씨앗이 가장
        오래된 행이면 **순위의 1등이 씨앗**이 되고, 그러면 화면의 「가장 오래 기다린」은
        사람이 기다린 사건을 가리키지 않는다.
        """
        from apps.dsm import services

        marker = self._gate_marker()
        newer = self._plant(track_id=None, minutes_ago=30)
        oldest_real = self._plant(track_id=None, minutes_ago=60)
        self._plant(track_id=f"{marker};run=20260920T124504", minutes_ago=180)

        _clear_thread_request()
        queue = services.focus_queue(scope=self.scope_a, limit=200)
        focus = queue.get("focus") or {}
        self.assertEqual(
            oldest_real, focus.get("event_id"),
            f"「가장 오래 기다린」 자리가 실측과 다릅니다 — 실측 최고령(비probe)은 "
            f"#{oldest_real} 인데 #{focus.get('event_id')} 가 섰습니다. "
            f"(#{newer} 가 섰다면 최신순으로 돌아간 것이고, 씨앗이 섰다면 P-193 입니다.)")
        self.assertEqual(2, queue.get("total_events"),
                         "원본 건수가 probe 를 세고 있습니다.")

        #: ㉡ 대기 카드(`occurred`)의 갈 곳에 되돌림(`in_progress`)이 없다.
        allowed = services.response_state(
            scope=self.scope_a, event_id=focus["event_id"])["allowed_next"]
        self.assertIn("acknowledged", allowed,
                      f"대기 카드가 갈 곳을 잃었습니다: {allowed}")
        self.assertNotIn(
            "in_progress", allowed,
            f"대기 카드에 되돌림 칸이 실렸습니다: {allowed}. 화면은 이 목록을 그대로 "
            f"단추로 그리므로(FocusQueue.tsx) 그 순간 되돌림 단추가 렌더됩니다.")

    # ── ④ 세는 법이 한 곳인가 ───────────────────────────────────────────
    def test_the_backend_predicate_agrees_with_the_gate_predicate(self):
        """게이트 정본과 백엔드 정본이 **출생 표본 전수에서** 같은 답을 내는가.

        ★ 백엔드는 `scripts/` 를 import 하지 못한다(컨테이너에서 `/app` 과 `/repo` 가
          다른 자리다). 그래서 「한 곳」은 **파일 하나**가 아니라 **뜻 하나**이고,
          그 뜻이 갈리지 않는다는 것을 여기서 잰다 — 갈리면 게이트는 「probe 0건」이라
          하는데 집계는 세고 있는(또는 그 반대) 상태가 되고, 그 어긋남은 아무도 못 본다.
        """
        from common import probe_marker

        path = _find_gate("probe_events.py")
        self.assertIsNotNone(
            path, "게이트 정본 `scripts/probe_events.py` 를 찾지 못했습니다 (D-285 (4) 마운트).")
        gate = _load_gate_module(path)

        self.assertEqual(
            gate.PROBE_MARKER, probe_marker.PROBE_MARKER,
            "표식 문자열이 갈렸습니다 — 한쪽이 거르는 것을 다른 쪽이 셉니다.")

        sample = self._birth_sample(path)
        self.assertGreaterEqual(len(sample), 8, "출생 표본이 너무 작습니다(표본 고장).")
        self.assertGreaterEqual(sum(1 for _, w in sample if w), 2, "표본에 양성이 모자랍니다.")
        self.assertGreaterEqual(sum(1 for _, w in sample if not w), 2, "표본에 음성이 모자랍니다.")

        wrong = [(track, want, probe_marker.is_probe_track(track))
                 for track, want in sample
                 if probe_marker.is_probe_track(track) != want]
        self.assertEqual([], wrong, f"두 판정기가 갈립니다: {wrong}")

    @staticmethod
    def _birth_sample(path: Path):
        """게이트 파일의 `BIRTH_SAMPLE` 을 **그 파일에서** 읽는다.

        베껴 오면 그 순간 표본이 두 벌이 되고, 게이트가 표본을 늘려도 이쪽은 옛 표본을
        잰다. 소스에서 뜯는 이유: `BIRTH_SAMPLE` 은 `self_test()` 안의 지역 변수다.
        """
        import ast

        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and node.targets
                    and getattr(node.targets[0], "id", "") == "BIRTH_SAMPLE"):
                return [tuple(pair) for pair in ast.literal_eval(node.value)]
        raise AssertionError(
            "게이트 정본에서 `BIRTH_SAMPLE` 을 찾지 못했습니다 — 이름이 바뀌었다면 "
            "두 판정기의 짝을 **아무도 안 재고 있는** 상태입니다.")


class ProbeIsNotCountedOnTheDeliveryAxisTest(ProbeFixture):
    """**축이 둘이다** — 사건을 막아도 발송은 안 막힌다 (2026-09-20 · 차선 U3 실측).

    사건 축을 닫은 뒤에도 관제요원의 M1 「나에게 온 것」 **첫 카드**가 게이트가 심은
    알림이었다. 발송은 다른 커널(`k2_notify.list_deliveries`)을 지나고, 표식은 발송 행에
    없이 `event` FK 너머에 있기 때문이다.

    **가른 축**: 「보는가 / 누르는가」다 — 「내 것인가」가 아니다.
        `mine=false` = 발송 **대장**(무엇이 언제 누구에게 갔나) → **보인다.**
                       여기서 빼면 「세지 않기」가 아니라 **「보낸 적 없음」**이 된다.
        `mine=true`  = M1 **일감**(다음 손이 가는 곳) → **안 센다.** 사건 축의 초점 큐와
                       같은 자리다.

    캐시 처리: 우회 — `_delivery_ids` 가 모든 HTTP 호출에 `X-No-Cache` 를 붙인다(파일
    머리말의 그 선언이 이 클래스에도 그대로 적용된다). 이 클래스도 **「변화 0」을 기대하는
    시험**이라 적중 본문 하나면 **필터 없이도 초록**이 된다.
    """

    MINE_URL = "/api/dsm/deliveries?mine=true&limit=200"
    LEDGER_URL = "/api/dsm/deliveries?limit=200"

    def _notify(self, event_id: int) -> list[int]:
        """**실제 발송 경로로** 알림을 낸다 — 행을 손으로 만들지 않는다.

        손으로 `DeliveryRecord` 를 만들면 그 행은 제품이 만드는 행과 **다를 수 있고**,
        다른 행 위의 초록은 제품에 대해 아무 말도 하지 않는다.
        """
        from apps.dsm import services

        _clear_thread_request()
        sent = services.notify_event(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent, f"#{event_id} 에 수신 규칙이 있는데 발송이 0건입니다(표본 고장).")
        return [r.delivery_id for r in sent]

    def _delivery_ids(self, url: str) -> list[int]:
        _clear_thread_request()
        resp = self.client.get(url, **_bearer(self.user_a), **NO_CACHE)
        self.assertEqual(200, resp.status_code, resp.content[:400])
        return [row["delivery_id"] for row in resp.json()["deliveries"]]

    def test_probe_deliveries_do_not_move_my_list_but_a_real_one_does(self):
        """M1 「나에게 온 것」 — probe 발송 4건 → **변화 0** · 비probe 1건 → **+1**."""
        marker = self._gate_marker()

        before = self._delivery_ids(self.MINE_URL)

        probe_deliveries: list[int] = []
        for minutes in (11, 12, 13, 14):
            event_id = self._plant(track_id=f"{marker};run=20260920T150000",
                                   minutes_ago=minutes)
            probe_deliveries += self._notify(event_id)
        self.assertEqual(4, len(probe_deliveries),
                         f"probe 발송이 4건이 아닙니다: {probe_deliveries}(표본 고장).")

        after_probe = self._delivery_ids(self.MINE_URL)
        self.assertEqual(
            before, after_probe,
            f"probe 사건 4건의 알림이 M1 「나에게 온 것」을 움직였습니다 "
            f"({len(before)} → {len(after_probe)}건). 관제요원의 다음 손이 게이트가 심은 "
            f"씨앗으로 갑니다 (P-193 · 발송 축).")

        real_event = self._plant(track_id=None, minutes_ago=15)
        real_delivery = self._notify(real_event)
        after_real = self._delivery_ids(self.MINE_URL)
        self.assertEqual(
            len(before) + len(real_delivery), len(after_real),
            f"비probe 발송 {real_delivery} 가 M1 에 안 나타납니다 "
            f"({len(after_probe)} → {len(after_real)}건). **전부 0으로 만드는 필터**는 "
            f"필터가 아닙니다.")
        for delivery_id in real_delivery:
            self.assertIn(delivery_id, after_real)

    def test_the_delivery_ledger_still_shows_what_actually_went_out(self):
        """발송 **대장**에는 그대로 있다 — 「안 센다」와 「보낸 적 없다」는 다른 말이다.

        `DeliveryRecord` 머리말: *「실패도 행으로 남는다. 실패를 남기지 않으면 "보낸 적
        없음"과 "보내려다 실패"가 같은 상태가 된다」*. 게이트 때문에 나간 알림도 **실제로
        나갔고**, 대장은 그 사실의 자리다.
        """
        marker = self._gate_marker()
        event_id = self._plant(track_id=f"{marker};run=20260920T150001", minutes_ago=9)
        sent = self._notify(event_id)

        ledger = self._delivery_ids(self.LEDGER_URL)
        for delivery_id in sent:
            self.assertIn(
                delivery_id, ledger,
                "게이트 때문에 나간 알림이 발송 대장에서 사라졌습니다 — 그것은 셈을 "
                "고친 것이 아니라 **보낸 적 없음**으로 만든 것입니다 (D-497 · P-193).")

        mine = self._delivery_ids(self.MINE_URL)
        for delivery_id in sent:
            self.assertNotIn(
                delivery_id, mine,
                "같은 행이 일감(M1)에도 섰습니다 — 가른 축은 「보는가 / 누르는가」입니다.")


class NoNewDoorForProbeTest(DsmFixture):
    """★ 조율자 선등록 ㉠ — **probe 를 표기·제외하는 새 문이 나면 빨강.**

    표식은 이미 행 안에 있다(`track_id`). 우리가 할 일은 세는 쪽이고, 새 라우트가
    태어나면 그것은 「지우지 않고 세지 않기」가 아니라 **새 쓰기·읽기 면**이다.
    """

    def test_no_route_declares_a_probe_door(self):
        import inspect

        from apps.dsm import api, api_u1

        offenders = []
        for module in (api, api_u1):
            lines = inspect.getsource(module).splitlines()
            for index, line in enumerate(lines):
                if not line.lstrip().startswith("@route."):
                    continue
                window = " ".join(lines[index:index + 6]).lower()
                if "probe" in window:
                    offenders.append(f"{module.__name__}:{index + 1} {line.strip()}")
        self.assertEqual(
            [], offenders,
            f"probe 를 표기·제외하는 새 라우트가 생겼습니다: {offenders}. "
            f"선등록 ㉠ 이 이것을 빨강으로 못 박았습니다.")
