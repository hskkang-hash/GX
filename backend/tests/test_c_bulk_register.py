# -*- coding: utf-8 -*-
"""카메라 벌크 등록 — **표가 먼저인가, 그리고 남의 테넌트에 심을 수 있는가**
(UX-18 · 차선 C · 2026-09-24 · D-209).

이 파일이 묻는 것
-----------------
① **dry-run 이 아무것도 안 쓰는가.** 「보여 주고 나서 쓴다」는 규약은 dry-run 이
   실제로 아무 행도 안 건드릴 때만 규약이다. 한 줄이라도 쓰면 그것은 미리보기가
   아니라 **덜 위험해 보이는 쓰기**다.
② **표와 집행이 같은 판정을 쓰는가.** 두 벌이면 표에 없던 일이 일어나고,
   그러면 dry-run 은 보여 주기일 뿐 약속이 아니게 된다.
③ **격리.** 남의 테넌트에 카메라를 무더기로 심을 수 있으면, 심어 둔 행은 그쪽의
   정상 데이터처럼 보이고 그 뒤의 어떤 읽기 시험도 그것을 이상하다고 하지 않는다.
   한 번에 100행이 들어오는 면이라 **한 건짜리 구멍과 값이 다르다.**
④ **부분 성공을 안 만드는가.** 100행 중 37행이 들어간 상태는 되돌릴 지점이 없다.
⑤ **배지가 분모와 함께 나오는가** (D-301). 「39대」만으로는 40 중 39인지 400 중
   39인지 모르고, 두 사실에 필요한 행동이 다르다.

★ 이 파일이 묻지 **않는** 것 — ONVIF 와 역지오코딩.
  둘 다 **없다**는 것이 착수 전 실측의 답이다(파일 머리 `bulk_register.py` 참조).
  없는 것 위에 시험을 세우면 그 초록은 아무것도 말하지 않는다.
  대신 `AbsentPathsAreNamedTest` 가 **없다는 사실 자체**를 못박는다 (D-300 부작위).
"""
from __future__ import annotations

from tests.test_dsm_app import DsmFixture

#: ★ D-289 — 표본은 저장소 실물이다.
REAL_SAMPLE = (
    "stream_monitors.services.bulk_register(parse_csv · plan_camera_import · "
    "apply_camera_import · address_gap) · stream_monitors.models.StreamMonitor · "
    "adapters.juso.resolve — 저장소의 실제 모듈과 실제 표. 합성 더미를 부르지 않는다"
)

CSV_TWO_NEW = (
    "name,code,ip_source,address,detail\n"
    "c-정문,C-GATE,rtsp://10.9.9.1/s,경기도 안양시 만안구 안양로 123,정문\n"
    "c-후문,C-BACK,rtsp://10.9.9.2/s,경기도 안양시 만안구 안양로 124,후문\n"
)


def _cameras(group):
    from stream_monitors.models import StreamMonitor

    return StreamMonitor.objects.filter(group_id=group.pk)


class DryRunWritesNothingTest(DsmFixture):
    """① ★ **표는 아무것도 안 쓴다.** 쓰면 그것은 미리보기가 아니다."""

    def test_a_dry_run_creates_no_row(self) -> None:
        from stream_monitors.services import bulk_register

        before = _cameras(self.group_a).count()
        plan = bulk_register.plan_camera_import(scope=self.scope_a,
                                                csv_text=CSV_TWO_NEW)
        after = _cameras(self.group_a).count()

        self.assertTrue(plan["dry_run"])
        self.assertEqual(2, plan["will_write"])
        self.assertEqual(
            before, after,
            "dry-run 이 행을 만들었습니다 — 그러면 이것은 미리보기가 아니라 "
            "덜 위험해 보이는 쓰기입니다(D-209).")

    def test_the_plan_says_what_will_change_field_by_field(self) -> None:
        """표가 「2행이 바뀝니다」만 말하면 사람이 볼 것이 없다 — **칸 단위**로 적는다."""
        from stream_monitors.services import bulk_register

        plan = bulk_register.plan_camera_import(scope=self.scope_a,
                                                csv_text=CSV_TWO_NEW)
        first = plan["rows"][0]
        self.assertEqual("create", first["action"])
        self.assertIn("install_address", first["changes"])
        self.assertEqual("manual", first["changes"]["address_source"][1],
                         "주소 출처는 manual 하나뿐입니다 — 팝업 API 로 채워도 "
                         "출처는 사람입니다(D-331).")


class PlanAndApplyAgreeTest(DsmFixture):
    """② 표와 집행이 **같은 판정**을 쓰는가."""

    def test_apply_writes_exactly_what_the_plan_promised(self) -> None:
        from stream_monitors.services import bulk_register

        plan = bulk_register.plan_camera_import(scope=self.scope_a,
                                                csv_text=CSV_TWO_NEW)
        applied = bulk_register.apply_camera_import(scope=self.scope_a,
                                                    csv_text=CSV_TWO_NEW)

        self.assertEqual(plan["will_write"], applied["applied"],
                         "표가 약속한 행 수와 실제로 쓴 행 수가 다릅니다.")
        self.assertEqual(2, applied["created"])
        self.assertEqual(
            {"c-정문", "c-후문"},
            set(_cameras(self.group_a).filter(
                name__startswith="c-").values_list("name", flat=True)))

    def test_a_second_apply_changes_nothing(self) -> None:
        """같은 파일을 두 번 올려도 두 벌이 안 생긴다 — 「변화 없음」은 오류가 아니다."""
        from stream_monitors.services import bulk_register

        bulk_register.apply_camera_import(scope=self.scope_a, csv_text=CSV_TWO_NEW)
        again = bulk_register.apply_camera_import(scope=self.scope_a,
                                                  csv_text=CSV_TWO_NEW)
        self.assertEqual(0, again["applied"])
        self.assertEqual(2, again["counts"]["unchanged"])

    def test_an_update_row_reports_the_old_value(self) -> None:
        """「무엇에서 무엇으로」를 못 적으면 되돌릴 값을 아무도 모른다."""
        from stream_monitors.services import bulk_register

        bulk_register.apply_camera_import(scope=self.scope_a, csv_text=CSV_TWO_NEW)
        changed = CSV_TWO_NEW.replace("안양로 123", "안양로 999")
        plan = bulk_register.plan_camera_import(scope=self.scope_a, csv_text=changed)

        row = next(r for r in plan["rows"] if r["name"] == "c-정문")
        self.assertEqual("update", row["action"])
        self.assertIn("안양로 123", str(row["changes"]["install_address"][0]))
        self.assertIn("안양로 999", str(row["changes"]["install_address"][1]))


class BulkWriteIsolationTest(DsmFixture):
    """③ ★ **남의 테넌트에 100행을 심을 수 있는가.** `WRITE_PROBES` 가 선등재한 자리."""

    def test_rows_land_in_the_requesters_tenant_only(self) -> None:
        from stream_monitors.services import bulk_register

        bulk_register.apply_camera_import(scope=self.scope_a, csv_text=CSV_TWO_NEW)
        self.assertEqual(
            0, _cameras(self.group_b).filter(name__startswith="c-").count(),
            "A 가 올린 카메라가 B 의 테넌트에 들어갔습니다 — 심어 둔 행은 그쪽의 "
            "정상 데이터처럼 보이고, 그 뒤의 어떤 읽기 시험도 이상하다고 하지 않습니다.")
        self.assertEqual(2, _cameras(self.group_a).filter(
            name__startswith="c-").count())

    def test_another_tenants_camera_is_not_updated_by_name_collision(self) -> None:
        """★ **이름이 같아도 남의 카메라는 안 건드린다.**

        여기가 이 파일에서 가장 조용한 구멍이다: 이름으로 찾는 등록이 테넌트를 안
        좁히면, 같은 이름을 올리는 것만으로 **남의 카메라 주소가 덮인다** — 그리고
        그 주소는 그쪽 알림 본문에 그대로 나가 사람을 엉뚱한 곳으로 보낸다.
        """
        from stream_monitors.models import StreamMonitor

        from stream_monitors.services import bulk_register

        victim = self._stream("c-정문", self.group_b)
        victim.install_address = "남의 테넌트 원래 주소"
        victim.address_source = "manual"
        victim.save(update_fields=["install_address", "address_source"])

        bulk_register.apply_camera_import(scope=self.scope_a, csv_text=CSV_TWO_NEW)

        after = StreamMonitor.objects.get(pk=victim.pk)
        self.assertEqual("남의 테넌트 원래 주소", after.install_address,
                         "남의 카메라 주소가 덮였습니다.")

    def test_a_system_scope_cannot_bulk_write(self) -> None:
        """100대를 심는 일에 요청자가 없으면 「누가 넣었나」가 영영 빈다 (D-281)."""
        from stream_monitors.services import bulk_register

        with self.assertRaises(Exception) as caught:
            bulk_register.apply_camera_import(scope=self.scope_pipe,
                                              csv_text=CSV_TWO_NEW)
        self.assertNotIsInstance(caught.exception, AssertionError)


class NoPartialSuccessTest(DsmFixture):
    """④ 부분 성공을 안 만든다."""

    def test_a_bad_header_writes_nothing(self) -> None:
        from stream_monitors.services import bulk_register

        before = _cameras(self.group_a).count()
        result = bulk_register.apply_camera_import(
            scope=self.scope_a, csv_text="이름,주소\nc-정문,어딘가\n")
        self.assertTrue(result["fatal"])
        self.assertEqual(0, result["applied"])
        self.assertEqual(before, _cameras(self.group_a).count())

    def test_duplicate_names_in_the_file_are_refused_not_last_wins(self) -> None:
        """겹치면 **아무것도 안 쓴다.** 어느 줄이 이겼는지 모르는 채로 쓰면
        엉뚱한 카메라의 주소가 알림에 나간다 (D-338 이 정한 규약)."""
        from stream_monitors.services import bulk_register

        dup = (
            "name,ip_source,address\n"
            "c-정문,rtsp://10.9.9.1/s,주소 A\n"
            "c-정문,rtsp://10.9.9.9/s,주소 B\n"
        )
        plan = bulk_register.plan_camera_import(scope=self.scope_a, csv_text=dup)
        actions = [r["action"] for r in plan["rows"]]
        self.assertEqual(["create", "error"], actions)
        self.assertIn("겹칩니다", plan["rows"][1]["reason"])

    def test_a_new_camera_without_a_stream_source_is_an_error_not_a_skip(self) -> None:
        """「건너뜀」과 「오류」를 합치지 않는다 (D-290) — 조용히 넘어가면
        「2대 다 넣었다」는 보고가 실제로는 1대만 들어간 상태와 구별되지 않는다."""
        from stream_monitors.services import bulk_register

        plan = bulk_register.plan_camera_import(
            scope=self.scope_a, csv_text="name,address\nc-외톨이,어딘가\n")
        self.assertEqual("error", plan["rows"][0]["action"])
        self.assertEqual(0, plan["will_write"])


class AddressGapBadgeTest(DsmFixture):
    """⑤ 「주소 없는 카메라 N대」 — **분모와 함께.**"""

    def test_the_badge_carries_its_denominator(self) -> None:
        from stream_monitors.services import bulk_register

        gap = bulk_register.address_gap(scope=self.scope_a)
        for key in ("total", "with_address", "without_address", "coverage",
                    "measurable"):
            self.assertIn(key, gap)
        #: 픽스처의 A 테넌트 카메라 1대는 주소가 없다.
        self.assertEqual(gap["total"], gap["without_address"] + gap["with_address"])

    def test_filling_addresses_moves_the_badge(self) -> None:
        """★ 배지가 **실제로 움직이는가.** 안 움직이면 그 수는 장식이다."""
        from stream_monitors.services import bulk_register

        before = bulk_register.address_gap(scope=self.scope_a)
        bulk_register.apply_camera_import(scope=self.scope_a, csv_text=CSV_TWO_NEW)
        after = bulk_register.address_gap(scope=self.scope_a)

        self.assertEqual(before["total"] + 2, after["total"])
        self.assertEqual(before["with_address"] + 2, after["with_address"])
        self.assertEqual(before["without_address"], after["without_address"])

    def test_no_cameras_means_null_coverage_not_zero(self) -> None:
        """분모 0 이면 비율은 **`null` 이다 — 0 이 아니다.** 카메라가 한 대도 없는 것과
        전부 주소가 있는 것을 같은 숫자로 내면 배지가 거짓말을 한다."""
        from stream_monitors.models import StreamMonitor

        from stream_monitors.services import bulk_register

        StreamMonitor.objects.filter(group_id=self.group_a.pk).delete()
        gap = bulk_register.address_gap(scope=self.scope_a)
        self.assertEqual(0, gap["total"])
        self.assertIsNone(gap["coverage"])
        self.assertFalse(gap["measurable"])

    def test_the_badge_does_not_count_another_tenants_cameras(self) -> None:
        from stream_monitors.services import bulk_register

        gap_a = bulk_register.address_gap(scope=self.scope_a)
        self.assertEqual(
            _cameras(self.group_a).count(), gap_a["total"],
            "배지의 분모에 남의 테넌트 카메라가 섞였습니다.")


class AbsentPathsAreNamedTest(DsmFixture):
    """★ **없는 것을 없다고 적는다** (D-300 부작위 시험 · D-284).

    지시서 §2 C행 UX-18 은 「CSV/**ONVIF** 일괄 등록 + **좌표→도로명 역지오코딩**」을
    적었다. 착수 전 실측이 둘 다 **없다**고 답했고, 그 답을 여기 못박는다 —
    ⚠ 둘 중 하나가 생기면 이 시험이 빨개진다. **그것이 옳다.**
    """

    def test_reverse_geocoding_is_still_judged_unavailable(self) -> None:
        """D-329 — 발급된 승인키 2건이 둘 다 「도로명주소 팝업 API」였다.
        그것은 서버 조회 API 가 아니고, 역지오코딩은 이 자원으로 열리지 않는다."""
        import adapters.juso as juso

        self.assertEqual(
            "no", juso.JUSO_REVERSE_SUPPORTED,
            "역지오코딩 판정이 바뀌었습니다 — 바뀌었다면 `bulk_register.py` 의 "
            "좌표 갈래가 이제 실제로 주소를 채웁니다. 이 시험을 고쳐 그 사실을 "
            "선언하십시오.")
        result = juso.resolve(lat=37.4, lng=126.9)
        self.assertEqual("disabled", result.status)

    def test_the_camera_model_has_no_coordinates_to_reverse_geocode(self) -> None:
        """★ 그리고 **역지오코딩할 좌표가 애초에 없다.** `StreamMonitor` 는 고정
        설치물이고 위도·경도 칸을 갖지 않는다 — D-330 이 FX-5 를 「설치 주소」로
        대체한 이유가 이것이다."""
        from stream_monitors.models import StreamMonitor

        names = {f.name for f in StreamMonitor._meta.get_fields()}
        self.assertNotIn("lat", names)
        self.assertNotIn("lng", names)
        self.assertIn("install_address", names)

    def test_onvif_has_no_implementation_in_this_repository(self) -> None:
        """ONVIF **구현이** 없다 — 라이브러리도 어댑터도 없다 [실측 2026-09-24].

        ★ 1차판은 「`onvif` 라는 글자가 backend 어디에도 없다」로 재려 했고 **즉시
          빨개졌다**: `bulk_register.py` 와 `api.py` 의 주석이 *「ONVIF 는 없다」*고
          적고 있었기 때문이다. 그 빨강은 옳지 않다 — 없다는 사실을 적는 문장과
          없는 것을 부르는 코드는 다르다. 그래서 **묻는 것을 바꿨다**: 글자가 아니라
          **import 를 본다**(`test_f05_event_api._scan` 이 K1 소비자를 세는 방식과 같다).
          시험을 물러 주려 고친 것이 아니라, 재는 것이 틀렸던 것을 고쳤다(D-327 구별).
        """
        import ast
        from pathlib import Path

        backend = Path(__file__).resolve().parent.parent
        importers = []
        for path in backend.rglob("*.py"):
            as_posix = str(path).replace("\\", "/")
            if "__pycache__" in path.parts or "/tests/" in as_posix:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if any("onvif" in n.lower() or "wsdiscovery" in n.lower()
                       for n in names):
                    importers.append(str(path))
        self.assertEqual(
            [], sorted(set(importers)),
            f"ONVIF 를 **부르는** 모듈이 생겼습니다: {sorted(set(importers))}. "
            f"어댑터가 들어왔다면 `bulk_register.Row.source` 에 값을 하나 더하고 "
            f"이 시험을 고치십시오 — 판정·표·집행은 그대로 쓰입니다.")

    def test_the_absence_of_onvif_is_written_down_where_it_matters(self) -> None:
        """★ 없는 것은 **없다고 적혀 있어야** 한다 (D-284).

        적지 않으면 다음 사람이 「CSV 만 있네, 만들다 만 건가」로 읽고, 그 읽기에서
        「판정이 이미 났다」는 사실이 사라진다.
        """
        import inspect

        from stream_monitors.services import bulk_register

        src = inspect.getsource(bulk_register)
        self.assertIn("ONVIF", src)
        self.assertIn("D-329", src, "역지오코딩 판정의 근거 번호가 안 적혀 있습니다.")
        self.assertIn("D-330", src, "카메라 설치 주소로 대체된 근거가 안 적혀 있습니다.")
