# -*- coding: utf-8 -*-
"""OPS-19 — **손으로 뜬 덤프는 RPO 가 아니다.** 판정문 한 장으로 beat 과 사람을 가른다.

캐시 처리: 해당 없음 — 이 파일은 HTTP 를 **한 번도 안 때린다.** 셀러리 beat 일정표와
`common.ops_tasks.ops_backup_beat` 의 시그니처·판정문 칸만 읽는다. 응답이 없으므로
응답 캐시가 낄 자리가 없다. [조율자 확인: `Client`·`requests`·`urlopen` **0건**]

왜 이 파일이 필요한가 — **게이트가 그렇게 말했다**
--------------------------------------------------
2026-09-24 에 `scripts/verify_backup_autonomy.py` 가 초록을 냈다(beat 이 부른 덤프가
10.1시간 전). 그래서 절을 `구현 · closed` 로 올렸더니 GA 판정기가 즉시 물었다:

    FAIL 영역 4 · OPS-19: '구현' 인데 **증명이 없다** — 그런 칸은 '미측정'이다 (D-346)

옳은 빨강이다. 게이트는 **오늘 그랬다**를 재고, 시험은 **그렇게 되도록 배선돼 있다**를
잰다. 둘은 다른 물음이고, 게이트만 있으면 내일 누가 배선을 지워도 **다음 05:00 까지**
아무도 모른다. 이 파일이 그 사이를 메운다.

무엇을 잠그는가 — **한 글자**
------------------------------
`config/celery.py` 의 `ops-backup-daily` 가 `kwargs={"invoked_by": "beat"}` 를 **명시로**
건네고, 함수 기본값은 `"manual"` 이다. 그 한 글자가 판정문에 남아 「저절로 돌았다」와
「사람이 떴다」를 가른다. `kwargs` 가 사라지면 beat 이 불러도 판정문에는 `manual` 이
남고, 게이트 ㉤ 은 **영원히 빨강**이 된다 — 그런데 그때 비난받는 것은 배선이 아니라
「백업이 안 돈다」가 된다. 그 오독을 막는 것이 이 파일의 전부다.

★ 왜 표준 메커니즘을 안 쓰나: `django_celery_beat` 가 넘기는 `periodic_task_name` 은
  태스크 메시지에 **안 실린다**(celery/kombu 소스에 그 필드가 없다 — 턴 AE 차선 E 실측).
  그래서 kwargs 로 직접 배선했고, 이 시험이 그 선택을 고정한다.
"""
from __future__ import annotations

import inspect

from django.test import TestCase

from common import ops_tasks

#: beat 일정표에서 이 절이 지키는 항목 하나.
SCHEDULE_KEY = "ops-backup-daily"
TASK_NAME = "common.ops_backup_beat"


def _schedule() -> dict:
    from config.celery import app

    return dict(app.conf.beat_schedule or {})


class TheBeatEntryCarriesItsOwnName(TestCase):
    """① beat 이 부를 때 **beat 이라고 적히는가.**"""

    def test_the_backup_entry_is_registered(self):
        entry = _schedule().get(SCHEDULE_KEY)
        self.assertIsNotNone(
            entry,
            "beat 일정표에 «%s» 가 없습니다. 등록이 사라지면 백업은 **한 번도 안 돌고**, "
            "그때 판정기는 「덤프가 낡았다」고만 말합니다 — 뿌리가 안 보입니다." % SCHEDULE_KEY)
        self.assertEqual(
            TASK_NAME, entry.get("task"),
            "«%s» 가 부르는 태스크 이름이 바뀌었습니다: %r" % (SCHEDULE_KEY, entry.get("task")))

    def test_the_entry_passes_invoked_by_beat_explicitly(self):
        """★★ 이 절의 한 글자. 이 kwargs 가 사라지면 게이트 ㉤ 은 영원히 빨강이다."""
        entry = _schedule().get(SCHEDULE_KEY) or {}
        kwargs = entry.get("kwargs") or {}
        self.assertEqual(
            "beat", kwargs.get("invoked_by"),
            "«%s» 가 `kwargs={'invoked_by': 'beat'}` 를 **명시로** 안 건넵니다(지금 %r). "
            "beat 이 불러도 판정문에는 기본값 `manual` 이 남고, 그러면 "
            "`verify_backup_autonomy.py` 의 ㉤ 은 **저절로 돈 덤프를 손으로 뜬 것으로** "
            "읽습니다 — 백업은 도는데 절은 영원히 빨강입니다." % (SCHEDULE_KEY, kwargs))


class TheHandCallStaysDistinguishable(TestCase):
    """② **음성 대조** — 사람이 부르면 사람이라고 적히는가.

    ①만 있으면 「`invoked_by` 가 beat 이다」만 지킨다. 그런데 기본값까지 `"beat"` 로
    바뀌면 ①은 **그대로 초록**이면서 사람이 셸에서 뜬 덤프도 beat 으로 적힌다 —
    그 순간 이 절이 묻던 것(「손으로 뜬 덤프는 RPO 가 아니다」)이 통째로 사라진다.
    """

    def test_the_default_is_manual_not_beat(self):
        sig = inspect.signature(ops_tasks.ops_backup_beat)
        default = sig.parameters["invoked_by"].default
        self.assertEqual(
            "manual", default,
            "`ops_backup_beat(invoked_by=...)` 의 기본값이 %r 입니다. `\"beat\"` 이면 "
            "**사람이 셸에서 뜬 덤프도 beat 으로 적히고**, 판정문 한 장으로 둘을 가르던 "
            "이 절의 술어가 통째로 무너집니다 — 그런데 색은 초록으로 남습니다." % (default,))

    def test_the_parameter_is_the_first_one_so_a_positional_call_still_says_who(self):
        """자리 인자로 불러도 그 칸이 채워지는가 — 이름을 안 쓰는 호출자가 있을 수 있다."""
        params = list(inspect.signature(ops_tasks.ops_backup_beat).parameters)
        self.assertEqual(
            "invoked_by", params[0],
            "`invoked_by` 가 첫 인자가 아닙니다(%r). 자리 인자로 부르는 코드가 생기면 "
            "엉뚱한 칸에 호출자 이름이 들어갑니다." % (params,))


class EveryVerdictSaysWhoCalledIt(TestCase):
    """③ **모든 갈래**가 그 칸을 싣는가 — 한 갈래라도 비면 그날의 판정문이 침묵한다."""

    #: `ops_backup_beat` 이 낼 수 있는 판정값 전수. 하나라도 `invoked_by` 를 안 실으면
    #: 그날 게이트는 「호출자가 beat 이 아니다(None)」로 빨강이 되고, 사람은 백업이
    #: 안 돈 줄 안다 — **실제로는 돌았는데 판정문이 말을 안 한 것**이다.
    VERDICTS = ("SKIPPED", "SKIPPED_UNDECLARED", "UNKNOWN", "ALARM", "OK")

    def test_the_source_puts_invoked_by_in_every_payload(self):
        src = inspect.getsource(ops_tasks.ops_backup_beat)
        payloads = [line for line in src.splitlines() if "payload = {" in line]
        self.assertTrue(
            payloads,
            "`ops_backup_beat` 안에서 판정문을 짓는 자리를 한 곳도 못 찾았습니다 — "
            "이 시험이 읽는 법이 낡았습니다(구현이 바뀌었으면 여기를 같이 고치십시오).")
        missing = [line.strip()[:60] for line in payloads if "invoked_by" not in line]
        self.assertEqual(
            [], missing,
            "판정문을 짓는 %d 곳 중 %d 곳이 `invoked_by` 를 안 싣습니다: %s. "
            "그 갈래로 끝난 날은 게이트가 「호출자가 beat 이 아니다」로 읽고, "
            "사람은 **백업이 안 돈 줄 압니다** — 실제로는 돌았는데 말을 안 한 것입니다."
            % (len(payloads), len(missing), missing))

    def test_the_known_verdicts_are_still_the_ones_the_gate_expects(self):
        """게이트와 시험이 같은 낱말을 보는가 — 다른 낱말을 보면 둘 다 초록인데 갈린다."""
        src = inspect.getsource(ops_tasks.ops_backup_beat)
        absent = [v for v in self.VERDICTS if ('"%s"' % v) not in src and ("'%s'" % v) not in src]
        self.assertEqual(
            [], absent,
            "판정값 %s 가 구현에서 사라졌습니다. 게이트(`verify_backup_autonomy.py`)와 "
            "이 시험이 서로 다른 낱말을 보고 있으면 **둘 다 초록인데 뜻이 갈립니다.**" % absent)
