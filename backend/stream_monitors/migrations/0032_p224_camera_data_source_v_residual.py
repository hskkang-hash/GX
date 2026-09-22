# -*- coding: utf-8 -*-
"""P-224 ① 잔여 — **0031 이 못 본 한 줄** (2026-09-22 · 턴 AD · 차선 B).

0031 은 [실측 2026-09-21 11:37]에 「지금 있는 것」을 얼렸다(`GX-ONB-V-*` 여섯
줄, 전부 PROBE). 온보딩 계측기(`scripts/measure_onboarding_t.py` U5#4)는 그
시각 **이후에도** 한 번 더 돌았다 — 턴 AB V 회차, 같은 09-21.

    [실측 2026-09-22 · 차선 B · docker exec ORM]
      6144  GX-ONB-V-20260921T145138  data_source=live  표식 없음  ← **지금 청구 중**
      (이전 여섯 GX-ONB-V-* 는 전부 data_source=probe — 0031 이 이미 소급)

이 카메라의 계정 짝은 `common/migrations/0004_p224_seed_account_marks_v_residual.py`
가 같이 소급하는 `gxprobe_onb_20260921T145138`(pk=226)이다 — 이름의 타임스탬프가
`T145138` 로 **같다**(같은 회에 같은 절이 계정 하나·카메라 하나를 만든다,
`docs/agent/checkpoints/turn-ab/V.md:190-198` U5#1·U5#4).

★ 삭제 0. `data_source` 만 `probe` 로 적는다 — 0031 과 같은 낱말, 같은 근거 문형.
"""
from django.db import migrations

#: 출처 낱말. 정본은 `common/billing_marks.py`.
PROBE = "probe"

#: **얼어 있는 장부 — 규칙이 아니다.** (pk, code, 출처, 근거)
#: [실측 2026-09-22 · 차선 B · turn-ad] `GX-ONB-V-*` 계열의 마지막 한 줄 — 0031 이
#: 못 본 것.
V_RESIDUAL_CAMERAS = (
    (6144, "GX-ONB-V-20260921T145138", PROBE,
     "출생 표본(D-310) — 턴 AB V 회차, 온보딩 계측기(measure_onboarding_t U5#4)가 "
     "09-21 에 심은 탐침. data_source=live 로 **지금 청구 중**. 계정 짝(pk=226)은 "
     "common 0004 가 같이 소급한다"),
)


def mark_v_residual_camera(apps, schema_editor):
    """얼어 있는 한 줄에만 표식을 단다. **pk 와 code 가 둘 다 맞을 때만.**"""
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    for pk, code, source, _reason in V_RESIDUAL_CAMERAS:
        Stream.objects.filter(pk=pk, code=code).update(data_source=source)


def unmark_v_residual_camera(apps, schema_editor):
    """되돌리기 — 표식만 지운다. 행은 그대로다(삭제 0)."""
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    for pk, code, _source, _reason in V_RESIDUAL_CAMERAS:
        Stream.objects.filter(pk=pk, code=code).update(data_source="live")


class Migration(migrations.Migration):

    dependencies = [
        ("stream_monitors", "0031_p224_camera_data_source"),
    ]

    operations = [
        migrations.RunPython(mark_v_residual_camera, unmark_v_residual_camera),
    ]
