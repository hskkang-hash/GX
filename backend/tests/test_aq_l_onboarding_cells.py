# -*- coding: utf-8 -*-
"""P-441 · 턴 AQ · 차선 L — **술어가 보는 칸 == 고친 칸** 을 시험으로 붙든다.

지난 턴(AP) 온보딩 고침 셋이 한 행도 못 올린 까닭은 「고친 칸과 술어가 보는 칸이
다르다」였다(WO-20 P-441). 그래서 이 파일은 행마다 **측정기(`scripts/measure_onboarding_t.py`)
의 술어가 실제로 보는 칸**을 소스에서 먼저 확인하고(측정기가 바뀌어 그 칸을 더는 안
보면 이 시험이 빨개진다 — 우리가 헛칸을 고치고 있다는 신호), 그다음 **제품의 그 칸**이
바뀌었음을 보인다. 측정기는 한 줄도 고치지 않는다(Q 소유 · 술어를 고쳐 초록을 만드는
것은 금지).

  U5#14 `/dsm/system` — 술어: 화면 본문 전체 → `verify_ui_copy.scan_line`(셋째 조건).
        고친 칸: 백업 카드 「누가 정했나」(`back.source` = `settings.RETENTION_DECLARATION_SOURCE`
        원문에 절 ID 가 든다) → `safeFreeText`.
  U2#4  `/dsm/events/:id` — 술어: `img` 중 `naturalWidth>0` 이고 **src 에 `snapshot`**.
        고친 칸: `EventSnapshot` 의 `<img src>`(blob 주소 뒤에 `#snapshot-<id>` 조각).
  U5#15 `/dsm/metering` — 술어: 화면 본문에 `%` 가 있는가(없으면 ◐).
        고친 칸: 「저장 용량 — 상한 대비」 칸(`GET /api/dsm/system/storage` 의 `used_pct`).
  U4#9  `/dsm/events/:id` — 술어: **브라우저가 부른** `GET …/clip` 이 200·404 인가
        (화면이 안 부르면 측정기가 인증 없이 불러 401).
        고친 칸: 상세 화면이 그 문을 직접 부른다 — 문은 JWT 로 200/404 를 낸다(HTTP 시험).

캐시 처리: 우회 — HTTP 시험은 `tests.no_cache.NO_CACHE` + `X-No-Cache` 로 부른다(D-341 ·
P-19: 적중 본문은 언제나 200 이라 문지기를 못 잰다). 나머지는 소스·함수 대조라 캐시와 무관.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.test import SimpleTestCase

from tests.test_clip_playback import _ClipFixture


def _repo_root() -> Path | None:
    for base in (Path("/repo"), *Path(__file__).resolve().parents):
        if (base / "frontend" / "src" / "App.tsx").is_file() and (base / "scripts").is_dir():
            return base
    return None


ROOT = _repo_root()


def _read(rel: str) -> str:
    assert ROOT is not None, "저장소 뿌리를 못 찾았다 — 판정 불가를 초록으로 두지 않는다"
    return (ROOT / rel).read_text(encoding="utf-8")


def _scan_line():
    """측정기가 셋째 조건에 쓰는 **바로 그 함수**(`verify_ui_copy.scan_line`)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_ui_copy import scan_line  # noqa: PLC0415
    return scan_line


def _safe_free_text_py():
    """`copy.ts::safeFreeText` 의 정규식을 **소스에서 꺼내** 파이썬으로 같은 순서로 적용한다.

    손으로 옮겨 적지 않는다 — 옮겨 적으면 두 벌이 되고 어긋나도 이 시험은 초록이다.
    """
    body = _read("frontend/src/features/dsm/copy.ts")
    names = ("FREE_TEXT_DECISION_NUMBER", "FREE_TEXT_SECTION_ID", "FREE_TEXT_BACKTICK",
             "FREE_TEXT_MARKDOWN_EMPHASIS", "FREE_TEXT_STATUS_WORD")
    rxs = []
    for name in names:
        m = re.search(r"const %s\s*=\s*/(.+?)/g;" % name, body, re.S)
        assert m, f"copy.ts 에서 {name} 을 못 찾았다"
        rxs.append(re.compile(m.group(1).replace("\n", "").strip()))

    def run(text: str) -> str:
        out = text
        for rx in rxs:
            out = rx.sub("", out)
        return re.sub(r"\s{2,}", " ", out).strip()
    return run


# ═══════════════════════════════════════════════════════════════════════════
# U5#14 — 셋째 조건 「절 ID」의 다섯째 자리
# ═══════════════════════════════════════════════════════════════════════════
class U5_14_SystemSourceCellTests(SimpleTestCase):

    def test_predicate_still_scans_the_whole_system_screen(self) -> None:
        """측정기 U5#14 는 `/dsm/system` 본문 전체를 셋째 조건으로 본다(바뀌면 헛칸)."""
        src = _read("scripts/measure_onboarding_t.py")
        block = src.split('# #14 시스템 상태 확인')[1].split('out.append(result("U5#14"')[1][:200]
        self.assertIn("screen_text=collect_screen_text(page=page)", block)

    def test_the_server_value_carries_a_section_id_the_predicate_catches(self) -> None:
        """개발·스테이징 선언 문장은 절 ID 를 품는다 — 원문 그대로면 ◐ 상한이다."""
        settings_src = _read("backend/config/settings.py")
        m = re.search(r'RETENTION_DECLARATION_SOURCE = \(\s*"([^"]+)"', settings_src)
        self.assertIsNotNone(m)
        declared = m.group(1)
        self.assertIn("절 ID", _scan_line()(declared),
                      "이 문장에 절 ID 가 없다면 U5#14 의 원인은 다른 칸이다 — 표를 다시 보라")
        self.assertEqual([], _scan_line()(_safe_free_text_py()(declared)),
                         "safeFreeText 를 지난 뒤에도 셋째 조건이 잡는다")

    def test_the_who_declared_cell_renders_through_safe_free_text(self) -> None:
        """「누가 정했나」 칸은 둘이다(보존 정책 · 백업) — 둘 다 같은 설정 문장을 품는다."""
        body = _read("frontend/src/features/dsm/pages/SystemSettings.tsx")
        cells = body.split('label="누가 정했나"')[1:]
        self.assertEqual(2, len(cells), "「누가 정했나」 칸 수가 바뀌었다 — 표를 다시 보라")
        for cell, name in zip(cells, ("policy", "back")):
            head = cell[:400]
            self.assertIn(f"safeFreeText({name}?.source)", head)
            self.assertNotIn(f"{{{name}?.source ||", head)
            self.assertNotIn(f"? {name}?.source ||", head)

    def test_retention_source_carries_the_same_sentence(self) -> None:
        """보존 정책 출처(`retention_source`)도 선언 문장을 붙여 낸다 — 그래서 두 칸 다 거른다."""
        body = _read("backend/apps/dsm/retention.py")
        self.assertIn('getattr(settings, "RETENTION_DECLARATION_SOURCE", "")', body)


# ═══════════════════════════════════════════════════════════════════════════
# U2#4 — 그림 주소가 자기가 사진임을 말한다
# ═══════════════════════════════════════════════════════════════════════════
class U2_4_SnapshotSrcTests(SimpleTestCase):

    def _predicate_needle(self) -> str:
        src = _read("scripts/measure_onboarding_t.py")
        block = src.split('# #4 심각 이벤트')[1].split('out.append(result("U2#4"')[1]
        head = src.split('# #4 심각 이벤트')[1].split('out.append(result("U2#4"')[0]
        m = re.search(r"\(i\.src\|\|''\)\.includes\('([^']+)'\)", head + block)
        self.assertIsNotNone(m, "측정기 U2#4 가 img src 를 더는 안 본다 — 고친 칸이 헛칸이 됐다")
        return m.group(1)

    def test_predicate_reads_img_src_not_data_gx(self) -> None:
        """턴 AP 가 단 `data-gx` 는 이 술어가 안 보는 칸이었다(P-441 의 실례)."""
        self.assertEqual("snapshot", self._predicate_needle())

    def test_img_src_carries_the_needle_on_a_blob_url(self) -> None:
        body = _read("frontend/src/features/dsm/components/EventSnapshot.tsx")
        m = re.search(r"src=\{url \? `\$\{url\}#([a-z]+)-\$\{eventId\}` : ''\}", body)
        self.assertIsNotNone(m, "EventSnapshot 의 img src 가 조각 없는 blob 주소로 돌아갔다")
        needle = self._predicate_needle()
        before = "blob:http://gx-nginx-e:8500/6f1c2a4e-0000-4000-8000-000000000000"
        after = f"{before}#{m.group(1)}-575509"
        self.assertNotIn(needle, before)   # 고치기 전: 0
        self.assertIn(needle, after)       # 고친 뒤: 센다

    def test_revoke_still_uses_the_bare_object_url(self) -> None:
        """조각을 붙인 주소로 revoke 하면 blob 이 안 풀린다 — 되돌림은 원래 주소로."""
        body = _read("frontend/src/features/dsm/components/EventSnapshot.tsx")
        self.assertIn("setUrl(objectUrl)", body)
        self.assertIn("revoke = undo", body)


# ═══════════════════════════════════════════════════════════════════════════
# U5#15 — 사용량 화면이 저장 용량을 % 로도 말한다
# ═══════════════════════════════════════════════════════════════════════════
class U5_15_MeteringPercentTests(SimpleTestCase):

    def test_predicate_is_a_percent_sign_on_the_metering_body(self) -> None:
        src = _read("scripts/measure_onboarding_t.py")
        block = src.split("# #15 저장 용량")[1][:700]
        self.assertIn('pct = "%" in b', block)
        self.assertIn("cap_half=(not pct)", block)

    def test_metering_reads_the_single_storage_judgement_and_draws_percent(self) -> None:
        body = _read("frontend/src/features/dsm/pages/Metering.tsx")
        self.assertIn("dsmU56AdminEndpoint.storage", body)
        self.assertIn("{storagePct.data.used_pct}%", body)
        # 미선언·못 잼이면 % 를 지어내지 않고 서버 사유를 그린다
        self.assertIn("safeFreeText(storagePct.data?.reason)", body)

    def test_declared_capacity_yields_a_percent_from_the_same_function(self) -> None:
        """화면이 읽는 판정 하나(`storage_declaration`)가 선언이 있으면 % 수를 낸다."""
        from common import ops_tasks

        with mock.patch.object(ops_tasks, "storage_capacity_gb", return_value=50.0), \
                mock.patch.object(ops_tasks, "storage_used_gb", return_value=(5.0, "센 것")):
            d = ops_tasks.storage_declaration()
        self.assertTrue(d["declared"])
        self.assertEqual(10.0, d["used_pct"])
        with mock.patch.object(ops_tasks, "storage_capacity_gb", return_value=0.0), \
                mock.patch.object(ops_tasks, "storage_used_gb", return_value=(5.0, "센 것")):
            d0 = ops_tasks.storage_declaration()
        self.assertIsNone(d0["used_pct"], "미선언인데 % 를 냈다 — 지어낸 수다")

    def test_free_text_on_metering_passes_the_third_condition(self) -> None:
        """% 가 생겨 ◐ 상한이 풀리면 셋째 조건이 드러난다 — 서버 문장이 걸리지 않는가."""
        from apps.dsm import metering

        scan, clean = _scan_line(), _safe_free_text_py()
        body = _read("frontend/src/features/dsm/pages/Metering.tsx")
        self.assertIn("safeFreeText(cell.why)", body)
        self.assertIn("safeFreeText(usage.data?.definitions?.[cell.key])", body)
        for text in list(metering.EXCLUSIONS_NOT_APPLIED.values()) + [
                "크기가 안 적힌 파일이 3개다 — 이 수는 **하한**이다"]:
            self.assertEqual([], scan(clean(text)), text)


# ═══════════════════════════════════════════════════════════════════════════
# U4#9 — 상세 화면이 구간 문을 직접 부른다 · 문은 JWT 로 200/404
# ═══════════════════════════════════════════════════════════════════════════
class U4_9_ClipDoorSourceTests(SimpleTestCase):

    def test_predicate_counts_browser_calls_to_the_clip_door(self) -> None:
        src = _read("scripts/measure_onboarding_t.py")
        block = src.split("def _u4_9():")[1][:900]
        self.assertIn('net.find("GET", f"/api/dsm/events/{ev}/clip", m)', block)
        self.assertIn("c in (200, 404)", block)

    def test_event_detail_calls_the_clip_door(self) -> None:
        body = _read("frontend/src/features/dsm/pages/EventDetail.tsx")
        self.assertIn("dsmGet<{ start_offset: number; duration: number }>(`/api/dsm/events/${id}/clip`)", body)
        self.assertIn("err.status === 404) return null", body)
        self.assertIn('data-gx="clip-window"', body)


class U4_9_ClipDoorHttpTests(_ClipFixture):
    """문이 JWT 로 **200(참조 있음) · 404(참조 없음)** 을 낸다 — 측정기가 받아들이는 둘."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        from core.middleware.refresh_token import thread_local
        thread_local.request = None
        super().setUpTestData()
        #: 역할 없는 계정은 문지기가 403(role_required)으로 막는다 — 측정기의 U4 는
        #: 읽기 전용 역할(`view_only_*`)을 가진 사람이다. 그 모양 그대로 하나 준다.
        Role = apps.get_model("role", "Role")
        role = cls._own(Role.objects.create(role_name="view_only_aq_l", code="view_only_aq_l"),
                        cls.group_a)
        cls.user_a.roles.add(role)

    def setUp(self) -> None:
        from django.test import Client

        from tests.no_cache import NO_CACHE

        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _bearer(self, user) -> str:
        import jwt as pyjwt
        from django.conf import settings
        from ninja_jwt.tokens import RefreshToken

        session_id = "gx-aq-l-clip"
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        user.set_encrypted_session_token(session_id, decoded.get("jti"))
        user.save()
        return f"Bearer {access}"

    def _get(self, event_id, bearer_header=None):
        extra = {"HTTP_X_NO_CACHE": "true"}
        if bearer_header:
            extra["HTTP_AUTHORIZATION"] = bearer_header
        return self.client.get(f"/api/dsm/events/{event_id}/clip", **extra)

    def test_signed_in_screen_gets_200_or_404_never_401(self) -> None:
        with_clip = self._event()
        without_clip = self._event(stream=self.stream_norec, event_type="flood",
                                   severity="warning")
        bearer_header = self._bearer(self.user_a)
        r200 = self._get(with_clip, bearer_header)
        r404 = self._get(without_clip, bearer_header)
        self.assertEqual(200, r200.status_code, r200.content[:300])
        self.assertEqual(404, r404.status_code, r404.content[:300])
        self.assertIn("start_offset", r200.json())

    def test_without_the_screen_token_the_door_is_401(self) -> None:
        """측정기가 화면 밖에서 인증 없이 두드리던 모양 — 아홉째 회차의 [401]."""
        self.assertEqual(401, self._get(self._event()).status_code)
