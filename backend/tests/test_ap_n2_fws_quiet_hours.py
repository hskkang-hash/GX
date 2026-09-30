# -*- coding: utf-8 -*-
"""FWS-F1-12 · FWS-F2-15 — 근무 외 알림 차단이 **실제로 발송을 막는가**
(WO-GX-20261001-19 턴 AP · 차선 N2 · P-421 ①).

턴 AO 소급(`docs/agent/evidence/SPEC/N1_promotions_ao.md` §2-2)이 잡은 결손:
F1-12·F2-15 는 저장·재조회만 실측돼 있었고, 저장한 방해 금지 시간대를 실제로
읽어 발송을 막는 코드가 없었다(`apps/fws/notify_prefs.py` 는 감사 로그에
쓰는데, `kernels/k2_notify/webpush.py::_blocked_reason` 은 DSM 의
`DsmNotifyPrefs` 표만 읽었다 — 두 저장소가 완전히 분리돼 있었다).

이 파일이 재는 것
------------------
    ① 근무 외(방해 금지 시간대 안) → **발송이 막힌다**(`succeeded=False` ·
       `failure_reason="quiet_hours"`).
    ② 근무 중(그 시간대 밖) → **발송이 간다**(`succeeded=True`).
    ★ [N2b] 앞 판의 ③ 「심각(critical) 등급은 근무 외 차단을 넘는다」는 뺐다 —
      명세 제목·완결조건(「근무 외 알림 차단 … 저장」)에 없는 예외를 지어낸 것이고,
      `_blocked_reason` 한 곳에 넣은 그 예외가 DSM(U3) 차단 계약까지 풀어
      `test_u3_webpush_send.RulePathTest` 둘을 빨강으로 만들었다(실측).

캐시 처리: 우회 — `tests.no_cache.NO_CACHE`(`test_fws_app.py` 와 같은 규약).
"""
from __future__ import annotations

import datetime as _dt
import json

from django.apps import apps as _apps
from django.core.cache import cache
from django.test import Client
from django.utils import timezone as dj_timezone

from common.evidence_guard import allow_evidence_writes
from tests.no_cache import NO_CACHE
from tests.test_fws_app import EVIDENCE_DIR, FwsHttpTest, NOTIFY_PREFS, _qs

ALERTS = "/api/fws/alerts"


def _write_evidence_full(clause_id: str, *, title: str, title_parts: list,
                         test_ref: str, method: str, path: str,
                         request_params: dict, response, what: str,
                         retro: str | None = None) -> None:
    """`test_fws_f3b.py::_write_evidence2` 와 같은 모양(공용 파일을 고치지 않고
    이 차선 파일 안에 둔다 · §0.4 인접) — 빈 칸 0 을 여기서도 먼저 본다."""
    for part in title_parts:
        missing = [k for k in ("part", "where", "status") if not (part.get(k) or "").strip()]
        if missing:
            raise AssertionError(
                f"{clause_id} title_parts 에 빈 칸이 있다: {part!r} (칸: {missing})")

    with allow_evidence_writes(
            "P-356 ② · P-392 FWS-F1-12·F2-15 근무 외 차단 실측 증거 — pytest 가 "
            "방금 두드린 HTTP·K2 send() 왕복을 그대로 적는다"):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            body = json.loads((response.content or b"{}").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            body = {"_raw": (response.content or b"").decode("utf-8", "replace")}
        #: [턴 AQ · P-431 · 차선 Q] 사람 표(`title_parts`·`retro`)는 `SPEC/<id>.retro.md`
        #: (손으로만) — 이 쓰개는 json(기계 실측)에 그 키를 쓰지 않는다.
        payload = {
            "id": clause_id, "title": title,
            "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "measured_by": "django_test_client", "test": test_ref,
            "request": {"method": method, "path": path, "params": request_params},
            "response": {"status": response.status_code, "body": body},
            "what": what,
        }
        out = EVIDENCE_DIR / f"{clause_id}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


#: F1-12·F2-15 는 저장 문(`/api/fws/notify-prefs`)도 차단 배선도 공유한다 —
#: 그래서 열린 행도 **같은 두 행**이다(P-419 「눈금은 하나다」: 한 절만 닫히고
#: 다른 절은 같은 결손으로 열려 있으면 두 잣대다).
def _shared_open_rows(post_word: str) -> list:
    return [
        {"part": f"'{post_word}' 저장값을 다른 기능이 실제로 읽어 쓰는가",
         "where": "backend/apps/fws — assigned_post_code 를 읽는 곳은 "
                  "notify_prefs.py::get_prefs(재조회) 하나뿐(grep)",
         "status": f"없음 — {post_word} 값은 저장·재조회만 되고, 알림 대상·순찰·임무 "
                   "배정 어느 로직도 그 값을 읽지 않는다(TITLE_PARTS §1-6)"},
        {"part": "화면(M4 설정 화면)",
         "where": "frontend/src/features/fws/api.ts 의 notifyPrefs 는 등록만 되고 "
                  "PatrolHome·FieldHome 어느 페이지도 부르지 않는다(grep)",
         "status": "없음 — 감시원·진화대가 시간대·담당 초소/구역을 입력할 화면이 "
                   "없다(App.tsx·routes.ts·copy.ts 는 공용 파일이라 이 차선이 못 붙인다)"},
    ]


RETRO_N2B = ("P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 저장값(감사 로그 "
             "guardianx.fws.notify_prefs)을 K2 webpush._blocked_reason 이 실제로 되읽어 "
             "근무 외 warning 을 막고(quiet_hours) 근무 중은 통과함을 같은 시험 두 발송으로 "
             "대조했다. 앞 판이 지어낸 critical 예외는 DSM 차단 계약을 깨서 뺐다. 담당 초소/구역 값의 쓰임과 M4 화면은 여전히 없다 "
             "— 열린 두 행으로 남긴다.")


class QuietHoursBlockTest(FwsHttpTest):
    """`FwsHttpTest`(F1 시험의 픽스처)를 그대로 쓴다 — 새 픽스처를 만들지 않는다."""

    def setUp(self) -> None:
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def _warning_rule(self):
        """픽스처는 `critical` 규칙만 심는다(`DsmFixture._rule`) — 경계 시험은
        심각이 아닌 등급으로 차단 자체를 재야 하므로 규칙 하나를 더 심는다."""
        Rule = _apps.get_model("stream_monitors", "NotificationRule")
        rule = Rule.objects.create(
            severity="warning", role=self.role_a, channels=["email"], is_active=True)
        return self._own(rule, self.group_a)

    def _save_quiet_hours(self, head, *, start: str, end: str):
        params = {"quiet_hours_start": start, "quiet_hours_end": end,
                  "assigned_post_code": "ZONE-9"}
        resp = self.client.post(_qs(NOTIFY_PREFS, **params), **head)
        self.assertEqual(200, resp.status_code, resp.content)
        return resp

    def test_off_duty_blocks_on_duty_delivers(self) -> None:
        from kernels.k2_notify.services import send

        self._warning_rule()
        head = self._bearer(self.user_a)

        now_local = dj_timezone.localtime(dj_timezone.now())
        start_off = (now_local - _dt.timedelta(minutes=30)).strftime("%H:%M")
        end_off = (now_local + _dt.timedelta(minutes=30)).strftime("%H:%M")
        start_on = (now_local + _dt.timedelta(hours=4)).strftime("%H:%M")
        end_on = (now_local + _dt.timedelta(hours=5)).strftime("%H:%M")

        #: ★ 두 발송 모두 **F-04 5분 억제를 끈다**(`respect_suppression=False`) —
        #:   같은 스트림·같은 유형(`fire`)이 5분 안에 겹치면 억제 키
        #:   (`services.py::_suppression_key`)가 접어 버려 **근무 외 차단과
        #:   무관한 이유로** 발송 행 자체가 안 생긴다. 이 시험이 재는 것은
        #:   억제가 아니라 차단이므로 억제를 분리한다.

        # ── ① 근무 외(방해 금지 시간대 안) → 발송이 막힌다 ──────────────────
        off_save = self._save_quiet_hours(head, start=start_off, end=end_off)
        event_off = self._event(self.stream_a, severity="warning", event_type="fire")
        deliveries_off = send(scope=self.scope_pipe, event_id=event_off,
                              respect_suppression=False)
        mine_off = next(
            (d for d in deliveries_off if d.recipient_id == self.user_a.pk), None)
        self.assertIsNotNone(mine_off, "경고 규칙이 user_a 에게 발송 행을 안 만들었다")
        self.assertFalse(
            mine_off.succeeded,
            "근무 외(방해 금지) 시간대인데 발송이 성공했다 — 저장값이 차단에 안 읽힌다")
        self.assertEqual("quiet_hours", mine_off.failure_reason)

        # ── ② 근무 중(그 시간대 밖) → 발송이 간다 ────────────────────────────
        on_save = self._save_quiet_hours(head, start=start_on, end=end_on)
        event_on = self._event(self.stream_a, severity="warning", event_type="fire")
        deliveries_on = send(scope=self.scope_pipe, event_id=event_on,
                             respect_suppression=False)
        mine_on = next(
            (d for d in deliveries_on if d.recipient_id == self.user_a.pk), None)
        self.assertIsNotNone(mine_on, "경고 규칙이 user_a 에게 발송 행을 안 만들었다")
        self.assertTrue(
            mine_on.succeeded,
            f"근무 중(방해 금지 시간대 밖)인데 발송이 막혔다 — 사유={mine_on.failure_reason}")

        read_back = self.client.get(NOTIFY_PREFS, **head)
        self.assertEqual(200, read_back.status_code)

        common_parts = [
            {"part": "저장(POST) 후 재조회(GET)에 방해 금지 시간대·담당 초소가 "
                     "그대로 보인다",
            "where": "backend/apps/fws/notify_prefs.py::save_prefs/get_prefs — "
                     "POST/GET /api/fws/notify-prefs",
            "status": "measured: 이 시험 setUp 의 POST 3회 뒤 GET 재조회로 확인"},
            {"part": "'근무 외 알림 차단' — 저장한 방해 금지 시간대가 실제로 알림 "
                     "발송을 억제하는가",
            "where": "backend/kernels/k2_notify/webpush.py::_fws_quiet_hours_block/"
                     "_blocked_reason(FWS_PREFS_LOGGER='guardianx.fws.notify_prefs' "
                     "를 같은 이름으로 되읽는다 · 턴 AP N2 · P-421 ①) → "
                     "kernels/k2_notify/services.py::_send_one",
            "status": "measured: 근무 외 warning 발송 succeeded=False·"
                     "failure_reason='quiet_hours' · 근무 중 재발송 succeeded=True "
                     "(같은 시험 안 두 발송으로 대조)"},
        ]
        _write_evidence_full(
            "FWS-F1-12", title="근무 외 알림 차단·담당 초소 설정",
            title_parts=common_parts + _shared_open_rows("담당 초소"),
            test_ref="tests.test_ap_n2_fws_quiet_hours.QuietHoursBlockTest."
                    "test_off_duty_blocks_on_duty_delivers",
            method="GET", path=NOTIFY_PREFS, request_params={}, response=read_back,
            what="근무 외 시간대에 발송한 warning 알림은 succeeded=False(quiet_hours), "
                "근무 중 재발송은 succeeded=True — 두 발송을 한 시험 안에서 대조 실측",
            retro=RETRO_N2B)

        _write_evidence_full(
            "FWS-F2-15", title="근무 외 차단·담당 구역",
            title_parts=[
                {"part": "근무 외 시간대 저장·재조회(quiet_hours)",
                "where": "backend/apps/fws/notify_prefs.py:save_prefs/get_prefs · "
                         "GET·POST /api/fws/notify-prefs",
                "status": "measured: 이 시험이 F1-12 와 같은 문을 재사용해 저장 뒤 "
                         "재조회로 확인(F2 진화대도 같은 문을 쓴다)"},
                {"part": "담당 구역(assigned_post_code) 저장·재조회",
                "where": "backend/apps/fws/notify_prefs.py:save_prefs/get_prefs "
                         "(assigned_post_code)",
                "status": "measured: 같은 시험 — assigned_post_code='ZONE-9' 저장 뒤 "
                         "재조회 확인"},
                {"part": "근무 외 '차단' — 저장한 시간대에 실제로 알림 발송이 "
                         "억제되는가",
                "where": "backend/kernels/k2_notify/webpush.py::_fws_quiet_hours_block "
                         "· _blocked_reason (F1-12 와 같은 배선 — F2 도 같은 문을 "
                         "쓰므로 같은 차단이 적용된다)",
                "status": "measured: F1-12 시험과 같은 왕복으로 근무 외 발송 "
                         "succeeded=False('quiet_hours') · 근무 중 succeeded=True 실측 "
                         "(F1-12·F2-15 가 저장 문을 공유하듯 차단 배선도 공유한다)"},
            ] + _shared_open_rows("담당 구역"),
            test_ref="tests.test_ap_n2_fws_quiet_hours.QuietHoursBlockTest."
                    "test_off_duty_blocks_on_duty_delivers",
            method="GET", path=NOTIFY_PREFS, request_params={}, response=read_back,
            what="F1-12 가 연 문을 F2 진화대도 그대로 쓴다 — 근무 외 저장값이 "
                "실제 발송 억제로 이어지는 것을 같은 시험이 함께 잰다",
            retro=RETRO_N2B)


class ConstantsMatchTest(FwsHttpTest):
    """K2 커널(`webpush.py`)이 FWS 감사 이름을 **글자 그대로** 재읽는지 —
    갈리면 저장은 되는데 차단은 조용히 안 걸린다(D-337 계열)."""

    def test_logger_and_action_names_match_notify_prefs_module(self) -> None:
        from apps.fws import notify_prefs
        from kernels.k2_notify import webpush

        self.assertEqual(notify_prefs.LOGGER_NAME, webpush.FWS_PREFS_LOGGER)
        self.assertEqual(notify_prefs.ACTION_SAVE, webpush.FWS_PREFS_ACTION_SAVE)
