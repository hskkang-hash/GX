# -*- coding: utf-8 -*-
"""P-224 ② 잔여 — **0003 이 못 본 다섯 줄** (2026-09-22 · 턴 AD · 차선 B).

왜 또 마이그레이션인가 — **0003 은 한 시각의 사진이다**
--------------------------------------------------------
0003 은 [실측 2026-09-21 11:37]에 「지금 있는 것」을 얼렸다. 그런데 온보딩
계측기(`scripts/measure_onboarding_t.py` U5#1)는 **그 시각 전후로도 계속 돌았다**
— 그래서 0003 의 장부 11줄 안에도, `0031_p224_camera_data_source.py` 의 카메라
장부(`GX-ONB-V-*` 6줄, 전부 PROBE) 안에도 **없는** `gxprobe_onb_*` 계정 다섯이
남아 있었다. 계정 쪽은 카메라 쪽과 달리 **한 번도 소급되지 않았다**:

    [실측 2026-09-22 · 차선 B · docker exec ORM]
      118  gxprobe_onb_20260919T055539  is_active=False  표식 없음
      119  gxprobe_onb_20260919T101555  is_active=False  표식 없음
      224  gxprobe_onb_20260920T045202  is_active=False  표식 없음
      225  gxprobe_onb_20260920T081440  is_active=False  표식 없음
      226  gxprobe_onb_20260921T145138  is_active=True   표식 없음  ← **지금 청구 중**

118·119·224·225 는 `is_active=False`(측정기가 되돌렸다)라 커널의 `users` 셈이
`is_active=True` 만 걸러서 **지금 당장 청구되지는 않는다**(`kernels/k6_feedback/
services.py:334-337`). 그러나 **다시 활성화되는 날 조용히 청구된다** — 표식이
없으면 그날 아무도 모른다. 그래서 다섯 다 적는다(P-224 가 이미 5/6를 카메라
쪽에서 한 것과 같은 이유 — 「이번 것만」이 아니라 **series 전부**).

226 은 지금 `is_active=True` 로 **청구에 실제로 들어 있다** — 이 턴이 고치는
발급 순간 배선(§ `seed_role_users.py`·`probe_video_backup.py`·`capture_screens.py`)
과 짝을 이루는 소급이다.

이름을 근거로 썼다 — 0003 · 0031 과 **같은 예외**
--------------------------------------------------
`billing_marks.py` 는 세는 코드가 이름을 보는 것을 금지한다(D-280) — **이 파일은
세는 코드가 아니다.** 0003 머리말 그대로: 「아래 목록은 규칙이 아니라 장부다」.
`gxprobe_onb_<타임스탬프>` 접두는 `scripts/measure_onboarding_t.py` 의 U5#1 절이
직접 짓는 값이고(코드에 `probe_user` 변수로 등장), 카메라 쪽 짝(`GX-ONB-V-<같은
타임스탬프>`)이 **같은 회에 같은 타임스탬프로 태어난다** — 두 표를 대조해 사람이
확인했다. pk 로 얼렸으니 다음 달에 이 접두를 쓰는 고객이 와도 **이 장부는 안
움직인다**(규칙이 아니라 사진이므로).

★ 삭제 0. 표식만 단다. 다섯 계정 다 로그인 이력·감사에 그대로 남는다.
"""
from django.conf import settings
from django.db import migrations

#: 출처 낱말. 정본은 `common/billing_marks.py`.
PROBE = "probe"

#: 표 이름.
MODEL_LABEL = "user.coreuser"

#: **얼어 있는 장부 — 규칙이 아니다.** (pk, username, 출처, 근거)
#: [실측 2026-09-22 · 차선 B · turn-ad] `gxprobe_onb_*` 다섯 — 0003 이 못 본 것.
V_RESIDUAL_ACCOUNTS = (
    (118, "gxprobe_onb_20260919T055539", PROBE,
     "온보딩 계측기(measure_onboarding_t U5#1)가 09-19 에 만든 계정 — 카메라 짝 "
     "GX-ONB-V-20260919T055539(pk=4565, 0031 에서 이미 PROBE)와 같은 회"),
    (119, "gxprobe_onb_20260919T101555", PROBE,
     "온보딩 계측기가 09-19 에 만든 계정 — 카메라 짝 GX-ONB-V-20260919T101555"
     "(pk=4686, 0031 에서 이미 PROBE)와 같은 회"),
    (224, "gxprobe_onb_20260920T045202", PROBE,
     "온보딩 계측기가 09-20 에 만든 계정 — 카메라 짝 GX-ONB-V-20260920T045202"
     "(pk=4915, 0031 에서 이미 PROBE)와 같은 회"),
    (225, "gxprobe_onb_20260920T081440", PROBE,
     "온보딩 계측기가 09-20 에 만든 계정 — 카메라 짝 GX-ONB-V-20260920T081440"
     "(pk=5055, 0031 에서 이미 PROBE)와 같은 회"),
    (226, "gxprobe_onb_20260921T145138", PROBE,
     "출생 표본(D-310) — 턴 AB V 회차. is_active=True 로 **지금 청구 중**. 카메라 "
     "짝 GX-ONB-V-20260921T145138(pk=6144)은 이 턴 0032 가 같이 소급한다"),
)


def mark_v_residual_accounts(apps, schema_editor):
    """얼어 있는 다섯 줄에만 표식을 단다. **pk 와 username 이 둘 다 맞을 때만.**"""
    BillingMark = apps.get_model("common", "BillingMark")
    CoreUser = apps.get_model("user", "CoreUser")
    for pk, username, source, reason in V_RESIDUAL_ACCOUNTS:
        if not CoreUser.objects.filter(pk=pk, username=username).exists():
            continue
        BillingMark.objects.update_or_create(
            model_label=MODEL_LABEL, object_id=str(pk),
            defaults={"data_source": source, "reason": reason[:500]})


def unmark_v_residual_accounts(apps, schema_editor):
    """되돌리기 — 이 마이그레이션이 적은 줄만 거둔다. 계정 행은 안 건드린다."""
    BillingMark = apps.get_model("common", "BillingMark")
    BillingMark.objects.filter(
        model_label=MODEL_LABEL,
        object_id__in=[str(pk) for pk, *_ in V_RESIDUAL_ACCOUNTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0003_p224_seed_account_marks"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(mark_v_residual_accounts, unmark_v_residual_accounts),
    ]
