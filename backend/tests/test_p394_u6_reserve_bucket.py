# -*- coding: utf-8 -*-
"""P-394 — U6 카드 진행률 문 403 의 원인과 고침 (턴 AN · 조율자 E).

[실측 2026-09-29] U6(기계 · 외부 연계) 표는 예비 계정 `gxseed_u5_newop` 으로 연다
(`scripts/verify_onboarding_walk.py::U5_RESERVE_ACCOUNT`). 그 계정의 역할이
`fire_user` 하나라 `bucket_of` 가 **U1** 을 골랐고, `PERSONA_VIEWERS["U6"] == ("U5",)`
이므로 `GET /api/dsm/onboarding/progress?persona=U6` 가 403(not_yours)이었다.

고침은 **역할 설정 한 칸**(개발 DB · 세종 P-394): 그 계정에 본계정
`gxseed_u5_sysop` 과 같은 `admin` 역할 행을 더했다. 되돌리기 = 그 행을 뺀다
(`evidence/P-394/u6_reserve_role.md`). 코드는 바꾸지 않았다 — 이 시험은 그 판단이
기대는 두 사실(역할 → 버킷 · 버킷 → U6 표)을 못 박는다.
"""
from django.test import SimpleTestCase

from apps.dsm import onboarding


class U6ReserveBucketTest(SimpleTestCase):
    def test_admin_role_is_the_u5_bucket(self) -> None:
        buckets = dict(onboarding._role_buckets())
        self.assertIn("admin", buckets["U5"])

    def test_u5_may_open_the_u6_table(self) -> None:
        self.assertEqual(onboarding.resolve_bucket("U5", "U6"), ("U6", ""))

    def test_fire_user_alone_was_the_403(self) -> None:
        """고치기 전의 모양 — U1(fire_user) 은 U6 표를 못 본다(403 의 원인)."""
        self.assertIn("fire_user", dict(onboarding._role_buckets())["U1"])
        self.assertEqual(onboarding.resolve_bucket("U1", "U6"), (None, "not_yours"))
