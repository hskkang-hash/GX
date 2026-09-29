# -*- coding: utf-8 -*-
"""P-423 · 턴 AP · 차선 L — 「누를 자리를 선언하지 않았다」 10행 중 이 차선이 선언한

것들이 소스에 실제로 섰는가 + 같은 턴에 찾은 두 「말·술어」 원인(U2#4 · U5#14)이
다시 새지 않는가.

이 파일은 `docs/agent/evidence/P-118/click_completes.json` 이 각 행에 적어 둔
"이 도구가 누를 자리를 선언하지 않았다" 사유와, `docs/agent/onboarding_48.md` 의
정본 문구·경로를 대조해 이 턴이 단 `data-gx` 표식이 그 화면·그 단추에 실제로
붙어 있는지를 **소스 문자열**로 본다(직전 턴 AN·AO 자매 파일 `test_ao_l_screen_
language.py` 와 같은 성질 — HTTP 를 한 번도 때리지 않는다). 판정기(`scripts/
verify_click_completes.py` · `measure_onboarding_t.py`)는 Q 소유라 이 파일이
대신하지 않는다 — 여기서 보는 것은 오직 "화면이 그 자리를 선언했는가"뿐이다.

이 파일이 검증하는 것 다섯 갈래:
  ① U5#1 `/dsm/people` — 「계정 만들기」 제출 단추(POST 한 번으로 끝나는 자리)에
     `data-gx="people-create-submit"`.
  ② U5#4 `/dsm/cameras/import` — dry-run·적용 두 단추에 각각
     `data-gx="camera-import-dryrun"` / `"camera-import-apply"`.
  ③ U5#5 `/dsm/cameras/address` — 행별 "이 한 대 채우기"·"채우기"(POST 를 실제로
     쏘는 자리)에 `data-gx="camera-address-row-start"` / `"camera-address-row-
     submit"`.
  ④ U3#16 `/m/settings` — 「설정 저장」 단추(PUT notify-prefs 를 부르는 자리)에
     `data-gx="prefs-save-submit"`.
  ⑤ U5#10 `/dsm/notify` — 채널 칸(U5#9 와 같은 단추를 다시 안 누르고 저장된
     channel 값을 읽는 자리)에 `data-gx="notify-rule-channel"` +
     `data-gx-channel`.

그리고 이번 턴 온보딩 +4 조사에서 찾은 두 「말·술어」 원인의 회귀 방지:
  ⑥ U2#4 `/dsm/events/:id` — `EventSnapshot` 호출에 `dataGx="snapshot"` (안 주면
     `img` 에 `data-gx` 속성 자체가 안 붙어 `naturalWidth` 술어를 잴 자리가 없다).
  ⑦ U5#14 `/dsm/system` — 재시작 사유 칸만이 아니라 백업·회수증·저장 용량의
     자유 문장 다섯 자리도 `safeFreeText()` 를 거치는가.

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

from pathlib import Path

from django.test import TestCase


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class DsmSourceMixin:
    """공용 — frontend/src 를 찾고 파일을 읽는다. 못 찾으면 판정 불가(회색)로 죽는다."""

    src: Path

    def setUp(self) -> None:  # noqa: D401
        found = _frontend_src()
        self.assertIsNotNone(found, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")
        self.src = found  # type: ignore[assignment]

    def _read(self, rel: str) -> str:
        return (self.src / rel).read_text(encoding="utf-8")


class PeopleCreateDeclaresClickPlaceTests(DsmSourceMixin, TestCase):
    """U5#1 — `/dsm/people` 「계정 만들기」."""

    def test_submit_button_has_data_gx(self) -> None:
        body = self._read("features/dsm/pages/People.tsx")
        self.assertIn("계정 만들기", body)
        idx = body.index("htmlType=\"submit\"")
        near = body[max(0, idx - 200):idx + 200]
        self.assertIn('data-gx="people-create-submit"', near,
                      "「계정 만들기」 제출 단추에 data-gx 선언이 없다")


class CameraImportDeclaresClickPlacesTests(DsmSourceMixin, TestCase):
    """U5#4 — `/dsm/cameras/import` dry-run · 적용 두 단추."""

    def setUp(self) -> None:
        super().setUp()
        self.body = self._read("features/dsm/pages/CameraImport.tsx")

    def test_dryrun_button_has_data_gx(self) -> None:
        self.assertIn("표 먼저 보기", self.body)
        idx = self.body.index("표 먼저 보기 (dry-run)")
        near = self.body[max(0, idx - 300):idx]
        self.assertIn('data-gx="camera-import-dryrun"', near)

    def test_apply_button_has_data_gx(self) -> None:
        self.assertIn("이 표대로 적용", self.body)
        idx = self.body.index("이 표대로 적용")
        near = self.body[max(0, idx - 300):idx]
        self.assertIn('data-gx="camera-import-apply"', near)


class CameraAddressDeclaresClickPlacesTests(DsmSourceMixin, TestCase):
    """U5#5 — `/dsm/cameras/address` 행별 「이 한 대 채우기」 → 「채우기」."""

    def setUp(self) -> None:
        super().setUp()
        self.body = self._read("features/dsm/pages/CameraAddress.tsx")

    def test_row_start_button_has_data_gx(self) -> None:
        # ★ "이 한 대 채우기" 는 이 파일 머리말 주석(턴 U 표기)에도 두 번 먼저 나온다
        #   (`rindex` 로 **마지막**(실제 JSX 자식 글자) 자리를 잡는다 — 안 그러면
        #   주석을 button 으로 착각해 이 시험이 늘 실패한다).
        idx = self.body.rindex("이 한 대 채우기")
        near = self.body[max(0, idx - 300):idx]
        self.assertIn('data-gx="camera-address-row-start"', near)

    def test_row_submit_button_has_data_gx(self) -> None:
        # 행 편집 중 "채우기" 제출 단추 — fillOne 을 부르는 자리.
        idx = self.body.index("onClick={() => fillOne(row, rowAddress.trim())}")
        near = self.body[idx:idx + 200]
        self.assertIn('data-gx="camera-address-row-submit"', near)

    def test_new_camera_buttons_disambiguated(self) -> None:
        # 아래 "아직 없는 카메라" 카드의 같은 글자 단추 둘과 안 섞이게 별도 표식.
        self.assertIn('data-gx="camera-address-new-dryrun"', self.body)
        self.assertIn('data-gx="camera-address-new-apply"', self.body)


class MobileSettingsDeclaresClickPlaceTests(DsmSourceMixin, TestCase):
    """U3#16 — `/m/settings` 「설정 저장」."""

    def test_save_button_has_data_gx(self) -> None:
        body = self._read("features/mobile/pages/MobileSettings.tsx")
        idx = body.index("설정 저장")
        near = body[max(0, idx - 300):idx]
        self.assertIn('data-gx="prefs-save-submit"', near)


class NotifySettingsChannelStateDeclaredTests(DsmSourceMixin, TestCase):
    """U5#10 — `/dsm/notify` 채널 칸(U5#9 와 같은 단추 재사용 · 상태만 새로 선언)."""

    def test_channel_cell_has_data_gx_and_channel_value(self) -> None:
        body = self._read("features/dsm/pages/NotifySettings.tsx")
        idx = body.index("dataIndex: 'channels'")
        near = body[idx:idx + 300]
        self.assertIn('data-gx="notify-rule-channel"', near,
                      "채널 칸에 data-gx 선언이 없다")
        self.assertIn("data-gx-channel={cs.join(',')}", near,
                      "채널 칸이 원래 채널 코드값(data-gx-channel)을 안 싣는다 — "
                      "표시명으로 바꾸면 서버 기록과 대조할 수 없다")


class EventSnapshotDataGxRegressionTests(DsmSourceMixin, TestCase):
    """U2#4 — 관제 쪽 `EventDetail.tsx` 가 `EventSnapshot` 에 dataGx="snapshot" 을 주는가.

    안 주면 `img[data-gx="snapshot"]` 셀렉터 자체가 없어 naturalWidth 술어를 잴
    자리가 없다(사진이 안 그려진 것이 아니라 잴 자리가 없었다 — 2026-09-29
    turn_ao_8.json U2#4 실측). 모바일 쪽(`MobileEventDetail.tsx`)은 이미 준다
    (U3#3 초록의 이유) — 그 짝을 관제 쪽에도 맞춘다.
    """

    def test_event_detail_passes_data_gx_snapshot(self) -> None:
        body = self._read("features/dsm/pages/EventDetail.tsx")
        idx = body.index("<EventSnapshot")
        end = body.index("/>", idx)
        call = body[idx:end]
        self.assertIn('dataGx="snapshot"', call,
                      "EventDetail.tsx 의 EventSnapshot 호출이 dataGx=\"snapshot\" 을 안 준다")

    def test_mobile_event_detail_still_passes_data_gx_snapshot(self) -> None:
        # 회귀 방지 — 모바일 쪽은 이미 옳았다. 같이 깨지지 않았는지 재확인.
        body = self._read("features/mobile/pages/MobileEventDetail.tsx")
        idx = body.index("<EventSnapshot")
        end = body.index("/>", idx)
        call = body[idx:end]
        self.assertIn('dataGx="snapshot"', call)


class SystemSettingsFreeTextCoverageTests(DsmSourceMixin, TestCase):
    """U5#14 — `/dsm/system` 재시작 사유 칸만이 아니라 나머지 자유 문장 다섯 자리도

    `safeFreeText()` 를 거치는가. 턴 AO(P-408)는 재시작 요청 이력의 「사유」 열
    하나만 감쌌다 — 같은 화면에 백업 선언 실패 사유(`back.reason`) · 회수증 실패
    사유(`receipts.data.reason`) · 저장 용량 사유(`storage.data?.reason`) ·
    저장 용량 각주(`capacity_note`) · 분모 출처(`capacity_source`) · 사용량 각주
    (`used_note`)까지 여섯 자리가 더 있었고, 이 자리들이 안 감싸여 있으면 셋째
    조건(그 사용자의 언어 — 절 ID 등)이 이 화면 어디선가 계속 걸린다
    (2026-09-29 turn_ao_8.json U5#14 실측 — 재시작 사유는 이미 고쳐졌는데도
    ◐ 상한이 그대로였다).
    """

    def setUp(self) -> None:
        super().setUp()
        self.body = self._read("features/dsm/pages/SystemSettings.tsx")

    def test_imports_safe_free_text(self) -> None:
        self.assertIn("safeFreeText", self.body)

    def test_backup_declared_false_reason_wrapped(self) -> None:
        self.assertIn("safeFreeText(back.reason)", self.body)

    def test_receipts_reason_wrapped(self) -> None:
        self.assertIn("safeFreeText(receipts.data.reason)", self.body)

    def test_storage_capacity_note_wrapped(self) -> None:
        self.assertIn("safeFreeText(storage.data.capacity_note)", self.body)

    def test_storage_used_pct_reason_wrapped(self) -> None:
        self.assertIn("safeFreeText(storage.data?.reason)", self.body)

    def test_storage_used_note_wrapped(self) -> None:
        self.assertIn("safeFreeText(storage.data.used_note)", self.body)

    def test_storage_capacity_source_wrapped(self) -> None:
        self.assertIn("safeFreeText(storage.data.capacity_source)", self.body)

    def test_restart_reason_column_still_wrapped(self) -> None:
        # 턴 AO(P-408) 가 먼저 고친 자리 — 회귀 방지.
        idx = self.body.index("title: '사유'")
        near = self.body[idx:idx + 200]
        self.assertIn("safeFreeText(", near)


class TheSelfTestCanFail(DsmSourceMixin, TestCase):
    """이 파일 자신을 망가뜨려 1 을 보는 시험 둘(§0.4 자기시험 감사 규약).

    문자열을 못 찾으면 진짜로 실패하는가 — 항상 통과하는 시험이 아님을 스스로
    증명한다.
    """

    def test_missing_data_gx_fails(self) -> None:
        body = self._read("features/dsm/pages/People.tsx")
        with self.assertRaises(AssertionError):
            self.assertIn('data-gx="이런-이름은-없다"', body)

    def test_missing_safe_free_text_call_fails(self) -> None:
        body = self._read("features/dsm/pages/SystemSettings.tsx")
        with self.assertRaises(AssertionError):
            self.assertIn("safeFreeText(존재하지_않는_필드)", body)
