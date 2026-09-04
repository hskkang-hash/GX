# -*- coding: utf-8 -*-
"""OPS-15 — **맥박 칸 하나**와 `camera_cluster_down` (2026-09-04 · 차선 Q).

두 가지를 한 마이그레이션에 담는다. 하나의 절이 요구하는 둘이고, 나눠 두면
「칸은 있는데 유형이 없는」 중간 상태가 배포 순서에 따라 생긴다.

    ① `StreamMonitor.last_frame_at`  — 맥박. 「조용함」과 「죽음」을 가르는 유일한 사실
    ② `DetectionEvent.EventType.camera_cluster_down` — 군집 두절

★ **열거 추가는 하위 호환이다** — 기존 값도 뜻도 안 바뀐다. D-294(`flood`) ·
  P-20 ③(`camera_down` · `storage_high`) 와 같은 모양이고, 같은 규약을 지켰다:
  계약 문서(`docs/contracts/detection-event.md` §열거값)를 같은 커밋에서 함께 고쳤다.

⚠ **W2-3 색 규칙(프런트 `frontend/src/features/dsm/severity.ts`)은 이 커밋에 없다.**
  이번 파에 차선 C 가 그 파일을 쓰고 있어 건드리지 않았다 — 0026 이 같은 사유를 남긴
  자리와 같다. 규약이 요구하는 「같은 커밋」의 나머지 반쪽이 비어 있다는 사실을 여기
  적어 둔다(지우지 않고 사유를 남긴다). 조율자에게 정확한 조각으로 보고했다.

★ `last_frame_at` 의 기본값은 **null 이고 백필하지 않는다.** `timezone.now()` 로 채우면
  한 번도 프레임을 준 적 없는 카메라가 「방금 살아 있었다」가 되고, 그 거짓말은 배포
  직후 5분 동안 모든 두절을 가린다. null 은 「아직 안 왔다」이고, 판정기는 그것을
  두절로 세지 않는다 (D-290 — 부재와 실패를 가른다).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stream_monitors', '0026_p20_system_event_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='streammonitor',
            name='last_frame_at',
            field=models.DateTimeField(
                blank=True, db_index=True, null=True,
                help_text="마지막 프레임 수신 시각(맥박). null 은 '아직 안 왔다'이지 "
                          "'죽었다'가 아니다. 군집 두절 판정은 camera_pulse.py 가 한다 (OPS-15)"),
        ),
        migrations.AlterField(
            model_name='detectionevent',
            name='event_type',
            field=models.CharField(
                choices=[('person', '사람'), ('vehicle', '차량'), ('fire', '화재'),
                         ('smoke', '연기'), ('intrusion', '침입'), ('sos', '구조요청'),
                         ('flood', '침수'), ('camera_down', '카메라 무응답'),
                         ('storage_high', '저장 용량 임계'),
                         ('camera_cluster_down', '카메라 군집 두절')],
                db_index=True, max_length=32),
        ),
    ]
