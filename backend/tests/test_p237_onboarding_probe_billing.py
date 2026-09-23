# -*- coding: utf-8 -*-
"""P-237 「청구서 정직」 — **온보딩 계측기가 만드는 씨앗이 청구로 안 샌다** (2026-09-23 · 턴 AE · 차선 K+Q).

왜 이 파일이 있나
-----------------
`scripts/measure_onboarding_t.py` 는 U5#1(사용자 계정 생성)·U5#4(카메라 일괄 등록)를
**실제 제품 문(HTTP)을 두드려** 잰다 — 그래서 돌 때마다 계정 1·카메라 1이 실제로
청구 셈에 든다. 조율자가 어제 이 배선이 없어서 **정본 회차를 다시 못 돌렸다**
(`docs/workorders/WO-GX-20260923-07_report_wave2.md` §5). 이 시험은 그 배선
(`measure_onboarding_t._mark_probe_unbillable`)이 실제로 청구를 안 늘리는지를
**서버 기록(청구 함수를 직접 부른 수)으로** 잰다 — 화면이 아니라 `apps.dsm.metering.usage()`.

★ **HTTP 를 안 때린다.** 이 시험은 계측기가 만드는 것과 같은 모양의 행(카메라·계정)을
  ORM 으로 직접 만들고, 계측기가 실제로 부르는 그 함수(`_mark_probe_unbillable`)를
  **그대로** 불러 청구 전/후를 잰다. 배선을 복제하지 않는다 — 계측기 소스를
  import 해서 그 함수를 직접 부른다(D-369 — 판정과 코드가 갈리면 아무 말도 안 한다).

★ **음성 대조 셋을 둔다** (이 저장소가 「혼자 재면 통과」로 세 번 되돌린 자리다):
  ① pk 를 못 읽은 경우 — 표식을 안 달고, **조용히 삼키지 않는다**(문자열로 알린다).
  ② 모르는 모델 — 실패를 알리되 호출자(측정 자체)는 안 죽는다.
  ③ **행 자체는 안 고친다** — `StreamMonitor.data_source` 는 표식 뒤에도 `live` 그대로다
     (곁표 `common.BillingMark` 가 대신 든다 · P-224 ②). 이것이 빨강이면 이 파일 전체가
     의미가 없다 — 표식 메커니즘이 아니라 "몰래 감추기"가 됐다는 뜻이기 때문이다.

★ **소유** — 이 시험 파일은 K+Q 몫이다(§2 소유표 · `그 문의 시험 파일`).
  `backend/common/billing_marks.py` 자체의 일반 규약은 `test_b_billing_marks.py`(차선 B)가
  이미 잰다 — 여기서 그 시험을 베끼지 않는다. 이 파일이 새로 묻는 것은 **한 가지**:
  「`measure_onboarding_t.py` 가 실제로 그 규약을 타는가」다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tests.test_b_billing_marks import BillingMarkFixture

#: 저장소 뿌리 후보 — `test_k1_event_kernel.py::_find_gate` 와 같은 자(D-369, 눈 하나).
#: 컨테이너에는 `backend/` 만 `/app` 으로 들어오므로 소스 트리를 되짚는 경로가
#: 안 통한다. `docker-compose` 가 `/repo` 로 뿌리 모양을 넣어 준다.
_REPO_ROOT_CANDIDATES = ("/repo",)


def _find_scripts_dir():
    """`scripts/measure_onboarding_t.py` 가 사는 디렉터리 실경로. 없으면 `None`."""
    here = Path(__file__).resolve()
    roots = [*(Path(c) for c in _REPO_ROOT_CANDIDATES), *here.parents[1:4]]
    for root in roots:
        candidate = root / "scripts" / "measure_onboarding_t.py"
        if candidate.is_file():
            return candidate.parent
    return None


def _import_probe_module():
    """계측기 소스를 **부른다**(베끼지 않는다 · D-369). 못 찾으면 `None`."""
    scripts_dir = _find_scripts_dir()
    if scripts_dir is None:
        return None
    sys.path.insert(0, str(scripts_dir))
    import measure_onboarding_t  # noqa: PLC0415

    return measure_onboarding_t


class MeasureOnboardingProbeBillingWiringFixture(BillingMarkFixture):
    """계측기 소스를 찾아 두고 못 찾으면 **회색(skip)** 으로 적는다 — 초록으로 숨기지 않는다."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._probe_mod = _import_probe_module()

    def setUp(self):
        super().setUp()
        if self._probe_mod is None:
            self.skipTest(
                "scripts/measure_onboarding_t.py 를 못 찾았다 — 컨테이너라면 "
                "docker-compose 의 `./scripts:/repo/scripts:ro` 마운트가 빠진 것이다 "
                "(D-285 (4) 와 같은 자리). 못 잰 것은 초록이 아니다 (D-301)")


# ═══════════════════════════════════════════════════════════════════════════
# ① ★★ 이 파일의 중심 — **카메라·계정이 표식 직후 청구에서 빠진다**
# ═══════════════════════════════════════════════════════════════════════════
class TheProbeCameraStopsBillingRightAfterMarkingTest(
        MeasureOnboardingProbeBillingWiringFixture):
    """U5#4 가 만드는 카메라 — `_mark_probe_unbillable("stream_monitors", "StreamMonitor", …)`."""

    def test_marking_drops_billed_camera_count_by_exactly_one(self):
        cam = self._camera("GX-ONB-PROBE-CAM-1")   # 기본값 live — 만들 때는 청구에 든다
        before_bill = self._bill()["cameras"]

        note = self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", cam.pk, "시험 — 청구 제외")

        self.assertIn(
            "표식 됨", note,
            f"표식이 성공했다고 말하지 않는다 — 사유: {note}")
        self.assertEqual(
            before_bill - 1, self._bill()["cameras"],
            "표식 뒤에도 청구 셈(cameras)이 안 줄었다 — 계측기가 돌 때마다 "
            "청구가 한 칸씩 는다는 뜻이다(조율자가 어제 이 자리에서 막혔다)")

    def test_marking_does_not_touch_the_row_itself(self):
        """★ **행을 안 고친다** (P-224 ②). 곁표가 대신 든다 — 감추는 것이 아니다."""
        cam = self._camera("GX-ONB-PROBE-CAM-2")
        self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", cam.pk, "시험")
        cam.refresh_from_db()
        self.assertEqual(
            "live", cam.data_source,
            "표식이 카메라 행 자체의 data_source 를 고쳤다 — 이 함수는 곁표 "
            "(common.BillingMark) 로만 표식해야 한다. 행을 고치면 다음 사람이 "
            "「이 카메라가 원래 씨앗이었다」로 잘못 읽는다")

    def test_marking_is_visible_to_the_operator_screen(self):
        """P-224 ③ · D-497 — 청구에서 빼도 **운영 면은 그대로 본다.**"""
        cam = self._camera("GX-ONB-PROBE-CAM-3")
        before_screen = self._operator_cameras()
        self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", cam.pk, "시험")
        self.assertEqual(
            before_screen, self._operator_cameras(),
            "표식을 달았더니 관제 화면의 카메라 수가 줄었다 — 청구에서 빼는 것과 "
            "화면에서 감추는 것은 다른 일이다 (D-497)")


class TheProbeAccountStopsBillingRightAfterMarkingTest(
        MeasureOnboardingProbeBillingWiringFixture):
    """U5#1 이 만드는 계정 — `_mark_probe_unbillable("user", "CoreUser", …)`."""

    def test_marking_drops_billed_user_count_by_exactly_one(self):
        user = self._account("gxprobe_onb_test_1")
        before_bill = self._bill()["users"]

        note = self._probe_mod._mark_probe_unbillable(
            "user", "CoreUser", user.pk, "시험 — 청구 제외")

        self.assertIn("표식 됨", note, f"표식이 성공했다고 말하지 않는다 — 사유: {note}")
        self.assertEqual(
            before_bill - 1, self._bill()["users"],
            "표식 뒤에도 청구 셈(users)이 안 줄었다")

    def test_marking_never_deletes_the_account(self):
        """P-222 — 삭제 0. 표식은 청구에서 빼는 것이지 지우는 것이 아니다."""
        user = self._account("gxprobe_onb_test_2")
        CoreUser = user._meta.model
        before_rows = CoreUser._base_manager.count()
        self._probe_mod._mark_probe_unbillable("user", "CoreUser", user.pk, "시험")
        self.assertEqual(before_rows, CoreUser._base_manager.count())
        self.assertTrue(CoreUser._base_manager.filter(pk=user.pk).exists())


# ═══════════════════════════════════════════════════════════════════════════
# ② 음성 대조 — **못 쟀다·못 찾았다를 조용히 삼키지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
class TheWiringFailsLoudlyNotSilentlyTest(MeasureOnboardingProbeBillingWiringFixture):
    """★ 실패해도 측정은 안 죽는다 — 그런데 **성공했다고 거짓말도 안 한다.**"""

    def test_missing_pk_is_not_silently_marked(self):
        from django.apps import apps

        BillingMark = apps.get_model("common", "BillingMark")
        before = BillingMark._base_manager.count()

        note = self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", None, "pk 없음")

        self.assertNotIn(
            "표식 됨", note,
            f"pk 가 없는데(None) 표식이 됐다고 말한다 — {note!r}")
        self.assertEqual(
            before, BillingMark._base_manager.count(),
            "pk 가 없는데도 곁표에 행이 하나 늘었다 — 무엇을 표시했는지 아무도 모른다")

    def test_unknown_model_reports_failure_without_raising(self):
        note = self._probe_mod._mark_probe_unbillable(
            "no_such_app", "NoSuchModel", 1, "존재하지 않는 표")
        self.assertIn(
            "표식 실패", note,
            f"모르는 표를 조용히 넘어간다 — {note!r} (실패를 삼키면 다음 사람이 "
            "「됐다」고 믿는다)")

    def test_calling_twice_does_not_double_count_or_raise(self):
        """`mark_unbillable` 은 `update_or_create` 다 — **두 번 불러도 결과가 같다.**"""
        cam = self._camera("GX-ONB-PROBE-CAM-4")
        n1 = self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", cam.pk, "1차")
        bill_after_1 = self._bill()["cameras"]
        n2 = self._probe_mod._mark_probe_unbillable(
            "stream_monitors", "StreamMonitor", cam.pk, "2차 — 같은 pk")
        self.assertIn("표식 됨", n1)
        self.assertIn("표식 됨", n2)
        self.assertEqual(
            bill_after_1, self._bill()["cameras"],
            "같은 행을 두 번 표식했더니 청구 셈이 또 줄었다 — 표식이 "
            "`update_or_create` 가 아니라 매번 새 곁표 행을 쌓는다는 뜻이다")


# ═══════════════════════════════════════════════════════════════════════════
# ③ 정적 배선 — **U5#1·U5#4 코드가 실제로 이 함수를 부르는가** (D-377 착시 ⑨ 가족)
# ═══════════════════════════════════════════════════════════════════════════
class TheCallSitesActuallyWireTheFunctionTest(MeasureOnboardingProbeBillingWiringFixture):
    """켠 것이 실제로 도는지 — 소스 문자열로 **두 자리 모두**를 확인한다.

    ★ 이 시험은 전체 계측기를 못 돌린다(브라우저·로그인이 필요하다 — 이 차선은
      브라우저를 안 쓴다). 그래서 완전한 증거는 아니다 — 그 사실을 시험 이름에도
      적는다. 그러나 「함수는 있는데 아무도 안 부른다」(D-377) 는 이 시험이 잡는다.
    """

    def test_u5_1_account_creation_calls_the_marker(self):
        src = Path(self._probe_mod.__file__).read_text(encoding="utf-8")
        u5_1_start = src.index("#1 사용자 계정 생성")
        u5_1_end = src.index("out.append(result(\"U5#1\"", u5_1_start)
        block = src[u5_1_start:u5_1_end]
        self.assertIn(
            "_mark_probe_unbillable(", block,
            "U5#1(계정 생성) 블록이 `_mark_probe_unbillable` 을 안 부른다 — "
            "함수는 있어도 잠든 코드다 (D-377)")
        self.assertIn(
            "\"user\", \"CoreUser\"", block,
            "U5#1 블록의 부름이 `user.CoreUser` 를 겨누지 않는다")

    def test_u5_4_camera_import_calls_the_marker(self):
        src = Path(self._probe_mod.__file__).read_text(encoding="utf-8")
        u5_4_start = src.index("#4 카메라 등록")
        u5_4_end = src.index("out.append(result(\"U5#4\"", u5_4_start)
        block = src[u5_4_start:u5_4_end]
        self.assertIn(
            "_mark_probe_unbillable(", block,
            "U5#4(카메라 등록) 블록이 `_mark_probe_unbillable` 을 안 부른다 — "
            "함수는 있어도 잠든 코드다 (D-377)")
        self.assertIn(
            "\"stream_monitors\", \"StreamMonitor\"", block,
            "U5#4 블록의 부름이 `stream_monitors.StreamMonitor` 를 겨누지 않는다")
