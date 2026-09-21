# -*- coding: utf-8 -*-
"""P-224 ① — **카메라 표에 청구 출처 칸을 더한다** (2026-09-21 · 턴 AB · 차선 B).

무엇을 고치나 — **우리가 심은 카메라에 고객이 돈을 내고 있었다**
---------------------------------------------------------------
    [실측 2026-09-21 11:37 · 마이그레이션 전]
      ETRI-Group 살아 있는 카메라           15대   ← 전부 청구에 들었다
        그중 우리가 심은 것                 11대   (탐침 7 · 검수 씨앗 1 · 훈련 3)
        고객의 것                            3대
        분류 미정                            1대   (`GX-U5-01` — 아래 ⚠)

사건·발송은 `track_id` 에 얹힌 표식으로 이미 빠지는데(P-193 · P-201) **카메라 표에는
표식을 걸 자리가 없었다.** 이 마이그레이션이 그 자리를 만들고, 위 11대에 표식을 단다.

두 조각이다 — **칸**과 **소급**
-------------------------------
    ① `AddField data_source` · 기본값 `live`
    ② 얼어 있는 11줄에 표식 (아래 `SEED_CAMERAS`)

★ **기본값이 `live` 인 것이 규약이다.** 표식 없음 = **고객의 것**이다. 반대로 두면
  표식을 안 단 고객 카메라가 조용히 공짜가 되고, **공짜가 된 것은 안 보인다** —
  틀린 청구는 고객이 항의하지만, 안 한 청구는 아무도 말하지 않는다.

★ **소급은 이름으로 안 한다 — pk 로 언다** (D-280).
  `code__startswith` 같은 규칙을 여기 쓰면 그것은 **규칙**이고, 규칙은 다음 달에도
  돈다 — 고객이 제 카메라 이름을 `GX-…` 로 짓는 날 그 카메라가 조용히 공짜가 된다.
  아래 목록은 **규칙이 아니라 장부**다: 2026-09-21 11:37 에 사람이 한 줄씩 보고
  근거를 적은 11줄이고, 여기서 끝난다. **세는 코드는 이름을 모른다.**

★ **pk 와 code 를 함께 본다.** pk 만 보면 다른 DB(스테이징·시험)에서 **엉뚱한
  카메라**에 표식이 붙는다 — 그 DB 의 3947번은 우리 탐침이 아니다. 둘이 다 맞을 때만
  손대고, 안 맞으면 **조용히 건너뛴다**(그 DB 에는 우리 씨앗이 없다는 뜻이다).

★ **삭제 0.** 행을 지우는 것이 아니라 **청구에서 빼는** 것이다 (P-222).
  운영자의 카메라 목록은 이 11대를 **그대로 본다** — 바뀌는 것은 셈뿐이다 (D-497).

⚠ **`GX-U5-01`(안양천서로카메라)은 안 건드렸다.** `GX-` 접두 말고는 근거가 없다.
  접두는 정황이고, **정황을 청구 근거로 쓰지 않는다** (D-301). 그 1대는 이 표에서
  **회색**이고 지금은 고객 쪽에 선다 — 근거가 생기는 날 한 줄 더한다.

⚠ **앞으로 나는 씨앗은 이 파일이 못 막는다.** 만드는 경로(게이트 탐침 · 온보딩
  계측기 · 훈련 창 · 씨앗 명령)가 제 손으로 `data_source` 를 적어야 한다. 그 배선이
  남은 자리는 차선 B 보고의 「넘김」에 적혀 있다.
"""
from django.db import migrations, models

#: 출처 낱말. **여기서 정하지 않는다** — `common/billing_marks.py` 가 정본이다.
#: 마이그레이션은 앱 코드를 import 하지 않는 것이 규약이라(과거 상태를 보아야 한다)
#: 낱말만 옮겨 적고, 그 짝은 `tests/test_b_billing_marks.py` 가 붙든다.
PROBE, SEED, DRILL, LIVE = "probe", "seed", "drill", "live"

#: **얼어 있는 장부 — 규칙이 아니다.** (pk, code, 출처, 근거)
#: [실측 2026-09-21 11:37 · ETRI-Group(pk=4) · 살아 있는 카메라 15대 중 11대]
SEED_CAMERAS = (
    (3947, "gxprobe-D384-screen-CAM", PROBE,
     "게이트 화면 캡처용 탐침 카메라 (D384) — 사람이 안 쓴다"),
    (3948, "GX-ONB-V-20260917T090709", PROBE,
     "온보딩 계측기(measure_onboarding_t)가 09-17 에 심은 탐침"),
    (4474, "GX-ONB-V-20260918T054717", PROBE,
     "온보딩 계측기가 09-18 에 심은 탐침"),
    (4565, "GX-ONB-V-20260919T055539", PROBE,
     "온보딩 계측기가 09-19 에 심은 탐침"),
    (4686, "GX-ONB-V-20260919T101555", PROBE,
     "온보딩 계측기가 09-19 에 심은 탐침"),
    (4915, "GX-ONB-V-20260920T045202", PROBE,
     "온보딩 계측기가 09-20 에 심은 탐침"),
    (5055, "GX-ONB-V-20260920T081440", PROBE,
     "온보딩 계측기가 09-20 에 심은 탐침"),
    (119, "GX-SEED-DSM", SEED,
     "검수용 시드 카메라 — 제품은 실물처럼 세고 청구만 뺀다"),
    (5356, "GX-DRILL-ANYANG-01", DRILL,
     "훈련 창(UX-17)이 세운 안양천 시험카메라 1 — 훈련은 0원이다"),
    (5357, "GX-DRILL-ANYANG-02", DRILL,
     "훈련 창(UX-17)이 세운 안양천 시험카메라 2 — 훈련은 0원이다"),
    (5358, "GX-DRILL-ANYANG-03", DRILL,
     "훈련 창(UX-17)이 세운 안양천 시험카메라 3 — 훈련은 0원이다"),
)


def mark_seed_cameras(apps, schema_editor):
    """얼어 있는 11줄에만 표식을 단다. **pk 와 code 가 둘 다 맞을 때만.**"""
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    for pk, code, source, _reason in SEED_CAMERAS:
        Stream.objects.filter(pk=pk, code=code).update(data_source=source)


def unmark_seed_cameras(apps, schema_editor):
    """되돌리기 — 표식만 지운다. **행은 그대로다** (삭제 0).

    되돌릴 수 있는 변경만 둔다. 다만 되돌려도 **이미 낸 청구서는 안 되돌아온다** —
    칸을 더하는 것은 되돌릴 수 있어도 청구서를 다시 내는 것은 못 되돌린다.
    """
    Stream = apps.get_model("stream_monitors", "StreamMonitor")
    for pk, code, _source, _reason in SEED_CAMERAS:
        Stream.objects.filter(pk=pk, code=code).update(data_source=LIVE)


class Migration(migrations.Migration):

    dependencies = [
        ("stream_monitors", "0030_turn_u_u56"),
    ]

    operations = [
        migrations.AddField(
            model_name="streammonitor",
            name="data_source",
            field=models.CharField(
                db_index=True, default="live", max_length=32,
                help_text="청구 출처. live = 고객의 것(기본값) · probe/seed/drill = "
                          "우리가 심은 것으로 청구에서 뺀다. 빼는 판단은 "
                          "common/billing_marks.py 한 곳이 한다 (P-224)"),
        ),
        migrations.RunPython(mark_seed_cameras, unmark_seed_cameras),
    ]
