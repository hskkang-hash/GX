# -*- coding: utf-8 -*-
"""★★ **감사 화면의 「대상」 칸** — 삭제된 사건을 「없음」이라고 적지 않는다 (턴 Y · P-208 U24 ①).

무엇이 이 파일을 만들게 했나 — **실제로 있었던 삭제**
-----------------------------------------------------
대표 결정으로 2026-09-19~20 에 씨앗 **177행**이 지워졌다(사건 16 + 발송 145 + 클립 16).
차선 S 가 그 뒤 해시 체인을 재고 이렇게 적었다:

    체인은 「이 행이 **안 고쳐졌다**」를 증명할 뿐
    **「가리키는 대상이 아직 있다」는 증명하지 않는다.** 삭제 뒤 감사의 값은 그만큼 줄었다.

그 말이 옳다. 그리고 화면은 그 사실을 **한 자도 말하지 않고** `upper_report:set:231073`
만 적어 두고 있었다 — 묻지 않으면 사람은 **그 231073 이 아직 있는 것으로 읽는다.**

★ **수는 한 건도 안 바뀐다.** 이 파일의 첫 클래스가 그것을 잰다(`total`·`pages`·행 수).
  바뀌는 것은 **그 0 이 무엇인지 말하는 것**뿐이다.

★ 갈래가 **셋**이다 — 둘로 적으면 또 거짓말이 된다
--------------------------------------------------
    live                 아직 있다
    deleted_by_decision  없다 **그리고** 09-20 스냅샷에 그 id 가 있다
    gone                 없다 **그리고** 스냅샷에 없다   ← **회색이다. 초록이 아니다**

「없으면 삭제된 것」으로 적으면 기록 없이 사라진 행까지 「대표가 지웠다」는 근거로 읽힌다
(D-280 — 모르는 칸을 그럴듯하게 채우면 그 값이 나중에 근거처럼 읽힌다). 그래서 이 파일은
**셋을 한 번에** 잰다: 한 갈래만 재면 「전부 gone」인 코드도, 「전부 deleted」인 코드도 통과한다.

★ 상수와 **스냅샷 파일**을 대 본다
----------------------------------
제품은 요청마다 `docs/` 를 읽지 않는다(컨테이너에 없을 수 있고, 증거 폴더가 제품의
의존이 되면 그 폴더는 더 이상 증거가 아니다). 그래서 id 열여섯은 `api_u24` 의 상수다 —
그리고 그 상수가 스냅샷과 **갈리지 못하게** 여기서 둘을 대 본다. 대 보지 않으면
「스냅샷 있음」이라는 화면 글자가 언젠가 **스냅샷에 없는 id** 에도 붙는다.

★ 함수가 아니라 **문을 두드린다** (D-210)
-----------------------------------------
`_with_target_column()` 을 직접 불러 재면 라우트가 그것을 부르는지를 못 본다 — 턴 U 의
체인 칸이 꼭 그 모양으로 라우트에서 빠질 뻔했다. `GET /api/dsm/audit` 를 누른다.

캐시 처리: 우회 — `TurnTFixture` 가 `Client(**NO_CACHE)` 와 `cache.clear()` 를 쓴다
(`X-No-Cache` · D-341 착시 ⑦). **이 파일이 막는 것**: 같은 사건을 「있는 채로 · 지운 뒤」
두 번 누른다. 적중 본문이 돌아오면 지운 **뒤**의 요청이 지우기 **전**의 `live` 를 그대로
받아 **「삭제된 사건」을 재는 줄이 조용히 초록**이 된다 — 즉 이 파일이 잡으려는 바로 그
거짓말이 캐시에 덮인다.
"""
from __future__ import annotations

import json
import pathlib

from django.test import override_settings

from apps.dsm import api_u24
from tests.test_api_contract import _bearer
from tests.test_u24_turn_t import AUDIT, TurnTFixture, _upper

#: 스냅샷 — 대표 결정 09-20 의 삭제를 적어 둔 유일한 자리.
#: 컨테이너 마운트가 셋이라 저장소 뿌리 기준 경로가 안 맞을 수 있다(`/docs` 가 따로 선다).
#: 그래서 **후보를 둘 다** 본다 — 못 찾으면 **빨강**이다(회색이 아니다: 이 파일이 재는
#: 사실의 절반이 그 파일에 있고, 「못 읽었다」를 초록으로 적을 자리가 없다).
_SNAPSHOT_REL = "docs/agent/evidence/P-184/deleted_probe_snapshot_20260920.json"
_SNAPSHOT_CANDIDATES = (
    pathlib.Path(__file__).resolve().parents[2] / _SNAPSHOT_REL,   # 호스트 저장소
    pathlib.Path("/docs/agent/evidence/P-184/deleted_probe_snapshot_20260920.json"),
)


def _snapshot_event_ids() -> set[int]:
    for path in _SNAPSHOT_CANDIDATES:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {int(row["pk"]) for row in data["events"]}
    raise AssertionError(
        "09-20 스냅샷을 못 찾았다 — 본 자리: "
        + " · ".join(str(p) for p in _SNAPSHOT_CANDIDATES)
        + "\n  이 파일이 재는 사실의 절반이 그 파일에 있다. 못 읽은 것은 초록이 아니다.")


class TheDeletedIdsMatchTheSnapshotTest(TurnTFixture):
    """★★ **상수 ↔ 스냅샷.** 화면의 「스냅샷 있음」이 거짓이 되지 못하게 둘을 대 본다."""

    def test_the_constant_is_exactly_the_snapshot_event_ids(self) -> None:
        got = set(api_u24.DELETED_EVENT_IDS)
        want = _snapshot_event_ids()
        self.assertEqual(
            got, want,
            "상수와 스냅샷이 갈렸다. "
            f"상수에만={sorted(got - want)} · 스냅샷에만={sorted(want - got)}\n"
            "  ⚠ 갈린 채로 두면 화면이 **스냅샷에 없는 id** 에 「스냅샷 있음」을 붙인다.")

    def test_the_denominator_is_not_zero(self) -> None:
        """분모 0 인 초록은 초록이 아니다 — 스냅샷이 비면 위 시험은 언제나 통과한다."""
        self.assertEqual(16, len(api_u24.DELETED_EVENT_IDS),
                         "09-20 삭제의 사건은 열여섯이었다(177행 = 16 + 145 + 16)")

    def test_the_decision_is_named_not_guessed(self) -> None:
        """「누가 · 언제」가 상수로 서 있다 — 화면이 지어내는 말이 아니다."""
        self.assertEqual("2026-09-20", api_u24.DELETED_EVENT_DECIDED_ON)
        self.assertIn("대표", api_u24.DELETED_EVENT_DECISION)
        self.assertTrue(api_u24.DELETED_EVENT_SNAPSHOT.endswith(".json"))
        self.assertIn("P-184", api_u24.DELETED_EVENT_SNAPSHOT)


class TheActionShapeIsPinnedTest(TurnTFixture):
    """★ **아무 숫자나 사건 id 로 읽지 않는다.** 읽으면 설정 변경의 숫자가 사건이 된다."""

    def test_only_the_upper_report_shape_points_at_an_event(self) -> None:
        points = {
            "upper_report:set:231073": 231073,
            "upper_report:clear:9": 9,
            #: ↓ 이 셋이 사건으로 읽히면 화면에 없는 사건이 무더기로 뜬다(실측 모양들)
            "write:inbound_api_key:rotate:7": None,
            "read:system:backup-receipts": None,
            "write:people:deactivate:3": None,
            "": None,
        }
        got = {k: api_u24.target_event_id(k) for k in points}
        self.assertEqual(got, points, got)


class TheNumbersDoNotMoveTest(TurnTFixture):
    """★★ **수는 안 바뀐다.** 이 턴이 바꾼 것은 「그 0 이 무엇인가」뿐이다.

    라우트가 낸 쪽과 **뒷면(`audit.read_page`)** 이 낸 쪽을 같은 필터로 대 본다.
    `total`·`pages`·행 수가 한 자라도 움직이면 이 칸은 수를 만진 것이다.
    """

    def test_total_pages_and_row_count_are_untouched(self) -> None:
        from apps.dsm import audit
        from common.tenant_scope import TenantScope

        e1 = self._event(self.stream_a)
        self.assertEqual(200, self.client.post(_upper(e1), **_bearer(self.manager_a)).status_code)
        self.assertEqual(200, self.client.delete(_upper(e1), **_bearer(self.manager_a)).status_code)

        body = self.client.get(AUDIT, **_bearer(self.manager_a)).json()
        raw = audit.read_page(scope=TenantScope.of(self.manager_a), page=1, page_size=50)
        self.assertEqual(
            (body["total"], body["pages"], len(body["items"])),
            (raw["total"], raw["pages"], len(raw["items"])),
            "「대상」 칸이 수를 만졌다 — 이 칸은 수를 세지 않는다")
        self.assertGreater(raw["total"], 0, "분모 0 이면 위 대조는 아무것도 안 잰다")

    def test_the_denominator_of_the_targets_is_the_page_itself(self) -> None:
        """네 갈래의 합 == 이 쪽의 행 수. 합이 모자라면 **안 센 행**이 있는 것이다."""
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        body = self.client.get(AUDIT, **_bearer(self.manager_a)).json()
        states = body["target_states"]
        self.assertEqual(sum(states.values()), len(body["items"]), states)


class TheThreeStatesAreDrawnTest(TurnTFixture):
    """★★ **셋을 한 번에 잰다** — 한 갈래만 재면 「전부 gone」도 「전부 deleted」도 통과한다."""

    def _press_and_read(self, event_id: int) -> dict:
        r = self.client.get(AUDIT, {"action": f"upper_report:set:{event_id}"},
                            **_bearer(self.manager_a)).json()
        self.assertEqual(1, r["total"], r)
        return r["items"][0]

    def test_a_living_event_is_live(self) -> None:
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        target = self._press_and_read(e1)["target"]
        self.assertEqual((api_u24.TARGET_LIVE, e1), (target["state"], target["event_id"]))
        self.assertIsNone(target["decided_on"],
                          "살아 있는 사건에 「대표 결정」이 붙으면 그것이 새 거짓말이다")

    def test_an_event_deleted_without_a_record_says_so(self) -> None:
        """★ **회색을 회색으로.** 기록 없이 사라진 행은 「대표가 지웠다」가 아니다."""
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        self._hard_delete(e1)
        target = self._press_and_read(e1)["target"]
        self.assertEqual(api_u24.TARGET_GONE, target["state"])
        self.assertIsNone(target["snapshot"],
                          "스냅샷에 없는 id 에 「스냅샷 있음」이 붙으면 증거가 거짓이 된다")

    def test_an_event_in_the_snapshot_says_the_decision_and_the_snapshot(self) -> None:
        """★★ **이 줄이 「대상 없음」을 멎게 한다.**

        상수를 이 시험 동안만 넓힌다 — 재는 것은 **갈래를 가르는가**이고, 상수가
        스냅샷과 같은가는 `TheDeletedIdsMatchTheSnapshotTest` 가 따로 잰다.
        한 시험에 두 사실을 담으면 어느 쪽이 깨졌는지 이름으로 못 읽는다.
        """
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        self._hard_delete(e1)
        widened = frozenset(set(api_u24.DELETED_EVENT_IDS) | {e1})
        with _swap(api_u24, "DELETED_EVENT_IDS", widened):
            target = self._press_and_read(e1)["target"]
        self.assertEqual(api_u24.TARGET_DELETED_BY_DECISION, target["state"])
        self.assertEqual("2026-09-20", target["decided_on"])
        self.assertIn("대표", target["decision"])
        self.assertIn("P-184", target["snapshot"])

    def test_a_row_that_points_at_nothing_is_not_a_missing_target(self) -> None:
        """★ 「대상이 애초에 없다」와 「대상이 사라졌다」를 같은 글자로 적지 않는다."""
        from apps.dsm import audit
        from common.tenant_scope import TenantScope

        audit.record(scope=TenantScope.of(self.manager_a), action="write:thresholds",
                     outcome=audit.ALLOWED, reason="시험", api_name="write:thresholds",
                     api_method="POST", status_http=200)
        r = self.client.get(AUDIT, {"action": "write:thresholds"},
                            **_bearer(self.manager_a)).json()
        self.assertEqual(1, r["total"], r)
        self.assertIsNone(r["items"][0]["target"])
        self.assertEqual(1, r["target_states"]["none"])

    def _hard_delete(self, event_id: int) -> None:
        """씨앗 삭제와 **같은 모양**으로 지운다 — 행이 표에서 사라진다(소프트 삭제 아님).

        대표 결정 09-20 이 한 일이 그것이다(S 가 확인: 감사 행을 데려가는 FK 는 없다).
        """
        from django.apps import apps

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        deleted, _ = Event._base_manager.filter(pk=event_id).delete()
        self.assertGreater(deleted, 0, "사건을 못 지웠다 — 이 시험은 아무것도 안 잰다")


class _swap:
    """상수 하나를 시험 동안만 바꾼다. `override_settings` 의 모듈 판."""

    def __init__(self, module, name: str, value) -> None:
        self.module, self.name, self.value = module, name, value

    def __enter__(self):
        self.old = getattr(self.module, self.name)
        setattr(self.module, self.name, self.value)
        return self.value

    def __exit__(self, *exc) -> None:
        setattr(self.module, self.name, self.old)


class TheCsvSaysTheSameThingTest(TurnTFixture):
    """★ **파일과 표가 같은 사실을 말한다.** 화면에 생긴 열은 파일에도 선다.

    턴 U 가 적어 둔 규약이다: 「파일이 표와 다른 사실을 말하면 둘 중 어느 쪽이 맞는지
    아무도 모른다」. 열을 화면에만 더하면 그 순간 두 장이 갈린다.
    """

    def test_the_export_carries_the_target_columns(self) -> None:
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        self._hard_delete_one(e1)
        r = self.client.get("/api/dsm/audit/export.csv", **_bearer(self.manager_a))
        self.assertEqual(200, r.status_code)
        text = r.content.decode("utf-8-sig")
        header = text.splitlines()[0].split(",")
        self.assertIn("target_event_id", header)
        self.assertIn("target_state", header)
        self.assertIn(api_u24.TARGET_GONE, text)

    def test_the_tail_row_is_as_wide_as_the_header(self) -> None:
        """★ 꼬리 줄의 빈 칸이 **머리글에서 세어진다** — 손으로 박힌 열셋이 아니다.

        손으로 박아 두면 열이 늘 때마다 꼬리 줄만 조용히 짧아지고, 표 계산기에서
        「잘림」이 엉뚱한 열에 선다(사람이 읽는 자리가 어긋난다).
        """
        e1 = self._event(self.stream_a)
        self.client.post(_upper(e1), **_bearer(self.manager_a))
        r = self.client.get("/api/dsm/audit/export.csv", **_bearer(self.manager_a))
        lines = [ln for ln in r.content.decode("utf-8-sig").splitlines() if ln.strip()]
        self.assertEqual(len(lines[0].split(",")), len(lines[-1].split(",")),
                         "꼬리 줄이 머리글과 폭이 다르다")

    def _hard_delete_one(self, event_id: int) -> None:
        from django.apps import apps

        apps.get_model("stream_monitors", "DetectionEvent")._base_manager.filter(
            pk=event_id).delete()


class TheOtherTenantsEventIsNotProbedTest(TurnTFixture):
    """★ **존재 여부가 새지 않는다.** 남의 테넌트 사건은 커널이 404 로 답한다.

    그래서 이 칸은 남의 사건을 `live` 로 적을 수 없다 — 적으면 「그 id 는 있다」가
    새는 것이고, `get_event` 가 403 대신 404 를 쓰는 이유가 바로 그것이다.
    """

    @override_settings(READONLY_ROLE_GATE_ENABLED=True)
    def test_the_column_never_reports_live_for_a_foreign_event(self) -> None:
        eb = self._event(self.stream_b)
        self.assertEqual(200, self.client.post(_upper(eb), **_bearer(self.manager_b)).status_code)
        #: B 의 감사 행은 A 에게 아예 안 보인다(테넌트 격리) — 그것이 첫 번째 울타리다.
        a_body = self.client.get(AUDIT, **_bearer(self.manager_a)).json()
        self.assertFalse(any(f":{eb}" in i["action"] for i in a_body["items"]))
        #: 그리고 두 번째 울타리: 해석기 자체가 남의 사건을 못 본다.
        from common.tenant_scope import TenantScope

        state = api_u24._resolve_event_target(eb, scope=TenantScope.of(self.manager_a))
        self.assertNotEqual(api_u24.TARGET_LIVE, state,
                            "남의 테넌트 사건이 `live` 로 새어 나왔다")
