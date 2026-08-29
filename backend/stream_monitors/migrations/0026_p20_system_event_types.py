# -*- coding: utf-8 -*-
"""P-20 ③ — `event_type` 열거에 **시스템 상태 둘**을 더한다 (2026-09-22).

    camera_down    카메라 무응답
    storage_high   저장 용량 임계

왜 열거를 늘리는가 — 죽은 카메라·저장 용량 신호는 `scripts/ops_monitor.py` 안에만 있었다
(온보딩 U1 #3 · U2 #19 · U5 #15). 운영 감시는 크론이 읽는 자리이지 **사람이 보는 화면이
아니다.** 같은 신호를 이벤트로 내면 W1 「시스템」 프리셋에서 새 화면 없이 U5 가 본다.

★ **열거 추가는 하위 호환이다** — 기존 값은 그대로이고 뜻도 바뀌지 않는다. D-294 가
  `flood` 를 더한 것과 같은 모양이고, 같은 규약을 지켰다: 계약 문서
  (`docs/contracts/detection-event.md` §열거값)와 등급 기본값
  (`detection_event_bridge.EVENT_TYPE_TO_SEVERITY`)을 **같은 커밋에서** 함께 고쳤다.

⚠ **W2-3 색 규칙(프런트)은 이 커밋에 없다.** 차선 C 가 같은 턴에 그 파일을 쓰고 있어
  건드리지 않았다 — 조율자에게 정확한 조각으로 보고했다. 규약이 요구하는 「같은 커밋」의
  나머지 반쪽이 비어 있다는 사실을 여기 적어 둔다(지우지 않고 사유를 남긴다).

★ DB 스키마는 바뀌지 않는다 — `choices` 는 Django 층의 검증이고 컬럼은 그대로
  `varchar(32)` 다. 그래도 마이그레이션을 남긴다: 남기지 않으면 `makemigrations --check`
  가 매번 「미반영 변경」을 외친다.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stream_monitors', '0025_backfill_response_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detectionevent',
            name='event_type',
            field=models.CharField(choices=[('person', '사람'), ('vehicle', '차량'), ('fire', '화재'), ('smoke', '연기'), ('intrusion', '침입'), ('sos', '구조요청'), ('flood', '침수'), ('camera_down', '카메라 무응답'), ('storage_high', '저장 용량 임계')], db_index=True, max_length=32),
        ),
    ]
