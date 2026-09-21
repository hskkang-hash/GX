# -*- coding: utf-8 -*-
"""P-224 ② — **우리가 만든 시험 계정을 청구에서 뺀다** (2026-09-21 · 턴 AB · 차선 B).

무엇을 고치나
-------------
    [실측 2026-09-21 11:37 · 마이그레이션 전]
      ETRI-Group 청구에 든 계정            30개
        그중 우리가 만든 씨앗·탐침         11개   (36.7 %)
        고객의 계정                         19개
      ★ 다른 테넌트 아홉의 씨앗은 **0**이다 — 수가 바뀌는 고객은 이 하나뿐이다.

★ **분모를 보지 않고 수를 옮기지 않는다.** 턴 AA 에 「105개 중 11개(10 %)」로
  올라갔던 수가 있었는데, **105 는 전 테넌트 합**이었다. 같은 테넌트는 30개이고,
  그래서 실제 비중은 10 % 가 아니라 **37 %** 였다 — 3.7배 과소평가.
  이 파일이 적는 분모는 **한 고객의 청구 계정 30**이다.

왜 칸이 아니라 곁표인가
-----------------------
`user.CoreUser` 는 **dj-core** 다(§0.4). 칸을 더할 수도, 그 행을 고칠 수도 없다.
그래서 **남의 행은 한 자도 안 건드리고** 우리 표(`common.BillingMark`)에
「저 행은 우리가 만든 것」이라고 적는다. 읽는 자리는
`common/billing_marks.exclude_unbillable` 하나다.

★ **이름으로 안 거른다 — pk 로 언다** (D-280).
  `username__startswith` 는 **규칙**이고 규칙은 다음 달에도 돈다: 고객 계정 하나가
  우리 접두와 겹치는 날 그 계정이 조용히 공짜가 된다. 아래 목록은 규칙이 아니라
  **장부**다 — 2026-09-21 11:37 에 한 줄씩 보고 근거를 적은 11줄이고 여기서 끝난다.
  ★ 그 11줄 중 **4줄은 표식이 이미 있었다**(`UserProfileLink.employee_id` 가
    `GX-SEED-ROLE-*` — `seed_role_users` 가 만드는 자리에서 적은 것). 나머지 7줄은
    게이트 탐침 경로가 만들었고 **아무 표식도 안 남겼다** — 그 7줄의 근거는 조율자의
    창 표(`docs/agent/checkpoints/turn-ab/_규약.md` 「창 표」)에 이름으로 등재된
    우리 계정이라는 **사람의 확인**이고, 그 사실을 여기 적어 둔다.
    *근거가 약한 줄과 강한 줄을 같은 칸에 섞지 않는다 — `reason` 이 가른다.*

★ **삭제 0** (P-222). 계정을 지우는 것이 아니라 **청구에서 빼는** 것이다.
  이 계정들은 로그인도 되고 감사에도 그대로 남는다 — 바뀌는 것은 셈뿐이다 (D-497).

⚠ **저장(미디어) 장부는 이 파일이 못 건드린다.** 미디어 행에는 표식도 없고
  이름·만든이로도 씨앗이 안 갈린다[실측: 이름 0건 · 만든이가 씨앗 계정 0건].
  그것은 **정황이지 표식이 아니다.** 0으로 덮지 않는다 (D-301).
"""
from django.conf import settings
from django.db import migrations

#: 표 이름. `CoreUser._meta.label_lower` 그대로다.
MODEL_LABEL = "user.coreuser"

#: 출처 낱말 — 정본은 `common/billing_marks.py`. 마이그레이션은 앱 코드를 import
#: 하지 않는 것이 규약이라(과거 상태를 보아야 한다) 낱말만 옮겨 적고, 그 짝은
#: `tests/test_b_billing_marks.py` 가 붙든다.
PROBE, SEED = "probe", "seed"

#: **얼어 있는 장부 — 규칙이 아니다.** (pk, username, 출처, 근거)
SEED_ACCOUNTS = (
    (110, "gxseed_u1_operator", SEED,
     "seed_role_users 가 만든 역할 씨앗 (employee_id=GX-SEED-ROLE-U1) — 만든 "
     "자리가 남긴 표식이 근거다"),
    (108, "gxseed_u2_manager", SEED,
     "seed_role_users 가 만든 역할 씨앗 (employee_id=GX-SEED-ROLE-U2)"),
    (109, "gxseed_u4_official", SEED,
     "seed_role_users 가 만든 역할 씨앗 (employee_id=GX-SEED-ROLE-U4)"),
    (115, "gxseed_u5_sysop", SEED,
     "seed_role_users 가 만든 역할 씨앗 (employee_id=GX-SEED-ROLE-U5)"),
    (117, "gxseed_u5_newop", SEED,
     "온보딩 첫 근무일 계측용 예비 계정 — employee_id 표식 없음. 근거는 턴 AB "
     "_규약.md 창 표에 등재된 우리 계정이라는 조율자 확인이다"),
    (105, "gxprobe_e2e", PROBE,
     "게이트 종단 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표(조율자 확인)"),
    (111, "gxprobe_s", PROBE,
     "차선 S 게이트 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표"),
    (112, "gxprobe_q", PROBE,
     "차선 Q 게이트 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표"),
    (113, "gxprobe_e", PROBE,
     "게이트 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표"),
    (114, "gxprobe_c", PROBE,
     "게이트 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표"),
    (116, "gxprobe_v", PROBE,
     "차선 V 전용 탐침 계정 — 표식 없음. 근거는 턴 AB _규약.md 창 표"),
)


def mark_seed_accounts(apps, schema_editor):
    """얼어 있는 11줄에만 표식을 남긴다. **pk 와 username 이 둘 다 맞을 때만.**

    ★ pk 만 보면 다른 DB(스테이징·시험)에서 **엉뚱한 고객 계정**이 공짜가 된다 —
      그 DB 의 110번은 우리 씨앗이 아니다. 둘이 다 맞을 때만 적고, 안 맞으면 조용히
      건너뛴다(그 DB 에는 우리 씨앗이 없다는 뜻이다).
    ★ `update_or_create` — 두 번 적용해도 같은 자리에 같은 한 줄이다.
    """
    BillingMark = apps.get_model("common", "BillingMark")
    CoreUser = apps.get_model("user", "CoreUser")
    for pk, username, source, reason in SEED_ACCOUNTS:
        if not CoreUser.objects.filter(pk=pk, username=username).exists():
            continue
        BillingMark.objects.update_or_create(
            model_label=MODEL_LABEL, object_id=str(pk),
            defaults={"data_source": source, "reason": reason[:500]})


def unmark_seed_accounts(apps, schema_editor):
    """되돌리기 — **이 마이그레이션이 적은 줄만** 거둔다 (P-222 되돌리기).

    계정 행은 한 자도 안 건드린다. 되돌려도 **이미 낸 청구서는 안 되돌아온다.**
    """
    BillingMark = apps.get_model("common", "BillingMark")
    BillingMark.objects.filter(
        model_label=MODEL_LABEL,
        object_id__in=[str(pk) for pk, *_ in SEED_ACCOUNTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_p224_billing_mark"),
        #: dj-core 의 계정 표를 **읽기만** 한다 — 그 앱을 고치지 않는다
        #: (`0001_audit_logger_name_index` 가 감사 표를 읽는 것과 같은 자리).
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(mark_seed_accounts, unmark_seed_accounts),
    ]
