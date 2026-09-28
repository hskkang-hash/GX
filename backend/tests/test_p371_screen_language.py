# -*- coding: utf-8 -*-
"""P-371 · 턴 AL · 차선 L — 「셋째 조건」(그 사용자의 언어)이 다시 잡은 자리를 잠근다.

온보딩 계측(`scripts/measure_onboarding_t.py::third_condition_violations` →
`scripts/verify_ui_copy.scan_line`)이 round 5(turn_ak_5.json)에서 열 행을
초록→반·빨강→반으로 내렸다 — 화면이 결정 번호(`D-\\d{3}`) · 절 ID(`P-\\d{1,3}` 등) ·
마크다운 강조(`**`) · 발송 채널 코드(email/webpush/sms/log/…)를 사용자 본문에
그대로 흘렸기 때문이다(U1#9 · U2#3 · U3#19 · U5#9 · U5#10 · U5#14).

이 파일은 **그 판정기를 다시 만들지 않는다**(D-479 — 두 벌은 반드시 어긋난다).
대신 이번 턴에 고친 자리 하나하나가 **다시 새지 않는가**를 소스 텍스트로 좁혀 잰다:
프런트는 정적 소스를 읽고(`ScreenWiringTests`), 백엔드는 실제로 그 모듈을 임포트해
문자열 값을 확인한다 — 값을 읽을 수 있는 곳은 값으로, 소스로만 잴 수 있는 프런트는
소스로 잰다.

캐시 처리: 해당 없음 — 이 파일은 HTTP 를 한 번도 때리지 않는다(정적 소스 읽기 +
파이썬 모듈 임포트뿐이라 `Client`/캐시 미들웨어를 지나지 않는다).

절대 금지 (D-105 · D-224): skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import TestCase

#: 이 판정기가 잡던 그 정규식 — **베끼지 않고** 이 파일 안에서만, 이미 고친 자리가
#: 다시 그 모양으로 돌아오는지 보는 데 쓴다(스캐너 자체의 재구현이 아니다 · D-479).
SECTION_ID = re.compile(r"\b(?:UX|SEC|OPS|QA|LAW|PERF|ISO|F|P|W|AC|FR|NFR|DA)-\d{1,3}\b")
MARKDOWN_EMPHASIS = re.compile(r"\*\*")

RAW_CHANNEL_CODES = ("email", "webpush", "sms", "push", "webhook")


def _frontend_src() -> Path | None:
    for base in (Path("/repo/frontend/src"),
                 *(p / "frontend" / "src" for p in Path(__file__).resolve().parents)):
        if (base / "App.tsx").is_file():
            return base
    return None


class NotifyChannelDictionaryTests(TestCase):
    """U5#9 · U5#10 · U1#9 · U2#3 · U3#19 — 발송 채널 코드가 사전을 거치는가."""

    def setUp(self) -> None:
        self.src = _frontend_src()
        self.assertIsNotNone(self.src, "frontend/src 를 못 찾았다 — 판정 불가를 초록으로 두지 않는다")

    def test_copy_ts_declares_notify_channel_label(self) -> None:
        """새 사전 — 감사표의 CHANNEL_LABEL 과 다른, 발송 채널 전용 사전."""
        copy_ts = (self.src / "features/dsm/copy.ts").read_text(encoding="utf-8")
        self.assertIn("export const NOTIFY_CHANNEL_LABEL", copy_ts)
        self.assertIn("export function notifyChannelLabel", copy_ts)
        for code in RAW_CHANNEL_CODES + ("log",):
            self.assertIn(f"{code}:", copy_ts,
                          f"NOTIFY_CHANNEL_LABEL 에 '{code}' 항목이 없다")

    def test_delivery_outcome_no_longer_echoes_raw_channel(self) -> None:
        """`channelDisplayLabel` 이 사람에게 닿는 채널도 사전의 말로 그리는가.

        ★ 종전엔 `return reachesAPerson(channel) ? channel : LOG_ONLY_CHANNEL_LABEL;`
          였다 — 그 한 줄이 email·webpush 를 영문 그대로 세 화면에 실어 날랐다.
        """
        body = (self.src / "features/dsm/deliveryOutcome.tsx").read_text(encoding="utf-8")
        self.assertIn("notifyChannelLabel(channel)", body)
        self.assertNotRegex(
            body, r"return reachesAPerson\(channel\) \? channel :",
            "channelDisplayLabel 이 다시 원문 채널 코드를 그대로 돌려주고 있다",
        )

    def test_event_detail_channel_column_has_render(self) -> None:
        """U1#9 · U2#3 — 발송 이력 표의 「채널」 칸에 렌더 함수가 있는가.

        ★ 종전엔 `{ title: '채널', dataIndex: 'channel', width: 110 }` 뿐이었다 —
          렌더 함수가 없어 antd 가 `row.channel` 원문을 그대로 찍었다.
        """
        body = (self.src / "features/dsm/pages/EventDetail.tsx").read_text(encoding="utf-8")
        self.assertIn("channelDisplayLabel(v)", body)
        self.assertNotRegex(
            body, r"title: '채널',\s*dataIndex: 'channel',\s*width: 110,\s*\},",
            "발송 이력 「채널」 칸이 렌더 함수 없이 원문을 다시 찍고 있다",
        )

    def test_notify_settings_uses_dictionary_everywhere(self) -> None:
        """U5#9 · U5#10 — `/dsm/notify` 의 채널 표시 다섯 자리가 전부 사전을 거치는가."""
        body = (self.src / "features/dsm/pages/NotifySettings.tsx").read_text(encoding="utf-8")
        self.assertIn("notifyChannelLabel", body)
        # 다섯 자리: 고를 수 있는 채널 목록 · 등급별 도달 채널 · 규칙 표 채널 열 ·
        # 저장 확인 문장 · 채널 카드 · 시험 발송 문장 — 전부 이 이름을 거친다.
        self.assertGreaterEqual(
            body.count("notifyChannelLabel("), 6,
            "notifyChannelLabel 호출이 다섯 자리보다 적다 — 어딘가 원문이 남았다",
        )
        # 종전의 원문 노출 자리 — 다시 생기면 실패한다.
        # ⚠ `key={c.channel}` 은 React 키일 뿐 화면 글자가 아니다 — 그것까지
        #   금지하면 이 시험이 정당한 코드를 잡는다. 좁혀서 본다: 화면 글자 자리
        #   (`<Text …>{c.channel}</Text>`)에만 원문이 없는가.
        self.assertNotRegex(body, r"<Text[^>]*>\{c\.channel\}</Text>")
        self.assertNotIn("cs.join(' · ')", body)


class OpsTasksCopyTests(TestCase):
    """U5#14 — `/dsm/system` 저장 용량·백업 카드가 절 ID·마크다운을 다시 흘리는가."""

    def test_storage_capacity_note_has_no_markdown(self) -> None:
        from common.ops_tasks import STORAGE_CAPACITY_NOTE

        self.assertNotRegex(STORAGE_CAPACITY_NOTE, MARKDOWN_EMPHASIS)
        # 뜻은 그대로 — 낱말이 사라지지 않았는지도 함께 본다.
        self.assertIn("선언값", STORAGE_CAPACITY_NOTE)
        self.assertIn("같은 그릇을 재지 않습니다", STORAGE_CAPACITY_NOTE)

    def test_backup_declaration_reason_has_no_decision_id_or_markdown(self) -> None:
        """`backup_declaration()` 의 미선언 사유 문장 — **소스로 좁혀** 잰다.

        ★ 이 함수를 직접 불러 재려면 환경·settings 를 여러 겹 흉내내야 하고
          (`OPS_BACKUP_DIR` · `OPS_BACKUP_SCHEDULE_ENABLED` · beat 표 …), 그 흉내가
          실제 컨테이너 환경과 어긋나면 **판정 자체가 거짓 초록/거짓 빨강**이 된다.
          이 문장은 f-string 리터럴이라 소스에서 그대로 읽을 수 있다 — 그래서 값이
          아니라 **그 리터럴이 있던 함수 몸통 전체**를 잰다(`test_u56_backup_declaration.py`
          가 실제 동작은 이미 문지기·404 갈래로 잰다 — 여기서 되풀이하지 않는다).
        """
        path = (Path(__file__).resolve().parents[1] / "common" / "ops_tasks.py")
        body = path.read_text(encoding="utf-8")
        start = body.index('"reason": "" if declared else (')
        end = body.index("\n    }", start)  # 이 반환 딕셔너리가 닫히는 자리
        literal = body[start:end]
        self.assertIn("백업 선언이 완전하지 않습니다", literal,
                      "backup_declaration() 의 사유 문장을 못 찾았다 — 함수가 바뀌었다")
        self.assertNotIn("(P-67)", literal,
                         "backup_declaration() 이 다시 절 ID(P-67)를 화면 문장에 흘린다")
        self.assertNotRegex(literal, MARKDOWN_EMPHASIS,
                            "backup_declaration() 이 다시 마크다운 강조를 화면 문장에 흘린다")
        # 기존 시험(test_u56_backup_declaration.py::assertIn("OPS_BACKUP_DIR", ...))
        # 이 재는 실제 값은 `BACKUP_DECLARATION_ENVS`(그 안에 "OPS_BACKUP_DIR")를
        # 그대로 이어 붙인다 — 그 이음이 여전히 있는가를 이름으로 본다.
        self.assertIn("BACKUP_DECLARATION_ENVS", literal)
        self.assertIn("선언 없음", literal)

    def test_channel_note_log_entry_has_no_markdown(self) -> None:
        from kernels.k2_notify.rule_admin import CHANNEL_NOTE

        self.assertNotRegex(CHANNEL_NOTE["log"], MARKDOWN_EMPHASIS)
        self.assertIn("사람이 아니라 로그에 도달한다", CHANNEL_NOTE["log"])


class EmailSendAllowedReasonTests(TestCase):
    """U1#9 · U2#3 — 발송 이력 「실패 사유」 칸(`failure_reason`)의 절 ID·마크다운."""

    def test_send_allowed_reasons_have_no_section_id_or_markdown(self) -> None:
        from kernels.k2_notify.channels import EmailChannel

        # 개발 환경엔 보통 허용 목록이 있어 이 경로가 안 걸릴 수 있다 — 그래도
        # 걸리는 두 갈래(목록 없음 · 목록 밖)를 직접 만들어 함수 본연의 문장을 본다.
        from unittest import mock

        with mock.patch("kernels.k2_notify.channels._allowed_domains", return_value=set()):
            empty = EmailChannel.send_allowed("x@yopmail.com")
        self.assertFalse(empty.ok)
        self.assertNotRegex(empty.reason or "", SECTION_ID, empty.reason)
        self.assertNotRegex(empty.reason or "", MARKDOWN_EMPHASIS, empty.reason)

        with mock.patch("kernels.k2_notify.channels._allowed_domains",
                        return_value={"yopmail.com"}):
            outside = EmailChannel.send_allowed("x@notyopmail.com")
        self.assertFalse(outside.ok)
        self.assertNotRegex(outside.reason or "", SECTION_ID, outside.reason)
        self.assertNotRegex(outside.reason or "", MARKDOWN_EMPHASIS, outside.reason)


class WebhookAuditReasonTests(TestCase):
    """U4#16 — 감사 「사유」 칸이 절 ID 를 다시 흘리는가."""

    def test_issue_reason_has_no_section_id(self) -> None:
        path = (Path(__file__).resolve().parents[1] / "apps" / "dsm"
                / "webhook_key_service.py")
        body = path.read_text(encoding="utf-8")
        m = re.search(r'reason="([^"]*구독 등록과 함께 서명키 생성[^"]*)"', body)
        self.assertIsNotNone(m, "감사 사유 문자열을 못 찾았다")
        self.assertNotRegex(m.group(1), SECTION_ID,
                            f"감사 사유에 절 ID 가 남아 있다: {m.group(1)!r}")
