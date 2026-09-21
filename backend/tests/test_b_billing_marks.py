# -*- coding: utf-8 -*-
"""P-224 — **씨앗을 청구에서 뺀다. 그런데 화면에서는 안 뺀다** (2026-09-21 · 차선 B).

이 파일이 묻는 것
-----------------
① ★ **계량 전/후 불변** — 표식을 붙여도 **운영·감사 면의 수가 안 변한다.**
   이것이 이 차선에서 가장 중요한 시험이다. 씨앗을 청구에서 빼는 가장 쉬운 길은
   **행을 안 보이게 하는 것**인데, 그러면 운영자가 실물을 못 본다 — 그리고
   **못 보는 것은 못 고친다**(D-497 「거르는 곳은 측정이지 제품이 아니다」).
② **그런데 청구는 정말 주는가** — ①만 재면 *아무것도 안 하는 코드*가 통과한다.
   표식을 단 행이 청구에서 **정확히 빠지는지**를 같은 시험 안에서 잰다.
③ **안 단 행은 그대로 센다** — 기본값이 `live` 다. ②만 재면 *전부 0으로 만드는
   코드*가 통과하고, 0을 돌려주는 계량은 가장 얇고 가장 조용하고 가장 틀렸다.
④ **이름으로 안 거른다** (D-280) — 세는 코드에 `gxseed`·`gxprobe` 라는 낱말이
   **한 글자도 없다.** 다음 사람이 접두를 바꾸면 조용히 새는 길이라서다.
⑤ **삭제 0** (P-222) — 표식을 달아도 행 수는 안 준다.
⑥ **짝 맞추기** — 마이그레이션이 적은 출처 낱말과 `billing_marks` 의 낱말이 같은가.
⑦ **가격표가 비면 회색** (P-223) — 지어내지 않되 개발을 막지 않는다.

★ 이 시험들은 **HTTP 를 한 번도 안 때린다.** 계량 함수를 직접 부르므로 응답 캐시도
  `cache_page` 도 경유하지 않는다 — 「전」과 「후」는 **같은 실행에서 두 번 실제로 센
  수**다. 스레드에 남은 요청은 매번 지운다(남으면 없는 격리가 초록으로 보인다).
"""
import contextlib

from django.apps import apps
from django.utils import timezone

from tests.test_dsm_app import DsmFixture
#: ★ **한 벌만 둔다.** 「독스트링이 아닌 리터럴만 뽑는」 판정은 이미
#:   `test_u56_metering_seeds.py` 에 있다. 여기 한 벌 더 쓰면 두 시험이 다른 뜻으로
#:   같은 이름을 쓰게 되고, 갈라진 쪽이 조용히 이긴다.
from tests.test_u56_metering_seeds import _code_string_literals

#: ★ D-289 — 표본은 저장소 실물이다. 가짜 표를 만들어 재지 않는다.
REAL_SAMPLE = (
    "common.billing_marks · common.models.BillingMark · apps.dsm.metering · "
    "stream_monitors.StreamMonitor.data_source · user.CoreUser — "
    "저장소의 실제 모듈과 표"
)


def _clear_thread_request() -> None:
    """dj-core 가 스레드에 매단 요청을 끊는다. 없으면 조용히 지나간다."""
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class BillingMarkFixture(DsmFixture):
    """다는 손과 재는 손. **시험은 아래 클래스들에 있다**(여긴 0건)."""

    def setUp(self):
        _clear_thread_request()
        self.month = timezone.localtime().strftime("%Y-%m")

    # ── 재는 손 ──────────────────────────────────────────────────────────
    def _bill(self, scope=None):
        """계량이 내는 **청구서의 수**. 부를 때마다 실제로 다시 센다."""
        from apps.dsm.metering import usage

        _clear_thread_request()
        got = usage(scope=scope or self.scope_a, month=self.month)
        return {c["key"]: c["value"] for c in got["cells"]}

    def _operator_cameras(self, group=None):
        """**운영 면** — 관제 화면이 보는 카메라 수. 청구의 거름을 안 지난다."""
        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        return Stream._base_manager.filter(
            group=group or self.group_a, deleted__isnull=True).count()

    def _people(self, group=None):
        """**운영 면** — 사람 관리 화면이 보는 계정 수."""
        CoreUser = apps.get_model("user", "CoreUser")
        return CoreUser._base_manager.filter(
            userprofilelink__group=group or self.group_a,
            is_active=True).distinct().count()

    def _all_rows(self):
        """행이 줄었는가 — **삭제 0**의 자.  표식은 행을 안 지운다."""
        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        CoreUser = apps.get_model("user", "CoreUser")
        return (Stream._base_manager.count(), CoreUser._base_manager.count())

    # ── 다는 손 ──────────────────────────────────────────────────────────
    def _camera(self, code, source=None):
        """카메라 한 대. `source` 를 주면 **만드는 자리에서** 출처를 적는다."""
        from common.billing_marks import BILLABLE_SOURCE

        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        cam = Stream.objects.create(
            name=code, code=code, ip_source="rtsp://dsm.invalid/x",
            data_source=source or BILLABLE_SOURCE)
        return self._own(cam, self.group_a)

    def _account(self, username):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret",
            is_active=True, email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": self.group_a})
        return user


# ═══════════════════════════════════════════════════════════════════════════
# ① ★ 계량 전/후 불변 — **운영·감사 면은 한 줄도 안 빠진다**
# ═══════════════════════════════════════════════════════════════════════════
class TheOperatorStillSeesEverythingTest(BillingMarkFixture):
    """표식을 달아도 **사람이 보는 면은 안 움직인다** (P-224 ③ · D-497).

    ★ 이 셋이 빨강이면 이 차선의 모든 초록이 무효다. 씨앗을 청구에서 빼는 가장 쉬운
      길은 행을 감추는 것이고, 감춘 순간 그것은 「세지 않기」가 아니라 **숨긴 것**이다.
    """

    def test_marking_a_camera_does_not_change_the_operator_camera_list(self):
        cam = self._camera("B-CAM-1")
        before_screen = self._operator_cameras()
        before_bill = self._bill()["cameras"]

        from common.billing_marks import NONBILLABLE_SOURCES

        cam.data_source = NONBILLABLE_SOURCES[0]
        cam.save(update_fields=["data_source"])

        self.assertEqual(
            before_screen, self._operator_cameras(),
            "표식을 달았더니 **관제 화면의 카메라 수가 줄었습니다.** 청구에서 빼는 "
            "것과 화면에서 감추는 것은 다른 일입니다 — 감춘 카메라는 아무도 "
            "못 고칩니다 (D-497).")
        self.assertEqual(
            before_bill - 1, self._bill()["cameras"],
            "화면은 그대로인데 **청구도 그대로입니다** — 표식이 셈에 안 걸렸습니다.")

    def test_marking_an_account_does_not_change_the_people_list(self):
        from common.billing_marks import SEED_SOURCE, mark_unbillable

        user = self._account("dsm_probe_account_1")
        before_screen = self._people()
        before_bill = self._bill()["users"]

        mark_unbillable(user, SEED_SOURCE, reason="시험이 만든 계정 — 청구 제외")

        self.assertEqual(
            before_screen, self._people(),
            "표식을 달았더니 **사람 관리 화면의 계정 수가 줄었습니다.** 곁표는 "
            "남의 행을 한 자도 안 건드려야 합니다 (P-224 ②).")
        self.assertEqual(
            before_bill - 1, self._bill()["users"],
            "화면은 그대로인데 **청구도 그대로입니다** — 곁표가 셈에 안 걸렸습니다.")

    def test_marking_never_removes_a_row(self):
        """**삭제 0** (P-222). 씨앗 행을 지우는 것이 아니라 청구에서 빼는 것이다."""
        from common.billing_marks import NONBILLABLE_SOURCES, mark_unbillable

        cam = self._camera("B-CAM-2")
        user = self._account("dsm_probe_account_2")
        before = self._all_rows()

        cam.data_source = NONBILLABLE_SOURCES[0]
        cam.save(update_fields=["data_source"])
        mark_unbillable(user, NONBILLABLE_SOURCES[0], reason="시험")

        self.assertEqual(
            before, self._all_rows(),
            "표식을 다는 동안 **행이 사라졌습니다.** 삭제는 이 턴에 0건이고 "
            "대표 자리입니다 (P-222).")

    def test_the_audit_trail_does_not_shrink(self):
        """**감사 면도 안 줄어든다.** 청구가 안 보는 것과 감사가 안 보는 것은 다르다."""
        from common.billing_marks import SEED_SOURCE, mark_unbillable

        AuditLogs = apps.get_model("logger", "AuditLogs")
        user = self._account("dsm_probe_account_3")
        before = AuditLogs._base_manager.count()

        mark_unbillable(user, SEED_SOURCE, reason="시험이 만든 계정 — 청구 제외")

        self.assertLessEqual(
            before, AuditLogs._base_manager.count(),
            "표식을 다는 동안 **감사 줄이 사라졌습니다.** 대장은 줄지 않습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ②③ 청구는 주는가 · 안 단 행은 그대로 세는가
# ═══════════════════════════════════════════════════════════════════════════
class TheBillMovesInBothDirectionsTest(BillingMarkFixture):
    """★ **한 방향만 재면 거짓 초록이 통과한다.**

    ② 만 재면 *전부 0으로 만드는 코드*가 통과하고, ③ 만 재면 *아무것도 안 하는
    코드*가 통과한다. 두 방향을 **같은 클래스 안에서** 잰다.
    """

    def test_an_unmarked_camera_is_still_billed(self):
        before = self._bill()["cameras"]
        self._camera("B-CAM-LIVE")
        self.assertEqual(
            before + 1, self._bill()["cameras"],
            "표식 없는 카메라가 청구에서 빠졌습니다 — **기본값이 고객 쪽이 "
            "아닙니다.** 그러면 표식을 안 단 고객 카메라가 조용히 공짜가 되고, "
            "공짜가 된 것은 아무도 말해 주지 않습니다.")

    def test_a_new_camera_is_born_billable(self):
        from common.billing_marks import BILLABLE_SOURCE

        cam = self._camera("B-CAM-DEFAULT")
        cam.refresh_from_db()
        self.assertEqual(
            BILLABLE_SOURCE, cam.data_source,
            "새 카메라의 기본 출처가 고객 쪽이 아닙니다 (P-224 ①).")

    def test_every_nonbillable_source_is_actually_subtracted(self):
        """`probe` · `seed` · `drill` **셋 다** 빠지는가 — 하나만 재지 않는다."""
        from common.billing_marks import NONBILLABLE_SOURCES

        for source in NONBILLABLE_SOURCES:
            before = self._bill()["cameras"]
            self._camera(f"B-CAM-{source}", source=source)
            self.assertEqual(
                before, self._bill()["cameras"],
                f"출처 {source!r} 인 카메라가 청구에 들었습니다 — 우리가 심은 "
                f"카메라에 고객이 돈을 냅니다.")

    def test_the_other_tenant_bill_never_moves(self):
        """B 테넌트에 무엇을 해도 A 의 청구서는 안 움직인다."""
        before = self._bill(self.scope_b)
        self._camera("B-CAM-TENANT")
        self._account("dsm_probe_account_tenant")
        self.assertEqual(
            before, self._bill(self.scope_b),
            "남의 테넌트 청구서가 움직였습니다 — 틀린 청구가 아니라 유출입니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ④ **이름으로 안 거른다** (D-280)
# ═══════════════════════════════════════════════════════════════════════════
class TheCountingCodeDoesNotKnowOurNamesTest(BillingMarkFixture):
    """세는 코드가 `gxseed_*`·`gxprobe_*` 라는 **낱말을 세지 않는가.**

    ★ 다음 사람이 접두를 바꾸면 조용히 새는 길이고, 고객 이름 하나가 우리 접두와
      겹치면 **그 계정이 조용히 공짜가 된다.** 그래서 표식으로 거른다.
    ★ **소급 한 번은 이름을 근거로 썼다** — 그 목록은 마이그레이션 안에 pk 로 얼어
      있고, 규칙이 아니라 장부다. 이 시험이 보는 것은 **세는 코드**다.
    """

    #: 세는 코드에 있으면 안 되는 낱말들. 우리 씨앗의 이름이다.
    FORBIDDEN = ("gxseed", "gxprobe", "GX-SEED", "GX-ONB", "GX-DRILL", "GX-U5")

    def test_the_billing_rule_has_no_name_prefix_in_it(self):
        import inspect

        from apps.dsm import metering
        from common import billing_marks

        for module in (billing_marks, metering):
            literals = _code_string_literals(inspect.getsource(module))
            bad = sorted(s for s in literals
                         if any(w.lower() in s.lower() for w in self.FORBIDDEN))
            self.assertEqual(
                [], bad,
                f"{module.__name__} 의 **코드**가 우리 씨앗의 이름 {bad} 을 "
                f"적습니다. 이름은 표식이 아니라 추측이고, 추측이 청구 근거가 되는 "
                f"순간 접두가 겹친 고객 계정이 조용히 공짜가 됩니다 (D-280).")

    def test_the_billing_rule_does_not_look_at_names_at_all(self):
        import inspect

        from common import billing_marks

        literals = _code_string_literals(inspect.getsource(billing_marks))
        bad = sorted(s for s in literals
                     if s.startswith(("username", "name", "code", "email")))
        self.assertEqual(
            [], bad,
            f"청구의 거름이 이름 칸 {bad} 을 봅니다. 봐야 하는 것은 표식뿐입니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ⑥ 짝 맞추기 — **낱말이 갈리면 한쪽이 조용히 이긴다**
# ═══════════════════════════════════════════════════════════════════════════
class TheWordsAgreeTest(BillingMarkFixture):

    def test_the_migrations_use_the_same_words_as_the_billing_side(self):
        """마이그레이션은 앱 코드를 import 하지 않는 것이 규약이다(과거 상태를 보아야
        한다). 그래서 낱말을 **옮겨 적었고**, 옮겨 적은 순간 두 벌이 된다 —
        **이 시험이 그 짝을 지킨다.**
        """
        import importlib

        from common.billing_marks import (BILLABLE_SOURCE, NONBILLABLE_SOURCES,
                                          SEED_SOURCE)

        cam = importlib.import_module(
            "stream_monitors.migrations.0031_p224_camera_data_source")
        acct = importlib.import_module(
            "common.migrations.0003_p224_seed_account_marks")

        self.assertEqual(BILLABLE_SOURCE, cam.LIVE)
        for word in (cam.PROBE, cam.SEED, cam.DRILL, acct.PROBE, acct.SEED):
            self.assertIn(
                word, NONBILLABLE_SOURCES,
                f"마이그레이션이 적은 출처 {word!r} 를 청구의 셈이 모릅니다 — "
                f"그 행은 표식을 달고도 청구에 듭니다.")
        self.assertEqual(SEED_SOURCE, cam.SEED)

        CoreUser = apps.get_model("user", "CoreUser")
        self.assertEqual(
            CoreUser._meta.label_lower, acct.MODEL_LABEL,
            "곁표가 가리키는 표 이름이 실제 계정 표와 다릅니다 — 그 표식은 "
            "아무 행도 안 가립니다.")

    def test_the_camera_column_is_named_after_the_marker(self):
        from common.billing_marks import DATA_SOURCE_FIELD
        from common.probe_marker import PROBE_MARKER

        self.assertEqual(
            PROBE_MARKER.split("=", 1)[0], DATA_SOURCE_FIELD,
            "칸 이름이 표식의 낱말과 갈렸습니다.")
        Stream = apps.get_model("stream_monitors", "StreamMonitor")
        self.assertIn(
            DATA_SOURCE_FIELD, {f.name for f in Stream._meta.get_fields()},
            "카메라 표에 청구 출처 칸이 없습니다 (P-224 ①).")

    def test_the_event_marker_still_has_its_field(self):
        """★ **`track_id` 가 사라진 날 조용히 통과되지 않게.**

        예전에는 `exclude_unbillable` 이 FieldError 로 큰 소리를 내는 것이 이
        역할이었는데, 칸이 없는 표(`CoreUser`)에도 그 함수가 걸리게 된 뒤로는
        그 소리를 낼 수 없다. 그래서 그 소리를 **이 시험이** 낸다.
        """
        from common.probe_marker import PROBE_FIELD

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertIn(
            PROBE_FIELD, {f.name for f in Event._meta.get_fields()},
            f"사건 표에 표식 칸({PROBE_FIELD})이 없습니다 — K1 의 청구 거름이 "
            f"**조용히 통과**가 됩니다 (P-193).")

    def test_the_words_are_not_typed_twice(self):
        """`probe`·`drill` 은 `probe_marker` 에서만 온다 — 여기서 다시 안 적는다."""
        from common.billing_marks import NONBILLABLE_SOURCES, SEED_SOURCE
        from common.probe_marker import DRILL_MARKER, PROBE_MARKER

        self.assertEqual(
            (PROBE_MARKER.split("=", 1)[1], DRILL_MARKER.split("=", 1)[1],
             SEED_SOURCE),
            tuple(NONBILLABLE_SOURCES),
            "청구가 아는 출처 낱말이 표식 정본과 갈렸습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ② 발급 순간의 표식 — `mark_unbillable`
# ═══════════════════════════════════════════════════════════════════════════
class TheMarkIsWrittenWhereTheRowIsBornTest(BillingMarkFixture):

    def test_marking_twice_leaves_one_row(self):
        """씨앗 명령을 두 번 돌려도 표식은 한 줄이다."""
        from common.billing_marks import SEED_SOURCE, mark_unbillable

        BillingMark = apps.get_model("common", "BillingMark")
        user = self._account("dsm_probe_account_twice")
        mark_unbillable(user, SEED_SOURCE, reason="첫 번째")
        mark_unbillable(user, SEED_SOURCE, reason="두 번째")
        self.assertEqual(
            1, BillingMark._base_manager.filter(
                model_label=user._meta.label_lower,
                object_id=str(user.pk)).count(),
            "한 행에 표식이 둘입니다 — 어느 쪽이 정본인지 아무도 못 답합니다.")

    def test_an_unknown_source_is_refused(self):
        """모르는 낱말은 **거절한다.** 부르는 자리에서 새 낱말이 태어나면 청구가
        그 뜻을 모른 채 그 행을 센다."""
        from common.billing_marks import mark_unbillable

        user = self._account("dsm_probe_account_bad")
        with self.assertRaises(ValueError):
            mark_unbillable(user, "free_for_a_friend", reason="시험")

    def test_marking_a_row_billable_keeps_it_in_the_bill(self):
        """`live` 로 적는 것은 **표식이 아니라 확인**이다 — 청구에 그대로 든다."""
        from common.billing_marks import BILLABLE_SOURCE, mark_unbillable

        user = self._account("dsm_live_account")
        before = self._bill()["users"]
        mark_unbillable(user, BILLABLE_SOURCE, reason="고객 계정임을 확인했다")
        self.assertEqual(
            before, self._bill()["users"],
            "고객으로 적었는데 청구에서 빠졌습니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ⑦ 가격표 — **비면 회색** (§4-5 · P-223)
# ═══════════════════════════════════════════════════════════════════════════
class ThePriceTableIsEmptyOnPurposeTest(BillingMarkFixture):
    """★ 값이 없으면 **회색**이다. 지어내지 않되 개발을 막지 않는다.

    ⚠ 이 시험은 **09-28 대표 확인 뒤 빨강이 된다** — 그때 값이 차기 때문이다.
      그것이 이 시험의 목적이다: 값이 차는 날 이 클래스가 손을 들고, 그 손을 보고
      다음 사람이 「회색이던 줄이 이제 초록인가」를 확인한다.
    """

    def test_the_four_numbers_are_still_empty(self):
        from apps.dsm.metering import load_price_table

        table = load_price_table()
        for key in ("center_base_year", "camera_month", "seat_month",
                    "golden_time_option_rate"):
            self.assertIsNone(
                table.get(key),
                f"가격표의 {key} 에 값이 들어왔습니다. 09-28 대표 확인 전까지 그 "
                f"수는 정본이 아니고, 확인 안 된 수로 낸 청구서는 못 되돌립니다.")

    def test_the_drill_line_is_zero_not_empty(self):
        """**0원과 미확정은 다른 사실이다.** 훈련은 정해졌다."""
        from apps.dsm.metering import load_price_table

        self.assertEqual(
            0, load_price_table().get("drill_month"),
            "훈련 단가가 비었습니다 — 훈련은 0원으로 **정해졌습니다** (P-224 ⑤).")

    def test_an_unpriced_line_comes_out_grey_not_zero(self):
        from apps.dsm.metering import UNPRICED, invoice_draft

        self._camera("B-CAM-PRICED")
        draft = invoice_draft(scope=self.scope_a, month=self.month)
        cameras = [ln for ln in draft["lines"] if ln["key"] == "cameras"][0]
        self.assertEqual(UNPRICED, cameras["state"])
        self.assertIsNone(
            cameras["amount"],
            "단가가 없는데 금액이 나왔습니다 — 지어낸 수입니다.")
        self.assertFalse(
            draft["is_total"],
            "회색 줄이 있는데 **총액**이라고 말합니다. 부분합을 총액이라 부르면 "
            "그 수로 청구서가 나갑니다.")

    def test_the_drill_line_is_not_grey(self):
        """훈련 줄만은 **못 잰 채로도 금액이 확정**이다 (0 × 무엇이든 0)."""
        from apps.dsm.metering import invoice_draft

        draft = invoice_draft(scope=self.scope_a, month=self.month)
        drill = [ln for ln in draft["lines"] if ln["key"] == "drill"][0]
        self.assertEqual(0, drill["amount"])
        self.assertEqual("ok", drill["state"])

    def test_the_price_table_folder_is_data_only(self):
        """⚠ `metering/` 에 `__init__.py` 가 생기면 **정규 패키지가 되어
        `metering.py` 를 가린다** — 계량이 통째로 사라진다."""
        from pathlib import Path

        from apps.dsm import metering

        folder = Path(metering.PRICE_TABLE_PATH).parent
        self.assertTrue(folder.is_dir(), "가격표 자리가 없습니다.")
        self.assertFalse(
            (folder / "__init__.py").exists(),
            "metering/ 에 __init__.py 가 생겼습니다 — 그 순간 이 디렉터리가 "
            "apps.dsm.metering 을 가리고 계량이 통째로 사라집니다.")
        self.assertTrue(
            Path(metering.__file__).is_file(),
            "apps.dsm.metering 이 모듈 파일이 아닙니다.")


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 「이번 달 사용량」이 **무엇을 뺐는지 말하는가** (P-224 ⑤)
# ═══════════════════════════════════════════════════════════════════════════
class TheUsageSaysWhatItLeftOutTest(BillingMarkFixture):

    def test_the_usage_declares_the_exclusion(self):
        from apps.dsm.metering import usage

        got = usage(scope=self.scope_a, month=self.month)
        self.assertIn("exclusions", got)
        self.assertTrue(got["exclusions"]["note"].strip())
        self.assertTrue(got["exclusions"]["drill_is_free"])

    def test_the_unmeasured_storage_is_named_not_hidden(self):
        """저장의 씨앗 몫은 **0이 아니라 못 쟀다**. 뭉뚱그리지 않는다 (D-301)."""
        from apps.dsm.metering import usage

        got = usage(scope=self.scope_a, month=self.month)
        self.assertIn("storage", got["exclusions"]["not_applied"])
        self.assertNotIn("storage", got["exclusions"]["applies_to"])
