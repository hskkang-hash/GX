# -*- coding: utf-8 -*-
"""K5 표 ① 임계값 — **F-02 「지점별 기준선 설정」 · F-12 「임계값」** (D-325).

이 시험이 묻는 것 넷
--------------------
    ① **없는 값을 0 이라고 하지 않는가**   F-02 의 기준선은 아직 없다. 없으면 멈춘다(D-284)
    ② **좁은 것이 이기는가**               camera → tenant → global. 지점별이 계약이다
    ③ **계약을 설정으로 어길 수 없는가**   F-04 5분 · F-10 30초는 취향이 아니라 계약이다
    ④ **왜 바꿨는지가 남는가**             변경 이력 — 무엇에서 무엇으로, 누가, 왜

③이 이 표 고유의 위험이다. "임계값을 설정 가능하게 만들었다" 가 곧
**"계약 AC 를 설정 가능하게 만들었다"** 가 되면, 표가 갚으려던 절을 표가 부순다.

★ D-289 — 표본은 저장소 실물이다: `kernels.k5_trust` 공개 면과 실제 모델을 쓴다.
"""
from __future__ import annotations

from django.test import TestCase

from tests.test_dsm_app import DsmFixture


class ThresholdTableTest(DsmFixture):
    """표 ①의 계약."""

    # ── ① 없는 값을 0 이라고 하지 않는다 ────────────────────────────────
    def test_the_waterlevel_baseline_has_no_invented_default(self) -> None:
        """★ F-02 — **기본값을 지어내지 않았다.** 지어내면 그 숫자가 AC 판정 근거가 된다.

        「기준선 0cm」는 **모든 신호가 초과**라는 뜻이다. 조용한 0 이 가장 위험하다.
        """
        from kernels.k5_trust import ThresholdNotSet, resolve_threshold

        with self.assertRaises(ThresholdNotSet):
            resolve_threshold("waterlevel.baseline", scope=self.scope_a, camera_id=self.stream_a.pk)

    def test_an_unknown_key_is_refused_not_defaulted(self) -> None:
        """오타 하나가 **새 임계값**이 되지 않는다."""
        from kernels.k5_trust import ThresholdNotDefined, resolve_threshold

        with self.assertRaises(ThresholdNotDefined):
            resolve_threshold("waterlevel.baseIine", scope=self.scope_a)   # 대문자 I 오타

    # ── ② 좁은 것이 이긴다 ──────────────────────────────────────────────
    def test_the_narrower_scope_wins(self) -> None:
        """★ F-02 「**지점별** 기준선 설정」 — 계약이 지점별이라고 못박았다."""
        from kernels.k5_trust import resolve_threshold, set_threshold

        set_threshold(scope=self.scope_a, key="waterlevel.baseline", value=120,
                      reason="A 지점 범람 수위 실측", scope_level="camera",
                      scope_ref=self.stream_a.pk)
        self.assertEqual(
            120.0, resolve_threshold("waterlevel.baseline", scope=self.scope_a, camera_id=self.stream_a.pk))
        # 다른 지점은 여전히 값이 없다 — 한 지점 설정이 전역을 만들지 않는다
        from kernels.k5_trust import ThresholdNotSet

        with self.assertRaises(ThresholdNotSet):
            resolve_threshold("waterlevel.baseline", scope=self.scope_b, camera_id=self.stream_b.pk)

    def test_a_defined_default_is_returned_when_nothing_overrides(self) -> None:
        from kernels.k5_trust import resolve_threshold

        self.assertEqual(10.0, resolve_threshold("event.dedup_window", scope=self.scope_a))

    def test_a_tenant_override_beats_the_default(self) -> None:
        from kernels.k5_trust import resolve_threshold, set_threshold

        set_threshold(scope=self.scope_a, key="event.dedup_window", value=15,
                      reason="현장 카메라 프레임률이 높다", scope_level="tenant",
                      scope_ref=self.group_a.pk)
        self.assertEqual(15.0, resolve_threshold("event.dedup_window",
                                                 scope=self.scope_a))
        self.assertEqual(10.0, resolve_threshold("event.dedup_window",
                                                 scope=self.scope_b),
                         "다른 테넌트가 남의 덮어쓰기를 받았습니다 — 격리가 샜습니다.")

    # ── ③ 계약을 설정으로 어길 수 없다 ──────────────────────────────────
    def test_contract_fixed_thresholds_cannot_be_overridden(self) -> None:
        """★ F-04 「5분」 · F-10 「30초」는 **계약이지 취향이 아니다.**

        설정 한 줄로 계약을 어길 수 있으면 그 계약은 코드에서 사라진 것이다.
        """
        from kernels.k5_trust import ThresholdIsContractFixed, set_threshold

        for key in ("notify.suppress_window", "notify.max_latency"):
            with self.subTest(key=key), self.assertRaises(ThresholdIsContractFixed):
                set_threshold(scope=self.scope_a, key=key, value=99,
                              reason="운영 편의")

    def test_the_contract_quote_is_pinned_in_the_table(self) -> None:
        """계약 고정 항목은 **어느 절이 그 값을 부르는지**를 표에 적고 있다."""
        rows = {r["key"]: r for r in _rows(self.scope_a)}
        for key in ("notify.suppress_window", "notify.max_latency"):
            self.assertTrue(rows[key]["contract_fixed"])
            self.assertTrue(rows[key]["clause"].strip(),
                            f"{key}: 계약 고정이라면서 어느 절인지 적혀 있지 않습니다.")

    # ── ④ 왜 바꿨는지가 남는다 ──────────────────────────────────────────
    def test_a_change_without_a_reason_is_refused(self) -> None:
        from kernels.k5_trust import set_threshold

        with self.assertRaises(ValueError):
            set_threshold(scope=self.scope_a, key="event.dedup_window", value=12,
                          reason="   ")

    def test_the_history_keeps_what_it_was_and_why(self) -> None:
        """**무엇에서 무엇으로, 누가, 왜** — 넷이 함께 남는다."""
        from kernels.k5_trust import set_threshold, threshold_history

        set_threshold(scope=self.scope_a, key="notify.email_timeout", value=20,
                      reason="고객 메일 서버가 느리다")
        set_threshold(scope=self.scope_a, key="notify.email_timeout", value=25,
                      reason="여전히 느리다")
        rows = threshold_history(scope=self.scope_a, key="notify.email_timeout")
        self.assertEqual(2, len(rows))
        self.assertEqual(("20", "25"), (rows[0]["old"], rows[0]["new"]))
        self.assertIsNone(rows[1]["old"], "첫 변경의 old 는 None 이어야 합니다 — "
                                          "그전에는 정의 기본값이었지 0 이 아니었습니다.")
        self.assertEqual(self.user_a.pk, rows[0]["changed_by"])
        self.assertTrue(all(r["reason"].strip() for r in rows))

    def test_the_change_is_audited_too(self) -> None:
        """설정 변경은 **감사에도** 남는다 — 표만 남기면 누가 봤는지가 사라진다."""
        from kernels.k5_trust import audit, set_threshold

        set_threshold(scope=self.scope_a, key="notify.email_timeout", value=20,
                      reason="고객 메일 서버가 느리다")
        rows = audit._entries(logger_name=audit.THRESHOLD_LOGGER_NAME)
        self.assertTrue(rows)
        self.assertEqual("set:notify.email_timeout", rows[0].action)
        self.assertEqual(audit.ALLOWED, rows[0].outcome)


class ThresholdWriteSurfaceTest(DsmFixture):
    """F-12 「임계값」 쓰기 면 — **F-02 의 「설정」이 실제로 일어나는 자리**."""

    def test_a_non_admin_cannot_change_a_threshold(self) -> None:
        """AC-12 — 무권한 차단 + 그 사실이 감사에 남는다."""
        from apps.dsm import services
        from apps.dsm.exceptions import PermissionDeniedForSetting

        with self.assertRaises(PermissionDeniedForSetting) as caught:
            services.set_threshold_value(
                scope=self.scope_a, key="event.dedup_window", value=12,
                reason="해 보고 싶어서")
        self.assertTrue(caught.exception.audit_id,
                        "차단이 감사에 남지 않았습니다 — 차단은 조용합니다.")

    def test_an_admin_sets_the_point_baseline(self) -> None:
        """★ F-02 「지점별 기준선 설정」 — 계약이 부른 그 행위."""
        from common.tenant_roles import tenant_admin_role_code

        from apps.dsm import services
        from kernels.k5_trust import resolve_threshold

        self.user_a.roles.add(self._own(
            self._role(tenant_admin_role_code(self.group_a.pk)), self.group_a))
        self.user_a.refresh_from_db()

        services.set_threshold_value(
            scope=self.scope_a, key="waterlevel.baseline", value=95,
            reason="안양천 A 지점 범람 수위 실측", scope_level="camera",
            scope_ref=self.stream_a.pk)
        self.assertEqual(95.0, resolve_threshold("waterlevel.baseline",
                                                 scope=self.scope_a,
                                                 camera_id=self.stream_a.pk))


class ThresholdSeedTest(DsmFixture):
    """첫 등재의 모양 — **자리는 있고 데이터는 없다** (D-325)."""

    def test_only_global_defaults_are_seeded(self) -> None:
        """★ D-325 「테넌트 override 자리는 두되 **지금은 전역 기본만 채운다**」.

        Zone 폴리곤과 같은 대칭이다(D-299) — 나중에 채우는 것이 재작업이 아니라
        **빈칸 채우기**가 되게 한다.
        """
        for row in _rows(self.scope_a):
            counts = row["override_counts"]
            self.assertEqual(0, counts["tenant"] + counts["camera"],
                             f"{row['key']}: 첫 등재에 테넌트·카메라 행이 있습니다.")


class ThresholdTableShowsTheEffectiveValueTest(DsmFixture):
    """표의 「지금 값」이 **정말 지금 유효한 값인가** — 턴 AB · 차선 F.

    턴 AA 에 차선 A 가 쟀다: 기관 관리자가 제 기관 임계값을 바꾸면 **저장은 200 인데
    표의 「지금 값」이 안 바뀐다.** `list_thresholds` 가 전역 층 덮어쓰기만 읽었기 때문이다.
    **제 값을 바꾼 사람이 제 값을 못 보는 화면**은 다음 사람에게 「저장이 안 됐다」로 읽힌다.
    """

    def test_the_table_shows_my_tenant_override_not_the_global_default(self) -> None:
        """★ 기관 층이 이긴다 — 그리고 **남의 기관에는 안 샌다.**"""
        from kernels.k5_trust import set_threshold

        before = {r["key"]: r for r in _rows(self.scope_a)}["event.dedup_window"]
        self.assertEqual(10.0, before["value"])
        self.assertEqual("default", before["source"])

        set_threshold(scope=self.scope_a, key="event.dedup_window", value=15,
                      reason="현장 카메라 프레임률이 높다", scope_level="tenant",
                      scope_ref=self.group_a.pk)

        mine = {r["key"]: r for r in _rows(self.scope_a)}["event.dedup_window"]
        self.assertEqual(15.0, mine["value"],
                         "제 기관 값을 바꾼 관리자가 표에서 제 값을 못 봅니다.")
        self.assertEqual("override", mine["source"])
        self.assertEqual("tenant", mine["source_level"],
                         "어느 층이 이겼는지가 안 나오면 고칠 사람을 못 고릅니다.")

        theirs = {r["key"]: r for r in _rows(self.scope_b)}["event.dedup_window"]
        self.assertEqual(10.0, theirs["value"],
                         "남의 테넌트가 내 덮어쓰기를 받았습니다 — 격리가 샜습니다.")
        self.assertEqual("default", theirs["source"])
        self.assertIsNone(theirs["source_level"])

    def test_the_global_layer_still_wins_over_the_definition(self) -> None:
        """기관 값이 없으면 전역이 이긴다 — 고친 것이 **한 층을 덮지 않았다.**"""
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_a, key="event.dedup_window", value=12,
                      reason="전역 기본을 올린다", scope_level="global")
        row = {r["key"]: r for r in _rows(self.scope_b)}["event.dedup_window"]
        self.assertEqual(12.0, row["value"])
        self.assertEqual("global", row["source_level"])

    def test_the_narrower_layer_beats_the_wider_one_in_the_table_too(self) -> None:
        """전역과 기관에 **둘 다** 값이 있으면 표도 좁은 쪽을 고른다."""
        from kernels.k5_trust import set_threshold

        set_threshold(scope=self.scope_a, key="event.dedup_window", value=12,
                      reason="전역", scope_level="global")
        set_threshold(scope=self.scope_a, key="event.dedup_window", value=15,
                      reason="우리 기관", scope_level="tenant",
                      scope_ref=self.group_a.pk)
        row = {r["key"]: r for r in _rows(self.scope_a)}["event.dedup_window"]
        self.assertEqual(15.0, row["value"])
        self.assertEqual("tenant", row["source_level"])

    def test_the_table_and_the_runtime_answer_the_same_number(self) -> None:
        """★★ **표와 실행이 갈리지 않는다** — 갈린 것이 바로 이 결함이었다(D-212).

        표의 모든 행에 대해 `resolve_threshold` 와 값을 대 본다. 값이 아직 없는 행
        (`waterlevel.baseline`)은 **양쪽 다 없어야** 맞다 — 0 이 아니다.
        """
        from kernels.k5_trust import ThresholdNotSet, resolve_threshold, set_threshold

        set_threshold(scope=self.scope_a, key="event.dedup_window", value=15,
                      reason="우리 기관", scope_level="tenant", scope_ref=self.group_a.pk)
        for row in _rows(self.scope_a):
            with self.subTest(key=row["key"]):
                if row["value"] is None:
                    self.assertEqual("unset", row["source"])
                    with self.assertRaises(ThresholdNotSet):
                        resolve_threshold(row["key"], scope=self.scope_a)
                    continue
                self.assertEqual(float(row["value"]),
                                 resolve_threshold(row["key"], scope=self.scope_a),
                                 "표가 그린 값과 실행이 쓰는 값이 다릅니다.")


class ThresholdTableIsTheSingleHomeTest(TestCase):
    """표가 **코드와 갈리지 않는가** — 게이트가 그것을 판정한다 (D-325).

    이 갈래는 **정의만** 본다(DB 를 읽지 않는다). 정의는 커밋으로 바뀌는 것이고,
    값은 화면으로 바뀌는 것이다 — 둘을 한 시험에서 재면 무엇이 깨졌는지 모른다.
    """

    def test_every_row_declares_a_unit_and_a_reason(self) -> None:
        from kernels.k5_trust.thresholds import THRESHOLDS

        self.assertTrue(THRESHOLDS)
        for key, spec in THRESHOLDS.items():
            with self.subTest(key=key):
                self.assertTrue(spec.unit.strip())
                self.assertTrue(spec.why.strip(),
                                "사유 없는 임계값은 다음 사람에게 마법의 숫자입니다.")

    def test_the_gate_that_binds_table_to_code_exists(self) -> None:
        """표를 지키는 것은 이 시험이 아니라 **게이트**다 (D-286)."""
        self.assertTrue(_gate("verify_threshold_table.py"),
                        "표와 코드를 묶는 게이트가 없으면 표는 문서입니다.")


def _rows(scope):
    from kernels.k5_trust import list_thresholds

    return list_thresholds(scope=scope)


def _gate(name: str):
    """게이트 파일을 찾는다. **컨테이너와 호스트의 경로가 다르므로 위로 훑고, 실패하면
    알려진 마운트 지점을 본다** — 경로를 상수로 박으면 한쪽에서만 도는 시험이 되고,
    한쪽에서만 도는 시험은 다른 쪽에서 **재지 않으면서 초록**이다 (D-301).
    """
    from pathlib import Path

    here = Path(__file__).resolve()
    for parent in (*here.parents, Path("/repo")):
        candidate = parent / "scripts" / name
        if candidate.is_file():
            return candidate
    return None
