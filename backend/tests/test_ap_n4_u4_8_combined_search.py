# -*- coding: utf-8 -*-
"""온보딩 48행 U4#8 (`docs/agent/onboarding_48.md`) — 「조합 검색(사건번호·주소·
유형) 없음 → ◐ 상한」을 올린다 (턴 AP · P-424 · 차선 N4).

★ `scripts/measure_onboarding_t.py::rows_u4` 의 U4#8 술어는 `cap_half=True` 로
  **정본이 직접 ◐ 상한을 선언**해 두었다(그 행 주석 「조합 검색 없음 → ◐ 상한
  (정본 표기)」) — 이 시험은 그 계측기의 점수를 올리려는 것이 아니다(계측기
  불가침, P-203·P-399). 이 시험이 실측하는 것은 그 행이 가리키는 **실제 기능**
  (지자체 담당관이 목록에서 사건번호·주소·유형을 **함께** 좁힐 수 있는가)이다.

새 문 하나 — `GET /api/dsm/events/combined-search` (`apps/dsm/api_u4.py`).
`case_no` 는 PK 정확 일치(커널 `get_event` 문지기 그대로), 주소·유형은 나머지
조건과 **서버가** 대조한다 — 화면은 받은 것을 그대로 그린다(DA-04).

캐시 처리: 우회 — `setUp` 에서 `cache.clear()` 뒤 `NO_CACHE`(`X-No-Cache`) 클라이언트로 부른다(턴 AP 병합 · D-341).
"""
from __future__ import annotations

from django.apps import apps

from tests.test_api_contract import _bearer
from tests.test_dsm_app import DsmFixture

SEARCH = "/api/dsm/events/combined-search"


class CombinedSearchU48Test(DsmFixture):
    def setUp(self) -> None:
        super().setUp()
        from django.core.cache import cache
        from django.test import Client

        from tests.no_cache import NO_CACHE

        cache.clear()
        self.client = Client(**NO_CACHE)

    def _set_address(self, event_id: int, address: str) -> None:
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        Event._base_manager.filter(pk=event_id).update(address=address)

    def test_case_no_alone_is_pk_exact_match(self) -> None:
        eid = self._event(self.stream_a, event_type="fire")
        resp = self.client.get(SEARCH, {"case_no": eid}, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        body = resp.json()
        self.assertEqual(1, body["total"])
        self.assertEqual(eid, body["events"][0]["event_id"])

    def test_case_no_plus_address_plus_type_all_three_together(self) -> None:
        """사건번호·주소·유형 **셋을 동시에** 준다 — 온보딩 표가 부르는 그 조합."""
        eid = self._event(self.stream_a, event_type="fire")
        self._set_address(eid, "안양시 만안구 xx로 1")

        ok = self.client.get(
            SEARCH, {"case_no": eid, "address": "만안구", "event_type": "fire"},
            **_bearer(self.user_a))
        self.assertEqual(200, ok.status_code, ok.content[:300])
        self.assertEqual(1, ok.json()["total"], ok.content[:300])
        self.assertEqual("안양시 만안구 xx로 1", ok.json()["events"][0]["address"])

        # 주소가 안 맞으면 — 사건번호가 맞아도 **좁혀서** 0건 (서버가 대조한다).
        wrong_addr = self.client.get(
            SEARCH, {"case_no": eid, "address": "없는동네"}, **_bearer(self.user_a))
        self.assertEqual(200, wrong_addr.status_code)
        self.assertEqual(0, wrong_addr.json()["total"],
                         "주소가 안 맞는데도 결과가 남았습니다 — 조합 검색이 아니라 "
                         "사건번호 단독 열기입니다.")

        # 유형이 안 맞으면 — 마찬가지로 0건.
        wrong_type = self.client.get(
            SEARCH, {"case_no": eid, "event_type": "flood"}, **_bearer(self.user_a))
        self.assertEqual(200, wrong_type.status_code)
        self.assertEqual(0, wrong_type.json()["total"])

    def test_unknown_case_no_is_200_zero_not_404(self) -> None:
        """목록 문의 계약(F-09) — 없으면 빈 목록이지 오류가 아니다(화면이 목록으로 그린다)."""
        resp = self.client.get(SEARCH, {"case_no": 9_999_999}, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, resp.json()["total"])

    def test_other_tenants_case_no_is_not_leaked(self) -> None:
        """B 사건번호를 A 가 조회하면 0건 — 「없다」와 「남의 것이다」를 구별 못 하게
        한다(D-274, 커널 `get_event` 와 같은 격리 계약)."""
        eid_b = self._event(self.stream_b, event_type="fire")
        resp = self.client.get(SEARCH, {"case_no": eid_b}, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code)
        self.assertEqual(0, resp.json()["total"],
                         "B 테넌트 사건번호가 A 테넌트 조합 검색에 노출됐습니다 — 격리 실패.")

    def test_no_case_no_falls_back_to_existing_address_type_list(self) -> None:
        """사건번호 없이 주소·유형만 주면 기존 `/events` 와 같은 커널 경로(재사용)."""
        eid = self._event(self.stream_a, event_type="flood")
        self._set_address(eid, "군포시 산본동")
        resp = self.client.get(
            SEARCH, {"address": "산본동", "event_type": "flood"}, **_bearer(self.user_a))
        self.assertEqual(200, resp.status_code, resp.content[:300])
        ids = [e["event_id"] for e in resp.json()["events"]]
        self.assertIn(eid, ids)
