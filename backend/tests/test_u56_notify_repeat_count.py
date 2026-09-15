# -*- coding: utf-8 -*-
"""U6 발송 — 「알림을 보내도 발송 수가 그대로다」의 서버 쪽 원인을 잰다 (턴 Q · 차선 U56).

무엇을 재는가
--------------
지시서가 준 두 가설:
    A) 수신자 0명 — K2 `NoRecipients`(규칙 0건)
    B) 억제 — F-04 5분 중복 억제(`kernels/k2_notify/services.py::suppress`)가
       같은 스트림·같은 이벤트종류에 **성공한 발송**이 있으면 새 발송을 **조용히
       접는다**(행조차 안 만든다). 이것은 결함이 아니라 계약이다 — 그러나 클라이언트가
       그 200/`total=0` 을 「실패」로 읽으면 「눌러도 안 된다」로 보인다(P-129 는
       그 해석 자리이고 F 차선이 가른다 — 이 파일은 **서버가 실제로 무엇을 했는지**만
       잰다).

★ 실측 (2026-09-15 · gx-shell · 개발 DB · 이름/개수만, 값 없음)
    group 4(ETRI-Group) 의 활성 알림 규칙 **9건** — critical 4 · info 2 · warning 3.
    각 규칙에 실제 구성원이 있다(예: `operator` 12명 · `fire_admin` 1명). 즉 **가설
    A(규칙 0건)는 이 테넌트에서 거짓이다.** 그리고 최근 이벤트들(예: id 4798~4801)은
    같은 스트림·같은 종류가 5분 창 안에 몰려 있어 **이미 한 건 이상의 성공한 발송이
    그 창 안에 있다** — 그래서 그 이벤트를 다시 두드리면 가설 B(억제)가 참이 된다.

이 시험은 그 두 모양을 **자기 픽스처 안에서 재현**해 가설 B 가 실제로 "200 인데
deliveries 가 안 는다"를 만드는지, 그리고 새 스트림(억제에 안 걸리는 쪽)을 두드리면
N+1 이 되는지를 HTTP 왕복으로 가른다.
"""
from __future__ import annotations

import json
import uuid
from datetime import timedelta

from django.conf import settings
from django.test import Client
from django.utils import timezone

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class NotifyRepeatCountTest(DsmFixture):
    """`DsmFixture` 는 이미 group_a 에 critical 규칙 1건(role_a · channel email)과
    구성원(user_a)을 갖고 있다 — **가설 A(규칙 0건)는 이 픽스처에서도 거짓**이다."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    def _notify(self, event_id):
        return self.client.post(
            "/api/dsm/events/%d/notify" % event_id,
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})

    def _delivery_count(self):
        resp = self.client.get(
            "/api/dsm/deliveries",
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code)
        return json.loads(resp.content.decode("utf-8"))["total"]

    def test_recipients_are_not_zero_ruling_out_hypothesis_a(self):
        """★ 가설 A 기각 — 이 테넌트에 규칙과 구성원이 실제로 있다.

        `resolve_recipients` 를 직접 부른다 — `setting_overview` 는 F-12 설정 문이라
        `tenant_admin` 자격을 요구하고, 이 시험이 묻는 것은 "수신자가 있는가"이지
        "이 계정이 설정을 볼 수 있는가"가 아니다(다른 질문을 섞지 않는다).
        """
        from kernels.k2_notify import resolve_recipients

        recipients = resolve_recipients(scope=self.scope_a, severity="critical")
        self.assertTrue(recipients, "critical 수신자가 0명입니다 — 가설 A 재현.")

    def test_a_second_notify_on_the_same_kind_within_the_window_is_suppressed_not_failed(self):
        """★ 가설 B 재현 — **같은 스트림·같은 종류**를 5분 안에 두 번 두드리면
        둘째는 200 이지만 `total=0` 이다. **행이 안 늘어난다** — 실패가 아니라 억제다.
        """
        first = self._event(self.stream_a, severity="critical", event_type="fire",
                            when=timezone.now() - timedelta(minutes=4))
        second = self._event(self.stream_a, severity="critical", event_type="fire",
                             when=timezone.now() - timedelta(minutes=1))

        before = self._delivery_count()
        resp1 = self._notify(first)
        self.assertEqual(200, resp1.status_code,
                         (resp1.content or b"")[:300].decode("utf-8", "replace"))
        body1 = json.loads(resp1.content.decode("utf-8"))
        self.assertGreater(body1["total"], 0, "첫 발송이 0건입니다 — 픽스처가 깨졌습니다.")
        after_first = self._delivery_count()
        self.assertEqual(before + body1["total"], after_first,
                         "첫 발송 뒤 /deliveries 가 N+1 이 아닙니다.")

        # ★ 여기가 이 시험의 핵심 관측이다 — **둘째는 200 이고 total=0** 이다.
        resp2 = self._notify(second)
        self.assertEqual(200, resp2.status_code,
                         (resp2.content or b"")[:300].decode("utf-8", "replace"))
        body2 = json.loads(resp2.content.decode("utf-8"))
        self.assertEqual(
            0, body2["total"],
            "억제가 걸리지 않았습니다 — 이 시험의 전제(같은 스트림·같은 종류·5분 안)가 "
            "바뀌었습니다. F-04 SUPPRESS_WINDOW 를 확인할 것.")
        self.assertEqual([], body2["deliveries"])
        after_second = self._delivery_count()
        self.assertEqual(
            after_first, after_second,
            "★ 발송 수가 그대로였던 자리 — 억제된 둘째 호출은 /deliveries 를 "
            "늘리지 않는다. 이것은 결함이 아니라 F-04 의 계약이다.")

    def test_a_different_kind_in_the_same_window_is_not_suppressed_and_adds_n_plus_one(self):
        """★ 대조 — **다른 이벤트종류**는 같은 창 안에서도 억제되지 않는다.

        억제가 "발송 자체가 죽었다"가 아니라 "같은 경보를 두 번 안 보낸다"임을
        보인다 — 서버는 여전히 살아서 새 종류는 N+1 로 늘린다.
        """
        fire = self._event(self.stream_a, severity="critical", event_type="fire",
                           when=timezone.now() - timedelta(minutes=3))
        self._notify(fire)
        before = self._delivery_count()

        flood = self._event(self.stream_a, severity="critical", event_type="flood",
                            when=timezone.now() - timedelta(minutes=1))
        resp = self._notify(flood)
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertGreater(body["total"], 0,
                           "다른 종류인데도 억제됐습니다 — suppress() 가 event_type 을 "
                           "안 보고 있을 수 있습니다.")
        after = self._delivery_count()
        self.assertEqual(before + body["total"], after,
                         "다른 종류 발송인데 /deliveries 가 N+1 이 아닙니다.")
