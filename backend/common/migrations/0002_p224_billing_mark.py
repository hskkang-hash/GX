# -*- coding: utf-8 -*-
"""P-224 ② — **칸을 못 더하는 표의 표식이 사는 곁표.**

왜 이 표가 서나
---------------
대표가 「청구 표식 칸을 **더해라**」라고 정했는데, 청구가 세는 표 넷 중 셋이
dj-core(`user.CoreUser` · `file_management.UserMediaFile` ·
`core.apikey_account.APIKey`)라 **칸을 못 더한다**(§0.4). 남의 표를 고치는 대신
**우리 표에 사실을 적는다** — `common/models.py` 머리말이 그 판단이다.

★ **이 마이그레이션은 아무 행도 안 건드린다.** 표 하나를 세울 뿐이다. 어느 행이
  우리 것인가를 적는 일은 다음 마이그레이션(`0003_p224_seed_account_marks`)이
  하고, 그것은 **얼어 있는 pk 목록**으로 한다 — 이름으로 훑지 않는다 (D-280).

`initial = False` 인 이유
-------------------------
`--fake-initial` 이 이 마이그레이션을 「이미 적용됐다」로 **건너뛰지 못하게** 한다.
건너뛰면 `django_migrations` 에는 줄이 서고 표는 안 생긴다 — 거짓 초록이다.
(`0001_audit_logger_name_index` 가 같은 이유로 같은 줄을 갖고 있다.)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    # 위 머리말 참조 — 이 앱의 첫 모델이지만 **건너뛰기 대상이 되면 안 된다**.
    initial = False

    dependencies = [
        ('common', '0001_audit_logger_name_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillingMark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_label', models.CharField(db_index=True, help_text='표 이름(app_label.modelname · 소문자). 가리키는 표가 사라져도 이 줄은 남는다 — 여기 적는 것은 관계가 아니라 사실이다.', max_length=100)),
                ('object_id', models.CharField(max_length=64)),
                ('data_source', models.CharField(db_index=True, max_length=32)),
                ('reason', models.CharField(blank=True, default='', max_length=500)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '청구 표식',
                'verbose_name_plural': '청구 표식',
                'db_table': 'common_billing_mark',
                'unique_together': {('model_label', 'object_id')},
            },
        ),
    ]
