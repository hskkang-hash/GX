# -*- coding: utf-8 -*-
"""P-178 U56 ① — **감사 화면이 여는 채널의 울타리** (대표 결정 ⑤ · 2026-09-21).

대표 결정: **「넓혀라 — 접속 로그는 빼고」**.
`apps/dsm/audit.READABLE_LOGGER_NAMES` 가 2 → 15 가 됐다.

왜 이 시험이 있나 — **넓히는 것은 되돌리기 어렵다**
---------------------------------------------------
화면에 한 번 올라간 것은 사람이 이미 봤다. 그래서 이 결정은 **글이 아니라 배선**이어야
하고, 배선은 시험이 잡고 있어야 한다. 이 파일이 묻는 것은 셋이다:

    ① 울타리와 접속 로그 목록이 **겹치지 않는가** (글자 대조)
    ② 화면이 내는 `channels` 가 **울타리 그 자체인가** (두 벌이면 한쪽이 거짓말한다)
    ③ 접속 로그 행이 **실제로 안 나오는가** (행을 심어 놓고 라우트 뒷면을 두드린다)

★ ③이 이 파일의 본체다. ①②는 글자만 본다 — 글자가 맞아도 질의가 틀릴 수 있고,
  그때 「목록은 옳은데 화면에는 뜬다」가 된다. 그 상태가 가장 나쁘다:
  목록을 읽은 사람이 안심하기 때문이다.

⚠ **0행이라 안 연 넷은 여기서 안 잠근다.** `guardianx.k5.credentials` 등 넷은
  「오늘 실물을 못 봤다」라서 뺀 것이고(D-400), 그것은 **바뀔 결정**이다. 바뀔 결정을
  시험으로 못박으면 다음 사람이 결정을 못 바꾸거나, 시험부터 지우고 바꾼다.
  그 넷의 이름과 사유는 `apps/dsm/audit.py` 머리말에 글로 있다.
"""
from __future__ import annotations

from django.apps import apps
from django.test import TestCase

from apps.dsm import audit


class TheFenceAndTheAccessLogsDoNotOverlapTest(TestCase):
    """① 글자 대조 — DB 가 필요 없다."""

    def test_no_access_log_name_is_opened(self) -> None:
        overlap = sorted(set(audit.READABLE_LOGGER_NAMES)
                         & set(audit.ACCESS_LOG_LOGGER_NAMES))
        self.assertEqual(
            [], overlap,
            f"접속 로그 채널이 감사 화면에 열려 있습니다: {overlap}. "
            f"대표 결정 ⑤ 의 조건이 그 이름들을 빼는 것입니다 — dj-core 는 요청 한 건마다 "
            f"이 표에 한 행을 쌓고, 그중 `security` 의 본문에는 **접속자 IP** 가 있습니다.")

    def test_the_fence_has_no_duplicate_name(self) -> None:
        """같은 이름이 두 번 들어 있으면 「열다섯」이라는 셈이 거짓이 된다."""
        names = list(audit.READABLE_LOGGER_NAMES)
        dupes = sorted({n for n in names if names.count(n) > 1})
        self.assertEqual([], dupes, f"울타리에 이름이 중복됩니다: {dupes}")


class TheScreenShowsExactlyTheFenceTest(TestCase):
    """②③ — 라우트 뒷면(`read_page`)을 실제로 두드린다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        CoreUser = apps.get_model("user", "CoreUser")
        cls.admin = CoreUser.objects.create_user(
            username="u56_channel_admin", password="test-only-not-a-secret",
            is_active=True, email="u56_channel_admin@test.invalid",
        )
        #: 전역 관리자로 읽는다 — 테넌트 좁히기가 아니라 **울타리**를 재는 시험이라
        #: 좁히기가 답을 가리면 안 된다(`_tenant_actor_ids` 는 전역이면 None 을 준다).
        CoreUser.objects.filter(pk=cls.admin.pk).update(is_superuser=True)
        cls.admin.refresh_from_db()

    @staticmethod
    def _row(logger_name: str, note: str):
        """감사 표에 행 하나. **`audit_writer.write` 를 안 쓴다** — 그 문은 체인을 잇고
        `logger_name` 을 부르는 쪽이 고르지 못하게 되어 있다. 여기서 심고 싶은 것은
        *dj-core 가 쌓은 것처럼 생긴 행*이라 표에 직접 넣는다(시험 DB 다)."""
        AuditLogs = apps.get_model("logger", "AuditLogs")
        return AuditLogs.objects.create(
            logger_name=logger_name, level_name="INFO",
            api_name="/probe", api_method="GET", note=note, msg=note,
        )

    def _read(self):
        from common.tenant_scope import TenantScope

        return audit.read_page(scope=TenantScope.of(self.admin),
                               page=1, page_size=audit.PAGE_SIZE_MAX)

    def test_the_payload_channels_are_the_fence_itself(self) -> None:
        """② 화면이 내는 목록이 울타리와 **같은 객체에서** 나와야 한다.

        두 벌이면 한쪽만 늘어나는 날이 오고, 그날 화면은 「이 채널만 봅니다」라고
        말하면서 다른 것을 보여 준다.
        """
        self.assertEqual(list(audit.READABLE_LOGGER_NAMES),
                         self._read()["channels"],
                         "화면이 내는 `channels` 가 울타리와 다릅니다 — 두 벌입니다.")

    def test_an_access_log_row_never_reaches_the_screen(self) -> None:
        """③ **본체.** 접속 로그처럼 생긴 행을 심어 놓고 뒷면을 두드린다."""
        for name in audit.ACCESS_LOG_LOGGER_NAMES:
            self._row(name, f"u56-fence-probe {name}")
        opened = self._row(audit.READABLE_LOGGER_NAMES[0], "u56-fence-probe opened")

        payload = self._read()
        got = {item["channel"] for item in payload["items"]}
        leaked = sorted(got & set(audit.ACCESS_LOG_LOGGER_NAMES))
        self.assertEqual(
            [], leaked,
            f"접속 로그 행이 감사 화면에 떴습니다: {leaked}. "
            f"(심은 행 {len(audit.ACCESS_LOG_LOGGER_NAMES)}건 · 쪽에 뜬 채널 {sorted(got)})")
        self.assertIn(
            opened.pk, {item["audit_id"] for item in payload["items"]},
            "열어 둔 채널의 행조차 안 보입니다 — 이 시험이 **아무것도 안 재고** 있습니다. "
            "분모 0 인 초록은 초록이 아닙니다 (D-301).")

    def test_a_newly_opened_channel_actually_shows_up(self) -> None:
        """넓힌 것이 **정말 넓어졌는가** — 턴 Z 에 새로 연 이름으로 직접 묻는다.

        ★ 이 시험이 없으면 위 시험은 「아무것도 안 열어도」 초록이다: 접속 로그가
          안 뜨는 가장 쉬운 방법은 **아무것도 안 뜨게 하는 것**이다.
        """
        newly = "guardianx.law02a.retention"
        self.assertIn(newly, audit.READABLE_LOGGER_NAMES,
                      "턴 Z 에 연 이름이 울타리에서 사라졌습니다 — 되돌린 것이라면 "
                      "이 시험도 같은 커밋에서 고치십시오(대표 결정 ⑤).")
        row = self._row(newly, "u56-fence-probe newly-opened")
        self.assertIn(row.pk, {i["audit_id"] for i in self._read()["items"]},
                      f"{newly} 를 열었는데 그 행이 화면에 안 뜹니다.")
